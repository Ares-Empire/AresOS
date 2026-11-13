"""Native owner disk-query regression, confined to fresh hosted-runner loops.

The exact helper queries execute against real lsblk/findmnt. A loop has no
USB transport or hardware serial: only those root identity fields and TYPE
are supplied by the fixture. Tree structure and partition fields are never
reshaped. The fixture maps guest mountpoint arguments to its scratch mount
and supplies a synthetic firmware read; it never accesses host firmware.
"""
import contextlib
import copy
import json
import os
import pathlib
import re
import subprocess
import struct
import shutil
import sys
import uuid
from unittest.mock import patch

import owner_fuse
import owner_media
from prepare_two_disks import verify_loop, wait_loop_partitions

owner = owner_media.bundle_module('owner')
WORK = pathlib.Path('.work').resolve()
EVIDENCE = pathlib.Path('evidence/14-native-owner-devices.json')


def fixture_firmware(guid, sectors=0x20000):
    """Source-derived efibootmgr18/efivar39 rendering, never a host EFI read.

    HD/file/end nodes and printf formats are bound in parser-sources/README.md.
    The GUID comes from both independent native fixture queries, not a guess.
    """
    file = '\\EFI\\fedora\\shimx64.efi'
    hd = struct.pack('<BBHIQQ16sBB',4,1,42,1,0x800,sectors,uuid.UUID(guid).bytes_le,2,2)
    name = (file+'\0').encode('utf-16-le')
    nodes = [hd,struct.pack('<BBH',4,4,len(name)+4)+name,b'\x7f\xff\x04\0']
    return ('Boot0001* Fixture Linux\tHD(1,GPT,'+guid.lower()+',0x800,'+hex(sectors)+')/'+file+'\n'
        +'      dp: '+' / '.join(n.hex(' ') for n in nodes)+'\n')


class Observations:
    """Persist native inputs before a helper can refuse them."""
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.value = dict(status='running',sha=os.environ.get('GITHUB_SHA'),
            raw_lsblk_trees=[],findmnt_rows=[],expected_guid=None,expected_guid_source={},
            synthetic_firmware_line=None,disk_record_resolved_guid=None,checks=[])

    def note(self, stage, **values):
        self.value.update(stage=stage,**values)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(self.value,indent=2)+'\n',encoding='utf-8',newline='\n')

    def check(self, condition, message):
        self.value['checks'].append(dict(message=message,passed=bool(condition)))
        self.note(message)
        if not condition:
            raise AssertionError(message)

    def failed(self, error):
        self.note('failure',status='failed',error=dict(type=type(error).__name__,message=str(error)))


def expected_guid(blkid_output, gpt_output, observations):
    # The live query selects -o value. Accept the complete real -p output too,
    # so the regression exercises the tag name rather than inventing PARTUUID.
    value = blkid_output.strip()
    if '=' in value:
        matches = re.findall(r'(?:^|\s)PART_ENTRY_UUID="([^"]*)"(?=\s|$)',value)
        value = matches[0] if len(matches)==1 else ''
    gpt = re.findall(r'^Partition unique GUID:[ \t]*(\S*)[ \t]*$',gpt_output,re.M)
    other = gpt[0] if len(gpt)==1 else ''
    observations.note('validate independent EFI GUIDs',blkid_guid=value,sgdisk_guid=other,
                      blkid_output=blkid_output,sgdisk_output=gpt_output,expected_guid=value)
    valid = lambda text: re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',text)
    observations.check(bool(valid(value) and valid(other) and value.lower()==other.lower()),
        'STOP: invalid or mismatched fixture EFI GUID: blkid PART_ENTRY_UUID='+repr(value)+
        '; sgdisk Partition unique GUID='+repr(other))
    return value


class LoopHost:
    def __init__(self, loops, efi, guid, observations):
        self.native = owner.Host()
        self.loops, self.efi, self.guid = loops, efi, guid
        self.observations = observations
        self.raw_trees = []
        self.adapted_tree = []
        self.efi_source = None
        self.firmware = fixture_firmware(guid)
        self.observations.note('synthetic firmware ready',synthetic_firmware_line=self.firmware)

    def resolved_guid(self):
        def nodes(rows):
            for row in rows:
                yield row
                yield from nodes(row.get('children',[]))
        matches = [row.get('partuuid') for row in nodes(self.adapted_tree) if row.get('path')==self.efi_source]
        return matches[0] if len(matches)==1 else None

    def read(self, *command, **kwargs):
        if command == ('efibootmgr','-v'):
            # disk_record has resolved this same lsblk/findmnt identity before
            # asking for firmware, even when its next assertion will fail.
            self.observations.note('before firmware mapping check',
                disk_record_resolved_guid=self.resolved_guid(),disk_record_efi_source=self.efi_source)
            return self.firmware
        native = list(command)
        if command[0] == 'findmnt' and command[3] == '--mountpoint':
            native[4] = str(self.efi)
        self.observations.note('before native read',command=list(command),native_command=native)
        raw = self.native.read(*native, **kwargs)
        if command[0] == 'lsblk':
            self.observations.value['raw_lsblk_trees'].append(dict(command=native,stdout=raw))
            self.observations.note('raw lsblk before JSON or shape assertions')
            value = json.loads(raw)
            self.observations.value['raw_lsblk_trees'][-1]['parsed'] = copy.deepcopy(value)
            # Keep orphan partition rows too: a flat native result must fail,
            # rather than becoming a plausible but incomplete root-only list.
            rows = [row for row in value['blockdevices'] if any(
                row['path'] == loop or row['path'].startswith(loop+'p') for loop in self.loops)]
            self.raw_trees.append(copy.deepcopy(rows))
            self.observations.note('raw selected loop rows',raw_loop_trees=self.raw_trees)
            for row in rows:
                if row['path'] in self.loops:
                    self.observations.check(row['type']=='loop','STOP: native fixture did not receive a loop root')
                    row.update(type='disk',serial=self.loops[row['path']],tran='usb',rm=True)
            self.adapted_tree = rows
            self.observations.note('adapted loop root identities; partitions unchanged')
            return json.dumps(dict(blockdevices=rows))
        if command[0] == 'findmnt':
            self.observations.value['findmnt_rows'].append(dict(command=native,requested=list(command),stdout=raw))
            self.observations.note('raw findmnt before JSON or mount assertions')
            value = json.loads(raw)
            self.observations.value['findmnt_rows'][-1]['parsed'] = copy.deepcopy(value)
            if getattr(self,'install_media',False) and command[3]=='--target':
                # install's exFAT contract is about the volume, whose native
                # lsblk FSTYPE remains exfat; this host mounts it with FUSE.
                row,=value['filesystems']
                target=next(iter(self.loops))
                self.observations.check(row['source']==target+'p2' and row['fstype']=='fuseblk',
                    'STOP: install adapter did not receive the native tools FUSE mount')
                row['fstype']='exfat'
            if command[3] == '--mountpoint':
                for row in value['filesystems']:
                    self.observations.check(row['target']==str(self.efi),'STOP: wrong sandbox mount')
                    row['target'] = command[4]
                    if command[4]=='/boot/efi': self.efi_source=row['source']
            if command[3]=='--mountpoint' and command[4]=='/boot/efi':
                self.observations.note('EFI mount before real helper assertions',
                    disk_record_resolved_guid=self.resolved_guid(),disk_record_efi_source=self.efi_source)
            else:
                self.observations.note('findmnt before real helper assertions')
            return json.dumps(value)
        self.observations.note('native read complete',native_queries=self.native.trace)
        return raw

    def json(self, *command): return json.loads(self.read(*command))

    def mutate(self, *command, **kwargs):
        self.observations.note('forbidden helper mutation',refused_mutation=list(command))
        raise AssertionError('STOP: disk/media readers attempted a mutation')


def run(*command):
    subprocess.run(list(command),check=True,timeout=30)


def mount_snapshot():
    rows = owner.Host().json('findmnt','--json','--list','--output','SOURCE,TARGET,FSTYPE,OPTIONS')['filesystems']
    return sorted(rows, key=lambda row: json.dumps(row,sort_keys=True))


def require_mounted_refusal(reader, host):
    try:
        reader(host,dict(target='TARGET',protected='KEEP'))
    except owner.Stop as error:
        assert str(error)=='Protected disk is mounted', 'STOP: wrong mounted-child refusal: '+str(error)
        return str(error)
    raise AssertionError('STOP: mounted protected child was accepted')


def mounted_child(host, protected, directory, observations):
    """The real install preflight helper, with native partition/mount fields.

    The negative control drops exactly the mounted-child requirement. All
    remaining real helper queries still run; the refusal oracle must reject it.
    Neither path can install, format, or write a file.
    """
    images = [directory/(name+'.raw') for name in ('target','protected')]
    before = dict(hashes=[owner_media.digest(p) for p in images],mounts=mount_snapshot(),
        partitions=[host.native.json('sfdisk','--json',loop) for loop in host.loops],
        files=sorted(str(p.relative_to(directory)) for name in ('efi','tools')
                     for p in (directory/name).rglob('*')))
    rows=owner_fuse.mounts('--source',protected+'p1')
    observations.check(len(rows)==1 and rows[0]['target']==str(directory/'protected-mount')
        and 'ro' in rows[0]['vfs-options'].split(',') and 'rw' not in rows[0]['vfs-options'].split(','),
        'STOP: protected child is not natively mounted read-only')
    def install_preflight(host, expected):
        host.install_media=True
        try:
            with patch.object(owner,'HOME',directory/'efi/native-install-refusal'), \
                 patch.object(sys,'dont_write_bytecode',True), \
                 patch.object(sys.stdin,'isatty',return_value=True), \
                 patch('builtins.input',side_effect=[expected['target'],expected['protected']]):
                return owner.install(directory/'private-bootstrap',host)
        finally:
            host.install_media=False
    refusal=require_mounted_refusal(owner.disk_record,host)
    install_refusal=require_mounted_refusal(install_preflight,host)
    real_require=owner.require
    def unchecked(condition,message):
        if message!='Protected disk is mounted': real_require(condition,message)
    def missing_check(*args):
        with patch.object(owner,'require',unchecked): return owner.disk_record(*args)
    try:
        require_mounted_refusal(missing_check,host)
    except AssertionError as error:
        assert str(error)=='STOP: mounted protected child was accepted'
        negative=str(error)
    else:
        raise AssertionError('STOP: missing mounted-child check was not detected')
    after = dict(hashes=[owner_media.digest(p) for p in images],mounts=mount_snapshot(),
        partitions=[host.native.json('sfdisk','--json',loop) for loop in host.loops],
        files=sorted(str(p.relative_to(directory)) for name in ('efi','tools')
                     for p in (directory/name).rglob('*')))
    observations.note('mounted protected child result',mounted_child=dict(status='passed',
        refusal=refusal,install_refusal=install_refusal,missing_check_rejected=negative,before=before,after=after,
        protected_child_mount=rows,helper='owner.install private bootstrap copy -> owner.disk_record'))
    observations.check(after==before,'STOP: mounted-child refusal mutated hashes, partitions, mounts or target files')
    return observations.value['mounted_child']


def detach(loop, image, parts, observations):
    observations.note('before cleanup backing verification',cleanup_loop=loop,cleanup_image=str(image))
    verify_loop(loop,image)
    for number in range(1,parts+1):
        observations.note('before cleanup mount query',cleanup_partition=loop+'p'+str(number))
        rows=owner_fuse.mounts('--source',loop+'p'+str(number))
        observations.note('cleanup mount rows',cleanup_mount_rows=rows)
        observations.check(not rows,'STOP: fixture partition remains mounted')
    run('losetup','--detach',loop)
    run('udevadm','settle','--timeout=5')
    remaining=owner.Host().json('losetup','--json','--list','--output','NAME,BACK-FILE')['loopdevices']
    observations.check(not any(row['name']==loop or row['back-file']==str(image) for row in remaining),
        'STOP: fixture loop or backing remains attached')
    observations.note('backing-verified loop detached',cleanup_remaining_loops=remaining)


def prove(directory, observations):
    try:
        return prove_observed(directory,observations)
    except BaseException as error:
        observations.failed(error)
        raise


def prove_observed(directory, observations):
    directory = pathlib.Path(directory).resolve()
    observations.note('fixture path guard',directory=str(directory))
    observations.check(not directory.exists() and directory.parent==WORK,'STOP: fresh workspace fixture required')
    directory.mkdir()
    mounts_before=mount_snapshot()
    with contextlib.ExitStack() as cleanup:
        loops = []
        for name, parts, size in (('target',2,160),('protected',1,80)):
            image=directory/(name+'.raw')
            with image.open('xb') as stream: stream.truncate(size*1024**2)
            args=['sgdisk','--clear','--new=1:2048:+64M','--typecode=1:ef00',
                  '--new=2:0:0','--typecode=2:0700',str(image)] if parts==2 else [
                  'sgdisk','--clear','--new=1:2048:0','--typecode=1:ef00',str(image)]
            run(*args)
            loop=subprocess.check_output(['losetup','--find','--show','--partscan',str(image)],text=True,timeout=10).strip()
            observations.note('before loop backing verification',loop=loop,image=str(image))
            verify_loop(loop,image)
            cleanup.callback(detach,loop,image,parts,observations)
            loops.append(loop)
            observations.note('before GPT/node readiness check',loop=loop,image=str(image))
            ready=wait_loop_partitions(loop,image)
            observations.note('GPT partition nodes ready',loop_partition_readiness=ready)
        run('udevadm','settle')
        target, protected = loops
        protected_image=directory/'protected.raw'
        run('mkfs.vfat','-F','32','-n','KEEP_ESP',protected+'p1')
        protected_before=owner_media.digest(protected_image)
        run('mkfs.vfat','-F','32','-n','ARES_ESP',target+'p1')
        run('mkfs.exfat','-L','ARESTOOLS',target+'p2')
        efi, tools = directory/'efi', directory/'tools'
        efi.mkdir(); tools.mkdir()
        run('mount','-t','vfat','-o','ro,nodev,nosuid,noexec',target+'p1',str(efi))
        cleanup.callback(owner_fuse.unmount,target+'p1',efi)
        # Register first so even a failed FUSE mount/postcondition is inspected
        # and unmounted before either backing-verified loop can be detached.
        cleanup.callback(owner_fuse.unmount,target+'p2',tools)
        owner_fuse.mount(target+'p2',tools)
        owner_media.bundle_module('bundle').build(tools/'ares-tools')
        run('sync','-f',str(tools))
        owner_fuse.unmount(target+'p2',tools)
        owner_fuse.mount(target+'p2',tools,readonly=True)
        shutil.copytree(tools/'ares-tools',directory/'private-bootstrap')
        blkid=['blkid','-p','-s','PART_ENTRY_UUID','-o','value',target+'p1']
        gpt=['sgdisk','-i','1',str(directory/'target.raw')]
        observations.note('independent GUID sources',expected_guid_source=dict(blkid=blkid,sgdisk=gpt))
        value=subprocess.check_output(blkid,text=True,timeout=10)
        observations.note('blkid GUID read',blkid_output=value)
        gpt_value=subprocess.check_output(gpt,text=True,timeout=10)
        guid=expected_guid(value,gpt_value,observations)
        host=LoopHost({target:'TARGET',protected:'KEEP'},efi,guid,observations)
        observations.note('before real disk_record')
        record=owner.disk_record(host,dict(target='TARGET',protected='KEEP'))
        observations.note('disk_record returned',disk_record_resolved_guid=record['esp_guid'],disk_record_returned_guid=record['esp_guid'])
        found=owner.media_module().find(host,owner.require)
        observations.note('media.find returned',found=found)
        observations.check(record['esp_guid'].lower()==guid.lower() and found['volume']['path']==target+'p2','STOP: helper EFI/tools identity mismatch')
        observations.check(found['disk']['path']==target and found['volume']['uuid'],'STOP: helper tools disk/UUID mismatch')
        observations.check(record['target']['children'][0]['parttype'].lower()=='c12a7328-f81f-11d2-ba4b-00a0c93ec93b','STOP: helper EFI type mismatch')
        mounted=owner.mount_record(host,'--target',tools)
        observations.note('tools mount returned',tools_mount=mounted)
        observations.check(mounted['source']==target+'p2' and mounted['fstype']=='fuseblk','STOP: tools FUSE mount mismatch')
        observations.check(all(row['type']=='loop' and row.get('children') for tree in host.raw_trees for row in tree),'STOP: raw loop tree mismatch')
        protected_mount=directory/'protected-mount'
        protected_mount.mkdir()
        cleanup.callback(owner_fuse.unmount,protected+'p1',protected_mount)
        run('mount','-t','vfat','-o','ro,nodev,nosuid,noexec',protected+'p1',str(protected_mount))
        mounted=mounted_child(host,protected,directory,observations)
        protected_after=owner_media.digest(protected_image)
        observations.note('protected fixture comparison',protected_before=protected_before,protected_after=protected_after)
        observations.check(protected_after==protected_before,'STOP: protected fixture changed')
        result=dict(status='passed',sha=os.environ['GITHUB_SHA'],native_queries=host.native.trace,
            raw_loop_trees=host.raw_trees, helper_mutations=0, loop_backing_verified=True, protected_fixture_unchanged=True,
            mounted_child=mounted,
            adapters=['loop root TYPE/serial/USB/removability only; no tree/partition reshaping',
                      'guest mountpoint arguments map to one scratch FAT mount; returned TARGET maps back',
                      'install findmnt FUSE type maps to the independently queried native exFAT volume type',
                      'private bootstrap HOME maps to the read-only target ESP; photographed serial input supplied by fixture',
                      'synthetic firmware read naming the native EFI PARTUUID; no firmware access'])
    mounts_after=mount_snapshot()
    observations.check(mounts_after==mounts_before,'STOP: fixture mounts remain after cleanup')
    result['all_fixture_mounts_unmounted_and_loops_detached']=True
    result['cleanup']=dict(status='passed',mounts_before=mounts_before,mounts_after=mounts_after,
        fixture_mounts_remaining=[],fixture_loops_remaining=[])
    hashes=[owner_media.digest(directory/(name+'.raw')) for name in ('target','protected')]
    observations.check(hashes==mounted['before']['hashes'],'STOP: fixture image changed during cleanup')
    result['cleanup']['image_hashes_after_detach']=hashes
    observations.note('complete',**result)
    return result


def main():
    observations=Observations(EVIDENCE)
    try:
        observations.note('before authorized-runner assertions')
        owner_media.require_runner()
        observations.check(os.geteuid()==0 and os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch','STOP: privileged dispatch fixture only')
        # owner_media.require_runner() allows update only for package 27's branch.
        observations.check(os.environ.get('REHEARSAL_MODE') in ('probe','owner-tools','update','reorder-probe'),'STOP: unauthorized fixture mode')
        prove(WORK/'14-native-owner-devices',observations)
    except BaseException as error:
        observations.failed(error)
        raise
    print('PASS native partitioned-loop lsblk/findmnt queries and real owner disk/media helpers; cleanup confirmed')
    print('PASS native mounted protected child: Protected disk is mounted; zero mutations (both image hashes, partition tables, mounts and target files unchanged); missing-check stand-in rejected')
    print('PASS cleanup: protected child and target mounts unmounted; backing-verified loops detached; no fixture mounts or loops remain')


if __name__=='__main__': main()
