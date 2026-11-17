#!/usr/bin/python3
"""Generate package 49's public run and paired-factor tables from committed summary.json evidence."""
import json, pathlib, statistics, sys
root=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent.parent/'runs'
rows={p.parent.name:json.loads(p.read_text()) for p in sorted(root.glob('*/summary.json'))}


def get(row,*keys):
    for key in keys:
        if not isinstance(row,dict): return None
        row=row.get(key)
    return row


def show(value): return '—' if value is None else str(value)


def spread(values):
    values=[v for v in values if v is not None]
    if not values: return 'unmeasured'
    return f'{statistics.fmean(values):.1f} ({min(values):g}–{max(values):g}; n={len(values)})'


print('All memory in MiB; paired savings are baseline minus factor, positive means less memory. Ranges are observed, not confidence intervals.\n')
print('Isolated factors and covered experiments use the original common mod tree. Combined validation uses fresh controls from the merged tree; see [source-refresh.json](source-refresh.json) and the provenance audit.\n')
print('| Factor | Research estimate | Settled RSS saving, mean (range) | Post-flight RSS saving | Covered 5-min RSS saving | Standing post-G1 heap minimum saving |')
print('|---|---|---:|---:|---:|---:|')
labels={'coh':'compact headers','dedup':'compact headers + string dedup',
        'trim':'native trim every 60 s','system':'60 s trim + LWJGL system allocator',
        'arenas':'MALLOC_ARENA_MAX=2','threads':'GC/background thread limits','ferrite':'FerriteCore 9.0.0'}
estimates={'coh':'30–60', 'dedup':'0–20 extra over headers', 'trim':'50–200 native total',
           'system':'50–200 native total; not additive', 'arenas':'50–200 native total; not additive',
           'threads':'10–40', 'ferrite':'15–45'}
for factor in labels:
    savings={label:[] for label in ('settled','flight','covered5m')}
    heaps=[]
    for repeat in (1,2):
        baseline=rows.get(f'v1-{factor}-{repeat}',{})
        variant=rows.get(f'{factor}-{repeat}',{})
        for label in savings:
            a,b=(get(row,'snapshots',label,'rss') for row in (baseline,variant))
            if a is not None and b is not None: savings[label].append(a-b)
        # Use the settled standing window, avoiding join-time collections before the world is fully populated.
        # This is an after-G1 proxy; no extra full GC is injected into factor runs.
        a,b=(get(row,'windows','stand','heap_after_gc_min_mib') for row in (baseline,variant))
        if a is not None and b is not None: heaps.append(a-b)
    print(f"| {labels[factor]} | {estimates[factor]} | {spread(savings['settled'])} | {spread(savings['flight'])} | {spread(savings['covered5m'])} | {spread(heaps)} |")

print('\nAccounting residual: RssAnon − (NMT total committed − shared class space). Committed bytes are not resident bytes: this is a rough residual, not a measured allocator heap. Positive paired savings mean a smaller residual.\n')
print('| Factor | Settled residual saving | Post-flight residual saving | Covered residual saving | Post-flight committed Java heap saving |')
print('|---|---:|---:|---:|---:|')
for factor,label in labels.items():
    residuals={phase:[] for phase in ('settled','flight','covered5m')}
    commits=[]
    for repeat in (1,2):
        a,b=(rows.get(f'{prefix}{factor}-{repeat}',{}) for prefix in ('v1-',''))
        for phase in residuals:
            x,y=(get(row,'snapshots',phase) for row in (a,b))
            if x and y and x['nmt_total'] is not None and y['nmt_total'] is not None:
                residual=lambda v:v['rss_anon']-v['nmt_total']+v['nmt'].get('Shared class space',0)
                residuals[phase].append(residual(x)-residual(y))
                if phase == 'flight': commits.append(x['heap_committed']-y['heap_committed'])
    print(f"| {label} | {spread(residuals['settled'])} | {spread(residuals['flight'])} | {spread(residuals['covered5m'])} | {spread(commits)} |")

if any(name.startswith('winner-flat-') for name in rows):
    print('\nCurrent-source combined candidate ([settings](winners.json)); fresh v1 controls and candidate runs, n=3 each. These absolute ranges and paired differences are measured directly, not summed from isolated factors.\n')
    print('| Current-source group | Settled RSS | Post-flight RSS | Covered 5-min RSS |')
    print('|---|---:|---:|---:|')
    values={}
    for label,prefix in (('fresh v1','v1-flat-'),('combined candidate','winner-flat-')):
        values[label]={phase:[get(rows.get(prefix+str(i),{}),'snapshots',phase,'rss') for i in (1,2,3)]
                       for phase in ('settled','flight','covered5m')}
        print('| '+label+' | '+' | '.join(spread(values[label][phase]) for phase in values[label])+' |')
    differences={phase:[a-b for a,b in zip(values['fresh v1'][phase],values['combined candidate'][phase])
                        if a is not None and b is not None] for phase in values['fresh v1']}
    print('| paired RSS saving | '+' | '.join(spread(values) for values in differences.values())+' |')

print('\nCovered actions use v1 settings. Each saving below compares with the untreated run in the same round; these are independent JVMs, so inspect the pre-action RSS too. zram is device-wide and includes other builders. Its physical-memory change is not an attributed game cost.\n')
print('| Covered run / status | RSS before / 5 min / wake | Saving vs untreated 5 min | Scope swap 5 min / wake | Global zram original / compressed / physical at 5 min (physical change) | Majflt covered / wake | Return to first frame ms | Wake worst; >17 / >33 ms | GC max after join ms |')
print('|---|---:|---:|---:|---:|---:|---:|---:|---:|')


def zram(snap):
    devices = snap.get('zram_mm_stat', {})
    if not devices: return None
    # Kernel mm_stat: orig_data_size, compr_data_size, mem_used_total (bytes).
    return [sum(values[index] for values in devices.values()) / 2**20 for index in range(3)]


covered_rows={name:(s,'complete') for name,s in rows.items() if name.startswith('cover-')}
for path in sorted((root.parent/'failures').glob('cover-*/partial/summary.json')):
    s=json.loads(path.read_text())
    covered_rows[s['name']] = (s, 'FAILED; wake incomplete')
for name,(s,status) in sorted(covered_rows.items()):
    before, covered, wake = (s['snapshots'].get(label, {}) for label in ('covered0','covered5m','wake'))
    control = rows.get('cover-none-'+name.rsplit('-',1)[1], {})
    baseline = get(control,'snapshots','covered5m','rss')
    saving = baseline-covered['rss'] if baseline is not None and 'rss' in covered else None
    initial, final = zram(before), zram(covered)
    zr = '—' if initial is None or final is None else ' / '.join(f'{v:.1f}' for v in final)+f' ({final[2]-initial[2]:+.1f})'
    w = s['windows'].get('wake', {})
    cover_faults = covered['majflt']-before['majflt'] if 'majflt' in covered and 'majflt' in before else None
    print(f"| {name} ({status}) | {show(before.get('rss'))} / {show(covered.get('rss'))} / {show(wake.get('rss'))} | "
          f"{show(saving)} | {show(covered.get('cgroup_swap'))} / {show(wake.get('cgroup_swap'))} | {zr} | "
          f"{show(cover_faults)} / {show(s.get('wake_majflt_delta'))} | "
          f"{show(s.get('return_to_first_frame_ms'))} | {show(w.get('max_ms'))}; "
          f"{show(w.get('over_17ms'))} / {show(w.get('over_33ms'))} | {show(get(s,'gc_after_join','max_ms'))} |")

print('\n| Run | Start to join s | Settled RSS / PSS | Post-flight RSS | Covered 5-min RSS / scope swap | Flight p99 / worst ms | Wake worst; >17 / >33 ms | Wake first frame ms | Majflt cover+wake | GC max after join ms | OOM / high / lost frames |')
print('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|')
for name,s in rows.items():
    g=lambda *keys:show(get(s,*keys))
    high=max((v.get('cgroup_high_events',0) for v in s['snapshots'].values()),default=0)
    print(f"| {name} | {g('game_start_to_join_s')} | {g('snapshots','settled','rss')} / {g('snapshots','settled','pss')} | "
          f"{g('snapshots','flight','rss')} | {g('snapshots','covered5m','rss')} / {g('snapshots','covered5m','cgroup_swap')} | "
          f"{g('windows','flight','p99_ms')} / {g('windows','flight','max_ms')} | "
          f"{g('windows','wake','max_ms')}; {g('windows','wake','over_17ms')} / {g('windows','wake','over_33ms')} | "
          f"{g('wake_first_frame_ms')} | {g('cover_wake_majflt_delta')} | {g('gc_after_join','max_ms')} | "
          f"{s.get('out_of_memory')} / {high} / {s.get('lost_frames')} |")
