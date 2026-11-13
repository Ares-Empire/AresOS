"""Retained history must not change live warnings or require payload decoding."""
import copy
import unittest
from unittest.mock import patch

import test_engine
from aresos_control import storage


class OperationHeaders(unittest.TestCase):
    def setUp(self):
        self.fixture=test_engine.Operations();self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.store=self.fixture.engine.store
        target=self.fixture.browser.facts['frames'][0]['target']
        target['name']=target['label']='Continue'
        self.assertTrue(self.fixture.call('click',self.fixture.target())['ok'])
        self.template=next(op for _,op in self.store.iter_items('op:'))

    def add(self,label,app='chrome',version=1,state='done'):
        op=copy.deepcopy(self.template)
        op.update(id=op['generation']+':'+label,app=app,state=state)
        if version is None:op.pop('context_version',None)
        else:op['context_version']=version
        self.store.write({'op:'+op['id']:op},'chrome_latency_fixture','Synthetic header selection; no input')
        return 'op:'+op['id'],op

    def test_header_filter_keeps_legacy_and_other_app_rows_and_fresh_changes(self):
        for app in ['chrome','mail','fake']:
            for index,version in enumerate([None,0,False,'',[],{},1,'old',{'v':1}]):
                self.add(app+str(index),app,version,'unknown')
        rows=list(self.store.iter_items('op:'))
        for app in ['chrome','mail','fake']:
            self.assertEqual(list(self.store.iter_operations(app=app)),[(k,v) for k,v in rows if v['app']==app])
            self.assertEqual(list(self.store.iter_operations(exclude_app=app)),[(k,v) for k,v in rows if v['app']!=app])
        legacy=[(k,v) for k,v in self.store.iter_operations(legacy_open=True) if not v.get('context_version')]
        self.assertEqual(legacy,[(k,v) for k,v in rows if not v.get('context_version') and v['state'] in {'reserved','submitting','unknown','partial'}])
        key,op=self.add('changed','chrome',1)
        op.update(app='mail',context_version=0,state='unknown')
        self.store.write({key:op},'chrome_latency_fixture','Changed synthetic row; no input')
        self.assertIn((key,op),list(self.store.iter_operations(app='mail',legacy_open=True)))
        self.assertNotIn(key,dict(self.store.iter_operations(app='chrome')))

    def test_finished_chrome_payloads_are_not_decoded_for_mail_or_legacy_catalogues(self):
        for index in range(10):self.add('finished-'+str(index))
        mail=self.add('open-mail','mail',None,'unknown')
        original=storage.json.loads;decoded=[]
        def loads(value,*args,**kwargs):
            row=original(value,*args,**kwargs)
            if isinstance(row,dict) and row.get('id'):decoded.append(row['id'])
            return row
        with patch.object(storage.json,'loads',loads):
            self.assertEqual(list(self.store.iter_operations(app='mail')),[mail])
            self.assertEqual(list(self.store.iter_operations(exclude_app='chrome')),[mail])
            self.assertEqual(list(self.store.iter_operations(legacy_open=True)),[mail])
        self.assertEqual(decoded,[mail[1]['id']]*3)

    def test_pending_response_equals_unfiltered_queries_with_mixed_live_history(self):
        self.add('completed')
        self.add('unfinished','chrome',1,'unknown')
        self.add('legacy','mail',None,'unknown')
        self.add('mail-current','mail',1,'partial')
        engine=self.fixture.engine
        def request():return engine.request({'v':1,'method':'pending'})
        filtered=request()
        original=self.store.iter_operations
        try:
            self.store.iter_operations=lambda **options:self.store.iter_items('op:')
            unfiltered=request()
        finally:self.store.iter_operations=original
        self.assertEqual(filtered,unfiltered)
        self.assertTrue(filtered['ok'])
        self.assertEqual({row['app'] for row in filtered['data']['items']},{'mail','chrome'})

    def test_header_index_fallback_and_rollback_keep_the_same_rows(self):
        key,op=self.add('rollback','mail',None,'unknown')
        before=list(self.store.iter_operations(app='mail',legacy_open=True))
        self.store.db.execute("UPDATE kv SET v=json_set(v,'$.app','chrome','$.state','done') WHERE k=?",(key,))
        self.assertNotIn(key,dict(self.store.iter_operations(app='mail')))
        self.store.db.rollback()
        self.assertEqual(list(self.store.iter_operations(app='mail',legacy_open=True)),before)
        self.store.db.execute('DROP INDEX operation_headers');self.store.operation_headers=False
        self.assertEqual(list(self.store.iter_operations(app='mail',legacy_open=True)),before)

    def test_low_space_can_decline_optional_index_without_losing_committed_reads(self):
        from aresos_control.common import Refused
        self.store.db.execute('DROP INDEX operation_headers')
        state,evidence=self.store.state_dir,self.store.evidence_dir
        committed=self.store.chrome_state.get('chrome:qualification')
        journal=(evidence/'operations.jsonl').read_bytes()
        self.fixture.engine.close()
        with patch('aresos_control.space.SpaceLedger.admit',side_effect=Refused('storage_limit','Synthetic no space for optional cache')):
            reopened=storage.Store(state,evidence)
        try:
            self.assertFalse(reopened.operation_headers)
            self.assertEqual(reopened.chrome_state.get('chrome:qualification'),committed)
            self.assertEqual(list(reopened.iter_operations(app='mail')),[])
            self.assertEqual((evidence/'operations.jsonl').read_bytes(),journal)
        finally:reopened.close()


class LatencySummary(unittest.TestCase):
    def test_summary_requires_all_calls_and_history_phases_without_duplicate_samples(self):
        import importlib.util
        import json
        from pathlib import Path
        import tempfile
        path=Path(__file__).resolve().parents[1]/'chrome/ci/latency-summary.py'
        spec=importlib.util.spec_from_file_location('latency_summary',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.work') as temporary:
            root=Path(temporary)
            rows=[{'sample':phase+':'+str(i),'phase':phase,'call':call,'milliseconds':10+i} for phase in sorted(module.PHASES) for i in range(20) for call in sorted(module.CALLS)]
            client={'samples':rows,'baseline':'current','privacy':'plain'}
            for file,value in [('chrome-version.txt','Synthetic Chrome'),('runtime-build.txt','synthetic-build')]:
                (root/file).write_text(value)
            (root/'latency-service.jsonl').write_text('\n'.join(json.dumps({'stage':'history_fixture','count':count}) for count in [1000,4000]))
            (root/'latency-client.json').write_text(json.dumps(client))
            result=module.summarize(root)
            self.assertEqual(set(result['phases']),module.PHASES)
            self.assertEqual(result['calls']['read']['client_total'],{'samples':20,'median_ms':19.5,'p95_ms':28})
            self.assertNotIn('compose_binding',result['calls']['read'])
            for bad in [rows[:-1],rows[:-1]+[rows[0]]]:
                (root/'latency-client.json').write_text(json.dumps({**client,'samples':bad}))
                with self.assertRaises(AssertionError):module.summarize(root)
