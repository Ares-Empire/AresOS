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
    return f'{statistics.fmean(values):.1f} ({min(values):g}–{max(values):g})'


print('All memory in MiB; paired savings are baseline minus factor, positive means less memory. Ranges are observed, not confidence intervals.\n')
print('| Factor | Settled RSS saving, mean (range) | Post-flight RSS saving | Covered 5-min RSS saving | Post-G1 heap minimum saving |')
print('|---|---:|---:|---:|---:|')
for factor in ('coh','dedup','trim','system','arenas','threads','ferrite'):
    savings={label:[] for label in ('settled','flight','covered5m')}
    heaps=[]
    for repeat in (1,2):
        baseline=rows.get(f'v1-{factor}-{repeat}',{})
        variant=rows.get(f'{factor}-{repeat}',{})
        for label in savings:
            a,b=(get(row,'snapshots',label,'rss') for row in (baseline,variant))
            if a is not None and b is not None: savings[label].append(a-b)
        # G1's after-collection minimum is a proxy; no extra full GC is injected into factor runs.
        a,b=(get(row,'heap_committed_mib','after_gc_min_after_join') for row in (baseline,variant))
        if a is not None and b is not None: heaps.append(a-b)
    print(f"| {factor} | {spread(savings['settled'])} | {spread(savings['flight'])} | {spread(savings['covered5m'])} | {spread(heaps)} |")

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
