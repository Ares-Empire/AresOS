#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): turns one run's raw data into its summary.
"""usage: analyze.py <rig folder> <out folder>

Reads the rig folder of run.sh (settings.txt, marks.txt, frames.txt, gc.txt, snap-*.json, samples.csv, game.txt)
and writes <out>/summary.json, plus copies of the small files (settings, marks, snapshots, the GC log as gc.txt,
the samples). Frame time is the gap between the starts of two frames (frames.txt); a window counts the frames that
start inside it. GC pauses come from -Xlog:gc with the timenanos decoration (System.nanoTime, the same clock)."""
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
GC_LINE = re.compile(r'^\[(\d+)ns\]\[[\d.]+s\] GC\(\d+\) (Pause [A-Za-z]+(?: \([^)]*\))*|Concurrent [A-Za-z ]+[A-Za-z]) ?(.*?)(?: (\d+\.\d+)ms)?$')
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
    elif kind.startswith('Concurrent'):
        cycles.append((end, kind))


def window(start, end):
    stats = {'seconds': round((end - start) / 1e9, 1)}
    inside = [t for t in frames if start <= t < end]
    if len(inside) > 1:
        gaps = sorted((b - a) / 1e6 for a, b in zip(inside, inside[1:]))
        stats.update(frames=len(gaps), fps=round(len(gaps) / ((inside[-1] - inside[0]) / 1e9), 1),
                     avg_ms=round(statistics.fmean(gaps), 2), p50_ms=round(gaps[len(gaps) // 2], 2),
                     p99_ms=round(gaps[min(len(gaps) - 1, int(len(gaps) * 0.99))], 2), max_ms=round(gaps[-1], 1),
                     over_50ms=sum(g > 50 for g in gaps), over_100ms=sum(g > 100 for g in gaps))
    in_window = [p for p in pauses if start <= p[0] - p[1] * 1e6 < end]
    stats.update(gc_pauses=len(in_window), gc_max_ms=round(max((p[1] for p in in_window), default=0), 2),
                 gc_total_ms=round(sum(p[1] for p in in_window), 1),
                 gc_over_50ms=sum(p[1] > 50 for p in in_window),
                 gc_kinds=sorted({p[2] for p in in_window}))
    return stats


summary = {'name': settings.get('name'), 'settings': {k: settings.get(k) for k in
           ('RD', 'SD', 'HEAP', 'MIN_HEAP', 'GC', 'MEMHIGH', 'SIZE', 'REFRESH', 'SETTLE', 'WINDOW', 'COVER')},
           'windows': {}, 'snapshots': {}}
for label in ('stand', 'flight', 'covered'):
    if f'{label}_start' in marks and f'{label}_end' in marks:
        summary['windows'][label] = window(marks[f'{label}_start'], marks[f'{label}_end'])
if 'joined' in marks:
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
                                     'max_before_gc': max(c[1] for c in committed)}
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
        'cgroup_high_events': snap['cgroup_events'].get('high'), 'memory_high': snap['cgroup_mib']['high'],
        'gpu_process': snap.get('gpu_process_mib'), 'gpu_total': snap.get('gpu_total_used_mib')}
logs = ''.join(open(os.path.join(rig, name), errors='replace').read()
               for name in ('game.txt', 'gradle.txt') if os.path.exists(os.path.join(rig, name)))
summary['out_of_memory'] = 'OutOfMemoryError' in logs
summary['town_frozen'] = 'without the town' in logs
summary['paused_lines'] = logs.count('Saving and pausing game')
summary['lost_frames'] = sum(1 for line in open(os.path.join(rig, 'frames.txt')) if line.startswith('lost')) \
    if os.path.exists(os.path.join(rig, 'frames.txt')) else None
json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
for name in ('settings.txt', 'marks.txt', 'samples.csv', 'cover.txt', 'randr.txt'):
    if os.path.exists(os.path.join(rig, name)):
        shutil.copy(os.path.join(rig, name), out)
if os.path.exists(os.path.join(rig, 'gc.txt')):
    shutil.copy(os.path.join(rig, 'gc.txt'), os.path.join(out, 'gc.txt'))
for path in glob.glob(os.path.join(rig, 'snap-*.json')) + glob.glob(os.path.join(rig, 'nmt-*.txt')):
    shutil.copy(path, out)
w = summary['windows']
print(json.dumps({k: summary[k] for k in ('name', 'settings')}, separators=(',', ':')))
for label, stats in w.items():
    print(f'{label:10} {stats}')
for label, snap in summary['snapshots'].items():
    print(f'{label:10} RSS {snap["rss"]} PSS {snap["pss"]} heap {snap["heap_used"]}/{snap["heap_committed"]} '
          f'NMT {snap["nmt_total"]} cgroup {snap["cgroup_current"]} (peak {snap["cgroup_peak"]}) GPU {snap["gpu_process"]}')
print('gc after join', summary.get('gc_after_join'), 'OOM', summary['out_of_memory'], 'frozen', summary['town_frozen'])
