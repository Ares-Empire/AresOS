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

    def test_an_unreadable_deadline_wakes_within_a_second(self):
        with patch.object(self.engine, 'next_deadline', side_effect=OSError('synthetic')):
            self.assertEqual(self.passes(1), [1.0])
