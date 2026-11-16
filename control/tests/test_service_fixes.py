"""Brief 18e: the client's start-up gap (item 1) and the admin hint (item 2)."""
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aresos_control import cli, protocol
from aresos_control.common import Refused
from aresos_control.definitions import BY_NAME, tools_for
from aresos_control.protocol import Client, NotConnected, receive, send
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
                with self.assertRaises(NotConnected) as caught:
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
            with self.assertRaises(NotConnected):
                Client(self.path).request(READ)
        self.assertEqual(sleep.call_count, 29)
        self.assertTrue(all(call.args == (protocol.CONNECT_STEP,) for call in sleep.call_args_list))

    def test_a_broken_setup_is_not_retried_and_says_so_without_try_again(self):
        # Review 1 #5: only "not listening" means not running; a permission, a path through a file or a link loop is a
        # setup that waiting won't mend.
        root = Path(self.folder.name)
        (root / 'file').write_text('')
        (root / 'loop').symlink_to(root / 'loop')
        (root / 'closed').mkdir()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(root / 'closed' / 'act.sock'))
            listener.listen(1)
            (root / 'closed').chmod(0)
            self.addCleanup((root / 'closed').chmod, 0o700)
            paths = {'ENOTDIR': root / 'file' / 'act.sock', 'ELOOP': root / 'loop'}
            if os.geteuid() != 0:  # root passes any folder permission
                paths['EACCES'] = root / 'closed' / 'act.sock'
            for name, path in paths.items():
                with self.subTest(error=name):
                    started = time.monotonic()
                    with self.assertRaises(NotConnected) as caught:
                        Client(str(path)).request(READ)
                    self.assertLess(time.monotonic() - started, 1)
                    self.assertEqual(caught.exception.code, 'setup_error')
                    message = str(caught.exception)
                    self.assertIn('setup looks wrong', message)
                    self.assertIn('Nothing was sent', message)
                    self.assertNotIn('Try again', message)
                    self.assertNotIn('not running', message)

    def test_a_busy_service_is_not_retried_and_says_try_again_later(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener, \
                socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as queued:
            listener.bind(self.path)
            listener.listen(0)
            queued.connect(self.path)  # the queue is full now: the next connect gets EAGAIN
            started = time.monotonic()
            with self.assertRaises(NotConnected) as caught:
                Client(self.path).request(READ)
            self.assertLess(time.monotonic() - started, 1)
        for cause in (caught.exception.__cause__, TimeoutError('timed out')):
            with self.subTest(cause=type(cause).__name__):
                error = NotConnected(cause)
                self.assertEqual(error.code, 'service_busy')
                self.assertIn('busy', str(error))
                self.assertIn('nothing was sent', str(error))
                self.assertIn('Try again later', str(error))
                self.assertNotIn('not running', str(error))

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

    def test_hooks_connect_once_and_the_proxy_still_waits(self):
        # Lead, 2026-11-15: the 3 s wait stays for the MCP proxies and the CLI; a hook makes one attempt, so a session
        # never waits at every prompt and turn end while the service is down.
        from aresos_control import hooks
        with patch.object(protocol.time, 'sleep') as sleep, self.assertRaises(NotConnected) as caught:
            Client(self.path, connect_wait=0).request(READ)
        sleep.assert_not_called()
        self.assertIn('not running', str(caught.exception))
        for socket_file in ('missing', 'stale'):
            if socket_file == 'stale':
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stale:
                    stale.bind(self.path)  # refuses connections (ECONNREFUSED), which the proxy waits on too
            for name in ('Stop', 'UserPromptSubmit'):
                event = json.dumps({'hook_event_name': name}).encode()
                with self.subTest(socket_file=socket_file, hook=name), \
                        patch.object(hooks.usage, 'used', return_value=True), \
                        patch.object(hooks.usage, 'notice', return_value=True) as notice, \
                        patch.object(hooks.usage, 'reached') as reached, \
                        patch('sys.stdin', io.TextIOWrapper(io.BytesIO(event))), redirect_stdout(io.StringIO()) as output:
                    started = time.monotonic()
                    hooks.main({'act_socket': self.path}, name)  # the real client, with the default 3 s wait in place
                    self.assertLess(time.monotonic() - started, 0.5)
                    reached.assert_not_called()
                    if name == 'Stop':
                        self.assertEqual(json.loads(output.getvalue())['reason'], hooks.NOT_RUNNING)
                    else:
                        self.assertEqual(output.getvalue(), '')
                        notice.assert_not_called()
            with self.subTest(socket_file=socket_file, caller='proxy'), patch.object(protocol, 'CONNECT_WAIT', 0.4):
                started = time.monotonic()
                result = Proxy('testapp', {'act_socket': self.path, 'admin_socket': self.path + '.admin'}).call('list', {'limit': 3})
                self.assertGreaterEqual(time.monotonic() - started, 0.4)
                self.assertEqual(result['error']['code'], 'service_unavailable')


class StartWithoutService(unittest.TestCase):
    """18c's VM run: a Claude Code session started while the service is down gets its tools once the service is up."""
    CALL = '{"jsonrpc":"2.0","id":"call","method":"tools/call","params":{"name":"list","arguments":{"limit":3}}}'

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, 'act.sock')
        self.config = {'act_socket': self.path, 'admin_socket': self.path + '.admin'}

    def test_the_proxy_offers_its_own_catalogue_and_calls_reach_the_service_once_it_is_up(self):
        proxy = Proxy('testapp', self.config)
        with patch.object(protocol, 'CONNECT_WAIT', 0.2):
            started = time.monotonic()
            tools = proxy.tools()
            self.assertGreaterEqual(time.monotonic() - started, 0.2)  # it asked the service first, with the wait
            down = proxy.call('list', {'limit': 3})
        self.assertEqual(tools, json.loads(json.dumps(tools_for('testapp'))))
        self.assertIn('prepare_send', [tool['name'] for tool in tools])
        self.assertFalse(any(BY_NAME['testapp_' + tool['name']].owner_only for tool in tools))
        self.assertNotIn('fixture_configure', [tool['name'] for tool in tools])
        self.assertEqual(down['error']['code'], 'service_unavailable')
        service = FakeService(self.path, 0)
        service.start()
        self.assertEqual(proxy.call('list', {'limit': 3})['ok'], True)
        service.join(5)
        self.assertEqual(service.requests[0]['action'], 'testapp_list')

    def test_a_catalogue_the_service_returns_wins_and_other_failures_still_stop(self):
        proxy = Proxy('testapp', self.config)
        served = [tool for tool in tools_for('testapp') if tool['name'] == 'list']
        owner_only = BY_NAME['testapp_fixture_configure'].tool()
        with patch.object(proxy.client, 'request', return_value={'ok': True, 'data': {'tools': served + [owner_only]}, 'pending': {}}):
            self.assertEqual([tool['name'] for tool in proxy.tools()], ['list'])
        for failure in ({'return_value': {'ok': False, 'error': {'code': 'invalid_input', 'message': 'synthetic'}, 'pending': {}}},
                        {'side_effect': Refused('transport_error', 'Service connection lost.')}):
            with self.subTest(failure=failure), patch.object(proxy.client, 'request', **failure), self.assertRaises(Refused):
                proxy.tools()

    def test_an_mcp_session_started_without_the_service_gets_its_tools(self):
        from raw_json_test_support import RawMCP
        code = ('import sys; from aresos_control import protocol; protocol.CONNECT_WAIT = 0.3; '
                'from aresos_control.proxy import main; main("testapp", {"act_socket": sys.argv[1]})')
        with RawMCP([sys.executable, '-c', code, self.path], env=os.environ.copy()) as client:
            listed = client.exchange('{"jsonrpc":"2.0","id":"list","method":"tools/list","params":{}}')
            self.assertEqual(sorted(tool['name'] for tool in listed['result']['tools']),
                             sorted(tool['name'] for tool in tools_for('testapp')))
            down = client.exchange(self.CALL)
            self.assertTrue(down['result']['isError'], down)
            self.assertEqual(down['result']['structuredContent']['error']['code'], 'service_unavailable')
            service = FakeService(self.path, 0)
            service.start()
            up = client.exchange(self.CALL)
            self.assertEqual(up['result']['structuredContent']['ok'], True, up)
            service.join(5)
            self.assertEqual(service.requests[0]['action'], 'testapp_list')


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

    def reserve(self, **changes):
        from support import message
        result = self.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_prepare_send', 'arguments': message(**changes)})
        self.assertTrue(result['ok'], result)
        return result['data']['approval']

    def expires(self, approval):
        return self.engine.store.get('op:' + approval['operation_id'])['expires']

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
        self.engine.ttl = 0.6
        later = self.reserve(subject='later')
        self.engine.ttl = 0.4
        first = self.reserve(subject='first')  # reserved second, expires first
        self.assertLess(self.expires(first), self.expires(later))
        self.assertEqual(self.engine.next_deadline(), self.expires(first))
        self.assertAlmostEqual(self.engine.next_deadline(), time.time() + 0.4, delta=0.2)
        time.sleep(0.45)
        self.engine.expire()
        self.assertEqual(self.engine.next_deadline(), self.expires(later))
        time.sleep(0.2)
        self.engine.expire()
        self.assertIsNone(self.engine.next_deadline())
        self.engine.store.deferred_notices['n'] = ({}, 'control_maintenance', 'synthetic')
        self.assertAlmostEqual(self.engine.next_deadline(), time.time() + engine_module.NOTICE_RETRY, delta=0.2)

    def test_deferred_notices_never_delay_an_earlier_reservation(self):
        # Review 1 #1 (minor): the 1 s notice retry used to hide a reservation expiring sooner.
        from aresos_control import engine as engine_module
        approval = self.reserve()
        self.engine.store.deferred_notices['n'] = ({}, 'control_maintenance', 'synthetic')
        self.assertEqual(self.engine.next_deadline(), self.expires(approval))
        # Overdue (its expiry failed with the notices' write in the last pass): retried with the notices, each second.
        with patch.object(engine_module.time, 'time', return_value=self.expires(approval) + 5):
            self.assertEqual(self.engine.next_deadline(), self.expires(approval) + 5 + engine_module.NOTICE_RETRY)
        self.engine.store.deferred_notices.clear()

    def test_an_expiry_that_keeps_failing_never_spins(self):
        # Review 1 #1, security review hardening note: an overdue reservation whose expiry write raises (not a storage
        # refusal, so no deferred notice) stays reserved; the loop then waits the old 0.1 s, never 0.
        import sqlite3
        from aresos_control import daemon as daemon_module
        approval = self.reserve()
        time.sleep(0.45)
        for failure in (ValueError('synthetic'), sqlite3.OperationalError('database is locked')):
            with self.subTest(failure=type(failure).__name__), \
                    patch.object(self.engine.store, 'write', side_effect=failure) as write, \
                    self.assertLogs('aresos_control.engine', 'ERROR'):
                timeouts = self.passes(5)
                self.assertEqual(write.call_count, 5)  # tried at every pass ...
                self.assertEqual(timeouts, [daemon_module.OVERDUE_RETRY] * 5)  # ... 0.1 s apart, never at once
                self.assertEqual(self.engine.store.get('op:' + approval['operation_id'])['state'], 'reserved')
                self.assertFalse(self.engine.store.deferred_notices)
        self.passes(1)  # the write works again: expired
        self.assertEqual(self.engine.store.get('op:' + approval['operation_id'])['state'], 'failed')
        self.assertGreater(self.passes(1)[0], 59)

    def test_only_a_deadline_already_due_waits_the_floor(self):
        from aresos_control import daemon as daemon_module
        approval = self.reserve()
        with patch.object(self.engine, 'expire'):
            for offset, expected in ((0.002, 0.002 + daemon_module.DEADLINE_MARGIN), (0.0, daemon_module.OVERDUE_RETRY),
                                     (-0.001, daemon_module.OVERDUE_RETRY)):
                with self.subTest(offset=offset), \
                        patch('aresos_control.daemon.time.time', return_value=self.expires(approval) - offset):
                    self.assertAlmostEqual(self.passes(1)[0], expected, places=6)

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
        """Mark `pid` as the proxy does: its parent as read at start, still its parent now."""
        from aresos_control import usage
        session = (pid, usage.process(pid, self.proc)[0])
        with patch.object(usage.os, 'getppid', return_value=pid):
            usage.mark(session, uid=self.uid, run=self.run_dir, proc=self.proc)

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
        self.mark(pid=10)  # a mark further up than the session (tmux) is not the session's
        self.assertFalse(self.used())
        self.process(60, 55, 3, 'python3')
        self.process(55, 50, 2, 'sh')
        self.process(50, 1, 1, 'claude')
        self.mark(pid=50)  # another session's mark
        self.assertFalse(self.used())
        self.assertTrue(self.used(pid=55))

    def test_a_reused_pid_with_another_start_time_has_no_mark(self):
        self.mark()
        self.process(20, 10, 777, 'claude')  # pid 20 ended; a new process got its number
        self.assertFalse(self.used())

    def test_four_levels_and_never_pid_1(self):
        self.process(80, 1, 80, 'sh')
        self.mark(pid=1)
        self.assertFalse(self.used(pid=80))  # shells up to PID 1, which never counts
        for pid in range(70, 75):  # 70 <- 71 <- ... <- 74, all shells, then 75 (claude)
            self.process(pid, pid + 1, pid, 'sh')
        self.process(75, 1, 75, 'claude')
        self.mark(pid=75)
        self.assertFalse(self.used(pid=70))  # from a hook whose parent is 70, process 75 is level 6: too far
        self.assertFalse(self.used(pid=71))  # level 5
        self.assertTrue(self.used(pid=72))  # level 4

    def test_unreadable_marks_or_processes_count_as_marked(self):
        self.mark(pid=10)
        self.process(60, 55, 3, 'python3')
        (self.proc / '55').mkdir()
        self.assertTrue(self.used(pid=55))  # no stat for the parent
        self.marks().chmod(0o755)
        self.assertTrue(self.used())  # not a private folder
        self.marks().chmod(0o700)
        (self.marks() / '20-500').mkdir()
        self.assertTrue(self.used())  # a folder where the session's mark should be

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
            proxy.note_use('testapp', 'prepare_send', approval, (20, 500))
            proxy.note_use('testapp', 'list', {'ok': True, 'data': {'items': [{'operation_id': 'x'}]}}, (20, 500))
            proxy.note_use('testapp', 'no_such_tool', approval, (20, 500))
            proxy.note_use('testapp', 'prepare_send', approval, None)  # the parent couldn't be read at start
        mark.assert_called_once_with((20, 500))
        with patch.object(proxy.usage, 'mark', side_effect=OSError('synthetic')):
            proxy.note_use('testapp', 'prepare_send', approval, (20, 500))
        with patch.object(proxy.usage, 'names_operation', side_effect=RuntimeError('synthetic')):
            proxy.note_use('testapp', 'prepare_send', approval, (20, 500))  # nothing in marking drops a result

    def stop(self, error, marked, event=None, name='Stop'):
        from aresos_control import hooks
        event = event or {'hook_event_name': name, 'session_id': 's', 'prompt_id': 'p'}
        output = io.StringIO()
        with patch.object(hooks, 'Client') as client, patch.object(hooks.usage, 'notice', return_value=marked) as notice, \
                patch.object(hooks.usage, 'used', return_value=marked), patch.object(hooks.usage, 'reached') as reached, \
                patch('sys.stdin', io.TextIOWrapper(io.BytesIO(json.dumps(event).encode()))), redirect_stdout(output):
            client.return_value.call.side_effect = error
            hooks.main({'act_socket': '/nonexistent'}, name)
        reached.assert_not_called()
        return output.getvalue(), notice

    def test_stop_hook_is_quiet_unless_used(self):
        import errno
        from aresos_control import hooks
        # Only "not listening" says not running; a busy service, a broken setup or a lost connection (a busy service's
        # read timeout among them) says could not be reached (review 1 #5, security review known limit 3).
        for error, reason in ((NotConnected(FileNotFoundError(2, 'No such file')), hooks.NOT_RUNNING),
                              (NotConnected(ConnectionRefusedError(errno.ECONNREFUSED, 'Connection refused')), hooks.NOT_RUNNING),
                              (NotConnected(BlockingIOError(errno.EAGAIN, 'Resource temporarily unavailable')), hooks.NOT_REACHED),
                              (NotConnected(TimeoutError('timed out')), hooks.NOT_REACHED),
                              (NotConnected(PermissionError(errno.EACCES, 'Permission denied')), hooks.NOT_REACHED),
                              (Refused('transport_error', 'Service connection lost; inspect operation_status with the same id, never repeat with a new id.'), hooks.NOT_REACHED)):
            with self.subTest(code=error.code, cause=type(error.__cause__ or error).__name__):
                printed, notice = self.stop(error, marked=False)
                self.assertEqual(printed, '')
                notice.assert_not_called()  # an unmarked session doesn't even connect
                printed, _ = self.stop(error, marked=True)
                decision = json.loads(printed)
                self.assertEqual(decision, {'decision': 'block', 'reason': reason})
                self.assertIn("don't repeat it", decision['reason'])
                if reason == hooks.NOT_REACHED:
                    self.assertNotIn('not running', decision['reason'])
                self.assertNotIn('operation_status', decision['reason'])
                printed, notice = self.stop(error, marked=True, event={'hook_event_name': 'Stop', 'stop_hook_active': True})
                self.assertEqual(printed, '')
                notice.assert_not_called()  # the continuation guard comes first: nothing is recorded as told
                printed, notice = self.stop(error, marked=True, name='UserPromptSubmit')
                self.assertEqual(printed, '')
                notice.assert_not_called()

    def test_stop_hook_with_the_service_up_is_unchanged(self):
        from aresos_control import hooks
        pending = {'items': [{'operation_id': 'op'}], 'total': 1}
        output = io.StringIO()
        with patch.object(hooks, 'Client') as client, patch.object(hooks.usage, 'notice') as notice, \
                patch.object(hooks.usage, 'used', return_value=True), patch.object(hooks.usage, 'reached') as reached, \
                patch('sys.stdin', io.TextIOWrapper(io.BytesIO(b'{"hook_event_name":"Stop"}'))), redirect_stdout(output):
            client.return_value.call.return_value = {'ok': True, 'data': pending}
            hooks.main({'act_socket': '/nonexistent'}, 'Stop')
        self.assertEqual(json.loads(output.getvalue())['decision'], 'block')
        self.assertIn('held/unfinished work', json.loads(output.getvalue())['reason'])
        notice.assert_not_called()
        reached.assert_called_once_with()

    # One notice per outage (lead, 2026-11-15).
    def notice(self, pid=35):
        from aresos_control import usage
        return usage.notice(pid=pid, uid=self.uid, run=self.run_dir, proc=self.proc)

    def reached(self, pid=35):
        from aresos_control import usage
        usage.reached(pid=pid, uid=self.uid, run=self.run_dir, proc=self.proc)

    def told(self):
        return self.marks() / '20-500.told'

    def test_a_marked_session_is_told_once_per_outage(self):
        self.mark()
        self.assertTrue(self.notice())
        self.assertEqual(sorted(p.name for p in self.marks().iterdir()), ['20-500', '20-500.told'])
        self.assertEqual(self.told().read_bytes(), b'')
        self.assertEqual(self.told().stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.notice())
        self.assertFalse(self.notice())
        self.assertTrue(self.used())  # still a session that used the tools
        self.reached()  # the service answered a hook
        self.assertFalse(self.told().exists())
        self.assertTrue((self.marks() / '20-500').exists())
        self.assertTrue(self.notice())  # the next outage tells again
        self.assertFalse(self.notice())
        self.reached()
        self.reached()  # nothing left to remove is fine
        self.assertTrue(self.notice())

    def test_unmarked_sessions_are_never_told_and_leave_no_file(self):
        self.assertFalse(self.notice())  # no folder at all
        self.reached()
        self.process(55, 50, 2, 'sh')
        self.process(50, 1, 1, 'claude')
        self.mark(pid=50)  # another session's mark
        self.assertFalse(self.notice())
        self.reached()
        self.assertEqual(sorted(p.name for p in self.marks().iterdir()), ['50-1'])
        self.process(20, 10, 777, 'claude')  # a reused pid doesn't inherit a mark or its notice
        self.mark(pid=50)
        self.assertTrue(self.notice(pid=55))
        self.assertFalse(self.notice())

    def test_a_told_file_that_cannot_be_written_or_read_still_tells(self):
        from aresos_control import usage
        self.mark()
        real_open, real_stat = os.open, os.stat
        def failing(real):
            def call(name, *args, **kwargs):
                if str(name).endswith(usage.TOLD):
                    raise PermissionError(13, 'synthetic')
                return real(name, *args, **kwargs)
            return call
        with patch.object(usage.os, 'open', failing(real_open)):
            self.assertTrue(self.notice())  # better twice than never
            self.assertTrue(self.notice())
        self.assertFalse(self.told().exists())
        with patch.object(usage.os, 'stat', failing(real_stat)):
            self.assertTrue(self.notice())  # can't be read: not told
            self.assertTrue(self.notice())
        self.assertTrue(self.told().exists())  # written all the same
        self.assertFalse(self.notice())

    def test_a_link_or_folder_at_the_told_name_is_never_followed_and_still_tells(self):
        self.mark()
        elsewhere = self.root / 'elsewhere'
        elsewhere.mkdir(mode=0o700)
        self.told().symlink_to(elsewhere / 'told')
        self.assertTrue(self.notice())
        self.assertTrue(self.notice())
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.reached()  # removes the link itself, never its target
        self.assertFalse(os.path.lexists(self.told()))
        self.told().mkdir()
        self.assertTrue(self.notice())
        self.assertTrue(self.notice())
        self.reached()  # can't remove a folder; never raises
        self.assertTrue(self.told().is_dir())

    def test_unreadable_marks_tell_at_every_stop_and_record_nothing(self):
        self.mark()
        self.marks().chmod(0o755)
        self.assertTrue(self.notice())
        self.assertTrue(self.notice())
        self.reached()
        self.marks().chmod(0o700)
        self.assertFalse(self.told().exists())
        (self.proc / '35' / 'stat').unlink()  # the hook's parent can't be read
        self.assertTrue(self.notice())
        self.assertTrue(self.notice())
        self.reached()
        self.assertFalse(self.told().exists())

    def test_the_stop_hook_tells_once_per_outage(self):
        from functools import partial
        from aresos_control import hooks, usage
        where = {'pid': 35, 'uid': self.uid, 'run': self.run_dir, 'proc': self.proc}
        down = NotConnected(FileNotFoundError(2, 'No such file'))
        lost = Refused('transport_error', 'Service connection lost; inspect operation_status with the same id, never repeat with a new id.')
        up = {'ok': True, 'data': {'total': 0}}

        def hook(outcome, name='Stop', active=False):
            event = {'hook_event_name': name, 'session_id': 's', **({'stop_hook_active': active} if name == 'Stop' else {})}
            output = io.StringIO()
            with patch.object(hooks, 'Client') as client, patch.object(hooks.usage, 'notice', partial(usage.notice, **where)), \
                    patch.object(hooks.usage, 'used', partial(usage.used, **where)), \
                    patch.object(hooks.usage, 'reached', partial(usage.reached, **where)), \
                    patch('sys.stdin', io.TextIOWrapper(io.BytesIO(json.dumps(event).encode()))), redirect_stdout(output):
                if isinstance(outcome, Exception):
                    client.return_value.call.side_effect = outcome
                else:
                    client.return_value.call.return_value = outcome
                hooks.main({'act_socket': '/nonexistent'}, name)
            return output.getvalue()

        def told(printed, reason=hooks.NOT_RUNNING):
            return json.loads(printed) == {'decision': 'block', 'reason': reason}

        self.assertEqual(hook(down), '')  # never used: quiet
        self.mark()
        self.assertEqual(hook(down, active=True), '')  # the continuation guard records nothing
        self.assertTrue(told(hook(down)))
        self.assertEqual(hook(down), '')  # the next turns of the same outage stay quiet
        self.assertEqual(hook(lost), '')
        self.assertEqual(hook(down, 'UserPromptSubmit'), '')
        self.assertEqual(json.loads(hook(up)), {})  # the service is back
        self.assertTrue(told(hook(down)))  # a new outage tells again
        self.assertEqual(hook(lost), '')
        self.assertEqual(json.loads(hook(up, 'UserPromptSubmit')), {})  # a prompt that reaches the service counts too
        self.assertTrue(told(hook(lost), hooks.NOT_REACHED))

    # Fix round 1 (review 1 #2, #3, #4; security review known limits 1 and 2; lead's items 9 and 10).
    def test_a_nested_claude_is_a_session_of_its_own(self):
        # Session A (claude 20) runs `claude -p` (88) through its Bash tool (87); B's hook runs under sh 89.
        self.process(90, 89, 950, 'python3')
        self.process(89, 88, 949, 'sh')
        self.process(88, 87, 940, 'claude')
        self.process(87, 20, 930, 'bash')
        self.mark()  # A used the tools
        self.assertTrue(self.used())
        self.assertFalse(self.used(pid=89))  # B never did: its walk ends at its own Claude Code
        self.assertFalse(self.notice(pid=89))
        self.assertFalse(self.told().exists())  # B never uses up A's notice ...
        self.assertTrue(self.notice())  # ... so A is still told
        self.mark(pid=88)  # B used them too: now B has its own mark and its own notice
        self.assertTrue(self.notice(pid=89))
        self.assertEqual(sorted(p.name for p in self.marks().iterdir()), ['20-500', '20-500.told', '88-940', '88-940.told'])

    def test_a_wrapper_that_isnt_a_shell_hides_the_mark(self):
        # The safer reading: a process other than a shell between Claude Code and the hook is taken as the session, so
        # the hook finds no mark and stays quiet. Claude Code 2.1.319 runs hooks through shells only (boundary pin).
        self.process(45, 44, 960, 'python3')
        self.process(44, 20, 959, 'timeout')
        self.mark()
        self.assertFalse(self.used(pid=44))
        self.assertFalse(self.notice(pid=44))
        self.assertTrue(self.used())

    def test_the_proxy_marks_only_while_its_parent_is_the_same_process(self):
        from functools import partial
        from aresos_control import proxy, usage
        where = {'uid': self.uid, 'run': self.run_dir, 'proc': self.proc}
        with patch.object(usage.os, 'getppid', return_value=20):
            session = usage.parent(proc=self.proc)
        self.assertEqual(session, (20, 500))
        approval = {'ok': True, 'data': {'approval': {'operation_id': 'op'}}, 'pending': {}}
        with patch.object(proxy.usage, 'mark', partial(usage.mark, **where)):
            # Claude Code died; the proxy now belongs to a subreaper (systemd --user, pid 7): nothing is marked.
            self.process(7, 1, 50, 'systemd')
            with patch.object(usage.os, 'getppid', return_value=7), self.assertLogs('aresos_control.proxy', 'WARNING') as logs:
                proxy.note_use('testapp', 'prepare_send', approval, session)
            self.assertEqual(len(logs.records), 1)
            self.assertIn('session not marked', logs.output[0])
            self.assertFalse((self.run_dir / str(self.uid) / 'aresos-control').exists())
            # The same pid with another start time is another process too.
            self.process(20, 10, 777, 'claude')
            with patch.object(usage.os, 'getppid', return_value=20), self.assertRaises(usage.ParentChanged):
                usage.mark(session, **where)
            self.process(20, 10, 500, 'claude')
            with patch.object(usage.os, 'getppid', return_value=20):
                proxy.note_use('testapp', 'prepare_send', approval, session)
        self.assertEqual(sorted(p.name for p in self.marks().iterdir()), ['20-500'])
        self.assertTrue(self.used())

    def test_a_new_use_re_arms_the_notice(self):
        # Review 1 #4: used again between two outages without a hook reaching the service in between.
        self.mark()
        self.assertTrue(self.notice())
        self.assertFalse(self.notice())
        self.mark()  # a new operation in the same session
        self.assertFalse(self.told().exists())
        self.assertTrue(self.notice())
        self.told().unlink()
        self.told().mkdir()  # a .told that can't be removed: the mark is still made, and the error still raises
        with self.assertRaises(OSError):
            self.mark()
        self.assertTrue((self.marks() / '20-500').is_file())

    def test_a_fifo_at_a_mark_or_told_name_never_blocks(self):
        # Security review known limit 2: a FIFO planted by a process of the owner must never hang the proxy's event
        # loop or the Stop hook (both used to block until a reader came).
        from aresos_control import proxy, usage
        from functools import partial

        def within(call, seconds=2):
            outcome = {}
            def run():
                try:
                    outcome['value'] = call()
                except Exception as exc:
                    outcome['error'] = exc
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            thread.join(seconds)
            self.assertFalse(thread.is_alive(), 'blocked on a FIFO')
            return outcome

        self.mark(pid=10)  # makes the folders
        os.mkfifo(self.marks() / '20-500')
        self.assertIsInstance(within(self.mark)['error'], OSError)
        approval = {'ok': True, 'data': {'approval': {'operation_id': 'op'}}, 'pending': {}}
        with patch.object(proxy.usage, 'mark', partial(usage.mark, uid=self.uid, run=self.run_dir, proc=self.proc)), \
                patch.object(usage.os, 'getppid', return_value=20):
            self.assertEqual(within(lambda: proxy.note_use('testapp', 'prepare_send', approval, (20, 500))), {'value': None})
        self.assertTrue(within(self.used)['value'])  # not a plain file: counts as marked
        self.assertTrue(within(self.notice)['value'])
        (self.marks() / '20-500').unlink()
        self.mark()
        os.mkfifo(self.told())
        self.assertTrue(within(self.notice)['value'])  # a .told that can't be written or read still tells
        self.assertTrue(within(self.notice)['value'])
        # With a reader on the FIFO the open succeeds, and the FIFO is still refused.
        reader = os.open(self.told(), os.O_RDONLY | os.O_NONBLOCK)
        self.addCleanup(os.close, reader)
        with self.assertRaises(usage.Unreadable):
            folder = usage._marks(self.uid, self.run_dir, create=False)
            try:
                usage._create('20-500.told', folder)
            finally:
                os.close(folder)

    # Pending work and notices reach only a session that used the tools (lead, 2026-11-16, item 9).
    def pending_hook(self, result, name='Stop', marked=True):
        from aresos_control import hooks
        event = {'hook_event_name': name, **({'stop_hook_active': False} if name == 'Stop' else {})}
        output = io.StringIO()
        with patch.object(hooks, 'Client') as client, patch.object(hooks.usage, 'used', return_value=marked), \
                patch.object(hooks.usage, 'notice') as notice, patch.object(hooks.usage, 'reached'), \
                patch('sys.stdin', io.TextIOWrapper(io.BytesIO(json.dumps(event).encode()))), redirect_stdout(output):
            client.return_value.call.return_value = result
            hooks.main({'act_socket': '/nonexistent'}, name)
        notice.assert_not_called()
        return output.getvalue(), client

    def test_an_unmarked_session_never_hears_of_pending_work(self):
        others = {'ok': True, 'data': {'items': [{'operation_id': 'other-session-op', 'state': 'reserved'}], 'total': 1,
                                       'notices': [{'reason': 'Outcome of another session'}]}}
        for name in ('Stop', 'UserPromptSubmit'):
            with self.subTest(hook=name):
                printed, client = self.pending_hook(others, name, marked=False)
                self.assertEqual(printed, '')
                client.assert_not_called()  # costs nothing: not even a connection

    def test_a_marked_session_still_gets_the_reminder_in_the_new_words(self):
        from aresos_control import hooks
        self.assertEqual(hooks.REMINDER, " Don't complete, cancel, resend or acknowledge this work on your own: tell the "
                                         "owner what is waiting, and let him decide.")
        pending = {'ok': True, 'data': {'items': [{'operation_id': 'op-1', 'state': 'reserved'}], 'total': 1}}
        printed, _ = self.pending_hook(pending, 'Stop')
        decision = json.loads(printed)
        self.assertEqual(decision['decision'], 'block')
        self.assertIn('op-1', decision['reason'])
        self.assertTrue(decision['reason'].endswith(hooks.REMINDER))
        self.assertNotIn('Resolve, cancel', decision['reason'])
        printed, _ = self.pending_hook(pending, 'UserPromptSubmit')
        self.assertIn('op-1', json.loads(printed)['hookSpecificOutput']['additionalContext'])

    def test_permission_denied_means_nothing_for_this_session(self):
        # Lead's item 10: root's or another user's session gets permission_denied from act.sock; it can't use the
        # tools, so it is never blocked or told.
        denied = {'ok': False, 'error': {'code': 'permission_denied', 'message': 'This peer is not permitted on this socket; '
                  'use act as owner, admin via sudo. Chrome bridge accepts nothing.'}, 'pending': {'items': [], 'total': 0}}
        for name in ('Stop', 'UserPromptSubmit'):
            with self.subTest(hook=name):
                printed, client = self.pending_hook(denied, name)
                self.assertEqual(printed, '')
                client.return_value.call.assert_called_once_with('control_pending', {})

    def test_the_hooks_follow_the_real_marks(self):
        # The gate with the real usage code on a fake /proc: quiet before the session's first use, reminded after.
        from functools import partial
        from aresos_control import hooks, usage
        where = {'pid': 35, 'uid': self.uid, 'run': self.run_dir, 'proc': self.proc}
        pending = {'ok': True, 'data': {'items': [{'operation_id': 'op-1', 'state': 'reserved'}], 'total': 1}}

        def stop():
            output = io.StringIO()
            with patch.object(hooks, 'Client') as client, patch.object(hooks.usage, 'used', partial(usage.used, **where)), \
                    patch.object(hooks.usage, 'reached', partial(usage.reached, **where)), \
                    patch('sys.stdin', io.TextIOWrapper(io.BytesIO(b'{"hook_event_name":"Stop"}'))), redirect_stdout(output):
                client.return_value.call.return_value = pending
                hooks.main({'act_socket': '/nonexistent'}, 'Stop')
            return output.getvalue()

        self.assertEqual(stop(), '')
        self.mark(pid=10)  # a process further up: still not this session
        self.assertEqual(stop(), '')
        self.mark()
        self.assertEqual(json.loads(stop())['decision'], 'block')


class FixRoundProxy(unittest.TestCase):
    """Review 1 #6 and #7: the saved path survives a service gone before its report; call_tool marks the session."""
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.home = Path(self.folder.name, 'home')
        (self.home / 'Downloads').mkdir(parents=True)
        self.config = {'act_socket': '/nonexistent/act.sock', 'admin_socket': '/nonexistent/admin.sock',
                       'home': str(self.home), 'folders': [str(self.home / 'Downloads')]}

    def test_a_file_saved_before_the_service_stopped_keeps_its_path(self):
        import hashlib
        from aresos_control import proxy as proxy_module
        data = b'saved bytes'
        digest = hashlib.sha256(data).hexdigest()
        down = NotConnected(FileNotFoundError(2, 'No such file or directory'))
        for app, verb, arguments in (
                ('testapp', 'file_save', {'sha256': digest, 'folder': str(self.home / 'Downloads'), 'name': 'a.txt'}),
                ('mail', 'attachment_save', {'reference': {'account': 'fixture', 'folder': 'INBOX', 'uidvalidity': 1, 'uid': 1,
                                                           'message_id': '<m@example.invalid>'}, 'part': '2', 'name': 'b.txt'})):
            with self.subTest(app=app):
                proxy = Proxy(app, self.config)
                requests = []
                def request(message):
                    requests.append(message)
                    if message['method'] == 'saved':
                        raise down  # the service stopped after the download, before the report
                    raise AssertionError(message)
                admission = {'export_id': 'e' * 32, 'other_holds': 0}
                with patch.object(proxy.client, 'download', return_value=({'ok': True, 'data': admission}, data)), \
                        patch.object(proxy.client, 'request', side_effect=request), \
                        patch.object(proxy.client, 'call', return_value={'ok': True, 'data': {'file': {
                            'sha256': digest, 'name': 'b.txt', 'export_id': 'e' * 32}}, 'pending': {}}):
                    result = proxy.call(verb, arguments)
                path = self.home / 'Downloads' / arguments['name']
                self.assertEqual(path.read_bytes(), data)
                self.assertEqual([message['method'] for message in requests], ['saved'])
                self.assertFalse(result['ok'])
                self.assertEqual(result['data']['saved'], {'path': str(path), 'sha256': digest, 'size': len(data)})
                self.assertEqual(result['error']['message'], proxy_module.SAVED_UNREPORTED)
                self.assertNotIn('nothing was sent', result['error']['message'])
                self.assertNotIn('Try again', result['error']['message'])

    def test_call_tool_marks_the_session_read_at_start(self):
        # The SDK's server, stood in for: serve() hands call_tool to Server(on_call_tool=...); call it as the SDK would.
        import asyncio
        from contextlib import asynccontextmanager
        from aresos_control import proxy as proxy_module
        calls = {}

        class Server:
            def __init__(self, name, version, instructions, on_list_tools, on_call_tool):
                calls['call_tool'] = on_call_tool

            def create_initialization_options(self):
                return None

            async def run(self, read, write, options):
                for name in ('prepare_send', 'list'):
                    calls[name] = await calls['call_tool'](None, SimpleNamespace(name=name, arguments={}))

        @asynccontextmanager
        async def stdio_server(stdin):
            yield None, None

        fake = lambda **names: SimpleNamespace(**names)
        sdk = {'mcp_types': fake(CallToolResult=lambda **kw: kw, TextContent=lambda **kw: kw),
               'mcp': fake(), 'mcp.server': fake(), 'mcp.server.lowlevel': fake(Server=Server),
               'mcp.server.stdio': fake(stdio_server=stdio_server)}
        answers = {'prepare_send': {'ok': True, 'data': {'approval': {'operation_id': 'op'}}, 'pending': {}},
                   'list': {'ok': True, 'data': {'items': [{'operation_id': 'x'}]}, 'pending': {}}}
        tools = [tool for tool in tools_for('testapp') if tool['name'] in answers]
        with patch.dict(sys.modules, sdk), patch.object(proxy_module.usage, 'parent', return_value=(20, 500)), \
                patch.object(proxy_module.usage, 'mark') as mark, patch.object(Proxy, 'tools', return_value=tools), \
                patch.object(Proxy, 'call', side_effect=lambda verb, arguments: answers[verb]):
            asyncio.run(proxy_module.serve('testapp', self.config))
        mark.assert_called_once_with((20, 500))  # the operation-naming result only, with the session read at start
        self.assertEqual(calls['prepare_send']['structured_content'], answers['prepare_send'])
        self.assertFalse(calls['list']['is_error'])


if __name__ == '__main__':
    unittest.main()
