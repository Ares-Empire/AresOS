"""Package14: the owner route, physical commands, unchanged disk/firmware audits."""
import base64
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
from owner_keys import maps, physical_keys, at_keycodes
from owner_media import Media, bundle_module

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
        super().login()
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


class Console:
    def __init__(self, guest, tty='tty3'):
        self.guest, self.tty = guest, tty
        self.root = False
        self.completed_epoch = None
        self.pending_hidden = None
        self.last_hidden = None
        self.login_prepared = None

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
                    result=(self.login_prepared.rpc('echo') if self.login_prepared is not None
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
            token=expected == owner_hidden.owner_reader(['login']) and prompt.rstrip() == TOKEN_PROMPT)
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

    def send_hidden(self, value, layout=None, public_inputs=(), expect_rejection=False, chunk_token=False):
        pending = self.pending_hidden
        assert pending is not None, 'No hidden reader authority'
        assert not pending.get('sent'), 'Hidden input already attempted; no caller retry'
        assert getattr(self.guest, 'owner_input_epoch', 0) == pending['epoch'], 'Input revoked hidden reader authority'
        assert not expect_rejection or pending['expected']['kind'] == 'login'
        if public_inputs:
            assert pending['expected']['kind'] == 'sudo' and pending['expected']['next'] == owner_hidden.owner_reader(['layout','proof'])
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

    def login(self, password, stage, wrong=False):
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
        self.visible('ares-recovery\n',stage+'-username')
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

    def run(self, name, stage, inputs=(), password=None, expect_stop=False, token_chunks=False):
        owner_xhci.checkpoint(self.guest, stage + '-begin')
        self.select()
        self.prompt(stage + '-ready')
        before = self.records()
        self.visible(COMMANDS[name] + '\n',stage+'-command')
        args = COMMANDS[name].split('/at ', 1)[-1].split()
        hidden_input = password is not None
        if password is not None:
            assert all(not hidden for _, _, hidden in inputs), 'Unwalked hidden continuation after sudo'
            self.hidden(stage + '-sudo-hidden', owner_hidden.sudo_reader(['/var/lib/ares/at', *args], owner_hidden.owner_reader(args)), SUDO_PROMPT)
            self.guest.screenshot_safe = False
            self.send_hidden(password, public_inputs=inputs)
            inputs = ()
        for prompt, value, hidden in inputs:
            if hidden:
                hidden_input = True
                self.hidden(stage + '-hidden-input', owner_hidden.owner_reader(args), prompt.rstrip())
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
        command = COMMANDS[name].split('/at ', 1)[-1].split()[0] if name != 'install' else 'install'
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
        td.save(stage + '-command', dict(command=COMMANDS[name], physical=True, status=result['status'], profile=self.guest.owner_layout))
        if hidden_input and name=='login':
            assert self.last_hidden['key_comparison']['matches'], 'Guest keyboard counts differ; preserve diagnostics; never retype token'
        return result

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
        self.guest.command(stage + '-no-session', 'set -e; if pgrep -t ' + self.tty + ' -u 1000 -x bash; then exit 1; fi')


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
        private_login(console)
        console.run('verify', 'owner-signature')
        console.run('switch', 'owner-switch')
        sw.inspect_transaction(guest.capture_json('owner-switch-pending', sw.framed('bootc status --json')), release, stock['checksum'])
        kb.deployment_snapshot(guest, 'owner-switch-staged')
        console.run('title', 'owner-switch-title')
        console.run('reboot', 'owner-switch-reboot')
    finally:
        finish(guest, audit, 'corrected-stock')
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
