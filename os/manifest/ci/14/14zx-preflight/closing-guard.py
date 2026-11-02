"""Closing read-only ledger; refuses to run while any round workflow is active."""
import datetime,json,pathlib,sys
r=pathlib.Path.cwd();w=r/'.work/14';sys.path.insert(0,str(r/'os/ci'))
import rehearsal_guard as guard
guard.configure('14')
head=json.loads((w/'14zx-one-push-scan.json').read_text())['checked_commit']
observed=[]
for mode in ('probe','owner-tools'):
    p=w/('14zx-'+mode+'-run.json')
    if p.exists():
        prior=json.loads(p.read_text());run=guard.api('actions/runs/'+str(prior['id']))
        assert run['status']=='completed' and run['run_attempt']==1 and run['head_sha']==head
        observed.append(dict(mode=mode,run=run['id'],head=head,conclusion=run['conclusion']))
assert observed and observed[0]['mode']=='probe'
ledger=guard.budget(0)
assert ledger['history']['complete'] and ledger['history']['ids_count']==ledger['history']['total_count']
assert ledger['dispatch_counts']=={'probe':28,'owner-tools':17 if len(observed)==2 else 16}
org=guard.organization_budget(0)
assert org['billing_mode']=='free-minutes-only' and org['paid_budget_read'] is False and org['paid_overflow'] is None
value=dict(status='closed; no further push or dispatch in this round',head=head,
    checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),runs=observed,ledger=ledger,organization=org,
    reservation_plan=guard.owner_reservations(),pushes=1,reruns=0,
    closing_report_commit_local_only=True,private_terms_recorded=False)
(w/'14zx/closed.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('CLOSED_REAL_LEDGER',ledger['consumed_minutes'],'/2750',ledger['dispatch_counts'],
      'history',ledger['history']['ids_count'],ledger['history']['total_count'],'orgfree',org['remaining_minutes'])
