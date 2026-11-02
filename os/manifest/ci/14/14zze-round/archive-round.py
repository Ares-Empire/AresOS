"""Archive available terminal receipts; never push or dispatch."""
import collections,hashlib,json,pathlib,shutil,subprocess,sys
r=pathlib.Path.cwd();w=r/'.work/14';head=json.loads((w/'14zze-one-push-scan.json').read_text())['checked_commit']
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
sys.path.insert(0,str(r/'os/ci'));import rehearsal_guard as guard
guard.configure('14')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def order(v):
 if isinstance(v,list):return [order(x) for x in v]
 if isinstance(v,dict):
  ks=[k for k in v if k.endswith('sha256')];return {k:order(v[k]) for k in ks+[k for k in v if k not in ks]}
 return v
closed=read(w/'14zze/closed.json');assert closed['head']==head
last=closed['runs'][-1];comparison=guard.ledger_organization_check(closed['ledger'],closed['organization'],dict(
 authorization=read(w/('14zze-pre-'+last['mode']+'-authorization.json')),dispatched_run=last['run']))
out=r/'os/manifest/ci/14/14zze-round';assert not out.exists();out.mkdir()
def write(name,v):(out/name).write_text(json.dumps(order(v),indent=2)+'\n',encoding='utf-8',newline='\n')
write('ledger.json',dict(**closed,organization_ledger_comparison=comparison,job_rule_counts=dict(collections.Counter(j['rule'] for run in closed['ledger']['runs'] for j in run['jobs'])),package_minute_ledger_trusted=True))
for source,name in [('14zze-pre-probe-authorization.json','probe-authorization.json'),('14zze-pre-owner-tools-authorization.json','qualification-authorization.json'),('14zze-push-attempt.json','push.json'),('14zze-one-push-scan.json','local-privacy-pushed-head.json'),('14zze-privacy.json','hook-privacy.json'),('14zze-owner-tools-local.json','qualification-replay.json'),('14zze-qualification-replay-attempts.json','qualification-replay-attempts.json')]:
 p=w/source
 if p.exists():write(name,read(p))
accepted=True;runs=[]
for run in closed['runs']:
 mode=run['mode'];label='probe34' if mode=='probe' else 'qualification21';rid=run['run'];base=w/('run-'+str(rid));basic=w/'14zze'/('basic-'+str(rid));kind='probe' if mode=='probe' else 'qualification'
 proof=base/('14zze-'+kind+'-proof.json');review=base/'14zze-post-review.json'
 passed=proof.exists() and review.exists() and run['conclusion']=='success'
 if passed:
  v=read(review);passed=v['status']=='passed' and v['head']==head and v['run']==rid and v['mode']==mode
 accepted=accepted and passed
 runs.append(dict(**run,accepted=passed))
 for source,suffix in [('receipt.json','artifact'),('14zze-post-review.json','complete-review'),('14zze-privacy-classification.json','artifact-review'),('14zze-log-classification.json','log-review'),('14zze-kernel-proof.json','kernel-proof'),('14zze-ps2-health-proof.json','ps2-health'),('independent-audits.json','independent-audits'),('native-timing-proof.json','native-timing'),('14zze-'+kind+'-proof.json','acceptance')]:
  p=base/source
  if p.exists():write(label+'-'+suffix+'.json',read(p))
 if basic.exists():write(label+'-source-bindings.json',dict(files=[dict(sha256=sha(p),path=p.relative_to(r).as_posix()) for p in sorted(basic.iterdir()) if p.is_file()]))
 if mode=='owner-tools' and (base/'evidence/two-disk/layout-reset-proof.json').exists():write('layout-reset-proof.json',read(base/'evidence/two-disk/layout-reset-proof.json'))
accepted=accepted and len(runs)==2
write('round.json',dict(status='accepted' if accepted else 'STOP; no rerun',head=head,runs=runs,acceptance_met=accepted,pushes=1,reruns=0,closing_commit_local_only=True,physical_release='NOT RELEASED',ledger_minutes=closed['ledger']['consumed_minutes']))
budget=read(r/'reviews/14-owner-tools/BUDGET.json');budget.update(closed['ledger']);budget.update(status='14zze accepted' if accepted else '14zze STOP; no rerun',acceptance_met=accepted,reserved_minutes=0,closed_round_manifest='os/manifest/ci/14/14zze-round/round.json',organization_ledger_comparison=comparison,organization_budget_snapshot=closed['organization'],current_round=dict(decision='briefs/14zze-checkout-bytes.md',runs=runs,pushes=1,reruns=0,closing_report_local_only=True));(r/'reviews/14-owner-tools/BUDGET.json').write_text(json.dumps(order(budget),indent=2)+'\n',encoding='utf-8',newline='\n')
print('ARCHIVED_TERMINAL_ROUND',accepted,closed['ledger']['consumed_minutes'],comparison)
