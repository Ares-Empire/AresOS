"""Execute the real guest VCSA reader against retained-screen fixtures."""
import base64
import contextlib
import hashlib
import io
import json
import pathlib
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_console as vc
import owner_vm as vm
from guest_shell import syntax

FIXTURE = ROOT / 'os/tests/fixtures/owner-console'
PROMPT = b'root@bazzite:~# '


def redrawn():
    return bytes([1, 80, len(PROMPT), 0]) + b''.join(
        bytes([char, 7]) for char in PROMPT.ljust(80))


class Clock:
    now = 0
    def monotonic(self): return self.now
    def sleep(self, seconds): self.now += seconds


class Guest:
    owner_layout = 'de'
    def __init__(self):
        self.raw = redrawn()
        self.pressed, self.reads = [], []
        self.redraw_on_enter = False

    def keys(self, keys):
        self.pressed.append(keys)
        if keys == ['ret'] and self.redraw_on_enter:
            self.raw = redrawn()

    def capture_json(self, name, command):
        syntax(name, command)
        words = shlex.split(command)
        index = words.index('python3')
        assert words[index + 1] == '-c'
        source = words[index + 2]
        def read(path):
            assert str(path) in ('/dev/vcsa3', '/dev/vcsa4')
            self.reads.append(str(path))
            return self.raw
        output = io.StringIO()
        with patch.object(pathlib.Path, 'read_bytes', read), contextlib.redirect_stdout(output):
            exec(compile(source, name, 'exec'), {})
        return json.loads(output.getvalue())


class ConsoleTest(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        temporary = self.stack.enter_context(tempfile.TemporaryDirectory(dir=ROOT / 'os/tests'))
        self.evidence = pathlib.Path(temporary)
        self.stack.enter_context(patch.object(vm.td, 'EVIDENCE', self.evidence))
        self.clock = Clock()
        self.stack.enter_context(patch.object(vc.time, 'monotonic', self.clock.monotonic))
        self.stack.enter_context(patch.object(vc.time, 'sleep', self.clock.sleep))
        self.guest = Guest()
        self.console = vm.Console(self.guest)
        self.clutter = (FIXTURE / '14i-hotplug.vcsa').read_bytes()

    def complete_then_clutter(self):
        self.console.prompt('completion-observed')
        self.guest.raw = self.clutter

    def test_exact_14i_prompt_kernel_cursor_region_recovers_with_one_physical_enter(self):
        index = json.loads((FIXTURE / 'sources.json').read_text())
        self.assertEqual(hashlib.sha256(self.clutter).hexdigest(), index['files'][0]['sha256'])
        self.assertEqual(hashlib.sha256((ROOT / index['source']['path']).read_bytes()).hexdigest(), index['source']['sha256'])
        self.assertEqual(list(self.clutter[:4]), [50, 160, 0, 49])
        full, line = vc.screen(self.clutter)
        self.assertIn('root@bazzite:~# [   68.583969] usb 2-2:', full)
        self.assertIn('[   69.699761] sd 6:0:0:0: [sda] Attached SCSI removable disk', full)
        self.assertEqual(line, '')
        self.complete_then_clutter()
        self.guest.redraw_on_enter = True
        self.console.prompt('tools-install-ready')
        self.assertEqual(self.guest.pressed, [['ret']])
        event = json.loads((self.evidence / 'tools-install-ready-resync-1.json').read_text())
        self.assertEqual(event['stage'], 'tools-install-ready')
        self.assertEqual(event['before_cursor_line'], '')
        self.assertEqual(event['after_cursor_line'], PROMPT.decode().rstrip())
        self.assertTrue(event['ready'])
        self.assertTrue(event['enter_sent'])
        self.assertTrue(event['time'] and event['after_time'])
        self.assertEqual((self.evidence / 'tools-install-ready-timeout-1.vcsa').read_bytes(), self.clutter)

    def test_busy_shell_never_gets_enter_and_retains_raw_timeout(self):
        self.console.prompt('completion-observed')
        vm.type_text(self.guest, 'sleep 300\n')
        self.guest.raw = self.clutter
        before = list(self.guest.pressed)
        with self.assertRaisesRegex(AssertionError, 'readiness deadline'):
            self.console.prompt('busy')
        self.assertEqual(self.guest.pressed, before)
        self.assertEqual((self.evidence / 'busy-timeout-1.vcsa').read_bytes(), self.clutter)
        self.assertFalse(list(self.evidence.glob('busy-resync*')))
        self.assertIsNone(self.console.completed_epoch)

    def test_three_cluttered_screens_fail_after_two_enters(self):
        self.complete_then_clutter()
        with self.assertRaisesRegex(AssertionError, 'readiness deadline'):
            self.console.prompt('clutter')
        self.assertEqual(self.guest.pressed, [['ret'], ['ret']])
        self.assertEqual(len(list(self.evidence.glob('clutter-timeout-*.vcsa'))), 3)
        for attempt in (1, 2):
            event = json.loads((self.evidence / f'clutter-resync-{attempt}.json').read_text())
            self.assertEqual(event['before_cursor_line'], event['after_cursor_line'])
            self.assertFalse(event['ready'])
        self.assertIsNone(self.console.completed_epoch)

    def test_unknown_shell_and_other_console_typing_revoke_idle_authority(self):
        self.guest.raw = self.clutter
        with self.assertRaises(AssertionError): self.console.prompt('unknown')
        self.assertEqual(self.guest.pressed, [])
        self.guest.raw = redrawn()
        self.console.prompt('completion-observed')
        other = vm.Console(self.guest, 'tty4')
        other.prompt('other-completed')
        vm.type_text(self.guest, 'x')
        self.guest.raw = self.clutter
        before = list(self.guest.pressed)
        for console in (self.console, other):
            with self.assertRaises(AssertionError): console.prompt('revoked-' + console.tty)
        self.assertEqual(self.guest.pressed, before)

    def test_login_and_input_waits_never_resync_even_after_completion(self):
        self.complete_then_clutter()
        with self.assertRaises(AssertionError):
            vm.wait_tty(self.guest, 'tty3', "line.endswith('login:')", 'login', timeout=1)
        self.assertEqual(self.guest.pressed, [])
        self.assertEqual((self.evidence / 'login-timeout-1.vcsa').read_bytes(), self.clutter)

    def test_input_during_wait_revokes_the_grant_before_any_enter(self):
        self.complete_then_clutter()
        original = self.guest.capture_json
        def capture(name, command):
            value = original(name, command)
            vm.type_text(self.guest, 'x')
            return value
        self.guest.capture_json = capture
        with self.assertRaisesRegex(AssertionError, 'Input revoked idle proof'):
            self.console.prompt('intervening-input')
        self.assertEqual(self.guest.pressed, [['x']])
        event = json.loads((self.evidence / 'intervening-input-resync-1.json').read_text())
        self.assertFalse(event['enter_sent'])
        self.assertIsNone(self.console.completed_epoch)

    def test_reader_keeps_strict_cursor_predicate_and_three_stable_samples(self):
        self.console.prompt('stable')
        self.assertEqual(len(self.guest.reads), 3)
        self.assertGreaterEqual(self.clock.now, 0.4)
        self.assertEqual(self.console.completed_epoch, 0)
        for raw in (b'', self.clutter[:-1], bytes([0, 160, 0, 49]) + self.clutter[4:],
                    bytes([50, 160, 160, 49]) + self.clutter[4:]):
            with self.assertRaises(AssertionError): vc.screen(raw)

    def test_prompt_present_but_not_yet_stable_never_gets_an_enter(self):
        retained, pressed = [], []
        value = dict(ready=False, raw=base64.b64encode(redrawn()).decode())
        # A prompt appearing on the last sample has not met three samples yet.
        with self.assertRaisesRegex(AssertionError, 'readiness deadline'):
            vc.wait(lambda seconds: value, 90,
                lambda phase, raw: retained.append(raw),
                resync=lambda: pressed.append('ret'), record=lambda event: None)
        self.assertEqual(pressed, [])
        self.assertEqual(retained, [redrawn()] * 3)

    def test_hidden_readiness_timeout_keeps_raw_without_an_enter(self):
        import os
        self.guest.raw = self.clutter
        with patch.object(os, 'open', side_effect=OSError('Synthetic busy tty')):
            with self.assertRaisesRegex(AssertionError, 'No hidden prompt'):
                self.console.hidden('hidden')
        self.assertEqual(self.guest.pressed, [])
        self.assertEqual((self.evidence / 'hidden-timeout-1.vcsa').read_bytes(), self.clutter)


if __name__ == '__main__': unittest.main()
