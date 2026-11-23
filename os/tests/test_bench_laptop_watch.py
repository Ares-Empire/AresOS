import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from test_bench_laptop_gates import ROOT, fixture, memory, psi
from test_bench_laptop_store import MIB, mock_space, roots
from laptop import Cancelled, Watch
from laptop_cli import Bench, RunExit
from store import Store

WORKER = """
import os
import signal
import subprocess
import sys
child = subprocess.Popen([sys.executable, '-c', 'import signal; signal.pause()'])
print(os.getpid(), child.pid, flush=True)
signal.pause()
"""


class StandInScopes:
    """Use only PID handles of the workers this fixture started."""
    def __init__(self, root):
        self.root = root

    def start(self, mode, unit, command, env):
        child = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
        if not select.select([child.stdout], [], [], 5)[0]:
            child.kill()
            child.wait()
            raise RuntimeError('stand-in startup timed out')
        report = child.stdout.readline().decode()
        child.stdout.close()
        _, descendant = map(int, report.split())
        self.descendant = os.pidfd_open(descendant)
        (self.root / 'worker-ids').write_text(report)
        return child

    def stop(self, unit):
        if (self.root / 'hold-stop').exists():
            (self.root / 'stopping').write_text('waiting\n')
            deadline = time.monotonic() + 5
            while not (self.root / 'finish-stop').exists() and time.monotonic() < deadline:
                time.sleep(0.01)
        signal.pidfd_send_signal(self.descendant, signal.SIGKILL)
        select.select([self.descendant], [], [], 5)
        os.close(self.descendant)
        (self.root / 'stopped').write_text(str(time.monotonic()))


def run_watcher(root, recheck):
    inputs = fixture(root)
    store = Store(*roots(root), disk_space=mock_space)
    scopes = StandInScopes(root)

    def setup(phase):
        phase.write('test-disk', 'overlay', b'fixture')
        if recheck:
            memory(inputs, 1)
        return [sys.executable, '-c', WORKER]

    def graceful(reason):
        (root / 'graceful').write_text(f'{time.monotonic()}\n{reason}\n')

    try:
        Bench(inputs, store).run('vm', {'test-disk': MIB}, setup, scopes=scopes, graceful=graceful,
                                 policy=Watch(interval=1.0, grace=0.3))
    except RunExit as error:
        return error.status
    except Cancelled as error:
        print(error, file=sys.stderr)
        return 1
    return 0


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix='.bench-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tree').mkdir()

    def child(self, *command):
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.reap, process)
        return process

    def reap(self, process):
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        process.stderr.close()

    def wait_result(self, path, watcher, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists() and path.stat().st_size:
                return path.read_text()
            if watcher.poll() is not None:
                self.fail(f'watcher ended early: {watcher.stderr.read()}')
            time.sleep(0.01)
        self.fail(f'timed out waiting for {path.name}')

    def watch_case(self, cause):
        game = self.child(sys.executable, '-c', 'import signal; signal.pause()')
        watcher = self.child(sys.executable, '-B', __file__, str(self.root), 'watch')
        leader, child = map(int, self.wait_result(self.root / 'worker-ids', watcher).split())
        handles = [os.pidfd_open(pid) for pid in (leader, child)]
        try:
            changed = time.monotonic()
            if cause == 'memory':
                (self.root / 'meminfo.new').write_text('MemAvailable: 1 kB\n')
                (self.root / 'meminfo.new').replace(self.root / 'meminfo')
            elif cause == 'pressure':
                (self.root / 'pressure.new').write_text('some avg10=90.00 avg60=0.00 avg300=0.00 total=0\n')
                (self.root / 'pressure.new').replace(self.root / 'pressure')
            else:
                watcher.kill()
            self.assertEqual(watcher.wait(timeout=5), -signal.SIGKILL if cause == 'watcher' else 1)
            for fd in handles:
                self.assertTrue(select.select([fd], [], [], 5)[0], 'stand-in scope member survived')
            deadline = time.monotonic() + 5
            stopped = self.root / 'stopped'
            while not stopped.exists() or not stopped.stat().st_size:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            ended = float(stopped.read_text())
            self.assertIsNone(game.poll(), 'unrelated stand-in game was stopped')
            self.assertLess(ended - changed, 3)
            graceful = self.root / 'graceful'
            store = Store(*roots(self.root), disk_space=mock_space)
            if cause == 'watcher':
                self.assertFalse(graceful.exists())
                print(f'{cause}: stop {ended - changed:.3f}s', flush=True)
                self.assertTrue(store.active.exists())
                # The guardian inherits stderr and the lock. EOF proves it has closed both.
                self.assertEqual(watcher.stderr.read(), '')
                store.expire()
            else:
                detected, reason = graceful.read_text().splitlines()
                elapsed = float(detected) - changed
                self.assertIn(cause, reason)
                self.assertLess(elapsed, 2)
                self.assertGreaterEqual(ended - float(detected), 0.25)
                print(f'{cause}: detection {elapsed:.3f}s, stop {ended - changed:.3f}s', flush=True)
            self.assertFalse((store.root / 'test-disk').exists())
        finally:
            for fd in handles:
                if not select.select([fd], [], [], 0)[0]:
                    signal.pidfd_send_signal(fd, signal.SIGKILL)
                os.close(fd)

    def test_falling_memory_stops_only_the_owned_tree(self):
        self.watch_case('memory')

    def test_rising_pressure_stops_only_the_owned_tree(self):
        self.watch_case('pressure')

    def test_sigkilling_watcher_stops_only_the_owned_tree(self):
        self.watch_case('watcher')

    def test_rechecks_gates_after_phase_setup_before_launch(self):
        watcher = self.child(sys.executable, '-B', __file__, str(self.root), 'recheck')
        self.assertEqual(watcher.wait(timeout=5), 75)
        self.assertIn('needs 7 GiB', watcher.stderr.read())
        self.assertFalse((self.root / 'worker-ids').exists())
        self.assertFalse((self.root / 'store/test-disk').exists())

    def test_signal_during_scope_stop_preserves_disk_until_stop_finishes(self):
        (self.root / 'hold-stop').touch()
        watcher = self.child(sys.executable, '-B', __file__, str(self.root), 'watch')
        self.wait_result(self.root / 'worker-ids', watcher)
        (self.root / 'meminfo.new').write_text('MemAvailable: 1 kB\n')
        (self.root / 'meminfo.new').replace(self.root / 'meminfo')
        self.wait_result(self.root / 'stopping', watcher)
        watcher.terminate()
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                watcher.wait(timeout=0.15)
            self.assertTrue((self.root / 'store/test-disk/overlay').exists())
        finally:
            (self.root / 'finish-stop').touch()
        self.assertEqual(watcher.wait(timeout=5), 1)
        self.assertIn('interrupted by SIGTERM', watcher.stderr.read())
        self.assertFalse((self.root / 'store/test-disk').exists())


if __name__ == '__main__':
    sys.exit(run_watcher(Path(sys.argv[1]), sys.argv[2] == 'recheck'))
