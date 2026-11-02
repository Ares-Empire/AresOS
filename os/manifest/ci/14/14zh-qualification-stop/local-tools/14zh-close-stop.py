import pathlib,json,sys,datetime
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'));import rehearsal_guard as g;g.configure('14')
ledger=g.budget(0);org=g.organization_budget(0)
assert ledger['dispatch_counts']=={'probe':17,'owner-tools':7} and ledger['history']['complete'] and ledger['history']['ids_count']==ledger['history']['total_count']
v=dict(status='STOP qualification7 private login hidden-completion idle timeout; no rerun',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=ledger,organization=org,pushes=1,dispatches=2,reruns=0,probe=40628158654,qualification=40630352782,head='d15678dc491905f592c2b7b1af852fca1d35e08b',acceptance_met=False)
(r/'.work/14/14zh-closed-stop.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print('CLOSED_STOP',ledger['consumed_minutes'],'/1100; history',ledger['history']['ids_count'],'/',ledger['history']['total_count'],'ORG_AVAILABLE',org['after_reservation'])
