"""F7: owner authority over chrome.sock waits for the owner's polkit password.

pkcheck is a stub here. Real polkitd with a password agent runs in
.github/workflows/control-chrome-polkit.yml (control/chrome/ci/polkit-check.py).
"""
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import confirm
from aresos_control.daemon import Daemon
import test_engine as engine_cases

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'control/chrome/packaging/org.aresos.control.chrome-loosen.policy'
STUB = '''#!/bin/sh
dir=$(dirname "$0")
for argument in "$@"; do printf '%s\\n' "$argument" >> "$dir/calls"; done
printf -- '--\\n' >> "$dir/calls"
if [ -f "$dir/delay" ]; then sleep "$(cat "$dir/delay")"; fi
if [ -f "$dir/stdout" ]; then cat "$dir/stdout"; fi
if [ -f "$dir/stderr" ]; then cat "$dir/stderr" >&2; fi
exit "$(cat "$dir/code")"
'''
PEER = {'pid': 4242, 'uid': 1000, 'start': 777}


class Polkit:
    """A pkcheck stand-in: answers with a set exit code and records every call."""

    def __init__(self, root):
        self.directory = Path(root) / 'polkit'
        self.directory.mkdir()
        self.path = self.directory / 'pkcheck'
        self.path.write_text(STUB)
        self.path.chmod(0o755)
        self.answer(1)

    def answer(self, code, stdout='', stderr='', delay=None):
        (self.directory / 'code').write_text(str(code))
        (self.directory / 'stdout').write_text(stdout)
        (self.directory / 'stderr').write_text(stderr)
        if delay is None:
            (self.directory / 'delay').unlink(missing_ok=True)
        else:
            (self.directory / 'delay').write_text(str(delay))

    def calls(self):
        path = self.directory / 'calls'
        if not path.exists():
            return []
        return [call.strip('\n').split('\n') for call in path.read_text().split('--\n') if call.strip('\n')]


class Confirmation(unittest.TestCase):
    setUp_engine, tearDown_engine = engine_cases.Operations.setUp, engine_cases.Operations.tearDown
    call, target, prepare, gmail = (engine_cases.Operations.call, engine_cases.Operations.target,
                                    engine_cases.Operations.prepare, engine_cases.OwnerRules.gmail)

    def setUp(self):
        self.setUp_engine()
        self.gmail()
        approval = self.prepare()
        self.assertTrue(self.call('submit', approval)['ok'])
        self.operation = approval['operation_id']
        self.server, self.client = socket.socketpair()
        self.client.settimeout(10)
        self.browser.connection, self.browser.peer = self.server, dict(PEER)
        self.polkit = Polkit(self.root)
        self.chrome.pkcheck, self.chrome.confirm_timeout = str(self.polkit.path), 10
        self.engine.store.write({'chrome:readonly:locked.test': True}, 'chrome_test_readonly', 'Synthetic read-only site')
        self.requests, self.inbox = 0, b''

    def tearDown(self):
        if self.chrome.confirmation is not None:
            self.chrome.confirmation['ask'].cancel()
        self.server.close(); self.client.close()
        self.tearDown_engine()

    def send(self, arguments, request_id=None):
        self.requests += 1
        self.chrome.event({'event': 'owner_sites', 'request_id': request_id or f'r{self.requests}', 'arguments': arguments})

    def settle(self, limit=15):
        deadline = time.monotonic() + limit
        while self.chrome.confirmation is not None and time.monotonic() < deadline:
            self.chrome.poll_confirmation()
            time.sleep(0.01)
        self.assertIsNone(self.chrome.confirmation, 'the confirmation never finished')

    def reply(self):
        while b'\n' not in self.inbox:
            self.inbox += self.client.recv(65536)
        line, self.inbox = self.inbox.split(b'\n', 1)
        return json.loads(line)

    def allowed(self):
        return [value for _, value in self.engine.store.iter_items('chrome:allow:')]

    def readonly(self, host):
        return self.engine.store.get('chrome:readonly:' + host)

    def refused(self, result, text):
        self.assertFalse(result['result']['ok'], result)
        self.assertIn(text, result['result']['error']['message'])

    def loosen_both(self):
        """A spoofed host's two loosening requests; returns the two replies."""
        replies = []
        for arguments in [{'command': 'allow', 'operation_id': self.operation},
                          {'command': 'readonly', 'site': 'https://locked.test/', 'enabled': False}]:
            self.send(arguments)
            self.settle()
            replies.append(self.reply())
        return replies

    def test_final_f7_spoofed_allow_and_readonly_off_write_nothing_without_a_success(self):
        cases = [('denied', dict(code=1, stderr='Not authorized.'), 'password was wrong'),
                 ('no agent', dict(code=2), 'no password dialog'),
                 ('dismissed', dict(code=3), 'dismissed'),
                 ('polkit error', dict(code=127, stderr='Error checking for authorization'), 'polkit could not check'),
                 ('untrusted caller', dict(code=127, stderr='Only trusted callers (e.g. uid 0 or an action owner)'), 'Only trusted callers')]
        for label, answer, reason in cases:
            with self.subTest(label):
                self.polkit.answer(**answer)
                for result in self.loosen_both():
                    self.assertFalse(result['result']['ok'], result)
                    self.refused(result, 'Nothing changed')
                    self.assertIn(reason, result['result']['error']['message'])
                self.assertEqual(self.allowed(), [])
                self.assertIs(self.readonly('locked.test'), True)
        self.assertEqual(len(self.polkit.calls()), 2 * len(cases))

    def test_final_f7_timeout_missing_polkit_and_unknown_process_refuse(self):
        self.polkit.answer(0, delay=5)
        self.chrome.confirm_timeout = 0.3
        for result in self.loosen_both():
            self.refused(result, 'timed out')
        self.chrome.confirm_timeout = 10
        self.chrome.pkcheck = str(self.polkit.directory / 'missing')
        for result in self.loosen_both():
            self.refused(result, 'polkit is unavailable')
        self.chrome.pkcheck = str(self.polkit.path)
        self.polkit.answer(0)
        for peer in [None, {**PEER, 'start': None}]:
            self.browser.peer = peer
            for result in self.loosen_both():
                self.refused(result, "connecting process can't be identified")
        self.assertEqual(self.allowed(), [])
        self.assertIs(self.readonly('locked.test'), True)

    def test_final_f7_success_writes_exactly_the_confirmed_change_for_the_connected_process(self):
        self.polkit.answer(0, delay=0.5)
        self.send({'command': 'allow', 'operation_id': self.operation})
        self.chrome.poll_confirmation()
        self.assertIsNotNone(self.chrome.confirmation)
        self.assertEqual(self.allowed(), [], 'nothing may be written while the dialog is up')
        self.settle()
        result = self.reply()
        self.assertTrue(result['result']['ok'], result)
        [entry] = self.allowed()
        self.assertEqual(entry['adapter']['kind'], 'gmail_send')
        self.assertEqual(self.engine.store.get('chrome:allow:' + result['result']['data']['id']), entry)
        [call] = self.polkit.calls()
        self.assertEqual(call[:6], ['--action-id', 'org.aresos.control.chrome-loosen', '--process', '4242,777,1000',
                                    '--allow-user-interaction', '--detail'])
        self.assertEqual(call[6:], ['change', "Don't ask again: gmail_send as Synthetic account on https://gmail.test "
                                              '(bcc hidden@example.invalid; to recipient@example.invalid)'])
        self.engine.store.write({'chrome:readonly:other.test': True}, 'chrome_test_readonly', 'Synthetic read-only site')
        self.polkit.answer(0)
        self.send({'command': 'readonly', 'site': 'https://locked.test/', 'enabled': False})
        self.settle()
        self.assertTrue(self.reply()['result']['ok'])
        self.assertIs(self.readonly('locked.test'), False)
        self.assertIs(self.readonly('other.test'), True)
        self.assertEqual(self.polkit.calls()[-1][-2:], ['change', 'Read-only off for locked.test'])

    def test_final_f7_cached_or_replayed_success_is_refused(self):
        for output in ['polkit.temporary_authorization_id=tmpauthz7\n', 'polkit.retains_authorization_after_challenge=1\n']:
            with self.subTest(output):
                self.polkit.answer(0, stdout=output)
                for result in self.loosen_both():
                    self.refused(result, 'reused an earlier confirmation')
                self.assertEqual(self.allowed(), [])
                self.assertIs(self.readonly('locked.test'), True)
        # A yes is spent on its one change: the same request again asks again.
        self.polkit.answer(0)
        arguments = {'command': 'allow', 'operation_id': self.operation}
        self.send(arguments, 'replayed'); self.settle()
        entry = self.reply()['result']['data']['id']
        self.send({'command': 'revoke', 'id': entry}); self.assertTrue(self.reply()['result']['ok'])
        calls = len(self.polkit.calls())
        self.polkit.answer(1)
        self.send(arguments, 'replayed'); self.settle()
        self.assertFalse(self.reply()['result']['ok'])
        self.assertEqual(len(self.polkit.calls()), calls + 1)
        self.assertTrue(self.engine.store.get('chrome:allow:' + entry)['revoked'])
        # A yes that arrives after the host changed belongs to nobody.
        self.polkit.answer(0, delay=0.5)
        self.send({'command': 'readonly', 'site': 'https://locked.test/', 'enabled': False})
        self.browser.connection_identity = 'a-later-host'
        self.settle()
        time.sleep(0.7)
        self.assertIs(self.readonly('locked.test'), True)
        self.client.settimeout(0.2)
        with self.assertRaises(socket.timeout):
            self.client.recv(1)

    def test_final_f7_one_dialog_at_a_time(self):
        self.polkit.answer(0, delay=0.5)
        self.send({'command': 'allow', 'operation_id': self.operation})
        self.send({'command': 'readonly', 'site': 'https://locked.test/', 'enabled': False})
        self.settle()
        self.assertEqual(len(self.polkit.calls()), 1)
        self.assertIs(self.readonly('locked.test'), True)
        second, first = self.reply(), self.reply()
        self.refused(second, 'waiting for the owner')
        self.assertTrue(first['result']['ok'])

    def test_final_f7_listing_revoking_and_readonly_on_need_no_password(self):
        self.polkit.answer(1)
        self.send({'command': 'list'})
        self.assertTrue(self.reply()['result']['ok'])
        self.send({'command': 'readonly', 'site': 'https://fresh.test/', 'enabled': True})
        self.assertTrue(self.reply()['result']['ok'])
        self.send({'command': 'readonly', 'site': 'https://other.test/'})
        self.assertTrue(self.reply()['result']['ok'])
        entry = self.call('sites', {'command': 'allow', 'operation_id': self.operation}, True)['data']['id']
        self.send({'command': 'revoke', 'id': entry})
        self.assertTrue(self.reply()['result']['ok'])
        self.assertTrue(self.engine.store.get('chrome:allow:' + entry)['revoked'])
        self.assertIs(self.readonly('fresh.test'), True)
        self.assertIs(self.readonly('other.test'), True)
        self.assertEqual(self.polkit.calls(), [])
        # Anything else is treated as loosening and checked before a dialog shows.
        for arguments in [{'command': 'readonly', 'site': 'https://x.test/', 'enabled': None}, {'command': 'unknown'}, 'allow']:
            self.send(arguments)
            self.assertFalse(self.reply()['result']['ok'])
        self.assertEqual(self.polkit.calls(), [])

    def test_final_f7_the_subject_is_the_process_that_connected(self):
        daemon = Daemon.__new__(Daemon)
        daemon.config, daemon.engine = {'owner_uid': 1000}, self.engine
        import selectors
        daemon.selector = selectors.DefaultSelector()
        self.chrome.bridge = bridge = __import__('aresos_control.chrome.bridge', fromlist=['Bridge']).Bridge()
        bridge.on_event = self.chrome.event
        self.chrome.maintenance = lambda: None

        class Peer:
            # A plain process of the owner's user, seen through SO_PEERCRED.
            def __init__(self, inner): self.inner = inner
            def getsockopt(self, *_): return struct.pack('3i', 5151, 1000, 1000)
            def __getattr__(self, name): return getattr(self.inner, name)

        server, client = socket.socketpair()
        try:
            client.sendall(json.dumps({'event': 'hello', 'session': 'spoof', 'version': '157.0.1.0'}).encode() + b'\n'
                           + json.dumps({'event': 'owner_sites', 'request_id': 's', 'arguments': {'command': 'allow', 'operation_id': self.operation}}).encode() + b'\n')
            self.polkit.answer(1)
            with patch.object(socket, 'SO_PEERCRED', 17, create=True), patch.object(confirm, 'start_time', return_value=31337):
                self.assertTrue(daemon.accept_chrome(Peer(server)))
            self.assertEqual(bridge.peer, {'pid': 5151, 'uid': 1000, 'start': 31337})
            daemon.drain_chrome_events(bridge.connection, buffered=True)
            self.settle()
            self.assertEqual(self.polkit.calls()[0][2:4], ['--process', '5151,31337,1000'])
            self.assertEqual(self.allowed(), [])
            bridge.close()
            self.assertIsNone(bridge.peer)
        finally:
            daemon.selector.close(); server.close(); client.close()

    @unittest.skipUnless(hasattr(socket, 'SO_PEERCRED') and Path('/proc/self/stat').exists(), 'Linux peer credentials')
    def test_final_f7_a_real_spoofing_process_on_the_socket_gets_nothing(self):
        daemon = Daemon.__new__(Daemon)
        daemon.config, daemon.engine = {'owner_uid': os.getuid()}, self.engine
        import selectors
        daemon.selector = selectors.DefaultSelector()
        from aresos_control.chrome.bridge import Bridge
        self.chrome.bridge = bridge = Bridge()
        bridge.on_event = self.chrome.event
        self.chrome.maintenance = lambda: None
        path = Path(tempfile.mkdtemp(dir=self.root)) / 'chrome.sock'
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path)); listener.listen(1)
        spoof = ('import json,socket,sys\n'
                 'c=socket.socket(socket.AF_UNIX);c.connect(sys.argv[1])\n'
                 "c.sendall(json.dumps({'event':'hello','session':'spoof','version':'157.0.1.0'}).encode()+b'\\n')\n"
                 "data=b''\n"
                 "for request in [{'command':'allow','operation_id':sys.argv[2]},{'command':'readonly','site':'https://locked.test/','enabled':False}]:\n"
                 "    c.sendall(json.dumps({'event':'owner_sites','request_id':'s','arguments':request}).encode()+b'\\n')\n"
                 "    while data.count(b'\\n')<(2 if request['command']=='readonly' else 1):\n"
                 "        data+=c.recv(65536)\n"
                 'print(data.decode(),end="")\n')
        process = subprocess.Popen([sys.executable, '-c', spoof, str(path), self.operation], stdout=subprocess.PIPE, text=True)
        try:
            connection, _ = listener.accept()
            start = int(Path(f'/proc/{process.pid}/stat').read_bytes().rsplit(b')', 1)[1].split()[19])
            self.polkit.answer(1)
            daemon.accept_chrome(connection)
            self.assertEqual(bridge.peer, {'pid': process.pid, 'uid': os.getuid(), 'start': start})
            for _ in range(2):
                deadline = time.monotonic() + 10
                while b'\n' not in bridge.buffer and time.monotonic() < deadline:
                    bridge.buffer += connection.recv(65536)
                daemon.drain_chrome_events(connection, buffered=True)
                self.settle()
            output, _ = process.communicate(timeout=10)
            for line in output.splitlines():
                self.assertFalse(json.loads(line)['result']['ok'])
            self.assertEqual([call[3] for call in self.polkit.calls()], [f'{process.pid},{start},{os.getuid()}'] * 2)
            self.assertEqual(self.allowed(), [])
            self.assertIs(self.readonly('locked.test'), True)
        finally:
            process.kill(); process.wait()
            listener.close(); daemon.selector.close(); bridge.close()


def real_polkit_check():
    spec = importlib.util.spec_from_file_location('polkit_check', ROOT / 'control/chrome/ci/polkit-check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Policy(unittest.TestCase):
    def test_final_f7_policy_asks_the_admin_password_every_time_and_names_the_service_user(self):
        text = POLICY.read_text()
        self.assertNotIn('keep', re.sub(r'<!--.*?-->', '', text, flags=re.S))
        action = ET.fromstring(text.encode()).find('action')
        self.assertEqual(action.get('id'), confirm.ACTION)
        defaults = {item.tag: item.text for item in action.find('defaults')}
        self.assertEqual(defaults, {'allow_any': 'no', 'allow_inactive': 'no', 'allow_active': 'auth_admin'})
        unit = (ROOT / 'control/packaging/aresos-toold.service').read_text()
        user = re.search(r'^User=(\S+)$', unit, re.M).group(1)
        owners = [item.text for item in action.findall('annotate') if item.get('key') == 'org.freedesktop.policykit.owner']
        self.assertEqual(owners, ['unix-user:' + user])
        self.assertIn('$(change)', action.find('message').text)
        self.assertEqual(confirm.command(PEER, 'x')[:2], ['/usr/bin/pkcheck', '--action-id'])

    def test_final_f7_policy_ships_with_the_hashed_packaging_and_is_named_for_the_image(self):
        sys.path.insert(0, str(ROOT / 'control/chrome'))
        from build import inputs
        self.assertIn(POLICY, list(inputs(ROOT)))
        readme = (ROOT / 'control/chrome/packaging/README.md').read_text()
        self.assertIn('/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy', readme)
        self.assertIn('pkcheck', readme)

    def test_final_f7_only_the_real_policy_reaches_the_install_tree(self):
        # The CI-only stand-in rule (allow_active on a seat-less container) and
        # the unowned test action live only inside polkit-check.py at run time.
        sys.path.insert(0, str(ROOT / 'control/chrome'))
        from build import inputs
        installed = list(inputs(ROOT))
        markers = ['polkit.addRule', 'polkit.Result', '-ci-unowned', '/etc/polkit-1']
        polkit = [path for path in installed if path.suffix in {'.policy', '.rules'} or '<policyconfig' in path.read_text(errors='replace')]
        self.assertEqual(polkit, [POLICY])
        self.assertEqual([path for path in installed if any(marker in path.read_text(errors='replace') for marker in markers)], [])
        self.assertNotIn(ROOT / 'control/chrome/ci/polkit-check.py', installed)
        readme = (ROOT / 'control/chrome/packaging/README.md').read_text()
        self.assertEqual(set(re.findall(r'/usr/share/polkit-1/[\w./-]*[\w]', readme)), {'/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy'})
        self.assertNotIn('/etc/polkit-1', readme)
        self.assertNotIn('rules.d', readme)

    def test_final_f7_the_real_polkit_check_requires_each_dialog_to_name_its_change(self):
        check = real_polkit_check()
        header = '\x1b[1;31m==== AUTHENTICATING FOR org.aresos.control.chrome-loosen ====\r\n\x1b[0m'
        def shown(message, prompts=1):
            tail = '\r\nAuthenticating as: owner\r\nPassword: \r\n\x1b[1;31m==== AUTHENTICATION COMPLETE ====\r\n\x1b[0m'
            return {'transcript': header + message + tail if prompts else '', 'prompts': prompts}
        intro = "Claude's Chrome tools: confirm this change with your password. "
        self.assertEqual(check.expected_message(check.CHANGE), intro + check.CHANGE)
        self.assertEqual(check.dialog_messages(shown(intro + check.CHANGE)['transcript']), [intro + check.CHANGE])
        self.assertEqual(check.dialog_problems(shown(intro + check.CHANGE), check.CHANGE, True), [])
        self.assertEqual(check.dialog_problems(shown(intro + check.OTHER_CHANGE), check.OTHER_CHANGE, True), [])
        # polkit dropping $(change), the wrong change, no dialog at all.
        self.assertTrue(check.dialog_problems(shown(intro), check.CHANGE, True))
        self.assertTrue(check.dialog_problems(shown(intro + '$(change)'), check.CHANGE, True))
        self.assertTrue(check.dialog_problems(shown(intro + check.CHANGE), check.OTHER_CHANGE, True))
        self.assertTrue(check.dialog_problems(shown('', prompts=0), check.CHANGE, True))
        self.assertEqual(check.dialog_problems(shown('', prompts=0), check.CHANGE, False), [])
        self.assertNotEqual(check.CHANGE, check.OTHER_CHANGE)
        # Every case goes through the dialog check.
        self.assertIn("problems += dialog_problems(result, result['change'], prompted)", inspect.getsource(check.main))

    def test_final_f7_the_real_polkit_check_runs_on_pull_requests_and_the_shim_is_gone(self):
        workflows = ROOT / '.github/workflows'
        polkit = (workflows / 'control-chrome-polkit.yml').read_text()
        trigger = polkit.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
        self.assertRegex(trigger, r'^  pull_request:\n    branches: \[main\]\n    paths: \[')
        paths = set(re.findall(r"'([^']+)'", trigger.split('workflow_dispatch')[0]))
        self.assertLessEqual({'control/aresos_control/chrome/confirm.py', 'control/chrome/packaging/org.aresos.control.chrome-loosen.policy',
                              'control/chrome/ci/polkit-check.py', '.github/workflows/control-chrome-polkit.yml'}, paths)
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertNotIn('workflow_call', polkit)
        # The dispatch shim in control-chrome-check.yml served only until this run was green.
        self.assertNotIn('polkit', (workflows / 'control-chrome-check.yml').read_text())

    def test_final_f7_dialog_text_is_one_bounded_line_without_markup(self):
        self.assertEqual(confirm.shown('a\n<b>x</b> & $(y)\u202e'), 'a ?b?x?/b? ? ?(y)?')
        self.assertEqual(len(confirm.shown('x' * 500, 300)), 301)
        self.assertEqual(confirm.loosening({'command': 'readonly', 'site': 'x'}), False)
        for arguments in [{'command': 'allow'}, {'command': 'readonly', 'enabled': False}, {'command': 'readonly', 'enabled': 0}, None, {}]:
            self.assertTrue(confirm.loosening(arguments), arguments)

    def test_final_f7_tool_text_says_where_the_password_is_asked(self):
        from aresos_control.definitions import BY_NAME
        text = BY_NAME['chrome_sites'].purpose
        self.assertIn('Requires sudo on admin.sock', text)
        self.assertIn('ask for his password in a polkit dialog, once for each change', text)


if __name__ == '__main__':
    unittest.main()
