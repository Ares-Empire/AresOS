"""Scan and commit closing evidence locally; never pushes or dispatches."""
import datetime,hashlib,json,pathlib,re,shutil,subprocess
r=pathlib.Path.cwd();w=r/'.work/14';out=r/'os/manifest/ci/14/14zzb-round';LOCAL='211df982b5bf080b0167b8fe6e8dd3c5eb264fe8';H='211df982b5bf080b0167b8fe6e8dd3c5eb264fe8'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==LOCAL
assert subprocess.run(['git','diff','--cached','--quiet']).returncode==0
pending=w/'14zzb/pending-closing';assert not pending.exists();pending.mkdir()
scanner=w/'gitleaks/gitleaks.exe';assert hashlib.sha256(scanner.read_bytes()).hexdigest()=='671591bd75e11fcd4a25732852afbbf0c3892b368181164ba19aa72e7513af8e'
assert subprocess.check_output([str(scanner),'version'],text=True).strip()=='8.21.2'
for setting in ('GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT'):
 assert re.search(r'<[^<>\s]+@users\.noreply\.github\.com>',subprocess.check_output(['git','var',setting],text=True)),'STOP: non-noreply commit identity'
def order(v):
 if isinstance(v,list):return [order(x) for x in v]
 if isinstance(v,dict):
  keys=[k for k in v if k.endswith('sha256')];return {k:order(v[k]) for k in keys+[k for k in v if k not in keys]}
 return v
def write(p,v):p.write_text(json.dumps(order(v),indent=2)+'\n',encoding='utf-8',newline='\n')
def paths():
 names=sorted(set(subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()+subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()))
 assert names and all(p in ('reviews/14-owner-tools/REPORT.md','reviews/14-owner-tools/BUDGET.json') or p.startswith('os/manifest/ci/14/14zzb-round/') for p in names),names
 return names
def copy_pending():
 for name in paths():
  p=r/name;assert p.is_file() and not p.is_symlink();dest=pending/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
def scan(args,name):
 p=w/'gitleaks'/name;subprocess.run([str(scanner),*args,'--redact=100','--no-banner','--log-level=error','--report-format=json','--report-path',str(p)],check=True)
 assert json.loads(p.read_text())==[],'STOP: new privacy finding'
 return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(r).as_posix(),findings=0,exit_code=0)
copy_pending();history=scan(['git','.','--log-opts=--all'],'14zzb-closing-history.json');first=scan(['dir',str(pending),'--config',str(r/'.gitleaks.toml')],'14zzb-closing-initial-pending.json')
write(out/'local-privacy.json',dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),checked_parent=LOCAL,existing_pushed_head=H,version='8.21.2',history=history,pending=first,scanner=dict(sha256=hashlib.sha256(scanner.read_bytes()).hexdigest(),path='.work/14/gitleaks/gitleaks.exe'),one_push_before_dispatch=True,existing_pushed_head_privacy=dict(head=H,actual_hook_exit_code=0,exact_range_exit_code=0,checker_version='8.30.1',personal_terms_skipped_warning_absent=True),new_pushes=0,new_ignore_or_rule_entries=False,closing_commit_local_only=True,further_dispatch_authorized=False))
files=[dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(r).as_posix()) for p in sorted(out.iterdir()) if p.is_file() and p.name!='files.json'];write(out/'files.json',dict(files=files))
copy_pending();scan(['dir',str(pending),'--config',str(r/'.gitleaks.toml')],'14zzb-closing-final-pending.json')
with (w/'14zzb/hash-order.log').open('wb') as f:
 result=subprocess.run(['wsl.exe','--exec','bash','-lc','cd /mnt/c/Users/pab/AresOS-14-owner-tools && TMPDIR=$PWD/.work/14/local/tmp PATH=$PWD/.work/14/local/bin:$PATH PYTHONPATH=os/ci:os/tests python3 -B -m unittest test_owner_equality.EqualityTest.test_package_hash_manifests_put_hashes_before_paths'],stdout=f,stderr=subprocess.STDOUT)
assert result.returncode==0,'STOP: hash-order regression'
subprocess.run(['git','diff','--check'],check=True)
frozen=['os/ci','os/tests','os/owner-tools','os/release','os/config','os/policy','.github','.gitleaksignore','.gitleaks.toml','os/manifest/base.json','os/manifest/release.json','os/packages.lock.json','os/keys','os/Containerfile.keyboard','docs/INSTALL.md','docs/EMERGENCY.md','docs/RELEASE-GATE.md','HANDOFF.md','STATE.md']
subprocess.run(['git','diff','--exit-code',H,'--',*frozen],check=True)
assert isinstance(json.loads((r/'reviews/14-owner-tools/BUDGET.json').read_text())['acceptance_met'],bool)
names=paths();subprocess.run(['git','add','--',*names],check=True);subprocess.run(['git','diff','--cached','--check'],check=True)
for row in files:assert hashlib.sha256(subprocess.check_output(['git','show',':'+row['path']])).hexdigest()==row['sha256'],row['path']
subprocess.run(['git','commit','-m','14zzb: record probe31 and qualification20 results locally'],check=True)
new=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert subprocess.check_output(['git','rev-parse','HEAD^'],text=True).strip()==LOCAL
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
assert subprocess.check_output(['git','rev-parse','origin/pkg/14-owner-tools'],text=True).strip()==H
post=scan(['git','.','--log-opts=--all'],'14zzb-closing-committed-history.json')
write(w/'14zzb/closing-commit.json',dict(commit=new,parent=LOCAL,pushed_head=H,commit_local_only=True,pushed=False,new_pushes=0,new_probes=1,qualification=41324240079,reruns=0,pinned_version='8.21.2',postcommit_history=post,pending_findings=0,hash_order_passed=True,diff_check_passed=True,frozen_paths_unchanged=True,status='Round closed locally after terminal qualification20; no more push or dispatch'))
print('LOCAL_14ZZB_CLOSING_COMMIT',new,'history/pending0; no push/probe/rerun/merge',flush=True)
