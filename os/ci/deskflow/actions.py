"""Guest actions for the DRM output gate. The virtio layer is the only caller."""
from collections import Counter
import contextlib
from configparser import ConfigParser
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
import tempfile
import time
import uuid

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
    return dict(pid=pid, uid=user.pw_uid, name=name, home=pathlib.Path(user.pw_dir),
                prefix=prefix, runtime=runtime, bus=bus, wayland=wayland)


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
    # Set only the log level. The socket and desktop must come from the real login.
    require(guest_command('env', 'ARESOS_INPUT_PORTAL_LOG=debug', 'dbus-update-activation-environment',
                          'ARESOS_INPUT_PORTAL_LOG'))
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
    launch = hub_launch(LAUNCH_ID, UNIT)
    return observe_deskflow(launch, root, frontend, monitor, core)


def hub_launch(launch_id, unit):
    return f"""
import runpy
shell = runpy.run_path('/usr/libexec/aresos-shell')
apps, _ = shell['load_catalogue'](shell['REGISTRY'])
app = apps[{HUB_ID!r}]
launcher = shell['ScopeLauncher']()
assert launcher.unit(app, {launch_id!r}) == {unit!r}
argv, work, reason = shell['resolve'](app)
assert reason is None, reason
import os
cmd = launcher.command(app, argv, {launch_id!r})
os.chdir(launcher.working_directory(work))
os.execve(cmd[0], cmd, launcher.environment(app))
"""


def observe_deskflow(launch, root, frontend, monitor, core):
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
    if session.get('daily'):
        # The kernel can switch VTs before logind updates the state polkit uses.
        login = environ(session['pid'])['XDG_SESSION_ID']
        active = 'yes' if expected == 'tty1' else 'no'

        def login_active():
            result = subprocess.run(['loginctl', 'show-session', login, '-p', 'Active', '--value'],
                                    capture_output=True, text=True, timeout=5)
            return require(result).strip() == active

        wait_for(login_active, f'logind reports Active={active} on {expected}', timeout=10)
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
    if session is None:
        return dict(returncode=0, daily=True)
    if session.get('daily'):
        return dict(returncode=0, daily=True, **startup_diagnostics())
    return dict(returncode=0, labwc_pid=labwc_pid(session['uid']), connectors=drm_connectors(),
                session_log=session_log()[-20000:])


ACTIONS = {'deskflow-ready': ready, 'deskflow-snapshot': snapshot, 'deskflow-change': change,
           'deskflow-vt': vt, 'deskflow-identity': identity, 'deskflow-diagnostics': diagnostics}

# The daily-use checks have their own boot, outside the output-mode controls.
SWITCH = pathlib.Path('/etc/aresos/input-portal/sharing')
SWITCH_UI = '/usr/bin/aresos-input-sharing'
FRONTEND = 'org.freedesktop.portal.Desktop'
DBUS_SERVICE = 'org.freedesktop.DBus'
DBUS_PATH = '/org/freedesktop/DBus'
CORE = '/usr/bin/deskflow-core'
GUARD = '/usr/libexec/aresos-deskflow'
LOGIN_HOOK = '/usr/libexec/aresos-deskflow-login'
PAIR_TITLE = 'Pair a Mac with Deskflow'
SHARING_TITLE = 'Mouse and keyboard sharing'
KEY_MARKER = 'aresosinput321'
PASSWORD = 'fixture321'  # Disposable guest account only; identical on US and German keyboards.
OFF_REFUSAL = 'Deskflow requested a session while sharing is off'
CLIENT_DISPLAY = ':92'
WL_HARNESS = '/usr/libexec/aresos-ci/wl-harness'
LOG_DATA = re.compile(
    r'(?i)aresosinput321|aresosclip[0-9]+|\bon(?:Key|Mouse)\w+\s+(?:id=|[+-]?\d)|\b(?:switch|jump) from .* at -?\d+,-?\d+|\b(key(?:code|sym)|button(?:id|code)|cursor_position|delta_[xy])\s*[:=]'
    r'|\b(key|button)(?:[ _-]*(?:down|up|press|release|code|id))\s*[(:= ]\s*(?:0x[0-9a-f]+|\d+)'
    r'|\b(?:mouse move|pointer motion|cursor at|motion delta)\s*[(:= ]\s*[-\d]'
)
daily_state = {}


def status():
    return require(guest_command(PORTAL, '--status')).strip()


def backend_session(armed=True, capture=None):
    lines = status().splitlines()
    if len(lines) != 1 or f'app="{DESKTOP_ID}"' not in lines[0]:
        return None
    line = lines[0]
    if armed and ('enabled=true' not in line or 'barriers=0' in line):
        return None
    if capture is not None and f'capturing={str(capture).lower()}' not in line:
        return None
    return line.split(': app=', 1)[0]


def current_owner(name):
    if bus('call', DBUS_SERVICE, DBUS_PATH, DBUS_SERVICE, 'NameHasOwner', 's', name) == 'b true':
        return json.loads(bus('call', DBUS_SERVICE, DBUS_PATH, DBUS_SERVICE,
                              'GetNameOwner', 's', name).split(' ', 1)[1])
    return None


def stop_pid(pid, sig=signal.SIGTERM, timeout=6):
    pinned = os.pidfd_open(pid)
    try:
        signal.pidfd_send_signal(pinned, sig)
        assert select.select([pinned], [], [], timeout)[0], 'the selected process did not exit'
    finally:
        os.close(pinned)


def trace_backend():
    if backend_running():
        stop_pid(backend_pid(backend_owner()))
    require(guest_command('env', 'ARESOS_INPUT_PORTAL_LOG=trace', 'dbus-update-activation-environment',
                          'ARESOS_INPUT_PORTAL_LOG'))
    assert status() == 'no sessions'
    pid = backend_pid(backend_owner())
    assert environ(pid)['ARESOS_INPUT_PORTAL_LOG'] == 'trace'


def x_command(*argv, **kwargs):
    return guest_command('env', f'DISPLAY={CLIENT_DISPLAY}', *argv, **kwargs)


def windows():
    return json.loads(require(guest_command('python3', '-B', '/usr/libexec/aresos-ci/deskflow-window-state.py')))


def windows_with(title):
    return [window for window in windows() if window[1].startswith(title)]


def core_pids():
    matches = []
    for proc in PROC.iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid == session['uid'] and os.readlink(proc / 'exe') == CORE:
                cmdline = (proc / 'cmdline').read_bytes().split(b'\0')
                if cmdline[1:2] == [b'server']:
                    matches.append(int(proc.name))
        except OSError:
            continue
    return matches


def off_refusals(log):
    return sum(OFF_REFUSAL in line and f'app_id="{DESKTOP_ID}"' in line for line in log.splitlines())


def startup_diagnostics():
    try:
        log = session_log()
    except FileNotFoundError:
        log = ''
    # The state directory persists across reboots, including the previous boot's server.log.
    core = log + '\n' + (probe_log('server') if 'server' in daily_state.get('processes', {}) else '')
    lines = log.splitlines()
    safe_lines = [line for line in lines if not LOG_DATA.search(line)]
    evidence = dict(
        core_pids=core_pids(), source_profile=(session['home'] / '.config/Deskflow/Deskflow.conf').is_file(),
        created=log.count('session created'),
        off_refusals=off_refusals(log), worker_started='Wayland worker started' in log,
        worker_failed='could not start the Wayland worker' in log,
        refusals=Counter(reasons.group(1) for line in safe_lines
                         if (reasons := re.search(r'\brefused: (.*?)(?:\s+\w+=|$)', line))),
        core_selected_wayland='detected wayland platform' in core,
        scope_error='Failed to start transient scope unit' in core,
        configuration_error='failed to load config' in core,
        traceback='Traceback' in core,
        could_not_start='Could not start Deskflow' in core,
        session_log_tail=''.join(('' if LOG_DATA.search(line) else line) + '\n' for line in lines[-40:]),
    )
    # Keep the log even if the bus is down or the backend is stopped in a test.
    try:
        evidence['backend_connections'] = backend_connections()
        result = guest_command(PORTAL, '--status')
        evidence['status'] = result.stdout
        evidence['status_returncode'] = result.returncode
    except (AssertionError, OSError, subprocess.TimeoutExpired) as error:
        evidence['status_error'] = type(error).__name__
    return evidence


def start_probe(name, argv, *, display=False, pipe=False):
    target = daily_state['root'] / f'{name}.log'
    command = session['prefix'] + ([f'DISPLAY={CLIENT_DISPLAY}'] if display else []) + argv
    with target.open('w') as output:
        process = subprocess.Popen(command, stdin=subprocess.PIPE if pipe else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE if pipe else output, stderr=output,
                                   start_new_session=True, text=True)
    daily_state['processes'][name] = process
    return process


def stop_probe(name):
    process = daily_state['processes'].pop(name, None)
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)


def fixture_file(path, body):
    path.write_text(body)
    os.chown(path, session['uid'], -1)


def client_profile(label, laptop_fingerprint, *, tls=True):
    root = daily_state['root'] / label
    profile = root / 'Deskflow'
    require(guest_command('mkdir', '-p', str(profile)))
    require(guest_command('python3', '-B', '-c',
                          'import runpy, sys; from pathlib import Path; '
                          'runpy.run_path(sys.argv[1])["ensure_certificate"](Path(sys.argv[2]))',
                          GUARD, str(profile)))
    fixture_file(profile / 'tls/trusted-servers', f'v2:sha256:{laptop_fingerprint.lower()}\n')
    fixture_file(profile / 'Deskflow.conf', '[core]\ncomputerName=fixture-mac\n'
                 f'[client]\nremoteHost=127.0.0.1\n[security]\ntlsEnabled={str(tls).lower()}\n')
    return root


def fingerprint(cert):
    value = require(guest_command('openssl', 'x509', '-in', str(cert), '-noout', '-fingerprint', '-sha256'))
    return value.strip().split('=', 1)[1].replace(':', '').lower()


def monitor_start():
    stop_probe('portal-profile')
    start_probe('portal-profile', ['dbus-monitor', '--session', '--profile',
                "interface='org.freedesktop.portal.InputCapture'",
                "interface='org.freedesktop.impl.portal.Clipboard'",
                "interface='org.freedesktop.portal.Session',member='Closed'"])
    wait_for(lambda: 'NameAcquired' in probe_log('portal-profile'), 'portal monitor ready')


def probe_log(name):
    path = daily_state['root'] / f'{name}.log'
    return path.read_text(errors='replace') if path.exists() else ''


def portal_events():
    lines = probe_log('portal-profile').splitlines()
    return {event: sum(line.endswith('\t' + event) or line.endswith(' ' + event) for line in lines)
            for event in ('Activated', 'Deactivated', 'Closed', 'SelectionRead', 'SelectionWrite')}


def start_tools():
    start_probe('xvfb', ['Xvfb', CLIENT_DISPLAY, '-screen', '0', '800x600x24', '-nolisten', 'tcp'])
    wait_for(lambda: x_command('xdotool', 'getdisplaygeometry').returncode == 0, 'private X11 display ready')
    start_probe('x11-input', ['stdbuf', '-oL', 'xev', '-name', 'Deskflow CI receiver',
                '-geometry', '800x600+0+0', '-event', 'keyboard', '-event', 'mouse'],
                display=True)
    window = wait_for(lambda: x_command('xdotool', 'search', '--name', '^Deskflow CI receiver$').stdout.strip(),
                      'X11 input receiver mapped')
    require(x_command('xdotool', 'windowfocus', window.splitlines()[0]))
    monitor_start()


def daily_prepare(request):
    global session
    mode = request['mode']
    old = session['pid'] if session is not None else None
    session = wait_for(lambda: info if (info := connect_session()) and info['pid'] != old else None,
                       'daily-use labwc session', timeout=120)
    session['daily'] = True
    wait_for(active_primary, 'daily-use primary output')
    if randr().get('Virtual-2', {}).get('enabled'):
        require(guest_command('wlr-randr', '--output', 'Virtual-2', '--off'))
    root = session['home'] / '.local/state/aresos/deskflow-ci-daily'
    if mode != 'relogin':
        daily_state.update(root=root, processes={}, helper_reports=[], clip_markers=[])
        require(guest_command('mkdir', '-p', str(root)))
        start_tools()
    else:
        # The frontend monitor follows the new bus, even if the headless peer survived the old login.
        if x_command('xdotool', 'getdisplaygeometry').returncode == 0:
            monitor_start()
        else:
            for probe in ('xvfb', 'x11-input'):
                stop_probe(probe)
            start_tools()
    source = session['home'] / '.config/Deskflow'
    daily_state['source'] = source
    if mode == 'initial':
        assert not SWITCH.exists() and not core_pids()
        require(guest_command('mkdir', '-p', str(source)))
        # Deskflow 1.27 reads screen names from the main profile before parsing the layout links.
        fixture_file(source / 'Deskflow.conf', '[core]\ncomputerName=fixture-host\ninterface=127.0.0.1\n'
                     '[computer_fixture-host]\nname=fixture-host\n[computer_fixture-mac]\nname=fixture-mac\n')
        fixture_file(source / 'deskflow-server.conf', 'section: links\n    fixture-host:\n        right = fixture-mac\n'
                     '    fixture-mac:\n        left = fixture-host\nend\n')
        require(subprocess.run(['chpasswd'], input=f'{session["name"]}:{PASSWORD}\n',
                               capture_output=True, text=True, timeout=10))
        trace_backend()
    owner = current_owner(BUS_NAME)
    pid = backend_pid(owner) if owner else None
    return dict(returncode=0, switch=require(guest_command(SWITCH_UI, 'status')).strip(),
                backend_connections=wayland_connections(pid) if pid is not None else None,
                backend_has_wayland_display='WAYLAND_DISPLAY' in environ(pid) if pid is not None else None,
                labwc_pid=session['pid'])


def daily_server(request):
    action = request['op']
    if action in ('hub', 'hook') and 'server' in daily_state['processes']:
        daily_state.setdefault('server_logs', []).append(probe_log('server'))
        stop_probe('server')
    if action == 'hub':
        suffix = os.urandom(8).hex()
        unit = f'app-aresos-{DESKTOP_ID}-{suffix}.scope'
        start_probe('server', ['python3', '-B', '-c', hub_launch(suffix, unit)])
    elif action == 'hook':
        start_probe('server', [LOGIN_HOOK])
    elif action == 'stop':
        for pid in core_pids():
            stop_pid(pid)
        wait_for(lambda: not core_pids() and not list(session['runtime'].glob('aresos-deskflow-*/Deskflow')),
                 'server and guarded profile stopped')
        wait_for(lambda: status() == 'no sessions', 'portal session closed after server stop')
    elif action == 'armed':
        path = wait_for(backend_session, 'one armed Deskflow session')
        pid, = core_pids()
        scope = (PROC / str(pid) / 'cgroup').read_text().strip().split('/')[-1]
        assert re.fullmatch(r'app-aresos-org\.deskflow\.deskflow-[0-9a-f]{16}\.scope', scope), scope
        owner = backend_owner()
        backend = backend_pid(owner)
        env = environ(backend)
        assert env['WAYLAND_DISPLAY'] == session['wayland'] and env['DBUS_SESSION_BUS_ADDRESS'] == session['bus']
        assert wayland_connections(backend) == 1
        daily_state.update(backend_pid=backend, core_pid=pid)
        # The monitor header identifies the unique bus sender. The cgroup alone would also match a process that
        # never made the call, so check the sender credentials against the running core.
        calls = [line.split() for line in probe_log('portal-profile').splitlines() if line.endswith('CreateSession2')]
        sender = calls[-1][3] if calls and calls[-1][0] == 'mc' else None
        if request.get('monitor', True):
            assert sender and sender.startswith(':') and backend_pid(sender) == pid, (
                'D-Bus credentials did not identify the scoped core as the CreateSession2 caller')
        return dict(returncode=0, session=path, scope=scope, pid=pid, backend=backend, owner=owner,
                    sender=sender, worker_connections=1)
    elif action == 'kill-backend':
        stop_pid(backend_pid(backend_owner()), signal.SIGKILL)
    elif action == 'kill-frontend':
        previous = current_owner(FRONTEND)
        assert previous, 'frontend was not running'
        stop_pid(backend_pid(previous), signal.SIGKILL)
        return dict(returncode=0, previous=previous)
    elif action == 'frontend':
        return dict(returncode=0, owner=current_owner(FRONTEND))
    elif action == 'freeze':
        pid = backend_pid(backend_owner())
        daily_state['frozen'] = pid
        record = session['runtime'] / 'aresos-deskflow.pid'
        launch, core = (int(line.split()[0]) for line in record.read_text().splitlines())
        assert core_pids() == [core] and GUARD in (
            PROC / str(launch) / 'cmdline').read_text().split('\0')
        daily_state['frozen_guard'] = (launch, core)
        os.kill(pid, signal.SIGSTOP)
    elif action == 'frozen-exited':
        pid = daily_state['frozen']
        wait_for(lambda: not (PROC / str(pid) / 'exe').exists(), 'release killed the stopped backend', timeout=4)
        assert not backend_running() or backend_pid(backend_owner()) != pid
        assert all(not (PROC / str(process) / 'exe').exists() for process in daily_state['frozen_guard'])
        assert SWITCH.read_text().strip() == 'on'
        assert not core_pids() and status() == 'no sessions' and not backend_connections()
        return dict(returncode=0, backend_stopped=True, guard_stopped=True, core_stopped=True, sharing='on')
    elif action == 'off':
        wait_for(lambda: status() == 'no sessions' and not core_pids(), 'sharing stopped, no server or sessions')
        return dict(returncode=0, connections=backend_connections())
    else:
        raise ValueError(action)
    return dict(returncode=0)


def daily_switch(request):
    op = request['op']
    root = session['runtime']
    answer = root / 'deskflow-ci-switch-answer'
    if op == 'start':
        answer.unlink(missing_ok=True)
        path = root / 'deskflow-ci-switch-request'
        temporary = path.with_suffix('.tmp')
        fixture_file(temporary, json.dumps(dict(args=request['args'], display={
            'DBUS_SESSION_BUS_ADDRESS': session['bus'], 'WAYLAND_DISPLAY': session['wayland'],
            'QT_QPA_PLATFORM': 'wayland', 'XDG_CURRENT_DESKTOP': 'AresOS',
        })))
        temporary.replace(path)
    elif op == 'read':
        result = wait_for(lambda: json.loads(answer.read_text()) if answer.exists() else None,
                          'pkexec result', timeout=15)
        daily_state['helper_reports'].extend((result['stdout'], result['stderr']))
        return dict(returncode=0, code=result['code'], switch=require(guest_command(SWITCH_UI, 'status')).strip())
    elif op == 'auth-window':
        target = wait_for(lambda: [window for window in windows()
                                  if window[2] and ('authentication' in window[1].lower()
                                                    or 'polkit' in window[0].lower())], 'polkit password window')
        assert len(target) == 1
    elif op == 'policy':
        def decisions(subject):
            return {verb: subprocess.run(['pkcheck', '--action-id', f'org.aresos.input-sharing.{verb}',
                                         '--process', str(subject)], capture_output=True, text=True, timeout=10).returncode
                    for verb in ('on', 'off')}

        local = decisions(session['pid'])
        active = request['active']
        assert local == ({'on': 2, 'off': 0} if active else {'on': 1, 'off': 2}), local
        with subprocess.Popen(session['prefix'] + ['sh', '-c', 'echo $$; exec sleep 20'],
                              stdout=subprocess.PIPE, text=True) as subject:
            uid_pid = int(subject.stdout.readline())
            try:
                remote = decisions(uid_pid)
                assert remote == {'on': 1, 'off': 2}, remote
            finally:
                os.kill(uid_pid, signal.SIGTERM)
        return dict(returncode=0, local=local, outside_seat=remote)
    elif op == 'outside-seat':
        return remote_switch_denied()
    elif op == 'status':
        return dict(returncode=0, switch=require(guest_command(SWITCH_UI, 'status')).strip())
    elif op == 'bad-pkexec-args':
        result = guest_command('pkexec', '--disable-internal-agent', HELPER, *request['args'])
        daily_state['helper_reports'].extend((result.stdout, result.stderr))
        assert result.returncode != 0 and not SWITCH.exists()
    elif op == 'bad-root-args':
        statuses = [subprocess.run([HELPER, *args], capture_output=True, text=True, timeout=5).returncode
                    for args in ([], ['ON'], ['on', 'x'], ['/tmp/deskflow-ci-not-a-switch'])]
        assert statuses == [2, 2, 2, 2] and not SWITCH.exists()
    elif op == 'unsafe':
        assert not SWITCH.exists()
        SWITCH.parent.mkdir(parents=True, exist_ok=True)
        other = SWITCH.with_name('ci-target')
        other.write_text('on\n')
        if request['kind'] == 'link':
            SWITCH.symlink_to(other)
        else:
            SWITCH.parent.chmod(0o777)
        try:
            assert require(guest_command(SWITCH_UI, 'status')).strip() == 'off'
            assert all(subprocess.run([HELPER, verb], capture_output=True, timeout=5).returncode != 0
                       for verb in ('on', 'off'))
            assert other.read_text() == 'on\n'
            assert SWITCH.is_symlink() if request['kind'] == 'link' else not SWITCH.exists()
            before = off_refusals(session_log())
            daily_server({'op': 'hub'})
            wait_for(lambda: off_refusals(session_log()) > before,
                     'backend refused a session with an unsafe sharing switch')
            wait_for(lambda: not core_pids(), 'refused Deskflow core stopped')
        finally:
            SWITCH.parent.chmod(0o755)
            SWITCH.unlink(missing_ok=True)
            other.unlink()
    elif op == 'remove':
        assert SWITCH.read_text() == 'on\n'
        SWITCH.unlink()
    elif op == 'seed-on':
        require(subprocess.run([HELPER, 'on'], capture_output=True, text=True, timeout=5))
    else:
        raise ValueError(op)
    return dict(returncode=0)


def daily_dialog(request):
    title = {'sharing': SHARING_TITLE, 'pair': PAIR_TITLE, 'recovery': 'AresOS',
             'invalid-profile': 'Deskflow'}[request['name']]
    if request.get('absent'):
        assert not windows_with(title), f'{request["name"]} unexpectedly mapped'
    else:
        seen = wait_for(lambda: windows_with(title), f'{request["name"]} mapped')
        if request.get('new'):
            before = [window for window in daily_state['window_mark'] if window[1].startswith(title)]
            wait_for(lambda: len(windows_with(title)) == len(before) + 1, 'new recovery terminal')
        else:
            assert len(seen) == 1, f'{request["name"]} opened more than one window'
        if request.get('focused', True):
            wait_for(lambda: any(window[2] for window in windows_with(title)),
                     f'{request["name"]} has the keyboard')
    return dict(returncode=0)


def trust_file():
    return daily_state['source'] / 'tls/trusted-clients'


def trusted_line(peer):
    cert = daily_state['root'] / peer / 'Deskflow/tls/deskflow.pem'
    return 'v2:sha256:' + fingerprint(cert) + '\n'


def server_listening():
    # A readiness probe must not generate a failed TLS handshake in the evidence.
    return bool(tcp_sockets('-l', 'sport = :24800'))


def tcp_sockets(*args):
    return require(subprocess.run(['ss', '-Htnp', *args], capture_output=True, text=True, timeout=5))


def new_server_log():
    server, session_tail = daily_state['peer_server_mark']
    return probe_log('server')[server:] + session_log()[session_tail:]


def daily_peer(request):
    op = request['op']
    label = request.get('peer')
    if op == 'prepare':
        cert = daily_state['source'] / 'tls/deskflow.pem'
        wait_for(cert.is_file, 'guard generated its TLS certificate')
        laptop = fingerprint(cert)
        for peer in ('enter', 'approved', 'stranger', 'plain'):
            client_profile(peer, laptop, tls=peer != 'plain')
        assert len({trusted_line(peer) for peer in ('enter', 'approved', 'stranger', 'plain')}) == 4
    elif op == 'start':
        wait_for(server_listening, 'guarded server listening')
        stop_probe('peer')
        profile = daily_state['root'] / label
        daily_state['peer_server_mark'] = (len(probe_log('server')), len(session_log()))
        # Keep client logs separate so a later connection cannot obscure an earlier refusal.
        start_probe('peer', ['env', '-u', 'WAYLAND_DISPLAY', 'QT_QPA_PLATFORM=xcb', 'XDG_SESSION_TYPE=x11',
                   f'XDG_CONFIG_HOME={profile}', f'TMPDIR={profile}', CORE, 'client'], display=True)
        daily_state['peer'] = label
        if request.get('connected'):
            wait_for(lambda: 'accepted client connection' in new_server_log() and
                     'connected to secure socket' in probe_log('peer'), 'Deskflow peers completed TLS')
            time.sleep(0.5)  # The next crossing proves the Deskflow protocol handshake as well.
    elif op == 'stop':
        # Save only logs that will participate in the privacy scan; never export them.
        if 'peer' in daily_state['processes']:
            stop_probe('peer')
            daily_state.setdefault('peer_logs', []).append(probe_log('peer'))
    elif op == 'trusted':
        path = trust_file()
        if label is None:
            assert not path.exists()
        else:
            wait_for(lambda: path.is_file() and path.read_text() == trusted_line(label), 'one verified fingerprint')
            runtime = [entry / 'tls/trusted-clients' for entry
                       in session['runtime'].glob('aresos-deskflow-*/Deskflow')]
            assert len(runtime) == 1 and runtime[0].read_text() == path.read_text()
            assert path.stat().st_mode & 0o777 == 0o600
    elif op == 'refused':
        assert label == daily_state['peer'] and label in ('stranger', 'plain'), label
        client_log = lambda: probe_log('peer')
        if label == 'stranger':
            assert trusted_line(label) != trusted_line('approved')
            daily_peer({'op': 'trusted', 'peer': 'approved'})
            wait_for(lambda: 'fingerprint does not match trusted fingerprint' in new_server_log(),
                     'server rejected the untrusted certificate')
            wait_for(lambda: 'connected to secure socket' in client_log(),
                     'stranger completed TLS on the client side before server fingerprint refusal')
        else:
            wait_for(lambda: 'deskflow-core' in tcp_sockets('state', 'established', 'dport = :24800'),
                     'native plaintext client attempted a TCP connection')
            wait_for(lambda: 'failed to accept secure socket' in new_server_log(),
                     'server did not complete TLS with the plaintext client')
            assert 'connected to secure socket' not in client_log()
        assert 'accepted secure socket' not in new_server_log()
        assert 'accepted client connection' not in new_server_log()
        return dict(returncode=0, server='fingerprint mismatch' if label == 'stranger' else 'TLS accept failed',
                    client='TLS reached' if label == 'stranger' else 'plaintext TCP reached')
    elif op == 'no-data':
        assert label == daily_state['peer'], label
        if label == 'stranger':
            wait_for(lambda: not tcp_sockets('state', 'established', 'dport = :24800'),
                     'the stranger lost its client-side transport after the fingerprint refusal', timeout=5)
        assert 'accepted client connection' not in new_server_log()
        assert 'accepted secure socket' not in new_server_log()
        assert not re.search(r'(?m)^(KeyPress|KeyRelease|MotionNotify|ButtonPress|ButtonRelease) event',
                             input_since(daily_state['input_mark'], 'x11-input')), 'rejected peer received input'
        assert not captured(), 'capture stayed active for a rejected peer'
        return dict(returncode=0, client_input_events=0, client_transport_closed=label == 'stranger')
    elif op == 'settings':
        settings = daily_state['source'] / 'Deskflow.conf'
        text = settings.read_text()
        if not request.get('stale') and '[security]' not in text:
            fixture_file(settings, text + '[security]\ntlsEnabled=false\ncheckPeerFingerprints=false\n')
        if request.get('stale'):
            fixture_file(trust_file(), trusted_line('approved') + trusted_line('stranger'))
        else:
            fixture_file(trust_file(), trusted_line('approved'))
    elif op == 'protected':
        pid, = core_pids()
        env = environ(pid)
        profile = pathlib.Path(env['XDG_CONFIG_HOME']) / 'Deskflow/Deskflow.conf'
        text = profile.read_text()
        assert re.search(r'(?im)^tlsEnabled=true$', text) and re.search(r'(?im)^checkPeerFingerprints=true$', text)
        assert env['QT_QPA_PLATFORM'] == 'wayland' and 'DISPLAY' not in env
        assert (PROC / str(pid) / 'cmdline').read_bytes().split(b'\0') == [CORE.encode(), b'server', b'']
    else:
        raise ValueError(op)
    return dict(returncode=0)


def send_virtual(device, commands):
    process = daily_state['processes'][device]
    for command in commands:
        process.stdin.write(command + '\n')
        process.stdin.flush()
        assert select.select([process.stdout], [], [], 5)[0] and process.stdout.readline() == 'OK\n', device


def input_mark():
    return {name: (daily_state['root'] / f'{name}.log').stat().st_size for name in ('local-input', 'x11-input')}


def input_since(mark, name):
    with (daily_state['root'] / f'{name}.log').open() as stream:
        stream.seek(mark[name])
        return stream.read()


def wait_received(mark, pattern, description, timeout=5):
    return wait_for(lambda: re.search(pattern, input_since(mark, 'x11-input'), re.M),
                    description, timeout=timeout)


def captured():
    return backend_session(capture=True)


def width_height():
    mode = active_mode(randr()['Virtual-1'])
    return mode['width'], mode['height']


def position_pointer(x, y):
    width, height = width_height()
    send_virtual('pointer', [f'abs {x} {y} {width} {height}'])


def attempt_crossing():
    width, height = width_height()
    position_pointer(width // 2, height // 2)
    position_pointer(width - 3, height // 2)
    send_virtual('pointer', ['rel 100 0'])


def x_key(code):
    # A real keyboard-path check also follows every binding, using the X11 event and its modifiers.
    return rf'(?m)state 0x[0-9a-f]+, keycode \d+ \(keysym 0x[0-9a-f]+, {re.escape(code)}\)'


def local_focus():
    width, height = width_height()
    position_pointer(width // 2, height // 2)
    send_virtual('pointer', ['btn 272 1', 'btn 272 0'])
    wait_for(lambda: any(w[0] == 'org.aresos.deskflow-ci' and w[2] for w in windows()),
             'the local input probe has focus')


def daily_input(request):
    op = request['op']
    if op == 'prepare':
        for old in ('local-input', 'pointer', 'keyboard'):
            stop_probe(old)
        start_probe('local-input', [WL_HARNESS, 'window', '--keep-open', '--app-id', 'org.aresos.deskflow-ci',
                                    '--title', 'Deskflow CI laptop', '--size', '600x450'])
        for device in ('pointer', 'keyboard'):
            process = start_probe(device, [WL_HARNESS, 'input', device], pipe=True)
            assert select.select([process.stdout], [], [], 8)[0] and process.stdout.readline() == 'READY\n'
        wait_for(lambda: bool(windows_with('Deskflow CI laptop')), 'local Wayland input probe')
        local_focus()
    elif op == 'focus':
        local_focus()
    elif op == 'untrusted-cross':
        attempt_crossing()
        time.sleep(0.2)
        send_virtual('pointer', ['rel 24 0'])
        wait_for(lambda: backend_session(capture=False), 'the pointer was released without a connected client')
        local_focus()
    elif op == 'cross':
        assert backend_session(capture=False), 'no armed session before crossing'
        before = portal_events()
        attempt_crossing()
        wait_for(captured, 'crossing started a capture')
        wait_for(lambda: portal_events()['Activated'] > before['Activated'], 'real frontend forwarded Activated')
    elif op == 'off-cross':
        assert status() == 'no sessions'
        attempt_crossing()
        assert status() == 'no sessions' and not backend_connections()
        # Leave the pointer inside the output before the On check places a barrier at the edge.
        local_focus()
    elif op == 'mark':
        daily_state.update(input_mark=input_mark(), event_mark=portal_events(), window_mark=windows())
    elif op == 'inward':
        send_virtual('pointer', ['rel 51 23', 'btn 272 1', 'btn 272 0', 'axis -2'])
    elif op == 'forwarded':
        mark = daily_state['input_mark']
        for pattern in (r'^MotionNotify', r'^ButtonPress', r'button 1, same_screen', r'button [45], same_screen', x_key('a')):
            wait_received(mark, pattern, 'remote client got motion, buttons, scroll and keys')
        assert not re.search(r'(?m)^(KEY|MOTION|BUTTON|AXIS) ', input_since(mark, 'local-input'))
    elif op == 'typed-marker':
        def typed():
            events = re.findall(r'(?ms)^KeyPress event,.*?(?=\n\n|\Z)', input_since(daily_state['input_mark'], 'x11-input'))
            symbols = [match[1] for event in events
                       if (match := re.search(r'keysym 0x[0-9a-f]+, ([a-z0-9])\)', event))]
            return KEY_MARKER in ''.join(symbols)
        wait_for(typed, 'the complete keyboard marker reached the private X11 recorder')
    elif op == 'binding':
        mark = daily_state['input_mark']
        wait_received(mark, x_key('b'), 'the next key went to Deskflow client')
        expected = request.get('key')
        if expected:
            wait_received(mark, x_key(expected), 'the unmarked binding itself reached the client')
        if request.get('mic_mute_limit'):
            assert not re.search(x_key('XF86AudioMicMute'), input_since(mark, 'x11-input'))
        if button := request.get('mouse'):
            assert button in ('1', '2', '3', '4', '5')
            wait_received(mark, rf'button {button}, same_screen', 'the mouse binding itself reached the client')
        assert captured() and portal_events()['Deactivated'] == daily_state['event_mark']['Deactivated']
        assert windows() == daily_state['window_mark'], 'an unmarked binding changed local windows or focus'
        assert not re.search(r'(?m)^(KEY|MOTION|BUTTON|AXIS|CLOSE)', input_since(mark, 'local-input'))
        result = dict(returncode=0, laptop='unchanged', capture='held', next_key='client')
        if request.get('mic_mute_limit'):
            result['binding_key'] = 'dropped by Deskflow 1.27'
        return result
    elif op == 'virtual-key':
        code = request['code']
        send_virtual('keyboard', [f'key {code} 1', f'key {code} 0'])
    elif op == 'virtual-mouse':
        send_virtual('pointer', request['commands'])
    elif op == 'released':
        wait_for(lambda: not captured(), 'capture ended')
        wait_for(lambda: portal_events()['Deactivated'] > daily_state['event_mark']['Deactivated'],
                 'real frontend forwarded Deactivated')
        if request.get('modifiers'):
            def neutral():
                text = input_since(daily_state['input_mark'], 'x11-input')
                for name in ('Super_L', 'Shift_L'):
                    press, release = (sum(re.search(x_key(name), event) is not None for event in
                                          re.findall(rf'(?ms)^{kind} event,.*?(?=\n\n|\Z)', text))
                                      for kind in ('KeyPress', 'KeyRelease'))
                    if not press or release != press:
                        return False
                return True
            wait_for(neutral, 'the client got both modifier releases while the QEMU keys were held')
        return dict(returncode=0, deactivated=True)
    elif op == 'local-key':
        wait_for(lambda: re.search(r'(?m)^KEY \d+ 1$', input_since(daily_state['input_mark'], 'local-input')),
                 'the next key was local')
        assert not re.search(x_key('b'), input_since(daily_state['input_mark'], 'x11-input'))
    elif op == 'still':
        assert captured()
        wait_received(daily_state['input_mark'], x_key('b'), 'key after idle reached client')
    elif op == 'closed':
        wait_for(lambda: portal_events()['Closed'] > daily_state['event_mark']['Closed'],
                 'real frontend forwarded Closed', timeout=3)
    else:
        raise ValueError(op)
    return dict(returncode=0)


def paste_matches(command, mark, display=False):
    read = x_command if display else guest_command
    try:
        result = read('timeout', '1', *command)
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0 and result.stdout == mark


def put_clipboard(name, marker, command, display=False):
    stop_probe(name)
    process = start_probe(name, command, display=display, pipe=True)
    process.stdin.write(marker)
    process.stdin.close()


def daily_clip(request):
    op = request['op']
    if op == 'baseline':
        time.sleep(0.5)
        pid = backend_pid(current_owner(FRONTEND))
        daily_state['clip_frontend'] = pid
        daily_state['clip_fds'] = len(os.listdir(PROC / str(pid) / 'fd'))
        daily_state['clip_before'] = portal_events()
    elif op in ('host', 'client'):
        index = len(daily_state['clip_markers'])
        marker = f'aresosclip{index:04d}'
        daily_state['clip_markers'].append(marker)
        daily_state['clip_marker'] = marker
        if op == 'host':
            put_clipboard('wl-copy', marker, ['wl-copy', '--foreground', '--type', 'text/plain;charset=utf-8'])
        else:
            put_clipboard('x-copy', marker, ['xclip', '-quiet', '-selection', 'clipboard'], display=True)
    elif op == 'read-client':
        wait_for(lambda: paste_matches(['xclip', '-o', '-selection', 'clipboard'], daily_state['clip_marker'], True),
                 'clipboard arrived at the client through Deskflow', timeout=6)
    elif op == 'read-host':
        wait_for(lambda: paste_matches(['wl-paste', '--no-newline'], daily_state['clip_marker']),
                 'clipboard arrived at the laptop through Deskflow', timeout=6)
    elif op == 'release':
        # Return through Deskflow's configured boundary so it switches the active screen and its clipboard.
        send_virtual('pointer', ['rel -1600 0'])
        wait_for(lambda: backend_session(capture=False), 'Deskflow crossed back to the laptop')
    elif op == 'counts':
        pid = daily_state['clip_frontend']
        assert pid == backend_pid(current_owner(FRONTEND))
        before = daily_state['clip_before']
        counts = {member: portal_events()[member] - before[member] for member in ('SelectionRead', 'SelectionWrite')}
        def stable_fd_count():
            count = len(os.listdir(PROC / str(pid) / 'fd'))
            return (count,) if count <= daily_state['clip_fds'] else None

        after, = wait_for(stable_fd_count, 'frontend returned to its original descriptor count', timeout=5)
        assert all(value >= 20 for value in counts.values()), counts
        return dict(returncode=0, portal_calls=counts, frontend_fds=[daily_state['clip_fds'], after])
    elif op == 'no-read':
        # Each attempted copy remained on its origin after shutdown.
        side = request['side']
        marker = daily_state['clip_marker']
        commands = {'client': (['xclip', '-o', '-selection', 'clipboard'], True),
                    'host': (['wl-paste', '--no-newline'], False)}
        origin = 'host' if side == 'client' else 'client'
        origin_command, origin_display = commands[origin]
        wait_for(lambda: paste_matches(origin_command, marker, origin_display), 'the local copy succeeded')
        destination, destination_display = commands[side]
        assert not paste_matches(destination, marker, destination_display)
        before = daily_state['event_mark']
        after = portal_events()
        assert all(after[member] == before[member] for member in ('SelectionRead', 'SelectionWrite'))
    else:
        raise ValueError(op)
    return dict(returncode=0)


def sandbox_refusal():
    app_id = 'org.aresos.UnlistedFixture'
    instance = str(uuid.uuid4().int % 10**18)
    root = session['runtime'] / '.flatpak' / instance
    require(guest_command('mkdir', '-m', '0700', '-p', str(root)))
    declaration = root / 'info'
    fixture_file(declaration, f'[Application]\nname={app_id}\nruntime=org.fedoraproject.Platform\n'
                 f'[Instance]\ninstance-id={instance}\n')
    before = len(session_log())
    command = ['sh', '-c', 'exec "$@" 3>&1', 'bwrap-info',
               'bwrap', '--die-with-parent', '--unshare-pid', '--info-fd', '3',
               '--ro-bind', '/usr', '/usr', '--ro-bind', '/etc', '/etc',
               '--ro-bind', '/run', '/run', '--ro-bind', '/tmp', '/tmp', '--proc', '/proc', '--dev', '/dev',
               '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
               '--ro-bind', str(declaration), '/.flatpak-info', '--', 'sh', '-c', 'read -r start && exec "$@"',
               'sandbox-probe', 'gdbus', 'call', '--session', '--dest', FRONTEND,
               '--object-path', '/org/freedesktop/portal/desktop', '--method',
               'org.freedesktop.portal.InputCapture.CreateSession2', "{'session_handle_token': <'unlisted'>}"]
    try:
        with subprocess.Popen(session['prefix'] + command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True) as sandbox:
            try:
                header = sandbox.stdout.readline() if select.select([sandbox.stdout], [], [], 5)[0] else ''
                if header.strip() == '{':
                    for line in sandbox.stdout:
                        header += line
                        if line.strip() == '}':
                            break
                    # The frontend resolves the Flatpak instance to the actual sandbox's pidfd.
                    assert json.loads(header)['child-pid'] > 0, header
                    fixture_file(root / 'bwrapinfo.json', header)
                stdout, stderr = sandbox.communicate('start\n', timeout=12)
            finally:
                if sandbox.poll() is None:
                    sandbox.kill()
                    sandbox.wait()
        evidence = dict(bwrap=header.strip(), reply=stdout.strip(), stderr=stderr.strip(), code=sandbox.returncode)
        reason = 'refused: this application is not on the allow-list'
        evidence['backend_refusal'] = next((line for line in session_log()[before:].splitlines()
                                            if f'app_id="{app_id}"' in line and reason in line), None)
        assert (header.startswith('{') and sandbox.returncode == 1 and not stdout.strip()
                and 'org.freedesktop.DBus.Error.AccessDenied: this application may not capture input' in stderr
                and evidence['backend_refusal']), evidence
        return dict(returncode=0, app_id=app_id, **evidence)
    finally:
        for file in (declaration, root / 'bwrapinfo.json'):
            file.unlink(missing_ok=True)
        root.rmdir()


def daily_proof(request):
    op = request['op']
    if op == 'off-launch':
        before = off_refusals(session_log())
        daily_server({'op': 'hub'})
        wait_for(lambda: off_refusals(session_log()) > before,
                 'real portal declined the scoped Deskflow server while Off')
        wait_for(lambda: not core_pids(), 'refused core exited')
        assert status() == 'no sessions' and not backend_connections()
    elif op == 'off-time':
        pid = backend_pid(backend_owner())
        pidfd = os.pidfd_open(pid)
        try:
            before = time.monotonic()
            daily_switch({'op': 'remove'})
            assert select.select([pidfd], [], [], 2)[0], 'original backend stayed alive past the Off deadline'
            elapsed = time.monotonic() - before
        finally:
            os.close(pidfd)
        assert elapsed <= 2
        return dict(returncode=0, seconds=round(elapsed, 3))
    elif op == 'flatpak':
        return sandbox_refusal()
    elif op == 'log':
        assert daily_state['clip_markers'] and portal_events()['Activated'] and portal_events()['Deactivated']
        pid = backend_pid(backend_owner())
        assert environ(pid)['ARESOS_INPUT_PORTAL_LOG'] == 'trace'
        pid, = core_pids()
        profile = pathlib.Path(environ(pid)['XDG_CONFIG_HOME']) / 'Deskflow/Deskflow.conf'
        settings = ConfigParser()
        settings.read(profile)
        level = settings.get('log', 'level', fallback='INFO')
        assert level.lower() == 'info' and not settings.getboolean('log', 'toFile', fallback=False), level
        journal = subprocess.run(['journalctl', '-b', '--no-pager', '-o', 'cat'], check=True,
                                 capture_output=True, text=True, timeout=30).stdout
        helper = '\n'.join(daily_state['helper_reports'])
        session_output = session_log()
        server_runs = '\n'.join(daily_state.get('server_logs', [])) + probe_log('server')
        client_runs = '\n'.join(daily_state.get('peer_logs', [])) + probe_log('peer')
        file_logs = {}
        for base in (session['home'], session['runtime'], pathlib.Path('/tmp')):
            for path in base.rglob('*.log'):
                if 'deskflow' in str(path).casefold() and path.name not in {
                    'deskflow-ci-session.log', 'local-input.log', 'x11-input.log', 'portal-profile.log',
                }:
                    file_logs[str(path)] = path.read_text(errors='replace')
        sources = {'journal': journal, 'session': session_output, 'server': server_runs,
                   'client': client_runs, 'helper': helper, **file_logs}
        assert 'detected wayland platform' in server_runs and 'started client' in client_runs
        assert any('DEBUG' in line and 'aresos_input_portal' in line for line in session_output.splitlines())
        for name, body in sources.items():
            assert not LOG_DATA.search(body), f'sensitive input in {name}'
        return dict(returncode=0, backend_level='trace', deskflow_level=level,
                    lines={name: len(body.splitlines()) for name, body in sources.items()})
    elif op == 'recovery-key':
        path = session['home'] / 'deskflowrecovered'
        wait_for(path.exists, 'keyboard input reached the new recovery terminal')
        path.unlink()
    elif op == 'login-off':
        assert require(guest_command(SWITCH_UI, 'status')).strip() == 'off'
        assert not core_pids() and not backend_connections()
    elif op == 'restart-login':
        name = session['name']
        require(subprocess.run(['systemctl', 'stop', 'greetd.service'], capture_output=True, text=True, timeout=45))
        require(subprocess.run(['loginctl', 'terminate-user', name], capture_output=True, text=True, timeout=20))
        wait_for(lambda: not session['runtime'].exists() and labwc_pid(session['uid']) is None and not core_pids(),
                 'the old login and its Deskflow scope ended', timeout=45)
        # greetd runs initial_session once per boot unless the runfile is removed in this disposable guest.
        pathlib.Path('/run/greetd.run').unlink(missing_ok=True)
        require(subprocess.run(['systemctl', 'start', '--no-block', 'greetd.service'],
                               capture_output=True, text=True, timeout=10))
    elif op == 'poweroff':
        # Leave time for the response to reach the host before systemd stops the CI channel.
        subprocess.Popen(['sh', '-c', 'sleep 1; exec systemctl poweroff'], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        raise ValueError(op)
    return dict(returncode=0)


ACTIONS.update({'deskflow-daily-prepare': daily_prepare, 'deskflow-daily-switch': daily_switch,
                'deskflow-daily-server': daily_server, 'deskflow-daily-dialog': daily_dialog,
                'deskflow-daily-peer': daily_peer, 'deskflow-daily-input': daily_input,
                'deskflow-daily-clip': daily_clip, 'deskflow-daily-proof': daily_proof})


def remote_switch_denied():
    """Ask from a real PAM SSH login on guest loopback, with only throwaway keys."""
    with tempfile.TemporaryDirectory(prefix='deskflow-ssh-') as directory:
        work = pathlib.Path(directory)
        key = work / 'id'
        require(subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                               capture_output=True, text=True, timeout=10))
        keys = session['home'] / '.ssh'
        require(guest_command('install', '-d', '-m', '0700', str(keys)))
        authorized = keys / 'deskflow-ci-authorized'
        fixture_file(authorized, key.with_suffix('.pub').read_text())
        authorized.chmod(0o600)
        require(subprocess.run(['ssh-keygen', '-A'], capture_output=True, text=True, timeout=12))
        require(subprocess.run(['restorecon', '-R', str(keys), '/etc/ssh'], capture_output=True, text=True, timeout=12))
        unit = 'deskflow-ci-sshd.service'
        command = ['systemd-run', '--quiet', f'--unit={unit}', '--service-type=exec',
                   '/usr/sbin/sshd', '-D', '-e',
                   '-o', 'ListenAddress=127.0.0.1', '-o', 'UsePAM=yes',
                   '-o', 'AuthorizedKeysFile=.ssh/deskflow-ci-authorized', '-o', 'PasswordAuthentication=no',
                   '-o', 'PermitRootLogin=no', '-o', 'UseDNS=no']
        started = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            # Let the system manager start sshd in its normal SELinux domain and load the image's SSH config.
            require(subprocess.run(command, capture_output=True, text=True, timeout=12))
            wait_for(lambda: 'sshd' in tcp_sockets('-l', 'src 127.0.0.1 and sport = :22'),
                     'systemd loopback sshd')
            pid = int(require(subprocess.run(['systemctl', 'show', '-p', 'MainPID', '--value', unit],
                                             capture_output=True, text=True, timeout=5)).strip())
            domain = (PROC / str(pid) / 'attr/current').read_text().strip().rstrip('\0')
            script = ('test "$(loginctl show-session self -p Remote --value)" = yes || exit 31; '
                      'printf "deskflow-remote=yes\n"; '
                      'exec pkexec --disable-internal-agent /usr/libexec/aresos-input-sharing-set on')
            result = subprocess.run(['ssh', '-n', '-tt', '-F', '/dev/null', '-o', 'BatchMode=yes',
                                     '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=no',
                                     '-o', 'UserKnownHostsFile=/dev/null', '-i', str(key),
                                     f'{session["name"]}@127.0.0.1', script],
                                    capture_output=True, text=True, timeout=12)
            daily_state['helper_reports'].extend((result.stdout, result.stderr))
            if result.returncode != 127 or 'deskflow-remote=yes' not in result.stdout.splitlines():
                journal = subprocess.run(['journalctl', '-b', '--since', started, '-u', unit,
                                          '-o', 'cat', '--no-pager', '-n', '20'], capture_output=True, text=True,
                                         timeout=10).stdout
                audit = subprocess.run(['journalctl', '-b', '--since', started, '-o', 'cat', '--no-pager',
                                        '-g', r'avc:.*(sshd|bash|pkexec)'], capture_output=True, text=True,
                                       timeout=10).stdout
                shell = pwd.getpwnam(session['name']).pw_shell
                lines = (result.stdout + result.stderr + journal + audit).splitlines()
                safe = '\n'.join(line for line in lines[-24:] if not LOG_DATA.search(line))
                raise AssertionError(f'remote switch probe exited {result.returncode}; sshd={domain}, shell={shell}, '
                                     f'nologin={pathlib.Path("/run/nologin").exists()}: {safe}')
            assert not SWITCH.exists()
            return dict(returncode=0, remote=True, refused=True, sshd_domain=domain, pkexec=result.returncode)
        finally:
            subprocess.run(['systemctl', 'stop', unit], capture_output=True, text=True, timeout=6)
            authorized.unlink(missing_ok=True)
