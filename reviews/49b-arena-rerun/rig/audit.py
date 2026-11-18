"""Audit every attempt, frozen settings/order, frame completeness and the measured source identity."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
WT=HERE.parents[2]
WORK=WT/'.work/pkg49b'
accepted=json.loads((ROOT/'accepted.json').read_text())
assert len(accepted)==18
expected=[]
for i,order in enumerate(('AB','BA','BA','AB','AB','BA'),1):
    expected += [f'flat-{i}-'+('control' if k=='A' else 'arena') for k in order]
for i,order in enumerate(('AB','BA'),1):
    expected += [f'create-{i}-'+('control' if k=='A' else 'arena') for k in order]
expected += ['nether-control','nether-arena']
assert list(accepted)==expected
freeze=subprocess.check_output(['git','show','2ddcb93f:reviews/49b-arena-rerun/REPORT.md'],text=True,cwd=WT).split('## Done')[0]
assert (ROOT/'REPORT.md').read_text().split('## Done')[0]==freeze,'frozen line/plan changed'


def bounds(values):
    values=list(values)
    return {'min':min(values),'median':statistics.median(values),'max':max(values)}


attempts=[]
for file in sorted((ROOT/'runs').glob('*/attempt.json'))+sorted((ROOT/'failures').glob('*/attempt.json')):
    attempts.append(json.loads(file.read_text()))
rows={};objects=set();baseline_flags=None
for slot,name in accepted.items():
    out=ROOT/'runs'/name
    summary=json.loads((out/'summary.json').read_text())
    proof=json.loads((out/'provenance.json').read_text())
    attempt=json.loads((out/'attempt.json').read_text())
    assert attempt['accepted'] and not attempt['contaminated'] and not attempt['utility']
    flags=sorted(proof['flags'])
    if baseline_flags is None:baseline_flags=flags
    assert flags==baseline_flags,(slot,'different JVM flags')
    env=proof['environment']
    assert env['MALLOC_ARENA_MAX']==('2' if slot.endswith('arena') else '')
    assert env['GLIBC_TUNABLES']==env['JE_MALLOC_CONF']==''
    assert env['DISPLAY']!=':0' and env['WAYLAND_DISPLAY']!='wayland-0'
    assert env['__GLX_VENDOR_LIBRARY_NAME']=='nvidia' and env['ALSOFT_DRIVERS']=='null'
    settings=summary['settings']
    for k,value in {'RD':'8','SD':'5','HEAP':'1024','MIN_HEAP':'256','MEMHIGH':'2560M','NMT':'1','PROBE':'0','FREEZE':'0','RECLAIM':'','COVER_ACTION':'none','SETTLE':'120','WINDOW':'60','COVER':'300'}.items():
        assert settings[k]==value,(slot,k,settings[k])
    options=dict(line.split(':',1) for line in (out/'options.txt').read_text().splitlines() if ':' in line)
    assert options['renderDistance']=='8' and options['simulationDistance']=='5' and options['maxFps']=='120'
    assert all(not snap['frozen'] and snap['memory_high']=='2684354560' for snap in summary['snapshots'].values())
    assert {'settled','stand','flight','covered0','covered1m','covered2m','covered3m','covered4m','covered5m','wake'}<=summary['snapshots'].keys()
    objects.add(tuple(proof['git_objects'][k] for k in ('mod_tree','helper_blob','labwc_blob')))
    raw=WORK/'rigs'/name
    frames=[int(line) for line in (raw/'frames.txt').read_text().splitlines() if line.isdigit()]
    marks={k:int(v) for k,v in (line.split() for line in (out/'marks.txt').read_text().splitlines())}
    assert summary['lost_frames']==0 and all(a<b for a,b in zip(frames,frames[1:]))
    required_end=max(marks['flight_end'],marks.get('joined',0)+30_000_000_000 if slot.startswith('create-') else 0)
    assert frames[-1]>=required_end,(slot,'recorder stopped before required window ended')
    evidence=json.loads((out/'decisive-frames.json').read_text())
    for label,record in evidence.items():
        before=[t for t in frames if t<record['start_ns']]
        assert record['timestamps_ns']==before[-1:]+[t for t in frames if record['start_ns']<=t<record['end_ns']]
    host=[json.loads(line) for line in (out/'host-watch.jsonl').read_text().splitlines()]
    assert host and not any(p['kind'] in ('gradle','game') for h in host for p in h['external_java'])
    start=json.loads((out/'host-start.json').read_text())
    assert start['memory_kib']['MemAvailable']>=6*1024*1024,(slot,'launch below floor')
    game=(raw/'game.txt').read_text(errors='replace')
    devices=[line.split('Using graphics device: ',1)[1] for line in game.splitlines() if 'Using graphics device: ' in line]
    assert devices and all('NVIDIA' in device for device in devices),(slot,'renderer not confirmed')
    rows[slot]={'attempt':name,'source_revision':proof['git_objects']['revision'],'source_objects':proof['git_objects'],
        'game_environment':env,'jvm_flags':proof['flags'],'launch_available_mib':start['memory_kib']['MemAvailable']//1024,
        'host_available_mib':bounds(h['memory_kib']['MemAvailable']//1024 for h in host),
        'host_load1':bounds(h['loadavg'][0] for h in host),
        'selected_process_count_ranges':{key:bounds(h['process_counts'].get(key,0) for h in host) for key in sorted({k for h in host for k in h['process_counts']})},
        'host_max_sample_gap_s':max((b['monotonic_ns']-a['monotonic_ns'])/1e9 for a,b in zip(host,host[1:])),
        'external_build_game_samples':0,'required_frames_covered':True,'frame_count':len(frames),'renderer':devices,
        'jar_sha256':proof['jars_sha256'],'java_executable_sha256':proof['executable_sha256']}
assert len(objects)==1,'measured source changed'
# Same fixture identity routine as the scheduler; the bases must remain byte-for-byte unchanged.
import importlib.util
spec=importlib.util.spec_from_file_location('schedule',HERE/'schedule.py');schedule=importlib.util.module_from_spec(spec);spec.loader.exec_module(schedule)
fixtures=json.loads((ROOT/'fixture-hashes.json').read_text())
for kind,name in [('flat','AresHub-base'),('nether','AresHub-nether-base')]:
    assert schedule.fingerprint(WORK/name)==fixtures[kind]
result={'pass_line_commit':'2ddcb93f','frozen_prefix_sha256':hashlib.sha256(freeze.encode()).hexdigest(),'accepted_slots':expected,
        'attempts':attempts,'measurement_count':len(accepted),'fixture_bases_unchanged':True,'source_objects_identical':True,'runs':rows}
(ROOT/'verification/measurement-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'{len(accepted)} accepted measurements; frozen line/order/settings/source/frames/fixtures audited; all attempts retained.')
