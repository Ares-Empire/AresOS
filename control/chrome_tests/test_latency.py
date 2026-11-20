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

    def test_header_filter_and_rollback_keep_the_same_rows(self):
        key,op=self.add('rollback','mail',None,'unknown')
        before=list(self.store.iter_operations(app='mail',legacy_open=True))
        self.store.db.execute("UPDATE kv SET v=json_set(v,'$.app','chrome','$.state','done') WHERE k=?",(key,))
        self.assertNotIn(key,dict(self.store.iter_operations(app='mail')))
        self.store.db.rollback()
        self.assertEqual(list(self.store.iter_operations(app='mail',legacy_open=True)),before)

    def no_header_index(self,store):
        # Final fixes F1: the optional header index is gone; a reopen adds none.
        names={row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertNotIn('operation_headers',names)

    def test_low_space_reopen_keeps_committed_reads(self):
        from aresos_control.common import Refused
        state,evidence=self.store.state_dir,self.store.evidence_dir
        committed=self.store.chrome_state.get('chrome:qualification')
        journal=(evidence/'operations.jsonl').read_bytes()
        self.fixture.engine.close()
        with patch('aresos_control.space.SpaceLedger.admit',side_effect=Refused('storage_limit','Synthetic no space for optional cache')):
            reopened=storage.Store(state,evidence)
        try:
            self.no_header_index(reopened)
            self.assertEqual(reopened.chrome_state.get('chrome:qualification'),committed)
            self.assertEqual(list(reopened.iter_operations(app='mail')),[])
            self.assertEqual((evidence/'operations.jsonl').read_bytes(),journal)
        finally:reopened.close()


    def test_tight_reopen_preserves_real_reserved_cancellation_space(self):
        import shutil
        from aresos_control.space import SAFETY_FLOOR
        target=self.fixture.browser.facts['frames'][0]['target']
        target['name']=target['label']='Send'
        approval=self.fixture.prepare()
        held=self.store.ledger.held;self.assertGreater(held,0)
        state,evidence=self.store.state_dir,self.store.evidence_dir
        self.fixture.engine.close()
        free=held+SAFETY_FLOOR+128*1024-1
        usage=shutil._ntuple_diskusage(1024**3,1024**3-free,free)
        with patch('aresos_control.space.shutil.disk_usage',return_value=usage):
            reopened=storage.Store(state,evidence)
        try:
            self.assertEqual(reopened.ledger.held,held)
            self.no_header_index(reopened)
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
        op['context']={'sha256':'top','list':[{'wire_sha256':'wire','notsha256':'ignored'},['plain',{'sha256':{'sha256':'nested'}}]],'number_sha256':42,'bool_sha256':True,'ü_sha256':'unicode','nul\0wire_sha256':'nul-reference','sha256\0not-a-suffix':'ignored-nul','unicode🙂\0_sha256':'unicode-nul-reference'}
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

    def test_namespace_prefixes_keep_legacy_sqlite_encoding_behavior(self):
        import json,sqlite3
        from types import SimpleNamespace
        prefixes=['','op:','ä','🙂','\ud7ff','\U0010ffff','z\U0010ffff','a\0']
        for encoding in ['UTF-8','UTF-16le','UTF-16be']:
            database=sqlite3.connect(':memory:')
            try:
                database.execute("PRAGMA encoding='"+encoding+"'")
                database.execute('CREATE TABLE kv(k TEXT PRIMARY KEY,v TEXT NOT NULL)')
                for prefix in prefixes:
                    for suffix in ['','x','\0','🙂','\U0010ffff']:
                        key=prefix+suffix
                        database.execute('INSERT OR REPLACE INTO kv VALUES (?,?)',(key,json.dumps(key)))
                store=SimpleNamespace(db=database)
                for prefix in prefixes:
                    expected=[(k,json.loads(v)) for k,v in database.execute('SELECT k,v FROM kv WHERE substr(k,1,?)=? ORDER BY k',(len(prefix),prefix))]
                    self.assertEqual(list(storage.Store.iter_items(store,prefix)),expected,(encoding,repr(prefix)))
            finally:database.close()

    def test_native_hash_keys_match_python_with_nuls_in_each_sqlite_encoding(self):
        import json,sqlite3
        from types import SimpleNamespace
        from aresos_control.retention import hashes
        operation={'nested':[{'wire\0_sha256':'nul','sha256\0ignored':'ignore','ü🙂_sha256':'unicode','sha256':'root','normal_sha256':'normal','container_sha256':[{'wire_sha256':'nested'}]}]}
        for encoding in ['UTF-8','UTF-16le','UTF-16be']:
            database=sqlite3.connect(':memory:')
            try:
                database.execute("PRAGMA encoding='"+encoding+"'")
                database.execute('CREATE TABLE kv(k TEXT PRIMARY KEY,v TEXT NOT NULL)')
                database.execute('INSERT INTO kv VALUES (?,?)',('op:encoding-probe',json.dumps(operation,ensure_ascii=False)))
                self.assertEqual(set(storage.Store.operation_hashes(SimpleNamespace(db=database))),set(hashes(operation)),encoding)
            finally:database.close()

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

    def test_completed_operation_nul_suffix_reference_preserves_old_blob(self):
        engine=self.fixture.engine
        blob,path=self.old_blob(engine.blobs,b'Fixture retained by a nested NUL-key reference')
        key,op=self.add('completed-nul-reference','chrome',1,'done')
        op['payload']['nested']=[{'evidence\0wire_sha256':blob}]
        self.store.write({key:op},'chrome_latency_fixture','Synthetic retained NUL-key reference')
        self.assertIn(blob,set(self.store.operation_hashes()))
        engine.expire();self.assertTrue(path.exists())

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


def sync_rows(rows,fsyncs=2,commits=2):
    """What latency-profile.py emits per sample besides the timings: the journal's fsyncs and control.sqlite's commits."""
    return [stage for row in rows for stage in [
        {'sample':row['sample'],'call':row['call'],'stage':'journal_fsync','milliseconds':.1,'count':fsyncs},
        {'sample':row['sample'],'call':row['call'],'stage':'sqlite_commit','count':commits}]]


def store_record(root,fstype='tmpfs',end=('/var/lib/aresos-tools','/var/lib/aresos-operation-evidence')):
    """run.sh's latency-store.py record: both store directories and their mount, with the end record for those in end."""
    import json
    directories={directory:{'mount_point':directory,'fstype':fstype,'source':'latency-store','options':'rw,size=524288k,mode=755,uid=1001',
                            'size_bytes':512*1024*1024,'used_bytes_start':0,**({'used_bytes_end':40*1024*1024} if directory in end else {})}
                 for directory in ['/var/lib/aresos-tools','/var/lib/aresos-operation-evidence']}
    (root/'latency-store.json').write_text(json.dumps({'directories':directories}))


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
            self.assertEqual(module.SAMPLES,json.loads((path.parent/'latency-targets.json').read_text())['samples_per_call'])
            rows=[{'sample':phase+':'+str(i),'phase':phase,'call':call,'milliseconds':(525 if call in module.INPUTS else 0)+10+i} for phase in sorted(module.PHASES) for i in range(module.SAMPLES) for call in sorted(module.CALLS)]
            client={'samples':rows,'baseline':'current','privacy':'plain'}
            for file,value in [('chrome-version.txt','Synthetic Chrome'),('runtime-build.txt','synthetic-build')]:
                (root/file).write_text(value)
            internal=[{'sample':row['sample'],'call':row['call'],'stage':'post_input_observation_wait','milliseconds':525} for row in rows if row['call'] in module.INPUTS]
            internal += [{'stage':'history_fixture','count':count} for count in [1000,4000]]
            internal += sync_rows(rows);store_record(root)
            (root/'latency-service.jsonl').write_text('\n'.join(map(json.dumps,internal)))
            (root/'latency-client.json').write_text(json.dumps(client))
            result=module.summarize(root)
            self.assertEqual(set(result['phases']),module.PHASES)
            # 60 samples of 10..69 ms: the median between the 30th and 31st,
            # the p95 the 57th (index 56).
            self.assertEqual(module.SAMPLES,60)
            self.assertEqual(result['calls']['read']['client_total'],{'samples':60,'median_ms':39.5,'p95_ms':66})
            self.assertEqual(result['samples_per_call'],60)
            self.assertEqual(result['notes'][0],'60 samples per call and history phase; owner think time absent.')
            self.assertNotIn('compose_binding',result['calls']['read'])
            for bad in [rows[:-1],rows[:-1]+[rows[0]]]:
                (root/'latency-client.json').write_text(json.dumps({**client,'samples':bad}))
                with self.assertRaises(AssertionError):module.summarize(root)


    def test_gate60b_the_old_runtime_summary_takes_20_at_positions_0_to_19(self):
        import importlib.util
        import json
        from pathlib import Path
        import tempfile
        path=Path(__file__).resolve().parents[1]/'chrome/ci/latency-summary.py'
        spec=importlib.util.spec_from_file_location('latency_summary',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        def write(root,runtime,positions):
            rows=[{'sample':phase+':'+str(i),'phase':phase,'call':call,'milliseconds':(525 if call in module.INPUTS else 0)+10+i} for phase in sorted(module.PHASES) for i in positions for call in sorted(module.CALLS)]
            internal=[{'sample':row['sample'],'call':row['call'],'stage':'post_input_observation_wait','milliseconds':525} for row in rows if row['call'] in module.INPUTS]
            internal+=[{'stage':'history_fixture','count':count} for count in [1000,4000]]
            internal+=sync_rows(rows);store_record(root)
            (root/'latency-service.jsonl').write_text('\n'.join(map(json.dumps,internal)))
            (root/'latency-client.json').write_text(json.dumps({'samples':rows,'baseline':runtime,'privacy':'plain'}))
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.work') as temporary:
            root=Path(temporary)
            for file,value in [('chrome-version.txt','Synthetic Chrome'),('runtime-build.txt','synthetic-build')]:(root/file).write_text(value)
            write(root,'ab7aba92',range(20))
            result=module.summarize(root)
            self.assertEqual((result['runtime'],result['samples_per_call']),('ab7aba92',20))
            self.assertEqual(result['calls']['read']['client_total']['samples'],20)
            self.assertEqual(result['notes'][0],'20 samples per call and history phase; owner think time absent.')
            self.assertEqual(sorted({row['sample'] for row in result['input_samples'] if row['phase']=='fresh'}),sorted('fresh:'+str(i) for i in range(20)))
            # The old runtime at 60 or at later positions, and the current runtime at 20, refuse.
            for runtime,positions in [('ab7aba92',range(60)),('ab7aba92',range(40,60)),('current',range(20)),('unknown',range(20))]:
                with self.subTest(runtime=runtime,positions=positions):
                    write(root,runtime,positions)
                    with self.assertRaises(AssertionError):module.summarize(root)


    def test_ci_noise_summary_carries_sync_counts_and_refuses_a_store_off_tmpfs(self):
        # Brief 20-ci-noise: the summary sums each sample's fsyncs and commits over its
        # requests, keeps them out of the timing stages, and states where the store was.
        import importlib.util
        import json
        from pathlib import Path
        import tempfile
        path=Path(__file__).resolve().parents[1]/'chrome/ci/latency-summary.py'
        spec=importlib.util.spec_from_file_location('latency_summary',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        rows=[{'sample':phase+':'+str(i),'phase':phase,'call':call,'milliseconds':(525 if call in module.INPUTS else 0)+10+i} for phase in sorted(module.PHASES) for i in range(module.SAMPLES) for call in sorted(module.CALLS)]
        timings=[{'sample':row['sample'],'call':row['call'],'stage':'post_input_observation_wait','milliseconds':525} for row in rows if row['call'] in module.INPUTS]
        timings+=[{'stage':'history_fixture','count':count} for count in [1000,4000]]
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.work') as temporary:
            root=Path(temporary)
            for file,value in [('chrome-version.txt','Synthetic Chrome'),('runtime-build.txt','synthetic-build')]:(root/file).write_text(value)
            (root/'latency-client.json').write_text(json.dumps({'samples':rows,'baseline':'current','privacy':'plain'}))
            def summarize(internal,fstype='tmpfs',**end):
                store_record(root,fstype,**end)
                (root/'latency-service.jsonl').write_text('\n'.join(map(json.dumps,timings+internal)))
                return module.summarize(root)
            # approval_to_done's first sample makes two requests: its counts add up.
            target=[row for row in rows if row['sample']=='fresh:0' and row['call']=='approval_to_done']
            result=summarize(sync_rows(rows,4,4)+sync_rows(target,2,1))
            self.assertEqual(result['sync_counts']['fresh']['approval_to_done'],{'journal_fsync':{'samples':60,'min':4,'max':6},'sqlite_commit':{'samples':60,'min':4,'max':5}})
            self.assertEqual(result['sync_counts']['history-4000']['read']['sqlite_commit'],{'samples':60,'min':4,'max':4})
            self.assertNotIn('sqlite_commit',result['phases']['fresh']['read'])
            self.assertEqual(result['phases']['fresh']['read']['journal_fsync']['samples'],60)
            self.assertEqual(result['store']['/var/lib/aresos-tools']['fstype'],'tmpfs')
            # A missing count, or a store that wasn't on a tmpfs, refuses.
            for internal,fstype in [(sync_rows(rows)[:-1],'tmpfs'),(sync_rows(rows)[1:],'tmpfs'),(sync_rows(rows),'ext4'),(sync_rows(rows),'overlay')]:
                with self.subTest(rows=len(internal),fstype=fstype),self.assertRaises(AssertionError):summarize(internal,fstype)
            # So does a store whose end-of-run check didn't run, for either directory (review nit 4).
            for end in [(),('/var/lib/aresos-tools',),('/var/lib/aresos-operation-evidence',)]:
                with self.subTest(end=end),self.assertRaisesRegex(AssertionError,'end-of-run'):summarize(sync_rows(rows),end=end)


class LatencyGate(unittest.TestCase):
    def test_round3_measured_cost_removal_probe_fails_the_production_ci_command(self):
        import json
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        root=Path(__file__).resolve().parents[2]
        ci=root/'control/chrome/ci'
        reference=json.loads((ci/'latency-reference.json').read_text())
        fixture=json.loads((root/'control/chrome_tests/fixtures/latency-round3-cost.json').read_text())
        self.assertEqual(reference['measurement_run'],'43502970342')
        self.assertEqual(fixture['source_run'],'43490400410')
        for profile,observed in fixture['profiles'].items():
            with self.subTest(profile=profile),tempfile.TemporaryDirectory(dir=root/'.work') as temporary:
                directory=Path(temporary)
                accepted=reference['profiles'][profile]
                current=copy.deepcopy(accepted['current'])
                self.assertEqual(current['chrome'],observed['chrome'])
                # The old runtime keeps the reference's 20 samples at its positions.
                baseline=directory/'baseline.json';baseline.write_text(json.dumps(self.counted(accepted['baseline'],self.old_samples)))
                source=directory/'current.json';source.write_text(json.dumps(self.counted(self.repeated(current),self.samples)))
                command=[sys.executable,'-B',str(ci/'latency-check.py'),str(source),str(baseline),str(ci/'latency-reference.json'),str(ci/'latency-targets.json')]
                nominal=subprocess.run(command,capture_output=True,text=True,timeout=30)
                self.assertEqual(nominal.returncode,0,nominal.stdout+nominal.stderr)
                group=current['phases']['history-4000']
                for call,metric in observed['client_total'].items():
                    group[call]['client_total']=copy.deepcopy(metric)
                by_identity={(row['sample'],row['call']):row for row in observed['input_samples']}
                for row in current['input_samples']:
                    if row['phase']=='history-4000':row.update(by_identity[(row['sample'],row['call'])])
                for call in self.gate.INPUTS:
                    rows=[row for row in current['input_samples'] if row['phase']=='history-4000' and row['call']==call]
                    for stage,values in [('client_total',[row['client_ms'] for row in rows]),('post_input_observation_wait',[row['wait_ms'] for row in rows]),('client_without_wait',[max(0,row['client_ms']-row['wait_ms']) for row in rows])]:
                        group[call][stage]=self.stats(values)
                source.write_text(json.dumps(self.counted(self.repeated(current),self.samples)))
                restored=subprocess.run(command,capture_output=True,text=True,timeout=30)
                self.assertEqual(restored.returncode,1,restored.stdout+restored.stderr)
                result=json.loads((directory/'latency-check.json').read_text())
                self.assertFalse(result['passed'])
                failures={(row['phase'],row['call']) for row in result['failures']}
                self.assertEqual(failures,{('history-4000',call) for call in self.gate.CALLS})

    def stats(self,values):
        # The production summary's arithmetic (its median and p95 rule).
        return self.summary.summary(values)

    def repeated(self,measurement):
        # The frozen reference has 20 samples per call; taking each sample
        # three times gives the 60 the gate requires of the current runtime with
        # the same median and p95 (the 30th/31st of 60 are the 10th/11th of 20,
        # the 57th of 60 the 19th of 20).
        factor,rest=divmod(self.samples,self.reference_samples)
        self.assertEqual((factor,rest),(3,0))
        value=copy.deepcopy(measurement)
        for group in value['phases'].values():
            for stages in group.values():
                for block in stages.values():block['samples']*=factor
        value['input_samples']=[{**row,'sample':row['phase']+':'+str(int(row['sample'].split(':')[1])+copy_index*self.reference_samples)}
                                for copy_index in range(factor) for row in measurement['input_samples']]
        return value

    def setUp(self):
        import importlib.util
        import json
        from pathlib import Path
        ci=Path(__file__).resolve().parents[1]/'chrome/ci'
        modules={}
        for name in ['latency-check','latency-summary']:
            spec=importlib.util.spec_from_file_location(name.replace('-','_'),ci/(name+'.py'))
            modules[name]=importlib.util.module_from_spec(spec);spec.loader.exec_module(modules[name])
        self.gate,self.summary=modules['latency-check'],modules['latency-summary']
        targets=json.loads((ci/'latency-targets.json').read_text())
        self.samples,self.old_samples,self.reference_samples=targets['samples_per_call'],targets['old_runtime_samples_per_call'],targets['measurement_samples_per_call']
        self.build(self.samples)

    def measurement(self,runtime,active,samples):
        phases={};pairs=[]
        for phase in self.gate.PHASES:
            group={}
            for call in self.gate.CALLS:
                value=active*(1 if phase=='fresh' else 2)
                values=[value]*(samples-2)+[value*1.2]*2
                wait=525 if call in self.gate.INPUTS else 0
                group[call]={'client_total':self.stats([wait+v for v in values])}
                for stage in ['service_total','service_without_bridge','bridge_round_trip','extension_total','session_rule_add','session_rule_remove','compose_binding','clipboard_hooks']:
                    group[call][stage]=self.stats([1]*(samples-2)+[2]*2)
                if wait:
                    group[call]['post_input_observation_wait']=self.stats([wait]*samples)
                    group[call]['client_without_wait']=self.stats(values)
                    pairs.extend({'sample':phase+':'+str(i),'phase':phase,'call':call,'client_ms':wait+v,'wait_ms':wait} for i,v in enumerate(values))
            phases[phase]=group
        return self.counted({'runtime':runtime,'privacy':'plain','chrome':'Synthetic Chrome','phases':phases,'input_samples':pairs},samples)

    def counted(self,measurement,samples,fsyncs=2,commits=2):
        # The summary's sync counts: the same number on every sample, as measured.
        value=copy.deepcopy(measurement)
        value['sync_counts']={phase:{call:{'journal_fsync':{'samples':samples,'min':fsyncs,'max':fsyncs},'sqlite_commit':{'samples':samples,'min':commits,'max':commits}}
                                     for call in self.gate.CALLS} for phase in self.gate.PHASES}
        return value

    def build(self,samples):
        # The current runtime takes `samples`, the old runtime and the
        # reference keep their own 20.
        self.current=self.measurement('current',20,samples);self.old=self.measurement('ab7aba92',15,self.old_samples)
        self.reference={'privacy':'plain','current':self.measurement('current',20,self.reference_samples),'baseline':self.measurement('ab7aba92',15,self.reference_samples)}
        self.targets={'format':1,'status':'lead-approved','samples_per_call':samples,'old_runtime_samples_per_call':self.old_samples,'measurement_samples_per_call':self.reference_samples,'baseline':'ab7aba92',
                      'ceilings_ms':{call:{'median_ms':100 if call not in self.gate.INPUTS else 650,'p95_ms':150 if call not in self.gate.INPUTS else 750} for call in self.gate.CALLS}}

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

    def test_ci_noise_an_added_fsync_or_sqlite_commit_fails_the_sync_gate(self):
        # Brief 20-ci-noise: with the store on a tmpfs the timings no longer see a sync's
        # disk cost, so its count must. One more fsync or commit than the old runtime, in
        # any phase and call and on any sample, fails with every timing nominal.
        result=self.check()
        self.assertTrue(result['passed']);self.assertEqual(result['sync_failures'],[])
        self.assertEqual(len(result['sync_counts']),len(self.gate.PHASES)*len(self.gate.CALLS)*2)
        for counter in ['journal_fsync','sqlite_commit']:
            for phase,call in [('fresh','read'),('history-1000','asking_click'),('history-4000','approval_to_done')]:
                for every in [True,False]:
                    with self.subTest(counter=counter,phase=phase,call=call,every_sample=every):
                        self.build(self.samples)
                        block=self.current['sync_counts'][phase][call][counter];block['max']+=1
                        if every:block['min']+=1
                        result=self.check()
                        self.assertFalse(result['passed']);self.assertEqual(result['failures'],[])
                        self.assertEqual([(row['phase'],row['call'],row['counter'],row['current_max'],row['ab7aba92_max']) for row in result['sync_failures']],[(phase,call,counter,3,2)])
        # Fewer syncs than the old runtime, or as many, pass, also where its counts vary.
        self.build(self.samples)
        self.current['sync_counts']['fresh']['fill']['journal_fsync'].update(min=1,max=1)
        self.old['sync_counts']['history-4000']['navigate']['sqlite_commit'].update(min=2,max=3)
        self.current['sync_counts']['history-4000']['navigate']['sqlite_commit'].update(min=2,max=3)
        self.assertTrue(self.check()['passed'])
        # Where the old runtime's counts vary, a sync added on every sample may raise only
        # the lowest count. That fails too (review nit 2).
        self.current['sync_counts']['history-4000']['navigate']['sqlite_commit'].update(min=3,max=3)
        result=self.check()
        self.assertFalse(result['passed']);self.assertEqual(result['failures'],[])
        self.assertEqual([(row['phase'],row['call'],row['counter'],row['current_min'],row['ab7aba92_min'],row['current_max'],row['ab7aba92_max']) for row in result['sync_failures']],
                         [('history-4000','navigate','sqlite_commit',3,2,3,3)])
        # Missing or malformed counts on either side can't pass.
        for side in ['current','old']:
            for name,mutate in [('missing',lambda value:value.pop('sync_counts')),
                                ('missing counter',lambda value:value['sync_counts']['fresh']['read'].pop('sqlite_commit')),
                                ('sample count',lambda value:value['sync_counts']['fresh']['read']['journal_fsync'].update(samples=1)),
                                ('order',lambda value:value['sync_counts']['fresh']['read']['journal_fsync'].update(min=3,max=2)),
                                ('type',lambda value:value['sync_counts']['fresh']['read']['journal_fsync'].update(max=2.0))]:
                with self.subTest(side=side,malformed=name):
                    self.build(self.samples);mutate(getattr(self,side))
                    with self.assertRaises((AssertionError,KeyError)):self.check()

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
        self.paired(self.reference['current'],phase,call,[40]*self.reference_samples,[525]*self.reference_samples)
        self.paired(self.current,phase,call,[200]*(self.samples-2)+[40]*2,[525]*(self.samples-2)+[750]*2)
        result=self.check();self.assertFalse(result['passed'])
        row=next(row for row in result['measurements'] if row['phase']==phase and row['call']==call)
        self.assertEqual(row['paired_work_ms'],{'median_ms':200,'p95_ms':200})

    def test_tail_spike_alone_does_not_fail_but_shortened_safety_wait_does(self):
        # Over the reference threshold (62 ms here) but under the 150 ms ceiling:
        # runner noise against the old measurement still needs both to cross.
        self.current['phases']['fresh']['read']['client_total']['p95_ms']=140
        result=self.check();self.assertTrue(result['passed'],result['failures'])
        row=next(row for row in result['measurements'] if row['phase']=='fresh' and row['call']=='read')
        self.assertGreater(row['paired_work_ms']['p95_ms'],row['regression_threshold_ms']['p95_ms'])
        self.paired(self.current,'fresh','fill',waits=[400]*self.samples)
        with self.assertRaises(AssertionError):self.check()

    def real_profile(self,profile='plain'):
        import json
        from pathlib import Path
        ci=Path(__file__).resolve().parents[1]/'chrome/ci'
        reference=json.loads((ci/'latency-reference.json').read_text())['profiles'][profile]
        targets=json.loads((ci/'latency-targets.json').read_text())
        return self.counted(self.repeated(reference['current']),self.samples),self.counted(reference['baseline'],self.old_samples),reference,targets

    def test_final_f4_a_median_or_p95_over_a_lead_ceiling_fails_alone(self):
        # The final review's case: the lead's ceilings, the measured reference,
        # and one history phase changed. read 35/60, asking_click 60/100, and
        # navigate 400/450 (linux-tools, 2026-11-20: chrome_go waits for the
        # page; its reference was re-taken, so its thresholds lie above these).
        for call,median,p95 in [('read',50,55),('asking_click',65,70),('read',30,65),('asking_click',50,110),('navigate',410,420),('navigate',390,460)]:
            with self.subTest(call=call,median=median,p95=p95):
                current,baseline,reference,targets=self.real_profile()
                self.assertTrue(self.gate.check(current,baseline,reference,targets)['passed'])
                current['phases']['history-4000'][call]['client_total'].update(median_ms=median,p95_ms=p95)
                result=self.gate.check(current,baseline,reference,targets)
                self.assertFalse(result['passed'])
                self.assertEqual(result['failures'],[{'phase':'history-4000','call':call,'regression':False,'target_miss':True}])
                self.assertIn('median or its p95 is over the ceiling',result['policy'])

    def test_final_f4_reference_comparison_still_needs_median_and_p95_to_cross(self):
        current,baseline,reference,targets=self.real_profile()
        # asking_click: its reference threshold lies under its ceiling, so a
        # median shift between them is runner noise to the comparison and passes.
        # (navigate carried this case until its reference was re-taken from run
        # 44705819383, linux-tools, 2026-11-20: its thresholds now lie above its ceilings.)
        accepted=reference['current']['phases']['history-4000']['asking_click']['client_total']
        median=accepted['median_ms']*1.5+10+1
        self.assertLess(median,targets['ceilings_ms']['asking_click']['median_ms'])
        current['phases']['history-4000']['asking_click']['client_total'].update(median_ms=median,p95_ms=max(median,accepted['p95_ms']))
        result=self.gate.check(current,baseline,reference,targets)
        self.assertTrue(result['passed'],result['failures'])
        row=next(row for row in result['measurements'] if row['phase']=='history-4000' and row['call']=='asking_click')
        self.assertGreater(row['paired_work_ms']['median_ms'],row['regression_threshold_ms']['median_ms'])
        self.assertLessEqual(row['paired_work_ms']['p95_ms'],row['regression_threshold_ms']['p95_ms'])

    def test_navigates_ceiling_and_reference_follow_chrome_go(self):
        # The lead (linux-tools, 2026-11-20, package 28a step 4): chrome_go returns
        # once the page has arrived and been quiet for 150 ms, so navigate's
        # ceiling is 400/450 and its reference is re-taken from run 44705819383
        # at the reference's own 20 positions. The old runtime and every other
        # call keep run 43502970342's.
        import json
        from pathlib import Path
        ci=Path(__file__).resolve().parents[1]/'chrome/ci'
        targets=json.loads((ci/'latency-targets.json').read_text())
        document=json.loads((ci/'latency-reference.json').read_text())
        self.assertEqual(targets['ceilings_ms']['navigate'],{'median_ms':400,'p95_ms':450})
        self.assertIn('linux-tools, 2026-11-20',targets['navigate_basis'])
        self.assertEqual((document['measurement_run'],document['navigate_measurement']['measurement_run']),('43502970342','44705819383'))
        for profile in ['plain','audit']:
            current=document['profiles'][profile]['current']
            self.assertEqual(current['calls']['navigate'],current['phases']['fresh']['navigate'])
            for phase,group in current['phases'].items():
                with self.subTest(profile=profile,phase=phase):
                    self.assertEqual({stage['samples'] for stage in group['navigate'].values()},{self.reference_samples})
                    total=group['navigate']['client_total']
                    # The waits alone are about 250 ms; the measured call sits under the new ceilings.
                    self.assertTrue(250<total['median_ms']<=total['p95_ms']<targets['ceilings_ms']['navigate']['median_ms'],total)

    def test_gate60_three_slow_samples_of_sixty_pass_and_a_fourth_fails(self):
        # The lead (mac-aresos-control, 2026-11-14, after run 43603381599): 60
        # samples per call and history phase, for the current runtime in both
        # profiles (the old runtime keeps 20, after run 43613647256). A
        # p95 over its ceiling then takes four slow samples; with the old 20 it
        # took two. The ceilings and "median or p95" stay; the frozen reference
        # keeps its 20.
        import json
        from pathlib import Path
        targets=json.loads((Path(__file__).resolve().parents[1]/'chrome/ci/latency-targets.json').read_text())
        self.assertEqual((targets['samples_per_call'],targets['measurement_samples_per_call']),(60,20))
        self.assertIn('mac-aresos-control, 2026-11-14, after run 43603381599',targets['samples_basis'])
        self.assertEqual(self.summary.SAMPLES,60)
        for samples,slow,passes in [(60,3,True),(60,4,False),(20,1,True),(20,2,False)]:
            with self.subTest(samples=samples,slow=slow):
                self.build(samples)
                # navigate through its client total, fill through its paired samples
                self.current['phases']['fresh']['navigate']['client_total']=self.stats([20]*(samples-slow)+[400]*slow)
                self.paired(self.current,'fresh','fill',[20]*(samples-slow)+[600]*slow)
                result=self.check()
                self.assertEqual(result['samples_per_call'],samples)
                expected=[] if passes else [{'phase':'fresh','call':call,'regression':False,'target_miss':True} for call in ['fill','navigate']]
                self.assertEqual(result['failures'],expected)
                self.assertEqual(result['passed'],passes)

    def test_gate60_new_measurements_take_the_lead_count_and_the_reference_keeps_its_own(self):
        # A measurement with the reference's 20 no longer passes, nor does a
        # reference with the new count: each is checked against its own number.
        current=copy.deepcopy(self.current)
        self.current=self.measurement('current',20,self.reference_samples)
        with self.assertRaises(AssertionError):self.check()
        self.current=current;self.assertTrue(self.check()['passed'])
        self.reference['baseline']=self.measurement('ab7aba92',15,self.samples)
        with self.assertRaises(AssertionError):self.check()

    def test_gate60b_the_runner_factor_reads_the_old_runtime_at_the_reference_positions(self):
        # The lead (mac-aresos-control, 2026-11-14, after run 43613647256): the
        # old runtime only feeds the runner-noise ratio and must match the
        # frozen 20-sample reference, so it takes 20 at the reference's sample
        # positions; the current runtime stays at 60.
        import json
        from pathlib import Path
        targets=json.loads((Path(__file__).resolve().parents[1]/'chrome/ci/latency-targets.json').read_text())
        self.assertEqual((targets['samples_per_call'],targets['old_runtime_samples_per_call'],targets['measurement_samples_per_call']),(60,20,20))
        self.assertIn('mac-aresos-control, 2026-11-14, after run 43613647256',targets['old_runtime_samples_basis'])
        self.assertIn('mac-aresos-control, 2026-11-14, after run 43603381599',targets['samples_basis'])
        self.assertEqual((self.summary.SAMPLES,self.summary.OLD_RUNTIME_SAMPLES),(60,20))
        self.assertEqual((self.summary.samples_for('current'),self.summary.samples_for('ab7aba92')),(60,20))
        for profile in ['plain','audit']:
            with self.subTest(profile=profile):
                current,baseline,reference,targets=self.real_profile(profile)
                positions={phase:sorted(row['sample'] for row in reference['baseline']['input_samples'] if row['phase']==phase and row['call']=='fill') for phase in self.gate.PHASES}
                self.assertEqual(positions,{phase:sorted(phase+':'+str(index) for index in range(20)) for phase in self.gate.PHASES})
                # Like for like: the reference's own old runtime gives a factor of exactly 1.
                result=self.gate.check(current,baseline,reference,targets)
                self.assertTrue(result['passed'],result['failures'])
                self.assertEqual(result['old_runtime_samples_per_call'],20)
                self.assertEqual({row['runner_factor'] for row in result['measurements']},{1.0})
                # The same 20 samples later in a longer history (positions 40
                # to 59) and the old runtime at 60 both refuse.
                shifted=copy.deepcopy(baseline)
                for row in shifted['input_samples']:row['sample']=row['phase']+':'+str(int(row['sample'].split(':')[1])+40)
                with self.assertRaisesRegex(AssertionError,'reference sample positions'):self.gate.check(current,shifted,reference,targets)
                with self.assertRaises(AssertionError):self.gate.check(current,self.repeated(baseline),reference,targets)
                # The current runtime still needs its 60.
                with self.assertRaises(AssertionError):self.gate.check(baseline|{'runtime':'current'},baseline,reference,targets)
        # An old-runtime count that leaves the reference's is refused outright.
        self.targets['old_runtime_samples_per_call']=60;self.old=self.measurement('ab7aba92',15,60)
        with self.assertRaisesRegex(AssertionError,'frozen reference count'):self.check()

    def test_missing_stage_phase_or_unset_lead_targets_cannot_pass(self):
        for change in ['stage','phase','targets']:
            original=copy.deepcopy(self.current)
            if change=='stage':del self.current['phases']['fresh']['fill']['session_rule_remove']
            elif change=='phase':del self.current['phases']['history-4000']
            else:self.targets['status']='awaiting-lead'
            with self.assertRaises((AssertionError,KeyError)):self.check()
            self.current=original

    def test_sparse_expiry_and_navigation_diagnostics_keep_required_samples_strict(self):
        self.current['phases']['fresh']['read']['daemon_expiry_inside_sample']={'samples':1,'median_ms':2,'p95_ms':2}
        self.current['phases']['fresh']['navigate']['clipboard_hooks']={'samples':self.samples-2,'median_ms':1,'p95_ms':2}
        self.assertTrue(self.check()['passed'])
        original=copy.deepcopy(self.current)
        for call,stage in [('read','service_total'),('free_click','clipboard_hooks')]:
            self.current=copy.deepcopy(original)
            self.current['phases']['fresh'][call][stage]['samples']=self.samples-1
            with self.assertRaises(AssertionError):self.check()
        self.current=copy.deepcopy(original)
        self.current['phases']['fresh']['read']['daemon_expiry_inside_sample']['samples']=0
        with self.assertRaises(AssertionError):self.check()

    def test_corrupt_percentiles_missing_timings_and_impossible_totals_refuse(self):
        original=copy.deepcopy(self.current)
        for change in ['order','stage','short','pair','nan']:
            self.current=copy.deepcopy(original)
            if change=='order':self.current['phases']['fresh']['read']['client_total'].update(median_ms=10000,p95_ms=1)
            elif change=='stage':self.current['phases']['fresh']['read']['service_total']={'samples':self.samples}
            elif change=='short':self.current['phases']['fresh']['fill']['client_total'].update(median_ms=1,p95_ms=2)
            elif change=='pair':self.current['input_samples'][0]['client_ms']=1
            else:self.current['phases']['fresh']['read']['service_total']['median_ms']=float('nan')
            with self.assertRaises((AssertionError,KeyError)):self.check()


class MainFixStorageStages(unittest.TestCase):
    """Main fix H5: the CI profile times the store's writes and the journal's fsyncs per marked sample."""

    def setUp(self):
        import importlib.util
        import json
        import os
        from pathlib import Path
        import tempfile
        from types import SimpleNamespace
        ROOT=Path(__file__).resolve().parents[2]
        self.temporary=tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome');self.addCleanup(self.temporary.cleanup)
        root=Path(self.temporary.name)
        spec=importlib.util.spec_from_file_location('latency_profile',ROOT/'control/chrome/ci/latency-profile.py')
        self.profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.profile)
        self.profile.MARKER=root/'latency-marker.json';self.profile.OUT=root/'latency-service.jsonl'
        self.addCleanup(setattr,storage,'os',os)
        journal=open(root/'journal','ab');self.addCleanup(journal.close)
        import sqlite3
        db=sqlite3.connect(root/'control.sqlite');self.addCleanup(db.close)
        db.execute('CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)')
        self.json,self.os=json,os
        def write(changes,action,summary):
            # Two journal fsyncs and two SQLite commits per write, as the real store's write does.
            for _ in range(2):storage.os.fsync(journal.fileno())
            for _ in range(2):
                with db:db.execute('INSERT OR REPLACE INTO kv VALUES (?,?)',('x',action))
            db.execute('SELECT v FROM kv').fetchall()
            return 'written'
        store=SimpleNamespace(write=write,db=db,state_dir=root)
        bridge=SimpleNamespace(connection=None,call=lambda name,**arguments:{'ok':True},on_event=lambda value:None)
        def request(value,admin=False):
            for _ in range(value.get('writes',0)):self.engine.store.write({'x':1},'chrome_fixture','synthetic')
            return {'ok':True}
        self.engine=SimpleNamespace(adapters={'chrome':SimpleNamespace(bridge=bridge)},request=request,expire=lambda:None,store=store)
        self.daemon=SimpleNamespace(engine=self.engine)

    def rows(self,stage):
        if not self.profile.OUT.exists():return []
        return [self.json.loads(line) for line in self.profile.OUT.read_text().splitlines() if self.json.loads(line).get('stage')==stage]

    def test_profile_refuses_the_store_connections_exclusive_lock(self):
        database=self.engine.store.db
        self.assertEqual(database.execute('PRAGMA locking_mode=EXCLUSIVE').fetchone()[0],'exclusive')
        with self.assertRaisesRegex(AssertionError,'exclusive'):
            self.profile.install(self.daemon)
        self.assertEqual(database.execute('PRAGMA locking_mode=NORMAL').fetchone()[0],'normal')
        self.profile.install(self.daemon)

    def test_store_write_and_journal_fsync_are_summed_per_marked_sample_only(self):
        self.profile.install(self.daemon)
        self.assertIsNot(storage.os,self.os);self.assertEqual(storage.os.SEEK_END,self.os.SEEK_END)
        # Work outside a marked sample is not counted and does not leak into the next one.
        self.engine.store.write({'x':1},'chrome_fixture','synthetic');self.engine.request({'writes':3})
        self.assertEqual(self.rows('store_write'),[]);self.assertEqual(self.rows('journal_fsync'),[]);self.assertEqual(self.rows('sqlite_commit'),[])
        self.profile.MARKER.write_text(self.json.dumps({'sample':'fresh:0','call':'approval_to_done'}))
        self.engine.request({'writes':2})
        self.profile.MARKER.write_text(self.json.dumps({'sample':'fresh:1','call':'read'}))
        self.engine.request({'writes':0})
        writes=self.rows('store_write');fsyncs=self.rows('journal_fsync')
        self.assertEqual([(row['sample'],row['call']) for row in writes],[('fresh:0','approval_to_done'),('fresh:1','read')])
        self.assertEqual([(row['sample'],row['call'],row['count']) for row in fsyncs],[('fresh:0','approval_to_done',4),('fresh:1','read',0)])
        # Brief 20-ci-noise: SQLite's commits are counted the same way, as counts with no timing.
        commits=self.rows('sqlite_commit')
        self.assertEqual([(row['sample'],row['call'],row['count']) for row in commits],[('fresh:0','approval_to_done',4),('fresh:1','read',0)])
        for row in commits:self.assertNotIn('milliseconds',row)
        self.assertGreater(writes[0]['milliseconds'],0);self.assertGreaterEqual(writes[0]['milliseconds'],fsyncs[0]['milliseconds'])
        self.assertEqual(writes[1]['milliseconds'],0);self.assertEqual(fsyncs[1]['milliseconds'],0)
        for row in writes+fsyncs:self.assertNotIn('command',row)
        # Every marked sample carries both stages, so the summary's per-call
        # sample counts stay complete for the gate's strict validation.
        totals=self.rows('service_total')
        self.assertEqual(len(totals),len(writes),2)

    def test_the_latency_pair_keeps_its_harness_streams_off_the_store_disk(self):
        from pathlib import Path
        ROOT=Path(__file__).resolve().parents[2]
        pair=(ROOT/'control/chrome/ci/latency-pair.sh').read_text()
        self.assertIn('--tmpfs /scratch:rw,size=256m,mode=1777 -e INSTALL_MODE=policy -e LATENCY_PROBE=true',pair)
        run=(ROOT/'control/chrome/ci/run.sh').read_text()
        self.assertIn('if test "${LATENCY_PROBE:-}" = true && test -d /scratch; then FIXTURE_LOG_DIR=/scratch; fi',run)
        self.assertIn('FIXTURE_LOG_DIR="$FIXTURE_LOG_DIR" python3 control/chrome/ci/service.py > "$FIXTURE_LOG_DIR/service.txt" 2>&1 &',run)
        self.assertIn('cp "$FIXTURE_LOG_DIR/service.txt" "$FIXTURE_LOG_DIR/browser-boundary.jsonl" /out/',run)
        self.assertLess(run.index('wait "$service_pid"'),run.index('cp "$FIXTURE_LOG_DIR/service.txt"'))
        service=(ROOT/'control/chrome/ci/service.py').read_text()
        self.assertIn("open(os.environ.get('FIXTURE_LOG_DIR','/out')+'/browser-boundary.jsonl','a',buffering=1)",service)
        self.assertNotIn("open('/out/browser-boundary.jsonl'",service)
        # The store keeps its own directories (run.sh mounts a tmpfs over them for the latency
        # pair): nothing redirects them to /scratch.
        self.assertIn("'state_dir':'/var/lib/aresos-tools'",service)
        self.assertNotIn('/scratch',service)

    def test_ci_noise_the_profile_counts_a_real_store_write_s_fsyncs_and_commits(self):
        # The real Store, not a stand-in: one write is two journal fsyncs and two
        # control.sqlite commits (its events row, then its state), and only inside a sample.
        from types import SimpleNamespace
        from aresos_control.storage import Store
        root=__import__('pathlib').Path(self.temporary.name)
        store=Store(root/'state',root/'evidence');self.addCleanup(store.close)
        self.engine.store=store
        def request(value,admin=False):
            for index in range(value.get('writes',0)):store.write({'latency:'+str(index):{'value':index}},'chrome_fixture','Synthetic')
            return {'ok':True}
        self.engine.request=request
        self.profile.install(self.daemon)
        self.engine.request({'writes':1})
        self.profile.MARKER.write_text(self.json.dumps({'sample':'fresh:0','call':'fill'}))
        self.engine.request({'writes':3})
        self.assertEqual([(row['sample'],row['count']) for row in self.rows('journal_fsync')],[('fresh:0',6)])
        self.assertEqual([(row['sample'],row['count']) for row in self.rows('sqlite_commit')],[('fresh:0',6)])
        self.assertEqual(store.get('latency:2'),{'value':2})

    def test_ci_noise_the_commit_count_is_what_commits_an_autocommit_write_included(self):
        # Review nit 3: the probe counts the commits control.sqlite records (its change
        # counter), not the COMMIT statements sent. A write in autocommit mode commits, and
        # syncs, without one; a COMMIT that changed nothing syncs nothing.
        import sqlite3
        db=self.engine.store.db
        def request(value,admin=False):
            if value.get('autocommit'):
                db.isolation_level=None
                try:db.execute("INSERT OR REPLACE INTO kv VALUES ('auto','1')")
                finally:db.isolation_level=''
            # The sqlite3 module opens no transaction before DDL: it commits on its own.
            if value.get('ddl'):db.execute('CREATE TABLE '+value['ddl']+' (x)')
            if value.get('unchanged'):
                with db:db.execute("DELETE FROM kv WHERE k='missing'")
            if value.get('nested'):
                with db:db.execute("INSERT OR REPLACE INTO kv VALUES ('outer','1')")
                self.engine.request({'autocommit':True,'ddl':'inner'})
                with db:db.execute("INSERT OR REPLACE INTO kv VALUES ('outer','2')")
            return {'ok':True}
        self.engine.request=request
        self.profile.install(self.daemon)
        self.profile.MARKER.write_text(self.json.dumps({'sample':'fresh:0','call':'fill'}))
        for value in [{'autocommit':True},{'ddl':'extra'},{'unchanged':True}]:self.engine.request(value)
        self.assertEqual([row['count'] for row in self.rows('sqlite_commit')],[1,1,0])
        # A nested request's commits are its own and the outer request's aren't counted twice.
        self.profile.MARKER.write_text(self.json.dumps({'sample':'fresh:1','call':'fill'}))
        self.engine.request({'nested':True})
        self.assertEqual([row['count'] for row in self.rows('sqlite_commit') if row['sample']=='fresh:1'],[2,2])
        # The probe refuses what it can't count: a control.sqlite replaced under it, or a
        # database in WAL mode, whose change counter need not move with each commit.
        replacement=sqlite3.connect(self.engine.store.state_dir/'replacement.sqlite')
        replacement.execute('CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)');replacement.close()
        self.os.replace(self.engine.store.state_dir/'replacement.sqlite',self.engine.store.state_dir/'control.sqlite')
        with self.assertRaisesRegex(AssertionError,'replaced'):self.engine.request({})
        wal=self.engine.store.state_dir/'wal';wal.mkdir()
        database=sqlite3.connect(wal/'control.sqlite');self.addCleanup(database.close)
        database.execute('PRAGMA journal_mode=WAL');database.execute('CREATE TABLE kv (k TEXT)');database.commit()
        self.engine.store.state_dir=wal
        with self.assertRaisesRegex(AssertionError,'rollback-journal'):self.profile.install(self.daemon)

    def test_ci_noise_the_store_is_on_a_tmpfs_for_both_runtimes_and_the_artifact_says_so(self):
        # run.sh mounts a tmpfs over both store directories before anything writes to them,
        # for both runtimes (the pair copies ci/ into the old tree), and records the mounts.
        from pathlib import Path
        ROOT=Path(__file__).resolve().parents[2]
        run=(ROOT/'control/chrome/ci/run.sh').read_text()
        service=(ROOT/'control/chrome/ci/service.py').read_text()
        pair=(ROOT/'control/chrome/ci/latency-pair.sh').read_text()
        self.assertIn('cp -R control/chrome/ci/. "$latency_tree/control/chrome/ci/"',pair)
        mount='mount -t tmpfs -o rw,nosuid,nodev,noexec,size=512m,mode=0755,uid="$(id -u aresos-tools)" latency-store "$store_dir"'
        self.assertIn('for store_dir in /var/lib/aresos-tools /var/lib/aresos-operation-evidence; do\n    '+mount,run)
        self.assertIn("'state_dir':'/var/lib/aresos-tools','evidence_dir':'/var/lib/aresos-operation-evidence'",service)
        # Only the latency probe mounts it, before the harness or the service writes.
        self.assertIn('if test "${LATENCY_PROBE:-}" = true; then\n  for store_dir',run)
        self.assertLess(run.index(mount),run.index('node control/chrome/ci/baseline.mjs'))
        self.assertLess(run.index('latency-store.py start /out/latency-store.json'),run.index('python3 control/chrome/ci/service.py'))
        self.assertLess(run.index('wait "$service_pid"'),run.index('latency-store.py end /out/latency-store.json'))

    def test_ci_noise_the_store_record_reads_the_kernel_s_mount_table(self):
        import importlib.util
        from pathlib import Path
        ROOT=Path(__file__).resolve().parents[2]
        spec=importlib.util.spec_from_file_location('latency_store',ROOT/'control/chrome/ci/latency-store.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        root=Path(self.temporary.name).resolve()
        state=root/'state dir';evidence=root/'evidence';state.mkdir();evidence.mkdir()
        def table(evidence_type):
            return ('22 1 0:21 / / rw,relatime - overlay overlay rw,lowerdir=/l\n'
                    '40 22 0:40 / '+str(root)+' rw - ext4 /dev/sda1 rw\n'
                    '41 40 0:41 / '+str(state).replace(' ','\\040')+' rw,nosuid - tmpfs latency-store rw,size=524288k,mode=755,uid=1001\n'
                    '42 40 0:42 / '+str(evidence)+' rw,nosuid - tmpfs latency-store rw,size=524288k,mode=755,uid=1001\n'
                    '43 42 0:43 / '+str(evidence)+' rw - '+evidence_type+' other rw\n')
        mountinfo=root/'mountinfo';output=root/'latency-store.json'
        mountinfo.write_text(table('tmpfs'))
        value=module.record('start',output,mountinfo,(str(state),str(evidence)))
        # The escaped space decodes; the later of two stacked mounts is the one in effect.
        self.assertEqual(value['directories'][str(state)]['mount_point'],str(state))
        self.assertEqual({key:value['directories'][str(evidence)][key] for key in ['fstype','source']},{'fstype':'tmpfs','source':'other'})
        self.assertEqual(module.mount_of(str(root/'elsewhere'),module.mounts(mountinfo.read_text()))['fstype'],'ext4')
        self.assertTrue(all(row['size_bytes']>0 and 'used_bytes_end' not in row for row in value['directories'].values()))
        value=module.record('end',output,mountinfo,(str(state),str(evidence)))
        self.assertTrue(all('used_bytes_end' in row for row in self.json.loads(output.read_text())['directories'].values()))
        # A store that moved off its recorded mount mid-run refuses.
        mountinfo.write_text(table('ext4'))
        with self.assertRaises(AssertionError):module.record('end',output,mountinfo,(str(state),str(evidence)))


class RealisticRecord(unittest.TestCase):
    """#79 O2: one latency leg measures a qualification record of realistic size, not one entry."""

    def setUp(self):
        import qualification_fixture
        from pathlib import Path
        self.fixture=qualification_fixture
        self.root=Path(__file__).resolve().parents[2]

    def test_only_the_plain_leg_s_current_runtime_starts_from_several_hundred_entries(self):
        from aresos_control.chrome.policy import CORE_GROUPS,HOSTS
        from aresos_control.chrome.qualification import validate_record
        build,version='c'*64,'157.0.8103.78'
        one={'build':build,'version':version,'channel':'stable','run':'synthetic-fixture-setup',
             'core':dict.fromkeys(CORE_GROUPS,True),'adapters':dict.fromkeys(HOSTS,True)}
        self.assertGreaterEqual(self.fixture.LATENCY_HISTORY,300)
        for privacy in ['plain','audit']:
            for runtime in ['current','ab7aba92']:
                with self.subTest(privacy=privacy,runtime=runtime):
                    shipped=self.fixture.harness_shipped({'LATENCY_PROBE':'true','LATENCY_PRIVACY':privacy,'LATENCY_BASELINE':runtime})
                    record=self.fixture.harness_record(shipped,build,version)
                    validate_record(shipped);validate_record(record)
                    realistic=(privacy,runtime)==('plain','current')
                    self.assertEqual(len(shipped['entries']),self.fixture.LATENCY_HISTORY if realistic else 0)
                    self.assertEqual(record['entries'],[*shipped['entries'],one])
                    # The history is other builds' only, so this build's switches are the one entry's.
                    self.assertNotIn(build,{item['build'] for item in shipped['entries']})
        # The fixture shards and qualification pairs keep the empty baseline and the one entry.
        self.assertEqual(self.fixture.harness_shipped({}),self.fixture.BASELINE)
        self.assertEqual(self.fixture.harness_shipped({'LATENCY_PRIVACY':'plain','LATENCY_BASELINE':'current'}),self.fixture.BASELINE)
        self.assertEqual(self.fixture.harness_shipped({'LATENCY_PROBE':'true','LATENCY_PRIVACY':'plain','LATENCY_BASELINE':'current','EFFICIENCY_PROBE':'true'}),self.fixture.BASELINE)
        self.assertEqual(self.fixture.harness_record(self.fixture.BASELINE,build,version),{'format':1,'entries':[one]})

    def test_the_realistic_record_qualifies_chrome_like_the_one_entry_record(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from aresos_control.chrome import adapter
        shipped=self.fixture.harness_shipped({'LATENCY_PROBE':'true','LATENCY_PRIVACY':'plain','LATENCY_BASELINE':'current'})
        temporary=tempfile.TemporaryDirectory(dir=test_engine.WORK);self.addCleanup(temporary.cleanup)
        operations=test_engine.Operations('test_group1_approval_first_exact_and_dispatch_once')
        with patch.object(adapter,'RUNTIME',self.fixture.fixture_runtime(Path(temporary.name),baseline=shipped)):
            operations.setUp()
        self.addCleanup(operations.tearDown)
        from aresos_control.chrome.qualification import switches
        chrome=operations.chrome;build,version=chrome.qualification.build,operations.browser.version
        one=switches(self.fixture.harness_record(self.fixture.BASELINE,build,version),build,version)
        held=self.fixture.harness_record(shipped,build,version)
        operations.engine.store.write({'chrome:qualification':held},'chrome_test_setup','Synthetic realistic qualification record')
        self.assertEqual(chrome.qualification.shipped,shipped)
        self.assertEqual(chrome.qualification.record(),held)
        self.assertEqual(chrome.mode(acting=True),one)
        self.assertFalse(one['conservative'])
        approval=operations.prepare();sent=operations.call('submit',approval)
        self.assertTrue(sent['ok'],sent);self.assertEqual(len(operations.browser.dispatched),1)

    def test_the_harness_starts_from_the_shared_records_and_says_which(self):
        service=(self.root/'control/chrome/ci/service.py').read_text()
        self.assertIn('shipped=qualification_fixture.harness_shipped(os.environ)',service)
        self.assertIn("qualification_fixture.install(tempfile.mkdtemp(prefix='fixture-runtime-'),baseline=shipped)",service)
        self.assertIn('record=qualification_fixture.harness_record(shipped,build,version)',service)
        self.assertLess(service.index('record=qualification_fixture.harness_record('),service.index("engine.store.write({'chrome:qualification':record}"))
        # The artifact's service.txt names the record sizes the leg measured.
        self.assertIn("print('FIXTURE_QUALIFICATION',json.dumps({'shipped_entries':len(shipped['entries']),'held_entries':len(record['entries'])}),flush=True)",service)
        # The synthetic modes rewrite the one entry, so they refuse a long baseline.
        self.assertLess(service.index("if shipped['entries']:raise ValueError("),service.index('candidate=json.loads(json.dumps(record))'))
        # The pair names the runtime and the profile inside the container.
        pair=(self.root/'control/chrome/ci/latency-pair.sh').read_text()
        self.assertRegex(pair, r'-e LATENCY_PRIVACY -e LATENCY_BASELINE="\$(latency_)?revision"')
