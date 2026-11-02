"""Scan and commit terminal receipts/status locally. Never pushes or dispatches."""
import datetime,hashlib,json,pathlib,re,shutil,subprocess,sys
r=pathlib.Path.cwd();w=r/'.work/14';d=r/'os/manifest/ci/14/14zze-round'
sys.path.insert(0,str(r/'os/ci'));import checkout_sources as checkout
round=json.loads((d/'round.json').read_text());head=round['head']
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
assert subprocess.run(['git','diff','--cached','--quiet']).returncode==0
for k in ('GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT'):assert re.search(r'<[^<>\s]+@users\.noreply\.github\.com>',subprocess.check_output(['git','var',k],text=True))
subprocess.run(['git','diff','--exit-code',head,'--','os/ci','os/owner-tools','os/tests','os/config','os/release','os/keys','os/packages.lock.json','os/manifest/base.json','os/manifest/release.json','.github','.gitleaksignore','.gitleaks.toml','docs/RELEASE-GATE.md'],check=True)
status=json.loads((d/'guide-status.json').read_text());assert all(v['bash_blocks_unchanged'] and v['open_gates_unchanged'] for v in status['files'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
tools=[]
for name in ('archive-round.py','close-report.py','commit-report.py'):
 p=w/'14zze'/name;shutil.copyfile(p,d/name);row=checkout.records(r,[(d/name).relative_to(r).as_posix()])[0];tools.append(dict(sha256=row['sha256'],local_sha256=sha(p),path='.work/14/14zze/'+name,archive=name))
(d/'closing-tools.json').write_text(json.dumps(dict(status='local-only closing helpers',files=tools),indent=2)+'\n',encoding='utf-8',newline='\n')
(d/'files.json').write_text(json.dumps(dict(files=checkout.records(r,[p.relative_to(r).as_posix() for p in sorted(d.iterdir()) if p.is_file() and p.name!='files.json']),binding_format='git-checkout-bytes-v1'),indent=2)+'\n',encoding='utf-8',newline='\n')
paths=sorted(set(subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()+subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()))
assert paths and all(p in ('docs/INSTALL.md','docs/EMERGENCY.md','reviews/14-owner-tools/REPORT.md','reviews/14-owner-tools/BUDGET.json') or p.startswith('os/manifest/ci/14/14zze-round/') for p in paths),paths
subprocess.run(['git','diff','--check'],check=True)
with (w/'14zze/closing-hash-order.log').open('wb') as log:
 q=subprocess.run(['wsl.exe','--exec','bash','-lc','cd /mnt/c/Users/pab/AresOS-14-owner-tools && PYTHONPATH=os/ci:os/tests python3 -B -m unittest test_owner_equality.EqualityTest.test_package_hash_manifests_put_hashes_before_paths'],stdout=log,stderr=subprocess.STDOUT)
assert q.returncode==0,'STOP: closing hash order'
pending=w/'14zze/pending-closing';assert not pending.exists();pending.mkdir()
for name in paths:
 p=r/name;assert p.is_file() and not p.is_symlink();dest=pending/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
scanner=w/'gitleaks/gitleaks.exe';assert sha(scanner)=='671591bd75e11fcd4a25732852afbbf0c3892b368181164ba19aa72e7513af8e'
for args,label in [(['dir',str(pending),'--config',str(r/'.gitleaks.toml')],'closing-pending'),(['git','.','--log-opts=--all'],'closing-before-history')]:
 p=w/'gitleaks'/('14zze-'+label+'.json');subprocess.run([str(scanner),*args,'--redact=100','--no-banner','--log-level=error','--report-format=json','--report-path',str(p)],check=True);assert json.loads(p.read_text())==[]
subprocess.run(['git','add','--',*paths],check=True);subprocess.run(['git','diff','--cached','--check'],check=True)
checkout.verify_git(r,checkout.records(r,paths),ref=None)
subprocess.run(['git','commit','-m','14zze: record probe34 and qualification21 outcome locally'],check=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
p=w/'gitleaks/14zze-closing-history.json';subprocess.run([str(scanner),'git','.','--log-opts=--all','--redact=100','--no-banner','--log-level=error','--report-format=json','--report-path',str(p)],check=True);assert json.loads(p.read_text())==[]
(w/'14zze/closing-commit.json').write_text(json.dumps(dict(status='committed locally only; no second push',commit=commit,qualified_or_stopped_head=head,acceptance_met=round['acceptance_met'],pinned_gitleaks_findings=0,checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n',encoding='utf-8',newline='\n')
print('LOCAL_ONLY_CLOSING_COMMIT',commit,'NO PUSH')
