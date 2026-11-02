import datetime,json,pathlib,subprocess,sys
root=pathlib.Path.cwd();work=root/'.work/14';sys.path.insert(0,str(root/'os/ci'));import rehearsal_guard as guard
guard.configure('14')
import importlib.util
spec=importlib.util.spec_from_file_location('controller',work/'14zzc-control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
control.live_gate()
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
scan=json.loads((work/'14zzc-one-push-scan.json').read_text());assert scan['checked_commit']==sha and scan['findings']==scan['exit_code']==0
assert json.loads((work/'14zzc-probe-local.json').read_text())['head']==sha
assert control.source_gate()==sha
assert json.loads(guard.read_only('repos/'+guard.REPOSITORY))['private'] is True
remote=guard.api('git/ref/heads/'+guard.BRANCH)['object']['sha']
subprocess.run(['git','merge-base','--is-ancestor',remote,sha],check=True)
assert remote==subprocess.check_output(['git','rev-parse','origin/'+guard.BRANCH],text=True).strip()
url=subprocess.check_output(['git','remote','get-url','origin'],text=True).strip()
assert url=='https://github.com/Ares-Empire/AresOS.git','STOP: unexpected push destination'
local=control.local_privacy.precheck(sha,remote,url)
plan=guard.owner_reservations();ledger=guard.budget(plan['pre_push']);org=guard.organization_budget(plan['pre_push'])
assert ledger['dispatch_counts']=={'probe':31,'owner-tools':20} and ledger['cap']==2750 and org['other_repos_reserve']==150
prepared=json.loads((root/'os/manifest/ci/14/14zzc-preflight/preparation.json').read_text())['november_settings']
assert ledger['consumed_minutes']==prepared['starting_ledger'], 'STOP: live November starting ledger changed since preparation'
assert guard.SETTINGS['dispatch_caps']=={'probe':32,'owner-tools':21}
assert (plan['push'],plan['closing_privacy'],plan['pre_push'])==(0,0,312)
control.local_privacy.verify(local,sha)
assert org['paid_overflow'] is None and org['paid_budget_read'] is False
comparison=guard.ledger_organization_check(ledger,org,json.loads((root/'os/manifest/ci/14/14zzc-preflight/previous-dispatch.json').read_text()))
record=work/'14zzc-push-attempt.json';assert not record.exists(),'STOP: a push was already attempted; never repeat automatically'
value=dict(head=sha,remote_before=remote,attempts=1,status='fast-forward push about to be attempted',
    checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=ledger,organization=org,reservation_plan=plan,organization_ledger_comparison=comparison,no_verify=False,local_precheck_exit_code=local['exit_code'])
record.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
result=subprocess.run(['git','push','origin','refs/heads/'+guard.BRANCH+':refs/heads/'+guard.BRANCH],capture_output=True,text=True,timeout=600)
value.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,
    actual_hook_warning_absent='personal terms check skipped' not in ' '.join((result.stdout+result.stderr).casefold().split()))
record.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
assert result.returncode==0,'STOP: push failed/ambiguous; do not repeat automatically'
assert value['actual_hook_warning_absent'],'STOP: actual push hook skipped personal terms; no dispatch'
control.local_privacy.verify(local,sha)
assert guard.api('git/ref/heads/'+guard.BRANCH)['object']['sha']==sha
assert subprocess.check_output(['git','rev-parse','origin/'+guard.BRANCH],text=True).strip()==sha
print('PUSHED_ONCE_FAST_FORWARD',remote,sha,'PACKAGE',ledger['consumed_minutes'],'+312/2750;ORG_AFTER',org['after_reservation'])
