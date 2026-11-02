"""Local checks before readiness; no git mutation, push or dispatch."""
import hashlib, json, pathlib, shutil, subprocess
r=pathlib.Path.cwd(); w=r/'.work/14'; h='211df982b5bf080b0167b8fe6e8dd3c5eb264fe8'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==h
out=r/'os/manifest/ci/14/14zzb-round'
assert json.loads((out/'round.json').read_text())['acceptance_met'] is True
names=sorted(set(subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()+subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()))
assert names and all(n in ('reviews/14-owner-tools/REPORT.md','reviews/14-owner-tools/BUDGET.json') or n.startswith('os/manifest/ci/14/14zzb-round/') for n in names)
pending=w/'14zzb/pending-readiness'; assert not pending.exists(); pending.mkdir()
assert pending.resolve().is_relative_to(r.resolve())
for n in names:
    p=r/n; assert p.is_file() and not p.is_symlink()
    target=pending/n; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,target)
scanner=w/'gitleaks/gitleaks.exe'
assert hashlib.sha256(scanner.read_bytes()).hexdigest()=='671591bd75e11fcd4a25732852afbbf0c3892b368181164ba19aa72e7513af8e'
assert subprocess.check_output([str(scanner),'version'],text=True).strip()=='8.21.2'
for args,name in [(['git','.','--log-opts=--all'],'history'),(['dir',str(pending),'--config',str(r/'.gitleaks.toml')],'pending')]:
    report=w/'gitleaks'/('14zzb-readiness-'+name+'.json')
    subprocess.run([str(scanner),*args,'--redact=100','--no-banner','--log-level=error','--report-format=json','--report-path',str(report)],check=True)
    assert json.loads(report.read_text())==[]
with (w/'14zzb/readiness-hash-order.log').open('wb') as f:
    subprocess.run(['wsl.exe','--exec','bash','-lc','cd /mnt/c/Users/pab/AresOS-14-owner-tools && TMPDIR=$PWD/.work/14/local/tmp PATH=$PWD/.work/14/local/bin:$PATH PYTHONPATH=os/ci:os/tests python3 -B -m unittest test_owner_equality.EqualityTest.test_package_hash_manifests_put_hashes_before_paths'],stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run(['git','diff','--check'],check=True)
frozen=['os/ci','os/tests','os/owner-tools','os/release','os/config','os/policy','.github','.gitleaksignore','.gitleaks.toml','os/manifest/base.json','os/manifest/release.json','os/packages.lock.json','os/keys','os/Containerfile.keyboard','docs/INSTALL.md','docs/EMERGENCY.md','docs/RELEASE-GATE.md','HANDOFF.md','STATE.md']
subprocess.run(['git','diff','--exit-code',h,'--',*frozen],check=True)
value=dict(status='passed local closing privacy/hash-order/diff/frozen-path checks',head=h,pending_findings=0,history_findings=0,pinned_gitleaks='8.21.2',acceptance_met=True,ready_action_authorized_by_prior_acceptance_instruction=True,pushes=0,dispatches=0)
(w/'14zzb/closing-checks.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('CLOSING_CHECKS_PASSED; history/pending0; frozen paths unchanged; hash order/diff passed')
