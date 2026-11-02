"""Record fresh replay of unchanged implementation on the existing pushed head."""
import datetime,hashlib,importlib.util,json,pathlib,subprocess
r=pathlib.Path.cwd();w=r/'.work/14';s=importlib.util.spec_from_file_location('control',w/'14zza/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
assert c.source_gate()==c.TARGET
def read(p):return json.loads(p.read_text(encoding='utf-8'))
prep=read(r/'os/manifest/ci/14/14zz-preflight/preparation.json')
assert prep['whole_suite']['tests']==597 and prep['whole_suite']['unknown_failures']==[] and prep['whole_suite']['skips']==0
assert 'Qualified private org release 2abc12e' in (w/'14zza-release-replay.log').read_text()
assert read(w/'14zza-zero-cost-replay.log')['retained_files_verified']==53
strict=read(w/'14zza-syntax.json');assert strict['status']=='passed' and strict['guest_scripts']==980
attempts=read(w/'14zza-qualification-replay-attempts.json');assert attempts['status']=='passed'
iso=next(x['result'] for x in attempts['attempts'] if x['exit_code']==0);assert iso['status']=='passed' and iso['bytes']==9068650496
assert read(w/'gitleaks/14zza-history.json')==[]
text=(w/'14zza/classifier-tests.log').read_text();assert 'Ran 14 tests in ' in text and '\nOK\n' in text and 'FAILED (' not in text
value=dict(status='passed',head=c.TARGET,local_metadata_head=c.LOCAL,mode='owner-tools',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),kind='fresh local replay; implementation identical to pushed probe30 head; four credential-only CI checks remain fail-closed',installer=iso,strict=strict,ci_only=prep['ci_only'],classify_tests=14,source_bindings=prep['source_bindings'],local_bindings=read(w/'14zza/local-bindings.json'),credentials_changed=False,owner_secret_used=False,no_new_push=True,no_new_probe=True)
(w/'14zz-owner-tools-local.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
(w/'14zza/local-replay.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PASS fresh existing-head replay receipt',c.TARGET)
