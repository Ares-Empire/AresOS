"""Record passed native subchecks without claiming whole-probe acceptance."""
import hashlib,json,pathlib,subprocess,sys
r=pathlib.Path.cwd();w=r/'.work/14';run=41363231606;b=w/('run-'+str(run));e=b/'evidence'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=read(b/'receipt.json');head=receipt['head'];assert receipt['status']=='failure'
subprocess.run([sys.executable,'-X','utf8',str(w/'14zzd-native-timing.py'),str(run)],check=True)
n=read(e/'14-native-owner-devices.json');assert n['sha']==head and n['status']=='passed'
assert n['helper_mutations']==0 and n['protected_fixture_unchanged'] and n['all_fixture_mounts_unmounted_and_loops_detached']
k=read(e/'14-counter-kernel.json');assert k['sha']==head and k['status']=='passed' and k['real_kernel'] and not k['skipped']
assert k['negative_control']['counts']==dict(press=0,release=1,repeat=0,syn_dropped=0) and not k['negative_control']['comparison']['matches']
assert k['fixed']['counts']==dict(press=1,release=1,repeat=0,syn_dropped=0) and k['fixed']['comparison']['matches']
iso=read(e/'installer/iso-download.json');assert iso['status']=='passed' and iso['bytes']==9068650496
assert iso['sha256']==iso['downloaded_sha256']==iso['official_sha256']
v=dict(status='passed native subchecks only; whole probe STOP before guest boot',run=run,head=head,
 native_tests=627,native_seconds=163.918,native_skips=0,native_timing_bound_unchanged_and_passed=True,
 loop_checks=len(n['checks']),loop_helper_mutations=0,protected_fixture_unchanged=True,all_fixture_mounts_unmounted_and_loops_detached=True,
 kernel_counter_native_real=True,kernel_counter_skipped=False,kernel_negative_control_detected_flush=True,kernel_fixed_separate_client_preserved_both_events=True,
 iso_bytes=iso['bytes'],iso_sha256=iso['sha256'],official_checksum_equal_to_pin=True,
 guest_started=False,qualification_dispatched=False,probe_accepted=False,
 files=[dict(sha256=sha(p),path=p.relative_to(e).as_posix()) for p in (e/'14-native-owner-devices.json',e/'14-counter-kernel.json',e/'14-host-capabilities.json',e/'installer/iso-download.json',e/'owner-auth-cleanup.json')])
(w/'14zzd/partial-native-proof.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
print('NATIVE_PARTIAL_PROOF',v['native_tests'],v['loop_checks'],'whole probe remains STOP')
