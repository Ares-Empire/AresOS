"""Ordinary-directory volume stand-in. Never invokes a host tool or device."""
import json
import pathlib
import shutil
import subprocess


class Volume:
    def __init__(self, root, mount):
        self.root, self.mount = root, mount
        self.volume = root / 'volume'; self.volume.mkdir()
        self.active, self.readonly = False, False
        self.flags = set()
        self.calls = []
        self.loop = '/dev/loopSYNTHETIC'
        self.image = None
        self.fstype, self.kind, self.source = 'fuseblk', 'exfat', self.loop + 'p1'
        self.bad_flags = self.linger = self.corrupt = self.fsck_failure = False

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
            shutil.copytree(argv[4], argv[5])
        elif name == 'fsck.exfat':
            assert not self.active and argv == ['fsck.exfat','-n',self.loop+'p1']
            if self.fsck_failure: raise subprocess.CalledProcessError(1, argv)
        elif name == 'losetup':
            assert argv == ['losetup','--detach',self.loop] and not self.active
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
