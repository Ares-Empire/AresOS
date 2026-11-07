from copy import deepcopy
from unittest.mock import patch

from support import MailCase
from aresos_control.common import ASK_LIMIT, canonical
from aresos_control.mail.transport import folders, quote, select, uids, ok


class Changes(MailCase):
    def test_move_copy_flags_junk_folder_create_rename(self):
        self.data('folder_create', {'account':'box','name':'Invoices'})
        ref = self.fixture()
        copied = self.data('copy', {'references':[ref],'target':'Invoices'})['items'][0]
        self.assertEqual(self.mail.message(copied)['msg']['Subject'], self.mail.message(ref)['msg']['Subject'])
        self.data('folder_rename', {'account':'box','folder':'Invoices','name':'Invoices-2026'})
        self.assertFalse(self.call('read',{'reference':copied})['ok'])
        moved = self.data('move', {'references':[ref],'target':self.account['special']['junk']})['items'][0]
        self.assertFalse(self.call('read',{'reference':ref})['ok'])
        moved = self.data('move', {'references':[moved],'target':'INBOX'})['items'][0]
        flag = self.data('flag', {'references':[moved],'add':['\\Seen','\\Flagged','\\Answered','project'],'remove':[]})
        self.assertTrue({'\\Seen','\\Flagged','\\Answered','project'} <= set(flag['items'][0]['flags']))
        flag = self.data('flag', {'references':[moved],'add':[],'remove':['\\Seen','project']})
        self.assertNotIn('\\Seen',flag['items'][0]['flags'])
        self.assertNotIn('project',flag['items'][0]['flags'])
        for forbidden in ('\\Deleted','\\Recent','\\Draft','bad flag','x)\\Deleted'):
            self.assertFalse(self.call('flag',{'references':[moved],'add':[forbidden],'remove':[]})['ok'])
        for verb in ('move','copy'):
            self.assertEqual(self.call(verb, {'references':[moved],'target':self.account['special']['trash']})['error']['code'],'refused')
        self.assertFalse(self.call('folder_rename',{'account':'box','folder':self.account['special']['junk'],'name':'X'})['ok'])
        self.data('folder_create',{'account':'box','name':'Parent'})
        self.data('folder_create',{'account':'box','name':'Parent/Child'})
        self.assertFalse(self.call('folder_rename',{'account':'box','folder':'Parent','name':'Moved'})['ok'])

    def test_trash_and_permanent_only_named_uids_others_deleted_survive(self):
        innocent = self.fixture(subject='Someone else marked me deleted', flags='(\\Deleted)')
        target = self.fixture(subject='Named target')
        approval = self.delete_approval([target])
        self.assertEqual(self.data('delete',approval)['operation']['state'],'done')
        self.assertEqual(self.data('delete',approval)['operation']['state'],'done')
        self.assertIn('\\Deleted',self.mail.message(innocent)['flags'])
        trash = self.data('search',{'account':'box','folders':[self.account['special']['trash']]})['items']
        self.assertEqual(len(trash),1)
        permanent = self.delete_approval([trash[0]['reference']],'permanent')
        self.assertEqual(self.data('delete',permanent)['operation']['state'],'done')
        self.assertIn('\\Deleted',self.mail.message(innocent)['flags'])
        self.assertFalse(self.call('read',{'reference':trash[0]['reference']})['ok'])

    def test_delete_without_uidplus_refused_and_all_items_checked_before_any(self):
        first, second = self.fixture(subject='First'), self.fixture(subject='Second')
        account = {**self.account,'capabilities':[c for c in self.account['capabilities'] if c != 'UIDPLUS']}
        self.engine.store.write({'mail:account:box':account},'fixture','remove capability')
        result = self.call('prepare_delete',{'items':[self.mail.named_item(first)],'mode':'permanent'})
        self.assertEqual(result['error']['code'],'unsupported_server')
        self.engine.store.write({'mail:account:box':self.account},'fixture','restore capability')
        approval = self.delete_approval([first,second],'permanent')
        # Another client expunges the second before approval. The first must survive.
        with self.mail.transport.imap(self.account) as conn:
            select(conn,'INBOX',readonly=False)
            ok(conn.uid('STORE',str(second['uid']),'+FLAGS.SILENT','(\\Deleted)'),'fixture mark')
            ok(conn.uid('EXPUNGE',str(second['uid'])),'fixture expunge')
        self.assertFalse(self.call('delete',approval)['ok'])
        self.assertEqual(self.mail.message(first)['reference'],first)

    def test_delete_prompt_metadata_escaped_bounded_and_cannot_be_forged(self):
        ref = self.fixture(subject='Direction \u202e café', sender='Odd <odd@mail.invalid>')
        items = [self.mail.named_item(ref)]
        forged = deepcopy(items)
        forged[0]['subject'] = 'Made up'
        self.assertEqual(self.call('prepare_delete',{'items':forged,'mode':'trash'})['error']['code'],'stale_approval')
        approval = self.delete_approval([ref])
        self.assertIn('\\u202e',approval['description']['items'][0]['subject'])
        self.assertLessEqual(len(canonical(approval).encode()),ASK_LIMIT)
        altered = deepcopy(approval)
        altered['description']['items'][0]['from'] = 'forged@mail.invalid'
        self.assertEqual(self.call('delete',altered)['error']['code'],'stale_approval')
        huge = self.fixture(subject='x' * 18000)
        result = self.call('prepare_delete', {'items':[self.mail.named_item(huge)],'mode':'trash'})
        self.assertEqual(result['error']['code'],'asking_input_too_large')

    def test_greenmail_nonempty_guard_and_delivery_during_folder_approval(self):
        green = self.add_account('green','greenmail')
        previous = self.account
        self.account = green
        try:
            self.data('folder_create',{'account':'green','name':'SafeLeaf'})
            ref = self.fixture('SafeLeaf')
            # Actual server guard qualification, not a mock: nonempty refused, empty allowed.
            with self.mail.transport.imap(green) as conn:
                self.assertEqual(conn.delete(quote('SafeLeaf'))[0],'NO')
            green['safe_folder_delete'] = True
            self.engine.store.write({'mail:account:green':green},'fixture','actual nonempty guard observed')
            self.data('delete',self.delete_approval([ref],'permanent'))
            approval = self.data('prepare_folder_delete',{'account':'green','folder':'SafeLeaf'})['approval']
            newcomer = self.fixture('SafeLeaf',subject='Arrived while owner considered approval')
            self.assertFalse(self.call('folder_delete',approval)['ok'])
            self.assertEqual(self.mail.message(newcomer)['reference'],newcomer)
            self.data('delete',self.delete_approval([newcomer],'permanent'))
            approval = self.data('prepare_folder_delete',{'account':'green','folder':'SafeLeaf'})['approval']
            # Delivery after revalidation, immediately before DELETE: real server refuses atomically.
            original = self.mail.revalidate
            checks = 0
            def deliver(op):
                nonlocal checks
                original(op)
                checks += 1
                if checks == 2:
                    self.fixture('SafeLeaf',subject='Concurrent final-boundary arrival')
            with patch.object(self.mail,'revalidate',side_effect=deliver):
                result = self.data('folder_delete',approval)['operation']
            self.assertEqual(result['state'],'refused',result)
            refs = self.data('search',{'account':'green','folders':['SafeLeaf']})['items']
            self.assertEqual(len(refs),1)
            self.data('delete',self.delete_approval([refs[0]['reference']],'permanent'))
            approval = self.data('prepare_folder_delete',{'account':'green','folder':'SafeLeaf'})['approval']
            self.assertEqual(self.data('folder_delete',approval)['operation']['state'],'done')
        finally:
            self.account = previous

    def test_unsafe_folder_delete_refused_subfolders_and_close_never_called(self):
        self.data('folder_create',{'account':'box','name':'Empty'})
        self.assertEqual(self.call('prepare_folder_delete',{'account':'box','folder':'Empty'})['error']['code'],'unsupported_server')
        self.fixture(flags='(\\Deleted)')
        import imaplib
        with patch.object(imaplib.IMAP4,'close',side_effect=AssertionError('CLOSE expunges unnamed mail')):
            self.data('search',{'account':'box'})
            self.data('folders',{'account':'box'})
            target = self.fixture(subject='Delete exact')
            self.data('delete',self.delete_approval([target],'permanent'))
