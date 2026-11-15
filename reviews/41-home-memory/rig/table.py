#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): the report's tables from every run's summary.json.
"""usage: table.py [runs folder]   (default: ../runs next to this script). Prints Markdown."""
import glob, json, os, sys

runs = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '../runs')
rows = [json.load(open(path)) for path in sorted(glob.glob(os.path.join(runs, '*', 'summary.json')))]


def g(d, *keys, default='-'):
    for key in keys:
        if not isinstance(d, dict) or key not in d or d[key] is None:
            return default
        d = d[key]
    return d


print('| Run | Render / sim | Heap max | GC flags | RSS settled | PSS settled | Heap used / committed | NMT | '
      'RSS after flight | Peak RSS | Scope peak | GPU | Stand: fps, avg, worst ms | Flight: fps, avg, worst ms | '
      'GC pauses in flight, longest | Longest GC pause in run |')
print('|' + '---|' * 16)
for s in rows:
    st, sn, w = s['settings'], s['snapshots'], s['windows']
    settled, flight = sn.get('settled', {}), sn.get('flight', {})
    last = sn[sorted(sn, key=lambda k: list(sn).index(k))[-1]] if sn else {}
    fmt = lambda win: (f"{g(w, win, 'fps')}, {g(w, win, 'avg_ms')}, {g(w, win, 'max_ms')}" if win in w else '-')
    print(f"| {s['name']} | {st['RD']} / {st['SD']} | {st['HEAP']} | {st['GC'] or 'default'} | {g(settled, 'rss')} | "
          f"{g(settled, 'pss')} | {g(settled, 'heap_used')} / {g(settled, 'heap_committed')} | {g(settled, 'nmt_total')} | "
          f"{g(flight, 'rss')} | {max((v.get('rss_peak') or 0) for v in sn.values()) if sn else '-'} | "
          f"{max((v.get('cgroup_peak') or 0) for v in sn.values()) if sn else '-'} | {g(flight, 'gpu_process')} | "
          f"{fmt('stand')} | {fmt('flight')} | {g(w, 'flight', 'gc_pauses')}, {g(w, 'flight', 'gc_max_ms')} ms | "
          f"{g(s, 'gc_after_join', 'max_ms')} ms |")
covered = [s for s in rows if any(k.startswith('covered') for k in s['snapshots'])]
if covered:
    print()
    print('| Run | Heap max | GC flags | RSS when covered | after 1 min | 2 | 3 | 4 | 5 min | Heap committed at 5 min | Scope current at 5 min |')
    print('|' + '---|' * 11)
    for s in covered:
        sn = s['snapshots']
        cells = [str(g(sn, label, 'rss')) for label in ('covered0', 'covered1m', 'covered2m', 'covered3m', 'covered4m', 'covered5m')]
        print(f"| {s['name']} | {s['settings']['HEAP']} | {s['settings']['GC'] or 'default'} | {' | '.join(cells)} | "
              f"{g(sn, 'covered5m', 'heap_committed')} | {g(sn, 'covered5m', 'cgroup_current')} |")
