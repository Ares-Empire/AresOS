"""Retain actual terminal run metadata/logs even if no artifact was produced."""
import pathlib,json,sys,hashlib,subprocess
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT/'os/ci'));import rehearsal_guard as guard

def export(run,head,folder,api,read_only):
    info=api('actions/runs/'+str(run))
    assert info['status']=='completed' and info['run_attempt']==1 and info['head_sha']==head
    assert info['head_branch']=='pkg/14-owner-tools'
    jobs=api(f'actions/runs/{run}/jobs?per_page=100')
    artifacts=api(f'actions/runs/{run}/artifacts?per_page=100')
    for value,key in ((jobs,'jobs'),(artifacts,'artifacts')):
        assert value['total_count']==len(value[key])<=100, 'STOP: incomplete diagnostics listing'
    assert not folder.exists();folder.mkdir(parents=True)
    for name,value in (('run.json',info),('jobs.json',jobs),('artifacts.json',artifacts)):
        (folder/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    logs=None
    try:
        raw=read_only(f'repos/{guard.REPOSITORY}/actions/runs/{run}/logs')
        (folder/'logs.zip').write_bytes(raw);logs=dict(sha256=hashlib.sha256(raw).hexdigest(),path='logs.zip')
    except subprocess.CalledProcessError as error:
        (folder/'logs-unavailable.json').write_text(json.dumps(dict(returncode=error.returncode,
            http_status=guard.failure_status(error.stderr or b''),credential_changed=False))+'\n')
    value=dict(run=run,head=head,conclusion=info['conclusion'],jobs=len(jobs['jobs']),artifacts=artifacts['total_count'],logs=logs)
    (folder/'receipt.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return value

if __name__=='__main__':
    run=int(sys.argv[1]);scan=json.loads((ROOT/'.work/14/14zx-one-push-scan.json').read_text())
    print(json.dumps(export(run,scan['checked_commit'],ROOT/'.work/14/14zx'/('basic-'+str(run)),guard.api,guard.read_only)))
