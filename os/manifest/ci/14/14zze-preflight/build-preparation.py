"""Seal final local checks without changing historical receipts."""
import datetime,hashlib,json,pathlib,re,shutil,sys
r=pathlib.Path.cwd();w=r/'.work/14';out=r/'os/manifest/ci/14/14zze-preflight'
sys.path.insert(0,str(r/'os/ci'));import checkout_sources as checkout
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def order(v):
 if isinstance(v,list):return [order(x) for x in v]
 if isinstance(v,dict):
  ks=[k for k in v if k.endswith('sha256')];return {k:order(v[k]) for k in ks+[k for k in v if k not in ks]}
 return v
def write(p,v):p.write_text(json.dumps(order(v),indent=2)+'\n',encoding='utf-8',newline='\n')
whole=read(w/'14zze/whole-suite.json');assert whole['tests']==whole['executed']==630 and whole['skips']==0 and not whole['unknown_failures']
t=(w/'14zze/whole-suite.log').read_text(encoding='utf-8');whole['runner_seconds']=float(re.search(r'Ran 630 tests in ([\d.]+)s',t)[1]);whole['host_timing_seconds']=[float(x) for x in re.findall(r'AssertionError: ([\d.]+) not less than 30',t)]
affected=[]
for mode in ('normal','no-bytecode'):
 p=w/'14zze'/('affected-'+mode+'.log');t=p.read_text(encoding='utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK\s*$',t,re.M);assert m and 'FAILED (' not in t
 affected.append(dict(sha256=sha(p),path=p.relative_to(r).as_posix(),mode=mode,tests=int(m[1]),seconds=float(m[2]),skips=0,python_dont_write_bytecode_env_unset=True))
assert affected[0]['tests']==affected[1]['tests']
assert affected[0]['tests']==78
assert re.search(r'Ran 31 tests in [\d.]+s\s+OK\s*$',(w/'14zze/local-control-tests.log').read_text())
assert 'PASS 17 destination refusals with zero writes' in (w/'14zze/powershell.log').read_text()
retry=read(w/'14zze-probe-replay-attempts.json');assert retry['status']=='passed';iso=next(x['result'] for x in retry['attempts'] if x['exit_code']==0);assert iso['bytes']==9068650496
strict=read(w/'14zze-syntax.json');assert strict['status']=='passed' and strict['guest_scripts']==1159
walk=read(out/'walk.json');assert not walk['uncovered_waits'] and len(walk['physical_typing_cases'])==13 and walk['hidden_pairs']==27
assert 'Qualified private org release 2abc12e' in (w/'14zze-release-replay.log').read_text()
assert read(w/'14zze-zero-cost-replay.log')['retained_files_verified']==53
live=read(w/'14zze/live-start.json');assert live['ledger']['consumed_minutes']==2326 and live['ledger']['dispatch_counts']=={'probe':33,'owner-tools':20};assert live['organization_ledger_comparison']['status']=='passed'
timing=read(r/'os/manifest/ci/14/14zzc-timing/projection.json')
prior=read(r/'os/manifest/ci/14/14zzc-preflight/preparation.json')
tools={
 '14zze-privacy.py':'local-privacy.py','14zze-control.py':'dispatch-control.py','14zze-push-once.py':'push-once.py','14za_watcher.py':'dispatch-watcher.py',
 '14zze-basic.py':'basic-diagnostics.py','14zze-collect.py':'artifact-collector.py','14zze-probe-proof.py':'probe-review.py','14zze-qualification-proof.py':'qualification-review.py','14zze-native-timing.py':'native-timing-review.py','14zze-local-receipt.py':'local-receipt.py',
 '14zze-installer.py':'installer-adapter.py','14zze-qualification-installer.py':'qualification-installer.py','14zze-retry.py':'qualification-retry.py','14zze-read-only-replay.py':'read-only-replay.py','14zze-syntax.py':'syntax-checks.py','14zze-walk.py':'qualification-walk.py','14zze-probe-walk.py':'probe-walk.py',
 '14zze/post-run.py':'after-run-review.py','14zze/close-guard.py':'closing-guard.py','14zze/kernel-review.py':'kernel-review.py','14zze/log-review.py':'full-log-review.py','14zze/recompute.py':'recompute.py','14zze-classify.py':'classify-whole-lines.py','14zze/commit-preflight.py':'commit-preflight.py','14zze/build-preparation.py':'build-preparation.py',
 '14zze/qualification-reclaim.py':'qualification-reclaim.py','14zze/probe-retry.py':'probe-retry.py','14zze/monitor.py':'monitor.py','14l-audits.py':'independent-audits.py','14zze/whole.py':'whole.py','14zze/final-local.py':'final-local.py'}
bindings=[]
for local,archive in tools.items():
 p=w/local;shutil.copyfile(p,out/archive)
archived=checkout.records(r,[(out/archive).relative_to(r).as_posix() for archive in tools.values()])
for (local,archive),row in zip(tools.items(),archived):
 bindings.append(dict(sha256=row['sha256'],local_sha256=sha(w/local),local=local,archive=archive))
for name in ('test_classify.py','test_dispatch_control.py','test_local_privacy.py','test_basic.py','cache-reclaim.json','cache-reclaim-extra.json'):shutil.copyfile(w/'14zze'/name,out/name)
sources={x['path'] for x in read(r/'os/manifest/ci/14/host-walk/result.json')['sources']};sources.update(('briefs/14zze-checkout-bytes.md','os/manifest/ci/14/14zze-preflight/previous-dispatch.json'))
v=dict(status='local checks passed with existing host limitations; fresh same-head native probe/qualification pending',brief='briefs/14zze-checkout-bytes.md',prepared_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),whole_suite=whole,affected_bytecode_modes=affected,local_control_tests=31,windows_zero_mutation_refusals=17,timing_projection=timing,installer=iso,installer_local_retry=retry,strict=strict,ci_only=prior['ci_only'],accounting=live,
 november_settings=dict(starting_ledger=2326,starting_counts={'probe':33,'owner-tools':20},minute_cap=2750,dispatch_caps={'probe':34,'owner-tools':21},other_repos_reserve=150,push_privacy_reservation=0,closing_privacy_reservation=0,privacy_decision='briefs/14zw-local-privacy.md',paid_minutes_counted=0,budget_api_read=False,probe_bound=72,qualification_bound=240,vm_step_limit=200,round_reservation=312),
 source_bindings=checkout.records(r,sorted(sources)),binding_format='git-checkout-bytes-v1',local_tool_bindings=bindings,physical_cases=walk['physical_typing_cases'],
 checkout_replay_all_source_tables=True,old_dda72ed_record_refused=True,fixture_bundle_manifest_only=True,strict_validator_unchanged=True,no_global_bytecode_flag_change=True,whole_suite_normal_python_env_unset=True,no_owner_script_or_payload_change=True,no_image_publication=True,next_runs={'probe':34,'qualification':21},pushes_allowed=1,reruns_allowed=0,closing_report_local_only=True)
write(out/'preparation.json',v);write(out/'files.json',dict(files=checkout.records(r,[p.relative_to(r).as_posix() for p in sorted(out.iterdir()) if p.is_file() and p.name!='files.json']),binding_format='git-checkout-bytes-v1'))
budget=read(r/'reviews/14-owner-tools/BUDGET.json');budget.update(live['ledger']);budget.update(status='14zze fixtures/local checks passed; probe34 and qualification21 pending',acceptance_met=False,reserved_minutes=312,organization_ledger_comparison=live['organization_ledger_comparison'],organization_budget_snapshot=live['organization'],this_round_starting_ledger=2326,this_round_starting_counts={'probe':33,'owner-tools':20},current_round=dict(brief='14zze',status='pending fresh same-head probe34/qualification21',pushes=0,reruns=0));write(r/'reviews/14-owner-tools/BUDGET.json',budget)
print('PREPARED630 mandatory native tests;',len(sources),'source bindings;',len(bindings),'controls;2326+312/2750')
