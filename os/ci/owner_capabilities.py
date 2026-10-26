"""Early native host smoke check. Only fresh disposable runner files are used."""
import errno
import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import time

import owner_fuse
import owner_media
import prepare_two_disks as fixture
from qmp import QMP

STEP = 'Prove package 14 native host capabilities before expensive downloads'
CHECKS = ('loop', 'fuse_exfat_rw', 'unmount_confirmed', 'fsck_readonly', 'fuse_exfat_ro',
          'readonly_write_refused', 'fixture_tools', 'qemu_ovmf', 'qmp', 'usb_hotplug',
          'serial_sockets', 'network_link_control', 'screenshot', 'keyboard')


def exfat(directory):
    image, target = directory / 'exfat.raw', directory / 'fuse'
    target.mkdir()
    with image.open('xb') as stream:
        stream.truncate(64 * 1024 ** 2)
    subprocess.run(['sgdisk', '--clear', '--new=1:2048:0', '--typecode=1:0700', str(image)], check=True, timeout=10)
    payload = bytes(range(256)) * 16
    for readonly in (False, True):
        args = ['losetup', '--find', '--show', '--partscan'] + (['--read-only'] if readonly else [])
        loop = subprocess.check_output([*args, str(image)], text=True, timeout=10).strip()
        try:
            fixture.verify_loop(loop, image)
            fixture.wait_loop_partitions(loop,image)
            if readonly:
                owner_fuse.check(loop + 'p1')
            else:
                subprocess.run(['mkfs.exfat', '-L', 'ARES_CAP', loop + 'p1'], check=True, timeout=30)
            owner_fuse.mount(loop + 'p1', target, readonly=readonly)
            if readonly:
                assert (target / 'proof.bin').read_bytes() == payload, 'STOP: FUSE readback differs'
                try:
                    with (target / 'must-refuse').open('xb'):
                        pass
                except OSError as error:
                    assert error.errno == errno.EROFS, 'STOP: unexpected read-only failure'
                else:
                    raise AssertionError('STOP: read-only FUSE mount accepted a write')
            else:
                (target / 'proof.bin').write_bytes(payload)
                subprocess.run(['sync', '-f', str(target)], check=True, timeout=30)
        finally:
            owner_fuse.detach(loop, target)
    return image


def connect(path, process):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        assert process.poll() is None, 'STOP: QEMU capability process exited'
        sock = socket.socket(socket.AF_UNIX)
        try:
            sock.connect(str(path))
            return sock
        except (FileNotFoundError, ConnectionRefusedError):
            sock.close()
            time.sleep(0.1)
    raise TimeoutError('STOP: QEMU capability socket did not appear')


def qemu(directory, image):
    # Exercise the exact existing file-fixture builder early, including EFI
    # compilation, GPT, FAT, NTFS and verified loop backing. No OS ISO is needed.
    previous = fixture.WORK
    fixture.WORK = directory
    try:
        fixture.main()
    finally:
        fixture.WORK = previous
    accel = ['-accel', 'kvm', '-cpu', 'host'] if os.access('/dev/kvm', os.R_OK | os.W_OK) else ['-accel', 'tcg,thread=multi', '-cpu', 'max']
    argv = ['qemu-system-x86_64', '-machine', 'q35', *accel, '-m', '6144', '-smp', '2',
        '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
        '-drive', f'if=pflash,format=raw,file={directory / "vars.fd"}',
        '-drive', f'if=none,id=protected,format=raw,readonly=on,file={directory / "protected.raw"}',
        '-device', 'virtio-blk-pci,drive=protected,id=protected-device,addr=0x3',
        '-drive', f'if=none,id=target,format=raw,file={directory / "target.raw"}',
        '-device', 'virtio-blk-pci,drive=target,id=target-device,addr=0x2',
        '-device', 'virtio-vga,addr=0x4', '-device', 'qemu-xhci,id=usb-controller,addr=0x5',
        '-device', 'usb-kbd,bus=usb-controller.0,port=1',
        '-device', 'virtio-serial-pci,id=webui-bus,addr=0x7',
        '-chardev', f'socket,id=webui,path={directory / "webui.sock"},server=on,wait=off',
        '-device', 'virtserialport,bus=webui-bus.0,chardev=webui,name=ares.webui',
        '-nic', 'user,model=virtio-net-pci,id=owner-net', '-display', 'none',
        '-serial', f'unix:{directory / "serial.sock"},server=on,wait=off',
        '-qmp', f'unix:{directory / "qmp.sock"},server=on,wait=off',
        '-debugcon', f'file:{directory / "marker.txt"}', '-global', 'isa-debugcon.iobase=0x402', '-S', '-no-reboot']
    sockets, monitor = [], None
    with (directory / 'qemu.log').open('w') as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
        try:
            for name in ('qmp', 'serial', 'webui'):
                sockets.append(connect(directory / (name + '.sock'), process))
            monitor = QMP(sockets[0]); monitor.command('qmp_capabilities')
            monitor.command('set_link', dict(name='owner-net', up=False))
            assert monitor.command('query-status')['status'] == 'prelaunch'
            assert monitor.command('query-pci') and monitor.command('query-block')
            monitor.command('query-blockstats')
            # A toy capability device is removed while CPUs are still paused;
            # it is never visible to firmware and is not the owner's tools stick.
            monitor.command('blockdev-add', dict(driver='file', **{'node-name': 'cap-file'}, filename=str(image)))
            monitor.command('blockdev-add', dict(driver='raw', **{'node-name': 'cap-raw'}, file='cap-file'))
            monitor.command('device_add', dict(driver='usb-storage', id='cap-usb', drive='cap-raw',
                                              bus='usb-controller.0', port='2', removable=True))
            assert any(b.get('inserted', {}).get('node-name') == 'cap-raw' for b in monitor.command('query-block'))
            start = len(monitor.events); monitor.command('device_del', dict(id='cap-usb'))
            deadline = time.monotonic() + 10
            while not any(e.get('event') == 'DEVICE_DELETED' and e.get('data', {}).get('device') == 'cap-usb'
                          for e in monitor.events[start:]):
                assert time.monotonic() < deadline, 'STOP: capability USB removal deadline'
                monitor.command('query-status'); time.sleep(0.1)
            monitor.command('blockdev-del', {'node-name': 'cap-raw'})
            monitor.command('blockdev-del', {'node-name': 'cap-file'})
            monitor.command('cont')
            deadline = time.monotonic() + 45
            while not (directory / 'marker.txt').exists() or 'MARKER_BOOT_COMPLETE' not in (directory / 'marker.txt').read_text():
                assert process.poll() is None and time.monotonic() < deadline, 'STOP: OVMF marker did not boot'
                time.sleep(0.1)
            monitor.command('send-key', dict(keys=[dict(type='qcode', data='a')]))
            monitor.command('screendump', dict(filename=str(directory / 'screen.ppm')))
            assert (directory / 'screen.ppm').stat().st_size > 100, 'STOP: QMP screenshot unavailable'
            monitor.command('quit'); process.wait(timeout=10)
            assert process.returncode == 0, 'STOP: capability QEMU did not exit cleanly'
        finally:
            if process.poll() is None:
                process.kill(); process.wait(timeout=10)
            for sock in sockets:
                sock.close()
    return dict(acceleration=accel, marker_booted=True, toy_usb_removed_before_firmware=True)


def main():
    owner_media.require_runner()
    assert os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
    assert os.environ.get('REHEARSAL_MODE') in ('probe', 'owner-tools')
    base = pathlib.Path('.work').resolve()
    directory = base / '14-host-capabilities'
    assert directory.parent == base and not directory.exists(), 'STOP: fresh capability directory required'
    needed = ('mount.exfat-fuse', 'mkfs.exfat', 'fsck.exfat', 'findmnt', 'blkid', 'mount', 'umount',
              'losetup', 'sgdisk', 'udevadm', 'partx', 'qemu-system-x86_64', 'pwsh', 'tesseract', 'ntfs-3g')
    for name in needed:
        assert shutil.which(name), 'STOP: missing host capability tool ' + name
    directory.mkdir()
    try:
        image = exfat(directory)
        observed = qemu(directory, image)
    finally:
        log = directory / 'qemu.log'
        if log.exists():
            shutil.copyfile(log, 'evidence/14-capability-qemu.log')
    proof = dict(status='passed', sha=os.environ['GITHUB_SHA'], checks={name: True for name in CHECKS},
                 qemu=observed, exfat=dict(sha256=owner_media.digest(image), path=str(image.relative_to(pathlib.Path.cwd()))),
                 ovmf=[dict(sha256=hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(), path=p) for p in
                       ('/usr/share/OVMF/OVMF_CODE_4M.fd', '/usr/share/OVMF/OVMF_VARS_4M.fd')])
    pathlib.Path('evidence/14-host-capabilities.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('PASS native loop/FUSE exFAT rw/ro/fsck, fixture tools, QEMU/OVMF/QMP; no OS ISO or owner device')


if __name__ == '__main__':
    main()
