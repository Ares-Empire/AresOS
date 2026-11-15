"""Walk the native loop regression with closed stand-ins, never host devices."""
import contextlib
import hashlib
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
import prepare_two_disks as loops

GUID='10000001-1111-2222-3333-444444444444'


class HostStandIn:
    def __init__(self):
        self.loops={}; self.mounts={}; self.calls=[]
        self.flat=self.linger=self.bad_backing=self.fail_fuse=False
        self.guid=GUID
        self.gpt_guid=GUID.upper()

    def output(self,command,**kwargs):
        self.calls.append(command)
        tool=pathlib.Path(command[0]).name
        if tool=='losetup' and '--find' in command:
            loop='/dev/loop'+str(90+len(self.loops))
            self.loops[loop]=command[-1]; result=loop+'\n'
        elif tool=='losetup' and '--list' in command:
            loop=command[-1]
            result=json.dumps(dict(loopdevices=[{'name':loop,'back-file':'/wrong' if self.bad_backing else self.loops[loop]}]))
        elif tool=='blkid':
            if command[1:6]==['-p','-s','PART_ENTRY_UUID','-o','value']: result=self.guid+'\n'
            elif command[-2]=='TYPE': result='exfat\n'
            elif command[-2]=='PARTUUID': result='\n'  # the old low-level query is not a GUID source
            else: raise AssertionError('Unwalked blkid tags: '+repr(command))
        elif tool=='sgdisk' and command[1:3]==['-i','1']:
            result='Partition GUID code: C12A7328-F81F-11D2-BA4B-00A0C93EC93B (EFI system partition)\nPartition unique GUID: '+self.gpt_guid+'\n'
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
            columns=set(command[command.index('--output')+1].lower().split(','))
            def selected(row):
                return {key: [selected(child) for child in value] if key=='children' else value
                        for key,value in row.items() if key in columns or key=='children'}
            stdout=json.dumps(dict(blockdevices=[selected(row) for row in rows]))
        elif tool=='sfdisk': stdout=json.dumps(dict(partitiontable=dict(device=command[-1],label='gpt',partitions=[])))
        elif tool=='findmnt':
            selector=next((k for k in ('--source','--target','--mountpoint') if k in command),None)
            value=command[command.index(selector)+1] if selector else None
            rows=[row for target,row in self.mounts.items() if selector is None or
                  (row['source']==value if selector=='--source' else
                   pathlib.Path(value).is_relative_to(target) if selector=='--target' else target==value)]
            if selector is None:
                return subprocess.CompletedProcess(command,0,json.dumps(dict(filesystems=rows)),'')
            if not rows: return subprocess.CompletedProcess(command,1,'','')
            stdout=json.dumps(dict(filesystems=rows))
        elif tool=='losetup' and '--list' in command:
            stdout=json.dumps(dict(loopdevices=[{'name':loop,'back-file':image} for loop,image in self.loops.items()]))
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
        elif tool not in ('sgdisk','udevadm','mkfs.vfat','mkfs.exfat','sync'):
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
            def layout(image):
                first=dict(number=1,start_lba=2048,end_lba=133119 if image.stem=='target' else image.stat().st_size//512-34)
                parts=[first]
                if image.stem=='target':parts.append(dict(number=2,start_lba=133120,end_lba=image.stat().st_size//512-34))
                return dict(partitions=parts)
            def state(loop,number):
                part=layout(pathlib.Path(standin.loops[loop]))['partitions'][number-1]
                return dict(node=loop+'p'+str(number),block=True,start=part['start_lba'],
                            size=part['end_lba']-part['start_lba']+1,dev='7:1',rdev='7:1')
            stack.enter_context(patch.object(loops,'gpt',side_effect=layout))
            stack.enter_context(patch.object(loops,'loop_partition_state',side_effect=state))
            observed=native.Observations(pathlib.Path(temporary)/'observations.json')
            try:
                return native.prove(pathlib.Path(temporary)/'fixture',observed)
            finally:
                self.observed=json.loads(observed.path.read_text())

    def test_complete_native_path_runs_real_helpers_and_confirms_cleanup(self):
        host=HostStandIn(); result=self.exercise(host)
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})
        for index,command in enumerate(host.calls):
            if command[:2]==['losetup','--detach']:
                self.assertEqual(host.calls[index+1],['udevadm','settle','--timeout=5'])
        self.assertEqual(result['helper_mutations'],0)
        self.assertTrue(result['protected_fixture_unchanged'])
        self.assertEqual(self.observed['status'],'passed')
        self.assertEqual(self.observed['expected_guid'],GUID)
        self.assertEqual(self.observed['disk_record_resolved_guid'],GUID)
        self.assertTrue(self.observed['raw_lsblk_trees'] and self.observed['findmnt_rows'])
        self.assertIn('HD(1,GPT,'+GUID+',',self.observed['synthetic_firmware_line'])
        self.assertEqual(self.observed['expected_guid_source']['blkid'][1:6],['-p','-s','PART_ENTRY_UUID','-o','value'])
        self.assertEqual(self.observed['expected_guid_source']['sgdisk'][1:3],['-i','1'])
        queries=[r['command'] for r in result['native_queries']]
        self.assertEqual(sum(c[0]=='lsblk' for c in queries),6)
        check=result['mounted_child']
        self.assertEqual(check['refusal'],'Protected disk is mounted')
        self.assertEqual(check['install_refusal'],'Protected disk is mounted')
        self.assertEqual(check['missing_check_rejected'],'STOP: mounted protected child was accepted')
        self.assertEqual(check['before'],check['after'])
        self.assertEqual(result['cleanup']['mounts_before'],result['cleanup']['mounts_after'])
        self.assertEqual(result['cleanup']['fixture_mounts_remaining'],[])
        self.assertEqual(result['cleanup']['fixture_loops_remaining'],[])
        for query in queries:
            if query[0]=='lsblk': self.assertIn('--tree',query)
            elif query[0]=='findmnt': self.assertIn('--list',query)

    def test_flat_native_result_fails_and_still_cleans_up(self):
        host=HostStandIn(); host.flat=True
        with self.assertRaisesRegex(ValueError,'Unexpected lsblk tree shape'): self.exercise(host)
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})
        self.assertEqual(self.observed['status'],'failed')
        self.assertTrue(self.observed['raw_lsblk_trees'])
        self.assertIn('Unexpected lsblk tree shape',self.observed['error']['message'])

    def test_missing_mounted_child_refusal_fails_the_native_check_and_cleans_up(self):
        host=HostStandIn()
        real=native.owner.require
        def unchecked(condition,message):
            if message!='Protected disk is mounted': real(condition,message)
        with patch.object(native.owner,'require',unchecked):
            with self.assertRaisesRegex(AssertionError,'mounted protected child was accepted'):
                self.exercise(host)
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})
        self.assertEqual(self.observed['status'],'failed')

    def test_wrong_refusal_does_not_satisfy_the_native_condition(self):
        def wrong(*args): raise native.owner.Stop('Wrong or ambiguous protected disk serial')
        with self.assertRaisesRegex(AssertionError,'wrong mounted-child refusal'):
            native.require_mounted_refusal(wrong,None)

    def test_target_file_mutation_fails_even_after_the_correct_refusal(self):
        host=HostStandIn(); real=native.require_mounted_refusal
        def changed(reader,loop_host):
            value=real(reader,loop_host)
            (loop_host.efi/'unexpected').write_text('mutation')
            return value
        with patch.object(native,'require_mounted_refusal',side_effect=changed):
            with self.assertRaisesRegex(AssertionError,'mutated hashes, partitions, mounts or target files'):
                self.exercise(host)
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
        self.assertIn('/dev/loop90',host.loops)
        self.assertFalse(any(c[:2]==['losetup','--detach'] and c[-1]=='/dev/loop90' for c in host.calls))

    def test_wrong_backing_refuses_before_any_format_or_mount(self):
        host=HostStandIn(); host.bad_backing=True
        with self.assertRaisesRegex(AssertionError,'Unexpected loop backing'): self.exercise(host)
        self.assertFalse(any(pathlib.Path(c[0]).name in ('mount','mount.exfat-fuse','mkfs.vfat','mkfs.exfat') for c in host.calls))

    def test_local_invocation_refuses_before_any_host_command(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work') as temporary, \
             patch.object(native,'EVIDENCE',pathlib.Path(temporary)/'observations.json'), \
             patch.dict(os.environ,{},clear=True), patch.object(subprocess,'run') as run, \
             patch.object(subprocess,'check_output') as output:
            with self.assertRaises(AssertionError): native.main()
            observed=json.loads(native.EVIDENCE.read_text())
            self.assertEqual(observed['status'],'failed')
        run.assert_not_called(); output.assert_not_called()

    def test_real_low_level_blkid_output_uses_part_entry_uuid_without_partuuid(self):
        folder=ROOT/'os/tests/fixtures/owner-tools'
        record=json.loads((folder/'blkid-p-gpt-source.json').read_text())
        data=(folder/record['path']).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),record['sha256'])
        text=data.decode();self.assertIn('PART_ENTRY_UUID=',text);self.assertNotIn('PARTUUID=',text)
        expected='f862ead9-063d-475f-a60c-5bbd4bb46c51'
        with tempfile.TemporaryDirectory(dir=ROOT/'.work') as temporary:
            observed=native.Observations(pathlib.Path(temporary)/'observations.json')
            gpt='Partition unique GUID: '+expected.upper()+'\n'
            self.assertEqual(native.expected_guid(text,gpt,observed),expected)
            self.assertEqual(native.expected_guid(expected+'\n',gpt,observed),expected)

    def test_empty_invalid_or_disagreeing_guids_stop_with_both_values_recorded(self):
        for value,gpt in (('',GUID),('not-a-guid',GUID),(GUID,''),(GUID,'20000001-1111-2222-3333-444444444444'),
                           ('PARTUUID="'+GUID+'"',GUID)):
            with self.subTest(value=value,gpt=gpt), tempfile.TemporaryDirectory(dir=ROOT/'.work') as temporary:
                observed=native.Observations(pathlib.Path(temporary)/'observations.json')
                with self.assertRaisesRegex(AssertionError,'blkid PART_ENTRY_UUID=.*sgdisk Partition unique GUID='):
                    native.expected_guid(value,'Partition unique GUID: '+gpt+'\n',observed)
                retained=json.loads(observed.path.read_text())
                self.assertEqual(retained['blkid_output'],value)
                self.assertEqual(retained['sgdisk_guid'],gpt)
                self.assertFalse(retained['checks'][-1]['passed'])

    def test_empty_native_guid_stops_before_real_helpers_and_still_cleans_up(self):
        host=HostStandIn();host.guid=''
        with patch.object(native.owner,'disk_record',wraps=native.owner.disk_record) as helper:
            with self.assertRaisesRegex(AssertionError,'blkid PART_ENTRY_UUID='):
                self.exercise(host)
            helper.assert_not_called()
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})
        self.assertEqual(self.observed['status'],'failed')
        self.assertEqual(self.observed['blkid_guid'],'')
        self.assertEqual(self.observed['sgdisk_guid'],GUID.upper())

    def test_firmware_failure_keeps_both_guids_native_rows_and_synthetic_line(self):
        host=HostStandIn()
        original=native.LoopHost.__init__
        def wrong_firmware(instance,*args,**kwargs):
            original(instance,*args,**kwargs)
            # Change both independently rendered text and its verbose raw node;
            # this tests a foreign EFI identity, not a corrupt formatter dump.
            instance.firmware=native.fixture_firmware('20000001-1111-2222-3333-444444444444')
            instance.observations.note('injected firmware failure',synthetic_firmware_line=instance.firmware)
        with patch.object(native.LoopHost,'__init__',wrong_firmware):
            with self.assertRaisesRegex(native.owner.Stop,'Linux firmware entry does not uniquely map'):
                self.exercise(host)
        self.assertEqual(self.observed['status'],'failed')
        self.assertEqual(self.observed['expected_guid'],GUID)
        self.assertEqual(self.observed['disk_record_resolved_guid'],GUID)
        self.assertTrue(self.observed['raw_lsblk_trees'] and self.observed['findmnt_rows'])
        self.assertIn('20000001-',self.observed['synthetic_firmware_line'])
        self.assertEqual(host.loops,{})
        self.assertEqual(host.mounts,{})

    def test_probe_native_suite_requires_the_loop_regression(self):
        import yaml
        workflow=yaml.load((ROOT/'.github/workflows/os-image.yml').read_text(),Loader=yaml.BaseLoader)
        job=workflow['jobs']['rehearsal']
        step,=[s for s in job['steps'] if s.get('name')=='Qualify tools, regressions, rewritten release identity and private access']
        self.assertNotIn('continue-on-error',step)
        self.assertIn('if test "$GITHUB_REF_NAME" = pkg/14-owner-tools || test "$GITHUB_REF_NAME" = pkg/16-staged-release || test "$GITHUB_REF_NAME" = pkg/27-first-update-release || test "$GITHUB_REF_NAME" = pkg/22c-ways-back-after-update; then\n',step['run'])
        self.assertIn('sudo -E env -u GH_TOKEN python3 os/ci/owner_devices.py',step['run'])
        self.assertLess(step['run'].index('owner_devices.py'),step['run'].index('verify_release.py'))


if __name__=='__main__': unittest.main()
