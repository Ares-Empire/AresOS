"""Pinned ISO rehearsal on two writable file-backed disks, with offline gates."""
import base64
import json
import os
import pathlib
import re
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import time

import switch_vm as sw
from grub_bls import stock_bls_entry, confirm_menu_ocr, StockSelectionError
from rehearsal_auth import auth_file, guest_mount_command, REFERENCE
from disk_audit import (all_variables, boot_variables, compare_disk, offline_disk,
                        protected_writes, set_variable, gpt, efi_files, entry_target, firmware_baseline, nvram_audit,
                        check_boot_next, linux_entry, ordered_options)

WORK = pathlib.Path('.work/installer').resolve()
EVIDENCE = pathlib.Path('evidence/two-disk').resolve()
LIVE = next(i for i in json.loads(pathlib.Path('os/manifest/installer-isos.json').read_text()) if i['kind'] == 'live')


def save(name, value):
    (EVIDENCE / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')


class Guest(sw.Guest):
    order = 'protected-first'
    mode = 'installed'
    boot_count = 0
    audit = None
    firmware_default = False
    boot_purpose = 'installed'

    def network_args(self):
        return super().network_args() + (',hostfwd=tcp:127.0.0.1:18080-:8080' if self.mode == 'live' else '')

    def __init__(self, disk, password, secrets):
        assert 'GHCR_READ_TOKEN' not in os.environ, 'Owner token must not enter the VM observer environment'
        self.owner_auth_directory = auth_file().parent
        Guest.boot_count += 1
        self.boot_number = Guest.boot_count
        token = os.environ.get('GH_TOKEN', '')
        if token:
            auth = base64.b64encode(f'{os.environ["GITHUB_ACTOR"]}:{token}'.encode()).decode()
            encoded = base64.b64encode(json.dumps({'auths': {'ghcr.io': {'auth': auth}}}).encode()).decode()
            secrets = [*secrets, token, auth, encoded]
        entries = boot_variables(WORK / 'vars.fd')
        esp = None
        self.bootnext_authorization = dict(for_boot=self.boot_number, purpose=self.boot_purpose,
            mode=self.mode, order=self.order, destination=None, value=None, written=False)
        if self.mode == 'installed':
            esp, = [p for p in gpt(disk)['partitions'] if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
            linux = [name for name, value in entries.items() if re.fullmatch(r'Boot[0-9A-F]{4}', name)
                     and linux_entry(value, esp)]
            assert len(linux) == 1, f'Ambiguous Linux firmware entry: {linux}'
            check_boot_next(entries, target_esp=esp)
            if self.firmware_default:
                assert ordered_options(entries)[0] == linux[0], 'First stock start must use the Linux firmware default'
            else:
                raw = struct.pack('<H', int(linux[0][4:], 16))
                self.bootnext_authorization.update(destination=linux[0], value=raw.hex(), written=True)
                set_variable(WORK / 'vars.fd', 'BootNext', raw)
        else:
            check_boot_next(entries)
            if self.mode.startswith('marker'):
                assert ordered_options(entries)[0] == 'Boot0000', 'Unattended marker requires Windows first'
        prepared = boot_variables(WORK / 'vars.fd')
        expected = dict(entries)
        if self.bootnext_authorization['written']:
            expected['BootNext'] = dict(attributes=7, hex=self.bootnext_authorization['value'])
        assert prepared == expected, 'Boot preparation changed more than the recorded BootNext'
        self.bootnext_authorization['prepared_store'] = prepared
        check_boot_next(prepared, authorization=self.bootnext_authorization if self.bootnext_authorization['written'] else None,
                        consumed=False, target_esp=esp)
        save(f'boot-{self.boot_number}-bootnext', self.bootnext_authorization)
        try:
            super().__init__(disk, password, secrets)
            self.devices = self.device_inventory()
            save(f'boot-{self.boot_number}-devices', self.devices)
        except Exception:
            self.close(f'boot-{self.boot_number}-inventory-failure')
            raise

    def peripheral_args(self):
        # Keep detached storage slots empty, rather than reusing them for VGA/USB.
        return ['-device', 'virtio-vga,addr=0x4', '-device', 'qemu-xhci,id=usb-controller,addr=0x5',
                '-device', 'usb-kbd,bus=usb-controller.0',
                '-fsdev', f'local,id=owner-auth,path={self.owner_auth_directory},security_model=none,readonly=on',
                '-device', 'virtio-9p-pci,id=owner-auth-device,fsdev=owner-auth,mount_tag=aresos-owner-auth,addr=0x6']

    def prepare_registry_auth(self, encoded_auth=None):
        self.command(f'boot-{self.boot_number}-owner-auth-mount', guest_mount_command())

    def command(self, name, script, timeout=900, private=False):
        # Registry-client diagnostics stay private without needing the owner
        # token in the observer's environment or redaction list.
        registry_read = 'cosign verify' in script or 'bootc switch' in script
        try:
            return super().command(name, script, timeout, private=private or registry_read)
        except Exception:
            self.failed_command = True
            raise

    def storage_specs(self):
        specs = [('protected', WORK / 'protected.raw', 'MICRON-KEEP'), ('target', WORK / 'target.raw', 'CRUCIAL-TARGET')]
        if self.order == 'protected-second':
            specs.reverse()
        # Assign addresses before filtering: protected stays at 3 in reverse order.
        return [(name, path, serial, slot) for slot, (name, path, serial) in enumerate(specs, 2)
                if self.mode != 'marker-detached' or name == 'protected']

    def device_inventory(self):
        pci = self.monitor.command('query-pci')
        blocks = self.monitor.command('query-block')
        save(f'boot-{self.boot_number}-raw-hardware', dict(query_pci=pci, query_block=blocks))
        root, = [bus for bus in pci if bus['bus'] == 0]
        attached = [dict(key=f'pci:00:{d["slot"]:02x}.{d["function"]}',
                         qdev_id=d.get('qdev_id', ''), evidence='QMP query-pci') for d in root['devices']]
        for name, path, _, slot in self.storage_specs():
            device, = [d for d in root['devices'] if d.get('qdev_id') == name + '-device']
            assert device['slot'] == slot and device['function'] == 0, 'PLAN-GAP: storage PCI address differs'
            block, = [b for b in blocks if b.get('device') == name]
            assert pathlib.Path(block['inserted']['file']).resolve() == path.resolve()
        if self.mode in ('live', 'marker-baseline'):
            controller, = [d for d in root['devices'] if d['slot'] == 31 and d['function'] == 2]
            assert controller['class_info']['class'] == 0x0106, 'PLAN-GAP: expected Q35 SATA controller missing'
            cd, = [b for b in blocks if b.get('device') == 'installer-cd']
            assert pathlib.Path(cd['inserted']['file']).resolve() == (WORK / LIVE['filename']).resolve()
            assert cd['qdev'] == 'installer-cd-device', 'Unexpected QMP ISO device ID'
            attached.append(dict(key='pci:00:1f.2/sata:0:65535:0', qdev_id='installer-cd-device',
                                 bus='ide.0', unit=0, evidence='explicit QEMU ide.0/unit=0 and QMP query-block'))
        return dict(boot=self.boot_number, mode=self.mode, order=self.order, attached=attached,
                    query_pci=pci, query_block=blocks)

    def disk_args(self, disk):
        args = []
        for name, path, serial, slot in self.storage_specs():
            assert path.is_file() and path.resolve().is_relative_to(WORK)
            args += ['-drive', f'file={path},format=raw,if=none,id={name}',
                     '-device', f'virtio-blk-pci,drive={name},id={name}-device,serial={serial},addr=0x{slot:x}']
        if self.mode in ('live', 'marker-baseline'):
            args += ['-drive', f'file={WORK / LIVE["filename"]},format=raw,if=none,id=installer-cd,media=cdrom,readonly=on',
                     '-device', 'ide-cd,drive=installer-cd,id=installer-cd-device,bus=ide.0,unit=0']
        return args

    def boot_args(self):
        args = ['-debugcon', f'file:{WORK / "marker-debug.txt"}', '-global', 'isa-debugcon.iobase=0x402', '-no-shutdown']
        if self.mode == 'live':
            args += ['-kernel', str(WORK / 'vmlinuz'), '-initrd', str(WORK / 'initrd.img'),
                '-append', 'root=live:CDLABEL=Bazzite-Live enforcing=0 rd.live.image console=tty0 console=ttyS0,115200n8']
        return args

    def login_live(self):
        self.wait(r'\blogin: *', timeout=360)
        self.authentication_started = True
        # This ISO's livesys-main deletes root's password for the live session.
        # Installed recovery administration still uses its password and sudo.
        self.send('root\n')
        self.wait(r'[$#] ?(?:\x1b\[[0-9;]*[A-Za-z])*$', timeout=180)
        self.send("stty -echo; export PS1='ARESOS_ROOT> '; printf '\\nARESOS_ROOT_READY\\n'\n")
        self.wait(r'\r?\nARESOS_ROOT_READY\r?\n')
        self.command('live-root', 'set -e; test "$(id -u)" = 0; echo ISO_LIVE_ROOT_READY')
        self.prepare_registry_auth()

    def login(self):
        super().login()
        self.command(f'boot-{self.boot_number}-installed-efi-target', '''set -e
esp=$(findmnt --nofsroot -n -o SOURCE /boot/efi)
test "$(findmnt -n -o FSTYPE /boot/efi)" = vfat
parent=$(lsblk -ndo PKNAME "$esp")
test "$(lsblk -ndo SERIAL "/dev/$parent")" = CRUCIAL-TARGET
findmnt /boot/efi
lsblk --json --bytes --list --output NAME,TYPE,SERIAL,PARTUUID,PARTTYPE,MOUNTPOINTS
''')
        self.prepare_registry_auth()

    def wait(self, pattern, timeout=300):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            shutdowns = [e for e in self.monitor.events if e.get('event') == 'SHUTDOWN']
            if shutdowns:
                self.finish_shutdown('pre-login-reset', shutdowns[0]['data']['reason'])
                raise EOFError('Guest shut down before the requested console checkpoint')
            try:
                return super().wait(pattern, timeout=min(1, deadline - time.monotonic()))
            except TimeoutError:
                continue
        raise TimeoutError(f'Guest console did not reach {pattern}')

    def writes(self, stage):
        stats = self.monitor.command('query-blockstats')
        save(stage + '-blockstats', stats)
        return protected_writes(stats)

    def failure_counter(self, stage, probe_only=False):
        receipt = dict(failure_path=True, probe_only=probe_only, boot=self.boot_number,
                       status='unavailable', counter=stage + '-blockstats.json')
        try:
            assert self.monitor is not None
            self.monitor.command('stop')
            receipt['vm_paused'] = True
        except Exception as error:
            # Even if pausing fails, still try the required counter query.
            receipt.update(vm_paused=False, pause_error_type=type(error).__name__)
        try:
            assert self.monitor is not None
            stats = self.monitor.command('query-blockstats')
            save(stage + '-blockstats', stats)
        except Exception as error:
            receipt['error_type'] = type(error).__name__
            save(stage + '-failure-counter', receipt)
            return False
        receipt.update(status='recorded')
        save(stage + '-failure-counter', receipt)
        protected_writes(stats)
        return True

    def close(self, stage):
        try:
            if self.process is not None and (self.process.poll() is None
                    or not getattr(self, 'stopped_events_verified', False)):
                self.failure_counter(stage)
            elif self.process is not None and not getattr(self, 'expected_initialization_reboot', False) \
                    and (getattr(self, 'failed_command', False) or sys.exc_info()[0]):
                # An assertion after an orderly shutdown still uses that exact
                # final sample, taken before QMP quit. Do not query a dead VM.
                sampled = self.final_counter_stage
                path = EVIDENCE / (sampled + '-failure-counter.json')
                if not path.exists():
                    counter = sampled + '-blockstats.json'
                    save(sampled + '-failure-counter', dict(failure_path=True, probe_only=False,
                         boot=self.boot_number, status='recorded' if (EVIDENCE / counter).exists() else 'unavailable',
                         counter=counter, vm_paused=True, source='already-verified-guest-shutdown-final-counter'))
        finally:
            # Sample while QEMU is alive; the receipt says whether pause worked.
            # Counter errors must still close the VM and must not be suppressed.
            super().close(stage)

    def type(self, text):
        if not getattr(self, 'german_verified', False):
            self.command('tty-keymap-proof', 'set -e; source /etc/vconsole.conf; test "$KEYMAP" = de; cat /etc/vconsole.conf; localectl status; dumpkeys -C /dev/tty3 --keys-only')
            self.german_verified = True
        for char in text:
            assert char.isascii() and (char.islower() or char.isdigit() or char in ' /-\n'), char
            self.keys(german_keys(char))
            time.sleep(0.12)

    def finish_shutdown(self, stage, reason, timeout=180):
        assert reason in ('guest-shutdown', 'guest-reset'), reason
        deadline = time.monotonic() + timeout
        output = bytearray()
        while not any(e.get('event') == 'SHUTDOWN' for e in self.monitor.events):
            assert time.monotonic() < deadline, 'Guest did not shut down before its deadline'
            self.console.settimeout(0.5)
            try:
                data = self.console.recv(65536)
            except socket.timeout:
                continue
            assert data, 'Console closed before guest shutdown'
            output.extend(data)
            reply = self.replies.feed(data)
            if reply:
                self.console.sendall(reply)
        shutdowns = [e for e in self.monitor.events if e.get('event') == 'SHUTDOWN']
        assert len(shutdowns) == 1 and shutdowns[0]['data'] == dict(guest=True, reason=reason), shutdowns
        assert not any(e.get('event') == 'GUEST_PANICKED' for e in self.monitor.events)
        # -no-shutdown keeps QEMU alive with the guest stopped, so this final
        # counter includes shutdown/unmount writes too. Only then close it.
        if getattr(self, 'failed_command', False) or sys.exc_info()[0]:
            self.failure_counter(stage)
        else:
            self.writes(stage)
        self.final_counter_stage = stage
        self.stopped_events = list(self.monitor.events)
        self.monitor.command('quit')
        self.process.wait(timeout=15)
        self.monitor.reader.join(timeout=5)
        tail = self.monitor.events[len(self.stopped_events):]
        closing = [e for e in tail if e.get('event') == 'SHUTDOWN']
        assert len(closing) <= 1 and all(e['data'] == dict(guest=False, reason='host-qmp-quit') for e in closing), tail
        assert not any(e.get('event') in ('GUEST_PANICKED', 'RESET') for e in tail), tail
        self.stopped_events_verified = True
        text = output.decode(errors='replace')
        self.transcript += text
        if not self.authentication_started:
            self.boot_transcript += text
        (EVIDENCE / (stage + '-shutdown-console.txt')).write_text(sw.redact(text, self.secrets))
        assert self.process.returncode == 0
        if stage == 'pre-login-reset' and self.audit is not None:
            self.audit.check(f'boot-{self.boot_number}-pre-login-reset', self)

    def poweroff(self, stage):
        self.send('systemctl poweroff\n')
        self.finish_shutdown(stage, 'guest-shutdown')

    def reboot(self, stage):
        self.send('systemctl reboot\n')
        self.finish_shutdown(stage, 'guest-reset')


class Audit:
    def __init__(self):
        self.disk = offline_disk(WORK / 'protected.raw')
        save('protected-baseline', self.disk)
        self.nvram = None
        self.all_nvram = None
        self.target_installed = False
        self.devices = None
        self.stage = None
        self.windows_default = False
        Guest.audit = self

    def check(self, stage, guest=None, establish_nvram=False):
        observed = offline_disk(WORK / 'protected.raw', guest.process if guest else None)
        save(stage + '-protected', observed)
        compare_disk(self.disk, observed)
        nvram = boot_variables(WORK / 'vars.fd')
        all_nvram = all_variables(WORK / 'vars.fd')
        save(stage + '-nvram', nvram)
        save(stage + '-all-variables', all_nvram)
        shutil.copyfile(WORK / 'vars.fd', EVIDENCE / (stage + '-vars.fd'))
        assert guest is not None, 'Every firmware audit requires its per-boot device record'
        save(stage + '-devices', guest.devices)
        esp = None
        if self.target_installed:
            esp, = [p for p in gpt(WORK / 'target.raw')['partitions'] if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
        authorization = getattr(guest, 'bootnext_authorization', None)
        selected = authorization if authorization and authorization['written'] else None
        bootnext = check_boot_next(nvram, authorization=selected, windows_default=self.windows_default, target_esp=esp)
        save(stage + '-bootnext-audit', dict(**bootnext, boot=guest.boot_number,
             authorization=f'boot-{guest.boot_number}-bootnext.json', windows_default=self.windows_default))
        if establish_nvram:
            assert nvram['Boot0000'] == boot_variables(EVIDENCE / 'pre-firmware-vars.fd')['Boot0000']
            contract = json.loads((EVIDENCE.parents[0] / 'firmware-contract.json' if EVIDENCE.name == 'two-disk'
                                   else EVIDENCE.parents[1] / 'firmware-contract.json').read_text())
            assert contract['guid'] == '8108ac4e-9f11-4d59-850e-e21a522c59b2' and contract['optional_data_bytes'] == 16
            baseline = firmware_baseline(nvram, guest.devices)
            assert baseline, 'PLAN-GAP: no baseline EDK2 automatic-option GUID found'
            save(stage + '-firmware-ownership', dict(build_contract=contract, baseline=baseline))
        else:
            assert self.nvram is not None
            comparison = nvram_audit(self.nvram, nvram, before_devices=self.devices,
                after_devices=guest.devices, target_esp=esp, windows_first=self.windows_default)
            save(stage + '-nvram-diff', dict(from_stage=self.stage, **comparison))
            save(stage + '-all-variables-diff', {name: dict(before=self.all_nvram.get(name), after=all_nvram.get(name))
                 for name in self.all_nvram.keys() | all_nvram.keys()
                 if self.all_nvram.get(name) != all_nvram.get(name)})
        self.nvram, self.all_nvram, self.devices, self.stage = nvram, all_nvram, guest.devices, stage
        if self.windows_default:
            assert bytes.fromhex(nvram['BootOrder']['hex'])[:2] == bytes(2), 'PRODUCT FAILURE: Windows is not the default'
        if self.target_installed:
            layout = gpt(WORK / 'target.raw')
            esp, = [p for p in layout['partitions'] if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
            linux = [entry_target(bytes.fromhex(value['hex'])) for name, value in nvram.items()
                     if re.fullmatch('Boot[0-9A-F]{4}', name) and name != 'Boot0000'
                     and b'f\0e\0d\0o\0r\0a\0' in bytes.fromhex(value['hex']).lower()]
            assert len(linux) == 1 and linux[0]['partition']['guid'] == esp['guid'], 'PRODUCT FAILURE: Linux EFI entry does not target the new target ESP'
            assert linux[0]['partition']['start_lba'] == esp['start_lba']
            assert linux[0]['partition']['sectors'] == esp['bytes'] // 512
            save(stage + '-target-efi', dict(gpt=layout, efi_files=efi_files(WORK / 'target.raw', layout), entry=linux[0]))
        print(f'OFFLINE PROTECTED DISK UNCHANGED: {stage} {observed["sha256"]}', flush=True)


def german_keys(char):
    return {'/': ['shift', '7'], '-': ['slash'], 'y': ['z'], 'z': ['y'],
            ' ': ['spc'], '\n': ['ret']}.get(char, [char])


def require_supported_live_kickstart(help_text):
    help_text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', help_text).replace('\r\n', '\n')
    section = re.search(r'^  --kickstart[^\n]*\n(.*?)(?=^  --\S|\Z)', help_text, re.M | re.S)
    assert section, 'Missing explicit local kickstart option documentation'
    normalized = ' '.join(section[1].split()).lower()
    if 'not supported for live installations' in normalized:
        raise RuntimeError('BLOCKED: this ISO explicitly does not support live kickstart; qualify the real installer UI')


def bls_identity(text):
    titles = re.findall(r'^title (.+)$', text, re.M)
    options = re.findall(r'^options (.+)$', text, re.M)
    assert len(titles) == 1 and len(options) == 1, 'Ambiguous BLS title/options'
    targets = re.findall(r'(?:^|\s)ostree=(\S+)', options[0])
    assert len(targets) == 1 and targets[0].startswith('/ostree/'), 'Missing or ambiguous BLS deployment'
    return dict(title=titles[0], ostree=targets[0])


def bls_inventory_command(entries_directory='/boot/loader/entries', sysroot='/sysroot'):
    # Keep the entire Python program one shell argument. Appending the JSON
    # frame's redirection to a heredoc terminator would invalidate that export.
    identity_source = __import__('inspect').getsource(bls_identity)
    script = (f'import json, pathlib, re\ndirectory = {str(entries_directory)!r}\n'
              f'sysroot = {str(sysroot)!r}\n' + identity_source + '''
entries=[]
for file in pathlib.Path(directory).glob('*.conf'):
    text=file.read_text()
    identity=bls_identity(text)
    path=pathlib.Path(sysroot + identity['ostree']).resolve(strict=True)
    entries.append(dict(id=file.stem, title=identity['title'], deployment=str(path), content=text))
print(json.dumps(entries))
''')
    return 'python3 -c ' + shlex.quote(script)


def disk_names(layout):
    devices = layout['blockdevices']
    protected, = [d for d in devices if d.get('serial') == 'MICRON-KEEP' and d['type'] == 'disk']
    target, = [d for d in devices if d.get('serial') == 'CRUCIAL-TARGET' and d['type'] == 'disk']
    assert protected['size'] == 50 * 1024 ** 3 and target['size'] == 49 * 1024 ** 3
    assert re.fullmatch(r'vd[a-z]', protected['name']) and re.fullmatch(r'vd[a-z]', target['name'])
    assert protected['name'] != target['name']
    for item in devices:
        if re.fullmatch(re.escape(protected['name']) + r'\d+', item['name']):
            assert not any(item.get('mountpoints') or []), 'PRODUCT FAILURE: protected partition mounted'
        assert not re.fullmatch(re.escape(target['name']) + r'\d+', item['name']), 'Target is not empty'
    return protected['name'], target['name']


def kickstart(target, password_hash):
    assert re.fullmatch(r'vd[a-z]', target)
    return f'''cmdline
lang en_US.UTF-8
keyboard --vckeymap=de --xlayouts=de
timezone Europe/Berlin --utc
rootpw --lock
user --name=ares-recovery --uid=1000 --groups=wheel --iscrypted --password={password_hash}
network --bootproto=dhcp --device=link --activate
ignoredisk --only-use={target}
clearpart --all --initlabel --drives={target}
autopart --type=btrfs
bootloader --boot-drive={target} --append="console=tty0 console=ttyS0,115200n8"
%include /usr/share/anaconda/interactive-defaults.ks
%post --nochroot --erroronfail
echo ARESOS_INSTALLER_POST_COMPLETE > /dev/ttyS0
%end
reboot
'''


def live_inventory(guest, stage):
    release = json.loads(pathlib.Path('os/manifest/release.json').read_text())
    assert release['reference'] == REFERENCE
    verify = pathlib.Path('os/release/verify.sh').read_text().replace('@REFERENCE@', REFERENCE).replace('@IDENTITY@', release['signature']['identity'])
    guest.command(stage + '-release-signature', verify, timeout=180)
    save(stage + '-release-signature-proof', dict(status='passed', reference=REFERENCE,
        identity=release['signature']['identity'], issuer=release['signature']['issuer'],
        diagnostics='private; only fixed proof fields exported'))
    layout = guest.capture_json(stage + '-disks', sw.framed('lsblk --json --bytes --list --output NAME,TYPE,SIZE,SERIAL,PARTUUID,FSTYPE,MOUNTPOINTS'))
    protected, target = disk_names(layout)
    save(stage + '-mapping', dict(protected=protected, target=target, protected_serial='MICRON-KEEP', target_serial='CRUCIAL-TARGET'))
    digest = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference'].split('@', 1)[1]
    guest.command(stage + '-payload', f'''set -e
digest=$(podman image inspect ghcr.io/ublue-os/bazzite-nvidia-open:stable --format "{{{{.Digest}}}}")
printf '%s\\n' "$digest"
test "$digest" = '{digest}'
command -v runuser curl python3 busctl ss liveinst
''')
    help_text = guest.command(stage + '-cli', 'set -e; NO_COLOR=1 anaconda --help > /tmp/rehearsal-anaconda-help; cat /tmp/rehearsal-anaconda-help')
    try:
        require_supported_live_kickstart(help_text)
    except RuntimeError:
        save(stage + '-kickstart-guard', dict(status='rejected-unsupported-live-kickstart', method='real-Web-UI-only'))
    else:
        raise AssertionError('Pinned ISO help changed; stop rather than assume a new installer contract')
    # Exercise the exact read-only command/export before part B can use it.
    # An empty live-media BLS directory proves transport only, never recovery.
    bls = guest.capture_json(stage + '-bls-export-preflight', sw.framed(bls_inventory_command()))
    assert isinstance(bls, list)
    return protected, target


def cleanup_live(guest, stage, diagnostics=False):
    if guest.process.poll() is not None:
        return
    if getattr(guest, 'command_pending', False):
        guest.buffer = ''
        guest.send('\x03')
        guest.wait('ARESOS_ROOT> ', timeout=15)
    try:
        if diagnostics:
            guest.command('probe-failure-diagnostics', 'cat /tmp/rehearsal-webui-launch.log; journalctl -u webui-cockpit-ws --no-pager; ss -lntp; pgrep -a -f anaconda', timeout=30)
    finally:
        # Missing diagnostic files/processes cannot prevent the final write
        # counters and offline audit. Never suppress a shutdown/write failure.
        guest.poweroff(stage)


def install(audit, password, password_hash):
    from installer_webui import run
    Guest.mode = 'live'
    Guest.boot_purpose = Guest.order + '-install'
    guest = Guest(WORK / 'target.raw', password, [password, password_hash])
    stage = Guest.order + '-install'
    try:
        guest.login_live()
        protected, target = live_inventory(guest, stage)
        run(guest, EVIDENCE, protected, target, password, install=True, stage=stage)
        guest.poweroff(stage)
        audit.target_installed = True
        save(stage + '-result', dict(status='passed', target=target,
             method='unmodified liveinst Web UI via host Chromium',
             click_path_qualified=False, installation_pages_exercised=True))
        return target
    finally:
        try:
            cleanup_live(guest, stage)
        finally:
            guest.close(stage)
            audit.check(stage, guest)


def restore_windows_order(stage):
    entries = boot_variables(WORK / 'vars.fd')
    check_boot_next(entries, windows_default=True)
    order = bytes.fromhex(entries['BootOrder']['hex'])
    numbers = list(struct.unpack('<' + 'H' * (len(order) // 2), order))
    assert 0 in numbers
    expected = struct.pack('<' + 'H' * len(numbers), 0, *[n for n in numbers if n != 0])
    set_variable(WORK / 'vars.fd', 'BootOrder', expected)
    observed = boot_variables(WORK / 'vars.fd')
    assert observed == dict(entries, BootOrder=dict(entries['BootOrder'], hex=expected.hex())), 'PRODUCT FAILURE: restore_windows_order must produce exactly Windows + previous order without Windows'
    save(stage + '-windows-order', dict(status='passed', before=entries, after=observed,
         rule='exactly Windows followed by previous BootOrder without Windows'))


def reset_target():
    target = WORK / 'target.raw'
    assert target.resolve().is_relative_to(WORK) and target.is_file()
    closed = subprocess.run(['fuser', str(target)], capture_output=True)
    assert closed.returncode == 1 and not closed.stdout.strip(), 'Target file is still open'
    target.unlink()
    with target.open('xb') as output:
        output.truncate(49 * 1024 ** 3)


def start_installed(password, password_hash, stage, firmware_default=False):
    Guest.mode, Guest.boot_purpose = 'installed', stage
    Guest.firmware_default = firmware_default
    try:
        return sw.start_guest(WORK / 'target.raw', password, [password, password_hash], stage)
    finally:
        Guest.firmware_default = False


def select_grub_menu(guest, backup, ocr):
    proof = confirm_menu_ocr(ocr, backup)
    save('b-grub-menu-ocr-proof', proof)
    guest.keys(['home'])
    time.sleep(0.15)
    for _ in range(backup['menu_index']):
        guest.keys(['down'])
        time.sleep(0.15)
    guest.screenshot('b-grub-recorded-stock-selected')
    save('b-grub-selection', dict(**proof, keys=['home'] + ['down'] * backup['menu_index'] + ['ret']))
    guest.keys(['ret'])


def grub_promotion(audit, password, password_hash, stock):
    """Try the real menu first, then the explicitly permitted one-time fallback."""
    release = json.loads(pathlib.Path('os/manifest/release.json').read_text())
    digest = release['base'].split('@', 1)[1]
    Guest.mode = 'installed'
    guest = start_installed(password, password_hash, 'b-stock')
    try:
        sw.pin_stock(guest, 'b-pin-stock')
        script = pathlib.Path('os/release/switch.sh').read_text().replace('@REFERENCE@', release['reference'])
        guest.command('b-switch', script, timeout=1500)
        pending = guest.capture_json('b-switch-inspection', sw.framed('bootc status --json'))
        sw.inspect_transaction(pending, release['reference'], stock)
        guest.reboot('b-switch')
    finally:
        guest.close('b-switch')
        audit.check('b-switch', guest)
    guest = start_installed(password, password_hash, 'b-aresos')
    try:
        status = guest.capture_json('b-aresos-status', sw.framed('bootc status --json'))
        assert sw.booted_reference(status) == release['reference']
        assert sw.booted_digest(status) == release['reference'].split('@', 1)[1]
        ordered = guest.capture_json('b-aresos-order', sw.framed('rpm-ostree status --json'))
        assert ordered['deployments'][0]['booted'] and ordered['deployments'][0]['checksum'] != stock
        # Resolve each actual BLS ostree= symlink to the deployment checksum.
        entries = guest.capture_json('b-bls-entries', sw.framed(bls_inventory_command()))
        try:
            backup = stock_bls_entry(entries, stock, ordered['deployments'])
        except StockSelectionError as error:
            save('grub-promotion', dict(status='blocked', reason=str(error), entries=entries))
            guest.poweroff('b-unresolved-menu')
            return False
        save('b-recorded-stock-entry', backup)
        # Verified Fedora menu_show_once exposes this one menu before any key.
        guest.command('b-show-menu-once', 'set -e; grub2-editenv - set menu_show_once=1; grub2-editenv - list')
        guest.reboot('b-menu-preparation')
    finally:
        guest.close('b-menu-preparation')
        audit.check('b-menu-preparation', guest)
    Guest.boot_purpose = 'b-grub-menu'
    guest = Guest(WORK / 'target.raw', password, [password, password_hash])
    path = f'QMP Home, Down x{backup["menu_index"]}, Enter after exact ordered OCR'
    try:
        selected = False
        deadline = time.monotonic() + 40
        attempt = 0
        last_menu_lines = None
        while time.monotonic() < deadline:
            attempt += 1
            name = f'b-grub-menu-attempt-{attempt:02}'
            guest.screenshot(name)
            ocr = subprocess.check_output(['tesseract', str(EVIDENCE / (name + '.png')), 'stdout', '--psm', '6'],
                                          stderr=subprocess.DEVNULL).decode()
            (EVIDENCE / (name + '-ocr.txt')).write_text(ocr)
            if re.search(r'Bazzite.*ostree', ocr, re.I):
                lines = [re.sub(r'\s+', ' ', line.strip()) for line in ocr.splitlines()
                         if re.search(r'Bazzite.*ostree', line, re.I)]
                if lines != last_menu_lines:
                    last_menu_lines = lines
                    time.sleep(0.3)
                    continue
                try:
                    select_grub_menu(guest, backup, ocr)
                except StockSelectionError as error:
                    save('grub-promotion', dict(status='blocked', reason=str(error), frame=name, entries=entries))
                    raise
                selected = True
                break
            time.sleep(1)
        if not selected:
            path = 'grub2-reboot fallback after QMP menu could not be identified/driven; no selection key sent'
        try:
            guest.login()
        except TimeoutError:
            # Firmware intercepted Esc or no menu could be identified. This is
            # a bounded UI dead end, not permission to guess an entry.
            guest.close('b-menu-undrivable')
            audit.check('b-menu-undrivable', guest)
            guest = start_installed(password, password_hash, 'b-menu-fallback')
            path = 'grub2-reboot fallback after QMP menu could not be driven'
        state = guest.capture_json('b-one-time-attempt-status', sw.framed('bootc status --json'))
        if state['status']['booted']['ostree']['checksum'] != stock:
            assert not selected, 'PRODUCT FAILURE: OCR-confirmed GRUB selection did not boot the recorded stock'
            assert sw.booted_reference(state) == release['reference']
            path = 'grub2-reboot fallback after QMP selection did not boot stock'
            guest.command('b-one-time-fallback', f"set -e; grub2-reboot {shlex.quote(backup['id'])}; grub2-editenv - list")
            guest.reboot('b-one-time-fallback')
            guest.close('b-one-time-fallback')
            audit.check('b-one-time-fallback', guest)
            guest = start_installed(password, password_hash, 'b-recovered-stock')
        state = guest.capture_json('b-recovered-stock-status', sw.framed('bootc status --json'))
        order = guest.capture_json('b-recovered-stock-order', sw.framed('rpm-ostree status --json'))
        assert state['status']['booted']['ostree']['checksum'] == stock
        assert sw.booted_digest(state) == digest
        assert not order['deployments'][0]['booted'] and order['deployments'][0]['checksum'] != stock
        assert any(d.get('booted') and d['checksum'] == stock for d in order['deployments'][1:])
        default = pathlib.Path('os/release/default-stock.sh').read_text().replace('@BASE_DIGEST@', digest).replace('@STOCK_CHECKSUM@', stock)
        guest.command('b-promote-recorded-stock', default)
        guest.reboot('b-promote-recorded-stock')
    finally:
        guest.close('b-recovered-stock')
        audit.check('b-recovered-stock', guest)
    guest = start_installed(password, password_hash, 'b-unattended-stock')
    try:
        state = guest.capture_json('b-unattended-stock-status', sw.framed('bootc status --json'))
        order = guest.capture_json('b-unattended-stock-order', sw.framed('rpm-ostree status --json'))
        assert state['status']['booted']['ostree']['checksum'] == stock and sw.booted_digest(state) == digest
        assert order['deployments'][0]['booted'] and order['deployments'][0]['checksum'] == stock
        assert not state['status'].get('staged') and not state['status'].get('rollbackQueued')
        sw.capture_stock_greeter(guest, EVIDENCE, 'b-unattended-stock')
        guest.poweroff('b-unattended-stock')
    finally:
        guest.close('b-unattended-stock')
        audit.check('b-unattended-stock', guest)
    save('grub-promotion', dict(status='passed', path=path, recorded_stock_checksum=stock,
                               stock_previous_index=backup['menu_index'], stock_now_booted_first=True, unattended_second_boot=True))
    return True


def marker(audit, stage, baseline=False, detached=False):
    Guest.mode = 'marker-baseline' if baseline else 'marker-detached' if detached else 'marker'
    Guest.boot_purpose = stage
    guest = Guest(WORK / 'target.raw', '', [])
    try:
        deadline = time.monotonic() + 90
        output = ''
        while time.monotonic() < deadline:
            output = (WORK / 'marker-debug.txt').read_text(errors='replace')
            if 'MARKER_BOOT_COMPLETE' in output:
                break
            assert guest.process.poll() is None, 'Marker VM exited without its completion marker'
            time.sleep(0.2)
        (EVIDENCE / (stage + '-marker.txt')).write_text(output)
        assert 'ARESOS_WINDOWS_MARKER BootCurrent=0000' in output, output
        assert '\\EFI\\Microsoft\\Boot\\bootmgfw.efi'.lower() in output.lower(), output
        assert audit.disk['gpt']['partitions'][0]['guid'].lower() in output.lower(), output
        guest.writes(stage)
        guest.screenshot(stage + '-windows-marker')
        guest.finish_shutdown(stage, 'guest-shutdown', timeout=30)
    finally:
        guest.close(stage)
    audit.check(stage, guest, establish_nvram=baseline)


def stock_inventory(guest, stage):
    source = pathlib.Path('os/tests/audit.py').read_text()
    program = source.split("if __name__ == '__main__':", 1)[0]
    program += "\nprint(json.dumps([u for u in inventory() if u['suspicious'] or u['name'] in " + repr(stock_unit_names()) + "]))\n"
    observed = guest.capture_json(stage, sw.framed('python3 -c ' + shlex.quote(program)))
    known = set(stock_unit_names())
    deployment = re.compile(r'uupd|topgrade|(?:rpm-ostree|bootc|ujust)\b.*\b(?:upgrade|update|rebase|switch|deploy|install)\b|systemd-sysupdate|packagekit|dnf.*(?:automatic|offline)', re.I)
    excluded = {'dnf5-offline-transaction-cleanup.service'}
    for unit in observed:
        if deployment.search(unit['name'] + '\n' + '\n'.join(unit['commands'])):
            assert unit['name'] in known or unit['name'] in excluded, 'PLAN-GAP: unreviewed stock OS updater unit: ' + unit['name']
    return observed


def stock_unit_names():
    import ast
    source = pathlib.Path('os/release/pause-stock-updates.sh').read_text().split("<<'PAUSE_STOCK'\n", 1)[1].split('\nPAUSE_STOCK', 1)[0]
    module = ast.parse(source)
    return sorted({value for node in module.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id in ('SYSTEM', 'USER') for t in node.targets)
                   for value in ast.literal_eval(node.value)})


def stock_recipe_probe(guest):
    stock_inventory(guest, 'stock-updater-inventory')
    guest.command('stock-recipe-tools', 'set -e; for tool in systemctl podman pgrep runuser getent python3; do command -v "$tool"; done')
    source = pathlib.Path('os/ci/stock_probe.py').read_text()
    digest = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference'].split('@', 1)[1]
    output = guest.command('cached-stock-cli-help', 'python3 -c ' + shlex.quote(source) + ' ' + shlex.quote(digest))
    clean = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output).replace('\r', '')
    proof, = [json.loads(line.split(' ', 1)[1]) for line in clean.splitlines() if line.startswith('ARESOS_CACHED_STOCK_CLI_PROBE ')]
    assert proof['status'] == 'passed' and proof['digest'] == digest
    assert proof['part_b_cli_help'] and proof['stock_idle_source_verified']
    assert proof['temporary_grubenv_bare_id']
    assert proof['idle_source']['bootloader_versions'] == {'ostree': '2026.4-1.fc44', 'grub2-common': '2.12-66.fc44'}
    save('cached-stock-cli-probe', proof)
    source = pathlib.Path('os/release/pause-stock-updates.sh').read_text().split("<<'PAUSE_STOCK'\n", 1)[1].split('\nPAUSE_STOCK', 1)[0]
    program = source.split("if __name__ == '__main__':", 1)[0]
    program += "\npause_units()\npause_units()\nprint('REAL_STOCK_UNIT_PAUSE_IDEMPOTENT_PROBE_PASSED')\n"
    output = guest.command('stock-unit-pause-probe', 'python3 -c ' + shlex.quote(program))
    assert 'REAL_STOCK_UNIT_PAUSE_IDEMPOTENT_PROBE_PASSED' in output
    save('stock-recipe-probe', dict(status='passed', tools_and_help=True, real_unit_pause_twice=True,
         cli_context='ISO cached exact stock image; pull never, network none, read-only, no owner credentials',
         pending_cleanup='read-only help plus real-status mocked native regressions; no OSTree deployment in live probe'))


def stock_before_windows(audit, password, password_hash):
    guest = start_installed(password, password_hash, 'stock', firmware_default=True)
    stage = 'stock-before-windows'
    try:
        installed_keyboard(guest)
        guest.command('first-stock-pause', pathlib.Path('os/release/pause-stock-updates.sh').read_text())
        stock_inventory(guest, 'first-stock-updater-inventory')
        proof = sw.pin_stock(guest, 'first-stock-pin')
        state = guest.capture_json('first-stock-ready-status', sw.framed('bootc status --json'))
        assert state['status']['booted']['ostree']['checksum'] == proof['booted_checksum']
        assert state['status']['booted']['image']['imageDigest'] == proof['booted_digest']
        assert state['status']['booted']['pinned'] and not state['status'].get('staged')
        guest.poweroff(stage)
    finally:
        guest.close(stage)
        audit.check(stage, guest)

    return proof


def keyboard_reader_command(root):
    from keyboard_proof import read_files
    import inspect
    program = 'import json, pathlib\n' + inspect.getsource(read_files)
    program += '\nprint(json.dumps(read_files(' + repr(str(root)) + ')))\n'
    return 'python3 -c ' + shlex.quote(program)


def installed_keyboard(guest):
    from keyboard_proof import validate_installed_keyboard
    assert guest.mode == 'installed', 'Installed keyboard proof cannot use the live root'
    choices = json.loads((EVIDENCE / 'webui-keyboard-proof.json').read_text())
    record = guest.capture_json('installed-keyboard-files', sw.framed(keyboard_reader_command('/')))
    result = validate_installed_keyboard(record, choices['layout_switching_options'])
    save('installed-keyboard-result', dict(**result, context='first installed stock root shell',
         boot=guest.boot_number, order=Guest.order, root=record['root'],
         module_proof='webui-keyboard-proof.json', files_record='installed-keyboard-files.json'))


def installed_keyboard_reader_probe(guest):
    from keyboard_proof import validate_installed_keyboard
    root = '/tmp/aresos-keyboard-reader-fixture'
    choices = json.loads((EVIDENCE / 'webui-keyboard-proof.json').read_text())
    options = choices['layout_switching_options']
    program = ('import pathlib\nroot = pathlib.Path(' + repr(root) + ')\n'
               '(root / "etc/X11/xorg.conf.d").mkdir(parents=True, exist_ok=True)\n'
               '(root / "etc/vconsole.conf").write_text(\'KEYMAP="de"\\n\')\n'
               '(root / "etc/X11/xorg.conf.d/00-keyboard.conf").write_text(' +
               repr('Section "InputClass"\n Option "XkbLayout" "de"\n Option "XkbOptions" "' + ','.join(options) + '"\nEndSection\n') + ')\n')
    guest.command('keyboard-reader-fixture', 'python3 -c ' + shlex.quote(program))
    record = guest.capture_json('keyboard-reader-probe-files', sw.framed(keyboard_reader_command(root)))
    result = validate_installed_keyboard(record, options)
    save('keyboard-reader-probe-result', dict(**result, installed=False, fixture_only=True,
         context='temporary synthetic files in live guest; reader transport only'))


def live_probe(audit):
    from installer_webui import probe
    Guest.mode = 'live'
    Guest.boot_purpose = 'live-ui-probe'
    guest = Guest(WORK / 'target.raw', '', [])
    try:
        guest.login_live()
        protected, target = live_inventory(guest, 'live')
        save('live-assumptions', dict(order=Guest.order, protected=protected, target=target))
        probe(guest, EVIDENCE, protected, target)
        after = guest.capture_json('live-after-preview-disks', sw.framed('lsblk --json --bytes --list --output NAME,TYPE,SIZE,SERIAL,PARTUUID,FSTYPE,MOUNTPOINTS'))
        assert disk_names(after) == (protected, target)
        guest.keys(['shift'])
        guest.screenshot('live-qmp-observer-input')
        ocr = subprocess.check_output(['tesseract', str(EVIDENCE / 'live-qmp-observer-input.png'), 'stdout'],
                                      stderr=subprocess.DEVNULL).decode()
        (EVIDENCE / 'live-ocr-tool-preflight.txt').write_text(ocr)
        save('part-b-tool-probe', dict(status='passed', ocr_executed=True,
             context='actual live QMP screenshot; OCR tool only, not GRUB menu qualification'))
        installed_keyboard_reader_probe(guest)
        stock_recipe_probe(guest)
        assert guest.failure_counter('failure-counter-probe', probe_only=True)
        assert json.loads((EVIDENCE / 'failure-counter-probe-failure-counter.json').read_text())['vm_paused']
        guest.monitor.command('cont')
        guest.writes('live-ui-probe')
        guest.poweroff('live-ui-probe')
    finally:
        try:
            cleanup_live(guest, 'live-ui-probe', diagnostics=True)
        finally:
            guest.close('live-ui-probe')
            audit.check('live-ui-probe', guest)


def main():
    global EVIDENCE
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    assert sys.argv[1:] in (['probe'], ['part-b']), '11l permits one probe and one protected-second Part B run only'
    if sys.argv[1:] == ['part-b']:
        authorization = json.loads((EVIDENCE.parent / '11c-dispatch-authorization.json').read_text())
        assert authorization['probe']['status'] == 'passed'
        assert authorization['probe']['commit'] == os.environ['GITHUB_SHA']
        assert authorization['probe']['both_orders'] and authorization['probe']['review_validated']
        assert authorization['probe']['detached_windows'] and authorization['probe']['target_reset']
        assert authorization['part_b_dispatched'] == 1 and authorization['full_dispatched'] == 5
        assert authorization['probe']['bootnext_checked'] and authorization['probe']['bootloader_source_verified']
        Guest.order = 'protected-second'
    sw.WORK, sw.EVIDENCE = WORK, EVIDENCE
    for name in ('vmlinuz', 'initrd.img'):
        with (WORK / name).open('wb') as output:
            subprocess.run(['bsdtar', '-xOf', str(WORK / LIVE['filename']), 'images/pxeboot/' + name], stdout=output, check=True)
    audit = Audit()
    shutil.copyfile(WORK / 'vars.fd', EVIDENCE / 'pre-firmware-vars.fd')
    marker(audit, 'baseline-firmware', baseline=True)
    if sys.argv[1:] == ['probe']:
        probe_root = EVIDENCE
        live_probe(audit)
        restore_windows_order('probe')
        audit.windows_default = True
        marker(audit, 'probe-windows-without-linux', detached=True)
        reset_target()
        shutil.copyfile(probe_root / 'pre-firmware-vars.fd', WORK / 'vars.fd')
        EVIDENCE = probe_root / 'protected-second'
        EVIDENCE.mkdir()
        sw.EVIDENCE = EVIDENCE
        Guest.order = 'protected-second'
        reverse = Audit()
        compare_disk(audit.disk, reverse.disk)
        shutil.copyfile(WORK / 'vars.fd', EVIDENCE / 'pre-firmware-vars.fd')
        marker(reverse, 'baseline-firmware', baseline=True)
        live_probe(reverse)
        restore_windows_order('probe')
        reverse.windows_default = True
        marker(reverse, 'probe-windows-without-linux', detached=True)
        proof = dict(status='passed', installed=False, both_orders=True, review_validated=True,
                     detached_windows=True, target_reset=True, owner_auth_read_only=True, signature_verified=True,
                     firmware_rule='11f-linux-position', stock_recipe_probe=True, failure_counter_probe=True,
                     read_only_keyboard_proof=True, installed_keyboard_reader_probe=True,
                     part_b_tools_probe=True, stock_idle_source_verified=True,
                     bootnext_checked=True, bootloader_source_verified=True,
                     commit=os.environ['GITHUB_SHA'])
        (probe_root / 'probe-result.json').write_text(json.dumps(proof, indent=2) + '\n')
        print('PROBE PASSED: both serial mappings, real UI through review, backend choices and zero protected writes; no installation', flush=True)
        return
    import crypt
    import secrets
    password = secrets.token_hex(24)
    password_hash = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    print(f'::add-mask::{password}', flush=True)
    print(f'::add-mask::{password_hash}', flush=True)
    credentials = WORK / 'credentials.json'
    credentials.write_text(json.dumps(dict(password=password)))
    credentials.chmod(0o600)
    sw.Guest = Guest
    install(audit, password, password_hash)
    # Match the owner guide: firmware still starts Linux for hardware setup and
    # first login. Only the successful keyboard/pause/pin permits the F2 step.
    stock = stock_before_windows(audit, password, password_hash)
    restore_windows_order('after-first-login-pin')
    audit.windows_default = True
    marker(audit, 'after-first-login-default-windows')
    marker(audit, 'after-install-without-linux', detached=True)
    promoted = grub_promotion(audit, password, password_hash, stock['booted_checksum'])
    save('part-b-result', dict(part_b='passed' if promoted else 'blocked', order=Guest.order,
         installed_keyboard_german=True, first_stock_firmware_default=True,
         windows_default_after_first_login_pin=True, unattended_windows_marker=True,
         detached_windows_marker=True, rollback_and_default_undo_repeated=False,
         part_a_evidence='11k full40119526154; both orders; earlier Windows-first timing',
         part_b_evidence='grub-promotion.json', commit=os.environ['GITHUB_SHA']))


if __name__ == '__main__':
    main()
