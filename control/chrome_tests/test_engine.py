import copy
import errno
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aresos_control.engine import Engine
from aresos_control.chrome.adapter import view_identity
from aresos_control.chrome.policy import HOSTS
from test_policy import entry

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.work/20-chrome'; WORK.mkdir(parents=True,exist_ok=True)


class Browser:
    session='fixture-session'; version='157.0.1.0'
    def __init__(self):
        self.dispatched=[]
        target={'element':'e1','role':'button','name':'Send','label':'Send','title':'','href':None,'states':{},'editable':False,'search':False,'submit':False,'box':{'x':1,'y':1,'width':30,'height':30},'onscreen':True}
        self.facts={'session':self.session,'tab':1,'url':'https://fixture.test/','title':'Fixture','frames':[
            {'frame':0,'document':'document-1','url':'https://fixture.test/','title':'Fixture','revision':1,'scroll':{},
             'target':target,'rows':[target],'form':None,'editable':[{'element':'e2','label':'Body','value':'Existing draft'}],'item':'Fixture item',
             'adapter':{'account':None}}],'dialog':None}
    def call(self,name,**args):
        if name=='validity':return {'document':self.facts['frames'][0]['document'],'control':self.facts.get('control'),'element_present':True}
        if name=='configure': return {'configured':True}
        if name in {'facts','read'}: return copy.deepcopy(self.facts)
        if name=='tab_context':return {'tab':args['tab'],'url':self.facts['url'],'session':self.session}
        if name=='open':self.dispatched.append((name,args));return {'tab':2,'session':self.session}
        if name=='tabs': return {'items':[{'tab':1,'url':self.facts['url'],'title':'Fixture'}]}
        self.dispatched.append((name,args))
        return {'checked':True,'dispatched':True,'steps':[]}
    def close(self): pass


class Operations(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=WORK)
        self.root=Path(self.temp.name)
        self.mock=patch('aresos_control.engine.Boundary'); self.mock.start()
        self.engine=Engine(self.root/'state',self.root/'evidence')
        self.chrome=self.engine.adapters['chrome']; self.browser=Browser(); self.chrome.bridge=self.browser
        self.chrome.read_owner_hosts=lambda: []
        record={'format':1,'entries':[entry(build=self.chrome.qualification.build)]}
        self.engine.store.write({'chrome:qualification':record},'chrome_test_setup','Synthetic qualification, test store only')
    def tearDown(self):
        self.engine.close();self.mock.stop();self.temp.cleanup()
    def call(self,verb,args=None,admin=False):
        return self.engine.request({'v':1,'method':'call','action':'chrome_'+verb,'arguments':args or {}},admin)
    def target(self):
        frame=self.browser.facts['frames'][0]
        return {'reference':{'session':self.browser.session,'tab':1,'frame':0,'document':frame['document'],'view':view_identity(self.browser.facts),'element':'e1'},'expected':copy.deepcopy(frame['target'])}
    def prepare(self):
        result=self.call('click',self.target());self.assertTrue(result['ok'],result)
        return result['data']['approval']

    def test_group1_approval_first_exact_and_dispatch_once(self):
        approval=self.prepare();self.assertEqual(self.browser.dispatched,[])
        self.assertEqual(list(approval),['question','operation_id','description'])
        wrong={**approval,'question':'Changed'};self.assertFalse(self.call('submit',wrong)['ok']);self.assertEqual(self.browser.dispatched,[])
        sent=self.call('submit',approval);self.assertTrue(sent['ok'],sent)
        self.assertEqual(sent['data']['operation']['state'],'done');self.assertEqual(len(self.browser.dispatched),1)
        self.assertTrue(self.browser.dispatched[0][1]['approved'])
        self.assertTrue(self.call('submit',approval)['ok']);self.assertEqual(len(self.browser.dispatched),1)

    def test_owner_excluded_link_is_refused_before_any_input(self):
        self.chrome.read_owner_hosts=lambda:['approval.test']
        target=self.browser.facts['frames'][0]['target'];target.update(name='Read more',label='Read more',href='http://approval.test/')
        result=self.call('click',self.target())
        self.assertFalse(result['ok']);self.assertEqual(self.browser.dispatched,[])

    def test_group3_current_draft_bound_even_without_prior_fill_and_across_frames(self):
        approval=self.prepare()
        state=approval['description']['untrusted_content']['page_state']
        self.assertEqual(state['editable'][0]['fields'][0]['value'],'Existing draft')
        self.assertIn("isn't visible to the tool",approval['question'])
        # The extension receives the committed binding verbatim, independent of prior unrelated approvals.
        self.call('submit',approval)
        self.assertEqual(self.browser.dispatched[0][1]['binding']['editable'],state['editable'])

    def test_failed_upload_staging_releases_copy_and_idle_cleanup_expires_old_copies(self):
        import os,time
        from aresos_control.chrome.uploads import prune
        from aresos_control.common import digest,Refused
        self.chrome.upload_dir=self.root/'uploads'
        data=b'Exact fixture bytes';key=self.engine.blobs.put(data,origin='caller_import')
        file={'sha256':key,'size':len(data),'name':'fixture.txt','real_path':'/fixture/source.txt'}
        self.engine.store.write({'blob:'+digest(file):file},'chrome_test','Synthetic imported file')
        original=self.browser.call
        def broken(name,**args):
            if name=='stage_file':raise Refused('transport_error','Synthetic cut during staging')
            return original(name,**args)
        self.browser.call=broken
        prepared=self.call('upload',{**self.target(),'path':'/fixture/source.txt','file':file})
        self.assertTrue(prepared['ok'],prepared)
        self.call('submit',prepared['data']['approval'])
        self.assertEqual(list(self.chrome.upload_dir.iterdir()),[])
        retained=self.chrome.upload_dir/'expired';retained.write_bytes(data);os.utime(retained,(time.time()-901,)*2)
        prune(self.chrome,admit=False);self.assertFalse(retained.exists())

    def test_group8_drop_deadline_restart_never_dispatch(self):
        for mode in ['drop','expired']:
            approval=self.prepare()
            if mode=='drop': result=self.call('drop',{'operation_id':approval['operation_id']})
            else:
                op=self.engine.operation(approval['operation_id']);op['expires']=0
                self.engine.store.write({'op:'+op['id']:op},'chrome_test_setup','Expire synthetic approval',op['id'])
            reply=self.call('submit',approval)
            self.assertEqual(reply['data']['operation']['state'],'failed')
        self.assertEqual(self.browser.dispatched,[])

    def test_r2_free_input_has_committed_context_before_dispatch(self):
        target=self.browser.facts['frames'][0]['target'];target['name']=target['label']='Ordinary';self.browser.facts['frames'][0]['rows']=[target]
        original=self.browser.call
        def checked(name,**args):
            if name=='input':
                self.assertFalse(args['approved'], 'Durable identity must not grant a free input submission authority')
                op=self.engine.store.get('op:'+args['operation'])
                self.assertEqual(op['state'],'submitting');self.assertEqual(op['payload']['binding']['tab'],1)
                self.assertEqual(op['payload']['binding']['editable'],None)
            return original(name,**args)
        self.browser.call=checked
        result=self.call('click',self.target());self.assertTrue(result['ok'],result);self.assertEqual(len(self.browser.dispatched),1)

    def test_warning_occurrences_bind_source_document_and_do_not_inherit_old_acknowledgement(self):
        step={'id':'h1','kind':'activation','element':'e1','submitter':None,'frame':0,'document':'document-1','cancellable':True}
        self.chrome.steps([step],1)
        notices=self.call('notices')['data']['items'];self.assertEqual(len(notices),1)
        self.call('notice_ack',{'operation_id':notices[0]['operation_id']})
        self.chrome.steps([step],1);self.assertEqual(self.call('notices')['data']['total'],0)
        self.browser.facts['frames'][0]['document']='document-2';step['document']='document-2'
        self.chrome.steps([step],1);second=self.call('notices')['data'];self.assertEqual(second['total'],1)
        self.assertNotEqual(second['items'][0]['operation_id'],notices[0]['operation_id'])
        self.chrome.steps([step],1);self.assertEqual(self.call('notices')['data']['total'],1)

    def test_r2_created_tab_identity_commits_before_navigation(self):
        original=self.browser.call
        def checked(name,**args):
            if name=='navigate':
                rows=[op for _,op in self.engine.store.iter_items('op:') if op['app']=='chrome']
                self.assertEqual(rows[-1]['payload']['created_tab']['tab'],2)
                self.assertEqual(rows[-1]['state'],'submitting')
            return original(name,**args)
        self.browser.call=checked
        result=self.call('open',{'url':'https://fixture.test/'});self.assertTrue(result['ok'],result)
        self.assertEqual([name for name,_ in self.browser.dispatched],['open','navigate'])

    def test_storage_admission_refusal_recovers_without_restart_and_prevents_dispatch(self):
        original=self.engine.store.ledger.admit
        with patch.object(self.engine.store.ledger,'admit',side_effect=OSError(errno.ENOSPC,'fixture')):
            result=self.call('click',self.target());self.assertFalse(result['ok']);self.assertEqual(self.browser.dispatched,[])
        approval=self.prepare();self.assertTrue(self.call('submit',approval)['ok'])

    def test_review1_readonly_added_after_prepare_refuses_all_dispatch_kinds(self):
        for kind in ['send','upload','dialog','resumed']:
            with self.subTest(kind=kind):
                approval=self.prepare()
                operation=self.engine.operation(approval['operation_id'])
                if kind=='upload': operation['payload']['input']['verb']='upload'
                if kind=='dialog':
                    operation['payload']['native_dialog']=True
                    operation['payload']['binding']['dialog']={'frame_url':'https://fixture.test/'}
                if kind=='resumed': operation['payload']['resume_kind']='native_submit'
                self.engine.store.write({'chrome:readonly:fixture.test':True},'chrome_test_setup','Owner marks site read-only')
                from aresos_control.common import Refused
                with self.assertRaises(Refused) as error:
                    self.chrome.revalidate(operation)
                self.assertEqual(error.exception.code,'readonly_site')
                self.assertEqual(self.browser.dispatched,[])
                self.engine.store.write({'chrome:readonly:fixture.test':False},'chrome_test_setup','Owner removes read-only restriction')
                self.chrome.revalidate(operation)

    def test_review1_password_failure_refuses_before_any_binding_read(self):
        approval=self.prepare()
        record={'format':1,'entries':[entry(build=self.chrome.qualification.build),entry(build=self.chrome.qualification.build,version='157.0.1.1')]}
        record['entries'][1]['core']['password_exclusion']=False
        self.engine.store.write({'chrome:qualification':record},'chrome_test_setup','Recorded password exclusion failure')
        self.browser.version='157.0.1.2'
        with patch.object(self.browser,'call',side_effect=AssertionError('Must not reread after password qualification failure')):
            result=self.call('submit',approval)
        self.assertFalse(result['ok'],result)
        self.assertEqual(result['error']['code'],'qualification_failed')
        self.assertEqual(self.browser.dispatched,[])


if __name__=='__main__':unittest.main()

class OwnerRules(Operations):
    def gmail(self):
        self.chrome.hosts={**HOSTS,'gmail':['gmail.test']}
        facts=self.browser.facts;facts['url']='https://gmail.test/'
        frame=facts['frames'][0];frame['url']=facts['url']
        frame['adapter']={'scope':'compose-1','scope_role':'dialog','account':'Synthetic account','to':'recipient@example.invalid','cc':'','bcc':'hidden@example.invalid',
                          'subject':'Synthetic subject','text':'Current text','attachments':[],'chat':None,'context':None,'preview':None,'target':'Send'}

    def test_group11_owner_only_exact_parameters_revocation_and_widened_kind(self):
        self.gmail();approval=self.prepare();self.assertTrue(self.call('submit',approval)['ok'])
        args={'command':'allow','operation_id':approval['operation_id']}
        self.assertFalse(self.call('sites',args)['ok'])
        allowed=self.call('sites',args,True);self.assertTrue(allowed['ok'],allowed)
        trusted=self.prepare();self.assertTrue(self.call('submit_trusted',trusted)['ok'])
        self.browser.facts['frames'][0]['adapter']['to']='other@example.invalid'
        changed=self.prepare();self.assertFalse(self.call('submit_trusted',changed)['ok'])
        self.browser.facts['frames'][0]['adapter']['to']='recipient@example.invalid'
        current=self.prepare()
        from aresos_control.chrome.sites import KINDS
        with patch.dict(KINDS['gmail_send'],scope='wider kind'):
            self.assertFalse(self.call('submit_trusted',current)['ok'])
        self.assertTrue(self.call('sites',{'command':'revoke','id':allowed['data']['id']},True)['ok'])
        self.assertFalse(self.call('submit_trusted',current)['ok'])

    def test_conservative_notice_on_every_result_and_independent_bank_restriction(self):
        self.assertTrue(self.call('sites',{'command':'readonly','site':'https://fixture.test/','enabled':True},True)['ok'])
        self.browser.version='999.0.1.0'
        result=self.call('click',self.target())
        self.assertFalse(result['ok']);self.assertEqual(result['error']['code'],'readonly_site')
        self.assertIn('chrome_version_notice',result['pending'])
        self.assertEqual(self.browser.dispatched,[])
