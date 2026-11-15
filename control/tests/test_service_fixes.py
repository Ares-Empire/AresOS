"""Brief 18e: the client's start-up gap (item 1) and the admin hint (item 2)."""
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aresos_control import cli, protocol
from aresos_control.common import Refused
from aresos_control.protocol import Client, ServiceUnavailable, receive, send
from aresos_control.proxy import Proxy

READ = {'method': 'call', 'action': 'testapp_list', 'arguments': {'limit': 3}}
CHANGE = {'method': 'call', 'action': 'testapp_send', 'arguments': {'operation_id': 'op-1'}}


class FakeService(threading.Thread):
    """Listens at `path` after `delay` seconds, answers one request (or drops it after reading it)."""
    def __init__(self, path, delay, drop=False):
        super().__init__(daemon=True)
        self.path, self.delay, self.drop, self.requests = path, delay, drop, []

    def run(self):
        time.sleep(self.delay)
        if os.path.lexists(self.path):
            os.unlink(self.path)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(self.path)
            listener.listen(1)
            connection, _ = listener.accept()
            with connection:
                self.requests.append(receive(connection))
                if not self.drop:
                    send(connection, {'ok': True, 'data': {'items': []}, 'pending': {}}, result=True)


class ConnectGap(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, 'act.sock')

    def test_a_socket_that_appears_within_the_wait_is_used(self):
        service = FakeService(self.path, 0.5)
        service.start()
        self.assertEqual(Client(self.path).request(READ)['ok'], True)
        service.join(5)
        self.assertEqual(service.requests[0]['action'], 'testapp_list')

    def test_a_stale_socket_file_refusing_connections_is_waited_for_too(self):
        # A stopped service leaves its socket file: connect answers ECONNREFUSED until the new one listens.
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stale:
            stale.bind(self.path)
        service = FakeService(self.path, 0.5)
        service.start()
        self.assertEqual(Client(self.path).request(CHANGE)['ok'], True)
        service.join(5)
        self.assertEqual(len(service.requests), 1)

    def test_a_socket_that_never_appears_says_nothing_was_sent(self):
        for request in (READ, CHANGE, {'method': 'upload', 'app': 'testapp', 'file': {'sha256': 'x'}}):
            with self.subTest(request=request), patch.object(protocol, 'CONNECT_WAIT', 0.4):
                started = time.monotonic()
                with self.assertRaises(ServiceUnavailable) as caught:
                    if request['method'] == 'upload':
                        Client(self.path).upload('testapp', request['file'], b'')
                    else:
                        Client(self.path).request(request)
                self.assertGreaterEqual(time.monotonic() - started, 0.4)
                self.assertEqual(caught.exception.code, 'service_unavailable')
                message = str(caught.exception)
                self.assertIn('not running', message)
                self.assertIn('nothing was sent', message)
                self.assertNotIn('operation_status', message)

    def test_the_default_wait_is_three_seconds(self):
        self.assertEqual(protocol.CONNECT_WAIT, 3.0)
        with patch.object(protocol.time, 'sleep') as sleep, \
                patch.object(protocol.time, 'monotonic', side_effect=[0.0] + [x / 10 for x in range(1, 40)]):
            with self.assertRaises(ServiceUnavailable):
                Client(self.path).request(READ)
        self.assertEqual(sleep.call_count, 29)
        self.assertTrue(all(call.args == (protocol.CONNECT_STEP,) for call in sleep.call_args_list))

    def test_other_connect_errors_are_not_retried_and_still_say_nothing_was_sent(self):
        Path(self.folder.name, 'file').write_text('')
        started = time.monotonic()
        with self.assertRaises(ServiceUnavailable) as caught:
            Client(os.path.join(self.folder.name, 'file', 'act.sock')).request(READ)
        self.assertLess(time.monotonic() - started, 1)
        self.assertIn('could not be reached', str(caught.exception))
        self.assertIn('nothing was sent', str(caught.exception))

    def test_a_connection_lost_after_sending_keeps_the_unknown_outcome(self):
        service = FakeService(self.path, 0, drop=True)
        service.start()
        time.sleep(0.2)
        result = Client(self.path).request(CHANGE)
        self.assertEqual(result['error']['code'], 'unknown')
        self.assertEqual(result['data']['request']['operation_id'], 'op-1')
        service.join(5)
        service = FakeService(self.path, 0, drop=True)
        service.start()
        time.sleep(0.2)
        with self.assertRaises(Refused) as caught:
            Client(self.path).request(READ)
        self.assertEqual(caught.exception.code, 'transport_error')
        self.assertIn('operation_status', str(caught.exception))

    def test_proxy_reports_the_service_down_without_waiting_twice(self):
        config = {'act_socket': self.path, 'admin_socket': self.path + '.admin'}
        with patch.object(protocol, 'CONNECT_WAIT', 0.4):
            started = time.monotonic()
            result = Proxy('testapp', config).call('list', {'limit': 3})
        self.assertLess(time.monotonic() - started, 0.8)
        self.assertEqual(result['ok'], False)
        self.assertEqual(result['error']['code'], 'service_unavailable')
        self.assertNotIn('operation_status', result['error']['message'])


class AdminWithoutSudo(unittest.TestCase):
    def run_cli(self, words, euid):
        output = io.StringIO()
        with patch.object(cli.os, 'geteuid', return_value=euid), patch.object(cli, 'Proxy') as proxy, \
                patch('getpass.getpass') as password, patch('sys.stdin.isatty', return_value=True), \
                patch.object(protocol.socket, 'socket') as sockets, redirect_stdout(output):
            proxy.return_value.call.return_value = {'ok': True, 'data': {}, 'pending': {}}
            code = cli.main({'act_socket': '/nonexistent/act', 'admin_socket': '/nonexistent/admin'}, words)
        return code, output.getvalue(), proxy, password, sockets

    def test_admin_as_owner_says_sudo_without_socket_or_password(self):
        for words in (['admin', 'mail', 'account', 'add', '--input', '{"id":"a"}'], ['admin', 'control', 'restore_confirm'],
                      ['admin', 'chrome', 'allowed']):
            with self.subTest(words=words):
                code, output, proxy, password, sockets = self.run_cli(words, 1000)
                self.assertEqual(code, 1)
                result = json.loads(output)
                self.assertEqual(result['error']['code'], 'permission_denied')
                self.assertIn('Admin commands need sudo: run sudo aresos admin ' + ' '.join(
                    w for w in words[1:] if not w.startswith('-') and not w.startswith('{')), result['error']['message'])
                proxy.assert_not_called()
                password.assert_not_called()
                sockets.assert_not_called()

    def test_admin_as_root_still_reaches_the_admin_path(self):
        code, output, proxy, password, sockets = self.run_cli(['admin', 'control', 'restore_confirm'], 0)
        proxy.assert_called_once()
        self.assertTrue(proxy.call_args.args[2])


if __name__ == '__main__':
    unittest.main()


class IdleLoop(unittest.TestCase):
    """Brief 18e, item 3: the service sleeps until its next real deadline."""
    def setUp(self):
        from aresos_control.daemon import Daemon
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        for name in ('state', 'independent', 'sockets'):
            (root / name).mkdir()
        self.daemon = Daemon({'owner_uid': os.geteuid() + 1, 'state_dir': str(root / 'state'),
                              'evidence_dir': str(root / 'independent'), 'socket_dir': str(root / 'sockets'), 'approval_ttl': 0.4})
        self.addCleanup(self.daemon.close)
        self.engine = self.daemon.engine
        patcher = patch.object(self.engine.boundary, 'require')
        patcher.start()
        self.addCleanup(patcher.stop)

    def reserve(self):
        from support import message
        result = self.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_prepare_send', 'arguments': message()})
        self.assertTrue(result['ok'], result)
        return result['data']['approval']

    def passes(self, count, sleep=False, check=lambda: None):
        """Run serve() for `count` selects; record each timeout (and `check()`), optionally sleeping it."""
        timeouts, self.checked = [], []
        def select(timeout):
            timeouts.append(timeout)
            self.checked.append(check())
            if sleep:
                # Like a real select whose deadline arrives; the long idle sleep is only recorded.
                time.sleep(min(timeout, 1))
            if len(timeouts) >= count:
                self.daemon.stopping = True
            return []
        self.daemon.selector.select = select
        self.daemon.stopping = False
        self.daemon.serve()
        return timeouts

    def test_next_deadline_is_none_idle_and_the_earliest_open_reservation_otherwise(self):
        from aresos_control import engine as engine_module
        self.assertIsNone(self.engine.next_deadline())
        first = self.reserve()
        operation = self.engine.store.operation(first['operation_id']) if hasattr(self.engine.store, 'operation') else None
        deadline = self.engine.next_deadline()
        self.assertAlmostEqual(deadline, time.time() + 0.4, delta=0.2)
        if operation:
            self.assertEqual(deadline, operation['expires'])
        time.sleep(0.5)
        self.engine.expire()
        self.assertIsNone(self.engine.next_deadline())
        self.engine.store.deferred_notices['n'] = ({}, 'control_maintenance', 'synthetic')
        self.assertAlmostEqual(self.engine.next_deadline(), time.time() + engine_module.NOTICE_RETRY, delta=0.2)

    def test_idle_sleeps_until_maintenance(self):
        timeouts = self.passes(3)
        for timeout in timeouts:
            self.assertGreater(timeout, 59)
            self.assertLessEqual(timeout, 60)

    def test_a_pending_expiry_is_met_on_time(self):
        approval = self.reserve()
        started = time.monotonic()
        def state():
            status = self.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_operation_status',
                                          'arguments': {'operation_id': approval['operation_id']}})
            return status['data']['operation']['state'], time.monotonic() - started
        timeouts = self.passes(2, sleep=True, check=state)
        # The first select sleeps until the expiry, not 0.1 s; the pass after it expires the reservation.
        self.assertGreater(timeouts[0], 0.3)
        self.assertLessEqual(timeouts[0], 0.41)
        self.assertGreater(timeouts[1], 59)
        self.assertEqual(self.checked[0][0], 'reserved')
        self.assertEqual(self.checked[1][0], 'failed')
        self.assertLess(self.checked[1][1], 0.6)

    def test_a_waiting_confirmation_is_polled_and_its_answer_handled(self):
        chrome = self.engine.adapters['chrome']
        answers = iter([None, None, (False, 'synthetic no')])
        polled = []
        ask = SimpleNamespace(outcome=lambda: polled.append(1) or next(answers), cancel=lambda: None)
        chrome.confirmation = {'request_id': 'r', 'arguments': {}, 'change': 'x', 'ask': ask,
                               'connection': chrome.bridge.connection_identity}
        with patch.object(chrome, 'owner_reply') as reply:
            timeouts = self.passes(4)
        # Polled before each select: two waiting answers, then the no; then back to the idle sleep.
        self.assertEqual(timeouts[:2], [0.1, 0.1])
        self.assertGreater(min(timeouts[2:]), 59)
        self.assertEqual(len(polled), 3)
        self.assertIsNone(chrome.confirmation)
        reply.assert_called_once()

    def test_stop_ends_a_sleeping_loop_at_once(self):
        # SIGTERM's handler calls stop(); Python restarts the select after a handler, so stop() must wake it.
        thread = threading.Thread(target=self.daemon.serve, daemon=True)
        thread.start()
        time.sleep(0.3)
        self.assertTrue(thread.is_alive())
        started = time.monotonic()
        self.daemon.stop()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertLess(time.monotonic() - started, 1)

    def test_an_unreadable_deadline_wakes_within_a_second(self):
        with patch.object(self.engine, 'next_deadline', side_effect=OSError('synthetic')):
            self.assertEqual(self.passes(1), [1.0])


class QuietUnlessUsed(unittest.TestCase):
    """Brief 18e, item 6, with fake /proc trees and marks."""
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.proc, self.run_dir, self.uid = self.root / 'proc', self.root / 'run', os.getuid()
        (self.run_dir / str(self.uid)).mkdir(parents=True, mode=0o700)
        # hook 40 <- sh 35 <- claude 20 <- tmux 10 <- init 1
        for pid, ppid, start, comm in ((40, 35, 900, 'python3'), (35, 20, 899, 'sh'), (20, 10, 500, 'claude (x)'),
                                       (10, 1, 100, 'tmux: server'), (1, 0, 1, 'systemd')):
            self.process(pid, ppid, start, comm)

    def process(self, pid, ppid, start, comm):
        (self.proc / str(pid)).mkdir(parents=True, exist_ok=True)
        (self.proc / str(pid) / 'stat').write_text(f'{pid} ({comm}) S {ppid} ' + '0 ' * 17 + f'{start} 0 0\n')

    def used(self, pid=35):
        from aresos_control import usage
        return usage.used(pid=pid, uid=self.uid, run=self.run_dir, proc=self.proc)

    def mark(self, pid=20):
        from aresos_control import usage
        usage.mark(pid=pid, uid=self.uid, run=self.run_dir, proc=self.proc)

    def marks(self):
        return self.run_dir / str(self.uid) / 'aresos-control' / 'used'

    def test_a_marked_session_is_found_through_the_hook_ancestors(self):
        self.assertFalse(self.used())
        self.mark()
        self.assertEqual(sorted(p.name for p in self.marks().iterdir()), ['20-500'])
        self.assertEqual(self.marks().stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.marks().parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.marks() / '20-500').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.marks() / '20-500').read_bytes(), b'')
        self.assertTrue(self.used())
        self.mark()  # marking again is harmless
        self.assertTrue(self.used())

    def test_unmarked_sessions_stay_quiet(self):
        self.assertFalse(self.used())  # no folder at all
        self.mark(pid=10)  # another process's mark ...
        self.assertTrue(self.used())  # ... is an ancestor here (level 3), so make a separate tree:
        self.process(60, 55, 3, 'python3')
        self.process(55, 50, 2, 'sh')
        self.process(50, 1, 1, 'claude')
        self.assertFalse(self.used(pid=55))

    def test_a_reused_pid_with_another_start_time_has_no_mark(self):
        self.mark()
        self.process(20, 10, 777, 'claude')  # pid 20 ended; a new process got its number
        self.assertFalse(self.used())

    def test_four_levels_and_never_pid_1(self):
        self.mark(pid=1)
        self.assertFalse(self.used())
        chain = [(70 + level, 71 + level) for level in range(5)]  # 70 <- 71 <- ... <- 75 (claude)
        for pid, ppid in chain:
            self.process(pid, ppid, pid, 'p')
        self.process(75, 1, 75, 'claude')
        self.mark(pid=75)
        self.assertFalse(self.used(pid=70))  # from a hook whose parent is 70, process 75 is level 6: too far
        self.assertTrue(self.used(pid=72))

    def test_unreadable_marks_or_processes_count_as_marked(self):
        self.mark(pid=10)
        self.process(60, 55, 3, 'python3')
        (self.proc / '55').mkdir()
        self.assertTrue(self.used(pid=55))  # no stat for the parent
        self.marks().chmod(0o755)
        self.assertTrue(self.used())  # not a private folder
        self.marks().chmod(0o700)
        (self.marks() / '35-899').mkdir()
        self.assertTrue(self.used())  # a folder where a mark should be

    def test_a_link_where_the_folder_should_be_is_never_followed(self):
        from aresos_control import usage
        elsewhere = self.root / 'elsewhere'
        elsewhere.mkdir(mode=0o700)
        (self.run_dir / str(self.uid) / 'aresos-control').symlink_to(elsewhere)
        with self.assertRaises(OSError):
            self.mark()
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.assertTrue(self.used())  # can't read: as if marked
        (self.run_dir / str(self.uid) / 'aresos-control').unlink()
        (self.run_dir / str(self.uid) / 'aresos-control').mkdir(mode=0o700)
        (self.run_dir / str(self.uid) / 'aresos-control' / 'used').symlink_to(elsewhere)
        with self.assertRaises(OSError):
            self.mark()
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.assertTrue(self.used())

    def test_what_names_an_operation(self):
        from aresos_control.usage import names_operation
        approval = {'ok': True, 'data': {'approval': {'operation_id': 'op', 'question': 'Send?'}}, 'pending': {}}
        self.assertTrue(names_operation('change', approval))
        self.assertTrue(names_operation('send', {'ok': True, 'data': {'items': [{'operation_id': 'op'}]}}))
        self.assertTrue(names_operation('send', {'ok': False, 'error': {'code': 'unknown'}, 'data': {'state': 'unknown'}}))
        self.assertFalse(names_operation('read', approval))  # plain reads never count
        busy = {'ok': True, 'data': {'items': []}, 'pending': {'items': [{'operation_id': 'other'}], 'total': 1}}
        self.assertFalse(names_operation('change', busy))  # another session's pending work isn't this one's
        self.assertFalse(names_operation('change', {'ok': False, 'error': {'code': 'service_unavailable'}, 'pending': {}}))

    def test_the_proxy_marks_before_returning_and_never_fails_the_call(self):
        from aresos_control import proxy
        approval = {'ok': True, 'data': {'approval': {'operation_id': 'op'}}, 'pending': {}}
        with patch.object(proxy.usage, 'mark') as mark:
            proxy.note_use('testapp', 'prepare_send', approval)
            proxy.note_use('testapp', 'list', {'ok': True, 'data': {'items': [{'operation_id': 'x'}]}})
            proxy.note_use('testapp', 'no_such_tool', approval)
        mark.assert_called_once_with()
        with patch.object(proxy.usage, 'mark', side_effect=OSError('synthetic')):
            proxy.note_use('testapp', 'prepare_send', approval)

    def stop(self, error, marked, event=None, name='Stop'):
        from aresos_control import hooks
        event = event or {'hook_event_name': name, 'session_id': 's', 'prompt_id': 'p'}
        output = io.StringIO()
        with patch.object(hooks, 'Client') as client, patch.object(hooks.usage, 'used', return_value=marked) as used, \
                patch('sys.stdin', io.TextIOWrapper(io.BytesIO(json.dumps(event).encode()))), redirect_stdout(output):
            client.return_value.call.side_effect = error
            hooks.main({'act_socket': '/nonexistent'}, name)
        return output.getvalue(), used

    def test_stop_hook_is_quiet_unless_used(self):
        for error in (ServiceUnavailable(FileNotFoundError(2, 'No such file')),
                      Refused('transport_error', 'Service connection lost; inspect operation_status with the same id, never repeat with a new id.')):
            with self.subTest(code=error.code):
                printed, _ = self.stop(error, marked=False)
                self.assertEqual(printed, '')
                printed, _ = self.stop(error, marked=True)
                decision = json.loads(printed)
                self.assertEqual(decision['decision'], 'block')
                self.assertTrue(decision['reason'].startswith('AresOS tools are not running.'))
                self.assertIn("don't repeat it", decision['reason'])
                self.assertNotIn('operation_status', decision['reason'])
                printed, used = self.stop(error, marked=True, event={'hook_event_name': 'Stop', 'stop_hook_active': True})
                self.assertEqual(printed, '')
                printed, used = self.stop(error, marked=True, name='UserPromptSubmit')
                self.assertEqual(printed, '')
                used.assert_not_called()

    def test_stop_hook_with_the_service_up_is_unchanged(self):
        from aresos_control import hooks
        pending = {'items': [{'operation_id': 'op'}], 'total': 1}
        output = io.StringIO()
        with patch.object(hooks, 'Client') as client, patch.object(hooks.usage, 'used') as used, \
                patch('sys.stdin', io.TextIOWrapper(io.BytesIO(b'{"hook_event_name":"Stop"}'))), redirect_stdout(output):
            client.return_value.call.return_value = {'ok': True, 'data': pending}
            hooks.main({'act_socket': '/nonexistent'}, 'Stop')
        self.assertEqual(json.loads(output.getvalue())['decision'], 'block')
        self.assertIn('held/unfinished work', json.loads(output.getvalue())['reason'])
        used.assert_not_called()
