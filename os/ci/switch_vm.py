"""Stock upstream disk -> published release -> retained stock, through real logins.

Only a file-backed runner disk is attached. No test code is baked into either
deployment. Passwords and registry credentials never enter retained transcripts.
"""
import base64
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import time

from qmp import QMP
from serial_console import TerminalReplies, decode_export, encode_command
from greeter import capture_stock_greeter

WORK = pathlib.Path('switch-work').resolve()
EVIDENCE = pathlib.Path('evidence/switch').resolve()
ADMIN = 'ares-recovery'


def booted_reference(status):
    return status['status']['booted']['image']['image']['image']


def booted_digest(status):
    return status['status']['booted']['image']['imageDigest']


def inspect_transaction(status, target, stock_checksum, rollback=False, digest=None):
    """A successful transaction alone never authorizes the following reboot."""
    state = status['status']
    if rollback:
        assert state.get('rollbackQueued') is True, state
        assert not state.get('staged'), state
        selected = state['rollback']
    else:
        assert not state.get('rollbackQueued'), state
        selected = state['staged']
        assert state['booted']['ostree']['checksum'] == stock_checksum, state
    assert selected['image']['image']['image'] == target, selected
    assert selected['image']['imageDigest'] == (digest or target.split('@', 1)[1]), selected
    if rollback:
        assert selected['ostree']['checksum'] == stock_checksum, selected


def partition_identity(layout, disk_name='vda'):
    """Compare the sole attached file disk, including every partition identity.

    Zram is also reported as TYPE=disk, but its swap UUID changes at boot.
    It is not part of the attached vda file or its partition table.
    """
    devices = [item for item in layout['blockdevices']
               if item['name'] == disk_name or (item['type'] == 'part' and re.fullmatch(re.escape(disk_name) + r'[0-9]+', item['name']))]
    assert any(item['name'] == disk_name and item['type'] == 'disk' for item in devices), 'Attached target disk absent'
    assert any(item['type'] == 'part' for item in devices), 'Attached disk has no partitions'
    return [(item['name'], item['type'], item.get('start'), item['size'],
             item.get('partuuid'), item.get('parttype'), item.get('uuid')) for item in devices]


def redact(value, secrets):
    for secret in secrets:
        if secret:
            value = value.replace(secret, '<redacted>')
    # The interactive UI salts its own account hash. It differs from the
    # harness's precomputed hash and must not leak through installer errors.
    return re.sub(r'\$(?:6|5|y|gy|2[aby])\$[^\s\x27\x22<>]+', '<redacted-password-hash>', value)


def stock_initialization_reboot(console, events):
    """Accept only an orderly, pre-login reset, never panic/host termination."""
    resets = [event for event in events if event.get('event') == 'SHUTDOWN']
    return (len(resets) == 1 and resets[0].get('data') == {'guest': True, 'reason': 'guest-reset'}
            and bool(re.search(r'reboot: Restarting system', console))
            and not re.search(r'Kernel panic|Fatal exception|Oops:', console, re.I)
            and not any(event.get('event') == 'GUEST_PANICKED' for event in events))


def wait_for_exit_draining(console, process, timeout):
    """Keep QEMU's UART writable while the guest shuts down; bound the wait."""
    deadline = time.monotonic() + timeout
    output = bytearray()
    replies = TerminalReplies()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            if process.poll() is None:
                raise subprocess.TimeoutExpired(process.args, timeout, output=bytes(output))
            break
        console.settimeout(min(0.5, remaining))
        try:
            data = console.recv(65536)
        except socket.timeout:
            if process.poll() is not None:
                break
            continue
        if not data:
            break
        output.extend(data)
        reply = replies.feed(data)
        if reply:
            console.sendall(reply)
    try:
        process.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        raise subprocess.TimeoutExpired(process.args, timeout, output=bytes(output))
    return bytes(output)


class Guest:
    def __init__(self, disk, password, secrets):
        self.password = password
        self.secrets = secrets
        self.console = None
        self.monitor = None
        self.process = None
        self.transcript = ''
        self.boot_transcript = ''
        self.authentication_started = False
        self.screenshot_safe = True
        self.buffer = ''
        self.replies = TerminalReplies()
        for name in ('serial.sock', 'qmp.sock'):
            path = WORK / name
            if path.is_socket():
                path.unlink()
        accel = ['-accel', 'kvm', '-cpu', 'host'] if os.access('/dev/kvm', os.R_OK | os.W_OK) else ['-accel', 'tcg,thread=multi', '-cpu', 'max']
        (EVIDENCE / 'acceleration.txt').write_text(' '.join(accel) + '\n')
        self.process = subprocess.Popen([
            'qemu-system-x86_64', '-machine', 'q35', *accel, '-smp', str(min(4, len(os.sched_getaffinity(0)))), '-m', '6144',
            '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
            '-drive', f'if=pflash,format=raw,file={WORK / "vars.fd"}',
            *self.disk_args(disk),
            '-device', 'virtio-vga', '-device', 'qemu-xhci', '-device', 'usb-kbd',
            '-display', 'none', '-nic', self.network_args(),
            '-qmp', f'unix:{WORK / "qmp.sock"},server=on,wait=off',
            '-serial', f'unix:{WORK / "serial.sock"},server=on,wait=off', *self.boot_args(), '-no-reboot',
        ], stdout=open(EVIDENCE / 'qemu.txt', 'a'), stderr=subprocess.STDOUT)
        self.console = self.connect('serial.sock')
        self.console.settimeout(1)
        self.monitor_socket = self.connect('qmp.sock')
        self.monitor = QMP(self.monitor_socket)
        self.monitor.command('qmp_capabilities')

    def disk_args(self, disk):
        return ['-drive', f'file={disk},format=raw,if=virtio']

    def boot_args(self):
        return []

    def network_args(self):
        return 'user,model=virtio-net-pci'

    def connect(self, name):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            sock = socket.socket(socket.AF_UNIX)
            try:
                sock.connect(str(WORK / name))
                return sock
            except OSError:
                sock.close()
                assert self.process.poll() is None, 'QEMU exited before its socket opened'
                time.sleep(0.1)
        raise TimeoutError(f'QEMU socket absent: {name}')

    def wait(self, pattern, timeout=300):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            match = re.search(pattern, self.buffer)
            if match:
                result = self.buffer[:match.end()]
                self.buffer = self.buffer[match.end():]
                return result
            try:
                data = self.console.recv(65536)
            except socket.timeout:
                continue
            if not data:
                raise EOFError('Guest console closed')
            reply = self.replies.feed(data)
            if reply:
                self.console.sendall(reply)
            text = data.decode(errors='replace')
            self.buffer += text
            self.transcript += text
            if not self.authentication_started:
                self.boot_transcript += text
        raise TimeoutError(f'Guest console did not reach {pattern}')

    def send(self, text):
        self.console.sendall(text.encode())

    def login(self):
        # Kernel messages may follow the prompt in the same UART read.
        self.wait(r'\blogin: *')
        self.authentication_started = True
        self.send(ADMIN + '\n')
        self.wait(r'\b[Pp]assword: *')
        self.send(self.password + '\n')
        self.wait(r'[$#] ?(?:\x1b\[[0-9;]*[A-Za-z])*$', timeout=180)
        self.send("stty -echo; export PS1='ARESOS_PROMPT> '; printf '\\nARESOS_READY\\n'\n")
        self.wait(r'\r?\nARESOS_READY\r?\n')
        self.send("sudo -k; sudo -p 'ARESOS_SUDO_PASSWORD:' -v\n")
        self.wait('ARESOS_SUDO_PASSWORD:')
        self.send(self.password + '\n')
        self.wait('ARESOS_PROMPT> ')
        # Enter a root shell only after the actual account/password sudo check.
        # Fedora sudoers may preserve PS1. Establish the root prompt/marker in
        # the sudo command itself instead of guessing the distribution prompt.
        self.send("sudo -n bash --noprofile --norc -c 'stty -echo; export PS1=\"ARESOS_ROOT> \"; printf \"\\nARESOS_ROOT_READY\\n\"; exec bash --noprofile --norc -i'\n")
        self.wait(r'\r?\nARESOS_ROOT_READY\r?\n')
        self.command('root-authentication', 'set -e; test "$(id -u)" = 0; echo PASSWORD_AUTHENTICATED_ADMIN_SUDO_PASSED')

    def command(self, name, script, timeout=900, private=False):
        transcript_start = len(self.transcript)
        self.send(encode_command(script))
        try:
            output = self.wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n', timeout)
        except (TimeoutError, EOFError):
            if not private:
                (EVIDENCE / f'{name}-incomplete.txt').write_text(redact(self.transcript[transcript_start:], self.secrets))
            raise
        code = int(re.search(r'ARESOS_CMD_DONE:(\d+)', output).group(1))
        clean = redact(output, self.secrets)
        if not private:
            (EVIDENCE / f'{name}.txt').write_text(clean)
        assert code == 0, f'Guest command failed: {name}, exit {code}'
        return output

    def json_command(self, name, script):
        output = self.command(name, script)
        return {'stdout': output.split('ARESOS_CMD_DONE:')[0].strip()}

    def capture_json(self, name, command):
        output = self.command(name, command)
        value = json.loads(decode_export(output))
        (EVIDENCE / f'{name}.json').write_text(json.dumps(value, indent=2) + '\n')
        return value

    def keys(self, names):
        self.monitor.command('send-key', {'keys': [{'type': 'qcode', 'data': name} for name in names], 'hold-time': 100})

    def screenshot(self, name):
        from PIL import Image
        ppm = WORK / 'screen.ppm'
        self.monitor.command('screendump', {'filename': str(ppm)})
        with Image.open(ppm) as picture:
            picture.save(EVIDENCE / f'{name}.png')

    def type(self, text):
        codes = {' ': 'spc', '/': 'slash', '-': 'minus', '\n': 'ret'}
        for char in text:
            assert char.isascii() and (char.islower() or char.isdigit() or char in codes), char
            self.keys([codes.get(char, char)])
            time.sleep(0.12)

    def reboot(self, stage):
        self.send('systemctl reboot\n')
        output = b''
        try:
            output = wait_for_exit_draining(self.console, self.process, timeout=180)
        except subprocess.TimeoutExpired as error:
            output = error.output or b''
            raise
        finally:
            (EVIDENCE / f'{stage}-shutdown-console.txt').write_text(
                redact(output.decode(errors='replace'), self.secrets))
        assert self.process.returncode == 0
        assert any(event.get('event') == 'SHUTDOWN' for event in self.monitor.events)

    def close(self, stage):
        if self.boot_transcript:
            (EVIDENCE / f'{stage}-boot-console.txt').write_text(redact(self.boot_transcript, self.secrets))
        if self.process and self.process.poll() is None:
            if self.screenshot_safe:
                try:
                    self.screenshot(f'failure-{stage}')
                except Exception:
                    pass
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        # Raw console transcripts are deliberately not exported: interactive
        # authentication and private registry setup share this transport.
        if self.monitor:
            (EVIDENCE / f'{stage}-qmp.json').write_text(json.dumps(self.monitor.events, indent=2) + '\n')
            self.monitor_socket.close()
        if self.console:
            self.console.close()


def framed(command):
    # bootc can print a lock-wait spinner on its terminal stderr even with
    # --json. Capture stdout separately, then reuse the checksum-framed export
    # protocol that already tolerates interleaved kernel UART messages.
    return '''set -e
result=$(mktemp /run/aresos-json.XXXXXX)
trap 'rm -f "$result"' EXIT
''' + command + ''' > "$result"
python3 - "$result" <<'ARESOS_JSON_EXPORT'
import base64, hashlib, json, pathlib, sys
raw = pathlib.Path(sys.argv[1]).read_bytes()
json.loads(raw)
print('\\nARESOS_EXPORT_START')
print(base64.encodebytes(raw).decode(), end='')
print('ARESOS_EXPORT_END')
print('ARESOS_EXPORT_SHA256 ' + hashlib.sha256(raw).hexdigest() + '  guest.json')
ARESOS_JSON_EXPORT
'''


def start_guest(disk, password, secrets, stage):
    # Upstream bazzite-hardware-setup runs Before=systemd-user-sessions and
    # reboots once after applying needed kargs. Keep its normal behavior.
    for attempt in range(2 if stage == 'stock' else 1):
        guest = Guest(disk, password, secrets)
        try:
            guest.login()
            return guest
        except EOFError:
            guest.process.wait(timeout=15)
            guest.monitor.reader.join(timeout=5)
            # A two-disk observer can hold QEMU after guest shutdown to collect
            # final write counters, then explicitly quit it. Its separately
            # verified guest-event snapshot excludes only that later host quit;
            # the complete raw event stream is still retained by close().
            initialization_events = (guest.stopped_events if getattr(guest, 'stopped_events_verified', False)
                                     else guest.monitor.events)
            expected = (stage == 'stock' and attempt == 0 and not guest.authentication_started
                        and guest.process.returncode == 0
                        and stock_initialization_reboot(guest.boot_transcript, initialization_events))
            guest.close(f'{stage}-initialization-{attempt}')
            if not expected:
                raise
            (EVIDENCE / 'stock-initialization-reboot.json').write_text(json.dumps(dict(
                status='orderly-pre-login-reboot', count=1,
                source='https://github.com/ublue-os/bazzite/blob/2fab72cbc9a3257d80c607e173f22527aea3b39b/system_files/desktop/shared/usr/libexec/bazzite-hardware-setup',
                kernel_reboot_marker=True, qmp_guest_reset=True), indent=2) + '\n')
            print('Stock Bazzite completed an orderly pre-login initialization reboot; booting the same disk again', flush=True)
        except Exception:
            guest.close(stage)
            raise
    raise RuntimeError('Stock initialization did not reach an authenticated login')


def main(disk=None, preserve_vars=False, target_name='vda', shutdown_hook=None):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    password = json.loads((WORK / 'credentials.json').read_text())['password']
    token = os.environ['GH_TOKEN']
    auth = base64.b64encode(f'{os.environ["GITHUB_ACTOR"]}:{token}'.encode()).decode()
    auth_json = json.dumps({'auths': {'ghcr.io': {'auth': auth}}})
    encoded_auth = base64.b64encode(auth_json.encode()).decode()
    secrets = [password, token, auth, encoded_auth]
    release = json.loads(pathlib.Path('evidence/release.json').read_text())
    target = release['reference']
    upstream = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference']
    upstream_name, upstream_digest = upstream.split('@', 1)
    disks = [pathlib.Path(disk).resolve()] if disk else list((WORK / 'output').rglob('disk.raw'))
    assert len(disks) == 1 and disks[0].is_relative_to(WORK), disks
    if not preserve_vars:
        shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', WORK / 'vars.fd')
    before = None
    stock_commit = None
    stock_reference = None
    homebrew_hash = None
    for stage in ('stock', 'aresos', 'rollback', 'persistent-stock'):
        guest = start_guest(disks[0], password, secrets, stage)
        try:
            guest.command(f'{stage}-account', 'set -e; test "$(id -u ares-recovery)" = 1000; id ares-recovery; id -nG ares-recovery | grep -qw wheel')
            status = guest.capture_json(f'{stage}-status', framed('bootc status --json'))
            layout = guest.capture_json(f'{stage}-partitions', framed('lsblk --json --bytes --list --output NAME,TYPE,START,SIZE,PARTUUID,PARTTYPE,UUID'))
            if before is None:
                before = partition_identity(layout, target_name)
            else:
                assert partition_identity(layout, target_name) == before, f'Partition identity changed at {stage}'
            if stage == 'stock':
                guest.command('stock-hardware-setup', 'set -e; systemctl is-active bazzite-hardware-setup.service; test "$(systemctl show bazzite-hardware-setup.service -p ExecMainStatus --value)" = 0; journalctl -b -u bazzite-hardware-setup.service --no-pager; rpm-ostree kargs')
                stock_reference = booted_reference(status)
                assert stock_reference.startswith((upstream_name + '@sha256:', upstream_name + ':')), status
                assert booted_digest(status) == upstream_digest, status
                stock_commit = status['status']['booted']['ostree']['checksum']
                guest.command('stock-session', pathlib.Path('os/release/stock-session.sh').read_text())
                capture_stock_greeter(guest, EVIDENCE, 'stock-bazzite')
                homebrew_output = guest.command('stock-inherited-homebrew', pathlib.Path('os/tests/inherited-homebrew.sh').read_text().replace('@STAGE@', stage))
                # Pin the booted deployment by its actual checksum, never assume
                # a deployment index from an example or after another update.
                guest.command('pin-stock', pathlib.Path('os/release/pin-stock.sh').read_text())
                guest.command('private-auth', f"set -e; install -d -m 0700 /etc/ostree; printf '%s' '{encoded_auth}' | base64 -d > /etc/ostree/auth.json; chmod 0600 /etc/ostree/auth.json", private=True)
                verify = pathlib.Path('os/release/verify.sh').read_text()
                verify = verify.replace('@REFERENCE@', target).replace('@IDENTITY@', release['signature']['identity'])
                guest.command('verify-published-signature', verify)
                script = pathlib.Path('os/release/switch.sh').read_text().replace('@REFERENCE@', target)
                guest.command('switch', script, timeout=1500)
                pending = guest.capture_json('switch-inspection', framed('bootc status --json'))
                inspect_transaction(pending, target, stock_commit)
            elif stage == 'aresos':
                assert booted_reference(status) == target, status
                assert booted_digest(status) == target.split('@', 1)[1], status
                guest.command('aresos-policy', "set -e; for n in {1..120}; do pgrep -u ares -x foot && break; sleep 1; done\nbash /run/aresos-guest-check.sh".replace('bash /run/aresos-guest-check.sh', pathlib.Path('os/tests/guest.sh').read_text()))
                homebrew_output = guest.command('aresos-inherited-homebrew', pathlib.Path('os/tests/inherited-homebrew.sh').read_text().replace('@STAGE@', stage))
                guest.keys(['ctrl', 'alt', 'f1'])
                guest.screenshot('aresos-labwc')
                guest.keys(['ctrl', 'alt', 'f3'])
                guest.command('tty-getty-ready', '''set -e
for n in {1..120}; do
    if test "$(cat /sys/class/tty/tty0/active)" = tty3 && pgrep -t tty3 -x agetty; then exit 0; fi
    sleep 1
done
exit 1''')
                # QMP keyboard -> actual tty3 getty -> login -> sudo. The
                # independent serial channel only observes the resulting state.
                guest.screenshot_safe = False
                guest.type(ADMIN + '\n')
                guest.command('tty-password-ready', "python3 - <<'PY'\n"
                              + pathlib.Path('os/ci/tty_password.py').read_text() + '\nPY')
                guest.type(password + '\n')
                guest.command('tty-admin-session', '''set -e
for n in {1..120}; do
    sessions=$(loginctl list-sessions --no-legend | awk '$3 == "ares-recovery" {print $1}')
    for session in $sessions; do
        if test "$(loginctl show-session "$session" -p TTY --value)" = tty3; then
            loginctl show-session "$session" -p Name -p User -p TTY -p Type -p Active
            exit 0
        fi
    done
    sleep 1
done
exit 1''')
                guest.type('sudo -k\n')
                guest.type('sudo touch /run/aresos-tty-admin\n')
                guest.command('tty-sudo-prompt', 'set -e; for n in {1..30}; do pgrep -t tty3 -x sudo && exit 0; sleep 1; done; exit 1')
                time.sleep(1)
                guest.type(password + '\n')
                guest.command('tty-admin-login', 'set -e; for n in {1..30}; do if test -e /run/aresos-tty-admin; then test "$(stat -c %u /run/aresos-tty-admin)" = 0; echo RECOVERY_ADMIN_TTY3_LOGIN_AND_PASSWORD_SUDO_PASSED; exit 0; fi; sleep 1; done; exit 1')
                guest.screenshot_safe = True
                guest.screenshot('recovery-admin-tty3')
                guest.type('sudo -k\n')
                guest.type('exit\n')
                guest.command('tty-admin-logged-out', '''set -e
for n in {1..30}; do
    if pgrep -t tty3 -x agetty; then
        if pgrep -t tty3 -u 1000; then echo 'Administrator still logged in on tty3'; exit 1; fi
        echo RECOVERY_ADMIN_LOGGED_OUT_TTY3_GETTY_READY
        exit 0
    fi
    sleep 1
done
exit 1''')
                guest.screenshot('recovery-tty3-logged-out')
                guest.keys(['ctrl', 'alt', 'f1'])
                rollback = pathlib.Path('os/release/rollback.sh').read_text().replace('@BASE_DIGEST@', upstream_digest)
                guest.command('rollback', rollback)
                pending = guest.capture_json('rollback-inspection', framed('bootc status --json'))
                inspect_transaction(pending, stock_reference, stock_commit, rollback=True, digest=upstream_digest)
            else:
                assert booted_reference(status) == stock_reference, status
                assert booted_digest(status) == upstream_digest, status
                assert status['status']['booted']['ostree']['checksum'] == stock_commit, status
                guest.command(f'{stage}-stock-session', pathlib.Path('os/release/stock-session.sh').read_text())
                homebrew_output = guest.command(f'{stage}-inherited-homebrew', pathlib.Path('os/tests/inherited-homebrew.sh').read_text().replace('@STAGE@', stage))
                capture_stock_greeter(guest, EVIDENCE, f'{stage}-bazzite')
                if stage == 'rollback':
                    script = pathlib.Path('os/release/default-stock.sh').read_text().replace('@BASE_DIGEST@', upstream_digest).replace('@STOCK_CHECKSUM@', stock_commit)
                    guest.command('default-stock', script)
                ordered = guest.capture_json(f'{stage}-default-inspection', framed('rpm-ostree status --json'))
                assert ordered['deployments'][0]['booted'] and ordered['deployments'][0]['checksum'] == stock_commit, ordered
                assert not status['status'].get('staged') and not status['status'].get('rollbackQueued'), status
            hashes = re.findall(r'^([0-9a-f]{64})  /', homebrew_output, re.M)
            assert len(hashes) == 1, 'Missing or ambiguous inherited brew hash'
            if homebrew_hash is None:
                homebrew_hash = hashes[0]
            assert hashes[0] == homebrew_hash, f'Inherited Homebrew changed at {stage}'
            if stage == 'persistent-stock':
                (EVIDENCE / 'result.json').write_text(json.dumps(dict(status='passed',
                    release=target, stock=upstream, retained_stock_checksum=stock_commit,
                    recovery_admin_tty='/dev/tty3', recovery_admin_uid=1000,
                    daily_user_uid=1001, partition_identity_unchanged=True,
                    inherited_homebrew_daily_denied=True, inherited_homebrew_owner_working_all_stages=True,
                    recovery_admin_logged_out=True, stock_greeter_rendered=True,
                    stock_default_second_boot=True, grub_recovery_promotion='untested'), indent=2) + '\n')
                print('Published-image switch, policy, tty3 login/logout, partition equality, rendered stock rollback and second default boot passed; GRUB recovery promotion UNTESTED', flush=True)
            if stage != 'persistent-stock':
                guest.reboot(stage)
            elif shutdown_hook:
                guest.poweroff(stage)
        finally:
            guest.close(stage)
            if shutdown_hook:
                shutdown_hook(stage, guest)


if __name__ == '__main__':
    main()
