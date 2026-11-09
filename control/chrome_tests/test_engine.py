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
        if name in {'facts','read'}: return copy.deepcopy(self.facts)
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
        self.assertTrue(self.call('submit',approval)['ok']);self.assertEqual(len(self.browser.dispatched),1)

    def test_group3_current_draft_bound_even_without_prior_fill_and_across_frames(self):
        approval=self.prepare()
        state=approval['description']['untrusted_content']['page_state']
        self.assertEqual(state['editable'][0]['fields'][0]['value'],'Existing draft')
        self.assertIn("isn't visible to the tool",approval['question'])
        # The extension receives the committed binding verbatim, independent of prior unrelated approvals.
        self.call('submit',approval)
        self.assertEqual(self.browser.dispatched[0][1]['binding']['editable'],state['editable'])

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
                op=self.engine.store.get('op:'+args['operation'])
                self.assertEqual(op['state'],'submitting');self.assertEqual(op['payload']['binding']['tab'],1)
                self.assertEqual(op['payload']['binding']['editable'],None)
            return original(name,**args)
        self.browser.call=checked
        result=self.call('click',self.target());self.assertTrue(result['ok'],result);self.assertEqual(len(self.browser.dispatched),1)

    def test_storage_admission_refusal_recovers_without_restart_and_prevents_dispatch(self):
        original=self.engine.store.ledger.admit
        with patch.object(self.engine.store.ledger,'admit',side_effect=OSError(errno.ENOSPC,'fixture')):
            result=self.call('click',self.target());self.assertFalse(result['ok']);self.assertEqual(self.browser.dispatched,[])
        approval=self.prepare();self.assertTrue(self.call('submit',approval)['ok'])


if __name__=='__main__':unittest.main()
