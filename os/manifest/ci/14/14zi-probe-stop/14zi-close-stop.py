import pathlib,json,sys,datetime
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'));import rehearsal_guard as g;g.configure('14')
ledger=g.budget(0);org=g.organization_budget(0)
assert ledger['dispatch_counts']=={'probe':18,'owner-tools':7} and ledger['history']['complete'] and ledger['history']['ids_count']==ledger['history']['total_count']
v=dict(status='STOP probe18 staged syntax ACK interrupted by kernel output; no rerun',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=ledger,organization=org,pushes=1,dispatches=1,reruns=0,probe=40646962291,qualification=None,head='9c3f8a3722e3321150813456fecad7abbfefda3e',acceptance_met=False)
(r/'.work/14/14zi-closed-stop.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print('CLOSED_STOP',ledger['consumed_minutes'],'/1200; history',ledger['history']['ids_count'],'/',ledger['history']['total_count'],'ORG_AVAILABLE',org['after_reservation'])
