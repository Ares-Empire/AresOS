"""Regressions for REVIEW-2: outgoing sources, local round trips and typed evidence."""
from contextlib import contextmanager
from email.message import EmailMessage
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from support import MailCase
from imap_guard_fixture import GuardedIMAPFixture
from smtp_fixture import SMTPFixture
from aresos_control.common import Refused, sha256
from aresos_control.engine import Engine
from aresos_control.mail import codec


class LocalMailDetection(unittest.TestCase):
    def test_review2_1_header_detection_bom_whitespace_case_and_first_empty_line(self):
        for header in (b'Date', b'Subject', b'Message-ID', b'Received', b'MIME-Version'):
            for prefix in (b'', b'\xef\xbb\xbf', b'\n', b' \t\r\n\xef\xbb\xbf\n  '):
                with self.subTest(header=header, prefix=prefix):
                    self.assertTrue(codec.is_mail(prefix + b'fRoM: synthetic@mail.invalid\r\n' + header + b': value\r\n\r\nBody'))
        for data in (b'From: synthetic@mail.invalid\n\nSubject: body only', b'Subject: no sender\n\nBody',
                     b'From: sender only\n\nBody', b'Ordinary text\n\nFrom: example\nSubject: example',
                     b'%PDF-1.7\n\nFrom: example\nSubject: example', b'Ordinary text file'):
            with self.subTest(data=data):
                self.assertFalse(codec.is_mail(data))


class ReviewFixes2(MailCase):
    def assert_clean_mail(self, raw, private):
        self.assertNotIn(private.encode(), raw)
        for part in codec.parse(raw).walk():
            self.assertIsNone(part.get('Bcc'))
            self.assertIsNone(part.get('Resent-Bcc'))
            if not part.is_multipart():
                data = codec.decoded(part)
                self.assertNotIn(private.encode(), data)
                if codec.is_mail(data) or (part.get_filename() or '').endswith('.eml'):
                    self.assert_clean_mail(data, private)

    def test_review2_2_explicit_sent_source_nested_message_and_container_in_every_mode(self):
        private = 'private-explicit@mail.invalid'
        sent = self.send(self.approval(bcc=[private]))
        source, = self.data('operation_status', {'operation_id':sent['id']})['evidence']['sent']
        original = self.mail.message(source)['raw']
        self.assertIn(private.encode(), original)
        inner = codec.parse(original)
        inner['Resent-Bcc'] = private
        container = EmailMessage()
        container.set_content('Container body')
        container.add_attachment(inner)
        outer = EmailMessage()
        outer['From'], outer['To'] = self.peer, self.owner
        outer['Message-ID'] = '<explicit-' + uuid.uuid4().hex + '@mail.invalid>'
        outer.set_content('Outer body')
        outer.make_mixed()
        outer.attach(container)
        # An opaque, renamed mail source still needs recursive Bcc removal.
        outer.add_attachment(b'\xef\xbb\xbf\n' + original, maintype='application', subtype='octet-stream', filename='renamed.txt')
        nested = self.fixture(msg=outer)
        self.assertEqual(codec.parts(self.mail.message(nested)['msg'])['1.2.2'].get_content_type(), 'message/rfc822')
        draft = self.data('draft_save', {k:v for k,v in self.compose().items() if k in ('composition_id','composition_hash')})['reference']
        for mode, style in (('new',None), ('reply',None), ('reply_all',None), ('forward','inline'), ('forward','attachment'), ('draft',None)):
            with self.subTest(mode=mode, style=style):
                args = {'account':'box', 'mode':mode, 'text':'Explicit attachment review', 'attachments':[
                    {'reference':source,'part':'source'}, {'reference':nested,'part':'1.2.2'},
                    {'reference':nested,'part':'1.2'}, {'reference':nested,'part':'1.3'}]}
                if mode != 'new':
                    args['reference'] = draft if mode == 'draft' else source
                if mode not in ('reply','reply_all'):
                    args['to'] = ['two@mail.invalid']
                if style:
                    args['forward_as'] = style
                comp = self.data('compose', args)
                approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})['approval']
                for item in approval['description']['attachments']:
                    self.assertIn('Bcc and Resent-Bcc removed', item['transformation'])
                    clean = self.engine.blobs.read(item['sha256'])
                    self.assertEqual(len(clean), item['size'])
                    self.assert_clean_mail(clean, private)
                result = self.send(approval)
                self.assertEqual(result['state'], 'done', result)
                recipient = codec.mailbox(comp['mail']['to'][0])
                received, = self.arrivals(recipient, result['stages']['message_id'])
                self.assert_clean_mail(received, private)
                attachments = list(codec.parse(received).iter_attachments())
                self.assertEqual(len(attachments), len(comp['mail']['attachments']))
                for part, approved in zip(attachments, approval['description']['attachments']):
                    self.assertEqual(sha256(codec.decoded(part)), approved['sha256'])
        saved = self.data('attachment_save', {'reference':source,'part':'source'})['file']
        self.assertEqual(self.engine.blobs.read(saved['sha256']), original)
        self.assertEqual(self.data('read', {'reference':source,'part':'source'})['untrusted_content']['text'].encode('latin1'), original)

    @contextmanager
    def caller(self):
        # Exercise the actual caller file policy, chunk transfer and service under distinct UIDs.
        owner, service = 26101, 26102
        self.engine.close()
        self.root.chmod(0o755)
        def service_paths():
            return [self.root / name for name in ('state','independent')] + list((self.root / 'state').rglob('*')) + list((self.root / 'independent').rglob('*'))
        for path in service_paths():
            os.chown(path, service, service)
        allowed_work = Path(__file__).resolve().parents[1] / 'test-work'
        allowed_work.mkdir(exist_ok=True)
        home_temp = tempfile.TemporaryDirectory(dir=allowed_work)
        parent = Path(home_temp.name)
        parent.chmod(0o755)
        home = parent / 'owner'
        home.mkdir(mode=0o700)
        os.chown(home, owner, owner)
        for name in ('Documents','Downloads'):
            folder = home / name
            folder.mkdir(mode=0o700)
            os.chown(folder, owner, owner)
        sockets = self.root / 'sockets'
        sockets.mkdir(mode=0o711)
        os.chown(sockets, service, service)
        config = {'owner_uid':owner, 'state_dir':str(self.root / 'state'), 'evidence_dir':str(self.root / 'independent'), 'socket_dir':str(sockets)}
        from boundary_test_support import install_boundary
        config.update(install_boundary(self.root / 'boundary', config['socket_dir']))
        config_file = self.root / 'service.json'
        config_file.write_text(json.dumps(config))
        proxy_config = {'act_socket':str(sockets / 'act.sock'), 'admin_socket':str(sockets / 'admin.sock'),
                        'home':str(home), 'folders':[str(home / name) for name in ('Documents','Downloads')]}
        daemon = subprocess.Popen(['setpriv','--reuid',str(service),'--regid',str(service),'--clear-groups',sys.executable,
                                   '-m','aresos_control.daemon','--config',str(config_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def proxy(verb, args):
            code = 'import json,sys; from aresos_control.proxy import Proxy; print(json.dumps(Proxy("mail",json.loads(sys.argv[1])).call(sys.argv[2],json.loads(sys.argv[3]))))'
            result = subprocess.run(['setpriv','--reuid',str(owner),'--regid',str(owner),'--clear-groups',sys.executable,'-c',code,
                                     json.dumps(proxy_config),verb,json.dumps(args)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        try:
            for _ in range(100):
                if (sockets / 'act.sock').exists():
                    break
                if daemon.poll() is not None:
                    self.fail(daemon.communicate())
                time.sleep(0.05)
            yield proxy, home
        finally:
            daemon.send_signal(signal.SIGTERM)
            stdout, stderr = daemon.communicate(timeout=10)
            for path in service_paths():
                os.chown(path, os.geteuid(), os.getegid())
            self.engine = Engine(self.root / 'state', self.root / 'independent')
            self.mail = self.engine.adapters['mail']
            home_temp.cleanup()
            self.assertEqual(daemon.returncode, 0, stdout + stderr)

    def test_review2_1_saved_draft_and_bcc_sent_refused_through_real_proxy_even_renamed(self):
        comp = self.compose(text='x' * 21000)
        draft = self.data('draft_save', {k:comp[k] for k in ('composition_id','composition_hash')})['reference']
        sent = self.send(self.approval(bcc=['private-roundtrip@mail.invalid']))
        sent_ref, = self.data('operation_status', {'operation_id':sent['id']})['evidence']['sent']
        originals = [self.mail.message(ref)['raw'] for ref in (draft, sent_ref)]
        with self.caller() as (proxy, home):
            for index, ref in enumerate((draft, sent_ref)):
                saved = proxy('attachment_save', {'reference':ref,'part':'source','name':f'saved-{index}.eml'})
                if index == 0:
                    self.assertFalse(saved['ok'], saved)
                    path = home / 'Downloads' / f'saved-{index}.eml'
                    self.assertFalse(path.exists())
                    path.write_bytes(originals[index])
                    os.chown(path, 26101, 26101)
                else:
                    self.assertTrue(saved['ok'], saved)
                    path = Path(saved['data']['path'])
                self.assertEqual(path.read_bytes(), originals[index])
                self.assertEqual(codec.AUTHORED_HEADER.encode() in path.read_bytes(), index == 0)
                if index:
                    self.assertIn(b'Bcc: private-roundtrip@mail.invalid', path.read_bytes())
                for variant, prefix, suffix in (('original',b'', '.eml'), ('renamed',b'', '.txt'),
                        ('bom',b'\xef\xbb\xbf', '.txt'), ('blank',b'\r\n', '.txt'), ('whitespace',b' \t\n\xef\xbb\xbf\r\n  ', '.txt')):
                    with self.subTest(source=index, variant=variant):
                        imported = path if variant == 'original' else home / 'Documents' / f'{index}-{variant}{suffix}'
                        if variant != 'original':
                            imported.write_bytes(prefix + originals[index])
                            os.chown(imported, 26101, 26101)
                        result = proxy('compose', {'account':'box','to':['one@mail.invalid'],'text':'Round trip', 'attachments':[{'path':str(imported)}]})
                        self.assertFalse(result['ok'], result)
                        self.assertEqual(result['error']['code'], 'file_refused')
                        self.assertIn('mode=forward', result['error']['message'])
                        self.assertIn('reference', result['error']['message'])
            for suffix in ('.EML','.msg','.MSG'):
                path = home / 'Documents' / ('ordinary' + suffix)
                path.write_bytes(b'Ordinary text, misleading mail extension')
                os.chown(path, 26101, 26101)
                self.assertFalse(proxy('compose', {'account':'box','text':'Refuse extension','attachments':[{'path':str(path)}]})['ok'])
            normal = [b'%PDF-1.7\nOrdinary synthetic PDF\x00\xff', b'Ordinary text\nSubject: a body line, not a mail header block.']
            paths = [home / 'Documents' / name for name in ('ordinary.pdf','ordinary.txt')]
            for path, data in zip(paths, normal):
                path.write_bytes(data)
                os.chown(path, 26101, 26101)
            result = proxy('compose', {'account':'box','to':['one@mail.invalid'],'text':'Ordinary files','attachments':[{'path':str(path)} for path in paths]})
            self.assertTrue(result['ok'], result)
            composition = result['data']
            prepared = proxy('prepare_send', {k:composition[k] for k in ('composition_id','composition_hash')})
            self.assertTrue(prepared['ok'], prepared)
            delivered = proxy('send', prepared['data']['approval'])
            self.assertTrue(delivered['ok'], delivered)
            self.assertEqual(delivered['data']['operation']['state'], 'done', delivered)
        raw, = self.arrivals('one@mail.invalid', delivered['data']['operation']['stages']['message_id'])
        self.assertEqual([codec.decoded(part) for part in codec.parse(raw).iter_attachments()], normal)

    def test_review2_3_password_collisions_preserve_acceptance_hashes_and_repair(self):
        with GuardedIMAPFixture(host='dovecot', port=993, backend_password='pass') as frontend, SMTPFixture(self.root) as smtp:
            self.account.update(imap_host='localhost', imap_port=frontend.port, smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'credential collision frontends')
            for collision in ('accepted:250', 'composition_hash'):
                for fail_sent in (False, True):
                    with self.subTest(collision=collision, fail_sent=fail_sent):
                        comp = self.compose(bcc=['private-collision@mail.invalid'])
                        approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})['approval']
                        stored = self.mail.composition(comp)
                        raw = self.mail.mime(stored, self.mail.message_id(approval['operation_id']))
                        wire_hash = sha256(raw)
                        # Deterministically collide with both composition and stored wire evidence.
                        password = collision if collision == 'accepted:250' else next(
                            comp['composition_hash'][i:i+n] for n in (2,1) for i in range(65-n)
                            if comp['composition_hash'][i:i+n] in wire_hash)
                        self.mail.transport.store_password('box', password)
                        previous = self.mail.local_stage
                        def local_stage(op, which):
                            if fail_sent and which == 'sent_copy':
                                raise Refused('stage_missing', 'Synthetic Sent failure')
                            return previous(op, which)
                        arrivals_before = len(smtp.arrivals())
                        with patch.object(self.mail, 'mime', return_value=raw), patch.object(self.mail, 'local_stage', side_effect=local_stage):
                            result = self.send(approval)
                        self.assertEqual(result['state'], 'partial' if fail_sent else 'done', result)
                        self.assertEqual(result['stages']['smtp_data'], 'accepted:250')
                        self.assertEqual(result['stages']['rcpt:one@mail.invalid'], 'accepted:250')
                        self.assertEqual(result['stages']['wire_sha256'], wire_hash)
                        sent_wire = self.mail.wires.read(result['stages']['sent_wire_sha256'])
                        self.assertEqual(sha256(sent_wire), result['stages']['sent_wire_sha256'])
                        if collision == 'composition_hash':
                            self.assertIn(password, self.engine.operation(result['id'])['payload']['composition']['hash'])
                        if fail_sent:
                            with patch.object(self.mail.transport, 'smtp', side_effect=AssertionError('Repair must not submit')):
                                repaired = self.data('operation_repair', {'operation_id':result['id'],'stage':'sent_copy'})
                            self.assertEqual(repaired['operation']['state'], 'done', repaired)
                            self.assertEqual(repaired['original']['state'], 'done', repaired)
                            self.assertEqual(repaired['original']['stages']['smtp_data'], 'accepted:250')
                        self.assertEqual(len(smtp.arrivals()), arrivals_before + 1)
                        self.assertEqual(len(self.data('operation_status', {'operation_id':result['id']})['evidence']['sent']), 1)

    def test_review2_3_only_diagnostics_are_scrubbed_and_server_text_is_not_evidence(self):
        approval = self.approval()
        op_id = approval['operation_id']
        message_id = self.mail.message_id(op_id)
        for value in ('smtp_data', op_id, message_id, 'one@mail.invalid', 'accepted:250', 'a' * 64):
            self.mail.transport.remember(self.account['username'], value)
        for name, value in (('message_id',message_id), ('wire_sha256','a' * 64),
                            ('rcpt:one@mail.invalid','accepted:250'), ('smtp_data','accepted:250')):
            self.engine.stage(op_id, name, value)
            self.assertEqual(self.engine.operation(op_id)['stages'][name], value)
        for name, value in (('smtp_data','accepted:250 Untrusted server diagnostic'),
                            ('unknown_stage','done'), ('rcpt:other@mail.invalid','accepted:250')):
            with self.assertRaises(Refused):
                self.engine.stage(op_id, name, value)
        self.engine.stage(op_id, 'diagnostic', 'Untrusted accepted:250')
        self.assertEqual(self.engine.operation(op_id)['stages']['diagnostic'], 'Untrusted [credential removed]')
