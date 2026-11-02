import pathlib,json,subprocess,datetime,sys,time
w=pathlib.Path('.work/14');p=w/'14zj-replay-attempts.json';v=json.loads(p.read_text());assert len(v['attempts'])==3 and not (w/'14zj-replay.lock').exists()
v['attempts'][-1]['reason']='local >25GiB free-space preflight; no ISO reader started; ended partial duplicate caches subsequently prefix-hash-verified and removed'
v['holder_check']='14zj-checkpoint-holders.json; none present at read-only snapshot'
lock=w/'14zj-replay.lock'
with lock.open('x') as f:f.write(str(__import__('os').getpid()))
def save():p.write_text(json.dumps(v,indent=2)+'\n',newline='\n')
try:
 print('LOCAL_REPLAY_RETRY_WAIT',30,flush=True);time.sleep(30)
 row=dict(attempt=4,folder='.work/14/14zj-replay-4',start=datetime.datetime.now(datetime.timezone.utc).isoformat());v['attempts'].append(row);v['status']='running final allowed retry';save()
 with (w/'14zj-replay-4-driver.txt').open('w',encoding='utf-8',newline='\n') as out:result=subprocess.run([sys.executable,'-B','-X','utf8',str(w/'14zj-installer-replay.py'),'14zj-replay-4'],stdout=out,stderr=out)
 row.update(exit_code=result.returncode,end=datetime.datetime.now(datetime.timezone.utc).isoformat());v['status']='passed' if result.returncode==0 else 'stopped'
 if result.returncode==0:row['result']=json.loads((w/'14zj-replay-4/result.json').read_text())
 save();print('FINAL_LOCAL_REPLAY_EXIT',result.returncode,flush=True);assert result.returncode==0,'STOP: final allowed local replay failed; inspect retained diagnostics'
finally:lock.unlink()
