"""Tests for measurement validity and scope isolation, without touching any live cgroup."""
import importlib.util, pathlib, subprocess, sys, tempfile, unittest
from unittest.mock import patch
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import scope
import snap
from snap import smaps_classes


def setUpModule():
    (ROOT / '../../../.work/pkg49b').resolve().mkdir(parents=True, exist_ok=True)


class ScopeTest(unittest.TestCase):
    def test_unrelated_unit_refused_before_any_read(self):
        for unit in ('user.slice', 'app-owner.scope', 'pkg49b-game-example.scope', '../memory.reclaim'):
            with self.subTest(unit=unit), patch.object(pathlib.Path, 'read_text', side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError): scope.owned_scope(123, unit)

    def test_pid_in_ancestor_or_different_scope_refused(self):
        unit = 'pkg49b-game-example-42.scope'
        for actual in ('/user.slice', '/user.slice/pkg49b-game-other-9.scope'):
            with self.subTest(actual=actual), patch.object(pathlib.Path, 'read_text', return_value='0::'+actual+'\n'), \
                    patch.object(subprocess, 'check_output', return_value='/user.slice/'+unit+'\n'):
                with self.assertRaises(ValueError): scope.owned_scope(123, unit)

    def test_exact_owned_scope_with_membership(self):
        unit = 'pkg49b-game-example-42.scope'
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
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory, \
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


class NmtOffTest(unittest.TestCase):
    def check_snapshot(self, output):
        import json
        fixture={'status_mib':{'VmRSS':100},'cgroup_mib':{'current':100,'swap':0},'majflt':0}
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory, \
                patch.dict('os.environ',{'PKG49_NMT':'0','PKG49_FROZEN':'0','PKG49_PROBE':'0'}), \
                patch.object(snap,'memory',return_value=fixture), \
                patch.object(snap,'jcmd',return_value={'exit':0,'stdout':'','stderr':''}), \
                patch.object(pathlib.Path,'read_text',return_value=''), \
                patch.object(subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,output,''),OSError('optional GPU')]):
            snap.snapshot(123,'nmt-off',directory)
            with open(pathlib.Path(directory)/'snap-nmt-off.json') as source: return json.load(source)

    def test_tracking_off_is_confirmed_by_jvm(self):
        result=self.check_snapshot('123:\nNative memory tracking is not enabled\n')
        self.assertTrue(result['nmt_disabled_confirmed'])
        self.assertEqual(result['nmt_committed_mib'],{})

    def test_silently_enabled_tracking_rejects_absolute_measurement(self):
        with self.assertRaisesRegex(RuntimeError,'did not confirm'):
            self.check_snapshot('Total: reserved=200MB, committed=100MB\n')


class WakeInputTest(unittest.TestCase):
    def test_dead_virtual_input_reader_fails_instead_of_holding_the_game_lock(self):
        import os, time
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory:
            rig=pathlib.Path(directory)
            (rig/'marks.txt').write_text(f'wake_start {time.monotonic_ns()}\n')
            os.mkfifo(rig/'vin')
            result=subprocess.run([sys.executable,'-I',str(ROOT/'wake.py'),str(rig)],capture_output=True,text=True,timeout=2)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('[Errno 6]',result.stderr)


    def test_reader_reopening_gap_and_multiple_commands(self):
        import os, threading, time
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory:
            rig=pathlib.Path(directory)
            (rig/'marks.txt').write_text(f'wake_start {time.monotonic_ns()-9_000_000_000}\n')
            os.mkfifo(rig/'vin')
            commands=[]
            def reader():
                time.sleep(.15)
                with (rig/'vin').open() as fifo: commands.extend(fifo.read().splitlines())
            worker=threading.Thread(target=reader,daemon=True);worker.start()
            result=subprocess.run([sys.executable,'-I',str(ROOT/'wake.py'),str(rig)],capture_output=True,text=True,timeout=2)
            worker.join(1)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(worker.is_alive())
            self.assertEqual(commands[:2],['key lctrl down','key lctrl up'])
            self.assertTrue(any(command.startswith('rel ') for command in commands))


class CreationTest(unittest.TestCase):
    def test_automatic_creation_uses_observed_time_and_rejects_wrong_home(self):
        import creation
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory:
            rig=pathlib.Path(directory)
            (rig/'marks.txt').write_text('game_detected 100\n')
            (rig/'creation-marks.txt').write_text('flat\t123456\n')
            creation.record(rig,'flat','automatic')
            self.assertIn('create_start 123456\n',(rig/'marks.txt').read_text())
            previous=(rig/'marks.txt').read_text()
            with self.assertRaises(ValueError): creation.record(rig,'nether','menu')
            self.assertEqual((rig/'marks.txt').read_text(),previous)

    def test_menu_keeps_confirmation_time_and_requires_it(self):
        import creation
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory:
            rig=pathlib.Path(directory)
            (rig/'marks.txt').write_text('game_detected 100\n')
            (rig/'creation-marks.txt').write_text('Nether\t456\n')
            with self.assertRaises(ValueError): creation.record(rig,'nether','menu')
            (rig/'marks.txt').write_text('game_detected 100\ncreate_start 123\n')
            creation.record(rig,'nether','menu')
            marks=dict(line.split() for line in (rig/'marks.txt').read_text().splitlines())
            self.assertEqual(marks['create_start'],'123')
            self.assertEqual(marks['world_create_start'],'456')


class UiTest(unittest.TestCase):
    def test_real_fifo_click_scales_observed_bounds_and_records_intent(self):
        import base64, os, threading, ui
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory:
            rig=pathlib.Path(directory); commands=[]
            (rig/'settings.txt').write_text('SIZE=1920x1080\n')
            label=base64.b64encode('New home…'.encode()).decode()
            (rig/'ui.txt').write_text(f'480\t270\tmenu\n{label}\t140\t127\t200\t20\ttrue\ttrue\n')
            os.mkfifo(rig/'vin')
            def reader():
                with (rig/'vin').open() as source: commands.extend(source.read().splitlines())
            worker=threading.Thread(target=reader,daemon=True);worker.start()
            ui.click(rig,'New home…',mark='create_start')
            worker.join(1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(commands,['move 960 548','click left'])
            self.assertTrue((rig/'marks.txt').read_text().startswith('create_start '))

    def test_inactive_or_ambiguous_buttons_never_send_input(self):
        import base64, ui
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory:
            rig=pathlib.Path(directory)
            (rig/'settings.txt').write_text('SIZE=1920x1080\n')
            label=base64.b64encode(b'Create').decode()
            line=f'{label}\t1\t2\t20\t20\ttrue\ttrue\n'
            (rig/'ui.txt').write_text('480\t270\tmenu\n'+line+line)
            with self.assertRaises(ValueError): ui.click(rig,'Create',timeout=0)
            (rig/'ui.txt').write_text('480\t270\tmenu\n'+line.replace('true\ttrue','false\ttrue'))
            with self.assertRaises(TimeoutError): ui.click(rig,'Create',timeout=0)


class WakeTest(unittest.TestCase):
    def test_frozen_gap_clipped_at_wake_and_33ms_is_exact(self):
        # An unthawed 5 minute gap must not be charged to wake latency.
        import json
        with tempfile.TemporaryDirectory(dir=ROOT / '../../../.work/pkg49b') as directory:
            rig=pathlib.Path(directory); out=rig/'out'
            (rig/'settings.txt').write_text('name=fixture\n')
            (rig/'marks.txt').write_text('joined 1000000000\nwake_start 301000000000\nwake_end 311000000000\ndone 311000000000\n')
            (rig/'frames.txt').write_text('1000000000\n301100000000\n301133200000\n301150000000\n')
            (rig/'faults-return.json').write_text(json.dumps({'majflt':3}))
            (rig/'snap-wake.json').write_text(json.dumps({'label':'wake','status_mib':{},'smaps_rollup_mib':{},
                'nmt_committed_mib':{},'cgroup_mib':{'current':1,'peak':1,'swap':0,'high':'2684354560'},
                'cgroup_events':{},'majflt':23,'zram_mm_stat':{},'smaps_classes':{},'frozen':False}))
            subprocess.run([sys.executable, '-I', str(ROOT/'analyze.py'), str(rig), str(out)], check=True, capture_output=True)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['wake_majflt_delta'],20)
            self.assertEqual(summary['wake_first_frame_ms'],100)
            self.assertEqual(summary['windows']['wake']['max_ms'],100)
            self.assertEqual(summary['windows']['wake']['over_33ms'],2)


if __name__ == '__main__': unittest.main()
