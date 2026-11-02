"""Scope, scan and commit the reviewed owner fixes. Never pushes."""
import datetime,hashlib,json,pathlib,re,shutil,subprocess,sys
r=pathlib.Path.cwd();w=r/'.work/14';out=r/'os/manifest/ci/14/14zze-preflight';initial='c0051ab'
sys.path.insert(0,str(r/'os/ci'));import checkout_sources as checkout
assert subprocess.check_output(['git','rev-parse','--short=7','HEAD'],text=True).strip()==initial
assert subprocess.run(['git','diff','--cached','--quiet']).returncode==0
paths=sorted(set(subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()+subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()))
allowed={'os/ci/checkout_sources.py','os/tests/test_checkout_sources.py','os/tests/fixtures/owner-tools/14zzd-checkout-sources.json',
 'reviews/14-owner-tools/BUDGET.json','reviews/14-owner-tools/REPORT.md',
 'os/manifest/ci/14/host-walk/result.json','os/manifest/ci/14/host-walk/guest-commands.json'}
assert paths and all(p in allowed or p.startswith('os/manifest/ci/14/14zze-preflight/') for p in paths),paths
prep=json.loads((out/'preparation.json').read_text());assert prep['whole_suite']['tests']==630 and not prep['whole_suite']['unknown_failures'] and prep['whole_suite']['skips']==0
assert prep['timing_projection']['vm_with_margin_minutes']<=200 and prep['timing_projection']['whole_job_with_margin_minutes']<=240
for k in ('GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT'):assert re.search(r'<[^<>\s]+@users\.noreply\.github\.com>',subprocess.check_output(['git','var',k],text=True)),'STOP: non-noreply identity'
frozen=['os/owner-tools','os/ci/owner_vm.py','os/ci/two_disk_vm.py','os/ci/rehearsal_guard.py','os/config','os/release','os/policy','os/manifest/base.json','os/manifest/release.json','os/packages.lock.json','os/keys','os/Containerfile.keyboard','os/manifest/ci/14/keyboard-sources','os/manifest/ci/13/13f-zero-cost/qemu-keymap.csv','.gitleaksignore','.gitleaks.toml','.gitattributes','os/ci/rehearsal-packages.json','docs','.github']
subprocess.run(['git','diff','--exit-code',initial,'--',*frozen],check=True)
old=json.loads(subprocess.check_output(['git','show',initial+':os/ci/rehearsal-packages.json']))
assert json.loads((r/'os/ci/rehearsal-packages.json').read_text())==old
subprocess.run(['git','diff','--check'],check=True)
check_env=dict(__import__('os').environ,PYTHONPATH=str(r/'os/ci')+__import__('os').pathsep+str(r/'os/tests'))
with (w/'14zze/final-checkout-regressions.log').open('wb') as log:
 subprocess.run([sys.executable,'-X','utf8','-m','unittest','-v','test_checkout_sources'],env=check_env,stdout=log,stderr=subprocess.STDOUT,check=True)
pending=w/'14zze/pending-preflight-lf';assert not pending.exists();pending.mkdir()
for name in paths:
 p=r/name;assert p.is_file() and not p.is_symlink();dest=pending/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
scanner=w/'gitleaks/gitleaks.exe';assert hashlib.sha256(scanner.read_bytes()).hexdigest()=='671591bd75e11fcd4a25732852afbbf0c3892b368181164ba19aa72e7513af8e'
for args,label in [(['dir',str(pending),'--config',str(r/'.gitleaks.toml')],'preflight-pending'),(['git','.','--log-opts=--all'],'preflight-history')]:
 report=w/'gitleaks'/('14zze-'+label+'.json');subprocess.run([str(scanner),*args,'--redact=100','--no-banner','--log-level=error','--report-format=json','--report-path',str(report)],check=True);assert json.loads(report.read_text())==[]
with (w/'14zze/hash-order-final.log').open('wb') as stream:
 result=subprocess.run(['wsl.exe','--exec','bash','-lc','cd /mnt/c/Users/pab/AresOS-14-owner-tools && TMPDIR=$PWD/.work/14/local/tmp PATH=$PWD/.work/14/local/bin:$PATH PYTHONPATH=os/ci:os/tests python3 -B -m unittest test_owner_equality.EqualityTest.test_package_hash_manifests_put_hashes_before_paths'],stdout=stream,stderr=subprocess.STDOUT)
assert result.returncode==0,'STOP: hash order regression'
subprocess.run(['git','add','--',*paths],check=True);subprocess.run(['git','diff','--cached','--check'],check=True)
checkout.verify_git(r,checkout.merge(checkout.active_tables(r)),ref=None)
checkout.verify_git(r,checkout.records(r,paths),ref=None)
for row in prep['local_tool_bindings']:
 assert hashlib.sha256((w/row['local']).read_bytes()).hexdigest()==row['local_sha256'],row['local']
subprocess.run(['git','commit','-m','14zze: bind every current source to Git checkout bytes'],check=True)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
report=w/'gitleaks/14zze-committed-history.json';subprocess.run([str(scanner),'git','.','--log-opts=--all','--redact=100','--no-banner','--log-level=error','--report-format=json','--report-path',str(report)],check=True);assert json.loads(report.read_text())==[]
(w/'14zze-one-push-scan.json').write_text(json.dumps(dict(checked_commit=head,findings=0,exit_code=0,pinned_version='8.21.2',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n',encoding='utf-8',newline='\n')
print('LOCAL_14ZZE_PREFLIGHT_COMMIT',head,'pending/history0; no push yet',flush=True)
