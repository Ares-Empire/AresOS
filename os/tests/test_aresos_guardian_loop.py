"""Package 25, the guardian: the real loop, the real wrapper and a stand-in game process (brief, Acceptance).

The brief's machine rules hold here. Every supervisor runs as a process of its own under `env -i` with HOME, a
temporary XDG_RUNTIME_DIR, PATH and the LABWC_PID of a stand-in this test started: never with the shell's DISPLAY,
WAYLAND_DISPLAY, DBUS_SESSION_BUS_ADDRESS or LABWC_PID. Commands reach it only through that temporary runtime
folder, and a process is ended only if its own environment names that folder.

Step 1 covers section 1: the gate, the hello, `save` and its failures, and peers that do not read. Step 2 covers
section 2 through `aresos-desktop stop`: a confirmed stop, saves that fail, and a game that ignores SIGTERM.
"""
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import textwrap
import threading
import time
import unittest

import test_aresos_desktop as base

desktop = base.desktop
SUPERVISOR = base.CONFIG / 'usr/libexec/aresos-desktop'
WRAPPER = base.CONFIG / 'usr/libexec/aresos-desktop-java'
SESSION_VARIABLES = ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS')

# Runs the real supervisor with stand-ins for Prism, the helper, the cover and the message window. There is no user
# systemd under `env -i`, so the wrapper starts the game directly (the scope has its own tests).
HARNESS = textwrap.dedent('''\
    import importlib.machinery, json, os, sys, types
    config = json.load(open(sys.argv[1]))
    loader = importlib.machinery.SourceFileLoader('aresos_desktop', config['desktop'])
    desktop = types.ModuleType(loader.name)
    sys.modules[loader.name] = desktop
    loader.exec_module(desktop)
    desktop.HELPER, desktop.COVER, desktop.VIEW_COMMAND = config['helper'], config['cover'], [config['view']]
    desktop.prism_command = lambda lock, launch_id, world=None: (
        [config['prism'], '--launch', lock['instance']] + (['--world', world] if world else []))
    desktop.game_scope = lambda launch_id: []
    desktop.Runner.real = False
    for name, value in config['numbers'].items():
        setattr(desktop, name, value)
    sys.exit(desktop.supervise(desktop.Paths(os.environ['HOME'], os.environ['XDG_RUNTIME_DIR'], config['share'])))
''')

# Stands in for systemd-run and Prism: runs the instance's real wrapper with the stand-in game, as Prism does.
PRISM = textwrap.dedent('''\
    #!/usr/bin/python3
    import json, os, subprocess, sys
    config = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')))
    with open(os.path.join(config['control'], 'prism.pids'), 'a') as output:
        output.write(f'{os.getpid()}\\n')
    with open(os.path.join(config['control'], f'prism-env.{os.getpid()}'), 'w') as output:
        json.dump(dict(os.environ), output)
    env = dict(os.environ, INST_ID='AresDesktop', INST_DIR=config['instance'])
    result = subprocess.run([config['wrapper'], config['java'], 'org.prismlauncher.EntryPoint'], env=env,
                            input=b'launch\\n', cwd=os.path.join(config['instance'], 'minecraft'))
    sys.exit(0 if result.returncode == 0 else 1)
''')

# Stands in for Minecraft with the AresOS mod. It speaks the lifecycle channel as LifecycleClient does: only with the
# gate, a hello first, a fresh hello after a closed connection, and one world_saved per save_world. The file
# save-mode says what it answers: saved, renamed (another world), hang (never), or one of the mod's refusals.
# SIGTERM ends it with 143, as it ends Java; while the file ignore-term exists it ignores SIGTERM, as a hung game.
GAME = textwrap.dedent('''\
    #!/usr/bin/python3
    import json, os, signal, socket, sys, time
    config = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')))
    control = config['control']
    with open(os.path.join(control, 'game.pids'), 'a') as output:
        output.write(f'{os.getpid()} {os.getppid()}\\n')
    with open(os.path.join(control, f'game-env.{os.getpid()}'), 'w') as output:
        json.dump(dict(os.environ), output)

    def term(*args):
        if not os.path.exists(os.path.join(control, 'ignore-term')):
            sys.exit(143)

    signal.signal(signal.SIGTERM, term)
    sys.stdin.readline()

    def mode():
        try:
            return open(os.path.join(control, 'save-mode')).read().strip()
        except OSError:
            return 'saved'

    sock, buffer = None, b''
    while True:
        if os.environ.get('ARESOS_DESKTOP_LIFECYCLE') != '1':
            time.sleep(0.05)
            continue
        if sock is None:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(os.path.join(os.environ['XDG_RUNTIME_DIR'], 'aresos', 'desktop.sock'))
                sock.sendall((json.dumps({'op': 'lifecycle_hello', 'major': 1, 'minor': 0,
                                          'instance': os.environ['ARESOS_DESKTOP_INSTANCE'],
                                          'nonce': os.environ['ARESOS_LAUNCH_NONCE'],
                                          'capabilities': ['save_world']}) + '\\n').encode())
                with open(os.path.join(control, 'hellos'), 'a') as output:
                    output.write('hello\\n')
                sock.settimeout(0.05)
                buffer = b''
            except OSError:
                sock = None
                time.sleep(0.1)
                continue
        try:
            data = sock.recv(65536)
        except socket.timeout:
            continue
        except OSError:
            data = b''
        if not data:
            sock.close()
            sock = None
            time.sleep(0.1)
            continue
        buffer += data
        while b'\\n' in buffer:
            line, buffer = buffer.split(b'\\n', 1)
            message = json.loads(line)
            with open(os.path.join(control, 'lines'), 'a') as output:
                output.write(json.dumps(message) + '\\n')
            if message.get('op') != 'save_world' or mode() == 'hang':
                continue
            answer = {'op': 'world_saved', 'id': message['id']}
            if mode() in ('saved', 'renamed'):
                answer.update(ok=True, ms=7, world={'id': 'AresHub' if mode() == 'saved' else 'AresHub-2026-11-19',
                                                    'desktop': True})
            else:
                answer.update(ok=False, reason=mode())
            sock.sendall((json.dumps(answer) + '\\n').encode())
''')

# Stands in for aresos-shell: reports the hub ready on the status pipe.
HELPER = textwrap.dedent('''\
    #!/usr/bin/python3
    import json, os, signal, sys, time
    config = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')))
    with open(os.path.join(config['control'], f'helper-env.{os.getpid()}'), 'w') as output:
        json.dump(dict(os.environ), output)
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    fd = int(os.environ['ARESOS_SHELL_STATUS_FD'])
    while True:
        os.write(fd, (json.dumps({'event': 'world_ready', 'world': 'AresHub'}) + '\\n').encode())
        time.sleep(0.2)
''')

WINDOW = "#!/bin/sh\ntrap 'exit 0' TERM\nwhile :; do sleep 0.05; done\n"
# A process named labwc that waits on its standard input, with the supervisor's runtime folder in its environment.
LABWC = '#!/bin/sh\nread line\n'


@unittest.skipUnless(base.LINUX, 'Unix sockets, pidfds and /proc')
class GuardianLoopTest(base.Base):
    def setUp(self):
        super().setUp()
        self.bin = self.root / 'bin'
        self.control = self.root / 'control'
        self.bin.mkdir()
        self.control.mkdir()
        for name, text in (('prism', PRISM), ('java', GAME), ('helper', HELPER), ('cover', WINDOW), ('view', WINDOW),
                           ('labwc', LABWC)):
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        (self.bin / 'harness.py').write_text(HARNESS)
        (self.bin / 'config.json').write_text(json.dumps({
            'wrapper': str(WRAPPER), 'java': str(self.bin / 'java'), 'instance': self.paths.instance('AresDesktop'),
            'control': str(self.control)}))
        self.lock['java']['path'] = str(self.bin / 'java')
        pathlib.Path(self.paths.share, desktop.LOCK_NAME).write_text(json.dumps(self.lock))
        desktop.provision(self.paths, self.lock)
        base.make_world(self.paths, self.lock)
        self.environment = [f'HOME={self.paths.home}', f'XDG_RUNTIME_DIR={self.paths.runtime}', 'PATH=/usr/bin:/bin']
        self.process = self.labwc = self.output = None
        self.addCleanup(self.stop)

    # -- the supervisor under test

    def start(self, **numbers):
        """The supervisor, as a process of its own under `env -i` (the machine rules)."""
        self.labwc = subprocess.Popen([str(self.bin / 'labwc')], stdin=subprocess.PIPE, cwd=self.root,
                                      env={'XDG_RUNTIME_DIR': self.paths.runtime, 'PATH': '/usr/bin:/bin'})
        (self.root / 'harness.json').write_text(json.dumps({
            'desktop': str(SUPERVISOR), 'share': self.paths.share, 'numbers': numbers,
            **{name: str(self.bin / name) for name in ('prism', 'helper', 'cover', 'view')}}))
        self.output = open(self.root / 'supervisor.log', 'wb')
        self.process = subprocess.Popen(
            ['/usr/bin/env', '-i', *self.environment, f'LABWC_PID={self.labwc.pid}', sys.executable, '-B',
             str(self.bin / 'harness.py'), str(self.root / 'harness.json')],
            stdin=subprocess.DEVNULL, stdout=self.output, stderr=subprocess.STDOUT, cwd=self.root)
        # The game runs, its hello is accepted (a hello before jvm_started is refused and tried again), and the
        # helper has reported the hub ready.
        self.wait(lambda: (lambda status: status.get('lifecycle') is True and status['state'] == 'IN_WORLD')(
            self.status()))

    def mine(self, pid):
        """Only a process whose own environment names this test's runtime folder is ever signalled."""
        try:
            environ = pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
        except OSError:
            return False
        return f'XDG_RUNTIME_DIR={self.paths.runtime}'.encode() in environ

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.status()  # a loop with nothing due sleeps: any request wakes it, and it sees that it must stop
            except (OSError, ValueError):
                pass
            try:
                self.process.wait(10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        # The supervisor leaves a running game alone when it stops: the test ends its own stand-ins.
        for name in ('game.pids', 'prism.pids'):
            for pid in (self.control / name).read_text().split() if (self.control / name).exists() else ():
                if self.mine(int(pid)):
                    os.kill(int(pid), signal.SIGKILL)
        if self.labwc is not None:
            self.labwc.kill()
            self.labwc.wait()
            self.labwc.stdin.close()
        if self.output is not None:
            self.output.close()

    def log(self):
        return (self.root / 'supervisor.log').read_text(errors='replace')

    def wait(self, condition, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if condition():
                    return
            except (OSError, ValueError):
                pass
            time.sleep(0.05)
        self.fail(f'timed out; the supervisor said:\n{self.log()}')

    # -- talking to it, through its temporary runtime folder only

    def status(self):
        return desktop.request(self.paths, {'op': 'status'}, timeout=5)

    def save(self, reason='manual', timeout=10):
        return desktop.request(self.paths, {'op': 'save', 'reason': reason}, timeout=timeout)

    def command(self, *words, runtime=None):
        """The real `aresos-desktop` command, under `env -i` too: (exit code, stdout, stderr)."""
        environment = self.environment if runtime is None else [
            self.environment[0], f'XDG_RUNTIME_DIR={runtime}', self.environment[2]]
        done = subprocess.run(['/usr/bin/env', '-i', *environment, sys.executable, '-B', str(SUPERVISOR), *words],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=90, cwd=self.root)
        return done.returncode, done.stdout, done.stderr

    def mode(self, value):
        (self.control / 'save-mode').write_text(value)

    def game(self):
        """(PID, environment) of the stand-in game that runs now."""
        pid = int((self.control / 'game.pids').read_text().splitlines()[-1].split()[0])
        return pid, json.loads((self.control / f'game-env.{pid}').read_text())

    def asked(self):
        """Every line the supervisor sent the game."""
        lines = self.control / 'lines'
        return [json.loads(line) for line in lines.read_text().splitlines()] if lines.exists() else []

    # -- the tests

    def test_the_game_gets_the_gate_says_hello_and_a_save_is_confirmed(self):
        self.start()
        pid, env = self.game()
        self.assertEqual(env['ARESOS_DESKTOP_LIFECYCLE'], '1')
        # The game would dial the supervisor of whatever runtime folder it has: it is this test's, never a session's.
        self.assertEqual(env['XDG_RUNTIME_DIR'], self.paths.runtime)
        self.assertEqual(env['LABWC_PID'], str(self.labwc.pid))
        self.assertEqual(pathlib.Path(f'/proc/{self.labwc.pid}/comm').read_text(), 'labwc\n')
        for name in SESSION_VARIABLES:
            self.assertNotIn(name, env)
        for other in list(self.control.glob('prism-env.*')) + list(self.control.glob('helper-env.*')):
            self.assertNotIn('ARESOS_DESKTOP_LIFECYCLE', json.loads(other.read_text()), other.name)
        status = self.status()
        self.assertEqual((status['jvm_pid'], status['lifecycle']), (pid, True))
        self.assertEqual(self.asked(), [])  # an accepted hello gets no reply
        reply = self.save('backup')
        self.assertEqual(reply, {'ok': True, 'result': 'saved', 'world': 'AresHub', 'reason': None, 'ms': 7,
                                 'message': 'Saved: AresHub is on the disk.'})
        self.assertEqual(self.command('save'), (0, 'Saved: AresHub is on the disk.\n', ''))
        self.assertEqual(self.command('save', '--reason', 'update')[0], 0)
        self.assertEqual(self.asked(), [{'op': 'save_world', 'id': 1, 'reason': 'backup'},
                                        {'op': 'save_world', 'id': 2, 'reason': 'manual'},
                                        {'op': 'save_world', 'id': 3, 'reason': 'update'}])
        self.assertEqual(self.save('nonsense')['error'], 'bad_reason')
        self.assertEqual(len(self.asked()), 3)
        self.assertNotIn(env['ARESOS_LAUNCH_NONCE'], self.log())

    def test_what_the_game_answers_decides(self):
        self.start()
        for mode, result, reason in (('error', 'refused', 'error'), ('no_world', 'refused', 'no_world'),
                                     ('server_stopping', 'refused', 'server_stopping'),
                                     ('not_desktop_world', 'refused', 'not_desktop_world'),
                                     ('renamed', 'wrong_world', None), ('busy', 'invalid', None)):
            with self.subTest(mode):
                self.mode(mode)
                reply = self.save()
                self.assertEqual((reply['ok'], reply['result'], reply['reason'], reply['world']),
                                 (False, result, reason, 'AresHub'))
                self.assertTrue(reply['message'].startswith('Not saved: '), reply['message'])
        self.mode('error')
        self.assertEqual(self.command('save'),
                         (1, '', 'Not saved: Minecraft could not write AresHub to the disk; its log says why.\n'))
        self.mode('saved')
        self.assertTrue(self.save()['ok'])  # the next request is judged on its own
        self.assertEqual([line['id'] for line in self.asked()], list(range(1, 9)))

    def test_a_save_that_hangs_times_out_while_the_loop_keeps_answering(self):
        self.start(SAVE_WAIT=1.5)
        self.mode('hang')
        replies = []
        started = time.monotonic()
        thread = threading.Thread(target=lambda: replies.append(self.save()), daemon=True)
        thread.start()
        self.wait(lambda: len(self.asked()) == 1)
        asked = time.monotonic()
        self.assertEqual(self.status()['state'], 'IN_WORLD')
        self.assertLess(time.monotonic() - asked, 1.0)  # the hung save blocks nobody else
        thread.join(10)
        self.assertEqual([(reply['ok'], reply['result']) for reply in replies], [(False, 'timeout')])
        self.assertGreaterEqual(time.monotonic() - started, 1.5)
        self.assertLess(time.monotonic() - started, 4.0)
        # The game was never touched, and a later save is a request of its own.
        self.assertEqual(self.status()['jvm_pid'], self.game()[0])
        self.mode('saved')
        self.assertEqual(self.save()['result'], 'saved')
        self.assertEqual([line['id'] for line in self.asked()], [1, 2])

    def test_the_game_ending_in_the_middle_of_a_save_is_never_a_save(self):
        self.start(BACKOFF=60.0)
        self.mode('hang')
        replies = []
        thread = threading.Thread(target=lambda: replies.append(self.save()), daemon=True)
        thread.start()
        self.wait(lambda: len(self.asked()) == 1)
        pid, _ = self.game()
        self.assertTrue(self.mine(pid))
        os.kill(pid, signal.SIGTERM)
        thread.join(10)
        self.assertEqual([(reply['ok'], reply['result']) for reply in replies], [(False, 'lost')])
        self.wait(lambda: self.status()['jvm_pid'] is None)
        self.assertIs(self.status()['lifecycle'], False)
        self.assertEqual(self.save()['result'], 'no_channel')
        self.assertEqual(self.command('save')[0], 1)

    def test_a_hello_from_another_process_is_refused_and_closes(self):
        self.start()
        runtime = json.loads(pathlib.Path(self.paths.runtime_file).read_text())
        hello = {'op': 'lifecycle_hello', 'major': 1, 'minor': 0, 'instance': runtime['instance'],
                 'nonce': runtime['nonce'], 'capabilities': ['save_world']}
        for changes in ({}, {'nonce': 'x' * 32}):  # the right nonce is not enough: the peer must be the game
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect(self.paths.socket)
                sock.sendall((json.dumps(dict(hello, **changes)) + '\n').encode())
                self.assertEqual(sock.recv(65536), b'')  # no reply, and the connection closes
        self.assertIs(self.status()['lifecycle'], True)  # the game's own channel stands
        self.assertEqual(self.save()['result'], 'saved')
        self.assertEqual(self.log().count('refused a lifecycle hello'), 2)
        self.assertNotIn(runtime['nonce'], self.log())
        self.assertEqual((self.control / 'hellos').read_text().count('hello'),
                         1 + self.log().count('no game is running that its launcher wrapper reported'))

    def test_a_peer_that_never_reads_is_dropped_and_blocks_nobody(self):
        self.start()
        stalled = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(stalled.close)
        stalled.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        stalled.settimeout(5)
        stalled.connect(self.paths.socket)
        sent = 0
        try:
            for _ in range(400):  # 20,000 requests whose replies nobody takes
                stalled.sendall(b'{"op":"status"}\n' * 50)
                sent += 50
        except OSError:
            pass  # dropped already
        started = time.monotonic()
        self.assertEqual(self.status()['state'], 'IN_WORLD')
        self.assertEqual(self.save()['result'], 'saved')
        self.assertLess(time.monotonic() - started, 2.0)
        # A caller that asks for a save and goes away without its reply changes nothing either.
        gone = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        gone.connect(self.paths.socket)
        gone.sendall(b'{"op":"save"}\n')
        gone.close()
        self.assertEqual(self.save()['result'], 'saved')
        # The stalled peer was dropped: what it was sent ends, long before 20,000 replies.
        taken = 0
        try:
            while True:
                data = stalled.recv(65536)
                if not data:
                    break
                taken += data.count(b'\n')
        except ConnectionResetError:
            pass
        self.assertLess(taken, 5000, sent)
        self.assertIsNone(self.process.poll())

    # -- step 2: the one stop routine, driven by `aresos-desktop stop`

    def games(self):
        """How many stand-in games were ever started."""
        return len((self.control / 'game.pids').read_text().splitlines())

    def test_a_stop_saves_closes_and_ends_at_the_quit_window(self):
        self.start()
        pid, _ = self.game()
        self.assertEqual(self.command('stop'), (0, 'Stopped: the home was saved first; Minecraft closed.\n', ''))
        self.assertFalse(self.mine(pid))  # Java is really gone when the command answers
        status = self.status()
        self.assertEqual((status['state'], status['reason'], status['jvm_pid'], status['stopping']),
                         ('RECOVERY', 'quit', None, False))
        record = status['stop']
        self.assertEqual((record['open'], record['kind'], record['save'], record['sigterm'], record['close'],
                          record['status']), (False, 'stop', 'saved', True, 'exited', 143))
        self.assertEqual(self.asked(), [{'op': 'save_world', 'id': 1, 'reason': 'shutdown'}])
        stored = self.stored()
        self.assertEqual((stored['latched'], stored['consecutive'], stored['failures']), (False, 0, []))
        for phase in ('begins for launch', 'the save is confirmed (saved)', 'SIGTERM sent to Java',
                      'stopped (exit code 143)', 'ended after'):
            self.assertIn(phase, self.log())
        # A planned stop is never restarted, and a second stop finds nothing to stop.
        time.sleep(1.0)
        self.assertEqual(self.games(), 1)
        self.assertEqual(self.command('stop'), (0, 'Nothing to stop: Minecraft is not running.\n', ''))
        self.assertEqual(self.status()['reason'], 'quit')

    def test_a_stop_whose_save_is_not_confirmed_is_called_off(self):
        self.start(STOP_SAVE_WAIT=1.5)
        pid, _ = self.game()
        for mode, why, asks in (('error', 'could not write AresHub', 1),
                                ('renamed', 'which is not the home AresHub', 1),
                                ('no_world', 'no home is open in Minecraft', 2),  # asked again after a second
                                ('hang', 'did not answer in time', 1)):
            self.mode(mode)
            before = len(self.asked())
            code, out, err = self.command('stop')
            self.assertEqual((code, out), (1, ''), mode)
            self.assertTrue(err.startswith('Not stopped: Minecraft keeps running. Not saved:'), err)
            self.assertIn(why, err)
            self.assertEqual(len(self.asked()) - before, asks, mode)
            self.assertTrue(self.mine(pid), mode)  # never signalled
            time.sleep(0.5)  # the helper's reports keep coming: the window stays
            status = self.status()
            self.assertEqual((status['state'], status['reason'], status['jvm_pid'], status['stop']['close']),
                             ('RECOVERY', 'save_failed', pid, 'called_off'), mode)
        self.mode('saved')
        self.assertEqual(self.command('retry')[0], 0)
        self.wait(lambda: self.status()['state'] == 'IN_WORLD')
        self.assertEqual(self.command('stop')[0], 0)
        self.assertEqual((self.games(), self.mine(pid)), (1, False))

    def test_a_game_that_ignores_sigterm_is_never_killed_and_no_second_game_starts(self):
        (self.bin / 'systemctl').write_text('#!/bin/sh\necho stopping\n')  # systemd's word: the system is stopping
        (self.bin / 'systemctl').chmod(0o755)
        self.start(STOP_BUDGET=3.0, SYSTEMCTL=str(self.bin / 'systemctl'))
        pid, _ = self.game()
        (self.control / 'ignore-term').write_text('')
        began = time.monotonic()
        code, out, err = self.command('stop')
        took = time.monotonic() - began
        self.assertEqual((code, out), (1, ''))
        self.assertIn('the home was saved first; Minecraft did not close within 3 seconds', err)
        self.assertTrue(2.5 < took < 6, took)  # it ends at the deadline
        self.assertTrue(self.mine(pid))
        status = self.status()
        self.assertEqual((status['state'], status['reason'], status['jvm_pid']), ('RECOVERY', 'stuck', pid))
        self.assertEqual((status['stop']['open'], status['stop']['close']), (True, 'overrun'))
        code, out, err = self.command('retry')
        self.assertEqual((code, out), (0, 'Minecraft is still running; the recovery state is cleared.\n'))
        # A stop that cannot be called off ends at the deadline too: the supervisor answers and keeps running.
        began = time.monotonic()
        code, out, err = self.command('stop', '--reason', 'shutdown')
        took = time.monotonic() - began
        self.assertEqual(code, 1, err)
        self.assertTrue(2.5 < took < 6, took)
        status = self.status()
        self.assertEqual((status['state'], status['stop']['kind'], status['stop']['close']),
                         ('STOPPING', 'shutdown', 'overrun'))
        self.assertEqual(self.command('retry')[0], 1)  # the session is ending: nothing is started any more
        time.sleep(0.5)
        self.assertEqual((self.games(), self.mine(pid)), (1, True))
        self.assertIsNone(self.process.poll())
        self.assertNotIn('SIGKILL', self.log())

    def test_the_command_without_a_supervisor_says_not_saved(self):
        empty = self.root / 'empty-run'
        empty.mkdir()
        code, out, err = self.command('save', runtime=empty)
        self.assertEqual((code, out), (1, ''))
        self.assertTrue(err.startswith('Not saved: the AresOS desktop supervisor did not answer'), err)


if __name__ == '__main__':
    unittest.main()
