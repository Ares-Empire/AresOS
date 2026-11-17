"""Tests for measurement validity and scope isolation, without touching any live cgroup."""
import importlib.util, pathlib, subprocess, sys, tempfile, unittest
from unittest.mock import patch
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import scope
import snap
from snap import smaps_classes


def setUpModule():
    (ROOT / '../../../.work/pkg49').resolve().mkdir(parents=True, exist_ok=True)


class ScopeTest(unittest.TestCase):
    def test_unrelated_unit_refused_before_any_read(self):
        for unit in ('user.slice', 'app-owner.scope', 'pkg49-game-example.scope', '../memory.reclaim'):
            with self.subTest(unit=unit), patch.object(pathlib.Path, 'read_text', side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError): scope.owned_scope(123, unit)

    def test_pid_in_ancestor_or_different_scope_refused(self):
        unit = 'pkg49-game-example-42.scope'
        for actual in ('/user.slice', '/user.slice/pkg49-game-other-9.scope'):
            with self.subTest(actual=actual), patch.object(pathlib.Path, 'read_text', return_value='0::'+actual+'\n'), \
                    patch.object(subprocess, 'check_output', return_value='/user.slice/'+unit+'\n'):
                with self.assertRaises(ValueError): scope.owned_scope(123, unit)

    def test_exact_owned_scope_with_membership(self):
        unit = 'pkg49-game-example-42.scope'
        group = '/user.slice/'+unit
        def read(path): return '0::'+group+'\n' if str(path).startswith('/proc/') else '123\n'
        with patch.object(pathlib.Path, 'read_text', read), patch.object(subprocess, 'check_output', return_value=group+'\n'):
            self.assertEqual(scope.owned_scope(123, unit), pathlib.Path('/sys/fs/cgroup'+group))


class SmapsTest(unittest.TestCase):
    def test_mapping_totals_and_unattributed_anonymous(self):
        data = '''1000-2000 rw-p 00000000 00:00 0
Rss: 100 kB
Anonymous: 100 kB
2000-3000 rw-p 00000000 00:00 0 [heap]
Rss: 20 kB
3000-4000 rw-s 00000000 00:01 1 /dev/nvidiactl
Rss: 30 kB
4000-5000 r-xp 00000000 00:01 1 /lib/libjemalloc.so
Rss: 40 kB
5000-6000 rw-p 00000000 00:00 0
Rss: 50 kB
'''
        result = smaps_classes(data, (0x1000, 0x2000))
        self.assertEqual({k: v['Rss_kib'] for k,v in result.items()}, {'java-heap':100, 'glibc-brk':20,
                         'nvidiactl':30, 'jemalloc-library':40, 'anonymous-unattributed':50})


class FrozenSnapshotTest(unittest.TestCase):
    def test_frozen_snapshot_never_attaches_jcmd(self):
        import json
        fixture={'status_mib':{'VmRSS':100},'cgroup_mib':{'current':100,'swap':2},'majflt':3}
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49') as directory, \
                patch.dict('os.environ', {'PKG49_FROZEN':'1','PKG49_PROBE':'1'}), \
                patch.object(snap,'memory',return_value=fixture), \
                patch.object(snap,'jcmd',side_effect=AssertionError('must not attach to a frozen game')), \
                patch.object(pathlib.Path,'read_text',return_value=''), \
                patch.object(subprocess,'run',side_effect=OSError('optional GPU unavailable')):
            snap.snapshot(123,'frozen',directory)
            # Use a real file read, rather than the mocked Path.read_text.
            with open(pathlib.Path(directory)/'snap-frozen.json') as source: result=json.load(source)
            self.assertTrue(result['frozen'])
            self.assertEqual(result['nmt_committed_mib'],{})


class WakeTest(unittest.TestCase):
    def test_frozen_gap_clipped_at_wake_and_33ms_is_exact(self):
        # An unthawed 5 minute gap must not be charged to wake latency.
        import json
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49') as directory:
            rig=pathlib.Path(directory); out=rig/'out'
            (rig/'settings.txt').write_text('name=fixture\n')
            (rig/'marks.txt').write_text('joined 1000000000\nwake_start 301000000000\nwake_end 311000000000\ndone 311000000000\n')
            (rig/'frames.txt').write_text('1000000000\n301100000000\n301133200000\n301150000000\n')
            subprocess.run([sys.executable, '-I', str(ROOT/'analyze.py'), str(rig), str(out)], check=True, capture_output=True)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['wake_first_frame_ms'],100)
            self.assertEqual(summary['windows']['wake']['max_ms'],100)
            self.assertEqual(summary['windows']['wake']['over_33ms'],2)


if __name__ == '__main__': unittest.main()
