"""Closing read-only accounting; no dispatch or budget mutation."""
import pathlib,json,sys,datetime
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'));import rehearsal_guard as guard
guard.configure('14');run=40866713472;head='a247ee898598636aee3f9cd1d9e60c01632d0280'
info=guard.api('actions/runs/'+str(run))
assert info['status']=='completed' and info['run_attempt']==1 and info['head_sha']==head and info['conclusion']=='failure'
value=dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=guard.budget(0),organization=guard.organization_budget(0),pushes_this_round=1,probe25=40863215153,qualification14=run,qualification_conclusion=info['conclusion'],closing_reservation=0,reserve=0,reruns=0)
assert value['ledger']['dispatch_counts']=={'probe':25,'owner-tools':14}
(r/'.work/14/14zr-closed.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print('CLOSED_LEDGER',value['ledger']['consumed_minutes'],'/1800;complete',value['ledger']['history']['ids_count'],value['ledger']['history']['total_count'],'ORG_AVAILABLE',value['organization']['remaining_minutes'],'NET_CHARGED',value['organization']['paid_overflow']['reported_net_amount'])
