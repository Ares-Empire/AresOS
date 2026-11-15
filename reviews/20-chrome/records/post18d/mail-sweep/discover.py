"""Clean discovery of the Mail fault sweep's points, with call-site attribution.

Run with cwd = <worktree>/control/mail_tests and
PYTHONPATH=<worktree>/control:<worktree>/control/mail_tests.
Usage: discover.py OUT.json [--singles] [flow ...]
Replicates test_review23_sweep's clean run (Scenario, OSWrites.wrap, call) and,
with --singles, every single-mode fault run, whose cleanup list fixes the pair
count exactly as the sweep computes it (cleanups after the failed point).
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import hostenv
hostenv.install()
import experiments
EXPERIMENTS = experiments.apply()
import storage_faults
import test_review23_sweep as sweep_module
from test_review23_sweep import Scenario, FLOWS
from storage_faults import OSWrites

ROOT = Path.cwd().resolve().parents[1]


def chain():
    # Walk code objects directly: traceback/linecache would stat source files,
    # which the sweep's ambient-timestamp guard correctly rejects.
    frames, frame = [], sys._getframe(1)
    while frame is not None:
        path = frame.f_code.co_filename
        if '/aresos_control/' in path:
            frames.append(path.split('/aresos_control/', 1)[1] + ':' + frame.f_code.co_name)
        frame = frame.f_back
    return frames[::-1]


class Traced(OSWrites):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sites = []

    def hit(self, label, sqlite=False):
        if not storage_faults.EXCLUDED:
            self.sites.append(chain())
        return super().hit(label, sqlite)


def site(frames):
    # Innermost frame in Chrome code if any, else innermost runtime frame.
    for frame in reversed(frames):
        if frame.startswith('chrome/'):
            return frame
    return frames[-1] if frames else '<test fixture>'


def origin(frames):
    # Outermost Chrome-reaching caller: the shared code that called into Chrome.
    for index, frame in enumerate(frames):
        if frame.startswith('chrome/'):
            return frames[index - 1] + ' -> ' + frame if index else frame
    return None


def clean(flow):
    timings = {}
    started = time.perf_counter()
    scenario = Scenario(flow)
    timings['setup'] = time.perf_counter() - started
    try:
        probe = Traced()
        started = time.perf_counter()
        with scenario.observed(), probe.wrap(None if flow.startswith('restart_') else scenario.fixture.engine.store):
            result = scenario.call()
        timings['call'] = time.perf_counter() - started
        started = time.perf_counter()
        scenario.recover()
        timings['recover'] = time.perf_counter() - started
    finally:
        started = time.perf_counter()
        scenario.close()
        timings['close'] = time.perf_counter() - started
    return probe, result, timings


def single(flow, number):
    scenario = Scenario(flow)
    try:
        probe = Traced(number)
        with scenario.phase('call'), scenario.observed(), probe.wrap(None if flow.startswith('restart_') else scenario.fixture.engine.store):
            scenario.call()
        with scenario.phase('recovery'):
            scenario.recover(failed=True)
    finally:
        scenario.close()
    return probe


def main():
    out = Path(sys.argv[1])
    singles = '--singles' in sys.argv
    flows = [a for a in sys.argv[2:] if not a.startswith('--')] or list(FLOWS)
    report = {}
    for flow in flows:
        probe, result, timings = clean(flow)
        points = probe.points
        entry = {
            'points': len(points),
            'labels': dict(Counter(points)),
            'primaries': sum(1 for label in points if not label.endswith('.close')),
            'by_site': Counter(),
            'chrome_reached_from': Counter(),
            'ok': result.get('ok'),
            'clean_timings': timings,
        }
        for label, frames in zip(points, probe.sites):
            entry['by_site'][label + ' @ ' + site(frames)] += 1
            reached = origin(frames)
            if reached:
                entry['chrome_reached_from'][label + ' @ ' + reached] += 1
        if singles:
            pairs, by_cleanup, elapsed = 0, Counter(), []
            for number, label in enumerate(points, 1):
                if label.endswith('.close'):
                    continue
                started = time.perf_counter()
                fault = single(flow, number)
                elapsed.append(time.perf_counter() - started)
                for cleanup_at, cleanup_label, purpose in fault.cleanup_points:
                    if cleanup_at <= number:
                        continue
                    pairs += 1
                    frames = fault.sites[cleanup_at - 1]
                    by_cleanup[cleanup_label + ' @ ' + site(frames) + ' [' + purpose + ']'] += 1
            entry['pairs'] = pairs
            entry['pairs_by_cleanup_site'] = dict(by_cleanup.most_common())
            elapsed.sort()
            entry['single_case_seconds'] = {'n': len(elapsed), 'median': elapsed[len(elapsed) // 2] if elapsed else None,
                                            'mean': sum(elapsed) / len(elapsed) if elapsed else None}
        entry['by_site'] = dict(entry['by_site'].most_common())
        entry['chrome_reached_from'] = dict(entry['chrome_reached_from'].most_common())
        report[flow] = entry
        print(flow, entry['points'], entry.get('pairs'), {k: round(v, 3) for k, v in timings.items()}, flush=True)
    report['_experiments'] = EXPERIMENTS
    out.write_text(json.dumps(report, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
