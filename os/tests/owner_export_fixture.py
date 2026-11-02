"""Fresh-process owner CLI fixture; no real host commands or privileged writes.

Only the filesystem root prefix is relocated. HOME, STOP_RECORDS, media.MOUNT,
the dispatcher, refusal recorder, private-file checks, export and readback all
run unchanged. Root/POSIX metadata and the removable device/mount operations
are explicit stand-ins on unprivileged DrvFS; payload bytes are never edited.
"""
import contextlib
import json
import os
import pathlib
import runpy
import stat
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


def main():
    real_path = pathlib.Path
    root = real_path(sys.argv[1]).resolve()
    repository = real_path(__file__).resolve().parents[2]
    assert root.is_relative_to(repository / 'os/tests') and root.is_dir()
    assert not any(p.is_symlink() for p in [root, *root.rglob('*')])
    command = sys.argv[2:]
    payload = root / 'var/lib/ares/tools'
    usb, mount = root / 'fixture-stick', root / 'run/ares-tools-media'
    mounted = False

    class RootPath(type(root)):
        def __new__(cls, *parts):
            if sys.version_info >= (3, 12):
                return object.__new__(cls)
            return cls._from_parts(cls.mapped(parts).parts)

        @staticmethod
        def mapped(parts):
            path = real_path(*parts)
            if path.is_absolute() and not path.is_relative_to(root):
                path = root / path.relative_to('/')
            return path

        def __init__(self, *parts):
            if sys.version_info >= (3, 12):
                super().__init__(self.mapped(parts))

    original_stat = real_path.stat

    def metadata(path, *args, **kwargs):
        info = original_stat(path, *args, **kwargs)
        if path.is_relative_to(root) and not stat.S_ISLNK(info.st_mode):
            values = {name: getattr(info, name) for name in dir(info) if name.startswith('st_')}
            values.update(st_uid=0, st_mode=stat.S_IFMT(info.st_mode) |
                          (0o700 if stat.S_ISDIR(info.st_mode) or path.name == 'at' else 0o600))
            return SimpleNamespace(**values)
        return info

    def tool(name, **kwargs):
        assert name in ('efibootmgr', 'lsblk', 'mount', 'umount', 'sync'), name
        return '/usr/bin/' + name

    def run(argv, **kwargs):
        nonlocal mounted
        name, *args = argv
        name = real_path(name).name
        output = ''
        if name == 'efibootmgr':
            assert args == ['-v']
            output = 'BootCurrent: 0001\n'
        elif name == 'lsblk':
            assert args == ['--json', '--tree', '--paths', '--output',
                            'PATH,TYPE,TRAN,RM,LABEL,FSTYPE,UUID,MOUNTPOINTS']
            output = json.dumps(dict(blockdevices=[dict(path='/dev/SYNTHETIC', type='disk',
                tran='usb', rm=True, mountpoints=[None], children=[dict(path='/dev/SYNTHETIC1',
                type='part', label='ARESTOOLS', fstype='exfat', uuid='fixture-stick',
                mountpoints=[str(mount)] if mounted else [None])])]))
        elif name == 'mount':
            assert args in (['--read-only', '-o', 'nodev,nosuid,noexec', '--', '/dev/SYNTHETIC1', str(mount)],
                            ['-o', 'nodev,nosuid,noexec', '--', '/dev/SYNTHETIC1', str(mount)])
            assert not mounted and not any(mount.iterdir())
            mount.rmdir()
            usb.rename(mount)
            mounted = True
        elif name == 'umount':
            assert args == ['--', str(mount)] and mounted
            mount.rename(usb)
            mount.mkdir()
            mounted = False
        elif name == 'sync':
            assert args == ['-f', str(mount / 'ares-records')] and mounted
        else:
            raise AssertionError('Real host command prohibited: ' + repr(argv))
        with (root / 'host-calls.jsonl').open('a') as stream:
            stream.write(json.dumps(argv) + '\n')
        return subprocess.CompletedProcess(argv, 0, output, '')

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(pathlib, 'Path', RootPath))
        stack.enter_context(patch.object(real_path, 'stat', metadata))
        stack.enter_context(patch.object(os, 'geteuid', return_value=0))
        stack.enter_context(patch('shutil.which', side_effect=tool))
        stack.enter_context(patch.object(subprocess, 'run', side_effect=run))
        stack.enter_context(patch.object(sys, 'argv', [str(payload / 'owner.py'), *command]))
        runpy.run_path(str(payload / 'owner.py'), run_name='__main__')
    assert not mounted, 'Owner export left the fixture stick mounted'


if __name__ == '__main__':
    main()
