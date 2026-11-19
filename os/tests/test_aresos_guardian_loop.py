"""Package 25, the guardian: the real loop, the real wrapper and a stand-in game process (brief, Acceptance).

The brief's machine rules hold here. Every supervisor runs as a process of its own under `env -i` with HOME, a
temporary XDG_RUNTIME_DIR, PATH and the LABWC_PID of a stand-in this test started: never with the shell's DISPLAY,
WAYLAND_DISPLAY, DBUS_SESSION_BUS_ADDRESS or LABWC_PID. Commands reach it only through that temporary runtime
folder, and a process is ended only if its own environment names that folder.

Step 1 covers section 1: the gate, the hello, `save` and its failures, and peers that do not read. Step 2 covers
section 2 through `aresos-desktop stop`: a confirmed stop, saves that fail, and a game that ignores SIGTERM. Step 3
covers 3.2 and 3.3: a signal (also through the keeper), the stand-in labwc's end, `logout` and `restart`. The only
labwc ever signalled is the stand-in this test started, and only by the supervisor through its watched pidfd.
Step 4 covers 3.4: the black screen and the lid block, as stand-ins that only note their start and their end. No
test here takes a logind inhibitor or draws on a screen. Step 5 covers 4.2's `use-home` through the real command:
the only world folders it touches are the ones this test made in its temporary home.
"""
import json
import os
import pathlib
import re
import shutil
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
    desktop.SYSTEMD_INHIBIT = config['inhibit']  # always the stand-in: no test takes a real logind inhibitor
    desktop.SYSTEMCTL = config['systemctl']  # always the stand-in: no test asks the laptop's systemd about the guard
    desktop.prism_command = lambda lock, launch_id, world=None: (
        [config['prism'], '--launch', lock['instance']] + (['--world', world] if world else []))
    desktop.game_scope = lambda launch_id: []
    desktop.Runner.real = False
    for name, value in config['numbers'].items():
        setattr(desktop, name, value)
    paths = desktop.Paths(os.environ['HOME'], os.environ['XDG_RUNTIME_DIR'], config['share'])
    if sys.argv[2:] == ['session']:  # the keeper, whose supervisor is this harness again
        desktop.SELF = config['self']
        sys.exit(desktop.session(paths))
    sys.exit(desktop.supervise(paths))
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

# Stands in for aresos-shell: reports the hub ready on the status pipe, and the app windows as the file `windows`
# says (one `windows` event at each change; no file: it has not said). While the file `quiet` exists it says nothing.
HELPER = textwrap.dedent('''\
    #!/usr/bin/python3
    import json, os, signal, sys, time
    config = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')))
    with open(os.path.join(config['control'], f'helper-env.{os.getpid()}'), 'w') as output:
        json.dump(dict(os.environ), output)
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    fd = int(os.environ['ARESOS_SHELL_STATUS_FD'])
    os.set_blocking(fd, False)
    said = None
    while True:
        if not os.path.exists(os.path.join(config['control'], 'quiet')):
            os.write(fd, (json.dumps({'event': 'world_ready', 'world': 'AresHub'}) + '\\n').encode())
            try:
                windows = open(os.path.join(config['control'], 'windows')).read().strip()
            except OSError:
                windows = None
            if windows and windows != said:
                os.write(fd, (windows + '\\n').encode())
                said = windows
            try:
                request = os.read(fd, 64).decode().split()
            except BlockingIOError:
                request = []
            if len(request) == 2 and request[0] == 'windows':
                report = json.loads(windows) if windows else dict(event='windows', count=None, names=[])
                os.write(fd, (json.dumps(dict(report, request=request[1])) + '\\n').encode())
        else:
            open(os.path.join(config['control'], 'quiet-ack'), 'a').close()
        time.sleep(0.2)
''')

WINDOW = "#!/bin/sh\ntrap 'exit 0' TERM\nwhile :; do sleep 0.05; done\n"
# Stands in for aresos-cover (`cover`) and for systemd-inhibit (`inhibit`): it notes its start with its arguments,
# and its end by SIGTERM, in the control file `covers` or `inhibits`. It never runs the command it is given and
# never talks to logind or to a compositor.
RECORDER = textwrap.dedent('''\
    #!/bin/sh
    log="$(dirname "$0")/../control/$(basename "$0")s"
    echo "start $$ $*" >> "$log"
    trap 'echo "end $$" >> "$log"; exit 0' TERM
    while :; do sleep 0.05; done
''')
# Stands in for systemctl: the shutdown guard's state is what the control file `guard` says (none: active), the
# system's what `system` says (none: running).
SYSTEMCTL = textwrap.dedent('''\
    #!/bin/sh
    control="$(dirname "$0")/../control"
    case "$1" in
        is-active) cat "$control/guard" 2>/dev/null || echo active ;;
        is-system-running) cat "$control/system" 2>/dev/null || echo running ;;
    esac
''')
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
        for name, text in (('prism', PRISM), ('java', GAME), ('helper', HELPER), ('cover', RECORDER),
                           ('view', WINDOW), ('labwc', LABWC), ('inhibit', RECORDER), ('systemctl', SYSTEMCTL)):
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

    def start(self, keeper=False, labwc_runtime=None, wait=True, **numbers):
        """The supervisor, as a process of its own under `env -i` (the machine rules). `keeper`: the session's
        keeper, which starts the supervisor itself. `labwc_runtime`: the stand-in labwc is another session's."""
        self.labwc = subprocess.Popen([str(self.bin / 'labwc')], stdin=subprocess.PIPE, cwd=self.root,
                                      env={'XDG_RUNTIME_DIR': labwc_runtime or self.paths.runtime,
                                           'PATH': '/usr/bin:/bin'})
        harness = [sys.executable, '-B', str(self.bin / 'harness.py'), str(self.root / 'harness.json')]
        (self.bin / 'self').write_text('#!/bin/sh\nexec ' + ' '.join(harness) + '\n')  # "$@" is `supervise`
        (self.bin / 'self').chmod(0o755)
        (self.root / 'harness.json').write_text(json.dumps({
            'desktop': str(SUPERVISOR), 'share': self.paths.share, 'numbers': numbers,
            **{name: str(self.bin / name) for name in ('prism', 'helper', 'cover', 'view', 'self', 'inhibit',
                                                        'systemctl')}}))
        self.output = open(self.root / 'supervisor.log', 'wb')
        self.process = subprocess.Popen(
            ['/usr/bin/env', '-i', *self.environment, f'LABWC_PID={self.labwc.pid}', *harness,
             *(['session'] if keeper else [])],
            stdin=subprocess.DEVNULL, stdout=self.output, stderr=subprocess.STDOUT, cwd=self.root)
        # The game runs, its hello is accepted (a hello before jvm_started is refused and tried again), and the
        # helper has reported the hub ready.
        if wait:
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
            # SIGTERM runs the stop routine now (3.2): let the stand-in game save and close at once.
            (self.control / 'ignore-term').unlink(missing_ok=True)
            self.mode('saved')
            self.process.terminate()
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
        # Whatever else this test's supervisor left behind (a keeper's supervisor, a helper): its own environment
        # names this test's runtime folder, or it is not touched.
        for entry in os.listdir('/proc'):
            if entry.isdigit() and int(entry) != os.getpid() and self.mine(int(entry)):
                os.kill(int(entry), signal.SIGKILL)
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
        pids = self.control / 'game.pids'
        return len(pids.read_text().splitlines()) if pids.exists() else 0

    # -- step 7: the shutdown guard (3.1)

    def test_no_game_starts_until_the_guard_is_active_and_retry_asks_again(self):
        (self.control / 'guard').write_text('inactive\n')
        self.start(wait=False)
        self.wait(lambda: self.status()['reason'] == 'guard')
        time.sleep(1.0)
        status = self.status()
        self.assertEqual((status['state'], status['latched'], status['jvm_pid'], self.games()),
                         ('RECOVERY', False, None, 0))
        self.assertIn('aresos-guardian.service: inactive', status['message'])
        self.assertFalse((self.control / 'prism.pids').exists())  # not even Prism was started
        code, out, _ = self.command('retry')
        self.assertEqual((code, self.status()['reason'], self.games()), (0, 'guard', 0))
        (self.control / 'guard').write_text('active\n')
        self.assertEqual(self.command('retry')[0], 0)
        self.wait(lambda: self.status()['state'] == 'IN_WORLD')
        self.assertEqual(self.games(), 1)
        self.assertIn('the shutdown guard (aresos-guardian.service) is not active (inactive)', self.log())

    def test_the_guards_command_ends_at_once_when_nothing_runs_and_passes_a_stop_on(self):
        # No supervisor and nobody holds the desktop lock: nothing is running. No waiting at a shutdown.
        os.makedirs(self.paths.run_dir, exist_ok=True)
        began = time.monotonic()
        code, out, err = self.command('stop', '--reason', 'shutdown')
        self.assertEqual((code, err), (0, ''))
        self.assertIn('Nothing to stop: the AresOS desktop supervisor did not answer', out)
        self.assertLess(time.monotonic() - began, 5)
        # No runtime folder at all: no session.
        code, out, err = self.command('stop', '--reason', 'shutdown', runtime=str(self.root / 'none'))
        self.assertEqual((code, out, err), (0, 'Nothing to stop: no AresOS session is running.\n', ''))
        # With the game running and systemd's word that the system stops: a shutdown, confirmed and closed.
        (self.control / 'system').write_text('stopping\n')
        self.start()
        pid, _ = self.game()
        code, out, err = self.command('stop', '--reason', 'shutdown')
        self.assertEqual((code, out, err), (0, 'Stopped: the home was saved first; Minecraft closed.\n', ''))
        stop = self.status()['stop']
        self.assertEqual((stop['kind'], stop['save'], stop['close'], self.mine(pid)), ('shutdown', 'saved', 'exited', False))
        self.assertFalse(os.path.exists(self.paths.guard_file))

    def test_no_supervisor_while_the_game_runs_leaves_the_fallback_record_and_the_next_start_says_unsaved(self):
        self.start()
        pid, _ = self.game()
        self.process.kill()  # the supervisor is gone, and no keeper brings one back; the game runs on
        self.process.wait()
        self.assertTrue(self.mine(pid))
        began = time.monotonic()
        code, out, err = self.command('stop', '--reason', 'shutdown')
        took = time.monotonic() - began
        self.assertEqual((code, out), (1, ''))
        self.assertIn('Minecraft is still running. The next start of AresOS says so.', err)
        self.assertTrue(desktop.GUARD_RECOVERY_WAIT <= took < desktop.GUARD_RECOVERY_WAIT + 5, took)
        self.assertTrue(self.mine(pid))  # the command never signals anything
        record = json.loads(pathlib.Path(self.paths.guard_file).read_text())
        self.assertEqual((record['why'], record['lock'], record['save'], record['launch']),
                         ('no_answer', 'held', None, json.loads(pathlib.Path(self.paths.runtime_file).read_text())['launch']))
        # The system's teardown ends the game; the next supervisor finds none and applies the record once.
        os.kill(pid, signal.SIGKILL)
        self.wait(lambda: not self.mine(pid))
        self.wait(lambda: desktop.desktop_lock_state(self.paths) == 'free')
        self.labwc.kill()
        self.labwc.wait()
        self.labwc.stdin.close()
        self.output.close()
        self.start(wait=False)
        self.wait(lambda: self.status()['reason'] == 'unsaved')
        status = self.status()
        self.assertEqual((status['state'], status['latched'], status['jvm_pid'], self.games()),
                         ('RECOVERY', True, None, 1))
        self.assertIn(desktop.GUARD_FALLBACK['held'], status['message'])
        self.assertFalse(os.path.exists(self.paths.guard_file))

    def fixture(self, mode, **numbers):
        """The check build's stand-in game (os/ci/overlay/GuardianGame.java) in place of the Python one: a real
        JVM, when this machine has a Java that runs a single-file program with Unix sockets (16 or newer)."""
        java = next((path for path in (self.lock_java(), shutil.which('java')) if path and os.access(path, os.X_OK)), None)
        if java is None:
            self.skipTest('no Java on this machine; the hosted run and the check build have one')
        version = subprocess.run([java, '-version'], capture_output=True, text=True, timeout=60).stderr
        major = re.search(r'version "(\d+)', version)
        if not major or int(major.group(1)) < 16:
            self.skipTest(f'this Java is too old for Unix sockets: {version.splitlines()[:1]}')
        game = base.CONFIG.parent / 'ci/overlay/GuardianGame.java'
        (self.control / 'camera').touch()
        (self.bin / 'java').write_text(textwrap.dedent(f'''\
            #!/bin/sh
            echo "$$ $PPID" >> "{self.control}/game.pids"
            exec "{java}" "{game}" {mode} 400 "{self.control}/save-asked" "{self.control}/camera" >> "{self.control}/game.out" 2>&1
        '''))
        self.start(wait=False, **numbers)
        # A JVM that first compiles its one file takes a moment longer than the Python stand-in.
        self.wait(lambda: (lambda status: status.get('lifecycle') is True and status['state'] == 'IN_WORLD')(
            self.status()), timeout=90)
        return int((self.control / 'game.pids').read_text().split()[0])

    @staticmethod
    def lock_java():
        return json.loads((base.CONFIG.parent / 'minecraft/desktop.lock.json').read_text())['java']['path']

    def test_the_vm_fixture_game_saves_and_ends_with_143_as_the_real_game_does(self):
        (self.control / 'system').write_text('stopping\n')
        pid = self.fixture('save')
        self.assertEqual(pathlib.Path(f'/proc/{pid}/comm').read_text().strip(), 'java')
        camera = self.control / 'camera'
        self.assertEqual(camera.read_text(), 'ready\n')
        began = time.monotonic()
        reply = self.save()
        self.assertEqual((reply['ok'], reply['result']), (True, 'saved'))
        self.assertGreaterEqual(time.monotonic() - began, 0.4)
        self.assertTrue((self.control / 'save-asked').exists())
        code, out, err = self.command('stop', '--reason', 'shutdown')
        self.assertEqual((code, out, err), (0, 'Stopped: the home was saved first; Minecraft closed.\n', ''))
        stop = self.status()['stop']
        self.assertEqual(stop['kind'], 'shutdown')
        self.assertEqual((stop['save'], stop['close'], stop['status']), ('saved', 'exited', 143))
        self.assertEqual(camera.read_text().splitlines(), ['ready', 'saving', 'answering', 'saving', 'answering'])
        said = (self.control / 'game.out').read_text()
        for marker in ('GUARDIAN_GAME started mode=save', 'GUARDIAN_GAME save_asked id=1',
                       'GUARDIAN_GAME save_answered id=1', 'GUARDIAN_GAME save_asked id=2', 'GUARDIAN_GAME closing'):
            self.assertIn(marker, said)
        # It never says its nonce, its instance or its environment: only its mode and the saves' ids.
        lines = [line for line in said.splitlines() if line.startswith('GUARDIAN_GAME ')]
        self.assertEqual(sorted({item.split('=')[0] for line in lines for item in line.split() if '=' in item}),
                         ['id', 'mode'])

    def test_the_vm_fixture_game_that_hangs_never_answers_and_ignores_sigterm(self):
        (self.control / 'system').write_text('stopping\n')
        pid = self.fixture('hang', STOP_BUDGET=4.0, STOP_SAVE_WAIT=1.5)
        code, out, err = self.command('stop', '--reason', 'shutdown')
        self.assertEqual((code, out), (1, ''))
        self.assertIn('Not a confirmed stop: the home could not be confirmed as saved first; Minecraft did not close', err)
        stop = self.status()['stop']
        self.assertEqual((stop['kind'], stop['close'], stop['sigterm'], stop['open']), ('shutdown', 'overrun', True, True))
        self.assertNotIn(stop['save'], ('saved', 'nothing'))
        self.assertTrue(self.mine(pid))  # never killed
        said = (self.control / 'game.out').read_text()
        self.assertIn('GUARDIAN_GAME save_asked id=1', said)
        self.assertIn('GUARDIAN_GAME sigterm_ignored', said)
        self.assertNotIn('save_answered', said)
        self.assertEqual((self.control / 'camera').read_text().splitlines(), ['ready', 'saving'])
        self.assertFalse(os.path.exists(self.paths.guard_file))  # the supervisor answered and recorded: no fallback

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
        (self.control / 'system').write_text('stopping\n')  # systemd's word: the system is stopping
        self.start(STOP_BUDGET=3.0)
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

    # -- step 3: the session ends under the supervisor, `logout` and `restart`

    def windows(self, *names):
        """What the stand-in helper reports as open app windows; waits until the supervisor has it."""
        (self.control / 'windows').write_text(json.dumps({'event': 'windows', 'count': len(names),
                                                          'names': list(names)}))
        self.wait(lambda: self.status()['windows'] == list(names))

    def last_stop(self):
        stop = self.stored()['stop']
        return stop['open'], stop['kind'], stop['save'], stop['close'], stop['status']

    def test_sigterm_to_an_idle_loop_begins_the_stop_within_a_second_and_the_keeper_waits(self):
        self.start(keeper=True)
        pid, _ = self.game()
        keeper = self.process.pid
        (supervisor,) = pathlib.Path(f'/proc/{keeper}/task/{keeper}/children').read_text().split()
        self.assertTrue(self.mine(int(supervisor)))
        (self.control / 'quiet').write_text('')  # the helper falls silent: nothing wakes the loop any more
        time.sleep(1.0)  # its next deadline is the heartbeat gap, 20 s away
        began = time.monotonic()
        self.process.terminate()  # SIGTERM to the keeper, which passes it on to its supervisor
        self.wait(lambda: 'begins for launch' in self.log(), timeout=5)
        self.assertLess(time.monotonic() - began, 1.0)
        self.assertEqual(self.process.wait(15), 0)
        # The keeper ended only after its supervisor had: the home saved, Java closed, the socket gone.
        self.assertFalse(self.mine(int(supervisor)))
        self.assertFalse(self.mine(pid))
        self.assertFalse(os.path.exists(self.paths.socket))
        self.assertEqual(self.asked(), [{'op': 'save_world', 'id': 1, 'reason': 'shutdown'}])
        self.assertEqual(self.last_stop(), (False, 'shutdown', 'saved', 'exited', 143))
        self.assertEqual((self.stored()['latched'], self.games()), (False, 1))
        self.assertTrue(os.path.exists(self.paths.stop_block))  # nothing is admitted in this session any more
        log = self.log()
        self.assertIn('the session is ending (SIGTERM)', log)
        self.assertLess(log.index('SIGTERM sent to Java'), log.index('stop (shutdown) ended after'))

    def test_sigterm_in_the_middle_of_a_save_closes_anyway_and_records_unsaved(self):
        self.start(STOP_SAVE_WAIT=1.5, STOP_BUDGET=8.0, STOP_EXIT_RESERVE=1.0)
        pid, _ = self.game()
        self.mode('hang')
        replies = []

        def save():
            try:
                replies.append(self.save())
            except (OSError, ValueError) as error:
                replies.append({'ok': False, 'error': str(error)})

        thread = threading.Thread(target=save, daemon=True)
        thread.start()
        self.wait(lambda: len(self.asked()) == 1)
        began = time.monotonic()
        self.process.terminate()
        self.assertEqual(self.process.wait(15), 0)
        self.assertLess(time.monotonic() - began, 8.0)
        thread.join(10)
        self.assertEqual([reply['ok'] for reply in replies], [False])  # the save in flight is never a save
        self.assertFalse(self.mine(pid))  # the session was ending: closed anyway, by SIGTERM
        self.assertEqual(self.last_stop(), (False, 'shutdown', 'timeout', 'exited', 143))
        self.assertEqual((self.stored()['latched'], self.stored()['reason']), (True, 'unsaved'))
        self.assertNotIn('SIGKILL', self.log())

    def test_a_signal_with_a_game_that_ignores_sigterm_exits_inside_the_deadline_and_never_kills(self):
        self.start(STOP_BUDGET=4.0, STOP_EXIT_RESERVE=1.0)
        pid, _ = self.game()
        (self.control / 'ignore-term').write_text('')
        began = time.monotonic()
        self.process.terminate()
        self.assertEqual(self.process.wait(15), 0)
        took = time.monotonic() - began
        self.assertTrue(2.8 < took < 4.0, took)  # it stopped waiting at 3 s, and its own exit fits in the rest
        self.assertTrue(self.mine(pid))  # never killed: the system's teardown ends it
        stop = self.stored()['stop']  # it still names the launch, so its end will be `stopped`
        self.assertEqual((stop['open'], stop['kind'], stop['save'], stop['sigterm'], stop['close']),
                         (True, 'shutdown', 'saved', True, 'overrun'))
        self.assertEqual(self.games(), 1)
        self.assertNotIn('SIGKILL', self.log())

    def test_the_stand_in_labwc_ending_ends_the_supervisor_and_the_keeper_inside_the_deadline(self):
        self.start(keeper=True, STOP_BUDGET=8.0, STOP_EXIT_RESERVE=1.0)
        pid, _ = self.game()
        self.assertIs(self.status()['labwc'], True)
        began = time.monotonic()
        self.labwc.stdin.close()  # the stand-in labwc ends by itself
        self.assertEqual(self.labwc.wait(5), 1)
        self.assertEqual(self.process.wait(15), 0)
        self.assertLess(time.monotonic() - began, 8.0)
        self.assertFalse(self.mine(pid))
        self.assertEqual(self.asked(), [{'op': 'save_world', 'id': 1, 'reason': 'shutdown'}])
        self.assertEqual(self.last_stop(), (False, 'shutdown', 'saved', 'exited', 143))
        self.assertEqual(self.games(), 1)
        self.assertIn('the session is ending (labwc ended)', self.log())
        self.assertFalse([entry for entry in os.listdir('/proc')
                          if entry.isdigit() and int(entry) != self.labwc.pid and self.mine(int(entry))])

    def test_logout_is_refused_with_an_app_open_and_otherwise_ends_the_stand_in_labwc(self):
        self.start()
        pid, _ = self.game()
        code, out, err = self.command('logout')  # the helper has not said
        self.assertEqual((code, out), (1, ''))
        self.assertIn('cannot tell whether an app is still open', err)
        self.windows('Mail')
        self.assertEqual(self.command('logout'), (1, '', 'Not logged out: an app is still open (Mail). Close it '
                                                         'first; nothing was stopped.\n'))
        self.assertEqual((self.mine(pid), self.labwc.poll(), self.asked()), (True, None, []))
        self.assertEqual((self.status()['state'], os.path.exists(self.paths.stop_block)), ('IN_WORLD', False))
        self.windows()
        self.assertEqual(self.command('logout'),
                         (0, 'Logged out: the home was saved first; Minecraft closed.\n', ''))
        self.assertEqual(self.labwc.wait(5), -signal.SIGTERM)  # ended by the supervisor, through its pidfd
        self.assertEqual(self.process.wait(10), 0)  # the session is over: the supervisor exits too
        self.assertFalse(self.mine(pid))
        self.assertEqual(self.asked(), [{'op': 'save_world', 'id': 1, 'reason': 'shutdown'}])
        self.assertEqual(self.last_stop(), (False, 'logout', 'saved', 'exited', 143))
        self.assertEqual((self.games(), os.path.exists(self.paths.stop_block)), (1, True))
        log = self.log()
        self.assertLess(log.index('stopped (exit code 143)'), log.index('SIGTERM sent to labwc'))

    def test_logout_keeps_the_session_when_the_helper_stalls_after_reporting_zero(self):
        self.start()
        self.windows()
        (self.control / 'quiet').touch()
        self.wait(lambda: (self.control / 'quiet-ack').exists())
        (self.control / 'windows').write_text(json.dumps({'event': 'windows', 'count': 1, 'names': ['Mail']}))
        self.assertEqual(self.status()['windows'], [])  # last report, before Mail opened
        code, out, err = self.command('logout')
        self.assertEqual((code, out), (1, ''))
        self.assertIn('can no longer tell whether an app is open', err)
        self.assertIsNone(self.labwc.poll())
        self.assertEqual(self.last_stop(), (False, 'logout', 'saved', 'exited', 143))

    def test_a_labwc_of_another_runtime_folder_is_never_watched_or_signalled(self):
        other = self.root / 'other-run'
        other.mkdir()
        self.start(labwc_runtime=str(other))
        pid, _ = self.game()
        self.windows()
        self.assertIs(self.status()['labwc'], False)
        self.assertIn('is not watched (that labwc runs on another runtime folder', self.log())
        code, out, err = self.command('logout')
        self.assertEqual((code, out), (1, ''))
        self.assertIn('watches no session of its own', err)
        self.assertEqual((self.mine(pid), self.labwc.poll(), self.asked()), (True, None, []))
        self.labwc.stdin.close()  # and that labwc's end is not this supervisor's session's
        self.labwc.wait(5)
        time.sleep(0.5)
        self.assertEqual((self.process.poll(), self.status()['state'], self.status()['session_over']),
                         (None, 'IN_WORLD', None))

    def test_restart_saves_closes_and_starts_the_game_again_in_the_same_session(self):
        self.start()
        self.windows()
        pid, _ = self.game()
        instance = self.status()['instance']
        self.assertEqual(self.command('restart'), (0, 'Stopped: the home was saved first; Minecraft closed. '
                                                      'Minecraft is starting again.\n', ''))
        self.assertFalse(self.mine(pid))
        self.wait(lambda: self.games() == 2 and (lambda status: status['state'] == 'IN_WORLD'
                                                 and status['lifecycle'] is True)(self.status()))
        new, env = self.game()
        self.assertNotEqual(new, pid)
        self.assertEqual((self.status()['instance'], env['ARESOS_DESKTOP_INSTANCE']), (instance, instance))
        self.assertEqual(self.save()['result'], 'saved')  # the new game's channel is the one in use
        self.assertEqual(self.last_stop(), (False, 'restart', 'saved', 'exited', 143))
        # A restart whose save fails leaves the game running and says why.
        self.mode('error')
        code, out, err = self.command('restart')
        self.assertEqual((code, out), (1, ''))
        self.assertTrue(err.startswith('Not restarted: Minecraft keeps running. Not saved:'), err)
        status = self.status()
        self.assertEqual((self.mine(new), self.games(), status['reason']), (True, 2, 'save_failed_restart'))
        self.assertIn('Minecraft was not restarted, because', status['message'])
        self.assertEqual(desktop.request(self.paths, {'op': 'restart', 'reason': 'shutdown'}, timeout=5)['error'],
                         'bad_reason')
        self.assertEqual(self.games(), 2)

    # -- 3.4: the black screen and the lid block

    BLACK = '--black --limit 90'
    LID = ('--what=handle-lid-switch:sleep --who=AresOS --mode=block --why=AresOS is saving your home before '
           'Minecraft stops /usr/bin/sleep 90')

    def noted(self, name):
        """What the stand-in covers (`covers`) or lid blocks (`inhibits`) noted: [start or end, PID, arguments]."""
        path = self.control / name
        return [line.split(' ', 2) for line in path.read_text().splitlines()] if path.exists() else []

    def up(self, name, arguments):
        """The PIDs of the stand-ins started with these arguments that have not ended."""
        notes = self.noted(name)
        ended = {note[1] for note in notes if note[0] == 'end'}
        return [note[1] for note in notes if note[:1] == ['start'] and note[2:] == [arguments] and note[1] not in ended]

    def test_a_restart_goes_black_holds_the_lid_block_and_hands_over_to_the_startup_cover(self):
        self.start()
        self.windows()
        self.assertEqual((self.status()['black'], self.noted('inhibits')), (False, []))
        self.assertEqual(self.command('restart')[0], 0)
        self.wait(lambda: self.games() == 2 and self.status()['state'] == 'IN_WORLD')
        self.wait(lambda: not self.up('covers', self.BLACK) and not self.up('covers', '--again'))
        notes = [note[0] + ' ' + note[2] if note[0] == 'start' else 'end' for note in self.noted('covers')]
        # The session's first cover and its end; then black, the restart's cover over it, and both end.
        self.assertEqual(notes, ['start ', 'end', 'start ' + self.BLACK, 'start --again', 'end', 'end'])
        # One lid block for the length of the stop: it ended with it, and the session goes on.
        self.wait(lambda: len(self.noted('inhibits')) == 2)
        (start, pid, arguments), (end, ended) = self.noted('inhibits')
        self.assertEqual((start, arguments, end, ended), ('start', self.LID, 'end', pid))
        status = self.status()
        self.assertEqual((status['black'], status['lid_block']), (False, False))
        log = self.log()
        self.assertLess(log.index('the screens go black'), log.index('SIGTERM sent to Java'))
        self.assertFalse(self.mine(int(pid)))

    def test_an_app_window_that_appears_while_the_screens_are_black_takes_the_black_away_at_once(self):
        self.start(STOP_SAVE_WAIT=4.0)
        self.windows()
        pid, _ = self.game()
        self.mode('hang')
        replies = []
        thread = threading.Thread(
            target=lambda: replies.append(desktop.request(self.paths, {'op': 'restart'}, timeout=30)))
        thread.start()
        self.addCleanup(thread.join, 30)
        self.wait(lambda: self.up('covers', self.BLACK) and self.up('inhibits', self.LID))
        self.assertIs(self.status()['black'], True)
        started = time.monotonic()
        (self.control / 'windows').write_text(json.dumps({'event': 'windows', 'count': 1, 'names': ['Mail']}))
        self.wait(lambda: not self.up('covers', self.BLACK))
        self.assertLess(time.monotonic() - started, 2.0)
        status = self.status()
        # The stop goes on behind his app, with its lid block.
        self.assertEqual((status['stopping'], status['black'], status['lid_block'], status['windows']),
                         (True, False, True, ['Mail']))
        self.assertTrue(self.up('inhibits', self.LID))
        thread.join(30)
        self.assertEqual((replies[0]['result'], self.mine(pid), self.games()), ('called_off', True, 1))
        self.wait(lambda: not self.up('inhibits', self.LID))
        self.assertIs(self.status()['lid_block'], False)

    def test_a_session_that_ends_stays_black_until_the_supervisor_exits_and_leaves_nothing_behind(self):
        self.start()
        self.windows()
        pid, _ = self.game()
        self.process.terminate()
        self.assertIsNotNone(self.process.wait(15))
        self.assertFalse(self.mine(pid))
        self.wait(lambda: len(self.noted('inhibits')) == 2 and len(self.noted('covers')) == 4)
        self.assertEqual([note[0] + ' ' + note[2] if note[0] == 'start' else 'end' for note in self.noted('covers')],
                         ['start ', 'end', 'start ' + self.BLACK, 'end'])
        self.assertEqual(self.noted('inhibits')[0][2], self.LID)
        log = self.log()
        # Black from the stop's start, and never taken away while the supervisor lived: it ended with its exit.
        self.assertLess(log.index('the screens go black'), log.index('SIGTERM sent to Java'))
        self.assertNotIn('the black screen ends', log)
        for note in self.noted('covers') + self.noted('inhibits'):
            self.assertFalse(self.mine(int(note[1])), note)

    def test_the_command_without_a_supervisor_says_not_saved(self):
        empty = self.root / 'empty-run'
        empty.mkdir()
        code, out, err = self.command('save', runtime=empty)
        self.assertEqual((code, out), (1, ''))
        self.assertTrue(err.startswith('Not saved: the AresOS desktop supervisor did not answer'), err)

    def test_use_home_is_refused_while_the_game_runs_and_moves_the_folder_once_nothing_runs(self):
        old = 'AresHub-2026-11-19_10-00-00-000'
        worlds = pathlib.Path(self.paths.worlds)
        base.make_world(self.paths, dict(self.lock, world=old))
        inode = (worlds / old).stat().st_ino

        def folders():
            return sorted((path.name, path.stat().st_ino) for path in worlds.iterdir())

        before = folders()
        code, out, err = self.command('use-home', old)  # no supervisor: nobody can tell whether a game runs
        self.assertEqual((code, out), (1, ''))
        self.assertTrue(err.startswith('Not moved: the AresOS desktop supervisor did not answer'), err)
        self.start()
        self.assertEqual(self.command('use-home', old), (
            1, '', 'Not moved: Minecraft is running. Stop it first (aresos-desktop stop), then try again.\n'))
        self.assertEqual(self.command('use-home', 'AresHub'), (
            1, '', 'Not moved: use-home takes the name of a dated home in ~/.local/share/aresos/worlds: '
                   'AresHub-<date> or AresHub-new-<date>.\n'))
        self.assertEqual(self.command('stop')[0], 0)
        self.assertEqual(self.command('use-home', old), (
            1, '', 'Not moved: AresHub exists. use-home only fills the place of a missing home and never replaces '
                   'one.\n'))
        self.assertEqual(folders(), before)
        os.rename(worlds / 'AresHub', worlds / 'kept-by-him')  # the test's own folder, as he would move his away
        self.assertEqual(self.command('use-home', old + '/'), (  # as the shell completes the name
            0, f'{old} is your home AresHub now (the folder was renamed; nothing was deleted). Type retry.\n', ''))
        self.assertEqual(folders(), sorted([('AresHub', inode), ('kept-by-him', dict(before)['AresHub'])]))
        self.assertTrue((worlds / 'kept-by-him/level.dat').is_file())
        self.assertIn(f'moved the world folder {old} to AresHub', self.log())
        self.assertEqual(self.status()['leftovers'], [])
        self.assertEqual(self.command('retry')[0], 0)  # the home it became opens
        self.wait(lambda: self.status()['state'] == 'IN_WORLD')
        self.assertEqual(self.games(), 2)
        fd = desktop.take_desktop_lock(self.paths)  # the new game's wrapper holds the lock the move had taken
        self.assertIsNone(fd)


if __name__ == '__main__':
    unittest.main()
