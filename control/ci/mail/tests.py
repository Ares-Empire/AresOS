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


def main(selection):
    if selection not in {'all', 'suite', 'sweep'}:
        raise SystemExit('Choose all, suite or sweep')
    root = Path(__file__).resolve().parents[2] / 'mail_tests'
    sys.path.insert(0, str(root))
    sweep = {'test_review23_sweep', 'test_review24_io', 'test_owner_state_sweep'}
    names = [p.stem for p in sorted(root.glob('test*.py'))
             if selection == 'all' or (p.stem in sweep) == (selection == 'sweep')]
    parallel = 'test_owner_state_sweep' in names
    if parallel:
        names.remove('test_owner_state_sweep')
    started = time.monotonic()
    def run():
        return unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    if parallel:
        environment = {**os.environ, 'PYTHONPATH': str(root) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        result, good = run_workers([sys.executable, '-m', 'unittest', '-v', 'test_owner_state_sweep'], environment, run)
    else:
        result, good = run(), True
    print(f'Mail selection={selection}: {result.testsRun} in-process tests; owner_workers={2 if parallel else 0}; elapsed={time.monotonic() - started:.3f}s', flush=True)
    return not result.wasSuccessful() or not good


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
