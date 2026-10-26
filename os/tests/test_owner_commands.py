"""Run complete owner handlers against retained states and executable shims.

The production command bodies and shared Python programs are unchanged. Only
the host adapters, /proc observations and BLS/disk reads are replaced, all with
ordinary files underneath this worktree; no real privilege or service access.
"""
import contextlib
import copy
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import test_owner_tools as common
from guest_shell import syntax

owner, bundle, ROOT = common.owner, common.bundle, common.ROOT
RUN = subprocess.run
GLOB = pathlib.Path.glob


class ShimHost(owner.Host):
    def __init__(self, root):
        super().__init__()
        self.root = root

    def invoke(self, command):
        result = RUN([sys.executable, str(ROOT / 'os/tests/owner_shim.py'), str(self.root), *command],
                     text=True, capture_output=True, check=False)
        if result.returncode:
            raise owner.Stop('Shim command refused: ' + result.stderr)
        return result.stdout

    def read(self, *command, **unused):
        result = self.invoke(command)
        self.trace.append(dict(command=command, stdout=result, returncode=0, mutation=False))
        return result

    def mutate(self, *command, **unused):
        self.invoke(command)
        self.trace.append(dict(command=command, mutation=True))

    def script(self, text, name, mutation=True):
        syntax(name, text)
        # Execute the exact embedded Python, including cleanup_only's loader.
        marker = text.split("<<'", 1)[1].split("'", 1)[0]
        source = text.split("<<'" + marker + "'\n", 1)[1].split('\n' + marker, 1)[0]
        scope = {'__name__': 'owner_shared_step'}
        with patch('subprocess.check_output', side_effect=lambda argv, **kw: self.invoke(argv)), \
                patch('subprocess.run', side_effect=lambda argv, **kw: subprocess.CompletedProcess(argv, 0, self.invoke(argv), '')), \
                patch.object(pathlib.Path, 'glob', lambda p, pattern: iter(()) if str(p) == '/run/user' else GLOB(p, pattern)), \
                contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source, name, 'exec'), scope)
            if marker == 'PAUSE_STOCK':
                scope['deployment_processes'] = lambda: []
                scope['pause_stock']()
            elif marker == 'SYSTEM_KEYBOARD':
                scope['fix']()
        self.trace.append(dict(script=name, mutation=mutation))


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / 'os/tests')
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.payload = self.root / 'payload'
        bundle.build(self.payload)
        self.store = self.root / 'records'
        self.store.mkdir()
        self.host = ShimHost(self.root)
        self.tools = owner.Tools(self.payload, self.host, self.store)
        self.tools.processes = lambda: []
        self.tools.save('disks', dict(target='TARGET', protected='KEEP'))
        self.state = common.stock()
        self.state.update(kargs='quiet ostree=/ostree/boot.1/stock/0 vconsole.keymap=de', paused=False,
            keyboard=dict(VConsoleKeymap='de', VConsoleKeymapToggle='', X11Layout='de', X11Model='pc105', X11Variant='', X11Options=''))
        self.write()
        self.tools.keyboard = lambda: self.read()['keyboard']
        self.disk = patch.object(owner, 'disk_record', return_value={})
        self.disk.start()
        self.addCleanup(self.disk.stop)
        self.bls = patch.object(owner, 'resolved_bls', side_effect=self.entries)
        self.bls.start()
        self.addCleanup(self.bls.stop)
        self.deferred = patch.object(owner, 'runtime_state', return_value=dict(unit='condition false (virtual graphics)'))
        self.deferred.start()
        self.addCleanup(self.deferred.stop)
        self.glob = patch.object(pathlib.Path, 'glob', lambda p, pattern: iter(()) if str(p) == '/run/user' else GLOB(p, pattern))
        self.glob.start()
        self.addCleanup(self.glob.stop)

    def write(self):
        (self.root / 'machine.json').write_text(json.dumps(self.state))

    def read(self):
        return json.loads((self.root / 'machine.json').read_text())

    def entries(self):
        return [dict(identity=list(owner.key(d)), title='stock ' + str(d['serial']), content='options ' + (self.read()['kargs'] if d['booted'] else 'quiet ostree=/old vconsole.keymap=de'))
                for d in self.read()['rpm']['deployments'] if not d.get('staged')]

    def calls(self):
        path = self.root / 'calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def refuse(self, method, message=None):
        before = (self.root / 'machine.json').read_bytes()
        offset = len(self.calls())
        with self.assertRaises(owner.Stop) as caught:
            method()
        if message:
            self.assertIn(message, str(caught.exception))
        self.assertEqual((self.root / 'machine.json').read_bytes(), before)
        self.assertFalse(any(c['mutation'] for c in self.calls()[offset:]))

    def test_prepare_shared_steps_one_two_de_us_no_override_and_rerun(self):
        for count, override in ((2, 'de'), (2, 'us'), (1, 'de'), (1, '')):
            with self.subTest(count=count, override=override):
                self.state = common.stock()
                if count == 1:
                    self.state['rpm']['deployments'].pop()
                    self.state['bootc']['status']['rollback'] = None
                self.state.update(kargs='quiet ostree=/ostree/boot.1/stock/0' + (' vconsole.keymap=' + override if override else ''), paused=False)
                self.write()
                (self.store / 'prepared.json').unlink(missing_ok=True)
                self.tools.prepare()
                prepared = self.tools.load('prepared')
                self.assertEqual(len(prepared['state']['rpm']['deployments']), count)
                self.assertTrue(prepared['stock']['pinned'])
                self.assertNotIn('vconsole', self.read()['kargs'])
                offset = len(self.calls())
                self.tools.prepare()
                self.assertFalse(any(c['mutation'] for c in self.calls()[offset:]))

    def test_complete_prepare_refusals_before_pause(self):
        for change in ('image', 'serial', 'root', 'transaction', 'queue', 'pin', 'origin', 'layer', 'duplicate'):
            self.state = common.stock()
            self.state.update(kargs='ostree=/boot vconsole.keymap=de')
            row = self.state['rpm']['deployments'][0]
            if change == 'image': row['container-image-reference-digest'] = 'sha256:' + 'f' * 64
            elif change == 'serial': row['serial'] += 1
            elif change == 'root': row['osname'] = 'wrong'
            elif change == 'transaction': self.state['rpm']['transaction'] = ['upgrade', 'owner', 'socket']
            elif change == 'queue': self.state['bootc']['status']['rollbackQueued'] = True
            elif change == 'pin': row['pinned'] = True
            elif change == 'origin': row['container-image-reference'] = 'ghcr.io/other/image:stable'
            elif change == 'layer': row['packages'] = ['wrong']
            else: self.state['rpm']['deployments'][1]['serial'] = row['serial']
            self.write()
            with self.subTest(change=change): self.refuse(self.tools.prepare)
        self.state = common.stock()
        self.state.update(kargs='ostree=/boot')
        self.write()
        for tool in ('bootc', 'rpm-ostree', 'ostree'):
            self.tools.processes = lambda: [dict(exe='/usr/bin/' + tool, excluded_as_daemon=False)]
            self.refuse(self.tools.prepare)
        self.tools.processes = lambda: []
        with patch.object(owner, 'disk_record', side_effect=owner.Stop('Wrong target')):
            self.refuse(self.tools.prepare, 'Wrong target')

    def test_staged_fixture_cleanup_and_updater_transaction_cancel_once(self):
        import ast
        import re
        raw = (ROOT / 'os/manifest/ci/11f/full-2/two-disk/pin-stock.txt').read_text()
        self.state['rpm'] = ast.literal_eval(re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw).split('AssertionError:', 1)[1].splitlines()[0].strip())
        self.state['bootc'] = json.loads((ROOT / 'os/manifest/ci/11f/full-2/two-disk/stock-status.json').read_text())
        self.state['rpm']['transaction'] = ['upgrade', 'updater', 'socket']
        self.write()
        def processes():
            return [dict(exe='/usr/bin/bootc', excluded_as_daemon=False, cgroup='0::/system.slice/uupd.service\n')] if self.read()['rpm']['transaction'] else []
        self.tools.processes = processes
        self.tools.prepare()
        commands = [c['command'] for c in self.calls()]
        self.assertEqual(commands.count(['rpm-ostree', 'cancel']), 1)
        self.assertEqual(commands.count(['rpm-ostree', 'cleanup', '-p']), 1)
        self.assertTrue(self.tools.load('prepared')['stock']['pinned'])

    def pair(self):
        state, saved, _ = common.RefusalTest().pair()
        state.update(keyboard=self.state['keyboard'])
        self.state = state
        self.write()
        self.tools.save('prepared', saved)
        return saved

    def test_recovery_refusals_at_complete_handler_leave_shims_unchanged(self):
        self.pair()
        original = copy.deepcopy(self.state)
        for change in ('stockserial', 'root', 'digest', 'reference', 'pin', 'ares', 'transaction', 'queue', 'stockboot'):
            self.state = copy.deepcopy(original)
            stock = self.state['rpm']['deployments'][1]
            if change == 'stockserial': stock['serial'] += 1
            elif change == 'root': stock['osname'] = 'wrong'
            elif change == 'digest': stock['container-image-reference-digest'] = 'sha256:' + 'f' * 64
            elif change == 'reference': stock['container-image-reference'] = 'ghcr.io/other:stable'
            elif change == 'pin': stock['pinned'] = False
            elif change == 'ares': self.state['rpm']['deployments'][0]['container-image-reference'] = 'ghcr.io/other:latest'
            elif change == 'transaction': self.state['rpm']['transaction'] = ['upgrade', 'owner', 'socket']
            elif change == 'queue': self.state['bootc']['status']['rollbackQueued'] = True
            else:
                self.state['rpm']['deployments'][0]['booted'] = False
                stock['booted'] = True
                status = self.state['bootc']['status']
                status['booted'], status['rollback'] = status['rollback'], status['booted']
            self.write()
            with self.subTest(change=change): self.refuse(self.tools.recover)
        self.state = copy.deepcopy(original)
        self.write()
        self.refuse(lambda: self.tools.recover(True))

    def test_layout_fresh_login_refusal_revert_success_and_partial_failure(self):
        self.pair()
        admin = dict(tty='tty3', session='1', boot='boot', started_us=1)
        self.tools.session = lambda: admin
        self.tools.layout('begin', 'us')
        self.refuse(lambda: self.tools.layout('proof'), 'fresh second-console')
        self.refuse(self.tools.reboot, 'unfinished')
        self.tools.layout('revert')
        self.assertEqual(self.read()['keyboard']['VConsoleKeymap'], 'de')
        second = dict(tty='tty4', session='2', boot='boot', started_us=int(time.monotonic()*1000000)+10)
        self.tools.session = lambda: second
        with patch('builtins.input', return_value='wrong'):
            self.refuse(lambda: self.tools.layout('proof'), 'Physical typing')
        with patch('builtins.input', return_value='yz-/!ü'):
            self.tools.layout('proof')
        self.tools.session = lambda: admin
        with patch.object(self.tools, 'title', return_value=['title checked']):
            self.tools.layout('finish')
        self.tools.layout('begin', 'us-intl')
        self.tools.session = lambda: dict(second, session='3', started_us=int(time.monotonic()*1000000)+10)
        with patch('builtins.input', return_value='yz-/!ü'):
            self.tools.layout('proof')
        self.tools.session = lambda: admin
        with patch.object(self.tools, 'title', return_value=['title checked']): self.tools.layout('finish')
        old = self.read()['keyboard']
        self.state = self.read()
        self.state['fail_x11_once'] = True
        self.write()
        with self.assertRaisesRegex(owner.Stop, 'old settings restored'):
            self.tools.layout('begin', 'de')
        self.assertEqual(self.read()['keyboard'], old)

    def test_bad_layout_arguments_never_write(self):
        for args in (('begin', 'xx'), ('proof', 'de'), ('finish', 'de'), ('revert', 'de'), ('no',)):
            self.refuse(lambda: self.tools.layout(*args))


if __name__ == '__main__':
    unittest.main()
