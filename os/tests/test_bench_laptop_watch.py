from contextlib import ExitStack
import io
import os
from pathlib import Path
import resource
import select
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_bench_laptop_gates import ROOT, fixture, memory, mock_mount, replace_text
from test_bench_laptop_store import MIB, mock_space, roots
from laptop import Busy, Cancelled, OwnedScope, UserScopes, Watch
from laptop_cli import Bench, RunExit
from store import FixedDisk, PolledDirectory, RESERVE, Store

WORKER = """
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys

child = subprocess.Popen([sys.executable, '-B', '-c', 'import signal; signal.pause()'])
fd = os.pidfd_open(child.pid)
try:
    for channel_fd in sys.argv[2:]:
        with socket.socket(fileno=int(channel_fd)) as channel:
            socket.send_fds(channel, [b'worker'], [fd])
finally:
    os.close(fd)
Path(sys.argv[1]).write_text('started')
signal.pause()
"""

GROW = """
import os
from pathlib import Path
import sys
import time

with Path(sys.argv[1]).open('wb', buffering=0) as output:
    while True:
        output.write(b'x' * 32768)
        os.fsync(output.fileno())
        time.sleep(0.09)
"""

INVOCATION = 'a' * 32


def receive_handle(channel):
    label, (fd,), _, _ = socket.recv_fds(channel, 16, 1)
    os.set_inheritable(fd, False)
    return label.decode(), fd


class StandInScope:
    """The group belongs to our unreaped test launcher, in its own session."""
    def __init__(self, root, pid, launcher, descendants):
        self.root = root
        self.pid = pid
        self.launcher = launcher
        self.descendants = descendants

    def stop(self):
        if (self.root / 'stopped').exists():
            return True
        if (self.root / 'hold-stop').exists():
            (self.root / 'stopping').write_text('waiting\n')
            deadline = time.monotonic() + 5
            while not (self.root / 'finish-stop').exists() and time.monotonic() < deadline:
                time.sleep(0.01)
        try:
            os.killpg(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        assert select.select([self.launcher], [], [], 5)[0]
        if select.select([self.descendants], [], [], 0)[0]:
            _, descendant = receive_handle(self.descendants)
            try:
                assert select.select([descendant], [], [], 5)[0]
            finally:
                os.close(descendant)
        (self.root / 'stopped').write_text(str(time.monotonic()))
        return True


class StandInScopes:
    def __init__(self, root, inputs, case, handles, descendants, sender):
        self.root = root
        self.inputs = inputs
        self.case = case
        self.handles = handles
        self.descendants = descendants
        self.sender = sender

    def start(self, mode, unit, payload):
        (self.root / 'scope-started').touch()
        return subprocess.Popen(payload, env={'INVOCATION_ID': INVOCATION}, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, start_new_session=True,
                                pass_fds=(self.handles.fileno(), self.sender.fileno()))

    def pin(self, unit, pid, invocation, stack):
        assert invocation == INVOCATION
        if self.case == 'scoped-recheck':
            (self.root / 'scope-active').touch()
            memory(self.inputs, 1)
        if self.case == 'reserve-recheck':
            (self.root / 'scope-active').touch()
            (self.root / 'low-space').touch()
        launcher = os.pidfd_open(pid)
        stack.callback(os.close, launcher)
        socket.send_fds(self.handles, [b'launcher'], [launcher])
        return StandInScope(self.root, pid, launcher, self.descendants)


def run_watcher(root, case, handles, descendants, sender):
    inputs = fixture(root)
    if case == 'bad-memfree':
        inputs.meminfo.write_text(inputs.meminfo.read_text().replace('MemFree: 1 kB', 'MemFree: 20000000 kB'))
    if case == 'empty-power':
        for path in (inputs.power / 'AC').iterdir():
            path.unlink()
        (inputs.power / 'AC').rmdir()
    if case == 'charging-offline':
        (inputs.power / 'AC/online').write_text('0')
        battery = inputs.power / 'BAT0'
        battery.mkdir()
        (battery / 'type').write_text('Battery')
        (battery / 'status').write_text('Charging')

    def disk_space(path):
        if (root / 'low-space').exists():
            return 1, RESERVE, 4096
        return mock_space(path)

    store = Store(*roots(root), disk_space=disk_space, mount=mock_mount)
    scopes = StandInScopes(root, inputs, case, handles, descendants, sender)

    def setup(phase):
        phase.write('test-disk', 'overlay', b'fixture')
        if case == 'recheck':
            memory(inputs, 1)
        if case == 'unbounded':
            return [sys.executable, '-c', 'raise Exception("unbounded command executed")']
        if case == 'disk':
            output = phase.destination('evidence', 'growing')
            return phase.command([sys.executable, '-B', '-c', GROW, str(output)],
                                 outputs=[PolledDirectory('evidence', output.name, 256 * 1024, MIB)])
        if case == 'fixed':
            disk = phase.destination('evidence', 'fixed')
            outside = root / 'outside'
            program = """
import os
from pathlib import Path
import resource
import sys
disk, outside = map(Path, sys.argv[1:])
assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
try:
    outside.write_bytes(b'outside')
except PermissionError:
    pass
else:
    raise AssertionError('undeclared write succeeded')
with disk.open('r+b') as stream:
    stream.write(b'fixture')
    stream.flush()
    try:
        os.ftruncate(stream.fileno(), 65537)
    except OSError:
        pass
    else:
        raise AssertionError('fixed disk grew')
    try:
        os.posix_fallocate(stream.fileno(), 0, 65537)
    except PermissionError:
        pass
    else:
        raise AssertionError('allocation shortcut was allowed')
try:
    os.setxattr(disk, 'user.bench-fixture', b'fixture')
except PermissionError:
    pass
else:
    raise AssertionError('unbudgeted xattr was allowed')
"""
            _, hard_core = resource.getrlimit(resource.RLIMIT_CORE)
            resource.setrlimit(resource.RLIMIT_CORE, (hard_core, hard_core))
            return phase.command([sys.executable, '-B', '-c', program, str(disk), str(outside)],
                                 outputs=[FixedDisk('evidence', disk.name, 65536)])
        if case == 'interrupted-evidence':
            phase.write('evidence', 'finished', b'finished')
            kind, name = 'evidence', 'command-log'
        else:
            kind, name = 'test-disk', 'worker-ready'
        output = phase.destination(kind, name)
        return phase.command([sys.executable, '-B', '-c', WORKER, str(output),
                              str(handles.fileno()), str(sender.fileno())],
                             outputs=[PolledDirectory(kind, name, 256 * 1024, 128 * 1024)])

    def graceful(reason):
        (root / 'graceful').write_text(f'{time.monotonic()}\n{reason}\n')
        if case == 'disk':
            output, = store.evidence.path.glob('*/.growing.partial')
            (root / 'allocated-at-stop').write_text(str(output.stat().st_blocks * 512))

    fork = os.fork

    def record_guardian():
        pid = fork()
        if pid:
            fd = os.pidfd_open(pid)
            try:
                socket.send_fds(handles, [b'guardian'], [fd])
            finally:
                os.close(fd)
        return pid

    try:
        with patch('laptop.os.fork', side_effect=record_guardian):
            Bench(inputs, store).run('vm', {'test-disk': MIB, 'evidence': 2 * MIB}, setup,
                                 scopes=scopes, graceful=graceful,
                                 policy=Watch(interval=1.0, grace=0.3))
    except RunExit as error:
        return error.status
    except Busy as error:
        print(error, file=sys.stderr)
        return 75
    except Cancelled as error:
        print(error, file=sys.stderr)
        return 1
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    return 0


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix='.bench-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tree').mkdir()
        self.handle_channels = {}

    def child(self, *command, pass_fds=()):
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE, text=True, pass_fds=pass_fds)
        self.addCleanup(self.reap, process)
        return process

    def start_watcher(self, case, root=None):
        receiver, sender = socket.socketpair(type=socket.SOCK_SEQPACKET)
        self.addCleanup(receiver.close)
        with sender:
            fd = sender.fileno()
            watcher = self.child(sys.executable, '-B', __file__, str(root or self.root), case, str(fd),
                                 pass_fds=(fd,))
        self.handle_channels[watcher] = receiver
        return watcher

    def handles(self, watcher):
        result = {}
        for _ in range(3):
            channel = self.handle_channels[watcher]
            self.assertTrue(select.select([channel], [], [], 5)[0], 'stand-in pidfd was not sent')
            label, fd = receive_handle(channel)
            self.addCleanup(os.close, fd)
            result[label] = fd
        self.assertEqual(set(result), {'launcher', 'worker', 'guardian'})
        return result

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
        watcher = self.start_watcher('watch')
        self.wait_result(self.root / 'store/test-disk/worker-ready', watcher)
        handles = self.handles(watcher)
        workers = [handles['launcher'], handles['worker']]
        try:
            changed = time.monotonic()
            if cause == 'memory':
                replace_text(self.root / 'meminfo', 'MemTotal: 16384000 kB\nMemFree: 1 kB\nMemAvailable: 1 kB\n')
            elif cause == 'pressure':
                replace_text(self.root / 'pressure', 'some avg10=90.00 avg60=0.00 avg300=0.00 total=0\n'
                             'full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n')
            elif cause == 'guardian':
                signal.pidfd_send_signal(handles['guardian'], signal.SIGKILL)
            else:
                watcher.kill()
            self.assertEqual(watcher.wait(timeout=5), -signal.SIGKILL if cause == 'watcher' else 1)
            for fd in workers:
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
            store = Store(*roots(self.root), disk_space=mock_space, mount=mock_mount)
            if cause in ('watcher', 'guardian'):
                self.assertFalse(graceful.exists())
                print(f'{cause}: stop {ended - changed:.3f}s', flush=True)
                if cause == 'watcher':
                    self.assertTrue(store.active.exists())
                    # EOF follows the guardian closing its copy of the lock.
                    watcher.stderr.read()
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
            for fd in workers:
                if not select.select([fd], [], [], 0)[0]:
                    try:
                        signal.pidfd_send_signal(fd, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_falling_memory_stops_only_the_owned_tree(self):
        self.watch_case('memory')

    def test_rising_pressure_stops_only_the_owned_tree(self):
        self.watch_case('pressure')

    def test_sigkilling_watcher_stops_only_the_owned_tree(self):
        self.watch_case('watcher')

    def test_sigkilling_guardian_stops_only_the_owned_tree(self):
        self.watch_case('guardian')

    def test_guardian_loss_keeps_lock_and_disk_until_fallback_confirms_stop(self):
        (self.root / 'hold-stop').touch()
        watcher = self.start_watcher('watch')
        self.wait_result(self.root / 'store/test-disk/worker-ready', watcher)
        signal.pidfd_send_signal(self.handles(watcher)['guardian'], signal.SIGKILL)
        self.wait_result(self.root / 'stopping', watcher)
        store = Store(*roots(self.root), disk_space=mock_space, mount=mock_mount)
        try:
            with self.assertRaisesRegex(Busy, 'lock is busy'):
                store.clean()
            self.assertTrue((store.root / 'test-disk/overlay').is_file())
        finally:
            (self.root / 'finish-stop').touch()
        self.assertEqual(watcher.wait(timeout=5), 1)
        self.assertFalse((store.root / 'test-disk').exists())

    def test_exec_boundary_rechecks_memory_after_scope_activation(self):
        watcher = self.start_watcher('scoped-recheck')
        self.assertEqual(watcher.wait(timeout=5), 75, watcher.stderr.read())
        self.assertTrue((self.root / 'scope-active').exists())
        self.assertFalse((self.root / 'store/test-disk').exists())

    def test_reserve_rechecked_after_scope_activation_before_workload_release(self):
        watcher = self.start_watcher('reserve-recheck')
        status = watcher.wait(timeout=5)
        errors = watcher.stderr.read()
        self.assertEqual(status, 75, errors)
        self.assertTrue((self.root / 'scope-active').exists())
        self.assertIn('20 GB', errors)
        self.assertFalse((self.root / 'store/test-disk').exists())

    def test_contradictory_readings_refuse_with_exit_75(self):
        for case in ('bad-memfree', 'empty-power', 'charging-offline'):
            with self.subTest(case=case):
                root = self.root / case
                root.mkdir()
                (root / 'tree').mkdir()
                watcher = self.start_watcher(case, root=root)
                self.assertEqual(watcher.wait(timeout=5), 75)
                self.assertIn('memory' if case == 'bad-memfree' else 'power', watcher.stderr.read())
                self.assertFalse((root / 'scope-started').exists())

    def test_unbounded_command_is_refused_before_scope_starts(self):
        watcher = self.start_watcher('unbounded')
        self.assertEqual(watcher.wait(timeout=5), 2)
        self.assertIn('unbounded bench workload command', watcher.stderr.read())
        self.assertFalse((self.root / 'scope-started').exists())
        self.assertFalse((self.root / 'store/test-disk').exists())

    def test_writer_is_stopped_at_polled_peak_within_margin(self):
        watcher = self.start_watcher('disk')
        self.assertEqual(watcher.wait(timeout=5), 1, watcher.stderr.read())
        self.assertIn('evidence reached its phase peak', (self.root / 'graceful').read_text())
        allocated = int((self.root / 'allocated-at-stop').read_text())
        self.assertGreaterEqual(allocated, 256 * 1024)
        self.assertLess(allocated, 256 * 1024 + MIB)
        self.assertFalse(list((self.root / 'tree/.work/bench').glob('*/growing')))
        self.assertFalse(list((self.root / 'tree/.work/bench').glob('*/.growing.partial')))

    def test_fixed_disk_and_undeclared_writes_are_kernel_bounded(self):
        watcher = self.start_watcher('fixed')
        self.assertEqual(watcher.wait(timeout=5), 0, watcher.stderr.read())
        output, = (self.root / 'tree/.work/bench').glob('*/fixed')
        self.assertEqual(output.stat().st_size, 65536)
        self.assertTrue(output.read_bytes().startswith(b'fixture'))
        self.assertFalse((self.root / 'outside').exists())

    def test_watcher_sigkill_recovers_staged_command_evidence_only(self):
        watcher = self.start_watcher('interrupted-evidence')
        run = self.root / 'tree/.work/bench'
        deadline = time.monotonic() + 5
        while not (staged := list(run.glob('*/.command-log.partial'))):
            self.assertIsNone(watcher.poll())
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        partial, = staged
        self.assertEqual(self.wait_result(partial, watcher), 'started')
        handles = self.handles(watcher)
        self.assertFalse((partial.parent / 'command-log').exists())
        watcher.kill()
        self.assertEqual(watcher.wait(timeout=5), -signal.SIGKILL)
        for fd in handles.values():
            self.assertTrue(select.select([fd], [], [], 5)[0], 'stand-in survived watcher loss')
        self.assertTrue(partial.exists())
        store = Store(*roots(self.root), disk_space=mock_space, mount=mock_mount)
        store.expire()
        self.assertEqual((partial.parent / 'finished').read_bytes(), b'finished')
        self.assertFalse(partial.exists())
        self.assertFalse((partial.parent / 'command-log').exists())

    def test_scope_identity_must_match_invocation_and_launcher_membership(self):
        inputs = fixture(self.root)
        scopes = UserScopes(inputs)
        unit = 'aresos-bench-fixture.scope'
        group = scopes.slice / unit
        path = inputs.cgroups / group.relative_to('/')
        path.mkdir(parents=True)
        (path / 'cgroup.kill').write_text('')
        (path / 'cgroup.events').write_text('populated 1\n')
        (path / 'cgroup.procs').write_text('42\n')
        proc_group = inputs.proc / '42/cgroup'
        proc_group.parent.mkdir()
        proc_group.write_text(f'0::{group}\n')
        properties = {'Id': unit, 'InvocationID': INVOCATION, 'ControlGroup': str(group), 'ActiveState': 'active'}
        with ExitStack() as stack, patch.object(scopes, 'properties', return_value=properties):
            with self.assertRaisesRegex(ValueError, 'scope invocation'):
                scopes.pin(unit, 42, 'b' * 32, stack)
            (path / 'cgroup.procs').write_text('43\n')
            with self.assertRaisesRegex(ValueError, 'ownership changed'):
                scopes.pin(unit, 42, INVOCATION, stack)
            self.assertEqual((path / 'cgroup.kill').read_text(), '')
            (path / 'cgroup.procs').write_text('42\n')
            scope = scopes.pin(unit, 42, INVOCATION, stack)
            (path / 'cgroup.events').unlink()
            (path / 'cgroup.events').write_text('populated 0\n')
            self.assertFalse(scope.empty(), 'replacement path is not proof of emptiness')

    def test_failed_kill_waits_for_confirmed_empty_with_closed_stderr(self):
        with ExitStack() as stack:
            group = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            stack.callback(os.close, group)
            events_path = self.root / 'events'
            events_path.write_text('populated 1\n')
            events = os.open(events_path, os.O_RDONLY)
            stack.callback(os.close, events)
            scope = OwnedScope(INVOCATION, group, events, -1)

            retries = []

            def recover(delay):
                self.assertFalse(scope.empty())
                retries.append(delay)
                if len(retries) == 2:
                    events_path.write_text('populated 0\n')

            closed_stderr = io.StringIO()
            closed_stderr.close()
            with patch('laptop.sleep', side_effect=recover), patch('laptop.sys.stderr', closed_stderr):
                self.assertFalse(scope.stop())
                self.assertTrue(scope.empty())
            self.assertEqual(retries, [1, 1])

    def test_rechecks_gates_after_phase_setup_before_launch(self):
        watcher = self.start_watcher('recheck')
        self.assertEqual(watcher.wait(timeout=5), 75)
        self.assertIn('needs 7 GiB', watcher.stderr.read())
        self.assertFalse((self.root / 'store/test-disk/worker-ready').exists())
        self.assertFalse((self.root / 'store/test-disk').exists())

    def test_signal_during_scope_stop_preserves_disk_until_stop_finishes(self):
        (self.root / 'hold-stop').touch()
        watcher = self.start_watcher('watch')
        self.wait_result(self.root / 'store/test-disk/worker-ready', watcher)
        replace_text(self.root / 'meminfo', 'MemTotal: 16384000 kB\nMemFree: 1 kB\nMemAvailable: 1 kB\n')
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
    with socket.socket(fileno=int(sys.argv[3])) as handles:
        descendants, sender = socket.socketpair(type=socket.SOCK_SEQPACKET)
        with descendants, sender:
            sys.exit(run_watcher(Path(sys.argv[1]), sys.argv[2], handles, descendants, sender))
