"""Package 53d: Super's search over the world (SIGUSR1, shell_search) and open_app's screen hint.

Everything runs in this process: no helper subprocess, no real WAYLAND_DISPLAY or XDG_RUNTIME_DIR.
"""
import os
import pathlib
import select
import selectors
import signal
import socket
import threading
import unittest
from unittest import mock

from test_aresos_shell import Conn, INSTANCE, NONCE, REGISTRY, shell
from test_aresos_shell_views import GAME, NOTEPAD, TERMINAL, TOKEN, ViewBase, example

DESKTOP_OFFERS = ['list_apps', 'open_app', 'app_state', 'shell_focus', 'world_ready', 'heartbeat', 'windows',
                  'app_details', 'apps_changed', 'list_paging', 'shell_covered', 'home_state', 'shell_search']
WORLD = {'desktop': True, 'id': 'world'}
# The world's screen and the other one.
MONITOR, LAPTOP = 1, 2


class SearchBase(ViewBase):
    def setUp(self):
        super().setUp()
        self.minimized = []

    def minimize(self, handle):
        self.minimized.append(handle)
        return True

    def start(self, *, tracked=True, executable=None):
        windows = shell.Windows(self.clock) if tracked else None
        helper = shell.Helper(REGISTRY, INSTANCE, NONCE, self.journal, launcher=self.launcher(), windows=windows,
                              activate=self.activate, minimize=self.minimize, clock=self.clock,
                              executable=executable or (lambda _: True), view_token=TOKEN)
        self.addCleanup(helper.watcher.stop)
        return helper

    def desktop(self, helper, minor=2, offers=DESKTOP_OFFERS, ready=True):
        conn = Conn()
        helper.connected(conn)
        reply = self.call(helper, conn, 'hello', major=1, minor=minor, instance=INSTANCE, nonce=NONCE,
                          capabilities=offers)
        self.assertTrue(reply['ok'], reply)
        if ready:
            self.assertTrue(self.call(helper, conn, 'world_ready', instance=INSTANCE, nonce=NONCE, world=WORLD)['ok'])
        return conn

    def world(self, helper, active=True):
        """The game's window on the monitor, as the compositor lists it."""
        self.show(helper.windows, 1, GAME, active=active, outputs=(MONITOR,))
        helper.windows_changed()

    def ready(self, **options):
        helper = self.start()
        conn = self.desktop(helper, **options)
        self.world(helper)
        return helper, conn


class SignalTest(SearchBase):
    def keep_signal_state(self):
        self.addCleanup(signal.signal, signal.SIGUSR1, signal.getsignal(signal.SIGUSR1))

    def test_the_handler_is_in_place_before_parse_args_and_build(self):
        self.keep_signal_state()
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)
        seen = {}
        parse = shell.argparse.ArgumentParser.parse_args

        def parse_args(parser, *arguments, **options):
            seen.setdefault('parse_args', signal.getsignal(signal.SIGUSR1))
            return parse(parser, *arguments, **options)

        class Built(Exception):
            pass

        def build(*arguments, **options):
            seen['build'] = signal.getsignal(signal.SIGUSR1)
            raise Built()

        runtime = pathlib.Path(self.folder.name, 'runtime')
        runtime.mkdir(mode=0o700)
        environment = {'XDG_RUNTIME_DIR': str(runtime), 'ARESOS_DESKTOP_INSTANCE': INSTANCE,
                       'ARESOS_LAUNCH_NONCE': NONCE}
        with mock.patch.dict(os.environ, environment), \
                mock.patch.object(shell.argparse.ArgumentParser, 'parse_args', parse_args), \
                mock.patch.object(shell, 'build', build), mock.patch.object(shell.logging, 'basicConfig'):
            os.environ.pop('ARESOS_SHELL_STATUS_FD', None)
            os.environ.pop('ARESOS_SHELL_SOCKET', None)
            with self.assertRaises(Built):
                shell.main(['--socket', str(runtime / 'aresos' / 'shell.sock')])
        for moment in ('parse_args', 'build'):
            handler = seen[moment]
            self.assertTrue(callable(handler), (moment, handler))
            self.assertIsInstance(getattr(handler, '__self__', None), shell.SearchSignal, moment)

    def test_the_handler_only_sets_the_flag(self):
        helper, conn = self.ready()
        before = list(conn.sent)
        search = shell.SearchSignal()
        with mock.patch.object(helper, 'search') as act, mock.patch.object(shell.os, 'write') as write:
            search.record(signal.SIGUSR1, None)
            act.assert_not_called()
            write.assert_not_called()
        self.assertTrue(search.requested)
        self.assertEqual((conn.sent, self.activations, self.minimized), (before, [], []))
        self.assertTrue(search.take())
        self.assertFalse(search.take())

    def test_a_real_signal_wakes_the_serving_loop_which_then_acts(self):
        self.keep_signal_state()
        helper, conn = self.ready()
        search = shell.SearchSignal.install()
        search.wake_through_pipe()
        self.addCleanup(search.close)
        self.assertEqual(signal.getsignal(signal.SIGUSR1), search.record)
        server = shell.Server(os.path.join(self.folder.name, 'run', 'shell.sock'), helper, search=search)
        self.addCleanup(server.close)
        with mock.patch.object(helper, 'search', wraps=helper.search) as act:
            server.step(timeout=0)
            act.assert_not_called()
            signal.raise_signal(signal.SIGUSR1)
            # Nothing has acted yet: the handler only set the flag and wrote to the wake-up pipe.
            self.assertEqual(conn.events('shell_search'), [])
            self.assertEqual(select.select([search.reader], [], [], 0)[0], [search.reader])
            server.step(timeout=5)
            act.assert_called_once_with()
        self.assertEqual(len(conn.events('shell_search')), 1)
        self.assertEqual(select.select([search.reader], [], [], 0)[0], [], 'the pipe is drained')
        self.assertFalse(search.requested)

    def test_a_signal_before_the_wake_up_pipe_is_not_lost(self):
        helper, conn = self.ready()
        search = shell.SearchSignal()
        server = shell.Server(os.path.join(self.folder.name, 'run', 'shell.sock'), helper, search=search)
        self.addCleanup(server.close)
        search.record(signal.SIGUSR1, None)
        server.step(timeout=0)
        self.assertEqual(len(conn.events('shell_search')), 1)


class EventTest(SearchBase):
    def test_capability_is_offered_only_to_a_minor_2_desktop_with_window_tracking(self):
        for tracked, minor, role, offered in ((True, 2, 'desktop', True), (True, 1, 'desktop', False),
                                              (False, 2, 'desktop', False), (True, 2, 'view', False)):
            with self.subTest(tracked=tracked, minor=minor, role=role):
                helper = self.start(tracked=tracked)
                conn = Conn()
                helper.connected(conn)
                if role == 'view':
                    reply = self.send(helper, conn, dict(example('view-hello-request'),
                                                         capabilities=['shell_search', 'views']))
                else:
                    reply = self.call(helper, conn, 'hello', major=1, minor=minor, instance=INSTANCE, nonce=NONCE,
                                      capabilities=DESKTOP_OFFERS)
                self.assertTrue(reply['ok'], reply)
                self.assertEqual('shell_search' in reply['capabilities'], offered)

    def test_the_event_reaches_only_a_minor_2_desktop_that_offered_it_and_never_a_view(self):
        helper, conn = self.ready()
        view = Conn()
        helper.connected(view)
        self.assertTrue(self.send(helper, view, dict(example('view-hello-request'),
                                                     capabilities=['shell_search', 'views']))['ok'])
        helper.search()
        self.assertEqual([event['event'] for event in conn.events() if event['event'] == 'shell_search'],
                         ['shell_search'])
        self.assertEqual(conn.events('shell_search')[0]['protocol'], 'aresos-shell/1.2')
        self.assertEqual(view.events('shell_search'), [])
        # emit_to's own gate: a view never, a minor-1 desktop never, whatever it offered.
        helper.emit_to(view, 'shell_search')
        self.assertEqual(view.events('shell_search'), [])
        conn.minor = 1
        helper.emit_to(conn, 'shell_search')
        self.assertEqual(len(conn.events('shell_search')), 1)

        for minor, offers in ((2, [name for name in DESKTOP_OFFERS if name != 'shell_search']), (1, DESKTOP_OFFERS)):
            with self.subTest(minor=minor, offered='shell_search' in offers):
                self.activations.clear()
                helper = self.start()
                conn = self.desktop(helper, minor=minor, offers=offers)
                self.world(helper, active=False)
                self.show(helper.windows, 2, NOTEPAD, active=True, outputs=(MONITOR,))
                helper.windows_changed()
                helper.search()
                self.assertEqual((conn.events('shell_search'), self.activations), ([], []))

    def test_nothing_happens_without_a_desktop_world_ready_window_tracking_or_the_worlds_window(self):
        def check(helper, conns):
            helper.search()
            for conn in conns:
                self.assertEqual(conn.events('shell_search'), [])
            self.assertEqual((self.activations, self.minimized), ([], []))

        helper = self.start()
        self.world(helper, active=False)
        view = self.view(helper)
        check(helper, [view])

        self.now[0] += 1
        helper = self.start()
        conn = self.desktop(helper, ready=False)
        self.world(helper, active=False)
        check(helper, [conn])

        # Ready, then taken back by a heartbeat.
        self.now[0] += 1
        helper = self.start()
        conn = self.desktop(helper)
        self.world(helper, active=False)
        self.assertTrue(self.call(helper, conn, 'heartbeat', instance=INSTANCE, nonce=NONCE, ready=False)['ok'])
        check(helper, [conn])

        # Another desktop's world_ready does not count for a new connection.
        self.now[0] += 1
        self.desktop(helper)
        replacement = self.desktop(helper, ready=False)
        check(helper, [replacement])

        self.now[0] += 1
        helper = self.start(tracked=False)
        conn = self.desktop(helper, offers=DESKTOP_OFFERS)
        check(helper, [conn])

        self.now[0] += 1
        helper = self.start()
        conn = self.desktop(helper)
        self.show(helper.windows, 2, NOTEPAD, active=True, outputs=(MONITOR,), maximized=True)
        helper.windows_changed()
        check(helper, [conn])

    def test_a_maximized_window_on_the_worlds_screen_is_minimized_and_other_windows_stay(self):
        helper, conn = self.ready()
        windows = helper.windows
        windows.state(1, False)
        windows.done(1)
        self.show(windows, 2, NOTEPAD, outputs=(MONITOR,))                   # small, on the world's screen
        self.show(windows, 3, TERMINAL, outputs=(LAPTOP,), maximized=True)   # maximized, on the other screen
        self.show(windows, 4, NOTEPAD, active=True, outputs=(MONITOR,), maximized=True)
        helper.windows_changed()
        self.assertEqual(conn.events('shell_covered')[-1]['covered'], True)
        focus = len(conn.events('shell_focus'))
        helper.search()
        # Activation is asked for; nothing is minimized and the mod is told nothing before the compositor answers.
        self.assertEqual(self.activations, [1])
        self.assertEqual(conn.events('shell_search'), [])
        self.assertEqual(self.minimized, [])
        self.assertEqual(len(conn.events('shell_focus')), focus, 'no shell_focus of our own, unlike return_to_desktop')
        self.assertEqual(helper.shell, 'background')
        # The compositor activates the world: the existing activation path uncovers it.
        windows.state(4, False, maximized=True)
        windows.done(4)
        windows.state(1, True)
        windows.done(1)
        helper.windows_changed()
        self.assertEqual(self.minimized, [4])
        self.assertEqual(conn.events('shell_focus')[-1], dict(conn.events('shell_focus')[-1], focus='foreground',
                                                              reason='desktop_activated'))
        # Then the search, after the focus: the world has the keyboard by now.
        self.assertEqual([event['event'] for event in conn.events() if event['event'] in ('shell_focus', 'shell_search')]
                         [-2:], ['shell_focus', 'shell_search'])

    def test_a_small_window_in_front_is_left_where_it_is(self):
        helper, conn = self.ready()
        helper.windows.state(1, False)
        helper.windows.done(1)
        self.show(helper.windows, 2, NOTEPAD, active=True, outputs=(MONITOR,))
        helper.windows_changed()
        helper.search()
        helper.windows.state(2, False)
        helper.windows.done(2)
        helper.windows.state(1, True)
        helper.windows.done(1)
        helper.windows_changed()
        self.assertEqual((self.activations, self.minimized, len(conn.events('shell_search'))), ([1], [], 1))

    def test_the_world_already_active(self):
        helper, conn = self.ready()
        self.show(helper.windows, 3, TERMINAL, outputs=(LAPTOP,), maximized=True)
        helper.windows_changed()
        helper.search()
        # The compositor is asked all the same (review 2): the world may only look active. It is the one active
        # window here, so the search opens at once.
        self.assertEqual((self.activations, self.minimized), ([1], []))
        self.assertEqual(len(conn.events('shell_search')), 1)
        self.assertIsNone(helper.search_handoff)
        # A maximized window that opened over the active world without taking the focus: no activation will come
        # to uncover it, so the search does, by the same rule.
        self.now[0] += 1
        self.show(helper.windows, 4, NOTEPAD, outputs=(MONITOR,), maximized=True)
        helper.windows_changed()
        helper.search()
        self.assertEqual((self.activations, self.minimized), ([1, 1], [4]))
        self.assertEqual(len(conn.events('shell_search')), 2)

    def test_a_failed_activation_sends_no_event(self):
        helper, conn = self.ready()
        helper.windows.state(1, False)
        helper.windows.done(1)
        self.show(helper.windows, 2, NOTEPAD, active=True, outputs=(MONITOR,))
        helper.windows_changed()
        helper.activate_window = lambda handle: False
        helper.search()
        self.assertEqual(conn.events('shell_search'), [])

    def test_signals_are_coalesced(self):
        helper, conn = self.ready()
        helper.search()
        self.now[0] += 0.1
        helper.search()
        self.now[0] += 0.19
        helper.search()
        self.assertEqual(len(conn.events('shell_search')), 1)
        self.now[0] += 0.02
        helper.search()
        self.assertEqual(len(conn.events('shell_search')), 2)


class HandoffTest(SearchBase):
    """Review 1: the bar opens only once the world really has the keyboard, on current readiness and activation."""

    def setUp(self):
        super().setUp()
        # The module quiets the helper's log; these tests read what it says.
        logging = mock.patch.object(shell.LOG, 'disabled', False)
        logging.start()
        self.addCleanup(logging.stop)

    def behind_a_terminal(self):
        helper, conn = self.ready()
        helper.windows.state(1, False)
        helper.windows.done(1)
        self.show(helper.windows, 2, TERMINAL, active=True, outputs=(MONITOR,))
        helper.windows_changed()
        return helper, conn

    def activate_world(self, helper, previous=2):
        if previous is not None:
            helper.windows.state(previous, False)
            helper.windows.done(previous)
        helper.windows.state(1, True)
        helper.windows.done(1)
        helper.windows_changed()

    def test_no_event_while_another_window_is_still_active_and_one_once_the_world_is(self):
        helper, conn = self.behind_a_terminal()
        helper.search()
        self.assertEqual((self.activations, conn.events('shell_search')), ([1], []))
        # Compositor news that is not the world's activation: the terminal still has the keyboard.
        self.now[0] += 0.2
        helper.windows.app_id(2, TERMINAL)
        helper.windows.done(2)
        helper.windows_changed()
        helper.tick()
        self.assertEqual(conn.events('shell_search'), [])
        self.now[0] += 0.2
        self.activate_world(helper)
        self.assertEqual(len(conn.events('shell_search')), 1)
        # Once: a later activation of the world (a click, Alt+Tab) is not Super.
        self.now[0] += 2
        helper.windows.state(1, False)
        helper.windows.done(1)
        helper.windows.state(2, True)
        helper.windows.done(2)
        helper.windows_changed()
        self.activate_world(helper)
        self.assertEqual(len(conn.events('shell_search')), 1)

    def test_nothing_when_the_world_does_not_get_the_keyboard_within_a_second(self):
        helper, conn = self.behind_a_terminal()
        helper.search()
        self.now[0] += shell.SEARCH_ACTIVATION + 0.01
        with self.assertLogs(shell.LOG, 'WARNING') as logs:
            helper.tick()
        self.assertIn('did not give the world the keyboard', '\n'.join(logs.output))
        self.activate_world(helper)
        self.assertEqual(conn.events('shell_search'), [])
        # Also when the late activation comes before the next tick.
        self.now[0] += 1
        helper.windows.state(1, False)
        helper.windows.done(1)
        helper.windows.state(2, True)
        helper.windows.done(2)
        helper.windows_changed()
        helper.search()
        self.now[0] += shell.SEARCH_ACTIVATION + 0.01
        with self.assertLogs(shell.LOG, 'INFO') as logs:
            self.activate_world(helper)
        self.assertIn('too late', '\n'.join(logs.output))
        self.assertEqual(conn.events('shell_search'), [])

    def test_readiness_taken_back_while_waiting_sends_nothing(self):
        helper, conn = self.behind_a_terminal()
        helper.search()
        self.assertTrue(self.call(helper, conn, 'heartbeat', instance=INSTANCE, nonce=NONCE, ready=False)['ok'])
        self.activate_world(helper)
        self.assertEqual(conn.events('shell_search'), [])
        # The desktop reconnected meanwhile: the new connection has not said its world is ready.
        self.now[0] += 1
        helper, conn = self.behind_a_terminal()
        helper.search()
        replacement = self.desktop(helper, ready=False)
        self.activate_world(helper)
        self.assertEqual((conn.events('shell_search'), replacement.events('shell_search')), ([], []))

    def test_no_uncover_on_the_last_active_handle_alone(self):
        # The world was active last, then no window is (a menu or a launcher of the compositor's own has the keyboard),
        # and a maximized window hides the world.
        helper, conn = self.ready()
        self.show(helper.windows, 4, NOTEPAD, outputs=(MONITOR,), maximized=True)
        helper.windows.state(1, False)
        helper.windows.done(1)
        helper.windows_changed()
        self.assertIsNone(helper.windows.active())
        self.assertEqual(helper.active_handle, 1)
        helper.search()
        self.assertEqual((self.activations, self.minimized, conn.events('shell_search')), ([1], [], []))
        # The compositor's activation is the current one: now it uncovers, and the search opens.
        self.activate_world(helper, previous=None)
        self.assertEqual((self.minimized, len(conn.events('shell_search'))), ([4], 1))

    def test_an_activation_that_never_comes_minimizes_nothing(self):
        helper, conn = self.ready()
        self.show(helper.windows, 4, NOTEPAD, outputs=(MONITOR,), maximized=True)
        helper.windows.state(1, False)
        helper.windows.done(1)
        helper.windows_changed()
        helper.search()
        self.now[0] += shell.SEARCH_ACTIVATION + 0.01
        helper.tick()
        self.assertEqual((self.minimized, conn.events('shell_search')), ([], []))


class OnlyActiveWindowTest(SearchBase):
    """Review 2: shell_search and the uncovering come only once the world is the one active window, and the activation
    of a search that was called off uncovers nothing."""

    def setUp(self):
        super().setUp()
        logging = mock.patch.object(shell.LOG, 'disabled', False)
        logging.start()
        self.addCleanup(logging.stop)

    def covered(self, first='world'):
        """The world behind a maximized terminal on its screen, which has the keyboard. `first`: which of the two the
        compositor listed first, the one Windows.active() names while both are reported active."""
        self.activations.clear()
        self.minimized.clear()
        helper = self.start()
        conn = self.desktop(helper)
        if first == 'world':
            self.world(helper, active=False)
        self.show(helper.windows, 2, TERMINAL, active=True, outputs=(MONITOR,), maximized=True)
        helper.windows_changed()
        if first != 'world':
            self.world(helper, active=False)
        self.assertEqual((helper.windows.active().handle, helper.shell), (2, 'background'))
        return helper, conn

    def news(self, helper, *changes):
        """One read from the compositor: each window's (handle, activated) with its done, then the helper looks."""
        for handle, activated in changes:
            helper.windows.state(handle, activated, maximized=handle != 1)
            helper.windows.done(handle)
        helper.windows_changed()

    def outcome(self, conn):
        return self.activations, self.minimized, len(conn.events('shell_search'))

    def test_a_split_update_waits_for_the_read_that_leaves_the_world_alone_active(self):
        for first in ('world', 'terminal'):
            with self.subTest(listed_first=first):
                helper, conn = self.covered(first)
                helper.search()
                self.assertEqual(self.outcome(conn), ([1], [], 0))
                # The read ends between the two windows' events: the world and the terminal are both reported active.
                self.news(helper, (1, True))
                self.assertEqual(self.outcome(conn), ([1], [], 0))
                helper.tick()
                self.assertEqual(self.outcome(conn), ([1], [], 0))
                self.news(helper, (2, False))
                self.assertEqual(self.outcome(conn), ([1], [2], 1))
                self.assertEqual([event['event'] for event in conn.events()
                                  if event['event'] in ('shell_focus', 'shell_search')][-2:],
                                 ['shell_focus', 'shell_search'])
                self.assertEqual(conn.events('shell_focus')[-1]['focus'], 'foreground')
                self.assertIsNone(helper.search_handoff)
                # Once: the terminal's later news opens nothing more.
                self.news(helper, (2, False))
                self.assertEqual(self.outcome(conn), ([1], [2], 1))

    def test_both_halves_in_one_read_open_the_search_at_that_read(self):
        for changes in (((2, False), (1, True)), ((1, True), (2, False))):
            for first in ('world', 'terminal'):
                with self.subTest(changes=changes, listed_first=first):
                    helper, conn = self.covered(first)
                    helper.search()
                    self.news(helper, *changes)
                    self.assertEqual(self.outcome(conn), ([1], [2], 1))

    def test_a_split_update_that_never_completes_ends_at_the_one_second_bound(self):
        helper, conn = self.covered()
        helper.search()
        self.news(helper, (1, True))
        self.now[0] += shell.SEARCH_ACTIVATION + 0.01
        with self.assertLogs(shell.LOG, 'WARNING'):
            helper.tick()
        self.news(helper, (2, False))
        self.assertEqual(self.outcome(conn), ([1], [], 0))

    def test_the_world_only_looking_active_beside_another_window(self):
        # Review 2's case: the focus is on its way from the world to a terminal, and the helper's last read ended
        # half-way: the terminal is reported active and the world still is. Listed first, the world is the window
        # Windows.active() names. Super asks the compositor anyway, and minimizes nothing until its answer.
        for first in (1, 2):
            with self.subTest(listed_first=first):
                self.activations.clear()
                self.minimized.clear()
                helper = self.start()
                conn = self.desktop(helper)
                for handle in (first, 3 - first):
                    if handle == 1:
                        self.show(helper.windows, 1, GAME, active=True, outputs=(MONITOR,))
                    else:
                        self.show(helper.windows, 2, TERMINAL, outputs=(MONITOR,), maximized=True)
                helper.windows_changed()
                self.assertTrue(helper.windows.alone_active(1))
                self.news(helper, (2, True))
                self.assertEqual(helper.windows.active().handle, first)
                helper.search()
                self.assertEqual(self.outcome(conn), ([1], [], 0))
                self.news(helper, (1, False))
                self.assertEqual(self.outcome(conn), ([1], [], 0))
                # The compositor's answer to Super's request.
                self.news(helper, (2, False), (1, True))
                self.assertEqual(self.outcome(conn), ([1], [2], 1))

    def test_a_not_ready_heartbeat_during_the_handoff_minimizes_nothing(self):
        for split in (False, True):
            with self.subTest(split=split):
                helper, conn = self.covered()
                helper.search()
                self.assertTrue(self.call(helper, conn, 'heartbeat', instance=INSTANCE, nonce=NONCE, ready=False)['ok'])
                # Ready again before the compositor answers: called off stays called off.
                self.assertTrue(self.call(helper, conn, 'world_ready', instance=INSTANCE, nonce=NONCE,
                                          world=WORLD)['ok'])
                if split:
                    self.news(helper, (1, True))
                    self.news(helper, (2, False))
                else:
                    self.news(helper, (2, False), (1, True))
                # The world simply has the focus: no window minimized, no search.
                self.assertEqual(self.outcome(conn), ([1], [], 0))
                self.assertEqual((helper.shell, conn.events('shell_focus')[-1]['focus']), ('foreground', 'foreground'))
                self.assertIsNone(helper.search_handoff)
                # The mark is used up: his own way back to the world uncovers it as ever.
                self.news(helper, (1, False), (2, True))
                self.news(helper, (2, False), (1, True))
                self.assertEqual(self.outcome(conn), ([1], [2], 0))

    def test_a_new_connection_during_the_handoff_minimizes_nothing(self):
        helper, conn = self.covered()
        helper.search()
        # The mod reconnected, and its new connection is ready and offered the search: still not this press's.
        replacement = self.desktop(helper)
        self.news(helper, (2, False), (1, True))
        self.assertEqual(self.outcome(conn), ([1], [], 0))
        self.assertEqual(replacement.events('shell_search'), [])
        self.assertEqual(helper.shell, 'foreground')

    def test_an_answer_after_the_one_second_bound_minimizes_nothing(self):
        for ticked in (True, False):
            with self.subTest(ticked=ticked):
                helper, conn = self.covered()
                helper.search()
                self.now[0] += shell.SEARCH_ACTIVATION + 0.01
                if ticked:
                    with self.assertLogs(shell.LOG, 'WARNING') as logs:
                        helper.tick()
                    self.assertIn('did not give the world the keyboard', '\n'.join(logs.output))
                self.now[0] += 0.5
                self.news(helper, (2, False), (1, True))
                self.assertEqual(self.outcome(conn), ([1], [], 0))
                self.assertEqual(helper.shell, 'foreground')
                self.assertIsNone(helper.search_handoff)

    def test_the_mark_runs_out_when_the_compositor_never_answers(self):
        self.assertGreater(shell.SEARCH_MARK, shell.SEARCH_ACTIVATION)
        for ticked in (True, False):
            with self.subTest(ticked=ticked):
                helper, conn = self.covered()
                helper.search()
                self.now[0] += shell.SEARCH_MARK + 0.01
                if ticked:
                    helper.tick()
                    self.assertIsNone(helper.search_handoff)
                # Long after: his own Alt+Tab to the world is not Super's activation, and uncovers it.
                self.news(helper, (2, False), (1, True))
                self.assertEqual(self.outcome(conn), ([1], [2], 0))

    def test_another_press_while_one_waits_asks_again_and_opens_once(self):
        helper, conn = self.covered()
        helper.search()
        self.now[0] += shell.SEARCH_COALESCE + 0.01
        helper.search()
        self.news(helper, (2, False), (1, True))
        self.assertEqual(self.outcome(conn), ([1, 1], [2], 1))


class WaylandWriteTest(SearchBase):
    """Review 1, should-fix 2: a full compositor socket never ends the helper; a closed one is a lost compositor."""

    def client(self, sock):
        windows = shell.Windows(self.clock)
        client = shell.ForeignToplevels(sock, windows)
        client.kinds.update({1000: 'toplevel'})
        client.seat = client._new('seat')
        return client

    def test_a_blocked_write_is_queued_and_a_partial_one_keeps_its_rest(self):
        sock = mock.Mock()
        sock.send.side_effect = lambda data: len(data)
        client = self.client(sock)
        sock.send.side_effect = BlockingIOError()
        self.assertTrue(client.activate(1000))
        self.assertTrue(client.minimize(1000))
        activate = shell.struct.pack('=III', 1000, (12 << 16) | 4, client.seat)
        minimize = shell.struct.pack('=II', 1000, (8 << 16) | 2)
        self.assertEqual(bytes(client.outbuf), activate + minimize)
        # The socket takes five bytes, then is full again: the rest stays queued, in order.
        sock.send.side_effect = [5, BlockingIOError()]
        client.flush()
        self.assertEqual(bytes(client.outbuf), (activate + minimize)[5:])
        written = []
        sock.send.side_effect = lambda data: written.append(bytes(data)) or len(data)
        client.flush()
        self.assertEqual((client.outbuf, written), (bytearray(), [(activate + minimize)[5:]]))

    def test_a_closed_compositor_socket_is_a_lost_compositor(self):
        sock = mock.Mock()
        sock.send.side_effect = lambda data: len(data)
        client = self.client(sock)
        for error in (BrokenPipeError(), ConnectionResetError()):
            with self.subTest(error=type(error).__name__):
                sock.send.side_effect = error
                with self.assertRaises(shell.WaylandError):
                    client.activate(1000)

    def test_super_over_a_full_socket_queues_the_activation_and_the_loop_sends_it_later(self):
        ours, theirs = socket.socketpair()
        self.addCleanup(ours.close)
        self.addCleanup(theirs.close)
        helper = self.start()
        wayland = self.client(ours)
        theirs.recv(65536)
        ours.setblocking(False)
        # The compositor is not reading: fill the socket up.
        try:
            while True:
                ours.send(b'\0' * 65536)
        except BlockingIOError:
            pass
        helper.activate_window, helper.minimize_window = wayland.activate, wayland.minimize
        conn = self.desktop(helper)
        self.show(helper.windows, 1000, GAME, outputs=(MONITOR,))
        self.show(helper.windows, 2, TERMINAL, active=True, outputs=(MONITOR,))
        helper.windows_changed()
        server = shell.Server(os.path.join(self.folder.name, 'run', 'shell.sock'), helper, wayland)
        self.addCleanup(server.close)
        helper.search()   # no BlockingIOError escapes
        request = shell.struct.pack('=III', 1000, (12 << 16) | 4, wayland.seat)
        self.assertEqual(bytes(wayland.outbuf), request)
        server.step(timeout=0)
        self.assertEqual(server.selector.get_key(ours).events, selectors.EVENT_READ | selectors.EVENT_WRITE)
        # The compositor reads again: the loop writes the queued request, whole and in order, and stops watching.
        theirs.setblocking(False)
        received = bytearray()
        for _ in range(100):
            try:
                while True:
                    received += theirs.recv(1 << 20)
            except BlockingIOError:
                pass
            server.step(timeout=0.05)
            if not wayland.outbuf:
                break
        try:
            while True:
                received += theirs.recv(1 << 20)
        except BlockingIOError:
            pass
        self.assertTrue(received.endswith(request), received[-16:])
        self.assertEqual(wayland.outbuf, bytearray())
        self.assertEqual(server.selector.get_key(ours).events, selectors.EVENT_READ)
        self.assertEqual(conn.events('shell_search'), [])


class ScreenHintTest(SearchBase):
    def open(self, helper, conn, request_id='o-1', **fields):
        return self.call(helper, conn, 'open_app', request_id, app_id='notepad', **fields)

    def test_valid_bad_from_a_view_and_from_1_1(self):
        helper = self.start()
        conn = self.desktop(helper)
        reply = self.open(helper, conn, screen='world')
        self.assertTrue(reply['ok'], reply)
        self.assertNotIn('screen', reply)
        self.assertEqual(helper.journal.entries['desktop', 'o-1']['screen'], 'world')
        plain = self.open(helper, conn, 'o-2')
        self.assertTrue(plain['ok'], plain)
        self.assertNotIn('screen', helper.journal.entries['desktop', 'o-2'])
        for number, screen in enumerate(('laptop', 'World', '', None, 5, ['world'], {'name': 'world'}), 3):
            with self.subTest(screen=screen):
                reply = self.open(helper, conn, f'o-{number}', screen=screen)
                self.assertEqual(reply['error'], 'malformed', reply)
                self.assertNotIn(('desktop', f'o-{number}'), helper.journal.entries)
        view = self.view(helper)
        self.assertEqual(self.open(helper, view, 'v-1', screen='world')['error'], 'malformed')
        self.assertTrue(self.open(helper, view, 'v-2')['ok'])
        older = self.desktop(helper, minor=1, offers=DESKTOP_OFFERS[:-1])
        self.assertEqual(self.open(helper, older, 'o-20', screen='world')['error'], 'malformed')
        self.assertTrue(self.open(helper, older, 'o-21')['ok'])

    def test_kept_through_a_duplicate_and_a_journal_reload(self):
        helper = self.start()
        conn = self.desktop(helper)
        first = self.open(helper, conn, screen='world')
        again = self.open(helper, conn, screen='world')
        self.assertEqual(again, first)
        self.assertEqual(self.popen.call_count, 1)
        # The duplicate of a resend without the hint is still the same launch, and the hint stays.
        self.assertEqual(self.open(helper, conn), first)
        self.assertEqual(helper.journal.entries['desktop', 'o-1']['screen'], 'world')
        restarted = self.start()
        self.assertEqual(restarted.journal.entries['desktop', 'o-1']['screen'], 'world')
        conn = self.desktop(restarted)
        self.assertEqual(self.open(restarted, conn, screen='world')['launch_id'], first['launch_id'])
        self.assertEqual(self.popen.call_count, 1)

    def test_kept_through_a_pending_check_and_its_duplicate(self):
        blocking, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def slow(path):
            # Only the launch check waits; the start-up's availability pass does not.
            if blocking.is_set():
                release.wait(5)
            return True

        helper = self.start(executable=slow)
        conn = self.desktop(helper)
        blocking.set()
        self.assertIsNone(self.open(helper, conn, screen='world'))
        self.assertIsNone(self.open(helper, conn, screen='world'))
        self.assertEqual(helper.checking['desktop', 'o-1']['screen'], 'world')
        release.set()
        helper.checking['desktop', 'o-1']['check'].done.wait(5)
        helper.tick()
        replies = [message for message in conn.sent if message.get('id') == 'o-1']
        self.assertEqual(len(replies), 2)
        self.assertTrue(all(reply['ok'] for reply in replies), replies)
        self.assertEqual(helper.journal.entries['desktop', 'o-1']['screen'], 'world')
        self.assertEqual(self.popen.call_count, 1)


if __name__ == '__main__':
    unittest.main()
