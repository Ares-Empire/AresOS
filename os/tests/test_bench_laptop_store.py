import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from test_bench_laptop_gates import ROOT, fixture
from laptop import Busy, Cancelled
from laptop_cli import Bench, main
from store import CAP, GB, IDLE, RESERVE, Store, allocated

MIB = 1024 * 1024


def roots(root):
    return root / 'store', root / 'tree', root / 'locks/client-test.lock'


def mock_space(path):
    return path.stat().st_dev, 80 * GB, 4096


def write_interrupted_phase(root):
    store = Store(*roots(root), disk_space=mock_space)
    with store.phase({'test-disk': MIB, 'export': MIB, 'evidence': MIB}) as phase:
        for kind in ('test-disk', 'export', 'evidence'):
            phase.write(kind, 'partial', b'fixture')
        (root / 'ready').touch()
        signal.pause()


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix='.bench-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(*roots(self.root), clock=lambda: 2 * IDLE, disk_space=mock_space)
        self.store.worktree.mkdir()

    def test_phase_peak_is_checked_before_output_on_each_filesystem(self):
        def filesystems(path):
            return (2, RESERVE + GB, 4096) if path.is_relative_to(self.store.worktree) else (1, 100 * GB, 4096)

        store = Store(*roots(self.root), disk_space=filesystems)
        with self.assertRaisesRegex(Busy, '40 GB'):
            with store.phase({'build-store': 17 * GB, 'builder-scratch': 15 * GB, 'base-disk': 10 * GB}):
                self.fail('over-cap phase admitted')
        self.assertFalse(store.root.exists())

        def low_evidence_space(path):
            return (2, RESERVE, 4096) if path.is_relative_to(store.worktree) else (1, 100 * GB, 4096)

        store.disk_space = low_evidence_space
        with self.assertRaisesRegex(Busy, '20 GB'):
            with store.phase({'test-disk': MIB, 'evidence': MIB}):
                self.fail('filesystem reserve ignored')
        self.assertFalse(store.root.exists())
        self.assertFalse((store.worktree / '.work').exists())

        store.disk_space = filesystems
        with store.phase({'base-disk': MIB, 'evidence': MIB}) as phase:
            phase.write('base-disk', 'disk', b'fixture')
            phase.write('evidence', 'results.txt', b'PASS')
        self.assertEqual(set(store.usage()), {1, 2})

    def test_same_filesystem_peaks_are_combined_and_old_use_is_counted(self):
        def free(path):
            return 1, RESERVE + 3 * MIB - 1, 4096

        self.store.disk_space = free
        with self.assertRaisesRegex(Busy, '20 GB'):
            with self.store.phase({'test-disk': MIB, 'podman-tmp': MIB}):
                self.fail('coexisting writes must fit together')

        self.store.disk_space = lambda path: (1, 100 * GB, 4096)
        with self.store.phase({'base-disk': MIB}) as phase:
            path = phase.write('base-disk', 'disk', b'x' * 128 * 1024)
        self.assertTrue(path.exists())
        self.store.cap = 2 * MIB
        with self.assertRaisesRegex(Busy, '40 GB'):
            with self.store.phase({'evidence': MIB}):
                self.fail('existing files must count')
        self.assertEqual(CAP, 40_000_000_000)

    def test_sparse_allocation_and_writer_preflight(self):
        with self.store.phase({'base-disk': MIB}) as phase:
            disk = phase.write('base-disk', 'disk', b'fixture', offset=2 * GB)
            self.assertGreater(disk.stat().st_size, 2 * GB)
            self.assertEqual(allocated(disk), disk.stat().st_blocks * 512)
            self.assertLess(sum(self.store.usage().values()), MIB)
            with self.assertRaisesRegex(Busy, 'phase peak'):
                phase.write('base-disk', 'too-large', b'a' * MIB)
            self.assertFalse((disk.parent / 'too-large').exists())
            with self.assertRaises(ValueError):
                phase.write('base-disk', '../outside', b'fixture')

    def test_replacement_scratch_and_expiry(self):
        with self.store.phase({'image': MIB, 'base-disk': MIB, 'build-store': MIB}) as phase:
            first = phase.write('image', 'old-image', b'old')
            disk = phase.write('base-disk', 'old-disk', b'old')
            build = phase.write('build-store', 'cache', b'fixture')
        with self.store.phase({'image': MIB, 'base-disk': MIB, 'builder-scratch': MIB,
                               'export': MIB, 'podman-tmp': MIB}) as phase:
            self.assertFalse(first.exists())
            self.assertFalse(disk.exists())
            newest = phase.write('base-disk', 'new-disk', b'new')
            scratch = [phase.write(kind, 'fixture', b'fixture')
                       for kind in ('builder-scratch', 'export', 'podman-tmp')]
        self.assertTrue(newest.exists())
        self.assertTrue(all(not path.exists() for path in scratch))
        os.utime(build.parent, (IDLE + 1, IDLE + 1))
        self.store.expire()
        self.assertTrue(build.exists())
        os.utime(build.parent, (IDLE, IDLE))
        self.store.expire()
        self.assertFalse(build.exists())
        self.assertTrue(newest.exists())

    def test_signal_and_exception_delete_test_disk_but_keep_finished_evidence(self):
        for interrupt in (False, True):
            expected = Cancelled if interrupt else RuntimeError
            with self.subTest(interrupt=interrupt), self.assertRaises(expected):
                with self.store.phase({'test-disk': MIB, 'evidence': MIB}) as phase:
                    disk = phase.write('test-disk', 'overlay', b'fixture')
                    evidence = phase.write('evidence', 'results.txt', b'FAIL')
                    if interrupt:
                        signal.raise_signal(signal.SIGTERM)
                    raise RuntimeError('test failed')
            self.assertFalse(disk.exists())
            self.assertTrue(evidence.exists())
            self.assertFalse(self.store.active.exists())

    def test_write_rechecks_free_space_without_creating_a_partial_file(self):
        available = 100 * GB

        def free(path):
            return 1, available, 4096

        self.store.disk_space = free
        with self.store.phase({'test-disk': MIB}) as phase:
            available = RESERVE
            with self.assertRaisesRegex(Busy, '20 GB'):
                phase.write('test-disk', 'overlay', b'fixture')
            self.assertEqual(list((self.store.root / 'test-disk').iterdir()), [])

    def test_shared_lock_refuses_phase_expiry_and_clean_during_active_store(self):
        with self.store.phase({'test-disk': MIB}) as phase:
            path = phase.write('test-disk', 'fixture', b'fixture')
            for operation in (self.store.clean, self.store.expire):
                with self.assertRaisesRegex(Busy, 'lock is busy'):
                    operation()
            with self.assertRaisesRegex(Busy, 'lock is busy'):
                with self.store.phase({'test-disk': MIB}):
                    self.fail('concurrent write admitted')
            self.assertTrue(path.is_file())

    def test_next_phase_and_clean_recover_a_sigkilled_writer(self):
        for cleanup in ('next phase', 'clean'):
            ready = self.root / 'ready'
            with self.subTest(cleanup=cleanup), subprocess.Popen(
                    [sys.executable, '-B', __file__, str(self.root)], stdin=subprocess.DEVNULL) as child:
                try:
                    deadline = time.monotonic() + 5
                    while not ready.exists():
                        self.assertIsNone(child.poll())
                        self.assertLess(time.monotonic(), deadline)
                        time.sleep(0.02)
                    self.assertTrue(self.store.active.is_file())
                    self.assertTrue((self.store.root / 'test-disk/partial').is_file())
                    with self.assertRaises(Busy):
                        self.store.clean()
                finally:
                    child.kill()
                    child.wait(timeout=5)
                self.assertEqual(child.returncode, -signal.SIGKILL)
            if cleanup == 'next phase':
                with self.store.phase({'builder-scratch': MIB}):
                    self.assertFalse((self.store.root / 'test-disk').exists())
                    self.assertFalse((self.store.root / 'export').exists())
                    self.assertFalse(list((self.store.worktree / '.work/bench').iterdir()))
            else:
                self.store.clean()
                self.assertFalse(self.store.root.exists())
                self.assertFalse((self.store.worktree / '.work/bench').exists())
            ready.unlink()

    def test_retained_evidence_is_counted_pruned_and_cleaned_across_worktrees(self):
        other = self.root / 'other'
        other.mkdir()
        stores = [self.store, Store(self.store.root, other, self.store.lock, disk_space=mock_space)]
        evidence = []
        for index in range(6):
            with stores[index % 2].phase({'evidence': MIB}) as phase:
                path = phase.write('evidence', 'results.txt', b'fixture')
                os.utime(path.parent, (index + 1, index + 1))
                evidence.append(path)
        self.assertFalse(evidence[0].exists())
        self.assertTrue(all(path.exists() for path in evidence[1:]))
        total = sum(self.store.usage().values())
        self.assertGreater(total, allocated(self.store.root))
        out = io.StringIO()
        self.assertEqual(main(['status'], bench=Bench(fixture(self.root), self.store), output=out), 0)
        self.assertIn(f'{total:,} /', out.getvalue())
        self.assertIn('kept evidence', out.getvalue())
        self.store.clean()
        self.assertFalse(any(path.exists() for path in evidence))
        self.assertTrue(self.store.lock.exists())

    def test_clean_refuses_redirected_evidence_path(self):
        with self.store.phase({'evidence': MIB}) as phase:
            file = phase.write('evidence', 'results.txt', b'fixture')
        existing = file.parent.parent
        unrelated = self.root / 'unrelated'
        existing.rename(unrelated)
        existing.symlink_to(unrelated, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'redirected'):
            self.store.clean()
        self.assertTrue((unrelated / file.parent.name / file.name).is_file())


if __name__ == '__main__':
    write_interrupted_phase(Path(sys.argv[1]))
