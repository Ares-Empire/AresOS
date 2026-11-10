"""The AresOS desktop supervisor and its Java wrapper (package 23; OS-BASE.md section 5, B1, B2, B5)."""
import gzip
import hashlib
import importlib.machinery
import json
import math
import os
import pathlib
import shutil
import struct
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'os/config'
LOCK = json.loads((ROOT / 'os/minecraft/desktop.lock.json').read_text())


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = types.ModuleType(loader.name)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


desktop = load('aresos_desktop', CONFIG / 'usr/libexec/aresos-desktop')
wrapper = load('aresos_desktop_java', CONFIG / 'usr/libexec/aresos-desktop-java')
desktop.LOG.disabled = True
LINUX = sys.platform.startswith('linux')


def fake_share(folder, lock=LOCK):
    """A stand-in for /usr/share/aresos/minecraft whose jars and metadata are random bytes, with a lock pinning them."""
    share = pathlib.Path(folder)
    lock = json.loads(json.dumps(lock))
    for name in ('libraries', 'mods', 'patches'):
        (share / name).mkdir(parents=True)
    for library in lock['fabric_loader']['libraries']:
        data = os.urandom(64)
        (share / 'libraries' / desktop.library_file(library)).write_bytes(data)
        library['sha256'] = hashlib.sha256(data).hexdigest()
    for mod in lock['mods']:
        data = os.urandom(64)
        (share / 'mods' / mod['file']).write_bytes(data)
        mod['sha256'] = hashlib.sha256(data).hexdigest()
    for component in lock['components']:
        data = json.dumps({'uid': component['uid'], 'version': component['version'], 'n': os.urandom(4).hex()})
        (share / 'patches' / component['file']).write_text(data)
        component['sha256'] = hashlib.sha256(data.encode()).hexdigest()
    (share / 'patches' / (desktop.LOADER_UID + '.json')).write_text(json.dumps(desktop.loader_patch(lock)))
    (share / desktop.LOCK_NAME).write_text(json.dumps(lock))
    return str(share), lock


# Minimal NBT writer for real-format saved data (tag, value) pairs, as Minecraft writes them.
BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, STRING, LIST, COMPOUND = 1, 2, 3, 4, 5, 6, 8, 9, 10


def nbt_payload(tag, value):
    if tag in (BYTE, SHORT, INT, LONG, FLOAT, DOUBLE):
        return struct.pack({BYTE: '>b', SHORT: '>h', INT: '>i', LONG: '>q', FLOAT: '>f', DOUBLE: '>d'}[tag], value)
    if tag == STRING:
        data = value.encode()
        return struct.pack('>H', len(data)) + data
    if tag == LIST:
        element, items = value
        return struct.pack('>bi', element, len(items)) + b''.join(nbt_payload(element, item) for item in items)
    if tag == COMPOUND:
        out = b''
        for name, (child, item) in value.items():
            out += struct.pack('>b', child) + nbt_payload(STRING, name) + nbt_payload(child, item)
        return out + b'\0'
    raise ValueError(tag)


def nbt_file(root):
    return gzip.compress(struct.pack('>b', COMPOUND) + nbt_payload(STRING, '') + nbt_payload(COMPOUND, root))


def saved(data):
    return {'data': (COMPOUND, data), 'DataVersion': (INT, 4903)}


MARKER = saved({'enabled': (BYTE, 1)})
HOME = saved({'seed': (LONG, 49), 'x': (INT, -64), 'y': (INT, 56), 'z': (INT, 32), 'yaw': (FLOAT, 0.0)})
LEVEL = {'Data': (COMPOUND, {'LevelName': (STRING, 'AresOS'), 'version': (INT, 19133)})}


def make_world(paths, lock, provisioned='complete\n', marker=MARKER, home=HOME, level=LEVEL, manifest=True):
    world = pathlib.Path(paths.worlds) / lock['world']
    (world / 'data/aresos').mkdir(parents=True)
    if level is not None:
        (world / 'level.dat').write_bytes(nbt_file(level))
    if marker is not None:
        (world / 'data/aresos/desktop.dat').write_bytes(nbt_file(marker))
    if home is not None:
        (world / 'data/aresos/nether_home.dat').write_bytes(nbt_file(home))
    if manifest:
        (world / 'aresos-home.properties').write_text('version=1\nseed=49\n')
    if provisioned is not None:
        (world / 'aresos-home.provisioned').write_text(provisioned)
    return world


class FakeRunner:
    real = False

    def __init__(self):
        self.helpers = []
        self.helper_alive = False
        self.prisms = []
        self.views = []
        self.closed_views = 0
        self.processes = {}
        self.watched = []
        self.lock_held = False
        self.stops = 0
        self.scope = None
        self.scopes_asked = []
        self.pressure = None

    def helper_running(self):
        return self.helper_alive

    def start_helper(self, instance, nonce, env):
        self.helpers.append((instance, nonce, env))
        self.helper_alive = True

    def stop_helper(self):
        self.stops += 1
        self.helper_alive = False

    def start_prism(self, command, env):
        self.prisms.append((command, env))
        return object()

    def identify(self, pid):
        if pid not in self.processes:
            return None
        parent, ticks, *cgroup = self.processes[pid]
        return parent, ticks, cgroup[0] if cgroup else ''

    def alive(self, pid, ticks):
        return pid in self.processes and self.processes[pid][1] == ticks

    def watch_jvm(self, pid, ticks):
        self.watched.append(pid)
        return True

    def jvm_lock_held(self):
        return self.lock_held

    def scope_result(self, unit):
        self.scopes_asked.append(unit)
        return self.scope

    def memory_pressure(self):
        return self.pressure

    def show_view(self, text):
        self.views.append(text)

    def close_view(self, wait=False):
        self.closed_views += 1


class Base(unittest.TestCase):
    def setUp(self):
        if not LINUX:
            self.skipTest('the managed instance is made of symlinks; run on Linux (CI, WSL)')
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        share, self.lock = fake_share(self.root / 'share')
        self.paths = desktop.Paths(str(self.root / 'home'), str(self.root / 'run'), share)
        os.makedirs(self.paths.home)
        os.makedirs(self.paths.runtime)
        self.now = [1000.0]
        self.wall = [1_800_000_000.0]
        self.runner = FakeRunner()
        self.next_pid = 4000

    def advance(self, seconds):
        self.now[0] += seconds
        self.wall[0] += seconds

    def supervisor(self, nvidia=False):
        return desktop.Supervisor(self.paths, self.lock, self.runner, clock=lambda: self.now[0],
                                  wall=lambda: self.wall[0], nvidia=nvidia,
                                  environ={'HOME': self.paths.home, 'XDG_RUNTIME_DIR': self.paths.runtime,
                                           'WAYLAND_DISPLAY': 'wayland-0', 'PATH': '/home/ares/.local/bin:/usr/bin',
                                           'ARESOS_LAUNCH_NONCE': 'leaked-nonce-0000000000'})

    def jvm_request(self, **changes):
        instance = self.paths.instance('AresDesktop')
        request = {'instance': 'AresDesktop', 'java': self.lock['java']['path'], 'instance_dir': instance,
                   'cwd': os.path.join(instance, 'minecraft')}
        request.update(changes)
        return request

    def run_game(self, sup, wrapper_pid=None):
        """The wrapper asks, the JVM starts: returns (pid, the environment the game got)."""
        wrapper_pid = wrapper_pid or self.next_pid
        pid = wrapper_pid + 1
        self.next_pid += 10
        ok, reply = sup.on_jvm_start(self.jvm_request())
        self.assertTrue(ok, reply)
        self.assertEqual(reply['scope'][-2:], ['--property=MemoryHigh=5G', '--'])
        self.assertEqual(reply['unit'], f'aresos-game-{reply["launch"]}.scope')
        self.runner.processes[pid] = (wrapper_pid, pid * 7,
                                      f'0::/user.slice/user@1001.service/aresos.slice/{reply["unit"]}\n')
        self.assertEqual(sup.on_jvm_started(wrapper_pid, pid, reply['launch']), (True, ''))
        return pid, reply['env']

    def end_game(self, sup, pid, status):
        sup.on_jvm_report(pid, status)
        self.runner.processes.pop(pid, None)
        sup.on_jvm_gone()
        sup.tick()

    def ready(self, sup, world='AresHub'):
        sup.on_helper_status({'event': 'world_ready', 'world': world})

    def heartbeat(self, sup, ready=True, world='AresHub'):
        sup.on_helper_status({'event': 'heartbeat', 'ready': ready, 'world': world if ready else None})

    def stored(self):
        return json.loads(pathlib.Path(self.paths.state_file).read_text())


# ---------------------------------------------------------------- pinned inputs


class PinnedInputsTest(unittest.TestCase):
    def test_shipped_loader_patch_is_generated_from_the_lock(self):
        shipped = json.loads((CONFIG / 'usr/share/aresos/minecraft/patches/net.fabricmc.fabric-loader.json')
                             .read_text())
        self.assertEqual(shipped, desktop.loader_patch(LOCK))
        self.assertTrue(all(library['MMC-hint'] == 'local' for library in shipped['libraries']))
        self.assertEqual(shipped['requires'], [{'uid': 'net.minecraft', 'equals': '26.2'}])

    def test_every_input_is_pinned_by_sha256_and_comes_from_its_upstream(self):
        self.assertEqual(LOCK['minecraft'], '26.2')
        self.assertEqual(LOCK['java']['major'], 25)
        self.assertEqual(LOCK['fabric_loader']['version'], '0.19.5')
        entries = [LOCK['prism'], *LOCK['fabric_loader']['libraries'], *LOCK['mods']]
        for entry in entries:
            self.assertRegex(entry['sha256'], r'\A[0-9a-f]{64}\Z', entry)
        for library in LOCK['fabric_loader']['libraries']:
            self.assertTrue(library['url'].startswith('https://maven.fabricmc.net/'), library)
            desktop.library_file(library)
        self.assertTrue(LOCK['prism']['url'].startswith(
            'https://github.com/PrismLauncher/PrismLauncher/releases/download/11.1.1/'))
        mods = {mod['file']: mod for mod in LOCK['mods']}
        self.assertEqual(set(mods), {'fabric-api.jar', 'aresos.jar'})
        self.assertEqual(mods['fabric-api.jar']['version'], '0.161.0+26.2')
        # The mod jar is built from this repository, never downloaded; its builder is pinned by digest.
        self.assertNotIn('url', mods['aresos.jar'])
        self.assertRegex(mods['aresos.jar']['builder'], r'@sha256:[0-9a-f]{64}\Z')
        # No Sodium or Iris yet (brief 23).
        self.assertFalse([m for m in mods if 'sodium' in m.lower() or 'iris' in m.lower()])

    def test_mod_version_matches_gradle(self):
        gradle = (ROOT / 'mod/gradle.properties').read_text()
        mod = next(m for m in LOCK['mods'] if m['file'] == 'aresos.jar')
        self.assertIn(f'version={mod["version"]}\n', gradle)
        self.assertIn(f'loader_version={LOCK["fabric_loader"]["version"]}\n', gradle)
        self.assertIn(f'minecraft_version={LOCK["minecraft"]}\n', gradle)
        self.assertIn('fabric_api_version=0.161.0+26.2\n', gradle)

    def test_mod_jar_is_reproducible(self):
        gradle = (ROOT / 'mod/build.gradle').read_text()
        self.assertIn('preserveFileTimestamps = false', gradle)
        self.assertIn('reproducibleFileOrder = true', gradle)

    def test_library_file_names_follow_prism(self):
        self.assertEqual(desktop.library_file({'name': 'net.fabricmc:sponge-mixin:0.17.4+mixin.0.8.7',
                                               'url': 'https://x/sponge-mixin-0.17.4+mixin.0.8.7.jar'}),
                         'sponge-mixin-0.17.4+mixin.0.8.7.jar')
        with self.assertRaises(ValueError):
            desktop.library_file({'name': 'a:b:1', 'url': 'https://x/c-1.jar'})


class VerifyInputsTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.share, self.lock = fake_share(folder.name)

    def test_matching_inputs_pass(self):
        self.assertEqual(desktop.verify_inputs(self.lock, self.share, java_check=False), [])

    def test_a_changed_jar_is_a_pin_mismatch(self):
        (pathlib.Path(self.share) / 'mods/aresos.jar').write_bytes(b'other')
        problems = desktop.verify_inputs(self.lock, self.share, java_check=False)
        self.assertEqual(len(problems), 1)
        self.assertIn('aresos.jar does not match its pinned SHA-256', problems[0])

    def test_missing_extra_symlinked_and_patched_inputs_are_reported(self):
        share = pathlib.Path(self.share)
        (share / 'libraries/asm-9.10.1.jar').unlink()
        (share / 'mods/sodium.jar').write_bytes(b'x')
        target = share / 'mods/fabric-api.jar'
        moved = share / 'elsewhere.jar'
        target.rename(moved)
        target.symlink_to(moved) if LINUX else moved.rename(target)
        patch = json.loads((share / 'patches/net.fabricmc.fabric-loader.json').read_text())
        patch['libraries'].append({'name': 'evil:agent:1', 'MMC-hint': 'local'})
        (share / 'patches/net.fabricmc.fabric-loader.json').write_text(json.dumps(patch))
        text = '\n'.join(desktop.verify_inputs(self.lock, self.share, java_check=False))
        self.assertIn('asm-9.10.1.jar', text)
        self.assertIn('unpinned files: sodium.jar', text)
        self.assertIn('differs from the pinned Fabric Loader', text)
        if LINUX:
            self.assertIn('fabric-api.jar is not a regular file', text)

    def test_the_pinned_component_metas_are_inputs_too(self):
        # Review 1, finding 8: the Minecraft and LWJGL metas Prism reads ship with the image and must match the pin.
        patches = pathlib.Path(self.share) / 'patches'
        meta = json.loads((patches / 'org.lwjgl3.json').read_text())
        meta['version'] = '3.4.3'
        (patches / 'org.lwjgl3.json').write_text(json.dumps(meta))
        (patches / 'org.lwjgl.json').write_text('{}')
        text = '\n'.join(desktop.verify_inputs(self.lock, self.share, java_check=False))
        self.assertIn('org.lwjgl3.json does not match its pinned SHA-256', text)
        self.assertIn('unpinned files: org.lwjgl.json', text)
        self.assertEqual(sorted(os.path.basename(path) for path, _ in desktop.pinned_files(self.lock, self.share)
                                if os.path.dirname(path) == str(patches)),
                         ['net.minecraft.json', 'org.lwjgl3.json'])

    def test_java_and_prism_must_exist(self):
        problems = desktop.verify_inputs(self.lock, self.share, java_check=True)
        if not os.access(self.lock['java']['path'], os.X_OK):
            self.assertIn(f'Java 25 is missing: {self.lock["java"]["path"]}', problems)


# ---------------------------------------------------------------- provisioning


class ProvisionTest(Base):
    def snapshot(self):
        result = {}
        for path in sorted(pathlib.Path(self.paths.home).rglob('*')):
            if path.is_symlink():
                result[str(path)] = ('link', os.readlink(path))
            elif path.is_file():
                result[str(path)] = ('file', path.read_bytes(), path.stat().st_mtime_ns)
            else:
                result[str(path)] = ('dir',)
        return result

    def test_first_start_creates_the_managed_instance_from_image_inputs(self):
        created = desktop.provision(self.paths, self.lock)
        instance = pathlib.Path(self.paths.instance('AresDesktop'))
        self.assertEqual(created, [self.paths.worlds, str(instance), self.paths.prism_config])
        self.assertEqual(sorted(p.name for p in instance.iterdir()),
                         ['.aresos-managed.json', 'instance.cfg', 'libraries', 'minecraft', 'mmc-pack.json', 'patches'])
        links = {'patches': os.path.join(self.paths.share, 'patches'),
                 'libraries': os.path.join(self.paths.share, 'libraries'),
                 'minecraft/mods': os.path.join(self.paths.share, 'mods'),
                 'minecraft/saves': self.paths.worlds}
        for link, target in links.items():
            self.assertTrue(os.path.islink(instance / link), link)
            self.assertEqual(os.readlink(instance / link), target)
        settings = desktop.parse_ini((instance / 'instance.cfg').read_text())
        self.assertEqual(settings['WrapperCommand'], '/usr/libexec/aresos-desktop-java')
        self.assertEqual(settings['JavaPath'], self.lock['java']['path'])
        self.assertEqual((settings['OverrideMemory'], settings['MaxMemAlloc']), ('true', '3072'))
        self.assertEqual((settings['ShowConsoleOnError'], settings['UseDiscreteGpu']), ('false', 'false'))
        self.assertEqual(settings['AutomaticJava'], 'false')
        pack = json.loads((instance / 'mmc-pack.json').read_text())
        self.assertEqual([(c['uid'], c['version']) for c in pack['components']],
                         [('net.minecraft', '26.2'), ('org.lwjgl3', '3.4.1'), ('net.fabricmc.fabric-loader', '0.19.5')])
        options = (instance / 'minecraft/options.txt').read_text().splitlines()
        self.assertIn('renderDistance:8', options)
        self.assertIn('simulationDistance:5', options)
        self.assertIn('fullscreen:false', options)
        prism = desktop.parse_ini(pathlib.Path(self.paths.prism_config).read_text())
        self.assertEqual((prism['AutomaticJavaDownload'], prism['AutomaticJavaSwitch'], prism['IgnoreJavaWizard']),
                         ('false', 'false', 'true'))
        self.assertEqual(desktop.check_instance(self.paths, self.lock), [])
        self.assertFalse([p for p in pathlib.Path(self.paths.instances).iterdir() if p.name.startswith('.')])

    def test_provisioning_is_idempotent(self):
        desktop.provision(self.paths, self.lock)
        before = self.snapshot()
        time.sleep(0.01)
        self.assertEqual(desktop.provision(self.paths, self.lock), [])
        self.assertEqual(self.snapshot(), before)

    def test_an_existing_instance_and_prism_config_are_never_overwritten(self):
        instance = pathlib.Path(self.paths.instance('AresDesktop'))
        (instance / 'minecraft').mkdir(parents=True)
        (instance / 'instance.cfg').write_text('[General]\nWrapperCommand=\nJavaPath=/opt/java\n')
        pathlib.Path(self.paths.prism_config).write_text('[General]\nLanguage=de_DE\n')
        before = self.snapshot()
        self.assertEqual(desktop.provision(self.paths, self.lock), [self.paths.worlds])
        new = os.path.dirname(self.paths.worlds)
        after = {k: v for k, v in self.snapshot().items() if not k.startswith(new)}
        self.assertEqual(after, before)
        problems = '\n'.join(desktop.check_instance(self.paths, self.lock))
        self.assertIn("WrapperCommand is ''", problems)
        self.assertIn('minecraft/mods is not the AresOS link', problems)
        self.assertIn('mmc-pack.json', problems)

    def test_a_failed_provisioning_leaves_no_half_instance(self):
        real = os.symlink
        calls = []

        def failing(*args, **kwargs):
            calls.append(args)
            if len(calls) == 3:
                raise OSError(28, 'No space left on device')
            return real(*args, **kwargs)

        if not LINUX:
            self.skipTest('symlinks need Linux')
        with mock.patch.object(desktop.os, 'symlink', failing):
            with self.assertRaises(OSError):
                desktop.provision(self.paths, self.lock)
        self.assertEqual(os.listdir(self.paths.instances), [])
        self.assertTrue(os.listdir(os.path.join(self.paths.share, 'mods')), 'staging cleanup followed a link')
        desktop.provision(self.paths, self.lock)
        self.assertEqual(desktop.check_instance(self.paths, self.lock), [])

    def test_drift_in_the_instance_is_reported_never_repaired(self):
        if not LINUX:
            self.skipTest('symlinks need Linux')
        desktop.provision(self.paths, self.lock)
        instance = pathlib.Path(self.paths.instance('AresDesktop'))
        (instance / 'minecraft/saves').unlink()
        (instance / 'minecraft/saves').symlink_to('/tmp/elsewhere')
        config = (instance / 'instance.cfg').read_text().replace('WrapperCommand=/usr/libexec/aresos-desktop-java',
                                                                 'WrapperCommand=/usr/bin/env')
        (instance / 'instance.cfg').write_text(config + 'lastLaunchTime=5\n')
        pack = json.loads((instance / 'mmc-pack.json').read_text())
        pack['components'][0]['version'] = '26.3'
        pack['components'][1]['version'] = '3.4.3'
        pack['components'].append({'uid': 'net.neoforged', 'version': '1'})
        (instance / 'mmc-pack.json').write_text(json.dumps(pack))
        problems = desktop.check_instance(self.paths, self.lock)
        self.assertEqual(len(problems), 5, problems)
        text = '\n'.join(problems)
        self.assertIn('minecraft/saves points to /tmp/elsewhere', text)
        self.assertIn("WrapperCommand is '/usr/bin/env'", text)
        self.assertIn('Minecraft is 26.3, this AresOS pins 26.2', text)
        self.assertIn('LWJGL is 3.4.3, this AresOS pins 3.4.1', text)
        self.assertIn('unexpected components: net.neoforged', text)
        self.assertEqual((instance / 'mmc-pack.json').read_text(), json.dumps(pack))

    def test_prism_rewriting_its_own_keys_is_not_drift(self):
        if not LINUX:
            self.skipTest('symlinks need Linux')
        desktop.provision(self.paths, self.lock)
        instance = pathlib.Path(self.paths.instance('AresDesktop'))
        # As Prism's QSettings writes it back after a launch.
        (instance / 'instance.cfg').write_text(
            '[General]\nConfigVersion=1.3\nInstanceType=OneSix\nJavaPath=/usr/lib/jvm/java-25-openjdk/bin/java\n'
            'JavaVersion=25.0.5\nOverrideCommands=true\nOverrideJavaLocation=true\nlastLaunchTime=1763000000\n'
            'WrapperCommand=/usr/libexec/aresos-desktop-java\nname=AresDesktop\n')
        # And mmc-pack.json as Prism saves it: its own order and cached fields.
        pack = json.loads((instance / 'mmc-pack.json').read_text())
        pack['components'].reverse()
        for component in pack['components']:
            component['cachedRequires'] = [{'uid': 'net.minecraft'}]
        (instance / 'mmc-pack.json').write_text(json.dumps(pack))
        self.assertEqual(desktop.check_instance(self.paths, self.lock), [])

    def test_any_other_lwjgl_or_a_missing_or_doubled_component_is_drift(self):
        # Review 1, finding 8: the whole executable set is pinned, LWJGL included.
        desktop.provision(self.paths, self.lock)
        pack_file = pathlib.Path(self.paths.instance('AresDesktop')) / 'mmc-pack.json'
        original = json.loads(pack_file.read_text())
        for change, expected in ((lambda c: c.__setitem__(1, dict(c[1], version='3.4.3')), 'LWJGL is 3.4.3'),
                                 (lambda c: c.pop(1), 'LWJGL is None'),
                                 (lambda c: c.append(dict(c[1])), 'a component listed twice')):
            pack = json.loads(json.dumps(original))
            change(pack['components'])
            pack_file.write_text(json.dumps(pack))
            self.assertIn(expected, '\n'.join(desktop.check_instance(self.paths, self.lock)))


class WorldCheckTest(Base):
    # Review 1, finding 2: real saved data, not gzip-readable placeholders.

    def check(self, **world):
        shutil.rmtree(self.paths.worlds, ignore_errors=True)
        make_world(self.paths, self.lock, **world)
        return desktop.check_world(self.paths, self.lock)

    def test_the_readers_follow_the_mods_real_saved_data(self):
        # Files the mod itself wrote in a client game test (os/tests/fixtures/desktop-world/SOURCE.txt).
        fixtures = ROOT / 'os/tests/fixtures/desktop-world'
        marker = desktop.read_saved(str(fixtures / 'desktop.dat'))
        self.assertEqual(marker['data'], (COMPOUND, {'enabled': (BYTE, 1)}))
        self.assertEqual(marker['DataVersion'][0], INT)
        home = desktop.read_saved(str(fixtures / 'nether_home.dat'))['data'][1]
        self.assertEqual({name: tag for name, (tag, _) in home.items()},
                         {'seed': LONG, 'x': INT, 'y': INT, 'z': INT, 'yaw': FLOAT})
        desktop.check_marker(str(fixtures / 'desktop.dat'))
        desktop.check_home(str(fixtures / 'nether_home.dat'))
        # A hub made of exactly those files passes.
        world = make_world(self.paths, self.lock, marker=None, home=None)
        shutil.copy(fixtures / 'desktop.dat', world / 'data/aresos/desktop.dat')
        shutil.copy(fixtures / 'nether_home.dat', world / 'data/aresos/nether_home.dat')
        self.assertEqual(desktop.check_world(self.paths, self.lock), ('ok', str(world)))

    def test_a_valid_hub_passes(self):
        self.assertEqual(desktop.check_world(self.paths, self.lock)[0], 'missing')
        self.assertEqual(self.check()[0], 'ok')
        with_home = saved({**HOME['data'][1], 'home': (COMPOUND, {
            'dimension': (STRING, 'minecraft:the_nether'), 'position': (LIST, (DOUBLE, [1.5, 64.0, 2.5])),
            'yaw': (FLOAT, 90.0), 'pitch': (FLOAT, 20.0)})})
        self.assertEqual(self.check(home=with_home)[0], 'ok')

    def test_damage_is_named_and_never_repaired(self):
        cases = {
            'missing home data': (dict(home=None), 'the saved Nether home (data/aresos/nether_home.dat) is missing'),
            'disabled marker': (dict(marker=saved({'enabled': (BYTE, 0)})), 'switched off'),
            'marker without enabled': (dict(marker=saved({})), 'enabled is missing'),
            'missing marker': (dict(marker=None), 'desktop marker (data/aresos/desktop.dat) is missing'),
            'home with a wrong type': (dict(home=saved({**HOME['data'][1], 'x': (LONG, 1)})), 'x is missing'),
            'home with a bad position': (dict(home=saved({**HOME['data'][1], 'home': (COMPOUND, {
                'dimension': (STRING, 'minecraft:the_nether'), 'position': (LIST, (DOUBLE, [1.0])),
                'yaw': (FLOAT, 0.0), 'pitch': (FLOAT, 0.0)})})), 'three numbers'),
            'interrupted provisioning': (dict(provisioned='started\n'), 'the hub build was not finished'),
            'no completion record': (dict(provisioned=None), 'no completion record'),
            'no manifest': (dict(manifest=False), 'manifest'),
            'unreadable level': (dict(level=None), 'the level cannot be read'),
            'level without Data': (dict(level={'Other': (INT, 1)}), 'Data is missing'),
        }
        for name, (world, expected) in cases.items():
            with self.subTest(name):
                before = None
                state, detail = self.check(**world)
                self.assertEqual(state, 'damaged', detail)
                self.assertIn(expected, detail)
        # Never repaired: checking leaves every byte as it was.
        world = pathlib.Path(self.paths.worlds, 'AresHub')
        before = sorted((path, path.read_bytes()) for path in world.rglob('*') if path.is_file())
        desktop.check_world(self.paths, self.lock)
        self.assertEqual(sorted((path, path.read_bytes()) for path in world.rglob('*') if path.is_file()), before)

    def test_malformed_nbt_is_damage(self):
        raw = gzip.decompress(nbt_file(MARKER))
        for name, data in (('not gzip', b'not gzip'), ('truncated', gzip.compress(raw[:-3])),
                           ('trailing bytes', gzip.compress(raw + b'\0')),
                           ('unknown tag', gzip.compress(raw[:3] + b'\x63' + raw[4:])),
                           ('list root', gzip.compress(b'\x09' + raw[1:]))):
            with self.subTest(name):
                shutil.rmtree(self.paths.worlds, ignore_errors=True)
                world = make_world(self.paths, self.lock)
                (world / 'data/aresos/desktop.dat').write_bytes(data)
                state, detail = desktop.check_world(self.paths, self.lock)
                self.assertEqual(state, 'damaged', name)
                self.assertIn('unreadable', detail)
        deep = b'\x0a\x00\x00' + b'\x0a\x00\x00' * 100 + b'\x00' * 101
        with self.assertRaises(desktop.NbtError):
            desktop.read_nbt(deep)

    def test_an_older_level_copy_counts_when_the_level_file_is_damaged(self):
        world = make_world(self.paths, self.lock)
        (world / 'level.dat').write_bytes(b'not gzip')
        self.assertEqual(desktop.check_world(self.paths, self.lock)[0], 'damaged')
        (world / 'level.dat_old').write_bytes(nbt_file(LEVEL))
        self.assertEqual(desktop.check_world(self.paths, self.lock)[0], 'ok')

    def test_exact_home_data_must_be_valid_by_the_mods_codecs(self):
        # Review 2, finding 5: home.dimension is an Identifier (Level.RESOURCE_KEY_CODEC), and an exact home's yaw
        # and pitch must be numbers, or the promised arrival cannot happen.
        def home(dimension='minecraft:the_nether', yaw=90.0, pitch=20.0):
            return saved({**HOME['data'][1], 'home': (COMPOUND, {
                'dimension': (STRING, dimension), 'position': (LIST, (DOUBLE, [1.5, 64.0, 2.5])),
                'yaw': (FLOAT, yaw), 'pitch': (FLOAT, pitch)})})
        for dimension in ('minecraft:the_nether', 'the_nether', ':the_nether', 'aresos:hub/nether-1.2', 'a:'):
            with self.subTest(valid=dimension):
                self.assertEqual(self.check(home=home(dimension))[0], 'ok')
        for dimension in ('Minecraft:the_nether', 'minecraft:the nether', 'a:b:c', '..:nether', 'mine/craft:x',
                          'minecraft:nether\u00e9', ''.join(['minecraft:', 'x' * 3, '\\'])):
            with self.subTest(invalid=dimension):
                state, detail = self.check(home=home(dimension))
                self.assertEqual(state, 'damaged', detail)
                self.assertIn('home dimension is not a valid identifier', detail)
        for name, value in (('yaw', math.nan), ('yaw', math.inf), ('pitch', -math.inf), ('pitch', math.nan)):
            with self.subTest(angle=name, value=value):
                state, detail = self.check(home=home(**{name: value}))
                self.assertEqual(state, 'damaged', detail)
                self.assertIn(f'home {name} is not a number', detail)

    def test_strings_are_read_as_java_writes_them(self):
        # Review 2, finding 6: NBT strings are Java's modified UTF-8. The fixture was written by the JDK's own
        # DataOutput.writeUTF (fixtures/desktop-world/JavaStrings.java): an emoji and a NUL.
        fixture = ROOT / 'os/tests/fixtures/desktop-world/level-modified-utf8.dat'
        data = desktop.read_saved(str(fixture))['Data'][1]
        self.assertEqual(data['LevelName'], (STRING, 'AresHub \U0001f525'))
        self.assertEqual(data['Note'], (STRING, 'a\0b'))
        world = make_world(self.paths, self.lock)
        shutil.copy(fixture, world / 'level.dat')
        self.assertEqual(desktop.check_world(self.paths, self.lock)[0], 'ok')
        self.assertEqual(desktop.java_utf(b'\xed\xa0\xbd\xed\xb4\xa5\xc0\x80'), '\U0001f525\0')
        self.assertEqual(desktop.java_utf(b'\xed\xa0\xbd'), '\ud83d', 'a lone surrogate stays, as in Java')
        for bad in (b'\xf0\x9f\x94\xa5', b'\xc0', b'\xe0\x80', b'\x80', b'\xc3\x28'):
            with self.subTest(bad=bad), self.assertRaises(desktop.NbtError):
                desktop.java_utf(bad)

    def test_corrupt_compressed_data_is_damage_never_a_crash(self):
        # Review 2, finding 7: a valid gzip header followed by corrupt DEFLATE data raises zlib.error.
        raw = gzip.compress(gzip.decompress(nbt_file(MARKER)))
        corrupt = raw[:10] + b'\xff' * 24 + raw[-8:]
        cases = {'corrupt deflate': corrupt, 'bad header': b'\x1f\x8b\x09' + raw[3:],
                 'cut-off stream': raw[:-12], 'wrong checksum': raw[:-8] + b'\0' * 8,
                 'truncated nbt': gzip.compress(gzip.decompress(raw)[:-3])}
        for name, data in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.paths.worlds, ignore_errors=True)
                world = make_world(self.paths, self.lock)
                (world / 'data/aresos/desktop.dat').write_bytes(data)
                state, detail = desktop.check_world(self.paths, self.lock)
                self.assertEqual(state, 'damaged', detail)
                self.assertIn('unreadable', detail)
        # The same corruption in level.dat falls back to a valid level.dat_old, or is damage without one.
        shutil.rmtree(self.paths.worlds, ignore_errors=True)
        world = make_world(self.paths, self.lock)
        (world / 'level.dat').write_bytes(nbt_file(LEVEL)[:10] + b'\xff' * 24 + nbt_file(LEVEL)[-8:])
        state, detail = desktop.check_world(self.paths, self.lock)
        self.assertEqual(state, 'damaged', detail)
        self.assertIn('level.dat: not readable gzip data', detail)
        (world / 'level.dat_old').write_bytes(nbt_file(LEVEL))
        self.assertEqual(desktop.check_world(self.paths, self.lock)[0], 'ok')
        # Through the supervisor's own gate: recovery, not an exception in the keeper's loop.
        (world / 'data/aresos/desktop.dat').write_bytes(corrupt)
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'world_damaged'))


# ---------------------------------------------------------------- launch command and environment


class LaunchTest(unittest.TestCase):
    def test_prism_runs_in_its_own_scope_with_the_b5_memory_target(self):
        self.assertEqual(desktop.prism_command(LOCK, 'abc123', 'AresHub'), [
            '/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--collect', '--slice=aresos.slice',
            '--unit=aresos-desktop-abc123.scope', '--',
            '/usr/bin/prismlauncher', '--launch', 'AresDesktop', '--world', 'AresHub'])
        self.assertEqual(desktop.prism_command(LOCK, 'abc123')[-3:], ['/usr/bin/prismlauncher', '--launch',
                                                                      'AresDesktop'])
        # Review 1, finding 4: the memory target sits on the JVM's own scope, which the wrapper creates.
        self.assertEqual(desktop.game_scope('abc123'), [
            '/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--slice=aresos.slice',
            '--unit=aresos-game-abc123.scope', '--property=MemoryHigh=5G', '--'])
        self.assertTrue(desktop.game_cgroup_matches(
            '0::/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-game-abc123.scope\n', 'abc123'))
        for cgroup in ('0::/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-desktop-abc123.scope\n',
                       '0::/user.slice/user-1001.slice/session-2.scope\n', '',
                       '0::/a/aresos.slice/aresos-game-abc123.scope\n0::/b\n'):
            self.assertFalse(desktop.game_cgroup_matches(cgroup, 'abc123'), cgroup)

    def test_memory_pressure_reads_the_last_ten_seconds(self):
        # Review 2, finding 2: samples of 'some avg10'; the supervisor builds the clear minute from them.
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'memory')
            pathlib.Path(path).write_text('some avg10=1.00 avg60=23.50 avg300=4.00 total=1\n'
                                          'full avg10=0.00 avg60=2.00 avg300=0.00 total=1\n')
            self.assertEqual(desktop.memory_pressure(path), 1.0)
            self.assertIsNone(desktop.memory_pressure(os.path.join(folder, 'none')))

    def test_prism_gets_the_system_path_and_no_launch_secrets(self):
        env = desktop.session_environment({'PATH': '/home/ares/.local/bin:/usr/bin', 'WAYLAND_DISPLAY': 'w',
                                           'ARESOS_LAUNCH_NONCE': 'x' * 20, 'ARESOS_DESKTOP_INSTANCE': 'd',
                                           'ARESOS_SHELL_STATUS_FD': '5', 'NOTIFY_SOCKET': '/run/x'})
        self.assertEqual(env, {'PATH': '/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin', 'WAYLAND_DISPLAY': 'w'})

    def test_the_game_runs_on_nvidia_only_when_its_driver_is_there(self):
        env = desktop.game_environment('desk-1', 'n' * 32, nvidia=True)
        self.assertEqual(env, {'ARESOS_DESKTOP_INSTANCE': 'desk-1', 'ARESOS_LAUNCH_NONCE': 'n' * 32,
                               'PATH': '/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin',
                               '__NV_PRIME_RENDER_OFFLOAD': '1', '__GLX_VENDOR_LIBRARY_NAME': 'nvidia',
                               '__VK_LAYER_NV_optimus': 'NVIDIA_only'})
        self.assertNotIn('__NV_PRIME_RENDER_OFFLOAD', desktop.game_environment('d', 'n' * 32, nvidia=False))
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(desktop.nvidia_present(root))
            os.makedirs(os.path.join(root, 'proc/driver/nvidia/gpus/0000:01:00.0'))
            self.assertTrue(desktop.nvidia_present(root))

    def test_the_wrapper_scrubs_prisms_bundle_and_gpu_variables(self):
        prism = {'HOME': '/var/home/ares', 'WAYLAND_DISPLAY': 'wayland-0', 'DISPLAY': ':0', 'INST_ID': 'AresDesktop',
                 'QT_PLUGIN_PATH': '/usr/lib/prismlauncher/shared/lib/qt6/plugins',
                 'XKB_CONFIG_ROOT': '/usr/lib/prismlauncher/share/X11/xkb', 'LD_PRELOAD': '/x.so',
                 'LD_LIBRARY_PATH': '/usr/lib/prismlauncher/shared/lib', 'DRI_PRIME': '1',
                 '__GLX_VENDOR_LIBRARY_NAME': 'mesa', 'ARESOS_LAUNCH_NONCE': 'old-nonce-from-somewhere',
                 'PATH': '/usr/lib/prismlauncher/bin:/usr/bin'}
        supplied = desktop.game_environment('desk-1', 'n' * 32, nvidia=False)
        env = wrapper.game_environment(prism, supplied)
        self.assertEqual(env, {'HOME': '/var/home/ares', 'WAYLAND_DISPLAY': 'wayland-0', 'DISPLAY': ':0',
                               'INST_ID': 'AresDesktop', **supplied})
        with self.assertRaises(ValueError):
            wrapper.game_environment(prism, {'LD_PRELOAD': '/evil.so'})

    def test_wrapper_and_supervisor_agree_on_what_the_supervisor_supplies(self):
        supplied = desktop.game_environment('d', 'n' * 32, nvidia=True)
        self.assertLessEqual(set(supplied), wrapper.SUPPLIED)
        self.assertEqual(desktop.SYSTEM_PATH, wrapper.SYSTEM_PATH)
        self.assertEqual(desktop.PRISM_ROOT, wrapper.PRISM_ROOT)


# ---------------------------------------------------------------- restart policy


class PolicyTest(unittest.TestCase):
    def test_three_failures_within_five_minutes_latch(self):
        policy = desktop.Persisted()
        self.assertEqual(policy.record_failure(0), (False, 5.0))
        policy.consecutive = 0
        self.assertEqual(policy.record_failure(100)[0], False)
        policy.consecutive = 0
        self.assertEqual(policy.record_failure(299)[0], True)

    def test_failures_outside_the_window_do_not_count_but_consecutive_ones_do(self):
        policy = desktop.Persisted()
        latched = [policy.record_failure(t)[0] for t in (0, 240, 480)]
        self.assertEqual(latched, [False, False, True])
        self.assertEqual(len(policy.failures), 2)
        self.assertEqual(policy.consecutive, 3)

    def test_backoff_grows(self):
        policy = desktop.Persisted()
        self.assertEqual([policy.record_failure(t * 1000)[1] for t in range(3)], [5.0, 10.0, 20.0])

    def test_round_trip_and_unreadable_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'desktop.json')
            policy = desktop.Persisted(latched=True, reason='crashes', detail='exit code 1', consecutive=3,
                                       failures=[1.0, 2.0], hub_seen=True)
            policy.save(path)
            self.assertEqual(desktop.Persisted.load(path), policy)
            pathlib.Path(path).write_text('{broken')
            broken = desktop.Persisted.load(path)
            self.assertTrue(broken.latched)
            self.assertEqual(broken.reason, 'state')
            self.assertEqual(desktop.Persisted.load(os.path.join(folder, 'none.json')), desktop.Persisted())


# ---------------------------------------------------------------- the supervisor


class FirstStartTest(Base):
    def test_first_start_is_setup_on_the_title_screen_with_prisms_sign_in(self):
        sup = self.supervisor()
        sup.start()
        self.assertEqual(sup.state, 'SETUP')
        self.assertTrue(os.path.isdir(self.paths.instance('AresDesktop')))
        self.assertTrue(os.path.isdir(self.paths.worlds))
        (command, env), = self.runner.prisms
        self.assertEqual(command[-3:], ['/usr/bin/prismlauncher', '--launch', 'AresDesktop'])
        self.assertNotIn('--world', command)
        self.assertNotIn('ARESOS_LAUNCH_NONCE', env)
        self.assertEqual(env['PATH'], desktop.SYSTEM_PATH)
        (instance, nonce, helper_env), = self.runner.helpers
        self.assertEqual((instance, nonce), (sup.instance, sup.launch.nonce))
        self.assertRegex(nonce, r'\A[A-Za-z0-9_-]{16,128}\Z')
        self.assertRegex(instance, r'\A[A-Za-z0-9._-]{1,64}\Z')
        self.assertNotIn('leaked-nonce', json.dumps(helper_env))
        self.assertEqual(len(self.runner.views), 1)
        self.assertIn('Sign in there with your own Microsoft account', self.runner.views[0])
        self.assertIn('click AresOS', self.runner.views[0])

    def test_creating_the_hub_finishes_setup(self):
        sup = self.supervisor()
        sup.start()
        pid, env = self.run_game(sup)
        self.assertEqual(sup.state, 'SETUP')
        self.assertEqual((env['ARESOS_DESKTOP_INSTANCE'], env['ARESOS_LAUNCH_NONCE']), self.runner.helpers[-1][:2])
        self.ready(sup, 'SomeOtherDesktop')
        self.assertEqual(sup.state, 'IN_WORLD')
        self.assertFalse(sup.persisted.hub_seen)
        self.ready(sup, 'AresHub')
        self.assertTrue(self.stored()['hub_seen'])
        self.assertEqual(self.runner.closed_views, 1)

    def test_prism_closing_without_a_game_during_setup_waits_for_the_owner(self):
        sup = self.supervisor()
        sup.start()
        self.advance(60)
        sup.on_prism_exit(1)
        sup.tick()
        self.assertEqual(sup.state, 'SETUP')
        self.advance(desktop.PRISM_GRACE)
        sup.tick()
        self.assertEqual((sup.state, sup.reason), ('SETUP', 'setup_cancelled'))
        self.assertIn('Type  retry', self.runner.views[-1])
        self.advance(3600)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)
        self.assertEqual(self.stored()['consecutive'] if os.path.exists(self.paths.state_file) else 0, 0)
        sup.retry()
        self.assertEqual(len(self.runner.prisms), 2)


class RestartPolicyTest(Base):
    def setUp(self):
        super().setUp()
        desktop.provision(self.paths, self.lock)
        make_world(self.paths, self.lock)

    def in_world(self, sup):
        pid, env = self.run_game(sup)
        self.ready(sup)
        self.assertEqual(sup.state, 'IN_WORLD')
        return pid, env

    def test_normal_start_goes_to_the_hub(self):
        sup = self.supervisor()
        sup.start()
        self.assertEqual(sup.state, 'STARTING')
        self.assertEqual(self.runner.prisms[0][0][-5:], ['/usr/bin/prismlauncher', '--launch', 'AresDesktop',
                                                         '--world', 'AresHub'])
        self.assertEqual(self.runner.views, [])
        self.in_world(sup)

    def test_crashes_restart_with_backoff_then_latch_recovery_that_survives_restarts(self):
        sup = self.supervisor()
        sup.start()
        nonces = []
        for crash in range(3):
            pid, env = self.in_world(sup)
            nonces.append(env['ARESOS_LAUNCH_NONCE'])
            self.advance(10)
            self.end_game(sup, pid, 1)
            if crash < 2:
                self.assertEqual((sup.state, sup.reason), ('STARTING', 'restarting'))
                self.assertEqual(len(self.runner.prisms), crash + 1)
                self.advance([5, 10][crash] - 0.5)
                sup.tick()
                self.assertEqual(len(self.runner.prisms), crash + 1)
                self.advance(0.5)
                sup.tick()
                self.assertEqual(len(self.runner.prisms), crash + 2)
        self.assertEqual(len(set(nonces)), 3)
        self.assertEqual([h[1] for h in self.runner.helpers], nonces)
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'crashes'))
        self.assertIn('stopped unexpectedly 3 times', self.runner.views[-1])
        self.assertIn('exit code 1', self.runner.views[-1])
        stored = self.stored()
        self.assertEqual((stored['latched'], stored['consecutive'], len(stored['failures'])), (True, 3, 3))
        self.advance(3600)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 3)
        # A new supervisor (keeper restart or reboot) stays in recovery.
        restarted = self.supervisor()
        restarted.start()
        self.assertEqual((restarted.state, restarted.reason), ('RECOVERY', 'crashes'))
        self.assertEqual(len(self.runner.prisms), 3)
        ok, reply = restarted.on_jvm_start({'instance': 'AresDesktop', 'java': self.lock['java']['path']})
        self.assertFalse(ok)
        self.assertIn('in recovery', reply['message'])
        restarted.retry()
        self.assertEqual(restarted.state, 'STARTING')
        self.assertEqual(len(self.runner.prisms), 4)
        stored = self.stored()
        self.assertEqual((stored['latched'], stored['consecutive'], stored['failures']), (False, 0, []))

    def test_ready_then_crash_cycles_four_minutes_apart_latch_on_the_third(self):
        sup = self.supervisor()
        sup.start()
        for cycle in range(3):
            pid, _ = self.in_world(sup)
            for _ in range(48):  # four minutes of healthy heartbeats
                self.advance(5)
                self.heartbeat(sup)
                sup.tick()
            self.end_game(sup, pid, 255)
            if cycle < 2:
                self.advance(30)
                sup.tick()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'crashes'))
        self.assertEqual(self.stored()['consecutive'], 3)
        self.assertLessEqual(len(self.stored()['failures']), 2)

    def test_thirty_healthy_minutes_reset_the_counts(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.end_game(sup, pid, 1)
        self.advance(5)
        sup.tick()
        pid, _ = self.in_world(sup)
        self.assertEqual(self.stored()['consecutive'], 1)
        for _ in range(int(desktop.HEALTHY_RESET // 5) - 1):
            self.advance(5)
            self.heartbeat(sup)
            sup.tick()
        self.assertEqual(self.stored()['consecutive'], 1)
        self.advance(5)
        self.heartbeat(sup)
        sup.tick()
        self.assertEqual((self.stored()['consecutive'], self.stored()['failures']), (0, []))

    def test_missing_heartbeats_restart_the_healthy_period(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.end_game(sup, pid, 1)
        self.advance(5)
        sup.tick()
        pid, _ = self.in_world(sup)
        for minute in range(40):
            for _ in range(12):
                self.advance(5)
                if minute != 20:
                    self.heartbeat(sup)
                sup.tick()
            if minute == 29:
                self.assertEqual(self.stored()['consecutive'], 1, 'a heartbeat gap must break the healthy period')
        self.assertEqual(self.stored()['consecutive'], 1)
        for _ in range(12 * 15):
            self.advance(5)
            self.heartbeat(sup)
            sup.tick()
        self.assertEqual(self.stored()['consecutive'], 0)

    def test_leaving_the_world_is_not_healthy(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.heartbeat(sup, ready=False)
        self.assertEqual(sup.state, 'STARTING')
        self.assertIsNone(sup.healthy_since)
        self.advance(desktop.START_TIMEOUT * 2)
        sup.tick()
        self.assertEqual(sup.state, 'STARTING', 'the start timeout applies only before the first ready world')

    def test_a_deliberate_quit_never_restarts_or_counts(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.end_game(sup, pid, 0)
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'quit', False))
        self.assertIn('Minecraft was closed', self.runner.views[-1])
        self.advance(3600)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)
        self.assertEqual(sup.persisted.consecutive, 0)
        # The owner may start it again from Prism himself.
        ok, _ = sup.on_jvm_start(self.jvm_request())
        self.assertTrue(ok)
        self.assertEqual(sup.state, 'STARTING')

    def test_a_kill_for_memory_latches_without_counting_or_restarting(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.end_game(sup, pid, -9)
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'killed'))
        self.assertTrue(self.stored()['latched'])
        self.assertEqual(self.stored()['consecutive'], 0)
        self.advance(3600)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)

    def test_a_whole_scope_death_without_a_report_latches_like_a_kill(self):
        # Review 1, finding 1 (JUDGMENT-CALL 10 updated): systemd-oomd or the kernel stopping the whole scope kills
        # the wrapper too, so no exit is reported. That is never a plain crash: latched, not counted, no restart.
        self.runner.scope = 'oom-kill'
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.runner.processes.pop(pid)
        sup.on_jvm_gone()
        sup.tick()
        self.assertEqual(sup.state, 'IN_WORLD')
        self.advance(desktop.EXIT_REPORT_WAIT)
        sup.tick()
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'killed', True))
        self.assertEqual((self.stored()['consecutive'], self.stored()['failures']), (0, []))
        self.assertIn('ended together; its scope ended with oom-kill', sup.persisted.detail)
        self.assertEqual(self.runner.scopes_asked, [f'aresos-game-{sup.launch.id}.scope'])
        self.advance(3600)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)

    def pass_time(self, sup, seconds, pressure):
        """Let `seconds` pass in sampling steps with the given pressure reading."""
        self.runner.pressure = pressure
        for _ in range(int(seconds // desktop.PRESSURE_SAMPLE)):
            self.advance(desktop.PRESSURE_SAMPLE)
            sup.tick()

    def test_a_kill_waits_for_a_whole_clear_minute_before_retry(self):
        # B5, review 2 finding 2: relaunch only after the owner's Retry and once memory pressure has stayed clear
        # for 60 s without a break. One low reading is not enough, and a spike or an unreadable value starts over.
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.end_game(sup, pid, -9)
        self.runner.pressure = 42.0
        ok, text = sup.retry()
        self.assertFalse(ok)
        self.assertIn('still under pressure (42%', text)
        self.runner.pressure = 3.0
        ok, text = sup.retry()
        self.assertFalse(ok, 'pressure that just dropped is not a clear minute')
        self.assertIn('free for 0 of the 60 seconds', text)
        self.pass_time(sup, 40, 3.0)
        self.pass_time(sup, 5, 20.0)  # a spike
        self.pass_time(sup, 30, 3.0)
        ok, text = sup.retry()
        self.assertFalse(ok, 'the spike started the minute again')
        self.pass_time(sup, 10, None)  # unreadable
        self.pass_time(sup, 55, 3.0)
        self.assertFalse(sup.retry()[0], 'an unreadable value started the minute again')
        self.assertTrue(self.stored()['latched'])
        self.assertEqual(len(self.runner.prisms), 1)
        self.pass_time(sup, 10, 3.0)
        ok, _ = sup.retry()
        self.assertTrue(ok)
        self.assertEqual(len(self.runner.prisms), 2)

    def test_a_supervisor_restart_never_skips_the_clear_minute(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.end_game(sup, pid, -9)
        self.pass_time(sup, 120, 0.0)
        again = self.supervisor()
        again.start()
        self.assertEqual((again.state, again.reason), ('RECOVERY', 'killed'))
        ok, text = again.retry()
        self.assertFalse(ok)
        self.assertIn('free for 0 of the 60 seconds', text)
        self.pass_time(again, 60, 0.0)
        self.assertTrue(again.retry()[0])

    def test_prism_killed_before_the_game_latches(self):
        sup = self.supervisor()
        sup.start()
        self.advance(30)
        sup.on_prism_exit(-9)
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'killed', True))
        self.advance(3600)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)

    def test_the_wrappers_exit_file_is_read_when_its_report_was_lost(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        os.makedirs(self.paths.run_dir, exist_ok=True)
        record = {'launch': sup.launch.id, 'pid': pid, 'ticks': pid * 7, 'status': 0}
        pathlib.Path(self.paths.exit_file).write_text(json.dumps(record))
        self.runner.processes.pop(pid)
        sup.on_jvm_gone()
        self.advance(desktop.EXIT_REPORT_WAIT)
        sup.tick()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'quit'))

    def test_an_exit_record_of_another_launch_or_process_is_ignored(self):
        # Review 1, finding 5: records bind to the launch ID and the process, not only a (reusable) PID.
        for record in ({'launch': 'other', 'status': 0}, {'pid': 1, 'status': 0}, {'ticks': 1, 'status': 0}):
            with self.subTest(record):
                self.runner = FakeRunner()
                sup = self.supervisor()
                desktop.Persisted().save(self.paths.state_file)
                sup = self.supervisor()
                sup.start()
                pid, _ = self.in_world(sup)
                full = {'launch': sup.launch.id, 'pid': pid, 'ticks': pid * 7, **record}
                os.makedirs(self.paths.run_dir, exist_ok=True)
                pathlib.Path(self.paths.exit_file).write_text(json.dumps(full))
                self.runner.processes.pop(pid)
                sup.on_jvm_gone()
                self.advance(desktop.EXIT_REPORT_WAIT)
                sup.tick()
                self.assertEqual(sup.reason, 'killed', record)

    def test_a_slow_start_shows_recovery_but_never_kills_the_game(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.run_game(sup)
        self.advance(desktop.START_TIMEOUT - 1)
        sup.tick()
        self.assertEqual(sup.state, 'STARTING')
        self.advance(1)
        sup.tick()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'slow_start'))
        self.assertIn('Minecraft is still running', self.runner.views[-1])
        self.assertIn(pid, self.runner.processes)
        self.assertFalse(sup.persisted.latched)
        self.ready(sup)
        self.assertEqual(sup.state, 'IN_WORLD')
        self.assertEqual(self.runner.closed_views, 1)

    def test_prism_ending_without_the_game_is_auth_required_and_waits(self):
        sup = self.supervisor()
        sup.start()
        self.advance(30)
        sup.on_prism_exit(1)
        self.advance(desktop.PRISM_GRACE)
        sup.tick()
        self.assertEqual(sup.state, 'AUTH_REQUIRED')
        self.assertIn('sign in again', self.runner.views[-1])
        self.advance(3600)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)
        self.assertEqual(sup.persisted.consecutive, 0)
        # Prism forwarded the launch to a Prism he had open: the game arrives late and is accepted.
        pid, env = self.run_game(sup)
        self.assertEqual(sup.state, 'STARTING')
        self.assertEqual(env['ARESOS_LAUNCH_NONCE'], self.runner.helpers[-1][1])

    def test_prism_failing_right_away_is_recovery_with_its_output(self):
        sup = self.supervisor()
        sup.start()
        sup.on_prism_output(b'Failed to start transient scope unit: Access denied\n')
        self.advance(0.5)
        sup.on_prism_exit(1)
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'prism_failed'))
        self.assertIn('Failed to start transient scope unit', self.runner.views[-1])
        self.assertFalse(sup.persisted.latched)

    def test_the_wrapper_is_refused_for_other_instances_java_or_a_second_game(self):
        sup = self.supervisor()
        sup.start()
        aside = self.paths.instance('AresDesktop') + '.aside-2026'
        for request in (self.jvm_request(instance='Gameplay'),
                        self.jvm_request(java='/usr/lib/jvm/java-21/bin/java'),
                        self.jvm_request(java=None),
                        self.jvm_request(instance_dir=aside),
                        self.jvm_request(cwd=self.paths.home),
                        self.jvm_request(instance_dir=None)):
            ok, reply = sup.on_jvm_start(request)
            self.assertFalse(ok, request)
        self.assertFalse(sup.persisted.latched)
        self.run_game(sup)
        ok, reply = sup.on_jvm_start(self.jvm_request())
        self.assertFalse(ok)
        self.assertIn('already running', reply['message'])

    def test_a_jvm_report_from_a_process_that_is_not_the_wrappers_child_is_refused(self):
        sup = self.supervisor()
        sup.start()
        ok, _ = sup.on_jvm_start(self.jvm_request())
        self.runner.processes[777] = (1, 5, '')
        self.assertEqual(sup.on_jvm_started(4000, 777)[0], False)
        self.assertIsNone(sup.launch.jvm_pid)

    def test_a_jvm_outside_its_memory_scope_is_refused(self):
        # Review 1, finding 4: in the real runner the JVM must be in this launch's game scope.
        self.runner.real = True
        with mock.patch.object(desktop, 'verify_inputs', return_value=[]):
            sup = self.supervisor()
            sup.start()
            ok, reply = sup.on_jvm_start(self.jvm_request())
        self.assertTrue(ok)
        prism_scope = f'0::/user.slice/user@1001.service/aresos.slice/aresos-desktop-{sup.launch.id}.scope\n'
        self.runner.processes[4001] = (4000, 1, prism_scope)
        ok, text = sup.on_jvm_started(4000, 4001)
        self.assertFalse(ok)
        self.assertIn('not in its memory scope', text)
        self.runner.processes[4001] = (4000, 1, f'0::/user.slice/user@1001.service/aresos.slice/{reply["unit"]}\n')
        self.assertEqual(sup.on_jvm_started(4000, 4001), (True, ''))

    def test_every_new_jvm_passes_the_same_gate(self):
        # Review 1, finding 6: a launch from Prism's own window, after the supervisor's own preflight, is checked
        # again: changed image inputs, a changed instance and a damaged or vanished world all refuse and latch.
        cases = (
            ('inputs', lambda: pathlib.Path(self.paths.share, 'mods/fabric-api.jar').write_bytes(b'changed')),
            ('instance', lambda: os.unlink(os.path.join(self.paths.instance('AresDesktop'), 'minecraft/mods'))),
            ('world_damaged', lambda: os.unlink(os.path.join(self.paths.worlds, 'AresHub/data/aresos/nether_home.dat'))),
            ('world_missing', lambda: shutil.rmtree(os.path.join(self.paths.worlds, 'AresHub'))),
        )
        for reason, damage in cases:
            with self.subTest(reason):
                shutil.rmtree(self.root / 'share')
                shutil.rmtree(self.paths.home)
                os.makedirs(self.paths.home)
                _, self.lock = fake_share(self.root / 'share')
                self.runner = FakeRunner()
                desktop.provision(self.paths, self.lock)
                make_world(self.paths, self.lock)
                sup = self.supervisor()
                sup.start()
                pid, _ = self.in_world(sup)
                self.end_game(sup, pid, 0)
                damage()
                ok, reply = sup.on_jvm_start(self.jvm_request())
                self.assertFalse(ok)
                self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', reason, True))
                self.assertIn('recovery', reply['message'])

    def test_a_held_desktop_lock_never_starts_a_second_game(self):
        self.runner.lock_held = True
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'locked'))
        self.assertEqual(self.runner.prisms, [])

    def test_the_game_inherits_nvidia_offload_only_with_the_driver(self):
        sup = self.supervisor(nvidia=True)
        sup.start()
        _, env = self.run_game(sup)
        self.assertEqual(env['__NV_PRIME_RENDER_OFFLOAD'], '1')
        self.assertEqual(env['__GLX_VENDOR_LIBRARY_NAME'], 'nvidia')

    def test_deadlines_never_spin_after_their_action(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.run_game(sup)
        self.advance(desktop.START_TIMEOUT)
        sup.tick()
        self.assertGreater(sup.deadline(), 0)
        self.end_game(sup, pid, 0)
        self.assertEqual(sup.pending(), [])
        self.assertEqual(sup.deadline(), 30.0)
        # A normally ended game is never mistaken for a lost hand-off later.
        self.advance(desktop.HANDOFF_TIMEOUT * 2)
        sup.tick()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'quit'))
        sup.on_wrapper_gone(sup.launch.id)
        self.assertEqual((sup.state, sup.reason, sup.persisted.consecutive), ('RECOVERY', 'quit', 0))

    def authorized(self):
        self.runner = FakeRunner()
        desktop.Persisted().save(self.paths.state_file)
        for name in (self.paths.exit_file, self.paths.runtime_file):
            if os.path.exists(name):
                os.unlink(name)
        sup = self.supervisor()
        sup.start()
        ok, reply = sup.on_jvm_start(self.jvm_request())
        self.assertTrue(ok)
        return sup, reply['launch']

    def write_start_record(self, launch, status=None, stopped=False, reason='Java could not be started'):
        pathlib.Path(self.paths.exit_file).write_text(json.dumps(
            {'launch': launch, 'pid': 77, 'ticks': None, 'status': status, 'stopped': stopped, 'reason': reason}))

    def test_a_death_before_the_hand_off_latches_like_a_kill(self):
        # Review 2, finding 1: a SIGKILL, or an end nobody explains, between authorization and the accepted PID is
        # treated exactly as after the hand-off: latched `killed`, not counted, never restarted by itself.
        self.runner.scope = 'oom-kill'
        for end in ('java killed', 'wrapper gone', 'hand-off timeout', 'killed, from the exit record'):
            with self.subTest(end):
                sup, launch = self.authorized()
                self.runner.scope = 'oom-kill'
                if end == 'java killed':
                    sup.on_jvm_failed(launch, 'Java ended before it was handed to AresOS', -9)
                elif end == 'wrapper gone':
                    sup.on_wrapper_gone(launch)
                    sup.tick()
                    self.advance(desktop.LOST_HANDOFF_WAIT - 1)
                    sup.tick()
                    self.assertEqual(sup.state, 'STARTING', 'it waits for the wrapper\'s own report')
                    self.advance(1)
                    sup.tick()
                elif end == 'hand-off timeout':
                    self.advance(desktop.HANDOFF_TIMEOUT)
                    sup.tick()
                else:
                    sup.on_wrapper_gone(launch)
                    self.write_start_record(launch, -9, reason='Java ended before it was handed to AresOS')
                    self.advance(desktop.LOST_HANDOFF_WAIT)
                    sup.tick()
                self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'killed', True))
                self.assertEqual((self.stored()['consecutive'], self.stored()['failures']), (0, []))
                self.assertIn('its scope ended with oom-kill', sup.persisted.detail)
                self.assertEqual(self.runner.scopes_asked, [f'aresos-game-{launch}.scope'])
                self.assertEqual(self.stored()['accounted'], launch)
                self.advance(3600)
                sup.tick()
                self.assertEqual(len(self.runner.prisms), 1, 'nothing restarts by itself')

    def test_a_failed_start_is_reported_and_counted_never_left_open(self):
        # Review 1, finding 7, with review 2 finding 1: a start that failed for a stated reason is counted like a
        # crash. That includes a report on a new connection after the first broke, and the wrapper's exit record.
        for end in ('jvm_failed', 'java ended by itself', 'report after the connection broke',
                    'exit record after a timeout', 'stopped by the wrapper, status ignored'):
            with self.subTest(end):
                sup, launch = self.authorized()
                if end == 'jvm_failed':
                    sup.on_jvm_failed(launch, 'Java could not be started: no such file')
                elif end == 'java ended by itself':
                    sup.on_jvm_failed(launch, 'Java ended before it was handed to AresOS', 1)
                    self.assertIn('Java ended with exit code 1', sup.detail)
                elif end == 'report after the connection broke':
                    sup.on_wrapper_gone(launch)
                    self.advance(desktop.EXIT_REPORT_WAIT / 2)
                    sup.tick()
                    sup.on_jvm_failed(launch, 'lost the supervisor during the hand-off; Java was stopped')
                elif end == 'exit record after a timeout':
                    self.write_start_record(launch)
                    self.advance(desktop.HANDOFF_TIMEOUT)
                    sup.tick()
                else:
                    sup.on_wrapper_gone(launch)
                    self.write_start_record(launch, -9, stopped=True, reason='lost the supervisor; Java was stopped')
                    self.advance(desktop.LOST_HANDOFF_WAIT)
                    sup.tick()
                self.assertEqual((sup.state, sup.reason), ('STARTING', 'restarting'))
                self.assertEqual(sup.persisted.consecutive, 1)
                self.advance(desktop.BACKOFF)
                sup.tick()
                self.assertEqual(len(self.runner.prisms), 2)
                # The automatic restart keeps an app in front (finding 11): the helper is told so.
                self.assertEqual(self.runner.helpers[-1][2].get('ARESOS_SHELL_KEEP_FOREGROUND'), '1')
                self.assertNotIn('ARESOS_SHELL_KEEP_FOREGROUND', self.runner.helpers[0][2])

    def test_a_lost_hand_off_answer_after_acceptance_is_a_failed_start(self):
        # Review 2, finding 3: the supervisor accepted the JVM, but the wrapper never got the answer, so it stopped
        # Java itself. That is a failed start (counted), not the owner's quit and not a kill.
        sup = self.supervisor()
        sup.start()
        pid, _ = self.run_game(sup)
        sup.on_jvm_failed(sup.launch.id, 'lost the supervisor during the hand-off; Java was stopped', -15, True)
        self.runner.processes.pop(pid)
        sup.on_jvm_gone()
        self.advance(desktop.EXIT_REPORT_WAIT)
        sup.tick()
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('STARTING', 'restarting', False))
        self.assertIn('lost the supervisor during the hand-off', sup.detail)
        self.assertEqual(self.stored()['consecutive'], 1)

    def test_a_sigkill_after_acceptance_with_a_lost_answer_latches(self):
        # Review 3, finding 1: the supervisor accepted the PID, its answer was lost, and Java was SIGKILLed before
        # the wrapper acted on the loss. The wrapper reports Java's own end (stopped=False): a kill, latched,
        # nothing counted, never restarted. The record the wrapper writes says the same.
        self.runner.scope = 'oom-kill'
        for path in ('report', 'exit record'):
            with self.subTest(path):
                self.runner = FakeRunner()
                self.runner.scope = 'oom-kill'
                desktop.Persisted().save(self.paths.state_file)
                sup = self.supervisor()
                sup.start()
                pid, _ = self.run_game(sup)
                if path == 'report':
                    sup.on_jvm_failed(sup.launch.id, 'lost the supervisor during the hand-off', -9, False)
                else:
                    pathlib.Path(self.paths.exit_file).write_text(json.dumps(
                        {'launch': sup.launch.id, 'pid': pid, 'ticks': pid * 7, 'status': -9, 'stopped': False,
                         'reason': 'lost the supervisor during the hand-off'}))
                self.runner.processes.pop(pid)
                sup.on_jvm_gone()
                self.advance(desktop.EXIT_REPORT_WAIT)
                sup.tick()
                self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'killed', True))
                self.assertEqual((self.stored()['consecutive'], self.stored()['failures']), (0, []))
                self.advance(3600)
                sup.tick()
                self.assertEqual(len(self.runner.prisms), 1, 'never restarted by itself')

    def test_a_late_report_still_explains_an_unexplained_start(self):
        # Review 3, finding 2: a report that arrives after the start was latched as unexplained still counts. An
        # explained end replaces the latch with one failed start; a kill stays latched.
        for stopped, status, expected, counted in ((True, -9, ('STARTING', 'restarting', False), 1),
                                                    (False, 1, ('STARTING', 'restarting', False), 1),
                                                    (False, -9, ('RECOVERY', 'killed', True), 0)):
            with self.subTest(stopped=stopped, status=status):
                sup, launch = self.authorized()
                sup.on_wrapper_gone(launch)
                self.advance(desktop.LOST_HANDOFF_WAIT)
                sup.tick()
                self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'killed', True))
                sup.on_jvm_failed(launch, 'lost the supervisor during the hand-off; Java was stopped', status, stopped)
                self.assertEqual((sup.state, sup.reason, sup.persisted.latched), expected)
                self.assertEqual(self.stored()['consecutive'], counted)
                sup.on_jvm_failed(launch, 'the same report again', status, stopped)
                self.assertEqual(self.stored()['consecutive'], counted, 'counted once')

    def test_the_wait_for_a_lost_hand_off_covers_the_wrappers_stop(self):
        # Review 3, finding 2: the supervisor waits at least as long as the wrapper may take to stop Java (SIGTERM,
        # then SIGKILL after STOP_WAIT) and report on a new connection.
        self.assertEqual((wrapper.STOP_WAIT, wrapper.REPORT_TIMEOUT),
                         (desktop.WRAPPER_STOP_WAIT, desktop.WRAPPER_REPORT_TIMEOUT))
        self.assertGreater(desktop.LOST_HANDOFF_WAIT, wrapper.STOP_WAIT + wrapper.REPORT_TIMEOUT)
        self.assertLess(desktop.LOST_HANDOFF_WAIT, desktop.HANDOFF_TIMEOUT)

    def test_a_gap_in_sampling_starts_the_clear_minute_again(self):
        # Review 3, finding 3: time nobody sampled is unknown, not clear.
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.end_game(sup, pid, -9)
        self.pass_time(sup, 10, 0.0)
        self.advance(70)  # the supervisor was stalled: no sampling ticks
        self.runner.pressure = 0.0
        ok, text = sup.retry()
        self.assertFalse(ok)
        self.assertIn('free for 0 of the 60 seconds', text)
        self.pass_time(sup, 60, 0.0)
        self.assertTrue(sup.retry()[0])

    def test_lost_heartbeats_show_without_touching_the_game(self):
        # Review 1, finding 10.
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        self.advance(desktop.HEARTBEAT_GAP)
        sup.tick()
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'unready', False))
        self.assertFalse(sup.launch.ready)
        self.assertIn('stopped reporting', self.runner.views[-1])
        self.assertIn(pid, self.runner.processes)
        self.heartbeat(sup)
        self.assertEqual(sup.state, 'IN_WORLD')

    def test_an_exhausted_helper_after_the_hub_was_ready_shows(self):
        sup = self.supervisor()
        sup.start()
        pid, _ = self.in_world(sup)
        for _ in range(desktop.HELPER_BUDGET[0]):
            self.runner.helper_alive = False
            sup.on_helper_exit(1)
            self.advance(desktop.HELPER_RESTART)
            sup.tick()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'helper'))
        self.assertFalse(sup.launch.ready)
        self.assertIn(pid, self.runner.processes)

    def test_a_damaged_hub_is_never_declared_ready(self):
        # Review 1, finding 2: the mod reports the marked world, but its home data is gone: not IN_WORLD.
        sup = self.supervisor()
        sup.start()
        pid, _ = self.run_game(sup)
        os.unlink(os.path.join(self.paths.worlds, 'AresHub/data/aresos/nether_home.dat'))
        self.ready(sup)
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'world_damaged', True))
        self.assertFalse(sup.launch.ready)
        self.assertIn(pid, self.runner.processes)

    def test_malformed_exact_home_data_is_refused_before_the_start_and_at_readiness(self):
        # Review 2, finding 5, through both gates: the preflight and the readiness report.
        home = saved({**HOME['data'][1], 'home': (COMPOUND, {
            'dimension': (STRING, 'minecraft:the nether'), 'position': (LIST, (DOUBLE, [1.5, 64.0, 2.5])),
            'yaw': (FLOAT, 0.0), 'pitch': (FLOAT, math.nan)})})
        shutil.rmtree(self.paths.worlds)
        world = make_world(self.paths, self.lock, home=home)
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'world_damaged'))
        self.assertIn('home dimension is not a valid identifier', sup.detail)
        shutil.rmtree(world)
        make_world(self.paths, self.lock)
        desktop.Persisted().save(self.paths.state_file)
        sup = self.supervisor()
        sup.start()
        pid, _ = self.run_game(sup)
        (world / 'data/aresos/nether_home.dat').write_bytes(nbt_file(home))
        self.ready(sup)
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'world_damaged', True))
        self.assertFalse(sup.launch.ready)
        self.assertIn(pid, self.runner.processes)


class RecoveryReasonsTest(Base):
    def test_a_missing_hub_that_existed_is_recovery_never_a_new_world(self):
        desktop.Persisted(hub_seen=True).save(self.paths.state_file)
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'world_missing'))
        self.assertEqual(self.runner.prisms, [])
        self.assertIn('never creates a replacement', self.runner.views[-1])
        self.assertTrue(self.stored()['latched'])
        sup.retry()
        self.assertEqual(sup.reason, 'world_missing')
        ok, _ = sup.forget_hub()
        self.assertTrue(ok)
        sup.retry()
        self.assertEqual(sup.state, 'SETUP')
        self.assertNotIn('--world', self.runner.prisms[-1][0])

    def test_forget_hub_refuses_while_the_hub_exists(self):
        make_world(self.paths, self.lock)
        sup = self.supervisor()
        sup.start()
        ok, text = sup.forget_hub()
        self.assertFalse(ok)
        self.assertIn('still exists', text)

    def test_a_damaged_hub_is_left_alone(self):
        world = make_world(self.paths, self.lock)
        (world / 'level.dat').write_bytes(b'garbage')
        before = sorted((p, p.read_bytes()) for p in world.rglob('*') if p.is_file())
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'world_damaged'))
        self.assertEqual(sorted((p, p.read_bytes()) for p in world.rglob('*') if p.is_file()), before)
        self.assertEqual(self.runner.prisms, [])

    def test_an_input_pin_mismatch_stops_before_anything_is_created(self):
        (pathlib.Path(self.paths.share) / 'libraries/fabric-loader-0.19.5.jar').write_bytes(b'tampered')
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'inputs'))
        self.assertIn('fabric-loader-0.19.5.jar does not match its pinned SHA-256', self.runner.views[-1])
        self.assertFalse(os.path.exists(self.paths.instances))
        self.assertEqual((self.runner.prisms, self.runner.helpers), ([], []))

    def test_a_changed_instance_stops_into_recovery_and_is_not_touched(self):
        desktop.provision(self.paths, self.lock)
        cfg = pathlib.Path(self.paths.instance('AresDesktop')) / 'instance.cfg'
        cfg.write_text(cfg.read_text().replace('JavaPath=/usr/lib/jvm/java-25-openjdk/bin/java', 'JavaPath=/x/java'))
        before = cfg.read_bytes()
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'instance'))
        self.assertIn('aresos-desktop reset-instance', self.runner.views[-1])
        self.assertEqual(cfg.read_bytes(), before)

    def test_an_unreadable_state_file_stops_into_recovery(self):
        os.makedirs(self.paths.state_dir)
        pathlib.Path(self.paths.state_file).write_text('not json')
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'state'))
        sup.retry()
        self.assertEqual(sup.state, 'SETUP')


class AdoptionTest(Base):
    def test_a_restarted_supervisor_watches_the_running_game_and_starts_nothing(self):
        desktop.provision(self.paths, self.lock)
        make_world(self.paths, self.lock)
        first = self.supervisor()
        first.start()
        pid, env = self.run_game(first)
        self.ready(first)
        prisms = len(self.runner.prisms)
        self.runner.helper_alive = False
        second = self.supervisor()
        second.start()
        self.assertEqual(second.state, 'STARTING')
        self.assertEqual(len(self.runner.prisms), prisms)
        self.assertEqual(self.runner.helpers[-1][:2], (first.instance, env['ARESOS_LAUNCH_NONCE']))
        self.ready(second)
        self.assertEqual(second.state, 'IN_WORLD')
        self.end_game(second, pid, 1)
        self.assertEqual((second.state, second.reason), ('STARTING', 'restarting'))

    def dead_launch(self, status=None, record=True, consecutive=0):
        # Review 1, finding 5: the previous supervisor recorded a running JVM; it ended while none ran.
        desktop.provision(self.paths, self.lock)
        make_world(self.paths, self.lock)
        desktop.Persisted(consecutive=consecutive, failures=[self.wall[0] - 1000] * consecutive).save(
            self.paths.state_file)
        os.makedirs(self.paths.run_dir, exist_ok=True)
        pathlib.Path(self.paths.runtime_file).write_text(json.dumps(
            {'instance': 'desk-old', 'nonce': 'n' * 32, 'launch': 'a', 'mode': 'hub', 'jvm_pid': 99, 'jvm_ticks': 1}))
        if record:
            pathlib.Path(self.paths.exit_file).write_text(json.dumps(
                {'launch': 'a', 'pid': 99, 'ticks': 1, 'status': status}))
        sup = self.supervisor()
        sup.start()
        return sup

    def test_a_game_that_ended_while_no_supervisor_ran_is_accounted_for_once(self):
        cases = {'normal exit': (0, True, ('RECOVERY', 'quit', False), 0),
                 'crash': (1, True, ('STARTING', 'restarting', False), 1),
                 'SIGKILL': (-9, True, ('RECOVERY', 'killed', True), 0),
                 'no exit record': (None, False, ('RECOVERY', 'killed', True), 0)}
        for name, (status, record, expected, counted) in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.paths.home)
                os.makedirs(self.paths.home)
                shutil.rmtree(self.paths.runtime)
                os.makedirs(self.paths.runtime)
                self.runner = FakeRunner()
                sup = self.dead_launch(status, record)
                self.assertEqual(sup.instance, 'desk-old')
                self.assertEqual((sup.state, sup.reason, sup.persisted.latched), expected)
                self.assertEqual(self.stored()['consecutive'], counted)
                self.assertEqual(self.stored()['accounted'], 'a')
                self.assertEqual(self.runner.prisms, [], 'nothing starts before the old launch is accounted for')
                # A second supervisor start never counts the same end again, and keeps its decision (finding 4).
                again = self.supervisor()
                again.start()
                self.assertEqual(self.stored()['consecutive'], counted)
                self.assertEqual((again.state, again.reason, again.persisted.latched), expected)
                self.assertEqual(self.runner.prisms, [])
        # A crash after two earlier failures latches, as if the supervisor had seen it.
        shutil.rmtree(self.paths.home)
        os.makedirs(self.paths.home)
        shutil.rmtree(self.paths.runtime)
        os.makedirs(self.paths.runtime)
        self.runner = FakeRunner()
        sup = self.dead_launch(1, True, consecutive=2)
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'crashes', True))

    def test_a_crash_accounted_after_downtime_restarts_after_its_backoff(self):
        sup = self.dead_launch(1, True)
        self.assertEqual(self.runner.prisms, [])
        self.advance(desktop.BACKOFF)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)
        self.assertNotEqual(sup.launch.nonce, 'n' * 32)

    def test_the_decision_after_an_end_survives_supervisor_restarts(self):
        # Review 2, finding 4: his quit stays stopped across two supervisor restarts; a pending crash restart keeps
        # its deadline; a new session (another instance, as after a reboot) starts the hub as usual.
        desktop.provision(self.paths, self.lock)
        make_world(self.paths, self.lock)
        first = self.supervisor()
        first.start()
        pid, _ = self.run_game(first)
        self.ready(first)
        self.end_game(first, pid, 0)
        self.assertEqual((first.state, first.reason), ('RECOVERY', 'quit'))
        for _ in range(2):
            again = self.supervisor()
            again.start()
            self.assertEqual((again.state, again.reason, again.persisted.latched), ('RECOVERY', 'quit', False))
            self.assertEqual(len(self.runner.prisms), 1, 'nothing starts after his quit')
        self.assertTrue(again.retry()[0])
        self.assertEqual(len(self.runner.prisms), 2)
        pid, _ = self.run_game(again)
        self.ready(again)
        self.end_game(again, pid, 1)
        self.assertEqual((again.state, again.reason), ('STARTING', 'restarting'))
        self.advance(desktop.BACKOFF - 2)
        restarted = self.supervisor()
        restarted.start()
        self.assertEqual((restarted.state, restarted.reason), ('STARTING', 'restarting'))
        self.assertEqual(len(self.runner.prisms), 2)
        self.advance(1)
        restarted.tick()
        self.assertEqual(len(self.runner.prisms), 2, 'the deadline is kept, not restarted from zero or skipped')
        self.advance(1)
        restarted.tick()
        self.assertEqual(len(self.runner.prisms), 3)
        self.assertEqual(self.stored()['consecutive'], 1, 'the crash was counted once')
        # A new session: the quit of the last one does not keep the hub closed.
        pid, _ = self.run_game(restarted)
        self.end_game(restarted, pid, 0)
        os.unlink(self.paths.runtime_file)
        fresh = self.supervisor()
        fresh.start()
        self.assertEqual(fresh.state, 'STARTING')
        self.assertEqual(len(self.runner.prisms), 4)

    def test_a_start_authorized_before_a_supervisor_restart_is_accounted_for(self):
        # Review 2, findings 1 and 3: the previous supervisor authorized a JVM that never reported to it.
        cases = {'no record, nothing running': (None, False, ('RECOVERY', 'killed', True), 0),
                 'killed, from the record': ({'status': -9, 'reason': 'Java ended'}, False,
                                             ('RECOVERY', 'killed', True), 0),
                 'failed, from the record': ({'status': None, 'reason': 'Java could not be started'}, False,
                                             ('STARTING', 'restarting', False), 1),
                 'its wrapper still runs': (None, True, ('STARTING', None, False), 0)}
        for name, (record, held, expected, counted) in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.paths.home)
                os.makedirs(self.paths.home)
                shutil.rmtree(self.paths.runtime)
                os.makedirs(self.paths.run_dir)
                desktop.provision(self.paths, self.lock)
                make_world(self.paths, self.lock)
                self.runner = FakeRunner()
                self.runner.lock_held = held
                pathlib.Path(self.paths.runtime_file).write_text(json.dumps(
                    {'instance': 'desk-old', 'nonce': 'n' * 32, 'launch': 'b', 'mode': 'hub', 'accepted': True,
                     'jvm_pid': None, 'jvm_ticks': None}))
                if record:
                    pathlib.Path(self.paths.exit_file).write_text(json.dumps(dict(record, launch='b', pid=5)))
                sup = self.supervisor()
                sup.start()
                self.assertEqual((sup.state, sup.reason, sup.persisted.latched), expected)
                self.assertEqual(self.stored()['consecutive'] if os.path.exists(self.paths.state_file) else 0,
                                 counted)
                self.assertEqual(self.runner.prisms, [])
                if held:
                    # The wrapper reports on a new connection, naming the launch.
                    sup.on_jvm_failed('b', 'lost the supervisor during the hand-off; Java was stopped')
                    self.assertEqual((sup.state, sup.reason), ('STARTING', 'restarting'))

    def test_an_adopted_game_that_never_becomes_ready_shows_after_the_timeout(self):
        # Review 1, finding 10: adoption keeps a bounded readiness check.
        desktop.provision(self.paths, self.lock)
        make_world(self.paths, self.lock)
        self.runner.processes[99] = (98, 1, '')
        os.makedirs(self.paths.run_dir, exist_ok=True)
        pathlib.Path(self.paths.runtime_file).write_text(json.dumps(
            {'instance': 'desk-old', 'nonce': 'n' * 32, 'launch': 'a', 'mode': 'hub', 'jvm_pid': 99, 'jvm_ticks': 1}))
        sup = self.supervisor()
        sup.start()
        self.assertEqual(sup.state, 'STARTING')
        self.advance(desktop.START_TIMEOUT)
        sup.tick()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'slow_start'))
        self.assertIn(99, self.runner.processes)


class HelperTest(Base):
    def test_the_helper_restarts_with_the_same_nonce_within_a_budget(self):
        sup = self.supervisor()
        sup.start()
        nonce = sup.launch.nonce
        for _ in range(desktop.HELPER_BUDGET[0] - 1):
            self.runner.helper_alive = False
            sup.on_helper_exit(1)
            self.advance(desktop.HELPER_RESTART)
            sup.tick()
        self.assertEqual([h[1] for h in self.runner.helpers], [nonce] * desktop.HELPER_BUDGET[0])
        self.runner.helper_alive = False
        sup.on_helper_exit(1)
        self.advance(desktop.HELPER_RESTART)
        sup.tick()
        self.assertEqual(len(self.runner.helpers), desktop.HELPER_BUDGET[0])

    def test_status_from_an_old_launch_is_ignored(self):
        sup = self.supervisor()
        sup.start()
        self.ready(sup)
        self.assertEqual(sup.state, 'SETUP')


class MessagesTest(Base):
    def test_every_view_tells_him_what_to_do(self):
        persisted = desktop.Persisted(consecutive=3)
        for state, reason in (('SETUP', 'setup_cancelled'), ('SETUP', 'setup_closed'), ('SETUP', 'setup_crashed'),
                              ('AUTH_REQUIRED', 'auth'), ('RECOVERY', 'quit'), ('RECOVERY', 'prism_failed'),
                              ('RECOVERY', 'crashes'), ('RECOVERY', 'killed'), ('RECOVERY', 'world_missing'),
                              ('RECOVERY', 'world_damaged'), ('RECOVERY', 'state'), ('RECOVERY', 'locked')):
            text = desktop.message(state, reason, 'detail', self.lock, persisted)
            self.assertIn('retry', text, (state, reason))
        for reason in ('instance', 'inputs', 'slow_start'):
            self.assertTrue(desktop.message('RECOVERY', reason, 'detail', self.lock, persisted).strip())
        self.assertLessEqual(max(len(line) for state in ('SETUP',)
                                 for line in desktop.message(state, 'setup', '', self.lock, persisted).splitlines()),
                             104)


class ImageBuildTest(unittest.TestCase):
    """Review 1, finding 3: every image build builds the mod jar from its own commit and requires its pin. Run
    42854477440 found the JDK stage calling curl, which the pinned JDK image does not have: now the source stage
    (pinned base, with curl) fetches the commit and the JDK stage runs only Gradle, with only the image's tools."""

    BUILDER = next(mod['builder'] for mod in LOCK['mods'] if mod['file'] == 'aresos.jar')

    def test_the_containerfile_fetches_in_the_base_builds_in_the_pinned_jdk_and_configure_checks_it(self):
        containerfile = (ROOT / 'os/Containerfile').read_text()
        stages = [line.split() for line in containerfile.splitlines() if line.startswith('FROM ')]
        base = json.loads((ROOT / 'os/manifest/base.json').read_text())['reference']
        # The workflow checks the first FROM against the pinned base; it stays first.
        self.assertEqual(stages, [['FROM', base, 'AS', 'packages'], ['FROM', base, 'AS', 'source'],
                                  ['FROM', self.BUILDER, 'AS', 'mod'], ['FROM', 'packages', 'AS', 'aresos']])
        source_stage = containerfile.split(' AS source\n', 1)[1].split('\nFROM ', 1)[0]
        self.assertIn('RUN bash /tmp/aresos-mod/build.sh source "$ARESOS_SOURCE_REVISION" /source', source_stage)
        mod_stage = containerfile.split(' AS mod\n', 1)[1].split('\nFROM ', 1)[0]
        # Only mod/ crosses into the JDK stage, which runs only Gradle.
        self.assertEqual([line for line in mod_stage.splitlines() if line.startswith(('COPY', 'RUN'))],
                         ['COPY build.sh /tmp/aresos-mod/build.sh',
                          'COPY --from=source /source/mod /tmp/aresos-mod/mod',
                          'RUN bash /tmp/aresos-mod/build.sh mod /tmp/aresos-mod/mod /out "$ARESOS_SOURCE_REVISION"'])
        final = containerfile.split('FROM packages AS aresos', 1)[1]
        copy = final.index('COPY --from=mod /out/aresos.jar /tmp/aresos/minecraft/aresos.jar')
        self.assertLess(copy, final.index('build.sh configure'))
        build = (ROOT / 'os/build.sh').read_text()
        configure = build.split('if [[ $1 == packages ]]', 1)[1]
        self.assertIn("assert digest == mod['sha256']", configure)
        self.assertIn("MOD_JAR_PINNED", configure)
        self.assertNotIn('aresos.jar', configure.split('\nfi\n', 1)[0])

    def test_check_build_and_the_pin_renewal_use_the_same_stages_as_every_image_build(self):
        script = (ROOT / 'os/ci/check-build.sh').read_text()
        build = script.split('build)', 1)[1].split(';;', 1)[0]
        self.assertNotIn('build-mod.sh', build)
        self.assertIn('test ! -e os/minecraft/aresos.jar', build)
        self.assertIn('--build-arg "ARESOS_SOURCE_REVISION=$revision"', build)
        self.assertIn('^MOD_SOURCE $revision [0-9a-f]{64}', build)
        self.assertIn('MOD_JAR_BUILT [0-9a-f]{64} from $revision', build)
        renew = (ROOT / 'os/ci/build-mod.sh').read_text()
        self.assertIn('sudo podman build --no-cache --target mod --format=oci --build-arg '
                      '"ARESOS_SOURCE_REVISION=$revision"', renew)
        self.assertIn('--file os/Containerfile os', renew)
        self.assertIn('python3 os/ci/builder-tools.py --check', renew)
        self.assertNotIn('podman run', renew, 'no second way to build the jar')

    def test_the_builder_tool_list_is_the_pinned_image(self):
        lines = (ROOT / 'os/minecraft/builder-tools.txt').read_text().splitlines()
        self.assertEqual(lines[0], f'# builder {self.BUILDER}', 'a new builder pin needs os/ci/builder-tools.py')
        tools = set(lines[3:])
        self.assertIn('java', tools)
        self.assertTrue({'curl', 'wget'}.isdisjoint(tools), 'the JDK image fetches nothing by itself')

    @unittest.skipUnless(LINUX, 'runs build.sh with the builder image\'s tools')
    def test_the_jdk_stage_needs_only_what_the_builder_image_has(self):
        # The mod stage's real script and the real gradlew, with a PATH of exactly the image's executables (from
        # minecraft/builder-tools.txt, linked to this system's copies). Java itself is a stand-in in JAVA_HOME.
        lines = (ROOT / 'os/minecraft/builder-tools.txt').read_text().splitlines()
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            tools = root / 'bin'
            tools.mkdir()
            for name in lines[3:]:
                host = shutil.which(name, path='/usr/bin:/bin:/usr/sbin:/sbin')
                if host and name != 'java':
                    (tools / name).symlink_to(host)
            jdk = root / 'jdk/bin'
            jdk.mkdir(parents=True)
            (jdk / 'java').write_text('#!/bin/sh\nprintf "%s\\n" "$@" > ../java-args\n'
                                      'mkdir -p build/libs\nprintf jar-bytes > build/libs/aresos-0.1.0.jar\n')
            (jdk / 'java').chmod(0o755)
            src = root / 'mod'
            (src / 'gradle/wrapper').mkdir(parents=True)
            shutil.copy(ROOT / 'mod/gradlew', src / 'gradlew')
            for name in ('gradle-wrapper.jar', 'gradle-wrapper.properties'):
                shutil.copy(ROOT / 'mod/gradle/wrapper' / name, src / 'gradle/wrapper' / name)
            (src / 'gradle.properties').write_text('version=0.1.0\n')
            env = {'PATH': str(tools), 'JAVA_HOME': str(root / 'jdk'), 'HOME': str(root)}
            bash = str(tools / 'bash')
            revision = 'cd' * 20
            result = subprocess.run([bash, str(ROOT / 'os/build.sh'), 'mod', str(src), str(root / 'out'), revision],
                                    env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f'MOD_JAR_BUILT {hashlib.sha256(b"jar-bytes").hexdigest()} from {revision}', result.stdout)
            args = (root / 'java-args').read_text().splitlines()
            # The real gradlew ran to Java: it starts the wrapper jar with the task.
            self.assertEqual(args[args.index('-jar') + 1], str(src / 'gradle/wrapper/gradle-wrapper.jar'))
            self.assertEqual(args[-3:], ['--no-daemon', '--console=plain', 'jar'])
            # The same sandbox refuses what the image cannot do: fetching (run 42854477440's failure).
            fetch = subprocess.run([bash, str(ROOT / 'os/build.sh'), 'source', revision, str(root / 'source')],
                                   env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(fetch.returncode, 127, fetch.stderr)
            self.assertIn('curl: command not found', fetch.stderr)

    @unittest.skipUnless(LINUX, 'runs build.sh with a stand-in for the network')
    def test_the_source_stage_fetches_the_named_commit_and_keeps_only_mod(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            revision = 'ab' * 20
            tree = root / f'AresOS-{revision}'
            (tree / 'mod/gradle/wrapper').mkdir(parents=True)
            (tree / 'mod/gradlew').write_text('#!/bin/sh\n')
            (tree / 'mod/gradlew').chmod(0o755)
            (tree / 'os').mkdir()
            (tree / 'os/unrelated').write_text('not extracted')
            archive = root / 'source.tar.gz'
            subprocess.run(['tar', '-czf', str(archive), '-C', str(root), tree.name], check=True)
            stubs = root / 'bin'
            stubs.mkdir()
            # A stand-in for the network only: the pinned base has the real curl (build.sh packages uses it too).
            (stubs / 'curl').write_text('#!/bin/sh\nfor a; do case $prev in -o) out=$a;; esac; prev=$a; '
                                        f'url=$a; done\necho "$@" > {root}/curl-args\ncp {archive} "$out"\n')
            (stubs / 'curl').chmod(0o755)
            env = dict(os.environ, PATH=f'{stubs}:/usr/bin:/bin')
            result = subprocess.run(['bash', str(ROOT / 'os/build.sh'), 'source', revision, str(root / 'out')],
                                    env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'curl-args').read_text().split(),
                             ['-fsSL', '--proto', '=https', '--tlsv1.2', '--retry', '3', '-o',
                              (root / 'curl-args').read_text().split()[7],
                              f'https://codeload.github.com/Ares-Empire/AresOS/tar.gz/{revision}'])
            self.assertEqual(sorted(p.name for p in (root / 'out').iterdir()), ['mod'])
            self.assertTrue(os.access(root / 'out/mod/gradlew', os.X_OK))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertIn(f'MOD_SOURCE {revision} {digest}', result.stdout)
            for mode in ('source', 'mod'):
                for bad in ('unrecorded', 'main', 'ab' * 19, 'AB' * 20):
                    args = [bad, str(root / 'out2')] if mode == 'source' else [str(root / 'out/mod'), str(root / 'o'),
                                                                                bad]
                    refused = subprocess.run(['bash', str(ROOT / 'os/build.sh'), mode, *args], env=env,
                                             capture_output=True, text=True, timeout=60)
                    self.assertNotEqual(refused.returncode, 0, (mode, bad))
                    self.assertIn('exact commit', refused.stderr)


class MemoryProtectionFilesTest(unittest.TestCase):
    """Review 1, finding 9: the session (compositor, supervisor, recovery terminal) and every ancestor are protected;
    systemd-oomd avoids the session scope. The VM check reads the effective values."""

    def test_drop_ins(self):
        units = CONFIG / 'usr/lib/systemd/system'
        for slice_ in ('user.slice', 'user-1001.slice'):
            lines = [l for l in (units / f'{slice_}.d/50-aresos-recovery.conf').read_text().splitlines()
                     if l and not l.startswith('#')]
            self.assertEqual(lines, ['[Slice]', 'MemoryLow=1G'], slice_)
        lines = [l for l in (units / 'session-.scope.d/50-aresos-recovery.conf').read_text().splitlines()
                 if l and not l.startswith('#')]
        self.assertEqual(lines, ['[Scope]', 'MemoryLow=1G', 'ManagedOOMPreference=avoid'])
        checks = (ROOT / 'os/ci/overlay/checks.py').read_text()
        for name in ('def memory_protection', 'def memory_pressure', 'def desktop_jvm'):
            self.assertIn(name, checks)


@unittest.skipUnless(LINUX, 'runs stand-in pressure sources')
class PressureCheckTest(unittest.TestCase):
    """Review 2, finding 9: the VM check passes only with real, proven pressure (checks.py, run in the VM)."""

    def setUp(self):
        sys.path[:0] = [str(ROOT / 'os/ci'), str(ROOT / 'os/ci/overlay')]
        self.addCleanup(lambda: [sys.path.remove(p) for p in (str(ROOT / 'os/ci'), str(ROOT / 'os/ci/overlay'))])
        import checks
        self.checks = checks
        alive = {'labwc': (10, '0::/s'), 'supervisor': (11, '0::/s'), 'keeper': (12, '0::/s'),
                 'recovery terminal': (13, '0::/s')}
        self.evidence = {'kernel': ['Out of memory: Killed process 1 (python3)'], 'oomd': [], 'unit': '',
                         'proven': True}
        for name, value in (('survivors', lambda: dict(alive)), ('timed_status', lambda: 0.1),
                            ('desktop_status', lambda: {'state': 'RECOVERY'}),
                            ('oom_evidence', lambda pid: self.evidence), ('PRESSURE_MIN_MIB', 128)):
            patch = mock.patch.object(checks, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def source(self, script):
        patch = mock.patch.object(self.checks, 'pressure_command', lambda: ['/bin/sh', '-c', script])
        patch.start()
        self.addCleanup(patch.stop)

    SCOPE = 'echo "SCOPE $$ 0::/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-ci-pressure.scope"; '
    GROW = 'for n in 64 128 192 256; do echo "ALLOCATED $n"; sleep 0.6; done; '

    def test_real_pressure_passes(self):
        self.source(self.SCOPE + self.GROW + 'kill -9 $$')
        result = self.checks.memory_pressure()
        self.assertEqual((result['allocated_mib'], result['hog_exit']), (256, -9))
        self.assertTrue(result['status_seconds'])

    def test_anything_short_of_proven_pressure_fails(self):
        cases = {
            'the launcher fails': ('echo "Failed to start transient scope unit: Access denied" >&2; exit 1',
                                   'never ran in its scope'),
            'another scope': ('echo "SCOPE $$ 0::/user.slice/session-2.scope"; ' + self.GROW + 'kill -9 $$',
                              'ran elsewhere'),
            'python fails at once': (self.SCOPE + 'echo "Traceback"; exit 1', 'ended before it made pressure'),
            'ends by itself': (self.SCOPE + self.GROW + 'exit 1', 'was not killed'),
        }
        for name, (script, expected) in cases.items():
            with self.subTest(name):
                self.source(script)
                with self.assertRaises(AssertionError) as caught:
                    self.checks.memory_pressure()
                self.assertIn(expected, str(caught.exception))
        with self.subTest('killed without OOM evidence'):
            self.source(self.SCOPE + self.GROW + 'kill -9 $$')
            self.evidence = {'kernel': [], 'oomd': [], 'unit': 'Result=success', 'proven': False}
            with self.assertRaises(AssertionError) as caught:
                self.checks.memory_pressure()
            self.assertIn('no kernel or systemd-oomd record', str(caught.exception))
        with self.subTest('the supervisor does not answer'):
            self.evidence = dict(self.evidence, proven=True)
            with mock.patch.object(self.checks, 'timed_status', lambda: None):
                with self.assertRaises(AssertionError) as caught:
                    self.checks.memory_pressure()
            self.assertIn('did not answer', str(caught.exception))


class SessionFilesTest(unittest.TestCase):
    def test_autostart_runs_the_supervisor_instead_of_a_terminal(self):
        lines = [l for l in (CONFIG / 'usr/share/aresos/labwc/autostart').read_text().splitlines()
                 if l and not l.startswith('#')]
        self.assertEqual(lines, ['/usr/libexec/kf6/polkit-kde-authentication-agent-1 &',
                                 '/usr/libexec/aresos-desktop session &'])

    def test_recovery_terminal_shortcut_is_kept(self):
        rc = (CONFIG / 'usr/share/aresos/labwc/rc.xml').read_text()
        self.assertIn('<keybind key="W-C-Escape"><action name="Execute" command="/usr/bin/aresos-terminal --recovery" />',
                      rc)
        self.assertIn('<windowRule identifier="aresos-desktop" serverDecoration="no"><action name="Maximize" />', rc)

    def test_supervisor_and_wrapper_run_absolute_commands_only(self):
        for name in ('aresos-desktop', 'aresos-desktop-java'):
            text = (CONFIG / 'usr/libexec' / name).read_text()
            self.assertTrue(text.startswith('#!/usr/bin/python3\n'), name)
            self.assertNotIn('shell=True', text)
            self.assertNotIn('execvp', text)
        for command in desktop.VIEW_COMMAND + [desktop.PRISM, desktop.SYSTEMD_RUN, desktop.HELPER, desktop.SELF,
                                               desktop.WRAPPER]:
            if command.startswith('-'):
                continue
            self.assertTrue(command.startswith('/usr/'), command)
        self.assertEqual(desktop.prism_command(LOCK, 'x')[0], '/usr/bin/systemd-run')

    def test_the_view_is_set_up_like_the_recovery_terminal(self):
        rc = (CONFIG / 'usr/share/aresos/desktop-view.bashrc').read_text()
        self.assertIn('. /usr/share/aresos/bashrc\n', rc)
        self.assertNotIn('.bashrc"', rc)
        self.assertIn('retry() { /usr/libexec/aresos-desktop retry; }', rc)
        source = (CONFIG / 'usr/libexec/aresos-desktop').read_text()
        self.assertIn("env['ARESOS_TERMINAL'] = 'recovery'", source)


# ---------------------------------------------------------------- Linux: the real wrapper and the real loop


FAKE_JAVA = textwrap.dedent('''\
    #!/usr/bin/python3
    import json, os, signal, sys, threading, time
    if os.environ.get('FAKE_JAVA_TERM') == 'ignore':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if os.environ.get('FAKE_JAVA_KILL_AFTER'):
        threading.Timer(float(os.environ['FAKE_JAVA_KILL_AFTER']), lambda: os.kill(os.getpid(), 9)).start()
    record = os.environ.get('FAKE_JAVA_RECORD')
    if record:
        with open('/proc/self/cgroup') as source:
            cgroup = source.read()
        with open(record, 'w') as output:
            line = [l for l in cgroup.splitlines() if l.startswith('0::')][0]
            try:
                high = open('/sys/fs/cgroup' + line[3:] + '/memory.high').read().strip()
            except OSError:
                high = None
            json.dump({'argv': sys.argv, 'env': dict(os.environ), 'stdin': sys.stdin.readline(), 'cgroup': cgroup,
                       'pid': os.getpid(), 'memory_high': high}, output)
    time.sleep(float(os.environ.get('FAKE_JAVA_SLEEP', '0')))
    sys.exit(int(os.environ.get('FAKE_JAVA_EXIT', '0')))
''')


@unittest.skipUnless(LINUX, 'Unix sockets, pidfds and prctl')
class WrapperTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        self.run_dir = self.root / 'aresos'
        self.run_dir.mkdir(mode=0o700)
        self.java = self.root / 'java'
        self.java.write_text(FAKE_JAVA)
        self.java.chmod(0o755)
        self.requests = []
        self.reply = {'ok': True, 'launch': 'L1', 'env': {'ARESOS_LAUNCH_NONCE': 'n' * 32,
                                                          'ARESOS_DESKTOP_INSTANCE': 'desk-1',
                                                          'PATH': desktop.SYSTEM_PATH},
                      'scope': [], 'unit': None}
        self.started_reply = {'ok': True}
        self.drop_started = False
        self.drop_delay = 0.0
        self.connections = 0
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(str(self.run_dir / 'desktop.sock'))
        self.listener.listen(4)
        self.serving = threading.Thread(target=self.serve, daemon=True)
        self.serving.start()

    def serve(self):
        while True:
            try:
                conn, _ = self.listener.accept()
            except OSError:
                return
            self.connections += 1
            number = self.connections
            with conn:
                buffer, open_ = b'', True
                while open_:
                    data = conn.recv(65536)
                    if not data:
                        break
                    buffer += data
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        request = json.loads(line)
                        self.requests.append(dict(request, connection=number))
                        if request['op'] == 'jvm_started' and self.drop_started:
                            time.sleep(self.drop_delay)
                            open_ = False  # the hand-off breaks: no answer, the connection closes
                            break
                        reply = {'jvm_start': self.reply, 'jvm_started': self.started_reply}.get(request['op'],
                                                                                                 {'ok': True})
                        conn.sendall((json.dumps(reply) + '\n').encode())

    def tearDown(self):
        self.listener.close()

    def wrap(self, *args, env=None, stdin=b'launch\n'):
        environ = {'XDG_RUNTIME_DIR': str(self.root), 'INST_ID': 'AresDesktop', 'HOME': str(self.root),
                   'INST_DIR': str(self.root / 'instance'),
                   'FAKE_JAVA_RECORD': str(self.root / 'record.json'), 'PATH': '/usr/lib/prismlauncher/bin:/usr/bin',
                   'LD_PRELOAD': '', 'QT_PLUGIN_PATH': '/usr/lib/prismlauncher/shared/lib/plugins'}
        environ.update(env or {})
        return subprocess.run([sys.executable, str(CONFIG / 'usr/libexec/aresos-desktop-java'), str(self.java),
                               *args], env=environ, input=stdin, capture_output=True, timeout=60, cwd=self.root)

    def test_the_game_gets_the_supervisors_environment_and_its_exit_is_reported(self):
        result = self.wrap('-Xmx3072m', 'org.prismlauncher.EntryPoint', env={'FAKE_JAVA_EXIT': '3'})
        self.assertEqual(result.returncode, 3, result.stderr)
        record = json.loads((self.root / 'record.json').read_text())
        self.assertEqual(record['argv'][1:], ['-Xmx3072m', 'org.prismlauncher.EntryPoint'])
        self.assertEqual(record['stdin'], 'launch\n')
        self.assertEqual(record['env']['ARESOS_LAUNCH_NONCE'], 'n' * 32)
        self.assertEqual(record['env']['PATH'], desktop.SYSTEM_PATH)
        self.assertNotIn('QT_PLUGIN_PATH', record['env'])
        self.assertNotIn('LD_PRELOAD', record['env'])
        ops = [r['op'] for r in self.requests]
        self.assertEqual(ops, ['jvm_start', 'jvm_started', 'jvm_exited'])
        start, started, exited = self.requests
        self.assertEqual((start['java'], start['instance']), (str(self.java), 'AresDesktop'))
        self.assertEqual((start['instance_dir'], start['cwd']), (str(self.root / 'instance'), str(self.root)))
        self.assertEqual(started['pid'], exited['pid'])
        self.assertEqual((exited['status'], exited['launch']), (3, 'L1'))
        record = json.loads((self.run_dir / 'desktop-exit.json').read_text())
        self.assertEqual((record['launch'], record['pid'], record['status']), ('L1', started['pid'], 3))
        self.assertIsInstance(record['ticks'], int)

    def test_a_start_that_fails_is_reported(self):
        # Review 1, finding 7: Java that cannot start, and a JVM the supervisor refuses, end as jvm_failed.
        self.java.chmod(0o644)
        result = self.wrap()
        self.assertEqual(result.returncode, wrapper.REFUSED, result.stderr)
        self.assertEqual([r['op'] for r in self.requests], ['jvm_start', 'jvm_failed'])
        self.assertIn('Java could not be started', self.requests[-1]['reason'])
        self.java.chmod(0o755)
        self.requests.clear()
        self.started_reply = {'ok': False, 'message': 'the JVM is not in its memory scope x'}
        result = self.wrap(env={'FAKE_JAVA_SLEEP': '30'})
        self.assertEqual(result.returncode, wrapper.REFUSED, result.stderr)
        self.assertEqual([r['op'] for r in self.requests], ['jvm_start', 'jvm_started', 'jvm_failed'])
        self.assertIn('refused the game: the JVM is not in its memory scope', self.requests[-1]['reason'])
        game = self.requests[1]['pid']
        self.assertFalse(os.path.exists(f'/proc/{game}') and
                         pathlib.Path(f'/proc/{game}/stat').read_text().split(')')[1].split()[0] != 'Z')

    def test_java_killed_before_the_hand_off_is_reported_with_its_status(self):
        # Review 2, finding 1: Java dies (SIGKILL) while the wrapper waits for its scope, before jvm_started.
        killer = self.root / 'fake-systemd-run'
        killer.write_text('#!/bin/sh\nkill -9 $$\n')
        killer.chmod(0o755)
        self.reply = dict(self.reply, scope=[str(killer)], unit='aresos-game-L1.scope')
        result = self.wrap()
        self.assertEqual(result.returncode, wrapper.REFUSED, result.stderr)
        self.assertEqual([r['op'] for r in self.requests], ['jvm_start', 'jvm_failed'])
        self.assertEqual((self.requests[-1]['status'], self.requests[-1]['launch']), (-9, 'L1'))
        self.assertIs(self.requests[-1]['stopped'], False, 'Java ended by itself')
        record = json.loads((self.run_dir / 'desktop-exit.json').read_text())
        self.assertEqual((record['launch'], record['status'], record['stopped']), ('L1', -9, False))

    def test_a_lost_hand_off_stops_java_and_reports_on_a_new_connection(self):
        # Review 2, finding 3: the connection breaks during jvm_started while Java runs. Java must not be left
        # running untracked: the wrapper stops it and reports on a new connection, naming the launch.
        self.drop_started = True
        started = time.monotonic()
        result = self.wrap(env={'FAKE_JAVA_SLEEP': '60'})
        self.assertEqual(result.returncode, wrapper.REFUSED, result.stderr)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual([r['op'] for r in self.requests], ['jvm_start', 'jvm_started', 'jvm_failed'])
        failed = self.requests[-1]
        self.assertNotEqual(failed['connection'], self.requests[0]['connection'])
        self.assertEqual(failed['launch'], 'L1')
        self.assertIn('lost the supervisor during the hand-off', failed['reason'])
        self.assertIs(failed['stopped'], True, 'the wrapper says it stopped Java itself')
        game = self.requests[1]['pid']
        self.assertFalse(os.path.exists(f'/proc/{game}') and
                         pathlib.Path(f'/proc/{game}/stat').read_text().split(')')[1].split()[0] != 'Z')
        record = json.loads((self.run_dir / 'desktop-exit.json').read_text())
        self.assertEqual((record['launch'], record['pid'], record['stopped']), ('L1', game, True))
        import fcntl
        lock = os.open(self.run_dir / 'desktop.lock', os.O_RDWR)
        self.addCleanup(os.close, lock)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # nothing holds the desktop lock any more

    def test_java_killed_after_a_lost_answer_reports_its_own_end(self):
        # Review 3, finding 1: the answer to jvm_started never comes, and Java is SIGKILLed before the wrapper notices.
        self.drop_started, self.drop_delay = True, 1.5
        result = self.wrap(env={'FAKE_JAVA_SLEEP': '30', 'FAKE_JAVA_KILL_AFTER': '0.3'})
        self.assertEqual(result.returncode, wrapper.REFUSED, result.stderr)
        failed = self.requests[-1]
        self.assertEqual((failed['op'], failed['status'], failed['stopped']), ('jvm_failed', -9, False))
        record = json.loads((self.run_dir / 'desktop-exit.json').read_text())
        self.assertEqual((record['status'], record['stopped']), (-9, False))

    def test_java_that_ignores_sigterm_is_killed_and_reported_as_stopped(self):
        # Review 3, finding 2: the wrapper's stop window (SIGTERM, SIGKILL after STOP_WAIT), then its report. The
        # answer is lost a moment after jvm_started, once the stand-in has set its SIGTERM handling.
        self.drop_started, self.drop_delay = True, 1.0
        started = time.monotonic()
        result = self.wrap(env={'FAKE_JAVA_SLEEP': '60', 'FAKE_JAVA_TERM': 'ignore'})
        took = time.monotonic() - started
        self.assertEqual(result.returncode, wrapper.REFUSED, result.stderr)
        self.assertGreaterEqual(took, wrapper.STOP_WAIT)
        self.assertLess(took, desktop.LOST_HANDOFF_WAIT, 'the report comes within the supervisor\'s wait')
        failed = self.requests[-1]
        self.assertEqual((failed['op'], failed['status'], failed['stopped']), ('jvm_failed', -9, True))
        game = self.requests[1]['pid']
        self.assertFalse(os.path.exists(f'/proc/{game}') and
                         pathlib.Path(f'/proc/{game}/stat').read_text().split(')')[1].split()[0] != 'Z')

    def test_a_scope_that_is_not_usable_is_refused_before_java_runs(self):
        for scope, unit in (('systemd-run', None), (['relative/systemd-run', '--'], 'u.scope'), ([], 'u.scope'),
                            (['/usr/bin/systemd-run', '--'], None)):
            with self.subTest(scope=scope, unit=unit):
                self.requests.clear()
                self.reply = dict(self.reply, scope=scope, unit=unit)
                result = self.wrap()
                self.assertEqual(result.returncode, wrapper.REFUSED)
                self.assertFalse((self.root / 'record.json').exists())
                self.assertEqual(self.requests[-1]['op'], 'jvm_failed')

    def test_the_game_waits_for_its_scope_and_is_reported_only_inside_it(self):
        # A stand-in for systemd-run that never puts Java into the named scope: the wrapper must not report it.
        fake = self.root / 'fake-systemd-run'
        fake.write_text('#!/bin/sh\nwhile [ "$1" != "--" ]; do shift; done\nshift\nexec "$@"\n')
        fake.chmod(0o755)
        self.reply = dict(self.reply, scope=[str(fake), '--unit=aresos-game-L1.scope', '--'],
                          unit='aresos-game-L1.scope')
        started = time.monotonic()
        result = self.wrap(env={'FAKE_JAVA_SLEEP': '30'})
        self.assertEqual(result.returncode, wrapper.REFUSED, result.stderr)
        self.assertLess(time.monotonic() - started, 25)
        self.assertEqual([r['op'] for r in self.requests], ['jvm_start', 'jvm_failed'])
        self.assertIn('did not reach its scope aresos-game-L1.scope', self.requests[-1]['reason'])

    def test_the_real_jvm_runs_in_its_own_scope_with_the_memory_target(self):
        # Review 1, finding 4: Prism (here: this test) runs outside any desktop scope; Java still lands in the
        # game's scope with MemoryHigh=5G, because the wrapper starts it there. Needs a user systemd manager.
        bus = f'unix:path=/run/user/{os.getuid()}/bus'
        probe_env = {'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': str(self.root), 'DBUS_SESSION_BUS_ADDRESS': bus}
        try:
            probe = subprocess.run(['/usr/bin/systemd-run', '--user', '--scope', '--quiet', '/bin/true'],
                                   env=probe_env, capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            probe = None
        if probe is None or probe.returncode != 0:
            self.skipTest('no user systemd manager reachable here (CI runner); WSL and the image have one')
        launch = 'pkg23t' + os.urandom(3).hex()
        self.reply = dict(self.reply, launch=launch, scope=desktop.game_scope(launch), unit=desktop.game_unit(launch))
        # Java lives a moment, so it is handed over before it ends (one that ends first is a failed start).
        result = self.wrap(env={'DBUS_SESSION_BUS_ADDRESS': bus, 'FAKE_JAVA_SLEEP': '2', 'FAKE_JAVA_EXIT': '0'})
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((self.root / 'record.json').read_text())
        line = next(l for l in record['cgroup'].splitlines() if l.startswith('0::'))
        self.assertTrue(line.endswith(f'/aresos.slice/aresos-game-{launch}.scope'), line)
        self.assertEqual(record['memory_high'], str(5 * 1024 ** 3))
        started = next(r for r in self.requests if r['op'] == 'jvm_started')
        self.assertEqual(started['pid'], record['pid'], 'the reported PID is the JVM itself, inside the scope')

    def test_a_refused_launch_never_runs_java(self):
        self.reply = {'ok': False, 'message': 'The AresOS desktop is in recovery.'}
        result = self.wrap()
        self.assertEqual(result.returncode, wrapper.REFUSED)
        self.assertIn(b'in recovery', result.stderr)
        self.assertFalse((self.root / 'record.json').exists())

    def test_without_the_supervisor_the_desktop_does_not_start(self):
        self.listener.close()
        os.unlink(self.run_dir / 'desktop.sock')
        result = self.wrap()
        self.assertEqual(result.returncode, wrapper.REFUSED)
        self.assertIn(b'only through its session supervisor', result.stderr)
        self.assertFalse((self.root / 'record.json').exists())

    def test_the_lock_is_held_until_the_jvm_ends_so_a_second_desktop_cannot_start(self):
        first = subprocess.Popen([sys.executable, str(CONFIG / 'usr/libexec/aresos-desktop-java'), str(self.java)],
                                 env={'XDG_RUNTIME_DIR': str(self.root), 'INST_ID': 'AresDesktop',
                                      'FAKE_JAVA_SLEEP': '4'}, stdin=subprocess.DEVNULL)
        self.addCleanup(first.kill)
        deadline = time.monotonic() + 10
        while len([r for r in self.requests if r['op'] == 'jvm_started']) < 1 and time.monotonic() < deadline:
            time.sleep(0.05)
        second = self.wrap()
        self.assertEqual(second.returncode, wrapper.BUSY)
        self.assertIn(b'already running', second.stderr)
        first.wait(10)
        self.assertEqual(self.wrap().returncode, 0)

    def test_killing_the_wrapper_kills_the_game(self):
        wrapper_process = subprocess.Popen([sys.executable, str(CONFIG / 'usr/libexec/aresos-desktop-java'),
                                            str(self.java)],
                                           env={'XDG_RUNTIME_DIR': str(self.root), 'INST_ID': 'AresDesktop',
                                                'FAKE_JAVA_SLEEP': '60'}, stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + 10
        while not [r for r in self.requests if r['op'] == 'jvm_started'] and time.monotonic() < deadline:
            time.sleep(0.05)
        game = next(r for r in self.requests if r['op'] == 'jvm_started')['pid']
        wrapper_process.kill()
        wrapper_process.wait()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                state = pathlib.Path(f'/proc/{game}/stat').read_text().split(')')[1].split()[0]
            except (FileNotFoundError, ProcessLookupError):
                break
            if state == 'Z':
                break
            time.sleep(0.05)
        else:
            self.fail('the game outlived its wrapper')

    def test_terminate_is_forwarded_to_the_game(self):
        process = subprocess.Popen([sys.executable, str(CONFIG / 'usr/libexec/aresos-desktop-java'), str(self.java)],
                                   env={'XDG_RUNTIME_DIR': str(self.root), 'INST_ID': 'AresDesktop',
                                        'FAKE_JAVA_SLEEP': '60'}, stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + 10
        while not [r for r in self.requests if r['op'] == 'jvm_started'] and time.monotonic() < deadline:
            time.sleep(0.05)
        process.terminate()
        self.assertEqual(process.wait(10), 128 + 15)
        self.assertEqual([r for r in self.requests if r['op'] == 'jvm_exited'][-1]['status'], -15)


FAKE_PRISM = textwrap.dedent('''\
    #!/usr/bin/python3
    # Stands in for systemd-run + Prism: runs the instance's wrapper with the fake Java, like Prism does.
    import os, subprocess, sys
    log = os.environ['FAKE_LOG']
    with open(log, 'a') as output:
        output.write(' '.join(sys.argv[1:]) + '\\n')
    mode = open(os.environ['FAKE_PRISM_MODE']).read().strip()
    if mode == 'no-game':
        sys.exit(1)
    env = dict(os.environ, INST_ID='AresDesktop', INST_DIR=os.environ['FAKE_INSTANCE'])
    result = subprocess.run([os.environ['FAKE_WRAPPER'], os.environ['FAKE_JAVA'], 'org.prismlauncher.EntryPoint'],
                            env=env, input=b'launch\\n', cwd=os.path.join(os.environ['FAKE_INSTANCE'], 'minecraft'))
    sys.exit(0 if result.returncode == 0 else 1)
''')

FAKE_HELPER = textwrap.dedent('''\
    #!/usr/bin/python3
    # Stands in for aresos-shell: reports the mod's world_ready and heartbeats on the status pipe.
    import json, os, signal, sys, time
    fd = int(os.environ['ARESOS_SHELL_STATUS_FD'])
    with open(os.environ['FAKE_LOG'], 'a') as output:
        output.write('helper ' + os.environ['ARESOS_DESKTOP_INSTANCE'] + ' ' + os.environ['ARESOS_LAUNCH_NONCE'] + '\\n')
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    ready_file = os.environ['FAKE_READY']
    while True:
        if os.path.exists(ready_file):
            os.write(fd, (json.dumps({'event': 'world_ready', 'world': 'AresHub'}) + '\\n').encode())
        time.sleep(0.1)
''')

FAKE_VIEW = '#!/bin/sh\nexec sleep 300\n'


@unittest.skipUnless(LINUX, 'Unix sockets, pidfds and prctl')
class LoopTest(Base):
    """The real event loop, socket, pipes and pidfds, with stand-ins for Prism, the helper, Java and foot."""

    def setUp(self):
        super().setUp()
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        self.log = self.root / 'log.txt'
        self.mode = self.root / 'prism-mode'
        self.mode.write_text('game')
        self.ready_file = self.root / 'ready'
        self.exit_file = self.root / 'java-exit'
        java = bin_dir / 'java'
        # Each fake JVM waits for its own stop file, named after its PID.
        # Flag files change how the stand-in reacts: .term-delay (SIGTERM ends it 3 s later), .term-ignore,
        # .kill (it SIGKILLs itself 0.3 s after starting).
        java.write_text('#!/bin/sh\necho $$ >> "$FAKE_JAVA_STOP.pids"\n'
                        '[ -e "$FAKE_JAVA_STOP.term-delay" ] && trap \'sleep 3; exit 143\' TERM\n'
                        '[ -e "$FAKE_JAVA_STOP.term-ignore" ] && trap \'\' TERM\n'
                        '[ -e "$FAKE_JAVA_STOP.kill" ] && { (sleep 0.3; kill -9 $$) & }\nread line\n'
                        'while [ ! -e "$FAKE_JAVA_STOP.$$" ]; do sleep 0.05; done\n'
                        'exit "$(cat "$FAKE_JAVA_STOP.$$")"\n')
        for name, text in (('prism', FAKE_PRISM), ('helper', FAKE_HELPER), ('view', FAKE_VIEW)):
            (bin_dir / name).write_text(text)
        for path in bin_dir.iterdir():
            path.chmod(0o755)
        self.lock['java']['path'] = str(java)
        pathlib.Path(self.paths.share, desktop.LOCK_NAME).write_text(json.dumps(self.lock))
        env = {'HOME': self.paths.home, 'XDG_RUNTIME_DIR': self.paths.runtime, 'FAKE_LOG': str(self.log),
               'FAKE_PRISM_MODE': str(self.mode), 'FAKE_READY': str(self.ready_file),
               'FAKE_WRAPPER': str(CONFIG / 'usr/libexec/aresos-desktop-java'), 'FAKE_JAVA': str(java),
               'FAKE_JAVA_STOP': str(self.exit_file), 'PATH': '/usr/bin:/bin',
               'FAKE_INSTANCE': self.paths.instance('AresDesktop')}
        patches = [mock.patch.object(desktop, 'HELPER', str(bin_dir / 'helper')),
                   mock.patch.object(desktop, 'VIEW_COMMAND', [str(bin_dir / 'view')]),
                   mock.patch.object(desktop, 'prism_command',
                                     lambda lock, launch_id, world=None: [str(bin_dir / 'prism'), '--launch',
                                                                         'AresDesktop'] + (['--world', world]
                                                                                           if world else [])),
                   mock.patch.object(desktop, 'BACKOFF', 0.2), mock.patch.object(desktop, 'PRISM_GRACE', 0.5),
                   # No user systemd here: the wrapper runs Java directly (the scope itself is tested separately).
                   mock.patch.object(desktop, 'game_scope', lambda launch_id: [])]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        desktop.provision(self.paths, self.lock)
        make_world(self.paths, self.lock)
        self.loop = desktop.Loop(self.paths, self.lock, environ=env, nvidia=False)
        self.loop.runner.real = False
        self.prisms = []
        start_prism = self.loop.runner.start_prism

        def recorded(command, env):
            process = start_prism(command, env)
            self.prisms.append(process)
            return process
        self.loop.runner.start_prism = recorded
        self.thread = threading.Thread(target=self.loop.run, daemon=True)
        self.addCleanup(self.stop)

    def end_jvm(self, status):
        pid = self.loop.supervisor.launch.jvm_pid
        pathlib.Path(f'{self.exit_file}.{pid}').write_text(str(status))
        return pid

    def stop(self):
        self.loop.stopping = True
        launch = self.loop.supervisor.launch
        if launch is not None and launch.jvm_pid is not None:
            self.end_jvm(0)
        self.thread.join(10)
        # The supervisor leaves a running game alone when it stops; the test reaps its stand-ins (own sessions).
        for process in self.prisms:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, 9)
                except ProcessLookupError:
                    pass
            process.wait(10)
            if process.stdout is not None:
                process.stdout.close()

    def wait(self, condition, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.05)
        self.fail(f'timed out; state {self.loop.supervisor.state} {self.loop.supervisor.reason}; '
                  f'log {self.log.read_text() if self.log.exists() else ""}')

    def test_crash_restart_latch_and_retry_through_the_real_loop(self):
        sup = self.loop.supervisor
        self.thread.start()
        for crash in range(3):
            self.wait(lambda: sup.launch is not None and sup.launch.jvm_pid is not None)
            self.ready_file.touch()
            self.wait(lambda: sup.state == 'IN_WORLD')
            nonce = sup.launch.nonce
            self.assertIn(f'helper {sup.instance} {nonce}', self.log.read_text())
            self.ready_file.unlink()
            pid = self.end_jvm(2)
            self.wait(lambda: sup.launch.jvm_pid != pid)
            if crash < 2:
                self.wait(lambda: sup.launch.jvm_pid is not None and sup.launch.jvm_pid != pid)
        self.wait(lambda: sup.state == 'RECOVERY')
        self.assertEqual(sup.reason, 'crashes')
        self.assertIn('exit code 2', sup.detail)
        status = desktop.request(self.paths, {'op': 'status'})
        self.assertEqual((status['state'], status['latched'], status['consecutive']), ('RECOVERY', True, 3))
        launches = [l for l in self.log.read_text().splitlines() if l.startswith('--launch')]
        self.assertEqual(launches, ['--launch AresDesktop --world AresHub'] * 3)
        reply = desktop.request(self.paths, {'op': 'retry'})
        self.assertTrue(reply['ok'])
        self.wait(lambda: sup.launch.jvm_pid is not None)
        self.assertFalse(sup.persisted.latched)

    def test_a_whole_scope_kill_latches_and_nothing_restarts(self):
        # Review 1, finding 1: kill the wrapper and Java together, as systemd-oomd or the kernel does to a whole
        # scope. No exit is reported; the supervisor latches recovery and never starts Minecraft again by itself.
        sup = self.loop.supervisor
        self.thread.start()
        self.wait(lambda: sup.launch is not None and sup.launch.jvm_pid is not None)
        jvm = sup.launch.jvm_pid
        wrapper_pid = int(pathlib.Path(f'/proc/{jvm}/stat').read_text().rsplit(')', 1)[1].split()[1])
        for pid in (wrapper_pid, jvm):
            os.kill(pid, 9)
        self.wait(lambda: (sup.state, sup.reason) == ('RECOVERY', 'killed'))  # latch() persists, then enters
        self.assertTrue(sup.persisted.latched)
        self.assertIn('ended together', sup.persisted.detail)
        time.sleep(1.5)  # far beyond the patched 0.2 s backoff
        launches = [l for l in self.log.read_text().splitlines() if l.startswith('--launch')]
        self.assertEqual(len(launches), 1)
        self.assertEqual(desktop.request(self.paths, {'op': 'status'})['consecutive'], 0)

    def kill_before_the_hand_off(self, script):
        # Review 2, finding 1, through the real loop and wrapper: SIGKILL right after authorization, before the PID
        # is accepted. A stand-in for systemd-run kills Java (and maybe the wrapper) before Java reaches its scope.
        killer = self.root / 'killer'
        killer.write_text(script)
        killer.chmod(0o755)
        sup = self.loop.supervisor
        with mock.patch.object(desktop, 'game_scope', lambda launch_id: [str(killer)]):
            self.thread.start()
            # The supervisor first waits LOST_HANDOFF_WAIT for a report from a wrapper that may still be stopping Java.
            self.wait(lambda: (sup.state, sup.reason) == ('RECOVERY', 'killed'), timeout=desktop.LOST_HANDOFF_WAIT + 20)
            self.assertTrue(sup.persisted.latched)
            time.sleep(1.5)  # far beyond the patched 0.2 s backoff
        self.assertEqual(len([l for l in self.log.read_text().splitlines() if l.startswith('--launch')]), 1)
        self.assertEqual(desktop.request(self.paths, {'op': 'status'})['consecutive'], 0)
        return sup

    def test_java_killed_before_the_hand_off_latches(self):
        sup = self.kill_before_the_hand_off('#!/bin/sh\nkill -9 $$\n')
        self.assertIn('killed by SIGKILL while it started', sup.persisted.detail)

    def test_java_and_wrapper_killed_before_the_hand_off_latch(self):
        sup = self.kill_before_the_hand_off('#!/bin/sh\nkill -9 $PPID\nkill -9 $$\n')
        self.assertIn('ended before the game was handed to AresOS', sup.persisted.detail)

    def test_a_lost_hand_off_never_leaves_java_running(self):
        # Review 2, finding 3, through the real loop: the supervisor's connection to the wrapper breaks while it
        # handles jvm_started, with Java alive. Java is stopped, the lock is free, and the start counts as failed.
        self.lost_hand_off()

    def test_a_lost_hand_off_with_a_java_that_delays_sigterm(self):
        # Review 3, finding 2: Java takes 3 s to stop, longer than the old 2 s wait: still one failed start.
        pathlib.Path(f'{self.exit_file}.term-delay').touch()
        self.lost_hand_off()

    def test_a_lost_hand_off_with_a_java_that_ignores_sigterm(self):
        # Review 3, finding 2: Java ignores SIGTERM; the wrapper kills it after its stop window and still reports.
        pathlib.Path(f'{self.exit_file}.term-ignore').touch()
        self.lost_hand_off()

    def test_a_kill_after_acceptance_with_a_lost_answer_latches(self):
        # Review 3, finding 1, through the real loop: the supervisor accepts the PID, its answer is lost (the loop
        # handles jvm_started, then drops the connection a moment later), and Java is SIGKILLed meanwhile.
        pathlib.Path(f'{self.exit_file}.kill').touch()
        handle = desktop.Loop.handle

        def losing(loop, peer, line):
            answer = handle(loop, peer, line)
            if json.loads(line).get('op') == 'jvm_started':
                time.sleep(1.0)
                loop.drop(peer)
            return answer
        sup = self.loop.supervisor
        with mock.patch.object(desktop.Loop, 'handle', losing):
            self.thread.start()
            self.wait(lambda: (sup.state, sup.reason) == ('RECOVERY', 'killed'), timeout=30)
            self.assertTrue(sup.persisted.latched)
            time.sleep(1.5)  # far beyond the patched 0.2 s backoff
        self.assertEqual(len([l for l in self.log.read_text().splitlines() if l.startswith('--launch')]), 1)
        self.assertEqual(desktop.request(self.paths, {'op': 'status'})['consecutive'], 0)

    def lost_hand_off(self):
        handle = desktop.Loop.handle

        def breaking(loop, peer, line):
            if json.loads(line).get('op') == 'jvm_started':
                time.sleep(0.5)  # the stand-in Java has recorded its PID and set its SIGTERM handling by now
                loop.drop(peer)
                return {'ok': True}
            return handle(loop, peer, line)
        sup = self.loop.supervisor
        # A long backoff keeps the counted failure in view (no automatic restart during the test).
        with mock.patch.object(desktop.Loop, 'handle', breaking), mock.patch.object(desktop, 'BACKOFF', 60):
            self.thread.start()
            self.wait(lambda: (sup.state, sup.reason) == ('STARTING', 'restarting'), timeout=40)
            self.assertIn('lost the supervisor during the hand-off', sup.detail)
            self.assertEqual((sup.persisted.consecutive, sup.persisted.latched), (1, False))
            java = int(pathlib.Path(f'{self.exit_file}.pids').read_text().split()[0])

            def gone():
                try:
                    return pathlib.Path(f'/proc/{java}/stat').read_text().split(')')[1].split()[0] == 'Z'
                except OSError:
                    return True
            self.wait(gone)
            self.wait(lambda: not self.loop.runner.jvm_lock_held())

    def test_prism_without_a_game_waits_in_auth_required(self):
        self.mode.write_text('no-game')
        patch = mock.patch.object(desktop, 'EARLY_PRISM_FAILURE', 0.0)
        patch.start()
        self.addCleanup(patch.stop)
        sup = self.loop.supervisor
        self.thread.start()
        self.wait(lambda: sup.state == 'AUTH_REQUIRED')
        time.sleep(1)
        self.assertEqual(len([l for l in self.log.read_text().splitlines() if l.startswith('--launch')]), 1)

    def test_other_users_and_malformed_requests_are_refused(self):
        self.thread.start()
        self.wait(lambda: os.path.exists(self.paths.socket))
        self.assertEqual(oct(os.stat(self.paths.socket).st_mode & 0o777), '0o600')
        self.assertEqual(oct(os.stat(self.paths.run_dir).st_mode & 0o777), '0o700')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.paths.socket)
        sock.sendall(b'not json\n{"op": "jvm_start", "pid": 1}\n{"op": "nothing"}\n')
        replies = []
        buffer = b''
        while len(replies) < 3:
            buffer += sock.recv(65536)
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                replies.append(json.loads(line))
        sock.close()
        self.assertEqual([r.get('error') for r in replies], ['malformed', 'not_authorized', 'unknown_operation'])
        # A request that hits an unexpected error answers 'internal'; the supervisor keeps running.
        with mock.patch.object(self.loop.supervisor, 'status', side_effect=RuntimeError('boom')):
            self.assertEqual(desktop.request(self.paths, {'op': 'status'})['error'], 'internal')
        self.assertTrue(self.thread.is_alive())
        self.assertTrue(desktop.request(self.paths, {'op': 'status'})['ok'])


if __name__ == '__main__':
    unittest.main()
