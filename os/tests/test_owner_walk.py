"""Zero-cost host walk. Real driver/control flow, synthetic command responses.

Retained 13f deployment/BLS states are observations, not evidence that package
14 ran in a VM. Every guest command is captured, never executed here.
"""
import contextlib
import copy
import hashlib
import json
import os
import pathlib
import shutil
import string
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_vm as vm
import owner_media
import test_owner_tools as common
from owner_fuse_shim import Volume
from guest_shell import syntax

FIXTURES = ROOT / 'os/tests/fixtures/owner-tools'


def retained(name):
    return json.loads((FIXTURES / (name + '-deployments.json')).read_text())


def walk():
    visits, commands, typed, checks, markers = [], [], [], [], []
    pinned, pair, staged, queued, rolled = (retained(n) for n in ('after-pin', 'aresos', 'after-switch-staged', 'after-rollback-queued', 'rollback'))
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
            self.screenshot_safe = True
            self.process = Mock(); self.process.poll.return_value = None
            self.monitor = Mock()
            self.boot_number = len(visits) + 1
            visits.append(stage)

        def command(self, name, source, **kw):
            syntax(name, source)
            commands.append((name, source))
            if name.endswith('-homebrew'): return 'f' * 64 + '  /home/linuxbrew/.linuxbrew/bin/brew\n'
            return ''

        def capture_json(self, name, source):
            syntax(name, source)
            commands.append((name, source))
            if name in ('offline-first-stock-link', 'stock-offline-login', 'live-offline-before-webui'):
                return dict(status='passed', physical_link_down=True)
            if name == 'owner-record-list': return []
            if name.endswith('-owner-result'):
                return dict(status='stopped' if 'refus' in name else 'passed', trace=[])
            if name == 'owner-prepared': return dict(stock=stock,state=dict(rpm=pinned['rpm'],bootc=pinned['bootc']))
            if name == 'owner-switch-pending': return staged['bootc']
            if name == 'owner-rollback-pending': return queued['bootc']
            if name.endswith('-loaded-keyboard'):
                profile = self.owner_layout
                props = dict(VConsoleKeymap=profile, X11Layout='de' if profile == 'de' else 'us', X11Variant='intl' if profile == 'us-intl' else '')
                return dict(localed=dict(data=[{k:dict(data=v) for k,v in props.items()}]),
                    loaded_map='keycode 21 = +' + ('z' if profile == 'de' else 'y') + '\nkeycode 44 = +' + ('y' if profile == 'de' else 'z') + '\n',
                    cmdline='quiet ostree=/ostree/fixture', bls={e['file']:e['content'] for e in (pinned if self.stage=='corrected-stock' else pair)['bls']})
            raise AssertionError('Unwalked response: ' + name)

        def keys(self, keys): pass
        def screenshot(self, stage): assert self.screenshot_safe
        def assert_offline(self, stage):
            vm.Guest.assert_offline(self, stage)
            checks.append(stage)
        def media_absent(self, stage):
            assert self.owner_media is None, 'Stick crossed a reboot'
            checks.append(stage + '-tools-absent')
        def finish_shutdown(self, stage, event):
            assert event == 'guest-reset'
            self.media_absent(stage)
            self.stopped_events_verified = True
        def poweroff(self, stage): self.media_absent(stage)
        def close(self, stage): pass

    class Media:
        fingerprint = '0' * 64
        def attach(self, guest, stage):
            assert guest.owner_signed_in and guest.owner_physical_signed_in
            guest.owner_media = self
            checks.append(stage + '-hotplug')
        def detach(self, guest, stage):
            assert guest.owner_media is self
            guest.owner_media = None
            checks.append(stage + '-detach')

    def snapshot(guest, stage):
        if stage == 'offline-first-stock': return first
        if stage == 'owner-switch-staged': return staged
        if stage == 'owner-rollback-queued': return queued
        if guest.stage.startswith(('tools-stock', 'corrected-stock')): return pinned
        if guest.stage in ('rollback-stock', 'default-stock'): return rolled
        return pair

    original = vm.type_text
    def collect(guest, text, layout=None):
        typed.append((text, layout or guest.owner_layout))
        original(guest, text, layout)

    with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary, contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(vm.Guest, 'network_up', False))
        for module in (vm.td, vm.sw):
            stack.enter_context(patch.object(module, 'EVIDENCE', pathlib.Path(temporary)))
        for name in ('install', 'restore_windows_order'):
            stack.enter_context(patch.object(vm.td, name))
        stack.enter_context(patch.object(vm.td, 'marker', side_effect=lambda audit,name,**kw: markers.append(name)))
        stack.enter_context(patch.object(vm.td, 'start_installed', side_effect=lambda p,h,s,**kw: Guest(s)))
        stack.enter_context(patch.object(vm.kb, 'deployment_snapshot', side_effect=snapshot))
        stack.enter_context(patch.object(vm.kb, 'capture_stock_greeter'))
        stack.enter_context(patch.object(vm, 'public_typing', side_effect=lambda *a,**kw: checks.append(a[1] + '-physical-observer')))
        stack.enter_context(patch.object(vm, 'type_text', side_effect=collect))
        stack.enter_context(patch.object(vm.time, 'sleep'))
        stack.enter_context(patch.dict(os.environ, GITHUB_ACTOR='synthetic-user', GH_TOKEN='synthetic_only_0123', GITHUB_SHA='a'*40))
        audit = Mock()
        vm.qualification(audit, Media(), 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH')
        result = json.loads((pathlib.Path(temporary) / 'owner-tools-result.json').read_text())
        assert result['status'] == 'passed'
        assert audit.check.call_count == 8
    assert visits == ['stock','tools-stock','corrected-stock','aresos','aresos-intl','aresos-back-de','rollback-stock','default-stock']
    assert {'prepared-unattended-windows','offline-roundtrip-unattended-windows','offline-roundtrip-detached-windows','final-unattended-windows','final-detached-windows'} <= set(markers)
    assert checks.index('tools-stock-hotplug') < checks.index('tools-stock-detach') < checks.index('tools-stock-reboot-tools-absent')
    return dict(stages=visits, commands=commands, typed=typed, checks=checks, markers=markers)


class OwnerWalkTest(unittest.TestCase):
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
        for fragment in ('layout-us-begin','layout-plain-us-rejected','layout-us-revert','layout-intl-proof',
                         'layout-back-de-proof','rollback-from-stock-refused','owner-keep-stock'):
            self.assertTrue(any(fragment in n for n in names), fragment)
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
        release=json.loads((ROOT/'os/manifest/release.json').read_text())['reference']
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


if __name__=='__main__': unittest.main()
