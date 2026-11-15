"""Time per sweep case, split by phase, replicating test_review23_sweep.fault().

Run with cwd = <worktree>/control/mail_tests, PYTHONPATH as for discover.py.
Usage: case_cost.py OUT.json [--profile] flow...
Each flow: clean discovery, then every primary point in single mode (the same
work as the sweep's 'single' cases, minus its assertions), timing Scenario
construction, the faulted call, recovery and close separately.
"""
import cProfile
import io
import json
import os
import pstats
import statistics
import sys
from time import perf_counter
from pathlib import Path

import hostenv
hostenv.install()
import experiments
EXPERIMENTS = experiments.apply()
from test_review23_sweep import Scenario
from storage_faults import OSWrites


def run(flow, number):
    phases = {}
    started = perf_counter()
    scenario = Scenario(flow)
    phases['setup'] = perf_counter() - started
    try:
        sweep = OSWrites(number)
        started = perf_counter()
        with scenario.phase('call'), scenario.observed(), sweep.wrap(None if flow.startswith('restart_') else scenario.fixture.engine.store):
            scenario.call()
        phases['call'] = perf_counter() - started
        started = perf_counter()
        with scenario.phase('recovery'):
            scenario.recover(failed=True)
        phases['recover'] = perf_counter() - started
    finally:
        started = perf_counter()
        scenario.close()
        phases['close'] = perf_counter() - started
    phases['total'] = sum(phases.values())
    return phases


def main():
    out = Path(sys.argv[1])
    profile = '--profile' in sys.argv
    flows = [a for a in sys.argv[2:] if not a.startswith('--')]
    report = {}
    profiler = cProfile.Profile() if profile else None
    for flow in flows:
        scenario = Scenario(flow)
        try:
            sweep = OSWrites()
            with scenario.observed(), sweep.wrap(None if flow.startswith('restart_') else scenario.fixture.engine.store):
                scenario.call()
            points = sweep.points
            scenario.recover()
        finally:
            scenario.close()
        numbers = [n for n, label in enumerate(points, 1) if not label.endswith('.close')]
        for n in numbers[:5]:
            run(flow, n)  # warm-up
        if profiler:
            profiler.enable()
        rows = [run(flow, n) for n in numbers]
        if profiler:
            profiler.disable()
        report[flow] = {phase: {'median_ms': statistics.median(r[phase] for r in rows) * 1000,
                                'mean_ms': statistics.fmean(r[phase] for r in rows) * 1000}
                        for phase in rows[0]}
        report[flow]['cases'] = len(rows)
        print(flow, {p: round(v['median_ms'], 2) for p, v in report[flow].items() if p != 'cases'}, flush=True)
    report['_experiments'] = EXPERIMENTS
    out.write_text(json.dumps(report, indent=1, sort_keys=True))
    if profiler:
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(45)
        out.with_suffix('.profile.txt').write_text(stream.getvalue())


if __name__ == '__main__':
    main()
