"""Round 12 questions through the real adapter/Engine, without a mail server."""
import copy
from contextlib import contextmanager
from email.message import EmailMessage
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import WORK, MailCase
from smtp_fixture import SMTPFixture
from test_review_fixes_11 import MemoryIMAP
from aresos_control.common import ASK_LIMIT, QUESTION_LIMIT, approval_input, canonical, digest, visible
from aresos_control.engine import Engine
from aresos_control.mail import codec
from aresos_control.mail.questions import question, short
from aresos_control.mail.roles import resolve
from aresos_control.mail.transport import folders


class PlainQuestions12(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: self.engine.close())
        self.mail = self.engine.adapters['mail']
        self.imap = MemoryIMAP(7, b'<question@mail.invalid>')
        @contextmanager
        def imap(account):
            yield self.imap
        patcher = patch.object(self.mail.transport, 'imap', imap)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.account = {'id': 'box', 'addresses': ['owner@example.com'], 'ready': True,
                        'capabilities': list(self.imap.capabilities), 'smtp_capabilities': [], 'sent_policy': 'client',
                        'safe_folder_delete': True, 'format': 'plain', 'signature': '', **resolve(folders(self.imap))}
        self.engine.store.write({'mail:account:box': self.account}, 'fixture', 'Synthetic question account')

    def call(self, verb, args):
        return self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_' + verb, 'arguments': args})

    def data(self, verb, args):
        result = self.call(verb, args)
        self.assertTrue(result['ok'], result)
        return result['data']

    def approval(self, verb, args):
        approval = self.data('prepare_' + verb, args)['approval']
        self.assertEqual(list(approval), ['question', 'operation_id', 'description'])
        self.assertLessEqual(len(approval['question']), QUESTION_LIMIT)
        self.assertLessEqual(len(canonical(approval).encode()), ASK_LIMIT)
        return approval

    def compose(self, **args):
        result = self.data('compose', {'account': 'box', 'to': ['Anna Example <anna@example.com>'], 'text': 'one\ntwo\n', **args})
        return {k: result[k] for k in ('composition_id', 'composition_hash')}

    def reference(self, uid=1):
        return {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
                'uid': uid, 'message_id': self.imap.mid}

    def test_round12_send_many_groups_names_fallback_and_attachments_keep_full_fields(self):
        groups = {key: [f'{key.title()} Example {i} <{key}{i}@example.com>' for i in range(7)] for key in ('to', 'cc', 'bcc')}
        groups['to'][:3] = ['Zoë Example <zoe@example.com>', '李 Example <li@example.com>', 'bare@example.com']
        attachments = []
        for i in range(7):
            raw = f'binary-{i}'.encode() + b'\x00'
            ref = {'sha256': self.engine.blobs.put(raw, origin='caller_import'), 'size': len(raw),
                   'name': f'offer-{i}.pdf', 'real_path': f'/fixture/offer-{i}.pdf', 'last_changed': '2026-11-07T10:00:00+00:00'}
            self.engine.store.write({'blob:' + digest(ref): ref}, 'fixture', 'Synthetic import')
            attachments.append(ref)
        approval = self.approval('send', self.compose(**groups, subject='Angebot für die Wohnung', attachments=attachments))
        text, details = approval['question'], approval['description']
        self.assertIn('to Zoë Example <zoe@example.com>, 李 Example <li@example.com>, bare@example.com and 4 more', text)
        self.assertIn(', Cc Cc Example 0 <cc0@example.com>, Cc Example 1 <cc1@example.com>, Cc Example 2 <cc2@example.com> and 4 more', text)
        self.assertIn('hidden copy (Bcc) to Bcc Example 0 <bcc0@example.com>, Bcc Example 1 <bcc1@example.com>, Bcc Example 2 <bcc2@example.com> and 4 more', text)
        self.assertIn('Subject: Angebot für die Wohnung; 2 lines, 7 attachments: offer-0.pdf, offer-1.pdf, offer-2.pdf and 4 more', text)
        for key in groups:
            self.assertEqual(details[key], groups[key])
        self.assertEqual(details['text'], visible('one\ntwo\n'))
        self.assertEqual(len(details['attachments']), 7)
        comp = self.mail.composition({'composition_id': details['composition_id'], 'composition_hash': details['composition_hash']})
        for key, value in visible(comp['mail']).items():
            self.assertEqual(details[key], value)

    def test_round12_lookalike_names_always_show_their_real_address(self):
        # A familiar name with a stranger's address: the sentence the owner reads must show the address.
        long_name = 'Mom ' + 'x' * 200
        comp = self.mail.composition(self.compose())['mail']
        comp = {**comp, 'to': ['Mom <stranger@example.org>'], 'cc': [long_name + ' <other.stranger@example.org>'],
                'bcc': ['"Mom\u202e" <third@example.org>']}
        text = approval_input('fixed', comp, question('send', comp))['question']
        self.assertIn('to Mom <stranger@example.org>', text)
        # Only the name is cut; the address stays whole after it.
        self.assertIn('Cc ' + short(long_name) + ' <other.stranger@example.org>', text)
        self.assertIn('hidden copy (Bcc) to Mom\\u202e <third@example.org>', text)
        items = [{'reference': {}, 'from': 'Mom <stranger@example.org>', 'subject': 'Hi', 'date': 'Thu, 05 Nov 2026 10:00:00 +0000'},
                 {'reference': {}, 'from': long_name + ' <other.stranger@example.org>', 'subject': 'Hi', 'date': 'Thu, 05 Nov 2026 10:00:00 +0000'}]
        text = question('delete', {'items': items, 'mode': 'trash'})
        self.assertIn("from Mom <stranger@example.org>, 'Hi' (5 Nov)", text)
        self.assertIn('from ' + short(long_name) + " <other.stranger@example.org>, 'Hi'", text)
        source = {'From': 'Mom <stranger@example.org>'}
        text = question('unsubscribe', {'target': 'mailto:leave@example.com', 'to': ['leave@example.com']}, source)
        self.assertTrue(text.startswith('Unsubscribe from Mom <stranger@example.org> by'), text)

    def test_round12_controls_bidi_and_backslashes_escape_once_without_cutting_escapes(self):
        comp = self.mail.composition(self.compose())['mail']
        comp = {**comp, 'to': ['"Anna\u202e\x01\\ Example" <anna@example.com>'],
                'subject': 'Wohnung\x00\u2066\\u202e', 'attachments': [{'name': 'f' * 78 + '\u202e.pdf'}]}
        approval = approval_input('fixed', comp, question('send', comp))
        self.assertIn(visible(comp['subject']), approval['question'])
        self.assertIn('\\u202e', approval['question'])
        self.assertIn('\\u0001', approval['question'])
        self.assertEqual(approval['description'], visible(comp))
        self.assertNotIn('\u202e', approval['question'])
        self.assertEqual(visible(short('x' * 78 + '\u202e.pdf')), 'x' * 78 + '…')
        self.assertEqual(visible(short('x' * 74 + '\u202e.pdf')), 'x' * 74 + '\\u202e…')
        folder = {'folder': 'Projects/Old\u202e\\\x01'}
        self.assertEqual(approval_input('fixed', folder, question('folder_delete', folder))['question'],
                         "Delete the empty folder '" + visible(folder['folder']) + "'?")

    def test_round12_reply_quotes_and_both_forwards_describe_generated_content(self):
        msg = EmailMessage()
        msg['From'] = 'Anna\u202e Example <anna@example.com>'
        msg['To'] = 'owner@example.com'
        msg['Subject'] = 'Wohnung\u2066'
        msg['Date'] = 'Thu, 05 Nov 2026 10:00:00 +0000'
        msg['Message-ID'] = self.imap.mid
        msg.set_content('Earlier text')
        self.imap.boxes['Source'][1] = msg.as_bytes(policy=codec.SMTP_POLICY)
        for mode, forward_as in (('reply', 'inline'), ('forward', 'inline'), ('forward', 'attachment')):
            with self.subTest(mode=mode, forward_as=forward_as):
                args = {'mode': mode, 'reference': self.reference(), 'forward_as': forward_as, 'text': 'Answer'}
                if mode == 'reply':
                    # Replies derive recipients rather than accepting the helper's To.
                    result = self.data('compose', {'account': 'box', **args})
                    comp = {k: result[k] for k in ('composition_id', 'composition_hash')}
                else:
                    comp = self.compose(**args)
                approval = self.approval('send', comp)
                self.assertIn('1 line', approval['question'])
                self.assertIn('quotes the earlier mail' if mode == 'reply' else 'forwards 1 mail', approval['question'])
                self.assertIn(visible('Wohnung\u2066'), approval['question'])
                if mode == 'reply':
                    self.assertIn(visible('Anna\u202e Example'), approval['question'])

    def test_round12_delete_both_modes_many_messages_and_empty_folder(self):
        for uid in range(1, 8):
            self.imap.boxes['Source'][uid] = self.imap.raw.replace(b'From: sender@mail.invalid', b'From: Anna Example <anna@example.com>').replace(b'Subject: Filing', f'Subject: Offer {uid}'.encode()).replace(
                b'\r\n\r\n', b'\r\nDate: Thu, 05 Nov 2026 10:00:00 +0000\r\n\r\n')
        items = [self.mail.named_item(self.reference(uid)) for uid in range(1, 8)]
        for mode in ('permanent', 'trash'):
            approval = self.approval('delete', {'items': items, 'mode': mode})
            text = approval['question']
            self.assertTrue(text.startswith('Delete 7 messages for good' if mode == 'permanent' else 'Move 7 messages to Trash'))
            self.assertIn("from Anna Example <anna@example.com>, 'Offer 1' (5 Nov)", text)
            self.assertIn('and 4 more', text)
            self.assertNotIn('Offer 4', text)
            self.assertEqual(approval['description']['items'], items)
        approval = self.approval('folder_delete', {'account': 'box', 'folder': 'Target'})
        self.assertEqual(approval['question'], "Delete the empty folder 'Target'?")
        self.assertEqual(self.imap.mutations, [])

    def test_round12_unsubscribe_mailto_and_one_click_list_or_sender(self):
        for target in ('mailto:leave@example.com?subject=Stop&body=Leave', 'https://news.example.com/leave?token=synthetic'):
            for list_id in (None, 'Example news <news.example.com>'):
                msg = EmailMessage()
                msg['From'] = 'Anna Example <anna@example.com>'
                msg['Message-ID'] = self.imap.mid
                msg['List-Unsubscribe'] = '<' + target + '>'
                msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
                if list_id:
                    msg['List-ID'] = list_id
                msg.set_content('News')
                self.imap.boxes['Source'][1] = msg.as_bytes(policy=codec.SMTP_POLICY)
                approval = self.approval('unsubscribe', {'reference': self.reference(), 'target': target})
                self.assertIn('Unsubscribe from ' + (list_id or 'Anna Example <anna@example.com>'), approval['question'])
                self.assertIn('by sending a mail to leave@example.com?' if target.startswith('mailto') else 'by a one-click web request to news.example.com?', approval['question'])
                self.assertEqual(approval['description']['target'], target)

    def test_round12_mail_changed_and_missing_question_never_execute(self):
        comp = self.compose()
        items = [self.mail.named_item(self.reference())]
        before = copy.deepcopy(self.imap.boxes)
        for verb, args in (('send', comp), ('delete', {'items': items, 'mode': 'permanent'})):
            approval = self.approval(verb, args)
            for remove in (False, True):
                altered = copy.deepcopy(approval)
                if remove:
                    del altered['question']
                else:
                    altered['question'] = 'A different operation?'
                with patch.object(self.mail, 'execute', wraps=self.mail.execute) as execute:
                    result = self.call(verb, altered)
                self.assertEqual(result['error']['code'], 'stale_approval', result)
                execute.assert_not_called()
                self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
        self.assertEqual(self.imap.boxes, before)
        self.assertEqual(self.imap.mutations, [])

    def test_round12_complete_question_and_description_share_limit_no_reservation_on_overflow(self):
        with patch('aresos_control.engine.time.time', return_value=1000):
            # A single-line body keeps the question and fixed-size ids unchanged.
            comp = self.compose(subject='Subject as written', text='x')
            stored = self.mail.composition(comp)
            preview = {**stored['mail'], 'action': 'mail_send', 'composition_id': stored['id'], 'composition_hash': stored['hash'], 'expires_at': 1900}
            template = approval_input('0' * 65, {**preview, 'text': ''}, question('send', preview))
            length = ASK_LIMIT - len(canonical(template).encode())
            exact = self.compose(subject='Subject as written', text='x' * length)
            approval = self.approval('send', exact)
            self.assertEqual(len(canonical(approval).encode()), ASK_LIMIT)
            self.assertEqual(approval['description']['text'], 'x' * length)
            too_big = self.compose(subject='Subject as written', text='x' * (length + 1))
            count = len(self.engine.store.items('op:'))
            self.assertEqual(self.call('prepare_send', too_big)['error']['code'], 'asking_input_too_large')
            long_subject = self.compose(subject='s' * QUESTION_LIMIT)
            self.assertEqual(self.call('prepare_send', long_subject)['error']['code'], 'asking_input_too_large')
            self.assertEqual(len(self.engine.store.items('op:')), count)

    def test_round12_onboarding_and_mail_repair_questions_first(self):
        for empty in (False, True):
            args = {'account': 'box', 'folder': 'AresOS-probe-synthetic', 'empty': empty}
            state = {'account': 'box', 'folder': args['folder'], 'uidvalidity': 100, 'uids': []}
            with patch.object(self.mail, 'safe_folder', return_value=state):
                approval = self.engine.reserve('mail', 'onboarding_folder_probe', args)['approval']
            self.assertEqual(list(approval), ['question', 'operation_id', 'description'])
            self.assertEqual(approval['question'], f"Test deleting the {'empty' if empty else 'nonempty'} disposable setup folder 'AresOS-probe-synthetic'?")
        approval = self.approval('send', self.compose())
        old = self.engine.operation(approval['operation_id'])
        old.update(state='partial', stages={'smtp_data': 'accepted:250'})
        self.engine.store.write({'op:' + old['id']: old}, 'fixture', 'Synthetic accepted send')
        for stage in ('sent_copy', 'answered_flag'):
            with patch.object(self.mail, 'repair', return_value='done'), patch.object(self.mail, 'repaired_outcome', return_value=('done', 'Local stage repaired')):
                repaired = self.data('operation_repair', {'operation_id': old['id'], 'stage': stage})['operation']
            self.assertEqual(list(repaired['approval']), ['question', 'operation_id', 'description'])
            self.assertIn('Repair the ' + ('Sent copy' if stage == 'sent_copy' else 'answered flag'), repaired['approval']['question'])
            self.assertIn(old['id'], repaired['approval']['question'])


class ServerQuestions12(MailCase):
    def test_round12_real_servers_tampered_or_removed_question_no_send_or_delete(self):
        ref = self.fixture(subject='Question protection')
        with SMTPFixture(self.root) as smtp:
            account = {**self.account, 'smtp_host': 'localhost', 'smtp_port': smtp.port}
            self.engine.store.write({'mail:account:box': account}, 'fixture', 'Synthetic SMTP')
            for verb, approval in (('send', self.approval()), ('delete', self.delete_approval([ref], 'permanent'))):
                self.assertEqual(list(approval), ['question', 'operation_id', 'description'])
                for remove in (False, True):
                    changed = copy.deepcopy(approval)
                    if remove:
                        del changed['question']
                    else:
                        changed['question'] = 'Do something else?'
                    result = self.call(verb, changed)
                    self.assertEqual(result['error']['code'], 'stale_approval', result)
                    self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
            self.assertEqual(smtp.arrivals(), [])
            self.assertEqual(str(self.mail.message(ref)['msg']['Subject']), 'Question protection')
