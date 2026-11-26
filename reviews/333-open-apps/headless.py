#!/usr/bin/python3
"""Run package 333 helper checks in a private labwc session and private D-Bus."""
import fcntl
import json
import os
from pathlib import Path
import select
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'os/config/usr/libexec/aresos-shell'
WORK = ROOT / '.work'
APP_ID = 'aresos.fixture.browser'


def wait_for(predicate, what):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if result := predicate():
            return result
        time.sleep(0.02)
    raise AssertionError(f'timed out waiting for {what}')


def restore_check():
    sys.path.insert(0, str(ROOT / 'os/tests'))
    from test_aresos_shell import shell
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    assert runtime.parent.parent == WORK and runtime.parent.name.startswith('h333-')
    assert os.environ['WAYLAND_DISPLAY'] != 'wayland-0' and os.environ.get('DISPLAY') != ':0'
    assert 'DBUS_SESSION_BUS_ADDRESS' in os.environ
    registry = runtime.parent / 'apps'
    registry.mkdir()
    (registry / 'browser.json').write_text(json.dumps({
        'schema': 1, 'id': 'browser', 'name': 'Test Browser', 'argv': ['/usr/bin/false'],
        'window': {'app_ids': [APP_ID], 'instance': 'multi'},
    }))
    instance = 'test-session-333'
    nonce = 'synthetic-restore-credentials'
    token = 'F' * 43
    helper_env = dict(os.environ, ARESOS_DESKTOP_INSTANCE=instance, ARESOS_LAUNCH_NONCE=nonce,
                      ARESOS_VIEW_TOKEN=token)
    socket_path = runtime / 'aresos/shell.sock'

    def start(stack, *args, **options):
        process = subprocess.Popen(args, **options)

        def close():
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        stack.callback(close)
        return process

    with ExitStack() as stack:
        windows = shell.Windows()
        observer = shell.ForeignToplevels.connect(windows)
        stack.callback(observer.sock.close)
        helper = start(stack, sys.executable, str(HELPER), '--registry', str(registry), env=helper_env)
        wait_for(socket_path.is_socket, 'the private helper socket')

        def read_windows():
            while select.select([observer.sock], [], [], 0)[0]:
                observer.readable()
            return {w.handle: w for w in windows.toplevels.values() if w.ready and w.app_id == APP_ID}

        def stand_in(title, known):
            start(stack, '/usr/bin/foot', f'--app-id={APP_ID}', f'--title={title}',
                  '/usr/bin/sleep', '60', stderr=subprocess.DEVNULL)
            return wait_for(lambda: next((w for w in read_windows().values()
                                          if w.handle not in known and w.activated), None), title)

        first = stand_in('first test window', set())
        second = stand_in('second test window', {first.handle})

        client = stack.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
        client.settimeout(10)
        client.connect(str(socket_path))
        reader = stack.enter_context(client.makefile('rb'))

        def send(op, request_id, **fields):
            request = dict(protocol='aresos-shell/1.3', id=request_id, op=op, **fields)
            client.sendall(json.dumps(request).encode() + b'\n')

        def until(predicate):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                message = json.loads(reader.readline())
                if predicate(message):
                    return message
            raise AssertionError('missing helper message')

        send('hello', 'h', major=1, minor=3, instance=instance, role='view', view='fixture', token=token,
             capabilities=['apps_state', 'activate_app'], requires=['apps_state', 'activate_app'])
        assert until(lambda m: m.get('id') == 'h')['ok']
        initial = until(lambda m: m.get('event') == 'apps_state')
        assert initial['apps'] == [dict(id='browser', windows=2, active=True, hidden=False)], initial

        assert observer.minimize(second.handle)
        wait_for(lambda: read_windows().get(second.handle) is second and second.minimized and not second.activated,
                 'the second window to minimize')
        wait_for(lambda: read_windows().get(first.handle) is first and first.activated, 'the first window to take focus')
        # Refocus the second before minimizing it with no other browser window eligible for the keyboard.
        # Otherwise labwc focuses the first browser window when the second is minimized, making the first the latest.
        assert observer.activate(second.handle)
        wait_for(lambda: read_windows().get(second.handle) is second and second.activated and not second.minimized,
                 'the second window to take focus again')
        assert observer.minimize(first.handle)
        wait_for(lambda: read_windows().get(first.handle) is first and first.minimized, 'the first window to minimize')
        assert observer.minimize(second.handle)
        hidden = until(lambda m: m.get('event') == 'apps_state' and m['apps'][0]['hidden'])
        assert hidden['apps'] == [dict(id='browser', windows=2, active=False, hidden=True)], hidden

        send('activate_app', 'restore-browser', app_id='browser')
        reply = until(lambda m: m.get('id') == 'restore-browser')
        assert reply == dict(protocol='aresos-shell/1.3', id='restore-browser', ok=True, state='activated'), reply
        wait_for(lambda: read_windows().get(second.handle) is second and second.activated and not second.minimized,
                 'the same second window to restore and take focus')
        assert first.minimized and not first.activated
        assert set(read_windows()) == {first.handle, second.handle}
        journal = json.loads((socket_path.parent / 'shell-journal.json').read_text())
        entries = list(journal['view_launches']['fixture'].values())
        assert len(entries) == 1 and entries[0]['state'] == 'activated'
        assert 'unit' not in entries[0] and 'launch_id' not in entries[0]
        assert helper.poll() is None
        print('PASS: real helper restored the most recently focused window on labwc with zero new spawns', flush=True)


def isolated(command):
    WORK.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='h333-', dir=WORK) as temporary:
        root = Path(temporary)
        for folder in ('home', 'run', 'state', 'config', 'cache', 'data', 'tmp'):
            (root / folder).mkdir(mode=0o700)
        (root / 'config/rc.xml').write_text(
            '<labwc_config><core><xwayland>no</xwayland></core></labwc_config>\n')
        env = dict(PATH='/usr/bin:/bin', HOME=str(root / 'home'), XDG_RUNTIME_DIR=str(root / 'run'),
                   XDG_STATE_HOME=str(root / 'state'), XDG_CONFIG_HOME=str(root / 'config'),
                   XDG_CACHE_HOME=str(root / 'cache'), XDG_DATA_HOME=str(root / 'data'),
                   TMPDIR=str(root / 'tmp'), LANG='C.UTF-8', LABWC_UPDATE_ACTIVATION_ENV='0',
                   WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_HEADLESS_OUTPUTS='1',
                   PYTHONDONTWRITEBYTECODE='1')
        status = root / 'status'
        launcher = root / 'run.sh'
        launcher.write_text('#!/usr/bin/bash\n'
                            'if [[ -z "$WAYLAND_DISPLAY" || "$WAYLAND_DISPLAY" == wayland-0 || "$DISPLAY" == :0 ]]; '
                            'then exit 1; fi\n'
                            f'{shlex.join(command)}\nprintf "%s\\n" "$?" > {shlex.quote(str(status))}\n')
        launcher.chmod(0o700)
        # Reserve the owner's display name even inside this empty, private runtime directory.
        with (root / 'run/wayland-0.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            subprocess.run(['/usr/bin/dbus-run-session', '--', '/usr/bin/labwc',
                            '--config-dir', str(root / 'config'), '--session', shlex.quote(str(launcher))],
                           env=env, timeout=120, check=True)
        if not status.is_file():
            raise RuntimeError('the private labwc session exited without a result')
        return int(status.read_text())


if __name__ == '__main__':
    if sys.argv[1:] == ['--restore']:
        restore_check()
    else:
        args = sys.argv[1:]
        if args:
            if len(args) != 1 or not args[0].startswith('test_aresos_shell') or Path(args[0]).name != args[0]:
                raise SystemExit('pass one helper test module filename')
            sys.exit(isolated([sys.executable, '-m', 'unittest', 'discover', '-s', 'os/tests', '-p', args[0]]))
        sys.exit(isolated([sys.executable, str(Path(__file__).resolve()), '--restore']))
