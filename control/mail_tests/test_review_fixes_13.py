"""Round 13 regressions: complete mailboxes and approval order before execution."""
import copy
from contextlib import ExitStack
from email.message import EmailMessage
from itertools import permutations
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.parse import quote
from unittest.mock import patch

from aresos_control.common import QUESTION_LIMIT, Refused, approval_input, visible
from aresos_control.mail import codec
from aresos_control.mail.questions import people, question, short
from aresos_control.protocol import receive, send
import test_review_fixes_12 as round12
from support import CERT, MailCase


class PlainApprovals13(unittest.TestCase):
    # Reuse the in-memory IMAP setup, without inheriting/repeating round 12's tests.
    setUp = round12.PlainQuestions12.setUp
    call = round12.PlainQuestions12.call
    data = round12.PlainQuestions12.data
    approval = round12.PlainQuestions12.approval
    compose = round12.PlainQuestions12.compose
    reference = round12.PlainQuestions12.reference

    def source(self, sender, target=None):
        msg = EmailMessage()
        msg['Message-ID'] = self.imap.mid
        if target:
            msg['List-Unsubscribe'] = '<' + target + '>'
        msg.set_content('Synthetic source')
        # Python 3.15's generator can encode earlier mailboxes into the last
        # display name when folding long names. Supply the exact incoming header.
        raw_from = ('From: ' + sender.replace(', ', ',\r\n ') + '\r\n').encode('ascii')
        self.imap.boxes['Source'][1] = raw_from + msg.as_bytes(policy=codec.SMTP_POLICY)

    def test_round13_unsubscribe_long_name_and_117_character_address_real_preparation(self):
        long_name = 'Mom ' + 'x' * 200
        long_address = 'a' * 64 + '@' + 'b' * 40 + '.example.org'
        self.assertEqual(len(long_address), 117)
        for recipient in (long_name + ' <stranger@example.org>', long_address):
            target = 'mailto:' + quote(recipient)
            self.source(long_name + ' <sender@example.org>', target)
            approval = self.approval('unsubscribe', {'reference': self.reference(), 'target': target})
            self.assertIn('Unsubscribe from ' + short(long_name) + ' <sender@example.org>', approval['question'])
            self.assertIn('by sending a mail to ' + (short(long_name) + ' <stranger@example.org>' if recipient != long_address else long_address) + '?', approval['question'])
            self.assertEqual(approval['description']['to'], [recipient])

    def test_round13_delete_multiple_long_named_senders_and_exact_mailbox_count(self):
        senders = ['Name ' + 'x' * 200 + f' <sender{i}@example.org>' for i in range(5)]
        for count in (2, 5):
            self.source(', '.join(senders[:count]))
            self.assertEqual([a.addr_spec for a in codec.parse(self.imap.boxes['Source'][1])['From'].addresses],
                             [f'sender{i}@example.org' for i in range(count)])
            item = self.mail.named_item(self.reference())
            approval = self.approval('delete', {'items': [item], 'mode': 'permanent'})
            for i in range(min(count, 3)):
                self.assertIn(f'<sender{i}@example.org>', approval['question'])
            if count == 5:
                self.assertIn('and 2 more', approval['question'])
                self.assertNotIn('<sender3@example.org>', approval['question'])
            self.assertEqual(approval['description']['items'][0]['from'], item['from'])
        # Multiple header values are counted as mailboxes rather than as headers.
        self.assertEqual(people(['A <a@example.org>, B <b@example.org>', 'c@example.org', 'd@example.org']),
                         'A <a@example.org>, B <b@example.org>, c@example.org and 1 more')

    def test_round13_unparsable_and_original_defective_from_refuse_with_reason(self):
        for header in ('', 'Mom', 'Mom <>', 'Mom <stranger@example.org', 'good@example.org, bad'):
            with self.subTest(header=header):
                with self.assertRaises(Refused) as error:
                    people([header])
                self.assertEqual(error.exception.code, 'invalid_input')
                self.assertIn('missing address or defective address header', str(error.exception))
                # Raw IMAP input preserves defects that str(header) could silently repair.
                self.imap.boxes['Source'][1] = (f'From: {header}\r\nMessage-ID: {self.imap.mid}\r\n\r\nBody').encode()
                item = self.mail.named_item(self.reference())
                before = len(self.engine.store.items('op:'))
                result = self.call('prepare_delete', {'items': [item], 'mode': 'permanent'})
                self.assertEqual(result['error']['code'], 'invalid_input', result)
                self.assertIn('complete mailbox', result['error']['message'])
                self.assertEqual(len(self.engine.store.items('op:')), before)

    def test_round13_addresses_and_folder_names_over_question_cap_refuse_without_cutting(self):
        address = 'x' * (QUESTION_LIMIT + 1) + '@example.org'
        self.assertEqual(people([address]), address)
        self.source(address)
        item = self.mail.named_item(self.reference())
        before = len(self.engine.store.items('op:'))
        result = self.call('prepare_delete', {'items': [item], 'mode': 'permanent'})
        self.assertEqual(result['error']['code'], 'asking_input_too_large', result)
        self.assertEqual(len(self.engine.store.items('op:')), before)
        for verb in ('folder_delete', 'onboarding_folder_probe'):
            details = {'folder': 'Projects/' + 'x' * QUESTION_LIMIT}
            text = question(verb, details)
            self.assertIn(details['folder'], text)
            with self.assertRaises(Refused) as error:
                approval_input('fixed', details, text)
            self.assertEqual(error.exception.code, 'asking_input_too_large')
        self.assertEqual(visible(people(['"' + 'x' * 78 + '\u202e' + '" <whole@example.org>'])),
                         'x' * 78 + '… <whole@example.org>')

    def test_round13_mail_all_wrong_orders_stop_before_submit_stage_evidence_or_adapter(self):
        items = [self.mail.named_item(self.reference())]
        before = copy.deepcopy(self.imap.boxes)
        for verb, args in (('send', self.compose()), ('delete', {'items': items, 'mode': 'permanent'}),
                           ('folder_delete', {'account': 'box', 'folder': 'Target'})):
            approval = self.approval(verb, args)
            wrong = [{k: approval[k] for k in order} for order in permutations(approval) if list(order) != list(approval)]
            wrong += [{**approval, 'extra': 1}, {k: v for k, v in approval.items() if k != 'question'}]
            for altered in wrong:
                with self.subTest(verb=verb, keys=list(altered)), ExitStack() as stack:
                    guards = [stack.enter_context(patch.object(obj, name, wraps=getattr(obj, name))) for obj, name in
                              ((self.engine, 'submit'), (self.engine, 'stage'), (self.mail, 'revalidate'),
                               (self.mail, 'has_submission_evidence'), (self.mail, 'execute'))]
                    caller, service = socket.socketpair()
                    with caller, service:
                        send(caller, {'v': 1, 'method': 'call', 'action': 'mail_' + verb, 'arguments': altered})
                        payload = receive(service)
                        self.assertEqual(list(payload['arguments']), list(altered))
                        send(service, self.engine.request(payload))
                        result = receive(caller)
                    self.assertEqual(result['error']['code'], 'stale_approval', result)
                    for guard in guards:
                        guard.assert_not_called()
                op = self.engine.operation(approval['operation_id'])
                self.assertEqual((op['state'], op['stages']), ('reserved', {}))
        self.assertEqual(self.imap.boxes, before)
        self.assertEqual(self.imap.mutations, [])


class ServerApprovals13(MailCase):
    def test_round13_real_mcp_socket_cli_wrong_orders_no_arrival_or_imap_then_once(self):
        import asyncio
        from aresos_control.engine import Engine
        from aresos_control.mail.transport import folders
        from imap_guard_fixture import GuardedIMAPFixture
        from smtp_fixture import SMTPFixture

        owner, service = 26101, 26102
        reference = self.fixture(subject='Order protected source')
        with GuardedIMAPFixture('dovecot', 993) as imap, SMTPFixture(self.root) as smtp:
            account = {**self.account, 'imap_host': 'localhost', 'imap_port': imap.port,
                       'smtp_host': 'localhost', 'smtp_port': smtp.port, 'safe_folder_delete': True}
            self.engine.store.write({'mail:account:box': account}, 'fixture', 'Guarded synthetic order account')
            self.data('folder_create', {'account': 'box', 'name': 'OrderLeaf'})
            approvals = [('send', self.approval()), ('delete', self.delete_approval([reference], 'permanent')),
                         ('folder_delete', self.data('prepare_folder_delete', {'account': 'box', 'folder': 'OrderLeaf'})['approval'])]
            self.engine.close()
            self.root.chmod(0o755)
            def state_paths():
                return [self.root / name for name in ('state', 'independent', 'sockets')] + list((self.root / 'state').rglob('*')) + list((self.root / 'independent').rglob('*'))
            (self.root / 'sockets').mkdir(mode=0o711)
            for path in state_paths():
                os.chown(path, service, service)
            config = {'owner_uid': owner, 'state_dir': str(self.root / 'state'), 'evidence_dir': str(self.root / 'independent'),
                      'socket_dir': str(self.root / 'sockets')}
            from boundary_test_support import install_boundary
            install_boundary('/etc/claude-code')
            config_file = self.root / 'order-service.json'
            config_file.write_text(json.dumps(config))
            proxy_config = {'act_socket': str(self.root / 'sockets/act.sock')}
            daemon = subprocess.Popen(['/usr/bin/setpriv', '--reuid', str(service), '--regid', str(service), '--clear-groups',
                                       sys.executable, '-m', 'aresos_control.daemon', '--config', str(config_file)],
                                      env={**os.environ, 'SSL_CERT_FILE': str(CERT / 'tls.crt')}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            def owner_call(verb, approval, cli=False):
                if cli:
                    code = 'import json,sys; from aresos_control.cli import main; raise SystemExit(main(json.loads(sys.argv[1]),sys.argv[2:]))'
                    args = [json.dumps(proxy_config), 'mail', verb, '--input', json.dumps(approval)]
                else:
                    # Independent raw JSON socket caller, with no result-presentation helper.
                    code = 'import json,socket,sys; s=socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.sendall((sys.argv[2]+"\\n").encode()); print(s.makefile().readline())'
                    args = [proxy_config['act_socket'], json.dumps({'v': 1, 'method': 'call', 'action': 'mail_' + verb, 'arguments': approval})]
                proc = subprocess.run(['/usr/bin/setpriv', '--reuid', str(owner), '--regid', str(owner), '--clear-groups', sys.executable,
                                       '-c', code, *args], capture_output=True, text=True, timeout=20)
                self.assertEqual(proc.returncode, int(cli and list(approval) != ['question', 'operation_id', 'description']), proc.stdout + proc.stderr)
                return json.loads(proc.stdout)
            try:
                deadline = time.monotonic() + 10
                while not (self.root / 'sockets/act.sock').exists():
                    if daemon.poll() is not None or time.monotonic() >= deadline:
                        self.fail('Order test daemon failed to start')
                    time.sleep(0.03)
                async def conversation():
                    from mcp import Client as MCPClient, StdioServerParameters
                    code = 'import json,sys; from aresos_control.proxy import main; main("mail",json.loads(sys.argv[1]))'
                    params = StdioServerParameters(command='/usr/bin/setpriv', args=['--reuid', str(owner), '--regid', str(owner), '--clear-groups',
                                                    sys.executable, '-c', code, json.dumps(proxy_config)],
                                                   env={'PYTHONPATH': os.environ['PYTHONPATH'], 'PATH': '/usr/bin:/bin'})
                    async with MCPClient(params) as client:
                        for verb, approval in approvals:
                            commands, arrivals = list(imap.commands), smtp.arrivals()
                            for order in permutations(approval):
                                if list(order) == list(approval):
                                    continue
                                altered = {k: approval[k] for k in order}
                                results = [(await client.call_tool(verb, altered)).structured_content,
                                           owner_call(verb, altered), owner_call(verb, altered, cli=True)]
                                for result in results:
                                    self.assertEqual(result['error']['code'], 'stale_approval', result)
                                self.assertEqual(imap.commands, commands, 'Rejected approval reached IMAP')
                                self.assertEqual(smtp.arrivals(), arrivals, 'Rejected approval reached SMTP')
                            correct = (await client.call_tool(verb, approval)).structured_content
                            self.assertTrue(correct['ok'], correct)
                            self.assertEqual(correct['data']['operation']['state'], 'done', correct)
                            commands, arrivals = list(imap.commands), smtp.arrivals()
                            for repeat in (owner_call(verb, approval), owner_call(verb, approval, cli=True),
                                           (await client.call_tool(verb, approval)).structured_content):
                                self.assertTrue(repeat['ok'], repeat)
                                self.assertEqual(repeat['data'], correct['data'])
                            self.assertEqual(imap.commands, commands, 'Replay called adapter')
                            self.assertEqual(smtp.arrivals(), arrivals, 'Replay submitted again')
                asyncio.run(conversation())
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
                self.assertNotIn('OrderLeaf', [f['name'] for f in folders(conn)])
            result = self.call('read', {'reference': reference})
            self.assertFalse(result['ok'], result)
            self.assertEqual(sum(command == b'DELETE' for command, _ in imap.commands), 1)
            self.assertEqual(sum(command == b'UID' and args.startswith(b'EXPUNGE ') for command, args in imap.commands), 1)
