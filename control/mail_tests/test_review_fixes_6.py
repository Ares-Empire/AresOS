"""Round 6: Drafts cannot leave; fresh IMAP Draft flags protect every folder."""
from email.message import EmailMessage

from support import MailCase
from smtp_fixture import SMTPFixture
from aresos_control.common import canonical, visible
from aresos_control.mail import codec
from aresos_control.mail.transport import fetch, ok, select, uids


class ReviewFixes6(MailCase):
    def keys(self, comp):
        return {k: comp[k] for k in ('composition_id', 'composition_hash')}

    def server_state(self, names):
        result = {}
        with self.mail.transport.imap(self.account) as conn:
            for name in names:
                validity = select(conn, name)
                result[name] = (validity, [(uid, *fetch(conn, uid, self.mail.wires.limit)) for uid in uids(conn)])
        return result

    def assert_attachment_refused(self, ref, parts=('source', '1')):
        attempts = [{'attachments':[{'reference':ref, 'part':part}]} for part in parts]
        attempts.append({'mode':'forward', 'reference':ref, 'forward_as':'attachment'})
        for args in attempts:
            with self.subTest(reference=ref, attempt=args):
                result = self.call('compose', {'account':'box', 'to':['one@mail.invalid'], 'text':'Draft refusal', **args})
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error']['code'], 'file_refused')
                for phrase in ('Drafts cannot be attachments', 'mode=draft', 'forward it inline'):
                    self.assertIn(phrase, result['error']['message'])

    def test_review6_unmarked_marked_flagged_drafts_and_subfolders_refuse_move_copy_atomically(self):
        drafts, archive = (self.account['special'][k] for k in ('drafts', 'archive'))
        child = drafts + self.account['delimiter'] + 'Owner-work'
        self.data('folder_create', {'account':'box', 'name':child})
        ordinary = self.fixture(text='Ordinary first item must stay too')
        for folder in (drafts, child):
            for kind in ('unmarked', 'marked', 'flagged'):
                ref = self.fixture(folder, sender=self.owner, text='Unsent owner words',
                                   headers={codec.AUTHORED_HEADER:'1'} if kind == 'marked' else {},
                                   flags='(\\Draft)' if kind == 'flagged' else None)
                message = self.mail.message(ref)
                if kind == 'unmarked':
                    self.assertNotIn(codec.AUTHORED_HEADER, message['msg'])
                    self.assertNotIn('\\Draft', message['flags'])
                for verb in ('move', 'copy'):
                    # The ordinary reference comes first to catch per-item checks
                    # that discover Drafts only after changing earlier messages.
                    before = self.server_state(['INBOX', drafts, child, archive])
                    result = self.call(verb, {'references':[ordinary, ref], 'target':archive})
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'refused')
                    for phrase in ('mail_compose', 'mode=draft', 'mail_delete', 'asks the owner'):
                        self.assertIn(phrase, result['error']['message'])
                    self.assertEqual(self.server_state(['INBOX', drafts, child, archive]), before)
                self.assert_attachment_refused(ref)

    def test_review6_flagged_inbox_archive_and_deep_parts_refuse_and_allowed_moves_keep_flag(self):
        archive = self.account['special']['archive']
        for folder, target in (('INBOX', archive), (archive, 'INBOX')):
            leaf = EmailMessage()
            leaf.set_content('Deep unsent words')
            nested = EmailMessage()
            nested.set_content('Nested wrapper')
            nested.add_attachment(leaf)
            msg = EmailMessage()
            msg['From'], msg['To'] = self.owner, 'one@mail.invalid'
            msg.set_content('Unmarked owner draft outside Drafts')
            msg.add_attachment(nested)
            ref = self.fixture(folder, msg=msg, flags='(\\Draft keep)')
            original = self.mail.message(ref)
            self.assertNotIn(codec.AUTHORED_HEADER, original['msg'])
            parts = ('source', *codec.parts(original['msg']))
            before = self.server_state(['INBOX', archive])
            self.assert_attachment_refused(ref, parts)
            self.assertEqual(self.server_state(['INBOX', archive]), before)
            copied = self.data('copy', {'references':[ref], 'target':target})['items'][0]
            moved = self.data('move', {'references':[ref], 'target':target})['items'][0]
            for changed in (copied, moved):
                current = self.mail.message(changed)
                self.assertEqual(current['raw'], original['raw'])
                self.assertEqual(current['flags'], original['flags'])
                self.assert_attachment_refused(changed, parts)
            self.assertFalse(self.call('read', {'reference':ref})['ok'])

    def test_review6_flagged_literal_text_fully_disclosed_or_oversized_in_all_inline_modes(self):
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box':self.account}, 'fixture', 'round 6 SMTP sink')
            for folder in ('INBOX', self.account['special']['archive']):
                for size in (32, 23100):
                    text = 'From: writer@mail.invalid\nSubject: ' + 's' * size + '\n\nEntire unsent body\nFinal words'
                    ref = self.fixture(folder, sender=self.owner, to='one@mail.invalid', text=text, flags='(\\Draft keep)')
                    original = self.mail.message(ref)
                    raw_body, before = codec.body(original['msg']), original['flags']
                    for mode in ('draft', 'reply', 'reply_all', 'forward'):
                        args = {'account':'box', 'mode':mode, 'reference':ref}
                        if mode == 'forward':
                            args.update(to=['one@mail.invalid'], forward_as='inline')
                        comp = self.data('compose', args)
                        generated, = comp['mail']['generated_parts']
                        # Compare the complete text, including header-like prose.
                        if mode == 'draft':
                            expected = raw_body
                        elif mode == 'forward':
                            headers = '\n'.join(h + ': ' + str(original['msg'].get(h, '')) for h in ('From', 'Date', 'Subject', 'To', 'Cc'))
                            expected = '\n\n---------- Forwarded mail ----------\n' + headers + '\n\n' + raw_body
                        else:
                            expected = '\n\n' + self.owner + ' — ' + str(original['msg'].get('Date', '')) + ':\n' + '\n'.join('> ' + line for line in raw_body.splitlines())
                        self.assertEqual(generated['text'], visible(expected))
                        result = self.call('prepare_send', self.keys(comp))
                        if size > 20000:
                            self.assertFalse(result['ok'], result)
                            self.assertEqual(result['error']['code'], 'asking_input_too_large')
                            self.assertIn('Nothing was reserved', result['error']['message'])
                        else:
                            self.assertTrue(result['ok'], result)
                            self.assertEqual(result['data']['approval']['description']['generated_parts'][0]['text'], visible(expected))
                            self.assertEqual(self.send(result['data']['approval'])['state'], 'done')
                            received = codec.body(codec.parse(smtp.arrivals()[-1][1]))
                            self.assertEqual(received.replace('\r\n', '\n').rstrip('\n'), expected.replace('\r\n', '\n').rstrip('\n'))
                    # Reply submission may add Answered, but reading/compose must
                    # never consume Draft or set Seen.
                    after = self.mail.message(ref)['flags']
                    self.assertEqual(set(after) - {'\\Answered'}, set(before))
            self.assertEqual(len(smtp.arrivals()), 8)

    def test_review6_flagged_draft_differing_html_is_disclosed_whole(self):
        msg = EmailMessage()
        msg['From'], msg['To'] = self.owner, 'one@mail.invalid'
        msg.set_content('Plain unsent words')
        msg.add_alternative('<p>Entire different HTML <a href="https://link.invalid/path">link</a></p>', subtype='html')
        ref = self.fixture(self.account['special']['archive'], msg=msg, flags='(\\Draft)')
        before = self.server_state([ref['folder']])
        comp = self.data('compose', {'account':'box', 'mode':'draft', 'reference':ref})
        approval = self.data('prepare_send', self.keys(comp))['approval']
        plain, html = approval['description']['generated_parts']
        self.assertEqual(plain['text'], visible('Plain unsent words\r\n'))
        self.assertEqual(html['text'], visible('Entire different HTML link (https://link.invalid/path)'))
        self.assertEqual(self.server_state([ref['folder']]), before)

    def test_review6_flag_is_fresh_after_another_client_changes_it_without_read_side_effects(self):
        ref = self.fixture(text='Fresh server flag, complete unsent words', flags='(keep)')
        self.assertNotIn('\\Draft', self.data('read', {'reference':ref})['flags'])
        self.assertTrue(self.call('compose', {'account':'box', 'attachments':[{'reference':ref, 'part':'source'}]})['ok'])
        # Another mail program marks this same UID as a draft after the read.
        with self.mail.transport.imap(self.account) as conn:
            select(conn, ref['folder'], readonly=False)
            ok(conn.uid('STORE', str(ref['uid']), '+FLAGS.SILENT', '(\\Draft)'), 'fixture draft flag')
        before = self.server_state([ref['folder']])
        self.assert_attachment_refused(ref)
        for mode in ('draft', 'reply', 'reply_all', 'forward'):
            comp = self.data('compose', {'account':'box', 'mode':mode, 'reference':ref, **({'to':['one@mail.invalid']} if mode == 'forward' else {})})
            approval = self.data('prepare_send', self.keys(comp))['approval']
            self.assertIn('Fresh server flag, complete unsent words', canonical(approval))
            self.assertIn('text', approval['description']['generated_parts'][0])
        self.data('read', {'reference':ref})
        self.assertEqual(self.server_state([ref['folder']]), before)

    def test_review6_flagged_sources_still_validate_uidvalidity_identity_and_existence(self):
        ref = self.fixture(flags='(\\Draft)')
        stale_refs = [{**ref, 'uidvalidity':ref['uidvalidity'] + 1},
                      {**ref, 'message_id':'<changed@mail.invalid>'}]
        before = self.server_state(['INBOX'])
        for index in range(3):
            if index == 2:
                with self.mail.transport.imap(self.account) as conn:
                    select(conn, ref['folder'], readonly=False)
                    ok(conn.uid('STORE', str(ref['uid']), '+FLAGS.SILENT', '(\\Deleted)'), 'fixture delete')
                    ok(conn.uid('EXPUNGE', str(ref['uid'])), 'fixture exact expunge')
                stale_refs.append(ref)
                replacement = self.fixture(flags='(\\Draft)')
                before = self.server_state(['INBOX'])
            stale = stale_refs[index]
            for args in ({'attachments':[{'reference':stale, 'part':'source'}]},
                         {'mode':'forward', 'reference':stale, 'forward_as':'attachment'},
                         {'mode':'draft', 'reference':stale}):
                result = self.call('compose', {'account':'box', **args})
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error']['code'], 'stale_reference')
        self.assertEqual(self.server_state(['INBOX']), before)
        self.assertIn('\\Draft', self.mail.message(replacement)['flags'])

    def test_review6_ordinary_move_copy_into_drafts_allowed_and_named_delete_still_works(self):
        drafts = self.account['special']['drafts']
        for verb in ('move', 'copy'):
            ref = self.fixture(text='Ordinary incoming mail', flags='(keep)')
            original = self.mail.message(ref)
            changed = self.data(verb, {'references':[ref], 'target':drafts})['items'][0]
            current = self.mail.message(changed)
            self.assertEqual(current['raw'], original['raw'])
            self.assertEqual(current['flags'], original['flags'])
            self.assert_attachment_refused(changed)
            if verb == 'copy':
                self.assertEqual(self.mail.message(ref)['raw'], original['raw'])
            else:
                self.assertFalse(self.call('read', {'reference':ref})['ok'])
        for flags in (None, '(\\Draft)'):
            ref = self.fixture(drafts, sender=self.owner, text='Named unsent draft to delete', flags=flags)
            before = self.mail.message(ref)
            approval = self.delete_approval([ref])
            self.assertEqual(self.mail.message(ref)['raw'], before['raw'])
            self.assertEqual(self.data('delete', approval)['operation']['state'], 'done')
            self.assertFalse(self.call('read', {'reference':ref})['ok'])
            messages, _ = self.mail.snapshot('box', [self.account['special']['trash']])
            self.assertTrue(any(m['raw'] == before['raw'] and m['flags'] == before['flags'] for m in messages))

    def test_review6_mail_flag_cannot_add_or_remove_draft_even_in_mixed_flags(self):
        for folder in ('INBOX', self.account['special']['archive']):
            for flags in ('(keep)', '(\\Draft keep)'):
                ref = self.fixture(folder, flags=flags)
                for key in ('add', 'remove'):
                    before = self.server_state([folder])
                    args = {'references':[ref], 'add':['\\Seen'], 'remove':['keep']}
                    args[key].append('\\Draft')
                    result = self.call('flag', args)
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'invalid_input')
                    self.assertIn('Draft forbidden', result['error']['message'])
                    self.assertEqual(self.server_state([folder]), before)
