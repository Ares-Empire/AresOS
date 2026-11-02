import datetime,json,pathlib,subprocess,sys
root=pathlib.Path.cwd();work=root/'.work/14';sys.path.insert(0,str(root/'os/ci'));import rehearsal_guard as guard
guard.configure('14');sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
scan=json.loads((work/'14ze-one-push-scan.json').read_text());assert scan['checked_commit']==sha and scan['findings']==scan['exit_code']==0
assert json.loads((work/'14ze-probe-local.json').read_text())['head']==sha
assert json.loads(guard.read_only('repos/'+guard.REPOSITORY))['private'] is True
remote=guard.api('git/ref/heads/'+guard.BRANCH)['object']['sha']
subprocess.run(['git','merge-base','--is-ancestor',remote,sha],check=True)
assert remote==subprocess.check_output(['git','rev-parse','origin/'+guard.BRANCH],text=True).strip()
plan=guard.owner_reservations();ledger=guard.budget(plan['pre_push']);org=guard.organization_budget(plan['pre_push'])
assert ledger['dispatch_counts']=={'probe':15,'owner-tools':5} and ledger['cap']==1100 and org['other_repos_reserve']==0
record=work/'14ze-push-attempt.json';assert not record.exists(),'STOP: a push was already attempted; never repeat automatically'
value=dict(head=sha,remote_before=remote,attempts=1,status='fast-forward push about to be attempted',
    checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=ledger,organization=org,reservation_plan=plan)
record.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
result=subprocess.run(['git','push','origin','HEAD:refs/heads/'+guard.BRANCH],capture_output=True,text=True,timeout=120)
value.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
record.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
assert result.returncode==0,'STOP: push failed/ambiguous; do not repeat automatically'
assert guard.api('git/ref/heads/'+guard.BRANCH)['object']['sha']==sha
assert subprocess.check_output(['git','rev-parse','origin/'+guard.BRANCH],text=True).strip()==sha
print('PUSHED_ONCE_FAST_FORWARD',remote,sha,'PACKAGE',ledger['consumed_minutes'],'+238/1100;ORG_AFTER',org['after_reservation'])
