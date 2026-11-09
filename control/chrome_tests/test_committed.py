"""Chrome owner views remain current when SQLite SELECTs cannot run."""
from contextlib import contextmanager
import sqlite3
import unittest
import test_engine as fixture


class Reads(unittest.TestCase):
    setUp=fixture.Operations.setUp
    tearDown=fixture.Operations.tearDown
    call=fixture.Operations.call
    target=fixture.Operations.target
    prepare=fixture.Operations.prepare

    @contextmanager
    def failed_reads(self):
        database=self.engine.store.db
        class Failed:
            def execute(self,sql,*args,**kwargs):
                if sql.lstrip().upper().startswith('SELECT'):
                    error=sqlite3.OperationalError('database or disk is full');error.sqlite_errorcode=sqlite3.SQLITE_FULL;raise error
                return database.execute(sql,*args,**kwargs)
            def __getattr__(self,name):return getattr(database,name)
        self.engine.store.db=Failed()
        try:yield
        finally:self.engine.store.db=database

    def step(self):
        return {'id':'h1','kind':'activation','element':'e1','submitter':None,'document':'document-1','frame':0,'cancellable':True}

    def test_new_warning_survives_an_empty_cached_pending_and_failed_sqlite_reads(self):
        self.assertEqual(self.engine.pending('chrome')['total'],0)
        self.chrome.steps([self.step()],1)
        expected={item['operation_id'] for item in self.chrome.notice_page()['items']}
        self.assertTrue(expected)
        with self.failed_reads():
            for app in ['chrome',None,'mail']:
                pending=self.engine.pending(app,resolve_checks=False)
                self.assertEqual({item['operation_id'] for item in pending['notices'] if item['app']=='chrome'},expected)
            self.assertEqual({item['operation_id'] for item in self.chrome.notice_page()['items']},expected)

    def test_acknowledgement_never_reappears_from_cached_pending_or_after_restart(self):
        self.chrome.steps([self.step()],1);pending=self.engine.pending('chrome')
        identifier=pending['notices'][0]['operation_id']
        self.assertTrue(self.call('notice_ack',{'operation_id':identifier})['ok'])
        with self.failed_reads():
            self.assertEqual(self.chrome.notice_page()['total'],0)
            self.assertEqual([item for item in self.engine.pending(resolve_checks=False).get('notices',[]) if item['app']=='chrome'],[])
        self.engine.close()
        from aresos_control.engine import Engine
        self.engine=Engine(self.root/'state',self.root/'evidence');self.chrome=self.engine.adapters['chrome'];self.chrome.bridge=self.browser;self.chrome.read_owner_hosts=lambda:[]
        with self.failed_reads():self.assertEqual(self.chrome.notice_page()['total'],0)

    def test_live_session_is_rechecked_during_failed_reads(self):
        self.prepare();self.assertEqual(self.engine.pending('chrome')['items'][0]['validity'],'current')
        with self.failed_reads():self.assertEqual(self.engine.pending('chrome',resolve_checks=False)['items'][0]['validity'],'current')
        self.browser.session='another-browser-session'
        with self.failed_reads():
            pending=self.engine.pending('chrome',resolve_checks=False)
            self.assertEqual(pending['items'][0]['validity'],'refused')
            self.assertIn('session changed',pending['items'][0]['reason'])
        self.assertEqual(self.browser.dispatched,[])

    def test_acknowledgement_survives_tombstone_and_reintroduced_old_working_row(self):
        self.chrome.steps([self.step()],1);identifier=self.chrome.notice_page()['items'][0]['operation_id']
        key='notice:'+identifier;old=self.engine.store.get(key)
        self.call('notice_ack',{'operation_id':identifier})
        self.engine.store.write({key:None},'chrome_test_archive','Archive acknowledged occurrence')
        self.engine.store.write({key:old},'chrome_test_restore','Reintroduce older working notice')
        self.assertEqual(self.chrome.notice_page()['total'],0)
        with self.failed_reads():self.assertFalse(any(item['app']=='chrome' for item in self.engine.pending(resolve_checks=False)['notices']))

    def test_clean_result_keeps_unacknowledged_occurrence_and_recurrence_gets_new_identity(self):
        from aresos_control.warnings import check_result
        self.chrome.steps([self.step()],1);first=self.chrome.notice_page()['items'][0]['operation_id']
        key,source=next(self.engine.store.iter_items('intent:chrome:'))
        changes,_=check_result(self.engine.store,source,key,'page_activation',[],None)
        self.engine.store.write({key:source,**changes},'chrome_test_clean','Committed clean check')
        self.assertEqual(self.chrome.notice_page()['items'][0]['operation_id'],first)
        self.call('notice_ack',{'operation_id':first});self.assertEqual(self.chrome.notice_page()['total'],0)
        self.chrome.steps([self.step()],1);self.assertEqual(self.chrome.notice_page()['total'],1)
        self.assertNotEqual(self.chrome.notice_page()['items'][0]['operation_id'],first)

    def test_an_appended_but_uncommitted_projection_tail_is_never_visible(self):
        from aresos_control.common import canonical,digest
        self.chrome.committed.sync()
        record={'format':2,'seq':self.engine.store.sequence+1,'previous':self.engine.store.head_hash,'time':0,'generation':self.engine.store.generation,'operations':[],
                'chrome':{'notice:invented':{'id':'invented','app':'chrome','state':'partial','ack':False,'untrusted_content':{'warning':'uncommitted'}}}}
        record['hash']=digest(record)
        with open(self.root/'evidence'/'operations.jsonl','ab') as stream:stream.write((canonical(record)+'\n').encode())
        self.assertNotIn('invented',{item['operation_id'] for item in self.chrome.notice_page()['items']})

    def test_ack_at_page_boundary_removes_stale_more_even_when_sqlite_is_full(self):
        for number in range(4):
            step=self.step();step['id']='h'+str(number);self.chrome.steps([step],1)
        pending=self.engine.pending('chrome');self.assertEqual(pending['notices_more']['count'],1)
        self.call('notice_ack',{'operation_id':pending['notices'][0]['operation_id']})
        with self.failed_reads():
            current=self.engine.pending('chrome',resolve_checks=False)
            self.assertEqual(len(current['notices']),3)
            self.assertNotIn('notices_more',current)

    def test_shared_notice_route_retrieves_all_chrome_notices(self):
        for number in range(4):
            step=self.step();step['id']='h'+str(number);self.chrome.steps([step],1)
        pending=self.engine.pending();self.assertEqual(pending['notices_more']['action'],'control_notices')
        first=self.engine.dispatch('control_notices',{'limit':3})
        second=self.engine.dispatch('control_notices',{'limit':3,'cursor':first['cursor']})
        self.assertEqual(first['total'],4)
        self.assertEqual(len({item['operation_id'] for item in first['items']+second['items']}),4)

    def test_failed_sqlite_compact_envelope_with_cached_mail_and_current_chrome_stays_bounded(self):
        self.engine.store.write({'notice:mail-'+str(i):{'id':'mail-'+str(i),'app':'mail','state':'partial','ack':False,
            'created_at':i,'untrusted_content':{'reason':'Synthetic cached Mail warning'}} for i in range(3)},'fixture','Mail warnings')
        self.assertEqual(len(self.engine.pending()['notices']),3)
        for number in range(4):
            step=self.step();step['id']='h'+str(number);self.chrome.steps([step],1)
        with self.failed_reads():
            pending=self.engine.pending(resolve_checks=False)
            self.assertEqual(len(pending['notices']),3)
            self.assertTrue(all(item['app']=='chrome' for item in pending['notices']))
            self.assertEqual(pending['notices_more'],{'count':1,'action':'chrome_notices'})

    def test_historical_index_peak_recovers_after_later_archive_tombstones(self):
        from unittest.mock import patch
        from aresos_control.chrome.committed import Projection
        from aresos_control.common import Refused
        store=self.engine.store
        for key in ['a','b','c']:store.write({'chrome:test:'+key:{'value':key}},'chrome_test','Index-bound fixture')
        projection=Projection(store)
        # Qualification is one current key; three fixture keys exceed this cap.
        with patch('aresos_control.chrome.committed.MAX_KEYS',3):
            with self.assertRaises(Refused):projection.sync()
            store.write({'chrome:test:a':None,'chrome:test:b':None},'chrome_test','Archive old fixture keys')
            projection.sync()
            self.assertEqual(projection.get('chrome:test:c'),{'value':'c'})
            self.assertIsNone(projection.get('chrome:test:a'))
            fresh=Projection(store);fresh.sync()
            self.assertEqual(set(fresh.entries),set(projection.entries))

    def test_unreadable_committed_projection_prioritizes_warning_inside_three_notice_bound(self):
        from unittest.mock import patch
        self.engine.store.write({'notice:mail-'+str(i):{'id':'mail-'+str(i),'app':'mail','state':'partial','ack':False,
            'created_at':i,'untrusted_content':{'reason':'Synthetic cached Mail warning'}} for i in range(3)},'fixture','Mail warnings')
        self.engine.pending()
        with self.failed_reads(),patch.object(self.chrome,'notice_page',side_effect=OSError('Synthetic evidence read failure')):
            pending=self.engine.pending(resolve_checks=False)
            self.assertEqual(len(pending['notices']),3)
            self.assertEqual(pending['notices'][0]['operation_id'],'chrome-owner-state-unavailable')

    def test_mail_only_continuation_keeps_existing_route_but_hidden_chrome_requires_shared_catalogue(self):
        self.engine.store.write({'notice:mail-'+str(i):{'id':'mail-'+str(i),'app':'mail','state':'partial','ack':False,
            'created_at':1e20+i,'untrusted_content':{'warning':'Synthetic Mail warning'}} for i in range(4)},'fixture','Synthetic Mail warnings')
        self.assertEqual(self.engine.pending()['notices_more'],{'count':1,'action':'mail_filing_notices'})
        self.chrome.steps([self.step()],1)
        current=self.engine.pending()
        self.assertTrue(all(item['app']=='mail' for item in current['notices']))
        self.assertEqual(current['notices_more'],{'count':2,'action':'control_notices'})

    def test_private_observation_commits_an_open_check_without_browser_io_and_survives_restart(self):
        from unittest.mock import patch
        step={**self.step(),'kind':'activation_unknown','cancellable':False}
        event={'event':'held_step','session':self.browser.session,'tab':1,'step':step}
        with patch.object(self.browser,'call',side_effect=AssertionError('nested browser call')):
            self.chrome.event(event);sequence=self.engine.store.sequence
            self.chrome.event(event);self.assertEqual(self.engine.store.sequence,sequence)
        self.assertEqual(self.chrome.notice_page()['total'],1)
        with self.failed_reads():self.assertEqual(self.chrome.notice_page()['total'],1)
        self.engine.close()
        from aresos_control.engine import Engine
        self.engine=Engine(self.root/'state',self.root/'evidence');self.chrome=self.engine.adapters['chrome'];self.chrome.bridge=self.browser;self.chrome.read_owner_hosts=lambda:[]
        self.assertGreaterEqual(self.chrome.notice_page()['total'],1);self.assertEqual(self.browser.dispatched,[])

    def test_open_dialog_keeps_a_dispatched_input_unknown_and_never_replays(self):
        approval=self.prepare();original=self.browser.call
        def modal(name,**args):
            result=original(name,**args)
            if name=='input':result['dialog']={'kind':'confirm','text':'Continue?'}
            return result
        self.browser.call=modal
        sent=self.call('submit',approval);self.assertTrue(sent['ok'],sent)
        self.assertEqual(sent['data']['operation']['state'],'unknown')
        self.call('submit',approval);self.assertEqual(len(self.browser.dispatched),1)

    def test_a_modal_is_not_evidence_that_an_observed_submission_document_disappeared(self):
        import copy
        from unittest.mock import patch
        step={**self.step(),'kind':'native_submit'};full=copy.deepcopy(self.browser.facts)
        self.browser.facts.update(frames=[],dialog={'kind':'confirm','text':'Continue?'})
        original=self.browser.call;acks=[]
        def call(name,**args):
            if name=='ack_steps':acks.extend(args['steps'])
            return original(name,**args)
        with patch.object(self.browser,'call',side_effect=call):
            result=self.chrome.steps([step],1)
            self.assertTrue(result[0]['pending']);self.assertEqual(acks,[])
            key,source=next(self.engine.store.iter_items('intent:chrome:'));self.assertEqual(source['state'],'started')
            self.browser.facts=full
            prepared=self.chrome.steps([step],1);self.assertIn('approval',prepared[0]);self.assertEqual(len(acks),1)
            same=self.chrome.steps([step],1);self.assertEqual(same,[]);self.assertEqual(len(acks),2)
            self.assertEqual(len([v for _,v in self.engine.store.iter_items('op:') if v['state']=='reserved']),1)
