import pathlib,json,sys,datetime
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'));import rehearsal_guard as g;g.configure('14')
ledger=g.budget(0);org=g.organization_budget(0)
assert ledger['dispatch_counts']=={'probe':19,'owner-tools':8} and ledger['history']['complete'] and ledger['history']['ids_count']==ledger['history']['total_count']
v=dict(status='STOP qualification8 direct-login read completion false negative; no rerun',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=ledger,organization=org,pushes=1,dispatches=2,reruns=0,probe=40655273119,qualification=40658792992,head='85c9cfeeeddd6a2592f86bdf4603818bbeb48ee7',acceptance_met=False)
(r/'.work/14/14zj-closed-stop.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print('CLOSED_STOP',ledger['consumed_minutes'],'/1200; history',ledger['history']['ids_count'],'/',ledger['history']['total_count'],'ORG_AVAILABLE',org['after_reservation'])
