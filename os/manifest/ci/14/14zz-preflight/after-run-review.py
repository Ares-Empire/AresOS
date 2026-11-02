"""Retain and independently check one completed real run; never dispatches."""
import hashlib,json,pathlib,shutil,subprocess,sys
r=pathlib.Path.cwd();w=r/'.work/14';sys.path.insert(0,str(r/'os/ci'))
import rehearsal_guard as guard
guard.configure('14')
mode,run=sys.argv[1:];assert mode in ('probe','owner-tools') and run.isdigit()
expected=json.loads((w/('14zz-'+mode+'-run.json')).read_text());assert expected['id']==int(run)
head=json.loads((w/'14zz-one-push-scan.json').read_text())['checked_commit']
actual=guard.api('actions/runs/'+run)
assert actual['status']=='completed' and actual['head_sha']==head and actual['run_attempt']==1
def execute(script,*args):subprocess.run([sys.executable,'-B','-X','utf8',str(r/script),*args],check=True)
basic=w/'14zz'/('basic-'+run)
if not basic.exists():execute('.work/14/14zz-basic.py',run)
assert json.loads((basic/'receipt.json').read_text())['head']==head
execute('.work/14/14zz/log-review.py',run)
artifacts=json.loads((basic/'artifacts.json').read_text())['artifacts']
targets=[x for x in artifacts if x['name']=='two-disk-evidence' and not x['expired']]
if not targets:
    assert actual['conclusion']!='success','STOP: successful workflow has no evidence artifact'
    print('CI_STOP_NO_ARTIFACT; actual terminal metadata/logs retained',run)
    raise SystemExit(20)
assert len(targets)==1
base=w/('run-'+run)
if not base.exists():execute('.work/14/14zz-collect.py',run)
receipt=json.loads((base/'receipt.json').read_text());assert receipt['run']==int(run) and receipt['head']==head
shutil.copyfile(basic/'log-privacy.json',base/'14zz-log-classification.json')
scanner=w/'gitleaks/gitleaks.exe'
assert hashlib.sha256(scanner.read_bytes()).hexdigest()=='671591bd75e11fcd4a25732852afbbf0c3892b368181164ba19aa72e7513af8e'
def scan(folder,report,allow_findings=False):
    result=subprocess.run([str(scanner),'dir',folder.relative_to(r).as_posix(),'--config',str(r/'.gitleaks.toml'),'--redact=100',
        '--no-banner','--log-level=error','--report-format=json','--report-path',str(report)])
    assert result.returncode in ((0,1) if allow_findings else (0,)),'STOP: scanner failed or new log finding'
    rows=json.loads(report.read_text());assert isinstance(rows,list)
    return rows
report=w/'gitleaks'/('14zz-'+mode+'-artifact.json')
rows=scan(base/'evidence',report,True)
if (base/'evidence/installer/squashfs-files.txt').exists():
    execute('reviews/14-owner-tools/classify-artifacts.py',run,str(report),str(base/'14zz-privacy-classification.json'))
else:
    assert not rows,'STOP: unclassified finding before the reviewed ISO listing existed'
    (base/'14zz-privacy-classification.json').write_text(json.dumps(dict(status='no findings; early CI STOP',run=int(run),head=head,findings=0))+'\n')
if (base/'native.log').exists():
    logs=base/'native-scan';logs.mkdir(exist_ok=True);shutil.copyfile(base/'native.log',logs/'native.log')
    assert not scan(logs,w/'gitleaks'/('14zz-'+mode+'-native.json'))
if actual['conclusion']!='success':
    print('CI_STOP; completed actual evidence retained/scanned; no rerun',run)
    raise SystemExit(20)
execute('.work/14/14l-audits.py',run)
execute('.work/14/14zz-native-timing.py',run)
execute('.work/14/14zz/kernel-review.py',run)
execute('.work/14/14zz-'+('probe-proof.py' if mode=='probe' else 'qualification-proof.py'),run)
print('ACCEPTED_REAL_RUN',mode,run,head,str(json.loads((base/'14zz-probe-proof.json' if mode=='probe' else base/'14zz-qualification-proof.json').read_text())['native_tests'])+' native tests/0skips; privacy/classification/raw audits/PS2 checks passed')
