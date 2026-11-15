#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): the report's tables from every run's summary.json.
"""usage: table.py [runs folder]   (default: ../runs next to this script). Prints Markdown.

Set 1 (runs a*) flew only sometimes (a key tap shorter than a game tick), so its flight columns read "not valid".
A run that created its world (MODE=create) is marked "new world" and also gets a row in the creation table; a run whose
flight was the rig's glide straight through the terrain (FLIGHT=glide, the Nether) is marked "glide"."""
import glob, json, os, sys

runs = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '../runs')
# In the order of the study: distances set 1 and 2, heap ceilings, covered GC runs, the middle ratio, validation,
# then review 1's runs: the first creation (f) and the Nether (n).
ORDER = 'adhcmvfn'
rows = sorted((json.load(open(path)) for path in glob.glob(os.path.join(runs, '*', 'summary.json'))),
              key=lambda s: (ORDER.index(s['name'][0]) if s['name'][0] in ORDER else len(ORDER), s['name']))


def g(d, *keys, default='-'):
    for key in keys:
        if not isinstance(d, dict) or key not in d or d[key] is None:
            return default
        d = d[key]
    return d


def frames(w, win):
    if win not in w or 'avg_ms' not in w[win]:
        return '-'
    cpu = w[win].get('cpu_percent')
    return f"{w[win]['fps']:.0f}, {w[win]['avg_ms']}, {w[win]['p99_ms']}, {w[win]['max_ms']}" + (f", {cpu} %" if cpu is not None else '')


print('| Run | Render / sim | -Xmx / -Xms | GC flags | RSS settled | PSS settled | Heap used / committed (settled) | '
      'NMT settled | RSS after flight | Peak RSS | Scope peak | GPU settled / after flight | '
      'Standing: fps, avg, p99, worst ms, CPU | Flying: fps, avg, p99, worst ms, CPU | GC pauses in flight, longest | '
      'Longest GC pause after joining |')
print('|' + '---|' * 16)
for s in rows:
    st, sn, w = s['settings'], s['snapshots'], s['windows']
    settled, flight = sn.get('settled', {}), sn.get('flight', {})
    valid = not s['name'].startswith('a')
    peak = lambda key: max((v.get(key) or 0) for v in sn.values()) if sn else '-'
    fly = frames(w, 'flight') if valid else 'not valid'
    gcf = f"{g(w, 'flight', 'gc_pauses')}, {g(w, 'flight', 'gc_max_ms')} ms" if valid else 'not valid'
    notes = [note for note, on in (('new world', 'create' in w), ('glide', st.get('FLIGHT') == 'glide')) if on]
    label = s['name'] + (f" ({', '.join(notes)})" if notes else '')
    print(f"| {label} | {st['RD']} / {st['SD']} | {st['HEAP']} / {st['MIN_HEAP']} | {st['GC'] or 'default'} | "
          f"{g(settled, 'rss')} | {g(settled, 'pss')} | {g(settled, 'heap_used')} / {g(settled, 'heap_committed')} | "
          f"{g(settled, 'nmt_total')} | {g(flight, 'rss') if valid else 'not valid'} | {peak('rss_peak')} | "
          f"{peak('cgroup_peak')} | {g(settled, 'gpu_process')} / {g(flight, 'gpu_process') if valid else '-'} | "
          f"{frames(w, 'stand')} | {fly} | {gcf} | {g(s, 'gc_after_join', 'max_ms')} ms |")
created = [s for s in rows if 'create' in s['windows']]
if created:
    print()
    print('| Run (new world) | Home | Create to joining: s, worst frame ms | Heap before GC, most / committed, most | GC pauses, longest, over 50 ms | '
          'RSS, most | Scope, most | Town build: s, worst frame ms, frames over 17 / 33 / 50 ms | '
          'First 30 s: worst frame ms, frames over 17 / 33 / 50 ms |')
    print('|' + '---|' * 9)
    for s in created:
        w, st = s['windows'], s['settings']
        # From the Create click to the end of the first 30 s in the world (the town builds inside it).
        parts = [w['create'], w['first_30s']]
        most = lambda key: max((p.get(key) or 0) for p in parts)
        pauses = sum(p['gc_pauses'] for p in parts)
        town = w.get('town')
        hitch = lambda p: f"{p.get('max_ms', '-')}, {p.get('over_17ms', '-')} / {p.get('over_33ms', '-')} / {p.get('over_50ms', '-')}"
        print(f"| {s['name']} | {st.get('HOMEKIND') or '-'} | {w['create']['seconds']} s, {w['create'].get('max_ms', '-')} | "
              f"{most('heap_before_gc_max_mib')} / {most('heap_committed_max_mib')} | "
              f"{pauses}, {most('gc_max_ms')} ms, {sum(p['gc_over_50ms'] for p in parts)} | {most('rss_max_mib')} | "
              f"{most('scope_max_mib')} | {(str(town['seconds']) + ' s, ' + hitch(town)) if town else '-'} | "
              f"{hitch(w['first_30s'])} |")
covered = [s for s in rows if any(k.startswith('covered') for k in s['snapshots'])]
if covered:
    print()
    print('| Run | -Xmx / -Xms | GC flags | RSS when covered | 1 min | 2 min | 3 min | 4 min | 5 min | '
          'Heap committed at 0 / 5 min | Scope at 5 min | GPU at 5 min |')
    print('|' + '---|' * 12)
    for s in covered:
        sn, st = s['snapshots'], s['settings']
        cells = [str(g(sn, label, 'rss')) for label in ('covered0', 'covered1m', 'covered2m', 'covered3m', 'covered4m', 'covered5m')]
        print(f"| {s['name']} | {st['HEAP']} / {st['MIN_HEAP']} | {st['GC'] or 'default'} | {' | '.join(cells)} | "
              f"{g(sn, 'covered0', 'heap_committed')} / {g(sn, 'covered5m', 'heap_committed')} | "
              f"{g(sn, 'covered5m', 'cgroup_current')} | {g(sn, 'covered5m', 'gpu_process')} |")
