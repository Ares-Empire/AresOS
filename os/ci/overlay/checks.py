"""Fixed checks in a disposable test layer; no shell prompt or keyboard login."""
import functools
import importlib.util
import json
import os
import pathlib
import subprocess
import threading
import time
import traceback

from channel import Frames, export_bytes, frame

HERE = pathlib.Path(__file__).parent
EXPORTS = {'backend.json': '/run/aresos-backend.json',
           'runtime-updaters.json': '/run/aresos-updaters.json',
           'updater-regressions.json': '/run/aresos-updater-regressions.json',
           'power-events.json': '/run/aresos-power-events.json'}


def run(*args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=300, **kwargs)
    return dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def wait_session(extra_terminal=False):
    for _ in range(120):
        result = run('pgrep', '-u', 'ares', '-x', 'foot')
        if result['returncode'] == 0 and len(result['stdout'].split()) >= (2 if extra_terminal else 1):
            return result
        time.sleep(1)
    raise TimeoutError('AresOS terminal did not start')


RECOVERY_TERMINAL = ['/usr/bin/foot', '--title=AresOS', '/usr/bin/bash', '--rcfile', '/usr/share/aresos/bashrc', '-i']
# Package 23: the desktop supervisor's message window (first start, sign-in, recovery).
DESKTOP_VIEW = ['/usr/bin/foot', '--title=AresOS', '--app-id=aresos.desktop', '--window-size-chars=104x32',
                '/usr/bin/bash', '--rcfile', '/usr/share/aresos/desktop-view.bashrc', '-i']


def terminal_shells(pids):
    """Each AresOS terminal (recovery or desktop message) runs the system bash with an AresOS rcfile."""
    for _ in range(30):
        terminals = []
        for pid in pids:
            cmdline = pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')[:-1]
            environ = pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
            children = run('pgrep', '-P', pid)['stdout'].split()
            terminals.append(dict(pid=pid, cmdline=[part.decode() for part in cmdline],
                                  terminal=[v.decode() for v in environ if v.startswith(b'ARESOS_TERMINAL=')],
                                  shells=[os.readlink(f'/proc/{child}/exe') for child in children]))
        if all(terminal['shells'] == ['/usr/bin/bash'] for terminal in terminals):
            break
        time.sleep(1)
    for terminal in terminals:
        assert terminal['cmdline'] in (RECOVERY_TERMINAL, DESKTOP_VIEW), terminals
        assert terminal['shells'] == ['/usr/bin/bash'], terminals
        # Both are set up as recovery terminals: system PATH, never his ~/.bashrc.
        assert terminal['terminal'] == ['ARESOS_TERMINAL=recovery'], terminals
    assert [t for t in terminals if t['cmdline'] == RECOVERY_TERMINAL], ('no recovery terminal', terminals)
    return terminals


def processes():
    rows = []
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = [p.decode(errors='replace') for p in (entry / 'cmdline').read_bytes().split(b'\0')[:-1]]
            uid = int(next(line.split()[1] for line in (entry / 'status').read_text().splitlines()
                           if line.startswith('Uid:')))
            exe = os.readlink(entry / 'exe')
            cgroup = (entry / 'cgroup').read_text().strip()
            environ = (entry / 'environ').read_bytes().split(b'\0')
        except (OSError, StopIteration):
            continue
        rows.append(dict(pid=int(entry.name), uid=uid, cmdline=cmdline, exe=exe, cgroup=cgroup,
                         env={k.decode(): v.decode(errors='replace') for k, _, v in
                              (item.partition(b'=') for item in environ if b'=' in item)}))
    return rows


def desktop_session():
    """Package 23: the desktop supervisor, the app helper and Prism run as ares in the session, nothing as root."""
    for _ in range(90):
        status = run('runuser', '-u', 'ares', '--', 'env', '-i', 'HOME=/var/home/ares', 'XDG_RUNTIME_DIR=/run/user/1001',
                     '/usr/libexec/aresos-desktop', 'status')
        rows = processes()
        prism = [r for r in rows if r['exe'].startswith('/usr/lib/prismlauncher/') or
                 any('/usr/lib/prismlauncher/' in part for part in r['cmdline'][:1])]
        if status['returncode'] == 0 and prism:
            break
        time.sleep(2)
    assert status['returncode'] == 0, status
    state = json.loads(status['stdout'])
    # A fresh VM has no Microsoft account and no hub world: first start.
    assert state['state'] == 'SETUP' and not state['latched'], state
    ours = [r for r in rows if any(name in ' '.join(r['cmdline'][:2]) for name in
                                   ('aresos-desktop', 'aresos-shell', 'prismlauncher'))
            or r['exe'].startswith('/usr/lib/prismlauncher/')]
    assert ours and all(r['uid'] == 1001 for r in ours), [(r['pid'], r['uid'], r['cmdline']) for r in ours]
    keeper = [r for r in ours if r['cmdline'][1:3] == ['/usr/libexec/aresos-desktop', 'session']]
    supervisor = [r for r in ours if r['cmdline'][1:3] == ['/usr/libexec/aresos-desktop', 'supervise']]
    assert len(keeper) == 1 and len(supervisor) == 1, ours
    assert keeper[0]['cmdline'][0] == '/usr/bin/python3', keeper
    helper = [r for r in ours if r['cmdline'][1:2] == ['/usr/libexec/aresos-shell']]
    assert len(helper) == 1, ours
    runtime = json.loads(pathlib.Path('/run/user/1001/aresos/desktop-runtime.json').read_text())
    assert helper[0]['env'].get('ARESOS_DESKTOP_INSTANCE') == state['instance'] == runtime['instance'], helper
    assert helper[0]['env'].get('ARESOS_LAUNCH_NONCE') == runtime['nonce'], 'the helper has the launch nonce'
    assert prism, ours
    assert all('ARESOS_LAUNCH_NONCE' not in r['env'] for r in prism), 'Prism must not get the launch nonce'
    scope = [r for r in prism if f'/aresos.slice/aresos-desktop-{runtime["launch"]}.scope' in r['cgroup']]
    assert scope, [(r['pid'], r['cgroup']) for r in prism]
    instance = pathlib.Path('/var/home/ares/.local/share/PrismLauncher/instances/AresDesktop')
    links = {link: os.readlink(instance / link) for link in ('patches', 'libraries', 'minecraft/mods',
                                                              'minecraft/saves')}
    assert links == {'patches': '/usr/share/aresos/minecraft/patches',
                     'libraries': '/usr/share/aresos/minecraft/libraries',
                     'minecraft/mods': '/usr/share/aresos/minecraft/mods',
                     'minecraft/saves': '/var/home/ares/.local/share/aresos/worlds'}, links
    prism_log = pathlib.Path('/var/home/ares/.local/share/PrismLauncher/logs/PrismLauncher-0.log').read_text(
        errors='replace')
    assert 'Updates Enabled            : No' in prism_log
    assert 'ID of instance to launch   : "AresDesktop"' in prism_log, prism_log[:3000]
    supervisor_log = pathlib.Path('/var/home/ares/.local/state/aresos/desktop.log').read_text(errors='replace')
    return dict(state=state, runtime={k: v for k, v in runtime.items() if k != 'nonce'}, links=links,
                prism_scope=scope[0]['cgroup'],
                processes=[dict(pid=r['pid'], uid=r['uid'], cmdline=r['cmdline'][:4]) for r in ours],
                supervisor_log=supervisor_log[-4000:], prism_log=prism_log[:6000])


AS_ARES = ['runuser', '-u', 'ares', '--', 'env', '-i', 'HOME=/var/home/ares', 'XDG_RUNTIME_DIR=/run/user/1001',
           'PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin']
MIB, GIB = 1024 ** 2, 1024 ** 3


def desktop_status():
    result = run(*AS_ARES, '/usr/libexec/aresos-desktop', 'status')
    assert result['returncode'] == 0, result
    return json.loads(result['stdout'])


def cgroup_folder(pid):
    line = next(l for l in pathlib.Path(f'/proc/{pid}/cgroup').read_text().splitlines() if l.startswith('0::'))
    return '/sys/fs/cgroup' + line.split('::', 1)[1]


def desktop_jvm():
    """Package 23 review 1 (findings 1 and 4): a real JVM through the real wrapper and supervisor, as Prism would
    start it from outside the desktop's scope. It must run in its own game scope with the 2560 MiB target (package
    23d); killing that whole scope must latch recovery and never start Minecraft again by itself."""
    lock = json.loads(pathlib.Path('/usr/share/aresos/minecraft/desktop.lock.json').read_text())
    instance = '/var/home/ares/.local/share/PrismLauncher/instances/AresDesktop'
    pause = '/tmp/aresos-ci-jvm.paused'
    # A real JVM that waits (HotSpot's PauseAtStartup) until its pause file is removed or it is killed.
    wrapper = subprocess.Popen([*AS_ARES, 'INST_ID=AresDesktop', f'INST_DIR={instance}',
                                '/usr/libexec/aresos-desktop-java', lock['java']['path'],
                                '-XX:+UnlockDiagnosticVMOptions', '-XX:+PauseAtStartup',
                                f'-XX:PauseAtStartupFile={pause}', '-version'],
                               cwd=f'{instance}/minecraft', stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    for _ in range(120):
        state = desktop_status()
        if state['jvm_pid']:
            break
        assert wrapper.poll() is None, wrapper.communicate()
        time.sleep(0.5)
    jvm = state['jvm_pid']
    assert jvm, state
    runtime = json.loads(pathlib.Path('/run/user/1001/aresos/desktop-runtime.json').read_text())
    unit = f'aresos-game-{runtime["launch"]}.scope'
    folder = cgroup_folder(jvm)
    assert folder.endswith(f'/user@1001.service/aresos.slice/{unit}'), folder
    memory_high = pathlib.Path(folder, 'memory.high').read_text().strip()
    assert memory_high == str(2560 * MIB), memory_high
    assert os.path.realpath(f'/proc/{jvm}/exe') == os.path.realpath(lock['java']['path'])
    environ = dict(item.split('=', 1) for item in pathlib.Path(f'/proc/{jvm}/environ').read_text().split('\0')
                   if '=' in item)
    assert environ.get('ARESOS_LAUNCH_NONCE') == runtime['nonce'], 'the JVM has the launch nonce'
    assert environ.get('ARESOS_DESKTOP_INSTANCE') == runtime['instance']
    assert '__NV_PRIME_RENDER_OFFLOAD' not in environ, 'no NVIDIA offload without the NVIDIA driver'
    kill = run(*AS_ARES, '/usr/bin/systemctl', '--user', 'kill', '--signal=SIGKILL', unit)
    assert kill['returncode'] == 0, kill
    output, _ = wrapper.communicate(timeout=60)
    assert wrapper.returncode == 128 + 9, (wrapper.returncode, output)
    for _ in range(60):
        state = desktop_status()
        if state['latched']:
            break
        time.sleep(0.5)
    assert (state['state'], state['reason'], state['latched']) == ('RECOVERY', 'killed', True), state
    time.sleep(12)  # longer than the 5 s and 10 s crash backoffs: nothing may start again by itself
    after = desktop_status()
    assert (after['state'], after['reason'], after['jvm_pid']) == ('RECOVERY', 'killed', None), after
    return dict(jvm_cgroup=folder, memory_high=memory_high, unit=unit, wrapper_exit=wrapper.returncode,
                wrapper_output=output.decode(errors='replace')[-2000:], after=after)


def survivors():
    rows = processes()
    wanted = {}
    for row in rows:
        if row['uid'] != 1001:
            continue
        if row['exe'] == '/usr/bin/labwc':
            wanted['labwc'] = row
        elif row['cmdline'][1:3] == ['/usr/libexec/aresos-desktop', 'supervise']:
            wanted['supervisor'] = row
        elif row['cmdline'][1:3] == ['/usr/libexec/aresos-desktop', 'session']:
            wanted['keeper'] = row
        elif row['cmdline'] == RECOVERY_TERMINAL:
            wanted['recovery terminal'] = row
    return {name: (row['pid'], row['cgroup']) for name, row in wanted.items()}


def memory_protection():
    """Package 23 review 1 (finding 9): the effective protection of the session and its ancestors, and oomd."""
    found = survivors()
    session = '/sys/fs/cgroup' + found['labwc'][1].split('::', 1)[1]
    assert '/user.slice/user-1001.slice/session-' in session and session.endswith('.scope'), session
    low = {}
    for folder in ('/sys/fs/cgroup/user.slice', '/sys/fs/cgroup/user.slice/user-1001.slice', session):
        low[folder] = pathlib.Path(folder, 'memory.low').read_text().strip()
        assert low[folder] == str(GIB), low
    for name in ('supervisor', 'recovery terminal'):
        assert '/sys/fs/cgroup' + found[name][1].split('::', 1)[1] == session, found
    avoid = {}
    for name in ('user.oomd_avoid', 'trusted.oomd_avoid'):
        try:
            avoid[name] = os.getxattr(session, name).decode(errors='replace')
        except OSError as error:
            avoid[name] = f'unset ({error.strerror})'
    assert any(not value.startswith('unset') for value in avoid.values()), avoid
    oomd = run('systemctl', 'show', 'user@1001.service', '-p', 'ManagedOOMMemoryPressure',
               '-p', 'ManagedOOMMemoryPressureLimit', '-p', 'ManagedOOMSwap')
    oomctl = run('oomctl')
    return dict(memory_low=low, oomd_avoid=avoid, user_service=oomd['stdout'], oomctl=oomctl['stdout'][-3000:],
                oomd_active=run('systemctl', 'is-active', 'systemd-oomd.service')['stdout'].strip())


PRESSURE_UNIT = 'aresos-ci-pressure.scope'
# The pressure source says where it runs, then how much it holds after each step (64 MiB, every page touched).
HOG = """
import os, time
print('SCOPE', os.getpid(), open('/proc/self/cgroup').read().strip().replace('\\n', ' '), flush=True)
chunks = []
while True:
    chunk = bytearray(64 << 20)
    chunk[::4096] = b'\\1' * (len(chunk) // 4096)
    chunks.append(chunk)
    print('ALLOCATED', len(chunks) * 64, flush=True)
    time.sleep(0.05)
"""
# The source must reach at least this much before it is killed, so the kill comes from real memory pressure.
PRESSURE_MIN_MIB = 1024
# Every status request to the supervisor during the pressure must be answered within this time.
RESPONSIVE = 30.0


def pressure_command():
    return [*AS_ARES, '/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--slice=aresos.slice',
            f'--unit={PRESSURE_UNIT}', '--property=MemorySwapMax=0', '/usr/bin/python3', '-c', HOG]


def timed_status():
    """Seconds the supervisor took to answer a status request, or None if it did not answer in time."""
    started = time.monotonic()
    try:
        result = subprocess.run([*AS_ARES, '/usr/libexec/aresos-desktop', 'status'], capture_output=True,
                                text=True, timeout=RESPONSIVE)
        json.loads(result.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return None
    return time.monotonic() - started if result.returncode == 0 else None


def oom_evidence(pid):
    """The kernel's or systemd-oomd's record of killing the pressure source, and its scope's systemd result."""
    kernel = run('journalctl', '-k', '-o', 'cat', '--no-pager', '-n', '3000')['stdout'].splitlines()
    oomd = run('journalctl', '-u', 'systemd-oomd.service', '-o', 'cat', '--no-pager', '-n', '200')['stdout']
    unit = run(*AS_ARES, '/usr/bin/systemctl', '--user', 'show', PRESSURE_UNIT, '-p', 'Result')['stdout'].strip()
    kernel = [line for line in kernel if f'Killed process {pid} ' in line
              or (f'/{PRESSURE_UNIT},' in line and f'pid={pid},' in line)]
    oomd = [line for line in oomd.splitlines() if PRESSURE_UNIT in line]
    return dict(kernel=kernel, oomd=oomd, unit=unit,
                proven=bool(kernel or oomd or unit == 'Result=oom-kill'))


def memory_pressure():
    """Package 23 (review 1 finding 9, review 2 finding 9): exhaust memory from a scope next to the game's. The
    source must enter that scope, allocate, and be killed for memory (kernel or systemd-oomd evidence for exactly
    that scope or process); the supervisor answers throughout, and the compositor, the supervisor, its keeper and
    the recovery terminal survive."""
    before = survivors()
    assert set(before) == {'labwc', 'supervisor', 'keeper', 'recovery terminal'}, before
    hog = subprocess.Popen(pressure_command(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
    lines = []

    def read():
        for line in hog.stdout:
            lines.append(line.rstrip('\n'))
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    answers = []
    deadline = time.monotonic() + 600
    while hog.poll() is None and time.monotonic() < deadline:
        if any(line.startswith('ALLOCATED ') for line in lines):
            answers.append(timed_status())
        time.sleep(0.5)
    if hog.poll() is None:
        hog.kill()
        hog.wait()
        raise AssertionError(('the pressure source was not stopped within 600 s', lines[-5:]))
    reader.join(10)
    hog.stdout.close()
    scope = [line.split(' ', 2) for line in lines if line.startswith('SCOPE ')]
    assert scope, ('the pressure source never ran in its scope', hog.returncode, lines[-5:])
    pid, cgroup = int(scope[0][1]), scope[0][2]
    assert cgroup.endswith(f'/aresos.slice/{PRESSURE_UNIT}'), ('the pressure source ran elsewhere', cgroup)
    allocated = max([int(line.split()[1]) for line in lines if line.startswith('ALLOCATED ')], default=0)
    assert allocated >= PRESSURE_MIN_MIB, ('the pressure source ended before it made pressure', allocated,
                                           hog.returncode, lines[-5:])
    assert hog.returncode in (128 + 9, -9), ('the pressure source was not killed', hog.returncode, lines[-5:])
    evidence = oom_evidence(pid)
    assert evidence['proven'], ('no kernel or systemd-oomd record of killing the pressure source', evidence)
    assert answers and all(answer is not None for answer in answers), (
        'the supervisor did not answer within %d s during the pressure' % RESPONSIVE, answers)
    after = survivors()
    assert after == before, ('a protected process did not survive', before, after)
    state = desktop_status()
    return dict(hog_exit=hog.returncode, pid=pid, cgroup=cgroup, allocated_mib=allocated, status_seconds=answers,
                survivors=after, supervisor_state=state['state'], evidence=evidence)


# Package 23b: the startup cover in the real session. A fresh VM is in SETUP (no account, no hub), where the
# supervisor never shows it, so the check starts it by hand as ares in the labwc session, over the SETUP view and
# the recovery terminal; the host takes the screenshot between 'cover' and 'cover-stop'. Before that, 'cover'
# requires fontconfig to give the cover Space Grotesk as ares in the session (review 1, finding 1).
COVER = {}
COVER_TOP, COVER_BOTTOM = (26, 25, 30), (13, 13, 16)  # #1a191e, #0d0d10
SPACE_GROTESK = '/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf'


def ppm_corners(path):
    """Top-left and bottom-right pixels of a binary PPM (grim -t ppm)."""
    data = pathlib.Path(path).read_bytes()
    fields, offset = [], 0
    while len(fields) < 4:
        while data[offset:offset + 1].isspace():
            offset += 1
        end = offset
        while not data[end:end + 1].isspace():
            end += 1
        fields.append(data[offset:end])
        offset = end
    width, height, pixels = int(fields[1]), int(fields[2]), data[offset + 1:]
    last = ((height - 1) * width + width - 1) * 3
    return tuple(pixels[0:3]), tuple(pixels[last:last + 3])


def near(pixel, expected):
    return all(abs(a - b) <= 3 for a, b in zip(pixel, expected))


def session_fonts(env):
    """Review 1, finding 1: the file fontconfig gives the cover's two faces as ares in the real session. In the
    deployed image /usr has mtime 0, so a font cache made before /usr/share/fonts/aresos existed would hide package
    31's font here (the image check's container cannot see that); build.sh rebuilds the cache."""
    found = {}
    for pattern in ('Space Grotesk:bold', 'Space Grotesk'):
        result = run(*env, '/usr/bin/fc-match', '-f', '%{file}', pattern)
        assert result['returncode'] == 0, result
        found[pattern] = result['stdout']
    if set(found.values()) != {SPACE_GROTESK}:
        mtimes = run('stat', '-c', '%n %Y', '/usr/share/fonts', '/usr/share/fonts/aresos')
        raise AssertionError(f'fontconfig does not give the cover Space Grotesk: {found}; {mtimes}')
    return found


def cover_start():
    supervisor = [r for r in processes() if r['uid'] == 1001
                  and r['cmdline'][1:3] == ['/usr/libexec/aresos-desktop', 'supervise']]
    assert len(supervisor) == 1, supervisor
    display = supervisor[0]['env'].get('WAYLAND_DISPLAY')
    assert display, 'the supervisor has no WAYLAND_DISPLAY'
    env = [*AS_ARES, f'WAYLAND_DISPLAY={display}']
    fonts = session_fonts(env)
    COVER['process'] = subprocess.Popen([*env, '/usr/libexec/aresos-cover'], stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    shot = pathlib.Path('/tmp/aresos-ci-cover.ppm')
    corners = None
    for _ in range(60):
        time.sleep(0.5)
        assert COVER['process'].poll() is None, COVER['process'].communicate()[0]
        # grim writes the picture to stdout as bytes (run() would decode it as text).
        result = subprocess.run([*env, '/usr/bin/grim', '-t', 'ppm', '-'], capture_output=True, timeout=60)
        if result.returncode == 0:
            shot.write_bytes(result.stdout)
            corners = ppm_corners(shot)
            if near(corners[0], COVER_TOP) and near(corners[1], COVER_BOTTOM):
                break
    else:
        raise AssertionError(f'the cover never covered the screen (corners {corners})')
    pids = [r['pid'] for r in processes() if r['uid'] == 1001 and r['cmdline'][1:2] == ['/usr/libexec/aresos-cover']]
    assert len(pids) == 1, pids
    COVER['pid'] = pids[0]
    row = next(r for r in processes() if r['pid'] == pids[0])
    assert row['env'].get('WAYLAND_DISPLAY') == display, row['env']
    return dict(returncode=0, pid=pids[0], corners=corners, display=display, fonts=fonts,
                stdout='COVER_UP corners %s; fontconfig as ares: %s' % (corners, fonts))


def cover_stop():
    process, pid = COVER.pop('process'), COVER.pop('pid')
    started = time.monotonic()
    os.kill(pid, 15)

    def ended():
        try:
            return pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z'
        except OSError:
            return True
    while not ended() and time.monotonic() - started < 10:
        time.sleep(0.02)
    took = time.monotonic() - started
    # runuser hands on the cover's own exit status.
    output = process.communicate(timeout=10)[0].decode(errors='replace')
    assert process.returncode == 0 and took < 2.0, (process.returncode, took, output)
    assert not pathlib.Path(f'/proc/{pid}').exists()
    return dict(returncode=0, seconds=round(took, 3), output=output[-2000:],
                stdout=f'COVER_STOPPED by SIGTERM in {took:.3f} s, exit 0')


def shortcut_reached_the_supervisor():
    """Package 23b, PLAN-GAP 2: Super+Ctrl+Escape (sent by the host before 'shortcut') also ran the supervisor's
    hide-cover as ares in the session. The VM is in SETUP, never covered, so the supervisor logs that no cover is up;
    the command itself answers the same and changes nothing."""
    log = pathlib.Path('/var/home/ares/.local/state/aresos/desktop.log')
    for _ in range(40):
        if 'hide-cover (Super+Ctrl+Escape): no startup cover is up' in log.read_text(errors='replace'):
            break
        time.sleep(0.25)
    else:
        raise AssertionError('Super+Ctrl+Escape never reached the supervisor: ' + log.read_text(errors='replace')[-2000:])
    before = desktop_status()
    result = run(*AS_ARES, '/usr/libexec/aresos-desktop', 'hide-cover')
    assert (result['returncode'], result['stdout'].strip()) == (0, 'No startup cover is up.'), result
    after = desktop_status()
    assert (after['state'], after['reason'], after['cover']) == (before['state'], before['reason'], False), after
    return dict(state=after['state'], reason=after['reason'], answer=result['stdout'].strip())


def check(action, request):
    if action == 'policy':
        wait_session()
        regressions = run('python3', str(HERE / 'updater_regressions.py'))
        assert regressions['returncode'] == 0, regressions
        print(regressions['stdout'], flush=True)
        return run('bash', str(HERE / 'guest.sh'))
    if action == 'recovery':
        for _ in range(100):
            if pathlib.Path('/sys/class/tty/tty0/active').read_text().strip() == 'tty3':
                break
            time.sleep(0.1)
        else:
            raise TimeoutError('Recovery shortcut did not select tty3')
        getty = run('systemctl', 'show', 'getty@tty3.service', '-p', 'ActiveState', '-p', 'MainPID')
        assert 'ActiveState=active\n' in getty['stdout'], getty
        pid = int(next(line.split('=', 1)[1] for line in getty['stdout'].splitlines() if line.startswith('MainPID=')))
        assert pid > 0, getty
        cmdline = pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode()
        tty = os.readlink(f'/proc/{pid}/fd/0')
        assert 'agetty' in cmdline and tty == '/dev/tty3', (cmdline, tty)
        assert pathlib.Path('/sys/class/tty/tty0/active').read_text().strip() == 'tty3'
        result = run('python3', str(HERE / 'pam_check.py'), input=json.dumps({'password': request['password']}))
        result.update(getty=getty, getty_cmdline=cmdline, getty_tty=tty)
        return result
    if action == 'power-events':
        return run('python3', str(HERE / 'power-events.py'))
    if action == 'shortcut':
        result = wait_session(extra_terminal=True)
        result['hide_cover'] = shortcut_reached_the_supervisor()
        # Package 21 review 5: the session, its terminal and the recovery
        # terminal started although broken copies of every startup command
        # head the daily account's ~/.local/bin; none of them may have run.
        names = (HERE / 'shadow-names.txt').read_text().split()
        missing = [name for name in names if not os.access(f'/var/home/ares/.local/bin/{name}', os.X_OK)]
        assert names and not missing, ('shadowing programs missing', missing)
        result['terminals'] = terminal_shells(result['stdout'].split())
        result['desktop'] = desktop_session()
        result['memory_protection'] = memory_protection()
        result['game_scope'] = desktop_jvm()
        result['pressure'] = memory_pressure()
        # greetd's wrapper (non-interactive, not a login shell) sources
        # /etc/profile before the session: its profile scripts keep the system PATH.
        # Review 6: a missing probe or no wrapper record fails instead of passing.
        probe = pathlib.Path('/tmp/aresos-ci-profile-path')
        assert probe.is_file(), 'the profile probe recorded nothing'
        lines = probe.read_text().splitlines()
        wrappers = []
        for line in lines:
            arg0, flags, login, path = line.split('|', 3)
            if 'i' not in flags and not arg0.startswith('-') and not login:
                wrappers.append(path)
        assert wrappers, ('no non-interactive, non-login profile run (greetd wrapper) recorded', lines)
        for path in wrappers:
            assert '/var/home/ares/.local/bin' not in path.split(':'), ('session wrapper got the daily PATH', lines)
        result['profile_paths'] = lines
        ran = pathlib.Path('/tmp/aresos-ci-shadow-ran')
        assert not ran.exists(), ('a shadowing program ran', ran.read_text())
        result['shadowed'] = names
        return result
    if action == 'cover':
        return cover_start()
    if action == 'cover-stop':
        return cover_stop()
    if action == 'export':
        return dict(returncode=0, files={name: export_bytes(pathlib.Path(path).read_bytes())
                                       for name, path in EXPORTS.items() if pathlib.Path(path).exists()})
    if action == 'prepare-poweroff':
        # A separate cgroup without shutdown dependencies keeps the follower
        # alive after this check service stops. A cursor closes the startup gap.
        journal = run('journalctl', '--lines=1', '--show-cursor', '--no-pager', '--output=cat')
        assert journal['returncode'] == 0, journal
        cursor = journal['stdout'].rsplit('-- cursor: ', 1)[1].strip()
        assert cursor and '\n' not in cursor, journal
        follower = run('systemd-run', '--quiet', '--unit=aresos-ci-journal',
                       '--property=DefaultDependencies=no', '--property=IgnoreOnIsolate=yes',
                       '--property=Type=exec', '--property=StandardOutput=tty',
                       '--property=TTYPath=/dev/ttyS0', '/usr/bin/journalctl',
                       '--follow', f'--after-cursor={cursor}', '--no-pager', '--output=short-monotonic')
        assert follower['returncode'] == 0, follower
        assert run('logger', '--tag', 'aresos-ci', 'ARESOS_JOURNAL_READY')['returncode'] == 0
        boot_id = pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip().replace('-', '')
        assert run('logger', '--tag', 'aresos-ci', 'ARESOS_POWER_KEY_ARMED')['returncode'] == 0
        for operation in ('--flush', '--sync'):
            result = run('journalctl', operation)
            assert result['returncode'] == 0, result
        persistent = pathlib.Path('/var/log/journal')
        files = [str(path.relative_to(persistent)) for path in persistent.rglob('*.journal')]
        assert files, 'No persistent journal files before poweroff'
        config = run('systemd-analyze', 'cat-config', 'systemd/journald.conf')
        assert config['returncode'] == 0, config
        return dict(returncode=0, journal_unit='aresos-ci-journal.service', after_cursor=cursor,
                    boot_id=boot_id, persistent_files=files, journald_config=config['stdout'])
    layer = layer_actions()
    if action in layer:
        return layer[action](request)
    raise ValueError(f'Unknown check: {action}')


@functools.cache
def layer_actions():
    """Package 18c (agreed change 8): a test layer above this one adds its own
    actions as files in actions.d, each with ACTIONS = {name: function(request)}.
    The fixed actions above come first; a layer can add actions, never replace one."""
    actions = {}
    for path in sorted((HERE / 'actions.d').glob('*.py')):
        spec = importlib.util.spec_from_file_location(f'aresos_ci_layer_{path.stem}', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert not actions.keys() & module.ACTIONS.keys(), f'{path} repeats an action'
        actions.update(module.ACTIONS)
    return actions


def main():
    port = pathlib.Path('/dev/virtio-ports/org.aresos.ci')
    deadline = time.monotonic() + 60
    while not port.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('CI virtio port absent')
        time.sleep(0.2)
    with port.open('r+b', buffering=0) as stream:
        incoming = Frames(stream.read)

        def send(value):
            data = frame(value)
            while data:
                written = stream.write(data)
                if not written:
                    raise EOFError('CI virtio port stopped accepting data')
                data = data[written:]

        send(dict(ready=True, protocol=1))
        while True:
            request = incoming.receive()
            try:
                result = check(request['action'], request)
            except Exception:
                result = dict(returncode=1, stderr=traceback.format_exc())
            send(dict(id=request['id'], **result))


if __name__ == '__main__':
    main()
