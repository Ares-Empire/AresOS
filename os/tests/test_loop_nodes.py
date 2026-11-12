"""No devices: exercise the real bounded wait with synthetic kernel snapshots."""
import ast
import contextlib
import json
import pathlib
import stat
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import prepare_two_disks as loops


class LoopNodesTest(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, states):
        clock=[0.0];calls=[];checks=[0]
        def snapshot(loop,number):
            checks[0]+=1
            return states[min(checks[0]-1,len(states)-1)]
        def command(args,**kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args,0,'SYNTHETIC UDEV LOOP STATE','')
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(loops,'verify_loop'))
            stack.enter_context(patch.object(loops,'gpt',return_value=dict(partitions=[dict(number=1,start_lba=2048,end_lba=4095)])))
            stack.enter_context(patch.object(loops,'loop_partition_state',side_effect=snapshot))
            stack.enter_context(patch.object(subprocess,'run',side_effect=command))
            stack.enter_context(patch.object(loops.time,'monotonic',side_effect=lambda:clock[0]))
            stack.enter_context(patch.object(loops.time,'sleep',side_effect=lambda seconds:clock.__setitem__(0,clock[0]+seconds)))
            yield calls,checks,clock

    def ready(self,**changes):
        return dict(dict(node='/dev/loop7p1',block=True,start=2048,size=2048,dev='7:8',rdev='7:8'),**changes)

    def test_node_appears_on_second_check_before_any_partx(self):
        with self.fixture([self.ready(block=False),self.ready()]) as (calls,checks,clock):
            result=loops.wait_loop_partitions('/dev/loop7',pathlib.Path('SYNTHETIC.raw'))
        self.assertEqual(checks[0],2)
        self.assertFalse(result['partx_retry'])
        self.assertEqual(calls,[['udevadm','settle','--timeout=5']])

    def test_never_appears_stops_at_fifteen_seconds_with_one_update_and_state(self):
        with self.fixture([self.ready(block=False)]) as (calls,checks,clock):
            with self.assertRaisesRegex(AssertionError,'STOP: loop partition nodes') as error:
                loops.wait_loop_partitions('/dev/loop7',pathlib.Path('SYNTHETIC.raw'))
        self.assertEqual(clock[0],15)
        self.assertEqual(calls.count(['partx','--update','/dev/loop7']),1)
        self.assertEqual(sum(c[:2]==['udevadm','settle'] for c in calls),2)
        report=json.loads(str(error.exception).split('GPT: ',1)[1])
        self.assertFalse(report['sysfs'][0]['block'])
        self.assertIn('SYNTHETIC UDEV LOOP STATE',report['udev']['stdout'])

    def test_stale_geometry_or_wrong_device_identity_never_passes(self):
        for changes in (dict(start=1),dict(size=1),dict(dev='7:OTHER'),dict(block=False)):
            with self.subTest(changes=changes),self.fixture([self.ready(**changes)]):
                with self.assertRaisesRegex(AssertionError,'did not match written GPT'):
                    loops.wait_loop_partitions('/dev/loop7',pathlib.Path('SYNTHETIC.raw'))

    def test_partx_retry_can_recover_after_first_wait(self):
        with self.fixture([self.ready(block=False)]*31+[self.ready()]) as (calls,checks,clock):
            result=loops.wait_loop_partitions('/dev/loop7',pathlib.Path('SYNTHETIC.raw'))
        self.assertTrue(result['partx_retry'])
        self.assertEqual(calls.count(['partx','--update','/dev/loop7']),1)
        self.assertLessEqual(clock[0],15)

    def test_real_state_reader_checks_block_type_and_reads_exact_sysfs_files(self):
        paths=[]
        def read(path,**kwargs):
            paths.append(str(path))
            return {'start':'2048\n','size':'2048\n','dev':'7:8\n'}[path.name]
        with patch.object(pathlib.Path,'lstat',return_value=SimpleNamespace(st_mode=stat.S_IFBLK,st_rdev=1792+8)), \
             patch.object(pathlib.Path,'read_text',read):
            result=loops.loop_partition_state('/dev/loop7',1)
        self.assertTrue(result['block'])
        self.assertEqual((result['start'],result['size'],result['dev'],result['rdev']),(2048,2048,'7:8','7:8'))
        self.assertEqual(paths,['/sys/block/loop7/loop7p1/'+field for field in ('start','size','dev')])
        for mode in (stat.S_IFREG,stat.S_IFLNK):
            with patch.object(pathlib.Path,'lstat',return_value=SimpleNamespace(st_mode=mode,st_rdev=0)), \
                 patch.object(pathlib.Path,'read_text',read):
                self.assertFalse(loops.loop_partition_state('/dev/loop7',1)['block'])

    def test_unverified_or_nonloop_device_refuses_before_settle_or_update(self):
        for loop in ('/dev/sda','/dev/loop7/../sda','/dev/loop7p1'):
            with self.subTest(loop=loop),patch.object(subprocess,'run') as command,self.assertRaises(AssertionError):
                loops.wait_loop_partitions(loop,pathlib.Path('SYNTHETIC.raw'))
            command.assert_not_called()
        with patch.object(loops,'verify_loop',side_effect=AssertionError('bad backing')), \
             patch.object(subprocess,'run') as command,self.assertRaisesRegex(AssertionError,'bad backing'):
            loops.wait_loop_partitions('/dev/loop7',pathlib.Path('SYNTHETIC.raw'))
        command.assert_not_called()

    def test_every_partscan_caller_uses_shared_wait_before_consuming_nodes(self):
        expected={('owner_media.py','mounted'),('owner_devices.py','prove_observed'),
                  ('owner_capabilities.py','exfat'),('prepare_two_disks.py','main'),
                  ('owner_vm.py','pin_serial_console')}
        actual=set()
        for path in (ROOT/'os/ci').glob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.FunctionDef) and any(isinstance(n,ast.Constant) and n.value=='--partscan' for n in ast.walk(node)):
                    actual.add((path.name,node.name))
                    calls=[n for n in ast.walk(node) if isinstance(n,ast.Call) and ast.unparse(n.func).endswith('wait_loop_partitions')]
                    self.assertEqual(len(calls),1,(path.name,node.name))
                    scan=min(n.lineno for n in ast.walk(node) if isinstance(n,ast.Constant) and n.value=='--partscan')
                    self.assertGreater(calls[0].lineno,scan)
                    formatters=[n for n in ast.walk(node) if isinstance(n,ast.Call) and
                                any(isinstance(a,ast.Constant) and isinstance(a.value,str) and a.value.startswith('mkfs.') for a in n.args)]
                    for formatter in formatters:self.assertGreater(formatter.lineno,calls[0].lineno)
        self.assertEqual(actual,expected)


if __name__=='__main__':unittest.main()
