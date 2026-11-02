import contextlib
import errno
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import owner_capabilities as caps
import owner_vm
from owner_fuse_shim import Volume


class CapabilitiesTest(unittest.TestCase):
    def test_native_step_is_mandatory_for_both_modes_before_downloads(self):
        workflow=yaml.load((ROOT/'.github/workflows/os-image.yml').read_text(),Loader=yaml.BaseLoader)
        steps=workflow['jobs']['rehearsal']['steps']
        capability,=[s for s in steps if s.get('name')==caps.STEP]
        self.assertEqual(capability['if'],"(github.ref_name == 'pkg/14-owner-tools' || github.ref_name == 'pkg/16-staged-release')")
        self.assertEqual(capability['timeout-minutes'],'3')
        self.assertIn('sudo -E python3 os/ci/owner_capabilities.py',capability['run'])
        self.assertNotIn('GH_TOKEN',capability.get('env',{}))
        install,=[s for s in steps if s.get('name')=='Install pinned rehearsal tools on disposable runner']
        self.assertIn(' exfat-fuse ',install['run'])
        index=steps.index(capability)
        self.assertLess(steps.index(install),index)
        for name in ('Qualify tools, regressions, rewritten release identity and private access',
                     'Prepare package 13 job-token credentials without owner-secret fallback',
                     'Qualify the exact pinned layer pull without installing',
                     'Inspect the exact pinned live ISO before assuming an installer path'):
            self.assertLess(index,next(i for i,s in enumerate(steps) if s.get('name')==name))

    def test_real_exfat_capability_flow_with_no_host_commands(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary,contextlib.ExitStack() as stack:
            directory=pathlib.Path(temporary).resolve();volume=Volume(directory,directory/'fuse')
            stack.enter_context(patch.object(subprocess,'run',side_effect=volume.run))
            stack.enter_context(patch.object(subprocess,'check_output',side_effect=volume.output))
            volume.patch_nodes(stack)
            original=pathlib.Path.open
            def opened(path,*args,**kwargs):
                if path.name=='must-refuse' and volume.readonly:raise OSError(errno.EROFS,'synthetic read-only filesystem')
                return original(path,*args,**kwargs)
            stack.enter_context(patch.object(pathlib.Path,'open',opened))
            image=caps.exfat(directory)
            self.assertEqual(image.stat().st_size,64*1024**2)
            self.assertFalse(volume.active)
            self.assertEqual(sum(c[0]=='mount.exfat-fuse' for c in volume.calls),2)
            self.assertEqual(sum(c[0]=='fsck.exfat' for c in volume.calls),1)

    def test_qemu_qmp_marker_and_paused_usb_paths_use_only_scratch_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary,contextlib.ExitStack() as stack:
            directory=pathlib.Path(temporary).resolve();image=directory/'exfat.raw';image.write_bytes(b'SYNTHETIC')
            process=Mock(returncode=None);process.poll.side_effect=lambda:process.returncode
            process.wait.side_effect=lambda **kw:process.returncode
            calls=[]
            class Monitor:
                def __init__(self,sock):self.events=[]
                def command(self,name,args=None):
                    calls.append((name,args))
                    if name=='human-monitor-command':return 'dev: i8042; dev: ps2-kbd'
                    if name=='query-status':return dict(status='prelaunch')
                    if name=='query-pci':return [dict(bus=0)]
                    if name=='query-block':return [dict(inserted={'node-name':'cap-raw'})]
                    if name=='device_del':self.events.append(dict(event='DEVICE_DELETED',data=dict(device='cap-usb')))
                    if name=='cont':(directory/'marker.txt').write_text('MARKER_BOOT_COMPLETE')
                    if name=='screendump':pathlib.Path(args['filename']).write_bytes(b'P6'+b'0'*1000)
                    if name=='quit':process.returncode=0
                    return {}
            stack.enter_context(patch.object(caps.fixture,'main'))
            popen=stack.enter_context(patch.object(subprocess,'Popen',return_value=process))
            stack.enter_context(patch.object(caps,'connect',return_value=Mock()))
            stack.enter_context(patch.object(caps,'QMP',Monitor))
            result=caps.qemu(directory,image)
            self.assertTrue(result['marker_booted'])
            names=[n for n,a in calls]
            self.assertLess(names.index('device_del'),names.index('cont'))
            self.assertLess(names.index('blockdev-del'),names.index('cont'))
            self.assertIn('send-key',names);self.assertIn('screendump',names)
            argv=popen.call_args.args[0]
            self.assertIn('-S',argv);self.assertIn('6144',argv)
            for word in argv:
                if 'file=' in word and '/usr/share/OVMF/' not in word:self.assertIn(str(directory),word)
            process.kill.assert_not_called()

    def test_missing_tool_or_fuse_failure_never_reaches_qemu(self):
        env=dict(GITHUB_ACTIONS='true',GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY='Ares-Empire/AresOS',
                 GITHUB_REF_NAME='pkg/14-owner-tools',REHEARSAL_PACKAGE='14',REHEARSAL_MODE='probe',GITHUB_SHA='a'*40)
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary,patch.dict(os.environ,env), \
             patch.object(pathlib.Path,'resolve',return_value=pathlib.Path(temporary).resolve()), \
             patch.object(caps.shutil,'which',return_value=None),patch.object(caps,'exfat') as fuse,patch.object(caps,'qemu') as qemu:
            with self.assertRaisesRegex(AssertionError,'missing host capability tool'):caps.main()
            fuse.assert_not_called();qemu.assert_not_called()
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary,patch.dict(os.environ,env), \
             patch.object(pathlib.Path,'resolve',return_value=pathlib.Path(temporary).resolve()), \
             patch.object(caps.shutil,'which',return_value='/synthetic/tool'), \
             patch.object(caps,'exfat',side_effect=RuntimeError('synthetic FUSE failure')),patch.object(caps,'qemu') as qemu:
            with self.assertRaisesRegex(RuntimeError,'synthetic FUSE failure'):caps.main()
            qemu.assert_not_called()

    def test_qemu_socket_failure_kills_only_its_own_process(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary,patch.object(caps.fixture,'main'), \
             patch.object(caps,'connect',side_effect=TimeoutError('synthetic missing QMP')), \
             patch.object(subprocess,'Popen') as popen:
            directory=pathlib.Path(temporary).resolve();process=popen.return_value
            process.poll.return_value=None
            with self.assertRaisesRegex(TimeoutError,'synthetic missing QMP'):caps.qemu(directory,directory/'toy.raw')
            process.kill.assert_called_once();process.wait.assert_called_once_with(timeout=10)

    def test_incomplete_or_wrong_head_capability_proof_refuses_before_media(self):
        good=dict(status='passed',sha='a'*40,checks=dict.fromkeys(caps.CHECKS,True))
        for package,branch in (('14','pkg/14-owner-tools'),('16','pkg/16-staged-release')):
            authorization=dict(allowance=package,native=dict(status='passed',sha='a'*40))
            for changed in (dict(good,status='failed'),dict(good,sha='b'*40),dict(good,checks={})):
                responses=iter((json.dumps(authorization),json.dumps(changed)))
                with self.subTest(package=package,changed=changed),patch.object(sys,'argv',['owner_vm.py','probe']), \
                     patch.dict(os.environ,GITHUB_SHA='a'*40,GITHUB_ACTIONS='true',GITHUB_EVENT_NAME='workflow_dispatch',
                         GITHUB_REPOSITORY='Ares-Empire/AresOS',GITHUB_REF_NAME=branch,
                         REHEARSAL_PACKAGE=package,REHEARSAL_MODE='probe'), \
                     patch.object(pathlib.Path,'read_text',side_effect=lambda *a,**kw:next(responses)) as read, \
                     patch.object(owner_vm,'Media') as media,self.assertRaises(AssertionError):owner_vm.main()
                self.assertEqual(read.call_count,2)
                media.assert_not_called()


if __name__=='__main__':unittest.main()
