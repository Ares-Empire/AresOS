"""Explicit laptop acceptance check; never imported by unittest discovery.

Own headless labwc, runtime, HOME, helper/socket and PIDs/scopes. No real-session
window/input or compositor reconfiguration. No installation or third-party assets.
"""
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time

from test_aresos_shell import shell, ROOT

WORK = ROOT / '.work/h30'
EVIDENCE = ROOT / 'reviews/30-installed-programs'


def wait_for(predicate, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if value := predicate():
            return value
        time.sleep(0.1)
    raise AssertionError('timed out waiting for headless check')


def main():
    memory = subprocess.check_output(['free', '-g'], text=True)
    print(memory, flush=True)
    assert int(next(line for line in memory.splitlines() if line.startswith('Mem:')).split()[-1]) >= 4
    for path in Path('/proc').glob('[0-9]*/exe'):
        try:
            target = os.readlink(path)
        except OSError:
            continue
        assert not ('/.lunarclient/' in target and 'java' in target.lower()), 'owner game is running'
    print('owner_lunar_java_pids: []', flush=True)
    WORK.mkdir(parents=True, exist_ok=True)
    runtime = WORK / 'r'
    runtime.mkdir(mode=0o700, exist_ok=True)
    os.chmod(runtime, 0o700)
    (runtime / 'systemd').mkdir(exist_ok=True)
    manager_socket = runtime / 'systemd/private'
    if not manager_socket.is_symlink():
        manager_socket.symlink_to(Path(os.environ['XDG_RUNTIME_DIR']) / 'systemd/private')
    home = WORK / 'home'
    config = home / '.config'
    entries = home / '.local/share/applications'
    registry = WORK / 'registry'
    for directory in (config / 'labwc', config / 'btop', config / 'foot', entries, registry,
                      WORK / 'tmp', EVIDENCE / 'screenshots'):
        directory.mkdir(parents=True, exist_ok=True)
    (config / 'labwc/rc.xml').write_text('<labwc_config><theme><name>Adwaita</name></theme></labwc_config>\n')
    (config / 'btop/btop.conf').write_text('shown_boxes = "cpu mem"\ncheck_temp = false\nupdate_ms = 1000\n')
    (config / 'foot/foot.ini').write_text('[main]\nfont=monospace:size=9\ninitial-window-size-chars=100x30\n')
    # KCalc is already installed as a Flatpak here. Its deployed binary also links
    # to this image's Qt/KF libraries; a private bus prevents owner-session activation.
    kcalc = Path('/usr/bin/kcalc')
    if not kcalc.exists():
        location = subprocess.check_output(['flatpak', 'info', '--show-location', 'org.kde.kcalc'], text=True).strip()
        kcalc = Path(location) / 'files/bin/kcalc'
    assert kcalc.is_file()
    (entries / 'check-kcalc.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=KCalc check\n'
        f'Exec=/usr/bin/dbus-run-session -- {kcalc}\nStartupWMClass=org.kde.kcalc\n')
    (entries / 'check-btop.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Btop check\nExec=/usr/bin/btop\nTerminal=true\n')
    env = dict(os.environ, HOME=str(home), XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(config),
               XDG_DATA_HOME=str(home / '.local/share'), XDG_CACHE_HOME=str(home / '.cache'),
               XDG_STATE_HOME=str(home / '.local/state'), TMPDIR=str(WORK / 'tmp'),
               WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_HEADLESS_OUTPUTS='1',
               ARESOS_DESKTOP_INSTANCE=f'headless-30-{os.getpid()}',
               ARESOS_LAUNCH_NONCE='headless-30-test-nonce-0123456789',
               QT_QPA_PLATFORM='wayland', GDK_BACKEND='wayland', TERM='xterm-256color')
    # Only systemd-run/systemctl need the existing user manager. No environment
    # import, activation or modification of the real compositor/session occurs.
    env['DBUS_SESSION_BUS_ADDRESS'] = os.environ.get('DBUS_SESSION_BUS_ADDRESS', 'unix:path=/run/user/1001/bus')
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'WAYLAND_SOCKET', 'SESSION_MANAGER'):
        env.pop(key, None)
    processes, scopes, logs = [], [], []
    client = reader = observer = None
    def spawn(args, name):
        log = open(WORK / (name + '.log'), 'w')
        logs.append(log)
        proc = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(proc)
        return proc
    try:
        compositor = spawn(['/usr/bin/labwc', '--config-dir', str(config / 'labwc')], 'labwc')
        display = wait_for(lambda: next((p for p in runtime.glob('wayland-*') if p.is_socket()), None))
        env['WAYLAND_DISPLAY'] = display.name
        assert runtime != Path('/run/user/1001')
        print('private_display:', display.relative_to(ROOT), 'labwc_pid:', compositor.pid, flush=True)
        hub = spawn(['/usr/bin/foot', '--app-id=aresos-desktop', '/usr/bin/sleep', '180'], 'hub')
        windows = shell.Windows()
        observer = shell.ForeignToplevels.connect(windows, env)
        def observe():
            if select.select([observer.sock], [], [], 0)[0]:
                observer.readable()
            return windows
        wait_for(lambda: observe().of(windows.SHELL))
        helper = spawn([sys.executable, str(ROOT / 'os/config/usr/libexec/aresos-shell'),
                        '--registry', str(registry)], 'helper')
        path = runtime / 'aresos/shell.sock'
        wait_for(path.exists)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(30)
        client.connect(str(path))
        reader = client.makefile('rb')
        transcript = []
        def send(op, request_id, **fields):
            message = dict(protocol='aresos-shell/1.1', id=request_id, op=op, **fields)
            client.sendall(json.dumps(message).encode() + b'\n')
        def until(predicate):
            end = time.monotonic() + 30
            while time.monotonic() < end:
                message = json.loads(reader.readline())
                transcript.append(message)
                if 'event' in message:
                    print('socket_event:', json.dumps(message, sort_keys=True), flush=True)
                if predicate(message):
                    return message
            raise AssertionError('missing socket reply/event')
        send('hello', 'hello', major=1, minor=1, capabilities=sorted(shell.BASE_CAPABILITIES |
             shell.WINDOW_CAPABILITIES | shell.DETAIL_CAPABILITIES), requires=['windows', 'open_app'],
             instance=env['ARESOS_DESKTOP_INSTANCE'], nonce=env['ARESOS_LAUNCH_NONCE'])
        assert until(lambda m: m.get('id') == 'hello')['minor'] == 1
        send('list_apps', 'list')
        listing = until(lambda m: m.get('id') == 'list')
        assert {'check-kcalc', 'check-btop'} <= {app['id'] for app in listing['apps']}
        observations = []
        for app_id in ('check-kcalc', 'check-btop'):
            request_id = 'open-' + app_id
            send('open_app', request_id, app_id=app_id)
            answer = until(lambda m: m.get('id') == request_id)
            assert answer['ok'], answer
            journal = json.loads((runtime / 'aresos/shell-journal.json').read_text())
            unit = journal['launches'][request_id]['unit']
            scopes.append(unit)
            focused = until(lambda m: m.get('event') == 'app_state' and m.get('request_id') == request_id
                            and m.get('state') == 'focused')
            properties = subprocess.check_output(['/usr/bin/systemctl', '--user', 'show', unit,
                                                  '-p', 'Slice', '-p', 'ControlGroup', '-p', 'ActiveState'],
                                                 env=env, text=True)
            assert 'Slice=app.slice\n' in properties and 'ActiveState=active\n' in properties, properties
            cgroup = next(line.split('=', 1)[1] for line in properties.splitlines() if line.startswith('ControlGroup='))
            pids = (Path('/sys/fs/cgroup') / cgroup.lstrip('/') / 'cgroup.procs').read_text().split()
            assert pids
            for pid in pids:
                assert cgroup in Path('/proc', pid, 'cgroup').read_text()
            expected_id = 'org.kde.kcalc' if app_id == 'check-kcalc' else 'aresos.app.check-btop'
            toplevel = wait_for(lambda: next((t for t in observe().toplevels.values()
                                             if t.app_id == expected_id and t.activated), None))
            time.sleep(2)  # A mapped/focused toplevel may not have painted its first frame yet.
            subprocess.run(['/usr/bin/grim', str(EVIDENCE / 'screenshots' / (app_id + '.png'))],
                           env=env, check=True, timeout=10, capture_output=True)
            print(app_id, unit, properties.strip().replace('\n', ' '),
                  'window_app_id=' + toplevel.app_id, 'scope_pids=' + ','.join(pids), flush=True)
            # Close only the owned foreign-toplevel handle, then check the real return event.
            observer._send(toplevel.handle, 5)
            returned = until(lambda m: m.get('event') == 'shell_focus' and m.get('focus') == 'foreground'
                             and (m.get('reason') == 'desktop_activated' or m.get('app_id') == app_id))
            assert returned.get('reason') in ('app_closed', 'desktop_activated'), returned
            wait_for(lambda: not any(t.app_id == expected_id for t in observe().toplevels.values()))
            wait_for(lambda: any(t.activated for t in observe().of(windows.SHELL)))
            if not any(m.get('event') == 'app_state' and m.get('request_id') == request_id
                       and m.get('state') == 'closed' for m in transcript):
                until(lambda m: m.get('event') == 'app_state' and m.get('request_id') == request_id
                      and m.get('state') == 'closed')
            observations.append(dict(app_id=app_id, unit=unit, properties=properties,
                                     window_app_id=toplevel.app_id, scope_pids=pids,
                                     focused=focused, returned=returned))
            print(app_id, 'return:', json.dumps(returned, sort_keys=True), flush=True)
        (EVIDENCE / 'headless.json').write_text(json.dumps(dict(display=str(display.relative_to(ROOT)),
            kcalc_binary=str(kcalc), observations=observations, transcript=transcript), indent=2) + '\n')
        print('HEADLESS_KCALC_BTOP_PASSED', flush=True)
    finally:
        if reader is not None:
            reader.close()
        if client is not None:
            client.close()
        if observer is not None:
            observer.sock.close()
        journal_path = runtime / 'aresos/shell-journal.json'
        if journal_path.exists():
            journal = json.loads(journal_path.read_text())
            if journal.get('instance') == env['ARESOS_DESKTOP_INSTANCE']:
                scopes.extend(entry['unit'] for entry in journal['launches'].values() if entry.get('unit'))
        for unit in set(scopes):
            subprocess.run(['/usr/bin/systemctl', '--user', 'stop', unit], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        for proc in reversed(processes):
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
        for log in logs:
            log.close()
        print('owned processes and scopes stopped', flush=True)


if __name__ == '__main__':
    main()
