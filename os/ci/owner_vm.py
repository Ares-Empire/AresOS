"""Package14: the owner route, physical commands, unchanged disk/firmware audits."""
import base64
import contextlib
import hashlib
import inspect
import itertools
import json
import os
import pathlib
import re
import secrets
import shlex
import shutil
import socket
import string
import subprocess
import sys
import tempfile
import time

import two_disk_vm as td
import switch_vm as sw
import keyboard_vm as kb
import keyboard_entries as ke
import offline_webui
import owner_console
import owner_hidden
import owner_read_diagnostics
import owner_key_counter
import owner_counter_kernel
import owner_login
import owner_xhci
import reorder_probe as rp
from owner_keys import maps, physical_keys, at_keycodes
from owner_media import Media, bundle_module
from prepare_two_disks import wait_loop_partitions

COMMANDS = json.loads(pathlib.Path('os/owner-tools/commands.json').read_text())
TEXT = 'yz-/!ü'
PROBE_MEDIA = None
OWNER_COMMAND_TIMEOUT = 900
OWNER_RESULT_WAIT = 840
TOKEN_RESULT_WAIT = 180
PROMPT_WAIT_IDS = itertools.count(1)
SUDO_PROMPT = "[sudo] password for ares-recovery:"
TOKEN_PROMPT = "Read-only token (hidden):"
LAYOUT_PROMPT = 'Physically type'
KEY_HOLD_MS = 30
KEY_GAP_SECONDS = .12


def typing_profile(guest, layout=None):
    profile = guest.owner_layout if layout is None else layout
    assert profile in ('de', 'us', 'us-intl'), 'Unknown physical layout profile'
    return profile


def type_text(guest, text, layout=None, counts=None):
    profile = typing_profile(guest, layout)
    if text:
        # Shared by all physical consoles/observers, including hidden input.
        guest.owner_input_epoch = getattr(guest, 'owner_input_epoch', 0) + 1
    for char in text:
        keys = physical_keys(char, profile)
        guest.keys(keys)
        if counts is not None:
            counts['key_event_count'] += 2 * len(keys)  # QMP send-key presses/releases each key.
            counts['key_chord_count'] += 1
            counts['last_key_was_ret'] = keys == ['ret']


def type_token(guest, value, layout, counts, chunked):
    assert value and '\n' not in value and '\r' not in value, 'Token line break refused before input'
    if chunked:
        for offset in range(0, len(value), 16):
            if offset: time.sleep(1)
            type_text(guest, value[offset:offset+16], layout, counts=counts)
        time.sleep(1)
    else:
        type_text(guest, value, layout, counts=counts)
    # Return belongs exclusively to the counter-verified pre-Enter gate.


def private_login(console):
    # Generated only in memory. Add it to the existing redactor before any input.
    dummy = 'ghp_' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))
    console.guest.secrets.append(dummy)
    try:
        result = console.run('login', 'private-owner-dummy-login', inputs=(
            ('GitHub username:', os.environ['GITHUB_ACTOR'], False), (TOKEN_PROMPT, dummy, True)), expect_stop=True)
        assert result['error'] == 'Private release read failed; check read:packages permission/expiry and network; no credential was written', 'Unexpected owner-length token result'
    except BaseException:
        td.save('owner-length-token-proof', dict(status='stopped', length=40, value_recorded=False,
            real_ci_token_typed=False, reason='Owner-length token proof failed; preserve counts and owner diagnostics'))
        raise AssertionError('Owner-length token path STOP; keep administrator session; real CI token not typed') from None
    finally:
        del dummy
    td.save('owner-length-token-proof', dict(status='passed', length=40, value_recorded=False,
        outcome='expected-registry-refusal', guest_key_counts=console.last_hidden['received_keys'],
        comparison=console.last_hidden['key_comparison']))
    return console.run('login', 'private-owner-login', inputs=(('GitHub username:', os.environ['GITHUB_ACTOR'], False),
        (TOKEN_PROMPT, os.environ['GH_TOKEN'], True)), token_chunks=True)


class Guest(td.Guest):
    network_up = False
    owner_media = None
    owner_layout = 'de'
    run_secret_tainted = False
    keyboard_transport = 'QMP i8042/PS-2 AT keyboard'

    def screenshot(self, name):
        result=super().screenshot(name)
        if self.run_secret_tainted:
            td.save(name+'-private-visual-policy',dict(secret_tainted=True,private_only=True,
                never_commit=True,required_ocr_capture_preserved=True))
        return result

    def keys(self, names):
        self.monitor.command('send-key', {'keys':[{'type':'qcode','data':name} for name in names],
            'hold-time':KEY_HOLD_MS})
        time.sleep(KEY_GAP_SECONDS)

    def network_args(self):
        # No host-forwarded NIC is needed: live WebUI uses virtio-serial.
        return 'user,model=virtio-net-pci,id=owner-net'

    def peripheral_args(self):
        args = ['-device', 'virtio-vga,addr=0x4', '-device', 'qemu-xhci,id=usb-controller,addr=0x5']
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
        self.xhci_context = dict(stage=getattr(self, 'boot_purpose', self.mode), since_usec=0,
            attached=False, needed=self.mode == 'live' or getattr(self, 'boot_purpose', '') == 'tools-stock',
            expected_disconnect=None)
        super().__init__(*args, **kwargs)
        # The CPU has never run. Set carrier before even the firmware starts.
        self.monitor.command('set_link', {'name': 'owner-net', 'up': self.network_up})
        self.monitor.command('cont')
        td.save(f'boot-{self.boot_number}-owner-route', dict(network_up=self.network_up,
            configured_before_cpu_start=True, tools_storage_attached=False,
            keyboard_device='i8042/PS-2 AT', usb_keyboard=False,
            keyboard_timing=dict(hold_ms=KEY_HOLD_MS,minimum_gap_ms=KEY_GAP_SECONDS*1000)))

    def keyboard_device(self):
        source = ('import json,os,pathlib,stat\n' + ''.join(inspect.getsource(f) for f in (
            owner_key_counter.keyboard, owner_key_counter.settings, owner_key_counter.released, owner_key_counter.at_mapping))
            + '\ndevice=keyboard()\nfd=os.open(device,os.O_RDONLY|os.O_NONBLOCK|os.O_NOCTTY)\n'
            + 'try:\n    assert stat.S_ISCHR(os.fstat(fd).st_mode)\n    settings(fd,device)\n'
            + '    checked=at_mapping(fd,' + repr(at_keycodes()) + ')\nfinally: os.close(fd)\n'
            + 'print(json.dumps(dict(device=device,name="AT Translated Set 2 keyboard",bus=17,static_keycodes_checked=checked)))\n')
        value = self.capture_json('boot-' + str(self.boot_number) + '-at-keyboard',
            sw.framed('python3 -c ' + shlex.quote(source)))
        assert value['name'] == 'AT Translated Set 2 keyboard' and value['bus'] == 17
        assert value['static_keycodes_checked'] == len(at_keycodes())

    def capture_json(self, name, command):
        value = super().capture_json(name, command)
        if (isinstance(value, dict) and value.get('ready') is False
                and not value.get('handoff_ready') and not value.get('rejected')):
            # A completed UART command is safe to follow with this independent
            # journal receipt. Failed/still-running UART transfers are never
            # interrupted with a second command.
            owner_xhci.checkpoint(self, name + '-not-ready')
        return value

    def prepare_registry_auth(self, encoded_auth=None):
        # The physical `login` command is the only credential writer in the guest.
        pass

    def login(self):
        try:
            super().login()
        except TimeoutError:
            # Only a boot that never showed `login:`; later prompts have their own evidence.
            if not self.authentication_started:
                boot_stall(self, getattr(self, 'boot_purpose', self.mode))
            raise
        self.owner_signed_in = True
        self.keyboard_device()
        owner_xhci.checkpoint(self, 'boot-' + str(self.boot_number) + '-begin')
        if not self.network_up:
            self.assert_offline('stock-offline-login')

    def login_live(self):
        super().login_live()
        self.owner_signed_in = True
        self.keyboard_device()
        self.counter_kernel_proof()
        owner_xhci.checkpoint(self, 'boot-' + str(self.boot_number) + '-begin')

    def counter_kernel_proof(self):
        native = json.loads(pathlib.Path('evidence/14-counter-kernel.json').read_text())
        assert native['sha'] == os.environ['GITHUB_SHA'] and native['skipped'] is False, 'STOP: counter proof receipt identity'
        if native['status'] == 'passed':
            result = native
        else:
            assert native['status'] == 'guest-required', 'STOP: unknown counter proof state'
            result = self.capture_json('counter-kernel-proof', sw.framed('python3 -c ' + shlex.quote(owner_counter_kernel.guest_source())))
            result.update(location='guest-before-hidden-input', sha=native['sha'])
        td.save('counter-kernel-proof', result)
        assert result['status'] == 'passed' and result['real_kernel'] and result['skipped'] is False, 'STOP: mandatory kernel counter proof failed'
        assert result['negative_control']['comparison']['matches'] is False and result['fixed']['comparison']['matches'] is True

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
        # Owner reboot performs its health check before typing the command.
        return super().finish_shutdown(stage, expected, timeout=timeout)

    def hard_reset(self, stage):
        self.media_absent(stage)
        owner_xhci.checkpoint(self, stage + '-before-hard-reset')
        assert not any(e.get('event') == 'SHUTDOWN' for e in self.monitor.events)
        self.monitor.command('system_reset')
        # Pinned QEMU8.2.2 converts system_reset to this exact host shutdown
        # under -no-reboot, then -no-shutdown keeps counters readable. There
        # is no guest shutdown/finalizer. The next start uses the existing
        # explicit one-boot Linux authorization; Windows remains default.
        self.finish_shutdown(stage, 'host-qmp-system-reset')
        td.save(stage + '-hard-reset', dict(status='passed', qmp='system_reset',
            reason='host-qmp-system-reset', guest_shutdown=False, tools_absent=True,
            stopped_events=self.stopped_events, physical_keyboard='i8042/PS-2 AT'))

    def poweroff(self, stage):
        if self.mode == 'live' and PROBE_MEDIA is not None and not getattr(self, 'media_probe_done', False) \
                and not getattr(self, 'failed_command', False) and sys.exc_info()[0] is None:
            probe_media(self, PROBE_MEDIA)
            self.media_probe_done = True
        self.media_absent(stage)
        return super().poweroff(stage)

    def close(self, stage):
        try:
            # Evidence only, never a check: the kernel command line this boot logged and the terminal
            # queries the harness answered on the serial console (rehearsal runs 6 and 12).
            lines = re.findall(r'Command line: ([^\r\n]*)', getattr(self, 'boot_transcript', '') or '')
            td.save(stage + '-serial-terminal', dict(kernel_command_line=lines[0] if lines else None,
                    terminal_replies=dict(getattr(getattr(self, 'replies', None), 'counts', {}) or {})))
        except Exception:
            pass
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


def vcpu_ticks(monitor, proc=pathlib.Path('/proc')):
    """CPU time (utime + stime, in clock ticks) of each vCPU thread QEMU reports."""
    rows = {}
    for cpu in monitor.command('query-cpus-fast'):
        # Fields after the command name's closing parenthesis start at field 3 (state);
        # utime and stime are fields 14 and 15.
        fields = (proc / str(cpu['thread-id']) / 'stat').read_text().rsplit(')', 1)[1].split()
        rows[cpu['cpu-index']] = dict(thread_id=cpu['thread-id'], ticks=int(fields[11]) + int(fields[12]))
    return rows


def boot_stall(guest, stage, seconds=5, settle=10):
    """A boot that never reached `login:` (rehearsal run 6, 43136407300): tell a frozen guest
    from an idle or busy one whose consoles stopped, before close() pauses and ends it.

    Each probe is best effort and records its own error; the caller re-raises the timeout.
    sysrq-w prints blocked tasks only if kernel.sysrq allows it; otherwise the kernel says so.
    """
    value = dict(stage=stage, boot=getattr(guest, 'boot_number', None), seconds=seconds,
                 clock_ticks_per_second=os.sysconf('SC_CLK_TCK'))
    try:
        value['status'] = guest.monitor.command('query-status')
    except Exception as error:
        value['status_error'] = repr(error)[:200]
    try:
        before = vcpu_ticks(guest.monitor)
        time.sleep(seconds)
        after = vcpu_ticks(guest.monitor)
        value['vcpus'] = [dict(cpu=cpu, thread_id=row['thread_id'], ticks_before=row['ticks'],
                               ticks_after=after[cpu]['ticks'], ticks_used=after[cpu]['ticks'] - row['ticks'])
                          for cpu, row in sorted(before.items()) if cpu in after]
    except Exception as error:
        value['vcpu_error'] = repr(error)[:200]
    try:
        guest.monitor.command('send-key', {'keys': [{'type': 'qcode', 'data': name} for name in ('alt', 'sysrq', 'w')],
                                           'hold-time': 100})
        value['sysrq_w_sent'] = True
        try:
            # Keep reading the UART so the kernel's answer lands in the boot console transcript.
            guest.wait(r'(?!)', timeout=settle)
        except (TimeoutError, EOFError):
            pass
    except Exception as error:
        value.update(sysrq_w_sent=False, sysrq_error=repr(error)[:200])
    td.save(stage + '-boot-stall', value)
    try:
        guest.screenshot(stage + '-boot-stall')
    except Exception as error:
        td.save(stage + '-boot-stall-screenshot', dict(error=repr(error)[:200]))
    return value


def retain_vcsa(tty, stage, phase, raw):
    path = td.EVIDENCE / (stage + '-timeout-' + str(phase) + '.vcsa')
    path.write_bytes(raw)
    td.save(path.stem, dict(sha256=hashlib.sha256(raw).hexdigest(), path=path.name,
        tty=tty, rows=raw[0], columns=raw[1], cursor_x=raw[2], cursor_y=raw[3],
        secret_tainted=Guest.run_secret_tainted,private_only=True,never_commit=True))


def wait_tty(guest, tty, predicate, stage, timeout=90, resync=None, observe=None):
    # Stage labels can be reused by a caller or another Console instance. Keep
    # every sample, observer answer and resync in a unique wait namespace.
    stage += '-wait-' + str(next(PROMPT_WAIT_IDS))
    samples = 0
    def sample(seconds):
        nonlocal samples
        samples += 1
        return guest.capture_json(stage + '-sample-' + str(samples), sw.framed('python3 -c ' + shlex.quote(
            owner_console.source(tty, predicate, seconds, health=owner_xhci.context(guest)))))
    owner_console.wait(sample, timeout,
        lambda phase, raw: retain_vcsa(tty, stage, phase, raw), resync=resync,
        observe=(lambda seconds, attempt: observe(stage + '-idle-' + str(attempt), seconds)) if observe else None,
        record=lambda event: td.save(stage + '-resync-' + str(event['attempt']),
            dict(stage=stage, tty=tty, **event)))


def diagnostic_reader(before=None, command=None, folders=('/var/lib/ares/records', '/var/lib/ares/diagnostics'), timeout=OWNER_RESULT_WAIT):
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


# The installed toolset, found the way os/owner-tools/at finds it: the entry's resolved path
# (readlink -f), then that path's folder.
ENTRY = r'''import json,subprocess
entry='/var/lib/ares/at'
resolved=subprocess.check_output(['/usr/bin/readlink','-f','--',entry],text=True).rstrip('\n')
print(json.dumps(dict(entry=entry,resolved=resolved)))
'''


class Console:
    def __init__(self, guest, tty='tty3', commands=None):
        self.guest, self.tty = guest, tty
        # The laptop's older tools differ only in the bootstrap's fingerprint.
        self.commands = COMMANDS if commands is None else commands
        self.user, self.uid = 'ares-recovery', 1000
        self.root = False
        self.completed_epoch = None
        self.pending_hidden = None
        self.last_hidden = None
        self.login_prepared = None
        # The installed toolset's folder; read in the guest before each command the tools read input for.
        self.tools = None

    def toolset(self, stage):
        """The folder the installed tools run from, resolved in the guest as os/owner-tools/at
        resolves it. It is /var/lib/ares/tools after the first install and tools-<fingerprint>
        after a tools update (run 43581458429); it is read here, never derived from what the
        route believes it installed."""
        value = self.guest.capture_json(stage + '-toolset', sw.framed('python3 -c ' + shlex.quote(ENTRY)))
        folder, _, name = value['resolved'].rpartition('/')
        assert value['entry'] == '/var/lib/ares/at' and name == 'at', 'STOP: the installed entry does not resolve to a toolset'
        owner_hidden.owner_reader(folder, [])  # refuses anything but an installed toolset's folder
        self.tools = folder
        return folder

    def owner_reader(self, args):
        """The tools' own process for a command typed in this console; None before a toolset was read."""
        return None if self.tools is None else owner_hidden.owner_reader(self.tools, args)

    def select(self):
        self.guest.keys(['ctrl', 'alt', 'f' + self.tty[3:]])

    def visible(self, text, stage='public-input'):
        for line in text.splitlines(keepends=True):
            value = line.removesuffix('\n')
            assert '\r' not in value and len(value)<120, 'Unexpected visible input line'
            type_text(self.guest,value)
            if line.endswith('\n'):
                if value:
                    name=stage+'-echo-'+str(next(PROMPT_WAIT_IDS))
                    source=('import json,pathlib,struct,time\n# visible-echo\n'+inspect.getsource(owner_console.screen)
                        +'\nready=False\ndeadline=time.monotonic()+5\nstable=0\nwhile time.monotonic()<deadline:\n'
                        +'    data=pathlib.Path('+repr('/dev/vcsa'+self.tty[3:])+').read_bytes()\n    _,line=screen(data)\n'
                        +('    uni=pathlib.Path('+repr('/dev/vcsu'+self.tty[3:])+').read_bytes()\n'
                          +'    rows,cols,x,y=data[:4]\n    assert len(uni)==rows*cols*4, "Invalid Unicode console size"\n'
                          +'    if pathlib.Path('+repr('/dev/vcsa'+self.tty[3:])+').read_bytes()[:4]!=data[:4]:\n'
                          +'        stable=0;time.sleep(.1);continue\n'
                          +'    chars=struct.unpack("="+"I"*(rows*cols),uni)\n'
                          +'    line="".join(chr(c) for c in chars[y*cols:y*cols+x]).rstrip()\n'
                          if not value.isascii() else '')
                        +'    stable=stable+1 if line.endswith('+repr(value)+') else 0\n'
                        +'    if stable>=3: ready=True;break\n    time.sleep(.1)\n'
                        +'print(json.dumps(dict(ready=ready,echo_matches=ready,value_recorded=False)))\n')
                    result=(self.login_prepared.rpc('echo', self.user) if self.login_prepared is not None
                        else self.guest.capture_json(name,sw.framed('python3 -c '+shlex.quote(owner_xhci.guard(source,owner_xhci.context(self.guest))))))
                    td.save(name,result)
                    assert result['ready'] and result['echo_matches'], 'Visible text differs; Enter withheld'
                type_text(self.guest,'\n')

    def prompt(self, stage):
        epoch = getattr(self.guest, 'owner_input_epoch', 0)
        def observe(name, seconds):
            assert getattr(self.guest, 'owner_input_epoch', 0) == epoch, 'Input revoked idle proof'
            value = self.guest.capture_json(name, sw.framed('python3 -c ' + shlex.quote(
                owner_console.hidden_idle_source(self.tty, seconds, health=owner_xhci.context(self.guest)))))
            td.save(name, value)
            assert getattr(self.guest, 'owner_input_epoch', 0) == epoch, 'Input revoked idle proof'
            assert type(value['ready']) is bool, 'Invalid physical idle observation'
            if not value['ready'] and value.get('raw'):
                retain_vcsa(self.tty, name, 1, base64.b64decode(value['raw'], validate=True))
            return value
        def resync():
            nonlocal epoch
            assert getattr(self.guest, 'owner_input_epoch', 0) == epoch, 'Input revoked idle proof'
            type_text(self.guest, '\n')
            epoch = self.guest.owner_input_epoch
        try:
            wait_tty(self.guest, self.tty, "bool(re.search(r'[$#]$',line))", stage,
                resync=resync, observe=observe)
        except BaseException:
            self.completed_epoch = None
            raise
        self.completed_epoch = getattr(self.guest, 'owner_input_epoch', 0)

    def hidden(self, stage, expected, prompt):
        assert self.pending_hidden is None, 'Previous hidden read has no completion receipt'
        stage += '-read-wait-' + str(next(PROMPT_WAIT_IDS))
        epoch = getattr(self.guest, 'owner_input_epoch', 0)
        prepared=self.login_prepared if expected['kind']=='login' else None
        value = (prepared.rpc('ready') if prepared is not None else self.guest.capture_json(stage, sw.framed('python3 -c ' + shlex.quote(
            owner_hidden.source(self.tty, expected, prompt=prompt.rstrip(), health=owner_xhci.context(self.guest))))))
        if prepared is not None:
            td.save(stage,value)
            if value.get('reader_changed'):raise owner_login.ReaderChanged('Login reader replaced before secret')
        assert getattr(self.guest, 'owner_input_epoch', 0) == epoch, 'Input revoked hidden readiness proof'
        assert type(value['ready']) is bool
        if not value['ready']:
            retain_vcsa(self.tty, stage, 1, base64.b64decode(value['raw'], validate=True))
            raise AssertionError('No verified hidden prompt')
        assert value['reader'] and value['prompt_at_cursor'] and value['reader_echo_enabled'] is False
        self.pending_hidden = dict(stage=stage, expected=expected, reader=value['reader'], epoch=epoch,
            token=expected == self.owner_reader(['login']) and prompt.rstrip() == TOKEN_PROMPT)
        if prepared is not None:self.pending_hidden['login_prepared']=prepared

    def input_guard(self, pending, phase):
        name=pending['stage']+'-input-guard-'+phase
        clearing=phase in ('before-clear','after-clear')
        prepared=pending.get('login_prepared')
        result=(prepared.guard(pending,phase,pending['counts']['length']*KEY_GAP_SECONDS*2+5 if phase.startswith('before-value') else 0)
            if prepared else self.guest.capture_json(name,sw.framed('python3 -c '+shlex.quote(
            owner_hidden.guard_source(self.tty,pending['expected'],pending['reader'],clearing,health=owner_xhci.context(self.guest))))))
        td.save(name,result)
        assert result['ready'] and not result['echo_enabled'] and result['syscall_number']==0, \
            'No unchanged hidden reader waiting in read; Enter withheld'
        assert not clearing or (result['canonical'] and result['vkill']==21), 'Canonical line clear unproved; Enter withheld'
        return result

    def counter_sample(self, pending, ticket):
        sequence=pending.get('counter_sequence',0)+1;pending['counter_sequence']=sequence
        name=pending['stage']+'-key-counter-sample-'+str(sequence)
        prepared=pending.get('login_prepared')
        result=(prepared.rpc('sample',sequence) if prepared else self.guest.capture_json(name,sw.framed('python3 -c '+shlex.quote(owner_key_counter.source(ticket,sequence)))))
        td.save(name,result)
        assert result['complete'] and result['keys_released'] and result['counts']['syn_dropped']==0, \
            'Incomplete keyboard counter or held key; Enter withheld'
        return result

    def verified_value(self,pending,ticket,value,layout,chunked):
        baseline=pending.get('public_baseline',dict(press=0,release=0,repeat=0,syn_dropped=0))
        pending['counter_baseline']=baseline;pending['attempts']=[]
        original=dict(pending['counts'])
        for attempt in (1,2):
            pending['counts']=dict(original,key_event_count=0,key_chord_count=0,last_key_was_ret=False)
            self.input_guard(pending,'before-value-'+str(attempt))
            if pending.get('login_prepared'):
                assert not chunked
                for char in value:
                    assert pending['login_prepared'].remaining()>.25, 'Login half-timeout budget expired while typing'
                    type_text(self.guest,char,layout,counts=pending['counts'])
            else:type_token(self.guest,value,layout,pending['counts'],chunked)
            assert pending['counts']['key_event_count']==pending['expected_events'] \
                and pending['counts']['key_chord_count']==len(value) and not pending['counts']['last_key_was_ret'], \
                'Hidden value was not completely sent; Enter withheld'
            epoch=self.guest.owner_input_epoch
            observed=self.counter_sample(pending,ticket)
            comparison=owner_key_counter.compare(owner_key_counter.delta(observed,baseline),pending['counts'])
            pending['attempts'].append(dict(attempt=attempt,sent=dict(pending['counts']),comparison=comparison))
            td.save(pending['stage']+'-pre-enter-proof',dict(status='pending',attempts=pending['attempts'],enter_sent=False))
            if comparison['matches']:
                self.input_guard(pending,'before-enter-'+str(attempt))
                assert self.guest.owner_input_epoch==epoch, 'Input revoked pre-Enter proof'
                pending['enter_epoch']=epoch
                td.save(pending['stage']+'-pre-enter-proof',dict(status='passed',attempts=pending['attempts'],
                    enter_sent=False,accepted_attempt=attempt,clear=pending.get('clear_proof')))
                return
            assert attempt==1, 'Second hidden-value count mismatch; Enter withheld'
            before=self.input_guard(pending,'before-clear')
            assert self.guest.owner_input_epoch==epoch, 'Input revoked clear authority'
            # No Return has been sent. Canonical VKILL is verified to be Ctrl-U.
            self.guest.owner_input_epoch=getattr(self.guest,'owner_input_epoch',0)+1
            self.guest.keys(['ctrl','u'])
            cleared=self.counter_sample(pending,ticket)
            clear_count=owner_key_counter.compare(owner_key_counter.delta(cleared,observed['counts']),dict(key_event_count=4))
            after=self.input_guard(pending,'after-clear')
            pending['clear_proof']=dict(ready=clear_count['matches'] and before['ready'] and after['ready'],
                comparison=clear_count,canonical=True,vkill=21,reader_still_waiting=True,enter_sent=False,
                value_recorded=False)
            td.save(pending['stage']+'-canonical-clear',pending['clear_proof'])
            assert pending['clear_proof']['ready'], 'Canonical line clear unproved; Enter withheld'
            baseline=cleared['counts'];pending['counter_baseline']=baseline
        raise AssertionError('Hidden pre-Enter proof unavailable')

    def hidden_diagnostics(self, pending, phase):
        name = pending['stage'] + '-diagnostics-' + phase
        value = self.guest.capture_json(name, sw.framed('python3 -c ' + shlex.quote(
            owner_read_diagnostics.source(self.tty, pending['expected'], pending['reader']))))
        value.update(phase=phase, typed=pending.get('counts'), token=pending.get('token', False))
        if pending.get('token'):
            value.update(guest_key_counts=pending.get('received_keys'), key_comparison=pending.get('key_comparison'))
        td.save(name, value)
        return value

    def send_hidden(self, value, layout=None, public_inputs=(), expect_rejection=False, chunk_token=False, repeat=None):
        pending = self.pending_hidden
        assert pending is not None, 'No hidden reader authority'
        assert not pending.get('sent'), 'Hidden input already attempted; no caller retry'
        assert getattr(self.guest, 'owner_input_epoch', 0) == pending['epoch'], 'Input revoked hidden reader authority'
        assert not expect_rejection or pending['expected']['kind'] == 'login'
        if public_inputs:
            assert pending['expected']['kind'] == 'sudo' and pending['expected']['next'] == self.owner_reader(['layout','proof'])
            assert all(prompt == LAYOUT_PROMPT and not hidden for prompt, _, hidden in public_inputs), 'Unwalked hidden-read continuation'
        pending['sent'] = True
        self.guest.screenshot_safe = False
        # Counts/classes only; never export the value, individual keys or their order.
        profile = typing_profile(self.guest, layout)
        assert value and '\n' not in value and '\r' not in value, 'Hidden line break refused before input'
        classes = set(); expected_events=0
        for char in value:
            try: keys = physical_keys(char, profile)
            except (AssertionError,KeyError): raise AssertionError('Unsupported hidden character; no input sent') from None
            assert 'ctrl' not in keys and 'ret' not in keys, 'Hidden control character refused before input'
            expected_events += 2*len(keys)
            if 'shift' in keys: classes.add('shift')
            if 'alt_r' in keys: classes.add('altgr')
            if ord(char) > 127: classes.add('non_ascii')
            if char in maps()['us'] and keys != physical_keys(char, 'us'):
                classes.add('layout_differs_from_us')
        pending['counts'] = dict(length=len(value), key_event_count=0, key_chord_count=0,
            last_key_was_ret=False, non_default_mapping_classes=sorted(classes),
            timing=dict(hold_ms=KEY_HOLD_MS,minimum_gap_ms=KEY_GAP_SECONDS*1000))
        pending['expected_events']=expected_events
        if pending.get('token'):
            pending['counts'].update(chunked=chunk_token,chunk_size=16 if chunk_token else None,
                between_chunks_seconds=1 if chunk_token else 0,before_return_seconds=1 if chunk_token else 0)
        self.last_hidden = pending
        assert not chunk_token or pending.get('token'), 'Chunking is only for the CI token'
        prepared=pending.get('login_prepared')
        ticket = prepared.ticket if prepared else self.guest.capture_json(pending['stage']+'-key-counter-start', sw.framed('python3 -c '+shlex.quote(owner_key_counter.source())))
        assert ticket['status']=='ready' and ticket['counts_only'], 'No guest keyboard counter authority'
        td.save(pending['stage']+'-key-counter-start', ticket)
        try:
            try:
                if prepared:
                    arm=prepared.rpc('arm',json.dumps([len(value)*KEY_GAP_SECONDS*2+5,expected_events],separators=(',',':')))
                    if arm.get('reader_changed'):raise owner_login.ReaderChanged('Login reader replaced before value')
                    assert arm['ready'], 'No login time/reader budget; no secret typed'
                    pending['public_baseline']=arm['baseline'];pending['counter_sequence']=1
                self.verified_value(pending,ticket,value,profile,chunk_token)
                assert self.guest.owner_input_epoch==pending['enter_epoch'], 'Input revoked verified hidden value'
                # The only Enter for this value, after its successful pre-Enter proof.
                type_text(self.guest,'\n',profile,counts=pending['counts'])
                if prepared:
                    timing=prepared.rpc('entered')
                    pending['login_timing']=timing
                    td.save(pending['stage']+'-login-timing',timing)
                    assert timing['within_half_timeout'], 'Login exceeded half guest LOGIN_TIMEOUT'
            finally:
                td.save(pending['stage']+'-key-events-sent',pending['counts'])
                time.sleep(1)
                received = (prepared.finish() if prepared else self.guest.capture_json(pending['stage']+'-key-counter-stop', sw.framed('python3 -c '+shlex.quote(owner_key_counter.source(ticket)))))
                whole=owner_key_counter.delta(received,pending.get('public_baseline',{}))
                current=owner_key_counter.delta(received,pending.get('counter_baseline',{}))
                pending['received_keys'] = dict(current,whole_window_counts=whole['counts'])
                pending['key_comparison'] = owner_key_counter.compare(current,pending['counts'])
                td.save(pending['stage']+'-key-counter-result', dict(received=pending['received_keys'],
                    whole_window=whole,comparison=pending['key_comparison'],attempts=pending.get('attempts'),
                    clear=pending.get('clear_proof')))
            assert pending['key_comparison']['matches'], 'Final key counts differ; no post-Enter retry'
        except BaseException:
            td.save(pending['stage']+'-pre-enter-stop',dict(status='stopped',enter_sent=pending['counts']['last_key_was_ret'],
                attempts=pending.get('attempts'),clear=pending.get('clear_proof'),value_recorded=False))
            try: self.hidden_diagnostics(pending,'input-refused')
            except BaseException as error: td.save(pending['stage']+'-diagnostics-unavailable',dict(kind=type(error).__name__))
            raise
        self.last_hidden = pending
        # No secret goes into this script/receipt. Never resend after a timeout.
        self.resync_serial_after_hidden(pending['stage'] + '-read-left')
        if repeat is not None:
            # passwd asks twice: the same reader must wait again, echo off, at
            # its second prompt; that new observation authorizes the next value.
            epoch = self.guest.owner_input_epoch
            again = self.guest.capture_json(pending['stage'] + '-repeat', sw.framed('python3 -c ' + shlex.quote(
                owner_hidden.source(self.tty, pending['expected'], prompt=repeat, health=owner_xhci.context(self.guest)))))
            assert self.guest.owner_input_epoch == epoch, 'Input revoked repeat prompt proof'
            if not again['ready']:
                retain_vcsa(self.tty, pending['stage'] + '-repeat', 1, base64.b64decode(again['raw'], validate=True))
                raise AssertionError('The hidden reader did not ask again; the value is not retyped')
            assert all(again['reader'][k] == pending['reader'][k] for k in ('pid', 'start', 'exe', 'tty')), \
                'Hidden reader changed between its two prompts'
            self.pending_hidden = None
            return again
        if pending.get('token'):
            self.hidden_diagnostics(pending, 'completion-start')
        for number, (prompt, public_value, _) in enumerate(public_inputs, 1):
            epoch = self.guest.owner_input_epoch
            handoff = self.guest.capture_json(pending['stage'] + '-handoff-' + str(number), sw.framed('python3 -c ' + shlex.quote(
                owner_hidden.source(self.tty, pending['expected'], receipt=pending['reader'], handoff=prompt,health=owner_xhci.context(self.guest)))))
            assert self.guest.owner_input_epoch == epoch, 'Input revoked public handoff'
            assert not handoff['ready'] and handoff.get('handoff_ready') and handoff['reader_left'], 'No verified public reader after sudo'
            self.visible(public_value + '\n',pending['stage']+'-public-handoff')
        epoch = self.guest.owner_input_epoch
        timeout = TOKEN_RESULT_WAIT if pending.get('token') else OWNER_RESULT_WAIT if pending['expected']['kind'] == 'owner' or public_inputs else 60
        result = self.guest.capture_json(pending['stage'] + '-left', sw.framed('python3 -c ' + shlex.quote(
            owner_hidden.source(self.tty, pending['expected'], receipt=pending['reader'], timeout=timeout,health=owner_xhci.context(self.guest)))))
        assert self.guest.owner_input_epoch == epoch, 'Input revoked hidden read completion'
        assert type(result['ready']) is bool
        if result.get('rejected') and expect_rejection:
            assert not result['ready'], 'Rejected login cannot grant completion'
            self.pending_hidden = None
            return result
        if not result['ready'] and result.get('reader_left') and result.get('shell_idle') and not result.get('prompt_at_cursor'):
            # A departed reader plus the independent idle observer authorizes
            # only the existing bounded redraw. Completion still needs prompt.
            self.completed_epoch = epoch
            self.prompt(pending['stage'] + '-transition-prompt')
            epoch = self.guest.owner_input_epoch
            result = self.guest.capture_json(pending['stage'] + '-left-after-resync', sw.framed('python3 -c ' + shlex.quote(
                owner_hidden.source(self.tty, pending['expected'], receipt=pending['reader'], timeout=timeout,health=owner_xhci.context(self.guest)))))
            assert self.guest.owner_input_epoch == epoch, 'Input revoked resynchronized completion'
        if not result['ready']:
            retain_vcsa(self.tty, pending['stage'] + '-left', 1, base64.b64decode(result['raw'], validate=True))
            self.hidden_diagnostics(pending, 'completion-timeout')
            raise AssertionError('Hidden reader did not leave its read; secret will not be retyped')
        self.pending_hidden = None
        return result

    def login(self, password, stage, wrong=False, user='ares-recovery'):
        # Package 27 also signs in the daily account with its new password.
        assert user in ('ares-recovery', 'ares') and not (wrong and user != 'ares-recovery')
        self.user, self.uid = user, 1000 if user == 'ares-recovery' else 1001
        for attempt in (1,2):
            try:
                result=self.login_attempt(password,stage+('-restart' if attempt==2 else ''),wrong)
                td.save(stage+'-physical-login-result',dict(status='expected-rejection' if wrong else 'passed',
                    tty=self.tty,attempts=attempt,reader_replacements=attempt-1,
                    timing=self.last_hidden['login_timing'],value_recorded=False,
                    secret_tainted=getattr(self.guest,'run_secret_tainted',False)))
                return result
            except owner_login.ReaderChanged:
                prepared=self.login_prepared
                assert prepared is not None
                self.pending_hidden=None
                if not prepared.finished:prepared.finish()
                fresh=prepared.clear_and_fresh()
                td.save(stage+'-login-reader-restart-'+str(attempt),dict(attempt=attempt,
                    fresh=fresh,secret_tainted=getattr(self.guest,'secret_tainted',False),value_recorded=False))
                prepared.cleanup();self.login_prepared=None
                assert attempt==1, 'Second login reader replacement; STOP'
            finally:
                if self.login_prepared is not None:
                    self.login_prepared.cleanup();self.login_prepared=None

    def login_attempt(self, password, stage, wrong=False):
        self.select()
        wait_tty(self.guest, self.tty, "line.endswith('login:')", stage + '-login-prompt')
        self.login_prepared=owner_login.Prepared(self,stage)
        self.login_prepared.begin()
        self.guest.screenshot_safe = False
        self.visible(self.user + '\n',stage+'-username')
        self.hidden(stage + '-password-prompt', dict(kind='login'), 'Password:')
        # The failure fixture deliberately uses German physical positions while
        # the loaded map is plain US. This does not claim the password was typed.
        result = self.send_hidden(password, 'de' if wrong else None, expect_rejection=wrong)
        if wrong:
            assert result['rejected'] and not result['ready'], 'Layout failure did not reject the login'
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
        self.visible('sudo -k\n',stage+'-sudo-reset')
        self.prompt(stage+'-sudo-reset-done')
        self.visible('sudo -i\n',stage+'-sudo-command')
        self.hidden(stage + '-sudo-hidden', owner_hidden.sudo_reader(['-i'], dict(kind='shell')), SUDO_PROMPT)
        self.guest.screenshot_safe = False
        self.send_hidden(password)
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
            owner_console.hidden_idle_source(self.tty, OWNER_RESULT_WAIT, health=owner_xhci.context(self.guest)))))
        assert type(value['ready']) is bool, 'Invalid hidden idle observation'
        assert self.guest.owner_input_epoch == epoch, 'Input revoked hidden completion observation'
        if not value['ready']:
            retain_vcsa(self.tty, stage + '-physical-idle', 1, base64.b64decode(value['raw'], validate=True))
            if self.last_hidden is not None:
                self.hidden_diagnostics(self.last_hidden, 'physical-idle-timeout-' + stage)
            raise AssertionError('Hidden owner command did not return to an idle shell')
        assert value['foreground_shell'], 'Hidden completion authority absent'
        self.completed_epoch = epoch
        # The original strict cursor predicate, three samples and at most two
        # recorded physical Enters apply only after the foreground shell returns.
        self.prompt(stage + '-after-hidden-ready')
        td.save(stage + '-hidden-completed', dict(status='passed', completion_uses_echo=False,
            foreground_shell=True, input_epoch=epoch, token_recorded=False))

    def run(self, name, stage, inputs=(), password=None, expect_stop=False, token_chunks=False, record=None):
        owner_xhci.checkpoint(self.guest, stage + '-begin')
        self.select()
        self.prompt(stage + '-ready')
        before = self.records()
        args = self.commands[name].split('/at ', 1)[-1].split()
        hidden_input = password is not None
        if password is not None or any(hidden for _, _, hidden in inputs):
            # The process that reads is the tools' own, from the toolset the entry resolves to now.
            self.toolset(stage)
        self.visible(self.commands[name] + '\n',stage+'-command')
        if password is not None:
            assert all(not hidden for _, _, hidden in inputs), 'Unwalked hidden continuation after sudo'
            self.hidden(stage + '-sudo-hidden', owner_hidden.sudo_reader(['/var/lib/ares/at', *args], self.owner_reader(args)), SUDO_PROMPT)
            self.guest.screenshot_safe = False
            self.send_hidden(password, public_inputs=inputs)
            inputs = ()
        for prompt, value, hidden in inputs:
            if hidden:
                hidden_input = True
                self.hidden(stage + '-hidden-input', self.owner_reader(args), prompt.rstrip())
                self.guest.screenshot_safe = False
            else:
                wait_tty(self.guest, self.tty, 'line.endswith('+repr(prompt.rstrip())+')', stage + '-input-ready')
            if hidden:
                self.send_hidden(value,chunk_token=token_chunks)
            else:
                self.visible(value + '\n',stage+'-public-input')
        if hidden_input:
            self.after_hidden(stage)
        if name == 'reboot' and not expect_stop:
            self.guest.media_absent(stage)
            self.guest.finish_shutdown(stage, 'guest-reset')
            return
        # A tools update through the bootstrap writes its own receipt name.
        command = record or (self.commands[name].split('/at ', 1)[-1].split()[0] if name != 'install' else 'install')
        source = owner_xhci.guard(diagnostic_reader(before, command), owner_xhci.context(self.guest))
        result = self.guest.capture_json(stage + '-owner-result', sw.framed('python3 -c ' + shlex.quote(source)))
        # Save before checking acceptance: an unexpected STOP is the evidence
        # needed to diagnose the failure, not an excuse to lose its record.
        td.save(stage + '-owner-diagnostics', result)
        assert result['status'] == ('stopped' if expect_stop else 'passed'), 'Owner command failed: ' + stage
        owner_xhci.checkpoint(self.guest, stage + '-completed')
        self.prompt(stage + '-completed')
        self.guest.screenshot_safe = True
        if not expect_stop:
            self.guest.screenshot(stage + '-owner-pass')
        td.save(stage + '-command', dict(command=self.commands[name], physical=True, status=result['status'], profile=self.guest.owner_layout))
        if hidden_input and name=='login':
            assert self.last_hidden['key_comparison']['matches'], 'Guest keyboard counts differ; preserve diagnostics; never retype token'
        return result

    def passwd(self, password, stage):
        """The guide's one-time `sudo passwd ares`, typed in this root console."""
        assert self.root and password and set(password) <= set(ARES_LETTERS)
        if password not in self.guest.secrets:
            self.guest.secrets.append(password)
        self.select()
        self.prompt(stage + '-ready')
        self.visible('sudo passwd ares\n', stage + '-command')
        reader = owner_hidden.passwd_reader('ares')
        self.hidden(stage + '-new', reader, 'New password:')
        self.guest.screenshot_safe = False
        self.send_hidden(password, repeat='Retype new password:')
        self.hidden(stage + '-retype', reader, 'Retype new password:')
        self.send_hidden(password)
        self.after_hidden(stage)
        wait_tty(self.guest, self.tty, "'updated successfully' in full and bool(re.search(r'[$#]$',line))", stage + '-updated')
        self.guest.screenshot_safe = True
        td.save(stage + '-result', dict(status='passed', command='sudo passwd ares', console=self.tty,
            value_recorded=False, letters='lowercase a-x and digits'))

    def ares_sudo(self, password, stage):
        """His new password signs him in and works for sudo, which keeps no ticket (package 21)."""
        assert self.tty != 'tty3' and not self.root
        self.login(password, stage, user='ares')
        self.prompt(stage + '-ares-shell')
        self.visible('sudo -v\n', stage + '-validate')
        self.hidden(stage + '-sudo-hidden', owner_hidden.sudo_reader(['-v'], dict(kind='shell')), ARES_SUDO_PROMPT)
        self.guest.screenshot_safe = False
        self.send_hidden(password)
        self.after_hidden(stage + '-sudo')
        self.guest.screenshot_safe = True
        self.visible('sudo -n true\n', stage + '-no-ticket')
        wait_tty(self.guest, self.tty, "'a password is required' in full and bool(re.search(r'[$#]$',line))", stage + '-ticket-refused')
        self.logout(stage + '-logout')
        td.save(stage + '-result', dict(status='passed', login_with_new_password=True, sudo_password_accepted=True,
            sudo_kept_no_ticket=True, console=self.tty, value_recorded=False))

    def logout(self, stage):
        self.select()
        self.prompt(stage + '-ready')
        if self.root:
            self.visible('exit\n',stage+'-root-exit')
            self.prompt(stage + '-user-ready')
        self.visible('sudo -k\n',stage+'-sudo-reset')
        self.prompt(stage+'-sudo-reset-done')
        self.visible('exit\n',stage+'-logout')
        wait_tty(self.guest, self.tty, "line.endswith('login:')", stage + '-getty-returned')
        self.guest.command(stage + '-no-session', 'set -e; if pgrep -t ' + self.tty + ' -u ' + str(self.uid) + ' -x bash; then exit 1; fi')


def probe_media(guest, media):
    ticket=guest.capture_json('probe-key-counter-start',sw.framed('python3 -c '+shlex.quote(owner_key_counter.source())))
    td.save('probe-key-counter-start',ticket)
    checkpoint=guest.capture_json('probe-key-counter-sample-1',sw.framed('python3 -c '+shlex.quote(owner_key_counter.source(ticket,1))))
    td.save('probe-key-counter-sample-1',checkpoint)
    assert checkpoint['complete'] and checkpoint['keys_released'] and checkpoint['counts']==dict(press=0,release=0,repeat=0,syn_dropped=0)
    observed=guest.capture_json('probe-key-counter-stop',sw.framed('python3 -c '+shlex.quote(owner_key_counter.source(ticket))))
    td.save('probe-key-counter-result',observed)
    assert observed['complete'] and observed['counts']==dict(press=0,release=0,repeat=0,syn_dropped=0), 'Guest key counter capability failed'
    active=guest.capture_json('probe-active-vt',sw.framed("python3 -c 'import json,pathlib; print(json.dumps(dict(active=pathlib.Path(\"/sys/class/tty/tty0/active\").read_text().strip())))'"))
    assert re.fullmatch(r'tty(?:[1-9]|1[0-2])',active['active']), 'Unknown live VT before Unicode getter proof'
    guest.keys(['ctrl','alt','f3'])
    try:
        unicode=guest.capture_json('probe-unicode-console',sw.framed('''python3 - <<'PY'
import json,pathlib,struct
raw=pathlib.Path('/dev/vcsa3').read_bytes()
rows,cols,x,y=raw[:4]
assert rows and cols and x<cols and y<rows and len(raw)==4+rows*cols*2
uni=pathlib.Path('/dev/vcsu3').read_bytes()
assert len(uni)==rows*cols*4
assert all(c<=0x10ffff for c in struct.unpack('='+'I'*(rows*cols),uni))
print(json.dumps(dict(status='passed',getter_only=True,unicode_cells=rows*cols)))
PY'''))
        td.save('probe-unicode-console',unicode)
        assert unicode['status']=='passed' and unicode['getter_only']
    finally: guest.keys(['ctrl','alt','f'+active['active'][3:]])
    media.attach(guest, 'probe')
    source = bundle_module('bootstrap').verification(media.fingerprint)
    source += '\necho LIVE_TOOLS_BUNDLE_MATCHED_WINDOWS_COPY\n'
    guest.command('probe-media-manifest', source)
    media.detach(guest, 'probe')


def keyboard(guest, stage, profile, temporary_old=None, loaded_profile=None):
    value = guest.capture_json(stage + '-loaded-keyboard', sw.framed('''python3 - <<'PY'
import json,pathlib,subprocess
reply=json.loads(subprocess.check_output(['busctl','--system','--json=short','call','org.freedesktop.locale1','/org/freedesktop/locale1','org.freedesktop.DBus.Properties','GetAll','s','org.freedesktop.locale1']))
print(json.dumps(dict(console=pathlib.Path('/etc/vconsole.conf').read_text(),x11=pathlib.Path('/etc/X11/xorg.conf.d/00-keyboard.conf').read_text(),
    localed=reply,loaded_map=subprocess.check_output(['dumpkeys','-C','/dev/tty3','--keys-only'],text=True),cmdline=pathlib.Path('/proc/cmdline').read_text(),
    bls={str(p):p.read_text() for p in pathlib.Path('/boot/loader/entries').glob('*.conf')})))
PY'''))
    fields = value['localed']['data'][0]
    assert fields['VConsoleKeymap']['data'] == profile
    x11_layout, x11_variant = kb.x11_profile(profile)
    assert fields['X11Layout']['data'] == x11_layout
    assert fields['X11Variant']['data'] == x11_variant
    kb.loaded_map(value['loaded_map'], loaded_profile or profile)
    texts = value['bls'].values()
    if temporary_old is not None:
        snapshot = kb.deployment_snapshot(guest, stage + '-temporary-stock')
        resolved = {e['file']: ke.entry_identity(e['deployment']) for e in snapshot['bls']}
        assert sum(identity == temporary_old for identity in resolved.values()) == 1
        texts = [text for file,text in value['bls'].items() if resolved[file] != temporary_old]
    for words in [value['cmdline'].split(), *[shlex.split(line)[1:] for text in texts for line in text.splitlines() if line.startswith('options ')]]:
        assert not any(re.match(r'(?:rd\.)?vconsole\.keymap(?:[._]toggle)?(?:=|$)', word) for word in words)
    return value


def finished_consoles(guest, stage):
    value = guest.capture_json(stage + '-all-console-maps', sw.framed('''python3 - <<'PY'
import json,subprocess
print(json.dumps({str(n):subprocess.check_output(['dumpkeys','-C','/dev/tty'+str(n),'--keys-only'],text=True) for n in range(1,7)}))
PY'''))
    assert set(value) == set(map(str, range(1,7)))
    for text in value.values(): kb.loaded_map(text, 'de')
    return value


def abandoned_trial(audit, password, hashed, stock, release, brew):
    for stage in ('layout-reset-trial', 'layout-reset-recovery'):
        guest = td.start_installed(password, hashed, stage)
        try:
            console, observed = common_boot(guest, stage, 'de', password, stock, release, ares=True)
            assert observed == brew
            if stage == 'layout-reset-trial':
                before = keyboard(guest, stage + '-before', 'de')
                console.run('layout-us', stage + '-begin-us')
                guest.owner_layout = 'us'
                trial = keyboard(guest, stage + '-pending', 'de', loaded_profile='us')
                assert trial['console'] == before['console'] and trial['x11'] == before['x11'], 'Trial persisted boot/greeter settings'
                guest.hard_reset(stage)
            else:
                finished_consoles(guest, stage)
                console.run('layout-abandon', stage + '-abandon')
                console.run('title', stage + '-reboot-title')
                console.run('reboot', stage + '-guarded-reboot')
        finally:
            finish(guest, audit, stage)
    td.save('layout-reset-proof', dict(status='passed', reset='QMP system_reset',
        trial='us', finished='de', persistent_console_and_x11_unchanged=True,
        every_console_german=True, german_password_login=True, physical_foot_german=True,
        fresh_authenticated_abandon=True, guarded_reboot=True, tools_absent_at_reset=True))


def public_typing(guest, stage, profile, console, foot=False):
    typing_profile(guest, profile)
    guest.owner_layout = profile
    # Reuse the existing observer and real terminal reader; only physical
    # positions now come from the exact three ISO maps, including the umlaut.
    previous = kb.TEXT, kb.type_text, kb.physical_keys
    try:
        kb.TEXT, kb.type_text, kb.physical_keys = TEXT, type_text, physical_keys
        console.select()
        console.prompt(stage + '-public-ready')
        kb.physical_input(guest, stage + '-console', profile, 0 if console.root else 1000)
        if foot:
            kb.foot(guest, stage, profile)
            console.select()
    finally:
        kb.TEXT, kb.type_text, kb.physical_keys = previous


def finish(guest, audit, stage):
    try:
        if sys.exc_info()[0] is None and not getattr(guest, 'stopped_events_verified', False):
            owner_xhci.checkpoint(guest, stage + '-end')
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


# The VM's console is serial (console=ttyS0, carried over by the installer), so systemd 259 probes
# it for its terminfo name and size. Runs 6 and 12 hung in that size probe at an installed boot.
# These kernel args give systemd the answer the probe yields today, so it never probes: PID 1
# reads systemd.tty.*.console for /dev/console, services read systemd.tty.*.ttyS0 (systemd v259:
# core/main.c fixup_environment, terminal-util.c reset_dev_console_fd, core/exec-invoke.c).
# VM only: the laptop has no serial console.
TTY_ARGS = ('systemd.tty.term.console=vt220', 'systemd.tty.rows.console=24', 'systemd.tty.columns.console=80',
            'systemd.tty.term.ttyS0=vt220', 'systemd.tty.rows.ttyS0=24', 'systemd.tty.columns.ttyS0=80')


def with_tty_args(entry):
    """The BLS entry with TTY_ARGS appended once to its only `options` line; nothing else changes."""
    lines = entry.split('\n')
    found = [index for index, line in enumerate(lines) if line.split(None, 1)[:1] == ['options']]
    assert len(found) == 1, 'STOP: the installed boot entry has ' + str(len(found)) + ' options lines'
    present = lines[found[0]].split()[1:]
    missing = [arg for arg in TTY_ARGS if arg not in present]
    if missing:
        lines[found[0]] = lines[found[0]].rstrip() + ' ' + ' '.join(missing)
    return '\n'.join(lines)


def edit_boot_entries(boot):
    """Pin the serial console in the only boot entry under a mounted /boot, and read it back."""
    entries = sorted(pathlib.Path(boot).glob('loader/entries/*.conf'))
    assert len(entries) == 1, 'STOP: expected exactly one installed boot entry, found ' + str(len(entries))
    entry = entries[0]
    before = entry.read_text()
    after = with_tty_args(before)
    if after != before:
        with open(entry, 'w') as stream:
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
    read = entry.read_text()
    assert read == after and with_tty_args(read) == read, 'STOP: the boot entry did not read back with the console args'
    option = lambda text: next(line for line in text.split('\n') if line.split(None, 1)[:1] == ['options'])
    return dict(entry=entry.name, before=option(before), after=option(read),
                added=[arg for arg in TTY_ARGS if arg not in option(before).split()])


def pin_serial_console(stage='stock-serial-console'):
    """Before stock's first boot, from the host: TTY_ARGS on the installed boot entry of the target only.

    The target is the harness's own target image (WORK/target.raw, which QEMU serves with the
    CRUCIAL-TARGET serial); the protected disk is never attached. ostree keeps the args for every
    later deployment (release 13 and release 27).
    """
    image = td.WORK / 'target.raw'
    assert image.is_file() and image.resolve().is_relative_to(td.WORK.resolve()), 'STOP: no target image'
    loop = subprocess.check_output(['losetup', '--find', '--show', '--partscan', str(image)], text=True, timeout=30).strip()
    try:
        # The shared wait: the loop is backed by this image, and exactly its GPT's partition nodes are ready.
        ready = wait_loop_partitions(loop, image)
        parts = [loop + 'p' + str(partition['number']) for partition in ready['expected']]
        types = {part: subprocess.run(['blkid', '-o', 'value', '-s', 'TYPE', part], capture_output=True,
                                      text=True, timeout=30).stdout.strip() for part in parts}
        boot = [part for part, kind in types.items() if kind == 'ext4']
        assert len(boot) == 1, 'STOP: expected exactly one ext4 /boot on the target, found ' + repr(types)
        mount = tempfile.mkdtemp(prefix='aresos-target-boot-')
        try:
            subprocess.run(['mount', '-t', 'ext4', '-o', 'nosuid,nodev,noexec', boot[0], mount], check=True, timeout=60)
            try:  # unmounted only once the mount succeeded
                result = edit_boot_entries(mount)
            finally:
                subprocess.run(['umount', mount], check=True, timeout=60)
        finally:
            os.rmdir(mount)
        result.update(partition=boot[0].removeprefix(loop), partitions=types)
    finally:
        subprocess.run(['losetup', '--detach', loop], check=True, timeout=30)
    td.save(stage, dict(status='passed', image='target.raw', **result))
    return result


def prepare_and_switch(audit, media, password, hashed, release, commands=None):
    """Steps 4 to 6: offline stock, tools and prepare, then login, verify and switch."""
    Guest.network_up = False
    td.install(audit, password, hashed)
    pin_serial_console()
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
        console = Console(guest, commands=commands)
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
        console = Console(guest, commands=commands)
        console.login(password, 'corrected-stock')
        console.become_root(password, 'corrected-stock')
        console.run('title', 'corrected-stock-title')
        console.run('records', 'corrected-stock-records')
        public_typing(guest, 'corrected-stock', 'de', console)
        output = guest.command('corrected-stock-homebrew', pathlib.Path('os/tests/inherited-homebrew.sh').read_text().replace('@STAGE@', 'stock'))
        brew, = re.findall(r'^([0-9a-f]{64})  /', output, re.M)
        private_login(console)
        console.run('verify', 'owner-signature')
        console.run('switch', 'owner-switch')
        sw.inspect_transaction(guest.capture_json('owner-switch-pending', sw.framed('bootc status --json')), release, stock['checksum'])
        kb.deployment_snapshot(guest, 'owner-switch-staged')
        console.run('title', 'owner-switch-title')
        console.run('reboot', 'owner-switch-reboot')
    finally:
        finish(guest, audit, 'corrected-stock')
    return stock, brew


def qualification(audit, media, password, hashed, release=None):
    release = release or json.loads(pathlib.Path('os/manifest/release.json').read_text())['reference']
    stock, brew = prepare_and_switch(audit, media, password, hashed, release)
    abandoned_trial(audit, password, hashed, stock, release, brew)
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
                second.run('layout-proof', 'layout-reverted-proof', inputs=((LAYOUT_PROMPT, 'yz-/!ü', False),), password=password)
                second.logout('layout-reverted-logout')
                console.select()
                console.run('layout-finish', 'layout-revert-finish')
                console.run('layout-intl', 'layout-intl-begin')
                guest.owner_layout = 'us-intl'
                second.login(password, 'layout-intl-login')
                second.run('layout-proof', 'layout-intl-proof', inputs=((LAYOUT_PROMPT, 'yz-/!ü', False),), password=password)
                second.logout('layout-intl-logout')
                console.select()
                console.run('layout-finish', 'layout-intl-finish')
            elif stage == 'aresos-intl':
                console.run('layout-de', 'layout-de-begin')
                guest.owner_layout = 'de'
                second = Console(guest, 'tty4')
                second.login(password, 'layout-back-de-login')
                second.run('layout-proof', 'layout-back-de-proof', inputs=((LAYOUT_PROMPT, 'yz-/!ü', False),), password=password)
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
        abandoned_trial_reset=True, finished_layout_after_reset=True, layout_abandon=True, abandoned_trial_guarded_reboot=True,
        rollback_guard=True, rollback=True, keep_stock=True, next_stock_default=True,
        protected_disk_audits=True, nvram_rule_unchanged=True, bootnext_audits=True))


# Package 27: the owner's first update, from the laptop's real state.
# The laptop runs package 15f's tools (merged as 17fe261c, fingerprint
# 3ef85c4a...), which switched it to release 13 on 2026-11-09.
LAPTOP_TOOLS_COMMIT = '17fe261cc00e5dac39d443e0be30b849567daf4c'
LAPTOP_TOOLS = '3ef85c4adab3c8a5daf5bf26c2a40805d24bcb0c17b9327cfc55e7e96aeebefc'
LAPTOP_RELEASE = 'os/manifest/releases/13.json'
# Qualification 21's head: the policy scripts that last passed on release 13.
RELEASE_13_SCRIPTS = '3fd79165fa96406948c17ea90f94f943cd9bc201'
# The tools the laptop runs since its update on 2026-11-13 (package 27, merged as 41b06513:
# version 2, fingerprint 851eb742...). Package 22c's runs install them from history, so their
# route stays the laptop's when this checkout's bundle moves on to version 3.
TOOLS_V2_COMMIT = '41b06513c1972ac4ccf395c169fdf261381243b0'
TOOLS_V2 = '851eb742bfe20bd4b47370b9f2558494edf4b74056d7023cc0d412e32fee6f33'
ARES_SUDO_PROMPT = '[sudo] password for ares:'
ARES_LETTERS = 'abcdefghijklmnopqrstuvwx0123456789'
DAILY_PATH = '/var/home/ares/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin'
SYSTEM_PATH = '/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin'
HUB_TERMINAL = ['/usr/bin/foot', '--app-id=aresos.terminal', '/usr/bin/bash', '--rcfile', '/usr/share/aresos/bashrc', '-i']


def git_blob(commit, path):
    # owner_vm runs as root in the runner's checkout; trust only that checkout.
    return subprocess.check_output(['git', '-c', 'safe.directory=' + os.getcwd(), 'show', commit + ':' + path])


def laptop_payload(destination, commit=LAPTOP_TOOLS_COMMIT, fingerprint=LAPTOP_TOOLS):
    """A tools bundle the laptop ran, byte-exact from main's history (by default the 15f one)."""
    destination = pathlib.Path(destination)
    names = subprocess.check_output(['git', '-c', 'safe.directory=' + os.getcwd(), 'ls-tree', '-r', '--name-only',
        commit, 'os/owner-tools/payload'], text=True).split()
    assert names, 'STOP: the laptop tools are not in this checkout'
    for name in names:
        target = destination / name[len('os/owner-tools/payload/'):]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git_blob(commit, name))
    assert hashlib.sha256((destination / 'SHA256SUMS').read_bytes()).hexdigest() == fingerprint, 'STOP: laptop tools fingerprint'
    return destination


def laptop_commands():
    """The command strings of the laptop's tools; only line 8 of the bootstrap differs."""
    return dict(COMMANDS, install=bundle_module('bootstrap').command(LAPTOP_TOOLS))


def deployment_shape(snapshot, stock, expected, staged=False, queued=False):
    """Exactly package 22's reviewed lists: expected digests in order, stock last and pinned."""
    rows = snapshot['rpm']['deployments']
    status = snapshot['bootc']['status']
    assert snapshot['rpm']['transaction'] is None, 'STOP: a deployment transaction is active'
    assert [d['container-image-reference-digest'] for d in rows] == expected, 'STOP: unexpected deployment list'
    assert ke.key(rows[-1]) == ke.key(stock) and rows[-1]['pinned'], 'STOP: corrected stock identity or pin lost'
    assert not any(d['pinned'] for d in rows[:-1]), 'STOP: an AresOS deployment is pinned'
    assert [bool(d.get('staged')) for d in rows] == [staged and i == 0 for i in range(len(rows))], 'STOP: unexpected staged row'
    assert bool(status.get('staged')) == staged and bool(status.get('rollbackQueued')) == queued, 'STOP: unexpected pending state'
    if staged:
        assert status['staged']['image']['imageDigest'] == expected[0], 'STOP: staged release differs'
    booted, = [d for d in rows if d['booted']]
    assert ke.key(booted) == (status['booted']['ostree']['checksum'], status['booted']['ostree']['deploySerial'],
                              status['booted']['ostree']['stateroot']), 'STOP: bootc/rpm-ostree disagreement'
    return {d['container-image-reference-digest']: ke.key(d) for d in rows}, booted['container-image-reference-digest']


def result_lines(*results):
    return [line for result in results for line in result.get('result', [])]


# His graphical session on seat0 (guest.sh's lookup) is active again after a VT switch.
ACTIVE_DESKTOP = ('set -e; for n in {1..60}; do '
                  'session=$(loginctl list-sessions --no-legend | awk \'$3 == "ares" && $4 == "seat0" {print $1; exit}\'); '
                  'if test -n "$session" && test "$(loginctl show-session "$session" -p Active --value)" = yes '
                  '&& test "$(loginctl show-session "$session" -p State --value)" = active; then '
                  'loginctl show-session "$session" -p Id -p Active -p State -p Seat -p VTNr; exit 0; fi; '
                  'sleep 1; done; exit 1')


def path_probe(target, seconds, required):
    """Wait in the guest for the terminal's PATH probe; only the last attempt fails on a miss."""
    miss = "raise SystemExit('No terminal PATH probe')" if required else 'print(json.dumps(dict(found=False)))'
    return sw.framed('''python3 - <<'PY'
import json,pathlib,time
p=pathlib.Path(@TARGET@)
for n in range(@SECONDS@):
    if p.exists() and p.stat().st_size:
        value=json.loads(p.read_text()); value.update(found=True,owner_uid=p.stat().st_uid); print(json.dumps(value)); break
    time.sleep(1)
else: @MISS@
PY'''.replace('@TARGET@', repr(target)).replace('@SECONDS@', str(seconds)).replace('@MISS@', miss))


def terminal_path(guest, stage):
    """The PATH his AresOS terminal really exports, typed in foot like any command."""
    target = '/tmp/aresos-path-' + stage
    program = ('import json,os,pathlib\npathlib.Path(' + repr(target) + ').write_text(json.dumps('
               'dict(uid=os.getuid(),path=os.environ["PATH"])))\n')
    guest.keys(['ctrl', 'alt', 'f1'])
    guest.command(stage + '-path-foot', 'set -e; for n in {1..120}; do if test "$(cat /sys/class/tty/tty0/active)" = tty1 && pgrep -u ares -x foot; then exit 0; fi; sleep 1; done; exit 1')
    # Run 5 (43120759117) typed right after the switch and the probe never ran. As in
    # kb.foot, a serial round trip comes first, then his session must be active again,
    # then labwc gets a moment to take its input devices back (as tty3's sudo does).
    guest.command(stage + '-path-prepare', 'set -e; rm -f ' + target + '; printf %s ' + shlex.quote(
        base64.b64encode(program.encode()).decode()) + ' | base64 -d > /run/aresos-path.py; chmod 0644 /run/aresos-path.py')
    guest.command(stage + '-path-session', ACTIVE_DESKTOP)
    time.sleep(1)
    type_text(guest, 'python3 /run/aresos-path.py\n', 'de')
    value = guest.capture_json(stage + '-path-result', path_probe(target, 20, required=False))
    retried = value.get('found') is not True
    if retried:
        # This step proves his PATH; kb.foot already proved typing in foot on this boot.
        # One retry: clear whatever reached the line, then type the idempotent probe again.
        guest.screenshot(stage + '-path-miss')
        guest.keys(['ctrl', 'u'])
        type_text(guest, 'python3 /run/aresos-path.py\n', 'de')
        value = guest.capture_json(stage + '-path-retry-result', path_probe(target, 60, required=True))
    assert value.get('found') is True, 'STOP: no terminal PATH probe'
    value['retried'] = retried
    td.save(stage + '-terminal-path', value)
    guest.screenshot(stage + '-path')
    assert value['uid'] == value['owner_uid'] == 1001, 'STOP: the AresOS terminal does not run as ares'
    assert value['path'] == DAILY_PATH or value['path'].startswith(DAILY_PATH + ':'), 'STOP: the AresOS terminal lacks his PATH'
    return value


RULES = r'''import grp,json,os,pathlib,re,subprocess
# His commands below start from / , not from the root shell's home he cannot read (rehearsal run 7).
os.chdir('/')
env={'LC_ALL':'C','PATH':'/usr/sbin:/usr/bin'}
out={}
out['ares_in_wheel']='ares' in grp.getgrnam('wheel').gr_mem
listing=subprocess.run(['sudo','-l','-U','ares'],capture_output=True,text=True,env=env).stdout
out['sudo_all_with_password']=bool(re.search(r'^\s+\(ALL\) ALL$',listing,re.M)) and not re.search(r'NOPASSWD|!authenticate',listing)
out['sudo_keeps_no_ticket']='timestamp_timeout=0' in listing
n=subprocess.run(['runuser','-u','ares','--','sudo','-n','true'],capture_output=True,text=True,env=env)
out['sudo_n_refused']=n.returncode==1 and 'a password is required' in n.stderr
# The hash itself, as package 21's checks read it: `passwd -S` formats differ between the old
# Red Hat passwd ("PS") and shadow-utils' (rehearsal run 9 on Fedora 44's shadow-utils 4.19).
def password_set(entry):
    hashed=entry.split(':')[1]
    return hashed.startswith('$')
out['ares_password_set']=password_set(subprocess.check_output(['getent','shadow','ares'],text=True,env=env))
chrome=subprocess.run(['timeout','150','runuser','-u','ares','--','/usr/bin/env','HOME=/var/home/ares',
    '/usr/bin/google-chrome','--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
    '--user-data-dir=/tmp/aresos-chrome-rehearsal','--dump-dom','data:text/html,<p>ARESOS_CHROME_STARTED</p>'],
    capture_output=True,text=True,env=env)
out['chrome_started']=chrome.returncode==0 and 'ARESOS_CHROME_STARTED' in chrome.stdout
out['chrome_stderr_tail']=chrome.stderr[-400:] if not out['chrome_started'] else ''
out['chrome_version']=subprocess.check_output(['runuser','-u','ares','--','/usr/bin/google-chrome','--version'],text=True,env=env).strip()
labwc,=subprocess.check_output(['pgrep','-u','ares','-x','labwc'],text=True,env=env).split()
session=dict(s.split('=',1) for s in pathlib.Path('/proc',labwc,'environ').read_bytes().decode().split('\0') if '=' in s)
out['session_path']=session.get('PATH')
out['hub_terminal_argv']=json.loads(pathlib.Path('/usr/share/aresos/apps/terminal.json').read_text()).get('argv')
listed=subprocess.run(['runuser','-u','ares','--','/usr/bin/env','-i','HOME=/var/home/ares','PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin',
    '/usr/libexec/aresos-shell','--list'],capture_output=True,text=True)
out['aresos_shell']={row['id']:row['available'] for row in json.loads(listed.stdout)['apps']} if listed.returncode==0 else listed.stderr[-400:]
out['aresos_shell_executable']=os.access('/usr/libexec/aresos-shell',os.X_OK)
print(json.dumps(out))
'''


def release_rules(guest, stage):
    """Package 21's rules on the updated laptop state, after the owner set the password."""
    value = guest.capture_json(stage + '-rules', sw.framed('python3 -c ' + shlex.quote(RULES)))
    td.save(stage + '-package21-rules', value)
    for name in ('ares_in_wheel', 'sudo_all_with_password', 'sudo_keeps_no_ticket', 'sudo_n_refused',
                 'ares_password_set', 'chrome_started', 'aresos_shell_executable'):
        assert value[name] is True, 'STOP: package 21 rule failed on the updated system: ' + name
    assert value['session_path'] == SYSTEM_PATH, 'STOP: the session lost the system PATH'
    assert value['hub_terminal_argv'] == HUB_TERMINAL, "STOP: the hub's terminal does not read his PATH"
    assert value['aresos_shell'] == {'browser': True, 'notepad': True, 'terminal': True}, 'STOP: aresos-shell apps'
    return value


# Package 21: no polkit grant lets `ares` act without his password beyond the
# reviewed list (os/ci/polkit-review.json, which polkit-check.js enforces on the
# image's rules). Here polkitd itself answers every installed action for his
# active desktop session on the updated system, so /etc kept from release 13
# counts too. pkcheck: 0 authorized, 1 not authorized, 2 needs authentication.
POLKIT = r'''import json,subprocess
env={'LC_ALL':'C','PATH':'/usr/sbin:/usr/bin'}
rows=[r.split() for r in subprocess.check_output(['loginctl','list-sessions','--no-legend'],text=True,env=env).splitlines()]
session,=[r[0] for r in rows if r[2:4]==['ares','seat0']]
state=dict(l.split('=',1) for l in subprocess.check_output(['loginctl','show-session',session,'-p','Active','-p','Remote'],
    text=True,env=env).splitlines())
labwc,=subprocess.check_output(['pgrep','-u','ares','-x','labwc'],text=True,env=env).split()
scope=open('/proc/'+labwc+'/cgroup').read()
actions=subprocess.check_output(['pkaction'],text=True,env=env).split()
codes={a:subprocess.run(['pkcheck','--action-id',a,'--process',labwc],capture_output=True,env=env).returncode for a in actions}
print(json.dumps(dict(session_active=state.get('Active'),session_remote=state.get('Remote'),
    session_scope=('/session-'+session+'.scope') in scope,actions=len(actions),
    answers={str(c):sum(1 for v in codes.values() if v==c) for c in sorted(set(codes.values()))},
    passwordless=sorted(a for a,c in codes.items() if c==0))))
'''


def polkit_sweep(guest, stage):
    """Every installed polkit action, asked for his active desktop session on the booted release."""
    reviewed = set(json.loads(pathlib.Path('os/ci/polkit-review.json').read_text())['passwordless'])
    value = guest.capture_json(stage + '-polkit', sw.framed('python3 -c ' + shlex.quote(POLKIT)))
    td.save(stage + '-polkit-sweep', value)
    assert value['session_active'] == 'yes' and value['session_remote'] == 'no' and value['session_scope'] is True, \
        'STOP: the polkit sweep needs his active local desktop session'
    assert value['actions'] > 0 and set(value['answers']) <= {'0', '1', '2'}, 'STOP: polkit did not answer every action'
    extra = sorted(set(value['passwordless']) - reviewed)
    assert not extra, 'STOP: polkit lets ares act without his password beyond the reviewed list: ' + ', '.join(extra)
    return value


def owner_scripts(guest, stage, commit=None, homebrew_stage='aresos'):
    """Policy and inherited-Homebrew checks of the release that is booted."""
    read = (lambda path: git_blob(commit, path).decode()) if commit else (lambda path: pathlib.Path(path).read_text())
    policy = guest.command(stage + '-policy', read('os/tests/guest.sh'))
    output = guest.command(stage + '-homebrew', read('os/tests/inherited-homebrew.sh').replace('@STAGE@', homebrew_stage))
    hashes = re.findall(r'^([0-9a-f]{64})  /', output, re.M)
    assert len(hashes) == 1
    return policy, hashes[0]


def laptop_update(audit, media, password, hashed, bundle=None):
    """The laptop's history up to the restart into the new release (package 27's route, unchanged).

    Steps 4 to 6 with the laptop's 15f tools, then step 8 on release 13: the newer tools through the
    bootstrap, `update`, and the restart. bundle: (folder, fingerprint) of the step 8 tools when they
    are not this checkout's payload (package 22c installs version 2 from history). Returns the
    references, digests, stock record, Homebrew hash and first identities the later boots compare.
    """
    old = json.loads(pathlib.Path(LAPTOP_RELEASE).read_text())['reference']
    new = json.loads(pathlib.Path('os/manifest/release.json').read_text())['reference']
    old_digest, new_digest = old.split('@')[1], new.split('@')[1]
    assert old != new and media.fingerprint == LAPTOP_TOOLS
    history = json.loads(pathlib.Path('os/owner-tools/history.json').read_text())['releases']
    assert [r['reference'] for r in history[-2:]] == [old, new] and history[-1]['daily_wheel'] is True
    # Steps 4 to 6 as on 2026-11-08/09, with the laptop's own tools.
    stock, brew = prepare_and_switch(audit, media, password, hashed, old, laptop_commands())
    stock_digest = stock['container-image-reference-digest']
    if bundle is None:
        media.replace('update-windows-copy')
        assert media.fingerprint == bundle_module('bundle').check(pathlib.Path('os/owner-tools/payload'))
        commands = COMMANDS
    else:
        media.replace('update-windows-copy', source=bundle[0])
        assert media.fingerprint == bundle[1]
        # As laptop_commands(): only the fingerprint line of the bootstrap differs between bundles.
        commands = dict(COMMANDS, install=bundle_module('bootstrap').command(bundle[1]))
    guest = td.start_installed(password, hashed, 'release-13')
    try:
        snapshot = kb.deployment_snapshot(guest, 'release-13')
        ke.retained_pair(snapshot, stock, old)
        assert sw.booted_digest(snapshot['bootc']) == old_digest
        first = {d['container-image-reference-digest']: ke.key(d) for d in snapshot['rpm']['deployments']}
        keyboard(guest, 'release-13', 'de')
        console = Console(guest, commands=laptop_commands())
        console.login(password, 'release-13')
        console.become_root(password, 'release-13')
        console.run('check', 'release-13-check')
        console.run('title', 'release-13-title')
        console.run('records', 'release-13-records')
        public_typing(guest, 'release-13', 'de', console, foot=True)
        _, observed = owner_scripts(guest, 'release-13', RELEASE_13_SCRIPTS)
        assert observed == brew
        # Step 8: the new tools first, through the same 13-line bootstrap.
        media.attach(guest, 'update-tools')
        console.commands = commands
        installed = console.run('install', 'update-tools-install', record='tools-update')
        assert installed['manifest'] == media.fingerprint and installed['previous_manifest'] == LAPTOP_TOOLS
        assert (installed['previous_version'], installed['tools_version']) == (1, 2)
        assert installed['releases'][-1]['reference'] == new
        update = console.run('update', 'owner-update')
        assert 'Signed exact release staged ' + new in result_lines(update)
        staged, _ = deployment_shape(kb.deployment_snapshot(guest, 'owner-update-staged'), stock,
                                     [new_digest, old_digest, stock_digest], staged=True)
        assert staged[old_digest] == first[old_digest], 'STOP: the running release changed while staging'
        console.run('title', 'owner-update-title')
        console.run('export', 'owner-update-export')
        media.detach(guest, 'update-tools')
        console.run('reboot', 'owner-update-reboot')
    finally:
        finish(guest, audit, 'release-13')
    return dict(old=old, new=new, old_digest=old_digest, new_digest=new_digest, stock=stock, stock_digest=stock_digest,
                brew=brew, first=first)


def confirmed_update(guest, password, route):
    """The new release's first start: the reviewed list, then `check` and `title` confirm the update.

    Returns the root console on tty3 and the three deployments' identities by digest.
    """
    identities, booted = deployment_shape(kb.deployment_snapshot(guest, 'release-27'), route['stock'],
                                          [route['new_digest'], route['old_digest'], route['stock_digest']])
    assert booted == route['new_digest'] and identities[route['old_digest']] == route['first'][route['old_digest']], \
        'STOP: the update did not boot the new release'
    keyboard(guest, 'release-27', 'de')
    console = Console(guest)
    console.login(password, 'release-27')
    console.become_root(password, 'release-27')
    checked = console.run('check', 'release-27-check')
    titled = console.run('title', 'release-27-title')
    assert 'Update to ' + route['new'] + ' confirmed after the restart' in result_lines(checked, titled), 'STOP: update not confirmed'
    return console, identities


def update_rehearsal(audit, media, password, hashed, ares_password):
    route = laptop_update(audit, media, password, hashed)
    old, new, old_digest, new_digest = (route[name] for name in ('old', 'new', 'old_digest', 'new_digest'))
    stock, stock_digest, brew, first = (route[name] for name in ('stock', 'stock_digest', 'brew', 'first'))
    guest = td.start_installed(password, hashed, 'release-27')
    try:
        console, identities = confirmed_update(guest, password, route)
        updated = identities[new_digest]
        console.run('records', 'release-27-records')
        public_typing(guest, 'release-27', 'de', console, foot=True)
        terminal = terminal_path(guest, 'release-27')
        # terminal_path left his desktop in front, so polkit sees his active session.
        policy, observed = owner_scripts(guest, 'release-27')
        assert observed == brew and 'ARESOS_ACTIVE_SESSION_POLKIT_PASSED' in policy and 'ARESOS_GUEST_CHECKS_PASSED' in policy
        polkit = polkit_sweep(guest, 'release-27')
        # The one-time administrator password, as the guide says, then his sudo.
        console.passwd(ares_password, 'release-27-ares-password')
        Console(guest, 'tty4').ares_sudo(ares_password, 'release-27-ares-sudo')
        console.select()
        rules = release_rules(guest, 'release-27')
        returned = console.run('previous', 'owner-previous')
        assert 'Previous AresOS queued for the next start ' + old in result_lines(returned)
        queued, _ = deployment_shape(kb.deployment_snapshot(guest, 'owner-previous-queued'), stock,
                                     [old_digest, new_digest, stock_digest], queued=True)
        assert queued[new_digest] == updated and queued[old_digest] == first[old_digest]
        console.run('title', 'owner-previous-title')
        console.run('reboot', 'owner-previous-reboot')
    finally:
        finish(guest, audit, 'release-27')
    guest = td.start_installed(password, hashed, 'previous-13')
    try:
        identities, booted = deployment_shape(kb.deployment_snapshot(guest, 'previous-13'), stock,
                                              [old_digest, new_digest, stock_digest])
        assert booted == old_digest and identities == {new_digest: updated, old_digest: first[old_digest], stock_digest: ke.key(stock)}
        keyboard(guest, 'previous-13', 'de')
        console = Console(guest)
        console.login(password, 'previous-13')
        console.become_root(password, 'previous-13')
        checked = console.run('check', 'previous-13-check')
        titled = console.run('title', 'previous-13-title')
        assert 'Return to ' + old + ' confirmed after the restart' in result_lines(checked, titled), 'STOP: return not confirmed'
        console.run('records', 'previous-13-records')
        public_typing(guest, 'previous-13', 'de', console, foot=True)
        # No forward route exists after a return (PLAN-GAP): update refuses and changes nothing.
        refused = console.run('update', 'previous-13-update-refused', expect_stop=True)
        assert refused['error'] == 'Target release is already deployed; get help'
        assert not any(r.get('mutation') for r in refused['trace']), 'STOP: the refused update changed something'
        after, _ = deployment_shape(kb.deployment_snapshot(guest, 'previous-13-after-refusal'), stock,
                                    [old_digest, new_digest, stock_digest])
        assert after == identities
        console.logout('previous-13-logout')
    finally:
        finish(guest, audit, 'previous-13')
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)
    td.save('update-rehearsal-result', dict(status='passed', commit=os.environ['GITHUB_SHA'], order='protected-second',
        starting_state='corrected pinned stock switched to release 13 by the laptop tools (15f)',
        laptop_tools=LAPTOP_TOOLS, laptop_tools_commit=LAPTOP_TOOLS_COMMIT, previous_release=old, release=new,
        bundle_manifest=media.fingerprint, tools_updated_from_version=1, tools_updated_to_version=2,
        update_staged=True, update_confirmed=True, previous_confirmed=True, forward_after_previous='refused (no route)',
        ares_password_set_by_typing=True, ares_sudo_password_accepted=True, ares_sudo_no_ticket=True,
        package21_rules=rules, terminal_path=terminal['path'], terminal_path_retried=terminal['retried'],
        stock_pinned_throughout=True,
        polkit_sweep=dict(actions=polkit['actions'], answers=polkit['answers'], passwordless=len(polkit['passwordless'])),
        deployments=dict(release_13=list(first[old_digest]), release_27=list(updated), stock=list(ke.key(stock))),
        owner_commands_physically_typed=True, protected_disk_audits=True, nvram_rule_unchanged=True, bootnext_audits=True))


# Package 22c, stage 0 (brief P): plain `ostree admin set-default` over the laptop's three
# deployments. The owner tools are used only on the way there (package 27's route); from release 27
# confirmed on, every command is plain and runs in the harness's root shell on the serial console.
def reorder_boot(audit, password, hashed, probe, stage, running, reached, stock_starts, step, guest=None):
    """One start of the walk: capture and prove the row; then `step(guest, snapshot)` and a restart, or the end."""
    if guest is None:
        guest = td.start_installed(password, hashed, stage)
    try:
        guest.owner_layout = 'de'
        facts, snapshot = probe.restarted(guest, stage, reached, running)
        if facts['running'] == 'S':
            # P6: a start of the stock takes the German login (the password is typed with German
            # key positions on tty3) and shows its greeter, as package 14's stock stages prove it.
            keyboard(guest, stage, 'de')
            console = Console(guest)
            console.login(password, stage)
            console.logout(stage + '-logout')
            kb.capture_stock_greeter(guest, td.EVIDENCE, stage + '-greeter')
            stock_starts.append(stage)
        if step is not None:
            step(guest, snapshot)
            guest.reboot(stage)
        return facts
    finally:
        finish(guest, audit, stage)


def reorder_probe(audit, media, password, hashed, version_2):
    """version_2: the folder with the laptop's current tools bundle (laptop_payload at TOOLS_V2_COMMIT)."""
    route = laptop_update(audit, media, password, hashed, bundle=(version_2, TOOLS_V2))
    stock = route['stock']
    stock_starts, menu = [], dict(backup=None, entry_rule=None, choice=None, path=None, stock_entry=None)
    guest = td.start_installed(password, hashed, 'release-27')
    try:
        console, identities = confirmed_update(guest, password, route)
        # The owner tools are not used again in this run.
        console.logout('release-27-logout')
        probe = rp.Probe(dict(R27=identities[route['new_digest']], R13=identities[route['old_digest']], S=ke.key(stock)))
        _, snapshot = probe.capture(guest, 'walk-0-start', "package 27's route: release 27 confirmed", running='R27', order=rp.START)
        probe.move(guest, 'walk-1-moved', rp.MOVES[0], snapshot)
        guest.reboot('release-27')
    finally:
        finish(guest, audit, 'release-27')
    # Nothing in the walk needs the network; without it nothing else can stage a deployment.
    Guest.network_up = False

    def prepare_menu(guest, snapshot):
        # The start order again. Find the stock row through its boot entry and show the menu once.
        menu['stock_entry'], = [e['file'].removesuffix('.conf') for e in probe.last['entries'] if e['role'] == 'S']
        menu['backup'], menu['entry_rule'], _ = rp.recorded_stock_entry(guest, 'menu', snapshot, stock['checksum'])
        if menu['backup'] is not None:
            rp.show_menu_once(guest, 'menu')
        else:
            rp.one_time_entry(guest, 'menu', menu['stock_entry'])

    for number, order in enumerate(rp.ORDERS, 1):
        step = prepare_menu if number == len(rp.MOVES) else \
            (lambda guest, snapshot, number=number: probe.move(guest, f'walk-{number + 1}-moved', rp.MOVES[number], snapshot))
        reorder_boot(audit, password, hashed, probe, f'walk-{number}-booted', order[0], 'restart with no choice', stock_starts, step)

    # One choice in the boot menu, from the start order: the stock row (package 11's selection).
    stage, guest = 'menu-stock', None
    if menu['backup'] is not None:
        guest = rp.start_at_menu(password, hashed, stage)
        try:
            menu['choice'] = rp.menu_choice(guest, menu['backup'], stage)
            guest.login()
        except BaseException:
            finish(guest, audit, stage)
            raise
    selected = bool(menu['choice'] and menu['choice']['selected'])
    menu['path'] = ('boot menu: Home, Down x' + str(menu['backup']['menu_index']) + ', Enter, after the rows read as recorded' if selected
                    else 'one-time start of the stock entry by its id (the boot entries do not follow the recorded rule)'
                    if menu['backup'] is None else None)

    def without_the_menu(guest, snapshot):
        if probe.last['running'] != 'S':
            # Package 11's fallback: nothing is guessed in a menu that was not read or took no keys.
            rp.one_time_entry(guest, 'menu-fallback', menu['stock_entry'])
    facts = reorder_boot(audit, password, hashed, probe, stage, 'S' if menu['path'] else None,
                         'the stock row taken in the boot menu' if selected else
                         'the stock entry started once by its id' if menu['backup'] is None else
                         'restart with the boot menu shown; no row could be taken',
                         stock_starts, without_the_menu, guest=guest)
    probe.expect(stage, 'the stock row could be taken in the boot menu', selected and facts['running'] == 'S',
                 dict(entry_rule=menu['entry_rule'], choice=menu['choice'], running=facts['running']))
    if facts['running'] != 'S':
        stage = 'menu-stock-one-time'
        menu['path'] = 'one-time start of the stock entry by its id, after the boot menu could not be driven'
        facts = reorder_boot(audit, password, hashed, probe, stage, 'S', 'the stock entry started once by its id',
                             stock_starts, lambda guest, snapshot: None)
    probe.expect(stage, 'a row that is not first runs while the order stays', facts['running'] == 'S' and facts['order'] == list(rp.START),
                 dict(running=facts['running'], order=facts['order']))
    last = 'after-menu-booted'
    final = reorder_boot(audit, password, hashed, probe, last, 'R27', 'restart with no choice', stock_starts, None)
    probe.expect(last, 'the run ends on the start order with nothing else changed',
                 final['order'] == list(rp.START) and final['stable'] == probe.reference['stable']
                 and final['options'] == probe.reference['options'], dict(order=final['order']))
    probe.expect(last, 'the six moves visited all six orders', [row['after'] for row in probe.swaps] == [list(o) for o in rp.ORDERS],
                 [row['after'] for row in probe.swaps])
    probe.expect(last, 'every start of the stock showed its greeter and took the German login', len(stock_starts) == 3, stock_starts)
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)
    result = probe.result(commit=os.environ['GITHUB_SHA'], order='protected-second',
        starting_state="package 27's route: corrected pinned stock, release 13 by the laptop tools (15f), release 27 by tools version 2",
        laptop_tools=LAPTOP_TOOLS, tools_version_2=TOOLS_V2, tools_version_2_commit=TOOLS_V2_COMMIT,
        previous_release=route['old'], release=route['new'], owner_tools_used_after_confirmation=False,
        commands='plain, as root, in the serial root shell', network_during_walk=False,
        deployments={role: list(identity) for identity, role in probe.roles.items()}, stock_starts=stock_starts,
        menu=dict(path=menu['path'], entry_rule=menu['entry_rule'], choice=menu['choice'], stock_entry=menu['stock_entry'],
                  rows=menu['backup'] and dict(titles=menu['backup']['menu_titles'], ids=menu['backup']['menu_ids'],
                                               stock_position=menu['backup']['menu_index'])),
        protected_disk_audits=True, nvram_rule_unchanged=True, bootnext_audits=True)
    td.save('reorder-probe-result', result)
    assert result['status'] == 'passed', 'STOP: the probe contradicts the brief: ' + '; '.join(
        row['stage'] + ': ' + row['point'] for row in result['expectations']['contradicted'])


# Package 22c, stage 2 (brief E): every way back, typed as the owner types, from the laptop's
# history. Package 27's route up to release 27 confirmed (tools version 2), then this checkout's
# tools (version 3) through the guide's stick block, layout trials, and every way between the
# three installed systems. `forward` wherever the walk returns to an installed AresOS; `update`
# only where it has nothing to install (release 27 is these tools' release) and names forward.
WAYS_BACK_ROLES = dict(R27='newer AresOS', R13='older AresOS', S='plain Bazzite')
# word: (the system it makes the next start, how its change is named, its own line)
WAYS = {'forward': ('R27', 'Forward to ', 'Newest installed AresOS starts next {}'),
        'previous': ('R13', 'Return to ', 'Previous AresOS queued for the next start {}'),
        'rollback': ('S', 'Rollback to ', 'Saved stock rollback queued'),
        'keep-stock': ('S', 'Change to ', 'Saved stock is default')}

# Brief E7's window, from a second root shell (the harness's serial one): as soon as the list
# shows the new order (ostree swaps the link under /sysroot/ostree, probe run 43470161858), the
# tools' own process is stopped. Its release step still ends (set-default, the step's sync, its
# last read); the tools can never write their record. Nothing of this is in the bundle.
CUT_WATCH = r'''import json,os,pathlib,signal,time
OSTREE,OUT='/sysroot/ostree','/run/aresos-cut.json'
out=pathlib.Path(OUT)
def write(value):
    temporary=out.with_suffix('.new'); temporary.write_text(json.dumps(value)); temporary.replace(out)
def links():
    # boot.<version> only: ostree swaps it by renaming a temporary link over it.
    found=[]
    for e in os.scandir(OSTREE):
        if e.name.startswith('boot.') and e.name[5:].isdigit():
            try: found.append((e.name,os.readlink(e.path)))
            except OSError: pass
    return sorted(found)
def processes():
    rows={}
    for p in pathlib.Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                fields=(p/'stat').read_text().rsplit(')',1)[1].split()
                rows[int(p.name)]=dict(state=fields[0],parent=int(fields[1]),argv=(p/'cmdline').read_bytes().split(b'\0'))
            except (OSError,ValueError,IndexError): pass
    return rows
def tools(rows):
    return [pid for pid,row in rows.items() if len(row['argv'])>=5 and row['argv'][0]==b'/usr/bin/python3'
            and row['argv'][3].endswith(b'/owner.py') and row['argv'][4]==b'rollback']
def below(rows,pid):
    found,todo=[],[pid]
    while todo:
        parent=todo.pop()
        for child,row in rows.items():
            if row['parent']==parent and child not in found: found.append(child); todo.append(child)
    return found
before=links()
assert before, 'no deployment link to watch'
write(dict(status='watching',links_before=before))
deadline=time.monotonic()+900
pid,scanned=None,0.0
while links()==before:
    if time.monotonic()>deadline:
        write(dict(status='no reorder seen',links_before=before)); raise SystemExit(1)
    if pid is None and time.monotonic()-scanned>.05:
        scanned=time.monotonic(); found=tools(processes()); pid=found[0] if len(found)==1 else None
    time.sleep(.002)
flipped=time.monotonic()
if pid is None:
    found=tools(processes()); pid=found[0] if len(found)==1 else None
if pid is None:
    write(dict(status='reorder seen without the tools process',links_before=before,links_after=links())); raise SystemExit(1)
os.kill(pid,signal.SIGSTOP)
stopped=time.monotonic()
while time.monotonic()<deadline:
    rows=processes()
    alive=[child for child in below(rows,pid) if rows[child]['state']!='Z']
    if pid in rows and rows[pid]['state'] in 'Tt' and not alive: break
    time.sleep(.05)
else:
    write(dict(status='the release step did not end',pid=pid)); raise SystemExit(1)
write(dict(status='frozen',pid=pid,state=rows[pid]['state'],links_before=before,links_after=links(),
    stop_after_swap_ms=round((stopped-flipped)*1000,3),release_step_ended=True))
'''

CUT_INTENT = r'''import json,pathlib
value=json.loads(pathlib.Path('/var/lib/ares/records/outcome-pending.json').read_text())
print(json.dumps({name:value.get(name) for name in ('schema','word','status','mode','reference','digest','target','before','intended','running')}))
'''

UPDATERS = r'''import json,subprocess
names=@NAMES@
listing=subprocess.check_output(['systemctl','--no-pager','--no-legend','list-unit-files'],text=True)
files={p[0]:p[1] for line in listing.splitlines() if len(p:=line.split())>=2 and p[0] in names}
active={}
for name in files:
    shown=subprocess.run(['systemctl','--no-pager','show',name,'--property=ActiveState'],capture_output=True,text=True).stdout
    active[name]=shown.strip().partition('=')[2]
print(json.dumps(dict(files=files,active=active)))
'''


def cut_wait(condition, seconds):
    """Wait in the guest until the cut watcher's file answers `condition`, and print it."""
    return ('import json,pathlib,time\np=pathlib.Path("/run/aresos-cut.json")\ndeadline=time.monotonic()+' + str(seconds) + '\n'
            'while time.monotonic()<deadline:\n    if p.exists():\n        value=json.loads(p.read_text())\n'
            '        if ' + condition + ':\n            print(json.dumps(value)); break\n    time.sleep(.2)\n'
            'else: raise SystemExit("The cut watcher did not answer")\n')


class WaysBack:
    """The rehearsal's record: every typed owner command with the lines it printed, and each
    stage's three deployments by identity (reorder_probe.Probe: nothing created, nothing removed,
    the stock pinned). A contradiction stops the walk: the next command would act on an unknown list."""

    def __init__(self, audit, password, hashed, route, identities):
        self.audit, self.password, self.hashed = audit, password, hashed
        stock = route['stock']
        self.probe = rp.Probe(dict(R27=identities[route['new_digest']], R13=identities[route['old_digest']], S=ke.key(stock)))
        digests = dict(R27=route['new_digest'], R13=route['old_digest'], S=route['stock_digest'])
        # The tools' names (rule 8): the role and the first twelve digits of the image digest.
        self.name = {role: WAYS_BACK_ROLES[role] + ' ' + digest.split(':')[1][:12] for role, digest in digests.items()}
        self.reference = dict(R27=route['new'], R13=route['old'], S=stock['container-image-reference']
                              .removeprefix('ostree-unverified-registry:').removeprefix('ostree-image-signed:docker://'))
        self.transcript, self.menus, self.stock_starts, self.cut_proof, self.updater_states = [], [], [], None, None
        self.boot_stage = 'release-27'
        # The folder of the toolset this walk installed (version 3); every layout proof must be read from it.
        self.toolset = None

    def checked(self, stage):
        missed = self.probe.contradicted()
        assert not missed, 'STOP: ' + stage + ': ' + '; '.join(row['stage'] + ': ' + row['point'] for row in missed)

    def run(self, console, name, stage, **more):
        """One owner command, typed; its lines go into the transcript."""
        result = console.run(name, stage, **more)
        result = result or dict(status='restart requested')
        self.transcript.append(dict(stage=stage, boot=self.boot_stage, system=self.probe.last['running'], console=console.tty,
            command=console.commands[name] if name != 'install' else "the guide's 13-line stick block (bash ./at install)",
            status=result['status'], lines=result.get('result', []), error=result.get('error')))
        return result

    def standing(self, lines, facts, settled=None):
        """Rule 8's first line and the row map, as the tools must print them for this list. The row
        numbers come from the boot entries the harness read itself, by identity."""
        order, running = facts['order'], facts['running']
        first = order[0]
        if first == running:
            line = self.name[running] + (' runs and now starts next; no restart is waiting' if settled == 'applied' else ' runs and starts next')
        elif settled == 'pending':
            line = self.name[running] + ' runs; ' + self.name[first] + ' starts next, after the restart'
        else:
            line = self.name[running] + ' runs; ' + self.name[first] + ' starts next; this start was not the default'
        place = {entry['role']: entry['title_index'] for entry in facts['entries']}
        menu = 'Boot menu at the next start: ' + '; '.join(
            '(ostree:%d) %s%s' % (place[role], self.name[role], ', starts next' if role == first else '') for role in order)
        assert line in lines, 'STOP: the tools do not say: ' + line
        assert menu in lines, "STOP: the title's row map differs from the boot entries: " + menu

    def begin(self, guest, stage, running, reached, layout='de'):
        """A start: the list by identity and the row that runs, then the owner's tty3 login and root."""
        guest.owner_layout, self.boot_stage = layout, stage
        self.probe.restarted(guest, stage, reached, running)
        self.checked(stage)
        keyboard(guest, stage, layout)
        console = Console(guest)
        console.login(self.password, stage)
        console.become_root(self.password, stage)
        if running == 'S':
            # Plain Bazzite's greeter beside its German login, as package 14's stock stages prove them.
            kb.capture_stock_greeter(guest, td.EVIDENCE, stage + '-greeter')
            self.stock_starts.append(stage)
        return console

    def start(self, stage, menu=None):
        if menu is None:
            return td.start_installed(self.password, self.hashed, stage)
        # The start stops at the boot menu, which was set to show once; the row is taken as recorded.
        guest = rp.start_at_menu(self.password, self.hashed, stage)
        try:
            choice = rp.menu_choice(guest, menu['backup'], stage)
            for name in ('b-grub-menu-ocr-proof', 'b-grub-selection'):
                # two_disk_vm writes one file per run; this walk takes two rows.
                if (td.EVIDENCE / (name + '.json')).exists():
                    shutil.copyfile(td.EVIDENCE / (name + '.json'), td.EVIDENCE / (stage + name[1:] + '.json'))
            self.menus.append(dict(stage=stage, system=menu['role'], row=menu['row'], titles=menu['backup']['menu_titles'], choice=choice))
            assert choice['selected'], 'STOP: the boot menu could not be driven: ' + str(choice.get('reason'))
            guest.login()
        except BaseException:
            finish(guest, self.audit, stage)
            raise
        return guest

    @contextlib.contextmanager
    def boot(self, stage, running, reached, layout='de', menu=None):
        guest = self.start(stage, menu)
        try:
            yield guest, self.begin(guest, stage, running, reached, layout)
        finally:
            finish(guest, self.audit, stage)

    def check(self, console, stage, confirmed=None, settled=None, also=(), never=()):
        """The guides' check box: `check`, then `title`. A confirmation shows once, in the check."""
        facts = self.probe.last
        checked = self.run(console, 'check', stage + '-check')['result']
        titled = self.run(console, 'title', stage + '-title')['result']
        for lines in (checked, titled):
            self.standing(lines, facts, settled)
        said = [line for line in checked + titled if 'confirmed after the restart' in line]
        assert said == ([confirmed + ' confirmed after the restart'] if confirmed else []) and (not confirmed or said[0] in checked), \
            'STOP: expected ' + (confirmed + ' confirmed once, in the check' if confirmed else 'no confirmation') + ': ' + repr(said)
        for line in also:
            assert line in checked, 'STOP: the check does not say: ' + line
        for word in ('WARNING', *never):
            assert not any(word in line for line in checked + titled), 'STOP: the check or the title says: ' + word
        return checked, titled

    def move(self, console, name, stage, settled='pending'):
        """A command that changes which system starts next: its own line, the title it prints
        (rule 5: waiting for the restart, or applied with nothing waiting), ostree's swap line."""
        role, change, said = WAYS[name]
        earlier = self.probe.journal(console.guest, stage + '-journal-before')
        lines = self.run(console, name, stage)['result']
        facts, _ = self.probe.tool_move(console.guest, stage, role, earlier, 'at ' + name)
        self.checked(stage)
        assert said.format(self.reference[role]) in lines, 'STOP: ' + name + ' does not say: ' + said.format(self.reference[role])
        self.standing(lines, facts, settled)
        waiting = change + self.reference[role] + ' is not finished until the restart'
        assert (waiting in lines) == (settled == 'pending'), 'STOP: ' + name + ': ' + waiting
        assert not any('confirmed' in line for line in lines), 'STOP: a confirmation before any start'
        return lines

    def nothing(self, console, name, stage, runs):
        """A command whose destination starts next already: it says so and changes nothing."""
        label = self.name[WAYS[name][0]]
        earlier = self.probe.journal(console.guest, stage + '-journal-before')
        lines = self.run(console, name, stage)['result']
        self.probe.unmoved(console.guest, stage, earlier, 'at ' + name + ': nothing changed')
        self.checked(stage)
        assert lines == [label[0].upper() + label[1:] + ' already starts next; nothing changed', runs], 'STOP: ' + name + ' says: ' + repr(lines)

    def refused(self, console, name, stage, starts, names):
        """A refusal: the line the guides quote, the command it names, nothing changed (no changing
        call in the tools' trace, the same list)."""
        earlier = self.probe.journal(console.guest, stage + '-journal-before')
        result = self.run(console, name, stage, expect_stop=True)
        error = str(result['error'])
        assert error.startswith(starts) and COMMANDS[names] in error and error.endswith('nothing changed'), \
            'STOP: ' + name + ' refused with: ' + error
        assert not any(row.get('mutation') for row in result['trace']), 'STOP: the refused ' + name + ' changed something'
        self.probe.unmoved(console.guest, stage, earlier, 'at ' + name + ' refused')
        self.checked(stage)

    def quiet(self, guest, stage, reached):
        """No list write in this boot so far (E7: the check records the cut change with no second reorder)."""
        self.probe.unmoved(guest, stage, [], reached)
        self.checked(stage)

    def restart(self, console, stage, take=None):
        """The guides' restart: a fresh title (older ones are INVALID), then `reboot`. With `take`,
        the next start shows the boot menu, and that system's row is found by the title's row map."""
        titled = self.run(console, 'title', stage + '-reboot-title')['result']
        menu = None
        if take is not None:
            guest = console.guest
            line, = [text for text in titled if text.startswith('Boot menu at the next start: ')]
            rows = {match[2]: int(match[1]) for match in re.finditer(r'\(ostree:([0-9]+)\) ([^;,]+)', line)}
            row = rows[self.name[take]]
            identity, = [identity for identity, role in self.probe.roles.items() if role == take]
            snapshot = kb.deployment_snapshot(guest, stage + '-menu')
            backup, error, _ = rp.recorded_stock_entry(guest, stage + '-menu', snapshot, identity[0])
            assert backup is not None, 'STOP: the boot entries do not follow the recorded rule: ' + str(error)
            assert backup['menu_index'] == row and backup['menu_titles'][row].endswith('(ostree:%d)' % row), \
                "STOP: the title's row map and the boot entries name different rows"
            rp.show_menu_once(guest, stage + '-menu')
            menu = dict(role=take, row=row, backup=backup)
        self.run(console, 'reboot', stage + '-owner-reboot')
        return menu

    def trial(self, console, begin, profile):
        """Later layout (the procedures guide): begin, a fresh tty4 login in the new layout, proof, finish."""
        guest = console.guest
        self.run(console, begin, begin + '-begin')
        guest.owner_layout = profile
        second = Console(guest, 'tty4')
        second.login(self.password, begin + '-login')
        self.run(second, 'layout-proof', begin + '-proof', inputs=((LAYOUT_PROMPT, TEXT, False),), password=self.password)
        # The folder was read in the guest before the proof (Console.toolset); it is this walk's version 3.
        assert second.tools == self.toolset, 'STOP: the proof was not read by the tools this walk installed'
        second.logout(begin + '-logout')
        console.select()
        self.run(console, 'layout-finish', begin + '-finish')

    def updaters(self, guest, stage):
        """E4: Bazzite's own updater timers are still disabled for good (the list rule 10 reads)."""
        names = bundle_module('owner').program(pathlib.Path('os/owner-tools/payload'), 'pause-stock-updates', 'PAUSE_STOCK')['SYSTEM']
        value = guest.capture_json(stage + '-updaters', sw.framed('python3 -c ' + shlex.quote(UPDATERS.replace('@NAMES@', repr(tuple(names))))))
        td.save(stage + '-stock-updaters', value)
        timers = {name: state for name, state in value['files'].items() if name.endswith('.timer')}
        assert 'uupd.timer' in timers and all(state in ('disabled', 'masked') for state in timers.values()), \
            'STOP: a Bazzite updater timer is on: ' + repr(timers)
        assert all(state in ('inactive', 'failed') for state in value['active'].values()), 'STOP: a Bazzite updater runs'
        self.updater_states = value

    def cut(self, console, stage):
        """E7: `rollback`, cut by one hard reset after its reorder is on disk and before its record."""
        guest, probe = console.guest, self.probe
        program = base64.b64encode(CUT_WATCH.encode()).decode()
        guest.command(stage + '-watch', 'set -e; rm -f /run/aresos-cut.json; printf %s ' + shlex.quote(program) +
                      ' | base64 -d > /run/aresos-cut.py\npython3 /run/aresos-cut.py > /run/aresos-cut.log 2>&1 < /dev/null &')
        guest.capture_json(stage + '-armed', sw.framed('python3 -c ' + shlex.quote(cut_wait("value['status']=='watching'", 30))))
        earlier = probe.journal(guest, stage + '-journal-before')
        owner_xhci.checkpoint(guest, stage + '-begin')
        console.select()
        console.prompt(stage + '-ready')
        console.visible(console.commands['rollback'] + '\n', stage + '-command')
        watcher = guest.capture_json(stage + '-frozen', sw.framed('python3 -c ' + shlex.quote(cut_wait("value['status']!='watching'", 300))))
        td.save(stage + '-watcher', watcher)
        assert watcher['status'] == 'frozen' and watcher['state'] in ('T', 't') and watcher['release_step_ended'], \
            'STOP: the rollback was not stopped after its reorder: ' + str(watcher['status'])
        facts, _ = probe.tool_move(guest, stage, 'S', earlier, 'at rollback, stopped after its reorder and before its record')
        self.checked(stage)
        intent = guest.capture_json(stage + '-intent', sw.framed('python3 -c ' + shlex.quote(CUT_INTENT)))
        stock, = [list(identity) for identity, role in probe.roles.items() if role == 'S']
        self.cut_proof = dict(stage=stage, watcher=watcher, journal=intent, order=facts['order'], running=facts['running'],
                              reset='QMP system_reset', journal_holds='the intent' if intent['status'] == 'intent' else intent['status'])
        td.save(stage + '-proof', self.cut_proof)
        # With the record already written the reset would not test the cut (brief E7): repeat the run.
        assert intent['status'] != 'recorded', 'STOP: the journal already holds the record: the cut was not tested; repeat it'
        assert (intent['word'], intent['status'], intent['mode'], intent['target']) == ('rollback', 'intent', 'reorder', stock), \
            'STOP: unexpected journal before the reset'
        assert facts['order'][0] == 'S' and facts['running'] == 'R27', 'STOP: the reorder is not in place before the reset'
        self.transcript.append(dict(stage=stage, boot=self.boot_stage, system='R27', console=console.tty, command=console.commands['rollback'],
            status='cut by a hard reset after its reorder and before its record', lines=[], error=None))
        guest.hard_reset(stage)


def ways_back_rehearsal(audit, media, password, hashed, ares_password, version_2):
    """version_2: the folder with the laptop's current tools bundle (laptop_payload at TOOLS_V2_COMMIT)."""
    route = laptop_update(audit, media, password, hashed, bundle=(version_2, TOOLS_V2))
    old, new = route['old'], route['new']
    # The guide's Windows side for new tools: this checkout's bundle (version 3) onto the stick.
    media.replace('tools-3')
    assert media.fingerprint == bundle_module('bundle').check(pathlib.Path('os/owner-tools/payload')) != TOOLS_V2
    guest = td.start_installed(password, hashed, 'release-27')
    try:
        console, identities = confirmed_update(guest, password, route)
        walk = WaysBack(audit, password, hashed, route, identities)
        walk.probe.capture(guest, 'release-27-start', "package 27's route: release 27 confirmed", running='R27', order=rp.START)
        walk.checked('release-27-start')
        # The one-time administrator password, as the guide says, then his sudo.
        console.passwd(ares_password, 'release-27-ares-password')
        Console(guest, 'tty4').ares_sudo(ares_password, 'release-27-ares-sudo')
        console.select()
        # E1: the tools update themselves from the stick (version 2 to 3), then the tools-only box.
        media.attach(guest, 'tools-3')
        installed = walk.run(console, 'install', 'tools-3-install', record='tools-update')
        assert installed['manifest'] == media.fingerprint and installed['previous_manifest'] == TOOLS_V2
        assert (installed['previous_version'], installed['tools_version']) == (2, 3)
        # A tools update publishes its toolset as tools-<fingerprint> (owner.py, installed_update).
        walk.toolset = '/var/lib/ares/tools-' + installed['manifest']
        walk.check(console, 'tools-3')
        media.detach(guest, 'tools-3')
        # E2: a layout trial to US International, then the restart.
        walk.trial(console, 'layout-intl', 'us-intl')
        walk.restart(console, 'release-27')
    finally:
        finish(guest, audit, 'release-27')
    # Nothing from here on needs the network, and without it nothing else can stage a deployment.
    Guest.network_up = False
    with walk.boot('intl-27', 'R27', 'restart with no choice', layout='us-intl') as (guest, console):
        walk.check(console, 'intl-27')
        public_typing(guest, 'intl-27', 'us-intl', console, foot=True)
        # Back to German the same way.
        walk.trial(console, 'layout-de', 'de')
        walk.restart(console, 'intl-27')
    with walk.boot('trial-27', 'R27', 'restart with no choice') as (guest, console):
        walk.check(console, 'trial-27')
        public_typing(guest, 'trial-27', 'de', console, foot=True)
        # One trial ended by a hard reset (package 14's abandoned trial, here over three deployments).
        before = keyboard(guest, 'trial-27-before', 'de')
        walk.run(console, 'layout-us', 'trial-27-begin-us')
        guest.owner_layout = 'us'
        pending = keyboard(guest, 'trial-27-pending', 'de', loaded_profile='us')
        assert pending['console'] == before['console'] and pending['x11'] == before['x11'], 'Trial persisted boot/greeter settings'
        guest.hard_reset('trial-27')
    with walk.boot('abandon-27', 'R27', 'a hard reset during a layout trial') as (guest, console):
        finished_consoles(guest, 'abandon-27')
        walk.run(console, 'layout-abandon', 'abandon-27-abandon')
        walk.check(console, 'abandon-27')
        # E3: the AresOS from before the update.
        walk.move(console, 'previous', 'owner-previous-1')
        walk.restart(console, 'abandon-27')
    with walk.boot('back-13', 'R13', 'restart with no choice') as (guest, console):
        walk.check(console, 'back-13', confirmed='Return to ' + old)
        # update has nothing to install and selects nothing: it names forward, nothing changed.
        walk.refused(console, 'update', 'back-13-update-refused', 'The release of these tools is installed already', 'forward')
        walk.move(console, 'forward', 'owner-forward-1')
        walk.restart(console, 'back-13')
    with walk.boot('forward-27', 'R27', 'restart with no choice') as (guest, console):
        walk.check(console, 'forward-27', confirmed='Forward to ' + new)
        # His password from the start still passes sudo -v (each system keeps its own /etc).
        Console(guest, 'tty4').ares_sudo(ares_password, 'forward-27-ares-sudo')
        console.select()
        # E4: plain Bazzite and back.
        walk.move(console, 'rollback', 'owner-rollback-1')
        walk.restart(console, 'forward-27')
    with walk.boot('stock-1', 'S', 'restart with no choice') as (guest, console):
        walk.check(console, 'stock-1', confirmed='Rollback to ' + walk.reference['S'])
        walk.refused(console, 'rollback', 'stock-1-rollback-refused', 'Plain Bazzite runs here: use ', 'keep-stock')
        walk.nothing(console, 'keep-stock', 'stock-1-keep-stock', 'It runs now')
        walk.updaters(guest, 'stock-1')
        walk.move(console, 'forward', 'owner-forward-2')
        walk.restart(console, 'stock-1')
    with walk.boot('forward-27b', 'R27', 'restart with no choice') as (guest, console):
        walk.check(console, 'forward-27b', confirmed='Forward to ' + new)
        assert walk.probe.last['order'] == ['R27', 'S', 'R13'], 'STOP: the stock is not second after the return from it'
        # E5: previous and forward from that order.
        walk.move(console, 'previous', 'owner-previous-2')
        walk.restart(console, 'forward-27b')
    with walk.boot('back-13b', 'R13', 'restart with no choice') as (guest, console):
        walk.check(console, 'back-13b', confirmed='Return to ' + old)
        walk.move(console, 'forward', 'owner-forward-3')
        walk.restart(console, 'back-13b')
    with walk.boot('forward-27c', 'R27', 'restart with no choice') as (guest, console):
        walk.check(console, 'forward-27c', confirmed='Forward to ' + new)
        # The restart that lands elsewhere: previous, then the newer AresOS row in the boot menu.
        walk.move(console, 'previous', 'owner-previous-3')
        menu = walk.restart(console, 'forward-27c', take='R27')
    with walk.boot('menu-27', 'R27', 'the newer AresOS row taken in the boot menu', menu=menu) as (guest, console):
        # Both facts: the newer AresOS runs; the older one starts next, in place, not yet started.
        walk.check(console, 'menu-27', also=('Return to ' + old + ' is in place and has not started yet',))
        # forward works at once: applied, nothing waits, and no confirmation before a start.
        walk.move(console, 'forward', 'owner-forward-4', settled='applied')
        walk.restart(console, 'menu-27')
    with walk.boot('forward-27d', 'R27', 'restart with no choice') as (guest, console):
        walk.check(console, 'forward-27d', confirmed='Forward to ' + new)
        # E6: the boot menu without a record.
        menu = walk.restart(console, 'forward-27d', take='S')
    with walk.boot('menu-stock', 'S', 'the plain Bazzite row taken in the boot menu', menu=menu) as (guest, console):
        # Rule 8's neutral line, and no cause named.
        walk.check(console, 'menu-stock', never=('confirmed', 'in place', 'not finished', 'was not applied', 'interrupted'))
        walk.move(console, 'keep-stock', 'owner-keep-stock', settled='applied')
        walk.restart(console, 'menu-stock')
    with walk.boot('stock-2', 'S', 'restart with no choice') as (guest, console):
        walk.check(console, 'stock-2', confirmed='Change to ' + walk.reference['S'])
        walk.move(console, 'forward', 'owner-forward-5')
        walk.restart(console, 'stock-2')
    with walk.boot('forward-27e', 'R27', 'restart with no choice') as (guest, console):
        walk.check(console, 'forward-27e', confirmed='Forward to ' + new)
        walk.cut(console, 'cut-rollback')
    with walk.boot('cut-stock', 'S', 'a hard reset inside rollback, after its reorder and before its record') as (guest, console):
        # The check records the change from the list it finds and confirms it, with no second reorder.
        walk.check(console, 'cut-stock', confirmed='Rollback to ' + walk.reference['S'],
                   also=('The interrupted rollback to ' + walk.reference['S'] + ' had made its change; it is recorded now',))
        walk.quiet(guest, 'cut-stock-recorded', 'at check: the cut change recorded and confirmed')
        walk.move(console, 'forward', 'owner-forward-6')
        walk.restart(console, 'cut-stock')
    with walk.boot('final-27', 'R27', 'restart with no choice') as (guest, console):
        walk.check(console, 'final-27', confirmed='Forward to ' + new)
        public_typing(guest, 'final-27', 'de', console, foot=True)
        console.logout('final-27-logout')
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)
    probe = walk.probe
    typed = [row['command'] for row in walk.transcript]
    result = probe.result(commit=os.environ['GITHUB_SHA'], order='protected-second',
        starting_state="package 27's route: corrected pinned stock, release 13 by the laptop tools (15f), release 27 by tools version 2",
        laptop_tools=LAPTOP_TOOLS, tools_version_2=TOOLS_V2, tools_version_2_commit=TOOLS_V2_COMMIT, tools_version_3=media.fingerprint,
        tools_version_3_folder=walk.toolset, layout_proofs_read_from_that_folder=True,
        previous_release=old, release=new, names=walk.name, references=walk.reference, network_after_release_27=False,
        deployments={role: list(identity) for identity, role in probe.roles.items()},
        transcript=walk.transcript, typed={name: typed.count(COMMANDS[name]) for name in COMMANDS if name != 'install'},
        menus=walk.menus, stock_starts=walk.stock_starts, stock_updaters=walk.updater_states, cut=walk.cut_proof,
        ares_password_set_by_typing=True, ares_sudo_after_the_returns=True, ends_on='R27',
        owner_commands_physically_typed=True, protected_disk_audits=True, nvram_rule_unchanged=True, bootnext_audits=True)
    td.save('ways-back-rehearsal-result', result)
    assert result['status'] == 'passed' and probe.last['running'] == 'R27' and probe.last['order'][0] == 'R27'


def bound_sources(walk_sources, package='27', before='16'):
    """The binding tables of the rehearsal before this one (package 27's rebound package 16's, package
    22c's rebinds package 27's) with this checkout's bytes, plus this walk's own sources.

    A bound file that no longer exists has no bytes and is left out: package 22c took two scripts out
    of the owner payload, and the waiting list names them under `removed` until the record step.
    """
    def current(rows):
        return [dict(sha256=hashlib.sha256(pathlib.Path(row['path']).read_bytes()).hexdigest(), path=row['path'])
                for row in rows if pathlib.Path(row['path']).is_file()]
    previous = json.loads(pathlib.Path('os/manifest/ci/' + before + '/source-bindings.json').read_text())
    tables = [dict(name='package' + package + ' host walk', sources=current(walk_sources))]
    for table in previous['tables'][1:]:
        tables.append(dict(name=table['name'].replace('package' + before + ' rebind', 'package' + package + ' rebind'),
                           sources=current(table['sources'])))
    return dict(package=package, encoding='checkout bytes on the hosted runner (core.autocrlf=false; repository attributes)',
                commit=os.environ['GITHUB_SHA'], tables=tables)


def main():
    global PROBE_MEDIA
    mode, = sys.argv[1:]
    assert mode in ('probe', 'owner-tools', 'update', 'reorder-probe', 'ways-back')
    from owner_media import require_runner
    require_runner()
    package=os.environ['REHEARSAL_PACKAGE']
    assert package!='16' or mode=='probe', 'STOP: package16 permits only the owner-tools probe'
    assert (package=='27') == (mode=='update'), 'STOP: the update rehearsal is package 27 only'
    assert (package=='22c') == (mode in ('reorder-probe', 'ways-back')), 'STOP: the reorder probe and the ways-back rehearsal are package 22c only'
    authorization = json.loads(pathlib.Path('evidence/'+package+'-dispatch-authorization.json').read_text())
    assert authorization['allowance'] == package and authorization['native']['status'] == 'passed'
    assert authorization['native']['sha'] == os.environ['GITHUB_SHA']
    from owner_capabilities import CHECKS
    capabilities = json.loads(pathlib.Path('evidence/14-host-capabilities.json').read_text())
    assert capabilities['status'] == 'passed' and capabilities['sha'] == os.environ['GITHUB_SHA']
    assert all(capabilities['checks'].get(name) is True for name in CHECKS), 'STOP: host capabilities incomplete'
    if mode == 'owner-tools':
        # Package 27's update rehearsal proves its native step in its own run instead.
        assert authorization['probe']['status'] == 'passed' and authorization['probe']['commit'] == os.environ['GITHUB_SHA']
    walk_path={'16':'os/manifest/ci/16/host-walk.json','27':'os/manifest/ci/27/host-walk.json',
               '22c':'os/manifest/ci/22c/host-walk.json'}.get(package,'os/manifest/ci/14/host-walk/result.json')
    walk = json.loads(pathlib.Path(walk_path).read_text())
    assert walk['status'] == 'passed' and walk['stick_across_reboot'] is False
    assert isinstance(walk['sources'], list) and walk['sources']
    assert len({row['path'] for row in walk['sources']}) == len(walk['sources']), 'Duplicate host source'
    for row in walk['sources']:
        assert list(row) == ['sha256', 'path'], 'Host source must put hash before path'
        assert hashlib.sha256(pathlib.Path(row['path']).read_bytes()).hexdigest() == row['sha256'], 'Host walk is stale'
    td.EVIDENCE.mkdir(parents=True, exist_ok=True)
    if package == '27':
        # The checkout bytes this walk ran on, for source-bindings.json after a pass.
        td.save('27-bound-sources', bound_sources(walk['sources']))
    if mode == 'ways-back':
        # Package 22c's rehearsal rebinds package 27's tables (rebind.py rebind, after a pass).
        td.save('22c-bound-sources', bound_sources(walk['sources'], '22c', '27'))
    sw.WORK, sw.EVIDENCE = td.WORK, td.EVIDENCE
    td.Guest = sw.Guest = Guest
    Guest.order = 'protected-second'
    Guest.network_up = False
    for name in ('vmlinuz', 'initrd.img'):
        with (td.WORK / name).open('wb') as output:
            subprocess.run(['bsdtar', '-xOf', str(td.WORK / td.LIVE['filename']), 'images/pxeboot/' + name], stdout=output, check=True)
    media = Media()
    if mode in ('update', 'reorder-probe', 'ways-back'):
        media.create(source=laptop_payload(td.WORK / 'laptop-tools'))
    else:
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
        if mode == 'update':
            ares_password = ''.join(secrets.choice(ARES_LETTERS) for _ in range(24))
            print(f'::add-mask::{ares_password}', flush=True)
            try:
                update_rehearsal(audit, media, password, hashed, ares_password)
            finally:
                del ares_password
        elif mode == 'reorder-probe':
            reorder_probe(audit, media, password, hashed,
                          laptop_payload(td.WORK / 'tools-version-2', TOOLS_V2_COMMIT, TOOLS_V2))
        elif mode == 'ways-back':
            ares_password = ''.join(secrets.choice(ARES_LETTERS) for _ in range(24))
            print(f'::add-mask::{ares_password}', flush=True)
            try:
                ways_back_rehearsal(audit, media, password, hashed, ares_password,
                                    laptop_payload(td.WORK / 'tools-version-2', TOOLS_V2_COMMIT, TOOLS_V2))
            finally:
                del ares_password
        else:
            qualification(audit, media, password, hashed)
    finally:
        del password, hashed


if __name__ == '__main__':
    main()
