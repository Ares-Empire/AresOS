"""Optional SPECIAL-USE roles over real Dovecot storage and a non-relaying SMTP sink."""
import unittest
import uuid
from unittest.mock import patch

from support import MailCase, CERT
from smtp_fixture import SMTPFixture
import test_review_fixes_7 as round7
import test_admin
from aresos_control.common import Refused
from aresos_control.mail.roles import resolve, check_optional, optional_status, recorded_optional
from aresos_control.mail.transport import context, folders, quote, ok


class RoleResolution8(unittest.TestCase):
    def listing(self):
        return [{'name': name, 'delimiter': '/', 'flags': ['\\' + role] if role else []}
                for name, role in [('INBOX', ''), ('Posta', 'Sent'), ('Bozze', 'Drafts'), ('Cestino', 'Trash')]]

    def test_review8_optional_absence_duplicates_and_unselectable_do_not_hide_required_errors(self):
        listed = self.listing()
        absent = resolve(listed)
        self.assertIsNone(absent['special']['junk'])
        self.assertIsNone(absent['special']['archive'])
        duplicate = listed + [{'name': name, 'delimiter': '/', 'flags': ['\\Archive']} for name in ('A', 'B')]
        self.assertEqual(len(resolve(duplicate)['optional']['archive']), 2)
        unselectable = listed + [{'name': 'A', 'delimiter': '/', 'flags': ['\\Archive', '\\NOSELECT']}]
        self.assertEqual(optional_status(absent['optional'], resolve(unselectable)['optional'])['archive']['status'], 'needs_setup')
        for role in ('Sent', 'Drafts', 'Trash'):
            for invalid in ([f for f in listed if '\\' + role not in f['flags']],
                            listed + [{'name': 'Other', 'delimiter': '/', 'flags': ['\\' + role]}],
                            [dict(f, flags=f['flags'] + ['\\Noselect']) if '\\' + role in f['flags'] else f for f in listed]):
                with self.subTest(role=role), self.assertRaisesRegex(Refused, 'account_folders'):
                    resolve(invalid)

    def test_review8_legacy_recorded_roots_scope_changes_and_missing_role_reason(self):
        account = {'special': {'archive': 'Old'}, 'delimiter': '/'}
        current = resolve(self.listing() + [{'name': 'New', 'delimiter': '/', 'flags': ['\\Archive']}])['optional']
        self.assertEqual(recorded_optional(account)['archive'][0]['folder'], 'Old')
        for name in ('Old', 'Old/Child', 'New', 'New/Child'):
            with self.subTest(name=name), self.assertRaisesRegex(Refused, 'Archive.*account_folders'):
                check_optional(account, current, [name])
        for name in ('INBOX', 'Ordinary', 'Oldish', 'Newish'):
            check_optional(account, current, [name])
        absent = resolve(self.listing())
        for role in ('junk', 'archive'):
            with self.assertRaisesRegex(Refused, role.title() + '.*mail server.*settings.*account_folders'):
                check_optional(absent, absent['optional'], needed=[role])


class ReviewFixes8(MailCase):
    # Reuse the same runner-controlled real LIST changes and byte/UID/flag snapshots.
    configure_roles = round7.ReviewFixes7.configure_roles
    switch_roles = round7.ReviewFixes7.switch_roles
    record_roles = round7.ReviewFixes7.record_roles
    server_state = round7.ReviewFixes7.server_state
    tearDown = round7.ReviewFixes7.tearDown
    keys = round7.ReviewFixes7.keys

    def statuses(self):
        accounts = self.data('accounts')['accounts']
        return next(a for a in accounts if a['id'] == self.account['id'])['optional_roles']

    def ordinary_actions(self):
        account_id = self.account['id']
        for name in ('OrdinaryA', 'OrdinaryB'):
            self.data('folder_create', {'account': account_id, 'name': name})
        self.data('folder_rename', {'account': account_id, 'folder': 'OrdinaryB', 'name': 'OrdinaryC'})
        ref = self.fixture(text='Ordinary received body')
        copy = self.data('copy', {'references': [ref], 'target': 'OrdinaryA'})['items'][0]
        moved = self.data('move', {'references': [copy], 'target': 'OrdinaryC'})['items'][0]
        self.assertFalse(self.call('read', {'reference': copy})['ok'])
        self.assertEqual(self.mail.message(moved)['raw'], self.mail.message(ref)['raw'])
        self.data('flag', {'references': [moved], 'add': ['\\Flagged'], 'remove': []})
        trashed = self.data('delete', self.delete_approval([moved]))['operation']
        self.assertEqual(trashed['state'], 'done', trashed)
        trash = self.data('search', {'account': account_id, 'folders': [self.account['special']['trash']]})['items']
        self.assertEqual(len(trash), 1)
        permanent = self.data('delete', self.delete_approval([trash[0]['reference']], 'permanent'))['operation']
        self.assertEqual(permanent['state'], 'done', permanent)
        self.assertEqual(self.data('search', {'account': account_id, 'folders': [self.account['special']['trash']]})['total'], 0)
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:' + account_id: self.account}, 'fixture', 'isolated optional-role SMTP sink')
            reply = self.data('compose', {'account': account_id, 'mode': 'reply', 'reference': ref, 'text': 'Approved reply'})
            approval = self.data('prepare_send', self.keys(reply))['approval']
            sent = self.send(approval)
            self.assertEqual(sent['state'], 'done', sent)
            self.assertEqual(sent['stages']['smtp_data'], 'accepted:250')
            self.assertEqual(sent['stages']['sent_copy'], 'done')
            self.assertEqual(sent['stages']['answered_flag'], 'done')
            self.assertIn('\\Answered', self.mail.message(ref)['flags'])
            self.assertEqual(len(self.mail.sent_matches(self.account, self.mail.message_id(sent['id']))), 1)
            draft_comp = self.compose(text='Whole optional-role draft body')
            draft = self.data('draft_save', self.keys(draft_comp))['reference']
            self.assertIn('\\Draft', self.mail.message(draft)['flags'])
            resumed = self.data('compose', {'account': account_id, 'mode': 'draft', 'reference': draft})
            approval = self.data('prepare_send', self.keys(resumed))['approval']
            self.assertIn('Whole optional-role draft body', str(approval))
            sent_draft = self.send(approval)
            self.assertEqual(sent_draft['state'], 'done', sent_draft)
            self.assertEqual(len(self.mail.sent_matches(self.account, self.mail.message_id(sent_draft['id']))), 1)
            self.assertEqual(len(smtp.arrivals()), 2)
            self.send(approval)
            self.assertEqual(len(smtp.arrivals()), 2)
            self.assertEqual(self.mail.message(draft)['reference'], draft)

    def refused(self, verb, args, role):
        result = self.call(verb, args)
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'special_folders_changed', result)
        self.assertIn(role.title(), result['error']['message'])
        self.assertIn('account_folders', result['error']['message'])

    def onboard_optional(self):
        args = test_admin.AccountAdmin.account_args(self, 'optional-' + uuid.uuid4().hex)
        original = context
        with patch('aresos_control.mail.transport.context', side_effect=lambda a: original({**a, 'ca_file': str(CERT / 'tls.crt')})):
            result = self.engine.request({'v': 1, 'method': 'mail_account_add', 'arguments': args, 'password': 'pass'}, admin=True)
        self.assertTrue(result['ok'], result)
        self.assertTrue(self.mail.account(args['id'], ready=False)['onboarded'])
        self.data('account_settings', {'id': args['id'], 'sent_policy': 'client'}, admin=True)
        self.account = self.mail.account(args['id'])
        self.account['ca_file'] = str(CERT / 'tls.crt')
        self.engine.store.write({'mail:account:' + args['id']: self.account}, 'fixture', 'trust isolated fixture certificate')
        self.owner = self.account['addresses'][0]

    def test_review8_duplicate_optional_role_onboards_without_disabling_other_actions(self):
        self.switch_roles('duplicate_archive')
        self.onboard_optional()
        self.assertEqual(self.statuses()['archive']['status'], 'needs_setup')
        ref = self.fixture()
        self.refused('move', {'references': [ref], 'target': 'DuplicateArchive'}, 'archive')
        self.ordinary_actions()

    def test_review8_no_optional_roles_onboard_and_all_ordinary_mail_actions_work(self):
        self.switch_roles('no_optional')
        self.onboard_optional()
        args = {'id': self.account['id']}
        for role, status in self.statuses().items():
            self.assertEqual(status['status'], 'absent', role)
            self.assertIsNone(self.account['special'][role])
        proposal = self.data('account_folders', {'id': args['id']}, admin=True)
        recorded = self.data('account_folders', {'id': args['id'], 'roles_hash': proposal['roles_hash']}, admin=True)
        self.assertTrue(recorded['recorded'])
        for role in ('junk', 'archive'):
            self.assertIsNone(recorded['untrusted_content']['special'][role])
        ref = self.fixture()
        before = self.server_state(['INBOX', 'Indesiderata', 'Archivio'])
        for verb in ('move', 'copy'):
            for role in ('junk', 'archive'):
                result = self.call(verb, {'references': [ref], 'target_role': role})
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error']['code'], 'special_folder_missing')
                for text in (role.title(), 'mark that folder', 'mail server', 'settings', 'account_folders'):
                    self.assertIn(text, result['error']['message'])
        self.assertEqual(self.server_state(['INBOX', 'Indesiderata', 'Archivio']), before)
        self.ordinary_actions()

    def affected_archive(self, mode):
        old = self.fixture('Archivio', text='Recorded Archive source')
        ordinary = self.fixture(text='Ordinary source must stay put')
        deletion = self.delete_approval([old])
        reply = self.data('compose', {'account': 'box', 'mode': 'reply', 'reference': old, 'text': 'Approved reply'})
        send = self.data('prepare_send', self.keys(reply))['approval']
        attached = self.compose(attachments=[{'reference': old, 'part': 'source'}])
        forward = self.data('compose', {'account': 'box', 'mode': 'forward', 'reference': old, 'text': 'Approved forward', 'to': ['one@mail.invalid']})
        self.switch_roles(mode)
        other = 'DuplicateArchive' if mode == 'duplicate_archive' else 'NewArchive'
        new = self.fixture(other, text='Current Archive source')
        names = ['INBOX', 'Archivio', other]
        before = self.server_state(names)
        self.assertEqual(self.statuses()['archive']['status'], 'needs_setup')
        for ref in (old, new):
            for verb in ('move', 'copy'):
                self.refused(verb, {'references': [ref], 'target': 'INBOX'}, 'archive')
                self.refused(verb, {'references': [ordinary], 'target': ref['folder']}, 'archive')
                self.refused(verb, {'references': [ordinary, ref], 'target': 'INBOX'}, 'archive')
            self.refused('flag', {'references': [ref], 'add': ['\\Seen'], 'remove': []}, 'archive')
            self.refused('attachment_save', {'reference': ref, 'part': '1'}, 'archive')
            self.refused('compose', {'account': 'box', 'mode': 'reply', 'reference': ref}, 'archive')
            for delete_mode in ('trash', 'permanent'):
                self.refused('prepare_delete', {'items': [self.mail.named_item(ref)], 'mode': delete_mode}, 'archive')
            self.refused('folder_rename', {'account': 'box', 'folder': ref['folder'], 'name': 'NeverRenamed'}, 'archive')
            self.refused('folder_create', {'account': 'box', 'name': ref['folder'] + '/Child'}, 'archive')
            self.assertTrue(self.call('read', {'reference': ref})['ok'])
        self.refused('delete', deletion, 'archive')
        with patch('smtplib.SMTP_SSL.data', side_effect=AssertionError('DATA forbidden')) as data:
            self.refused('send', send, 'archive')
            data.assert_not_called()
        for comp in (reply, attached, forward):
            self.refused('prepare_send', self.keys(comp), 'archive')
            self.refused('draft_save', self.keys(comp), 'archive')
        self.assertEqual(self.engine.operation(send['operation_id'])['state'], 'reserved')
        self.assertEqual(self.server_state(names), before)
        # Also prove the second check at the actual UID command boundary.
        self.configure_roles('default')
        original = self.mail.message
        switched = False
        def change_after_reference_check(ref, writable=False, client=None):
            nonlocal switched
            result = original(ref, writable, client)
            if not switched:
                switched = True
                self.configure_roles(mode)
            return result
        with patch.object(self.mail, 'message', side_effect=change_after_reference_check):
            self.refused('move', {'references': [ordinary], 'target': other}, 'archive')
        self.assertTrue(switched)
        self.assertEqual(self.server_state(names), before)
        self.ordinary_actions()

    def test_review8_duplicate_archive_refuses_only_affected_changes_and_allows_ordinary_actions(self):
        self.affected_archive('duplicate_archive')
        self.record_roles()
        self.assertEqual(self.statuses()['archive']['status'], 'needs_setup')
        ref = self.fixture()
        self.refused('move', {'references': [ref], 'target_role': 'archive'}, 'archive')

    def test_review8_moved_archive_refuses_old_and_new_until_owner_records_then_role_move_works(self):
        self.affected_archive('archive')
        self.record_roles()
        self.assertEqual(self.statuses()['archive']['status'], 'present')
        ref = self.fixture()
        moved = self.data('move', {'references': [ref], 'target_role': 'archive'})['items'][0]
        self.assertEqual(moved['folder'], 'NewArchive')
        moved = self.data('move', {'references': [moved], 'target': 'Archivio'})['items'][0]
        self.assertEqual(moved['folder'], 'Archivio')

    def test_review8_optional_appearance_disappearance_needs_setup_only_for_affected_folder(self):
        old = self.fixture('Archivio')
        ordinary = self.fixture()
        self.switch_roles('missing_archive')
        self.assertEqual(self.statuses()['archive']['status'], 'needs_setup')
        self.refused('move', {'references': [old], 'target': 'INBOX'}, 'archive')
        self.data('flag', {'references': [ordinary], 'add': ['\\Flagged'], 'remove': []})
        self.record_roles()
        self.assertEqual(self.statuses()['archive']['status'], 'absent')
        self.configure_roles('default')
        self.assertEqual(self.statuses()['archive']['status'], 'needs_setup')
        self.refused('copy', {'references': [ordinary], 'target': 'Archivio'}, 'archive')
        self.refused('move', {'references': [old], 'target': 'INBOX'}, 'archive')
        self.data('flag', {'references': [ordinary], 'add': [], 'remove': ['\\Flagged']})
        self.record_roles()
        self.assertEqual(self.statuses()['archive']['status'], 'present')
        moved = self.data('move', {'references': [ordinary], 'target_role': 'archive'})['items'][0]
        self.assertEqual(moved['folder'], 'Archivio')

    def test_review8_junk_reads_defaults_exclude_all_current_and_recorded_roots_without_refusing(self):
        for mode in ('junk', 'duplicate_junk', 'missing_junk'):
            with self.subTest(mode=mode):
                self.configure_roles('default')
                self.account = self.add_account('box')
                self.owner = self.account['addresses'][0]
                seed = self.fixture(mid='<optional-thread@mail.invalid>')
                old = self.fixture('Indesiderata', sender='old-junk@mail.invalid', headers={'In-Reply-To': seed['message_id']})
                listed = self.switch_roles(mode)
                roots = [f['name'] for f in listed if '\\Junk' in f['flags']]
                refs = [old] + [self.fixture(name, sender='current-junk@mail.invalid', headers={'In-Reply-To': seed['message_id']})
                                for name in roots if name != old['folder']]
                # Descendants of the old root stay excluded even after its flag moves.
                with self.mail.transport.imap(self.account) as conn:
                    if 'Indesiderata/Child' not in [f['name'] for f in folders(conn)]:
                        ok(conn.create(quote('Indesiderata/Child')), 'fixture Junk descendant')
                refs.append(self.fixture('Indesiderata/Child', headers={'In-Reply-To': seed['message_id']}))
                names = sorted(set(['INBOX', 'Indesiderata', 'Indesiderata/Child'] + roots))
                before = self.server_state(names)
                self.assertEqual(self.statuses()['junk']['status'], 'needs_setup')
                for verb, args in [('search', {'account': 'box'}), ('thread', {'reference': seed})]:
                    result = self.data(verb, args)
                    self.assertEqual([item['reference'] for item in result['items']], [seed])
                for ref in refs:
                    self.assertTrue(self.call('read', {'reference': ref})['ok'])
                    self.assertEqual(self.data('thread', {'reference': ref})['total'], 0)
                    self.refused('flag', {'references': [ref], 'add': ['\\Seen'], 'remove': []}, 'junk')
                    self.refused('move', {'references': [seed], 'target': ref['folder']}, 'junk')
                explicit = self.data('search', {'account': 'box', 'folders': ['Indesiderata']})
                self.assertEqual(explicit['items'][0]['reference'], old)
                self.data('folders', {'account': 'box'})
                contacts = str(self.data('contacts', {'account': 'box'}))
                self.assertNotIn('old-junk@mail.invalid', contacts)
                self.assertNotIn('current-junk@mail.invalid', contacts)
                self.assertEqual(self.server_state(names), before)
        self.ordinary_actions()

    def test_review8_each_missing_duplicate_required_role_still_blocks_setup_and_changes(self):
        ref = self.fixture()
        comp = self.compose()
        approval = self.data('prepare_send', self.keys(comp))['approval']
        before = self.server_state(['INBOX'])
        for mode in ('missing', 'ambiguous', 'missing_sent', 'duplicate_sent', 'missing_drafts', 'duplicate_drafts'):
            with self.subTest(mode=mode):
                self.switch_roles(mode)
                for verb, args in [('compose', {'account': 'box', 'text': 'Blocked'}),
                                   ('draft_save', self.keys(comp)), ('send', approval),
                                   ('move', {'references': [ref], 'target': 'Archivio'}),
                                   ('flag', {'references': [ref], 'add': ['\\Seen'], 'remove': []}),
                                   ('prepare_delete', {'items': [self.mail.named_item(ref)], 'mode': 'trash'})]:
                    result = self.call(verb, args)
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'special_folders_changed')
                    self.assertIn('account_folders', result['error']['message'])
                self.assertFalse(self.call('account_folders', {'id': 'box'}, admin=True)['ok'])
                args = test_admin.AccountAdmin.account_args(self, 'required-' + uuid.uuid4().hex)
                original = context
                with patch('aresos_control.mail.transport.context', side_effect=lambda a: original({**a, 'ca_file': str(CERT / 'tls.crt')})):
                    result = self.engine.request({'v': 1, 'method': 'mail_account_add', 'arguments': args, 'password': 'pass'}, admin=True)
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error']['code'], 'unsupported_server')
                self.assertIn('account_folders', result['error']['message'])
                self.assertFalse(self.mail.account(args['id'], ready=False)['ready'])
                self.assertEqual(self.server_state(['INBOX']), before)
        self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
