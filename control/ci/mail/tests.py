"""Disjoint CI selections with isolated processes for the owner fault sweep."""
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


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


def select_names(selection, modules, shard=0, shards=1):
    if selection not in {'all', 'suite', 'sweep', 'perturb'}:
        raise ValueError('Choose all, suite, sweep or perturb')
    if shards < 1 or shard not in range(shards):
        raise ValueError('Invalid suite shard')
    sweep = {'test_review23_sweep', 'test_review24_io', 'test_owner_state_sweep'}
    names = [name for name in sorted(modules) if selection == 'all' or
        selection == 'sweep' and name in sweep or
        selection == 'perturb' and name == 'test_owner_state_perturb' or
        selection == 'suite' and name not in sweep | {'test_owner_state_perturb'}]
    return [name for index, name in enumerate(names) if index % shards == shard] if selection == 'suite' else names


def main(selection):
    root = Path(__file__).resolve().parents[2] / 'mail_tests'
    sys.path.insert(0, str(root))
    names = select_names(selection, [p.stem for p in root.glob('test*.py')],
        int(os.environ.get('MAIL_SUITE_SHARD', '0')), int(os.environ.get('MAIL_SUITE_SHARDS', '1')))
    parallel = 'test_owner_state_sweep' in names
    if parallel:
        names.remove('test_owner_state_sweep')
    started = time.monotonic()
    def run():
        # The owner worker keeps its twelve ledger buckets. The inherited
        # whole-flow sweep partitions across every group/job exactly once.
        group = int(os.environ.get('MAIL_FLOW_GROUP', '0'))
        groups = int(os.environ.get('MAIL_FLOW_GROUPS', '1'))
        inherited = {} if selection != 'sweep' else {
            'MAIL_SWEEP_SHARD': str(group * int(os.environ.get('MAIL_SWEEP_SHARDS', '1')) + int(os.environ.get('MAIL_SWEEP_SHARD', '0'))),
            'MAIL_SWEEP_SHARDS': str(groups * int(os.environ.get('MAIL_SWEEP_SHARDS', '1')))}
        with patch.dict(os.environ, inherited):
            return unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    if parallel:
        environment = {**os.environ, 'PYTHONPATH': str(root) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        result, good = run_workers([sys.executable, '-m', 'unittest', '-v', 'test_owner_state_sweep'], environment, run, count=int(os.environ.get('OWNER_SWEEP_WORKERS', '3')))
    else:
        result, good = run(), True
    print(f'Mail selection={selection}: {result.testsRun} in-process tests; owner_workers={int(os.environ.get('OWNER_SWEEP_WORKERS', '3')) if parallel else 0}; elapsed={time.monotonic() - started:.3f}s', flush=True)
    return not result.wasSuccessful() or not good


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
