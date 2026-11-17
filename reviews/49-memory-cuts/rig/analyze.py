#!/usr/bin/python3
# DEVELOPMENT AID of package 49 (copied from package 41) (measurement only): turns one run's raw data into its summary.
"""usage: analyze.py <rig folder> <out folder>

Reads the rig folder of run.sh (settings.txt, marks.txt, frames.txt, gc.txt, snap-*.json, samples.csv, game.txt)
and writes <out>/summary.json, plus copies of the small files (settings, marks, snapshots, the GC log as gc.txt,
the samples). Frame time is the gap between the starts of two frames (frames.txt); a window counts the gaps that end
inside it, so the gap in progress at its start counts too. GC pauses come from -Xlog:gc with the timenanos decoration
(System.nanoTime, the same clock); the JVM prints uptime first, then timenanos."""
import glob, json, os, re, shutil, statistics, sys

rig, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
settings = dict(line.rstrip('\n').split('=', 1) for line in open(os.path.join(rig, 'settings.txt')) if '=' in line)
marks = {}
for line in open(os.path.join(rig, 'marks.txt')):
    label, ns = line.split()
    marks[label] = int(ns)
frames = []
if os.path.exists(os.path.join(rig, 'frames.txt')):
    frames = [int(line) for line in open(os.path.join(rig, 'frames.txt')) if line.strip().isdigit()]
pauses = []  # (end ns, ms, kind)
cycles = []
GC_LINE = re.compile(r'^\[[\d.]+s\]\[(\d+)ns\] GC\(\d+\) (Pause [A-Za-z]+(?: \([^)]*\))*|Concurrent [A-Za-z ]+[A-Za-z]) ?(.*?)(?: (\d+\.\d+)ms)?$')
committed = []
for line in open(os.path.join(rig, 'gc.txt')) if os.path.exists(os.path.join(rig, 'gc.txt')) else []:
    match = GC_LINE.match(line.strip())
    if not match:
        continue
    end, kind, rest, ms = int(match[1]), match[2], match[3], match[4]
    if kind.startswith('Pause') and ms:
        pauses.append((end, float(ms), kind))
        heap = re.search(r'(\d+)M->(\d+)M\((\d+)M\)', rest)
        if heap:
            committed.append((end, int(heap[1]), int(heap[2]), int(heap[3])))
    elif kind.startswith('Concurrent') and not rest:
        cycles.append((end, kind))  # a cycle's opening line; its closing line carries the duration (in rest)


rows = []
samples = []  # (monotonic ns, CPU s)
memory = []  # (monotonic ns, RSS MiB, scope current MiB)
if os.path.exists(os.path.join(rig, 'samples.csv')):
    rows = [line.strip().split(',') for line in open(os.path.join(rig, 'samples.csv'))]
    if rows and 'cpu_s' in rows[0]:
        column = rows[0].index('cpu_s')
        samples = [(int(row[0]), float(row[column])) for row in rows[1:] if len(row) > column]
    if rows and 'rss_mib' in rows[0] and 'cgroup_current_mib' in rows[0]:
        rss, scope = rows[0].index('rss_mib'), rows[0].index('cgroup_current_mib')
        memory = [(int(row[0]), int(row[rss]), int(row[scope])) for row in rows[1:] if len(row) > max(rss, scope)]


def cpu_percent(start, end):
    """The game's CPU over a window from the 2 s samples (100 = one core), or None without CPU samples."""
    inside = [sample for sample in samples if start <= sample[0] <= end]
    if len(inside) < 2:
        return None
    return round((inside[-1][1] - inside[0][1]) / ((inside[-1][0] - inside[0][0]) / 1e9) * 100)


def window(start, end, clip_start=False):
    stats = {'seconds': round((end - start) / 1e9, 1), 'cpu_percent': cpu_percent(start, end)}
    # The frames that start inside the window, plus the last one before it: a window counts every gap that ends inside
    # it, so the gap in progress at its start (the frame that handles the Create click, a few ms before the mark)
    # counts here, and the one in progress at its end counts in the next window.
    before = [t for t in frames if t < start]
    inside = ([start] if clip_start else before[-1:]) + [t for t in frames if start <= t < end]
    if len(inside) > 1:
        gaps = sorted((b - a) / 1e6 for a, b in zip(inside, inside[1:]))
        stats.update(frames=len(gaps), fps=round(len(gaps) / ((inside[-1] - inside[0]) / 1e9), 1),
                     avg_ms=round(statistics.fmean(gaps), 2), p50_ms=round(gaps[len(gaps) // 2], 2),
                     p99_ms=round(gaps[min(len(gaps) - 1, int(len(gaps) * 0.99))], 2), max_ms=round(gaps[-1], 1),
                     over_17ms=sum(g > 17 for g in gaps), over_33ms=sum(g > 33 for g in gaps),
                     over_50ms=sum(g > 50 for g in gaps), over_100ms=sum(g > 100 for g in gaps))
    in_window = [p for p in pauses if start <= p[0] - p[1] * 1e6 < end]
    stats.update(gc_pauses=len(in_window), gc_max_ms=round(max((p[1] for p in in_window), default=0), 2),
                 gc_total_ms=round(sum(p[1] for p in in_window), 1),
                 gc_over_50ms=sum(p[1] > 50 for p in in_window),
                 gc_kinds=sorted({p[2] for p in in_window}))
    # The most the 2 s samples and the GC log saw inside the window: RSS, the scope, the heap before a collection and
    # its committed size.
    sampled = [m for m in memory if start <= m[0] <= end]
    heaps = [c for c in committed if start <= c[0] <= end]
    stats.update(rss_max_mib=max((m[1] for m in sampled), default=None),
                 scope_max_mib=max((m[2] for m in sampled), default=None),
                 heap_before_gc_max_mib=max((c[1] for c in heaps), default=None),
                 heap_after_gc_min_mib=min((c[2] for c in heaps), default=None),
                 heap_after_gc_max_mib=max((c[2] for c in heaps), default=None),
                 heap_committed_max_mib=max((c[3] for c in heaps), default=None))
    return stats


summary = {'name': settings.get('name'), 'settings': {k: settings.get(k) for k in
           ('RD', 'SD', 'HEAP', 'MIN_HEAP', 'GC', 'MEMHIGH', 'SIZE', 'REFRESH', 'SETTLE', 'WINDOW', 'COVER', 'MODE',
            'HOMEKIND', 'BASE', 'FLIGHT', 'ENV', 'MODS', 'PROBE', 'RECLAIM', 'FREEZE', 'LONG', 'NMT', 'COVER_ACTION', 'WAKE_INPUT')},
           'windows': {}, 'snapshots': {}}
# A first creation (MODE=create): from the Create click to joining, then while the town builds (flat), and the first
# 30 s in the new world (60 s would reach vanilla's 30-frames limit, 60 s after the last input: the Create click).
if 'create_start' in marks and 'joined' in marks:
    summary['windows']['create'] = window(marks['create_start'], marks['joined'])
    if 'town_built' in marks:
        summary['windows']['town'] = window(marks['joined'], marks['town_built'])
    summary['windows']['first_30s'] = window(marks['joined'], marks['joined'] + 30 * 10**9)
for label in ('stand', 'flight', 'covered', 'wake', 'idle'):
    if f'{label}_start' in marks and f'{label}_end' in marks:
        summary['windows'][label] = window(marks[f'{label}_start'], marks[f'{label}_end'], clip_start=(label == 'wake'))
if 'wake_start' in marks:
    first = next((t for t in frames if t >= marks['wake_start']), None)
    summary['wake_first_frame_ms'] = None if first is None else round((first - marks['wake_start']) / 1e6, 2)
    summary['return_to_first_frame_ms'] = None if first is None else round((first - marks.get('return_start', marks['wake_start'])) / 1e6, 2)
if 'joined' in marks:
    start_sample = marks.get('game_detected', int(rows[1][0]) if len(rows) > 1 else marks['joined'])
    summary['game_start_to_join_s'] = round((marks['joined'] - start_sample) / 1e9, 2)
    end = marks.get('done', max(marks.values()))
    summary['windows']['whole_run'] = window(marks['joined'], end)
    after = [p for p in pauses if p[0] >= marks['joined']]
    summary['gc_after_join'] = {'pauses': len(after), 'max_ms': round(max((p[1] for p in after), default=0), 2),
                                'full': sum('Full' in p[2] for p in after),
                                'concurrent_cycles': sum(c[0] >= marks['joined'] and 'Mark Cycle' in c[1] for c in cycles)}
    summary['gc_before_join'] = {'pauses': len(pauses) - len(after),
                                 'max_ms': round(max((p[1] for p in pauses if p[0] < marks['joined']), default=0), 2)}
if committed:
    summary['heap_committed_mib'] = {'max': max(c[3] for c in committed), 'last': committed[-1][3],
                                     'max_before_gc': max(c[1] for c in committed),
                                     'after_gc_min_after_join': min((c[2] for c in committed if c[0] >= marks.get('joined', 0)), default=None)}
for path in sorted(glob.glob(os.path.join(rig, 'snap-*.json'))):
    snap = json.load(open(path))
    summary['snapshots'][snap['label']] = {
        'rss': snap['status_mib'].get('VmRSS'), 'rss_peak': snap['status_mib'].get('VmHWM'),
        'pss': snap['smaps_rollup_mib'].get('Pss'), 'rss_anon': snap['status_mib'].get('RssAnon'),
        'rss_file': snap['status_mib'].get('RssFile'), 'swap': snap['status_mib'].get('VmSwap'),
        'heap_used': snap.get('heap_mib', {}).get('used'), 'heap_committed': snap.get('heap_mib', {}).get('committed'),
        'nmt_total': snap['nmt_committed_mib'].get('Total'),
        'nmt': {k: v for k, v in snap['nmt_committed_mib'].items() if k != 'Total' and v >= 5},
        'cgroup_current': snap['cgroup_mib']['current'], 'cgroup_peak': snap['cgroup_mib']['peak'],
        'cgroup_anon': snap['cgroup_mib'].get('anon'), 'cgroup_file': snap['cgroup_mib'].get('file'),
        'cgroup_high_events': snap['cgroup_events'].get('high'),
        'cgroup_events': snap['cgroup_events'], 'cgroup_swap': snap['cgroup_mib']['swap'],
        'majflt': snap['majflt'], 'zram_mm_stat': snap['zram_mm_stat'], 'smaps_classes': snap['smaps_classes'],
        'frozen': snap['frozen'],
        'probe_trim_rss_delta_mib': (snap['status_mib']['VmRSS'] - snap['after_trim']['status_mib']['VmRSS']) if 'after_trim' in snap else None,
        'probe_gc_trim_rss_delta_mib': (snap['after_gc']['status_mib']['VmRSS'] - snap['after_gc_trim']['status_mib']['VmRSS']) if 'after_gc_trim' in snap else None, 'memory_high': snap['cgroup_mib']['high'],
        'gpu_process': snap.get('gpu_process_mib'), 'gpu_total': snap.get('gpu_total_used_mib')}
logs = ''.join(open(os.path.join(rig, name), errors='replace').read()
               for name in ('game.txt', 'gradle.txt') if os.path.exists(os.path.join(rig, name)))
summary['out_of_memory'] = 'OutOfMemoryError' in logs
summary['town_frozen'] = 'without the town' in logs
summary['paused_lines'] = logs.count('Saving and pausing game')
summary['lost_frames'] = sum(1 for line in open(os.path.join(rig, 'frames.txt')) if line.startswith('lost')) \
    if os.path.exists(os.path.join(rig, 'frames.txt')) else None
if 'covered0' in summary['snapshots'] and 'wake' in summary['snapshots']:
    summary['cover_wake_majflt_delta'] = summary['snapshots']['wake']['majflt'] - summary['snapshots']['covered0']['majflt']
fault_path = os.path.join(rig, 'faults-return.json')
if os.path.exists(fault_path) and 'wake' in summary['snapshots']:
    summary['wake_majflt_delta'] = summary['snapshots']['wake']['majflt'] - json.load(open(fault_path))['majflt']
# Small evidence is public. Raw game and launcher logs remain local.
worktree = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
def public(value):
    if isinstance(value, str): return value.replace(worktree, '<worktree>').replace(os.path.expanduser('~'), '<home>')
    if isinstance(value, dict): return {k: public(v) for k, v in value.items()}
    if isinstance(value, list): return [public(v) for v in value]
    return value
summary = public(summary)
json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
for name in ('settings.txt', 'marks.txt', 'samples.csv', 'cover.txt', 'randr.txt', 'actions.jsonl', 'host-start.json', 'host-end.json', 'faults-return.json', 'wake-input.jsonl'):
    if os.path.exists(os.path.join(rig, name)):
        open(os.path.join(out, name), 'w').write(public(open(os.path.join(rig, name)).read()).rstrip() + '\n')
if os.path.exists(os.path.join(rig, 'gc.txt')):
    shutil.copy(os.path.join(rig, 'gc.txt'), os.path.join(out, 'gc.txt'))
for path in glob.glob(os.path.join(rig, 'snap-*.json')) + glob.glob(os.path.join(rig, 'nmt-*.txt')) + glob.glob(os.path.join(rig, 'probe-*.json')) + glob.glob(os.path.join(rig, 'heap-*.txt')):
    open(os.path.join(out, os.path.basename(path)), 'w').write(public(open(path).read()).rstrip() + '\n')
w = summary['windows']
print(json.dumps({k: summary[k] for k in ('name', 'settings')}, separators=(',', ':')))
for label, stats in w.items():
    print(f'{label:10} {stats}')
for label, snap in summary['snapshots'].items():
    print(f'{label:10} RSS {snap["rss"]} PSS {snap["pss"]} heap {snap["heap_used"]}/{snap["heap_committed"]} '
          f'NMT {snap["nmt_total"]} cgroup {snap["cgroup_current"]} (peak {snap["cgroup_peak"]}) GPU {snap["gpu_process"]}')
print('gc after join', summary.get('gc_after_join'), 'OOM', summary['out_of_memory'], 'frozen', summary['town_frozen'])
