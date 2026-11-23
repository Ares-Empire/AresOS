import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
from laptop import Busy, GIB_KIB, Inputs, Watch, scope_command, shared_lock
from laptop_cli import Bench, main, native
from store import Store


def fixture(root):
    paths = {name: root / name for name in ('home', 'proc', 'meminfo', 'pressure', 'power', 'cgroups', 'kvm')}
    for name in ('home', 'proc', 'power', 'cgroups'):
        paths[name].mkdir()
    inputs = Inputs(**paths)
    memory(inputs, 8 * GIB_KIB)
    psi(inputs, 0)
    inputs.kvm.touch()
    return inputs


def replace_text(path, text):
    temp = path.with_suffix('.new')
    temp.write_text(text)
    temp.replace(path)


def memory(inputs, available):
    replace_text(inputs.meminfo, f'MemTotal: 16384000 kB\nMemAvailable: {available} kB\n')


def psi(inputs, percent):
    replace_text(inputs.pressure, f'some avg10={percent:.2f} avg60=0.00 avg300=0.00 total=0\n'
                                 'full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n')


class GatesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix='.bench-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = fixture(self.root)

    def test_memory_boundary_and_kvm_only_for_vm(self):
        memory(self.inputs, 7 * GIB_KIB)
        self.inputs.require('vm')
        memory(self.inputs, 6 * GIB_KIB)
        with self.assertRaisesRegex(Busy, '7 GiB'):
            self.inputs.require('vm')
        self.inputs.require('build')
        memory(self.inputs, 6 * GIB_KIB - 1)
        with self.assertRaisesRegex(Busy, '6 GiB'):
            self.inputs.require('build')
        memory(self.inputs, 8 * GIB_KIB)
        self.inputs.kvm.unlink()
        with self.assertRaisesRegex(Busy, 'KVM unavailable'):
            self.inputs.require('vm')
        self.inputs.require('build')

    def test_lunar_matches_only_java_executables_under_either_home_path(self):
        exe = self.inputs.proc / '1234/exe'
        exe.parent.mkdir()
        (exe.parent / 'cmdline').write_text(str(self.inputs.home / '.lunarclient/runtime/bin/java'))
        for target in ('/usr/bin/java', self.inputs.home / '.lunarclient/launcher',
                       self.inputs.home / '.lunarclient-old/runtime/bin/java'):
            exe.symlink_to(target)
            self.inputs.require('vm')
            exe.unlink()
        exe.symlink_to(self.inputs.home / '.lunarclient/a/b/c/bin/java')
        with self.assertRaisesRegex(Busy, 'Lunar Client Java'):
            self.inputs.require('vm')

    def test_battery_and_home_game(self):
        ac, battery, mouse = (self.inputs.power / name for name in ('AC', 'BAT0', 'mouse'))
        for path, kind in ((ac, 'Mains'), (battery, 'Battery'), (mouse, 'Battery')):
            path.mkdir()
            (path / 'type').write_text(kind)
        (mouse / 'scope').write_text('Device')
        (battery / 'status').write_text('Discharging')
        (ac / 'online').write_text('0')
        with self.assertRaisesRegex(Busy, 'battery'):
            self.inputs.require('vm')
        (battery / 'status').write_text('Full')
        with self.assertRaisesRegex(Busy, 'power'):
            self.inputs.require('vm')
        (ac / 'online').write_text('1')
        self.inputs.require('vm')

        game = self.inputs.cgroups / 'a/aresos.slice/aresos-game-fixture.scope'
        game.mkdir(parents=True)
        (game / 'cgroup.events').write_text('populated 0\nfrozen 0\n')
        self.assertEqual(self.inputs.home_game(), 'idle')
        (game / 'cgroup.events').write_text('populated 1\nfrozen 0\n')
        self.assertEqual(self.inputs.home_game(), 'running')
        self.inputs.require('vm')

    def test_unreadable_readings_fail_closed(self):
        self.inputs.meminfo.unlink()
        with self.assertRaisesRegex(Busy, 'memory reading unavailable'):
            self.inputs.require('build')
        memory(self.inputs, 8 * GIB_KIB)
        self.inputs.pressure.write_text('bad\n')
        with self.assertRaisesRegex(Busy, 'pressure reading unavailable'):
            self.inputs.require('vm')
        self.assertIn('reading unavailable', Watch().reason(self.inputs))

    def test_scope_argv_is_literal_and_leaves_swap_enabled(self):
        self.assertEqual(scope_command('vm', 'aresos-bench-fixture.scope', ['/tool', '$NAME']), [
            '/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--collect',
            '--expand-environment=no', '--unit=aresos-bench-fixture.scope', '--slice=aresos-bench.slice',
            '--property=MemoryMax=5G', '--property=CPUWeight=10',
            '--property=KillMode=control-group', '--property=KillSignal=SIGKILL',
            '--property=TimeoutStopSec=2s', '--nice=10',
            '--', '/usr/bin/choom', '-n', '1000', '--', '/tool', '$NAME',
        ])

    def test_native_paths_and_read_only_status(self):
        worktree = self.root / 'tree'
        worktree.mkdir()
        with patch.dict(os.environ, {'HOME': str(self.inputs.home), 'XDG_CACHE_HOME': str(self.root / 'cache')}):
            configs = native()
        self.assertEqual(configs.store.lock, self.inputs.home / '.cache/aresos-dev/client-test.lock')
        self.assertEqual(configs.store.root, self.root / 'cache/aresos-bench')

        store = Store(configs.store.root, worktree, configs.store.lock)
        bench = Bench(self.inputs, store)
        out = io.StringIO()
        memory(self.inputs, 6 * GIB_KIB)
        self.assertEqual(main(['status'], bench=bench, output=out), 0)
        self.assertIn('0 / 40,000,000,000 bytes allocated', out.getvalue())
        self.assertIn('vm memory: needs 7 GiB available', out.getvalue())
        self.assertIn('build memory: ready', out.getvalue())
        self.assertFalse(store.root.parent.exists())
        self.assertFalse(store.lock.parent.exists())
        with shared_lock(store.lock):
            self.assertEqual(main(['clean'], bench=bench, errors=io.StringIO()), 75)
        self.assertEqual(main(['clean'], bench=bench, output=out), 0)
        self.assertTrue(store.lock.is_file())
        self.assertFalse(store.root.exists())
        with self.assertRaises(SystemExit) as caught, patch('sys.stderr', io.StringIO()):
            main(['clean', '--force'], bench=bench)
        self.assertEqual(caught.exception.code, 2)
