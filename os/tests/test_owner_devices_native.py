"""Walk the native loop regression with closed stand-ins, never host devices."""
import contextlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import owner_devices as native

GUID='10000001-1111-2222-3333-444444444444'


class HostStandIn:
    def __init__(self):
        self.loops={}; self.mounts={}; self.calls=[]
        self.flat=self.linger=self.bad_backing=self.fail_fuse=False

    def output(self,command,**kwargs):
        self.calls.append(command)
        tool=pathlib.Path(command[0]).name
        if tool=='losetup' and '--find' in command:
            loop='/dev/loopFIXTURE'+str(len(self.loops))
            self.loops[loop]=command[-1]; result=loop+'\n'
        elif tool=='losetup' and '--list' in command:
            loop=command[-1]
            result=json.dumps(dict(loopdevices=[{'name':loop,'back-file':'/wrong' if self.bad_backing else self.loops[loop]}]))
        elif tool=='blkid': result='exfat\n' if command[-2]=='TYPE' else GUID+'\n'
        else: raise AssertionError('Unwalked output: '+repr(command))
        return result if kwargs.get('text') else result.encode()

    def run(self,command,**kwargs):
        self.calls.append(command)
        tool=pathlib.Path(command[0]).name
        stdout=''
        if tool=='lsblk':
            rows=[]
            for loop,image in self.loops.items():
                children=[]
                for number in range(1,3 if pathlib.Path(image).stem=='target' else 2):
                    source=loop+'p'+str(number)
                    children.append(dict(path=source,type='part',partuuid=GUID,
                        parttype='c12a7328-f81f-11d2-ba4b-00a0c93ec93b' if number==1 else 'ebd0a0a2-b9e5-4433-87c0-68b6b72699c7',
                        label='ARESTOOLS' if number==2 else None,fstype='exfat' if number==2 else 'vfat',
                        uuid='CAFE-1234',mountpoints=[target for target,row in self.mounts.items() if row['source']==source] or [None]))
                row=dict(path=loop,type='loop',serial=None,tran=None,rm=False,mountpoints=[None])
                if self.flat: rows.extend([row,*children])
                else: rows.append(dict(row,children=children))
            stdout=json.dumps(dict(blockdevices=rows))
        elif tool=='sfdisk': stdout=json.dumps(dict(partitiontable=dict(device=command[-1],label='gpt',partitions=[])))
        elif tool=='findmnt':
            selector=next(k for k in ('--source','--target','--mountpoint') if k in command)
            value=command[command.index(selector)+1]
            rows=[row for target,row in self.mounts.items() if (row['source'] if selector=='--source' else target)==value]
            if not rows: return subprocess.CompletedProcess(command,1,'','')
            stdout=json.dumps(dict(filesystems=rows))
        elif tool=='mount.exfat-fuse':
            if self.fail_fuse: raise subprocess.CalledProcessError(9,command)
            self.mounts[command[-1]]=dict(source=command[-2],target=command[-1],fstype='fuseblk',**{'vfs-options':command[2]})
        elif tool=='mount' and '--internal-only' in command:
            self.mounts[command[-1]]['vfs-options']=command[3].removeprefix('remount,bind,')
        elif tool=='mount':
            self.mounts[command[-1]]=dict(source=command[-2],target=command[-1],fstype='vfat',**{'vfs-options':command[4]})
        elif tool=='umount':
            if not self.linger: del self.mounts[command[-1]]
        elif tool=='losetup' and '--detach' in command:
            assert not any(row['source'].startswith(command[-1]+'p') for row in self.mounts.values())
            del self.loops[command[-1]]
        elif tool not in ('sgdisk','udevadm','mkfs.vfat','mkfs.exfat'):
            raise AssertionError('Unwalked command: '+repr(command))
        return subprocess.CompletedProcess(command,0,stdout,'')


class NativeWalkTest(unittest.TestCase):
    def exercise(self,standin):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work') as temporary, contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(native,'WORK',pathlib.Path(temporary)))
            stack.enter_context(patch.dict(os.environ,GITHUB_SHA='a'*40))
            stack.enter_context(patch.object(subprocess,'run',side_effect=standin.run))
            stack.enter_context(patch.object(subprocess,'check_output',side_effect=standin.output))
            stack.enter_context(patch('shutil.which',side_effect=lambda name,**kw:'/fixture/'+name))
            return native.prove(pathlib.Path(temporary)/'fixture')

    def test_complete_native_path_runs_real_helpers_and_confirms_cleanup(self):
        host=HostStandIn(); result=self.exercise(host)
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})
        self.assertEqual(result['helper_mutations'],0)
        self.assertTrue(result['protected_fixture_unchanged'])
        queries=[r['command'] for r in result['native_queries']]
        self.assertEqual(sum(c[0]=='lsblk' for c in queries),2)
        for query in queries:
            if query[0]=='lsblk': self.assertIn('--tree',query)
            elif query[0]=='findmnt': self.assertIn('--list',query)

    def test_flat_native_result_fails_and_still_cleans_up(self):
        host=HostStandIn(); host.flat=True
        with self.assertRaisesRegex(ValueError,'Unexpected lsblk tree shape'): self.exercise(host)
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})

    def test_failed_fuse_mount_cleans_up_without_a_filesystem_fallback(self):
        host=HostStandIn(); host.fail_fuse=True
        with self.assertRaises(subprocess.CalledProcessError): self.exercise(host)
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})
        self.assertEqual(sum(pathlib.Path(c[0]).name=='mount.exfat-fuse' for c in host.calls),1)

    def test_unconfirmed_unmount_prevents_target_detach(self):
        host=HostStandIn(); host.linger=True
        with self.assertRaisesRegex(AssertionError,'unmount|mounted'): self.exercise(host)
        self.assertIn('/dev/loopFIXTURE0',host.loops)
        self.assertFalse(any(c[:2]==['losetup','--detach'] and c[-1]=='/dev/loopFIXTURE0' for c in host.calls))

    def test_wrong_backing_refuses_before_any_format_or_mount(self):
        host=HostStandIn(); host.bad_backing=True
        with self.assertRaisesRegex(AssertionError,'Unexpected loop backing'): self.exercise(host)
        self.assertFalse(any(pathlib.Path(c[0]).name in ('mount','mount.exfat-fuse','mkfs.vfat','mkfs.exfat') for c in host.calls))

    def test_local_invocation_refuses_before_any_host_command(self):
        with patch.dict(os.environ,{},clear=True), patch.object(subprocess,'run') as run, \
             patch.object(subprocess,'check_output') as output, self.assertRaises(AssertionError): native.main()
        run.assert_not_called(); output.assert_not_called()

    def test_probe_native_suite_requires_the_loop_regression(self):
        import yaml
        workflow=yaml.load((ROOT/'.github/workflows/os-image.yml').read_text(),Loader=yaml.BaseLoader)
        job=workflow['jobs']['rehearsal']
        step,=[s for s in job['steps'] if s.get('name')=='Qualify tools, regressions, rewritten release identity and private access']
        self.assertNotIn('continue-on-error',step)
        self.assertIn('if test "$GITHUB_REF_NAME" = pkg/14-owner-tools; then\n',step['run'])
        self.assertIn('sudo -E env -u GH_TOKEN python3 os/ci/owner_devices.py',step['run'])
        self.assertLess(step['run'].index('owner_devices.py'),step['run'].index('verify_release.py'))


if __name__=='__main__': unittest.main()
