"""Package 25, the guardian: the unit-level parts of the check build's VM proof (brief 25, Acceptance: the VM).

The VM itself runs only in CI (os/ci/vm.py with the check overlay). Here: the home the guest seeds passes the
supervisor's own checks; the host's reading of a stopped guest's journal accepts the two boots as the brief
describes them and refuses each way the guard's order can be wrong; and the wiring between vm.py, the overlay and
the image is in place; and image-checks.sh's rule that no system unit starts the desktop, with the guard as its one
reviewed exception. No test here starts a unit, a VM or a game.
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import test_aresos_desktop as base

desktop = base.desktop
CI = base.CONFIG.parent / 'ci'


def load(path):
    spec = importlib.util.spec_from_file_location('pkg25_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guest = load(CI / 'overlay/guardian.py')
host = load(CI / 'guardian_host.py')
GUARD, GAME = 'aresos-guardian.service', 'aresos-ci-game.service'
ARMED = {'session_scope': 'session-2.scope', 'home_mount': 'var-home.mount', 'scenario': 'x'}


class Journal:
    """A stopped guest's journal as offline_journal.py exports it, built record by record. Seconds count from the
    power key, which comes 100 s after boot."""

    def __init__(self):
        self.rows = []
        self.add(0, MESSAGE='Power key pressed short.')

    def add(self, seconds, **fields):
        self.rows.append({'__MONOTONIC_TIMESTAMP': str(int((100 + seconds) * 1_000_000)), **fields})

    def systemd(self, seconds, unit, message, **fields):
        self.add(seconds, _PID='1', UNIT=unit, MESSAGE=message, **fields)

    def game(self, seconds, marker):
        self.add(seconds, SYSLOG_IDENTIFIER='aresos-ci-game', MESSAGE=f'GUARDIAN_GAME {marker}')

    def tagged(self, seconds, identifier, tag, value):
        self.add(seconds, SYSLOG_IDENTIFIER=identifier, MESSAGE=f'{tag} {json.dumps(value)}')

    def probe(self, seconds, **changes):
        sample = dict(labwc=True, jvm=True, wrapper=True, socket=True, home=True, black_window=True, black=True,
                      lid_block=True, stopping=True, windows=0, tty='tty1', t=100 + seconds,
                      units=dict(guard='deactivating', session='active', greetd='active', user='active',
                                 home_mount='active'))
        sample.update(changes)
        self.tagged(seconds, 'aresos-ci-probe', 'GUARDIAN_PROBE', sample)

    def teardown(self, seconds):
        self.systemd(seconds, 'session-2.scope', 'Stopping session-2.scope - Session 2 of User ares...')
        self.systemd(seconds + 0.1, 'greetd.service', 'Stopping greetd.service - Greeter daemon...')
        self.systemd(seconds + 0.2, 'user@1001.service', 'Stopping user@1001.service - User Manager for UID 1001...')
        self.probe(seconds + 0.5, labwc=False, socket=False, stopping=False, black=False, black_window=False)

    def write(self, folder):
        (folder / 'offline-boot.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in self.rows))


def save_boot():
    journal = Journal()
    journal.systemd(0.2, GUARD, 'Stopping aresos-guardian.service - AresOS guardian...')
    journal.game(0.3, 'save_asked id=1')
    for second in (1, 2, 3, 4, 5):
        journal.probe(second)
    journal.tagged(1.0, 'aresos-ci-probe', 'GUARDIAN_PROBE_PEER', dict(dropped=True, after_requests=128))
    journal.tagged(1.2, 'aresos-ci-lid', 'GUARDIAN_LID', dict(closed=True, t=100.5, logind_lid_closed='b true',
                                                              aresos_lid_blocks=['AresOS … handle-lid-switch block']))
    journal.game(5.3, 'save_answered id=1')
    journal.game(5.35, 'closing')
    journal.systemd(6.0, GAME, 'aresos-ci-game.service: Main process exited, code=exited, status=143/n/a',
                    EXIT_CODE='exited', EXIT_STATUS='143')
    journal.add(6.2, _SYSTEMD_UNIT=GUARD, _PID='900', MESSAGE='Stopped: the home was saved first; Minecraft closed.')
    journal.systemd(6.3, GUARD, 'Stopped aresos-guardian.service - AresOS guardian.', JOB_TYPE='stop', JOB_RESULT='done')
    journal.tagged(6.4, 'aresos-ci-record', 'GUARDIAN_RECORD', dict(
        jvm_alive=False, fallback_record=False, latched=False, reason=None,
        stop=dict(open=False, kind='shutdown', phase='ended', save='saved', why='', sigterm=True, close='exited',
                  status=143)))
    journal.teardown(6.5)
    journal.systemd(8.0, 'var-home.mount', 'Unmounting var-home.mount - /var/home...')
    return journal


def hang_boot():
    journal = Journal()
    journal.systemd(0.2, GUARD, 'Stopping aresos-guardian.service - AresOS guardian...')
    journal.game(0.3, 'save_asked id=1')
    for second in range(1, 60):
        journal.probe(second, tty='tty3' if second > 4 else 'tty1')
    journal.game(30.3, 'sigterm_ignored')
    journal.add(60.2, _SYSTEMD_UNIT=GUARD, _PID='900', MESSAGE=(
        'Not a confirmed stop: the home could not be confirmed as saved first; Minecraft did not close within 60 '
        'seconds, so AresOS stopped waiting (it never ends Minecraft by force). Not saved: Minecraft did not answer in '
        'time.'))
    journal.systemd(60.3, GUARD, 'Stopped aresos-guardian.service - AresOS guardian.', JOB_TYPE='stop', JOB_RESULT='done')
    journal.tagged(60.4, 'aresos-ci-record', 'GUARDIAN_RECORD', dict(
        jvm_alive=True, fallback_record=False, latched=False, reason=None,
        stop=dict(open=True, kind='shutdown', phase='close', save='timeout', why='Not saved: …', sigterm=True,
                  close='overrun', status=None)))
    journal.teardown(60.5)
    journal.systemd(75.9, GAME, 'aresos-ci-game.service: Main process exited, code=exited, status=137/n/a',
                    EXIT_CODE='exited', EXIT_STATUS='137')
    return journal


WATCHED = dict(black=True, black_lit_shares=[0.4, 0.0], save_asked_after=0.4, black_after=1.1)


class HostCheckTest(base.Base):
    def check(self, kind, journal, watched=WATCHED, seconds=None, before_lit=0.6, cues=None):
        journal.write(self.root)
        if cues is None:
            cues = {'save': b'ready\nsaving\nanswering\n', 'hang': b'ready\nsaving\n'}[kind]
        (self.root / 'guardian-camera.log').write_bytes(cues)
        return host.check(self.root, kind, ARMED, watched, {'save': 12.0, 'hang': 82.0}[kind] if seconds is None
                          else seconds, before_lit)

    def changed(self, journal, old, new):
        """The journal with one piece of text replaced, in a record's own field or inside a watcher's line."""
        text = json.dumps(journal.rows)
        inside = (json.dumps(old)[1:-1], json.dumps(new)[1:-1])
        self.assertTrue(old in text or inside[0] in text, old)
        journal.rows = json.loads(text.replace(inside[0], inside[1]).replace(old, new))
        return journal

    def refused(self, kind, journal, **arguments):
        with self.assertRaises(AssertionError):
            self.check(kind, journal, **arguments)

    def test_fixture_cues_the_frame_when_the_serial_follower_goes_silent(self):
        (self.root / 'serial.log').write_text('ARESOS_POWER_KEY_ARMED\nStopped session-1.scope\n')
        camera = self.root / 'guardian-camera.log'
        camera.write_bytes(b'ready\n')
        screenshot = mock.Mock()
        with mock.patch.object(host.time, 'sleep', side_effect=lambda _: camera.write_bytes(b'ready\nsaving\n')), \
                mock.patch.object(host, 'lit_share', return_value=0):
            result = host.watch('save', camera, lambda: True, screenshot, self.fail, self.root)
        screenshot.assert_called_once_with('guardian-black.png')
        self.assertTrue(result['black'], result)
        self.check('save', save_boot(), watched=result)

    def test_missing_marker_preserves_the_guest_evidence_and_fails_the_boot(self):
        camera = self.root / 'guardian-camera.log'
        camera.write_bytes(b'ready\n')
        result = host.watch('save', camera, lambda: False, self.fail, self.fail, self.root)
        self.assertFalse(result['black'])
        self.assertIn('saving marker', result['error'])
        self.assertEqual(json.loads((self.root / 'guardian-watch.json').read_text()), result)
        self.refused('save', save_boot(), watched=result, cues=camera.read_bytes())
        self.assertEqual(json.loads((self.root / 'guardian.json').read_text())['record']['stop']['save'], 'saved')

    def test_a_frame_captured_as_the_fixture_answers_is_too_late(self):
        camera = self.root / 'guardian-camera.log'
        camera.write_bytes(b'ready\nsaving\n')

        def answer(_):
            with camera.open('ab') as stream:
                stream.write(b'answering\n')

        result = host.watch('save', camera, lambda: True, answer, self.fail, self.root)
        self.assertFalse(result['black'])
        self.assertIn('save window ended', result['error'])

    def test_boot_1_the_power_key_with_a_save_that_takes_five_seconds(self):
        summary = self.check('save', save_boot())
        self.assertEqual((summary['guard_stop_began'], summary['save_asked'], summary['save_answered'],
                          summary['java_exited'], summary['guard_stop_ended']), (0.2, 0.3, 5.3, 6.0, 6.3))
        self.assertEqual(summary['began_to_stop'], {'session-2.scope': 6.5, 'greetd.service': 6.6,
                                                    'user@1001.service': 6.7, 'var-home.mount': 8.0})
        self.assertEqual((summary['java_status'], summary['labwc_gone'], summary['peer_dropped']), ('143', 7.0, True))
        self.assertEqual(json.loads((self.root / 'guardian.json').read_text())['record']['stop']['save'], 'saved')
        # A home's mount that is never unmounted while the journal is written (the root's) is no stop before the guard.
        journal = save_boot()
        journal.rows = [row for row in journal.rows if row.get('UNIT') != 'var-home.mount']
        self.assertIsNone(self.check('save', journal)['began_to_stop']['var-home.mount'])

    def test_boot_1_is_refused_when_the_order_or_the_record_is_wrong(self):
        for name, change in (
                ('the session began to stop during the save', lambda j: j.systemd(
                    3.0, 'session-2.scope', 'Stopping session-2.scope - Session 2 of User ares...')),
                ('greetd began to stop during the save', lambda j: j.systemd(3.0, 'greetd.service', 'Stopping greetd.service...')),
                ('the user manager began to stop during the save', lambda j: j.systemd(
                    3.0, 'user@1001.service', 'Stopping user@1001.service...')),
                ('the home was unmounted during the save', lambda j: j.systemd(3.0, 'var-home.mount', 'Unmounting var-home.mount...')),
                ('labwc was gone during the save', lambda j: j.probe(3.5, labwc=False)),
                ('the home was not writable', lambda j: j.probe(3.5, home=False)),
                ('the socket was gone', lambda j: j.probe(3.5, socket=False, stopping=False)),
                ('the wrapper was gone', lambda j: j.probe(3.5, wrapper=False)),
                ('an ordering cycle', lambda j: j.add(-50, MESSAGE='graphical.target: Found ordering cycle on greetd.service')),
                ('the machine went to sleep', lambda j: j.add(3.0, MESSAGE='Suspending system...')),
        ):
            with self.subTest(name):
                journal = save_boot()
                change(journal)
                self.refused('save', journal)
        for name, edit in (
                ('the save was not answered', lambda r: r.get('MESSAGE', '').startswith('GUARDIAN_GAME save_answered')),
                ('the game was never asked', lambda r: r.get('MESSAGE', '').startswith('GUARDIAN_GAME save_asked')),
                ('the peer was not dropped', lambda r: r.get('MESSAGE', '').startswith('GUARDIAN_PROBE_PEER')),
                ('no lid event', lambda r: r.get('MESSAGE', '').startswith('GUARDIAN_LID')),
                ('the record was not read', lambda r: r.get('MESSAGE', '').startswith('GUARDIAN_RECORD')),
                ('the guard never stopped', lambda r: r.get('UNIT') == GUARD),
                ('no black window', lambda r: r.get('MESSAGE', '').startswith('GUARDIAN_PROBE {')),
        ):
            with self.subTest(name):
                journal = save_boot()
                journal.rows = [row for row in journal.rows if not edit(row)]
                self.refused('save', journal)
        for name, old, new in (('unsaved', '"save": "saved"', '"save": "timeout"'),
                               ('not exited', '"close": "exited"', '"close": "failed"'),
                               ('latched', '"latched": false', '"latched": true'),
                               ('Java still there', '"jvm_alive": false', '"jvm_alive": true'),
                               ('a save that took no time', 'GUARDIAN_GAME save_answered', 'GUARDIAN_GAME nothing'),
                               ('another request answered', 'GUARDIAN_GAME save_answered id=1', 'GUARDIAN_GAME save_answered id=2'),
                               ('Java killed', '"EXIT_STATUS": "143"', '"EXIT_STATUS": "137"')):
            with self.subTest(name):
                self.refused('save', self.changed(save_boot(), old, new))
        self.refused('save', save_boot(), watched=dict(WATCHED, black=False))
        self.refused('save', save_boot(), cues=b'ready\nsaving\n')
        self.refused('save', save_boot(), before_lit=0.0)  # a frame that was black before proves nothing
        self.refused('save', save_boot(), seconds=121.0)

    def test_boot_2_a_game_that_never_answers_and_ignores_sigterm(self):
        summary = self.check('hang', hang_boot())
        self.assertEqual((summary['guard_stop_seconds'], summary['sigterm_ignored'], summary['java_status'],
                          summary['game_killed_after_user_stop'], summary['console_switched']),
                         (60.1, 30.3, '137', 15.2, True))
        self.assertEqual((summary['record']['stop']['save'], summary['record']['stop']['close']), ('timeout', 'overrun'))
        self.assertEqual(host.POWER_OFF_BOUND, 85 + 15 + 20)

    def test_boot_2_is_refused_when_the_game_was_killed_early_or_the_record_says_saved(self):
        for name, old, new in (('recorded as saved', '"save": "timeout"', '"save": "saved"'),
                               ('recorded as exited', '"close": "overrun"', '"close": "exited"'),
                               ('Java gone at the guard\'s end', '"jvm_alive": true', '"jvm_alive": false'),
                               ('no console switch', '"tty": "tty3"', '"tty": "tty1"'),
                               ('it answered', 'GUARDIAN_GAME sigterm_ignored', 'GUARDIAN_GAME save_answered id=1')):
            with self.subTest(name):
                self.refused('hang', self.changed(hang_boot(), old, new))
        early = hang_boot()
        early.rows = [row for row in early.rows if row.get('UNIT') != GAME]
        early.systemd(40.0, GAME, 'aresos-ci-game.service: Main process exited', EXIT_STATUS='137')
        self.refused('hang', early)  # something ended the game before the guard's stop did
        short = hang_boot()
        for row in short.rows:
            if row.get('UNIT') == GUARD and row.get('JOB_TYPE') == 'stop':
                row['__MONOTONIC_TIMESTAMP'] = str(int(140.3 * 1_000_000))
        self.refused('hang', short)
        self.refused('hang', hang_boot(), seconds=121.0)
        missing = self.root / 'offline-boot.jsonl'
        missing.unlink()
        with self.assertRaises(AssertionError):
            host.check(self.root, 'hang', ARMED, WATCHED, 82.0, 0.6)  # no offline journal, no proof


class GuestTest(base.Base):
    def test_the_seeded_home_passes_the_supervisors_own_checks(self):
        self.assertEqual(desktop.check_world(self.paths, self.lock)[0], 'missing')
        world = guest.seed_world(self.paths.worlds, self.lock['world'])
        self.assertEqual(desktop.check_world(self.paths, self.lock), ('ok', str(world)))
        self.assertEqual(world.name, 'AresHub')  # the stand-in game answers for this name
        self.assertIn('"world":{"id":"AresHub","desktop":true}', (CI / 'overlay/GuardianGame.java').read_text()
                      .replace('\\"', '"'))

    def test_the_guest_and_the_supervisor_agree(self):
        self.assertEqual((guest.GUARD, guest.DESKTOP), (desktop.GUARD_UNIT, desktop.SELF))
        self.assertEqual(guest.SOCKET, desktop.Paths(guest.HOME, guest.RUNTIME).socket)
        self.assertEqual(guest.STATE, desktop.Paths(guest.HOME, guest.RUNTIME).state_dir)
        self.assertEqual(guest.WORLDS, desktop.Paths(guest.HOME, guest.RUNTIME).worlds)
        self.assertEqual(os.path.join(guest.STATE, 'desktop-guard.json'), desktop.Paths(guest.HOME, guest.RUNTIME).guard_file)
        checks = (CI / 'overlay/checks.py').read_text()
        self.assertIn(f'RECOVERY_TERMINAL = {guest.RECOVERY_TERMINAL!r}', checks)
        self.assertEqual(tuple(host.SCENARIOS.values()), guest.SCENARIOS)
        # The evidence's allowlist: never the launch's id, its nonce or its instance.
        self.assertEqual(guest.RECORD_FIELDS, ('open', 'kind', 'phase', 'save', 'why', 'sigterm', 'close', 'status'))
        source = (CI / 'overlay/guardian.py').read_text()
        for word in ('nonce', 'environ', 'ARESOS_DESKTOP_INSTANCE', 'desktop-runtime'):
            self.assertNotIn(word, source.split('"""', 2)[2], word)

    def test_the_wiring(self):
        container = (CI / 'overlay/Containerfile').read_text()
        self.assertIn('COPY os/ci/overlay/guardian.py os/ci/overlay/GuardianGame.java /usr/libexec/aresos-ci/', container)
        self.assertIn("if action == 'guardian-arm':\n", (CI / 'overlay/checks.py').read_text())
        vm = (CI / 'vm.py').read_text()
        self.assertIn(f'virtserialport,chardev=camera,name={guest.CAMERA_PORT.name}', vm)
        steps = ["request('guardian-arm', scenario=guardian)", "request('prepare-poweroff')",
                 "monitor.command('system_powerdown')", 'guardian_host.watch(', 'qemu.wait(timeout=',
                 'check_offline_poweroff(', 'guardian_host.check(']
        places = [vm.index(step) for step in steps]
        self.assertEqual(places, sorted(places))
        self.assertEqual(host.scenario('1'), 'save')
        self.assertEqual(host.scenario(2), 'hang')
        with self.assertRaises(KeyError):
            host.scenario('3')  # a third pass would need a scenario of its own

    def test_the_check_build_requires_both_guardian_boots(self):
        build = (CI / 'check-build.sh').read_text()
        steps = [f'ARESOS_VM_PASS={number} python3 os/ci/vm.py' for number in host.SCENARIOS]
        places = [build.index(step) for step in [*steps, 'echo CHECK_BUILD_VM_PASSED']]
        self.assertEqual(places, sorted(places))


class SystemUnitRuleTest(unittest.TestCase):
    """image-checks.sh's SYSTEM_UNITS rule, run as the image runs it, on unit trees made here (step 8: the check build
    44533435611 stopped on the old rule, a grep for the desktop's name anywhere in a unit, which the guard's own
    ExecStop and Documentation= lines matched)."""
    UNIT = base.CONFIG / 'usr/lib/systemd/system' / GUARD
    DROP_IN = base.CONFIG / 'usr/lib/systemd/system/session-.scope.d/50-aresos-guardian.conf'

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        self.lib, self.etc = self.root / 'usr/lib/systemd/system', self.root / 'etc/systemd/system'
        source = (CI / 'image-checks.sh').read_text()
        head = "python3 -I - /usr/lib/systemd/system /etc/systemd/system <<'SYSTEM_UNITS'\n"
        self.assertEqual(source.count(head), 1)
        self.rule = source.split(head, 1)[1].split('\nSYSTEM_UNITS\n', 1)[0]
        # The image's tree as it is: the guard, its link, the session scopes' drop-in, a drop-in for every service
        # without an Exec line, a mask, a dangling link, and units that mention the desktop without running it.
        self.write('usr/lib/systemd/system/' + GUARD, self.UNIT.read_text())
        self.write('usr/lib/systemd/system/session-.scope.d/50-aresos-guardian.conf', self.DROP_IN.read_text())
        self.write('usr/lib/systemd/system/service.d/10-timeout-abort.conf',
                   '[Service]\nTimeoutStopFailureMode=abort\n')
        self.link('etc/systemd/system/graphical.target.wants/' + GUARD, self.lib / GUARD)
        self.link('etc/systemd/system/masked.service', '/dev/null')
        self.link('etc/systemd/system/multi-user.target.wants/gone.service', self.lib / 'gone.service')
        self.write('usr/lib/systemd/system/greetd.service',
                   '# Logs in ares, whose labwc session starts aresos-desktop.\n[Unit]\n'
                   'Documentation=file:/usr/libexec/aresos-desktop man:prismlauncher(6)\n'
                   '[Service]\nExecStart=/usr/bin/greetd\n; ExecStartPre=/usr/libexec/aresos-desktop\n')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def link(self, name, target):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)

    def check(self):
        return subprocess.run([sys.executable, '-I', '-', str(self.lib), str(self.etc)], input=self.rule,
                              capture_output=True, text=True, timeout=30)

    def assert_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SYSTEM_UNITS_OK', result.stdout)

    def assert_fails(self, *words):
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('SYSTEM_UNITS_FAILED', result.stderr)
        for word in words:
            self.assertIn(word, result.stdout + result.stderr)
        return result

    def test_the_images_tree_with_the_reviewed_guard_passes(self):
        self.assert_passes()

    def test_a_changed_guard_fails(self):
        unit = self.UNIT.read_text()
        stop = 'ExecStop=/usr/libexec/aresos-desktop stop --reason shutdown\n'
        changed = {
            'another stop': unit.replace(stop, 'ExecStop=/usr/libexec/aresos-desktop stop\n'),
            'a start of the desktop': unit.replace('ExecStart=/usr/bin/true\n', 'ExecStart=/usr/libexec/aresos-desktop\n'),
            'another start': unit.replace('ExecStart=/usr/bin/true\n', 'ExecStart=/usr/bin/sleep 1\n'),
            'one more line that runs': unit.replace(stop, stop + 'ExecStopPost=/usr/bin/true\n'),
            'one before the start': unit.replace('[Service]\n', '[Service]\nExecStartPre=-/usr/bin/true\n'),
            'the stop twice': unit.replace(stop, stop + stop),
            'no stop': unit.replace(stop, ''),
            'a continued line': unit.replace('ExecStart=/usr/bin/true\n',
                                             'ExecStart=/usr/bin/true \\\n# a comment\n  /usr/bin/prismlauncher\n'),
        }
        for what, text in changed.items():
            with self.subTest(what):
                self.assertNotEqual(text, unit)
                self.write('usr/lib/systemd/system/' + GUARD, text)
                self.assert_fails('A system unit starts the desktop or Prism', 'the shutdown guard runs exactly')

    def test_the_guard_only_by_its_exact_path(self):
        self.write('etc/systemd/system/' + GUARD, self.UNIT.read_text())  # a copy that would override it
        self.assert_fails(str(self.etc / GUARD) + ': ExecStop=/usr/libexec/aresos-desktop stop --reason shutdown')

    def test_the_guard_as_a_link_fails(self):
        (self.lib / GUARD).rename(self.root / 'elsewhere.service')
        self.link('usr/lib/systemd/system/' + GUARD, self.root / 'elsewhere.service')
        self.assert_fails('must be a file of its own')

    def test_a_drop_in_that_adds_to_what_the_guard_runs_fails(self):
        for folder in (f'etc/systemd/system/{GUARD}.d', f'usr/lib/systemd/system/{GUARD}.d',
                       'etc/systemd/system/aresos-.service.d', 'etc/systemd/system/service.d'):
            with self.subTest(folder):
                path = self.write(folder + '/50-more.conf', '[Service]\nExecStopPost=/usr/bin/true\n')
                self.assert_fails('a drop-in adds what the shutdown guard runs', str(path))
                path.unlink()
        self.write(f'etc/systemd/system/{GUARD}.d/50-quiet.conf', '[Service]\nTimeoutStopSec=85\n')
        self.assert_passes()

    def test_a_unit_that_starts_the_desktop_or_prism_fails(self):
        units = {
            'usr/lib/systemd/system/aresos-desktop.service': '[Service]\nExecStart=/usr/libexec/aresos-desktop\n',
            'etc/systemd/system/prism.service': '[Service]\nExecStart = /usr/bin/prismlauncher\n',
            'etc/systemd/system/wrapper.service': '[Service]\nExecStartPre=-/usr/libexec/aresos-desktop-java x\n',
            'etc/systemd/system/getty@.service.d/50-x.conf': '[Service]\nExecStartPost=/usr/libexec/aresos-desktop\n',
            'etc/systemd/system/continued.service': '[Service]\nExecStart=/usr/bin/env \\\n; skipped\n'
                                                    '  /usr/libexec/aresos-desktop\n',
        }
        for name, text in units.items():
            with self.subTest(name):
                path = self.write(name, text)
                self.assert_fails('A system unit starts the desktop or Prism', str(path) + ': Exec')
                path.unlink()
        self.assert_passes()


if __name__ == '__main__':
    unittest.main()
