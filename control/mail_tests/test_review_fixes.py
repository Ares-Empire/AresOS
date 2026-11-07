"""Regressions for the five findings in the package 19 review."""
from email.message import EmailMessage
import base64
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import io
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from unittest.mock import patch

from support import MailCase, CERT
from imap_guard_fixture import GuardedIMAPFixture
from smtp_fixture import SMTPFixture
from aresos_control.common import canonical, visible
from aresos_control.engine import Engine
from aresos_control.mail import codec
from aresos_control.mail.transport import context, ok, quote


class ReviewFixes(MailCase):
    @contextmanager
    def secret_frontend(self, password, echo=b'Synthetic failure'):
        with GuardedIMAPFixture(host='dovecot', port=993, error_text=echo, backend_password='pass') as frontend:
            self.account = {**self.account, 'imap_host':'localhost', 'imap_port':frontend.port}
            self.mail.transport.store_password('box', password)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'IMAP failure frontend')
            yield frontend

    def prepare(self, composition):
        return self.call('prepare_send', {k: composition[k] for k in ('composition_id', 'composition_hash')})

    def save(self, text):
        comp = self.compose(text=text)
        return self.data('draft_save', {k: comp[k] for k in ('composition_id', 'composition_hash')})['reference']

    def test_review_1_draft_reload_full_text_and_21000_characters_refused(self):
        for text in ('Entire authored draft body', 'x' * 21000):
            with self.subTest(size=len(text)):
                ref = self.save(text)
                comp = self.data('compose', {'account':'box', 'mode':'draft', 'reference':ref})
                result = self.prepare(comp)
                if len(text) > 20000:
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'asking_input_too_large')
                    self.assertIn('Nothing was reserved', result['error']['message'])
                else:
                    self.assertTrue(result['ok'], result)
                    self.assertIn(visible(text), result['data']['approval']['description']['generated_parts'][0]['text'])

    def test_review_1_owner_draft_plain_and_differing_readable_html_with_links(self):
        msg = EmailMessage()
        msg['From'], msg['To'], msg['Message-ID'] = self.owner, 'one@mail.invalid', '<html-draft@mail.invalid>'
        msg.set_content('Plain draft words')
        msg.add_alternative('<p>Different HTML words <a href="https://link.invalid/path">Link</a></p>', subtype='html')
        ref = self.fixture(self.account['special']['drafts'], msg=msg)
        comp = self.data('compose', {'account':'box', 'mode':'draft', 'reference':ref})
        result = self.prepare(comp)
        self.assertTrue(result['ok'], result)
        parts = result['data']['approval']['description']['generated_parts']
        self.assertIn('Plain draft words', parts[0]['text'])
        self.assertIn('Different HTML words Link (https://link.invalid/path)', parts[1]['text'])

    def test_review_1_moved_and_copied_draft_reply_and_both_forwards_keep_provenance(self):
        self.data('folder_create', {'account':'box', 'name':'Draft-copies'})
        for verb in ('move', 'copy'):
            for text in ('Authored words must remain visible', 'x' * 21000):
                ref = self.save(text)
                ref = self.data(verb, {'references':[ref], 'target':'Draft-copies'})['items'][0]
                self.assertIn(codec.AUTHORED_HEADER, self.mail.message(ref)['msg'])
                for mode, style in (('reply',None), ('reply_all',None), ('forward','inline'), ('forward','attachment')):
                    with self.subTest(verb=verb, size=len(text), mode=mode, style=style):
                        args = {'account':'box', 'mode':mode, 'reference':ref}
                        if style:
                            args.update(forward_as=style, to=['one@mail.invalid'])
                        comp = self.data('compose', args)
                        result = self.prepare(comp)
                        if len(text) > 20000:
                            self.assertFalse(result['ok'], result)
                            self.assertEqual(result['error']['code'], 'asking_input_too_large')
                        else:
                            self.assertTrue(result['ok'], result)
                            self.assertIn(text, canonical(result['data']['approval']))

    def assert_no_private_headers(self, msg, address):
        self.assertNotIn(address, msg.as_string())
        for part in msg.walk():
            self.assertIsNone(part.get('Bcc'))
            self.assertIsNone(part.get('Resent-Bcc'))
            if not part.is_multipart() and (part.get_filename() or '').endswith('.eml'):
                self.assert_no_private_headers(codec.parse(codec.decoded(part)), address)

    def assert_forward_clean(self, ref, secret):
        for style in ('inline','attachment'):
            with self.subTest(style=style):
                comp = self.data('compose', {'account':'box', 'mode':'forward', 'reference':ref,
                    'forward_as':style, 'to':['two@mail.invalid'], 'text':'Review this'})
                result = self.prepare(comp)
                self.assertTrue(result['ok'], result)
                approval = result['data']['approval']
                for att in approval['description']['attachments']:
                    if att['name'].endswith('.eml'):
                        self.assertIn('Bcc', att['transformation'])
                        self.assertEqual(att['sha256'], codec.sha256(self.engine.blobs.read(att['sha256'])))
                sent = self.send(approval)
                self.assertEqual(sent['state'], 'done', sent)
                raw, = self.arrivals('two@mail.invalid', sent['stages']['message_id'])
                msg = codec.parse(raw)
                self.assert_no_private_headers(msg, secret)
                for part, approved in zip(msg.iter_attachments(), approval['description']['attachments']):
                    self.assertEqual(codec.sha256(codec.decoded(part)), approved['sha256'])

    def test_review_2_forward_service_sent_bcc_copy_and_reply_headers(self):
        secret = 'private-forward@mail.invalid'
        sent = self.send(self.approval(bcc=[secret]))
        ref, = self.data('operation_status', {'operation_id':sent['id']})['evidence']['sent']
        self.assertEqual(str(self.mail.message(ref)['msg']['Bcc']), secret)
        self.assert_forward_clean(ref, secret)
        for mode in ('reply','reply_all'):
            comp = self.data('compose', {'account':'box','mode':mode,'reference':ref,'text':'Follow up'})
            msg = codec.parse(self.mail.mime(self.mail.composition(comp), '<reply-check@mail.invalid>'))
            self.assert_no_private_headers(msg, secret)
            self.assertNotIn(secret, canonical(comp['mail']['to'] + comp['mail']['cc']))

    def test_review_2_nested_rfc822_and_frozen_eml_bcc_removed(self):
        secret = 'private-nested@mail.invalid'
        inner = EmailMessage()
        inner['From'], inner['To'], inner['Bcc'] = self.peer, self.owner, secret
        inner['Resent-Bcc'] = secret
        inner['Message-ID'] = '<nested-' + uuid.uuid4().hex + '@mail.invalid>'
        inner.set_content('Nested forwarded body')
        for frozen in (False,True):
            outer = EmailMessage()
            outer['From'], outer['To'], outer['Message-ID'] = self.peer, self.owner, '<outer-' + uuid.uuid4().hex + '@mail.invalid>'
            outer['Resent-Bcc'] = secret
            outer.set_content('Outer body')
            if frozen:
                outer.add_attachment(inner.as_bytes(policy=codec.SMTP_POLICY), maintype='application', subtype='octet-stream', filename='nested.eml')
            else:
                outer.add_attachment(inner)
            ref = self.fixture(msg=outer)
            self.assert_forward_clean(ref, secret)

    def test_review_3_echoed_imap_password_after_preflight_and_mid_delete_is_never_persisted(self):
        password = 'Synthetic-credential-7!'
        encodings = [password, base64.b64encode(password.encode()).decode(),
                     base64.b64encode(('\0' + self.account['username'] + '\0' + password).encode()).decode()]
        echo = ('Untrusted backend diagnostic ' + ' '.join(encodings)).encode()
        with self.secret_frontend(password, echo) as frontend:
            frontend.mode = 'echo_login'
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                response = self.call('search', {'account':'box'})
            self.assertFalse(response['ok'], response)
            self.assert_clean_diagnostics([response, output.getvalue()], encodings)
            frontend.mode = 'guard'
            for mode in ('echo_login','echo_store','echo_expunge','echo_disconnect_expunge'):
                with self.subTest(mode=mode):
                    ref = self.fixture()
                    approval = self.delete_approval([ref], 'permanent')
                    original = self.mail.execute
                    def fail_after_preflight(op, stage):
                        frontend.mode = mode
                        return original(op, stage)
                    output = io.StringIO()
                    with redirect_stdout(output), redirect_stderr(output), patch.object(self.mail,'execute',side_effect=fail_after_preflight):
                        response = self.call('delete', approval)
                    self.assertTrue(response['ok'], response)
                    self.assertNotEqual(response['data']['operation']['state'], 'done')
                    if mode == 'echo_disconnect_expunge':
                        self.assertEqual(response['data']['operation']['state'], 'unknown')
                    frontend.mode = 'guard'
                    if mode == 'echo_disconnect_expunge':
                        self.assertFalse(self.call('read', {'reference':ref})['ok'])
                        self.assertEqual(self.data('delete', approval)['operation']['state'], 'unknown')
                    status = self.data('operation_status', {'operation_id':approval['operation_id']})
                    self.assert_clean_diagnostics([response, status, output.getvalue()], encodings)

    def assert_clean_diagnostics(self, results, encodings):
        entries = self.engine.request({'v':1,'method':'call','action':'control_log','arguments':{'limit':10}})
        artifacts = [canonical(results), canonical(entries), canonical(self.engine.store.audit()),
                     (self.root / 'independent/operations.jsonl').read_text(),
                     (self.root / 'state/control.sqlite').read_bytes().decode('latin1')]
        for text in artifacts:
            self.assertNotIn('Untrusted backend diagnostic', text)
            for secret in encodings:
                self.assertNotIn(secret, text)

    def test_review_3_smtp_credential_echo_during_auth_envelope_and_final_data(self):
        password = 'Synthetic-smtp-credential-9!'
        encodings = [password, base64.b64encode(password.encode()).decode(),
                     base64.b64encode(('\0' + self.account['username'] + '\0' + password).encode()).decode()]
        echo = ('Untrusted backend diagnostic ' + ' '.join(encodings)).encode()
        with self.secret_frontend(password):
            for mode in ('echo_auth','echo_mail','echo_data'):
                directory = self.root / mode
                directory.mkdir()
                with self.subTest(mode=mode), SMTPFixture(directory, mode=mode, error_text=echo) as smtp:
                    account = {**self.account, 'smtp_host':'localhost', 'smtp_port':smtp.port}
                    self.engine.store.write({'mail:account:box':account}, 'fixture', 'SMTP failure frontend')
                    approval = self.approval()
                    output = io.StringIO()
                    with redirect_stdout(output), redirect_stderr(output):
                        response = self.call('send', approval)
                    self.assertTrue(response['ok'], response)
                    self.assertEqual(response['data']['operation']['state'], 'failed', response)
                    status = self.data('operation_status', {'operation_id':approval['operation_id']})
                    self.assert_clean_diagnostics([response, status, output.getvalue()], encodings)

    def test_review_3_second_guard_scrubs_password_and_auth_base64_before_stage_storage(self):
        password = 'Synthetic-stage-credential-5!'
        encodings = [password, base64.b64encode(password.encode()).decode(),
                     base64.b64encode(('\0' + self.account['username'] + '\0' + password).encode()).decode()]
        with self.secret_frontend(password):
            self.mail.transport.password(self.account)
            approval = self.approval()
            self.engine.stage(approval['operation_id'], 'diagnostic', ' '.join(encodings))
            status = self.data('operation_status', {'operation_id':approval['operation_id']})
            self.assertIn('[credential removed]', status['operation']['stages']['diagnostic'])
            self.assert_clean_diagnostics([status], encodings)

    def test_review_3_act_socket_mcp_cli_and_daemon_log_hide_execution_failure(self):
        import asyncio
        password = 'Synthetic-daemon-credential-3!'
        encodings = [password, base64.b64encode(password.encode()).decode(),
                     base64.b64encode(('\0' + self.account['username'] + '\0' + password).encode()).decode()]
        echo = ('Untrusted backend diagnostic ' + ' '.join(encodings)).encode()
        owner, service = 26101, 26102
        with self.secret_frontend(password, echo) as frontend:
            ref = self.fixture()
            approval = self.delete_approval([ref], 'permanent')
            frontend.mode = 'echo_expunge'
            self.engine.close()
            self.root.chmod(0o755)
            def service_paths():
                return [self.root / name for name in ('state','independent')] + list((self.root / 'state').rglob('*')) + list((self.root / 'independent').rglob('*'))
            for path in service_paths():
                os.chown(path, service, service)
            sockets = self.root / 'sockets'
            sockets.mkdir(mode=0o711)
            os.chown(sockets, service, service)
            config = {'owner_uid':owner, 'state_dir':str(self.root / 'state'),
                      'evidence_dir':str(self.root / 'independent'), 'socket_dir':str(sockets)}
            config_file = self.root / 'service.json'
            config_file.write_text(json.dumps(config))
            proxy_config = {'act_socket':str(sockets / 'act.sock'), 'admin_socket':str(sockets / 'admin.sock')}
            daemon = subprocess.Popen(['setpriv','--reuid',str(service),'--regid',str(service),'--clear-groups',sys.executable,
                                       '-m','aresos_control.daemon','--config',str(config_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            results = []
            try:
                for _ in range(100):
                    if (sockets / 'act.sock').exists():
                        break
                    if daemon.poll() is not None:
                        self.fail(daemon.communicate())
                    time.sleep(0.05)
                async def conversation():
                    from mcp import Client as MCPClient, StdioServerParameters
                    code = 'import json,sys; from aresos_control.proxy import main; main("mail",json.loads(sys.argv[1]))'
                    parameters = StdioServerParameters(command='/usr/bin/setpriv', args=['--reuid',str(owner),'--regid',str(owner),'--clear-groups',sys.executable,'-c',code,json.dumps(proxy_config)],
                        env={'PYTHONPATH':os.environ['PYTHONPATH'], 'PATH':'/usr/bin:/bin'})
                    async with MCPClient(parameters) as client:
                        result = (await client.call_tool('delete', approval)).structured_content
                        self.assertTrue(result['ok'], result)
                        self.assertNotEqual(result['data']['operation']['state'], 'done')
                        results.append(result)
                        results.append((await client.call_tool('operation_status', {'operation_id':approval['operation_id']})).structured_content)
                asyncio.run(conversation())
                code = 'import json,sys; from aresos_control.protocol import Client; print(json.dumps(Client(sys.argv[1]).call("mail_operation_status",json.loads(sys.argv[2]))))'
                raw = subprocess.run(['setpriv','--reuid',str(owner),'--regid',str(owner),'--clear-groups',sys.executable,'-c',code,str(sockets / 'act.sock'),json.dumps({'operation_id':approval['operation_id']})], capture_output=True, text=True, timeout=20)
                self.assertEqual(raw.returncode, 0, raw.stderr)
                results.append(json.loads(raw.stdout))
                code = 'import json,sys; from aresos_control.cli import main; raise SystemExit(main(json.loads(sys.argv[1]),["log","--input","{\\"limit\\":10}","--json"]))'
                cli = subprocess.run(['setpriv','--reuid',str(owner),'--regid',str(owner),'--clear-groups',sys.executable,'-c',code,json.dumps(proxy_config)], capture_output=True, text=True, timeout=20)
                self.assertEqual(cli.returncode, 0, cli.stderr)
                results.append(json.loads(cli.stdout))
            finally:
                daemon.send_signal(signal.SIGTERM)
                stdout, stderr = daemon.communicate(timeout=10)
                for path in service_paths():
                    os.chown(path, os.geteuid(), os.getegid())
                self.engine = Engine(self.root / 'state', self.root / 'independent')
                self.mail = self.engine.adapters['mail']
            self.assertEqual(daemon.returncode, 0, stdout + stderr)
            self.assert_clean_diagnostics(results + [stdout, stderr], encodings)

    def onboard_with_frontend(self, mode):
        with GuardedIMAPFixture(host='dovecot', port=993, mode=mode) as frontend:
            account_id = 'qualification-' + mode
            args = {'id':account_id, 'addresses':['owner-' + account_id + '@mail.invalid'], 'username':'setup-' + account_id,
                    'imap_host':'localhost', 'imap_port':frontend.port, 'smtp_host':'greenmail', 'smtp_port':3465, 'smtp_tls':'implicit'}
            with patch('aresos_control.mail.transport.context', side_effect=lambda a: context({**a,'ca_file':str(CERT / 'tls.crt')})):
                response = self.engine.request({'v':1, 'method':'mail_account_add', 'arguments':args, 'password':'pass'}, admin=True)
            self.assertTrue(response['ok'], response)
            account = next(a for a in self.data('accounts')['accounts'] if a['id'] == account_id)
            self.assertEqual(response['data']['account'], account)
            if mode == 'inuse':
                # The transient refusal disappears; the underlying server really is unsafe.
                frontend.mode = 'unsafe'
                recorded = self.mail.account(account_id, ready=False)
                recorded['ca_file'] = str(CERT / 'tls.crt')
                with self.mail.transport.imap(recorded) as conn:
                    ok(conn.create(quote('Unsafe-proof')), 'Create synthetic proof folder')
                    msg = EmailMessage()
                    msg.set_content('Synthetic proof that nonempty DELETE is unsafe')
                    ok(conn.append(quote('Unsafe-proof'), None, None, msg.as_bytes(policy=codec.SMTP_POLICY)), 'Append synthetic proof')
                    self.assertEqual(conn.delete(quote('Unsafe-proof'))[0], 'OK')
            return account

    def test_review_4_transient_permission_and_generic_refusals_never_qualify(self):
        for mode in ('inuse','permission','generic'):
            with self.subTest(mode=mode):
                account = self.onboard_with_frontend(mode)
                self.assertFalse(account['safe_folder_delete'], account)
                self.assertIn('not proven', account['folder_delete_reason'])

    def test_review_4_missing_exact_probe_or_failed_cleanup_never_qualifies(self):
        for mode in ('missing_probe','expunge_failure','empty_delete_failure'):
            with self.subTest(mode=mode):
                account = self.onboard_with_frontend(mode)
                self.assertFalse(account['safe_folder_delete'], account)
                self.assertIn('owner must inspect', account['folder_delete_reason'])

    def test_review_4_positive_guard_qualifies_only_after_verified_cleanup(self):
        account = self.onboard_with_frontend('guard')
        self.assertTrue(account['safe_folder_delete'], account)
        self.assertIn('exact probe survived', account['folder_delete_reason'])
