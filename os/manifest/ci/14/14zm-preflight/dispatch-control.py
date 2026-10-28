"""Local read-only gates and single-attempt dispatch; never a workflow rerun."""
import contextlib,datetime,hashlib,io,json,os,pathlib,re,stat,subprocess,sys,time,zipfile
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT/'os/ci'));import rehearsal_guard as guard
guard.configure('14');REPO=guard.REPOSITORY;BRANCH=guard.BRANCH
WORK=ROOT/'.work/14';sys.path.insert(0,str(WORK));import importlib.util
_spec=importlib.util.spec_from_file_location('local_watcher',WORK/'14za_watcher.py');watcher=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(watcher)
PREFIX='os/manifest/ci/14/14zm-preflight/'


def write(name,value): (WORK/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def out(*command): return subprocess.check_output(command,text=True,encoding='utf-8').strip()
def read(name): return json.loads((WORK/name).read_text())
TARGET=out('git','rev-parse','HEAD')
def head(): return TARGET


def source_gate():
    sha=head();assert out('git','branch','--show-current')==BRANCH
    assert not out('git','status','--porcelain'),'STOP: dirty worktree'
    for name,key in ((PREFIX+'preparation.json','source_bindings'),('os/manifest/ci/14/host-walk/result.json','sources')):
        for row in json.loads((ROOT/name).read_text())[key]:
            assert hashlib.sha256(subprocess.check_output(['git','show',sha+':'+row['path']])).hexdigest()==row['sha256'],row['path']
    for row in json.loads((ROOT/(PREFIX+'preparation.json')).read_text())['local_tool_bindings']:
        assert hashlib.sha256((WORK/row['local']).read_bytes()).hexdigest()==row['sha256'],row['local']
        assert hashlib.sha256(subprocess.check_output(['git','show',sha+':'+PREFIX+row['archive']])).hexdigest()==row['sha256']
    subprocess.run(['git','diff','--check','5079914','HEAD'],check=True)
    subprocess.run(['git','diff','--exit-code','5079914','HEAD','--','os/release','os/config','os/policy',
        'os/manifest/base.json','os/manifest/release.json','os/Containerfile.keyboard','os/.containerignore','os/packages.lock.json',
        'os/keys','os/tests/audit.py','.gitleaksignore','.gitleaks.toml'],check=True)
    subprocess.run(['git','diff','--exit-code','bb55ce1','HEAD','--','.github/workflows',':(exclude).github/workflows/os-image.yml'],check=True)
    return sha


def privacy():
    sha=source_gate();assert out('git','rev-parse','origin/'+BRANCH)==sha
    assert json.loads(guard.read_only('repos/'+REPO))['private'] is True
    listing=guard.api(guard.RUN_HISTORY_PATH)
    current=[r for r in listing['workflow_runs'] if r['head_sha']==sha and r['name']=='privacy-check']
    if len(current)<2 or any(r['status']!='completed' for r in current):
        print('WAIT_PRIVACY',[(r['id'],r['status'],r['conclusion']) for r in current]);return 2
    assert len(current)==2 and {r['event'] for r in current}=={'push','pull_request'}
    required=['No secrets (gitleaks)','Only private commit emails','No personal terms'];proof=[]
    for run in current:
        assert run['conclusion']=='success' and run['run_attempt']==1,'STOP: exact-head privacy failed'
        jobs=guard.api(f'actions/runs/{run["id"]}/jobs?per_page=100');assert jobs['total_count']==len(jobs['jobs'])==1
        job,=jobs['jobs'];steps={s['name']:s['conclusion'] for s in job['steps']}
        assert all(steps.get(name)=='success' for name in required),'STOP: privacy step did not execute successfully'
        data=guard.read_only(f'repos/{REPO}/actions/runs/{run["id"]}/logs')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                if name.endswith('.txt'):
                    for line in archive.read(name).decode(errors='replace').splitlines():
                        payload=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',line).split('Z ',1)[-1]
                        assert not (payload.startswith(('##[warning]','::warning::')) and 'PRIVATE_TERMS secret is not set' in payload),'STOP: personal terms skipped'
        proof.append(dict(run=run['id'],head=sha,event=run['event'],steps={name:steps[name] for name in required},
                          personal_terms_not_skipped=True,log_zip_sha256=hashlib.sha256(data).hexdigest()))
    write('14zm-privacy.json',dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),head=sha,
        private_repository=True,source_hashes_match=True,runs=proof))
    print('PASS exact-head privacy all3 steps executed',sha,[r['run'] for r in proof]);return 0


def authorize(mode):
    sha=source_gate();assert mode in ('probe','owner-tools')
    assert out('git','rev-parse','origin/'+BRANCH)==sha
    assert read('14zm-privacy.json')['head']==sha
    scan=read('14zm-one-push-scan.json');assert scan['checked_commit']==sha and scan['findings']==scan['exit_code']==0
    local=read('14zm-'+mode+'-local.json');assert local['head']==sha and local['status']=='passed'
    os.environ['GITHUB_REPOSITORY']=REPO
    with (WORK/('14zm-pre-'+mode+'-release.log')).open('w',encoding='utf-8',newline='\n') as log:
        subprocess.run([sys.executable,'-X','utf8','os/ci/verify_release.py','40154642447'],stdout=log,stderr=log,check=True)
    os.environ['REHEARSAL_PACKAGE']='14';os.environ['GITHUB_SHA']=sha
    if mode=='owner-tools':
        run=read('14zm-probe-run.json');os.environ['PROBE_RUN']=str(run['id'])
        classified=read('run-'+str(run['id'])+'/14zm-privacy-classification.json');assert classified['status']=='passed'
        assert classified['run']==run['id'] and classified['head']==sha
        native=json.loads((WORK/('run-'+str(run['id']))/'evidence/14-native-owner-devices.json').read_text())
        assert native['status']=='passed' and native['sha']==sha and native['helper_mutations']==0
        assert native['protected_fixture_unchanged'] and native['all_fixture_mounts_unmounted_and_loops_detached']
    plan=guard.owner_reservations();reserve=plan['before_probe' if mode=='probe' else 'before_qualification']
    sys.argv=['os/ci/rehearsal_guard.py',mode,str(reserve)]
    with (WORK/('14zm-pre-'+mode+'-guard.log')).open('w',encoding='utf-8',newline='\n') as log,contextlib.redirect_stdout(log): guard.main()
    value=read('14-dispatch-authorization.json')
    assert value['history']['complete'] and value['history']['ids_count']==value['history']['total_count']
    assert value['dispatch_counts']=={'probe':19 if mode=='probe' else 20,'owner-tools':8}
    assert value['reservation_plan']==plan
    assert value['cap']==1500 and value['organization_budget']['other_repos_reserve']==0
    write('14zm-pre-'+mode+'-authorization.json',value)
    print('AUTHORIZED',mode,sha,'PACKAGE',value['consumed_minutes'],'+',reserve,'/1500;ORG_AFTER',
          value['organization_budget']['after_reservation'],'HISTORY',value['history']['ids_count'],value['history']['total_count'])


def dispatch(mode):
    assert mode in ('probe','owner-tools'),'STOP:14zm permits probe20 and qualification9 only'
    sha=source_gate();proof=read('14zm-pre-'+mode+'-authorization.json')
    plan=guard.owner_reservations()
    assert proof['reservation_plan']==plan and proof['reserved_minutes']==plan['before_probe' if mode=='probe' else 'before_qualification']
    assert proof['allowance']=='14' and proof['native']['sha']==sha
    assert proof['native']['status']==('pending' if mode=='probe' else 'passed')
    assert proof['cap']==1500 and proof['consumed_minutes']+proof['reserved_minutes']<=1500
    assert proof['organization_budget']['after_reservation']>=0
    assert proof['organization_budget']['paid_overflow']['budget_amount']==10
    assert proof['organization_budget']['paid_overflow']['prevent_further_usage'] is True
    assert proof['dispatch_counts']=={'probe':19 if mode=='probe' else 20,'owner-tools':8}
    assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(proof['organization_budget']['checked_at'])).total_seconds()<300
    remote=guard.api('git/ref/heads/'+BRANCH);assert remote['object']['sha']==sha
    pr=json.loads(subprocess.check_output(['gh','pr','view','13','--repo',REPO,'--json','state,isDraft,headRefOid']))
    assert pr==dict(state='OPEN',isDraft=True,headRefOid=sha)
    record='14zm-'+mode+'-dispatch-command.json';assert not (WORK/record).exists(),'STOP: a dispatch was already attempted'
    write(record,dict(head=sha,mode=mode,attempts=1,status='POST about to be sent; never repeat an ambiguous attempt'))
    args=['gh','workflow','run','os-image.yml','--repo',REPO,'--ref',BRANCH,'-f','rehearsal='+mode]
    if mode=='owner-tools': args+=['-f','probe_run='+str(proof['probe_run'])]
    result=subprocess.run(args,capture_output=True,text=True,timeout=60)
    write(record,dict(head=sha,mode=mode,attempts=1,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
    assert result.returncode==0,'STOP: failed/ambiguous dispatch response; no repeat POST'
    run=watcher.confirm(result.stdout,REPO,sha,BRANCH,guard.SETTINGS['titles'][mode],guard.api,
        lambda evidence:write('14zm-'+mode+'-confirmation.json',evidence))
    write('14zm-'+mode+'-run.json',run)
    print('DISPATCHED_ONCE',mode,run['id'],sha,run['html_url'])


def monitor(run_id):
    info=guard.api('actions/runs/'+run_id);assert info['run_attempt']==1 and info['head_sha']==read('14zm-one-push-scan.json')['checked_commit']
    jobs=guard.api(f'actions/runs/{run_id}/jobs?per_page=100');assert jobs['total_count']==len(jobs['jobs'])<=100
    main=[j for j in jobs['jobs'] if j['name']=='Pinned live ISO inspection and two-disk rehearsal'];assert len(main)<=1
    steps=main[0]['steps'] if main else [];active=[s for s in steps if s['status']=='in_progress']
    elapsed=round((datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(active[0]['started_at'].replace('Z','+00:00'))).total_seconds()/60,1) if active else None
    value=dict(run=int(run_id),status=info['status'],conclusion=info['conclusion'],active=[s['name'] for s in active],
        active_minutes=elapsed,failed=[s['name'] for s in steps if s['conclusion']=='failure'],
        last_completed=[s['name'] for s in steps if s['conclusion']=='success'][-2:])
    write('run-'+run_id+'-status.json',value);print(json.dumps(value))


if __name__=='__main__':
    action=sys.argv[1]
    if action=='privacy': sys.exit(privacy())
    elif action=='source': print('PASS committed source bindings',source_gate())
    elif action=='authorize': authorize(sys.argv[2])
    elif action=='dispatch': dispatch(sys.argv[2])
    elif action=='monitor': monitor(sys.argv[2])
    else: raise AssertionError('Unknown local action')
