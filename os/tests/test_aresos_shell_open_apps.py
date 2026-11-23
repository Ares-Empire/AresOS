"""Package 333 window state, replay, and private diagnostic logs."""
import errno
import io
import json
import logging
from pathlib import Path
import socket
import stat
import threading
import types
from unittest import mock

from test_aresos_shell import ALL, Conn, INSTANCE, NONCE, ROOT, shell, wire_toplevel
from test_aresos_shell_views import GAME, NOTEPAD, TOKEN, WEB, ViewBase

WIRE = 'aresos-shell/1.3'
NEW = ['apps_state', 'activate_app']
BROWSER = 'google-chrome'
TERMINAL = 'aresos.terminal'


def example(name):
    return json.loads((ROOT / 'mod/src/test/resources/shell-1.3' / f'{name}.json').read_text())


class OpenAppsTest(ViewBase):
    def hello13(self, helper, *, view=None, capabilities=NEW):
        conn = Conn()
        helper.connected(conn)
        identity = dict(instance=INSTANCE, nonce=NONCE) if view is None else dict(
            instance=INSTANCE, role='view', view=view, token=TOKEN)
        reply = self.send(helper, conn, dict(protocol=WIRE, id='hello', op='hello', major=1, minor=3,
                                            capabilities=[*ALL, *capabilities], **identity))
        self.assertTrue(reply['ok'], reply)
        return conn, reply

    def ask(self, helper, conn, request_id, app='browser', **fields):
        return self.send(helper, conn, dict(protocol=WIRE, id=request_id, op='activate_app', app_id=app, **fields))

    def test_window_snapshots_and_minor_2_laptop_home(self):
        helper = self.start(tracked=True)
        windows = helper.windows
        self.show(windows, 1, BROWSER)
        self.show(windows, 2, BROWSER, active=True)
        self.show(windows, 3, NOTEPAD)
        windows.state(3, False, minimized=True)
        windows.done(3)
        self.show(windows, 4, TERMINAL)
        self.show(windows, 5, 'unattributed')
        helper.windows_changed()
        laptop = self.view(helper)
        desktop, reply = self.hello13(helper)
        view13, reply13 = self.hello13(helper, view='new-view')
        omitted, omitted_reply = self.hello13(helper, view='only-running', capabilities=[])
        self.assertTrue(set(NEW) <= set(reply['capabilities']))
        self.assertTrue(set(NEW) <= set(reply13['capabilities']))
        self.assertTrue(set(NEW).isdisjoint(omitted_reply['capabilities']))
        self.assertEqual(laptop.sent[0]['minor'], 2)
        self.assertEqual(laptop.sent[1], dict(protocol='aresos-shell/1.2', id='e-1', event='apps_running',
                                             apps=['browser', 'notepad', 'terminal']))
        self.assertEqual(desktop.sent[1], example('apps-state-event'))
        self.assertEqual(view13.events('apps_state')[0]['apps'], desktop.sent[1]['apps'])
        self.assertEqual(omitted.events('apps_state'), [])
        self.assertEqual(self.ask(helper, laptop, 'old')['error'], 'invalid_state')
        self.assertEqual(self.ask(helper, omitted, 'omits')['error'], 'invalid_state')
        mismatch = self.send(helper, laptop, dict(protocol='aresos-shell/9.3', op='list_apps', id='wrong'))
        self.assertEqual(mismatch['message'], 'this helper speaks aresos-shell/1.2')
        helper.tick()
        self.assertEqual(len(desktop.events('apps_state')), 1)

        windows.state(2, False, minimized=True)
        helper.tick()  # State has to reach done before the event.
        self.assertEqual(len(desktop.events('apps_state')), 1)
        windows.done(2)
        windows.state(1, False, minimized=True)
        windows.done(1)
        windows.gone(3)
        helper.windows_changed()
        self.assertEqual(len(desktop.events('apps_state')), 1)
        helper.tick()
        self.assertEqual(len(desktop.events('apps_state')), 2)
        self.assertEqual(desktop.events('apps_state')[-1]['apps'], [
            dict(id='browser', windows=2, active=False, hidden=True),
            dict(id='terminal', windows=1, active=False, hidden=False),
        ])
        self.assertEqual(laptop.events('apps_running')[-1]['apps'], ['browser', 'terminal'])
        self.assertEqual(laptop.events('apps_state'), [])
        self.assertEqual(omitted.events('apps_state'), [])

    def test_no_other_clients_replies_can_refuse_bringing_back_a_visible_window(self):
        helper = self.start(tracked=True)
        self.show(helper.windows, 30, BROWSER)
        helper.windows_changed()
        with mock.patch.object(helper, 'activate_window', return_value=False):
            for name in range(5):
                filler, _ = self.hello13(helper, view=f'filler-{name}')
                for number in range(shell.RECEIPT_LIMIT):
                    self.assertEqual(self.ask(helper, filler, f'a-{number}')['error'], 'activation_refused')
                self.assertEqual(self.ask(helper, filler, 'one-too-many')['error'], 'journal_full')
                # Its launch records are another table.
                self.assertEqual(self.call(helper, filler, 'open_app', 'unknown', app_id='fixture-unknown')['error'],
                                 'unknown_app')
                helper.disconnected(filler)
        desktop, _ = self.hello13(helper)
        other, _ = self.hello13(helper, view='unrelated')
        for conn in (desktop, other):
            self.assertIsNone(self.ask(helper, conn, 'restore'))
        helper.windows.state(30, True)
        helper.windows.done(30)
        helper.windows_changed()
        for conn in (desktop, other):
            self.assertEqual(next(m for m in conn.sent if m['id'] == 'restore')['state'], 'activated')
        # A receipt makes room once nobody can resend its ID any more.
        self.now[0] += shell.RECEIPT_HORIZON
        filler, _ = self.hello13(helper, view='filler-0')
        self.assertIsNone(self.ask(helper, filler, 'after-the-horizon'))
        self.assertEqual(self.popen.call_count, 0)

    def test_a_full_launch_table_never_refuses_a_visible_window(self):
        helper = self.start(tracked=True)
        view, _ = self.hello13(helper, view='full')
        for number in range(shell.VIEW_JOURNAL_LIMIT):
            self.call(helper, view, 'open_app', f'u-{number}', app_id='fixture-unknown')
        self.assertEqual(self.call(helper, view, 'open_app', 'more', app_id='terminal')['error'], 'journal_full')
        self.assertEqual(self.ask(helper, view, 'no-window', app='terminal')['error'], 'journal_full')
        self.show(helper.windows, 30, BROWSER, active=True)
        helper.windows_changed()
        self.assertIsNone(self.ask(helper, view, 'restore'))
        helper.tick()
        self.assertEqual(next(m for m in view.sent if m['id'] == 'restore')['state'], 'activated')
        self.assertEqual(self.popen.call_count, 0)

    def test_capabilities_need_compositor_activation_even_with_window_tracking(self):
        helper = self.start(tracked=True)
        helper.activate_window = None
        desktop, reply = self.hello13(helper)
        view, view_reply = self.hello13(helper, view='without-activation')
        for response in (reply, view_reply):
            self.assertTrue(set(NEW).isdisjoint(response['capabilities']))
        self.assertEqual(self.ask(helper, desktop, 'desktop')['error'], 'unknown_operation')
        self.assertEqual(self.ask(helper, view, 'view')['error'], 'invalid_state')
        helper.tick()
        self.assertEqual(desktop.events('apps_state'), [])
        self.assertEqual(view.events('apps_state'), [])
        self.assertEqual(self.popen.call_count, 0)

    def test_restore_history_modal_confirmation_and_reconnect_after_window_disappears(self):
        helper = self.start(tracked=True)
        windows = helper.windows
        self.show(windows, 1, BROWSER, active=True)
        windows.state(1, False, minimized=True)
        windows.done(1)
        self.show(windows, 2, BROWSER)
        self.show(windows, 3, GAME, active=True)
        helper.windows_changed()
        conn, _ = self.hello13(helper)
        self.assertIsNone(self.send(helper, conn, example('activate-app-request')))
        self.assertEqual(self.activations, [1])
        helper.tick()
        self.assertEqual([m for m in conn.sent if m['id'] == 'restore-browser'], [])
        conn, _ = self.hello13(helper)
        self.assertIsNone(self.send(helper, conn, example('activate-app-request')))
        self.assertEqual(self.activations, [1])
        windows.state(3, False)
        windows.done(3)
        windows.state(1, False)
        windows.done(1)
        self.show(windows, 4, '', active=True, parent=1)
        helper.windows_changed()
        self.assertIn(example('activate-app-reply'), conn.sent)
        windows.gone(1)
        windows.gone(2)
        windows.gone(4)
        helper.windows_changed()
        before_replay = self.activations[:]
        conn, _ = self.hello13(helper)
        self.assertEqual(self.send(helper, conn, example('activate-app-request')), example('activate-app-reply'))
        self.assertEqual(self.activations, before_replay)
        self.assertEqual(self.popen.call_count, 0)

    def test_never_active_fallback_and_failed_or_stale_activation_never_spawn(self):
        for failure in ('activation_refused', 'stale', 'activation_timeout'):
            with self.subTest(failure=failure):
                Path(self.journal).unlink(missing_ok=True)
                self.activations.clear()
                helper = self.start(tracked=True)
                conn, _ = self.hello13(helper)
                windows = helper.windows
                self.show(windows, 30, BROWSER)
                self.show(windows, 20, BROWSER)
                helper.windows_changed()
                if failure == 'activation_refused':
                    helper.activate_window = mock.Mock(return_value=False)
                    reply = self.ask(helper, conn, 'restore')
                    helper.activate_window.assert_called_once_with(20)
                else:
                    self.assertIsNone(self.ask(helper, conn, 'restore'))
                    self.assertEqual(self.activations, [20])
                    if failure == 'stale':
                        windows.gone(20)
                        self.show(windows, 20, BROWSER, active=True)
                        helper.windows_changed()
                    else:
                        self.now[0] += shell.APP_ACTIVATION_TIMEOUT
                        helper.tick()
                    reply = next(m for m in conn.sent if m['id'] == 'restore')
                self.assertEqual(reply['error'], 'activation_refused' if failure == 'stale' else failure)
                windows.gone(30)
                windows.gone(20)
                helper.windows_changed()
                reconnected, _ = self.hello13(helper)
                self.assertEqual(self.ask(helper, reconnected, 'restore'), reply)
                self.assertEqual(self.popen.call_count, 0)

    def test_already_active_window_waits_for_the_compositor_round_trip(self):
        helper = self.start(tracked=True)
        conn, _ = self.hello13(helper)
        dispatched = threading.Event()
        helper.activation_barrier = lambda: dispatched.is_set
        self.show(helper.windows, 1, BROWSER, active=True)
        helper.windows_changed()
        self.assertIsNone(self.ask(helper, conn, 'restore'))
        helper.tick()
        self.assertFalse(any(m['id'] == 'restore' for m in conn.sent))
        dispatched.set()
        helper.tick()
        self.assertEqual(conn.sent[-1]['state'], 'activated')
        self.assertEqual(self.popen.call_count, 0)

    def test_joins_pending_and_started_launches_under_each_clients_own_id(self):
        helper = self.start(tracked=True)
        laptop = self.view(helper)
        desktop, _ = self.hello13(helper)
        view, _ = self.hello13(helper, view='new-view')
        check = types.SimpleNamespace(done=threading.Event(), result=(['/usr/bin/unused'], '~', None))
        with mock.patch.object(helper.checks, 'start', return_value=check) as checks:
            self.assertIsNone(self.call(helper, laptop, 'open_app', 'origin-only', app_id='browser'))
            self.assertIsNone(self.ask(helper, desktop, 'joined-check'))
            desktop, _ = self.hello13(helper)
            self.assertIsNone(self.ask(helper, desktop, 'joined-check'))
            checks.assert_called_once()
            check.done.set()
            helper.tick()
        self.assertEqual(self.popen.call_count, 1)
        origin = next(m for m in laptop.sent if m['id'] == 'origin-only')
        joined = next(m for m in desktop.sent if m['id'] == 'joined-check')
        joined_start = self.ask(helper, view, 'joined-start')
        for request_id, reply in (('joined-check', joined), ('joined-start', joined_start)):
            self.assertEqual((reply['id'], reply['request_id'], reply['state'], reply['launch_id']),
                             (request_id, request_id, 'starting', origin['launch_id']))
            self.assertNotIn('origin-only', json.dumps(reply))
        self.assertEqual(self.popen.call_count, 1)

        fresh = self.call(helper, desktop, 'open_app', 'new-window', app_id='browser')
        self.assertEqual(self.popen.call_count, 2)
        self.assertNotEqual(fresh['launch_id'], origin['launch_id'])
        self.show(helper.windows, 10, BROWSER, active=True)
        helper.windows_changed()
        for request_id, client in (('joined-check', desktop), ('joined-start', view), ('origin-only', laptop)):
            event = client.events('app_state')[-1]
            self.assertEqual((event['request_id'], event['state'], event['launch_id']),
                             (request_id, 'focused', origin['launch_id']))
        self.assertNotIn('origin-only', json.dumps(desktop.events('app_state')))
        view, _ = self.hello13(helper, view='new-view')
        self.assertEqual(self.ask(helper, view, 'joined-start')['state'], 'focused')
        self.assertEqual(self.activations, [])
        self.assertEqual(self.popen.call_count, 2)

    def test_desktop_join_can_start_when_the_view_live_cap_is_full(self):
        helper = self.start(tracked=True)
        filler, laptop = self.view(helper, 'filler'), self.view(helper)
        desktop, _ = self.hello13(helper)
        for number in range(shell.MAX_VIEW_LAUNCHES):
            reply = self.call(helper, filler, 'open_app', f'fill-{number}', app_id='terminal')
            self.assertEqual(reply.get('state'), 'starting', reply)
            self.active_units.add(self.launch_for(helper, filler.client, f'fill-{number}').entry['unit'])

        check = shell.LaunchCheck(from_view=True)
        with mock.patch.object(helper.checks, 'start', return_value=check) as checks, \
                mock.patch.object(shell, 'CHECK_WAIT', 0):
            self.assertIsNone(self.call(helper, laptop, 'open_app', 'view-open', app_id='browser'))
            self.assertIsNone(self.ask(helper, desktop, 'desktop-open', screen='world'))
            checks.assert_called_once()
            self.assertTrue(checks.call_args.kwargs['from_view'])
            check.result = (['/usr/bin/unused'], '~', None)
            check.done.set()
            helper.tick()

        view_reply = next(m for m in laptop.sent if m['id'] == 'view-open')
        desktop_reply = next(m for m in desktop.sent if m['id'] == 'desktop-open')
        self.assertEqual(view_reply.get('error'), 'journal_full')
        self.assertEqual((desktop_reply.get('request_id'), desktop_reply.get('state')), ('desktop-open', 'starting'))
        launch = self.launch_for(helper, shell.DESKTOP, 'desktop-open')
        self.assertEqual(launch.origin, (shell.DESKTOP, 'desktop-open'))
        self.assertEqual(launch.entry['screen'], 'world')
        self.assertEqual(self.popen.call_count, shell.MAX_VIEW_LAUNCHES + 1)
        self.show(helper.windows, 10, BROWSER, active=True)
        helper.windows_changed()
        event = desktop.events('app_state')[-1]
        self.assertEqual((event['request_id'], event['state'], event['launch_id']),
                         ('desktop-open', 'focused', desktop_reply['launch_id']))
        self.assertEqual(laptop.events('app_state'), [])

    def test_launch_fallback_keeps_screen_and_replays_when_a_window_appears(self):
        helper = self.start(tracked=True)
        conn, _ = self.hello13(helper)
        reply = self.ask(helper, conn, 'fallback', screen='world')
        self.assertEqual(reply['state'], 'starting')
        self.assertEqual(helper.journal.entries[shell.DESKTOP, 'fallback']['screen'], 'world')
        self.assertEqual(self.popen.call_count, 1)
        self.show(helper.windows, 10, BROWSER, active=True)
        helper.windows_changed()
        conn, _ = self.hello13(helper)
        duplicate = self.ask(helper, conn, 'fallback', screen='world')
        self.assertEqual((duplicate['state'], duplicate['launch_id']), ('focused', reply['launch_id']))
        self.assertEqual(self.activations, [])
        self.assertEqual(self.popen.call_count, 1)

    def test_a_window_queued_during_the_executable_check_is_restored_without_spawning(self):
        for deferred in (False, True):
            with self.subTest(deferred=deferred):
                Path(self.journal).unlink(missing_ok=True)
                self.activations.clear()
                helper = self.start(tracked=True)
                desktop, _ = self.hello13(helper)
                view, _ = self.hello13(helper, view='another-view')
                display, compositor = socket.socketpair()
                with display, compositor:
                    wayland = shell.ForeignToplevels(display, helper.windows)
                    wayland.manager = 50
                    wayland.kinds[50] = 'manager'
                    display.setblocking(False)
                    helper.drain_windows = wayland.drain
                    check = shell.LaunchCheck()

                    def complete_check():
                        compositor.sendall(wire_toplevel(30, BROWSER, active=True))
                        check.result = (['/usr/bin/unused'], '~', None)
                        check.done.set()

                    def wait_for_check(_):
                        if not deferred:
                            complete_check()
                        return check.done.is_set()

                    with mock.patch.object(helper.checks, 'start', return_value=check) as checks, \
                            mock.patch.object(check.done, 'wait', side_effect=wait_for_check):
                        self.assertIsNone(self.ask(helper, desktop, 'restore'))
                        if deferred:
                            self.assertIsNone(self.ask(helper, view, 'joined-restore'))
                            complete_check()
                        checks.assert_called_once()
                        helper.tick()
                self.assertEqual(self.activations, [30])
                replies = [(desktop, 'restore')]
                if deferred:
                    replies.append((view, 'joined-restore'))
                for conn, request_id in replies:
                    reply = next(m for m in conn.sent if m['id'] == request_id)
                    self.assertEqual(reply, dict(protocol=WIRE, id=request_id, ok=True, state='activated'))
                self.assertEqual(self.popen.call_count, 0)

    def test_fallback_recheck_joins_a_deliberate_open_that_started_during_the_check(self):
        helper = self.start(tracked=True)
        desktop, _ = self.hello13(helper)
        view, _ = self.hello13(helper, view='new-view')
        check = shell.LaunchCheck()
        with mock.patch.object(shell, 'CHECK_WAIT', 0), mock.patch.object(helper.checks, 'start', return_value=check):
            self.assertIsNone(self.ask(helper, desktop, 'restore'))
            check.result = (['/usr/bin/unused'], '~', None)
            check.done.set()
            deliberate = self.call(helper, view, 'open_app', 'new-window', app_id='browser')
            self.assertEqual(deliberate['state'], 'starting')
            helper.tick()
        reply = next(m for m in desktop.sent if m['id'] == 'restore')
        self.assertEqual((reply['request_id'], reply['state'], reply['launch_id']),
                         ('restore', 'starting', deliberate['launch_id']))
        self.assertEqual(self.popen.call_count, 1)

    def test_fallback_recheck_joins_a_deliberate_open_whose_reply_is_gone(self):
        helper = self.start(tracked=True)
        desktop, _ = self.hello13(helper)
        laptop = self.view(helper)
        check = shell.LaunchCheck()
        with mock.patch.object(shell, 'CHECK_WAIT', 0), mock.patch.object(helper.checks, 'start', return_value=check):
            self.assertIsNone(self.ask(helper, desktop, 'restore'))
            check.result = (['/usr/bin/unused'], '~', None)
            check.done.set()
            deliberate = self.call(helper, laptop, 'open_app', 'new-window', app_id='browser')
        self.assertEqual(deliberate['state'], 'starting')
        helper.disconnected(laptop)
        # RECHECK-1's sequence drops no reply any more.
        self.protect_view_histories(helper, 3)
        new_view = self.view(helper, 'new-view')
        self.assertEqual(self.call(helper, new_view, 'open_app', 'unknown', app_id='fixture-unknown')['error'],
                         'unknown_app')
        self.assertIn((laptop.client, 'new-window'), helper.journal.entries)
        # And the recheck reads the launch table: it holds even with the reply gone.
        del helper.journal.entries[laptop.client, 'new-window']
        self.assertIsNone(helper.activation_target('browser'))

        helper.tick()
        reply = next(m for m in desktop.sent if m['id'] == 'restore')
        self.assertEqual((reply['request_id'], reply['state'], reply['launch_id']),
                         ('restore', 'starting', deliberate['launch_id']))
        self.assertEqual(self.popen.call_count, 1)
        self.show(helper.windows, 30, BROWSER, active=True)
        helper.windows_changed()
        event = desktop.events('app_state')[-1]
        self.assertEqual((event['request_id'], event['state'], event['launch_id']),
                         ('restore', 'focused', deliberate['launch_id']))

    def protect_view_histories(self, helper, count):
        self.show(helper.windows, 20, NOTEPAD)
        helper.windows_changed()
        replies = []
        with mock.patch.object(helper, 'activate_window', return_value=False):
            for number in range(count):
                name = f'protected-{number}'
                view, _ = self.hello13(helper, view=name)
                reply = self.ask(helper, view, 'refused', app='notepad')
                self.assertEqual(reply['error'], 'activation_refused')
                replies.append((name, reply))
                helper.disconnected(view)
        helper.windows.gone(20)
        helper.windows_changed()
        return replies

    def test_laptop_can_open_with_four_protected_histories_and_refusals_still_replay(self):
        helper = self.start(tracked=True)
        replies = self.protect_view_histories(helper, 4)
        laptop = self.view(helper)
        # Other names' replies take no room from the laptop home, and none of them gives way to it.
        self.assertEqual(self.call(helper, laptop, 'open_app', 'new-window', app_id='browser')['state'], 'starting')
        self.assertEqual(len(helper.journal.view_clients), 5)
        self.assertIn('view:protected-0', helper.journal.view_clients)
        for current in (helper, self.start(tracked=True)):
            for name, original in replies:
                view, _ = self.hello13(current, view=name)
                self.assertEqual(self.ask(current, view, 'refused', app='notepad'), original)
                current.disconnected(view)
        self.assertEqual(self.popen.call_count, 1)

    def test_a_tray_resident_app_is_started_again_not_answered_closed(self):
        helper = self.start(tracked=True)
        desktop, _ = self.hello13(helper)
        first = self.call(helper, desktop, 'open_app', 'first', app_id=WEB.id)
        self.show(helper.windows, 2, WEB.app_ids[0], active=True)
        helper.windows_changed()
        helper.windows.gone(2)
        helper.windows_changed()
        self.now[0] += shell.HANDOFF + 0.01
        helper.tick()
        launch = helper.app_launches[WEB.id].running[first['launch_id']]
        self.assertEqual(launch.entry['state'], 'closed')
        self.assertIsNone(launch.process.poll())  # it stays in the tray
        again = self.ask(helper, desktop, 'bring-back', app=WEB.id)
        self.assertEqual(again['state'], 'starting')
        self.assertNotEqual(again['launch_id'], first['launch_id'])
        self.assertEqual(self.popen.call_count, 2)
        # While that second start waits for its window, another bring-back joins it.
        joined = self.ask(helper, desktop, 'again', app=WEB.id)
        self.assertEqual((joined['launch_id'], joined['state']), (again['launch_id'], 'starting'))
        self.assertEqual(self.popen.call_count, 2)

    def test_an_expired_start_is_not_joined_even_before_tick(self):
        helper = self.start(tracked=True)
        desktop, _ = self.hello13(helper)
        laptop = self.view(helper)
        opened = self.call(helper, laptop, 'open_app', 'slow-window', app_id='terminal')
        self.now[0] += shell.WINDOW_TIMEOUT + 1
        fresh = self.ask(helper, desktop, 'restore', app='terminal')
        self.assertEqual(fresh['state'], 'starting')
        self.assertNotEqual(fresh['launch_id'], opened['launch_id'])
        helper.tick()
        replay = self.call(helper, laptop, 'open_app', 'slow-window', app_id='terminal')
        self.assertEqual((replay['launch_id'], replay['error']), (opened['launch_id'], 'no_window'))
        self.assertEqual(self.popen.call_count, 2)

    def test_a_failed_laptop_launch_with_an_unknown_scope_is_not_joined(self):
        helper = self.start(tracked=True)
        laptop = self.view(helper)
        desktop, _ = self.hello13(helper)
        opened = self.call(helper, laptop, 'open_app', 'laptop-start', app_id='terminal')
        launch = self.launch_for(helper, laptop.client, 'laptop-start')
        launch.process.code = 1
        self.scope_answer = (1, '')
        helper.tick()
        self.assertEqual((launch.entry['state'], launch.scope), ('failed', shell.UNKNOWN))
        fresh = self.ask(helper, desktop, 'after-failure', app='terminal')
        self.assertEqual(fresh['state'], 'starting')
        self.assertNotEqual(fresh['launch_id'], opened['launch_id'])
        self.assertEqual(self.launch_for(helper, desktop.client, 'after-failure').origin[0], shell.DESKTOP)
        replay = self.call(helper, laptop, 'open_app', 'laptop-start', app_id='terminal')
        self.assertEqual((replay['launch_id'], replay['error']), (opened['launch_id'], 'launch_failed'))
        self.assertEqual(self.popen.call_count, 2)

    def test_a_cleanly_ended_launcher_is_not_a_join_target(self):
        helper = self.start(tracked=True)
        laptop = self.view(helper)
        desktop, _ = self.hello13(helper)
        opened = self.call(helper, laptop, 'open_app', 'handoff', app_id='browser')
        launch = self.launch_for(helper, laptop.client, 'handoff')
        self.active_units.add(launch.entry['unit'])
        launch.process.code = 0
        helper.tick()
        self.scope_pass(helper)
        # The original reply can still follow a handoff window, but its launcher has exited.
        self.assertEqual((launch.entry['state'], launch.scope), ('starting', shell.ACTIVE))
        fresh = self.ask(helper, desktop, 'fresh')
        self.assertEqual(fresh['state'], 'starting')
        self.assertNotEqual(fresh['launch_id'], opened['launch_id'])
        self.assertEqual(self.popen.call_count, 2)

    def test_a_scope_registering_after_reconcile_counts_on_the_next_admission(self):
        helper = self.start(tracked=True)
        laptop, _ = self.hello13(helper, view='laptop')
        opened = self.call(helper, laptop, 'open_app', 'interrupted', app_id='terminal')
        unit = self.launch_for(helper, laptop.client, 'interrupted').entry['unit']
        self.assertEqual(self.ask(helper, laptop, 'joined', app='terminal')['launch_id'], opened['launch_id'])
        self.active_units = {f'app-aresos-unmapped-{n}.scope' for n in range(shell.MAX_VIEW_LAUNCHES - 1)}
        self.active_units.add('unrelated-active.scope')

        restarted = self.start(tracked=True)
        laptop, _ = self.hello13(restarted, view='laptop')
        desktop, _ = self.hello13(restarted)
        self.assertEqual(restarted.journal.scope_owners[unit], 'view')
        self.assertNotIn(unit, restarted.watched_units())
        for request_id in ('interrupted', 'joined'):
            replay = self.ask(restarted, laptop, request_id, app='terminal')
            self.assertEqual((replay['state'], replay['error'], replay['launch_id']),
                             ('failed', 'launch_uncertain', opened['launch_id']))
        fresh = self.ask(restarted, desktop, 'fresh', app='terminal')
        self.assertEqual(fresh['state'], 'starting')
        self.assertNotEqual(fresh['launch_id'], opened['launch_id'])
        self.active_units.add(self.launch_for(restarted, desktop.client, 'fresh').entry['unit'])

        # The new listing sees the late unit even though there is no launch tracker to poll.
        self.active_units.add(unit)
        refusal = self.call(restarted, laptop, 'open_app', 'next', app_id='notepad')
        self.assertEqual(refusal.get('error'), 'journal_full', refusal)
        self.assertEqual(self.popen.call_count, 2)
        self.active_units.remove(unit)
        reply = self.call(restarted, laptop, 'open_app', 'next', app_id='notepad')
        self.assertEqual(reply.get('state'), 'starting', reply)
        self.assertEqual(self.popen.call_count, 3)

    def churn_view_history(self, helper):
        for number in range(shell.MAX_VIEWS):
            view = self.view(helper, f'temporary-{number}')
            reply = self.call(helper, view, 'open_app', f'unknown-{number}', app_id='fixture-unknown')
            self.assertEqual(reply['error'], 'unknown_app')
            helper.disconnected(view)

    def test_a_resent_deliberate_open_never_starts_a_second_instance(self):
        helper = self.start(tracked=True)
        origin = self.view(helper, 'origin')
        first = self.call(helper, origin, 'open_app', 'same', app_id='terminal')
        self.assertEqual(first['state'], 'starting')
        helper.disconnected(origin)
        # RECHECK-2's sequence: four more view names record requests, then the first reconnects and resends.
        self.churn_view_history(helper)
        for reconnect in (lambda: self.view(helper, 'origin'), lambda: self.hello13(helper, view='origin')[0]):
            origin = reconnect()
            again = self.call(helper, origin, 'open_app', 'same', app_id='terminal')
            self.assertEqual((again['launch_id'], again['state']), (first['launch_id'], 'starting'))
        # Whatever the journal holds: with the reply gone, the live launch still answers for its ID.
        del helper.journal.entries['view:origin', 'same']
        helper.save_launches()
        self.active_units = {launch.entry['unit'] for launch in helper.launch_entries()}
        for current in (helper, self.start(tracked=True)):
            origin = self.view(current, 'origin')
            again = self.call(current, origin, 'open_app', 'same', app_id='terminal')
            self.assertEqual((again['launch_id'], again['state']), (first['launch_id'], 'starting'))
            self.assertEqual(self.call(current, origin, 'open_app', 'same', app_id='notepad')['error'],
                             'request_id_reused')
        self.assertEqual(self.popen.call_count, 1)

    def test_view_history_churn_preserves_a_join_until_its_outcome(self):
        helper = self.start(tracked=True)
        laptop = self.view(helper)
        desktop, _ = self.hello13(helper)
        origin = self.call(helper, laptop, 'open_app', 'origin', app_id='browser')
        joined = self.ask(helper, desktop, 'joined')
        self.assertEqual(joined['launch_id'], origin['launch_id'])
        helper.disconnected(laptop)
        self.churn_view_history(helper)
        self.assertIn((laptop.client, 'origin'), helper.journal.entries)
        self.show(helper.windows, 30, BROWSER, active=True)
        helper.windows_changed()
        event = desktop.events('app_state')[-1]
        self.assertEqual((event['request_id'], event['state']), ('joined', 'focused'))
        self.assertEqual(self.popen.call_count, 1)

    def test_refused_activation_replays_after_view_churn_and_window_close(self):
        helper = self.start(tracked=True)
        original, _ = self.hello13(helper, view='original-view')
        self.show(helper.windows, 30, BROWSER)
        helper.windows_changed()
        helper.activate_window = mock.Mock(return_value=False)
        refused = self.ask(helper, original, 'refused')
        self.assertEqual(refused['error'], 'activation_refused')
        helper.activate_window.assert_called_once_with(30)
        helper.disconnected(original)
        self.churn_view_history(helper)
        helper.windows.gone(30)
        helper.windows_changed()
        for current in (helper, self.start(tracked=True)):
            reconnected, _ = self.hello13(current, view='original-view')
            self.assertEqual(self.ask(current, reconnected, 'refused'), refused)
        self.assertEqual(self.popen.call_count, 0)

    def test_unjoined_fallback_launch_remains_starting_after_view_churn(self):
        helper = self.start(tracked=True)
        original, _ = self.hello13(helper, view='original-view')
        starting = self.ask(helper, original, 'fallback')
        self.assertEqual(starting['state'], 'starting')
        helper.disconnected(original)
        self.churn_view_history(helper)
        reconnected, _ = self.hello13(helper, view='original-view')
        self.assertEqual(self.ask(helper, reconnected, 'fallback'), starting)
        self.assertEqual(self.popen.call_count, 1)


class LoggingTest(ViewBase):
    def capture_log(self, state):
        log = shell.LOG
        stderr = io.StringIO()
        stderr_handler = logging.StreamHandler(stderr)
        previous = log.handlers[:]
        previous_level, disabled, propagate = log.level, log.disabled, log.propagate
        log.handlers[:] = [stderr_handler]
        log.setLevel(logging.INFO)
        log.propagate = log.disabled = False

        def restore():
            for handler in log.handlers[:]:
                handler.close()
            log.handlers[:] = previous
            log.setLevel(previous_level)
            log.disabled, log.propagate = disabled, propagate

        self.addCleanup(restore)
        shell.configure_log({'XDG_STATE_HOME': str(state)})
        return stderr

    def test_credentials_request_fields_spawn_errors_and_rollover(self):
        state = Path(self.folder.name) / 'state'
        stderr = self.capture_log(state)
        path = state / 'aresos/shell.log'
        persistent = next(handler for handler in shell.LOG.handlers if isinstance(handler, shell.ShellLog))
        self.assertEqual(persistent.maxBytes, 512 * 1024)
        persistent.maxBytes = 1024
        # Roll over one known record, and leave the diagnostic cases together in the new log.
        for _ in range(12):
            shell.LOG.info('synthetic filler for rotation %s', 'x' * 100)

        helper = self.start(tracked=True)
        wrong_token = 'credential-sentinel-' + 'W' * 23
        wrong_nonce = 'wrong-desktop-sentinel'
        field = 'private-request-text'
        exception = 'private-spawn-argv and private-environment-text'
        bad = Conn()
        helper.connected(bad)
        reply = self.call(helper, bad, 'hello', major=1, minor=2, role='view', view='laptop-home',
                          instance=INSTANCE, token=wrong_token)
        self.assertEqual(reply['error'], 'not_authorized')
        bad = Conn()
        helper.connected(bad)
        reply = self.call(helper, bad, 'hello', major=1, minor=2, instance=INSTANCE, nonce=wrong_nonce)
        self.assertEqual(reply['error'], 'not_authorized')
        desktop = self.desktop(helper)
        self.call(helper, desktop, 'open_app', 'unknown', app_id=field)
        self.popen.side_effect = OSError(errno.ENOENT, exception, exception)
        self.call(helper, desktop, 'open_app', 'spawn-error', app_id='browser')
        try:
            self.unexpected(exception)
        except RuntimeError:
            shell.log_unexpected('fixture encountered an unexpected error')
        backup = path.with_suffix('.log.1')
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        combined = path.read_text() + backup.read_text() + stderr.getvalue()
        for text in (wrong_token, wrong_nonce, NONCE, field, exception):
            self.assertNotIn(text, combined)
        self.assertIn(f'unknown app ID ({len(field)} characters)', combined)
        self.assertIn('could not start browser (FileNotFoundError, errno 2)', combined)
        self.assertRegex(combined, r'RuntimeError at aresos-shell:\d+')

    @staticmethod
    def unexpected(text):
        class InvalidVersion:
            def __format__(self, _):
                raise RuntimeError(text)
        shell.protocol(InvalidVersion())

    def test_log_open_failure_and_rotation_failure_keep_stderr(self):
        state = Path(self.folder.name) / 'state'
        stderr = self.capture_log(state)
        log = state / 'aresos/shell.log'
        backup = log.with_suffix('.log.1')
        sentinel = state / 'untouched'
        sentinel.write_text('private contents')
        shell.LOG.info('seed the log before rotation')
        backup.symlink_to(sentinel)
        handler = next(handler for handler in shell.LOG.handlers if isinstance(handler, shell.ShellLog))
        handler.maxBytes = 1
        shell.LOG.warning('record before a refused rotation')
        self.assertIn('could not write or rotate shell.log', stderr.getvalue())
        self.assertIn('record before a refused rotation', stderr.getvalue())
        self.assertEqual(sentinel.read_text(), 'private contents')
        self.assertNotIn(handler, shell.LOG.handlers)
        shell.configure_log({'XDG_STATE_HOME': str(sentinel)})
        shell.LOG.warning('still serving after the unwritable log')
        self.assertIn('could not open shell.log', stderr.getvalue())
        self.assertIn('still serving after the unwritable log', stderr.getvalue())

    def test_log_detaches_before_cleanup_when_flush_and_close_fail(self):
        stderr = self.capture_log(Path(self.folder.name) / 'state')
        handler = next(handler for handler in shell.LOG.handlers if isinstance(handler, shell.ShellLog))
        handler.stream.close()
        handler.maxBytes = 0
        stream = mock.Mock()
        stream.flush.side_effect = OSError(errno.ENOSPC, 'synthetic flush failure')
        attached_at_close = []

        def close():
            attached_at_close.append(handler in shell.LOG.handlers)
            raise OSError(errno.EIO, 'synthetic close failure')

        stream.close.side_effect = close
        handler.stream = stream
        shell.LOG.warning('record whose file flush fails')
        shell.LOG.warning('record after the file handler detached')
        self.assertNotIn(handler, shell.LOG.handlers)
        self.assertIsNone(handler.stream)
        self.assertEqual(stream.flush.call_count, 2)
        stream.close.assert_called_once_with()
        self.assertEqual(attached_at_close, [False])
        self.assertIn('record whose file flush fails', stderr.getvalue())
        self.assertIn(f'could not write or rotate shell.log (OSError, errno {errno.ENOSPC})', stderr.getvalue())
        self.assertIn('record after the file handler detached', stderr.getvalue())
