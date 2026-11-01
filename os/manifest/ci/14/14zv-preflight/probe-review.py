import pathlib,json,re,hashlib
r=pathlib.Path.cwd();w=r/'.work/14';import sys
run=int(sys.argv[1]);base=w/('run-'+str(run));e=base/'evidence'
NATIVE_TESTS=json.loads((r/'os/manifest/ci/14/14zv-preflight/preparation.json').read_text())['whole_suite']['tests']

def read(p):return json.loads(p.read_text())
b=base
receipt=read(base/'receipt.json');assert receipt['status']=='success'
privacy=read(base/'14zv-privacy-classification.json');assert privacy['status']=='passed'
assert read(w/'gitleaks/14zv-probe-native.json')==[]
log=(base/'native.log').read_text(encoding='utf-8');matched=re.search(r'Ran (\d+) tests in ([\d.]+)s',log)
assert matched and int(matched[1])==NATIVE_TESTS and re.search(r'Z OK\s*$',log,re.M)
native=read(e/'14-native-owner-devices.json');assert native['status']=='passed' and native['helper_mutations']==0
assert native['protected_fixture_unchanged'] and native['all_fixture_mounts_unmounted_and_loops_detached']
iso=read(e/'installer/iso-download.json');assert iso['status']=='passed' and iso['bytes']==9068650496 and iso['sha256']==iso['downloaded_sha256']==iso['official_sha256']
proof=read(e/'two-disk/probe-result.json');assert proof['status']=='passed' and proof['installed'] is False
counter=read(e/'two-disk/probe-key-counter-result.json')
assert counter['status']=='passed' and counter['complete'] and counter['counts_only']
assert counter['counts']==dict(press=0,release=0,repeat=0,syn_dropped=0)
assert not counter['codes_recorded'] and not counter['values_recorded']
assert set(counter['autorepeat'])=={'delay_ms','period_ms'}
sample=read(e/'two-disk/probe-key-counter-sample-1.json')
assert sample['complete'] and sample['keys_released'] and sample['sequence']==1
assert sample['counts']==dict(press=0,release=0,repeat=0,syn_dropped=0)
unicode=read(e/'two-disk/probe-unicode-console.json');assert unicode['status']=='passed' and unicode['getter_only']
timings=[read(p)['keyboard_timing'] for p in (e/'two-disk').glob('*-owner-route.json')]
assert timings and all(t==dict(hold_ms=30,minimum_gap_ms=120) for t in timings)
transfers=[read(p) for p in (e/'two-disk').glob('*-transport.json')]
staged=[v for v in transfers if v.get('staged') is True]
assert staged and all(v['verified'] and all(x['status']=='passed' for x in v['steps']) for v in staged)
value=dict(status='passed independent probe acceptance inspection',run=run,head=receipt['head'],
    artifact=receipt,probe=proof,key_counter=counter,key_checkpoint=sample,unicode_console=unicode,keyboard_timings=timings,native_tests=int(matched[1]),native_seconds=float(matched[2]),native_skips=0,
    loop_checks=len(native['checks']),loop_helper_mutations=0,fixture_protected_unchanged=True,fixture_cleanup=True,
    iso=iso,staged_transfers=len(staged),staged_sha_and_syntax_verified=True,
    privacy=privacy,independent_audits=read(base/'independent-audits.json'))
(base/'14zv-probe-proof.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print('PROBE_ACCEPTED',value['native_tests'],'tests/',value['native_seconds'],'seconds;',len(staged),'guest tmpfs transfers verified; loop',value['loop_checks'],'checks; unknown artifact findings0')

sys.path.insert(0,str(r/'os/ci'))
from owner_keys import at_keycodes
at=[read(p) for p in (e/'two-disk').glob('boot-*-at-keyboard.json')]
assert at and all(v['name']=='AT Translated Set 2 keyboard' and v['bus']==17 and
    v['static_keycodes_checked']==len(at_keycodes()) and re.fullmatch('/dev/input/event[0-9]+',v['device']) for v in at)
health=[read(p) for p in (e/'two-disk').glob('*-xhci-health.json')]
assert health and all(v['counts_only'] is True and v['stop'] is False for v in health)
caps=read(e/'14-host-capabilities.json')
assert caps['qemu']['keyboard']=='i8042/ps2-kbd; qtree verified'
extra=dict(status='passed actual PS2 boot/static mappings and counts-only xHCI health records',at_boots=len(at),
    static_keycodes_checked=len(at_keycodes()),health_checkpoints=len(health),hardware='actual disposable runner/guest, not local stand-ins')
(b/'14zv-ps2-health-proof.json').write_text(json.dumps(extra,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PS2_HEALTH_ACCEPTED',len(at),len(health))
