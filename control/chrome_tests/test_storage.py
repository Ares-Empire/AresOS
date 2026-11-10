"""Chrome's own writes use Mail's raw OS/SQLite injector, not mock SQL results."""
import copy
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mail_tests'))
from storage_faults import OSWrites
import test_engine
from aresos_control.engine import Engine
from aresos_control.common import canonical
from state_views import StateViews


class Storage(StateViews,test_engine.Operations):
    # Inherited operation tests also run with the SQLite VFS wrapper installed.
    def restart(self):
        self.engine.close()
        self.engine=Engine(self.root/'state',self.root/'evidence')
        self.chrome=self.engine.adapters['chrome'];self.chrome.bridge=self.browser
        self.chrome.read_owner_hosts=lambda: []
        if self.engine.store.locked:
            reply=self.engine.request({'v':1,'method':'call','action':'control_restore_confirm','arguments':{'confirm':'invalidate earlier approvals'}},True)
            self.assertTrue(reply['ok'],reply)

    def scenario(self,flow,fail_at=None,mode='single',cleanup_at=None):
        self.begin_views(flow)
        if flow=='submit':
            arguments=self.prepare();verb='submit'
        else:
            target=self.browser.facts['frames'][0]['target'];target['name']=target['label']='Ordinary'
            self.browser.facts['frames'][0]['rows']=[target]
            arguments=self.target();verb='click'
        before=[copy.deepcopy(record) for record in self.engine.store.events]
        self.watch_receiver(True)
        injector=OSWrites(fail_at,mode,cleanup_at)
        with injector.wrap(self.engine.store):
            result=self.call(verb,arguments)
            original_points=list(injector.points);cleanup_points=list(injector.cleanup_points)
            self.compare_views('persistent')
        self.compare_views('space_restored')
        injector.points=original_points;injector.cleanup_points=cleanup_points
        self.assertLessEqual(len(self.browser.dispatched),1)
        if result['ok'] and flow=='submit':
            self.assertEqual(result['data']['operation']['state'],'done')
            self.assertEqual(len(self.browser.dispatched),1)
        try:
            self.restart()
        except Exception:
            # A real transaction can require owner recovery; this is never delivery authority.
            raise
        self.script.append({'kind':'restore'})
        self.compare_views('restart')
        self.assertEqual(list(self.engine.store.events)[:len(before)],before)
        count=len(self.browser.dispatched)
        self.engine.request({'v':1,'method':'call','action':'control_pending','arguments':{}})
        if flow=='submit':
            self.call('submit',arguments)
        self.assertEqual(len(self.browser.dispatched),count,'restart/status/replay dispatched again')
        if self.browser.dispatched:
            operations=[op for _,op in self.engine.store.iter_items('op:') if op['app']=='chrome']
            self.assertTrue(operations)
            self.assertFalse(any(op['state']=='reserved' and op['id']==self.browser.dispatched[0][1].get('operation') for op in operations))
        return injector

    def test_chrome_storage_single_persistent_cleanup_pairs_crash_restart_space_restored(self):
        counts={'single':0,'persistent':0,'pairs':0}
        # Each case gets its own committed log; no earlier fault can hide a later writer.
        for flow in ['submit','free']:
            clean=self.scenario(flow)
            self.tearDown();self.setUp()
            for point,label in enumerate(clean.points,1):
                if label.endswith('.close'):
                    continue  # Close is a secondary EIO site, as in Mail's injector.
                for mode in ['single','persistent']:
                    with self.subTest(flow=flow,point=point,label=label,mode=mode):
                        observed=self.scenario(flow,point,mode)
                        self.assertTrue(observed.failed,(flow,point,label))
                        counts[mode]+=1
                    self.tearDown();self.setUp()
                primary=self.scenario(flow,point)
                self.tearDown();self.setUp()
                for secondary,_,_ in primary.cleanup_points:
                    if secondary<=point:continue
                    with self.subTest(flow=flow,point=point,cleanup=secondary):
                        observed=self.scenario(flow,point,'single',secondary)
                        self.assertTrue(observed.failed);counts['pairs']+=1
                    self.tearDown();self.setUp()
        print('Chrome durable-write sweep',counts,flush=True)
