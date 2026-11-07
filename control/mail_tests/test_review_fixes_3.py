"""REVIEW-3 regressions: header syntax, recursive decoding and independent wire guard."""
import base64
from email import policy
from email.message import EmailMessage
from email.parser import BytesHeaderParser
import os
from pathlib import Path
import quopri
import re
import unittest
import uuid
from unittest.mock import patch

from support import MailCase
import test_review_fixes_2 as previous
from smtp_fixture import SMTPFixture
from aresos_control.common import Refused, canonical, visible, sha256
from aresos_control.mail import codec, guard


def encapsulated(inner, kind='rfc822', encoding='base64'):
    # Encode header names too: permissive parsers sometimes see through ASCII-only QP.
    payload = base64.encodebytes(inner).replace(b'\n', b'\r\n') if encoding == 'base64' else b'=\r\n'.join(
        b''.join(b'=%02X' % byte for byte in inner[start:start + 24]) for start in range(0, len(inner), 24))
    return (b'From: nested@mail.invalid\r\nSubject: Encapsulated\r\nContent-Type: message/' + kind.encode()
            + b'\r\nContent-Transfer-Encoding: ' + encoding.encode() + b'\r\n\r\n' + payload)


def received_nodes(raw):
    """Test oracle: decode on the wire, including message parts Python calls multipart."""
    head, payload = re.split(rb'\r\n\r\n|\n\n', raw, maxsplit=1)
    headers = BytesHeaderParser(policy=policy.default).parsebytes(head + b'\r\n\r\n')
    yield headers, payload
    encoding = str(headers.get('Content-Transfer-Encoding', '')).lower()
    if encoding == 'base64':
        payload = base64.b64decode(payload)
    elif encoding == 'quoted-printable':
        payload = quopri.decodestring(payload)
    yield headers, payload
    if headers.get_content_maintype() == 'multipart':
        for child in codec.parse(raw).get_payload():
            yield from received_nodes(child.as_bytes(policy=codec.SMTP_POLICY))
    elif headers.get_content_maintype() == 'message' or codec.is_mail(payload):
        yield from received_nodes(codec.mail_content(payload))


class HeaderAndEncoding(unittest.TestCase):
    def test_review3_1_full_field_syntax_scan_past_damage_and_mbox(self):
        for byte in range(33, 127):
            if byte == 58:
                continue
            for suffix in (b': value', b' \t: value'):
                raw = b'From synthetic mbox envelope\r\nX' + bytes([byte]) + suffix + b'\r\nMalformed line\r\nFrom: synthetic@mail.invalid\r\nBcc: private@mail.invalid\r\n\r\nBody'
                self.assertTrue(codec.is_mail(raw), raw)
        for name in (b'Bcc', b'Resent-Bcc', b'X-AresOS-Authored'):
            self.assertTrue(codec.is_mail(b'From: synthetic@mail.invalid\n' + name + b': value\n\nBody'))
        self.assertFalse(codec.is_mail(b'From: synthetic@mail.invalid\n\nBcc: body only'))
        for prefix in (b'Ordinary text\n', b'%PDF-1.7\n'):
            # The round-2 detector stopped here; the round-3 brief requires scanning onward.
            self.assertTrue(codec.is_mail(prefix + b'From: example\nSubject: example'))

    def test_review3_guard_frozen_mime_container_and_headerless_eml_are_checked(self):
        inner = b'Bcc: private@mail.invalid\r\nResent-Bcc: private@mail.invalid\r\nContent-Type: text/plain\r\n\r\nBody\r\n'
        container = b'Content-Type: multipart/mixed; boundary=x\r\n\r\n--x\r\n' + encapsulated(inner) + b'\r\n--x--\r\n'
        for payload, name in ((inner, 'headerless.eml'), (container, 'opaque.bin')):
            wrapper = EmailMessage(policy=codec.SMTP_POLICY)
            wrapper['From'], wrapper['Subject'] = 'synthetic@mail.invalid', 'Frozen mail source'
            wrapper.set_content('Root text')
            wrapper.add_attachment(payload, maintype='application', subtype='octet-stream', filename=name)
            raw = wrapper.as_bytes()
            with self.assertRaises(Refused):
                guard.check(raw, ['Root text'], [])
            guard.check(codec.without_bcc(raw), ['Root text'], [])
        with self.assertRaises(Refused):
            guard.check(container.replace(b'--x\r\n', b'--x-invalid\r\n'), [], [])

    def test_review3_2_recursive_encoding_and_provenance_before_text_classification(self):
        inner = b'From: synthetic@mail.invalid\r\nSubject: Inner\r\nBcc: private@mail.invalid\r\nResent-Bcc: private@mail.invalid\r\nX-AresOS-Authored: 1\r\n\r\nEntire authored nested text\r\n'
        for kind in ('rfc822', 'global'):
            for encoding in ('base64', 'quoted-printable'):
                for outer_type in ('application/octet-stream', 'text/plain', 'message/' + kind):
                    with self.subTest(kind=kind, encoding=encoding, outer_type=outer_type):
                        nested = encapsulated(encapsulated(inner, kind, encoding), kind, encoding)
                        raw = (b'From: outer@mail.invalid\r\nSubject: Outer\r\nContent-Type: ' + outer_type.encode()
                               + b'\r\nContent-Disposition: attachment; filename="source.bin"\r\nContent-Transfer-Encoding: base64\r\n\r\n' + base64.encodebytes(nested))
                        clean = codec.without_bcc(raw)
                        texts = codec.approval_texts(codec.parse(clean))
                        self.assertIn('Entire authored nested text', ''.join(texts))
                        for headers, data in received_nodes(clean):
                            self.assertNotIn('Bcc', headers)
                            self.assertNotIn('Resent-Bcc', headers)
                            self.assertNotIn(b'private@mail.invalid', data)
                        guard.check(clean, [], texts)
                        with self.assertRaises(Refused):
                            guard.check(raw, [], texts)
                        with self.assertRaises(Refused):
                            guard.check(clean, [], [])

    def test_review3_2_unknown_broken_ambiguous_and_defective_mail_refused(self):
        inner = b'From: synthetic@mail.invalid\r\nSubject: Inner\r\n\r\nBody\r\n'
        good = encapsulated(inner)
        bad_header = b'From: synthetic@mail.invalid\r\nBroken line\r\nBcc: private@mail.invalid\r\n\r\nBody\r\n'
        invalid = [good.replace(b'base64', b'x-unknown'), good + b'!',
                   encapsulated(inner, encoding='quoted-printable') + b'=QZ',
                   encapsulated(bad_header), encapsulated(inner.replace(b'From:', b'From :')),
                   good.replace(b'Content-Type:', b'Content-Transfer-Encoding: 7bit\r\nContent-Type:'),
                   good.replace(b'message/rfc822', b'multipart/mixed; boundary=x'),
                   encapsulated(inner, encoding='quoted-printable').replace(b'message/rfc822', b'multipart/mixed; boundary=x'),
                   good.replace(b'message/rfc822', b'message/partial')]
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaises(Refused):
                    codec.without_bcc(raw)
                with self.assertRaises(Refused):
                    guard.check(raw, [], [])


class ReviewFixes3(MailCase):
    caller = previous.ReviewFixes2.caller

    def test_review3_1_export_punctuation_malformed_and_mbox_refused_by_real_proxy(self):
        comp = self.compose(text='x' * 21000)
        draft = self.data('draft_save', {k: comp[k] for k in ('composition_id', 'composition_hash')})['reference']
        sent = self.send(self.approval(bcc=['private-syntax@mail.invalid']))
        sent_ref, = self.data('operation_status', {'operation_id': sent['id']})['evidence']['sent']
        with self.caller() as (proxy, home):
            for index, ref in enumerate((draft, sent_ref)):
                exported = proxy('attachment_save', {'reference':ref, 'part':'source', 'name':f'export-{index}.eml'})
                self.assertTrue(exported['ok'], exported)
                original = Path(exported['data']['path']).read_bytes()
                self.assertIn(b'X-AresOS-Authored:', original)
                if index:
                    self.assertIn(b'Bcc: private-syntax@mail.invalid', original)
                for variant in (b'X_Custom: value\r\n', b'X.Y: value\r\n', b'X!: value\r\n',
                                b'X_Custom \t: value\r\n', b'Malformed header line\r\n',
                                b'From synthetic mbox envelope\r\n',
                                b'From synthetic mbox envelope\r\nX_Custom: value\r\nMalformed line\r\n'):
                    with self.subTest(source=index, variant=variant):
                        path = home / 'Documents' / f'renamed-{index}.txt'
                        path.write_bytes(variant + original)
                        os.chown(path, 26101, 26101)
                        result = proxy('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Round trip', 'attachments':[{'path':str(path)}]})
                        self.assertFalse(result['ok'], result)
                        self.assertEqual(result['error']['code'], 'file_refused')
                        self.assertIn('mode=forward', result['error']['message'])
            ordinary = [b'Ordinary local text', b'%PDF-1.7\nSynthetic ordinary PDF\x00\xff']
            paths = [home / 'Documents' / name for name in ('ordinary.txt', 'ordinary.pdf')]
            for path, data in zip(paths, ordinary):
                path.write_bytes(data)
                os.chown(path, 26101, 26101)
            result = proxy('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Ordinary attachments', 'attachments':[{'path':str(path)} for path in paths]})
            self.assertTrue(result['ok'], result)
            prepared = proxy('prepare_send', {k:result['data'][k] for k in ('composition_id','composition_hash')})
            self.assertTrue(prepared['ok'], prepared)
            sent = proxy('send', prepared['data']['approval'])
            self.assertTrue(sent['ok'], sent)
            self.assertEqual(sent['data']['operation']['state'], 'done')
        raw, = self.arrivals('one@mail.invalid', sent['data']['operation']['stages']['message_id'])
        self.assertEqual([codec.decoded(p) for p in codec.parse(raw).iter_attachments()], ordinary)

    def nested_fixture(self, kind, encoding, text):
        inner = EmailMessage(policy=codec.SMTP_POLICY)
        inner['From'], inner['Subject'] = self.peer, 'Marked nested source'
        inner['Bcc'] = inner['Resent-Bcc'] = 'private-encoded@mail.invalid'
        inner[codec.AUTHORED_HEADER] = '1'
        inner.set_content(text)
        nested = encapsulated(encapsulated(inner.as_bytes(), kind, encoding), kind, encoding)
        raw = (b'From: Alice <alice@mail.invalid>\r\nTo: ' + self.owner.encode() + b'\r\nSubject: Outer\r\nMessage-ID: <'
               + uuid.uuid4().hex.encode() + b'@mail.invalid>\r\nContent-Type: multipart/mixed; boundary=review3\r\n\r\n'
               + b'--review3\r\nContent-Type: text/plain\r\n\r\nOuter source body\r\n--review3\r\n'
               + b'Content-Disposition: attachment; filename="nested.eml"\r\n' + nested + b'\r\n--review3--\r\n')
        return raw, self.mail.append(self.account, 'INBOX', raw)

    def test_review3_2_received_two_level_encoded_messages_in_all_composition_modes(self):
        for kind in ('rfc822', 'global'):
            for encoding in ('base64', 'quoted-printable'):
                text = 'Full marked words ' + kind + ' ' + encoding
                raw, ref = self.nested_fixture(kind, encoding, text)
                draft = self.mail.append(self.account, self.account['special']['drafts'], raw)
                for mode, style in (('new',None), ('reply',None), ('reply_all',None), ('forward','inline'), ('forward','attachment'), ('draft',None)):
                    with self.subTest(kind=kind, encoding=encoding, mode=mode, style=style):
                        args = {'account':'box', 'mode':mode, 'text':'New authored words',
                                'attachments':[{'reference':ref, 'part':'source'}, {'reference':ref, 'part':'1.2'}]}
                        if mode != 'new':
                            args['reference'] = draft if mode == 'draft' else ref
                        if mode not in ('reply', 'reply_all'):
                            args['to'] = ['one@mail.invalid']
                        if style:
                            args['forward_as'] = style
                        comp = self.data('compose', args)
                        approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})['approval']
                        self.assertIn(visible(text), canonical(approval))
                        for item in approval['description']['attachments']:
                            self.assertIn('Bcc and Resent-Bcc removed', item['transformation'])
                            self.assertIn(text, ''.join(item['authored_text']))
                        sent = self.send(approval)
                        self.assertEqual(sent['state'], 'done', sent)
                        received, = self.arrivals(codec.mailbox(comp['mail']['to'][0]), sent['stages']['message_id'])
                        found = False
                        for headers, data in received_nodes(received):
                            self.assertNotIn('Bcc', headers)
                            self.assertNotIn('Resent-Bcc', headers)
                            self.assertNotIn(b'private-encoded@mail.invalid', data)
                            found = found or text.encode() in data
                        self.assertTrue(found)
                        for part, item in zip(codec.parse(received).iter_attachments(), approval['description']['attachments']):
                            self.assertEqual(sha256(codec.decoded(part)), item['sha256'])
                saved = self.data('attachment_save', {'reference':ref,'part':'source'})['file']
                self.assertEqual(self.engine.blobs.read(saved['sha256']), raw)

    def test_review3_2_large_encoded_marked_draft_is_not_approved_by_hash(self):
        for kind in ('rfc822', 'global'):
            for encoding in ('base64', 'quoted-printable'):
                with self.subTest(kind=kind, encoding=encoding):
                    _, ref = self.nested_fixture(kind, encoding, 'x' * 21000)
                    comp = self.compose(attachments=[{'reference':ref, 'part':'source'}])
                    self.assertIn('x' * 21000, ''.join(comp['mail']['attachments'][0]['authored_text']))
                    result = self.call('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'asking_input_too_large')

    def test_review3_2_broken_encoding_and_nested_header_defects_refuse_compose(self):
        inner = b'From: synthetic@mail.invalid\r\nBroken line\r\nBcc: private@mail.invalid\r\n\r\nBody\r\n'
        for raw in (encapsulated(inner), encapsulated(inner).replace(b'base64', b'x-unknown'), encapsulated(inner) + b'!'):
            ref = self.mail.append(self.account, 'INBOX', raw)
            for part in ('source', '1'):
                with self.subTest(raw=raw, part=part):
                    result = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Refuse unsafe source',
                                                  'attachments':[{'reference':ref, 'part':part}]})
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'file_refused')

    def test_review3_guard_extracted_marked_body_keeps_ancestor_provenance(self):
        inner = EmailMessage()
        inner['From'], inner['Subject'] = self.peer, 'Marked enclosed body'
        inner[codec.AUTHORED_HEADER] = '1'
        inner.set_content('Entire extracted authored body')
        inner.add_alternative('<p>Distinct extracted HTML body</p>', subtype='html')
        outer = EmailMessage()
        outer['From'], outer['Subject'] = self.peer, 'Unmarked outer'
        outer.set_content('Untrusted outer text')
        outer.add_attachment(inner)
        ref = self.fixture(msg=outer)
        comp = self.compose(attachments=[{'reference':ref, 'part':'1.2.1.1'}, {'reference':ref, 'part':'1.2.1.2'}])
        approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})['approval']
        for text in ('Entire extracted authored body', 'Distinct extracted HTML body'):
            self.assertIn(text, canonical(approval))
        stored = self.mail.composition(comp)
        raw = self.mail.mime(stored, '<extracted@mail.invalid>')
        for part in codec.parse(raw).iter_attachments():
            self.assertIn(codec.AUTHORED_HEADER, part)
        incomplete = {**stored, 'mail':{**stored['mail'], 'attachments':[{**att, 'authored_text':[]} for att in stored['mail']['attachments']]}}
        with self.assertRaises(Refused):
            self.mail.check_mime(incomplete, raw)
        sent = self.send(approval)
        self.assertEqual(sent['state'], 'done', sent)
        received, = self.arrivals('one@mail.invalid', sent['stages']['message_id'])
        self.assertIn('Entire extracted authored body', codec.text_part(list(codec.parse(received).iter_attachments())[0]))
        _, encoded = self.nested_fixture('rfc822', 'base64', 'Encoded authored body')
        result = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Refuse parser phantom child',
                                       'attachments':[{'reference':encoded,'part':'1.2.1'}]})
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'file_refused')

    def test_review3_guard_bypassed_sanitizer_refuses_compose_prepare_and_send_without_data(self):
        for private in (True, False):
            with self.subTest(private=private), SMTPFixture(self.root) as smtp:
                self.account.update(smtp_host='localhost', smtp_port=smtp.port)
                self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'wire guard SMTP fixture')
                comp = self.compose()
                approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})['approval']
                inner = (b'From: synthetic@mail.invalid\r\nSubject: Injected\r\n' +
                         (b'Bcc: private-guard@mail.invalid\r\n' if private else b'X-AresOS-Authored: 1\r\n') +
                         b'\r\nHidden authored text\r\n')
                bad = (b'From: synthetic@mail.invalid\r\nSubject: Wire injection\r\nContent-Type: multipart/mixed; boundary=guard\r\n\r\n'
                       b'--guard\r\nContent-Type: text/plain\r\n\r\nFull authored text\r\n--guard\r\n'
                       b'Content-Disposition: attachment; filename="hidden.eml"\r\n' + encapsulated(inner) + b'\r\n--guard--\r\n')
                with patch.object(self.mail, 'mime', return_value=bad):
                    refused = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Full authored text'})
                    self.assertFalse(refused['ok'], refused)
                    self.assertIn('Outgoing MIME guard', refused['error']['message'])
                    refused = self.call('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})
                    self.assertFalse(refused['ok'], refused)
                    with patch.object(self.mail.transport, 'smtp', side_effect=AssertionError('No SMTP connection permitted')):
                        stopped = self.send(approval)
                    self.assertEqual(stopped['state'], 'failed', stopped)
                    self.assertNotIn('smtp_data', stopped['stages'])
                    self.assertEqual(self.send(approval)['state'], 'failed')
                # Bypass the earlier check as well: the check immediately before DATA still stops it.
                approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})['approval']
                original_check = self.mail.check_mime
                calls = []
                def last_check(comp, raw):
                    calls.append(raw)
                    if len(calls) > 1:
                        original_check(comp, raw)
                with patch.object(self.mail, 'mime', return_value=bad), patch.object(self.mail, 'check_mime', side_effect=last_check), patch('smtplib.SMTP_SSL.data', side_effect=AssertionError('SMTP DATA must never be called')) as data:
                    stopped = self.send(approval)
                    data.assert_not_called()
                self.assertEqual(calls, [bad, bad])
                self.assertEqual(smtp.auth_count, 1)
                self.assertEqual(stopped['state'], 'failed', stopped)
                self.assertNotIn('smtp_data', stopped['stages'])
                self.assertEqual(smtp.arrivals(), [])
