"""One explicit FUSE exFAT path for disposable runner files; no fallback."""
import json
import pathlib
import subprocess


def mounts(option, value):
    result = subprocess.run(['findmnt', '--json', option, str(value), '--output',
                             'SOURCE,TARGET,FSTYPE,VFS-OPTIONS'], capture_output=True, text=True, timeout=10)
    assert result.returncode in (0, 1), 'STOP: cannot determine mount state'
    assert not result.stderr.strip(), 'STOP: mount query reported a diagnostic'
    if result.returncode == 1:
        assert not result.stdout.strip(), 'STOP: ambiguous absent mount'
        return []
    rows = json.loads(result.stdout)['filesystems']
    assert rows, 'STOP: empty successful mount query'
    return rows


def identity(partition, target):
    rows = mounts('--mountpoint', target)
    assert len(rows) == 1, 'STOP: missing or ambiguous FUSE mount'
    row, = rows
    assert row['source'] == partition and pathlib.Path(row['target']) == target, 'STOP: wrong FUSE mount identity'
    assert row['fstype'] == 'fuseblk', 'STOP: expected block-device FUSE filesystem'
    kind = subprocess.check_output(['blkid', '--probe', '--output', 'value', '--match-tag', 'TYPE', partition],
                                   text=True, timeout=10).strip()
    assert kind == 'exfat', 'STOP: FUSE source is not exFAT'
    return row


def mount(partition, target, readonly=False):
    assert not mounts('--mountpoint', target), 'STOP: mountpoint already occupied'
    mode = 'ro' if readonly else 'rw'
    options = mode + ',nodev,nosuid,noexec'
    subprocess.run(['mount.exfat-fuse', '-o', options, partition, str(target)], check=True, timeout=30)
    identity(partition, target)
    # Upstream passes only selected -o options through to libfuse. Apply the
    # VFS flags to this already-identified FUSE mount; never invoke an FS helper
    # or try a kernel exFAT mount. No volume content is written before checking.
    subprocess.run(['mount', '--internal-only', '-o', 'remount,bind,' + options,
                    str(target), str(target)], check=True, timeout=10)
    row = identity(partition, target)
    flags = set(row['vfs-options'].split(','))
    assert {mode, 'nodev', 'nosuid', 'noexec'} <= flags, 'STOP: unsafe FUSE mount flags'
    assert ('rw' if readonly else 'ro') not in flags, 'STOP: wrong FUSE access mode'
    return row


def unmount(partition, target):
    rows = mounts('--mountpoint', target)
    if rows:
        assert len(rows) == 1 and rows[0]['source'] == partition, 'STOP: refuse to unmount another source'
        subprocess.run(['umount', str(target)], check=True, timeout=30)
    assert not mounts('--mountpoint', target), 'STOP: unmount did not complete'
    assert not mounts('--source', partition), 'STOP: loop partition remains mounted'


def detach(loop, target):
    # Confirmation errors deliberately prevent detach, including on failures.
    unmount(loop + 'p1', target)
    subprocess.run(['losetup', '--detach', loop], check=True, timeout=10)


def check(partition):
    assert not mounts('--source', partition), 'STOP: refuse fsck on a mounted partition'
    subprocess.run(['fsck.exfat', '-n', partition], check=True, timeout=30)
