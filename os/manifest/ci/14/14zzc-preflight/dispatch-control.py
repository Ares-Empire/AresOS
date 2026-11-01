"""Local read-only gates and single-attempt dispatch; never a workflow rerun."""
import contextlib,datetime,hashlib,io,json,os,pathlib,re,stat,subprocess,sys,time,zipfile
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT/'os/ci'));import rehearsal_guard as guard
guard.configure('14');REPO=guard.REPOSITORY;BRANCH=guard.BRANCH
WORK=ROOT/'.work/14';sys.path.insert(0,str(WORK));import importlib.util
_spec=importlib.util.spec_from_file_location('local_watcher',WORK/'14za_watcher.py');watcher=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(watcher)
PREFIX='os/manifest/ci/14/14zzc-preflight/'
_spec=importlib.util.spec_from_file_location('local_privacy',WORK/'14zzc-privacy.py');local_privacy=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(local_privacy)


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
    subprocess.run(['git','diff','--check','bd85527','HEAD'],check=True)
    frozen=['os/config','os/release','os/policy','os/manifest/base.json','os/manifest/release.json',
      'os/Containerfile.keyboard','os/.containerignore','os/packages.lock.json','os/keys','os/tests/audit.py',
      'os/ci/rehearsal-packages.json','os/manifest/ci/14/keyboard-sources',
      'os/manifest/ci/13/13f-zero-cost/qemu-keymap.csv','.gitleaksignore','.gitleaks.toml']
    subprocess.run(['git','diff','--exit-code','bd85527','HEAD','--',*frozen],check=True)
    subprocess.run(['git','diff','--exit-code','bd85527','HEAD','--','.github',':(exclude).github/workflows/os-image.yml'],check=True)
    baseline=subprocess.check_output(['git','show','bd85527:.github/workflows/os-image.yml'],text=True)
    baseline=baseline.replace("inputs.rehearsal == 'owner-tools' && 220","inputs.rehearsal == 'owner-tools' && 240")
    baseline=baseline.replace("inputs.rehearsal == 'owner-tools' && 180","inputs.rehearsal == 'owner-tools' && 200")
    assert (ROOT/'.github/workflows/os-image.yml').read_text()==baseline
    proof=json.loads((ROOT/'os/manifest/ci/14/14zzc-preflight/source-proof.json').read_text())
    import ast
    current=(ROOT/'os/ci/two_disk_vm.py').read_text()
    node=next(n for n in ast.parse(current).body if isinstance(n,ast.ClassDef) and n.name=='Audit')
    source=''.join(current.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
    assert hashlib.sha256(source.encode()).hexdigest()==proof['audit_source_sha256']
    assert not (ROOT/'.github/workflows/privacy-check.yml').exists()
    return sha


UTC_START=datetime.datetime(2026,11,1,0,5,tzinfo=datetime.timezone.utc)
def live_gate(now=None):
    now=now or datetime.datetime.now(datetime.timezone.utc)
    assert now.tzinfo is not None and now.astimezone(datetime.timezone.utc)>=UTC_START, 'STOP: live guard/push/dispatch before2026-11-01 00:05UTC'
    return now.astimezone(datetime.timezone.utc).isoformat()


def privacy():
    live_gate()
    sha=source_gate();assert out('git','rev-parse','origin/'+BRANCH)==sha
    assert json.loads(guard.read_only('repos/'+REPO))['private'] is True,'STOP: repository is not private'
    proof=local_privacy.verify(read('14zzc-prepush-privacy.json'),sha)
    push=read('14zzc-push-attempt.json')
    assert push['head']==sha and push['remote_before']==proof['remote_before']
    assert push['attempts']==1 and push['returncode']==0 and push['no_verify'] is False
    assert push['actual_hook_warning_absent'] is True and push['local_precheck_exit_code']==0
    write('14zzc-privacy.json',dict(status='passed',head=sha,kind='aresync local exact-range pre-push and actual git push hook',
        checker=proof['identity'],exit_code=0,personal_terms_skipped_warning_absent=True,
        standard_stdin=proof['standard_stdin'],commits_checked=proof['commits_checked'],
        no_verify=False,github_privacy_runs_required=False))
    print('PASS exact-head local hook privacy',sha,'checker gitleaks',proof['identity']['gitleaks']['version'])
    return 0


def authorize(mode):
    live_gate()
    sha=source_gate();assert mode in ('probe','owner-tools')
    assert out('git','rev-parse','origin/'+BRANCH)==sha
    assert privacy()==0
    scan=read('14zzc-one-push-scan.json');assert scan['checked_commit']==sha and scan['findings']==scan['exit_code']==0
    local=read('14zzc-'+mode+'-local.json');assert local['head']==sha and local['status']=='passed'
    os.environ['GITHUB_REPOSITORY']=REPO
    with (WORK/('14zzc-pre-'+mode+'-release.log')).open('w',encoding='utf-8',newline='\n') as log:
        subprocess.run([sys.executable,'-X','utf8','os/ci/verify_release.py','40154642447'],stdout=log,stderr=log,check=True)
    os.environ['REHEARSAL_PACKAGE']='14';os.environ['GITHUB_SHA']=sha
    if mode=='probe':
        checkpoint=ROOT/(PREFIX+'previous-dispatch.json')
    else:
        previous=dict(authorization=read('14zzc-pre-probe-authorization.json'),dispatched_run=read('14zzc-probe-run.json')['id'])
        write('14zzc-previous-probe-dispatch.json',previous);checkpoint=WORK/'14zzc-previous-probe-dispatch.json'
    os.environ['REHEARSAL_PREVIOUS_DISPATCH']=str(checkpoint)
    if mode=='owner-tools':
        run=read('14zzc-probe-run.json');os.environ['PROBE_RUN']=str(run['id'])
        reviewed=read('run-'+str(run['id'])+'/14zzc-post-review.json')
        assert reviewed['status']=='passed' and reviewed['mode']=='probe' and reviewed['head']==sha and reviewed['run']==run['id']
        classified=read('run-'+str(run['id'])+'/14zzc-privacy-classification.json');assert classified['status']=='passed'
        assert classified['run']==run['id'] and classified['head']==sha
        native=json.loads((WORK/('run-'+str(run['id']))/'evidence/14-native-owner-devices.json').read_text())
        assert native['status']=='passed' and native['sha']==sha and native['helper_mutations']==0
        assert native['protected_fixture_unchanged'] and native['all_fixture_mounts_unmounted_and_loops_detached']
        logs=read('run-'+str(run['id'])+'/14zzc-log-classification.json')
        assert logs['status']=='passed' and logs['head']==sha and logs['run']==run['id']
        kernel=read('run-'+str(run['id'])+'/14zzc-kernel-proof.json')
        assert kernel['status']=='passed' and kernel['head']==sha and kernel['run']==run['id'] and kernel['skipped'] is False
    plan=guard.owner_reservations();reserve=plan['before_probe' if mode=='probe' else 'before_qualification']
    sys.argv=['os/ci/rehearsal_guard.py',mode,str(reserve)]
    with (WORK/('14zzc-pre-'+mode+'-guard.log')).open('w',encoding='utf-8',newline='\n') as log,contextlib.redirect_stdout(log): guard.main()
    value=read('14-dispatch-authorization.json')
    assert value['history']['complete'] and value['history']['ids_count']==value['history']['total_count']
    assert value['dispatch_counts']=={'probe':31 if mode=='probe' else 32,'owner-tools':20}
    assert value['reservation_plan']==plan
    assert value['organization_ledger_comparison']['status']=='passed' and value['organization_ledger_comparison']['current_minutes']==value['consumed_minutes']
    assert value['cap']==2750 and value['organization_budget']['other_repos_reserve']==150
    write('14zzc-pre-'+mode+'-authorization.json',value)
    print('AUTHORIZED',mode,sha,'PACKAGE',value['consumed_minutes'],'+',reserve,'/2750;ORG_AFTER',
          value['organization_budget']['after_reservation'],'HISTORY',value['history']['ids_count'],value['history']['total_count'])


def dispatch(mode):
    live_gate()
    assert mode in ('probe','owner-tools'),'STOP:14zzc permits probe32 and qualification21 only'
    sha=source_gate();assert privacy()==0;proof=read('14zzc-pre-'+mode+'-authorization.json')
    plan=guard.owner_reservations()
    assert proof['reservation_plan']==plan and proof['reserved_minutes']==plan['before_probe' if mode=='probe' else 'before_qualification']
    assert proof['allowance']=='14' and proof['native']['sha']==sha
    assert proof['native']['status']==('pending' if mode=='probe' else 'passed')
    assert proof['cap']==2750 and proof['consumed_minutes']+proof['reserved_minutes']<=2750
    comparison=proof['organization_ledger_comparison']
    assert comparison['status']=='passed' and comparison['current_minutes']==proof['consumed_minutes']
    assert comparison['package_increase']>=0 and comparison['organization_increase']>=0
    assert comparison['organization_increase']-comparison['package_increase']<=5
    assert proof['organization_budget']['after_reservation']>=150
    assert proof['organization_budget']['paid_overflow'] is None
    assert proof['organization_budget']['paid_budget_read'] is False and proof['organization_budget']['billing_mode']=='free-minutes-only'
    assert proof['dispatch_counts']=={'probe':31 if mode=='probe' else 32,'owner-tools':20}
    assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(proof['organization_budget']['checked_at'])).total_seconds()<300
    remote=guard.api('git/ref/heads/'+BRANCH);assert remote['object']['sha']==sha
    pr=json.loads(subprocess.check_output(['gh','pr','view','13','--repo',REPO,'--json','state,isDraft,headRefOid']))
    assert pr==dict(state='OPEN',isDraft=True,headRefOid=sha)
    record='14zzc-'+mode+'-dispatch-command.json';assert not (WORK/record).exists(),'STOP: a dispatch was already attempted'
    write(record,dict(head=sha,mode=mode,attempts=1,status='POST about to be sent; never repeat an ambiguous attempt'))
    args=['gh','workflow','run','os-image.yml','--repo',REPO,'--ref',BRANCH,'-f','rehearsal='+mode]
    if mode=='owner-tools': args+=['-f','probe_run='+str(proof['probe_run'])]
    result=subprocess.run(args,capture_output=True,text=True,timeout=60)
    write(record,dict(head=sha,mode=mode,attempts=1,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
    assert result.returncode==0,'STOP: failed/ambiguous dispatch response; no repeat POST'
    run=watcher.confirm(result.stdout,REPO,sha,BRANCH,guard.SETTINGS['titles'][mode],guard.api,
        lambda evidence:write('14zzc-'+mode+'-confirmation.json',evidence))
    write('14zzc-'+mode+'-run.json',run)
    print('DISPATCHED_ONCE',mode,run['id'],sha,run['html_url'])


def monitor(run_id):
    live_gate()
    info=guard.api('actions/runs/'+run_id);assert info['run_attempt']==1 and info['head_sha']==read('14zzc-one-push-scan.json')['checked_commit']
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
