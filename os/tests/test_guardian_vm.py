"""Package 25, the guardian: the unit-level parts of the check build's VM proof (brief 25, Acceptance: the VM).

The VM itself runs only in CI (os/ci/vm.py with the check overlay). Here: the home the guest seeds passes the
supervisor's own checks; the host's reading of a stopped guest's journal accepts the two boots as the brief
describes them and refuses each way the guard's order can be wrong; and the wiring between vm.py, the overlay and
the image is in place. No test here starts a unit, a VM or a game.
"""
import importlib.util
import json
import os
import pathlib
import unittest

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
    def check(self, kind, journal, watched=WATCHED, seconds=None, before_lit=0.6):
        journal.write(self.root)
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
                               ('Java killed', '"EXIT_STATUS": "143"', '"EXIT_STATUS": "137"')):
            with self.subTest(name):
                self.refused('save', self.changed(save_boot(), old, new))
        self.refused('save', save_boot(), watched=dict(WATCHED, black=False))
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
        steps = ["request('guardian-arm', scenario=guardian)", "request('prepare-poweroff')",
                 "monitor.command('system_powerdown')", 'guardian_host.watch(', 'qemu.wait(timeout=',
                 'check_offline_poweroff(', 'guardian_host.check(']
        places = [vm.index(step) for step in steps]
        self.assertEqual(places, sorted(places))
        self.assertEqual(host.scenario('1'), 'save')
        self.assertEqual(host.scenario(2), 'hang')
        with self.assertRaises(KeyError):
            host.scenario('3')  # a third pass would need a scenario of its own


if __name__ == '__main__':
    unittest.main()
