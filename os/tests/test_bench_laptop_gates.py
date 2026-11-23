import io
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
from laptop import Busy, GIB_KIB, Inputs, KVM_GET_API_VERSION, Watch, scope_command, shared_lock
from laptop_cli import Bench, main, native
from store import Store


def mock_mount(_fd):
    return 1


@dataclass(frozen=True)
class FakeInputs(Inputs):
    def kvm_ready(self):
        return self.kvm.read_text() == '12'


def fixture(root):
    paths = {name: root / name for name in ('home', 'proc', 'meminfo', 'pressure', 'power', 'cgroups', 'kvm')}
    for name in ('home', 'proc', 'power', 'cgroups'):
        paths[name].mkdir()
    inputs = FakeInputs(**paths)
    memory(inputs, 8 * GIB_KIB)
    psi(inputs, 0)
    inputs.kvm.write_text('12')
    ac = inputs.power / 'AC'
    ac.mkdir()
    (ac / 'type').write_text('Mains')
    (ac / 'online').write_text('1')
    return inputs


def process_status(path, state='S', uid=None):
    user = os.getuid() if uid is None else uid
    (path / 'status').write_text(f'State:\t{state} (fixture)\nUid:\t{user}\t{user}\t{user}\t{user}\n')


def replace_text(path, text):
    temp = path.with_suffix('.new')
    temp.write_text(text)
    temp.replace(path)


def memory(inputs, available):
    replace_text(inputs.meminfo, f'MemTotal: 16384000 kB\nMemFree: 1 kB\nMemAvailable: {available} kB\n')


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
        process_status(exe.parent)
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
        for path, kind in ((battery, 'Battery'), (mouse, 'Battery')):
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
        (battery / 'status').write_text('Charging')
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

    def test_empty_inventory_and_non_ac_or_usb_evidence_are_refused(self):
        ac = self.inputs.power / 'AC'
        (ac / 'type').write_text('Wireless')
        with self.assertRaisesRegex(Busy, 'power'):
            self.inputs.require('vm')
        (ac / 'type').write_text('USB_PD')
        self.inputs.require('vm')
        (ac / 'online').unlink()
        (ac / 'type').unlink()
        ac.rmdir()
        with self.assertRaisesRegex(Busy, 'power'):
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

    def test_malformed_meminfo_and_psi_refuse(self):
        valid = self.inputs.meminfo.read_text()
        for bad in (
            valid + 'MemAvailable: broken\n',
            valid.replace('8388608 kB', '20000000 kB'),
            valid.replace('8388608 kB', '8388608'),
            valid + 'MemAvailable: 8388608 kB\n',
            valid.replace('MemFree: 1 kB', 'MemFree: 20000000 kB'),
            valid.replace('MemFree: 1 kB', 'MemFree: -1 kB'),
            valid.replace('MemFree: 1 kB\n', ''),
            valid.replace('MemTotal: 16384000 kB\n', ''),
            valid.replace('MemAvailable: 8388608 kB\n', ''),
        ):
            with self.subTest(bad=bad):
                self.inputs.meminfo.write_text(bad)
                with self.assertRaisesRegex(Busy, 'memory reading unavailable'):
                    self.inputs.require('vm')
        memory(self.inputs, 8 * GIB_KIB)
        for bad in (
            'some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n',
            'full avg10=0.00 avg60=0.00 avg300=0.00 total=0\nsome avg10=0.00 avg60=0.00\n',
            'full avg10=0.00 avg60=0.00 avg300=0.00 total=0\nsome avg10=0.00 avg60=101.00 avg300=0.00 total=0\n',
            'some avg10=0.00 avg60=0.00 avg300=0.00 total=0\nsome avg10=1.00 avg60=1.00 avg300=1.00 total=1\n',
            'some avg10=0.00 avg60=0.00 avg300=0.00 total=0\nfull avg10=1.00 avg60=0.00 avg300=0.00 total=1\n',
        ):
            with self.subTest(bad=bad):
                self.inputs.pressure.write_text(bad)
                with self.assertRaisesRegex(Busy, 'pressure reading unavailable'):
                    self.inputs.require('vm')

    def test_owner_permission_error_refuses_but_foreign_and_exited_processes_are_ignored(self):
        process = self.inputs.proc / '1234'
        process.mkdir()
        process_status(process)
        with patch('laptop.os.readlink', side_effect=PermissionError):
            with self.assertRaisesRegex(Busy, 'Lunar Client reading unavailable'):
                self.inputs.require('vm')
            process_status(process, uid=os.getuid() + 1)
            self.inputs.require('vm')
        process_status(process)
        with self.assertRaisesRegex(Busy, 'Lunar Client reading unavailable'):
            self.inputs.require('vm')
        process_status(process, state='Z')
        self.inputs.require('vm')
        (process / 'status').unlink()
        process.rmdir()
        self.inputs.require('vm')

    def test_unknown_battery_type_and_malformed_power_status_refuse(self):
        battery = self.inputs.power / 'BAT0'
        battery.mkdir()
        kind = battery / 'type'
        kind.write_text('Mystery')
        with self.assertRaisesRegex(Busy, 'power reading unavailable'):
            self.inputs.require('vm')
        kind.write_text('Battery')
        (battery / 'status').write_text('Malformed')
        with self.assertRaisesRegex(Busy, 'power reading unavailable'):
            self.inputs.require('vm')

    def test_kvm_requires_open_character_device_and_api_version(self):
        kvm = self.inputs.kvm
        inputs = Inputs(self.inputs.home, kvm=kvm)
        self.assertFalse(inputs.kvm_ready(), 'a writable regular file is not KVM')
        with patch('laptop.os.open', side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                inputs.kvm_ready()
        with patch('laptop.stat.S_ISCHR', return_value=True), patch('laptop.fcntl.ioctl') as ioctl:
            ioctl.return_value = 11
            self.assertFalse(inputs.kvm_ready())
            ioctl.return_value = 12
            self.assertTrue(inputs.kvm_ready())
            self.assertEqual(ioctl.call_args.args[1], KVM_GET_API_VERSION)
            ioctl.side_effect = OSError('fixture ioctl denied')
            with self.assertRaises(OSError):
                inputs.kvm_ready()

    def test_missing_or_malformed_game_events_are_unknown(self):
        game = self.inputs.cgroups / 'aresos-game-fixture.scope'
        game.mkdir()
        self.assertEqual(self.inputs.home_game(), 'unknown')
        for bad in ('populated 2\n', 'frozen 0\n', 'populated 0\npopulated 1\n',
                    'populated 0\nfrozen wrong\n'):
            (game / 'cgroup.events').write_text(bad)
            with self.subTest(bad=bad):
                self.assertEqual(self.inputs.home_game(), 'unknown')

    def test_unsafe_cache_paths_are_refused_before_clean(self):
        worktree = self.root / 'tree'
        worktree.mkdir()
        cache = self.inputs.home / '.cache'
        redirect = self.root / 'redirect'
        redirect.mkdir()
        cache.symlink_to(redirect, target_is_directory=True)
        for path in ('relative', '', '/', str(cache / '..'), str(cache), str(cache / 'child')):
            with self.subTest(path=path), patch.dict(os.environ, {'HOME': str(self.inputs.home),
                                                               'XDG_CACHE_HOME': path}), \
                    patch('laptop_cli.pwd.getpwuid', return_value=SimpleNamespace(pw_dir=str(self.inputs.home))), \
                    patch('laptop_cli.native', side_effect=lambda: native(worktree=worktree)):
                errors = io.StringIO()
                self.assertEqual(main(['clean'], errors=errors), 2)
                self.assertIn('bench:', errors.getvalue())
        self.assertEqual(list(redirect.iterdir()), [])
        self.assertEqual(list(worktree.iterdir()), [])

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
        cache = self.inputs.home / '.cache'
        with patch.dict(os.environ, {'HOME': str(self.inputs.home), 'XDG_CACHE_HOME': str(cache)}), \
                patch('laptop_cli.pwd.getpwuid', return_value=SimpleNamespace(pw_dir=str(self.inputs.home))):
            configs = native(worktree=worktree)
        self.assertEqual(configs.store.lock, self.inputs.home / '.cache/aresos-dev/client-test.lock')
        self.assertEqual(configs.store.root, cache / 'aresos-bench')

        store = Store(configs.store.root, worktree, configs.store.lock, mount=mock_mount)
        bench = Bench(self.inputs, store)
        out = io.StringIO()
        memory(self.inputs, 6 * GIB_KIB)
        self.assertEqual(main(['status'], bench=bench, output=out), 0)
        self.assertIn('0 / 40,000,000,000 bytes allocated', out.getvalue())
        self.assertIn('2,000,000,000 bytes charged to the cap', out.getvalue())
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

    def test_native_rejects_conflicting_home_for_the_same_store(self):
        worktree = self.root / 'tree'
        worktree.mkdir()
        home = self.inputs.home
        alternate = self.root / 'alternate'
        alternate.mkdir()
        with patch('laptop_cli.pwd.getpwuid', return_value=SimpleNamespace(pw_dir=str(home))):
            # An absent environment and explicit canonical settings share the lock.
            with patch.dict(os.environ, {}, clear=True):
                canonical = native(worktree=worktree).store
            with shared_lock(canonical.lock), patch.dict(os.environ, {'HOME': str(home),
                                                                     'XDG_CACHE_HOME': str(home / '.cache')}):
                explicit = native(worktree=worktree).store
                self.assertEqual(explicit.root, canonical.root)
                with self.assertRaisesRegex(Busy, 'lock is busy'):
                    explicit.clean()
                with patch.dict(os.environ, {'HOME': str(alternate)}):
                    with self.assertRaisesRegex(ValueError, 'HOME must match'):
                        native(worktree=worktree)
                with patch.dict(os.environ, {'XDG_CACHE_HOME': str(alternate)}):
                    with self.assertRaisesRegex(ValueError, 'XDG_CACHE_HOME must match'):
                        native(worktree=worktree)
        self.assertEqual(list(alternate.iterdir()), [])
