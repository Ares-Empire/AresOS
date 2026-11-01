"""Ordinary-directory volume stand-in. Never invokes a host tool or device."""
import json
import pathlib
import shutil
import subprocess
from unittest.mock import patch

import prepare_two_disks as loops


class Volume:
    def __init__(self, root, mount):
        self.root, self.mount = root, mount
        self.volume = root / 'volume'; self.volume.mkdir()
        self.active, self.readonly = False, False
        self.flags = set()
        self.calls = []
        self.loop = '/dev/loop99'
        self.image = None
        self.fstype, self.kind, self.source = 'fuseblk', 'exfat', self.loop + 'p1'
        self.bad_flags = self.linger = self.corrupt = self.fsck_failure = False

    def patch_nodes(self, stack):
        def layout(image):
            return dict(partitions=[dict(number=1,start_lba=2048,end_lba=image.stat().st_size//512-34)])
        def state(loop,number):
            assert loop==self.loop and number==1
            row=layout(pathlib.Path(self.image))['partitions'][0]
            return dict(node=loop+'p1',block=True,start=row['start_lba'],size=row['end_lba']-row['start_lba']+1,
                        dev='7:99',rdev='7:99')
        stack.enter_context(patch.object(loops,'gpt',side_effect=layout))
        stack.enter_context(patch.object(loops,'loop_partition_state',side_effect=state))

    def run(self, argv, **kwargs):
        self.calls.append(argv)
        name = argv[0]
        if name == 'findmnt':
            rows = [dict(source=self.source, target=str(self.mount), fstype=self.fstype,
                         **{'vfs-options':','.join(sorted(self.flags))})] if self.active else []
            return subprocess.CompletedProcess(argv, 0 if rows else 1,
                json.dumps(dict(filesystems=rows)) if rows else '', '')
        if name == 'mount.exfat-fuse':
            assert not self.active
            self.readonly = 'ro' in argv[2].split(',')
            self.flags = {'ro' if self.readonly else 'rw'}
            self.active = True
            for p in self.volume.iterdir(): p.rename(self.mount / p.name)
        elif name == 'mount':
            assert self.active and argv[1] == '--internal-only' and argv[3].startswith('remount,bind,')
            self.flags = set(argv[3].split(',')) - {'remount', 'bind'}
            if self.bad_flags: self.flags.discard('noexec')
        elif name == 'umount':
            if not self.linger:
                for p in self.mount.iterdir(): p.rename(self.volume / p.name)
                self.active = False
                if self.corrupt and not self.readonly:
                    (self.volume / 'ares-tools/at').write_text('TAMPERED')
        elif name == 'pwsh':
            assert self.active and not self.readonly and {'rw','nodev','nosuid','noexec'} <= self.flags
            assert argv[1:3] == ['-NoProfile','-File']
            assert 'Copy-AresToolsPayload' in pathlib.Path(argv[3]).read_text()
            from owner_bundle_fixture import copy_bundle
            copy_bundle(argv[4], argv[5])
        elif name == 'fsck.exfat':
            assert not self.active and argv == ['fsck.exfat','-n',self.loop+'p1']
            if self.fsck_failure: raise subprocess.CalledProcessError(1, argv)
        elif name == 'losetup':
            assert argv == ['losetup','--detach',self.loop] and not self.active
        elif name=='udevadm':
            assert argv[1]=='settle'
        elif name=='partx':
            assert argv==['partx','--update',self.loop]
        elif name not in ('sgdisk','mkfs.exfat','sync'):
            raise AssertionError('Unwalked tool: ' + repr(argv))
        return subprocess.CompletedProcess(argv, 0)

    def output(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[0] == 'losetup':
            if '--list' in argv:
                value = json.dumps(dict(loopdevices=[{'name':self.loop,'back-file':self.image}]))
            else:
                self.image = argv[-1]; value = self.loop + '\n'
        elif argv[0] == 'blkid': value = self.kind + '\n'
        else: raise AssertionError('Unwalked output: ' + repr(argv))
        return value if kwargs.get('text') else value.encode()
