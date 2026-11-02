import pathlib,subprocess,sys,json,time,datetime
r=pathlib.Path.cwd();w=r/'.work/14';log=w/'14zv/iso-replay.log'
text=log.read_text(encoding='utf-8')
assert 'PermissionError: [WinError 5]' in text and 'checkpoint' in text and 'replace' in text
lock=w/'14zv-probe-replay.lock';rows=[dict(attempt=1,exit_code=1,windows_checkpoint_denial=True,path='14zv-replay-1')]
with lock.open('x') as f:f.write(str(__import__('os').getpid()))
def save(status):
    (w/'14zv-probe-replay-attempts.json').write_text(json.dumps(dict(status=status,waits=[10,20,30],attempts=rows,ci_inspector_changed=False),indent=2)+'\n',encoding='utf-8',newline='\n')
try:
    for number,delay in ((2,10),(3,20),(4,30)):
        print('LOCAL_ONLY_RETRY_WAIT',delay,flush=True);time.sleep(delay)
        row=dict(attempt=number,path='14zv-replay-'+str(number),start=datetime.datetime.now(datetime.timezone.utc).isoformat());rows.append(row);save('running')
        target=w/'14zv'/('iso-replay-'+str(number)+'.log')
        with target.open('w',encoding='utf-8',newline='\n') as f:
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(w/'14zv-installer.py'),row['path']],stdout=f,stderr=f)
        row.update(exit_code=result.returncode,end=datetime.datetime.now(datetime.timezone.utc).isoformat())
        if result.returncode==0:
            proof=json.loads((w/row['path']/'result.json').read_text());assert proof['status']=='passed'
            row['result']=proof;save('passed');print('LOCAL_ISO_REPLAY_PASSED',number,flush=True);break
        text=target.read_text(encoding='utf-8');row['windows_checkpoint_denial']='PermissionError: [WinError 5]' in text and 'checkpoint' in text and 'replace' in text
        save('retryable Windows checkpoint denial' if row['windows_checkpoint_denial'] else 'stopped')
        assert row['windows_checkpoint_denial'], 'STOP: different local replay failure'
    else:
        save('stopped persistent Windows checkpoint denial; identify holder')
        raise AssertionError('STOP: WinError5 persisted after3 local retries; identify holder')
finally:lock.unlink()
