import pathlib,json,sys,datetime
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'));import rehearsal_guard as g;g.configure('14')
ledger=g.budget(0);org=g.organization_budget(0)
assert ledger['dispatch_counts']=={'probe':16,'owner-tools':6} and ledger['history']['complete'] and ledger['history']['ids_count']==ledger['history']['total_count']
v=dict(status='STOP qualification6 after title pass at physical readiness; no rerun',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=ledger,organization=org,pushes=1,dispatches=2,reruns=0,probe=40614909488,qualification=40617562735,head='ea803fd9b81fbd21ac1d8a054d253cf6d4bb17ac',acceptance_met=False)
(r/'.work/14/14zg-closed-stop.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print('CLOSED_STOP',ledger['consumed_minutes'],'/1100; history',ledger['history']['ids_count'],'/',ledger['history']['total_count'],'ORG_AVAILABLE',org['after_reservation'])
