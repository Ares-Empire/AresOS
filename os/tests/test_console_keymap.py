"""Package 50: boot unit and disposable-guest checks, with no host console or service access."""
import ast
import configparser
from contextlib import nullcontext
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'os/ci'), str(ROOT / 'os/ci/overlay')]
import console_keymap as console
import checks

UNIT_PATH = ROOT / 'os/config/usr/lib/systemd/system' / console.UNIT


def properties(**changes):
    return dict(LoadState='loaded', ActiveState='active', SubState='exited', Result='success',
                ExecMainCode='1', ExecMainStatus='0', ExecMainStartTimestampMonotonic='100',
                ExecMainExitTimestampMonotonic='110', InvocationID='a' * 32, **changes)


def result(stdout=''):
    return dict(returncode=0, stdout=stdout, stderr='')


def dump(keymap):
    name = 'de' if keymap == 'de' else 'us'
    return (ROOT / f'os/tests/fixtures/keyboard/{name}-dumpkeys.txt').read_text()


class ImageUnitTest(unittest.TestCase):
    def check_content(self, text):
        source = (ROOT / 'os/ci/image-checks.sh').read_text().split("<<'CONSOLE_UNIT'\n", 1)[1].split('\nCONSOLE_UNIT', 1)[0]
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / console.UNIT
            path.write_text(text)
            with patch.object(sys, 'argv', ['unit-check', str(path)]):
                exec(compile(source, 'image-checks.sh CONSOLE_UNIT', 'exec'), {})

    def test_shipped_unit_passes_the_real_image_content_check(self):
        self.check_content(UNIT_PATH.read_text())
        self.assertEqual(UNIT_PATH.stat().st_mode & 0o777, 0o644)
        self.assertIn('systemctl enable ' + console.UNIT, (ROOT / 'os/build.sh').read_text())

    def test_image_check_rejects_a_blocking_repeating_or_hardcoded_unit(self):
        text = UNIT_PATH.read_text()
        mutations = [text.replace('DefaultDependencies=no', 'DefaultDependencies=yes'),
                     text.replace('After=graphical.target ', 'After='),
                     text.replace('plymouth-quit-wait.service ', ''),
                     text.replace(' systemd-vconsole-setup.service', ''),
                     text.replace('TimeoutStartSec=15s', 'TimeoutStartSec=infinity'),
                     text.replace(console.SETUP + ' /dev/tty3', 'loadkeys -C /dev/tty3 -- de'),
                     text.replace('Type=oneshot', 'Type=simple'),
                     text.replace('WantedBy=graphical.target', 'RequiredBy=graphical.target'),
                     text.replace('RemainAfterExit=yes', 'RemainAfterExit=no'),
                     text.replace('[Service]', '[Service]\nRestart=always'),
                     text.replace('[Unit]', '[Unit]\nBefore=greetd.service'),
                     text + '\n[Timer]\nOnBootSec=1\n']
        for changed in mutations:
            with self.subTest(unit=changed), self.assertRaises((AssertionError, configparser.Error)):
                self.check_content(changed)

    def test_image_checks_ownership_regular_file_enablement_and_exact_link(self):
        source = (ROOT / 'os/ci/image-checks.sh').read_text()
        for check in ('test -f "$console_unit"', 'test ! -L "$console_unit"',
                      'test "$(stat -c \'%a %u %g\' "$console_unit")" = \'644 0 0\'',
                      'test "$(systemctl --root=/ is-enabled ' + console.UNIT + ')" = enabled',
                      'test "$(readlink "$console_link")" = "$console_unit"',
                      'test "$(stat -c \'%a %u %g\' "$console_link")" = \'777 0 0\''):
            self.assertIn(check, source)


class ConfiguredAndLoadedKeysTest(unittest.TestCase):
    def test_supported_config_with_comments_quotes_whitespace_and_last_assignment(self):
        for keymap in ('de', 'us', 'us-intl'):
            for quoted in (keymap, '"' + keymap + '"', "'" + keymap + "'"):
                text = '# KEYMAP=fr\nFONT="some-font"\nKEYMAP=us\n KEYMAP = ' + quoted + '\n'
                self.assertEqual(console.configured_map(text), keymap)

    def test_missing_unsupported_or_executable_config_fails_closed(self):
        for text in ('', '#KEYMAP=de', 'KEYMAP=fr', 'KEYMAP=', 'KEYMAP="de',
                     'KEYMAP=$(touch /never)', 'KEYMAP=de;false', 'KEYMAP=de us'):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                console.configured_map(text)

    def test_both_retained_layouts_and_all_owner_check_symbol_spellings(self):
        for keymap in ('de', 'us', 'us-intl'):
            self.assertEqual(set(console.loaded_keys(dump(keymap), keymap)), {'21', '44'})
            letters = ('z', 'y') if keymap == 'de' else ('y', 'z')
            for spelling in (lambda c: c, lambda c: '+' + c, lambda c: 'U+' + format(ord(c), '04x'),
                             lambda c: '+U+' + format(ord(c), '04x')):
                text = ''.join(f'keycode {code} = {spelling(letter)} OtherSymbol\n'
                               for code, letter in zip((21, 44), letters))
                self.assertEqual(set(console.loaded_keys(text, keymap)), {'21', '44'})

    def test_wrong_missing_duplicate_and_shifted_only_keys_are_rejected(self):
        correct = dump('de')
        for text in (dump('us'), '', correct.replace('keycode  44', 'keycode  45'), correct + correct,
                     'shift keycode 21 = +z\nshift keycode 44 = +y\n', correct.replace('+z', '+Z')):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                console.loaded_keys(text, 'de')


class UnitResultTest(unittest.TestCase):
    def observe(self, values):
        text = '\n'.join(key + '=' + value for key, value in values.items())
        with patch.object(console, 'command', return_value=result(text)):
            return console.successful_unit()

    def test_a_real_successful_execution_is_required(self):
        self.assertEqual(self.observe(properties()), properties())
        changes = [('LoadState', 'not-found'), ('ActiveState', 'failed'), ('Result', 'exit-code'),
                   ('ExecMainCode', '2'), ('ExecMainStatus', '1'), ('ExecMainStartTimestampMonotonic', '0'),
                   ('ExecMainExitTimestampMonotonic', '99'), ('InvocationID', ''), ('InvocationID', 'not-an-id')]
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.observe(dict(properties(), **{key: value}))

    def test_waits_for_boot_without_starting_or_restarting_the_service(self):
        rows = [dict(properties(), ActiveState='inactive', SubState='dead'),
                dict(properties(), ActiveState='activating', SubState='start'), properties()]
        with patch.object(console, 'command', side_effect=[result('\n'.join(k + '=' + v for k, v in p.items()))
                                                         for p in rows]) as command, patch.object(console.time, 'sleep'):
            self.assertEqual(console.successful_unit(), properties())
        self.assertTrue(all(call.args[:2] == ('systemctl', 'show') for call in command.call_args_list))

    def test_timeout_is_a_failure(self):
        with patch.object(console, 'command', return_value=result('LoadState=loaded\nActiveState=inactive\n')), \
                patch.object(console.time, 'monotonic', side_effect=[0, 31]), self.assertRaises(TimeoutError):
            console.successful_unit()

    def test_failed_external_command_is_not_treated_as_a_success(self):
        failed = subprocess.CompletedProcess(['fixture-only'], 3, stdout='', stderr='injected failure')
        with patch.object(console.subprocess, 'run', return_value=failed) as run, self.assertRaises(AssertionError):
            console.command('fixture-only')
        self.assertEqual(run.call_args.kwargs['timeout'], 30)


class GraphicsCleanupTest(unittest.TestCase):
    def exercise(self, *, fail_set=False, fail_body=False, fail_restore=False):
        modes, closed, events = {10: console.KD_GRAPHICS, 30: console.KD_TEXT}, [], []
        failed = False

        def ioctl(fd, operation, value, *extra):
            nonlocal failed
            if operation == console.KDGETMODE:
                value[0] = modes[fd]
                return 0
            self.assertEqual(operation, console.KDSETMODE)
            events.append((fd, value))
            if fd == 30 and not failed and ((fail_set and value == console.KD_GRAPHICS)
                                            or (fail_restore and value == console.KD_TEXT)):
                failed = True
                raise OSError('injected set/restore failure')
            modes[fd] = value
            return 0

        paths = [pathlib.Path('/dev/' + name) for name in ('vcs1', 'vcs3', 'vcsa3', 'vcs0')]
        with patch.object(console.pathlib.Path, 'glob', return_value=paths), \
                patch.object(console.os, 'open', side_effect=lambda tty, flags: {'/dev/tty1': 10, '/dev/tty3': 30}[tty]), \
                patch.object(console.os, 'close', side_effect=closed.append), patch.object(console.fcntl, 'ioctl', side_effect=ioctl):
            try:
                with console.graphics_consoles() as originals:
                    self.assertEqual(originals, {'/dev/tty1': console.KD_GRAPHICS, '/dev/tty3': console.KD_TEXT})
                    self.assertEqual(modes, {10: console.KD_GRAPHICS, 30: console.KD_GRAPHICS})
                    if fail_body:
                        raise RuntimeError('injected skip failure')
            except (OSError, RuntimeError):
                self.assertTrue(fail_set or fail_body or fail_restore)
            else:
                self.assertFalse(fail_set or fail_body or fail_restore)
        self.assertEqual(set(closed), {10, 30})
        self.assertIn((10, console.KD_GRAPHICS), events)
        self.assertIn((30, console.KD_TEXT), events)
        if not fail_restore:
            self.assertEqual(modes, {10: console.KD_GRAPHICS, 30: console.KD_TEXT})

    def test_normal_exit_restores_every_original_display_mode(self):
        self.exercise()

    def test_exception_in_skip_restores_display_modes(self):
        self.exercise(fail_body=True)

    def test_partial_setup_restores_and_closes_already_opened_consoles(self):
        self.exercise(fail_set=True)

    def test_one_restore_failure_still_closes_and_restores_other_consoles(self):
        self.exercise(fail_restore=True)


class GuestCheckTest(unittest.TestCase):
    def exercise(self, keymap='us', failure=None):
        self.calls, self.loaded, self.invocation = [], keymap, 'a' * 32
        dumps = {name: dump(name) for name in ('de', 'us', 'us-intl')}

        def command(*args):
            self.calls.append(args)
            if args[:2] == ('systemctl', 'show'):
                state = dict(properties(), InvocationID=self.invocation)
                if failure == 'unit' and self.invocation == 'b' * 32:
                    state['Result'] = 'exit-code'
                return result('\n'.join(k + '=' + v for k, v in state.items()))
            if args[:1] == ('journalctl',):
                return result('guest journal')
            if args == ('dumpkeys', '-C', console.CONSOLE, '--keys-only'):
                return result(dumps['de' if self.loaded != 'de' else 'us'] if failure == 'boot' else dumps[self.loaded])
            if args[:1] == ('loadkeys',):
                self.assertEqual(args[1:4], ('-C', console.CONSOLE, '--'))
                self.loaded = args[4]
                return result()
            if args == ('env', 'SYSTEMD_LOG_TARGET=console', console.SETUP):
                return result('no skip' if failure == 'skip' else console.SKIPPED)
            if args == ('systemctl', 'restart', console.UNIT):
                if failure == 'restart':
                    raise AssertionError('injected failed restart')
                self.invocation = 'b' * 32
                if failure != 'keys':
                    self.loaded = keymap
                return result()
            self.fail(f'Unexpected command: {args}')

        with patch.object(console, 'command', side_effect=command), \
                patch.object(console.pathlib.Path, 'read_text', return_value='KEYMAP="' + keymap + '"\n'), \
                patch.object(console, 'graphics_consoles', return_value=nullcontext({'/dev/tty3': console.KD_TEXT})):
            return console.check()

    def test_boot_then_opposite_runtime_map_then_forced_skip_then_real_unit_repair(self):
        for keymap in ('de', 'us', 'us-intl'):
            with self.subTest(keymap=keymap):
                evidence = self.exercise(keymap)
                self.assertEqual(evidence['returncode'], 0)
                self.assertIn('CONSOLE_KEYMAP_PASSED', evidence['stdout'])
                self.assertEqual(evidence['keymap'], self.loaded)
                self.assertNotEqual(evidence['boot']['InvocationID'], evidence['repair']['InvocationID'])
                self.assertNotEqual(evidence['before']['keys'], evidence['trial']['keys'])
                self.assertEqual(evidence['trial']['keys'], evidence['after_skip']['keys'])
                self.assertEqual(evidence['before']['keys'], evidence['after']['keys'])
                mutations = [c for c in self.calls if c[0] == 'loadkeys' or c[1:2] == ('restart',)]
                self.assertEqual(len(mutations), 2)
                self.assertEqual(mutations[-1], ('systemctl', 'restart', console.UNIT))

    def test_bad_boot_keys_fail_before_any_mutation(self):
        with self.assertRaises(AssertionError):
            self.exercise(failure='boot')
        self.assertTrue(all(c[0] != 'loadkeys' and c[1:2] != ('restart',) for c in self.calls))

    def test_missing_skip_failed_restart_failed_unit_or_wrong_repair_keys_fail_and_restore_map(self):
        for failure in ('skip', 'restart', 'unit', 'keys'):
            with self.subTest(failure=failure), self.assertRaises(AssertionError):
                self.exercise(failure=failure)
            self.assertEqual(self.loaded, 'us')
            self.assertEqual(self.calls[-1], ('loadkeys', '-C', console.CONSOLE, '--', 'us'))


class CheckBuildWiringTest(unittest.TestCase):
    def test_guest_action_calls_the_check(self):
        with patch.object(checks.console_keymap, 'check', return_value={'fixture': True}) as check:
            self.assertEqual(checks.check('console-keymap', {}), {'fixture': True})
        check.assert_called_once_with()

    def test_vm_and_check_build_require_the_check_before_the_pass_marker(self):
        source = (ROOT / 'os/ci/vm.py').read_text()
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == 'request'
                 and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'console-keymap']
        self.assertEqual(len(calls), 1)
        self.assertLess(calls[0].lineno, next(i for i, line in enumerate(source.splitlines(), 1) if "keys(['ctrl'" in line))
        build = (ROOT / 'os/ci/check-build.sh').read_text()
        required = 'grep -q CONSOLE_KEYMAP_PASSED evidence/vm-pass-1/console-keymap-result.json'
        self.assertIn(required, build)
        self.assertLess(build.index(required), build.index('echo CHECK_BUILD_VM_PASSED'))

    def test_helper_is_copied_into_only_the_disposable_overlay(self):
        self.assertIn('COPY os/ci/overlay/console_keymap.py /usr/libexec/aresos-ci/',
                      (ROOT / 'os/ci/overlay/Containerfile').read_text())
        self.assertIn('ci/', (ROOT / 'os/.containerignore').read_text().splitlines())
        self.assertNotIn('console_keymap.py', (ROOT / 'os/Containerfile').read_text())


if __name__ == '__main__':
    unittest.main()
