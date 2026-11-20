"""Package 25, the guardian, in the check build's VM (brief 25, Acceptance; the lead's fixes 5 and 6).

`arm` (the check channel's action `guardian-arm`, before the host presses the power key) makes the session look
like his laptop when he shuts it down in his home: a sound, disposable home on the disk, a real JVM that the
supervisor took as the game through the real wrapper and whose lifecycle hello it accepted, and no app window
open. It checks the guard unit as systemd loaded it, and starts three watchers that the check service's own stop
cannot reach:

- `probe` (as ares) samples twice a second what must still be there while the home is saved, and holds one
  connection to the supervisor that it writes to and never reads;
- `lid` (as root) closes a virtual lid when the game is asked to save;
- `record` (as root) is the stop of a unit ordered before the guard, so it runs after the guard's stop has ended,
  and copies the stop record from desktop.json into the journal.

Everything they say goes to the journal, which the host reads offline after the power-off. The evidence holds
allowlisted fields only: never an environment, a runtime file, a nonce, a token or a launch's id.
"""
import fcntl
import gzip
import json
import os
import pathlib
import re
import socket
import struct
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
HOME = '/var/home/ares'
RUNTIME = '/run/user/1001'
SYSTEM_PATH = '/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin'
AS_ARES = ['runuser', '-u', 'ares', '--', 'env', '-i', f'HOME={HOME}', f'XDG_RUNTIME_DIR={RUNTIME}',
           f'PATH={SYSTEM_PATH}']
DESKTOP = '/usr/libexec/aresos-desktop'
GUARD = 'aresos-guardian.service'
GAME = HERE / 'GuardianGame.java'
INSTANCE = f'{HOME}/.local/share/PrismLauncher/instances/AresDesktop'
WORLDS = f'{HOME}/.local/share/aresos/worlds'
STATE = f'{HOME}/.local/state/aresos'
SOCKET = f'{RUNTIME}/aresos/desktop.sock'
# The game writes this file when it is asked to save; the lid watcher waits for it.
MARKER = f'{RUNTIME}/aresos-ci-guardian-save-asked'
CAMERA_PORT = pathlib.Path('/dev/virtio-ports/org.aresos.guardian')
SCENARIOS = ('save', 'hang')
SAVE_MS = 5000  # boot 1: the save takes 5 s
RECOVERY_TERMINAL = ['/usr/bin/foot', '--title=AresOS', '/usr/bin/bash', '--rcfile', '/usr/share/aresos/bashrc', '-i']
# What survives the check service's stop and the shutdown's first transaction: no default dependencies.
DETACHED = ['--property=DefaultDependencies=no', '--property=IgnoreOnIsolate=yes']
# The stop record's fields that go into the evidence (brief 2.3); never the launch's id.
RECORD_FIELDS = ('open', 'kind', 'phase', 'save', 'why', 'sigterm', 'close', 'status')


def run(*args, timeout=120, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, **kwargs)
    return dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


# ---------------------------------------------------------------- the seeded home (the lead's fix 5)

BYTE, INT, LONG, FLOAT, STRING, COMPOUND = 1, 3, 4, 5, 8, 10


def nbt(tag, value):
    """Minecraft's NBT, as much of it as a home's three files need."""
    if tag in (BYTE, INT, LONG, FLOAT):
        return struct.pack({BYTE: '>b', INT: '>i', LONG: '>q', FLOAT: '>f'}[tag], value)
    if tag == STRING:
        data = value.encode()
        return struct.pack('>H', len(data)) + data
    out = b''
    for name, (child, item) in value.items():
        out += struct.pack('>b', child) + nbt(STRING, name) + nbt(child, item)
    return out + b'\0'


def nbt_file(root):
    return gzip.compress(struct.pack('>b', COMPOUND) + nbt(STRING, '') + nbt(COMPOUND, root))


def seed_world(worlds, name='AresHub'):
    """A disposable home that passes the supervisor's own checks (check_world), so a stop takes the save path. It
    holds no chunks: nothing ever opens it, the stand-in game only answers for it."""
    world = pathlib.Path(worlds) / name
    (world / 'data/aresos').mkdir(parents=True)

    def saved(data):
        return {'data': (COMPOUND, data), 'DataVersion': (INT, 4903)}
    (world / 'level.dat').write_bytes(nbt_file({'Data': (COMPOUND, {'LevelName': (STRING, 'AresOS'),
                                                                   'version': (INT, 19133)})}))
    (world / 'data/aresos/desktop.dat').write_bytes(nbt_file(saved({'enabled': (BYTE, 1)})))
    (world / 'data/aresos/nether_home.dat').write_bytes(nbt_file(saved({
        'seed': (LONG, 49), 'x': (INT, -64), 'y': (INT, 56), 'z': (INT, 32), 'yaw': (FLOAT, 0.0)})))
    (world / 'aresos-home.properties').write_text('version=1\nseed=49\n')
    (world / 'aresos-home.provisioned').write_text('complete\n')
    return world


# ---------------------------------------------------------------- arm


def status():
    result = run(*AS_ARES, DESKTOP, 'status')
    assert result['returncode'] == 0, result
    return json.loads(result['stdout'])


def wait_status(condition, seconds, what):
    deadline = time.monotonic() + seconds
    while True:
        state = status()
        if condition(state):
            return state
        if time.monotonic() >= deadline:
            shown = {key: state.get(key) for key in ('state', 'reason', 'latched', 'lifecycle', 'windows', 'labwc')}
            game = run('journalctl', '-b', '-u', 'aresos-ci-game.service', '-o', 'cat', '--no-pager', '-n', '30')
            raise AssertionError((f'not within {seconds} s: {what}', shown, game['stdout'][-3000:]))
        time.sleep(0.5)


def ours(match):
    """PIDs of ares's processes whose (exe, cmdline) match."""
    found = []
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != 1001:
                continue
            cmdline = [part.decode(errors='replace') for part in (entry / 'cmdline').read_bytes().split(b'\0')[:-1]]
            exe = os.readlink(entry / 'exe')
        except OSError:
            continue
        if match(exe, cmdline):
            found.append(int(entry.name))
    return found


def show(unit, *properties, user=False):
    command = ['/usr/bin/systemctl', *(['--user'] if user else []), 'show', unit, *(f'--property={p}' for p in properties)]
    result = run(*AS_ARES, *command) if user else run(*command)
    assert result['returncode'] == 0, result
    return dict(line.split('=', 1) for line in result['stdout'].splitlines() if '=' in line)


def first_authorization():
    """(microseconds since boot, where it was read) of the session's first authorized JVM, or (None, why)."""
    found = run('journalctl', '-b', '--no-pager', '-o', 'json', '-g', 'launch [0-9a-f]+: the game is starting')
    for line in found['stdout'].splitlines():
        try:
            return int(json.loads(line)['__MONOTONIC_TIMESTAMP']), 'the journal'
        except (ValueError, KeyError):
            continue
    # The supervisor's own log has wall-clock times: bring the first such line onto the boot's clock.
    try:
        log = pathlib.Path(STATE, 'desktop.log').read_text(errors='replace')
    except OSError as error:
        return None, f'no journal line, and desktop.log: {error}'
    for line in log.splitlines():
        match = re.match(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) aresos-desktop: INFO launch [0-9a-f]+: the game is starting', line)
        if match:
            wall = time.mktime(time.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')) + int(match.group(2)) / 1000
            return int((wall - (time.time() - time.monotonic())) * 1_000_000), 'desktop.log (wall clock)'
    return None, 'no JVM was authorized yet'


def detached(unit, identifier, *command, user=None, properties=()):
    """A transient unit that neither this check service's stop nor the shutdown's first transaction ends."""
    args = ['systemd-run', '--quiet', f'--unit={unit}', *DETACHED, f'--property=SyslogIdentifier={identifier}',
            *properties]
    if user:
        args += [f'--uid={user}', f'--setenv=HOME={HOME}', f'--setenv=XDG_RUNTIME_DIR={RUNTIME}',
                 f'--setenv=PATH={SYSTEM_PATH}']
    result = run(*args, *command)
    assert result['returncode'] == 0, result
    return result


def arm(request):
    scenario = request.get('scenario')
    assert scenario in SCENARIOS, scenario
    facts = dict(scenario=scenario)

    # The guard as systemd loaded it: active, enabled, 85 s, and ordered after what must outlive the save.
    labwc = ours(lambda exe, cmdline: exe == '/usr/bin/labwc')
    assert len(labwc) == 1, labwc
    cgroup = next(line for line in pathlib.Path(f'/proc/{labwc[0]}/cgroup').read_text().splitlines()
                  if line.startswith('0::'))
    session = cgroup.rsplit('/', 1)[1]
    assert re.fullmatch(r'session-[0-9a-z]+\.scope', session), cgroup
    target = run('findmnt', '--noheadings', '--output', 'TARGET', '--target', HOME)
    assert target['returncode'] == 0 and target['stdout'].strip(), target
    mount = run('systemd-escape', '--path', '--suffix=mount', target['stdout'].strip())['stdout'].strip()
    guard = show(GUARD, 'ActiveState', 'SubState', 'UnitFileState', 'After', 'TimeoutStopUSec', 'User',
                 'ActiveEnterTimestampMonotonic', 'ExecStop')
    after = guard['After'].split()
    protected = ('greetd.service', 'user@1001.service', 'user-runtime-dir@1001.service', 'polkit.service',
                 'getty@tty3.service', mount)
    facts['guard'] = dict(active=guard['ActiveState'], sub=guard['SubState'], enabled=guard['UnitFileState'],
                          timeout_stop=guard['TimeoutStopUSec'], user=guard['User'],
                          active_since_us=int(guard['ActiveEnterTimestampMonotonic']),
                          after=sorted(set(protected).intersection(after)))
    assert (guard['ActiveState'], guard['SubState'], guard['UnitFileState']) == ('active', 'exited', 'enabled'), guard
    assert guard['TimeoutStopUSec'] == '1min 25s' and guard['User'] == 'ares', guard
    assert 'aresos-desktop ; argv[]=/usr/libexec/aresos-desktop stop --reason shutdown' in guard['ExecStop'], guard
    for unit in protected:
        assert unit in after, (unit, 'is not ordered before the guard', after)
    scope = show(session, 'ActiveState', 'Before', 'TimeoutStopUSec')
    assert scope['ActiveState'] == 'active' and GUARD in scope['Before'].split(), scope
    facts.update(session_scope=session, home_mount=mount, session_scope_timeout_stop=scope['TimeoutStopUSec'])
    cycles = run('journalctl', '-b', '--no-pager', '-o', 'cat', '-g', 'ordering cycle')
    assert not cycles['stdout'].strip(), ('systemd found an ordering cycle at boot', cycles['stdout'][-2000:])

    # The image's Java must run a single-file program (else the class has to be built into this overlay).
    lock = json.loads(pathlib.Path('/usr/share/aresos/minecraft/desktop.lock.json').read_text())
    java = lock['java']['path']
    modules = run(*AS_ARES, java, '--list-modules')
    assert 'jdk.compiler' in modules['stdout'], ('the pinned Java cannot run a single-file program: build '
                                                 'GuardianGame into the overlay', modules['stdout'][:500])

    # His laptop when he shuts it down in his home: a home on the disk, no app window, the game running.
    before = status()
    assert before['labwc'] is True, 'the supervisor does not watch its session\'s labwc'
    facts['before'] = {key: before.get(key) for key in ('state', 'reason', 'latched', 'labwc')}
    assert not pathlib.Path(WORLDS, 'AresHub').exists(), 'the VM already has a home'
    seeded = run(*AS_ARES, '/usr/bin/python3', str(HERE / 'guardian.py'), 'seed')
    assert seeded['returncode'] == 0, seeded
    for pid in ours(lambda exe, cmdline: cmdline == RECOVERY_TERMINAL):
        os.kill(pid, 15)
    # The shortcut step left the latch `killed`: `retry` answers once memory pressure has been clear for a minute.
    began = time.monotonic()
    while True:
        retried = run(*AS_ARES, DESKTOP, 'retry')
        if retried['returncode'] == 0:
            break
        assert time.monotonic() - began < 240, ('retry never cleared the latch', retried)
        time.sleep(5)
    facts['retry_seconds'] = round(time.monotonic() - began, 1)
    pathlib.Path(MARKER).unlink(missing_ok=True)
    assert CAMERA_PORT.is_char_device(), 'the VM has no guardian camera port'
    os.chown(CAMERA_PORT, 1001, -1)  # only this disposable port, for the unprivileged fixture JVM
    detached('aresos-ci-game', 'aresos-ci-game', '/usr/libexec/aresos-desktop-java', java, str(GAME), scenario,
             str(SAVE_MS), MARKER, str(CAMERA_PORT), user='ares',
             properties=['--setenv=INST_ID=AresDesktop', f'--setenv=INST_DIR={INSTANCE}',
                         f'--working-directory={INSTANCE}/minecraft'])
    state = wait_status(lambda s: s.get('jvm_pid') and s.get('lifecycle') is True, 120,
                        'the game runs and its lifecycle hello is accepted')
    jvm = state['jvm_pid']
    assert os.path.realpath(f'/proc/{jvm}/exe') == os.path.realpath(java), 'the game is not the pinned Java'
    wrapper = int(show('aresos-ci-game.service', 'MainPID')['MainPID'])
    assert wrapper > 0 and wrapper != jvm, (wrapper, jvm)
    # Prism's own window counts as an app window: end the Prism that `retry` started. The game is the JVM above.
    for pid in ours(lambda exe, cmdline: exe.startswith('/usr/lib/prismlauncher/')
                    or any('prismlauncher' in part for part in cmdline[:1])):
        os.kill(pid, 15)
    state = wait_status(lambda s: s.get('windows') == [] and s.get('jvm_pid') == jvm and s.get('lifecycle') is True,
                        60, 'no app window is open and the game still runs')
    assert not state['latched'] and not state['stopping'], state
    facts['armed'] = {key: state.get(key) for key in ('state', 'reason', 'latched', 'lifecycle', 'windows', 'labwc',
                                                      'stopping', 'black', 'lid_block', 'helper')}

    # The lead's fix 6: the game scope's effective stop limit is 15 s. The session scope's is printed.
    game = show(f'aresos-game-{state["launch"]}.scope', 'ActiveState', 'TimeoutStopUSec', user=True)
    assert game == {'ActiveState': 'active', 'TimeoutStopUSec': '15s'}, game
    facts['game_scope_timeout_stop'] = game['TimeoutStopUSec']

    # Armed first: the guard was active before the session's first JVM was authorized.
    authorized, basis = first_authorization()
    assert authorized is not None, basis
    assert 0 < facts['guard']['active_since_us'] < authorized, (facts['guard'], authorized, basis)
    facts['first_jvm_authorized_us'], facts['first_jvm_basis'] = authorized, basis

    # The watchers.
    watcher = ['/usr/bin/python3', str(HERE / 'guardian.py')]
    detached('aresos-ci-guardian-probe', 'aresos-ci-probe', *watcher, 'probe', str(jvm), str(wrapper), str(labwc[0]),
             session, mount, user='ares')
    if scenario == 'save':
        detached('aresos-ci-guardian-lid', 'aresos-ci-lid', *watcher, 'lid')
    recorder = run('systemd-run', '--quiet', '--unit=aresos-ci-guardian-record', '--service-type=oneshot',
                   '--remain-after-exit', f'--property=Before={GUARD}', '--property=SyslogIdentifier=aresos-ci-record',
                   f'--property=ExecStop={" ".join(watcher)} record {jvm}', '/usr/bin/true')
    assert recorder['returncode'] == 0, recorder
    time.sleep(3)  # the probe's first samples and the lid's device are there before the power key
    for unit in ('polkit.service', 'getty@tty3.service', 'aresos-ci-guardian-probe.service',
                 'aresos-ci-guardian-record.service', 'aresos-ci-game.service',
                 *(['aresos-ci-guardian-lid.service'] if scenario == 'save' else [])):
        assert show(unit, 'ActiveState')['ActiveState'] == 'active', unit
    facts['stdout'] = (f'GUARDIAN_ARMED ({scenario}): the guard is active and ordered after greetd, the user manager, '
                       f'polkit, the tty3 getty, the runtime folder and {mount}, with {session} before it; '
                       f'the game scope stops within {game["TimeoutStopUSec"]}, the session scope within '
                       f'{scope["TimeoutStopUSec"]}; the stand-in '
                       'game runs with an accepted hello and no app window is open')
    return dict(returncode=0, **facts)


# ---------------------------------------------------------------- the watchers


def say(tag, value):
    print(f'{tag} {json.dumps(value, sort_keys=True)}', flush=True)


def alive(pid):
    try:
        return pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'
    except (OSError, IndexError):
        return False


def ask_status():
    """The supervisor's answer to `status`, or None: the socket is there and the loop answers."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            sock.connect(SOCKET)
            sock.sendall(b'{"op": "status"}\n')
            data = b''
            while not data.endswith(b'\n'):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        return json.loads(data)
    except (OSError, ValueError):
        return None


def home_writable():
    try:
        folder = pathlib.Path(HOME, '.cache')
        folder.mkdir(exist_ok=True)
        with open(folder / 'aresos-ci-guardian-probe', 'w') as output:
            output.write(f'{time.monotonic()}\n')
            output.flush()
            os.fsync(output.fileno())
        return True
    except OSError:
        return False


def probe(jvm, wrapper, labwc, session, mount):
    """As ares, twice a second: what must still be there while the home is saved. One line for each change and at
    least one each second. From the moment the guard's stop begins, the second connection asks for `status` again
    and again and never reads an answer: the supervisor must drop it and go on."""
    units = (GUARD, session, 'greetd.service', 'user@1001.service', mount)
    try:
        silent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        silent.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
        silent.connect(SOCKET)
        silent.setblocking(False)
    except OSError as error:
        silent = None
        say('GUARDIAN_PROBE_PEER', dict(connected=False, error=type(error).__name__))
    sent, last, said = 0, None, 0.0
    deadline = time.monotonic() + 400
    while time.monotonic() < deadline:
        try:
            states = subprocess.run(['/usr/bin/systemctl', 'is-active', *units], capture_output=True, text=True,
                                    timeout=10).stdout.split()
        except (OSError, subprocess.SubprocessError):
            states = []  # late in the shutdown systemd no longer answers
        states = dict(zip(('guard', 'session', 'greetd', 'user', 'home_mount'), states))
        answer = ask_status()
        sample = dict(labwc=alive(labwc), jvm=alive(jvm), wrapper=alive(wrapper), socket=answer is not None,
                      home=home_writable(), units=states,
                      black_window=bool(ours(lambda exe, cmdline: '/usr/libexec/aresos-cover' in cmdline[1:2]
                                             and '--black' in cmdline)),
                      black=bool(answer and answer.get('black')), lid_block=bool(answer and answer.get('lid_block')),
                      stopping=bool(answer and answer.get('stopping')),
                      windows=len(answer['windows']) if answer and isinstance(answer.get('windows'), list) else None)
        try:
            sample['tty'] = pathlib.Path('/sys/class/tty/tty0/active').read_text().strip()
        except OSError:
            sample['tty'] = None
        now = time.monotonic()
        if sample != last or now - said >= 1.0:
            say('GUARDIAN_PROBE', dict(sample, t=round(now, 3)))
            last, said = sample, now
        if silent is not None and states.get('guard') not in ('active', None):
            try:
                for _ in range(64):
                    silent.send(b'{"op": "status"}\n')
                    sent += 1
            except BlockingIOError:
                pass  # its own buffer is full: the supervisor has not dropped it yet
            except OSError as error:
                say('GUARDIAN_PROBE_PEER', dict(dropped=True, after_requests=sent, error=type(error).__name__,
                                                t=round(time.monotonic(), 3)))
                silent.close()
                silent = None
        time.sleep(0.3)


def lid():
    """As root: a virtual lid (uinput, as os/tests/power-events.py makes one) that closes when the game is asked
    to save, and stays closed. Then what logind lists as inhibitors: AresOS's lid block, taken by the supervisor."""
    subprocess.run(['modprobe', 'uinput'], check=False)
    with open('/dev/uinput', 'wb', buffering=0) as device:
        fcntl.ioctl(device, 0x40045564, 1)   # UI_SET_EVBIT(EV_KEY), as that script's device: logind opens it
        fcntl.ioctl(device, 0x40045565, 142) # UI_SET_KEYBIT(KEY_SLEEP); never pressed
        fcntl.ioctl(device, 0x40045564, 5)   # UI_SET_EVBIT(EV_SW)
        fcntl.ioctl(device, 0x4004556d, 0)   # UI_SET_SWBIT(SW_LID)
        fcntl.ioctl(device, 0x405c5503, struct.pack('HHHH80sI', 3, 0x1234, 2, 1, b'AresOS CI guardian lid', 0))
        fcntl.ioctl(device, 0x5501)          # UI_DEV_CREATE
        subprocess.run(['udevadm', 'settle'], check=False)
        say('GUARDIAN_LID', dict(ready=True))
        deadline = time.monotonic() + 600
        while not os.path.exists(MARKER) and time.monotonic() < deadline:
            time.sleep(0.05)
        if not os.path.exists(MARKER):
            say('GUARDIAN_LID', dict(closed=False, why='the game was never asked to save'))
            return
        device.write(struct.pack('llHHi', 0, 0, 5, 0, 1))  # EV_SW, SW_LID, closed
        device.write(struct.pack('llHHi', 0, 0, 0, 0, 0))  # SYN_REPORT
        sent = time.monotonic()
        time.sleep(0.7)
        closed = subprocess.run(['busctl', 'get-property', 'org.freedesktop.login1', '/org/freedesktop/login1',
                                 'org.freedesktop.login1.Manager', 'LidClosed'], capture_output=True, text=True,
                                timeout=20).stdout.strip()
        listed = subprocess.run(['systemd-inhibit', '--list', '--no-pager'], capture_output=True, text=True,
                                timeout=20).stdout
        blocks = [' '.join(line.split()) for line in listed.splitlines()
                  if 'AresOS' in line and 'handle-lid-switch' in line]
        say('GUARDIAN_LID', dict(closed=True, t=round(sent, 3), logind_lid_closed=closed, aresos_lid_blocks=blocks))
        time.sleep(600)  # the lid stays closed: he has left


def record(jvm):
    """After the guard's stop has ended: the stop record as it is on the disk, and whether Java is still there."""
    result = dict(jvm_alive=alive(jvm), fallback_record=os.path.exists(os.path.join(STATE, 'desktop-guard.json')))
    try:
        data = json.loads(pathlib.Path(STATE, 'desktop.json').read_text())
        stop = data.get('stop') if isinstance(data.get('stop'), dict) else {}
        result.update(latched=data.get('latched'), reason=data.get('reason'),
                      stop={key: stop.get(key) for key in RECORD_FIELDS})
    except (OSError, ValueError) as error:
        result['error'] = type(error).__name__
    say('GUARDIAN_RECORD', result)


def main(argv):
    if argv[:1] == ['seed']:
        seed_world(WORLDS)
    elif argv[:1] == ['probe']:
        probe(int(argv[1]), int(argv[2]), int(argv[3]), argv[4], argv[5])
    elif argv[:1] == ['lid']:
        lid()
    elif argv[:1] == ['record']:
        record(int(argv[1]))
    else:
        raise SystemExit('guardian.py seed | probe <jvm> <wrapper> <labwc> <session scope> <home mount> | lid | record <jvm>')


if __name__ == '__main__':
    main(sys.argv[1:])
