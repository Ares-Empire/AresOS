"""Host control-flow walk; retained 13e prefix, explicitly synthetic future guests.

No command returned by this stand-in is executed. This is not VM evidence.
The real main/tty/foot/input/transaction/entry assertions run without QEMU.
"""
import contextlib
import copy
import io
import json
import os
import pathlib
import shutil
import string
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'os/ci'))
import keyboard_vm as vm
import keyboard_entries as ke
import greeter

RETAINED = ROOT/'os/manifest/ci/13/qualification-2/evidence/two-disk'
STAGES = ('corrected-stock', 'aresos', 'aresos-us', 'aresos-back-de', 'rollback')


def retained(name):
    return json.loads((RETAINED/(name+'.json')).read_text())


def derived_snapshots():
    """Use real stock identities; future checksum is deliberately synthetic."""
    pinned = retained('after-pin-deployments')
    stock = copy.deepcopy(pinned['rpm']['deployments'][0])
    release = json.loads((ROOT/'os/manifest/release.json').read_text())['reference']
    image = dict(stock, checksum='b'*64, serial=0, pinned=False, booted=True,
                 **{'container-image-reference-digest': release.split('@')[1]})
    stock['booted'] = False
    pair = copy.deepcopy(pinned)
    pair['rpm']['deployments'] = [image, stock]
    pair['bls'] = []
    for d in (image, stock):
        pair['bls'].append(dict(file='/boot/loader/entries/synthetic-'+d['checksum']+'.conf',
            deployment='/sysroot/ostree/deploy/'+d['osname']+'/deploy/'+d['checksum']+'.'+str(d['serial']),
            content='title SOURCE-DERIVED FIXTURE\noptions rw ostree=/ostree/synthetic console=tty0\n'))
    status = pair['bootc']['status']
    slot = copy.deepcopy(status['booted'])
    status.update(staged=None, rollbackQueued=False)
    for name, d in (('booted', image), ('rollback', stock)):
        status[name] = copy.deepcopy(slot)
        status[name]['ostree'].update(checksum=d['checksum'], deploySerial=d['serial'], stateroot=d['osname'])
        status[name]['pinned'] = d['pinned']
    status['booted']['image']['image']['image'] = release
    status['booted']['image']['imageDigest'] = release.split('@')[1]
    staged = copy.deepcopy(pinned)
    new = dict(image, staged=True, booted=False)
    staged['rpm']['deployments'].insert(0, new)
    staged['bootc']['status']['staged'] = copy.deepcopy(status['booted'])
    queued = copy.deepcopy(pair)
    queued['bootc']['status']['rollbackQueued'] = True
    rolled = copy.deepcopy(pair)
    rolled['rpm']['deployments'].reverse()
    for d in rolled['rpm']['deployments']:
        d['booted'] = ke.key(d) == ke.key(stock)
    rolled['bootc']['status']['booted'], rolled['bootc']['status']['rollback'] = (
        rolled['bootc']['status']['rollback'], rolled['bootc']['status']['booted'])
    return pinned, pair, staged, queued, rolled


def walk(render_frame=False, mutation=None):
    typed, commands, qcodes, screenshots, visits = [], [], [], [], []
    pinned, pair, staged, queued, rolled = derived_snapshots()
    if mutation:
        mutation(pair)
    sha = 'a'*40
    authorization = dict(allowance='13', native=dict(status='passed', sha=sha),
                         probe=dict(status='passed', commit=sha))
    original_read = pathlib.Path.read_text
    original_type = vm.type_text

    def read(path, *args, **kwargs):
        if path.as_posix() == 'evidence/13-dispatch-authorization.json':
            return json.dumps(authorization)
        return original_read(path, *args, **kwargs)

    def collect(guest, text, layout):
        typed.append((text, layout))
        original_type(guest, text, layout)

    class Guest:
        def __init__(self, stage):
            self.stage = stage
            self.process = Mock(); self.process.poll.return_value = None
            self.screenshot_safe = True
            visits.append(stage)

        def keys(self, keys):
            qcodes.append(keys)

        def command(self, name, command, **kwargs):
            commands.append((name, command))
            if name.startswith('repair-'):
                return 'ARESOS_SYSTEM_KEYBOARD_RESULT '+json.dumps(retained(name))+'\n'
            if name == 'stock-pin':
                return 'ARESOS_STOCK_PIN_RESULT '+json.dumps(retained('stock-pin-result'))+'\n'
            if name.endswith('-homebrew'):
                return 'f'*64+'  /home/linuxbrew/.linuxbrew/bin/brew\n'
            return ''

        def capture_json(self, name, command):
            commands.append((name, command))
            if name.endswith('-labwc-environment'):
                value = dict(XKB_DEFAULT_LAYOUT='us' if self.stage == 'aresos-us' else 'de')
            elif name.endswith('-keyboard'):
                value = retained('corrected-stock-keyboard')
                if self.stage != 'corrected-stock':
                    layout = 'us' if self.stage == 'aresos-us' else 'de'
                    value['console'] = 'KEYMAP='+layout+'\n'
                    value['localed']['data'][0]['X11Layout']['data'] = layout
                    value['loaded_map'] = 'keycode 21 = +'+('y' if layout=='us' else 'z')+'\nkeycode 44 = +'+('z' if layout=='us' else 'y')+'\n'
                    value['bls'] = {e['file']: e['content'] for e in pair['bls']}
            elif name in ('pending-switch', 'pending-rollback'):
                value = (staged if name=='pending-switch' else queued)['bootc']
            elif name.endswith('-status') and not name.endswith(('-rpm-ostree-status', '-bootc-status')):
                value = (pinned if self.stage=='corrected-stock' else rolled if self.stage=='rollback' else pair)['bootc']
            else:
                field, suffix = next((f, s) for f, s in (('rpm','-rpm-ostree-status'),('bootc','-bootc-status'),('bls','-resolved-bls')) if name.endswith(s))
                stage = name[:-len(suffix)]
                if stage.startswith(('first-stock-', 'repair-', 'after-pin')):
                    value = retained(stage+'-deployments')[field]
                else:
                    snapshot = (staged if stage=='after-switch-staged' else queued if stage=='after-rollback-queued'
                                else pinned if stage.startswith('corrected-stock') else rolled if stage=='rollback' else pair)
                    value = snapshot[field]
            value = copy.deepcopy(value)
            vm.td.save(name, value)
            return value

        def screenshot(self, name):
            assert self.screenshot_safe
            screenshots.append(name)
            if name == 'rollback-greeter':
                shutil.copyfile(ROOT/'reviews/06-image-release/screenshots/06c-full-2-stock-bazzite.png', vm.td.EVIDENCE/(name+'.png'))

        def poweroff(self, stage):
            commands.append((stage+'-poweroff', 'STAND-IN ONLY'))

        def close(self, stage):
            pass

    def capture(guest, evidence, name):
        if render_frame:
            greeter.capture_stock_greeter(guest, evidence, name, sleep=lambda _: None)
        else:
            # Still run the real readiness, capture loop and threshold logic;
            # Pillow pixels are separately exercised on the retained real PNG.
            with patch.object(greeter, 'frame_metrics', return_value=dict(nonblack_fraction=.8, bright_fraction=.1, spread=30)):
                greeter.capture_stock_greeter(guest, evidence, name, sleep=lambda _: None)

    with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory, contextlib.ExitStack() as stack:
        work = pathlib.Path(directory); evidence = work/'evidence'; evidence.mkdir()
        (work/'vars.fd').write_bytes(b'SYNTHETIC FIRMWARE STAND-IN')
        for module in (vm.td, vm.sw):
            stack.enter_context(patch.object(module, 'WORK', work))
            stack.enter_context(patch.object(module, 'EVIDENCE', evidence))
        stack.enter_context(patch.object(vm.td, 'Guest', Guest))
        # main assigns sw.Guest too; restore it so later transport tests use
        # the real class rather than this stand-in.
        stack.enter_context(patch.object(vm.sw, 'Guest', vm.sw.Guest))
        for name in ('marker', 'install', 'restore_windows_order', 'installed_keyboard'):
            stack.enter_context(patch.object(vm.td, name))
        audit = stack.enter_context(patch.object(vm.td, 'Audit')).return_value
        stack.enter_context(patch.object(vm.td, 'start_installed', side_effect=lambda p,h,stage,**kw: Guest(stage)))
        stack.enter_context(patch.object(pathlib.Path, 'read_text', read))
        # Only main's two ISO extractions call subprocess.run; no shell allowed.
        def extract(args, **kwargs):
            assert args[:2] == ['bsdtar', '-xOf'] and args[-1] in ('images/pxeboot/vmlinuz','images/pxeboot/initrd.img')
        stack.enter_context(patch.object(vm.subprocess, 'run', side_effect=extract))
        stack.enter_context(patch.dict(sys.modules, crypt=types.SimpleNamespace(METHOD_SHA512=object(), mksalt=lambda _: 'synthetic', crypt=lambda p,s: 'synthetic-hash')))
        stack.enter_context(patch.object(vm.secrets, 'token_hex', return_value='0123456789abcdef'*2+'01234567'))
        stack.enter_context(patch.object(vm.time, 'sleep'))
        stack.enter_context(patch.object(vm, 'type_text', side_effect=collect))
        stack.enter_context(patch.object(vm, 'capture_stock_greeter', side_effect=capture))
        stack.enter_context(patch.dict(os.environ, GITHUB_SHA=sha))
        stack.enter_context(patch.object(sys, 'argv', ['keyboard_vm.py','keyboard']))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        vm.main()
        result = json.loads((evidence/'keyboard-result.json').read_text())
        assert result['status']=='passed' and result['temporary_old_stock_removed_by_finalization']
        assert visits == ['stock', *STAGES]
        assert audit.check.call_count == 6
        for stage in STAGES:
            assert json.loads((evidence/(stage+'-tty-physical.json')).read_text())['uid'] == 1000
        for stage in STAGES[1:4]:
            assert json.loads((evidence/(stage+'-foot-physical.json')).read_text())['uid'] == 1001
    # Include all possible generated password characters, not just one draw.
    strings = [text for text, layout in typed] + ['yz-/!'+string.hexdigits[:16]+'\n']
    strings += [command for name, command in commands if name.endswith('-change-layout')]
    return dict(strings=strings, typed=typed, commands=commands, screenshots=screenshots, qcodes=qcodes, stages=visits)


class KeyboardWalkTest(unittest.TestCase):
    def test_entire_unreached_host_path_and_every_typed_string_on_both_layouts(self):
        result = walk()
        for text in result['strings']:
            for layout in ('de','us'):
                for char in text:
                    with self.subTest(text=text, layout=layout, char=char):
                        self.assertTrue(vm.physical_keys(char, layout))
        names = {name for name, command in result['commands']}
        self.assertTrue({'verify-release','switch','rollback','rollback-session','rollback-greeter-ready',
                         'aresos-change-layout','aresos-us-change-layout','pending-switch','pending-rollback'} <= names)
        self.assertEqual(len(result['typed']), 5*7 + 3*2)
        self.assertIn('rollback-greeter', result['screenshots'])

    def test_walk_stops_if_the_old_stock_survives_finalization(self):
        def old(pair):
            original=retained('after-pin-deployments')
            pair['rpm']['deployments'].append(original['rpm']['deployments'][1])
            pair['bls'].append(original['bls'][1])
        with self.assertRaisesRegex(AssertionError, 'unexpected final deployment list'):
            walk(mutation=old)

    def test_punctuation_and_layout_sensitive_positions_from_pinned_sources(self):
        expected = {'.':(['dot'],['dot']), ';':(['shift','comma'],['semicolon']),
                    "'":(['shift','backslash'],['apostrophe']), 'y':(['z'],['y']),
                    'z':(['y'],['z']), '-':(['slash'],['minus']), '/':(['shift','7'],['slash']),
                    '!':(['shift','1'],['shift','1'])}
        for char, positions in expected.items():
            for layout, position in zip(('de','us'), positions):
                self.assertEqual(vm.physical_keys(char,layout),position)


if __name__ == '__main__':
    unittest.main()
