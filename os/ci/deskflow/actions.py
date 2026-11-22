"""Guest actions for the DRM output gate. The virtio layer is the only caller."""
import contextlib
import ctypes
import errno
import json
import os
import pathlib
import pwd
import re
import select
import signal
import socket
import subprocess
import time

PROC = pathlib.Path('/proc')
VT = pathlib.Path('/sys/class/tty/tty0/active')
PORTAL = '/usr/libexec/aresos-input-portal'
BUS_NAME = 'org.freedesktop.impl.portal.desktop.aresos-input'
GEOMETRY = re.compile(r'Screen \{ name: "([^"]+)", zone: Zone \{ width: (\d+), height: (\d+), '
                      r'x: (-?\d+), y: (-?\d+) \}')
HELPER = '/usr/libexec/aresos-input-sharing-set'
DESKTOP_ID = 'org.deskflow.deskflow'
HUB_ID = 'org-deskflow-deskflow'
LAUNCH_ID = '3213213213213213'
UNIT = f'app-aresos-{DESKTOP_ID}-{LAUNCH_ID}.scope'
SYS_PIDFD_GETFD = 438
session = None
listener = None
# The real frontend, its monitor and Deskflow, kept from the backend state's readiness to the end of the boot.
running = contextlib.ExitStack()


def labwc_pid(uid):
    pids = []
    for proc in PROC.iterdir():
        if proc.name.isdigit():
            try:
                if proc.stat().st_uid == uid and os.readlink(proc / 'exe') == '/usr/bin/labwc':
                    pids.append(int(proc.name))
            except OSError:
                pass
    return pids[0] if len(pids) == 1 else None


def environ(pid):
    return dict(entry.split('=', 1) for entry in (PROC / str(pid) / 'environ').read_text().split('\0') if entry)


def guest_command(*argv, **kwargs):
    return subprocess.run(session['prefix'] + list(argv), capture_output=True, text=True, timeout=15, **kwargs)


def require(result):
    assert result.returncode == 0, (result.args[-5:], result.returncode, result.stdout, result.stderr)
    return result.stdout


def wait_for(read, description, timeout=30):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = read()
        if last:
            return last
        time.sleep(0.25)
    raise TimeoutError(f'{description}: {last!r}')


def connect_session():
    # Use the image's user declaration and the compositor's bus and runtime directory.
    declaration = pathlib.Path('/usr/lib/sysusers.d/aresos.conf').read_text().splitlines()
    _, name, *_ = next(line.split() for line in declaration if line.startswith('u '))
    user = pwd.getpwnam(name)
    pid = labwc_pid(user.pw_uid)
    if not pid:
        return None
    env = environ(pid)
    runtime = pathlib.Path(env['XDG_RUNTIME_DIR'])
    sockets = [path for path in runtime.glob('wayland-*') if path.is_socket() and path.stat().st_uid == user.pw_uid]
    if len(sockets) != 1:
        return None
    wayland = sockets[0].name
    bus = env['DBUS_SESSION_BUS_ADDRESS']
    assert env['XDG_CURRENT_DESKTOP'] == 'AresOS'
    prefix = ['runuser', '-u', name, '--', 'env', '-i', 'PATH=/usr/bin:/usr/sbin', 'LANG=C.UTF-8',
              f'HOME={user.pw_dir}', f'XDG_RUNTIME_DIR={runtime}', f'DBUS_SESSION_BUS_ADDRESS={bus}',
              f'WAYLAND_DISPLAY={wayland}', 'XDG_CURRENT_DESKTOP=AresOS']
    return dict(pid=pid, uid=user.pw_uid, prefix=prefix, runtime=runtime, bus=bus, wayland=wayland)


def session_log():
    path = session['runtime'] / 'deskflow-ci-session.log'
    return re.sub(r'\x1b\[[\d;]*m', '', path.read_text(errors='replace'))


def check_compositor():
    pid = labwc_pid(session['uid'])
    log = session_log()
    journal = subprocess.run(['journalctl', '-b', '--no-pager', '-q', '-o', 'cat', f'_PID={session["pid"]}'],
                             capture_output=True, text=True, timeout=10, check=True).stdout
    log += journal
    assert pid == session['pid'] and 'Assertion' not in log, (session['pid'], pid, log[-6000:])
    if listener is not None:
        assert listener.poll() is None, 'listen-only Wayland connection ended'
    if 'backend_owner' in session:
        assert backend_owner() == session['backend_owner'], 'original backend lost its bus name'
        if session.get('worker'):
            assert backend_connections() == 1, 'the backend Wayland worker stopped during the run'
    elif session.get('state') in ('none', 'listener') or session.get('worker') is False:
        # Normal activation: the frontend may start the backend, but with sharing off it holds no Wayland
        # connection, so nobody but the listener is on the output manager.
        assert not backend_connections(), 'input portal held a Wayland connection during a DRM control case'


def bus(*args):
    return require(guest_command('busctl', '--user', '--no-pager', *args)).strip()


def backend_running():
    answer = bus('call', 'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                 'NameHasOwner', 's', BUS_NAME)
    assert answer in ('b true', 'b false'), answer
    return answer == 'b true'


def backend_owner():
    kind, owner = bus('call', 'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                      'GetNameOwner', 's', BUS_NAME).split()
    assert kind == 's' and owner.startswith('":') and owner.endswith('"'), (kind, owner)
    return owner[1:-1]


def wayland_connections(pid):
    """How many of `pid`'s sockets are connected to the session's Wayland socket: each socket descriptor is
    copied here with pidfd_getfd(2) (root) and asked for its peer, so the backend's own word isn't needed."""
    display = str(session['runtime'] / session['wayland'])
    libc = ctypes.CDLL(None, use_errno=True)
    count = 0
    pidfd = os.pidfd_open(pid)
    try:
        for name in os.listdir(PROC / str(pid) / 'fd'):
            try:
                if not os.readlink(PROC / str(pid) / 'fd' / name).startswith('socket:'):
                    continue
            except FileNotFoundError:
                continue
            fd = libc.syscall(SYS_PIDFD_GETFD, pidfd, int(name), 0)
            if fd < 0:
                error = ctypes.get_errno()
                if error == errno.EBADF:  # The target closed the descriptor after readlink.
                    continue
                raise OSError(error, f'pidfd_getfd of descriptor {name} of process {pid}')
            try:
                sock = socket.socket(fileno=fd)
            except OSError as error:
                os.close(fd)
                if error.errno == errno.ENOTSOCK:  # The descriptor was closed and reused.
                    continue
                raise
            with sock:
                try:
                    count += sock.family == socket.AF_UNIX and sock.getpeername() == display
                except OSError as error:
                    if error.errno != errno.ENOTCONN:
                        raise
    finally:
        os.close(pidfd)
    return count


def backend_connections():
    """None when no backend runs, else its number of Wayland connections."""
    if not backend_running():
        return None
    return wayland_connections(backend_pid(backend_owner()))


def backend_pid(owner):
    words = bus('call', 'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                'GetConnectionUnixProcessID', 's', owner).split()
    assert words[0] == 'u' and len(words) == 2, words
    return int(words[1])


def ready(request):
    global session, listener
    assert session is None
    state = request['state']
    assert state in ('none', 'listener', 'backend'), state
    session = wait_for(connect_session, 'real labwc session', timeout=120)
    session['state'] = state
    initial = wait_for(lambda: randr() if active_primary() else None, 'Virtual-1 enabled', timeout=90)
    initial_pid = session['pid']
    proof = dict(state=state, labwc_pid=initial_pid, wayland=session['wayland'], outputs=initial)
    if state == 'listener':
        path = session['runtime'] / 'deskflow-ci-listener.log'
        with path.open('w') as log:
            listener = subprocess.Popen(session['prefix'] + ['/usr/libexec/aresos-ci/wl-harness', 'outputs'],
                                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        proof['first_list'] = wait_for(
            lambda: (report if 'OUTPUT Virtual-1\n' in (report := path.read_text())
                     and 'OUTPUTS_READY ' in report else None), 'listen-only output list')
    # First boot, sharing off, normal activation: the frontend may have started the backend already.
    assert not pathlib.Path('/etc/aresos/input-portal/sharing').exists()
    proof['first_boot_backend'] = backend_connections()
    assert not proof['first_boot_backend'], 'the backend held a Wayland connection with sharing off'
    if state == 'backend':
        ready_backend(proof)
    check_compositor()
    return dict(returncode=0, **proof)


def ready_backend(proof):
    """The backend with its Wayland worker running: sharing on, and the real Deskflow's session through the real
    frontend, both kept for the boot. The worker starts only for that session."""
    if backend_running():
        # Started by the frontend at login, at the default log level: the zone checks need debug.
        pid = backend_pid(backend_owner())
        os.kill(pid, signal.SIGTERM)
        wait_for(lambda: not backend_running(), 'the login-activated backend stopped', timeout=10)
    # Set the log level for this activation alone. Use the socket of the real session.
    require(guest_command('env', 'ARESOS_INPUT_PORTAL_LOG=debug', 'dbus-update-activation-environment',
                          'ARESOS_INPUT_PORTAL_LOG', 'WAYLAND_DISPLAY', 'XDG_CURRENT_DESKTOP'))
    require(subprocess.run([HELPER, 'on'], capture_output=True, text=True, timeout=10))
    assert require(guest_command(PORTAL, '--status')).strip() == 'no sessions'
    owner = backend_owner()
    pid = backend_pid(owner)
    env = environ(pid)
    assert env['DBUS_SESSION_BUS_ADDRESS'] == session['bus']
    assert env['WAYLAND_DISPLAY'] == session['wayland']
    assert env['XDG_CURRENT_DESKTOP'] == 'AresOS'
    assert os.readlink(PROC / str(pid) / 'exe') == PORTAL
    assert (PROC / str(pid)).stat().st_uid == session['uid']
    assert wayland_connections(pid) == 0, 'sharing on and no session: nothing needs the Wayland worker'
    session['backend_owner'] = owner
    proof.update(backend_owner=owner, backend_pid=pid, on_without_session=0)
    session['identity'] = start_deskflow()
    assert wayland_connections(pid) == 1, 'the session did not start the Wayland worker'
    session['worker'] = True
    proof['worker_connections'] = 1


def start_deskflow():
    """The real frontend, a monitor of CreateSession2 and Deskflow launched as the hub launches it, in a fixture
    profile; returns the caller's identity once the backend has its session."""
    root = session['runtime'] / 'deskflow-ci-identity'
    layout = root / 'Deskflow'
    require(guest_command('mkdir', '-p', str(layout)))
    (layout / 'Deskflow.conf').write_text('[core]\ncomputerName=fixture\ninterface=127.0.0.1\n')
    (layout / 'deskflow-server.conf').write_text('section: screens\n    fixture:\nend\n')
    session['identity_root'] = root
    frontend, monitor, core = root / 'frontend.log', root / 'monitor.log', root / 'core.log'
    launch = f"""
import runpy
shell = runpy.run_path('/usr/libexec/aresos-shell')
apps, _ = shell['load_catalogue'](shell['REGISTRY'])
app = apps[{HUB_ID!r}]
launcher = shell['ScopeLauncher']()
assert launcher.unit(app, {LAUNCH_ID!r}) == {UNIT!r}
argv, work, reason = shell['resolve'](app)
assert reason is None, reason
import os
cmd = launcher.command(app, argv, {LAUNCH_ID!r})
os.chdir(launcher.working_directory(work))
os.execve(cmd[0], cmd, launcher.environment(app))
"""
    try:
        running.enter_context(logged_process(frontend, ['/usr/libexec/xdg-desktop-portal', '--verbose', '--replace']))
        wait_for(lambda: 'org.freedesktop.portal.Desktop acquired' in frontend.read_text(),
                 'real frontend acquired its name')
        routes = frontend.read_text()
        assert "Using portal configuration file '/usr/share/xdg-desktop-portal/aresos-portals.conf'" in routes, routes
        assert all(f'Using aresos-input.portal for org.freedesktop.impl.portal.{name}' in routes
                   for name in ('InputCapture', 'Clipboard')), routes
        running.enter_context(logged_process(monitor, [
            '/usr/bin/dbus-monitor', '--session',
            "type='method_call',interface='org.freedesktop.portal.InputCapture',member='CreateSession2'",
        ]))
        wait_for(lambda: 'member=NameAcquired' in monitor.read_text(), 'input capture monitor ready')
        count = session_log().count('session created')
        running.enter_context(logged_process(core, ['env', f'XDG_CONFIG_HOME={root}', 'python3', '-B', '-c', launch]))

        def observe():
            match = re.search(r'method call .*?sender=(:[\d.]+).*?member=CreateSession2', monitor.read_text())
            return match[1] if match else None

        sender = wait_for(observe, 'Deskflow CreateSession2')
        pid = backend_pid(sender)
        executable = os.readlink(PROC / str(pid) / 'exe')
        assert executable == '/usr/bin/deskflow-core', executable
        assert UNIT in (PROC / str(pid) / 'cgroup').read_text().strip().split('/'), UNIT
        line = wait_for(lambda: next((line for line in session_log().splitlines()
                                     if 'session created' in line and f'app_id="{DESKTOP_ID}"' in line), None),
                        'the backend received the native Deskflow ID')
        assert session_log().count('session created') == count + 1
        wait_for(lambda: 'Wayland worker started' in session_log(), 'the backend started its Wayland worker')
        return dict(sender=sender, pid=pid, exe=executable, scope=UNIT, backend=line,
                    frontend_routes=routes.splitlines())
    except (OSError, AssertionError, TimeoutError) as error:
        logs = {path.name: path.read_text()[-2500:] for path in (frontend, monitor, core) if path.exists()}
        raise AssertionError((str(error), logs)) from error


def randr():
    result = guest_command('wlr-randr', '--json')
    return {head['name']: head for head in json.loads(require(result))}


def active_primary():
    result = guest_command('wlr-randr', '--json')
    if result.returncode:
        return False
    return any(head['name'] == 'Virtual-1' and head['enabled'] for head in json.loads(result.stdout))


def active_mode(head):
    return next(mode for mode in head['modes'] if mode['current'])


def zones(outputs):
    result = {}
    for name, head in outputs.items():
        if not head['enabled']:
            continue
        mode = active_mode(head)
        width, height = mode['width'], mode['height']
        if '90' in head['transform'] or '270' in head['transform']:
            width, height = height, width
        result[name] = [int(width / head['scale']), int(height / head['scale']),
                        head['position']['x'], head['position']['y']]
    return result


def backend_zones(expected):
    def current():
        lines = [line for line in session_log().splitlines() if 'screen geometry' in line]
        if not lines:
            return None
        logged = {name: [int(value) for value in (w, h, x, y)]
                  for name, w, h, x, y in GEOMETRY.findall(lines[-1])}
        if logged == expected and (logged or 'screens=[]' in lines[-1]):
            return lines[-1]
        return None
    return wait_for(current, f'backend zones match {expected!r}', timeout=6)


def drm_connectors():
    return {node.parent.name: node.read_text().strip() for node in pathlib.Path('/sys/class/drm').glob('*/status')}


def snapshot(request):
    check_compositor()
    outputs = randr()
    geometry = zones(outputs)
    result = dict(returncode=0, labwc_pid=session['pid'], outputs=outputs, zones=geometry,
                  connectors=drm_connectors(), vt=VT.read_text().strip())
    if 'backend_owner' in session and request.get('geometry', True) and session.get('last_geometry') != geometry:
        result['backend_zones'] = backend_zones(geometry)
        session['last_geometry'] = geometry
    check_compositor()
    return result


def change(request):
    name, option = request['output'], request['option']
    assert re.fullmatch(r'Virtual-\d+', name), name
    assert option in ('off', 'mode', 'custom-mode'), option
    args = ['--off']
    if option != 'off':
        mode = request['mode']
        assert re.fullmatch(r'\d+x\d+(?:@\d+(?:\.\d+)?Hz)?', mode), mode
        args = ['--on', '--' + option, mode]
    check_compositor()
    result = guest_command('wlr-randr', '--output', name, *args)
    check_compositor()
    return dict(returncode=0, stdout=require(result), stderr=result.stderr)


def vt(request):
    expected = request['expected']
    assert expected in ('tty1', 'tty3'), expected
    observed = wait_for(lambda: VT.read_text().strip() == expected, f'VT switched to {expected}')
    check_compositor()
    return dict(returncode=0, labwc_pid=session['pid'], vt=expected, observed=observed)


@contextlib.contextmanager
def logged_process(log, argv):
    with log.open('w') as stream:
        process = subprocess.Popen(session['prefix'] + argv, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    try:
        yield process
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)


def identity(_request):
    """The real Deskflow caller traced through the real portal (started at readiness), then sharing back off."""
    proof = session['identity']
    first = require(guest_command(PORTAL, '--status')).splitlines()
    assert len(first) == 1 and DESKTOP_ID in first[0], first
    time.sleep(1)
    kept = require(guest_command(PORTAL, '--status')).splitlines()
    assert len(kept) == 1 and kept[0].split(': app=', 1)[0] == first[0].split(': app=', 1)[0], kept
    owner = session['backend_owner']
    pid = backend_pid(owner)
    assert wayland_connections(pid) == 1
    # Off must end the original process, including its Wayland connection.
    pidfd = os.pidfd_open(pid)
    try:
        require(subprocess.run([HELPER, 'off'], capture_output=True, text=True, timeout=10))
        # The watch can win the race and exit before --revoke reaches the bus.
        revoked = require(guest_command(PORTAL, '--revoke')).strip()
        assert revoked.startswith(('sharing is off', 'no backend is running')), revoked
        assert select.select([pidfd], [], [], 3)[0], 'the original backend did not exit after Off'
    finally:
        os.close(pidfd)
    del session['backend_owner']
    session['worker'] = False
    assert require(guest_command(PORTAL, '--status')).strip() == 'no sessions'
    fresh = backend_owner()
    assert fresh != owner and wayland_connections(backend_pid(fresh)) == 0
    guest_command('systemctl', '--user', 'stop', UNIT)
    # The same guarded executable, started from outside the hub scope.
    root = session['identity_root']
    start_log = session_log().count('refused: the application has no ID')
    with logged_process(root / 'core-terminal.log', ['env', f'XDG_CONFIG_HOME={root}', '/usr/libexec/aresos-deskflow']):
        wait_for(lambda: session_log().count('refused: the application has no ID') > start_log,
                 'terminal launch refused with no app ID')
    check_compositor()
    return dict(returncode=0, app_id=DESKTOP_ID, hub_id=HUB_ID, terminal='empty ID refused',
                off=dict(revoke=revoked, worker_connections=0, stopped=True, fresh_owner=fresh), **proof)


def diagnostics(request):
    return dict(returncode=0, labwc_pid=labwc_pid(session['uid']), connectors=drm_connectors(),
                session_log=session_log()[-20000:])


ACTIONS = {'deskflow-ready': ready, 'deskflow-snapshot': snapshot, 'deskflow-change': change,
           'deskflow-vt': vt, 'deskflow-identity': identity, 'deskflow-diagnostics': diagnostics}
