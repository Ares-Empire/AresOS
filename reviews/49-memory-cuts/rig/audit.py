#!/usr/bin/python3
"""Summarize recorded guards and comparisons without hiding failed experiments or adding tolerances."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WT = ROOT.parents[1]
rows = {p.parent.name: json.loads(p.read_text()) for p in sorted((ROOT/'runs').glob('*/summary.json'))}


def bounds(values):
    values = [v for v in values if v is not None]
    return {'min': min(values), 'max': max(values), 'n': len(values)} if values else None


def guards(s):
    events = [snap['cgroup_events'] for snap in s['snapshots'].values()]
    oom = s['out_of_memory'] or any(v.get('oom', 0) or v.get('oom_kill', 0) for v in events)
    high = max((v.get('high', 0) for v in events), default=0)
    gc = s.get('gc_after_join', {}).get('max_ms')
    return {'oom': bool(oom), 'high_events': high, 'gc_after_join_max_ms': gc,
            'gc_at_most_50ms': gc is not None and gc <= 50, 'lost_frames': s.get('lost_frames'),
            'memory_gc_recorder_pass': not oom and high == 0 and gc is not None and gc <= 50 and s.get('lost_frames') == 0}


metrics = ('p99_ms', 'max_ms', 'over_17ms', 'over_33ms', 'fps')


def compare(candidate, control):
    return {window:{metric:{'candidate':candidate['windows'][window].get(metric),
                           'control':control['windows'][window].get(metric)} for metric in metrics}
            for window in ('stand','flight','wake','first_30s','create','town')
            if window in candidate['windows'] and window in control['windows']}


sources = {}
run_trees = {}
for name in rows:
    path = ROOT/'runs'/name/'settings.txt'
    settings = dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line)
    revision = settings['source_revision']
    if revision not in sources:
        tree = subprocess.check_output(['git','rev-parse',revision+':mod'], cwd=WT, text=True).strip()
        sources[revision] = {'mod_tree':tree, 'runs':[]}
    sources[revision]['runs'].append(name)
    run_trees[name] = sources[revision]['mod_tree']

flat_controls = {name:s for name,s in rows.items() if name.startswith('v1-') and name != 'v1-nether'
                 and s['settings']['MODE'] == 'measure'}
control_groups = {}
for tree in sorted({run_trees[name] for name in flat_controls}):
    group = {name:s for name,s in flat_controls.items() if run_trees[name] == tree}
    control_groups[tree] = {'names':sorted(group), 'frame_envelopes':{
        window:{metric:bounds(s['windows'].get(window, {}).get(metric) for s in group.values())
                for metric in metrics} for window in ('stand','flight','wake')}}

covered_actions = {}
for name in rows:
    path = ROOT/'runs'/name/'actions.jsonl'
    if not name.startswith('cover-') or not path.exists(): continue
    actions = []
    for line in path.read_text().splitlines():
        record = json.loads(line)
        item = {'action':record['action'], 'duration_ms':round((record['end_monotonic_ns']-record['monotonic_ns'])/1e6,2),
                'result':record.get('result'), 'errno':record.get('errno'), 'failure':record.get('failure')}
        if 'before' in record:
            item['scope_current_change_mib'] = round((int(record['after']['memory.current'])-int(record['before']['memory.current']))/2**20,2)
            item['scope_swap_change_mib'] = round((int(record['after']['memory.swap.current'])-int(record['before']['memory.swap.current']))/2**20,2)
        actions.append(item)
    covered_actions[name] = actions

winners = {name:{'guards':guards(s), 'observed_frames':{w:{m:values.get(m) for m in metrics}
            for w,values in s['windows'].items() if w in ('stand','flight','wake','idle','first_30s','create','town')},
            'glide_tick_samples':s.get('glide_tick_samples',[])} for name,s in rows.items() if name.startswith('winner-')}
for name,s in rows.items():
    if name == 'winner-nether' and 'v1-nether' in rows:
        winners[name]['same_base_control_comparison'] = compare(s, rows['v1-nether'])
        winners[name]['control_mod_tree_matches'] = run_trees[name] == run_trees['v1-nether']
    elif name == 'winner-create' and 'v1-create' in rows:
        winners[name]['first_creation_control_comparison'] = compare(s, rows['v1-create'])
        winners[name]['control_mod_tree_matches'] = run_trees[name] == run_trees['v1-create']
    elif name.startswith('winner-flat-'):
        control = name.replace('winner-', 'v1-', 1)
        if control in rows:
            winners[name]['paired_control_comparison'] = compare(s, rows[control])
            winners[name]['control_mod_tree_matches'] = run_trees[name] == run_trees[control]
    if name in winners:
        winners[name]['mod_tree'] = run_trees[name]
        winners[name]['matching_flat_control_group'] = run_trees[name] if run_trees[name] in control_groups else None
    if name == 'winner-nmt0':
        winners[name]['all_live_snapshots_confirm_nmt_disabled'] = bool(s['snapshots']) and all(
            snap.get('nmt_disabled_confirmed') is True for snap in s['snapshots'].values() if not snap['frozen'])

result = {'valid_completed_run_count':len(rows),
          'guards_all_runs':{name:guards(s) for name,s in rows.items()},
          'source_revisions':sources, 'all_measured_mod_trees_equal':len({v['mod_tree'] for v in sources.values()}) == 1,
          'run_mod_trees':run_trees, 'flat_controls_by_mod_tree':control_groups,
          'frame_interpretation':'Observed ranges are descriptive, not confidence intervals or new pass tolerances. Compare counts, p99 and worst together; a first-creation loading frame is not a settled standing frame.',
          'covered_actions':covered_actions, 'winners':winners}
json.dump(result, sys.stdout, indent=2)
print()
