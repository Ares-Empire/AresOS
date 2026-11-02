"""Finish the final zero-cost checks, in dependency order. No git/network action."""
import hashlib,json,pathlib,subprocess,time
r=pathlib.Path.cwd();w=r/'.work/14/14zzc'
sources={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in ('os/owner-tools/owner.py','os/owner-tools/bootstrap.py','os/owner-tools/payload/SHA256SUMS','os/owner-tools/commands.json','os/tests/test_owner_abandon.py','os/tests/test_owner_hidden.py','os/tests/test_owner_bootstrap.py')}
deadline=time.monotonic()+1200
while True:
 t=(w/'walk-post-root-link.log').read_text()
 if t.strip():
  v=json.loads(t);assert v['status']=='passed' and v['hidden_pairs']==27 and v['composed_guest_commands']==1152;break
 assert time.monotonic()<deadline,'STOP: local stand-in walk did not finish within20minutes; inspect only local processes'
 time.sleep(2)
print('FINAL_WALK_PASSED; strict checks and whole suite starting',flush=True)
for script,label in [('14zzc-probe-walk.py','probe-walk'),('14zzc-syntax.py','strict'),('14zzc/whole.py','whole-suite')]:
 assert all(hashlib.sha256((r/p).read_bytes()).hexdigest()==s for p,s in sources.items()),'STOP: source changed during final checks'
 command='cd /mnt/c/Users/pab/AresOS-14-owner-tools && export TMPDIR="$PWD/.work/14/local/tmp" && export PATH="$PWD/.work/14/local/bin:$PATH" && python3 -B .work/14/'+script
 with (w/(label+'.log')).open('wb') as log:result=subprocess.run(['wsl.exe','--exec','bash','-lc',command],stdout=log,stderr=subprocess.STDOUT)
 assert result.returncode==0,(label,result.returncode)
 assert all(hashlib.sha256((r/p).read_bytes()).hexdigest()==s for p,s in sources.items()),'STOP: source changed during final checks'
 print('FINAL_LOCAL_PASSED',label,flush=True)
