import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_bench_laptop_gates import ROOT, fixture, mock_mount
from laptop import Busy, Cancelled
from laptop_cli import Bench, main
from store import CAP, GB, IDLE, OTHER_EVIDENCE, RESERVE, Store, space
from store_paths import MARKER

MIB = 1024 * 1024


def roots(root):
    return root / 'store', root / 'tree', root / 'locks/client-test.lock'


def mock_space(path):
    return 1, 80 * GB, 4096


def write_interrupted_phase(root):
    store = Store(*roots(root), disk_space=mock_space, mount=mock_mount)
    with store.phase({'test-disk': MIB, 'export': MIB, 'evidence': MIB}) as phase:
        for kind in ('test-disk', 'export', 'evidence'):
            file = phase.write(kind, 'partial', b'fixture')
        (file.parent / '.unfinished.partial').write_bytes(b'fixture')
        (root / 'ready').touch()
        signal.pause()


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix='.bench-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(*roots(self.root), clock=lambda: 2 * IDLE, disk_space=mock_space, mount=mock_mount)
        self.store.worktree.mkdir()

    def test_phase_peak_is_checked_before_output_on_each_filesystem(self):
        def filesystems(path):
            return (2, RESERVE + GB, 4096) if path.is_relative_to(self.store.worktree) else (1, 100 * GB, 4096)

        store = Store(*roots(self.root), disk_space=filesystems, mount=mock_mount)
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
        self.store.cap = OTHER_EVIDENCE + 2 * MIB
        with self.assertRaisesRegex(Busy, '40 GB'):
            with self.store.phase({'evidence': MIB}):
                self.fail('existing files must count')
        self.assertEqual(CAP, 40_000_000_000)

    def test_subvolumes_with_distinct_devices_share_one_reserve(self):
        self.store.disk_space = space
        statvfs = SimpleNamespace(f_fsid=1234, f_bavail=(RESERVE + 2 * MIB) // 4096, f_frsize=4096)
        with patch('store.os.statvfs', return_value=statvfs), patch.object(
                Path, 'stat', autospec=True,
                side_effect=lambda path: SimpleNamespace(st_dev=2 if path == self.store.worktree else 1)):
            with self.assertRaisesRegex(Busy, '20 GB'):
                self.store.admit([(self.root, MIB), (self.store.worktree, MIB)])
            self.assertEqual(space(self.store.worktree)[0], 1234)

    def test_other_worktrees_evidence_allowance_is_charged_without_scanning(self):
        with self.store.phase({'base-disk': MIB}):
            pass
        with patch.object(self.store.data, 'allocated', return_value=35 * GB):
            self.store.admit([(self.store.root, 2 * GB)])
            with self.assertRaisesRegex(Busy, '40 GB'):
                self.store.admit([(self.store.root, 4_900_000_000)])

    def test_sparse_allocation_and_writer_preflight(self):
        with self.store.phase({'base-disk': MIB}) as phase:
            disk = phase.write('base-disk', 'disk', b'fixture', offset=2 * GB)
            self.assertGreater(disk.stat().st_size, 2 * GB)
            self.assertEqual(self.store.data.allocated(disk.relative_to(self.store.root)),
                             disk.stat().st_blocks * 512)
            self.assertLess(sum(self.store.usage().values()), MIB)
            with self.assertRaisesRegex(Busy, 'phase peak'):
                phase.write('base-disk', 'too-large', b'a' * MIB)
            self.assertFalse((disk.parent / 'too-large').exists())
            with self.assertRaises(ValueError):
                phase.write('base-disk', '../outside', b'fixture')
        with self.assertRaisesRegex(ValueError, 'phase has ended'):
            phase.write('base-disk', 'late-write', b'fixture')
        self.assertFalse((disk.parent / 'late-write').exists())

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
                    runs = list((self.store.worktree / '.work/bench').glob('*/partial'))
                    self.assertEqual(len(runs), 1)
                    self.assertEqual(runs[0].read_bytes(), b'fixture')
                    self.assertFalse(list(runs[0].parent.glob('.*.partial')))
            else:
                self.store.clean()
                self.assertFalse(self.store.root.exists())
                self.assertFalse((self.store.worktree / '.work/bench').exists())
            ready.unlink()

    def test_retained_evidence_is_counted_pruned_and_cleaned_in_current_worktree(self):
        other = self.root / 'other'
        other.mkdir()
        stores = [self.store, Store(self.store.root, other, self.store.lock, disk_space=mock_space, mount=mock_mount)]
        with stores[1].phase({'evidence': MIB}) as phase:
            other_file = phase.write('evidence', 'results.txt', b'other fixture')
        evidence = []
        for index in range(6):
            with stores[0].phase({'evidence': MIB}) as phase:
                path = phase.write('evidence', 'results.txt', b'fixture')
                os.utime(path.parent, (index + 1, index + 1))
                evidence.append(path)
        self.assertFalse(evidence[0].exists())
        self.assertTrue(all(path.exists() for path in evidence[1:]))
        total = sum(self.store.usage().values())
        self.assertGreater(total, self.store.data.allocated())
        out = io.StringIO()
        self.assertEqual(main(['status'], bench=Bench(fixture(self.root), self.store), output=out), 0)
        self.assertIn(f'{total:,} /', out.getvalue())
        self.assertIn('kept evidence', out.getvalue())
        self.store.clean()
        self.assertFalse(any(path.exists() for path in evidence))
        self.assertTrue(self.store.lock.exists())
        self.assertEqual(other_file.read_bytes(), b'other fixture')

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


    def test_clean_refuses_unmarked_store_and_evidence(self):
        for tree in (self.store.data, self.store.evidence):
            with self.subTest(path=tree.path.name):
                tree.path.mkdir(parents=True)
                keeper = tree.path / 'keep'
                keeper.touch()
                with self.assertRaisesRegex(ValueError, 'ownership marker'):
                    self.store.clean()
                self.assertTrue(keeper.is_file())
                keeper.unlink()
                tree.path.rmdir()

    def test_recovery_rejects_planted_paths_and_ignores_legacy_registry(self):
        outside = self.root / 'outside'
        outside.mkdir()
        keeper = outside / 'keep'
        keeper.touch()
        with self.store.phase({'builder-boot': MIB}):
            pass
        registry = self.store.root / 'worktree-fake.json'
        registry.write_text(json.dumps(str(outside)))
        for record in ({'writes': [str(outside)]}, {'writes': ['../outside']},
                       {'writes': ['export'], 'worktree': str(outside)}):
            self.store.active.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'phase record'):
                self.store.expire()
            self.assertTrue(keeper.is_file())
        self.store.clean()
        self.assertTrue(keeper.is_file())
        self.assertFalse(registry.exists())

    def test_cleanup_unlinks_leaf_symlinks_without_following_them(self):
        outside = self.root / 'outside'
        outside.mkdir()
        keeper = outside / 'keep'
        keeper.touch()
        with self.store.phase({'builder-boot': MIB}) as phase:
            phase.destination('builder-boot', 'link').symlink_to(outside, target_is_directory=True)
        self.store.clean()
        self.assertTrue(keeper.is_file())

    def test_cleanup_refuses_same_device_mount_at_root_or_below(self):
        with self.store.phase({'builder-boot': MIB}) as phase:
            keep = phase.write('builder-boot', 'keep', b'fixture')
        with self.store.phase({'evidence': MIB}) as phase:
            evidence = phase.write('evidence', 'keep', b'fixture')
        store = self.store.root
        mounted = set()

        def fake_mountinfo(fd):
            # Model distinct mount IDs for a same-device bind mount.
            return 2 if os.fstat(fd).st_ino in mounted else 1

        checked = Store(*roots(self.root), disk_space=mock_space, mount=fake_mountinfo)
        for path in (store, keep.parent, keep, self.store.worktree / '.work'):
            with self.subTest(path=path.name):
                self.assertEqual(path.stat().st_dev, store.parent.stat().st_dev)
                mounted.clear()
                mounted.add(path.stat().st_ino)
                with self.assertRaisesRegex(ValueError, 'mount'):
                    checked.clean()
                self.assertTrue(keep.is_file())
                self.assertTrue((store / MARKER).is_file())
                self.assertTrue(evidence.is_file())


if __name__ == '__main__':
    write_interrupted_phase(Path(sys.argv[1]))
