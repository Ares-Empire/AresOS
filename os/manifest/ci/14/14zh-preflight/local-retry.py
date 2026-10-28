"""Local-only Windows retries. Does not change the CI inspector or its checks."""
import datetime,json,pathlib,subprocess,sys,time,hashlib
r=pathlib.Path.cwd();w=r/'.work/14';rows=[]
lock=w/'14zh-replay.lock'
with lock.open('x') as f:f.write(str(__import__('os').getpid()))
def save(status):
    (w/'14zh-replay-attempts.json').write_text(json.dumps(dict(status=status,
      waits=[10,20,30],max_attempts=4,ci_inspector_changed=False,attempts=rows),indent=2)+'\n',newline='\n')
try:
    for number in range(1,5):
        if number>1:
            delay=(10,20,30)[number-2]
            print('LOCAL_REPLAY_RETRY_WAIT',delay,flush=True);time.sleep(delay)
        folder='14zh-replay-'+str(number)
        row=dict(attempt=number,folder='.work/14/'+folder,start=datetime.datetime.now(datetime.timezone.utc).isoformat())
        rows.append(row);save('running')
        print('LOCAL_REPLAY_ATTEMPT',number,flush=True)
        with (w/(folder+'-driver.txt')).open('w',encoding='utf-8',newline='\n') as output:
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(w/'14zh-installer-replay.py'),folder],stdout=output,stderr=output)
        row.update(exit_code=result.returncode,end=datetime.datetime.now(datetime.timezone.utc).isoformat())
        if result.returncode==0:
            proof=json.loads((w/folder/'result.json').read_text());assert proof['status']=='passed'
            row['result']=proof;save('passed');print('LOCAL_REPLAY_PASSED',number,flush=True);break
        text=(w/(folder+'-driver.txt')).read_text(encoding='utf-8')
        row['windows_checkpoint_denial']='PermissionError: [WinError 5]' in text and 'checkpoint' in text and 'replace' in text
        save('retryable Windows checkpoint denial' if row['windows_checkpoint_denial'] else 'stopped')
        print('LOCAL_REPLAY_REFUSED',number,'checkpoint denial',row['windows_checkpoint_denial'],flush=True)
        assert row['windows_checkpoint_denial'],'STOP: different local replay failure; preserve diagnostics'
    else:raise AssertionError('STOP: Windows denial persisted after three retries; identify holder')
finally:
    lock.unlink()
