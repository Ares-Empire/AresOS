import collections,datetime,hashlib,json,math,pathlib,sys
r=pathlib.Path.cwd();w=r/'.work/14/14zz';d=w/'history';d.mkdir(exist_ok=True);sys.path.insert(0,str(r/'os/ci'))
import rehearsal_guard as g
g.configure('14');original=g.api
rawjobs={}
def api(path):
 value=original(path)
 if path==g.RUN_HISTORY_PATH:(d/'history.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
 elif path.startswith('actions/runs/') and '/jobs?' in path:
  run=int(path.split('/')[2]);rawjobs[run]=value;(d/('jobs-'+str(run)+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
 return value
g.api=api
plan=g.owner_reservations();ledger=g.budget(plan['pre_push']);org=g.organization_budget(plan['pre_push']);previous=json.loads((r/'os/manifest/ci/14/14zz-preflight/previous-dispatch.json').read_text());comparison=g.ledger_organization_check(ledger,org,previous)
changed=[];rules=collections.Counter();files=[]
for row in ledger['runs']:
 jobs=rawjobs[row['run']]['jobs'];assert len(jobs)==len(row['jobs'])
 for job,new in zip(jobs,row['jobs']):
  assert new['job']==job['id'];rules[new['rule']]+=1
  old=0 if job['conclusion']=='skipped' else max(1,math.ceil((datetime.datetime.fromisoformat(job['completed_at'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(job['started_at'].replace('Z','+00:00'))).total_seconds()/60))
  if old!=new['minutes']:changed.append(dict(run=row['run'],job=job['id'],name=job['name'],old_minutes=old,new_minutes=new['minutes'],rule=new['rule'],selected_start=new.get('selected_start'),selected_completion=new.get('selected_completion')))
 p=d/('jobs-'+str(row['run'])+'.json');files.append(dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(r).as_posix()))
value=dict(status='passed complete live recomputation',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ledger=ledger,organization=org,reservation_plan=plan,organization_ledger_comparison=comparison,changed_jobs=changed,rules=dict(rules),raw_json_snapshots=files,raw_snapshots_committed=False)
(w/'live-start.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('RECOMPUTED',ledger['consumed_minutes'],'/2750',ledger['dispatch_counts'],'history',ledger['history']['ids_count'],'/',ledger['history']['total_count']);print('CHANGED_JOBS',json.dumps(changed));print('BILLING_COMPARISON',json.dumps(comparison));print('ORG_FREE',org['remaining_minutes'])
