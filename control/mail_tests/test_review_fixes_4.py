"""Round 4: reconstruction, independent decoded-content guard and exact binaries."""
import ast
import base64
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesHeaderParser
import os
from pathlib import Path
import quopri
import re
import time
import unittest
import uuid
from unittest.mock import patch

from support import MailCase
import test_review_fixes_2 as previous
from test_review_fixes_3 import encapsulated
from imap_guard_fixture import GuardedIMAPFixture
from smtp_fixture import SMTPFixture
from aresos_control.common import Refused, sha256
from aresos_control.mail import codec, guard


MESSAGE_HEADERS = {'from', 'sender', 'reply-to', 'to', 'cc', 'date', 'subject',
                   'message-id', 'in-reply-to', 'references', 'mime-version'}
MIME_HEADERS = {'content-type', 'content-transfer-encoding', 'content-disposition',
                'content-id', 'content-description', 'content-language'}


def decoded_nodes(raw, default='text/plain'):
    """Independent receipt oracle: raw boundaries, never reserialize binary leaves."""
    if raw.startswith(b'\r\n'):
        head, payload = b'', raw[2:]
    else:
        head, sep, payload = raw.partition(b'\r\n\r\n')
        if not sep:
            head, sep, payload = raw.partition(b'\n\n')
    headers = BytesHeaderParser(policy=policy.default).parsebytes(head + b'\r\n\r\n')
    headers.set_default_type(default)
    cte = str(headers.get('Content-Transfer-Encoding', '7bit')).lower()
    data = base64.b64decode(payload) if cte == 'base64' else quopri.decodestring(payload) if cte == 'quoted-printable' else payload
    yield headers, data
    if headers.get_content_maintype() == 'multipart':
        boundary = re.escape(headers.get_boundary().encode())
        chunks = re.split(rb'(?:^|\r\n)--' + boundary + rb'(--)?[ \t]*(?:\r\n|$)', data)
        for index in range(2, len(chunks), 2):
            if chunks[index - 1] == b'--':
                break
            default = 'message/rfc822' if headers.get_content_type() == 'multipart/digest' else 'text/plain'
            yield from decoded_nodes(chunks[index], default)
    elif headers.get_content_maintype() == 'message':
        yield from decoded_nodes(data)
    else:
        nested_head = data.split(b'\r\n\r\n', 1)[0]
        nested = BytesHeaderParser(policy=policy.default).parsebytes(nested_head + b'\r\n\r\n')
        if nested.keys():
            yield from decoded_nodes(data)


def digest_fixture(with_from):
    inner = ((b'From: peer@mail.invalid\r\n' if with_from else b'') +
             b'Subject: Implicit digest mail\r\nBcc: private-digest@mail.invalid\r\n'
             b'Resent-Bcc: private-digest@mail.invalid\r\nResent-From: dropped@mail.invalid\r\n'
             b'X-Unlisted: discarded\r\n\r\nDigest body\r\n')
    return (b'Content-Type: multipart/digest; boundary=digest\r\n'
            b'Content-Disposition: attachment; filename="inner.txt"\r\n\r\n'
            b'--digest\r\nContent-Disposition: attachment; filename="inner.txt"\r\n\r\n' + inner + b'\r\n--digest--\r\n')


def wrapper(data, name='opaque.bin', kind='application/octet-stream', cte='base64'):
    message = EmailMessage(policy=codec.SMTP_POLICY)
    message['From'], message['Subject'] = 'peer@mail.invalid', 'Independent wrapper'
    message.set_content('Full authored text')
    major, minor = kind.split('/')
    message.add_attachment(data, maintype=major, subtype=minor, filename=name, cte=cte)
    return message.as_bytes()


class RebuildAndGuard(unittest.TestCase):
    def test_review4_allowlist_all_nested_headers_and_original_provenance(self):
        inner = (b'From: peer@mail.invalid\r\nSender: peer@mail.invalid\r\nReply-To: reply@mail.invalid\r\n'
                 b'To: one@mail.invalid\r\nCc: two@mail.invalid\r\nDate: Sat, 07 Nov 2026 10:00:00 +0000\r\n'
                 b'Subject: Rebuilt\r\nMessage-ID: <inner@mail.invalid>\r\nIn-Reply-To: <prior@mail.invalid>\r\n'
                 b'References: <prior@mail.invalid>\r\nMIME-Version: 1.0\r\n'
                 b'Bcc: private@mail.invalid\r\nResent-Bcc: private@mail.invalid\r\nResent-From: dropped@mail.invalid\r\n'
                 b'X-Unlisted: discarded\r\nX-AresOS-Authored: 1\r\n'
                 b'Content-Type: text/plain; charset=utf-8\r\nContent-Language: en\r\n'
                 b'Content-ID: <body@mail.invalid>\r\nContent-Description: Original description\r\n\r\nFull authored nested words\r\n')
        for kind in ('rfc822', 'global'):
            for encoding in ('base64', 'quoted-printable'):
                raw = encapsulated(encapsulated(inner, kind, encoding), kind, encoding)
                clean, texts = codec.rebuild(raw)
                self.assertIn('Full authored nested words', ''.join(texts))
                for headers, data in decoded_nodes(clean):
                    self.assertLessEqual({k.lower() for k in headers}, MESSAGE_HEADERS | MIME_HEADERS)
                    self.assertNotIn(b'private@mail.invalid', data)
                    self.assertNotIn(b'discarded', data)
                    self.assertNotIn(b'X-AresOS-Authored:', data)
                self.assertNotIn(b'X-AresOS-Authored:', clean)
                guard.check(clean, [], texts)
                with self.assertRaises(Refused):
                    guard.check(clean, [], [])
        # A Drafts source needs disclosure even without an authored marker.
        clean, texts = codec.rebuild(inner.replace(b'X-AresOS-Authored: 1\r\n', b''), authored=True)
        self.assertIn('Full authored nested words', ''.join(texts))
        with self.assertRaises(Refused):
            guard.check(wrapper(clean), ['Full authored text'], [])

    def test_review4_implicit_digest_default_is_preserved_at_every_depth(self):
        for with_from in (False, True):
            for raw in (digest_fixture(with_from), encapsulated(digest_fixture(with_from)),
                        wrapper(digest_fixture(with_from), name='inner.txt')):
                clean = codec.without_bcc(raw)
                nodes = list(decoded_nodes(clean))
                self.assertTrue(any(h.get_content_type() == 'message/rfc822' for h, _ in nodes))
                self.assertTrue(any(b'Digest body' in data for _, data in nodes))
                for headers, data in nodes:
                    self.assertNotIn('Bcc', headers)
                    self.assertNotIn('Resent-Bcc', headers)
                    self.assertNotIn(b'private-digest@mail.invalid', data)
                    self.assertNotIn(b'X-Unlisted:', data)
                guard.check(clean, ['Full authored text'], [])
                with self.assertRaises(Refused):
                    guard.check(raw, ['Full authored text'], [])

    def test_review4_guard_checks_every_decoded_leaf_and_literal_private_lines(self):
        for kind in ('text/plain', 'application/octet-stream', 'image/png'):
            for cte in ('base64', 'quoted-printable', '7bit', '8bit', 'binary'):
                for line in (b'Bcc: private@mail.invalid', b' \tReSeNt-BcC \t: private@mail.invalid'):
                    raw = wrapper(b'Literal file text\r\n' + line + b'\r\n', kind=kind, cte=cte)
                    with self.subTest(kind=kind, cte=cte, line=line), self.assertRaisesRegex(Refused, 'literal text-file line'):
                        guard.check(raw, ['Full authored text'], [])
        for data in (b'Content-Transfer-Encoding: base64\r\n\r\n' + base64.b64encode(b'Bcc: private@mail.invalid\r\n\r\nHidden'),
                     b'X_Custom: value\r\n \t\r\nSubject: No From\r\nBcc \t: private@mail.invalid\r\n\r\nHidden'):
            with self.assertRaises(Refused):
                guard.check(wrapper(data), ['Full authored text'], [])
        # The checker has no import, dynamic import or builder-helper dependency.
        imports = [node for node in ast.walk(ast.parse(Path(guard.__file__).read_text())) if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any('codec' in ast.dump(node) for node in imports))

    def test_review4_rebuild_and_guard_refuse_depth_size_and_broken_structures(self):
        raw = b'From: peer@mail.invalid\r\nSubject: Deep\r\n\r\nBody\r\n'
        for _ in range(42):
            raw = b'Content-Type: message/rfc822\r\n\r\n' + raw
        for call in (lambda: codec.rebuild(raw), lambda: guard.check(raw, [], [])):
            with self.assertRaisesRegex(Refused, 'depth|nesting'):
                call()
        with patch.object(codec, 'INSPECTION_LIMIT', 32), self.assertRaisesRegex(Refused, 'size'):
            codec.rebuild(b'Subject: Oversized\r\n\r\n' + b'x' * 64)
        with patch.object(guard, 'MAX_BYTES', 32), self.assertRaisesRegex(Refused, 'size'):
            guard.check(b'Subject: Oversized\r\n\r\n' + b'x' * 64, [], [])
        with patch.object(guard, 'MAX_WORK', 64), self.assertRaisesRegex(Refused, 'size'):
            guard.check(wrapper(b'Ordinary file'), ['Full authored text'], [])
        for data in (digest_fixture(False).replace(b'--digest--', b'--broken--'),
                     b'Content-Type: message/global\r\nContent-Transfer-Encoding: base64\r\n\r\n!!!'):
            with self.assertRaises(Refused):
                codec.rebuild(data)
            with self.assertRaises(Refused):
                guard.check(data, [], [])


class ReviewFixes4(MailCase):
    caller = previous.ReviewFixes2.caller

    def test_review4_saved_sent_whitespace_continuation_refused_through_proxy(self):
        sent = self.send(self.approval(bcc=['private-continuation@mail.invalid']))
        ref, = self.data('operation_status', {'operation_id':sent['id']})['evidence']['sent']
        with self.caller() as (proxy, home):
            exported = proxy('attachment_save', {'reference':ref, 'part':'source', 'name':'sent.eml'})
            self.assertTrue(exported['ok'], exported)
            raw = Path(exported['data']['path']).read_bytes().replace(b'X-AresOS-Authored: 1\r\n', b'')
            self.assertIn(b'Bcc: private-continuation@mail.invalid', raw)
            path = home / 'Documents' / 'saved.txt'
            path.write_bytes(b'X_Custom: value\r\n \t\r\n' + raw)
            os.chown(path, 26101, 26101)
            result = proxy('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Refuse saved mail', 'attachments':[{'path':str(path)}]})
            self.assertFalse(result['ok'], result)
            self.assertEqual(result['error']['code'], 'file_refused')
            self.assertIn('mode=forward', result['error']['message'])
            self.assertIn('reference', result['error']['message'])
        self.assertEqual(len(self.arrivals('one@mail.invalid', sent['stages']['message_id'])), 1)

    def digest_source(self, with_from):
        raw = (b'From: peer@mail.invalid\r\nTo: ' + self.owner.encode() + b'\r\nSubject: Digest source\r\nMessage-ID: <' +
               uuid.uuid4().hex.encode() + b'@mail.invalid>\r\nContent-Type: multipart/mixed; boundary=outer\r\n\r\n'
               b'--outer\r\nContent-Type: text/plain\r\n\r\nOuter body\r\n--outer\r\n' +
               digest_fixture(with_from) + b'\r\n--outer--\r\n')
        return raw, self.mail.append(self.account, 'INBOX', raw)

    def test_review4_digest_without_content_type_sent_clean_in_both_forward_styles_and_explicit_parts(self):
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'digest SMTP sink')
            for with_from in (False, True):
                raw, ref = self.digest_source(with_from)
                for mode, style in (('new', None), ('forward', 'inline'), ('forward', 'attachment')):
                    with self.subTest(with_from=with_from, mode=mode, style=style):
                        args = {'mode':mode, 'attachments':[{'reference':ref, 'part':'1.2'}]}
                        if style:
                            args.update(reference=ref, forward_as=style)
                        comp = self.compose(**args)
                        approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id', 'composition_hash')})['approval']
                        for item in approval['description']['attachments']:
                            self.assertIn('rebuilt', item['transformation'])
                            self.assertEqual(set(item['allowed_message_headers']), MESSAGE_HEADERS)
                            self.assertEqual(set(item['allowed_mime_headers']), MIME_HEADERS)
                        sent = self.send(approval)
                        self.assertEqual(sent['state'], 'done', sent)
                        received = smtp.arrivals()[-1][1]
                        nodes = list(decoded_nodes(received))
                        self.assertTrue(any(b'Digest body' in data for _, data in nodes))
                        for headers, data in nodes:
                            self.assertNotIn('Bcc', headers)
                            self.assertNotIn('Resent-Bcc', headers)
                            self.assertNotIn(b'private-digest@mail.invalid', data)
                        for part, item in zip(codec.parse(received).iter_attachments(), approval['description']['attachments']):
                            self.assertEqual(sha256(codec.decoded(part)), item['sha256'])
                saved = self.data('attachment_save', {'reference':ref, 'part':'source'})['file']
                self.assertEqual(self.engine.blobs.read(saved['sha256']), raw)

    def test_review4_raw_binary_and_base64_pdf_png_are_byte_equal_after_all_send_paths(self):
        payloads = [('fixture.pdf', 'application/pdf', b'%PDF-1.7\nraw LF\rbare CR\r\npaired\x00\xff'),
                    ('fixture.png', 'image/png', b'\x89PNG\r\n\x1a\nraw LF\rbare CR\r\npaired\x00\xff')]
        with GuardedIMAPFixture(host='dovecot', port=993) as source, SMTPFixture(self.root) as smtp:
            self.account.update(imap_host='localhost', imap_port=source.port, smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'exact raw received source and SMTP sink')
            for encoding in ('binary', 'base64'):
                mid = b'<' + uuid.uuid4().hex.encode() + b'@mail.invalid>'
                raw = (b'From: peer@mail.invalid\r\nSubject: Raw binary source\r\nMessage-ID: ' + mid +
                       b'\r\nContent-Type: multipart/mixed; boundary=rawfixture\r\n\r\n'
                       b'--rawfixture\r\nContent-Type: text/plain\r\n\r\nReceived body\r\n')
                for name, kind, data in payloads:
                    encoded = base64.encodebytes(data).replace(b'\n', b'\r\n') if encoding == 'base64' else data
                    raw += (b'--rawfixture\r\nContent-Type: ' + kind.encode() + b'\r\nContent-Disposition: attachment; filename="' + name.encode() +
                            b'"\r\nContent-Transfer-Encoding: ' + encoding.encode() + b'\r\n\r\n' + encoded + b'\r\n')
                raw += b'--rawfixture--\r\n'
                source.exact_sources[mid] = raw
                ref = self.mail.append(self.account, 'INBOX', raw)
                self.assertEqual(self.mail.message(ref)['raw'], raw)
                for mode, style in (('new', None), ('forward', 'inline'), ('forward', 'attachment')):
                    with self.subTest(encoding=encoding, mode=mode, style=style):
                        args = {'mode':mode}
                        if style:
                            args.update(reference=ref, forward_as=style)
                        else:
                            args['attachments'] = [{'reference':ref, 'part':part} for part in ('1.2', '1.3')]
                        comp = self.compose(**args)
                        approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id', 'composition_hash')})['approval']
                        sent = self.send(approval)
                        self.assertEqual(sent['state'], 'done', sent)
                        received = smtp.arrivals()[-1][1]
                        leaves = {h.get_filename(): data for h, data in decoded_nodes(received) if h.get_content_type() in {'application/pdf', 'image/png'}}
                        self.assertEqual(leaves, {name:data for name, _, data in payloads})
                        for part, item in zip(codec.parse(received).iter_attachments(), approval['description']['attachments']):
                            self.assertEqual(sha256(codec.decoded(part)), item['sha256'])
                for part, (_, _, data) in zip(('1.2', '1.3'), payloads):
                    saved = self.data('attachment_save', {'reference':ref, 'part':part})['file']
                    self.assertEqual(self.engine.blobs.read(saved['sha256']), data)

    def test_review4_guard_bypassing_builder_fails_compose_prepare_and_final_data_without_replay(self):
        hidden = b'Subject: Hidden\r\nBcc: private-final@mail.invalid\r\n\r\nHidden body\r\n'
        marked = b'Content-Type: text/plain\r\nX-AresOS-Authored: 1\r\n\r\nUndisclosed marked text\r\n'
        cases = [wrapper(encapsulated(hidden)), wrapper(digest_fixture(False), name='inner.txt'), wrapper(marked)]
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'independent final guard SMTP sink')
            for bad in cases:
                with self.subTest(bad=bad):
                    comp = self.compose()
                    keys = {k:comp[k] for k in ('composition_id', 'composition_hash')}
                    approval = self.data('prepare_send', keys)['approval']
                    with patch.object(self.mail, 'mime', return_value=bad):
                        refused = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Full authored text'})
                        self.assertFalse(refused['ok'], refused)
                        self.assertIn('Outgoing MIME guard', refused['error']['message'])
                        self.assertFalse(self.call('prepare_send', keys)['ok'])
                        stopped = self.send(approval)
                        self.assertEqual(stopped['state'], 'failed', stopped)
                        self.assertNotIn('smtp_data', stopped['stages'])
                        self.assertEqual(self.send(approval)['state'], 'failed')
                    approval = self.data('prepare_send', keys)['approval']
                    original_check, calls = self.mail.check_mime, []
                    def final_only(comp, raw):
                        calls.append(raw)
                        if len(calls) > 1:
                            original_check(comp, raw)
                    with patch.object(self.mail, 'mime', return_value=bad), patch.object(self.mail, 'check_mime', side_effect=final_only), patch('smtplib.SMTP_SSL.data', side_effect=AssertionError('DATA forbidden')) as data:
                        stopped = self.send(approval)
                        data.assert_not_called()
                    self.assertEqual(calls, [bad, bad])
                    self.assertEqual(stopped['state'], 'failed', stopped)
                    self.assertNotIn('smtp_data', stopped['stages'])
                    self.assertEqual(self.send(approval)['state'], 'failed')
            self.assertEqual(smtp.auth_count, len(cases))
            self.assertEqual(smtp.arrivals(), [])

