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
import subprocess

import owner_fuse
import owner_media
from prepare_two_disks import verify_loop

owner = owner_media.bundle_module('owner')
WORK = pathlib.Path('.work').resolve()


class LoopHost:
    def __init__(self, loops, efi, guid):
        self.native = owner.Host()
        self.loops, self.efi, self.guid = loops, efi, guid
        self.raw_trees = []

    def read(self, *command, **kwargs):
        if command == ('efibootmgr','-v'):
            return 'Boot0001* Fixture Linux HD(1,GPT,'+self.guid+',0x800,0x20000)/File(\\EFI\\fedora\\shimx64.efi)'
        native = list(command)
        if command[0] == 'findmnt' and command[3] == '--mountpoint':
            native[4] = str(self.efi)
        raw = self.native.read(*native, **kwargs)
        if command[0] == 'lsblk':
            value = json.loads(raw)
            # Keep orphan partition rows too: a flat native result must fail,
            # rather than becoming a plausible but incomplete root-only list.
            rows = [row for row in value['blockdevices'] if any(
                row['path'] == loop or row['path'].startswith(loop+'p') for loop in self.loops)]
            self.raw_trees.append(copy.deepcopy(rows))
            for row in rows:
                if row['path'] in self.loops:
                    assert row['type'] == 'loop', 'STOP: native fixture did not receive a loop root'
                    row.update(type='disk',serial=self.loops[row['path']],tran='usb',rm=True)
            return json.dumps(dict(blockdevices=rows))
        if command[0] == 'findmnt' and command[3] == '--mountpoint':
            value = json.loads(raw)
            for row in value['filesystems']:
                assert row['target'] == str(self.efi), 'STOP: wrong sandbox mount'
                row['target'] = command[4]
            return json.dumps(value)
        return raw

    def json(self, *command): return json.loads(self.read(*command))

    def mutate(self, *command, **kwargs):
        raise AssertionError('STOP: disk/media readers attempted a mutation')


def run(*command):
    subprocess.run(list(command),check=True,timeout=30)


def detach(loop, image, parts):
    verify_loop(loop,image)
    for number in range(1,parts+1):
        assert not owner_fuse.mounts('--source',loop+'p'+str(number)), 'STOP: fixture partition remains mounted'
    run('losetup','--detach',loop)


def prove(directory):
    directory = pathlib.Path(directory).resolve()
    assert not directory.exists() and directory.parent == WORK, 'STOP: fresh workspace fixture required'
    directory.mkdir()
    with contextlib.ExitStack() as cleanup:
        loops = []
        for name, parts, size in (('target',2,160),('protected',1,32)):
            image=directory/(name+'.raw')
            with image.open('xb') as stream: stream.truncate(size*1024**2)
            args=['sgdisk','--clear','--new=1:2048:+64M','--typecode=1:ef00',
                  '--new=2:0:0','--typecode=2:0700',str(image)] if parts==2 else [
                  'sgdisk','--clear','--new=1:2048:0','--typecode=1:0700',str(image)]
            run(*args)
            loop=subprocess.check_output(['losetup','--find','--show','--partscan',str(image)],text=True,timeout=10).strip()
            verify_loop(loop,image)
            cleanup.callback(detach,loop,image,parts)
            loops.append(loop)
        run('udevadm','settle')
        target, protected = loops
        protected_image=directory/'protected.raw'
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
        owner_fuse.mount(target+'p2',tools,readonly=True)
        guid=subprocess.check_output(['blkid','--probe','--output','value','--match-tag','PARTUUID',target+'p1'],text=True,timeout=10).strip()
        host=LoopHost({target:'TARGET',protected:'KEEP'},efi,guid)
        record=owner.disk_record(host,dict(target='TARGET',protected='KEEP'))
        found=owner.media_module().find(host,owner.require)
        assert record['esp_guid'] == guid and found['volume']['path'] == target+'p2'
        assert found['disk']['path'] == target and found['volume']['uuid']
        assert record['target']['children'][0]['parttype'].lower() == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b'
        mounted=owner.mount_record(host,'--target',tools)
        assert mounted['source'] == target+'p2' and mounted['fstype'] == 'fuseblk'
        assert all(row['type']=='loop' and row.get('children') for tree in host.raw_trees for row in tree)
        assert owner_media.digest(protected_image)==protected_before, 'STOP: protected fixture changed'
        result=dict(status='passed',sha=os.environ['GITHUB_SHA'],native_queries=host.native.trace,
            raw_loop_trees=host.raw_trees, helper_mutations=0, loop_backing_verified=True, protected_fixture_unchanged=True,
            adapters=['loop root TYPE/serial/USB/removability only; no tree/partition reshaping',
                      'guest mountpoint arguments map to one scratch FAT mount; returned TARGET maps back',
                      'synthetic firmware read naming the native EFI PARTUUID; no firmware access'])
    result['all_fixture_mounts_unmounted_and_loops_detached']=True
    return result


def main():
    owner_media.require_runner()
    assert os.geteuid()==0 and os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch'
    assert os.environ.get('REHEARSAL_MODE') in ('probe','owner-tools')
    proof=prove(WORK/'14-native-owner-devices')
    pathlib.Path('evidence/14-native-owner-devices.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('PASS native partitioned-loop lsblk/findmnt queries and real owner disk/media helpers; cleanup confirmed')


if __name__=='__main__': main()
