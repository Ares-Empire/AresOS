"""Round 5: draft refusal, draft-only markers, and literal text bodies."""
import base64
from email import policy
from email.message import EmailMessage
from email.parser import BytesHeaderParser
import quopri
import re
import unittest
from unittest.mock import patch

from support import MailCase
from smtp_fixture import SMTPFixture
from test_review_fixes_3 import encapsulated
from test_review_fixes_4 import wrapper
from aresos_control.common import Refused, canonical, visible
from aresos_control.mail import codec, guard


def wire_nodes(raw, default='text/plain'):
    """Receipt oracle: raw boundaries/transfer decoding, text is always literal."""
    offset = 0
    for line in raw.splitlines(keepends=True):
        if line in (b'\r\n', b'\r', b'\n'):
            head, payload = raw[:offset], raw[offset + len(line):]
            break
        offset += len(line)
    else:
        return
    headers = BytesHeaderParser(policy=policy.default).parsebytes(head + b'\r\n\r\n')
    headers.set_default_type(default)
    cte = str(headers.get('Content-Transfer-Encoding', '7bit')).lower()
    data = base64.b64decode(payload) if cte == 'base64' else quopri.decodestring(payload) if cte == 'quoted-printable' else payload
    yield headers, data
    major = headers.get_content_maintype()
    if major == 'multipart':
        boundary = re.escape(headers.get_boundary().encode())
        chunks = re.split(rb'(?:^|\r\n)--' + boundary + rb'(--)?[ \t]*(?:\r\n|$)', data)
        for index in range(2, len(chunks), 2):
            if chunks[index - 1] == b'--':
                break
            child_default = 'message/rfc822' if headers.get_content_type() == 'multipart/digest' else 'text/plain'
            yield from wire_nodes(chunks[index], child_default)
    elif major == 'message':
        yield from wire_nodes(data)
    elif major != 'text':
        candidate = data.lstrip().removeprefix(b'\xef\xbb\xbf').lstrip()
        head, sep, _ = candidate.partition(b'\r\n\r\n')
        if sep and all(re.fullmatch(rb'[\x21-\x39\x3b-\x7e]+:[^\r\n]*|[ \t][^\r\n]*', line) for line in head.split(b'\r\n')):
            yield from wire_nodes(candidate)


def marked_containers():
    opaque = b'Content-Type: application/octet-stream\r\n\r\nHidden authored words'
    return [
        b'X-AresOS-Authored: 1\r\nContent-Type: multipart/mixed; boundary=marked\r\n\r\n--marked\r\n' + opaque + b'\r\n--marked--\r\n',
        b'X-AresOS-Authored: 1\r\nContent-Type: message/rfc822\r\n\r\n' + opaque,
        b'Content-Type: application/octet-stream\r\nContent-Transfer-Encoding: base64\r\n\r\n' + base64.b64encode(b'X-AresOS-Authored: 1\r\nHidden authored words'),
    ]


class DraftAndTextGuard(unittest.TestCase):
    def test_review5_markers_on_containers_and_decoded_leaves_always_refuse(self):
        for source in marked_containers():
            for raw in (source, wrapper(source), wrapper(encapsulated(source))):
                with self.subTest(raw=raw):
                    with self.assertRaisesRegex(Refused, 'Drafts cannot be attachments'):
                        codec.rebuild(raw)
                    # Supposed disclosure can never authorize a container marker.
                    with self.assertRaisesRegex(Refused, 'authored marker'):
                        guard.check(wrapper(raw), ['Full authored text'], ['Hidden authored words'])
        # Source provenance cannot disappear with an unlisted header containing
        # a folded marker, even with the bare CR line endings accepted by MIME.
        for newline in (b'\r', b'\n', b'\r\n'):
            raw = (b'X-Unlisted: dropped\n X-AresOS-Authored: 1\nContent-Type: multipart/mixed; boundary=folded\n\n'
                   b'--folded\nContent-Type: text/plain\n\nHidden authored words\n--folded--\n').replace(b'\n', newline)
            _, _, _, authored, _ = codec.source_part(raw, '1.1')
            self.assertTrue(authored)
            with self.assertRaisesRegex(Refused, 'Drafts cannot be attachments'):
                codec.rebuild(raw)
            with self.assertRaises(Refused):
                guard.check(wrapper(raw), ['Full authored text'], ['Hidden authored words'])

    def test_review5_text_payloads_never_become_nested_mail(self):
        for text in ('FYI: the documents are attached.\nPlease review them before Friday.',
                     'Status: all green\nPlease review the documents.',
                     'From: writer@mail.invalid\nSubject: ' + 's' * 23100 + '\n\nSmall body',
                     'Content-Transfer-Encoding: base64\n\nLiteral text, not an encoding'):
            msg = EmailMessage(policy=codec.SMTP_POLICY)
            msg.set_content(text, cte='quoted-printable')
            raw = msg.as_bytes()
            clean, texts = codec.rebuild(raw)
            self.assertEqual(codec.decoded(codec.parse(clean)), codec.decoded(codec.parse(raw)))
            self.assertEqual(texts, [])
            guard.check(clean, [text], [text])
            guard.check(wrapper(raw, kind='text/plain'), ['Full authored text'], [])
        for line in ('Bcc: hidden@mail.invalid', ' \tResent-Bcc \t: hidden@mail.invalid'):
            with self.assertRaisesRegex(Refused, 'literal text-file line'):
                guard.check(wrapper(('FYI: attached\n' + line).encode(), kind='text/plain'), ['Full authored text'], [])

    def test_review5_opaque_bytes_need_complete_well_formed_headers(self):
        for data in (b'FYI: attached\nPlease review\n\nOrdinary prose',
                     b'Status: all green\nPlease review', b'Content-Type: text/plain'):
            self.assertFalse(codec.possible_entity(data))
            raw = wrapper(data)
            clean, _ = codec.rebuild(raw)
            self.assertEqual(codec.decoded(next(codec.parse(clean).iter_attachments())), data)
            guard.check(clean, ['Full authored text'], [])
        nested = b'Content-Transfer-Encoding: base64\r\n\r\n' + base64.b64encode(b'Bcc: hidden@mail.invalid')
        self.assertTrue(codec.possible_entity(nested))
        with self.assertRaisesRegex(Refused, 'literal text-file line'):
            guard.check(wrapper(nested), ['Full authored text'], [])
        for raw in (b'Content-Type: message/rfc822\r\n\r\nBroken header\r\n\r\nBody',
                    b'Content-Type: text/plain\r\nContent-Transfer-Encoding: base64\r\n\r\n!!!'):
            with self.assertRaises(Refused):
                codec.rebuild(raw)
            with self.assertRaises(Refused):
                guard.check(raw, [], [])

    def test_review5_literal_main_body_marker_needs_full_disclosure_and_no_header_marker(self):
        text = 'Approved literal text\nX-AresOS-Authored: 1\nEntire body'
        msg = EmailMessage(policy=codec.SMTP_POLICY)
        msg.set_content(text)
        with self.assertRaises(Refused):
            guard.check(msg.as_bytes(), [text], [])
        guard.check(msg.as_bytes(), [text], [text])
        msg[codec.AUTHORED_HEADER] = '1'
        with self.assertRaises(Refused):
            guard.check(msg.as_bytes(), [text], [text])
        guard.check(msg.as_bytes(), [text], [text], draft=True)


class ReviewFixes5(MailCase):
    def keys(self, comp):
        return {k: comp[k] for k in ('composition_id', 'composition_hash')}

    def save(self, text):
        comp = self.compose(text=text)
        return self.data('draft_save', self.keys(comp))['reference']

    def assert_draft_refused(self, args):
        result = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Draft refusal', **args})
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'file_refused')
        for phrase in ('Drafts cannot be attachments', 'mode=draft', 'forward it inline'):
            self.assertIn(phrase, result['error']['message'])

    def assert_no_private_headers(self, raw):
        nodes = list(wire_nodes(raw))
        self.assertTrue(nodes)
        for headers, data in nodes:
            self.assertFalse(any(name.lower().startswith('x-aresos') for name in headers), headers)
            self.assertFalse(re.search(rb'(?im)^[ \t]*x-aresos[^\r\n:]*:', data), data[:500])

    def test_review5_header_like_saved_draft_source_and_parts_refused_even_after_move_copy(self):
        self.data('folder_create', {'account':'box', 'name':'Round5-drafts'})
        for size in (20, 23100):
            text = 'From: writer@mail.invalid\nSubject: ' + 's' * size + '\n\nSmall body'
            saved = self.save(text)
            # Round 6 forbids leaving Drafts; retain the ordinary-folder
            # move/copy provenance regression with the exact saved bytes.
            draft = self.mail.append(self.account, "INBOX", self.mail.message(saved)["raw"])
            copied = self.data('copy', {'references':[draft], 'target':'Round5-drafts'})['items'][0]
            moved = self.data('move', {'references':[draft], 'target':'Round5-drafts'})['items'][0]
            for ref in (copied, moved):
                self.assertIn(codec.AUTHORED_HEADER, self.mail.message(ref)['msg'])
                for part in ('source', '1'):
                    self.assert_draft_refused({'attachments':[{'reference':ref, 'part':part}]})
                self.assert_draft_refused({'mode':'forward', 'reference':ref, 'forward_as':'attachment'})
                # Moving the draft must not make the advertised mode=draft unusable.
                for mode in ('draft', 'forward', 'reply', 'reply_all'):
                    args = {'account':'box', 'mode':mode, 'reference':ref}
                    if mode == 'forward':
                        args.update(to=['one@mail.invalid'], forward_as='inline')
                    comp = self.data('compose', args)
                    result = self.call('prepare_send', self.keys(comp))
                    if size > 20000:
                        self.assertFalse(result['ok'], result)
                        self.assertEqual(result['error']['code'], 'asking_input_too_large')
                        self.assertIn('Nothing was reserved', result['error']['message'])
                    else:
                        self.assertTrue(result['ok'], result)
                        shown = canonical(result['data']['approval'])
                        if mode == 'draft':
                            self.assertEqual(result['data']['approval']['description']['generated_parts'][0]['text'], visible(text.replace('\n', '\r\n') + '\r\n'))
                        else:
                            self.assertIn('Subject: ' + 's' * size, shown)
                        self.assertIn('Small body', shown)

    def test_review5_special_use_drafts_and_nested_draft_ancestors_refused_before_rebuild(self):
        msg = EmailMessage()
        msg['From'], msg['To'] = self.peer, 'one@mail.invalid'
        msg.set_content('Unmarked owner draft')
        msg.add_attachment(b'Ordinary file', maintype='application', subtype='octet-stream', filename='ordinary.bin')
        ref = self.fixture(self.account['special']['drafts'], msg=msg)
        self.assertNotIn(codec.AUTHORED_HEADER, self.mail.message(ref)['msg'])
        for part in ('source', '1', '1.1', '1.2'):
            self.assert_draft_refused({'attachments':[{'reference':ref, 'part':part}]})
        self.assert_draft_refused({'mode':'forward', 'reference':ref, 'forward_as':'attachment'})
        for kind in ('rfc822', 'global'):
            for encoding in ('base64', 'quoted-printable'):
                for marked in marked_containers():
                    raw = encapsulated(encapsulated(marked, kind, encoding), kind, encoding)
                    nested = self.mail.append(self.account, 'INBOX', raw)
                    for part in ('source', '1'):
                        self.assert_draft_refused({'attachments':[{'reference':nested, 'part':part}]})
                    self.assert_draft_refused({'mode':'forward', 'reference':nested, 'forward_as':'attachment'})
        msg[codec.AUTHORED_HEADER] = '1'
        outer = EmailMessage()
        outer['From'] = self.peer
        outer.set_content('Received wrapper')
        outer.add_attachment(msg)
        nested = self.fixture(msg=outer)
        for part in ('1.2.1.1', '1.2.1.2'):
            self.assert_draft_refused({'attachments':[{'reference':nested, 'part':part}]})
        folded = (b'From: peer@mail.invalid\r\nSubject: Folded draft provenance\r\n'
                  b'X-Unlisted: dropped\r\n X-AresOS-Authored: 1\r\n'
                  b'Content-Type: text/plain\r\n\r\nEntire folded draft body\r\n')
        ref = self.mail.append(self.account, 'INBOX', folded)
        for part in ('source', '1'):
            self.assert_draft_refused({'attachments':[{'reference':ref, 'part':part}]})
        for mode in ('draft', 'forward'):
            comp = self.data('compose', {'account':'box', 'mode':mode, 'reference':ref, 'to':['one@mail.invalid']})
            approval = self.data('prepare_send', self.keys(comp))['approval']
            self.assertIn('Entire folded draft body', approval['description']['generated_parts'][0]['text'])

    def test_review5_all_modes_smtp_and_sent_have_no_private_headers_and_sent_can_forward(self):
        ref = self.fixture(text='Received text', attachments=[('ordinary.bin', b'File bytes', 'application/octet-stream')])
        draft = self.save('Full draft body')
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'round 5 SMTP sink')
            sent_refs = []
            for mode, style, fmt in (('new',None,'plain'), ('new',None,'formatted'), ('reply',None,'plain'),
                                     ('reply_all',None,'formatted'), ('forward','inline','plain'),
                                     ('forward','attachment','plain'), ('draft',None,'plain')):
                with self.subTest(mode=mode, style=style, fmt=fmt):
                    args = {'account':'box', 'mode':mode, 'format':fmt}
                    if mode != 'draft':
                        args['text'] = 'Full authored text'
                    if mode != 'new':
                        args['reference'] = draft if mode == 'draft' else ref
                    if mode in ('new', 'forward'):
                        args['to'] = ['one@mail.invalid']
                    if style:
                        args['forward_as'] = style
                    comp = self.data('compose', args)
                    approval = self.data('prepare_send', self.keys(comp))['approval']
                    sent = self.send(approval)
                    self.assertEqual(sent['state'], 'done', sent)
                    self.assert_no_private_headers(smtp.arrivals()[-1][1])
                    sent_ref, = self.data('operation_status', {'operation_id':sent['id']})['evidence']['sent']
                    self.assert_no_private_headers(self.mail.message(sent_ref)['raw'])
                    sent_refs.append(sent_ref)
            comp = self.compose(mode='forward', reference=sent_refs[0], forward_as='attachment')
            item, = comp['mail']['attachments']
            self.assertEqual(item['type'], 'application/octet-stream')
            self.assertEqual(item['name'], 'forward.eml')
            sent = self.send(self.data('prepare_send', self.keys(comp))['approval'])
            self.assertEqual(sent['state'], 'done', sent)
            self.assert_no_private_headers(smtp.arrivals()[-1][1])

    def test_review5_header_like_draft_sent_itself_discloses_whole_body_and_long_body_refuses(self):
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'literal draft SMTP sink')
            for size in (20, 23100):
                text = 'From: writer@mail.invalid\nSubject: ' + 's' * size + '\n\nSmall body'
                ref = self.save(text)
                comp = self.data('compose', {'account':'box', 'mode':'draft', 'reference':ref})
                expected = visible(text.replace('\n', '\r\n') + '\r\n')
                self.assertEqual(comp['mail']['generated_parts'][0]['text'], expected)
                result = self.call('prepare_send', self.keys(comp))
                if size > 20000:
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'asking_input_too_large')
                else:
                    self.assertTrue(result['ok'], result)
                    self.assertEqual(result['data']['approval']['description']['generated_parts'][0]['text'], expected)
                    sent = self.send(result['data']['approval'])
                    self.assertEqual(sent['state'], 'done', sent)
                    received = smtp.arrivals()[-1][1]
                    self.assertEqual(codec.body(codec.parse(received)).replace('\r\n', '\n').rstrip('\n'), text)
                    self.assert_no_private_headers(received)
            self.assertEqual(len(smtp.arrivals()), 1)

    def test_review5_prose_colon_first_line_new_plain_formatted_reply_and_text_attachment(self):
        ref = self.fixture(text='Received quote')
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'ordinary prose SMTP sink')
            for first in ('FYI: the documents are attached.', 'Status: all green'):
                text = first + '\nPlease review them before Friday.'
                for mode in ('new', 'reply'):
                    for fmt in ('plain', 'formatted'):
                        args = {'account':'box', 'mode':mode, 'format':fmt, 'text':text}
                        if mode == 'reply':
                            args['reference'] = ref
                        else:
                            args['to'] = ['one@mail.invalid']
                        comp = self.data('compose', args)
                        approval = self.data('prepare_send', self.keys(comp))['approval']
                        self.assertEqual(approval['description']['text'], visible(text))
                        self.assertEqual(self.send(approval)['state'], 'done')
                        body = codec.body(codec.parse(smtp.arrivals()[-1][1])).replace('\r\n', '\n').rstrip('\n')
                        expected = first + ('\n\n' if fmt == 'formatted' else '\n') + 'Please review them before Friday.'
                        if mode == 'new':
                            self.assertEqual(body, expected)
                        else:
                            self.assertTrue(body.startswith(expected), body)
                            self.assertIn('> Received quote', body)
            for text in ('FYI: the documents are attached.\nPlease review them before Friday.',
                         'Status: all green\nPlease review them before Friday.'):
                attachment = self.fixture(text=text)
                comp = self.compose(attachments=[{'reference':attachment, 'part':'1'}])
                self.assertEqual(self.send(self.data('prepare_send', self.keys(comp))['approval'])['state'], 'done')
                received = codec.parse(smtp.arrivals()[-1][1])
                part, = received.iter_attachments()
                self.assertEqual(codec.decoded(part).decode().replace('\r\n', '\n').rstrip('\n'), text)
            attachment = self.fixture(text='FYI: attached\nBcc: hidden@mail.invalid\nLiteral file')
            refused = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Text file', 'attachments':[{'reference':attachment,'part':'1'}]})
            self.assertFalse(refused['ok'], refused)
            self.assertIn('literal text-file line', refused['error']['message'])

    def test_review5_builder_bypass_marked_containers_fail_compose_and_send_no_data_or_replay(self):
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'container guard SMTP sink')
            for source in marked_containers():
                bad = wrapper(source)
                comp = self.compose()
                keys = self.keys(comp)
                approval = self.data('prepare_send', keys)['approval']
                with patch.object(self.mail, 'mime', return_value=bad):
                    refused = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Full authored text'})
                    self.assertFalse(refused['ok'], refused)
                    self.assertIn('authored marker', refused['error']['message'])
                    self.assertFalse(self.call('prepare_send', keys)['ok'])
                    with patch('smtplib.SMTP_SSL.data', side_effect=AssertionError('DATA forbidden')) as data:
                        stopped = self.send(approval)
                        self.assertEqual(stopped['state'], 'failed', stopped)
                        self.assertEqual(self.send(approval)['state'], 'failed')
                        data.assert_not_called()
                    self.assertNotIn('smtp_data', stopped['stages'])
                approval = self.data('prepare_send', keys)['approval']
                original_check, calls = self.mail.check_mime, []
                def final_only(comp, raw):
                    calls.append(raw)
                    if len(calls) > 1:
                        original_check(comp, raw)
                with patch.object(self.mail, 'mime', return_value=bad), patch.object(self.mail, 'check_mime', side_effect=final_only), patch('smtplib.SMTP_SSL.data', side_effect=AssertionError('DATA forbidden')) as data:
                    stopped = self.send(approval)
                    self.assertEqual(stopped['state'], 'failed', stopped)
                    data.assert_not_called()
                self.assertEqual(calls, [bad, bad])
                self.assertNotIn('smtp_data', stopped['stages'])
                self.assertEqual(self.send(approval)['state'], 'failed')
            self.assertEqual(smtp.auth_count, 3)
            self.assertEqual(smtp.arrivals(), [])
