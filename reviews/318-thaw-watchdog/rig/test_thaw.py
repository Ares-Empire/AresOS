"""Package 318's offline tests: realtime-thread parsing, the Tgid check, the reset-on-fork demotion, the INVALID check,
the thaw sampler and exit watcher, and the run records. No game, no rtkit, no cgroup write.

The only policy changes are on stand-in processes this test starts itself, which set SCHED_OTHER|SCHED_RESET_ON_FORK
on themselves (an unprivileged process may set the flag; only clearing it needs CAP_SYS_NICE). No realtime policy is
ever asked for: this account shares rtkit's per-user limits with the owner's session.
"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import records
import rt

WORK = HERE.parents[2] / '.work/pkg318'
CHRT = '/usr/bin/chrt'

# A stand-in with a second thread that flags itself reset-on-fork, as rtkit's grant leaves a mixer thread, and can
# spin on request (one line on stdin) without blocking, as a catching-up mixer would.
STAND_IN = r'''
import os, sys, threading, time
go = threading.Event()
def worker():
    os.sched_setscheduler(0, os.SCHED_OTHER | os.SCHED_RESET_ON_FORK, os.sched_param(0))
    print(threading.get_native_id(), flush=True)
    go.wait()
    end = time.monotonic() + 0.5
    while time.monotonic() < end: pass
    time.sleep(60)
threading.Thread(target=worker, daemon=True).start()
sys.stdin.readline()
go.set()
time.sleep(60)
'''


def stat_line(tid, comm, policy, priority=0, state='S'):
    rest = [state] + ['0'] * 49  # proc(5) fields 3..52
    rest[37], rest[38] = str(priority), str(policy)
    return f'{tid} ({comm}) ' + ' '.join(rest) + '\n'


def fake_proc(root, pid, threads):
    for tid, comm, policy, priority in threads:
        task = root / str(pid) / 'task' / str(tid)
        task.mkdir(parents=True)
        (task / 'stat').write_text(stat_line(tid, comm, policy, priority))
        (root / str(tid)).mkdir(exist_ok=True)
        (root / str(tid) / 'status').write_text(f'Name:\t{comm}\nTgid:\t{pid}\nPid:\t{tid}\n')


class StandIn:
    """A stand-in process (optionally launched flagged reset-on-fork by chrt) and its flagged worker thread."""

    def __init__(self, chrt_flagged=False):
        command = [sys.executable, '-I', '-c', STAND_IN]
        if chrt_flagged:
            command = [CHRT, '--other', '--reset-on-fork', '0', *command]
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.pid = self.proc.pid
        self.worker = int(self.proc.stdout.readline())

    def spin(self):
        self.proc.stdin.write('go\n'); self.proc.stdin.flush()

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(5)
        self.proc.stdin.close(); self.proc.stdout.close()


class ParseTest(unittest.TestCase):
    def test_comm_with_spaces_and_parentheses(self):
        parsed = rt.parse_stat(stat_line(7, 'a (b) c)', 2, 1, 'R'))
        self.assertEqual(parsed, {'comm': 'a (b) c)', 'state': 'R', 'rt_priority': 1, 'policy': 2})

    def test_realtime_threads_found_with_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            fake_proc(root, 100, [(100, 'java', 0, 0), (101, 'alsoft-mixer', 2, 1), (102, 'fifo one', 1, 5),
                                  (103, 'batch', 3, 0), (104, 'idle', 5, 0)])
            flags = {101: 2 | rt.RESET_ON_FORK, 102: 1}
            found = rt.realtime(100, root, getscheduler=lambda tid: flags[tid])
        self.assertEqual(found, [
            {'tid': 101, 'comm': 'alsoft-mixer', 'policy': 'SCHED_RR', 'priority': 1, 'flags': ['SCHED_RESET_ON_FORK']},
            {'tid': 102, 'comm': 'fifo one', 'policy': 'SCHED_FIFO', 'priority': 5, 'flags': []}])

    def test_real_process_has_no_realtime_thread(self):
        self.assertEqual(rt.realtime(os.getpid()), [])
        self.assertGreaterEqual(len(rt.threads(os.getpid())), 1)


class TgidTest(unittest.TestCase):
    def test_thread_of_another_process_is_refused_before_any_command(self):
        game, other = StandIn(), StandIn()
        try:
            def never(*_, **__): raise AssertionError('no policy command for a foreign thread')
            with self.assertRaises(PermissionError):
                rt.demote(game.pid, other.worker, run=never)
            with self.assertRaises(PermissionError):
                rt.demote(game.pid, other.pid, run=never)
            self.assertEqual(rt.tgid(game.worker), game.pid)
        finally:
            game.close(); other.close()

    def test_fake_tree_tgid_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            fake_proc(root, 200, [(201, 'x', 2, 1)])
            with self.assertRaises(PermissionError):
                rt.demote(100, 201, proc=root, run=None)


class DemoteTest(unittest.TestCase):
    def check_thread(self, stand_in, tid):
        self.assertTrue(os.sched_getscheduler(tid) & rt.RESET_ON_FORK, 'stand-in thread lacks the flag')
        plain = subprocess.run([CHRT, '--other', '--pid', '0', str(tid)], capture_output=True, text=True)
        self.assertNotEqual(plain.returncode, 0)
        self.assertIn('Operation not permitted', plain.stderr)
        self.assertTrue(os.sched_getscheduler(tid) & rt.RESET_ON_FORK, 'plain chrt changed the thread')
        result = rt.demote(stand_in.pid, tid)
        self.assertEqual(result['exit'], 0, result)
        self.assertEqual((result['after'], result['after_reset_on_fork']), ('SCHED_OTHER', True))
        self.assertEqual(result['command'], f'{CHRT} --reset-on-fork --other --pid 0 {tid}')
        return plain.stderr.strip(), result

    def test_plain_chrt_refused_and_rig_command_works(self):
        stand_in = StandIn(chrt_flagged=True)
        try:
            # The worker thread flagged itself; the main thread was started flagged by chrt.
            self.worker = self.check_thread(stand_in, stand_in.worker)
            self.main = self.check_thread(stand_in, stand_in.pid)
            print(f'\n  plain chrt: {self.worker[0]}\n  rig: {self.worker[1]}', file=sys.stderr)
        finally:
            stand_in.close()


class CheckTest(unittest.TestCase):
    """rt.py check, the INVALID gate: a realtime thread left at the thaw fails a demote run, never a keep run."""

    def run_check(self, mode, left):
        with tempfile.TemporaryDirectory(dir=WORK) as directory, \
                patch('scope.owned_scope', return_value=pathlib.Path(directory)), \
                patch.object(rt, 'frozen', return_value=True), patch.object(rt, 'realtime', return_value=left):
            code = rt.main(['check', '123', 'pkg318-game-x-1.scope', directory, mode])
            return code, json.loads((pathlib.Path(directory) / 'rt-prethaw.json').read_text())

    def test_demote_with_thread_left_is_invalid(self):
        left = [{'tid': 5, 'comm': 'alsoft-mixer', 'policy': 'SCHED_RR', 'priority': 1, 'flags': []}]
        code, record = self.run_check('demote', left)
        self.assertEqual((code, record['invalid']), (rt.INVALID, True))
        self.assertEqual(self.run_check('demote', [])[0], 0)
        code, record = self.run_check('keep', left)
        self.assertEqual((code, record['invalid']), (0, False))

    def test_record_and_demote_refuse_an_unfrozen_game(self):
        with tempfile.TemporaryDirectory(dir=WORK) as directory, \
                patch('scope.owned_scope', return_value=pathlib.Path(directory)), patch.object(rt, 'frozen', return_value=False):
            for command in ('record', 'demote'):
                with self.assertRaisesRegex(RuntimeError, 'only while'):
                    rt.main([command, '123', 'pkg318-game-x-1.scope', directory])

    def test_demote_command_uses_recorded_threads_only(self):
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            rig = pathlib.Path(directory)
            (rig / 'rt-freeze.json').write_text(json.dumps({'pid': 123, 'realtime': [{'tid': 124}]}))
            seen = []
            with patch('scope.owned_scope', return_value=rig), patch.object(rt, 'frozen', return_value=True), \
                    patch.object(rt, 'demote', side_effect=lambda pid, tid: seen.append((pid, tid)) or {'tid': tid}), \
                    patch.object(rt, 'realtime', return_value=[]):
                self.assertEqual(rt.main(['demote', '123', 'pkg318-game-x-1.scope', directory]), 0)
            self.assertEqual(seen, [(123, 124)])


def watcher(stand_in, rig, mode, hold=30.0, recorded=True):
    rig.mkdir(exist_ok=True)
    (rig / 'marks.txt').write_text(f'return_start {time.monotonic_ns()}\n')
    if recorded:
        (rig / 'rt-freeze.json').write_text(json.dumps({'pid': stand_in.pid, 'realtime': [{'tid': stand_in.worker}]}))
    with (rig / 'thaw.txt').open('w') as log:
        proc = subprocess.Popen([sys.executable, '-I', str(HERE / 'thaw.py'), str(stand_in.pid), str(rig), mode,
                                 '--hold', str(hold)], stdout=log, stderr=subprocess.STDOUT)
    deadline = time.monotonic() + 5
    while not (rig / 'thaw-ready').exists():
        assert time.monotonic() < deadline and proc.poll() is None, 'watcher never ready'
        time.sleep(.01)
    return proc


def samples(rig):
    lines = (rig / 'thaw-samples.csv').read_text().splitlines()
    head = lines[0].split(',')
    return [dict(zip(head, line.split(','))) for line in lines[1:]]


class WatcherTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=WORK)
        self.rig = pathlib.Path(self.directory.name)
        self.stand_in = StandIn()

    def tearDown(self):
        self.stand_in.close()
        self.directory.cleanup()

    def test_sigkill_during_sampling_stops_both_and_reads_the_zombie(self):
        proc = watcher(self.stand_in, self.rig, 'demote')
        time.sleep(.2)
        killed = time.monotonic()
        # Not reaped until the watcher is done: the zombie's wait status stays readable, as under Gradle.
        os.kill(self.stand_in.pid, signal.SIGKILL)
        proc.wait(timeout=5)
        stopped = time.monotonic() - killed
        self.assertLess(stopped, 1.5, 'the watcher ran on after the exit (10 s demote window)')
        record = json.loads((self.rig / 'exit.json').read_text())
        self.assertEqual((record['outcome'], record['source'], record['signal']), ('exited', 'zombie', 9))
        self.assertIs(record['cleanup_started_before_exit'], False)
        rows = samples(self.rig)
        self.assertGreater(len(rows), 5)
        self.assertEqual({r['tid'] for r in rows}, {str(self.stand_in.worker)})
        self.assertTrue(all(r['cpu_ns'].isdigit() and r['voluntary'].isdigit() for r in rows))
        self.assertLess(int(rows[-1]['monotonic_ns']), record['exit_detected_ns'] + 1)
        self.assertTrue((self.rig / 'thaw-sampled').exists())

    def test_exit_after_cleanup_start_is_marked(self):
        proc = watcher(self.stand_in, self.rig, 'keep')
        with (self.rig / 'marks.txt').open('a') as marks:
            marks.write(f'cleanup_start {time.monotonic_ns()}\n')
        self.stand_in.proc.terminate()
        proc.wait(timeout=5)
        record = json.loads((self.rig / 'exit.json').read_text())
        self.assertEqual((record['outcome'], record['signal']), ('exited', signal.SIGTERM))
        self.assertIs(record['cleanup_started_before_exit'], True)

    def test_survivor_sampled_for_the_window_then_alive_at_the_hold(self):
        proc = watcher(self.stand_in, self.rig, 'keep', hold=3.5)
        time.sleep(.3)
        self.stand_in.spin()  # 500 ms on the CPU without blocking
        proc.wait(timeout=10)
        record = json.loads((self.rig / 'exit.json').read_text())
        self.assertEqual(record['outcome'], 'alive')
        self.assertGreaterEqual(record['after_return_ms'], 3500)
        rows = samples(self.rig)
        span = (int(rows[-1]['monotonic_ns']) - int(rows[0]['monotonic_ns'])) / 1e9
        self.assertTrue(2.8 < span < 3.1, span)
        self.assertGreater(len(rows), 150)  # about 300 at 10 ms; tolerant of a loaded laptop
        scans = (self.rig / 'thaw-scan.jsonl').read_text().splitlines()
        self.assertTrue(20 <= len(scans) <= 31, len(scans))
        # The verdict's measure: CPU time gained while the voluntary switch count stays unchanged.
        longest = run = 0
        for before, after in zip(rows, rows[1:]):
            if after['voluntary'] == before['voluntary']:
                run += int(after['cpu_ns']) - int(before['cpu_ns'])
                longest = max(longest, run)
            else:
                run = 0
        self.assertGreater(longest, 150_000_000, longest)

    def test_sigterm_records_stopped(self):
        proc = watcher(self.stand_in, self.rig, 'demote', recorded=False)
        proc.terminate()
        proc.wait(timeout=5)
        self.assertEqual(json.loads((self.rig / 'exit.json').read_text())['outcome'], 'stopped')


class RecordsTest(unittest.TestCase):
    def test_rtkit_lines_kept_for_the_game_or_no_process(self):
        self.assertTrue(records.keep_rtkit('rtkit-daemon[1]: Successfully made thread 7 of process 42 (java) RT', 42))
        self.assertFalse(records.keep_rtkit('rtkit-daemon[1]: Successfully made thread 9 of process 77 (x) RT', 42))
        self.assertTrue(records.keep_rtkit('rtkit-daemon[1]: Demoting known real-time threads.', 42))

    def test_final_records_fallback_and_public_copy(self):
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            rig = pathlib.Path(directory) / 'rig'; out = pathlib.Path(directory) / 'out'; rig.mkdir()
            (rig / 'settings.txt').write_text('name=x\nstarted=2026-11-20T10:00:00+01:00\nGAME_PID=42\n')
            (rig / 'exit.json').write_text(json.dumps({'outcome': 'exited', 'signal': None, 'source': None}))
            (rig / 'gradle.txt').write_text(f"Process 'command '{records.HOME}/jdk/bin/java'' finished with non-zero exit value 137\n")
            (rig / 'game.txt').write_text('[Render thread/INFO]: OpenAL initialized on device Null Output\nother\n')
            (rig / 'marks.txt').write_text(f'path {records.WORKTREE}/x\n')
            calls = []

            def run(command, **_):
                calls.append(command)
                if command[0] == 'cardwire':
                    return subprocess.CompletedProcess(command, 1, '', 'needs root\n')
                if '-k' in command:
                    return subprocess.CompletedProcess(command, 0, 'k: NVRM: GPU at PCI:0000:01:00\nk: usb thing\n', '')
                return subprocess.CompletedProcess(command, 0, 'a rtkit-daemon[1]: Successfully made thread 9 of process 77 (x)\n'
                                                   'b rtkit-daemon[1]: Successfully made thread 43 of process 42 (java)\n'
                                                   'c cardwired[2]: D0\n', '')
            records.final(rig, out, run=run)
            self.assertTrue(all('--no-hostname' in c for c in calls if c[0] == 'journalctl'))
            journal = (rig / 'journal.txt').read_text()
            self.assertIn('of process 42', journal); self.assertNotIn('of process 77', journal)
            self.assertIn('cardwired', journal); self.assertIn('NVRM', journal); self.assertNotIn('usb', journal)
            self.assertIn('needs root', (rig / 'cardwire.txt').read_text())
            self.assertIn('OpenAL', (rig / 'sound-lines.txt').read_text())
            record = json.loads((out / 'exit.json').read_text())
            self.assertEqual((record['signal'], record['signal_source'], record['gradle_exit_value']), (9, 'gradle exit value', 137))
            for path in out.iterdir():
                text = path.read_text()
                self.assertNotIn(records.HOME + '/', text, path.name)
            self.assertIn('<worktree>/x', (out / 'marks.txt').read_text())

    def test_runtime_status_needs_a_pci_address(self):
        self.assertIsNone(records.runtime_status({'PKG318_GPU_PCI': '../../etc'}))
        self.assertIsNone(records.runtime_status({}))


if __name__ == '__main__':
    WORK.mkdir(parents=True, exist_ok=True)
    unittest.main(verbosity=2)
