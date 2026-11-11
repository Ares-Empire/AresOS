"""Disjoint CI selections with isolated processes for the owner fault sweep."""
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


def run_workers(command, environment, task, count=2):
    # A separate process is necessary: fault injection patches global Python
    # functions and SQLite's VFS. Threads would inject into another scenario.
    work = Path(__file__).resolve().parents[3] / '.work'
    work.mkdir(exist_ok=True)
    processes = []
    with tempfile.TemporaryDirectory(prefix='owner-workers-', dir=work) as temporary, ExitStack() as files:
        logs = []
        try:
            for worker in range(count):
                path = Path(temporary) / f'{worker}.txt'
                output = files.enter_context(path.open('w'))
                logs.append(path)
                processes.append(subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                    env={**environment, 'OWNER_SWEEP_WORKER': str(worker), 'OWNER_SWEEP_WORKERS': str(count)}))
            result = task()
            good = True
            for worker, (process, path) in enumerate(zip(processes, logs)):
                code = process.wait()
                print(path.read_text(), end='', flush=True)
                print(f'Owner sweep worker={worker}/{count} exit={code}', flush=True)
                good &= code == 0
            return result, good
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


def flow_partition(flows, group=0, groups=1, isolated=()):
    if groups < 1 or group not in range(groups):
        raise ValueError('Invalid flow group')
    if isolated and groups > 1:
        if group == groups - 1:
            return tuple(flow for flow in flows if flow in isolated)
        flows = tuple(flow for flow in flows if flow not in isolated)
        groups -= 1
    return tuple(flows[group::groups])


INHERITED = {'test_review23_sweep', 'test_review24_io'}
OPTIONAL_MODULES = {'test_owner_state_sweep', 'test_owner_state_contracts'}
ALTERATIONS = {'test_owner_state_perturb', 'test_owner_state_plants'}
OPTIONAL_CASES = {
    'test_owner_state_regressions.ReviewRegressions.' + name for name in (
        'test_review22_live_rename_trash_with_unresolved_drafts_M03_C03',
        'test_review22_refused_recovery_result_keeps_changed_evidence_M03_C03',
        'test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13')
}


def select_names(selection, modules, shard=0, shards=1):
    if selection not in {'all', 'suite', 'sweep', 'owner', 'perturb'}:
        raise ValueError('Choose all, suite, sweep, owner or perturb')
    if shards < 1 or shard not in range(shards):
        raise ValueError('Invalid suite shard')
    names = [name for name in sorted(modules) if selection == 'all' or
        selection == 'sweep' and name in INHERITED or
        selection == 'owner' and name in OPTIONAL_MODULES | {'test_owner_state_regressions'} or
        selection == 'perturb' and name in ALTERATIONS or
        selection == 'suite' and name not in INHERITED | OPTIONAL_MODULES | ALTERATIONS]
    return [name for index, name in enumerate(names) if index % shards == shard] if selection == 'suite' else names


def select_cases(suite, selection):
    from ci.base import cases
    def include(case):
        if selection == 'suite':
            return case.id() not in OPTIONAL_CASES
        if selection == 'owner' and case.id().startswith('test_owner_state_regressions.'):
            return case.id() in OPTIONAL_CASES
        return True
    return unittest.TestSuite(case for case in cases(suite) if include(case))


def alteration_label(name):
    # Fault offsets are discovered on each platform, not hardcoded selections.
    parts = name.split('/')
    if parts[0] == 'sweep' and len(parts) > 2 and parts[2].isdigit():
        parts[2] = '<discovered>'
    return '/'.join(parts)


def alteration_partition(recordings, costs, shards):
    """Balance measured evaluation time, splitting the four longest recordings.

    A split owns candidate ordinals modulo its part count. Every recording and
    every candidate still runs once; changed corpus ordering requires new costs.
    """
    if shards < 1:
        raise ValueError('Invalid alteration shard count')
    if [(c['index'], c['scenario']) for c in costs] != list(enumerate(map(alteration_label, recordings))):
        raise ValueError(('Alteration corpus changed; update measured cost manifest',
                          [(c['index'], c['scenario'], recordings[c['index']] if c['index'] < len(recordings) else None)
                           for c in costs if c['index'] >= len(recordings) or c['scenario'] != recordings[c['index']]],
                          len(recordings), len(costs)))
    loads, assignments = [0.0] * shards, [[] for _ in range(shards)]
    tasks = [(c['seconds'] / c['parts'], c['index'], part, c['parts'])
             for c in costs for part in range(c['parts'])]
    for seconds, index, part, parts in sorted(tasks, key=lambda task: (-task[0], task[1], task[2])):
        shard = min(range(shards), key=lambda s: (loads[s], s))
        loads[shard] += seconds
        assignments[shard].append((index, part, parts))
    return [sorted(tasks) for tasks in assignments]


def main(selection):
    root = Path(__file__).resolve().parents[2] / 'mail_tests'
    sys.path.insert(0, str(root))
    names = select_names(selection, [p.stem for p in root.glob('test*.py')],
        int(os.environ.get('MAIL_SUITE_SHARD', '0')), int(os.environ.get('MAIL_SUITE_SHARDS', '1')))
    parallel = 'test_owner_state_sweep' in names
    if parallel:
        names.remove('test_owner_state_sweep')
    if selection == 'owner' and (int(os.environ.get('MAIL_FLOW_GROUP', '0')) != 0 or
                                 int(os.environ.get('MAIL_SWEEP_SHARD', '0')) != 0):
        names = []
    started = time.monotonic()
    def run():
        return unittest.TextTestRunner(verbosity=2).run(select_cases(unittest.defaultTestLoader.loadTestsFromNames(names), selection))
    if parallel:
        environment = {**os.environ, 'PYTHONPATH': str(root) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        result, good = run_workers([sys.executable, '-m', 'unittest', '-v', 'test_owner_state_sweep'], environment, run, count=int(os.environ.get('OWNER_SWEEP_WORKERS', '3')))
    else:
        result, good = run(), True
    print(f'Mail selection={selection}: {result.testsRun} in-process tests; owner_workers={int(os.environ.get('OWNER_SWEEP_WORKERS', '3')) if parallel else 0}; elapsed={time.monotonic() - started:.3f}s', flush=True)
    return not result.wasSuccessful() or not good


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
