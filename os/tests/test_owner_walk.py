"""Zero-cost host walk. Real driver/control flow, synthetic command responses.

Retained 13f deployment/BLS states are observations, not evidence that package
14 ran in a VM. Every guest command is captured, never executed here.
"""
import contextlib
import base64
import copy
import hashlib
import json
import os
import pathlib
import re
import shutil
import shlex
import string
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_vm as vm
import owner_media
import test_owner_tools as common
from owner_fuse_shim import Volume
from guest_shell import syntax
from owner_console_shim import execute_idle, execute_hidden, execute_screen
from test_owner_hidden import vcsa

FIXTURES = ROOT / 'os/tests/fixtures/owner-tools'


def retained(name):
    return json.loads((FIXTURES / (name + '-deployments.json')).read_text())


UPDATE_STAGES = ['stock', 'tools-stock', 'corrected-stock', 'release-13', 'release-27', 'previous-13']
QUALIFICATION_STAGES = ['stock','tools-stock','corrected-stock','layout-reset-trial','layout-reset-recovery','aresos','aresos-intl','aresos-back-de','rollback-stock','default-stock']


def update_states(pair):
    """Package 22's three-deployment shapes, built from the retained release 13 pair."""
    old = next(d for d in pair['rpm']['deployments'] if d['booted'])
    stock = next(d for d in pair['rpm']['deployments'] if d['pinned'])
    reference = json.loads((ROOT / 'os/manifest/release.json').read_text())['reference']
    new = copy.deepcopy(old)
    new.update(checksum='c2' * 32, serial=0, **{'container-image-reference': 'ostree-unverified-registry:' + reference,
                                               'container-image-reference-digest': reference.split('@')[1]})
    def slot(row):
        return dict(ostree=dict(checksum=row['checksum'], deploySerial=row['serial'], stateroot=row['osname']),
            pinned=row['pinned'], image=dict(image=dict(image=row['container-image-reference'].split(':', 1)[1],
            transport='registry'), imageDigest=row['container-image-reference-digest']))
    def machine(*rows):
        rows = [copy.deepcopy(r) for r in rows]
        booted = next(i for i, r in enumerate(rows) if r['booted'])
        staged = [r for r in rows if r.get('staged')]
        others = [i for i, r in enumerate(rows) if not r.get('staged') and i != booted]
        bootc = copy.deepcopy(pair['bootc'])
        bootc['status'].update(booted=slot(rows[booted]), staged=slot(staged[0]) if staged else None,
            rollback=slot(rows[others[0]]), rollbackQueued=others[0] < booted)
        return dict(rpm=dict(copy.deepcopy(pair['rpm']), deployments=rows), bootc=bootc, bls=[])
    up = lambda row, **kw: dict(copy.deepcopy(row), **kw)
    return {'owner-update-staged': machine(up(new, booted=False, staged=True), up(old, booted=True), stock),
            'release-27': machine(up(new, booted=True), up(old, booted=False), stock),
            'owner-previous-queued': machine(up(old, booted=False), up(new, booted=True), stock),
            'previous-13': machine(up(old, booted=True), up(new, booted=False), stock)}


def walk(ps2=False, route='qualification'):
    assert route in ('qualification', 'update')
    visits, commands, typed, checks, markers = [], [], [], [], []
    visible_blocks = []
    physical_cases = []
    prompt_waits, idle_answers, hidden_reads = {}, [], []
    hidden_shapes, wait_shapes = [], []
    pinned, pair, staged, queued, rolled = (retained(n) for n in ('after-pin', 'aresos', 'after-switch-staged', 'after-rollback-queued', 'rollback'))
    updates = update_states(pair)
    old_reference = json.loads((ROOT / 'os/manifest/releases/13.json').read_text())['reference']
    new_reference = json.loads((ROOT / 'os/manifest/release.json').read_text())['reference']
    stock = copy.deepcopy(pinned['rpm']['deployments'][0])
    first = common.stock()
    first['bls'] = copy.deepcopy(pinned['bls'])
    class Guest:
        def __init__(self, stage):
            self.stage, self.owner_layout = stage, 'de'
            self.owner_signed_in = True
            self.owner_physical_signed_in = False
            self.owner_media = None
            self.mode = 'installed'
            self.idle_models, self.idle_shapes = {}, {}
            self.screenshot_safe = True
            self.secrets = []
            self.key_counts = None
            self.process = Mock(); self.process.poll.return_value = None
            self.monitor = SimpleNamespace(command=self.qmp)
            self.physical_case = None
            self.last_typing_frame = None
            self.last_visible_frame = None
            self.typing_case = None
            self.boot_number = len(visits) + 1
            self.events = []
            self.monitor = SimpleNamespace(command=self.qmp,events=self.events)
            if ps2:
                from test_owner_ps2 import context
                self.xhci_context=context(needed=stage=='tools-stock')
                self.xhci_context['stage']=stage
            visits.append(stage)

        def command(self, name, source, **kw):
            syntax(name, source)
            commands.append((name, source))
            if name.endswith('-prepare-input'):
                self.physical_case = name.removesuffix('-prepare-input')
            if name.endswith('-input-result'):
                self.physical_case = None
            if source.startswith('python3 -B /run/ares-login-'):
                from owner_login_shim import command
                return command(self,source)
            if name.endswith('-login-observers-prepare'):
                import ast,base64
                body=source.split("<<'ARES_LOGIN_PREPARE'\n",1)[1].split('\nARES_LOGIN_PREPARE',1)[0]
                tree=ast.parse(body)
                encoded,=[ast.literal_eval(n.args[0]) for n in ast.walk(tree) if isinstance(n,ast.Call)
                    and isinstance(n.func,ast.Attribute) and n.func.attr=='b64decode']
                compile(base64.b64decode(encoded),'prepared-observer-model','exec')
            if name.endswith('-homebrew'): return 'f' * 64 + '  /home/linuxbrew/.linuxbrew/bin/brew\n'
            if name.endswith('-policy'): return 'ARESOS_ACTIVE_SESSION_POLKIT_PASSED\nARESOS_GUEST_CHECKS_PASSED\n'
            return ''

        def capture_json(self, name, source):
            syntax(name, source)
            commands.append((name, source))
            if ps2 and name.endswith('-xhci-health'):
                import io,contextlib
                script=shlex.split(source)[shlex.split(source).index('python3')+2]
                output=io.StringIO()
                with contextlib.redirect_stdout(output):exec(script,{})
                result=json.loads(output.getvalue());assert not result['stop']
                checks.append(name)
                return result
            if '# hidden-key-counter' in source:
                if '-start' in name:
                    self.key_counts = dict(press=0,release=0,repeat=0,syn_dropped=0)
                    return dict(status='ready',path='/run/ares-input-fixture1',pid=77,device='/dev/input/event5',autorepeat=dict(delay_ms=250,period_ms=33),counts_only=True)
                result=dict(status='passed',counts_only=True,complete=True,keys_released=True,counts=dict(self.key_counts),
                    autorepeat=dict(delay_ms=250,period_ms=33),codes_recorded=False,values_recorded=False)
                if name.endswith('-stop'):self.key_counts=None
                return result
            if '# hidden-input-guard' in source:
                from test_owner_reliable_typing import execute_guard
                words=shlex.split(source);script=words[words.index('python3')+2]
                result=execute_guard(script)
                assert result['ready'], 'Modelled canonical reader refused'
                checks.append(name+'-canonical-blocked-reader')
                return result
            if '# visible-echo' in source:
                import ast
                words=shlex.split(source);script=words[words.index('python3')+2]
                value,=[ast.literal_eval(n.args[0]) for n in ast.walk(ast.parse(script)) if isinstance(n,ast.Call)
                    and isinstance(n.func,ast.Attribute) and n.func.attr=='endswith']
                result=execute_screen(script,vcsa('root# '+value))
                assert result['ready'];checks.append(name+'-cursor-echo-verified')
                return result
            if '# hidden-read-diagnostics' in source:
                from test_owner_read_diagnostics import execute_diagnostics
                words = shlex.split(source)
                return execute_diagnostics(words[words.index('python3') + 2])
            if '# hidden-phase:' in source:
                words = shlex.split(source)
                script = words[words.index('python3') + 2]
                phase = 'handoff' if '# hidden-phase: handoff' in script else 'left' if '# hidden-phase: left' in script else 'ready'
                rejected = phase == 'left' and 'layout-plain-us' in name
                result, rows, shape = execute_hidden(script, rejected=rejected, facts=True)
                assert (result.get('handoff_ready') and not result['ready']) if phase == 'handoff' else (result.get('rejected') and not result['ready']) if rejected else result['ready']
                tty, = re.findall(r"(?:hidden_observation|hidden_left|hidden_handoff)\('(?P<tty>tty[34])'", script)
                if phase == 'left':
                    self.idle_models[tty] = rows
                    self.idle_shapes[tty] = shape
                hidden_reads.append((name, phase))
                hidden_shapes.append(dict(boot=self.stage, tty=tty, stage=name, phase=phase, shape=shape, completion=result['ready'] if phase=='left' else None,
                    expected_rejection=rejected, completion_uses_echo=False if phase!='ready' else None))
                return result
            if 'ready=shell' in source:
                words = shlex.split(source)
                script = words[words.index('python3') + 2]
                # Execute the real read-only observer on the pinned sudo relay
                # model at every wait, not a pre-granted Boolean authority.
                tty, = re.findall(r"os.open\('/dev/(tty[34])'", script)
                value = execute_idle(script, (ROOT / 'os/tests/fixtures/owner-console/14zg-title-completed.vcsa').read_bytes(), rows=self.idle_models.get(tty))
                idle_answers.append(name)
                return value
            if 'base64.b64encode(data)' in source or 'base64.b64encode(raw)' in source:
                words=shlex.split(source);script=words[words.index('python3')+2]
                tty,=re.findall(r"pathlib.Path\('/dev/(vcsa[34])'",script)
                tty='tty'+tty[-1]
                predicate,=re.findall(r'^    if \((.*)\):$',script,re.M)
                if "'updated successfully' in full" in predicate or "'a password is required' in full" in predicate:
                    text=('passwd: all authentication tokens updated successfully.\nroot@bazzite:~#' if 'updated' in predicate
                          else 'sudo: a password is required\n[ares@bazzite ~]$')
                    raw=vcsa(text);kind='owner-output';shape='root-console-output'
                elif "bool(re.search(r'" in predicate:
                    wait=name.rsplit('-sample-',1)[0]
                    prompt_waits[wait]=prompt_waits.get(wait,0)+1
                    if ps2 and self.stage not in ('stock','tools-stock'):
                        from test_owner_records_prompt import retained_shape
                        clutter=retained_shape()
                    else:clutter=(ROOT/'os/tests/fixtures/owner-console/14zg-title-completed.vcsa').read_bytes()
                    raw=clutter if prompt_waits[wait]==1 else vcsa('ares-recovery@bazzite:~$')
                    kind='shell-prompt';shape=self.idle_shapes.get(tty,'sudo-i-readline')
                elif "line.endswith('login:')" in predicate:
                    raw=vcsa(('Login incorrect\n' if 'Login incorrect' in predicate else '')+'localhost login:')
                    kind='rejected-login' if 'Login incorrect' in predicate else 'getty-login-prompt';shape='getty-login-reader'
                elif predicate.startswith('line.endswith('):
                    import ast
                    prompt=ast.literal_eval(ast.parse(predicate,mode='eval').body.args[0])
                    assert prompt in ('Photographed Crucial serial:', 'Windows baseline Micron serial:', 'GitHub username:'), ('Uncovered public prompt',prompt)
                    raw=vcsa(prompt);kind='public-owner-input';shape='nested-owner-reader'
                else:
                    raise AssertionError('Uncovered cursor wait: '+name)
                result=execute_screen(script,raw)
                wait_shapes.append(dict(boot=self.stage,tty=tty,stage=name,kind=kind,shape=shape,predicate_executed=True))
                return result
            if name in ('offline-first-stock-link', 'stock-offline-login', 'live-offline-before-webui'):
                return dict(status='passed', physical_link_down=True)
            if name == 'owner-record-list': return []
            if name == 'update-tools-install-owner-result':
                return dict(status='passed', trace=[], manifest=media.fingerprint, previous_manifest=vm.LAPTOP_TOOLS,
                    previous_version=1, tools_version=2, releases=[dict(reference=old_reference), dict(reference=new_reference)])
            if name.endswith('-owner-result') and route == 'update':
                lines = {'owner-update-owner-result': ['Signed exact release staged ' + new_reference],
                         'release-27-title-owner-result': ['Update to ' + new_reference + ' confirmed after the restart'],
                         'owner-previous-owner-result': ['Previous AresOS queued for the next start ' + old_reference],
                         'previous-13-title-owner-result': ['Return to ' + old_reference + ' confirmed after the restart']}
                if name == 'previous-13-update-refused-owner-result':
                    return dict(status='stopped', trace=[], error='Target release is already deployed; get help')
                if 'refus' in name or '-dummy-' in name:
                    return dict(status='stopped', trace=[],
                        error='Private release read failed; check read:packages permission/expiry and network; no credential was written')
                return dict(status='passed', trace=[], result=lines.get(name, []))
            if name.endswith('-owner-result'):
                return dict(status='stopped' if 'refus' in name or '-dummy-' in name else 'passed', trace=[],
                    error='Private release read failed; check read:packages permission/expiry and network; no credential was written')
            if name.endswith('-path-result'):
                return dict(found=True, uid=1001, owner_uid=1001, path=vm.DAILY_PATH + ':/home/linuxbrew/.linuxbrew/bin')
            if name.endswith('-polkit'):
                reviewed = sorted(json.loads((ROOT / 'os/ci/polkit-review.json').read_text())['passwordless'])
                return dict(session_active='yes', session_remote='no', session_scope=True, actions=len(reviewed) + 2,
                            answers={'0': len(reviewed) - 1, '1': 1, '2': 2}, passwordless=reviewed[1:])
            if name.endswith('-rules'):
                return dict(ares_in_wheel=True, sudo_all_with_password=True, sudo_keeps_no_ticket=True, sudo_n_refused=True,
                    ares_password_set=True, chrome_started=True, chrome_stderr_tail='', chrome_version='Google Chrome 157.0.8103.50',
                    session_path=vm.SYSTEM_PATH, hub_terminal_argv=vm.HUB_TERMINAL,
                    aresos_shell=dict(browser=True, notepad=True, terminal=True), aresos_shell_executable=True)
            if name == 'owner-prepared': return dict(stock=stock,state=dict(rpm=pinned['rpm'],bootc=pinned['bootc']))
            if name == 'owner-switch-pending': return staged['bootc']
            if name == 'owner-rollback-pending': return queued['bootc']
            if name.endswith('-labwc-environment'):
                # XKB separates its base layout from its variant.
                layout, variant = {'de': ('de', ''), 'us': ('us', ''), 'us-intl': ('us', 'intl')}[self.owner_layout]
                return dict(XKB_DEFAULT_LAYOUT=layout, XKB_DEFAULT_VARIANT=variant)
            if name.endswith('-loaded-keyboard'):
                profile = 'de' if self.stage=='layout-reset-trial' and '-pending-' in name else self.owner_layout
                layout, variant = {'de': ('de', ''), 'us': ('us', ''), 'us-intl': ('us', 'intl')}[profile]
                props = dict(VConsoleKeymap=profile, X11Layout=layout, X11Variant=variant)
                return dict(localed=dict(data=[{k:dict(data=v) for k,v in props.items()}]),
                    console='KEYMAP='+profile, x11='X11='+profile,
                    loaded_map=json.loads((FIXTURES/('dumpkeys-'+self.owner_layout+'.json')).read_text()),
                    cmdline='quiet ostree=/ostree/fixture', bls={e['file']:e['content'] for e in (pinned if self.stage=='corrected-stock' else pair)['bls']})
            if name.endswith('-all-console-maps'):
                return {str(n):json.loads((FIXTURES/'dumpkeys-de.json').read_text()) for n in range(1,7)}
            raise AssertionError('Unwalked response: ' + name)

        def qmp(self, command, args=None):
            if command == 'system_reset':
                self.events.append(dict(event='SHUTDOWN',data=dict(guest=False,reason='host-qmp-system-reset')))
                checks.append(self.stage+'-QMP-system-reset')
            if command != 'send-key': return
            assert args['hold-time'] == 30
            assert all(k['type'] == 'qcode' for k in args['keys'])
            keys = [k['data'] for k in args['keys']]
            # Observe the real call, without replacing any typing helper.
            frame = sys._getframe(1)
            while frame is not None and frame.f_code is not vm.type_text.__code__:
                frame = frame.f_back
            if frame is not None:
                visible=frame
                while visible is not None and visible.f_code is not vm.Console.visible.__code__: visible=visible.f_back
                if visible is not None and visible is not self.last_visible_frame:
                    self.last_visible_frame=visible
                    visible_blocks.append((visible.f_locals['text'],self.owner_layout))
                if frame is not self.last_typing_frame:
                    self.last_typing_frame = frame
                    text, layout = frame.f_locals['text'], frame.f_locals['layout']
                    profile = self.owner_layout if layout is None else layout
                    typed.append((text, profile))
                    self.typing_case = None
                    if self.physical_case and text == vm.TEXT + '\n':
                        self.typing_case = dict(stage=self.physical_case, boot=self.stage, profile=profile,
                            text=text, key_events=[], hold_ms=30, minimum_gap_ms=120)
                        physical_cases.append(self.typing_case)
                if self.typing_case is not None:
                    self.typing_case['key_events'].append(list(keys))
            if self.key_counts is not None:
                # Synthetic EV_KEY stream; the real parser computes the aggregate.
                import struct,owner_key_counter
                data=b''.join(struct.pack('@llHHi',0,0,1,30,value) for key in keys for value in (1,0))
                owner_key_counter.count_events(data,self.key_counts)
        keys = vm.Guest.keys
        def resync_after_hidden(self, stage):
            checks.append(stage + '-serial-idle-resync')
            return dict(status='passed', prior_completion_observed=True,
                raw_output_retained=False, serial_input_flushed=True, physical_enter_sent=False)
        def screenshot(self, stage): assert self.screenshot_safe
        def assert_offline(self, stage):
            vm.Guest.assert_offline(self, stage)
            checks.append(stage)
        def media_absent(self, stage):
            assert self.owner_media is None, 'Stick crossed a reboot'
            checks.append(stage + '-tools-absent')
        def finish_shutdown(self, stage, event):
            assert event in ('guest-reset','host-qmp-system-reset')
            if event=='host-qmp-system-reset':
                assert self.events==[dict(event='SHUTDOWN',data=dict(guest=False,reason=event))]
                self.stopped_events=list(self.events)
            self.media_absent(stage)
            self.stopped_events_verified = True
        hard_reset=vm.Guest.hard_reset
        def poweroff(self, stage): self.media_absent(stage)
        def close(self, stage):
            self.last_typing_frame = None
            self.last_visible_frame = None

    class Media:
        fingerprint = vm.LAPTOP_TOOLS if route == 'update' else '0' * 64
        def replace(self, stage):
            assert self.fingerprint == vm.LAPTOP_TOOLS and guest_media[0] is None
            self.fingerprint = common.bundle.check(ROOT / 'os/owner-tools/payload')
            checks.append(stage + '-windows-copy')
        def attach(self, guest, stage):
            assert guest.owner_signed_in and guest.owner_physical_signed_in
            guest.owner_media = self
            guest_media[0] = self
            if ps2:vm.owner_xhci.checkpoint(guest,stage+'-model-after-hotplug',attached=True)
            checks.append(stage + '-hotplug')
        def detach(self, guest, stage):
            assert guest.owner_media is self
            guest.owner_media = None
            guest_media[0] = None
            if ps2:vm.owner_xhci.checkpoint(guest,stage+'-model-after-detach',attached=False,needed=False)
            checks.append(stage + '-detach')

    guest_media = [None]
    media = Media()

    def snapshot(guest, stage):
        if route == 'update' and stage in updates: return updates[stage]
        if route == 'update' and stage == 'previous-13-after-refusal': return updates['previous-13']
        if stage == 'offline-first-stock': return first
        if stage == 'owner-switch-staged': return staged
        if stage == 'owner-rollback-queued': return queued
        if guest.stage.startswith(('tools-stock', 'corrected-stock')): return pinned
        if guest.stage in ('rollback-stock', 'default-stock'): return rolled
        return pair

    with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary, contextlib.ExitStack() as stack:
        if ps2:
            import subprocess
            from test_owner_ps2 import kernel_result,journal
            original_run=subprocess.run
            def run(argv,*args,**kwargs):
                if argv[0]=='journalctl':return kernel_result(journal())
                return original_run(argv,*args,**kwargs)
            stack.enter_context(patch.object(subprocess,'run',side_effect=run))
        # The walk models guest time; deadline boundaries have dedicated tests.
        stack.enter_context(patch.object(vm.owner_login.time,'monotonic',return_value=10.0))
        save=vm.td.save
        def record(name,value):
            if re.search(r'-read-wait-[0-9]+$',name) and value.get('reader') and value.get('ready'):
                tty='tty'+str(value['reader']['physical']-1024)
                hidden_reads.append((name,'ready'))
                hidden_shapes.append(dict(boot='prepared-login',tty=tty,stage=name,phase='ready',
                    shape='getty-login-reader',completion=None,expected_rejection=False,completion_uses_echo=None))
            return save(name,value)
        stack.enter_context(patch.object(vm.td,'save',side_effect=record))
        stack.enter_context(patch.object(vm.Guest, 'network_up', False))
        for module in (vm.td, vm.sw):
            stack.enter_context(patch.object(module, 'EVIDENCE', pathlib.Path(temporary)))
        for name in ('install', 'restore_windows_order'):
            stack.enter_context(patch.object(vm.td, name))
        stack.enter_context(patch.object(vm.td, 'marker', side_effect=lambda audit,name,**kw: markers.append(name)))
        stack.enter_context(patch.object(vm.td, 'start_installed', side_effect=lambda p,h,s,**kw: Guest(s)))
        stack.enter_context(patch.object(vm.kb, 'deployment_snapshot', side_effect=snapshot))
        stack.enter_context(patch.object(vm.kb, 'capture_stock_greeter'))
        # public_typing/physical_input/type_text/physical_keys/Guest.keys are
        # unpatched. The QMP recorder above observes their actual key events.
        stack.enter_context(patch.object(vm.time, 'sleep'))
        stack.enter_context(patch.dict(os.environ, GITHUB_ACTOR='synthetic-user', GH_TOKEN='synthetic_only_0123', GITHUB_SHA='a'*40))
        audit = Mock()
        if route == 'update':
            vm.update_rehearsal(audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', 'abcdefghijklmnopqrstuvwx')
            result = json.loads((pathlib.Path(temporary) / 'update-rehearsal-result.json').read_text())
        else:
            # The retained switch fixtures are release 13's first switch.
            vm.qualification(audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', release=old_reference)
            result = json.loads((pathlib.Path(temporary) / 'owner-tools-result.json').read_text())
        assert result['status'] == 'passed'
        assert audit.check.call_count == len(UPDATE_STAGES if route == 'update' else QUALIFICATION_STAGES)
        events = [json.loads(p.read_text()) for p in pathlib.Path(temporary).glob('*-resync-1.json')]
        assert len(events) == len(prompt_waits) and all(n == 2 for n in prompt_waits.values())
        assert all(e['enter_sent'] and e['ready'] and e['observer']['ready'] and
                   e['observer']['observation']['foreground_chain'] for e in events)
        assert all(wait + '-idle-1' in idle_answers for wait in prompt_waits)
        # passwd's first value completes when the same reader asks again (-repeat).
        ready_names = [name for name, phase in hidden_reads if phase == 'ready' and not name.endswith('-repeat')]
        left_names = [name.removesuffix('-left') for name, phase in hidden_reads if phase == 'left']
        left_names += [name.removesuffix('-repeat') for name, phase in hidden_reads if phase == 'ready' and name.endswith('-repeat')]
        assert ready_names and len(set(ready_names)) == len(ready_names) and set(ready_names) == set(left_names)
    assert visits == (UPDATE_STAGES if route == 'update' else QUALIFICATION_STAGES)
    assert {'prepared-unattended-windows','offline-roundtrip-unattended-windows','offline-roundtrip-detached-windows','final-unattended-windows','final-detached-windows'} <= set(markers)
    assert checks.index('tools-stock-hotplug') < checks.index('tools-stock-detach') < checks.index('tools-stock-reboot-tools-absent')
    return dict(stages=visits, commands=commands, typed=typed, visible_blocks=visible_blocks, checks=checks, markers=markers,
        physical_cases=physical_cases,
        prompt_waits=sorted(prompt_waits), fresh_idle_answers=idle_answers, resyncs=events,
        hidden_reads=hidden_reads, hidden_shapes=hidden_shapes, wait_shapes=wait_shapes)


class OwnerWalkTest(unittest.TestCase):
    def test_real_typing_chain_emits_exact_keys_through_every_remaining_stage(self):
        result = walk(ps2=True)
        german = [['z'], ['y'], ['slash'], ['shift', '7'], ['shift', '1'], ['bracket_left'], ['ret']]
        international = [['y'], ['z'], ['minus'], ['slash'], ['shift', '1'], ['alt_r', 'y'], ['ret']]
        expected = {
            'corrected-stock-console': 'de', 'aresos-console': 'de', 'aresos-foot': 'de',
            'layout-reset-trial-console':'de','layout-reset-trial-foot':'de',
            'layout-reset-recovery-console':'de','layout-reset-recovery-foot':'de',
            'aresos-intl-console': 'us-intl', 'aresos-intl-foot': 'us-intl',
            'aresos-back-de-console': 'de', 'aresos-back-de-foot': 'de',
            'rollback-stock-console': 'de', 'default-stock-console': 'de',
        }
        self.assertEqual({row['stage']: row['profile'] for row in result['physical_cases']}, expected)
        self.assertEqual(len(result['physical_cases']), len(expected))
        for row in result['physical_cases']:
            self.assertEqual(row['text'], 'yz-/!ü\n')
            self.assertEqual(row['key_events'], international if row['profile'] == 'us-intl' else german)
            self.assertEqual((row['hold_ms'], row['minimum_gap_ms']), (30, 120))
        # These firmware-default marker boots have no typed text or layout.
        self.assertEqual(result['markers'][-2:], ['final-unattended-windows', 'final-detached-windows'])
        self.assertFalse(any(row['boot'].startswith('final-') for row in result['physical_cases']))

    def test_ps2_health_and_q15_clutter_walk_all_remaining_stages(self):
        result=walk(ps2=True)
        self.assertIn('final-unattended-windows',result['markers'])
        self.assertIn('final-detached-windows',result['markers'])
        names=[name for name,source in result['commands']]
        self.assertTrue(any(name.endswith('-xhci-health') for name in names))
        for stage in ('aresos','aresos-intl','aresos-back-de','rollback-stock','default-stock'):
            self.assertTrue(any(name.startswith(stage) and name.endswith('-xhci-health') for name in names),stage)

    def test_update_route_walks_the_laptop_tools_update_password_and_previous(self):
        commands = json.loads((ROOT / 'os/owner-tools/commands.json').read_text())
        for ps2 in (False, True):
            with self.subTest(ps2=ps2):
                result = walk(ps2=ps2, route='update')
                typed = [text for text, profile in result['visible_blocks']]
                # Steps 4 to 6 with the laptop's 15f bootstrap, step 8 with this guide's.
                self.assertEqual(sum(t.rstrip('\n') == vm.laptop_commands()['install'] for t in typed), 1)
                self.assertEqual(sum(t.rstrip('\n') == commands['install'] for t in typed), 1)
                self.assertNotEqual(vm.laptop_commands()['install'], commands['install'])
                for name in ('prepare', 'login', 'verify', 'switch', 'update', 'previous', 'check', 'title', 'records', 'export', 'reboot'):
                    self.assertIn(commands[name] + '\n', typed, name)
                order = [typed.index(commands['install'] + '\n'), typed.index(commands['update'] + '\n'),
                         typed.index('sudo passwd ares\n'), typed.index('sudo -v\n'), typed.index(commands['previous'] + '\n')]
                self.assertEqual(order, sorted(order))
                self.assertIn('ares\n', typed)
                self.assertIn('sudo -n true\n', typed)
                self.assertIn('sudo-passwd-reader', {s['shape'] for s in result['hidden_shapes']})
                # polkit is asked while his desktop is in front: after the terminal PATH
                # probe (which leaves tty1 active) and guest.sh, before the console returns.
                names = [name for name, source in result['commands']]
                self.assertEqual(names.count('release-27-polkit'), 1)
                self.assertLess(names.index('release-27-path-result'), names.index('release-27-policy'))
                self.assertLess(names.index('release-27-policy'), names.index('release-27-polkit'))
                self.assertLess(names.index('release-27-polkit'), names.index('release-27-rules'))
                checks = result['checks']
                self.assertLess(checks.index('update-windows-copy-windows-copy'), checks.index('update-tools-hotplug'))
                self.assertLess(checks.index('update-tools-hotplug'), checks.index('update-tools-detach'))
                self.assertIn('owner-update-reboot-tools-absent', checks)
                self.assertEqual(result['markers'][-2:], ['final-unattended-windows', 'final-detached-windows'])

    def test_live_offline_command_is_composed_and_checked(self):
        guest = object.__new__(vm.Guest)
        checked = []
        def capture(name, source):
            syntax(name, source)
            checked.append(source)
            return dict(physical_link_down=True)
        guest.capture_json = capture
        guest.assert_offline('live-offline-before-webui')
        self.assertEqual(len(checked), 1)
        self.assertIn("\nPY\n} >", checked[0])

    def test_real_guest_boot_and_marker_shutdown_adapters_preserve_parent_api(self):
        monitor=Mock()
        def initialize(guest,*args,**kw):guest.monitor=monitor;guest.boot_number=1
        with patch.object(vm.td.Guest,'__init__',initialize),patch.object(vm.td,'save'),patch.object(vm.Guest,'network_up',False):
            guest=vm.Guest('SYNTHETIC-DISK','SYNTHETIC-PASSWORD',[])
        self.assertEqual(monitor.command.call_args_list[0].args,('set_link',{'name':'owner-net','up':False}))
        self.assertEqual(monitor.command.call_args_list[1].args,('cont',))
        guest.media_absent=Mock()
        with patch.object(vm.td.Guest,'finish_shutdown',return_value='stopped') as finish:
            self.assertEqual(guest.finish_shutdown('marker','guest-shutdown',timeout=30),'stopped')
            finish.assert_called_once_with('marker','guest-shutdown',timeout=30)
        guest.media_absent.assert_called_once_with('marker')
        with patch.object(vm.td.Guest,'boot_args',return_value=['EXISTING']):
            self.assertEqual(guest.boot_args(),['EXISTING','-S'])
        guest.mode='marker-windows'
        self.assertNotIn('usb-storage',' '.join(guest.peripheral_args()))
        self.assertNotIn('fsdev',' '.join(guest.peripheral_args()))
        self.assertNotIn('hostfwd',guest.network_args())

    def test_file_image_creation_windows_copy_and_export_inspection_host_paths(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory, contextlib.ExitStack() as stack:
            root=pathlib.Path(directory).resolve()
            evidence=root/'evidence';evidence.mkdir()
            stack.enter_context(patch.object(owner_media.td,'WORK',root))
            stack.enter_context(patch.object(owner_media.td,'EVIDENCE',evidence))
            stack.enter_context(patch.dict(os.environ,GITHUB_ACTIONS='true',GITHUB_REPOSITORY='Ares-Empire/AresOS',
                GITHUB_REF_NAME='pkg/14-owner-tools',REHEARSAL_PACKAGE='14'))
            media=owner_media.Media()
            fake=Volume(root,media.mount)
            volume=fake.volume;calls=fake.calls
            stack.enter_context(patch.object(owner_media.subprocess,'run',side_effect=fake.run))
            stack.enter_context(patch.object(owner_media.subprocess,'check_output',side_effect=fake.output))
            fake.patch_nodes(stack)
            verify=stack.enter_context(patch.object(owner_media,'verify_loop',wraps=owner_media.verify_loop))
            media.create()
            self.assertEqual(media.path.stat().st_size,128*1024**2)
            self.assertEqual(media.fingerprint,common.bundle.check(volume/'ares-tools'))
            records=volume/'ares-records';records.mkdir();(records/'diagnostic.json').write_text('{"synthetic":true}')
            media.verify('standin')
            self.assertEqual((evidence/'owner-records/diagnostic.json').read_bytes(),(records/'diagnostic.json').read_bytes())
            self.assertEqual(verify.call_count,3)
            self.assertTrue(any(c[0]=='mount.exfat-fuse' and 'ro,nodev,nosuid,noexec' in c for c in calls))
            self.assertFalse(media.attached)

    def test_all_remaining_host_paths_and_all_typed_characters(self):
        with patch(__name__ + '.syntax', wraps=syntax) as checked:
            result = walk()
        self.assertEqual(checked.call_count, len(result['commands']))
        names = {name for name, source in result['commands']}
        self.assertTrue(result['prompt_waits'])
        for fragment in ('export', 'corrected-stock', 'login', 'signature', 'switch', 'aresos',
                         'layout-us-begin', 'layout-intl-proof', 'layout-us-revert',
                         'layout-intl-finish', 'rollback', 'keep-stock'):
            self.assertTrue(any(fragment in n for n in result['prompt_waits']), fragment)
        for fragment in ('layout-us-begin','layout-plain-us-rejected','layout-us-revert','layout-intl-proof',
                         'layout-back-de-proof','rollback-from-stock-refused','owner-keep-stock'):
            self.assertTrue(any(fragment in n for n in names), fragment)
        self.assertEqual({s['shape'] for s in result['hidden_shapes']}, {'getty-login-reader',
            'persistent-login-readline','sudo-password-reader','sudo-i-readline',
            'nested-owner-getpass','sudo-owner-public-handoff','login-rejected'})
        left=[s for s in result['hidden_shapes'] if s['phase']=='left']
        self.assertEqual(len(left),27)
        self.assertEqual(sum(s['expected_rejection'] and not s['completion'] for s in left),1)
        self.assertTrue(all(not s['completion_uses_echo'] for s in left))
        self.assertEqual(sum(s['phase']=='handoff' for s in result['hidden_shapes']),3)
        self.assertEqual({s['boot'] for s in left},set(result['stages'])-{'stock'})
        self.assertTrue(all(s['predicate_executed'] for s in result['wait_shapes']))
        for text, profile in result['typed']:
            # Deliberately wrong positions in the plain-US failure use de.
            for char in text: vm.physical_keys(char, profile)
        for profile in ('de','us-intl'):
            for char in string.ascii_letters + string.digits + '_-\n': vm.physical_keys(char, profile)
        with self.assertRaises(AssertionError): vm.physical_keys('☃', 'de')
        with self.assertRaises(AssertionError): vm.physical_keys('ü', 'us')

    def test_retained_full_states_agree_and_keep_saved_serial(self):
        index=json.loads((FIXTURES/'sources.json').read_text())
        saved=retained('after-pin')
        stock=saved['rpm']['deployments'][0]
        prepared=dict(stock_identity=list(common.owner.key(stock)), stock=stock, state=dict(rpm=saved['rpm'],bootc=saved['bootc']))
        # The retained 13f states are release 13's.
        release=json.loads((ROOT/'os/manifest/releases/13.json').read_text())['reference']
        for row in index['files']:
            self.assertEqual(hashlib.sha256((FIXTURES/row['file']).read_bytes()).hexdigest(),row['sha256'])
            state=json.loads((FIXTURES/row['file']).read_text())
            common.owner.qualified_state(dict(rpm=state['rpm'], bootc=state['bootc']), prepared, release)

    def test_qmp_hotplug_identity_removal_and_bad_hash_refuse_before_qmp(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary:
            media=object.__new__(owner_media.Media)
            media.path=pathlib.Path(temporary)/'stick.raw';media.path.write_bytes(b'SYNTHETIC-IMAGE')
            media.expected=owner_media.digest(media.path);media.attached=False;media.fingerprint='f'*64
            class Monitor:
                events=[]
                def __init__(self): self.calls=[]
                def command(self, command, args=None):
                    self.calls.append((command,args))
                    if command=='query-block':return [dict(inserted={'node-name':'owner-tools','file':str(media.path)})]
                    if command=='device_del': self.events.append(dict(event='DEVICE_DELETED',data=dict(device='owner-tools-usb')))
            guest=Mock(mode='installed',owner_signed_in=True,owner_physical_signed_in=True,boot_number=1)
            guest.monitor=Monitor();guest.capture_json.return_value=dict(label='ARESTOOLS')
            with patch.object(owner_media.td,'save'),patch.object(media,'verify'),patch.object(owner_media.time,'sleep'):
                media.attach(guest,'fixture');media.detach(guest,'fixture')
                self.assertFalse(media.attached)
                self.assertEqual([c for c,a in guest.monitor.calls],['blockdev-add','blockdev-add','device_add','query-block','device_del','blockdev-del','blockdev-del'])
                offset=len(guest.monitor.calls);media.path.write_bytes(b'ALTERED')
                with self.assertRaises(AssertionError):media.attach(guest,'bad')
                self.assertEqual(len(guest.monitor.calls),offset)

    def test_only_the_exact_untouched_old_entry_is_temporarily_exempt(self):
        from keyboard_entries import entry_identity
        state=retained('after-pin')
        bls=[dict(identity=list(entry_identity(e['deployment'])),content=e['content']) for e in state['bls']]
        stock=state['rpm']['deployments'][0]
        prepared=dict(stock_identity=list(common.owner.key(stock)),stock=stock,before_bls=copy.deepcopy(bls),
                      state=dict(rpm=state['rpm'],bootc=state['bootc']))
        checked=common.owner.keyboard_entries(prepared['state'],prepared,bls)
        self.assertEqual([e['identity'] for e in checked],[prepared['stock_identity']])
        old=next(e for e in bls if e['identity']!=prepared['stock_identity'])
        old['content']+='\noptions evil=changed\n'
        with self.assertRaises(common.owner.Stop):common.owner.keyboard_entries(prepared['state'],prepared,bls)


class TerminalPathTest(unittest.TestCase):
    """Rehearsal run 5 (43120759117) typed the PATH probe right after Ctrl+Alt+F1 and it never ran."""
    PATH = vm.DAILY_PATH + ':/home/linuxbrew/.linuxbrew/bin'

    def run_path(self, answers):
        events, saved = [], {}

        class Guest:
            owner_layout = 'de'
            def keys(self, names): events.append(('keys', tuple(names)))
            def command(self, name, source, **kw):
                syntax(name, source); events.append(('command', name, source)); return ''
            def capture_json(self, name, source):
                syntax(name, source); events.append(('capture', name, source))
                answer = answers.pop(0)
                if isinstance(answer, BaseException): raise answer
                return answer
            def screenshot(self, name): events.append(('screenshot', name))
        real_sleep = vm.time.sleep

        def sleep(seconds):
            # time.sleep is the time module's. Only terminal_path's own sleep belongs to the order;
            # subprocess waits (the guest syntax check's bash -n, other tests' threads) keep the
            # real one. On rehearsal run 8's runner and under load such waits slept 1 ms here.
            if sys._getframe(1).f_code is vm.terminal_path.__code__:
                events.append(('sleep', seconds))
            else:
                real_sleep(seconds)
        with patch.object(vm.time, 'sleep', new=sleep), \
                patch.object(vm.td, 'save', side_effect=lambda name, value: saved.__setitem__(name, value)):
            try: result = vm.terminal_path(Guest(), 'release-27')
            except AssertionError as error: result = error
        return events, saved, result

    def typed(self, events):
        """The text typed in foot, read back from its physical German keys."""
        german = {tuple(vm.physical_keys(c, 'de')): c for c in set('python3 /run/aresos-path.py\n')}
        return ''.join(german[e[1]] for e in events if e[0] == 'keys' and e[1] not in (('ctrl', 'alt', 'f1'), ('ctrl', 'u')))

    def test_types_only_after_switch_foot_round_trip_active_session_and_settle(self):
        events, saved, result = self.run_path([dict(found=True, uid=1001, owner_uid=1001, path=self.PATH)])
        self.assertNotIsInstance(result, AssertionError)
        steps = [e[:2] for e in events if e[0] != 'keys']
        first_key = next(i for i, e in enumerate(events) if e[0] == 'keys' and e[1] != ('ctrl', 'alt', 'f1'))
        self.assertEqual(events[0], ('keys', ('ctrl', 'alt', 'f1')))
        self.assertEqual([e[:2] for e in events[1:first_key]],
                         [('command', 'release-27-path-foot'), ('command', 'release-27-path-prepare'),
                          ('command', 'release-27-path-session'), ('sleep', 1)])
        self.assertEqual(steps[-2:], [('capture', 'release-27-path-result'), ('screenshot', 'release-27-path')])
        self.assertEqual(self.typed(events), 'python3 /run/aresos-path.py\n')
        session = dict((e[1], e[2]) for e in events if e[0] == 'command')['release-27-path-session']
        self.assertEqual(session, vm.ACTIVE_DESKTOP)
        for needle in ('$3 == "ares" && $4 == "seat0"', '-p Active --value)" = yes', '-p State --value)" = active'):
            self.assertIn(needle, session)
        self.assertFalse(saved['release-27-terminal-path']['retried'])
        self.assertNotIn(('screenshot', 'release-27-path-miss'), [e[:2] for e in events])

    def test_one_miss_is_retried_once_after_a_screenshot_and_line_clear(self):
        events, saved, result = self.run_path([dict(found=False),
                                               dict(found=True, uid=1001, owner_uid=1001, path=self.PATH)])
        self.assertNotIsInstance(result, AssertionError)
        names = [e[:2] for e in events if e[0] != 'keys' or e[1] == ('ctrl', 'u')]
        miss = names.index(('capture', 'release-27-path-result'))
        self.assertEqual(names[miss + 1:], [('screenshot', 'release-27-path-miss'), ('keys', ('ctrl', 'u')),
                                            ('capture', 'release-27-path-retry-result'), ('screenshot', 'release-27-path')])
        self.assertEqual(self.typed(events), 'python3 /run/aresos-path.py\n' * 2)
        self.assertTrue(saved['release-27-terminal-path']['retried'])
        sources = {e[1]: e[2] for e in events if e[0] == 'capture'}
        self.assertIn('range(20)', sources['release-27-path-result'])
        self.assertNotIn('SystemExit', sources['release-27-path-result'])
        self.assertIn('range(60)', sources['release-27-path-retry-result'])
        self.assertIn("raise SystemExit('No terminal PATH probe')", sources['release-27-path-retry-result'])

    def test_a_second_miss_stops_without_a_third_attempt(self):
        failed = AssertionError('Guest command failed: release-27-path-retry-result, exit 1')
        events, saved, result = self.run_path([dict(found=False), failed])
        self.assertIs(result, failed)
        self.assertEqual(self.typed(events), 'python3 /run/aresos-path.py\n' * 2)
        self.assertNotIn('release-27-terminal-path', saved)
        self.assertNotIn(('screenshot', 'release-27-path'), [e[:2] for e in events])

    def test_the_guest_probe_reports_a_first_miss_and_reads_a_hit(self):
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            target = str(pathlib.Path(folder) / 'probe')
            def program(required):
                source = vm.path_probe(target, 1, required)
                return source.split("python3 - <<'PY'\n", 1)[1].split('\nPY', 1)[0]
            miss = subprocess.run([sys.executable, '-c', program(False)], capture_output=True, text=True)
            self.assertEqual((miss.returncode, json.loads(miss.stdout)), (0, dict(found=False)))
            stop = subprocess.run([sys.executable, '-c', program(True)], capture_output=True, text=True)
            self.assertNotEqual(stop.returncode, 0)
            self.assertIn('No terminal PATH probe', stop.stderr)
            pathlib.Path(target).write_text(json.dumps(dict(uid=1001, path=self.PATH)))
            hit = subprocess.run([sys.executable, '-c', program(False)], capture_output=True, text=True)
            value = json.loads(hit.stdout)
            self.assertEqual((value['found'], value['uid'], value['path']), (True, 1001, self.PATH))
            self.assertEqual(value['owner_uid'], os.stat(target).st_uid)


if __name__=='__main__': unittest.main()
