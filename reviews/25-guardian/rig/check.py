#!/usr/bin/python3
# DEVELOPMENT AID of package 25 (the real-game check), headless use only.
"""The steps of one launch of the real-game check (briefs/25-guardian.md, Acceptance), called by check.sh:

  check.py prepare <rig> <mode> <unit> <memory high> <java>   the launch's identity and the java wrapper's settings
  check.py run <rig> <mode> <probe> <verify> <health pid>      the check itself, once the game's JVM runs
  check.py evidence <rig> <out.json>                           the public evidence: allowlisted fields only
  check.py sweep <rig>                                         end the test supervisor and its stand-ins

Modes: `create` (the game makes the first home; the rig adds its probe data pack), `close` (the close alone: a block,
SIGTERM to the rig's own game, what the disk holds after Java's exit), `stop` (the path: the real supervisor adopts
the rig's game, the hello, `save`, `stop`), `verify` (reopen and look). Every mode but `create` first asks the
reopened game itself whether the blocks of the launch before are there.

The machine rules: the supervisor runs under `env -i` with HOME, the run's temporary XDG_RUNTIME_DIR, PATH and the
LABWC_PID of a stand-in started here. A process is signalled only if its own /proc/<pid>/environ names that runtime
folder. Before anything else the game's own environment is checked for it: with the session's folder the mod would
dial the owner's live supervisor."""
import importlib.machinery
import json
import os
import pathlib
import re
import secrets
import select
import shutil
import signal
import subprocess
import sys
import time
import types

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
WT = HERE.parents[2]
SUPERVISOR = WT / 'os/config/usr/libexec/aresos-desktop'
WRAPPER = WT / 'os/config/usr/libexec/aresos-desktop-java'
PINS = WT / 'os/minecraft/desktop.lock.json'
WINDOW_TOOL = WT / 'reviews/40-real-home/rig/tl.py'
WORLD, PACK = 'AresHub', 'pkg25-probe'
PROBE_BLOCK, PROBES = 'minecraft:glass', 56
HOME_BLOCK = (0, 63, 0)  # the pad's centre, a gold block (mod/README.md, "The flat home")
SYSTEM_PATH = 'PATH=/usr/bin:/bin'
# What the game's log says while the server stops (the brief asks for these lines), and nothing else of the log.
STOP_LINES = re.compile(r'Stopping server|Saving players|Saving worlds|Saving chunks for level|All chunks are saved|'
                        r'All dimensions are saved|Stopping!|[Ll]ifecycle|Client Shutdown')
PATHS = re.compile(r'(?:/var)?/home/\S+|/run/user/\S+|/tmp/\S+')

sys.path.insert(0, str(HERE))
import region  # noqa: E402
from input import Writer  # noqa: E402


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = types.ModuleType(loader.name)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class Unshown(Exception):
    """The rig could not show what it is for. Never a verdict on the close."""


class Rig:
    def __init__(self, folder):
        self.rig = pathlib.Path(folder).resolve()
        self.work = self.rig.parents[1]
        self.home = self.work / 'home'  # the test supervisor's HOME
        self.runtime = self.rig / 'rt'  # its temporary XDG_RUNTIME_DIR, and the game's
        self.world = self.home / '.local/share/aresos/worlds' / WORLD
        self.state = self.home / '.local/state/aresos'
        self.private, self.control, self.bin = self.rig / 'private', self.rig / 'control', self.rig / 'bin'
        self.game_log = WT / 'mod/run/logs/latest.log'
        self.environment = [f'HOME={self.home}', f'XDG_RUNTIME_DIR={self.runtime}', SYSTEM_PATH]
        self.result_file = self.rig / 'result.json'
        self.result = {}

    def note(self, **facts):
        """The result so far goes to the disk at each step, so a run that dies still says how far it came."""
        self.result.update(facts)
        self.result_file.write_text(json.dumps(self.result, indent=1) + '\n')

    def read(self, name):
        return json.loads((self.private / name).read_text())

    def private_file(self, name, text):
        path = self.private / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(text)
        return path


# ---------------------------------------------------------------- processes: only ever the run's own


def environ(pid):
    try:
        return pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
    except OSError:
        return None


def mine(rig, pid):
    """Whether the process's own environment names this run's runtime folder: the only processes ever signalled."""
    found = environ(pid)
    return found is not None and f'XDG_RUNTIME_DIR={rig.runtime}'.encode() in found


def start_ticks(pid):
    try:
        data = pathlib.Path(f'/proc/{pid}/stat').read_bytes()
        return int(data[data.rindex(b')') + 2:].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def check_environment(rig, pid, gate):
    """Before anything else (brief, Acceptance): the game's JVM has the run's XDG_RUNTIME_DIR and no other, and the
    gate exactly when this run means it to."""
    found = environ(pid)
    if found is None:
        raise Unshown('the game\'s environment could not be read')
    runtime = [entry for entry in found if entry.startswith(b'XDG_RUNTIME_DIR=')]
    has_gate = b'ARESOS_DESKTOP_LIFECYCLE=1' in found
    facts = {'runtime_folder_is_the_runs_own': runtime == [f'XDG_RUNTIME_DIR={rig.runtime}'.encode()],
             'gate': has_gate, 'gate_expected': gate, 'checked': 'before the supervisor started and before any save'}
    rig.note(environment=facts)
    if not facts['runtime_folder_is_the_runs_own'] or has_gate != gate:
        raise Unshown('the game does not have the run\'s own XDG_RUNTIME_DIR and gate; nothing was asked of it')


def wait_for(condition, timeout, step=0.2):
    deadline = time.monotonic() + timeout
    while True:
        try:
            value = condition()
            if value:
                return value
        except (OSError, ValueError):
            pass
        if time.monotonic() >= deadline:
            return None
        time.sleep(step)


# ---------------------------------------------------------------- the game: its log, its chat, its window


def log_size(rig):
    try:
        return rig.game_log.stat().st_size
    except OSError:
        return 0


def log_since(rig, offset):
    try:
        with open(rig.game_log, 'rb') as source:
            source.seek(offset)
            return source.read().decode('utf-8', 'replace')
    except OSError:
        return ''


def vin(rig, command):
    with Writer(rig.rig) as writer:
        writer.send(command)


def chat(rig, text, expect, timeout=8.0, tries=3):
    """Type one command into the game's chat (letters, digits and spaces: / opens it with the slash typed) and wait
    for its answer in the game's log. The match, or None."""
    for _ in range(tries):
        offset = log_size(rig)
        vin(rig, 'key slash')
        time.sleep(0.6)
        vin(rig, 'type ' + text)
        time.sleep(0.4)
        vin(rig, 'key enter')
        found = wait_for(lambda: re.search(expect, log_since(rig, offset)), timeout)
        if found:
            return found
    return None


def spot(number):
    """Where probe block `number` is (probe/data/pkg25/function/act.mcfunction): in the home pad's chunk, in the air."""
    return 1 + (number - 1) % 14, 90, 2 + (number - 1) // 14


def absent(rig, number):
    """The game's own word that probe block `number` is not there yet (asked before anything is set)."""
    before = chat(rig, f'trigger pkg25 set {100 + number}', rf'pkg25 probe {number} (present|absent)')
    if not before or before.group(1) != 'absent':
        raise Unshown(f'block {number} is there already, or the game did not say; take another PROBE')


def put(rig, number):
    """A glass block set by the rig's data pack on the host's /trigger. The moment the game answered that it is
    there.

    The game writes a changed chunk to its region file within a tick by itself, but the same chunk at most once in
    ten seconds (seen in the first runs: a lone block was on the disk before anything was asked). So every check
    sets a first block (the chunk goes to the disk and its ten seconds begin) and then, at once, the block it is
    about: that one reaches the disk only if a save writes it."""
    if not chat(rig, f'trigger pkg25 set {number}', rf'pkg25 probe {number} placed'):
        raise Unshown(f'the rig could not set its block {number} (no answer in the game\'s log)')
    return time.monotonic_ns()


def rewritten(rig, since):
    """Which of the save's own files were written after `since` (wall clock): the level, and the player's data."""
    def after(paths):
        return any(path.is_file() and path.stat().st_mtime > since - 0.01 for path in paths)
    try:
        return {'level.dat': after([rig.world / 'level.dat']),
                'player data': after([*rig.world.glob('players/**/*.dat'), *rig.world.glob('playerdata/*.dat')])}
    except OSError:
        return None


def on_disk(rig, number):
    """Whether the disk holds probe block `number`: True, False, or a word for why it could not be read."""
    try:
        found = region.block(rig.world, *spot(number))
    except Exception as error:  # a region file read while the game writes it can be torn
        return f'unreadable ({type(error).__name__})'
    return found == PROBE_BLOCK


def look(rig, numbers):
    """Ask the reopened game itself whether the blocks of the launch before are in the world it loaded."""
    seen = []
    for number in numbers:
        found = chat(rig, f'trigger pkg25 set {100 + number}', rf'pkg25 probe {number} (present|absent)')
        if not found:
            raise Unshown(f'the reopened game did not say whether block {number} is there')
        seen.append({'block': number, 'in_the_reopened_game': found.group(1) == 'present',
                     'on_the_disk': on_disk(rig, number)})
        rig.note(reopened=seen)
    return seen


def stop_lines(rig, offset):
    lines = [PATHS.sub('<path>', line)[:240] for line in log_since(rig, offset).splitlines() if STOP_LINES.search(line)]
    return lines[:40]


def end_health(pid):
    """The rig's health watcher takes the compositor's end for a failure: stop it before an end that is meant."""
    try:
        if b'health.py' in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes():
            os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError):
        pass


def wait_exit(rig, descriptor, timeout):
    """Java's real exit, by its pidfd: (monotonic ns of the exit as seen here, the wrapper's exit note) or None."""
    if not select.select([descriptor], [], [], timeout)[0]:
        return None
    seen = time.monotonic_ns()
    note = wait_for(lambda: rig.read('exit.json'), 15)
    return seen, note


def close_window(rig, game):
    """Close the game's window as he would: the game saves and quits. For `create` and `verify`."""
    descriptor = os.pidfd_open(game['pid'])
    subprocess.run([sys.executable, '-I', str(WINDOW_TOOL), str(rig.rig), 'close', 'aresos-desktop'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=False)
    ended = wait_exit(rig, descriptor, 120)
    os.close(descriptor)
    if ended is None or ended[1] is None or ended[1].get('status') != 0:
        raise Unshown('the game did not quit cleanly when its window was closed')


# ---------------------------------------------------------------- the modes


def create(rig, game, health):
    if not wait_for(lambda: 'The town is built' in log_since(rig, 0), 600, 1):
        raise Unshown('the game did not finish the first home')
    time.sleep(20)
    end_health(health)
    close_window(rig, game)
    target = rig.world / 'datapacks' / PACK
    shutil.copytree(HERE / 'probe', target)
    desktop = load('aresos_desktop', SUPERVISOR)
    paths = desktop.Paths(str(rig.home), str(rig.runtime), str(rig.rig / 'share'))
    state, _ = desktop.check_world(paths, json.loads(PINS.read_text()))
    # The rig's reader, tried on the real save: the block he stands on at home, and the air where the probes go.
    pad, air = region.block(rig.world, *HOME_BLOCK), region.block(rig.world, *spot(1))
    rig.note(home={'made_by': 'the real game with the real mod (the first start of a session with no AresHub)',
                   'supervisor_home_check': state, 'reader_finds_at_the_pad': pad, 'reader_finds_at_block_1': air})
    if state != 'ok' or pad in (None, 'minecraft:air') or air != 'minecraft:air':
        raise Unshown('the home the game made does not pass the supervisor\'s checks, or the rig cannot read it')


def close_alone(rig, game, number, health):
    """The close alone: no save is asked by anyone. A first block, then block number + 1 within the chunk's ten
    seconds, SIGTERM to the rig's own game at once, Java's exit, and what the disk holds then."""
    descriptor = os.pidfd_open(game['pid'])
    absent(rig, number)
    absent(rig, number + 1)
    put(rig, number)
    placed = put(rig, number + 1)
    before = on_disk(rig, number + 1)
    offset = log_size(rig)
    if start_ticks(game['pid']) != game['ticks'] or not mine(rig, game['pid']):
        raise Unshown('the game is no longer the process this run started')
    end_health(health)
    wall, sent = time.time(), time.monotonic_ns()
    signal.pidfd_send_signal(descriptor, signal.SIGTERM)
    rig.note(close={'signal': 'SIGTERM through a pidfd, by the rig, to its own game', 'save_asked_before': False,
                    'first_block': number, 'block': number + 1,
                    'ms_from_the_blocks_answer_to_sigterm': round((sent - placed) / 1e6),
                    'block_on_disk_before_sigterm': before})
    ended = wait_exit(rig, descriptor, 90)
    os.close(descriptor)
    close = rig.result['close']
    if ended is None:
        close['exited'] = False
        rig.note(close=close)
        return
    seen, exit_note = ended
    close.update(exited=True, seconds_to_exit=round((seen - sent) / 1e9, 2),
                 exit_status=exit_note.get('status') if exit_note else None,
                 block_on_disk_after_exit=on_disk(rig, number + 1), first_block_on_disk_after_exit=on_disk(rig, number),
                 written_after_sigterm=rewritten(rig, wall), server_stop_lines=stop_lines(rig, offset))
    rig.note(close=close)


def stand_ins(rig):
    """The supervisor's stand-ins, as the loop test has them: none opens a window, talks to logind or starts a game."""
    rig.bin.mkdir(exist_ok=True)
    control = rig.control
    scripts = {
        # Reports the home ready once the rig has seen the game join it, as the real helper does on the mod's word.
        'helper': f'''#!/usr/bin/python3
import json, os, signal, sys, time
signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
fd = int(os.environ['ARESOS_SHELL_STATUS_FD'])
while True:
    if os.path.exists({str(control / 'joined')!r}):
        os.write(fd, (json.dumps({{'event': 'world_ready', 'world': {WORLD!r}}}) + '\\n').encode())
    time.sleep(0.5)
''',
        'view': "#!/bin/sh\ntrap 'exit 0' TERM\nwhile :; do sleep 0.1; done\n",
        'cover': "#!/bin/sh\ntrap 'exit 0' TERM\nwhile :; do sleep 0.1; done\n",
        'inhibit': "#!/bin/sh\ntrap 'exit 0' TERM\nwhile :; do sleep 0.1; done\n",
        'prism': f"#!/bin/sh\necho started >> '{control / 'prism.calls'}'\nexit 1\n",
        'labwc': '#!/bin/sh\nread line\n',
    }
    for name, text in scripts.items():
        (rig.bin / name).write_text(text)
        (rig.bin / name).chmod(0o755)
    share = rig.rig / 'share'
    share.mkdir(exist_ok=True)
    shutil.copy(PINS, share / 'desktop.lock.json')
    config = {'desktop': str(SUPERVISOR), 'share': str(share),
              **{name: str(rig.bin / name) for name in ('helper', 'cover', 'view', 'inhibit', 'prism')}}
    rig.private_file('supervisor.json', json.dumps(config))
    return share


def command(rig, *words):
    """The real `aresos-desktop` command, under `env -i` with the run's folders only."""
    started = time.monotonic()
    done = subprocess.run(['/usr/bin/env', '-i', *rig.environment, sys.executable, '-B', str(SUPERVISOR), *words],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120, cwd=rig.rig)
    return {'exit': done.returncode, 'says': PATHS.sub('<path>', done.stdout.strip())[:400],
            'seconds': round(time.monotonic() - started, 2)}


def stop_path(rig, game, number, health):
    """The path: the real supervisor adopts the rig's game; the hello, `save`, `stop`."""
    share = stand_ins(rig)
    desktop = load('aresos_desktop', SUPERVISOR)
    paths = desktop.Paths(str(rig.home), str(rig.runtime), str(share))
    identity = rig.read('launch.json')
    # The adoption runtime file, as a supervisor leaves it for the one that replaces it (save_runtime).
    os.makedirs(paths.run_dir, mode=0o700, exist_ok=True)
    desktop.write_atomic(paths.runtime_file, json.dumps(dict(
        instance=identity['instance'], nonce=identity['nonce'], launch=identity['launch'], mode='hub', accepted=True,
        reported=True, failed=False, jvm_pid=game['pid'], jvm_ticks=game['ticks'])) + '\n', 0o600)
    (rig.control / 'joined').write_text('')
    labwc = subprocess.Popen([str(rig.bin / 'labwc')], stdin=subprocess.PIPE, cwd=rig.rig,
                             env={'XDG_RUNTIME_DIR': str(rig.runtime), 'PATH': '/usr/bin:/bin'})
    output = open(rig.rig / 'supervisor.txt', 'wb')
    supervisor = subprocess.Popen(
        ['/usr/bin/env', '-i', *rig.environment, f'LABWC_PID={labwc.pid}', sys.executable, '-B',
         str(HERE / 'supervisor.py'), str(rig.private / 'supervisor.json')],
        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, cwd=rig.rig)
    (rig.control / 'pids').write_text(f'{supervisor.pid}\n{labwc.pid}\n')
    try:
        def status():
            try:
                return desktop.request(paths, {'op': 'status'}, timeout=5)
            except (OSError, ValueError):
                return {}

        ready = wait_for(lambda: (lambda s: s if s.get('lifecycle') is True and s.get('state') == 'IN_WORLD'
                                  else None)(status()), 90, 0.5)
        said = (rig.rig / 'supervisor.txt').read_text(errors='replace')
        path = {'adopted': 'adopted the running game' in said, 'hello_accepted': bool(ready),
                'state': (ready or status()).get('state'), 'watches_its_stand_in_labwc': (ready or {}).get('labwc')}
        rig.note(path=path)
        if not ready or not path['adopted']:
            raise Unshown('the supervisor did not adopt the game with an accepted hello and the home ready')
        for block in (number, number + 1, number + 2):
            absent(rig, block)
        # A first block (the chunk goes to the disk by itself), then at once the block `save` is about: what the mod
        # calls saved is on the disk when it says so, and was not before.
        put(rig, number)
        put(rig, number + 1)
        path['blocks'] = {'first': number, 'before_save': number + 1, 'before_stop': number + 2}
        path['save_block_on_disk_before_save'] = on_disk(rig, number + 1)
        path['save'] = command(rig, 'save')
        path['save_block_on_disk_after_saved'] = on_disk(rig, number + 1)
        rig.note(path=path)
        # Another block after that save, then the stop: its own save, SIGTERM through the pidfd, Java's exit.
        placed = put(rig, number + 2)
        path['stop_block_on_disk_before_stop'] = on_disk(rig, number + 2)
        offset = log_size(rig)
        descriptor = os.pidfd_open(game['pid'])
        end_health(health)
        wall, asked = time.time(), time.monotonic_ns()
        path['stop'] = command(rig, 'stop')
        path['ms_from_the_stop_blocks_answer_to_stop'] = round((asked - placed) / 1e6)
        ended = wait_exit(rig, descriptor, 5)
        os.close(descriptor)
        record = status().get('stop') or {}
        path['stop_record'] = {key: record.get(key) for key in ('open', 'kind', 'phase', 'save', 'sigterm', 'close',
                                                                'status')}
        path['java_exited'] = ended is not None
        path['exit_status'] = ended[1].get('status') if ended and ended[1] else None
        path['blocks_on_disk_after_exit'] = [on_disk(rig, block) for block in (number, number + 1, number + 2)]
        path['written_after_stop_began'] = rewritten(rig, wall)
        path['server_stop_lines'] = stop_lines(rig, offset)
        said = (rig.rig / 'supervisor.txt').read_text(errors='replace')
        path['stop_phases'] = [PATHS.sub('<path>', line[line.index('stop ('):])[:240]
                               for line in said.splitlines() if 'stop (' in line and ' s: ' in line][:20]
        path['prism_started'] = (rig.control / 'prism.calls').exists()
        rig.note(path=path)
    finally:
        if supervisor.poll() is None and mine(rig, supervisor.pid):
            supervisor.terminate()  # the session's end for it: with no game left it exits at once
            try:
                supervisor.wait(20)
            except subprocess.TimeoutExpired:
                pass
        labwc.kill()
        labwc.wait()
        labwc.stdin.close()
        output.close()


def run(folder, mode, probe, verify, health):
    rig = Rig(folder)
    rig.note(mode=mode, shown=False)
    try:
        game = wait_for(lambda: rig.read('jvm.json'), 60)
        if not game or start_ticks(game['pid']) != game['ticks']:
            raise Unshown('the game\'s JVM was not found')
        check_environment(rig, game['pid'], gate=mode in ('close', 'stop'))
        started = rig.rig / 'settings.txt'
        if not wait_for(lambda: rig.game_log.stat().st_mtime > started.stat().st_mtime
                        and 'joined the game' in log_since(rig, 0), 900, 0.5):
            raise Unshown('the game did not open the world')
        if mode == 'create':
            create(rig, game, health)
        else:
            time.sleep(15)
            look(rig, verify)
            if mode == 'close':
                close_alone(rig, game, probe, health)
            elif mode == 'stop':
                stop_path(rig, game, probe, health)
            else:
                end_health(health)
                close_window(rig, game)
        rig.note(shown=True)
        return 0
    except Unshown as error:
        rig.note(shown=False, why=str(error))
        print(f'check.py: {error}', file=sys.stderr)
        return 1


# ---------------------------------------------------------------- before and after


def prepare(folder, mode, unit, memory_high, java):
    rig = Rig(folder)
    for path in (rig.private, rig.runtime):
        path.mkdir(mode=0o700, exist_ok=True)
    rig.control.mkdir(exist_ok=True)
    if len(str(rig.runtime / 'aresos/desktop.sock')) > 100:
        sys.exit('the checkout\'s path is too long for the test supervisor\'s socket')
    identity = {'instance': 'aresdesktop-rig-' + secrets.token_hex(6), 'nonce': secrets.token_urlsafe(24),
                'launch': secrets.token_hex(6)}
    rig.private_file('launch.json', json.dumps(identity))
    rig.private_file('identity', f'ARESOS_DESKTOP_INSTANCE={identity["instance"]}\n'
                                 f'ARESOS_LAUNCH_NONCE={identity["nonce"]}\n')
    rig.private_file('wrapper.json', json.dumps({
        'java': java, 'unit': unit, 'memory_high': memory_high, 'runtime': str(rig.runtime),
        'gate': mode in ('close', 'stop'), 'launch': identity['launch'], 'instance': identity['instance'],
        'record': str(rig.state / 'desktop-exit.json'), 'wrapper': str(WRAPPER)}))
    return 0


def evidence(folder, out):
    """What goes into the public repo: the result's own fields (made here, never an environment, a runtime file, a
    nonce or a path) and how Gradle saw the game end."""
    rig = Rig(folder)
    result = json.loads(rig.result_file.read_text()) if rig.result_file.exists() else {'shown': False}
    settings = dict(line.split('=', 1) for line in (rig.rig / 'settings.txt').read_text().splitlines() if '=' in line)
    gradle = (rig.rig / 'gradle.txt').read_text(errors='replace') if (rig.rig / 'gradle.txt').exists() else ''
    value = re.search(r'finished with non-zero exit value (\d+)', gradle)
    public = {'run': settings.get('name'), 'source_revision': settings.get('source_revision'),
              'started': settings.get('started'), 'game': 'Minecraft 26.2 development client (Loom runClient) with '
              'the worktree\'s AresOS mod, headless in the rig\'s own labwc',
              **result, 'gradle_saw_exit_value': int(value.group(1)) if value else 0 if 'BUILD SUCCESSFUL' in gradle
              else None}
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out).write_text(json.dumps(public, indent=1) + '\n')
    return 0


def sweep(folder):
    """End what the run's supervisor left: only processes whose own environment names the run's runtime folder."""
    rig = Rig(folder)
    left = 0
    for entry in os.listdir('/proc'):
        if entry.isdigit() and int(entry) != os.getpid() and mine(rig, int(entry)):
            try:
                os.kill(int(entry), signal.SIGKILL)
                left += 1
            except OSError:
                pass
    if left:
        print(f'check.py: ended {left} process(es) of this run that were still there', file=sys.stderr)
    return 0


if __name__ == '__main__':
    action, arguments = sys.argv[1], sys.argv[2:]
    if action == 'prepare':
        sys.exit(prepare(*arguments))
    if action == 'run':
        folder, mode, probe, verify, health = arguments
        sys.exit(run(folder, mode, int(probe), [int(n) for n in verify.split(',') if n], int(health)))
    if action == 'evidence':
        sys.exit(evidence(*arguments))
    if action == 'sweep':
        sys.exit(sweep(arguments[0]))
    sys.exit(f'unknown action {action}')
