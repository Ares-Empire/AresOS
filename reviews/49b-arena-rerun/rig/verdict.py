"""Recompute the frozen pass line directly from retained frame windows and paired snapshots."""
import hashlib
import json
import re
from pathlib import Path
import statistics
import subprocess

ROOT=Path(__file__).resolve().parent.parent
accepted=json.loads((ROOT/'accepted.json').read_text())
assert len(accepted)==18
rows={slot:json.loads((ROOT/'runs'/name/'summary.json').read_text()) for slot,name in accepted.items()}


def frames(slot,label):
    data=json.loads((ROOT/'runs'/accepted[slot]/'decisive-frames.json').read_text())[label]
    times=data['timestamps_ns']
    gaps=[(b-a)/1e6 for a,b in zip(times,times[1:])]
    s=rows[slot]['windows'][label]
    result={'over_17ms':sum(g>17 for g in gaps),'over_33ms':sum(g>33 for g in gaps),'max_ms':max(gaps),'frames':len(gaps)}
    for key in ('over_17ms','over_33ms','frames'):assert s[key]==result[key],(slot,label,key)
    return result


safety={}
for slot,s in rows.items():
    events=[v['cgroup_events'] for v in s['snapshots'].values()]
    marks=dict(line.split() for line in (ROOT/'runs'/accepted[slot]/'marks.txt').read_text().splitlines())
    pauses=[]
    for line in (ROOT/'runs'/accepted[slot]/'gc.txt').read_text().splitlines():
        match=re.match(r'^\[[0-9.]+s\]\[(\d+)ns\].*\bPause\b.*\s(\d+(?:\.\d+)?)ms$',line)
        if match and int(match[1])>=int(marks['joined']):pauses.append(float(match[2]))
    exact_gc=max(pauses,default=0)
    assert round(exact_gc,2)==s['gc_after_join']['max_ms'],(slot,'GC parser mismatch')
    safety[slot]={'oom':s['out_of_memory'] or any(e.get('oom',0) or e.get('oom_kill',0) for e in events),'high':max(e.get('high',0) for e in events),'gc_ms':exact_gc,'lost_frames':s['lost_frames']}
    assert not s['town_frozen'] and s['lost_frames']==0,(slot,'invalid workload/recorder')
    terminal=json.loads((ROOT/'runs'/accepted[slot]/'terminal.json').read_text())
    final_events=dict(line.split() for line in terminal['memory.events'].splitlines())
    safety[slot]['oom'] |= bool(int(final_events.get('oom',0)) or int(final_events.get('oom_kill',0)))
    safety[slot]['high']=max(safety[slot]['high'],int(final_events.get('high',0)))
    proof=json.loads((ROOT/'runs'/accepted[slot]/'provenance.json').read_text())
    assert proof['environment']['MALLOC_ARENA_MAX']==('2' if slot.endswith('arena') else ''),(slot,'wrong actual game environment')
    assert not json.loads((ROOT/'runs'/accepted[slot]/'attempt.json').read_text())['contaminated']
    assert {'-Xms256m','-Xmx1024m','-XX:MaxHeapFreeRatio=30','-XX:MinHeapFreeRatio=10'}.issubset(set(proof['flags']))
    assert all(v['memory_high']=='2684354560' for v in s['snapshots'].values())
    if slot.startswith('nether'):assert 1200 in s['glide_tick_samples'],(slot,'glide incomplete')

savings=[rows[f'flat-{i}-control']['snapshots']['settled']['rss']-rows[f'flat-{i}-arena']['snapshots']['settled']['rss'] for i in range(1,7)]
flat={side:[frames(f'flat-{i}-{side}','flight') for i in range(1,7)] for side in ('control','arena')}
creation={side:[frames(f'create-{i}-{side}','first_30s') for i in range(1,3)] for side in ('control','arena')}
nether={side:frames('nether-'+side,'flight') for side in ('control','arena')}
flat_counts={side:sum(x['over_17ms'] for x in values) for side,values in flat.items()}
start_counts={side:sum(x['over_33ms'] for x in values) for side,values in creation.items()}
checks={
'safety':{'pass':all(not s['oom'] and s['high']==0 and s['gc_ms']<=50 for s in safety.values()),'runs':safety},
'memory':{'pass':statistics.median(savings)>=100,'paired_savings_mib':savings,'median_mib':statistics.median(savings),'threshold_mib':100},
'flat_flight_count':{'pass':flat_counts['arena']<=flat_counts['control']+2,'counts':flat_counts,'allowed_excess':2},
'flat_flight_max':{'pass':all(f['over_33ms']==0 for f in flat['arena']),'candidate_max_ms':max(f['max_ms'] for f in flat['arena']),'limit_ms':33},
'creation_count':{'pass':start_counts['arena']<=start_counts['control']+1,'counts':start_counts,'allowed_excess':1},
'nether_count':{'pass':nether['arena']['over_17ms']<=nether['control']['over_17ms']+2,'counts':{side:f['over_17ms'] for side,f in nether.items()},'allowed_excess':2},
'nether_max':{'pass':nether['arena']['over_33ms']==0,'candidate_max_ms':nether['arena']['max_ms'],'limit_ms':33}}
result={'pass_line_commit':'2ddcb93f','verdict':'QUALIFIED' if all(c['pass'] for c in checks.values()) else 'NOT QUALIFIED','checks':checks,'flat_flight':flat,'first_creation':creation,'nether':nether}
(ROOT/'verification/verdict.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# Package 49b results','',f"Verdict: **{result['verdict']}** against pass-line commit `2ddcb93f`.",'','| Slot | Settled RSS MiB | Flight RSS MiB | Covered 5m RSS MiB | Join s | Flight >17 / >33 | Flight max ms | First 30s >33 | Post-join GC max ms |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for slot,s in rows.items():
    f=s['windows'].get('flight',{});start=s['windows'].get('first_30s',{});sn=s['snapshots']
    lines.append(f"| [{slot}](runs/{accepted[slot]}/summary.json) | {sn['settled']['rss']} | {sn['flight']['rss']} | {sn['covered5m']['rss']} | {s['game_start_to_join_s']} | {f.get('over_17ms')} / {f.get('over_33ms')} | {f.get('max_ms_exact',0):.3f} | {start.get('over_33ms','—')} | {s['gc_after_join']['max_ms']} |")
lines+=['','Paired RSS saving = control minus arena; positive values favor the cap.','', '| Flat pair | Settled saving MiB | Flight saving MiB | Covered saving MiB |','|---|---:|---:|---:|']
for i in range(1,7):
    a=rows[f'flat-{i}-control']['snapshots'];b=rows[f'flat-{i}-arena']['snapshots']
    lines.append(f"| {i} | {a['settled']['rss']-b['settled']['rss']} | {a['flight']['rss']-b['flight']['rss']} | {a['covered5m']['rss']-b['covered5m']['rss']} |")
(ROOT/'TABLES.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(result,indent=2))
