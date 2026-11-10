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
import owner_fuse
from prepare_two_disks import verify_loop, wait_loop_partitions


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
    assert ((os.environ.get('GITHUB_REF_NAME'),os.environ.get('REHEARSAL_PACKAGE')) == ('pkg/14-owner-tools','14') or
            (os.environ.get('GITHUB_REF_NAME'),os.environ.get('REHEARSAL_PACKAGE'),os.environ.get('REHEARSAL_MODE')) ==
            ('pkg/16-staged-release','16','probe') or
            (os.environ.get('GITHUB_REF_NAME'),os.environ.get('REHEARSAL_PACKAGE'),os.environ.get('REHEARSAL_MODE')) ==
            ('pkg/27-first-update-release','27','update'))


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
        try:
            wait_loop_partitions(loop,self.path)
            self.mount.mkdir(exist_ok=True)
            assert not self.mount.is_symlink() and not any(self.mount.iterdir())
        except BaseException:
            verify_loop(loop,self.path)
            owner_fuse.detach(loop,self.mount)
            raise
        return loop

    def create(self, source=None):
        """Format the stick and copy a bundle with the Windows helper.

        source: an existing checked bundle (package 27: the laptop's older tools)
        instead of this checkout's payload.
        """
        assert not self.path.exists() and not self.payload.exists()
        if source is None:
            self.fingerprint = bundle_module('bundle').build(self.payload)
        else:
            shutil.copytree(source, self.payload)
            self.fingerprint = bundle_module('owner').checked_bundle(self.payload)
        with self.path.open('xb') as output:
            output.truncate(128 * 1024 ** 2)
        subprocess.run(['sgdisk', '--clear', '--new=1:2048:0', '--typecode=1:0700', str(self.path)], check=True)
        loop = self.mounted()
        try:
            subprocess.run(['mkfs.exfat', '-L', 'ARESTOOLS', loop + 'p1'], check=True)
            owner_fuse.mount(loop + 'p1', self.mount)
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
            owner_fuse.detach(loop, self.mount)
        # A clean fsck and every-file readback on a read-only loop/FUSE mount
        # must pass before any backing hash can authorize QMP attachment.
        self.verify('tools-stick-created')
        td.save('tools-stick-windows-copy', dict(status='passed', image_sha256=self.expected,
            manifest_sha256=self.fingerprint, source='Copy-AresToolsPayload in OwnerTools.psm1',
            filesystem='FUSE exFAT', label='ARESTOOLS', fsck_readonly=True, readonly_bundle_verified=True,
            file_backed=True, real_hardware=False))

    def replace(self, stage):
        """Step 8's Windows side: keep the old bundle under a dated name, copy the new one."""
        assert not self.attached and self.fingerprint
        old = self.fingerprint
        payload = td.WORK / 'owner-payload-update'
        assert not payload.exists()
        fingerprint = bundle_module('bundle').build(payload)
        assert fingerprint != old
        renamed = 'ares-tools-replaced-' + time.strftime('%Y%m%d-%H%M', time.gmtime())
        loop = self.mounted()
        try:
            owner_fuse.mount(loop + 'p1', self.mount)
            assert (self.mount / 'ares-tools').is_dir() and not (self.mount / renamed).exists()
            # The guide's three PowerShell lines, against the file-backed stick.
            script = '''param($Source,$Destination,$Root,$Renamed)
Rename-Item -LiteralPath $Destination -NewName $Renamed
Import-Module ./docs/install-tools/OwnerTools.psm1 -Force
$drive=@{Letter='T';DriveType='Removable';BusType='USB';IsBoot=$false;IsSystem=$false;
Serial='VIRTUAL-TOOLS';FileSystem='exFAT';Root=$Root}
Copy-AresToolsPayload -Source $Source -Destination $Destination -Drive $drive
'''
            path = td.WORK / 'replace-owner-tools.ps1'
            path.write_text(script)
            subprocess.run(['pwsh', '-NoProfile', '-File', str(path), str(payload), str(self.mount / 'ares-tools'),
                            str(self.mount), renamed], check=True)
            checked = bundle_module('owner').checked_bundle
            assert checked(self.mount / 'ares-tools') == fingerprint and checked(self.mount / renamed) == old
            subprocess.run(['sync', '-f', str(self.mount)], check=True)
        finally:
            owner_fuse.detach(loop, self.mount)
        self.fingerprint = fingerprint
        self.verify(stage)
        td.save(stage + '-windows-copy', dict(status='passed', manifest_sha256=fingerprint, replaced_manifest_sha256=old,
            replaced_folder=renamed, source='Rename-Item, then Copy-AresToolsPayload in OwnerTools.psm1',
            image_sha256=self.expected, filesystem='FUSE exFAT', label='ARESTOOLS', real_hardware=False))

    def verify(self, stage):
        assert not self.attached
        loop = self.mounted(readonly=True)
        try:
            owner_fuse.check(loop + 'p1')
            owner_fuse.mount(loop + 'p1', self.mount, readonly=True)
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
            owner_fuse.detach(loop, self.mount)
        self.expected = digest(self.path)
        td.save(stage + '-media-backing', dict(status='passed', image_sha256=self.expected,
            bundle_unchanged=True, fsck_readonly=True, fuse_readonly=True,
            manifest_sha256=self.fingerprint, device_attached=False))

    def attach(self, guest, stage):
        import owner_xhci
        assert not self.attached and digest(self.path) == self.expected
        assert getattr(guest, 'owner_signed_in', False), 'Hotplug only after boot and sign-in'
        assert guest.mode == 'live' or getattr(guest, 'owner_physical_signed_in', False)
        owner_xhci.checkpoint(guest, stage + '-before-hotplug', needed=True)
        guest.monitor.command('blockdev-add', {'driver': 'file', 'node-name': 'owner-tools-file', 'filename': str(self.path)})
        guest.monitor.command('blockdev-add', {'driver': 'raw', 'node-name': 'owner-tools', 'file': 'owner-tools-file'})
        guest.monitor.command('device_add', {'driver': 'usb-storage', 'id': 'owner-tools-usb', 'drive': 'owner-tools',
            'bus': 'usb-controller.0', 'port': '2', 'removable': True})
        self.attached = True
        guest.owner_media = self
        owner_xhci.checkpoint(guest, stage + '-after-hotplug', attached=True)
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
        import owner_xhci
        assert self.attached
        owner_xhci.checkpoint(guest, stage + '-before-unplug')
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
        if owner_xhci.context(guest) is not None:
            # Resolve the owned controller's port 2 while the stick still
            # exists. Never excuse an unrelated disconnect or controller death.
            port = guest.capture_json(stage + '-tools-usb-port', td.sw.framed('''python3 - <<'PY'
import json,pathlib,re
root=pathlib.Path('/sys/bus/pci/devices/0000:00:05.0')
ports=[p.name for p in root.glob('usb*/*-2') if re.fullmatch('[0-9]+-2',p.name)]
assert len(ports)==1, 'STOP: tools-stick xHCI port identity missing or ambiguous'
print(json.dumps(dict(port=ports[0])))
PY'''))
            owner_xhci.checkpoint(guest, stage + '-requested-unplug', expected_disconnect=port['port'])
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
        owner_xhci.checkpoint(guest, stage + '-unplug-confirmed')
        owner_xhci.checkpoint(guest, stage + '-no-more-tools', attached=False, needed=False)
        guest.devices = guest.device_inventory()
        td.save(stage + '-media-detach', dict(status='passed', qmp_events=guest.monitor.events[start:],
            absent_before_shutdown=True, boot=guest.boot_number))
        self.verify(stage)
