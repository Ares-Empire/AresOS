"""Package 30, review fixes 2: SECURITY-2.md findings 1 and 2, REVIEW-2.md findings 1 to 4.

Everything is synthetic: no real program, window or compositor. Time moves through the tests' own clock; a stalled
mount is a stand-in check that never answers until the test ends.
"""
import dataclasses
import os
import pathlib
import resource
import subprocess
import sys
import threading
import time
from unittest import mock

from test_aresos_shell import shell, Base, Conn, HELPER, REGISTRY, INSTANCE, NONCE, ALL
from test_aresos_shell_hardening import HardeningBase, svg
from test_aresos_shell_icons import IconBase, SVG, NORMAL


def icons_stub():
    icons = mock.Mock()
    icons.take.side_effect = lambda apps, revision: (apps, shell.icons_revision(apps, revision))
    return icons


class StalledMountTest(HardeningBase, Base):
    """Security fix 1: a program on a mount that stopped answering never stops the helper answering."""

    DEAD = '/mnt/dead/'

    def setUp(self):
        HardeningBase.setUp(self)
        Base.setUp(self)
        self.loop = threading.current_thread()
        # Set when the test ends: the mount answers again, so no check thread outlives the test for long.
        self.mount_back = threading.Event()
        self.addCleanup(self.mount_back.set)

    def stalled(self, path):
        """Anything under /mnt/dead never answers while the mount is down. On the serving loop that would stop the
        helper for good, so there it fails the test at once instead of hanging it."""
        if not str(path).startswith(self.DEAD):
            return False
        if threading.current_thread() is self.loop:
            raise AssertionError(f'the serving loop touched {path}')
        self.mount_back.wait()
        return True

    def executable(self, path):
        self.stalled(path)
        return True

    def start(self):
        # The worker found every program while the mount still answered.
        discovery = shell.Discovery(shell.Catalogue(str(REGISTRY), entry_dirs=self.folders, executable=lambda p: True,
                                                    deployments=()))
        self.addCleanup(discovery.stop)
        discovery.start(self.clock())
        helper = shell.Helper(str(REGISTRY), INSTANCE, NONCE, self.journal, registry=(discovery.apps,
                              discovery.revision), catalogue=discovery, icons=icons_stub(), clock=self.clock,
                              executable=self.executable, launcher=self.launcher())
        self.addCleanup(helper.watcher.stop)
        conn = Conn()
        helper.connected(conn)
        self.assertTrue(self.request(helper, conn, 'hello', 'h-1', major=1, minor=1, capabilities=ALL,
                                     instance=INSTANCE, nonce=NONCE)['ok'])
        return helper, conn

    @staticmethod
    def answers(conn, *request_ids):
        return {message['id']: message for message in conn.sent if message.get('id') in request_ids}

    def wait_for_checks(self, helper):
        deadline = time.monotonic() + 5
        while helper.checks.running and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(helper.checks.running, {})

    def test_listing_heartbeats_and_other_launches_go_on_while_a_launch_check_never_returns(self):
        self.write(self.folders[0] / 'stalled.desktop', Name='Stalled', Exec=self.DEAD + 'tool')
        self.write(self.folders[0] / 'other.desktop', Name='Other', Exec='/usr/bin/other')
        # Its program answers, but its working folder is on the dead mount: Popen would wait for chdir there.
        self.write(self.folders[0] / 'folder.desktop', Name='Folder', Exec='/usr/bin/other', Path=self.DEAD + 'work')
        helper, conn = self.start()
        original_stat, original_resolve, resolved_on = os.stat, shell.resolve, []

        def stat(path, *args, **kwargs):
            self.stalled(path)
            return original_stat(path, *args, **kwargs)

        def resolve(*args, **kwargs):
            resolved_on.append(threading.current_thread())
            return original_resolve(*args, **kwargs)

        with mock.patch.object(shell.os, 'stat', stat), mock.patch.object(shell, 'resolve', side_effect=resolve):
            start = time.monotonic()
            self.request(helper, conn, 'open_app', 'o-1', app_id='stalled')
            self.request(helper, conn, 'open_app', 'o-2', app_id='folder')
            self.assertEqual(self.answers(conn, 'o-1', 'o-2'), {})  # answered once their checks answer
            listing = self.request(helper, conn, 'list_apps', 'l-1')
            rows = {row['id']: row for row in listing['apps']}
            # The catalogue's published value: the program was there when the worker looked.
            self.assertEqual((rows['stalled']['available'], rows['stalled']['reason']), (True, None))
            self.assertTrue(rows['terminal']['available'])
            self.assertTrue(self.request(helper, conn, 'heartbeat', 'b-1', ready=True, instance=INSTANCE,
                                         nonce=NONCE)['ok'])
            other = self.request(helper, conn, 'open_app', 'o-3', app_id='other')
            self.assertEqual((other['id'], other['ok'], other['state']), ('o-3', True, 'starting'))
            self.request(helper, conn, 'open_app', 'o-4', app_id='stalled')  # a second click shares the check
            self.assertEqual(self.answers(conn, 'o-4'), {})
            helper.tick()
            self.assertLess(time.monotonic() - start, 3 * shell.CHECK_WAIT + 1.0)
            self.assertNotIn(self.loop, resolved_on)
            self.assertEqual(len(helper.checks.running), 2)  # stalled (shared) and folder
            # The checks are overdue: those launches fail as unavailable, nothing else changes.
            self.now[0] += shell.CHECK_SECONDS
            helper.tick()
            self.assertTrue(self.request(helper, conn, 'heartbeat', 'b-2', ready=True, instance=INSTANCE,
                                         nonce=NONCE)['ok'])
        answers = self.answers(conn, 'o-1', 'o-2', 'o-4')
        self.assertEqual(sorted(answers), ['o-1', 'o-2', 'o-4'])
        for request_id, answer in answers.items():
            with self.subTest(request_id):
                self.assertEqual((answer['ok'], answer['state'], answer['error'], answer['reason'], answer['launch_id']),
                                 (False, 'failed', 'unavailable', 'not_responding', None))
                self.assertEqual(helper.journal.entries[request_id]['reason'], 'not_responding')
        self.assertEqual(self.popen.call_count, 1)  # only Other started
        # A resent request ID replays its answer; it never starts a second check or a launch.
        replay = self.request(helper, conn, 'open_app', 'o-1', app_id='stalled')
        self.assertEqual(replay['reason'], 'not_responding')
        # The mount comes back: its check threads end, and the program opens again.
        self.mount_back.set()
        self.wait_for_checks(helper)
        self.assertEqual(self.request(helper, conn, 'open_app', 'o-5', app_id='stalled')['state'], 'starting')

    def test_at_most_a_few_checks_wait_at_once_and_the_helper_still_answers(self):
        names = [f'stalled{n}' for n in range(shell.MAX_CHECKS + 1)]
        for name in names:
            self.write(self.folders[0] / f'{name}.desktop', Name=name, Exec=self.DEAD + name)
        self.write(self.folders[0] / 'other.desktop', Name='Other', Exec='/usr/bin/other')
        helper, conn = self.start()
        for n, name in enumerate(names[:shell.MAX_CHECKS]):
            self.request(helper, conn, 'open_app', f'o-{n}', app_id=name)
        self.assertEqual(len(helper.checks.running), shell.MAX_CHECKS)
        self.assertEqual(len(helper.checking), shell.MAX_CHECKS)
        # No further thread: the next launches fail at once, whatever they open, and say why.
        for request_id, name in (('o-busy', names[-1]), ('o-other', 'other')):
            start = time.monotonic()
            answer = self.request(helper, conn, 'open_app', request_id, app_id=name)
            self.assertLess(time.monotonic() - start, shell.CHECK_WAIT)
            self.assertEqual((answer['id'], answer['ok'], answer['error'], answer['reason']),
                             (request_id, False, 'unavailable', 'checks_busy'))
        self.assertEqual(len([t for t in threading.enumerate() if t.name == 'aresos-launch-check']),
                         shell.MAX_CHECKS)
        self.assertTrue(self.request(helper, conn, 'list_apps', 'l-1')['ok'])
        self.assertTrue(self.request(helper, conn, 'heartbeat', 'b-1', ready=True, instance=INSTANCE,
                                     nonce=NONCE)['ok'])
        self.popen.assert_not_called()
        # Once the mount answers, the waiting launches go on and new ones are checked again.
        self.mount_back.set()
        self.wait_for_checks(helper)
        helper.tick()
        self.assertEqual([self.answers(conn, f'o-{n}')[f'o-{n}']['state'] for n in range(shell.MAX_CHECKS)],
                         ['starting'] * shell.MAX_CHECKS)
        self.assertEqual(self.request(helper, conn, 'open_app', 'o-again', app_id='other')['state'], 'starting')


class ScanDeadlineTest(HardeningBase):
    """Security fix 1: the scan's deadline holds while entries are parsed and right before a catalogue is published."""

    def test_a_scan_out_of_time_while_parsing_or_before_publishing_changes_nothing(self):
        self.write(self.folders[0] / 'good.desktop')
        catalogue = self.catalogue()
        self.assertTrue(catalogue.scan())
        good = (catalogue.apps, catalogue.revision, catalogue.legacy)
        for n in range(10):
            self.write(self.folders[1] / f'more{n}.desktop', Name=f'More {n}')

        calls = {}

        def slow(name, before=0.0, after=0.0):
            original = getattr(shell, name)

            def call(*args, **kwargs):
                calls[name] = calls.get(name, 0) + 1
                time.sleep(before)
                result = original(*args, **kwargs)
                time.sleep(after)
                return result
            return mock.patch.object(shell, name, call)

        # Each case also says where the work stopped: a scan out of time stops, it does not finish and then refuse.
        cases = {
            'while parsing entries': ([slow('discovered_app', before=0.03)], lambda: calls['discovered_app'] < 10),
            'after parsing': ([slow('load_hints', before=0.2), slow('resolve')], lambda: 'resolve' not in calls),
            'right before publishing': ([slow('load_legacy', after=0.2)], lambda: calls['load_legacy'] == 1),
        }
        with mock.patch.object(shell, 'SCAN_SECONDS', 0.1):
            for name, (patches, stopped) in cases.items():
                calls.clear()
                with self.subTest(name):
                    for patch in patches:
                        patch.start()
                    try:
                        self.assertFalse(catalogue.scan())
                    finally:
                        for patch in patches:
                            patch.stop()
                    self.assertTrue(catalogue.limited)
                    self.assertEqual((catalogue.apps, catalogue.revision, catalogue.legacy), good)
                    self.assertTrue(stopped(), calls)
        # In time again, the same scan publishes the new programs.
        self.assertTrue(catalogue.scan())
        self.assertEqual(len(catalogue.apps), 11)


def name_bomb():
    """The security review's case: a 256 KiB namespace address and 50,000 differently named elements in it. Parsed
    with namespaces, every name grows by the address, and Python keeps each one: about 12 GiB."""
    address = 'urn:' + 'x' * (256 * 1024)
    names = ''.join(f'<p:n{n}/>' for n in range(50000))
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:p="{address}" width="8" height="8">{names}</svg>'.encode()


def address_space():
    with open('/proc/self/status') as status:
        return int(next(line for line in status if line.startswith('VmSize')).split()[1]) * 1024


class SvgPreCheckTest(IconBase):
    """Security fix 2: the SVG pre-check runs in a process of its own under the converter's ceiling, and is bounded."""

    def test_the_reviews_name_bomb_is_refused_the_helper_does_not_grow_and_the_program_keeps_its_fallback(self):
        raw = name_bomb()
        self.assertLess(len(raw), shell.MAX_ICON_BYTES)
        source = self.write(self.root / 'names.svg', raw)
        # Should the pre-check ever run in this process again, it stops at 1 GiB more, not at the laptop's memory.
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        ceiling = address_space() + 1024 ** 3
        resource.setrlimit(resource.RLIMIT_AS, (ceiling if hard == resource.RLIM_INFINITY else min(ceiling, hard),
                                                hard))
        self.addCleanup(resource.setrlimit, resource.RLIMIT_AS, (soft, hard))
        before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        app = shell.App('names', 'Names', icon_name=str(source))
        self.cache.request({app.id: app}, 'r-1')
        revision, app_id, icon_name, path = self.cache.results.get(timeout=30)
        self.assertEqual((revision, app_id, icon_name, path), ('r-1', 'names', str(source), None))
        apps, _ = self.cache.take({app.id: app}, 'r-1')
        self.assertIsNone(apps['names'].icon)  # no picture: the program keeps its fallback look
        self.cache.failed.clear()
        with self.assertRaisesRegex(ValueError, 'namespace'):
            self.cache.convert(str(source))
        grown = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before  # KiB
        self.assertLess(grown, 32 * 1024)
        self.assertEqual(list(pathlib.Path(self.cache.directory).glob('*.png')), [])

    def test_the_pre_check_never_runs_in_the_helper_but_in_its_own_process_under_the_ceiling(self):
        drawn = self.write(self.root / 'drawn.svg', SVG)
        refused = self.write(self.root / 'refused.svg', svg('<image href="file:///etc/hostname"/>'))
        self.cache.svg_checked = True
        with mock.patch.object(shell, 'drawn_svg', side_effect=AssertionError('the helper ran the pre-check')), \
                mock.patch.object(shell.subprocess, 'Popen', wraps=subprocess.Popen) as popen, \
                mock.patch.object(self.cache, 'run', return_value=NORMAL) as run:
            self.assertIsNotNone(self.cache.convert(str(drawn)))
            with self.assertRaisesRegex(ValueError, 'refused: SVG contains <image>'):
                self.cache.convert(str(refused))
        self.assertEqual(run.call_count, 1)  # only the drawn one was converted
        for call in popen.call_args_list:
            command = call.args[0]
            self.assertEqual(command[:3], [self.cache.prlimit, f'--as={shell.ICON_ADDRESS_SPACE}', '--'])
            self.assertEqual(command[3:8], [sys.executable, '-I', '-S', str(HELPER), '--check-svg'])
            # It reads the work folder's private copy, which is gone again afterwards.
            self.assertEqual(pathlib.Path(command[8]).parent.parent, pathlib.Path(self.cache.directory))
            self.assertFalse(pathlib.Path(command[8]).exists())
        self.assertEqual(popen.call_count, 2)

    def test_the_pre_check_looks_at_bounded_names_namespaces_counts_and_nesting(self):
        def elements(count, attributes=0):
            attribute = ' '.join(f'a{n}="1"' for n in range(attributes))
            return ''.join(f'<g {attribute}/>' for _ in range(count))

        refused = {
            'namespace address': svg('<p:g/>', f' xmlns:p="urn:{"x" * shell.SVG_NAMESPACE}"'),
            'default namespace address': svg(f'<g xmlns="urn:{"x" * shell.SVG_NAMESPACE}"/>'),
            'namespace prefix': svg('', f' xmlns:{"p" * (shell.SVG_NAME + 1)}="urn:x"'),
            'element name': svg(f'<{"g" * (shell.SVG_NAME + 1)}/>'),
            'attribute name': svg(f'<g {"a" * (shell.SVG_NAME + 1)}="1"/>'),
            'elements': svg(elements(shell.SVG_ELEMENTS)),  # with the root, one too many
            'attributes': svg(elements(shell.SVG_ATTRIBUTES // 1000 + 1, 1000)),
            'nesting': svg('<g>' * shell.SVG_DEPTH + '</g>' * shell.SVG_DEPTH),
        }
        for name, raw in refused.items():
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, 'over'):
                    shell.drawn_svg(raw)
        # At the bounds themselves, a drawing still passes.
        shell.drawn_svg(svg(elements(shell.SVG_ELEMENTS - 1)))
        shell.drawn_svg(svg('<g>' * (shell.SVG_DEPTH - 1) + '</g>' * (shell.SVG_DEPTH - 1)))
        shell.drawn_svg(svg(f'<{"g" * shell.SVG_NAME}/>', f' xmlns:p="urn:{"x" * (shell.SVG_NAMESPACE - 4)}"'))


from test_aresos_shell_review_fixes import OwnershipBase  # noqa: E402  (after the classes above)


class WindowsBase(OwnershipBase):
    """The terminal and the editor open behind Lunar Client, which has the focus (as in review fixes 1)."""

    def setUp(self):
        super().setUp()
        self.window(3, 'aresos.terminal')
        self.window(4, 'org.kde.kwrite')
        self.open('lunarclient', 'o-l')
        self.window(2, 'lunarclient', active=True)
        self.later(10)
        self.before = len(self.conn.events('shell_focus'))

    def hello(self, minor, request_id='h-2'):
        conn = Conn()
        self.helper_.connected(conn)
        reply = self.request(self.helper_, conn, 'hello', request_id, major=1, minor=minor, capabilities=ALL,
                             instance=INSTANCE, nonce=NONCE)
        self.assertEqual(reply['minor'], minor)
        self.conn = conn
        return conn

    def settle(self):
        for _ in range(4):
            self.later(shell.HANDOFF)


class LegacyReconnectTest(WindowsBase):
    """Package review fix 1 (REVIEW-2 finding 1): a 1.0 desktop taking over drops a discovered program's return."""

    def test_a_1_0_reconnect_inside_the_waiting_time_drops_the_pending_return(self):
        self.close(2)
        self.focus(3)  # the compositor's pick: the terminal
        self.later(shell.HANDOFF / 5)
        self.hello(0)
        self.settle()
        self.assertEqual(self.activations, [])
        self.assertEqual((self.state('o-l'), self.helper_.shell), ('closed', 'background'))
        self.assertEqual(self.helper_.foreground_app, 'terminal')

    def test_a_1_1_reconnect_right_after_does_not_bring_it_back(self):
        self.close(2)
        self.focus(3)
        self.later(shell.HANDOFF / 5)
        self.hello(0, 'h-2')
        self.later(shell.HANDOFF / 5)
        self.hello(1, 'h-3')
        self.settle()
        self.assertEqual(self.activations, [])
        self.assertEqual(self.state('o-l'), 'closed')

    def test_under_1_0_a_discovered_close_not_yet_processed_forces_no_return(self):
        # The close is still in the compositor's queue when the 1.0 desktop says hello.
        self.windows.gone(2)
        self.hello(0)
        self.focus(3)
        self.settle()
        self.assertEqual(self.activations, [])
        self.assertEqual(self.state('o-l'), 'closed')

    def test_control_a_1_1_desktop_still_gets_the_return(self):
        self.close(2)
        self.focus(3)
        self.settle()
        self.assertEqual(self.activations, [1])


class LateSwitchTest(WindowsBase):
    """Package review fix 2 (REVIEW-2 finding 2): the switch he just made wins over an overdue return."""

    def test_a_switch_arriving_after_the_deadline_but_before_the_return_ran_wins(self):
        self.close(2)
        self.focus(3)  # the compositor's pick
        self.later(shell.HANDOFF * 0.8)  # a tick inside the hand-over interval: the return still waits
        self.now[0] += shell.HANDOFF * 0.3  # past its deadline, and no tick ran since
        self.focus(4)  # his switch to the editor is the next thing the helper hears
        self.settle()
        self.assertEqual(self.activations, [])
        self.assertEqual(self.state('o-l'), 'closed')
        self.assertEqual((self.helper_.shell, self.helper_.foreground_app), ('background', 'notepad'))
        self.assertEqual(self.focus_events(self.before), [])

    def test_control_other_news_after_the_deadline_still_runs_the_return(self):
        self.close(2)
        self.focus(3)
        self.later(shell.HANDOFF * 0.8)
        self.now[0] += shell.HANDOFF * 0.3
        self.window(6, 'aresos.terminal')  # compositor news, but no switch: the pick stays in front
        self.assertEqual(self.activations, [1])
        self.assertEqual(self.focus_events(self.before), [('foreground', 'app_closed', 'lunarclient')])


class PrefixPrecedenceTest(OwnershipBase):
    """Package review fix 3 (REVIEW-2 finding 3): a reviewed prefix beats a discovered program's exact identity."""

    def start(self, tracked=True, journal=None, windows=None):
        apps, revision = shell.load_registry(REGISTRY)
        apps.update({app_id: self.app(app_id) for app_id in ('lunarclient', 'discord', 'steam')})
        # A program of his own whose entry names a Steam game's window identity.
        apps['cyberpunk'] = self.app('cyberpunk', StartupWMClass='steam_app_1086940')
        apps = shell.apply_hints(apps, shell.load_hints(str(REGISTRY / 'hints')))
        self.windows = windows or shell.Windows(clock=self.clock)
        self.helper_ = shell.Helper(str(REGISTRY), INSTANCE, NONCE, journal or self.journal,
                                    registry=(apps, revision), launcher=self.launcher(), windows=self.windows,
                                    activate=self.activate, clock=self.clock, executable=lambda path: True)
        self.addCleanup(self.helper_.watcher.stop)
        self.conn = self.connect(self.helper_)
        return self.helper_

    def test_the_discovered_entry_loses_the_identity_and_steam_keeps_its_game(self):
        self.open('steam', 'o-s')
        self.window(2, 'steam', active=True)
        self.later(20)
        self.window(3, 'steam_app_1086940', active=True)
        self.assertEqual(self.windows.toplevels[3].owner, 'steam')
        self.later(shell.HANDOFF / 5)
        self.close(2)  # the launcher closes right after the game took the focus
        self.later(shell.HANDOFF * 4)
        self.assertEqual((self.activations, self.state('o-s'), self.helper_.shell), ([], 'focused', 'background'))
        self.later(600)
        self.close(3)
        self.later(shell.HANDOFF + 0.01)
        self.assertEqual((self.activations, self.state('o-s')), ([1], 'closed'))
        self.assertEqual(self.focus_events()[-1], ('foreground', 'app_closed', 'steam'))
        self.assertEqual(self.helper_.apps['cyberpunk'].app_ids, ('cyberpunk',))  # its own identity stays

    def test_windows_rank_registry_then_hints_exact_then_prefix_then_discovered_candidates(self):
        steam = dataclasses.replace(self.app('steam'), app_id_prefixes=('steam_app_',))
        lunar = dataclasses.replace(self.app('lunarclient'), app_ids=('lunarclient', 'com.mojang.minecraft'),
                                    hint_ids=('com.mojang.minecraft',))
        # Candidates that apply_hints would have removed, as a program kept from an older catalogue may still hold.
        game = self.app('cyberpunk', StartupWMClass='steam_app_1086940')
        other = self.app('prism', StartupWMClass='com.mojang.minecraft')
        terminal = self.app('fake-terminal', StartupWMClass='aresos.terminal')
        registry, _ = shell.load_registry(REGISTRY)
        expected = {'steam_app_1086940': 'steam', 'com.mojang.minecraft': 'lunarclient', 'aresos.terminal': 'terminal',
                    'cyberpunk': 'cyberpunk', 'prism': 'prism', 'aresos-desktop': shell.Windows.SHELL}
        for order in ((game, other, terminal, steam, lunar), (steam, lunar, game, other, terminal)):
            with self.subTest(first=order[0].id):
                windows = shell.Windows()
                windows.set_registry({app.id: app for app in order} | registry)
                for handle, identity in enumerate(expected, 1):
                    windows.new(handle)
                    windows.app_id(handle, identity)
                    windows.done(handle)
                self.assertEqual({t.app_id: t.owner for t in windows.toplevels.values()}, expected)
