"""Pinned ISO rehearsal on two writable file-backed disks, with offline gates."""
import json
import pathlib
import re
import shutil
import socket
import struct
import subprocess
import sys
import time

import switch_vm as sw
from disk_audit import (boot_variables, compare_disk, compare_nvram, offline_disk,
                        protected_writes, set_variable)

WORK = pathlib.Path('.work/installer').resolve()
EVIDENCE = pathlib.Path('evidence/two-disk').resolve()
LIVE = next(i for i in json.loads(pathlib.Path('os/manifest/installer-isos.json').read_text()) if i['kind'] == 'live')


def save(name, value):
    (EVIDENCE / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')


class Guest(sw.Guest):
    order = 'protected-first'
    mode = 'installed'

    def __init__(self, disk, password, secrets):
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

    def finish_shutdown(self, stage, reason, timeout=180):
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
        # -no-shutdown keeps QEMU alive with the guest stopped, so this final
        # counter includes shutdown/unmount writes too. Only then close it.
        self.writes(stage)
        self.monitor.command('quit')
        self.process.wait(timeout=15)
        (EVIDENCE / (stage + '-shutdown-console.txt')).write_text(sw.redact(output.decode(errors='replace'), self.secrets))
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

    def check(self, stage, guest=None, establish_nvram=False):
        observed = offline_disk(WORK / 'protected.raw', guest.process if guest else None)
        save(stage + '-protected', observed)
        compare_disk(self.disk, observed)
        nvram = boot_variables(WORK / 'vars.fd')
        save(stage + '-nvram', nvram)
        shutil.copyfile(WORK / 'vars.fd', EVIDENCE / (stage + '-vars.fd'))
        if establish_nvram:
            assert nvram['Boot0000'] == boot_variables(EVIDENCE / 'pre-firmware-vars.fd')['Boot0000']
            self.nvram = nvram
        else:
            assert self.nvram is not None
            save(stage + '-nvram-diff', compare_nvram(self.nvram, nvram))
        print(f'OFFLINE PROTECTED DISK UNCHANGED: {stage} {observed["sha256"]}', flush=True)


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
    Guest.mode = 'live'
    guest = Guest(WORK / 'target.raw', '', [])
    try:
        guest.login_live()
        layout = guest.capture_json('live-disks', sw.framed('lsblk --json --bytes --list --output NAME,TYPE,SIZE,SERIAL,PARTUUID,FSTYPE,MOUNTPOINTS'))
        save('live-assumptions', dict(order=Guest.order, layout=layout))
        guest.command('live-installer-evidence', '''set -e
cat /usr/lib/os-release
cat /etc/anaconda/profile.d/bazzite.conf
cat /usr/share/anaconda/interactive-defaults.ks
cat /usr/bin/liveinst
efibootmgr -v
''')
        guest.command('launch-installer-ui', 'PKEXEC_UID=$(id -u liveuser) liveinst > /tmp/rehearsal-installer-ui.log 2>&1 < /dev/null &\nsleep 30\npgrep -a -f anaconda')
        guest.keys(['ctrl', 'alt', 'f1'])
        time.sleep(5)
        guest.screenshot('live-installer-ui')
        guest.keys(['tab'])
        guest.keys(['ret'])
        time.sleep(5)
        guest.screenshot('live-installer-keyboard-probe')
        guest.writes('live-ui-probe')
        guest.poweroff('live-ui-probe')
    finally:
        guest.close('live-ui-probe')
        audit.check('live-ui-probe', guest)


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sw.WORK, sw.EVIDENCE = WORK, EVIDENCE
    for name in ('vmlinuz', 'initrd.img'):
        with (WORK / name).open('wb') as output:
            subprocess.run(['bsdtar', '-xOf', str(WORK / LIVE['filename']), 'images/pxeboot/' + name], stdout=output, check=True)
    audit = Audit()
    shutil.copyfile(WORK / 'vars.fd', EVIDENCE / 'pre-firmware-vars.fd')
    marker(audit, 'baseline-firmware', baseline=True)
    if sys.argv[1:] == ['probe']:
        live_probe(audit)
        save('probe-result', dict(status='inspection-only', installed=False))
        return
    raise RuntimeError('Full installation requires the recorded ISO/probe assumption audit')


if __name__ == '__main__':
    main()
