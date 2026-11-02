"""Zero-cost checks in dependency order; default Python matches native CI."""
import hashlib,json,pathlib,re,subprocess,time
r=pathlib.Path.cwd();w=r/'.work/14/14zzd'
deadline=time.monotonic()+3600
while True:
 texts=[(w/('affected-'+name+'.log')).read_text(encoding='utf-8') for name in ('normal','no-bytecode')]
 if all(re.search(r'Ran \d+ tests in [\d.]+s\s+OK\s*$',t,re.M) and 'FAILED (' not in t for t in texts):break
 assert not any(re.search(r'^FAILED \(',t,re.M) for t in texts),'STOP: affected module failure; preserve logs'
 assert time.monotonic()<deadline,'STOP: local affected checks did not finish'
 time.sleep(2)
print('BOTH_BYTECODE_MODES_PASSED',flush=True)
files=['os/ci/rehearsal-packages.json','os/tests/owner_bundle_fixture.py','os/tests/owner_fuse_shim.py']
files += [p.relative_to(r).as_posix() for p in (r/'os/tests').glob('test_owner_*.py')]
sources={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in files}
for script,label in [('14zzd-walk.py','final-walk'),('14zzd-probe-walk.py','probe-walk'),('14zzd-syntax.py','strict'),('14zzd/whole.py','whole-suite')]:
 assert all(hashlib.sha256((r/p).read_bytes()).hexdigest()==s for p,s in sources.items())
 command='cd /mnt/c/Users/pab/AresOS-14-owner-tools && env -u PYTHONDONTWRITEBYTECODE TMPDIR="$PWD/.work/14/local/tmp" PATH="$PWD/.work/14/local/bin:$PATH" python3 .work/14/'+script
 with (w/(label+'.log')).open('wb') as log:result=subprocess.run(['wsl.exe','--exec','bash','-lc',command],stdout=log,stderr=subprocess.STDOUT)
 assert result.returncode==0,(label,result.returncode)
 assert all(hashlib.sha256((r/p).read_bytes()).hexdigest()==s for p,s in sources.items())
 print('FINAL_LOCAL_PASSED',label,flush=True)
