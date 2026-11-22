"""Package 333 window state, replay, and private diagnostic logs."""
import errno
import io
import json
import logging
from pathlib import Path
import stat
import threading
import types
from unittest import mock

from test_aresos_shell import ALL, Conn, INSTANCE, NONCE, ROOT, shell
from test_aresos_shell_views import GAME, NOTEPAD, TOKEN, ViewBase

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

    def test_view_history_churn_preserves_a_join_until_its_outcome(self):
        helper = self.start(tracked=True)
        laptop = self.view(helper)
        desktop, _ = self.hello13(helper)
        origin = self.call(helper, laptop, 'open_app', 'origin', app_id='browser')
        joined = self.ask(helper, desktop, 'joined')
        self.assertEqual(joined['launch_id'], origin['launch_id'])
        helper.disconnected(laptop)
        for number in range(shell.MAX_VIEWS):
            view = self.view(helper, f'temporary-{number}')
            self.call(helper, view, 'open_app', 'unknown', app_id='fixture-unknown')
            helper.disconnected(view)
        self.assertIn((laptop.client, 'origin'), helper.journal.entries)
        self.show(helper.windows, 30, BROWSER, active=True)
        helper.windows_changed()
        event = desktop.events('app_state')[-1]
        self.assertEqual((event['request_id'], event['state']), ('joined', 'focused'))
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
