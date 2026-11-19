#!/usr/bin/python3
# DEVELOPMENT AID of package 25 (the real-game check): the rig's own checks, without a game.
"""python3 -B reviews/25-guardian/rig/test_rig.py

No game, no display, no input. The region reader reads a region file made here. Then check.py's two checks run
against a stand-in game (os/tests/test_aresos_guardian_loop.py's, which speaks the lifecycle channel and ends with
143 on SIGTERM) started through the rig's java wrapper in a real, disposable user scope: the environment check, the
close alone, and the path (the real supervisor under `env -i` adopts it; `save`, `stop`). Setting a block and reading
the disk are stand-ins here: they need the game. Everything lives in a temporary folder and ends with the test."""
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / 'os/tests')]
import check  # noqa: E402
import region  # noqa: E402
import test_aresos_desktop as base  # noqa: E402
import test_aresos_guardian_loop as loop  # noqa: E402


def text(value):
    return struct.pack('>H', len(value)) + value.encode()


def region_file(path, names, data):
    """One chunk (0, 0) whose section Y=5 has this palette and these packed longs."""
    palette = b''.join(b'\x08' + text('Name') + text(name) + b'\x00' for name in names)
    states = (b'\x09' + text('palette') + b'\x0a' + struct.pack('>i', len(names)) + palette
              + b'\x0c' + text('data') + struct.pack('>i', len(data)) + struct.pack(f'>{len(data)}q', *data) + b'\x00')
    section = b'\x01' + text('Y') + b'\x05' + b'\x0a' + text('block_states') + states + b'\x00'
    chunk = zlib.compress(b'\x0a' + text('') + b'\x09' + text('sections') + b'\x0a' + struct.pack('>i', 1) + section
                          + b'\x00')
    path.write_bytes(struct.pack('>I', (2 << 8) | 1) + bytes(8188) + struct.pack('>IB', len(chunk) + 1, 2) + chunk)


class RegionTest(unittest.TestCase):
    def test_a_block_is_read_from_its_packed_place(self):
        with tempfile.TemporaryDirectory() as folder:
            world = pathlib.Path(folder)
            (world / 'region').mkdir()
            # 17 names need 5 bits: 12 entries in each long. Block (3, 90, 2) is entry (10 << 8) | (2 << 4) | 3.
            index = (10 << 8) | (2 << 4) | 3
            longs = [0] * (4096 // 12 + 1)
            longs[index // 12] = 16 << (5 * (index % 12))
            names = ['minecraft:air'] + [f'minecraft:filler_{n}' for n in range(15)] + ['minecraft:glass']
            region_file(world / 'region/r.0.0.mca', names, longs)
            self.assertEqual(region.block(world, 3, 90, 2), 'minecraft:glass')
            self.assertEqual(region.block(world, 4, 90, 2), 'minecraft:air')
            self.assertEqual(region.block(world, 3, 200, 2), 'minecraft:air')  # no such section
            self.assertIsNone(region.block(world, 40, 90, 2))  # no such chunk


@unittest.skipUnless(os.environ.get('XDG_RUNTIME_DIR') and shutil.which('systemd-run'), 'a user systemd')
class ChecksTest(unittest.TestCase):
    def setUp(self):
        # Under the runtime folder: the supervisor's socket path must stay short.
        self.root = pathlib.Path(tempfile.mkdtemp(prefix='pkg25-test-', dir=os.environ['XDG_RUNTIME_DIR']))
        self.folder = self.root / 'pkg25/rigs/t'
        self.folder.mkdir(parents=True)
        self.unit = f'pkg25-game-test-{os.getpid()}-{time.monotonic_ns()}.scope'
        self.wrapper = None
        self.addCleanup(self.clean)
        self.place, self.on_disk = check.place, check.on_disk
        check.place, check.on_disk = (lambda rig, number: time.monotonic_ns()), (lambda rig, number: True)

    def clean(self):
        check.place, check.on_disk = self.place, self.on_disk
        subprocess.run(['systemctl', '--user', 'stop', self.unit], capture_output=True, timeout=30, check=False)
        if self.wrapper is not None:
            self.wrapper.stdin.close()
            self.wrapper.wait(20)
        check.sweep(self.folder)
        shutil.rmtree(self.root, ignore_errors=True)

    def launch(self, mode):
        """The stand-in game through the rig's java wrapper, as Gradle starts the real one."""
        fake = self.root / 'bin'
        (self.root / 'control').mkdir()
        fake.mkdir()
        (fake / 'java').write_text(loop.GAME)
        (fake / 'java').chmod(0o755)
        (fake / 'config.json').write_text(json.dumps({'control': str(self.root / 'control')}))
        check.prepare(self.folder, mode, self.unit, '512M', str(fake / 'java'))
        (self.folder / 'jdk/bin').mkdir(parents=True)
        shutil.copy(HERE / 'java-wrapper.py', self.folder / 'jdk/bin/java')
        (self.folder / 'jdk/bin/java').chmod(0o755)
        identity = dict(line.split('=', 1) for line in (self.folder / 'private/identity').read_text().split())
        environment = {'PATH': '/usr/bin:/bin', 'HOME': str(self.root), **identity,
                       'XDG_RUNTIME_DIR': os.environ['XDG_RUNTIME_DIR']}  # the session's: the wrapper replaces it
        self.wrapper = subprocess.Popen([str(self.folder / 'jdk/bin/java'), '-cp', 'x',
                                         'net.fabricmc.devlaunchinjector.Main'], env=environment,
                                        stdin=subprocess.PIPE)
        self.wrapper.stdin.write(b'launch\n')
        self.wrapper.stdin.flush()
        rig = check.Rig(self.folder)
        game = check.wait_for(lambda: rig.read('jvm.json'), 20)
        self.assertTrue(game, 'the stand-in game did not reach its scope')
        return rig, game

    def test_the_close_alone_ends_the_runs_own_game_and_reads_its_real_status(self):
        rig, game = self.launch('close')
        check.check_environment(rig, game['pid'], gate=True)
        self.assertTrue(rig.result['environment']['runtime_folder_is_the_runs_own'])
        check.close_alone(rig, game, 1, 0)
        close = rig.result['close']
        self.assertEqual((close['exited'], close['exit_status'], close['save_asked_before']), (True, 143, False))
        self.assertEqual(self.wrapper.wait(20), 143)

    def test_a_game_with_another_runtime_folder_is_refused_before_anything_is_asked(self):
        rig, game = self.launch('close')
        with self.assertRaises(check.Unshown):
            check.check_environment(rig, os.getpid(), gate=True)  # this test's own process: the session's folder
        with self.assertRaises(check.Unshown):
            check.check_environment(rig, game['pid'], gate=False)

    def test_the_path_the_real_supervisor_adopts_saves_and_stops(self):
        rig, game = self.launch('stop')
        check.check_environment(rig, game['pid'], gate=True)
        lock = json.loads(check.PINS.read_text())
        base.make_world(base.desktop.Paths(str(rig.home), str(rig.runtime), str(self.root / 'share')), lock)
        check.stop_path(rig, game, 2, 0)
        path = rig.result['path']
        self.assertEqual((path['adopted'], path['hello_accepted'], path['state']), (True, True, 'IN_WORLD'), path)
        self.assertEqual((path['save']['exit'], path['save']['says']), (0, 'Saved: AresHub is on the disk.'), path)
        self.assertEqual(path['stop']['exit'], 0, path)
        record = path['stop_record']
        self.assertEqual((record['open'], record['kind'], record['save'], record['close'], record['status']),
                         (False, 'stop', 'saved', 'exited', 143), path)
        self.assertEqual((path['java_exited'], path['exit_status'], path['prism_started']), (True, 143, False), path)
        self.assertTrue(any('SIGTERM sent to Java' in line for line in path['stop_phases']), path)
        self.assertEqual(self.wrapper.wait(20), 143)
        # Nothing of the run is left: the supervisor, its stand-ins and the game all named the run's runtime folder.
        left = [entry for entry in os.listdir('/proc') if entry.isdigit() and check.mine(rig, int(entry))]
        self.assertEqual(left, [])


if __name__ == '__main__':
    unittest.main()
