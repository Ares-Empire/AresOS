"""Under a restore lock no app but Chrome is shown as current (package 20-restore-lock, R1).

A restore lock means the working database is older than the committed record,
so the Mail rows and warnings in it may describe work that is no longer current.
While the lock holds, control_pending and control_notices list only Chrome's
committed rows and warnings and say that other apps are unavailable, no
continuation names a route the lock refuses, and no Mail server check runs.
chrome_notices is unchanged. After control_restore_confirm the ordinary replies
come back, checks included.
"""
import errno
import sqlite3
import time
import unittest
from unittest.mock import patch

import test_engine as fixture
from test_full_disk_reads import ReadOnlyIMAP
from aresos_control.engine import Engine
from aresos_control.mail.roles import resolve
from aresos_control.mail.transport import folders

# The notice routes Engine.dispatch answers while the store is locked.
ANSWERED_ROUTES={'control_notices','chrome_notices'}
CONFIRM={'confirm':'invalidate earlier approvals'}


class RestoreLock(unittest.TestCase):
    setUp=fixture.Operations.setUp
    tearDown=fixture.Operations.tearDown
    call=fixture.Operations.call
    target=fixture.Operations.target
    prepare=fixture.Operations.prepare

    def request(self,name,args=None,admin=False):
        return self.engine.request({'v':1,'method':'call','action':name,'arguments':args or {}},admin)

    def step(self,number=1):
        return {'id':'h'+str(number),'kind':'activation','element':'e1','submitter':None,'document':'document-1','frame':0,'cancellable':True}

    def fake_transport(self):
        """Every IMAP or SMTP session the current Mail adapter opens lands in self.sessions."""
        self.imap=ReadOnlyIMAP(0,b'<restore-lock@mail.invalid>')
        self.sessions=[]
        imap,sessions=self.imap,self.sessions
        class Session:
            def __init__(self,kind):self.kind=kind
            def __enter__(self):sessions.append(self.kind);return imap
            def __exit__(self,*exc):return False
        transport=self.engine.adapters['mail'].transport
        for kind in ['imap','smtp']:
            patcher=patch.object(transport,kind,lambda account,kind=kind:Session(kind))
            patcher.start();self.addCleanup(patcher.stop)

    def plant_mail(self,notices=4):
        """A Mail account, one submitting send with an open Sent-copy check, and Mail warnings newer than any Chrome row."""
        store=self.engine.store
        account={'id':'box','addresses':['owner@example.invalid'],'ready':True,'capabilities':list(self.imap.capabilities),
                 'smtp_capabilities':[],'sent_policy':'client','safe_folder_delete':True,'format':'plain','signature':'',
                 **resolve(folders(self.imap))}
        store.write({'mail:account:box':account},'fixture','Synthetic Mail account, test store only')
        generation=store.generation
        op={'id':generation+':stale-send','generation':generation,'app':'mail','action':'mail_send','state':'submitting',
            'reason':'Durably submitting; do not cancel or retry.','input_hash':'fixture','expires':time.time()+900,'stages':{},
            'approval':{'question':'Send?','operation_id':generation+':stale-send','description':{'subject':'Synthetic send'}},
            'payload':{'composition':{'mail':{'account':'box'}}},'context_version':1,'sent_copy_check':{'state':'open'}}
        store.write({'op:'+op['id']:op},'fixture','Synthetic submitting send, test store only',op['id'])
        store.write({'notice:mail-'+str(i):{'id':'mail-'+str(i),'app':'mail','state':'partial','ack':False,'created_at':1e20+i,
            'untrusted_content':{'warning':'Synthetic Mail warning'}} for i in range(notices)},'fixture','Synthetic Mail warnings')
        return op['id']

    def lock(self):
        """Put an older database under a newer committed record, as a crash or an owner's restore does."""
        backup=sqlite3.connect(self.root/'backup.sqlite');self.engine.store.db.backup(backup);backup.close()
        self.engine.store.write({'notice:mail-later':{'id':'mail-later','app':'mail','state':'partial','ack':False,'created_at':1e20+99,
            'untrusted_content':{'warning':'Committed after the backup'}}},'fixture','A write the older database lacks')
        self.restart(older_database=True)
        self.assertTrue(self.engine.store.locked)

    def restart(self,older_database=False):
        self.engine.close()
        if older_database:(self.root/'state'/'control.sqlite').write_bytes((self.root/'backup.sqlite').read_bytes())
        self.engine=Engine(self.root/'state',self.root/'evidence')
        self.chrome=self.engine.adapters['chrome'];self.chrome.bridge=self.browser;self.chrome.read_owner_hosts=lambda:[]
        self.fake_transport()

    def apps(self,view):
        return {item['app'] for item in view.get('items',[])}|{item['app'] for item in view.get('notices',[])}

    def assert_only_chrome(self,view):
        self.assertTrue(view['restore_required'],view)
        self.assertLessEqual(self.apps(view),{'chrome'},view)
        self.assertIn('until the owner confirms the restore',view.get('unavailable',''),view)
        if 'notices_more' in view:
            self.assertIn(view['notices_more']['action'],ANSWERED_ROUTES,view)

    def test_locked_pending_lists_only_chrome_rows_and_warnings_until_the_owner_confirms(self):
        self.fake_transport();stale=self.plant_mail()
        approval=self.prepare();self.chrome.steps([self.step()],1)
        chrome_warnings={item['operation_id'] for item in self.chrome.notice_page()['items']};self.assertEqual(len(chrome_warnings),1)
        unlocked=self.request('control_pending')['data']
        self.assertIn(stale,{item['operation_id'] for item in unlocked['items']})
        self.assertIn('mail',self.apps(unlocked))
        self.lock()
        # The answered read, and the pending envelope of a refused one (its app view is Mail's).
        for name in ['control_pending','mail_filing_notices']:
            with self.subTest(name):
                result=self.request(name)
                self.assertEqual(result['ok'],name=='control_pending',result)
                views=[result['pending']]+([result['data']] if result['ok'] else [])
                for view in views:self.assert_only_chrome(view)
                if result['ok']:
                    rows={item['operation_id'] for item in result['data']['items']}
                    self.assertEqual(rows,{approval['operation_id']},'Chrome committed rows stay listed')
                    self.assertEqual({item['operation_id'] for item in result['data']['notices']},chrome_warnings)
                else:
                    self.assertEqual(result['error']['code'],'restore_required')
        confirmed=self.request('control_restore_confirm',CONFIRM,admin=True);self.assertTrue(confirmed['ok'],confirmed)
        after=self.request('control_pending');self.assertTrue(after['ok'],after)
        self.assertFalse(after['data']['restore_required']);self.assertNotIn('unavailable',after['data'])
        self.assertIn(stale,{item['operation_id'] for item in after['data']['items']})
        self.assertIn('mail',self.apps(after['data']))

    def test_locked_mail_only_warnings_leave_no_continuation_to_the_refused_route(self):
        self.fake_transport();self.plant_mail()
        # Unlocked, Mail's own catalogue is the continuation for Mail-only warnings.
        self.assertEqual(self.request('control_pending')['data']['notices_more']['action'],'mail_filing_notices')
        self.lock()
        for name in ['control_pending','control_notices']:
            with self.subTest(name):
                result=self.request(name);self.assertTrue(result['ok'],result)
                data=result['data']
                self.assertEqual(data['items'],[]);self.assertEqual(data.get('notices',[]),[])
                self.assertNotIn('notices_more',data);self.assertIsNone(data['cursor'])
                self.assertIn('until the owner confirms the restore',data.get('unavailable',''),data)
                self.assert_only_chrome(result['pending'])
        self.assertEqual(self.request('control_notices')['data']['total'],0)

    def test_locked_notices_page_only_chrome_warnings_through_an_answered_route(self):
        self.fake_transport();self.plant_mail()
        for number in range(4):self.chrome.steps([self.step(number)],1)
        chrome_warnings={item['operation_id'] for item in self.engine.dispatch('chrome_notices',{'limit':10})['items']}
        self.assertEqual(len(chrome_warnings),4)
        self.lock()
        pending=self.request('control_pending')['data'];self.assert_only_chrome(pending)
        self.assertEqual(len(pending['notices']),3)
        self.assertEqual(pending['notices_more'],{'count':1,'action':'control_notices'})
        first=self.request('control_notices',{'limit':3});self.assertTrue(first['ok'],first)
        self.assertEqual(first['data']['total'],4);self.assertIn('until the owner confirms the restore',first['data'].get('unavailable',''),first)
        second=self.request('control_notices',{'limit':3,'cursor':first['data']['cursor']});self.assertTrue(second['ok'],second)
        paged=first['data']['items']+second['data']['items']
        self.assertEqual({item['app'] for item in paged},{'chrome'})
        self.assertEqual({item['operation_id'] for item in paged},chrome_warnings)
        chrome=self.request('chrome_notices',{'limit':10});self.assertTrue(chrome['ok'],chrome)
        self.assertEqual({item['operation_id'] for item in chrome['data']['items']},chrome_warnings)
        self.assertNotIn('unavailable',chrome['data'])
        self.assert_only_chrome(chrome['pending'])
        self.assertTrue(self.request('control_restore_confirm',CONFIRM,admin=True)['ok'])
        after=self.request('control_notices',{'limit':10})['data']
        self.assertNotIn('unavailable',after);self.assertIn('mail',{item['app'] for item in after['items']})

    def test_locked_reads_open_no_mail_server_session(self):
        # The older database keeps the Sent-copy check open, as after a crash: no read
        # before the lock may run it (package review 1), or the lock's refused write
        # would stop a reverted engine before IMAP and the counter would prove nothing.
        self.fake_transport();self.plant_mail()
        self.prepare();self.chrome.steps([self.step()],1)
        self.lock()
        self.assertEqual(self.sessions,[])
        for name in ['control_pending','control_notices','chrome_notices']:
            with self.subTest(name):
                result=self.request(name)
                self.assertEqual(self.sessions,[],name)
                self.assertTrue(result['ok'],result)
        self.assertTrue(self.request('control_restore_confirm',CONFIRM,admin=True)['ok'])
        self.assertTrue(self.request('control_pending')['ok'])
        self.assertIn('imap',self.sessions,'checks resume once the owner has confirmed')
        self.assertNotIn('smtp',self.sessions)


    def test_locked_storage_failure_lists_no_stale_mail_notice(self):
        # Security review 1: the storage-failure fallback of pending listed the recovery notices that
        # the lock's opening recovery defers from the older database, and the snapshot's other apps.
        self.fake_transport();self.plant_mail()
        self.prepare();self.chrome.steps([self.step()],1)
        self.lock()
        self.assertTrue(any(key.startswith('notice:') and value.get('app')=='mail'
                            for changes,_,_ in self.engine.store.deferred_notices.values() for key,value in changes.items()),
                        'the older database leaves a deferred Mail recovery notice')
        self.assertTrue(self.request('control_pending')['ok'])
        def full(*arguments,**options):raise OSError(errno.ENOSPC,'No space left on device')
        with patch.object(self.chrome.committed,'sync',full):
            for name in ['control_pending','control_notices']:
                with self.subTest(name):
                    result=self.request(name)
                    for view in [result['pending']]+([result['data']] if result['ok'] and name=='control_pending' else []):
                        self.assert_only_chrome(view)
        self.assertEqual(self.sessions,[])


if __name__=='__main__':
    unittest.main()
