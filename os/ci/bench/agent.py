"""Guest-only service. The virtio channel never carries launch credentials."""
import json
import os
import pathlib
import pwd
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time

from channel import Frames, frame

PORT = pathlib.Path('/dev/virtio-ports/org.aresos.bench')
OUTPUT_LIMIT = 256 * 1024


def captured(argv, timeout=10):
    with tempfile.TemporaryFile() as output:
        with subprocess.Popen(['prlimit', f'--fsize={OUTPUT_LIMIT + 1}', '--', *argv],
                              stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                              start_new_session=True) as child:
            try:
                code = child.wait(timeout=timeout)
            finally:
                # A command may leave children holding the capture file open.
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        output.seek(0)
        raw = output.read(OUTPUT_LIMIT + 1)
        if len(raw) > OUTPUT_LIMIT:
            raise ValueError('Guest output exceeds the cap')
    return code, raw.decode(errors='replace')


def desktop_user():
    user = pwd.getpwnam('ares')
    runtime = pathlib.Path(f'/run/user/{user.pw_uid}')
    return user, runtime


def as_desktop(*argv, session=False):
    user, runtime = desktop_user()
    env = dict(HOME=user.pw_dir, USER=user.pw_name, LOGNAME=user.pw_name, XDG_RUNTIME_DIR=str(runtime),
               PATH='/usr/local/bin:/usr/bin:/usr/sbin')
    if session:
        pid = labwc_pid(user.pw_uid)
        if pid is None:
            raise ValueError('Desktop compositor is not running')
        for item in pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
            if item.startswith(b'DBUS_SESSION_BUS_ADDRESS='):
                env['DBUS_SESSION_BUS_ADDRESS'] = item.split(b'=', 1)[1].decode()
        displays = sorted(path.name for path in runtime.glob('wayland-*') if stat.S_ISSOCK(path.lstat().st_mode))
        if len(displays) != 1 or 'DBUS_SESSION_BUS_ADDRESS' not in env:
            raise ValueError('Desktop socket or bus not ready')
        env['WAYLAND_DISPLAY'] = displays[0]
    return ['runuser', '-u', user.pw_name, '--', 'env', '-i',
            *(f'{key}={value}' for key, value in env.items()), *argv]


def labwc_pid(uid):
    code, output = captured(['pgrep', '-u', str(uid), '-x', 'labwc'])
    return output.split()[0] if code == 0 else None


def session_status(user):
    # Resolve the user's local session the same way as the existing VM policy
    # test, then require an active greetd session containing the compositor.
    code, sessions = captured(['loginctl', 'list-sessions', '--no-legend'])
    pid = labwc_pid(user.pw_uid)
    cgroup_paths = []
    if pid:
        try:
            cgroup_paths = pathlib.Path(f'/proc/{pid}/cgroup').read_text().splitlines()
        except FileNotFoundError:
            pass
    facts = dict(greetd_running=captured(['systemctl', 'is-active', '--quiet', 'greetd.service'])[0] == 0,
                 initial_login_attempted=pathlib.Path('/run/greetd.run').exists(),
                 compositor_running=bool(pid), seat_session=False, active_greetd_session=False,
                 compositor_in_session=False)
    if code == 0:
        for line in sessions.splitlines():
            columns = line.split()
            if len(columns) < 4 or columns[2:4] != [user.pw_name, 'seat0']:
                continue
            facts['seat_session'] = True
            code, output = captured(['loginctl', 'show-session', columns[0], '-p', 'Service', '-p', 'Active',
                                     '-p', 'Remote', '-p', 'Scope'])
            fields = dict(item.split('=', 1) for item in output.splitlines() if '=' in item)
            if code != 0 or any(fields.get(name) != value for name, value in (
                    ('Service', 'greetd'), ('Active', 'yes'), ('Remote', 'no'))):
                continue
            facts['active_greetd_session'] = True
            scope = fields.get('Scope')
            if scope and any(scope in row.split('/') for row in cgroup_paths):
                facts['compositor_in_session'] = True
                break
    return facts


def status():
    user, _ = desktop_user()
    facts = session_status(user)
    manifest = pathlib.Path('/usr/share/aresos/manifest/aresos-mod.json')
    return dict(boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                revision=json.loads(manifest.read_bytes())['source_revision'],
                active_session=facts['compositor_in_session'], session=facts,
                no_nic=os.listdir('/sys/class/net') == ['lo'])


def probe_helper(runtime):
    # A fresh SETUP session has no game connection. Authenticate the same way the
    # game would, issue only list_apps, and project the result to the exit code.
    identity = json.loads((runtime / 'aresos/desktop-runtime.json').read_bytes())
    with socket.socket(socket.AF_UNIX) as helper:
        helper.settimeout(3)
        helper.connect(str(runtime / 'aresos/shell.sock'))
        incoming = Frames(helper.recv)

        def request(op, **fields):
            helper.sendall(frame(dict(protocol='aresos-shell/1.1', id=op, op=op, **fields)))
            for _ in range(32):
                reply = incoming.receive()
                if reply.get('id') == op:
                    if reply.get('ok') is not True:
                        raise ValueError('Session helper refused request')
                    return reply
            raise ValueError('No matching helper reply')

        request('hello', major=1, minor=1, requires=['list_apps'],
                instance=identity['instance'], nonce=identity['nonce'])
        reply = request('list_apps')
        return (isinstance(reply.get('revision'), str)
                and isinstance(reply.get('apps'), list) and bool(reply['apps']))


def action(request):
    verb = request['action']
    if verb == 'status':
        return status()
    if verb == 'health':
        code, _ = captured(as_desktop(sys.executable, '-B', __file__, '--probe-helper'))
        return dict(healthy=code == 0)
    if verb == 'exec':
        argv = request['argv']
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
            raise ValueError('Invalid command')
        code, output = captured(as_desktop(*argv, session=True), timeout=30)
        return dict(code=code, output=output)
    if verb == 'journal':
        code, output = captured(['journalctl', '-b', '-u', 'greetd.service', '-n', '80', '--no-pager', '-o', 'cat'])
        return dict(code=code, output=output)
    if verb == 'reboot':
        # Leave time to acknowledge the request over virtio before systemd stops us.
        code, _ = captured(['systemd-run', '--quiet', '--on-active=2s', '--timer-property=AccuracySec=100ms',
                            '--unit=aresos-bench-reboot', '/usr/bin/systemctl', '--no-block', 'reboot'])
        return dict(scheduled=code == 0)
    raise ValueError('Unknown guest action')


def serve():
    deadline = time.monotonic() + 60
    while not PORT.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('Bench virtio port absent')
        time.sleep(0.2)
    with PORT.open('r+b', buffering=0) as stream:
        incoming = Frames(stream.read)

        def send(value):
            data = memoryview(frame(value))
            while data:
                written = stream.write(data)
                if not written:
                    raise EOFError('Bench virtio port stopped accepting data')
                data = data[written:]

        send(dict(ready=True, protocol=1))
        while True:
            request = incoming.receive()
            try:
                answer = action(request)
            except (KeyError, OSError, ValueError, subprocess.SubprocessError):
                answer = {'error': True}
            send(dict(id=request['id'], **answer))


if __name__ == '__main__':
    if sys.argv[1:] == ['--probe-helper']:
        try:
            healthy = probe_helper(pathlib.Path(os.environ['XDG_RUNTIME_DIR']))
        except (EOFError, KeyError, OSError, ValueError):
            healthy = False
        sys.exit(0 if healthy else 1)
    serve()
