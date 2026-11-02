import pathlib,json,hashlib,subprocess,datetime,sys,importlib.util
r=pathlib.Path.cwd();w=r/'.work/14';mode=sys.argv[1]
assert mode in ('probe','owner-tools')
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
spec=importlib.util.spec_from_file_location('controller',w/'14zm-control.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
assert c.source_gate()==sha
prep=json.loads((r/'os/manifest/ci/14/14zm-preflight/preparation.json').read_text())
assert prep['installer']['bytes']==9068650496 and prep['strict']['guest_scripts']>=283
assert json.loads((w/'gitleaks/14zm-committed-history.json').read_text())==[]
assert 'Qualified private org release 2abc12e' in (w/'14zm-release-replay.log').read_text()
assert json.loads((w/'14zm-zero-cost-replay.log').read_text())['retained_files_verified']==53
assert json.loads((w/'14zm-syntax.json').read_text())['status']=='passed'
iso=prep['installer'] if mode=='probe' else next(x['result'] for x in json.loads((w/'14zm-qualification-replay-attempts.json').read_text())['attempts'] if x['exit_code']==0)
assert iso['status']=='passed' and iso['bytes']==9068650496
value=dict(status='passed',kind='all locally replayable checks only; CI-only steps deferred fail-closed',
    head=sha,mode=mode,checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    installer=iso,ci_only=prep['ci_only'],source_bindings=prep['source_bindings'],
    local_tools=[dict(sha256=hashlib.sha256((w/p).read_bytes()).hexdigest(),path='.work/14/'+p) for p in
       ('14zm-control.py','14za_watcher.py','14zm-push-once.py','14zm-collect.py','14zm-local-receipt.py')],
    credentials_changed=False,owner_secret_used=False)
(w/('14zm-'+mode+'-local.json')).write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print('PASS exact committed-head local replay receipt',mode,sha)
