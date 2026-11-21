#!/usr/bin/python3
"""Package 318: read one run's public records into the numbers FINDINGS.md uses. Read-only.

    read_run.py <runs/name>

The run measure is PLAN.md's: for a recorded thread (rt-freeze.json), the longest stretch after the thaw write of
consecutive 10 ms samples (thaw-samples.csv) in which its voluntary_ctxt_switches stays the same, measured as the sum
of its schedstat CPU-time increases across that stretch. Only rows at or after the thaw write count.
"""
import csv
import json
import pathlib
import re
import sys

LIMIT = re.compile(r'^Max realtime timeout\s+(\S+)\s+(\S+)\s+(\S+)', re.M)


def load(run, name):
    path = run / name
    if not path.exists():
        return None
    text = path.read_text()
    if name.endswith('.json'):
        return json.loads(text)
    if name.endswith('.jsonl'):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return text


def thaw_write_ns(run):
    for row in load(run, 'actions.jsonl') or []:
        if row.get('what') == 'thaw' or row.get('action') == 'thaw':
            if 'write_monotonic_ns' in row:
                return row['write_monotonic_ns']
    return None


def stretches(rows, start_ns):
    """The longest no-voluntary-switch stretch at or after start_ns: (cpu_ns, first row, last row, wall ns)."""
    rows = [r for r in rows if int(r['monotonic_ns']) >= start_ns and r['voluntary'] != '']
    best = (0, None, None)
    run_cpu, first = 0, rows[0] if rows else None
    for before, after in zip(rows, rows[1:]):
        if after['voluntary'] == before['voluntary']:
            run_cpu += int(after['cpu_ns']) - int(before['cpu_ns'])
            if run_cpu > best[0]:
                best = (run_cpu, first, after)
        else:
            run_cpu, first = 0, after
    return best


def summary(run):
    run = pathlib.Path(run)
    freeze = load(run, 'rt-freeze.json') or {}
    exit_record = load(run, 'exit.json') or {}
    thaw_ns = thaw_write_ns(run)
    out = {'run': run.name, 'thaw_write_ns': thaw_ns}
    limits = LIMIT.search(freeze.get('limits', '') or '')
    out['rt_limit'] = limits.groups() if limits else None
    out['recorded'] = [{k: t.get(k) for k in ('tid', 'comm', 'policy', 'flags', 'priority')}
                       for t in freeze.get('realtime', [])]
    demote = load(run, 'rt-demote.json')
    if demote is not None:
        out['demote'] = demote
    prethaw = load(run, 'rt-prethaw.json')
    if prethaw is not None:
        out['prethaw'] = {k: prethaw.get(k) for k in ('invalid', 'realtime') if k in prethaw}
    by_tid = {}
    with (run / 'thaw-samples.csv').open() as source:
        for row in csv.DictReader(source):
            by_tid.setdefault(int(row['tid']), []).append(row)
    out['threads'] = []
    for tid, rows in sorted(by_tid.items()):
        cpu, first, last = stretches(rows, thaw_ns) if thaw_ns else (None, None, None)
        after = [r for r in rows if thaw_ns and int(r['monotonic_ns']) >= thaw_ns]
        entry = {'tid': tid, 'recorded_realtime': any(t.get('tid') == tid for t in freeze.get('realtime', [])),
                 'rows': len(rows), 'rows_after_thaw': len(after),
                 'longest_no_switch_cpu_ms': round(cpu / 1e6, 3) if cpu is not None else None}
        if first and last:
            entry['stretch_from_thaw_ms'] = round((int(first['monotonic_ns']) - thaw_ns) / 1e6, 3)
            entry['stretch_to_thaw_ms'] = round((int(last['monotonic_ns']) - thaw_ns) / 1e6, 3)
            entry['stretch_policies'] = sorted({first['policy'], last['policy']})
        before = [r for r in rows if thaw_ns and int(r['monotonic_ns']) < thaw_ns]
        if before:
            # The frozen thread's totals, for context: the measure itself never uses rows before the thaw write.
            entry['frozen_cpu_s'] = round(int(before[-1]['cpu_ns']) / 1e9, 3)
            entry['frozen_voluntary'] = int(before[-1]['voluntary'])
            if after:
                entry['cpu_since_last_frozen_sample_ms'] = round(
                    (int(after[-1]['cpu_ns']) - int(before[-1]['cpu_ns'])) / 1e6, 3)
        if after:
            entry['first_row_after_thaw_ms'] = round((int(after[0]['monotonic_ns']) - thaw_ns) / 1e6, 3)
            entry['last_row_after_thaw_ms'] = round((int(after[-1]['monotonic_ns']) - thaw_ns) / 1e6, 3)
            entry['cpu_after_thaw_ms'] = round((int(after[-1]['cpu_ns']) - int(after[0]['cpu_ns'])) / 1e6, 3)
            entry['voluntary_after_thaw'] = int(after[-1]['voluntary']) - int(after[0]['voluntary'])
            entry['nonvoluntary_after_thaw'] = int(after[-1]['nonvoluntary']) - int(after[0]['nonvoluntary'])
            # The coarse curve: CPU time gained by the last sample of each 100 ms after the thaw write.
            bins = {}
            for row in after:
                index = (int(row['monotonic_ns']) - thaw_ns) // 100_000_000
                bins[index] = int(row['cpu_ns'])
            previous = int(after[0]['cpu_ns'])
            curve = []
            for index in range(0, max(bins) + 1):
                if index in bins:
                    curve.append(round((bins[index] - previous) / 1e6, 1))
                    previous = bins[index]
                else:
                    curve.append(None)
            entry['cpu_ms_per_100ms'] = curve
        out['threads'].append(entry)
    scans = load(run, 'thaw-scan.jsonl') or []
    out['realtime_after_thaw_scans'] = sorted({t['tid'] for s in scans if thaw_ns and s['monotonic_ns'] >= thaw_ns
                                              for t in s['realtime']})
    out['exit'] = {k: exit_record.get(k) for k in ('outcome', 'signal', 'source', 'signal_source', 'gradle_exit_value',
                                                   'after_return_ms', 'cleanup_started_before_exit')}
    if thaw_ns and exit_record.get('exit_detected_ns'):
        out['exit']['detected_after_thaw_ms'] = round((exit_record['exit_detected_ns'] - thaw_ns) / 1e6, 3)
    out['card'] = [(c['label'], c['runtime_status']) for c in load(run, 'card-status.jsonl') or []]
    return out


if __name__ == '__main__':
    result = summary(sys.argv[1])
    print(json.dumps(result, indent=1))
