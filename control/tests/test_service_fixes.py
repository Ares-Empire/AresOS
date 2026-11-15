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
