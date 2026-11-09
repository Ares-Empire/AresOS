"""Chrome writer inventory and fault sweep; expectations come from the scenario log."""
import ast
import copy
import io
import json
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mail_tests'))
from storage_faults import OSWrites
import test_engine as fixture
from test_policy import entry
from aresos_control.common import Refused


class Writers(fixture.Operations):
    def prepare_flow(self, flow):
        # Preparation is outside the injected interval: each writer is reached from a healthy committed input.
        if flow in {'allow','revoke','trusted'}:
            fixture.OwnerRules.gmail(self)
            first=self.prepare();self.call('submit',first)
            if flow!='allow':allowed=self.call('sites',{'command':'allow','operation_id':first['operation_id']},True)['data']['id']
            if flow=='allow':run=lambda:self.call('sites',{'command':'allow','operation_id':first['operation_id']},True)
            elif flow=='revoke':run=lambda:self.call('sites',{'command':'revoke','id':allowed},True)
            else:
                second=self.prepare();run=lambda:self.call('submit_trusted',second)
        elif flow=='readonly':run=lambda:self.call('sites',{'command':'readonly','site':'https://fixture.test/'},True)
        elif flow=='qualification':
            path=self.root/'qualification.json';path.write_text(json.dumps({'format':1,'entries':[entry(build=self.chrome.qualification.build),entry(build=self.chrome.qualification.build,version='158.0.1.0',channel='beta')]}))
            run=lambda:self.chrome.qualification.accept(path,verifier=lambda _:None)
        elif flow=='delivery':
            candidate=json.dumps({'format':1,'entries':[entry(build=self.chrome.qualification.build),entry(build=self.chrome.qualification.build,version='158.0.1.0',channel='beta')]}).encode()
            def run():
                with patch('urllib.request.urlopen',return_value=io.BytesIO(candidate)):
                    return self.chrome.qualification.refresh(now=1000000000,verifier=lambda _:None)
        elif flow=='observation':
            step={'id':'h1','kind':'activation_unknown','element':'e1','submitter':None,'frame':0,'document':'document-1','cancellable':False}
            run=lambda:self.chrome.event({'event':'held_step','session':self.browser.session,'tab':1,'step':step})
        elif flow in {'activation','stopped'}:
            step={'id':'h1','kind':'activation' if flow=='activation' else 'native_submit','element':'e1','submitter':None,'frame':0,'document':'document-1','cancellable':True}
            run=lambda:self.chrome.steps([step],1)
        elif flow=='acknowledgement':
            self.chrome.steps([{'id':'h1','kind':'activation','element':'e1','submitter':None,'frame':0,'document':'document-1','cancellable':True}],1)
            notice=next(value for _,value in self.engine.store.iter_items('notice:') if value['app']=='chrome')
            run=lambda:self.call('notice_ack',{'operation_id':notice['id']})
        elif flow=='release':
            self.prepare();run=lambda:self.chrome.event({'event':'released','session':self.browser.session,'tab':1})
        elif flow=='upload_copy':
            from aresos_control.chrome.uploads import copy_for_browser,release
            data=b'synthetic upload';key=self.engine.blobs.put(data,'caller_import')
            self.chrome.upload_dir=self.root/'uploads'
            file={'sha256':key,'size':len(data),'name':'fixture.txt','real_path':'/fixture.txt'}
            def run():
                _,path=copy_for_browser(self.chrome,file);release(self.chrome,path)
        else:raise AssertionError(flow)
        self.browser.dispatched.clear()
        return run

    def sweep_case(self,flow,fail_at=None,mode='single',cleanup_at=None):
        run=self.prepare_flow(flow);injector=OSWrites(fail_at,mode,cleanup_at)
        with injector.wrap(self.engine.store):
            try:run()
            except Exception:
                if not injector.failed:raise
        # The only scenario with permission to send is trusted. Configuration and checks cannot dispatch.
        sends=[item for item in self.browser.dispatched if item[0] in {'input','resume','dialog'}]
        self.assertLessEqual(len(sends),1 if flow=='trusted' else 0)
        self.engine.close()
        from aresos_control.engine import Engine
        self.engine=Engine(self.root/'state',self.root/'evidence');self.chrome=self.engine.adapters['chrome'];self.chrome.bridge=self.browser
        self.chrome.read_owner_hosts=lambda:[]
        if self.engine.store.locked:
            reply=self.engine.request({'v':1,'method':'call','action':'control_restore_confirm','arguments':{'confirm':'invalidate earlier approvals'}},True)
            self.assertTrue(reply['ok'],reply)
        before=len(self.browser.dispatched)
        self.engine.pending(resolve_checks=False)
        self.assertEqual(len(self.browser.dispatched),before,'restart or disclosure replayed an effect')
        from chrome_oracle import committed,warnings
        expected=warnings(committed(self.root/'state',self.root/'evidence'))
        observed=set();cursor=None
        while True:
            result=self.call('notices',{'cursor':cursor} if cursor else {})
            self.assertTrue(result['ok'],result)
            observed.update(item['operation_id'] for item in result['data']['items'])
            cursor=result['data']['cursor']
            if not cursor:break
        self.assertEqual(observed,expected,('independent committed-record oracle',flow,fail_at,mode))
        return injector

    def test_every_chrome_durable_writer_single_persistent_cleanup_pairs_restart_space_restored(self):
        counts={'single':0,'persistent':0,'pairs':0}
        flows=['readonly','allow','revoke','trusted','qualification','delivery','observation','activation','stopped','acknowledgement','release','upload_copy']
        for flow in flows:
            clean=self.sweep_case(flow);self.tearDown();self.setUp()
            for point,label in enumerate(clean.points,1):
                if label.endswith('.close'):continue
                for mode in ['single','persistent']:
                    with self.subTest(flow=flow,point=point,label=label,mode=mode):
                        observed=self.sweep_case(flow,point,mode);self.assertTrue(observed.failed);counts[mode]+=1
                    self.tearDown();self.setUp()
                primary=self.sweep_case(flow,point);self.tearDown();self.setUp()
                for secondary,_,_ in primary.cleanup_points:
                    if secondary<=point:continue
                    with self.subTest(flow=flow,point=point,cleanup=secondary):
                        observed=self.sweep_case(flow,point,'single',secondary);self.assertTrue(observed.failed);counts['pairs']+=1
                    self.tearDown();self.setUp()
        print('Chrome full writer surface',counts,flush=True)
