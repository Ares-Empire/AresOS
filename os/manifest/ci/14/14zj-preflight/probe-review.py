import pathlib,json,re,hashlib
r=pathlib.Path.cwd();w=r/'.work/14';import sys
run=int(sys.argv[1]);base=w/('run-'+str(run));e=base/'evidence'
def read(p):return json.loads(p.read_text())
receipt=read(base/'receipt.json');assert receipt['status']=='success'
privacy=read(base/'14zj-privacy-classification.json');assert privacy['status']=='passed'
assert read(w/'gitleaks/14zj-probe-native.json')==[]
log=(base/'native.log').read_text(encoding='utf-8');matched=re.search(r'Ran (\d+) tests in ([\d.]+)s',log)
assert matched and int(matched[1])==470 and re.search(r'Z OK\s*$',log,re.M)
native=read(e/'14-native-owner-devices.json');assert native['status']=='passed' and native['helper_mutations']==0
assert native['protected_fixture_unchanged'] and native['all_fixture_mounts_unmounted_and_loops_detached']
iso=read(e/'installer/iso-download.json');assert iso['status']=='passed' and iso['bytes']==9068650496 and iso['sha256']==iso['downloaded_sha256']==iso['official_sha256']
proof=read(e/'two-disk/probe-result.json');assert proof['status']=='passed' and proof['installed'] is False
transfers=[read(p) for p in (e/'two-disk').glob('*-transport.json')]
staged=[v for v in transfers if v.get('staged') is True]
assert staged and all(v['verified'] and all(x['status']=='passed' for x in v['steps']) for v in staged)
value=dict(status='passed independent probe acceptance inspection',run=run,head=receipt['head'],
    artifact=receipt,probe=proof,native_tests=int(matched[1]),native_seconds=float(matched[2]),native_skips=0,
    loop_checks=len(native['checks']),loop_helper_mutations=0,fixture_protected_unchanged=True,fixture_cleanup=True,
    iso=iso,staged_transfers=len(staged),staged_sha_and_syntax_verified=True,
    privacy=privacy,independent_audits=read(base/'independent-audits.json'))
(base/'14zj-probe-proof.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print('PROBE_ACCEPTED',value['native_tests'],'tests/',value['native_seconds'],'seconds;',len(staged),'guest tmpfs transfers verified; loop',value['loop_checks'],'checks; unknown artifact findings0')
