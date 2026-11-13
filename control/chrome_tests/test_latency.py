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


    def test_optional_header_migration_preserves_real_reserved_cancellation_space(self):
        import shutil
        from aresos_control.space import SAFETY_FLOOR
        target=self.fixture.browser.facts['frames'][0]['target']
        target['name']=target['label']='Send'
        approval=self.fixture.prepare()
        held=self.store.ledger.held;self.assertGreater(held,0)
        state,evidence=self.store.state_dir,self.store.evidence_dir
        self.store.db.execute('DROP INDEX operation_headers')
        self.fixture.engine.close()
        free=held+SAFETY_FLOOR+128*1024-1
        usage=shutil._ntuple_diskusage(1024**3,1024**3-free,free)
        with patch('aresos_control.space.shutil.disk_usage',return_value=usage):
            reopened=storage.Store(state,evidence)
        try:
            self.assertEqual(reopened.ledger.held,held)
            self.assertFalse(reopened.operation_headers,'Optional index spent space reserved for cancellation')
            operation=reopened.chrome_state.get('op:'+approval['operation_id'])
            self.assertEqual(operation['state'],'reserved')
        finally:reopened.close()


    def test_namespace_range_matches_literal_substr_with_unicode_wildcards_and_nuls(self):
        import json
        prefixes=['','op:','mail:','%','_','ä','🙂','\ud7ff','a\0','\U0010ffff','z\U0010ffff']
        for prefix in prefixes:
            for suffix in ['','x','%_','ä','🙂','\0after','\U0010ffff']:
                key=prefix+suffix
                self.store.db.execute('INSERT OR REPLACE INTO kv VALUES (?,?)',(key,json.dumps({'marker':key})))
        for key in [None,b'op:binary-key']:
            self.store.db.execute('INSERT INTO kv VALUES (?,?)',(key,json.dumps({'marker':'non-text-key'})))
        for prefix in prefixes:
            expected=[(k,json.loads(v)) for k,v in self.store.db.execute('SELECT k,v FROM kv WHERE substr(k,1,?)=? ORDER BY k',(len(prefix),prefix))]
            self.assertEqual(list(self.store.iter_items(prefix)),expected,repr(prefix))

    def test_native_hash_enumeration_matches_nested_references_and_current_updates(self):
        from aresos_control.retention import hashes,OPEN
        key,op=self.add('references','chrome',1,'done')
        op['context']={'sha256':'top','list':[{'wire_sha256':'wire','notsha256':'ignored'},['plain',{'sha256':{'sha256':'nested'}}]],'number_sha256':42,'bool_sha256':True,'ü_sha256':'unicode'}
        self.store.write({key:op},'chrome_latency_fixture','Synthetic nested reference test')
        expected={value for _,item in self.store.iter_items('op:') for value in hashes(item)}
        self.assertEqual(set(self.store.operation_hashes()),expected)
        op['state']='unknown';self.store.write({key:op},'chrome_latency_fixture','Synthetic fresh state')
        self.assertIn(key,dict(self.store.iter_operations(states=OPEN)))
        self.store.db.execute("UPDATE kv SET v=json_set(v,'$.state','done') WHERE k=?",(key,))
        self.assertNotIn(key,dict(self.store.iter_operations(states=OPEN)))
        self.store.db.rollback();self.assertIn(key,dict(self.store.iter_operations(states=OPEN)))
        self.store.write({key:None},'chrome_latency_fixture','Synthetic retired reference')
        self.assertEqual(set(self.store.operation_hashes()),set())

    def test_empty_blob_stores_do_not_decode_completed_history_during_daemon_expiry(self):
        for index in range(10):self.add('completed-expiry-'+str(index))
        original=self.store.iter_items
        def iter_items(prefix):
            self.assertNotEqual(prefix,'op:','Completed payloads decoded during expiry')
            yield from original(prefix)
        with patch.object(self.store,'iter_items',iter_items),patch.object(self.store,'operation_hashes',side_effect=AssertionError('No old file needs pins')):
            self.fixture.engine.expire()

    def old_blob(self,blob_store,data):
        import os,time
        key=blob_store.put(data,origin='caller_import');path=blob_store.directory/key
        os.utime(path,(time.time()-172800,)*2)
        return key,path

    def test_completed_operation_keeps_both_old_blob_stores_and_archival_releases_them(self):
        from aresos_control import retention
        engine=self.fixture.engine
        blob,path=self.old_blob(engine.blobs,b'Fixture import retained by a completed operation')
        wire,wire_path=self.old_blob(engine.adapters['mail'].wires,b'Fixture wire retained by a completed operation')
        key,op=self.add('completed-files','chrome',1,'done')
        op['payload']['nested']=[{'sha256':blob},[{'wire_sha256':wire}]]
        self.store.write({key:op},'chrome_latency_fixture','Synthetic retained completed references')
        engine.expire();self.assertTrue(path.exists());self.assertTrue(wire_path.exists())
        self.store.write({key:None},'chrome_latency_fixture','Synthetic archive removes only current reference')
        engine.expire();self.assertFalse(path.exists());self.assertFalse(wire_path.exists())

    def test_active_operation_protects_old_composition_and_import_metadata(self):
        import time
        engine=self.fixture.engine
        key,op=self.add('active-files','chrome',1,'unknown')
        blob,path=self.old_blob(engine.blobs,b'Fixture active import')
        op['payload'].update(composition={'id':'pinned-composition'},file={'sha256':blob})
        comp={'id':'pinned-composition','created_at':time.time()-172800,'sha256':blob}
        meta={'sha256':blob}
        self.store.write({key:op,'mail:composition:pinned-composition':comp,'blob:fixture-active':meta},'chrome_latency_fixture','Synthetic active composition/reference')
        self.store.db.execute("UPDATE retained SET created=? WHERE k='blob:fixture-active'",(time.time()-172800,));self.store.db.commit()
        engine.expire()
        self.assertEqual(self.store.get('mail:composition:pinned-composition'),comp)
        self.assertEqual(self.store.get('blob:fixture-active'),meta);self.assertTrue(path.exists())

    def test_malformed_state_still_refuses_expiry_before_deleting_old_files(self):
        engine=self.fixture.engine
        key,op=self.add('bad-state','chrome',1,'done')
        _,path=self.old_blob(engine.blobs,b'Fixture candidate beside malformed operation')
        self.store.db.execute("UPDATE kv SET v=json_set(v,'$.state',json('{}')) WHERE k=?",(key,))
        with self.assertRaises(TypeError):engine.expire()
        self.assertTrue(path.exists())

    def test_reference_enumeration_failure_precedes_every_blob_unlink(self):
        import errno
        engine=self.fixture.engine
        key,first=self.old_blob(engine.blobs,b'Fixture first candidate')
        _,second=self.old_blob(engine.blobs,b'Fixture second candidate')
        def broken():
            yield key
            raise OSError(errno.EIO,'Synthetic reference read fault')
        with patch.object(self.store,'operation_hashes',broken):
            with self.assertRaises(OSError):engine.expire()
        self.assertTrue(first.exists());self.assertTrue(second.exists())


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
            rows=[{'sample':phase+':'+str(i),'phase':phase,'call':call,'milliseconds':(525 if call in module.INPUTS else 0)+10+i} for phase in sorted(module.PHASES) for i in range(20) for call in sorted(module.CALLS)]
            client={'samples':rows,'baseline':'current','privacy':'plain'}
            for file,value in [('chrome-version.txt','Synthetic Chrome'),('runtime-build.txt','synthetic-build')]:
                (root/file).write_text(value)
            internal=[{'sample':row['sample'],'call':row['call'],'stage':'post_input_observation_wait','milliseconds':525} for row in rows if row['call'] in module.INPUTS]
            internal += [{'stage':'history_fixture','count':count} for count in [1000,4000]]
            (root/'latency-service.jsonl').write_text('\n'.join(map(json.dumps,internal)))
            (root/'latency-client.json').write_text(json.dumps(client))
            result=module.summarize(root)
            self.assertEqual(set(result['phases']),module.PHASES)
            self.assertEqual(result['calls']['read']['client_total'],{'samples':20,'median_ms':19.5,'p95_ms':28})
            self.assertNotIn('compose_binding',result['calls']['read'])
            for bad in [rows[:-1],rows[:-1]+[rows[0]]]:
                (root/'latency-client.json').write_text(json.dumps({**client,'samples':bad}))
                with self.assertRaises(AssertionError):module.summarize(root)


class LatencyGate(unittest.TestCase):
    def stats(self,values):
        import statistics
        return {'samples':len(values),'median_ms':statistics.median(values),'p95_ms':sorted(values)[18]}

    def setUp(self):
        import importlib.util
        from pathlib import Path
        path=Path(__file__).resolve().parents[1]/'chrome/ci/latency-check.py'
        spec=importlib.util.spec_from_file_location('latency_gate',path)
        self.gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.gate)
        def measurement(runtime,active):
            phases={};pairs=[]
            for phase in self.gate.PHASES:
                group={}
                for call in self.gate.CALLS:
                    value=active*(1 if phase=='fresh' else 2)
                    values=[value]*18+[value*1.2]*2
                    wait=525 if call in self.gate.INPUTS else 0
                    group[call]={'client_total':self.stats([wait+v for v in values])}
                    for stage in ['service_total','service_without_bridge','bridge_round_trip','extension_total','session_rule_add','session_rule_remove','compose_binding','clipboard_hooks']:
                        group[call][stage]=self.stats([1]*18+[2]*2)
                    if wait:
                        group[call]['post_input_observation_wait']=self.stats([wait]*20)
                        group[call]['client_without_wait']=self.stats(values)
                        pairs.extend({'sample':phase+':'+str(i),'phase':phase,'call':call,'client_ms':wait+v,'wait_ms':wait} for i,v in enumerate(values))
                phases[phase]=group
            return {'runtime':runtime,'privacy':'plain','chrome':'Synthetic Chrome','phases':phases,'input_samples':pairs}
        self.current=measurement('current',20);self.old=measurement('ab7aba92',15)
        self.reference={'privacy':'plain','current':copy.deepcopy(self.current),'baseline':copy.deepcopy(self.old)}
        self.targets={'format':1,'status':'lead-approved','ceilings_ms':{call:{'median_ms':100 if call not in self.gate.INPUTS else 650,'p95_ms':150 if call not in self.gate.INPUTS else 750} for call in self.gate.CALLS}}

    def check(self):return self.gate.check(self.current,self.old,self.reference,self.targets)

    def paired(self,measurement,phase,call,values=None,waits=None):
        rows=[row for row in measurement['input_samples'] if row['phase']==phase and row['call']==call]
        for index,row in enumerate(rows):
            value=values[index] if values is not None else row['client_ms']-row['wait_ms']
            wait=waits[index] if waits is not None else row['wait_ms']
            row.update(client_ms=wait+value,wait_ms=wait)
        group=measurement['phases'][phase][call]
        for stage,numbers in [('client_total',[r['client_ms'] for r in rows]),('post_input_observation_wait',[r['wait_ms'] for r in rows]),('client_without_wait',[max(0,r['client_ms']-r['wait_ms']) for r in rows])]:
            group[stage]=self.stats(numbers)

    def scale(self,measurement,factor):
        for phase,group in measurement['phases'].items():
            for call,details in group.items():
                if call in self.gate.INPUTS:
                    rows=[r for r in measurement['input_samples'] if r['phase']==phase and r['call']==call]
                    self.paired(measurement,phase,call,[(r['client_ms']-r['wait_ms'])*factor for r in rows])
                else:
                    for stat in ['median_ms','p95_ms']:details['client_total'][stat]*=factor

    def test_accepts_nominal_and_common_runner_noise(self):
        self.assertTrue(self.check()['passed'])
        self.scale(self.current,1.8);self.scale(self.old,1.8)
        self.assertTrue(self.check()['passed'])

    def test_clear_regression_in_each_call_and_history_phase_fails(self):
        original=copy.deepcopy(self.current)
        for call in self.gate.CALLS:
            for phase in self.gate.PHASES:
                self.current=copy.deepcopy(original)
                if call in self.gate.INPUTS:
                    rows=[r for r in self.current['input_samples'] if r['phase']==phase and r['call']==call]
                    self.paired(self.current,phase,call,[r['client_ms']-r['wait_ms']+200 for r in rows])
                else:
                    for stat in ['median_ms','p95_ms']:self.current['phases'][phase][call]['client_total'][stat]+=200
                result=self.check();self.assertFalse(result['passed'],(phase,call))
                self.assertIn((phase,call),[(row['phase'],row['call']) for row in result['failures']])

    def test_nominal_ceilings_apply_to_warm_histories_even_without_relative_regression(self):
        for value in [self.current,self.reference['current']]:
            value['phases']['history-4000']['read']['client_total'].update(median_ms=200,p95_ms=240)
        result=self.check();self.assertFalse(result['passed'])
        row=next(row for row in result['failures'] if row['phase']=='history-4000' and row['call']=='read')
        self.assertTrue(row['target_miss']);self.assertFalse(row['regression'])

    def test_correlated_wait_tail_cannot_hide_fivefold_warm_work_regression(self):
        phase='history-4000';call='fill'
        self.paired(self.reference['current'],phase,call,[40]*20,[525]*20)
        self.paired(self.current,phase,call,[200]*18+[40]*2,[525]*18+[750]*2)
        result=self.check();self.assertFalse(result['passed'])
        row=next(row for row in result['measurements'] if row['phase']==phase and row['call']==call)
        self.assertEqual(row['paired_work_ms'],{'median_ms':200,'p95_ms':200})

    def test_tail_spike_alone_does_not_fail_but_shortened_safety_wait_does(self):
        self.current['phases']['fresh']['read']['client_total']['p95_ms']=1000
        self.assertTrue(self.check()['passed'])
        self.paired(self.current,'fresh','fill',waits=[400]*20)
        with self.assertRaises(AssertionError):self.check()

    def test_missing_stage_phase_or_unset_lead_targets_cannot_pass(self):
        for change in ['stage','phase','targets']:
            original=copy.deepcopy(self.current)
            if change=='stage':del self.current['phases']['fresh']['fill']['session_rule_remove']
            elif change=='phase':del self.current['phases']['history-4000']
            else:self.targets['status']='awaiting-lead'
            with self.assertRaises((AssertionError,KeyError)):self.check()
            self.current=original

    def test_corrupt_percentiles_missing_timings_and_impossible_totals_refuse(self):
        original=copy.deepcopy(self.current)
        for change in ['order','stage','short','pair','nan']:
            self.current=copy.deepcopy(original)
            if change=='order':self.current['phases']['fresh']['read']['client_total'].update(median_ms=10000,p95_ms=1)
            elif change=='stage':self.current['phases']['fresh']['read']['service_total']={'samples':20}
            elif change=='short':self.current['phases']['fresh']['fill']['client_total'].update(median_ms=1,p95_ms=2)
            elif change=='pair':self.current['input_samples'][0]['client_ms']=1
            else:self.current['phases']['fresh']['read']['service_total']['median_ms']=float('nan')
            with self.assertRaises((AssertionError,KeyError)):self.check()
