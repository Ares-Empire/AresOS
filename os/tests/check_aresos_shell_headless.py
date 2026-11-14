"""Explicit laptop acceptance check; never imported by unittest discovery.

Own headless labwc, runtime, HOME, session bus, helper/socket and PIDs/scopes. No real-session
window/input or compositor reconfiguration. No installation or third-party assets.

Three cases: KCalc from its deployed binary, btop in Foot, and KCalc through its real Flatpak
desktop entry (`flatpak run`, which moves itself out of the helper's scope into its own).
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
FLATPAK_APP = 'org.kde.kcalc'
FLATPAK_ENTRY = Path('/var/lib/flatpak/exports/share/applications/org.kde.kcalc.desktop')
FLATPAK_SCOPE = 'app-flatpak-org.kde.kcalc-'
# The units this check can start: its own entries' scopes, the helper's scope for the Flatpak entry
# (systemd escapes its '-') and the scope `flatpak run` moves into.
CHECK_UNITS = ('app-aresos-check', 'app-aresos-org\\x2dkde\\x2dkcalc-', FLATPAK_SCOPE)
# Only the check's own programs (and KCalc) go into the public evidence, never the owner's catalogue.
EVIDENCE_APPS = ('check-kcalc', 'check-btop', 'org-kde-kcalc')
SESSION_BUS = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:path={path}</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""


def wait_for(predicate, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if value := predicate():
            return value
        time.sleep(0.1)
    raise AssertionError('timed out waiting for headless check')


def check_units():
    """The user manager's units this check could own, read-only: name -> active state."""
    listing = subprocess.run(['/usr/bin/systemctl', '--user', 'list-units', '--all', '--no-legend', '--plain',
                              '--no-pager'], capture_output=True, text=True, timeout=10, check=True).stdout
    units = {}
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[0].startswith(CHECK_UNITS):
            units[fields[0]] = fields[2]
    return units


def kcalc_in_session(own_units=()):
    """Why KCalc already runs outside this check, or None. Read-only: flatpak ps, the unit list, /proc."""
    instances = subprocess.run(['flatpak', 'ps', '--columns=application'], capture_output=True, text=True,
                               timeout=10).stdout.split()
    if FLATPAK_APP in instances:
        return 'flatpak ps lists ' + FLATPAK_APP
    if any(name.startswith(FLATPAK_SCOPE) and state == 'active' for name, state in check_units().items()):
        return 'a ' + FLATPAK_SCOPE + '* scope is active'
    for process in Path('/proc').glob('[0-9]*'):
        try:
            words = (process / 'cmdline').read_bytes().split(b'\0')
            cgroup = (process / 'cgroup').read_text()
        except OSError:
            continue
        if any(os.path.basename(word) == b'kcalc' or word == FLATPAK_APP.encode() for word in words):
            if not any(unit in cgroup for unit in own_units):
                return 'a kcalc process runs (PID %s)' % process.name
    return None


def helper_child_scope(parent):
    """(unit, PID) of the helper's child once `flatpak run` has moved it into its own scope."""
    for status in Path('/proc').glob('[0-9]*/status'):
        try:
            ppid = next(int(line.split()[1]) for line in status.read_text().splitlines() if line.startswith('PPid:'))
            unit = (status.parent / 'cgroup').read_text().strip().rsplit('/', 1)[-1]
        except (OSError, StopIteration, ValueError):
            continue
        if ppid == parent and unit.startswith(FLATPAK_SCOPE) and unit.endswith('.scope'):
            return unit, int(status.parent.name)
    return None


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
    units_before = check_units()
    print('check_units_before:', json.dumps(units_before, sort_keys=True), flush=True)
    kcalc_running = kcalc_in_session()
    print('kcalc_in_owner_session:', kcalc_running, flush=True)
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
        location = subprocess.check_output(['flatpak', 'info', '--show-location', FLATPAK_APP], text=True).strip()
        kcalc = Path(location) / 'files/bin/kcalc'
    assert kcalc.is_file()
    (entries / 'check-kcalc.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=KCalc check\n'
        f'Exec=/usr/bin/dbus-run-session -- {kcalc}\nStartupWMClass=org.kde.kcalc\n')
    (entries / 'check-btop.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Btop check\nExec=/usr/bin/btop\nTerminal=true\n')
    bus = runtime / 'bus'
    bus.unlink(missing_ok=True)
    (WORK / 'session-bus.conf').write_text(SESSION_BUS.format(path=bus))
    env = dict(os.environ, HOME=str(home), XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(config),
               XDG_DATA_HOME=str(home / '.local/share'), XDG_CACHE_HOME=str(home / '.cache'),
               XDG_STATE_HOME=str(home / '.local/state'), TMPDIR=str(WORK / 'tmp'),
               WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_HEADLESS_OUTPUTS='1',
               ARESOS_DESKTOP_INSTANCE=f'headless-30-{os.getpid()}',
               ARESOS_LAUNCH_NONCE='headless-30-test-nonce-0123456789',
               QT_QPA_PLATFORM='wayland', GDK_BACKEND='wayland', TERM='xterm-256color')
    # Only systemd-run/systemctl (and `flatpak run`, which moves itself into its own scope) reach the existing
    # user manager, through its private socket. The session bus is the check's own, without activation: the
    # Flatpak case's bus proxy, portals and helpers can't reach the owner's session or start anything there.
    env['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path={bus}'
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'WAYLAND_SOCKET', 'SESSION_MANAGER'):
        env.pop(key, None)
    processes, scopes, logs = [], [], []
    flatpak_units = []  # exact names read from the check's own child's cgroup, stopped by that name only
    client = reader = observer = None
    def spawn(args, name):
        log = open(WORK / (name + '.log'), 'w')
        logs.append(log)
        proc = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(proc)
        return proc
    try:
        spawn(['/usr/bin/dbus-daemon', '--config-file=' + str(WORK / 'session-bus.conf'), '--nofork', '--nopidfile'],
              'session-bus')
        wait_for(bus.is_socket)
        compositor = spawn(['/usr/bin/labwc', '--config-dir', str(config / 'labwc')], 'labwc')
        display = wait_for(lambda: next((p for p in runtime.glob('wayland-*') if p.is_socket()), None))
        env['WAYLAND_DISPLAY'] = display.name
        assert runtime != Path('/run/user/1001') and 'DISPLAY' not in env
        print('private_display:', display.relative_to(ROOT), 'labwc_pid:', compositor.pid,
              'private_bus:', bus.relative_to(ROOT), flush=True)
        hub = spawn(['/usr/bin/foot', '--app-id=aresos-desktop', '/usr/bin/sleep', '600'], 'hub')
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
        client.settimeout(120)
        client.connect(str(path))
        reader = client.makefile('rb')
        transcript = []
        def send(op, request_id, **fields):
            message = dict(protocol='aresos-shell/1.1', id=request_id, op=op, **fields)
            client.sendall(json.dumps(message).encode() + b'\n')
        def until(predicate, timeout=30):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                message = json.loads(reader.readline())
                if 'apps' in message:
                    shown = [app for app in message['apps'] if app['id'] in EVIDENCE_APPS]
                    transcript.append(dict(message, apps=shown, apps_count=len(message['apps'])))
                else:
                    transcript.append(message)
                if 'event' in message:
                    print('socket_event:', json.dumps(message, sort_keys=True), flush=True)
                if predicate(message):
                    return message
            raise AssertionError('missing socket reply/event')
        listings = iter(range(1, 10_000))
        def list_all():
            request_id = f'list-{next(listings)}'
            send('list_apps', request_id)
            page = until(lambda m: m.get('id') == request_id)
            apps = list(page['apps'])
            while 'next' in page:
                request_id = f'list-{next(listings)}'
                send('list_apps', request_id, cursor=page['next'])
                page = until(lambda m: m.get('id') == request_id)
                apps += page['apps']
            return {app['id']: app for app in apps}
        def journal_entry(request_id):
            return json.loads((runtime / 'aresos/shell-journal.json').read_text())['launches'][request_id]
        def unit_properties(unit):
            text = subprocess.check_output(['/usr/bin/systemctl', '--user', 'show', unit, '-p', 'Slice', '-p',
                                            'ControlGroup', '-p', 'ActiveState', '-p', 'LoadState'], env=env, text=True)
            return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
        def scope_pids(properties):
            procs = Path('/sys/fs/cgroup') / properties.get('ControlGroup', '').lstrip('/') / 'cgroup.procs'
            return procs.read_text().split() if properties.get('ControlGroup') and procs.exists() else []
        def close_and_return(request_id, app_id, expected_id, toplevel):
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
            print(app_id, 'return:', json.dumps(returned, sort_keys=True), flush=True)
            return returned
        send('hello', 'hello', major=1, minor=1, capabilities=sorted(shell.BASE_CAPABILITIES |
             shell.WINDOW_CAPABILITIES | shell.DETAIL_CAPABILITIES), requires=['windows', 'open_app'],
             instance=env['ARESOS_DESKTOP_INSTANCE'], nonce=env['ARESOS_LAUNCH_NONCE'])
        assert until(lambda m: m.get('id') == 'hello')['minor'] == 1
        assert {'check-kcalc', 'check-btop'} <= set(list_all())
        observations = []
        for app_id in ('check-kcalc', 'check-btop'):
            request_id = 'open-' + app_id
            send('open_app', request_id, app_id=app_id)
            answer = until(lambda m: m.get('id') == request_id)
            assert answer['ok'], answer
            unit = journal_entry(request_id)['unit']
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
            returned = close_and_return(request_id, app_id, expected_id, toplevel)
            observations.append(dict(app_id=app_id, unit=unit, properties=properties,
                                     window_app_id=toplevel.app_id, scope_pids=pids,
                                     focused=focused, returned=returned))
        print('HEADLESS_KCALC_BTOP_PASSED', flush=True)

        # Third case: KCalc through its real Flatpak entry, as Discord would start. The first case's entry claims
        # org.kde.kcalc first (the check's HOME is the first application folder), so it goes before this case.
        (entries / 'check-kcalc.desktop').unlink()
        app_id, request_id, flatpak = 'org-kde-kcalc', 'open-flatpak-kcalc', {}
        def catalogue_ready():
            apps = list_all()
            if 'check-kcalc' not in apps and app_id in apps:
                return apps[app_id]
            time.sleep(1)
            return None
        row = wait_for(catalogue_ready, timeout=30)
        assert row['available'] and row.get('desktop_id') == FLATPAK_ENTRY.name, row
        assert row.get('source') == 'flatpak-system', row
        entry_exec = next(line for line in FLATPAK_ENTRY.read_text().splitlines() if line.startswith('Exec='))
        assert ' run ' in entry_exec and entry_exec.endswith(' ' + FLATPAK_APP), entry_exec
        skip = kcalc_running or kcalc_in_session(scopes)
        if skip:
            flatpak = dict(skipped=skip)
            print('HEADLESS_FLATPAK_KCALC_SKIPPED:', skip, '(KCalc runs in the owner\'s session)', flush=True)
        else:
            send('open_app', request_id, app_id=app_id)
            answer = until(lambda m: m.get('id') == request_id)
            assert answer['ok'], answer
            unit = journal_entry(request_id)['unit']
            scopes.append(unit)
            # flatpak run moves itself (the helper's child) into app-flatpak-org.kde.kcalc-<n>.scope.
            flatpak_unit, child = wait_for(lambda: helper_child_scope(helper.pid), timeout=60)
            flatpak_units.append(flatpak_unit)
            print('flatpak_scope:', flatpak_unit, 'helper_child_pid:', child, flush=True)
            focused = until(lambda m: m.get('event') == 'app_state' and m.get('request_id') == request_id
                            and m.get('state') in ('focused', 'failed', 'closed'), timeout=90)
            assert focused['state'] == 'focused', focused
            toplevel = wait_for(lambda: next((t for t in observe().toplevels.values()
                                             if t.app_id == FLATPAK_APP and t.activated), None))
            own = unit_properties(unit)
            assert own.get('ActiveState') != 'active' or not scope_pids(own), own
            moved = unit_properties(flatpak_unit)
            moved_pids = scope_pids(moved)
            assert moved.get('ActiveState') == 'active' and str(child) in moved_pids, (moved, moved_pids)
            for pid in moved_pids:
                assert moved['ControlGroup'] in Path('/proc', pid, 'cgroup').read_text()
            time.sleep(2)  # A mapped/focused toplevel may not have painted its first frame yet.
            subprocess.run(['/usr/bin/grim', str(EVIDENCE / 'screenshots/check-flatpak-kcalc.png')],
                           env=env, check=True, timeout=10, capture_output=True)
            # Stays open while the helper's scope is empty: two of the helper's scope checks go by, then a round
            # trip, so every event decided before it is in the transcript.
            time.sleep(2 * shell.SCOPE_CHECK + 2)
            list_all()
            ended = [m for m in transcript if m.get('event') == 'app_state' and m.get('request_id') == request_id
                     and m.get('state') != 'focused']
            assert not ended, ended
            assert journal_entry(request_id)['state'] == 'focused'
            assert any(t.app_id == FLATPAK_APP for t in observe().toplevels.values())
            own_later = unit_properties(unit)
            assert own_later.get('ActiveState') != 'active' or not scope_pids(own_later), own_later
            print(app_id, 'helper_scope:', json.dumps(own_later, sort_keys=True), 'flatpak_scope:',
                  json.dumps(moved, sort_keys=True), 'scope_pids=' + ','.join(moved_pids),
                  'window_app_id=' + toplevel.app_id, flush=True)
            returned = close_and_return(request_id, app_id, FLATPAK_APP, toplevel)
            wait_for(lambda: unit_properties(flatpak_unit).get('ActiveState') != 'active', timeout=30)
            wait_for(lambda: not Path('/proc', str(child)).exists(), timeout=30)
            flatpak_units.remove(flatpak_unit)
            flatpak = dict(app_id=app_id, unit=unit, helper_scope_while_open=own_later, flatpak_scope=flatpak_unit,
                           flatpak_scope_while_open=moved, flatpak_scope_pids=moved_pids,
                           window_app_id=toplevel.app_id, focused=focused, returned=returned,
                           entry_exec=entry_exec.split('=', 1)[1])
            print('HEADLESS_FLATPAK_KCALC_PASSED', flush=True)
        (EVIDENCE / 'headless.json').write_text(json.dumps(dict(display=str(display.relative_to(ROOT)),
            kcalc_binary=str(kcalc), observations=observations, flatpak=flatpak, transcript=transcript),
            indent=2) + '\n')
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
        for unit in set(scopes) | set(flatpak_units):
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
        time.sleep(1)
        left = {name: state for name, state in check_units().items() if name not in units_before}
        print('check_units_left:', json.dumps(left, sort_keys=True), flush=True)
        print('owned processes and scopes stopped', flush=True)


if __name__ == '__main__':
    main()
