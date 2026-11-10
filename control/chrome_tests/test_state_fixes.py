"""Panel D regressions, through production owner actions, without a browser."""
import copy
import errno
import json
import shutil
import sqlite3
import time
import unittest
from unittest.mock import patch

import test_engine as fixture
import test_committed
from test_policy import entry
from aresos_control.common import Refused
from aresos_control.engine import Engine


class StateFixes(unittest.TestCase):
    setUp=fixture.Operations.setUp
    tearDown=fixture.Operations.tearDown
    call=fixture.Operations.call
    target=fixture.Operations.target
    prepare=fixture.Operations.prepare
    failed_reads=test_committed.Reads.failed_reads
    step=test_committed.Reads.step

    def snapshot(self):
        path=self.root/'snapshot.sqlite'
        connection=sqlite3.connect(path)
        self.engine.store.db.backup(connection);connection.close()
        return path

    def reopen(self, snapshot=None):
        self.engine.close()
        if snapshot:shutil.copyfile(snapshot,self.root/'state'/'control.sqlite')
        self.engine=Engine(self.root/'state',self.root/'evidence')
        self.chrome=self.engine.adapters['chrome'];self.chrome.bridge=self.browser
        self.chrome.read_owner_hosts=lambda:[]

    def restore(self):
        result=self.engine.request({'v':1,'method':'call','action':'control_restore_confirm',
            'arguments':{'confirm':'invalidate earlier approvals'}},True)
        self.assertTrue(result['ok'],result)
        self.assertFalse(self.engine.store.locked)

    def test_s1_restore_reconciles_revocation_readonly_and_qualification_offline(self):
        fixture.OwnerRules.gmail(self)
        approval=self.prepare();self.assertTrue(self.call('submit',approval)['ok'])
        allowed=self.call('sites',{'command':'allow','operation_id':approval['operation_id']},True)['data']['id']
        snapshot=self.snapshot()
        self.assertTrue(self.call('sites',{'command':'revoke','id':allowed},True)['ok'])
        self.assertTrue(self.call('sites',{'command':'readonly','site':'https://gmail.test/'},True)['ok'])
        record=self.chrome.qualification.record()
        failed=entry(build=self.chrome.qualification.build,version='157.0.1.1')
        failed['core']['binding']=False
        record['entries'].append(failed)
        self.engine.store.write({'chrome:qualification':record},'chrome_qualification','Synthetic recorded failure')
        self.reopen(snapshot);self.assertTrue(self.engine.store.locked)
        self.restore()
        self.assertTrue(self.engine.store.get('chrome:allow:'+allowed)['revoked'])
        self.assertTrue(self.engine.store.get('chrome:readonly:gmail.test'))
        self.assertEqual(self.chrome.qualification.record(),record)
        self.browser.version='157.0.1.2'
        with self.assertRaises(Refused) as error:self.chrome.trusted(self.engine.operation(approval['operation_id'],'chrome'))
        self.assertEqual(error.exception.code,'qualification_failed')
        self.assertEqual(self.call('click',self.target())['error']['code'],'qualification_failed')
        self.reopen();self.assertEqual(self.chrome.qualification.record(),record)

    def test_s1_readable_policy_rollback_cannot_hide_committed_qualification(self):
        old=self.chrome.qualification.record();record=copy.deepcopy(old)
        failure=entry(build=self.chrome.qualification.build,version='157.0.1.1')
        failure['core']['password_exclusion']=False;record['entries'].append(failure)
        self.engine.store.write({'chrome:qualification':record},'chrome_qualification','Synthetic later failure')
        self.engine.store.db.execute('UPDATE kv SET v=? WHERE k=?',(json.dumps(old),'chrome:qualification'))
        self.engine.store.db.commit()
        self.assertEqual(self.chrome.qualification.record(),record)
        self.browser.version='157.0.1.2'
        self.assertEqual(self.call('read',{'tab':1})['error']['code'],'qualification_failed')

    def test_s2_readable_rollback_pending_uses_committed_reservation(self):
        snapshot=self.snapshot();approval=self.prepare()
        self.reopen(snapshot)
        for app in ['chrome',None]:
            page=self.engine.pending(app,resolve_checks=False)
            self.assertEqual(page['total'],1,page)
            self.assertEqual(page['items'][0]['operation_id'],approval['operation_id'])
            self.assertEqual(page['items'][0]['validity'],'refused')
            self.assertTrue(page['restore_required'])
        self.assertEqual(self.engine.operation(approval['operation_id'],'chrome')['state'],'reserved')

    def test_s2_failed_completion_marker_never_reports_uncommitted_done(self):
        approval=self.prepare();store=self.engine.store
        operation=self.engine.operation(approval['operation_id'],'chrome');operation['state']='submitting'
        store.write({'op:'+operation['id']:operation},'chrome_submit','Input may start',operation['id'])
        operation['state']='done';append=store._append
        def fail_marker(value):
            if 'commit' in value:raise OSError(errno.ENOSPC,'Synthetic marker failure')
            return append(value)
        with patch.object(store,'_append',side_effect=fail_marker):
            with self.assertRaises(OSError):store.write({'op:'+operation['id']:operation},'chrome_submit','Completed',operation['id'])
        self.assertEqual(store.get('op:'+operation['id'])['state'],'done')
        self.assertEqual(self.engine.operation(operation['id'],'chrome')['state'],'submitting')
        self.assertEqual(self.engine.pending('chrome',resolve_checks=False)['items'][0]['state'],'submitting')
        status=self.call('operation_status',{'operation_id':operation['id']})
        self.assertEqual(status['data']['operation']['state'],'submitting',status)

    def test_s3_cancel_and_expiry_ack_survive_rollback_restore_archive_restart(self):
        for outcome in ['cancel','expiry']:
            with self.subTest(outcome=outcome):
                approval=self.prepare();identifier=approval['operation_id']
                if outcome=='cancel':self.assertTrue(self.call('drop',{'operation_id':identifier})['ok'])
                else:
                    op=self.engine.operation(identifier);op['expires']=0
                    self.engine.store.write({'op:'+identifier:op},'chrome_test','Synthetic expiry',identifier)
                    self.engine.expire()
                snapshot=self.snapshot()
                self.assertTrue(self.call('notice_ack',{'operation_id':identifier})['ok'])
                self.reopen(snapshot);self.restore()
                op=self.engine.operation(identifier,'chrome')
                self.assertEqual(op['state'],'failed');self.assertTrue(op['ack'])
                self.assertEqual(self.chrome.notice_page()['total'],0)
                self.engine.store.db.execute('UPDATE retained SET created=0');self.engine.store.db.commit()
                result=self.engine.request({'v':1,'method':'call','action':'control_archive','arguments':{'before':time.time()-1,'confirm':'archive finished history'}},True)
                self.assertTrue(result['ok'],result)
                self.reopen();self.assertEqual(self.chrome.notice_page()['total'],0)

    def test_s4_more_than_512_completed_checks_leave_room_for_chrome_and_mail(self):
        from aresos_control import retention
        store=self.engine.store
        # Exercise the actual reader/step route; an already-stale submission
        # commits cleanly without needing approval or receiver traffic.
        original=self.browser.call
        queued=[]
        def call(name,**args):
            if name=='queued_steps':return list(queued)
            return original(name,**args)
        self.browser.call=call
        for number in range(520):
            queued[:]=[{**self.step(),'id':str(number),'kind':'native_submit','document':'old-document'}]
            result=self.call('read',{'tab':1});self.assertTrue(result['ok'],result)
        self.assertLess(len(store.items('intent:chrome:')),512)
        store.write({},'mail_fixture_change','Synthetic Mail change open',outcome='started')
        self.assertEqual(len(store.active_intents),1)
        store.write({},'mail_fixture_change','Synthetic Mail change done',outcome='done')
        retention.expire(self.engine)
        self.assertEqual(store.items('intent:chrome:'),[])
        self.assertEqual(self.chrome.notice_page()['total'],0)
        self.assertEqual(self.browser.dispatched,[])

    def test_s4_retirement_keeps_warning_ack_and_dedup_identity_in_history(self):
        from aresos_control import retention
        step=self.step();self.chrome.steps([step],1)
        key,source=next(self.engine.store.iter_items('intent:chrome:'))
        identifier=self.chrome.notice_page()['items'][0]['operation_id']
        self.assertTrue(self.call('notice_ack',{'operation_id':identifier})['ok'])
        retention.expire(self.engine)
        self.assertIsNone(self.engine.store.get(key))
        self.assertIsNone(self.engine.store.get('notice:'+identifier))
        self.reopen();self.chrome.steps([step],1)
        self.assertEqual(self.chrome.notice_page()['total'],0)
        self.assertEqual(self.chrome.committed.historical(key)['id'],source['id'])
        self.assertTrue(self.chrome.committed.historical('notice:'+identifier)['ack'])
        retention.expire(self.engine)
        self.assertIsNone(self.engine.store.get(key),'Repeated evidence must not recreate an unacknowledged working notice')
        # A committed clean interval must end the old condition, even if its
        # working row is retired again before the same evidence returns.
        from aresos_control.warnings import check_result
        source=self.chrome.committed.historical(key)
        changes,_=check_result(self.engine.store,source,key,'page_activation',[],None)
        self.engine.store.write({key:source,**changes},'chrome_page_step','Synthetic clean interval')
        retention.expire(self.engine);self.chrome.steps([step],1)
        current=self.chrome.notice_page();self.assertEqual(current['total'],1)
        self.assertNotEqual(current['items'][0]['operation_id'],identifier)

    def test_s4_archive_retires_checks_even_above_the_shared_history_quota(self):
        from aresos_control import retention
        source={'id':'finished','app':'chrome','state':'done','step':self.step(),'tab':1,'session':self.browser.session}
        store=self.engine.store;store.write({'intent:chrome:finished':source},'chrome_page_step','Synthetic completed check')
        with patch.object(store.ledger,'history_usage',return_value=retention.HISTORY_BYTES+1):
            result=self.engine.request({'v':1,'method':'call','action':'control_archive',
                'arguments':{'before':time.time()-1,'confirm':'archive finished history'}},True)
        self.assertTrue(result['ok'],result)
        self.assertIsNone(store.get('intent:chrome:finished'))

    def test_s5_clean_stopped_submission_has_no_interruption_warning(self):
        result=self.chrome.steps([{**self.step(),'kind':'native_submit'}],1)
        self.assertEqual(self.chrome.notice_page()['total'],0)
        self.assertTrue(self.call('submit',result[0]['approval'])['ok'])
        self.assertEqual(self.chrome.notice_page()['total'],0)
        self.assertEqual(len(self.browser.dispatched),1)

    def test_s6_lost_queue_resolves_native_check_and_preserves_uncertain_occurrence(self):
        for kind in ['native_submit','activation_unknown']:
            self.chrome.observe_step({**self.step(),'kind':kind},1)
        self.browser.session='new-session'
        self.browser.facts['session']=self.browser.session
        result=self.call('read',{'tab':1});self.assertTrue(result['ok'],result)
        sources=[value for _,value in self.engine.store.iter_items('intent:chrome:')]
        self.assertEqual(len(sources),2)
        self.assertTrue(all(source['state']=='done' and source['result']=='stale' and source['resumable'] is False for source in sources))
        notices=self.chrome.notice_page();self.assertEqual(notices['total'],1)
        self.assertTrue(self.call('notice_ack',{'operation_id':notices['items'][0]['operation_id']})['ok'])
        self.assertEqual(self.chrome.notice_page()['total'],0)
        self.reopen();self.assertEqual(self.chrome.notice_page()['total'],0)
        self.assertEqual(self.browser.dispatched,[])

    def test_s6_a_stale_step_cannot_be_prepared_if_the_same_queue_entry_returns(self):
        step={**self.step(),'kind':'native_submit'}
        self.chrome.observe_step(step,1)
        self.assertTrue(self.call('read',{'tab':1})['ok'])
        key,source=next(self.engine.store.iter_items('intent:chrome:'))
        self.assertEqual(source['result'],'stale')
        self.assertEqual(self.chrome.steps([step],1),[])
        self.assertFalse(any(value['app']=='chrome' and value['state']=='reserved' for _,value in self.engine.store.items('op:')))
        self.assertEqual(self.engine.store.get(key)['state'],'done')
        self.assertEqual(self.browser.dispatched,[])

    def test_s7_drop_spends_cancel_reservation_at_history_and_physical_boundaries(self):
        from aresos_control.space import SAFETY_FLOOR
        from collections import namedtuple
        usage=namedtuple('usage','total used free')
        approval=self.prepare();store=self.engine.store
        with patch.object(store,'admit_history',side_effect=Refused('storage_limit','Ordinary history is full')):
            reply=self.call('drop',{'operation_id':approval['operation_id']})
        self.assertTrue(reply['ok'],reply)
        approval=self.prepare()
        held=store.ledger.holds['cancel:'+approval['operation_id']]
        with patch('aresos_control.space.shutil.disk_usage',return_value=usage(10**9,0,SAFETY_FLOOR+held+4096)):
            reply=self.call('drop',{'operation_id':approval['operation_id']})
        self.assertTrue(reply['ok'],reply);self.assertEqual(self.browser.dispatched,[])

    def test_s8_archive_remains_publicly_reachable_above_index_bound_and_after_restart(self):
        for restart in [False,True]:
            for number in range(4):
                op=self.prepare();self.assertTrue(self.call('submit',op)['ok'])
            self.engine.store.db.execute('UPDATE retained SET created=0');self.engine.store.db.commit()
            if restart:self.reopen()
            with patch('aresos_control.chrome.committed.MAX_KEYS',3):
                from aresos_control.chrome.committed import Projection
                self.chrome.committed=self.engine.store._chrome_state=Projection(self.engine.store)
                pending=self.engine.pending(resolve_checks=False)
                self.assertIn('unavailable',pending)
                reply=self.engine.request({'v':1,'method':'call','action':'control_archive',
                    'arguments':{'before':time.time()-1,'confirm':'archive finished history'}},True)
                self.assertTrue(reply['ok'],reply)
                self.assertNotIn('unavailable',self.engine.pending(resolve_checks=False))

    def mail_notices(self,count):
        self.engine.store.write({'notice:mail-'+str(i):{'id':'mail-'+str(i),'app':'mail','state':'partial','ack':False,
            'created_at':int(1577836800*1e9)+i,'untrusted_content':{'warning':'Synthetic Mail occurrence'}}
            for i in range(count)},'fixture','Synthetic Mail warnings')

    def test_s9_mail_only_and_mixed_fallback_keep_all_remaining_counts(self):
        self.mail_notices(4);self.engine.pending()
        with self.failed_reads():
            pending=self.engine.pending(resolve_checks=False)
            self.assertEqual(pending['notices_more'],{'count':1,'action':'mail_filing_notices'})
        self.chrome.steps([self.step()],1)
        with self.failed_reads():
            pending=self.engine.pending(resolve_checks=False)
            self.assertEqual(pending['notices_more'],{'count':2,'action':'control_notices'})
            self.assertEqual(pending['notices'][0]['app'],'chrome')

    def test_s9_replacing_a_cached_chrome_page_does_not_double_count_its_hidden_rows(self):
        self.mail_notices(4)
        for number in range(4):self.chrome.steps([{**self.step(),'id':str(number)}],1)
        page=self.engine.pending();self.assertEqual(page['notices_more']['count'],5)
        for _,notice,_ in list(self.chrome.committed.rows('notice:')):
            if not notice.get('ack'):self.assertTrue(self.call('notice_ack',{'operation_id':notice['id']})['ok'])
        with self.failed_reads():
            pending=self.engine.pending(resolve_checks=False)
            self.assertTrue(all(item['app']=='mail' for item in pending['notices']))
            self.assertEqual(len(pending['notices'])+pending['notices_more']['count'],4)
            self.assertEqual(pending['notices_more']['action'],'mail_filing_notices')

    def test_s10_mixed_notice_pages_use_nanosecond_chronology(self):
        self.mail_notices(3);self.chrome.steps([self.step()],1)
        first=self.engine.dispatch('control_notices',{'limit':3})
        self.assertEqual(first['items'][0]['app'],'chrome')
        self.assertEqual(first['total'],4)
        last=self.engine.dispatch('control_notices',{'limit':3,'cursor':first['cursor']})
        self.assertEqual([item['operation_id'] for item in last['items']],['mail-0'])

    def test_s12_every_page_text_copy_is_inside_untrusted_content(self):
        sentinel='SYNTHETIC_PAGE_SENTINEL'
        def assert_marked(value,path=()):
            if isinstance(value,dict):
                for key,item in value.items():assert_marked(item,path+(key,))
            elif isinstance(value,list):
                for item in value:assert_marked(item,path)
            elif isinstance(value,str) and sentinel in value:
                self.assertIn('untrusted_content',path,path)
        self.browser.facts['dialog']={'kind':'confirm','text':sentinel}
        assert_marked(self.call('read',{'tab':1}))
        self.browser.facts['dialog']=None
        step={**self.step(),'label':sentinel}
        assert_marked(self.chrome.steps([step],1))
        approval=self.prepare();op_id=approval['operation_id']
        self.engine.stage(op_id,'page',json.dumps({'dialog':{'text':sentinel}}))
        assert_marked(self.engine.public_operation(self.engine.operation(op_id)))
        assert_marked(self.chrome.evidence(op_id))
        assert_marked(self.call('operation_status',{'operation_id':op_id}))
        assert_marked(self.engine.dispatch('control_log',{}))
        # Pre-upgrade audit summaries and free-input stages need the same rule.
        operation=self.engine.operation(op_id);operation['stages']['page']=sentinel
        self.engine.store.write({'op:'+op_id:operation},'chrome_submit',sentinel,op_id)
        assert_marked(self.engine.dispatch('control_log',{}))
        assert_marked(self.engine.public_operation(operation))
        # Stage details observed before a failed write also appear in error
        # envelopes. They have not passed through public_operation().
        from aresos_control.results import Observations
        self.engine.store.observations=Observations()
        with patch.object(self.engine.store,'write',side_effect=OSError(errno.ENOSPC,'Synthetic stage failure')):
            with self.assertRaises(OSError):self.engine.stage(op_id,'page',sentinel)
        result=self.engine.store.observations.finish({'ok':False,'error':{'code':'storage_limit','message':'Synthetic failure'}},self.engine.store)
        assert_marked(result)


if __name__=='__main__':unittest.main()
