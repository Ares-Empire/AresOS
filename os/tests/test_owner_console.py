"""Execute the real guest VCSA reader against retained-screen fixtures."""
import base64
import contextlib
import hashlib
import io
import json
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_console as vc
import owner_vm as vm
from guest_shell import syntax as guest_syntax
from owner_console_shim import execute_idle
from test_owner_sudo_idle import relay, row, PTS

FIXTURE = ROOT / 'os/tests/fixtures/owner-console'
PROMPT = b'root@bazzite:~# '
HOST_SLEEP, HOST_MONOTONIC = time.sleep, time.monotonic


def syntax(name, source):
    # subprocess.wait may sleep while the Bash parser exits. Those real host
    # waits must not spend the fake guest's readiness deadline by spinning.
    with patch.object(time,'sleep',HOST_SLEEP),patch.object(time,'monotonic',HOST_MONOTONIC):
        guest_syntax(name,source)


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
        self.proc_rows = relay()

    def keys(self, keys):
        self.pressed.append(keys)
        if keys == ['ret'] and self.redraw_on_enter:
            self.raw = redrawn()

    def resync_after_hidden(self, stage):
        return dict(status='passed', prior_completion_observed=True,
            serial_input_flushed=True, raw_output_retained=False, physical_enter_sent=False)

    def capture_json(self, name, command):
        syntax(name, command)
        words = shlex.split(command)
        index = words.index('python3')
        assert words[index + 1] == '-c'
        source = words[index + 2]
        if "ready=shell" in source:
            return execute_idle(source, self.raw, self.proc_rows)
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

    def receipt(self, pattern):
        expression = re.escape(pattern).replace('\\-resync\\-', r'\-wait-\d+\-resync\-').replace('\\-timeout\\-', r'\-wait-\d+\-timeout\-')
        paths = [p for p in self.evidence.iterdir() if re.fullmatch(expression, p.name)]
        self.assertEqual(len(paths), 1, pattern)
        return paths[0]

    def test_host_parser_exit_wait_cannot_spend_guest_deadline(self):
        original=subprocess.Popen
        def delayed_exit(args,**kwargs):
            self.assertEqual(args,['bash','--noprofile','--norc','-n'])
            # Pipes may close before process exit. Popen's real wait sleeps
            # must never advance the simulated physical-console clock.
            return original(['bash','--noprofile','--norc','-c',
                'exec 1>&- 2>&-; sleep 0.02'],**kwargs)
        before=self.clock.now
        with patch.object(subprocess,'Popen',side_effect=delayed_exit):syntax('host-wait','true\n')
        self.assertEqual(self.clock.now,before)

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
        event = json.loads(self.receipt('tools-install-ready-resync-1.json').read_text())
        self.assertTrue(event['stage'].startswith('tools-install-ready-wait-'))
        self.assertTrue(event['observer']['observation']['ready'])
        self.assertEqual(event['before_cursor_line'], '')
        self.assertEqual(event['after_cursor_line'], PROMPT.decode().rstrip())
        self.assertTrue(event['ready'])
        self.assertTrue(event['enter_sent'])
        self.assertTrue(event['time'] and event['after_time'])
        self.assertEqual(self.receipt('tools-install-ready-timeout-1.vcsa').read_bytes(), self.clutter)

    def test_busy_shell_never_gets_enter_and_retains_raw_timeout(self):
        self.clutter = (FIXTURE / '14zg-title-completed.vcsa').read_bytes()
        self.console.prompt('completion-observed')
        vm.type_text(self.guest, 'sleep 300\n')
        self.guest.proc_rows[2]['tpgid'] = self.guest.proc_rows[3]['tpgid'] = 23
        self.guest.proc_rows.append(row(23, 22, 23, 21, PTS, 23, 'sleep', ['sleep', '300']))
        self.guest.raw = self.clutter
        before = list(self.guest.pressed)
        with self.assertRaisesRegex(AssertionError, 'idle observer refused'):
            self.console.prompt('busy')
        self.assertEqual(self.guest.pressed, before)
        self.assertEqual(self.receipt('busy-timeout-1.vcsa').read_bytes(), self.clutter)
        event = json.loads(self.receipt('busy-resync-1.json').read_text())
        self.assertFalse(event['enter_sent'])
        self.assertFalse(event['observer']['ready'])
        self.assertEqual(event['before_cursor_line'], event['after_cursor_line'])
        self.assertTrue(event['observer']['observation']['foreground_chain'])
        self.assertIsNone(self.console.completed_epoch)

    def test_three_cluttered_screens_fail_after_two_enters(self):
        self.complete_then_clutter()
        with self.assertRaisesRegex(AssertionError, 'readiness deadline'):
            self.console.prompt('clutter')
        self.assertEqual(self.guest.pressed, [['ret'], ['ret']])
        self.assertEqual(len(list(self.evidence.glob('clutter-wait-*-timeout-*.vcsa'))), 3)
        for attempt in (1, 2):
            event = json.loads(self.receipt(f'clutter-resync-{attempt}.json').read_text())
            self.assertEqual(event['before_cursor_line'], event['after_cursor_line'])
            self.assertFalse(event['ready'])
            self.assertTrue(event['observer']['ready'])
        self.assertIsNone(self.console.completed_epoch)

    def test_fresh_idle_proof_replaces_stale_completion_for_every_wait_kind(self):
        self.guest.raw = (FIXTURE / '14zg-title-completed.vcsa').read_bytes()
        self.guest.redraw_on_enter = True
        for kind in ('completed', 'after-hidden', 'after-hotplug', 'after-network', 'after-boot'):
            for console in (self.console, vm.Console(Guest())):
                console.guest.raw = (FIXTURE / '14zg-title-completed.vcsa').read_bytes()
                console.guest.redraw_on_enter = True
                vm.type_text(console.guest, 'x')  # Previous epoch cannot be authority.
                console.completed_epoch = None
                console.prompt(kind)
        events = [json.loads(p.read_text()) for p in self.evidence.glob('*-resync-1.json')]
        self.assertEqual(len(events), 10)
        self.assertEqual(len({e['stage'] for e in events}), 10)
        self.assertTrue(all(e['enter_sent'] and e['ready'] and e['observer']['ready'] for e in events))

    def test_exact_qualification6_cursor_region_and_idle_relay_recovers(self):
        index = json.loads((FIXTURE / '14zg-source.json').read_text())
        self.guest.raw = raw = (FIXTURE / index['path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), index['sha256'])
        self.assertEqual(list(raw[:4]), [50, 160, 0, 49])
        full, line = vc.screen(raw)
        self.assertIn('root@bazzite:~# [  273.927657] sched: DL replenish lagged too much', full)
        self.assertEqual(line, '')
        self.guest.redraw_on_enter = True
        self.console.prompt('after-first-network-title-completed')
        self.assertEqual(self.guest.pressed, [['ret']])
        event = json.loads(self.receipt('after-first-network-title-completed-resync-1.json').read_text())
        self.assertEqual(event['observer']['observation']['reason'], 'sudo -i monitor to foreground pts interactive bash')
        self.assertEqual(event['after_cursor_line'], PROMPT.decode().rstrip())

    def test_login_and_input_waits_never_resync_even_after_completion(self):
        self.complete_then_clutter()
        with self.assertRaises(AssertionError):
            vm.wait_tty(self.guest, 'tty3', "line.endswith('login:')", 'login', timeout=1)
        self.assertEqual(self.guest.pressed, [])
        self.assertEqual(self.receipt('login-timeout-1.vcsa').read_bytes(), self.clutter)

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
        event = json.loads(self.receipt('intervening-input-resync-1.json').read_text())
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
                resync=lambda: pressed.append('ret'), record=lambda event: None,
                observe=lambda seconds, attempt: self.fail('Prompt already on cursor line'))
        self.assertEqual(pressed, [])
        self.assertEqual(retained, [redrawn()] * 3)

    def test_hidden_readiness_timeout_keeps_raw_without_an_enter(self):
        import os
        self.guest.raw = self.clutter
        with patch.object(os, 'open', side_effect=OSError('Synthetic busy tty')):
            with self.assertRaisesRegex(AssertionError, 'No verified hidden prompt'):
                self.console.hidden('hidden', dict(kind='login'), 'Password:')
        self.assertEqual(self.guest.pressed, [])
        retained, = self.evidence.glob('hidden-read-wait-*-timeout-1.vcsa')
        self.assertEqual(retained.read_bytes(), self.clutter)

    def test_hidden_busy_shell_never_grants_enter_or_prompt_authority(self):
        self.guest.owner_input_epoch=7
        value=dict(ready=False,echo_enabled=False,foreground_shell=False,raw=base64.b64encode(self.clutter).decode())
        with patch.object(self.guest,'capture_json',return_value=value),patch.object(self.console,'prompt') as prompt, \
             self.assertRaisesRegex(AssertionError,'idle shell'):
            self.console.after_hidden('secret-busy')
        prompt.assert_not_called();self.assertEqual(self.guest.pressed,[])
        self.assertIsNone(self.console.completed_epoch)
        self.assertEqual((self.evidence/'secret-busy-physical-idle-timeout-1.vcsa').read_bytes(),self.clutter)

    def test_hidden_completion_grants_only_existing_two_enter_prompt_rule(self):
        self.guest.owner_input_epoch=7;self.guest.raw=self.clutter;self.guest.redraw_on_enter=True
        capture=self.guest.capture_json
        def observe(name,source):
            if name.endswith('-physical-idle'):
                syntax(name,source)
                return dict(ready=True,echo_enabled=False,foreground_shell=True,raw='')
            return capture(name,source)
        with patch.object(self.guest,'capture_json',side_effect=observe):self.console.after_hidden('secret-done')
        self.assertEqual(self.guest.pressed,[['ret']])
        self.assertTrue(json.loads(self.receipt('secret-done-after-hidden-ready-resync-1.json').read_text())['enter_sent'])
        self.assertTrue(json.loads((self.evidence/'secret-done-hidden-completed.json').read_text())['foreground_shell'])

    def test_departed_reader_with_clutter_redraws_then_reproves_the_transition(self):
        from owner_console_shim import execute_hidden
        capture=self.guest.capture_json
        observed=[]
        def observe(name,source):
            if '# hidden-phase:' in source:
                script=shlex.split(source)[shlex.split(source).index('python3')+2]
                raw=None if '# hidden-phase: ready' in script else self.guest.raw
                value=execute_hidden(script,raw=raw)
                observed.append((name,value['ready']))
                if not value['ready']:self.guest.redraw_on_enter=True
                return value
            return capture(name,source)
        with patch.object(self.guest,'capture_json',side_effect=observe):
            self.console.hidden('transition',dict(kind='login'),'Password:')
            self.guest.raw=self.clutter;self.guest.redraw_on_enter=False
            value=self.console.send_hidden('synthetic-fixture')
        self.assertTrue(value['ready'] and value['reader_left'])
        self.assertIsNone(self.console.pending_hidden)
        self.assertEqual([ready for _,ready in observed],[True,False,True])
        self.assertTrue(observed[-1][0].endswith('-left-after-resync'))
        # One Enter terminates the sole synthetic hidden send; the other is
        # the existing independently-observed idle prompt redraw.
        self.assertEqual(self.guest.pressed.count(['ret']),2)
        event,=self.evidence.glob('*transition-prompt*resync-1.json')
        self.assertTrue(json.loads(event.read_text())['observer']['ready'])

    def test_typing_during_hidden_completion_revokes_enter_authority(self):
        self.guest.owner_input_epoch=7
        def observe(*args):
            self.guest.owner_input_epoch+=1
            return dict(ready=True,echo_enabled=False,foreground_shell=True,raw='')
        with patch.object(self.guest,'capture_json',side_effect=observe),patch.object(self.console,'prompt') as prompt, \
             self.assertRaisesRegex(AssertionError,'revoked hidden'):
            self.console.after_hidden('secret-revoked')
        prompt.assert_not_called();self.assertIsNone(self.console.completed_epoch);self.assertEqual(self.guest.pressed,[])


if __name__ == '__main__': unittest.main()
