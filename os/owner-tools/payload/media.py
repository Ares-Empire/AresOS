"""Tools-stick access after login only. Never called during a boot or reboot.

Mounts are inspection/data access to the uniquely labelled removable USB;
there is no partitioning, formatting, firmware or deployment operation here.
"""
import hashlib
import pathlib
import shutil

LABEL = 'ARESTOOLS'
MOUNT = pathlib.Path('/run/ares-tools-media')


def block_tree(host, require, *options):
    tree = host.json('lsblk', '--json', '--tree', *options)
    message = 'Unexpected lsblk tree shape; STOP rather than infer disk ancestry'
    require(isinstance(tree, dict) and isinstance(tree.get('blockdevices'), list), message)
    seen = set()

    def visit(row, parent=None):
        require(isinstance(row, dict), message)
        path, kind = row.get('path'), row.get('type')
        require(isinstance(path, str) and path.startswith('/dev/') and path not in seen, message)
        seen.add(path)
        require(isinstance(kind, str) and kind, message)
        if parent is None:
            # Live media can expose a read-only loop or optical root as well
            # as disks. A partition is never an independent top-level device.
            require(kind in ('disk', 'loop', 'rom'), message)
        else:
            require(kind not in ('disk', 'loop', 'rom'), message)
            if kind == 'part':
                require(parent['type'] in ('disk', 'loop'), message)
        mounts, children = row.get('mountpoints'), row.get('children', [])
        require(isinstance(mounts, list) and all(m is None or isinstance(m, str) for m in mounts), message)
        require(isinstance(children, list), message)
        for child in children:
            visit(child, row)

    for disk in tree['blockdevices']:
        visit(disk)
    return tree


def find(host, require):
    tree = block_tree(host, require, '--paths', '--output', 'PATH,TYPE,TRAN,RM,LABEL,FSTYPE,UUID,MOUNTPOINTS')
    found = []
    for disk in tree['blockdevices']:
        def visit(row):
            if row.get('label') == LABEL:
                found.append((disk, row))
            for child in row.get('children', []):
                visit(child)
        visit(disk)
    require(len(found) <= 1, 'Several ARESTOOLS labels; unplug all USBs and get help')
    if not found:
        return None
    disk, volume = found[0]
    require(disk.get('tran') == 'usb' and disk.get('rm') in (True, 1)
        and volume.get('fstype') == 'exfat' and volume.get('uuid')
        and volume['type'] in ('part', 'disk'), 'ARESTOOLS is not an identifiable removable exFAT USB')
    return dict(disk=disk, volume=volume)


def export(host, store, fingerprint, checked_bundle, require):
    device = find(host, require)
    if device is None:
        return ['Tools stick absent; full records remain internal']
    volume = device['volume']
    existing = [m for m in volume.get('mountpoints', []) if m]
    require(len(existing) <= 1, 'Tools stick has several mounts; close its users and get help')
    if existing:
        root = pathlib.Path(existing[0])
        require(checked_bundle(root / 'ares-tools') == fingerprint, 'Mounted tools bundle differs')
        host.mutate('umount', '--', str(root))
    require(not MOUNT.is_symlink() and not MOUNT.is_mount(), 'Tools mount point is already in use')
    MOUNT.mkdir(mode=0o700, exist_ok=True)
    require(not any(MOUNT.iterdir()), 'Tools mount directory is not empty')
    mounted = False
    def inspect_records():
        destination = MOUNT / 'ares-records'
        require(not destination.is_symlink() and (not destination.exists() or destination.is_dir()), 'USB records path is not a directory')
        paths = sorted(store.glob('*.json'))
        for path in paths:
            require(path.is_file() and not path.is_symlink(), 'Private record is not an ordinary file')
            target = destination / path.name
            require(not target.is_symlink() and (not target.exists() or target.is_file()), 'USB record is not an ordinary file')
            if target.exists():
                require(target.read_bytes() == path.read_bytes() or path.name in
                    ('title.json', 'record-c.json', 'layout-pending.json', 'layout-completed.json'),
                    'USB has a different immutable record; preserve both and get help')
        return destination, paths
    try:
        # Inspect read-only first; no exFAT data is changed on a bad manifest.
        host.mutate('mount', '--read-only', '-o', 'nodev,nosuid,noexec', '--', volume['path'], str(MOUNT))
        mounted = True
        require(checked_bundle(MOUNT / 'ares-tools') == fingerprint, 'Tools manifest differs; do not copy records')
        inspect_records()
        host.mutate('umount', '--', str(MOUNT))
        mounted = False
        host.mutate('mount', '-o', 'nodev,nosuid,noexec', '--', volume['path'], str(MOUNT))
        mounted = True
        require(checked_bundle(MOUNT / 'ares-tools') == fingerprint, 'Tools bundle changed between mounts')
        destination, paths = inspect_records()
        destination.mkdir(exist_ok=True)
        for path in paths:
            target = destination / path.name
            shutil.copyfile(path, target)
            require(hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(path.read_bytes()).digest(), 'USB record copy differs')
        host.mutate('sync', '-f', str(destination))
    finally:
        if mounted:
            host.mutate('umount', '--', str(MOUNT))
    after = find(host, require)
    require(after and after['volume']['uuid'] == volume['uuid'] and
        not any(after['volume'].get('mountpoints', [])), 'Stick is not fully unmounted; do not remove it')
    return ['Records copied with SHA256 readback', 'SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart']
