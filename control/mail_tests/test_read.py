from email.message import EmailMessage
from unittest.mock import patch

from support import MailCase
from aresos_control.mail import codec
from aresos_control.mail.transport import quote, ok, select, uids


class Reading(MailCase):
    def test_every_read_action_preserves_flags(self):
        ref = self.fixture(attachments=[('invoice.pdf', b'%PDF-synthetic', 'application/pdf')])
        self.fixture(self.account['special']['archive'], headers={'In-Reply-To':ref['message_id']})
        approval = self.approval()
        before = self.all_flags()
        for verb, args in [('accounts', {}), ('folders', {'account':'box'}), ('search', {'account':'box'}),
                           ('read', {'reference':ref}), ('read', {'reference':ref, 'part':'source'}),
                           ('read', {'reference':ref, 'part':'1.1'}), ('thread', {'reference':ref}),
                           ('contacts', {'account':'box', 'text':'alice'}),
                           ('operation_status', {'operation_id':approval['operation_id']})]:
            with self.subTest(action=verb, args=args):
                self.data(verb, args)
                self.assertEqual(before, self.all_flags())

    def test_filters_and_large_folder_cursors_bind_full_state_and_query(self):
        for i in range(24):
            self.fixture(subject=f'Invoice {i}', flags='(\\Flagged)' if i == 3 else None,
                         attachments=[('invoice.pdf', b'bytes', 'application/pdf')] if i == 3 else [])
        self.fixture(self.account['special']['trash'], subject='Invoice hidden')
        page = self.data('search', {'account':'box', 'subject':'Invoice', 'limit':7})
        self.assertEqual(page['total'], 24)
        found = list(page['items'])
        while page['cursor']:
            page = self.data('search', {'account':'box', 'subject':'Invoice', 'limit':7, 'cursor':page['cursor']})
            found += page['items']
        self.assertEqual(len(found), 24)
        self.assertEqual(len({i['reference']['uid'] for i in found}), 24)
        args = {'account':'box', 'from':'alice', 'to':self.owner, 'text':'fixture', 'since':'2026-11-01', 'before':'2026-12-01', 'unread':True, 'flagged':True, 'answered':False, 'has_attachment':True}
        self.assertEqual(self.data('search', args)['total'], 1)
        first = self.data('search', {'account':'box'})
        self.assertFalse(self.call('search', {'account':'box', 'subject':'other', 'cursor':first['cursor']})['ok'])
        ref = first['items'][0]['reference']
        self.data('flag', {'references':[ref], 'add':['\\Seen'], 'remove':[]})
        self.assertFalse(self.call('search', {'account':'box', 'cursor':first['cursor']})['ok'])
        self.fixture(subject='new arrival')
        self.assertFalse(self.call('search', {'account':'box', 'cursor':first['cursor']})['ok'])

    def test_html_plain_non_utf8_calendar_and_nested_forward_fixtures(self):
        msg = EmailMessage()
        msg['From'] = self.peer
        msg['To'] = self.owner
        msg['Subject'] = 'HTML fixture'
        msg.set_content('<p>Hello <b>café</b><a href="https://remote.invalid/path">link</a><img src="https://remote.invalid/pixel" alt="diagram"></p><script>evil()</script>', subtype='html')
        ref = self.fixture(msg=msg)
        with patch('http.client.HTTPSConnection', side_effect=AssertionError('Remote fetch')):
            text = self.data('read', {'reference':ref})['untrusted_content']['text']
        self.assertIn('link (https://remote.invalid/path)', text)
        self.assertNotIn('evil()', text)
        legacy = EmailMessage()
        legacy['From'] = self.peer
        legacy['To'] = self.owner
        legacy.set_content('Grüße', charset='iso-8859-1')
        ref = self.fixture(msg=legacy)
        self.assertIn('Grüße', self.data('read', {'reference':ref})['untrusted_content']['text'])
        nested = EmailMessage()
        nested['From'] = self.peer
        nested['To'] = self.owner
        nested.set_content('Outer')
        nested.add_attachment(legacy)
        ref = self.fixture(msg=nested)
        read = self.data('read', {'reference':ref})
        self.assertEqual(read['untrusted_content']['attachments'][0]['type'], 'message/rfc822')
        self.assertIn('Grüße', self.data('read', {'reference':ref, 'part':'1.2.1'})['untrusted_content']['text'])
        ref = self.fixture(attachments=[('invite.ics', b'BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n', 'text/calendar')])
        self.assertEqual(self.data('read', {'reference':ref})['untrusted_content']['attachments'][0]['type'], 'text/calendar')

    def test_long_body_source_and_parts_are_paged_and_state_bound(self):
        text = 'line café\n' * 4000
        ref = self.fixture(text=text)
        result = self.data('read', {'reference':ref})
        joined = result['untrusted_content']['text']
        while result['next_offset'] is not None:
            result = self.data('read', {'reference':ref, 'offset':result['next_offset'], 'cursor':result['cursor']})
            joined += result['untrusted_content']['text']
        self.assertEqual(joined.replace('\r\n','\n'), text)
        self.assertFalse(self.call('read', {'reference':ref, 'offset':1})['ok'])
        first = self.data('read', {'reference':ref})
        self.data('flag', {'references':[ref], 'add':['\\Flagged'], 'remove':[]})
        self.assertFalse(self.call('read', {'reference':ref, 'offset':first['next_offset'], 'cursor':first['cursor']})['ok'])
        source = self.data('read', {'reference':ref, 'part':'source'})
        self.assertIn('From:', source['untrusted_content']['text'])
        self.assertIsNotNone(source['cursor'])

    def test_thread_across_folders_missing_duplicate_ids_no_subject_guess(self):
        root = self.fixture(mid='<thread-root@mail.invalid>')
        second = self.fixture(self.account['special']['archive'], headers={'In-Reply-To':root['message_id']})
        duplicate = self.fixture(mid=second['message_id'], subject='Duplicate')
        self.fixture(subject='Same subject but unrelated')
        self.fixture(self.account['special']['trash'], headers={'In-Reply-To':root['message_id']})
        thread = self.data('thread', {'reference':root})
        self.assertEqual(thread['total'], 3)
        self.assertEqual(sum(x['duplicate_message_id'] for x in thread['items']), 2)
        missing = self.fixture(mid='missing')
        isolated = self.data('thread', {'reference':missing})
        self.assertEqual(isolated['total'], 1)
        self.assertIsNotNone(isolated['items'][0]['internal_thread_id'])
        comp = self.data('compose', {'account':'box', 'mode':'reply', 'reference':missing, 'text':'Reply'})
        self.assertEqual(comp['mail']['in_reply_to'], '')

    def test_stale_uidvalidity_after_folder_recreated_never_hits_replacement(self):
        self.data('folder_create', {'account':'box', 'name':'Disposable'})
        ref = self.fixture('Disposable')
        with self.mail.transport.imap(self.account) as conn:
            select(conn, 'Disposable', readonly=False)
            ok(conn.uid('STORE', str(ref['uid']), '+FLAGS.SILENT', '(\\Deleted)'), 'fixture mark')
            ok(conn.uid('EXPUNGE', str(ref['uid'])), 'fixture expunge')
            conn.unselect()
            ok(conn.delete(quote('Disposable')), 'fixture delete')
            ok(conn.create(quote('Disposable')), 'fixture recreate')
        replacement = self.fixture('Disposable', subject='Must survive')
        self.assertNotEqual(ref['uidvalidity'], replacement['uidvalidity'])
        for verb, args in [('read', {'reference':ref}), ('thread', {'reference':ref}),
                           ('flag', {'references':[ref], 'add':['\\Seen'], 'remove':[]}),
                           ('copy', {'references':[ref], 'target':self.account['special']['archive']}),
                           ('compose', {'account':'box', 'mode':'reply', 'reference':ref, 'text':'Reply'})]:
            result = self.call(verb, args)
            self.assertFalse(result['ok'], result)
            self.assertEqual(result['error']['code'], 'stale_reference')
        self.assertEqual(self.data('read', {'reference':replacement})['untrusted_content']['headers']['Subject'], 'Must survive')

    def test_multiple_accounts_contacts_and_special_use_names(self):
        other = self.add_account('other')
        self.fixture(sender=self.owner, to='Bob <bob@mail.invalid>')
        self.fixture(sender='Alice <alice@mail.invalid>')
        contacts = self.data('contacts', {'account':'box'})['items']
        self.assertEqual({i['untrusted_content']['address'] for i in contacts}, {'alice@mail.invalid', 'bob@mail.invalid'})
        self.assertEqual(self.data('contacts', {'account':'box', 'text':'bob'})['total'], 1)
        self.assertEqual(self.data('search', {'account':'other'})['total'], 0)
        accounts = self.data('accounts')['accounts']
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0]['special']['sent'], 'Posta')
        self.assertNotIn('username', accounts[0])
        self.assertNotIn('ca_file', accounts[0])
        counts = self.data('folders', {'account':'box', 'limit':20})
        self.assertEqual(next(f for f in counts['items'] if f['name'] == 'INBOX')['unread'], 2)
