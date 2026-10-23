"""Pinned ISO rehearsal on two writable file-backed disks, with offline gates."""
import base64
import json
import os
import pathlib
import re
import shutil
import socket
import struct
import subprocess
import sys
import time

import switch_vm as sw
from disk_audit import (all_variables, boot_variables, compare_disk, compare_nvram, offline_disk,
                        protected_writes, set_variable, gpt, efi_files, entry_target)

WORK = pathlib.Path('.work/installer').resolve()
EVIDENCE = pathlib.Path('evidence/two-disk').resolve()
LIVE = next(i for i in json.loads(pathlib.Path('os/manifest/installer-isos.json').read_text()) if i['kind'] == 'live')


def save(name, value):
    (EVIDENCE / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')


class Guest(sw.Guest):
    order = 'protected-first'
    mode = 'installed'
    boot_count = 0

    def network_args(self):
        return super().network_args() + (',hostfwd=tcp:127.0.0.1:18080-:8080' if self.mode == 'live' else '')

    def __init__(self, disk, password, secrets):
        Guest.boot_count += 1
        self.boot_number = Guest.boot_count
        token = os.environ.get('GH_TOKEN', '')
        if token:
            auth = base64.b64encode(f'{os.environ["GITHUB_ACTOR"]}:{token}'.encode()).decode()
            encoded = base64.b64encode(json.dumps({'auths': {'ghcr.io': {'auth': auth}}}).encode()).decode()
            secrets = [*secrets, token, auth, encoded]
        if self.mode == 'installed':
            entries = boot_variables(WORK / 'vars.fd')
            linux = [name for name, value in entries.items() if re.fullmatch(r'Boot[0-9A-F]{4}', name)
                     and b'f\0e\0d\0o\0r\0a\0' in bytes.fromhex(value['hex']).lower()]
            assert len(linux) == 1, f'Ambiguous Linux firmware entry: {linux}'
            set_variable(WORK / 'vars.fd', 'BootNext', struct.pack('<H', int(linux[0][4:], 16)))
        super().__init__(disk, password, secrets)

    def disk_args(self, disk):
        specs = [('protected', WORK / 'protected.raw', 'MICRON-KEEP'), ('target', WORK / 'target.raw', 'CRUCIAL-TARGET')]
        if self.order == 'protected-second':
            specs.reverse()
        if self.mode == 'marker-detached':
            specs = [item for item in specs if item[0] == 'protected']
        args = []
        for name, path, serial in specs:
            assert path.is_file() and path.resolve().is_relative_to(WORK)
            args += ['-drive', f'file={path},format=raw,if=none,id={name}',
                     '-device', f'virtio-blk-pci,drive={name},serial={serial}']
        if self.mode in ('live', 'marker-baseline'):
            args += ['-drive', f'file={WORK / LIVE["filename"]},format=raw,media=cdrom,readonly=on']
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
        self.writes(stage)
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

    def check(self, stage, guest=None, establish_nvram=False):
        observed = offline_disk(WORK / 'protected.raw', guest.process if guest else None)
        save(stage + '-protected', observed)
        compare_disk(self.disk, observed)
        nvram = boot_variables(WORK / 'vars.fd')
        all_nvram = all_variables(WORK / 'vars.fd')
        save(stage + '-nvram', nvram)
        save(stage + '-all-variables', all_nvram)
        shutil.copyfile(WORK / 'vars.fd', EVIDENCE / (stage + '-vars.fd'))
        if establish_nvram:
            assert nvram['Boot0000'] == boot_variables(EVIDENCE / 'pre-firmware-vars.fd')['Boot0000']
            self.nvram = nvram
            self.all_nvram = all_nvram
        else:
            assert self.nvram is not None
            save(stage + '-nvram-diff', compare_nvram(self.nvram, nvram))
            save(stage + '-all-variables-diff', {name: dict(before=self.all_nvram.get(name), after=all_nvram.get(name))
                 for name in self.all_nvram.keys() | all_nvram.keys()
                 if self.all_nvram.get(name) != all_nvram.get(name)})
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
    help_text = guest.command(stage + '-cli', 'anaconda --help')
    try:
        require_supported_live_kickstart(help_text)
    except RuntimeError:
        save(stage + '-kickstart-guard', dict(status='rejected-unsupported-live-kickstart', method='real-Web-UI-only'))
    else:
        raise AssertionError('Pinned ISO help changed; stop rather than assume a new installer contract')
    return protected, target


def install(audit, password, password_hash):
    from installer_webui import run
    Guest.mode = 'live'
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
        if guest.process.poll() is None:
            try:
                guest.buffer = ''
                guest.send('\x03')
                guest.wait('ARESOS_ROOT> ', timeout=15)
                guest.poweroff(stage)
            except Exception:
                pass
        guest.close(stage)
        audit.check(stage, guest)


def restore_windows_order():
    entries = boot_variables(WORK / 'vars.fd')
    order = bytes.fromhex(entries['BootOrder']['hex'])
    numbers = list(struct.unpack('<' + 'H' * (len(order) // 2), order))
    assert 0 in numbers
    set_variable(WORK / 'vars.fd', 'BootOrder', struct.pack('<' + 'H' * len(numbers), 0, *[n for n in numbers if n != 0]))


def grub_promotion(audit, password, password_hash):
    """Try the real menu first, then the explicitly permitted one-time fallback."""
    release = json.loads(pathlib.Path('os/manifest/release.json').read_text())
    stock = json.loads((EVIDENCE / 'result.json').read_text())['retained_stock_checksum']
    digest = release['base'].split('@', 1)[1]
    Guest.mode = 'installed'
    guest = sw.start_guest(WORK / 'target.raw', password, [password, password_hash], 'b-stock')
    try:
        script = pathlib.Path('os/release/switch.sh').read_text().replace('@REFERENCE@', release['reference'])
        guest.command('b-switch', script, timeout=1500)
        pending = guest.capture_json('b-switch-inspection', sw.framed('bootc status --json'))
        sw.inspect_transaction(pending, release['reference'], stock)
        guest.reboot('b-switch')
    finally:
        guest.close('b-switch')
        audit.check('b-switch', guest)
    guest = sw.start_guest(WORK / 'target.raw', password, [password, password_hash], 'b-aresos')
    try:
        status = guest.capture_json('b-aresos-status', sw.framed('bootc status --json'))
        assert sw.booted_reference(status) == release['reference']
        ordered = guest.capture_json('b-aresos-order', sw.framed('rpm-ostree status --json'))
        assert ordered['deployments'][0]['booted'] and ordered['deployments'][0]['checksum'] != stock
        # Resolve each actual BLS ostree= symlink to the deployment checksum.
        identity_source = __import__('inspect').getsource(bls_identity)
        entries = guest.capture_json('b-bls-entries', sw.framed('''python3 - <<'PY'
import json, pathlib, re
''' + identity_source + '''
entries=[]
for file in pathlib.Path('/boot/loader/entries').glob('*.conf'):
    text=file.read_text()
    identity=bls_identity(text)
    path=pathlib.Path('/sysroot' + identity['ostree']).resolve()
    entries.append(dict(id=file.stem, title=identity['title'], deployment=str(path), content=text))
print(json.dumps(entries))
PY'''))
        candidates = [entry for entry in entries if stock in entry['deployment']]
        if len(candidates) != 1 or candidates[0]['id'] != 'ostree-1-default':
            save('grub-promotion', dict(status='blocked', reason='Actual BLS stock entry was not uniquely index 1', entries=entries))
            guest.poweroff('b-unresolved-menu')
            return False
        backup = candidates[0]
        guest.reboot('b-menu-preparation')
    finally:
        guest.close('b-menu-preparation')
        audit.check('b-menu-preparation', guest)
    guest = Guest(WORK / 'target.raw', password, [password, password_hash])
    path = 'QMP Esc, Home, Down, Enter'
    try:
        # Attempt Esc in GRUB, retain the frame and OCR before selecting. Never
        # select by guessed position if the actual recorded titles are absent.
        time.sleep(2)
        guest.keys(['esc'])
        time.sleep(0.3)
        guest.screenshot('b-grub-menu-attempt')
        frame = EVIDENCE / 'b-grub-menu-attempt.png'
        ocr = subprocess.check_output(['tesseract', str(frame), 'stdout'], stderr=subprocess.DEVNULL).decode()
        (EVIDENCE / 'b-grub-menu-attempt-ocr.txt').write_text(ocr)
        normalized = re.sub('[^a-z0-9]', '', ocr.lower())
        if 'ostree0' in normalized and 'ostree1' in normalized and 'grub' in normalized:
            guest.keys(['home'])
            guest.keys(['down'])
            guest.screenshot('b-grub-recorded-stock-selected')
            guest.keys(['ret'])
        else:
            path = 'grub2-reboot fallback after QMP menu could not be identified'
        try:
            guest.login()
        except TimeoutError:
            # Firmware intercepted Esc or no menu could be identified. This is
            # a bounded UI dead end, not permission to guess an entry.
            guest.close('b-menu-undrivable')
            audit.check('b-menu-undrivable', guest)
            guest = sw.start_guest(WORK / 'target.raw', password, [password, password_hash], 'b-menu-fallback')
            path = 'grub2-reboot fallback after QMP menu could not be driven'
        state = guest.capture_json('b-one-time-attempt-status', sw.framed('bootc status --json'))
        if state['status']['booted']['ostree']['checksum'] != stock:
            assert sw.booted_reference(state) == release['reference']
            path = 'grub2-reboot fallback after QMP selection did not boot stock'
            guest.command('b-one-time-fallback', f"set -e; grub2-reboot '{backup['id']}'; grub2-editenv - list")
            guest.reboot('b-one-time-fallback')
            guest.close('b-one-time-fallback')
            audit.check('b-one-time-fallback', guest)
            guest = sw.start_guest(WORK / 'target.raw', password, [password, password_hash], 'b-recovered-stock')
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
    guest = sw.start_guest(WORK / 'target.raw', password, [password, password_hash], 'b-unattended-stock')
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
                               stock_was_index_1=True, stock_now_booted_first=True, unattended_second_boot=True))
    return True


def marker(audit, stage, baseline=False, detached=False):
    Guest.mode = 'marker-baseline' if baseline else 'marker-detached' if detached else 'marker'
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


def live_probe(audit):
    from installer_webui import probe
    Guest.mode = 'live'
    guest = Guest(WORK / 'target.raw', '', [])
    try:
        guest.login_live()
        protected, target = live_inventory(guest, 'live')
        save('live-assumptions', dict(order=Guest.order, protected=protected, target=target))
        probe(guest, EVIDENCE, protected, target)
        after = guest.capture_json('live-after-preview-disks', sw.framed('lsblk --json --bytes --list --output NAME,TYPE,SIZE,SERIAL,PARTUUID,FSTYPE,MOUNTPOINTS'))
        assert disk_names(after) == (protected, target)
        guest.writes('live-ui-probe')
        guest.poweroff('live-ui-probe')
    finally:
        if guest.process.poll() is None:
            try:
                guest.buffer = ''
                guest.send('\x03')
                guest.wait('ARESOS_ROOT> ', timeout=15)
                guest.command('probe-failure-diagnostics', 'cat /tmp/rehearsal-webui-launch.log; journalctl -u webui-cockpit-ws --no-pager; ss -lntp; pgrep -a -f anaconda', timeout=30)
                guest.poweroff('live-ui-probe')
            except Exception:
                pass
        guest.close('live-ui-probe')
        audit.check('live-ui-probe', guest)


def main():
    global EVIDENCE
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    assert sys.argv[1:] in (['probe'], ['full'])
    if sys.argv[1:] == ['full']:
        authorization = json.loads((EVIDENCE.parent / '11b-dispatch-authorization.json').read_text())
        assert authorization['probe']['status'] == 'passed'
        assert authorization['probe']['commit'] == os.environ['GITHUB_SHA']
        assert authorization['probe']['both_orders'] and authorization['probe']['review_validated']
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
        proof = dict(status='passed', installed=False, both_orders=True, review_validated=True,
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
    pristine_vars = WORK / 'pristine-vars.fd'
    shutil.copyfile(EVIDENCE / 'pre-firmware-vars.fd', pristine_vars)
    target = install(audit, password, password_hash)
    set_variable(WORK / 'vars.fd', 'BootNext', bytes(2))
    marker(audit, 'after-install-without-linux', detached=True)
    Guest.mode = 'installed'
    sw.Guest = Guest
    sw.main(WORK / 'target.raw', preserve_vars=True, target_name=target,
            shutdown_hook=lambda stage, guest: audit.check('switch-sequence-' + stage, guest))
    promoted = grub_promotion(audit, password, password_hash)
    set_variable(WORK / 'vars.fd', 'BootNext', bytes(2))
    marker(audit, 'before-undo-windows')
    restore_windows_order()
    marker(audit, 'after-undo-default-windows')
    marker(audit, 'after-undo-without-linux', detached=True)
    save('first-order-result', dict(status='passed', grub_promotion=promoted, default_undo='Windows-first; no erase'))
    # A separate fresh install, same protected bytes, reversed enumeration.
    # Discard only the closed disposable Linux target; preserve all evidence.
    closed = subprocess.run(['fuser', str(WORK / 'target.raw')], capture_output=True)
    assert closed.returncode == 1 and not closed.stdout.strip()
    assert (WORK / 'target.raw').resolve().is_relative_to(WORK)
    (WORK / 'target.raw').unlink()
    with (WORK / 'target.raw').open('xb') as output:
        output.truncate(49 * 1024 ** 3)
    shutil.copyfile(pristine_vars, WORK / 'vars.fd')
    EVIDENCE = EVIDENCE / 'protected-second'
    EVIDENCE.mkdir()
    sw.EVIDENCE = EVIDENCE
    Guest.order = 'protected-second'
    reverse = Audit()
    compare_disk(audit.disk, reverse.disk)
    shutil.copyfile(WORK / 'vars.fd', EVIDENCE / 'pre-firmware-vars.fd')
    marker(reverse, 'baseline-firmware', baseline=True)
    install(reverse, password, password_hash)
    set_variable(WORK / 'vars.fd', 'BootNext', bytes(2))
    marker(reverse, 'after-install-without-linux', detached=True)
    save('result', dict(status='passed', install_both_orders=True, offline_protected_disk_unchanged=True,
                        windows_boot_without_linux_after_install_and_undo=True, grub_promotion=promoted))
    print('TWO-DISK INSTALL PASSED IN BOTH DRIVE ORDERS; FIRST-ORDER SWITCH/ROLLBACK/UNDO PASSED', flush=True)


if __name__ == '__main__':
    main()
