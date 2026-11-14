"""Assemble mail-sweep-growth.json from the harness outputs (no new measurement).

Usage: summarize.py OUT_DIR RECORD.json [CONTEXT.json]
CONTEXT.json (commits, runs, environment, attribution) is merged in unchanged.
"""
import json
import statistics
import sys
from pathlib import Path


def load(directory, name):
    path = directory / name
    return json.loads(path.read_text()) if path.exists() else None


def flows(report):
    return {k: v for k, v in (report or {}).items() if not k.startswith('_')}


def sweep_counts(singles):
    out = {}
    for flow, entry in flows(singles).items():
        out[flow] = {'single': entry['primaries'], 'persistent': entry['primaries'], 'pairs': entry['pairs'],
                     'cases': 2 * entry['primaries'] + entry['pairs']}
    total = {key: sum(v[key] for v in out.values()) for key in ('single', 'persistent', 'pairs', 'cases')}
    return out, total


def pair_sites(singles):
    sites = {}
    for entry in flows(singles).values():
        for site, count in entry['pairs_by_cleanup_site'].items():
            sites[site] = sites.get(site, 0) + count
    return dict(sorted(sites.items(), key=lambda kv: -kv[1]))


def point_sites(clean_main, clean_branch):
    delta = {}
    for flow in flows(clean_main):
        a, b = clean_main[flow]['by_site'], clean_branch[flow]['by_site']
        for site in set(a) | set(b):
            change = b.get(site, 0) - a.get(site, 0)
            if change:
                delta[site] = delta.get(site, 0) + change
    return dict(sorted(delta.items(), key=lambda kv: -kv[1]))


def headline(result):
    runs = result['ci_runs']
    main_runs = [v for k, v in runs.items() if k.startswith('main-')]
    branch_runs = [v for k, v in runs.items() if k.startswith('branch-')]
    complete = lambda label: {k: sum(f[k] for f in runs[label]['per_flow'].values())
                              for k in ('single', 'persistent', 'pairs', 'cases')}
    main_median = statistics.median(v['ms_per_case'] for v in main_runs)
    branch_median = statistics.median(v['ms_per_case'] for v in branch_runs)
    same = {}
    for flow in ('maintenance', 'restart_index', 'restart_tail'):
        same[flow] = {'main_ms_per_case_median': statistics.median(v['per_flow'][flow]['ms_per_case'] for v in main_runs if flow in v['per_flow']),
                      'branch_ms_per_case_median': statistics.median(v['per_flow'][flow]['ms_per_case'] for v in branch_runs if flow in v['per_flow'])}
    local = result['local']
    out = {'cases_ci': {'main': complete('main-a'), 'branch': complete('branch-a')},
           'ms_per_case_ci': {'main_runs': [v['ms_per_case'] for v in main_runs], 'branch_runs': [v['ms_per_case'] for v in branch_runs],
                              'main_median': main_median, 'branch_median': branch_median,
                              'ratio': round(branch_median / main_median, 3), 'identical_count_flows': same}}
    out['cases_ci']['ratio'] = round(out['cases_ci']['branch']['cases'] / out['cases_ci']['main']['cases'], 3)
    if 'main' in local and 'branch' in local:
        matching = [f for f, v in local['branch']['per_flow'].items()
                    if (v['single'], v['pairs']) == (runs['branch-a']['per_flow'][f]['single'], runs['branch-a']['per_flow'][f]['pairs'])
                    and (local['main']['per_flow'][f]['single'], local['main']['per_flow'][f]['pairs'])
                    == (runs['main-a']['per_flow'][f]['single'], runs['main-a']['per_flow'][f]['pairs'])]
        extra = local['branch']['total']['pairs'] - local['main']['total']['pairs']
        chrome = sum(v for k, v in local['branch']['pairs_by_cleanup_site'].items() if 'chrome/committed.py:journal_reader' in k)
        out['local_reproduction'] = {'flows_matching_ci_exactly': len(matching),
                                     'flows_differing_by_mac_only_steps': sorted(set(local['branch']['per_flow']) - set(matching)),
                                     'cases': {k: local[k]['total']['cases'] for k in ('main', 'branch', 'branch-realstat') if k in local},
                                     'extra_pairs': extra, 'extra_pairs_at_chrome_journal_reader': chrome,
                                     'chrome_share_of_extra_pairs': round(chrome / extra, 4)}
    if 'primaries' in local:
        out['primaries_without_header_index_equal_main'] = all(
            v['branch_without_header_index'] == v['main'] for v in local['primaries'].values())
    latency = local['mail_call_latency']
    if latency:
        table = {}
        for history in ('0', '1000', '4000'):
            for call in ('search', 'read', 'file', 'compose', 'prepare_send', 'expiry'):
                cell = {}
                for side in ('main', 'branch'):
                    rows = [v['phases'][history][call] for k, v in latency.items() if k.startswith('plain-' + side)]
                    cell[side] = {'median_ms': round(statistics.fmean(r['median_ms'] for r in rows), 3),
                                  'p95_ms': round(statistics.fmean(r['p95_ms'] for r in rows), 3), 'rounds': len(rows)}
                cell['branch_over_main_median'] = round(cell['branch']['median_ms'] / cell['main']['median_ms'], 3)
                table.setdefault(history, {})[call] = cell
        out['mail_call_latency_plain'] = table
    return out


def main():
    directory, record = Path(sys.argv[1]), Path(sys.argv[2])
    ci = load(directory, 'ci.json')
    result = {'ci_runs': {}, 'local': {}}
    for label, entry in ci.items():
        result['ci_runs'][label] = {k: entry[k] for k in ('run', 'flows_finished', 'cases', 'seconds', 'ms_per_case')}
        result['ci_runs'][label]['per_flow'] = {f: {k: v[k] for k in ('shard', 'single', 'persistent', 'pairs', 'cases', 'seconds', 'ms_per_case')}
                                                for f, v in sorted(entry['flows'].items())}
    singles = {side: load(directory, f'allsingles-{side}.json') for side in ('main', 'branch', 'branch-realstat')}
    for side, report in singles.items():
        if report is None:
            continue
        per_flow, total = sweep_counts(report)
        result['local'][side] = {'total': total, 'per_flow': per_flow, 'pairs_by_cleanup_site': pair_sites(report)}
    clean_main, clean_branch = load(directory, 'clean-main.json'), load(directory, 'clean-branch.json')
    noindex = load(directory, 'clean-branch-noindex.json')
    result['local']['clean_point_delta_by_site'] = point_sites(clean_main, clean_branch)
    if noindex:
        result['local']['primaries'] = {flow: {'main': clean_main[flow]['primaries'], 'branch': clean_branch[flow]['primaries'],
                                               'branch_without_header_index': noindex[flow]['primaries']}
                                        for flow in flows(clean_main)}
    result['local']['journal_reads_per_clean_call'] = {
        flow: {'main': clean_main[flow]['labels'].get('journal.close', 0), 'branch': clean_branch[flow]['labels'].get('journal.close', 0)}
        for flow in flows(clean_main)}
    costs = {}
    for name in sorted(directory.glob('cost-*.json')):
        costs[name.stem.removeprefix('cost-')] = json.loads(name.read_text())
    result['local']['case_cost_ms'] = costs
    latency = {}
    for name in sorted(directory.glob('latency-*.json')):
        latency[name.stem.removeprefix('latency-')] = json.loads(name.read_text())
    result['local']['mail_call_latency'] = latency
    result['local']['full_disk_read'] = {side: load(directory, f'fulldisk-{side}.json') for side in ('main', 'branch')}
    result['headline'] = headline(result)
    if len(sys.argv) > 3:
        result = {**json.loads(Path(sys.argv[3]).read_text()), **result}
    record.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
