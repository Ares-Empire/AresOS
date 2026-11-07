"""Raw JSON regressions: refuse before approval/adapter work, and actionable cleanup."""
import copy
from contextlib import ExitStack, redirect_stdout
import io
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from aresos_control import cli
from aresos_control.common import JSONInputError, canonical, visible
from aresos_control.engine import Engine
from aresos_control.protocol import receive
from raw_json_test_support import RawMCP, duplicate_arguments, socket_request, mcp_request
import test_review_fixes_12 as round12
from support import CERT, MailCase


class PlainJSON14(unittest.TestCase):
    setUp = round12.PlainQuestions12.setUp
    call = round12.PlainQuestions12.call
    data = round12.PlainQuestions12.data
    approval = round12.PlainQuestions12.approval
    compose = round12.PlainQuestions12.compose
    reference = round12.PlainQuestions12.reference

    def test_round14_raw_mail_socket_and_cli_refuse_before_validation_and_execution(self):
        items = [self.mail.named_item(self.reference())]
        before = copy.deepcopy(self.imap.boxes)
        for verb, args in (('send', self.compose()), ('delete', {'items': items, 'mode': 'permanent'}),
                           ('folder_delete', {'account': 'box', 'folder': 'Target'})):
            approval = self.approval(verb, args)
            for label, raw in duplicate_arguments(approval):
                with self.subTest(verb=verb, duplicate=label), ExitStack() as stack:
                    guards = [stack.enter_context(patch.object(obj, name, wraps=getattr(obj, name))) for obj, name in (
                        (self.engine, 'request'), (self.engine, 'reserve'), (self.engine, 'submit'), (self.engine, 'stage'),
                        (self.mail, 'revalidate'), (self.mail, 'has_submission_evidence'), (self.mail, 'execute'))]
                    guards += [stack.enter_context(patch('aresos_control.engine.validate')),
                               stack.enter_context(patch('aresos_control.engine.digest'))]
                    caller, service = socket.socketpair()
                    with caller, service:
                        caller.sendall((socket_request('mail_' + verb, raw, label == 'envelope') + '\n').encode())
                        with self.assertRaises(JSONInputError) as error:
                            self.engine.request(receive(service))
                        self.assertEqual(error.exception.code, 'stale_approval')
                    output = io.StringIO()
                    with patch.object(cli, 'Proxy') as proxy, redirect_stdout(output):
                        self.assertEqual(cli.main({}, ['mail', verb, '--input', raw]), 1)
                    self.assertEqual(json.loads(output.getvalue())['error']['code'], 'stale_approval')
                    proxy.assert_not_called()
                    for guard in guards:
                        guard.assert_not_called()
                op = self.engine.operation(approval['operation_id'])
                self.assertEqual((op['state'], op['stages']), ('reserved', {}))
        self.assertEqual(self.imap.boxes, before)
        self.assertEqual(self.imap.mutations, [])

    def test_round14_delete_refusal_names_only_bad_references_and_healthy_batch_prepares(self):
        self.imap.boxes['Source'][2] = self.imap.boxes['Source'][2].replace(b'sender@mail.invalid', b'"Bad\x01 Name" <sender@mail.invalid>')
        # The reference's message-id is untrusted too: it must be escaped in feedback.
        self.imap.boxes['Source'][2] = self.imap.boxes['Source'][2].replace(self.imap.mid.encode(), b'<bad\x01@mail.invalid>')
        bad = {**self.reference(2), 'message_id': '<bad\x01@mail.invalid>'}
        refs = [self.reference(1), bad, self.reference(3)]
        items = [self.mail.named_item(ref) for ref in refs]
        before = len(self.engine.store.items('op:'))
        for mode in ('trash', 'permanent'):
            result = self.call('prepare_delete', {'items': items, 'mode': mode})
            self.assertEqual(result['error']['code'], 'invalid_input', result)
            text = result['error']['message']
            self.assertIn(canonical(visible([bad])), text)
            self.assertNotIn(canonical(refs[0]), text)
            self.assertNotIn(canonical(refs[2]), text)
            self.assertNotIn('\x01', text)
            self.assertIn('Leave these out of the selection and delete them in your mail program.', text)
            self.assertEqual(len(self.engine.store.items('op:')), before)
            prepared = self.approval('delete', {'items': [items[0], items[2]], 'mode': mode})
            self.assertEqual(len(prepared['description']['items']), 2)
            before += 1


class ServerJSON14(MailCase):
    def test_round14_real_proxy_socket_cli_duplicates_no_arrival_or_deletion_then_once(self):
        from aresos_control.mail.transport import folders
        from imap_guard_fixture import GuardedIMAPFixture
        from smtp_fixture import SMTPFixture

        owner, service_uid = 26201, 26202
        reference = self.fixture(subject='Duplicate protected source')
        with GuardedIMAPFixture('dovecot', 993) as imap, SMTPFixture(self.root) as smtp:
            account = {**self.account, 'imap_host': 'localhost', 'imap_port': imap.port,
                       'smtp_host': 'localhost', 'smtp_port': smtp.port, 'safe_folder_delete': True}
            self.engine.store.write({'mail:account:box': account}, 'fixture', 'Synthetic duplicate-key account')
            self.data('folder_create', {'account': 'box', 'name': 'DuplicateLeaf'})
            approvals = [('send', self.approval()), ('delete', self.delete_approval([reference], 'permanent')),
                         ('folder_delete', self.data('prepare_folder_delete', {'account': 'box', 'folder': 'DuplicateLeaf'})['approval'])]
            self.engine.close()
            self.root.chmod(0o755)
            (self.root / 'sockets').mkdir(mode=0o711)
            def state_paths():
                return [self.root / name for name in ('state', 'independent', 'sockets')] + list((self.root / 'state').rglob('*')) + list((self.root / 'independent').rglob('*'))
            for path in state_paths():
                os.chown(path, service_uid, service_uid)
            config = {'owner_uid': owner, 'state_dir': str(self.root / 'state'), 'evidence_dir': str(self.root / 'independent'),
                      'socket_dir': str(self.root / 'sockets')}
            config_file = self.root / 'strict-service.json'
            config_file.write_text(json.dumps(config))
            proxy_config = {'act_socket': str(self.root / 'sockets/act.sock')}
            prefix = ['/usr/bin/setpriv', '--reuid', str(owner), '--regid', str(owner), '--clear-groups', sys.executable]
            daemon = subprocess.Popen(['/usr/bin/setpriv', '--reuid', str(service_uid), '--regid', str(service_uid), '--clear-groups',
                                       sys.executable, '-m', 'aresos_control.daemon', '--config', str(config_file)],
                                      env={**os.environ, 'SSL_CERT_FILE': str(CERT / 'tls.crt')}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            def owner_call(verb, raw, terminal=False, envelope=False):
                if terminal:
                    code = 'import json,sys; from aresos_control.cli import main; raise SystemExit(main(json.loads(sys.argv[1]),sys.argv[2:]))'
                    args = [json.dumps(proxy_config), 'mail', verb, '--input', raw]
                else:
                    code = 'import socket,sys; s=socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.sendall((sys.argv[2]+"\\n").encode()); print(s.makefile().readline())'
                    args = [proxy_config['act_socket'], socket_request('mail_' + verb, raw, envelope)]
                proc = subprocess.run([*prefix, '-c', code, *args], capture_output=True, text=True, timeout=20)
                result = json.loads(proc.stdout)
                self.assertEqual(proc.returncode, int(terminal and not result['ok']), proc.stdout + proc.stderr)
                return result
            def status(operation_id):
                # operation_status intentionally probes Sent. Inspect the durable
                # row read-only so our assertion cannot itself reach the adapter.
                import sqlite3
                with sqlite3.connect('file:' + str(self.root / 'state/control.sqlite') + '?mode=ro', uri=True) as db:
                    return json.loads(db.execute('SELECT v FROM kv WHERE k=?', ('op:' + operation_id,)).fetchone()[0])
            try:
                deadline = time.monotonic() + 10
                while not (self.root / 'sockets/act.sock').exists():
                    if daemon.poll() is not None or time.monotonic() >= deadline:
                        self.fail('Duplicate-key test daemon failed to start')
                    time.sleep(0.03)
                code = 'import json,sys; from aresos_control.proxy import main; main("mail",json.loads(sys.argv[1]))'
                with RawMCP([*prefix, '-c', code, json.dumps(proxy_config)]) as client:
                    for verb, approval in approvals:
                        commands, arrivals = list(imap.commands), smtp.arrivals()
                        for label, raw in duplicate_arguments(approval):
                            with self.subTest(verb=verb, duplicate=label):
                                response = client.exchange(mcp_request(label, verb, raw, label == 'envelope'))
                                self.assertEqual(response['id'], label)
                                self.assertEqual(response['error']['data']['code'], 'stale_approval', response)
                                for result in (owner_call(verb, raw, envelope=label == 'envelope'), owner_call(verb, raw, terminal=True)):
                                    self.assertEqual(result['error']['code'], 'stale_approval', result)
                                op = status(approval['operation_id'])
                                self.assertEqual((op['state'], op['stages']), ('reserved', {}))
                                self.assertEqual(imap.commands, commands, 'Refusal reached IMAP/evidence/execution')
                                self.assertEqual(smtp.arrivals(), arrivals, 'Refusal reached SMTP')
                        raw = json.dumps(approval)
                        correct = client.exchange(mcp_request('correct', verb, raw))['result']['structuredContent']
                        self.assertTrue(correct['ok'], correct)
                        self.assertEqual(correct['data']['operation']['state'], 'done')
                        commands, arrivals = list(imap.commands), smtp.arrivals()
                        for result in (owner_call(verb, raw), owner_call(verb, raw, terminal=True),
                                       client.exchange(mcp_request('replay', verb, raw))['result']['structuredContent']):
                            self.assertTrue(result['ok'], result)
                            self.assertEqual(result['data'], correct['data'])
                        self.assertEqual(imap.commands, commands, 'Replay called Mail adapter')
                        self.assertEqual(smtp.arrivals(), arrivals, 'Replay submitted twice')
            finally:
                daemon.terminate()
                stdout, stderr = daemon.communicate(timeout=10)
                for path in state_paths():
                    os.chown(path, os.geteuid(), os.getegid())
                self.engine = Engine(self.root / 'state', self.root / 'independent')
                self.mail = self.engine.adapters['mail']
                self.assertEqual(daemon.returncode, 0, stdout + stderr)
            self.assertEqual(len(smtp.arrivals()), 1)
            with self.mail.transport.imap(account) as conn:
                self.assertNotIn('DuplicateLeaf', [f['name'] for f in folders(conn)])
            self.assertFalse(self.call('read', {'reference': reference})['ok'])
            self.assertEqual(sum(command == b'DELETE' for command, _ in imap.commands), 1)
            self.assertEqual(sum(command == b'UID' and args.startswith(b'EXPUNGE ') for command, args in imap.commands), 1)
