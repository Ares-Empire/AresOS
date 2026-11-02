import pathlib,json,re,hashlib,sys
r=pathlib.Path.cwd();run=int(sys.argv[1]);b=r/'.work/14'/('run-'+str(run));receipt=json.loads((b/'receipt.json').read_text());log=b/'native.log';text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',log.read_text(encoding='utf-8'))
NATIVE_TESTS=json.loads((r/'os/manifest/ci/14/14zz-preflight/preparation.json').read_text())['whole_suite']['tests']
name='test_exact_login_driver_sequence_stops_on_lost_result_chunk_without_retry (test_serial_staging.StagingTest.test_exact_login_driver_sequence_stops_on_lost_result_chunk_without_retry)'
matched=[(i,line) for i,line in enumerate(text.splitlines(),1) if name+' ... ok' in line]
assert len(matched)==1,'STOP: mandatory native timing test not explicitly passed'
assert re.search(r'Ran '+str(NATIVE_TESTS)+r' tests in [\d.]+s',text) and re.search(r'Z OK\s*$',text,re.M),'STOP: native suite not all expected tests passed with zero skips'
v=dict(status='passed',run=run,head=receipt['head'],test=name,native_result='ok; unchanged30-second bound',log=dict(sha256=hashlib.sha256(log.read_bytes()).hexdigest(),path='native.log'),line=matched[0][0],local_exception_applied_in_ci=False)
(b/'native-timing-proof.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print('PASS explicit mandatory native timing case;',NATIVE_TESTS,'native, zero skips')
