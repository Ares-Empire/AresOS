"""Package14: the owner route, physical commands, unchanged disk/firmware audits."""
import base64
import hashlib
import inspect
import json
import os
import pathlib
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import time

import two_disk_vm as td
import switch_vm as sw
import keyboard_vm as kb
import keyboard_entries as ke
import offline_webui
import owner_console
from owner_keys import physical_keys
from owner_media import Media

COMMANDS = json.loads(pathlib.Path('os/owner-tools/commands.json').read_text())
PROFILE = 'de'
TEXT = 'yz-/!ü'
PROBE_MEDIA = None
OWNER_COMMAND_TIMEOUT = 900
OWNER_RESULT_WAIT = 840


def type_text(guest, text, layout=None):
    if text:
        # Shared by all physical consoles/observers, including hidden input.
        guest.owner_input_epoch = getattr(guest, 'owner_input_epoch', 0) + 1
    for char in text:
        guest.keys(physical_keys(char, layout or guest.owner_layout))
        time.sleep(0.12)


class Guest(td.Guest):
    network_up = False
    owner_media = None
    owner_layout = 'de'

    def network_args(self):
        # No host-forwarded NIC is needed: live WebUI uses virtio-serial.
        return 'user,model=virtio-net-pci,id=owner-net'

    def peripheral_args(self):
        args = ['-device', 'virtio-vga,addr=0x4', '-device', 'qemu-xhci,id=usb-controller,addr=0x5',
                '-device', 'usb-kbd,bus=usb-controller.0,port=1']
        if self.mode == 'live':
            path = td.WORK / 'owner-webui.sock'
            if path.is_socket():
                path.unlink()
            args += ['-device', 'virtio-serial-pci,id=owner-webui-bus,addr=0x7',
                '-chardev', f'socket,id=owner-webui,path={path},server=on,wait=off',
                '-device', 'virtserialport,bus=owner-webui-bus.0,chardev=owner-webui,name=ares.webui']
        return args

    def boot_args(self):
        return [*super().boot_args(), '-S']

    def __init__(self, *args, **kwargs):
        self.webui_server = None
        self.webui_socket = None
        self.owner_signed_in = False
        super().__init__(*args, **kwargs)
        # The CPU has never run. Set carrier before even the firmware starts.
        self.monitor.command('set_link', {'name': 'owner-net', 'up': self.network_up})
        self.monitor.command('cont')
        td.save(f'boot-{self.boot_number}-owner-route', dict(network_up=self.network_up,
            configured_before_cpu_start=True, tools_storage_attached=False))

    def prepare_registry_auth(self, encoded_auth=None):
        # The physical `login` command is the only credential writer in the guest.
        pass

    def login(self):
        super().login()
        self.owner_signed_in = True
        if not self.network_up:
            self.assert_offline('stock-offline-login')

    def login_live(self):
        super().login_live()
        self.owner_signed_in = True

    def assert_offline(self, stage):
        result = self.capture_json(stage, sw.framed('''python3 - <<'PY'
import json,pathlib
rows=[]
for p in pathlib.Path('/sys/class/net').iterdir():
    if (p/'device').exists():
        flags=int((p/'flags').read_text(),16)
        try: carrier=(p/'carrier').read_text().strip()
        except OSError:
            assert not flags&1, 'An up physical interface has unreadable carrier'
            carrier='0'
        rows.append(dict(name=p.name,carrier=carrier,flags=flags,operstate=(p/'operstate').read_text().strip()))
assert rows and all(row['carrier']=='0' for row in rows)
print(json.dumps(dict(status='passed',interfaces=rows,physical_link_down=True)))
PY'''))
        assert result['physical_link_down']

    def start_offline_webui_transport(self):
        self.assert_offline('live-offline-before-webui')
        raw = base64.b64encode(pathlib.Path('os/ci/offline_webui.py').read_bytes()).decode()
        self.command('live-offline-byte-transport', "set -e; printf %s " + shlex.quote(raw) +
            ' | base64 -d > /run/owner-offline-webui.py\npython3 /run/owner-offline-webui.py > /run/owner-offline-webui.log 2>&1 < /dev/null &')
        self.webui_socket = self.connect('owner-webui.sock')
        bridge = offline_webui.Bridge(offline_webui.Channel(self.webui_socket.recv, self.webui_socket.send))
        self.webui_server = bridge.server()
        td.save('offline-webui-transport', dict(status='started', channel='virtio-serial',
            destination='guest loopback:8080', external_nic_carrier=0, request_bodies_logged=False))

    def media_absent(self, stage):
        assert not self.owner_media or not self.owner_media.attached, 'PLAN-GAP: tools stick across a reboot/shutdown'
        blocks = self.monitor.command('query-block')
        assert not any(b.get('inserted', {}).get('node-name') == 'owner-tools' for b in blocks)
        td.save(stage + '-tools-absent', dict(status='passed', boot=self.boot_number, qmp_blocks=blocks))

    def finish_shutdown(self, stage, expected, timeout=180):
        self.media_absent(stage)
        return super().finish_shutdown(stage, expected, timeout=timeout)

    def poweroff(self, stage):
        if self.mode == 'live' and PROBE_MEDIA is not None and not getattr(self, 'media_probe_done', False) \
                and not getattr(self, 'failed_command', False) and sys.exc_info()[0] is None:
            probe_media(self, PROBE_MEDIA)
            self.media_probe_done = True
        self.media_absent(stage)
        return super().poweroff(stage)

    def close(self, stage):
        try:
            if self.webui_server:
                self.webui_server.shutdown()
                self.webui_server.server_close()
                self.webui_server = None
            if self.webui_socket:
                self.webui_socket.close()
                self.webui_socket = None
        finally:
            super().close(stage)


def retain_vcsa(tty, stage, phase, raw):
    path = td.EVIDENCE / (stage + '-timeout-' + str(phase) + '.vcsa')
    path.write_bytes(raw)
    td.save(path.stem, dict(sha256=hashlib.sha256(raw).hexdigest(), path=path.name,
        tty=tty, rows=raw[0], columns=raw[1], cursor_x=raw[2], cursor_y=raw[3]))


def wait_tty(guest, tty, predicate, stage, timeout=90, resync=None):
    def sample(seconds):
        return guest.capture_json(stage, sw.framed('python3 -c ' + shlex.quote(
            owner_console.source(tty, predicate, seconds))))
    owner_console.wait(sample, timeout,
        lambda phase, raw: retain_vcsa(tty, stage, phase, raw), resync=resync,
        record=lambda event: td.save(stage + '-resync-' + str(event['attempt']),
            dict(stage=stage, tty=tty, **event)))


def diagnostic_reader(before=None, command=None, folders=('/var/lib/ares/records', '/run/ares-owner-diagnostics'), timeout=OWNER_RESULT_WAIT):
    """Read only private owner JSON, including pre-install STOP records."""
    source = '''import json,pathlib,stat,time
folders=@FOLDERS@
def records():
    found=[]
    for folder in folders:
        root=pathlib.Path(folder)
        if not root.exists():
            assert not root.is_symlink(), 'Diagnostic directory is a broken link'
            continue
        info=root.lstat()
        assert stat.S_ISDIR(info.st_mode) and not root.is_symlink() and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o700, 'Diagnostics are not private'
        for p in root.glob('*.json'):
            info=p.lstat()
            assert stat.S_ISREG(info.st_mode) and not p.is_symlink() and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o600, 'Diagnostic record is not private'
            found.append(p)
    return found
'''.replace('@FOLDERS@', repr(folders))
    if before is None:
        return source + 'print(json.dumps([str(p) for p in records()]))\n'
    assert 0 < timeout <= OWNER_RESULT_WAIT < OWNER_COMMAND_TIMEOUT
    return source + '''before=set(@BEFORE@)
deadline=time.monotonic()+@TIMEOUT@
while time.monotonic()<deadline:
    paths=[p for p in records() if str(p) not in before and p.name.endswith('-@COMMAND@.json')]
    if paths:
        assert len(paths)==1, 'Ambiguous owner command records'
        result=json.loads(paths[0].read_text())
        assert result['status'] in ('passed','stopped')
        print(json.dumps(result));break
    time.sleep(.5)
else: raise SystemExit('Owner command did not finish')
'''.replace('@BEFORE@', repr(before)).replace('@COMMAND@', command).replace('@TIMEOUT@', repr(timeout))


class Console:
    def __init__(self, guest, tty='tty3'):
        self.guest, self.tty = guest, tty
        self.root = False
        self.completed_epoch = None

    def select(self):
        self.guest.keys(['ctrl', 'alt', 'f' + self.tty[3:]])

    def prompt(self, stage):
        epoch = getattr(self.guest, 'owner_input_epoch', 0)
        idle = self.completed_epoch is not None and self.completed_epoch == epoch
        def resync():
            nonlocal epoch
            assert getattr(self.guest, 'owner_input_epoch', 0) == epoch, 'Input revoked idle proof'
            type_text(self.guest, '\n')
            epoch = self.guest.owner_input_epoch
        try:
            wait_tty(self.guest, self.tty, "bool(re.search(r'[$#]$',line))", stage,
                resync=resync if idle else None)
        except BaseException:
            self.completed_epoch = None
            raise
        self.completed_epoch = getattr(self.guest, 'owner_input_epoch', 0)

    def hidden(self, stage):
        source = ('import base64,json,os,pathlib,termios,time\n' + owner_console.foreground_source()) + '''
hidden=False
observation={}
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    try:
        fd=os.open('/dev/@TTY@',os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
        try:
            echo=bool(termios.tcgetattr(fd)[3]&termios.ECHO)
            shell=foreground_is_shell(fd,observation)
        finally: os.close(fd)
        hidden=not echo and not shell
        if hidden: break
    except (OSError,termios.error): pass
    time.sleep(0.1)
raw=pathlib.Path('/dev/vcsa@NUMBER@').read_bytes() if not hidden else b''
print(json.dumps(dict(ready=hidden,observation=observation if not hidden else {},raw=base64.b64encode(raw).decode())))
'''.replace('@TTY@', self.tty)
        source = source.replace('@NUMBER@', self.tty[3:])
        value = self.guest.capture_json(stage, sw.framed('python3 -c ' + shlex.quote(source)))
        assert type(value['ready']) is bool
        if not value['ready']:
            retain_vcsa(self.tty, stage, 1, base64.b64decode(value['raw'], validate=True))
            raise AssertionError('No hidden prompt')

    def login(self, password, stage, wrong=False):
        self.select()
        wait_tty(self.guest, self.tty, "line.endswith('login:')", stage + '-login-prompt')
        self.guest.screenshot_safe = False
        type_text(self.guest, 'ares-recovery\n')
        self.hidden(stage + '-password-prompt')
        # The failure fixture deliberately uses German physical positions while
        # the loaded map is plain US. This does not claim the password was typed.
        type_text(self.guest, password + '\n', 'de' if wrong else None)
        if wrong:
            self.resync_serial_after_hidden(stage)
            wait_tty(self.guest, self.tty, "'Login incorrect' in full and line.endswith('login:')", stage + '-rejected')
            self.guest.command(stage + '-no-session', 'set -e; if pgrep -t ' + self.tty + ' -u 1000 -x bash; then exit 1; fi')
            td.save(stage + '-failure', dict(status='expected-login-rejected', loaded_profile='us',
                physical_positions='de', original_administrator_retained=True, reboot_permitted=False))
            return
        self.after_hidden(stage + '-account-login')
        self.guest.owner_physical_signed_in = True
        self.guest.screenshot_safe = True

    def become_root(self, password, stage):
        self.prompt(stage + '-ready')
        type_text(self.guest, 'sudo -k\nsudo -i\n')
        self.hidden(stage + '-sudo-hidden')
        self.guest.screenshot_safe = False
        type_text(self.guest, password + '\n')
        self.after_hidden(stage + '-sudo')
        self.root = True
        self.guest.screenshot_safe = True

    def records(self):
        return self.guest.capture_json('owner-record-list', sw.framed('python3 -c ' + shlex.quote(diagnostic_reader())))

    def resync_serial_after_hidden(self, stage):
        # The UART's previous hidden-read observation completed. Drain/resync
        # that separate channel before another framed transfer, without sending
        # Enter to the still-running physical owner command.
        serial = self.guest.resync_after_hidden(stage)
        td.save(stage + '-serial-resync', serial)

    def after_hidden(self, stage):
        epoch = self.guest.owner_input_epoch
        self.completed_epoch = None
        self.resync_serial_after_hidden(stage)
        value = self.guest.capture_json(stage + '-physical-idle', sw.framed('python3 -c ' + shlex.quote(
            owner_console.hidden_idle_source(self.tty, OWNER_RESULT_WAIT))))
        assert type(value['ready']) is bool, 'Invalid hidden idle observation'
        assert self.guest.owner_input_epoch == epoch, 'Input revoked hidden completion observation'
        if not value['ready']:
            retain_vcsa(self.tty, stage + '-physical-idle', 1, base64.b64decode(value['raw'], validate=True))
            raise AssertionError('Hidden owner command did not return to an idle shell')
        assert type(value['echo_enabled']) is bool and value['foreground_shell'], 'Hidden completion authority absent'
        self.completed_epoch = epoch
        # The original strict cursor predicate, three samples and at most two
        # recorded physical Enters apply only after the foreground shell returns.
        self.prompt(stage + '-after-hidden-ready')
        td.save(stage + '-hidden-completed', dict(status='passed', echo_enabled=value['echo_enabled'],
            foreground_shell=True, input_epoch=epoch, token_recorded=False))

    def run(self, name, stage, inputs=(), password=None, expect_stop=False):
        self.select()
        self.prompt(stage + '-ready')
        before = self.records()
        type_text(self.guest, COMMANDS[name] + '\n')
        hidden_input = password is not None
        if password is not None:
            self.hidden(stage + '-sudo-hidden')
            self.guest.screenshot_safe = False
            type_text(self.guest, password + '\n')
        for prompt, value, hidden in inputs:
            if hidden:
                hidden_input = True
                self.hidden(stage + '-hidden-input')
                self.guest.screenshot_safe = False
            else:
                wait_tty(self.guest, self.tty, repr(prompt) + ' in full', stage + '-input-ready')
            type_text(self.guest, value + '\n')
        if hidden_input:
            self.after_hidden(stage)
        if name == 'reboot' and not expect_stop:
            self.guest.media_absent(stage)
            self.guest.finish_shutdown(stage, 'guest-reset')
            return
        command = COMMANDS[name].split('/at ', 1)[-1].split()[0] if name != 'install' else 'install'
        source = diagnostic_reader(before, command)
        result = self.guest.capture_json(stage + '-owner-result', sw.framed('python3 -c ' + shlex.quote(source)))
        # Save before checking acceptance: an unexpected STOP is the evidence
        # needed to diagnose the failure, not an excuse to lose its record.
        td.save(stage + '-owner-diagnostics', result)
        assert result['status'] == ('stopped' if expect_stop else 'passed'), 'Owner command failed: ' + stage
        self.prompt(stage + '-completed')
        self.guest.screenshot_safe = True
        if not expect_stop:
            self.guest.screenshot(stage + '-owner-pass')
        td.save(stage + '-command', dict(command=COMMANDS[name], physical=True, status=result['status'], profile=self.guest.owner_layout))
        return result

    def logout(self, stage):
        self.select()
        self.prompt(stage + '-ready')
        if self.root:
            type_text(self.guest, 'exit\n')
            self.prompt(stage + '-user-ready')
        type_text(self.guest, 'sudo -k\nexit\n')
        wait_tty(self.guest, self.tty, "line.endswith('login:')", stage + '-getty-returned')
        self.guest.command(stage + '-no-session', 'set -e; if pgrep -t ' + self.tty + ' -u 1000 -x bash; then exit 1; fi')


def probe_media(guest, media):
    media.attach(guest, 'probe')
    source = '''set -e
mkdir -p /run/owner-probe-stick
mount -o ro,nodev,nosuid,noexec LABEL=ARESTOOLS /run/owner-probe-stick
trap 'umount /run/owner-probe-stick' EXIT
python3 - <<'PY'
import runpy,pathlib
root=pathlib.Path('/run/owner-probe-stick/ares-tools')
module=runpy.run_path(str(root/'owner.py'),run_name='owner_probe')
assert module['checked_bundle'](root)==@FINGERPRINT@
print('LIVE_TOOLS_BUNDLE_MATCHED_WINDOWS_COPY')
PY
'''.replace('@FINGERPRINT@', repr(media.fingerprint))
    guest.command('probe-media-manifest', source)
    media.detach(guest, 'probe')


def keyboard(guest, stage, profile, temporary_old=None):
    value = guest.capture_json(stage + '-loaded-keyboard', sw.framed('''python3 - <<'PY'
import json,pathlib,subprocess
reply=json.loads(subprocess.check_output(['busctl','--system','--json=short','call','org.freedesktop.locale1','/org/freedesktop/locale1','org.freedesktop.DBus.Properties','GetAll','s','org.freedesktop.locale1']))
print(json.dumps(dict(console=pathlib.Path('/etc/vconsole.conf').read_text(),x11=pathlib.Path('/etc/X11/xorg.conf.d/00-keyboard.conf').read_text(),
    localed=reply,loaded_map=subprocess.check_output(['dumpkeys','-C','/dev/tty3','--keys-only'],text=True),cmdline=pathlib.Path('/proc/cmdline').read_text(),
    bls={str(p):p.read_text() for p in pathlib.Path('/boot/loader/entries').glob('*.conf')})))
PY'''))
    fields = value['localed']['data'][0]
    assert fields['VConsoleKeymap']['data'] == profile
    assert fields['X11Layout']['data'] == ('de' if profile == 'de' else 'us')
    assert fields['X11Variant']['data'] == ('intl' if profile == 'us-intl' else '')
    kb.loaded_map(value['loaded_map'], 'de' if profile == 'de' else 'us')
    texts = value['bls'].values()
    if temporary_old is not None:
        snapshot = kb.deployment_snapshot(guest, stage + '-temporary-stock')
        resolved = {e['file']: ke.entry_identity(e['deployment']) for e in snapshot['bls']}
        assert sum(identity == temporary_old for identity in resolved.values()) == 1
        texts = [text for file,text in value['bls'].items() if resolved[file] != temporary_old]
    for words in [value['cmdline'].split(), *[shlex.split(line)[1:] for text in texts for line in text.splitlines() if line.startswith('options ')]]:
        assert not any(re.match(r'(?:rd\.)?vconsole\.keymap(?:[._]toggle)?(?:=|$)', word) for word in words)
    return value


def public_typing(guest, stage, profile, console, foot=False):
    global PROFILE
    PROFILE = profile
    guest.owner_layout = profile
    # Reuse the existing observer and real terminal reader; only physical
    # positions now come from the exact three ISO maps, including the umlaut.
    kb.TEXT = TEXT
    kb.type_text = type_text
    kb.physical_keys = lambda char, unused: physical_keys(char, PROFILE)
    console.select()
    console.prompt(stage + '-public-ready')
    kb.physical_input(guest, stage + '-console', 'de' if profile == 'de' else 'us', 0 if console.root else 1000)
    if foot:
        kb.foot(guest, stage, 'de' if profile == 'de' else 'us')
        console.select()


def finish(guest, audit, stage):
    try:
        if guest.process.poll() is None and not getattr(guest, 'failed_command', False) and sys.exc_info()[0] is None \
                and not getattr(guest, 'stopped_events_verified', False):
            guest.poweroff(stage)
    finally:
        guest.close(stage)
        audit.check(stage, guest)


def common_boot(guest, stage, profile, password, stock, release, ares=False):
    guest.owner_layout = profile
    state = kb.deployment_snapshot(guest, stage)
    ke.retained_pair(state, stock, release)
    expected = release.split('@')[1] if ares else json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference'].split('@')[1]
    assert sw.booted_digest(state['bootc']) == expected
    if not ares:
        assert ke.key(next(d for d in state['rpm']['deployments'] if d['booted'])) == ke.key(stock)
    keyboard(guest, stage, profile)
    console = Console(guest)
    console.login(password, stage)
    console.become_root(password, stage)
    console.run('check', stage + '-check')
    public_typing(guest, stage, profile, console, foot=ares)
    if ares:
        guest.command(stage + '-policy', pathlib.Path('os/tests/guest.sh').read_text())
    output = guest.command(stage + '-homebrew', pathlib.Path('os/tests/inherited-homebrew.sh').read_text().replace('@STAGE@', 'aresos' if ares else 'stock'))
    hashes = re.findall(r'^([0-9a-f]{64})  /', output, re.M)
    assert len(hashes) == 1
    return console, hashes[0]


def qualification(audit, media, password, hashed):
    release = json.loads(pathlib.Path('os/manifest/release.json').read_text())['reference']
    Guest.network_up = False
    td.install(audit, password, hashed)
    guest = td.start_installed(password, hashed, 'stock', firmware_default=True)
    try:
        raw = kb.deployment_snapshot(guest, 'offline-first-stock')
        status = raw['bootc']['status']
        assert raw['rpm']['transaction'] is None and not status.get('staged') and not status.get('rollbackQueued')
        assert not any(d.get('staged') or d['pinned'] for d in raw['rpm']['deployments'])
        guest.assert_offline('offline-first-stock-link')
        td.save('offline-first-stock-result', dict(status='passed', hardware_setup_finished=True, staged=False,
            rollback_queued=False, tools_attached=False, network_up=False))
    finally:
        finish(guest, audit, 'offline-first-stock')
    td.restore_windows_order('offline-tools-roundtrip')
    audit.windows_default = True
    td.marker(audit, 'offline-roundtrip-unattended-windows')
    td.marker(audit, 'offline-roundtrip-detached-windows', detached=True)
    guest = td.start_installed(password, hashed, 'tools-stock')
    try:
        guest.owner_layout = 'de'
        kb.deployment_snapshot(guest, 'tools-stock-before-prepare')
        console = Console(guest)
        console.login(password, 'tools-stock')
        console.become_root(password, 'tools-stock')
        media.attach(guest, 'tools-stock')
        console.run('install', 'tools-install', inputs=(('Photographed Crucial serial:', 'CRUCIAL-TARGET', False),
            ('Windows baseline Micron serial:', 'MICRON-KEEP', False)))
        console.run('prepare', 'tools-prepare')
        rerun = console.run('prepare', 'tools-prepare-rerun')
        assert not any(r.get('mutation') for r in rerun['trace']), 'Prepared rerun mutated the OS'
        prepared = guest.capture_json('owner-prepared', sw.framed('cat /var/lib/ares/records/prepared.json'))
        stock = prepared['stock']
        before = kb.deployment_snapshot(guest, 'before-first-network')
        ke.unchanged_old(raw, before)
        Guest.network_up = True
        guest.monitor.command('set_link', {'name': 'owner-net', 'up': True})
        guest.command('first-network-ready', '''set -e
for n in {1..60}; do
    status=$(curl --connect-timeout 2 --max-time 4 -s -o /dev/null -w '%{http_code}' https://ghcr.io/v2/ || true)
    if test "$status" = 401; then echo NETWORK_AVAILABLE_AFTER_PREPARE; exit 0; fi
    sleep 1
done
exit 1''', timeout=360)
        console.run('title', 'after-first-network-title')
        console.run('records', 'after-first-network-records')
        after = kb.deployment_snapshot(guest, 'after-first-network')
        assert before == after, 'Network changed deployments/pins/pending/BLS'
        console.run('export', 'tools-record-export')
        media.detach(guest, 'tools-stock')
        console.run('title', 'tools-before-reboot-title')
        console.run('reboot', 'tools-stock-reboot')
    finally:
        finish(guest, audit, 'tools-stock')
    td.marker(audit, 'prepared-unattended-windows')
    guest = td.start_installed(password, hashed, 'corrected-stock')
    try:
        guest.owner_layout = 'de'
        snapshot = kb.deployment_snapshot(guest, 'corrected-stock')
        assert ke.key(next(d for d in snapshot['rpm']['deployments'] if d['booted'])) == ke.key(stock)
        assert dict(rpm=snapshot['rpm'], bootc=snapshot['bootc']) == prepared['state']
        old = [ke.key(d) for d in snapshot['rpm']['deployments'] if not d['booted']]
        keyboard(guest, 'corrected-stock', 'de', temporary_old=old[0] if old else None)
        console = Console(guest)
        console.login(password, 'corrected-stock')
        console.become_root(password, 'corrected-stock')
        console.run('title', 'corrected-stock-title')
        console.run('records', 'corrected-stock-records')
        public_typing(guest, 'corrected-stock', 'de', console)
        output = guest.command('corrected-stock-homebrew', pathlib.Path('os/tests/inherited-homebrew.sh').read_text().replace('@STAGE@', 'stock'))
        brew, = re.findall(r'^([0-9a-f]{64})  /', output, re.M)
        console.run('login', 'private-owner-login', inputs=(('GitHub username:', os.environ['GITHUB_ACTOR'], False),
            ('', os.environ['GH_TOKEN'], True)))
        console.run('verify', 'owner-signature')
        console.run('switch', 'owner-switch')
        sw.inspect_transaction(guest.capture_json('owner-switch-pending', sw.framed('bootc status --json')), release, stock['checksum'])
        kb.deployment_snapshot(guest, 'owner-switch-staged')
        console.run('title', 'owner-switch-title')
        console.run('reboot', 'owner-switch-reboot')
    finally:
        finish(guest, audit, 'corrected-stock')
    for stage, profile in (('aresos', 'de'), ('aresos-intl', 'us-intl'), ('aresos-back-de', 'de')):
        guest = td.start_installed(password, hashed, stage)
        try:
            console, observed_brew = common_boot(guest, stage, profile, password, stock, release, ares=True)
            assert observed_brew == brew
            if stage == 'aresos':
                console.run('logs', 'owner-logind-diagnostics')
                console.run('layout-us', 'layout-us-begin')
                guest.owner_layout = 'us'
                console.run('reboot', 'layout-unproved-reboot-refusal', expect_stop=True)
                second = Console(guest, 'tty4')
                second.login(password, 'layout-plain-us', wrong=True)
                console.select()
                console.run('layout-revert', 'layout-us-revert')
                guest.owner_layout = 'de'
                second.login(password, 'layout-reverted-login')
                second.run('layout-proof', 'layout-reverted-proof', inputs=(('Physically type', 'yz-/!ü', False),), password=password)
                second.logout('layout-reverted-logout')
                console.select()
                console.run('layout-finish', 'layout-revert-finish')
                console.run('layout-intl', 'layout-intl-begin')
                guest.owner_layout = 'us-intl'
                second.login(password, 'layout-intl-login')
                second.run('layout-proof', 'layout-intl-proof', inputs=(('Physically type', 'yz-/!ü', False),), password=password)
                second.logout('layout-intl-logout')
                console.select()
                console.run('layout-finish', 'layout-intl-finish')
            elif stage == 'aresos-intl':
                console.run('layout-de', 'layout-de-begin')
                guest.owner_layout = 'de'
                second = Console(guest, 'tty4')
                second.login(password, 'layout-back-de-login')
                second.run('layout-proof', 'layout-back-de-proof', inputs=(('Physically type', 'yz-/!ü', False),), password=password)
                second.logout('layout-back-de-logout')
                console.select()
                console.run('layout-finish', 'layout-de-finish')
            else:
                console.run('rollback', 'owner-rollback')
                sw.inspect_transaction(guest.capture_json('owner-rollback-pending', sw.framed('bootc status --json')),
                    stock['container-image-reference'].removeprefix('ostree-image-signed:docker://').removeprefix('ostree-unverified-registry:'),
                    stock['checksum'], rollback=True, digest=stock['container-image-reference-digest'])
                ke.retained_pair(kb.deployment_snapshot(guest, 'owner-rollback-queued'), stock, release, queued=True)
            console.run('title', stage + '-reboot-title')
            console.run('reboot', stage + '-owner-reboot')
        finally:
            finish(guest, audit, stage)
    for stage in ('rollback-stock', 'default-stock'):
        guest = td.start_installed(password, hashed, stage)
        try:
            console, observed_brew = common_boot(guest, stage, 'de', password, stock, release)
            assert observed_brew == brew
            kb.capture_stock_greeter(guest, td.EVIDENCE, stage + '-greeter')
            if stage == 'rollback-stock':
                refused = console.run('rollback', 'rollback-from-stock-refused', expect_stop=True)
                assert not any(r.get('mutation') for r in refused['trace'])
                console.run('keep-stock', 'owner-keep-stock')
                console.run('title', 'owner-keep-stock-title')
                console.run('reboot', 'owner-keep-stock-reboot')
            else:
                rows = kb.deployment_snapshot(guest, stage + '-default-verified')['rpm']['deployments']
                assert rows[0]['booted'] and ke.key(rows[0]) == ke.key(stock)
                console.logout('default-stock-logout')
        finally:
            finish(guest, audit, stage)
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)
    td.save('owner-tools-result', dict(status='passed', commit=os.environ['GITHUB_SHA'], order='protected-second',
        release=release, offline_install=True, offline_hardware_boot=True, windows_roundtrip=True,
        tools_hotplug=True, tools_removed_before_every_reboot=True, bundle_manifest=media.fingerprint,
        prepare=True, prepare_rerun_zero_mutations=True, after_network_unchanged=True, record_export=True,
        owner_commands_physically_typed=True, password_contains_umlaut_and_punctuation=True,
        layout_failure_revert=True, layout_profiles=['de', 'us-failed', 'de-revert', 'us-intl', 'de'],
        fresh_second_console_proof=True, tty3_password_sudo=True, foot_physical=True,
        rollback_guard=True, rollback=True, keep_stock=True, next_stock_default=True,
        protected_disk_audits=True, nvram_rule_unchanged=True, bootnext_audits=True))


def main():
    global PROBE_MEDIA
    mode, = sys.argv[1:]
    assert mode in ('probe', 'owner-tools')
    authorization = json.loads(pathlib.Path('evidence/14-dispatch-authorization.json').read_text())
    assert authorization['allowance'] == '14' and authorization['native']['status'] == 'passed'
    assert authorization['native']['sha'] == os.environ['GITHUB_SHA']
    from owner_capabilities import CHECKS
    capabilities = json.loads(pathlib.Path('evidence/14-host-capabilities.json').read_text())
    assert capabilities['status'] == 'passed' and capabilities['sha'] == os.environ['GITHUB_SHA']
    assert all(capabilities['checks'].get(name) is True for name in CHECKS), 'STOP: host capabilities incomplete'
    if mode != 'probe':
        assert authorization['probe']['status'] == 'passed' and authorization['probe']['commit'] == os.environ['GITHUB_SHA']
    walk = json.loads(pathlib.Path('os/manifest/ci/14/host-walk/result.json').read_text())
    assert walk['status'] == 'passed' and walk['stick_across_reboot'] is False
    assert isinstance(walk['sources'], list) and walk['sources']
    assert len({row['path'] for row in walk['sources']}) == len(walk['sources']), 'Duplicate host source'
    for row in walk['sources']:
        assert list(row) == ['sha256', 'path'], 'Host source must put hash before path'
        assert hashlib.sha256(pathlib.Path(row['path']).read_bytes()).hexdigest() == row['sha256'], 'Host walk is stale'
    td.EVIDENCE.mkdir(parents=True, exist_ok=True)
    sw.WORK, sw.EVIDENCE = td.WORK, td.EVIDENCE
    td.Guest = sw.Guest = Guest
    Guest.order = 'protected-second'
    Guest.network_up = False
    for name in ('vmlinuz', 'initrd.img'):
        with (td.WORK / name).open('wb') as output:
            subprocess.run(['bsdtar', '-xOf', str(td.WORK / td.LIVE['filename']), 'images/pxeboot/' + name], stdout=output, check=True)
    media = Media()
    media.create()
    audit = td.Audit()
    shutil.copyfile(td.WORK / 'vars.fd', td.EVIDENCE / 'pre-firmware-vars.fd')
    td.marker(audit, 'baseline-firmware', baseline=True)
    if mode == 'probe':
        PROBE_MEDIA = media
        td.live_probe(audit)
        PROBE_MEDIA = None
        td.restore_windows_order('probe')
        audit.windows_default = True
        td.marker(audit, 'probe-detached-windows', detached=True)
        td.reset_target()
        td.save('probe-result', dict(status='passed', installed=False, both_orders=False, order='protected-second',
            review_validated=True, detached_windows=True, target_reset=True, owner_auth_read_only=True,
            native_job_auth=True, guest_credential_share=False, signature_verified=True, firmware_rule='11f-linux-position',
            stock_recipe_probe=True, failure_counter_probe=True, read_only_keyboard_proof=True,
            installed_keyboard_reader_probe=True, part_b_tools_probe=True, stock_idle_source_verified=True,
            bootnext_checked=True, bootloader_source_verified=True, offline_link=True, tools_hotplug=True,
            tools_absent_before_reboot=True, bundle_equality=True, host_walk=True, commit=os.environ['GITHUB_SHA']))
        return
    import crypt
    password = 'yz-/!ü' + secrets.token_hex(12)
    hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    print(f'::add-mask::{password}', flush=True)
    print(f'::add-mask::{hashed}', flush=True)
    try:
        qualification(audit, media, password, hashed)
    finally:
        del password, hashed


if __name__ == '__main__':
    main()
