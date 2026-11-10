"""Actual process cuts at durable boundaries; no browser process is involved."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

import test_engine as fixture
from aresos_control.engine import Engine
from aresos_control.chrome.committed import Projection
from chrome_oracle import history,expectations
from state_views import StateViews


CHILD=r'''
import json,os,sys
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['control','control/chrome_tests']
from test_engine import Browser
from aresos_control.engine import Engine
from aresos_control.chrome.adapter import view_identity
from chrome_oracle import history
root=Path(sys.argv[1]);boundary=sys.argv[2];phase=sys.argv[3]
receiver=root/'receiver.jsonl'
def checkpoint(name):
    if name==boundary and receiver.exists()==(phase=='after_input'):os._exit(73)
with patch('aresos_control.engine.Boundary'):
    engine=Engine(root/'state',root/'evidence')
    chrome=engine.adapters['chrome'];browser=Browser();chrome.bridge=browser;chrome.read_owner_hosts=lambda:[]
    target=browser.facts['frames'][0]['target'];target['name']=target['label']='Ordinary'
    original=browser.call
    def call(name,**args):
        if name=='input':
            records=history(root/'evidence');operation=records['rows'].get('op:'+args['operation'],{})
            fd=os.open(receiver,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
            os.write(fd,(json.dumps({'operation':args['operation'],'authorized':True,'committed_submitting':operation.get('state')=='submitting'})+'\n').encode())
            os.fsync(fd);os.close(fd)
        return original(name,**args)
    browser.call=call;engine.store.checkpoint=checkpoint
    frame=browser.facts['frames'][0]
    reference={'session':browser.session,'tab':1,'frame':0,'document':frame['document'],'view':view_identity(browser.facts),'element':'e1'}
    result=engine.request({'v':1,'method':'call','action':'chrome_click','arguments':{'reference':reference,'expected':dict(target)}})
    print(result)
    engine.close()
'''


class CrashCuts(StateViews,unittest.TestCase):
    setUp=fixture.Operations.setUp
    tearDown=fixture.Operations.tearDown

    def test_s11_actual_process_cuts_before_and_after_input_keep_every_committed_view(self):
        cuts=[(name,phase) for name in ['journal_appended','sqlite_prepared','sqlite_committed','journal_committed']
              for phase in ['before_input','after_input']]+[('chrome_before_dispatch','before_input')]
        for boundary,phase in cuts:
            with self.subTest(boundary=boundary,phase=phase):
                self.engine.close()
                result=subprocess.run([sys.executable,'-c',CHILD,str(self.root),boundary,phase],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,73,result.stdout+result.stderr)
                receiver=self.root/'receiver.jsonl'
                arrivals=[json.loads(line) for line in receiver.read_text().splitlines()] if receiver.exists() else []
                self.assertEqual(len(arrivals),1 if phase=='after_input' else 0)
                committed=history(self.root/'evidence')
                expected=expectations([],arrivals,committed)
                # Inspect the raw crash state before startup can replay even a
                # local prepared completion. SQLite is deliberately unopened.
                projection=Projection(self.engine.store)
                self.assertEqual({row['id']:row['state'] for _,row,_ in projection.rows('op:')},expected['operations'])
                self.engine=Engine(self.root/'state',self.root/'evidence')
                self.chrome=self.engine.adapters['chrome'];self.chrome.bridge=self.browser;self.chrome.read_owner_hosts=lambda:[]
                if self.engine.store.locked:
                    result=self.engine.request({'v':1,'method':'call','action':'control_restore_confirm',
                        'arguments':{'confirm':'invalidate earlier approvals'}},True)
                    self.assertTrue(result['ok'],result)
                self.begin_views('process_cut');self.script.append({'kind':'restore'});self.receiver_log=arrivals
                self.compare_views('restart')
                self.assertEqual(self.browser.dispatched,[])
            self.tearDown();self.setUp()
        print('Chrome actual process cuts: 9; raw committed status and all public views checked',flush=True)
