"""Guest actions for the DRM output gate. The virtio layer is the only caller."""
import json
import os
import pathlib
import pwd
import re
import subprocess
import time

PROC = pathlib.Path('/proc')
VT = pathlib.Path('/sys/class/tty/tty0/active')
PORTAL = '/usr/libexec/aresos-input-portal'
BUS_NAME = 'org.freedesktop.impl.portal.desktop.aresos-input'
GEOMETRY = re.compile(r'Screen \{ name: "([^"]+)", zone: Zone \{ width: (\d+), height: (\d+), '
                      r'x: (-?\d+), y: (-?\d+) \}')
session = None
listener = None


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


def bus(*args):
    return require(guest_command('busctl', '--user', '--no-pager', *args)).strip()


def backend_owner():
    words = bus('call', 'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                'GetConnectionUnixProcessID', 's', BUS_NAME).split()
    assert words[0] == 'u' and len(words) == 2, words
    return int(words[1])


def ready(request):
    global session, listener
    assert session is None
    state = request['state']
    assert state in ('none', 'listener', 'backend'), state
    session = wait_for(connect_session, 'real labwc session', timeout=120)
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
    if state == 'backend':
        assert bus('call', 'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                   'NameHasOwner', 's', BUS_NAME) == 'b false', 'backend was already running'
        assert not pathlib.Path('/etc/aresos/input-portal/sharing').exists()
        # Set the log level for this activation alone. Use the socket of the real session.
        require(guest_command('env', 'ARESOS_INPUT_PORTAL_LOG=debug', 'dbus-update-activation-environment',
                              'ARESOS_INPUT_PORTAL_LOG', 'WAYLAND_DISPLAY', 'XDG_CURRENT_DESKTOP'))
        assert require(guest_command(PORTAL, '--status')).strip() == 'no sessions'
        pid = backend_owner()
        env = environ(pid)
        assert env['DBUS_SESSION_BUS_ADDRESS'] == session['bus']
        assert env['WAYLAND_DISPLAY'] == session['wayland']
        assert env['XDG_CURRENT_DESKTOP'] == 'AresOS'
        assert os.readlink(PROC / str(pid) / 'exe') == PORTAL
        assert (PROC / str(pid)).stat().st_uid == session['uid']
        session['backend'] = pid
        proof['backend_pid'] = pid
    check_compositor()
    return dict(returncode=0, **proof)


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
    assert backend_owner() == session['backend'], 'backend restarted'
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
    if 'backend' in session and request.get('geometry', True) and session.get('last_geometry') != geometry:
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


def diagnostics(request):
    return dict(returncode=0, labwc_pid=labwc_pid(session['uid']), connectors=drm_connectors(),
                session_log=session_log()[-20000:])


ACTIONS = {'deskflow-ready': ready, 'deskflow-snapshot': snapshot, 'deskflow-change': change,
           'deskflow-vt': vt, 'deskflow-diagnostics': diagnostics}
