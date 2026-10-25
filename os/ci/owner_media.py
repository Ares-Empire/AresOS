"""File-backed exFAT tools stick populated by the Windows copy implementation.

Only the authorized hosted runner may create/mount the image. QMP hotplug is
after login; firmware inventories and their decoder are deliberately unchanged.
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import time

import two_disk_vm as td
from prepare_two_disks import verify_loop


def bundle_module(name):
    spec = importlib.util.spec_from_file_location('owner_' + name, pathlib.Path('os/owner-tools') / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require_runner():
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'Ares-Empire/AresOS'
    assert os.environ.get('GITHUB_REF_NAME') == 'pkg/14-owner-tools'
    assert os.environ.get('REHEARSAL_PACKAGE') == '14'


class Media:
    def __init__(self):
        require_runner()
        self.path = td.WORK / 'owner-tools.raw'
        self.payload = td.WORK / 'owner-payload'
        self.mount = td.WORK / 'owner-media-mount'
        self.expected = None
        self.attached = False
        self.fingerprint = None

    def mounted(self, readonly=False):
        require_runner()
        assert self.path.resolve().is_relative_to(td.WORK) and self.path.is_file() and not self.path.is_symlink()
        command = ['losetup', '--find', '--show', '--partscan']
        if readonly:
            command.append('--read-only')
        loop = subprocess.check_output([*command, str(self.path)], text=True).strip()
        verify_loop(loop, self.path)
        self.mount.mkdir(exist_ok=True)
        assert not self.mount.is_symlink() and not any(self.mount.iterdir())
        return loop

    def create(self):
        assert not self.path.exists() and not self.payload.exists()
        self.fingerprint = bundle_module('bundle').build(self.payload)
        with self.path.open('xb') as output:
            output.truncate(128 * 1024 ** 2)
        subprocess.run(['sgdisk', '--clear', '--new=1:2048:0', '--typecode=1:0700', str(self.path)], check=True)
        loop = self.mounted()
        mounted = False
        try:
            subprocess.run(['mkfs.exfat', '-L', 'ARESTOOLS', loop + 'p1'], check=True)
            subprocess.run(['mount', '-t', 'exfat', '-o', 'nodev,nosuid,noexec', loop + 'p1', str(self.mount)], check=True)
            mounted = True
            script = '''param($Source,$Destination,$Root)
Import-Module ./docs/install-tools/OwnerTools.psm1 -Force
$drive=@{Letter='T';DriveType='Removable';BusType='USB';IsBoot=$false;IsSystem=$false;
Serial='VIRTUAL-TOOLS';FileSystem='exFAT';Root=$Root}
Copy-AresToolsPayload -Source $Source -Destination $Destination -Drive $drive
'''
            path = td.WORK / 'copy-owner-tools.ps1'
            path.write_text(script)
            subprocess.run(['pwsh', '-NoProfile', '-File', str(path), str(self.payload), str(self.mount / 'ares-tools'), str(self.mount)], check=True)
            assert bundle_module('owner').checked_bundle(self.mount / 'ares-tools') == self.fingerprint
            subprocess.run(['sync', '-f', str(self.mount)], check=True)
        finally:
            if mounted:
                subprocess.run(['umount', str(self.mount)], check=True)
            subprocess.run(['losetup', '--detach', loop], check=True)
        self.expected = digest(self.path)
        td.save('tools-stick-windows-copy', dict(status='passed', image_sha256=self.expected,
            manifest_sha256=self.fingerprint, source='Copy-AresToolsPayload in OwnerTools.psm1',
            filesystem='exFAT', label='ARESTOOLS', file_backed=True, real_hardware=False))

    def verify(self, stage):
        assert not self.attached
        loop = self.mounted(readonly=True)
        mounted = False
        try:
            subprocess.run(['mount', '-t', 'exfat', '-o', 'ro,nodev,nosuid,noexec', loop + 'p1', str(self.mount)], check=True)
            mounted = True
            assert bundle_module('owner').checked_bundle(self.mount / 'ares-tools') == self.fingerprint
            records = self.mount / 'ares-records'
            if records.exists():
                destination = td.EVIDENCE / 'owner-records'
                destination.mkdir(exist_ok=True)
                for source in records.iterdir():
                    assert source.is_file() and not source.is_symlink() and source.suffix == '.json'
                    data = source.read_bytes()
                    json.loads(data)
                    secret = os.environ.get('GH_TOKEN', '').encode()
                    assert not secret or secret not in data, 'STOP: credential in record export; do not upload'
                    shutil.copyfile(source, destination / source.name)
        finally:
            if mounted:
                subprocess.run(['umount', str(self.mount)], check=True)
            subprocess.run(['losetup', '--detach', loop], check=True)
        self.expected = digest(self.path)
        td.save(stage + '-media-backing', dict(status='passed', image_sha256=self.expected,
            bundle_unchanged=True, manifest_sha256=self.fingerprint, device_attached=False))

    def attach(self, guest, stage):
        assert not self.attached and digest(self.path) == self.expected
        assert getattr(guest, 'owner_signed_in', False), 'Hotplug only after boot and sign-in'
        assert guest.mode == 'live' or getattr(guest, 'owner_physical_signed_in', False)
        guest.monitor.command('blockdev-add', {'driver': 'file', 'node-name': 'owner-tools-file', 'filename': str(self.path)})
        guest.monitor.command('blockdev-add', {'driver': 'raw', 'node-name': 'owner-tools', 'file': 'owner-tools-file'})
        guest.monitor.command('device_add', {'driver': 'usb-storage', 'id': 'owner-tools-usb', 'drive': 'owner-tools',
            'bus': 'usb-controller.0', 'port': '2', 'removable': True})
        self.attached = True
        guest.owner_media = self
        blocks = guest.monitor.command('query-block')
        matching = [b for b in blocks if b.get('inserted', {}).get('node-name') == 'owner-tools']
        assert len(matching) == 1 and pathlib.Path(matching[0]['inserted']['file']).resolve() == self.path
        seen = guest.capture_json(stage + '-media-hotplug', td.sw.framed('''python3 - <<'PY'
import json,subprocess,time
for attempt in range(60):
    value=json.loads(subprocess.check_output(['lsblk','--json','--paths','--output','PATH,TYPE,TRAN,RM,LABEL,FSTYPE,UUID,MOUNTPOINTS']))
    if 'ARESTOOLS' in json.dumps(value):
        print(json.dumps(value));break
    time.sleep(1)
else: raise SystemExit('Tools stick did not appear')
PY'''))
        assert 'ARESTOOLS' in json.dumps(seen)
        td.save(stage + '-media-attach', dict(status='passed', after_login=True, image_sha256=self.expected,
            manifest_sha256=self.fingerprint, qmp_blocks=blocks, boot=guest.boot_number))

    def detach(self, guest, stage):
        assert self.attached
        guest.command(stage + '-media-unmounted', '''set -e
python3 - <<'PY'
import json,subprocess
tree=json.loads(subprocess.check_output(['lsblk','--json','--paths','--output','PATH,LABEL,MOUNTPOINTS']))
def rows(node):
    yield node
    for child in node.get('children',[]): yield from rows(child)
matched=[r for d in tree['blockdevices'] for r in rows(d) if r.get('label')=='ARESTOOLS']
assert len(matched)==1 and not any(matched[0].get('mountpoints',[])), 'Tools USB is still mounted'
print('TOOLS_USB_UNMOUNTED')
PY''')
        start = len(guest.monitor.events)
        guest.monitor.command('device_del', {'id': 'owner-tools-usb'})
        deadline = time.monotonic() + 30
        while not any(e.get('event') == 'DEVICE_DELETED' and e.get('data', {}).get('device') == 'owner-tools-usb'
                      for e in guest.monitor.events[start:]):
            assert time.monotonic() < deadline, 'QMP tools detach deadline'
            guest.monitor.command('query-status')
            time.sleep(0.1)
        guest.monitor.command('blockdev-del', {'node-name': 'owner-tools'})
        guest.monitor.command('blockdev-del', {'node-name': 'owner-tools-file'})
        self.attached = False
        guest.command(stage + '-media-gone', '''set -e
for n in {1..30}; do
    if test -z "$(lsblk -nr -o LABEL | grep -x ARESTOOLS || true)"; then echo TOOLS_USB_GONE_BEFORE_REBOOT; exit 0; fi
    sleep 1
done
exit 1''')
        guest.devices = guest.device_inventory()
        td.save(stage + '-media-detach', dict(status='passed', qmp_events=guest.monitor.events[start:],
            absent_before_shutdown=True, boot=guest.boot_number))
        self.verify(stage)
