"""Read-only laptop gates and ownership of one capped process tree."""
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
import fcntl
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

GIB_KIB = 1024 * 1024
FLOORS = {'vm': 7 * GIB_KIB, 'build': 6 * GIB_KIB}
MEMORY_MAX = {'vm': '5G', 'build': '5G'}
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
KVM_GET_API_VERSION = 0xAE00
EXTERNAL_POWER_TYPES = {
    'Mains', 'USB', 'USB_DCP', 'USB_CDP', 'USB_ACA', 'USB_C', 'USB_PD',
    'USB_PD_DRP', 'Apple_Brick_ID', 'USB_FLOAT',
}
POWER_TYPES = EXTERNAL_POWER_TYPES | {'Battery', 'UPS', 'Wireless'}


class Busy(Exception):
    """A safety gate refused work for now."""


class Cancelled(Exception):
    """A signal interrupted the bench."""


def log_error(message):
    try:
        print(f'bench: {message}', file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass


def populated(events):
    fields = {}
    for line in events.splitlines():
        match = re.fullmatch(r'([a-z_]+) ([0-9]+)', line)
        if not match or match[1] in fields:
            raise ValueError('malformed cgroup events')
        fields[match[1]] = match[2]
    if fields.get('populated') not in ('0', '1') or fields.get('frozen', '0') not in ('0', '1'):
        raise ValueError('malformed cgroup events')
    return fields['populated'] == '1'


@dataclass(frozen=True)
class Inputs:
    home: Path
    proc: Path = Path('/proc')
    meminfo: Path = Path('/proc/meminfo')
    pressure: Path = Path('/proc/pressure/memory')
    power: Path = Path('/sys/class/power_supply')
    cgroups: Path = Path('/sys/fs/cgroup')
    kvm: Path = Path('/dev/kvm')

    def available(self):
        fields = {}
        for line in self.meminfo.read_text().splitlines():
            match = re.fullmatch(r'([A-Za-z0-9_()]+):[ \t]+([0-9]+)(?:[ \t]+(kB))?', line)
            if not match or match[1] in fields:
                raise ValueError('malformed meminfo')
            fields[match[1]] = (int(match[2]), match[3])
        available, available_unit = fields.get('MemAvailable', (0, None))
        free, free_unit = fields.get('MemFree', (0, None))
        total, total_unit = fields.get('MemTotal', (0, None))
        if (available_unit != 'kB' or free_unit != 'kB' or total_unit != 'kB' or
                total == 0 or not 0 <= available <= total or not 0 <= free <= total):
            raise ValueError('invalid MemAvailable, MemFree or MemTotal')
        return available

    def require_memory(self, mode):
        try:
            available = self.available()
        except (OSError, ValueError):
            raise Busy('memory reading unavailable') from None
        if available < FLOORS[mode]:
            raise Busy(f'needs {FLOORS[mode] // GIB_KIB} GiB available')

    def lunar_running(self):
        homes = {self.home, self.home.resolve()}
        for entry in self.proc.iterdir():
            if not re.fullmatch(r'[0-9]+', entry.name):
                continue
            try:
                folder = os.open(entry, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW)
            except (FileNotFoundError, ProcessLookupError):
                continue
            try:
                status = os.open('status', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=folder)
                with os.fdopen(status, encoding='utf-8', errors='surrogateescape') as stream:
                    fields = stream.read()
                # proc inode ownership can change when a process becomes non-dumpable.
                uids = re.findall(r'^Uid:[ \t]+([0-9]+)[ \t]+([0-9]+)[ \t]+([0-9]+)[ \t]+([0-9]+)$',
                                  fields, re.MULTILINE)
                if len(uids) != 1 or len(re.findall(r'^Uid\b', fields, re.MULTILINE)) != 1:
                    raise ValueError('process ownership unavailable')
                if str(os.getuid()) not in uids[0]:
                    continue
                states = re.findall(r'^State:[ \t]+([RSDZTtXxKWPI])(?:[ \t].*)?$', fields, re.MULTILINE)
                if len(states) != 1:
                    raise ValueError('owner process state unavailable')
                if states[0] in ('Z', 'X', 'x'):
                    continue
                try:
                    executable = os.readlink('exe', dir_fd=folder)
                except FileNotFoundError:
                    if not entry.exists():
                        continue
                    raise ValueError('owner process executable unavailable') from None
            except ProcessLookupError:
                continue
            except FileNotFoundError:
                if not entry.exists():
                    continue
                raise
            finally:
                os.close(folder)
            # proc appends this suffix when the executable was removed after launch.
            executable = Path(executable.removesuffix(' (deleted)'))
            if not executable.is_absolute():
                raise ValueError('owner process executable is invalid')
            if any(executable.is_relative_to(home / '.lunarclient') and
                   executable.parts[-2:] == ('bin', 'java') and
                   len(executable.relative_to(home / '.lunarclient').parts) > 2
                   for home in homes):
                return True
        return False

    def on_battery(self):
        internal = []
        online = False
        for supply in self.power.iterdir():
            kind = (supply / 'type').read_text().strip()
            if kind not in POWER_TYPES:
                raise ValueError('unknown power supply type')
            try:
                scope = (supply / 'scope').read_text().strip()
            except FileNotFoundError:
                scope = 'Unknown'
            if scope not in ('Unknown', 'System', 'Device'):
                raise ValueError('invalid power supply scope')
            if scope == 'Device':
                continue
            if kind == 'Battery':
                internal.append(supply)
            else:
                state = (supply / 'online').read_text().strip()
                if state not in ('0', '1'):
                    raise ValueError('invalid external power state')
                online |= kind in EXTERNAL_POWER_TYPES and state == '1'
        states = [(supply / 'status').read_text().strip() for supply in internal]
        if any(state not in ('Charging', 'Discharging', 'Not charging', 'Full') for state in states):
            raise ValueError('invalid battery state')
        return not online or 'Discharging' in states

    def home_game(self):
        def unreadable(error):
            raise error

        unknown = False
        try:
            for parent, dirs, _ in os.walk(self.cgroups, onerror=unreadable):
                for name in dirs:
                    if re.fullmatch(r'aresos-game-.+\.scope', name):
                        try:
                            if populated((Path(parent) / name / 'cgroup.events').read_text()):
                                return 'running'
                        except (OSError, ValueError):
                            unknown = True
        except OSError:
            unknown = True
        return 'unknown' if unknown else 'idle'

    def pressure_avg10(self):
        fields = {}
        number = r'([0-9]+(?:\.[0-9]+)?)'
        for line in self.pressure.read_text().splitlines():
            match = re.fullmatch(rf'(some|full) avg10={number} avg60={number} avg300={number} total=([0-9]+)', line)
            if not match or match[1] in fields:
                raise ValueError('malformed memory pressure')
            averages = tuple(float(value) for value in match.groups()[1:4])
            if any(value > 100 for value in averages):
                raise ValueError('invalid memory pressure average')
            fields[match[1]] = (*averages, int(match[5]))
        if fields.keys() != {'some', 'full'}:
            raise ValueError('missing memory pressure record')
        if any(full > some for full, some in zip(fields['full'], fields['some'])):
            raise ValueError('contradictory memory pressure records')
        return fields['some'][0]

    def kvm_ready(self):
        fd = os.open(self.kvm, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            return stat.S_ISCHR(os.fstat(fd).st_mode) and fcntl.ioctl(fd, KVM_GET_API_VERSION) == 12
        finally:
            os.close(fd)

    def session_gates(self):
        checks = (
            ('Lunar Client', lambda: not self.lunar_running(), 'Lunar Client Java is running'),
            ('power', lambda: not self.on_battery(), 'laptop is on battery or external power is unconfirmed'),
        )
        result = {}
        for name, check, reason in checks:
            try:
                result[name] = None if check() else reason
            except (OSError, ValueError):
                result[name] = f'{name} reading unavailable'
        return result

    def gates(self, mode):
        result = self.session_gates()
        if mode == 'vm':
            try:
                result['KVM'] = None if self.kvm_ready() else 'KVM unavailable'
            except OSError:
                result['KVM'] = 'KVM unavailable'
        try:
            self.pressure_avg10()
            result['pressure'] = None
        except (OSError, ValueError):
            result['pressure'] = 'memory pressure reading unavailable'
        try:
            self.require_memory(mode)
            result['memory'] = None
        except Busy as error:
            result['memory'] = str(error)
        return result

    def require(self, mode):
        for reason in self.gates(mode).values():
            if reason:
                raise Busy(reason)


@dataclass(frozen=True)
class Watch:
    floor_kib: int = 2 * GIB_KIB
    pressure_percent: float = 10.0
    interval: float = 1.0
    grace: float = 2.0

    def __post_init__(self):
        if (self.floor_kib <= 0 or not 0 <= self.pressure_percent <= 100 or
                not 1 <= self.interval <= 2 or not math.isfinite(self.grace) or self.grace <= 0):
            raise ValueError('invalid memory watcher settings')

    def reason(self, inputs):
        try:
            if inputs.available() < self.floor_kib:
                return 'available memory fell below the watcher floor'
            if inputs.pressure_avg10() > self.pressure_percent:
                return 'memory pressure exceeded the watcher threshold'
        except (OSError, ValueError):
            return 'memory watcher reading unavailable'
        return None


@contextmanager
def shared_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('client-test lock is not a regular file')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Busy('client-test lock is busy') from None
        yield
    finally:
        # The guardian retains this same open file description if the caller dies.
        os.close(fd)


@contextmanager
def catch_signals():
    def cancel(number, _frame):
        for sig in SIGNALS:
            signal.signal(sig, signal.SIG_IGN)
        raise Cancelled(f'interrupted by {signal.Signals(number).name}')

    previous = {sig: signal.signal(sig, cancel) for sig in SIGNALS}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@contextmanager
def defer_signals():
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
    try:
        yield previous
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def scope_command(mode, unit, command):
    return [
        '/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--collect',
        '--expand-environment=no', f'--unit={unit}', '--slice=aresos-bench.slice',
        f'--property=MemoryMax={MEMORY_MAX[mode]}', '--property=CPUWeight=10',
        '--property=KillMode=control-group', '--property=KillSignal=SIGKILL',
        '--property=TimeoutStopSec=2s', '--nice=10',
        '--', '/usr/bin/choom', '-n', '1000', '--', *command,
    ]


class OwnedScope:
    def __init__(self, invocation, cgroup, events, kill):
        self.invocation = invocation
        self.cgroup = cgroup
        self.events = events
        self.kill = kill

    def empty(self):
        # The kernel can remove this pinned cgroup only after its last live task leaves.
        try:
            if os.fstat(self.cgroup).st_nlink == 0:
                return True
            return not populated(os.pread(self.events, 4096, 0).decode())
        except (OSError, ValueError):
            return False

    def stop(self):
        failed = False
        warned = False
        while not self.empty():
            try:
                os.write(self.kill, b'1')
            except OSError:
                if self.empty():
                    break
                failed = True
            if not warned and not self.empty():
                log_error(f'waiting for scope {self.invocation} to empty')
                warned = True
            sleep(0.05 if not failed else 1)
        if failed:
            log_error('scope shutdown failed before the tree was confirmed empty')
        return not failed


def scope_payload(inputs, mode, command, env, files, file_limit):
    wrapper = str(Path(__file__).absolute())
    config = {key: str(value) for key, value in asdict(inputs).items()}
    data = json.dumps([config, mode, command, env, [str(file) for file in files], file_limit])
    return [sys.executable, '-B', '-E', '-s', wrapper, data]


class UserScopes:
    def __init__(self, inputs):
        self.inputs = inputs
        uid = os.getuid()
        self.env = {'PATH': os.defpath, 'LC_ALL': 'C', 'XDG_RUNTIME_DIR': f'/run/user/{uid}'}
        self.slice = Path(f'/user.slice/user-{uid}.slice/user@{uid}.service/aresos.slice/aresos-bench.slice')

    def start(self, mode, unit, payload):
        return subprocess.Popen(scope_command(mode, unit, payload), env=self.env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def properties(self, unit):
        query = subprocess.run(
            ['/usr/bin/systemctl', '--user', 'show', '--property=Id,InvocationID,ControlGroup,ActiveState',
             '--', unit], env=self.env, text=True, check=True, capture_output=True, timeout=5)
        return dict(line.split('=', 1) for line in query.stdout.splitlines())

    def pin(self, unit, pid, invocation, stack):
        expected = self.slice / unit
        properties = {'Id': unit, 'InvocationID': invocation, 'ControlGroup': str(expected), 'ActiveState': 'active'}
        if (not re.fullmatch(r'[0-9a-f]{32}', invocation) or int(invocation, 16) == 0 or
                self.properties(unit) != properties):
            raise ValueError('could not verify the bench scope invocation')
        proc_group = (self.inputs.proc / str(pid) / 'cgroup').read_text().splitlines()
        if proc_group != [f'0::{expected}']:
            raise ValueError('launcher is outside the bench cgroup')
        with ExitStack() as ancestors:
            folder = os.open(self.inputs.cgroups, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            ancestors.callback(os.close, folder)
            for part in expected.parts[1:-1]:
                folder = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=folder)
                ancestors.callback(os.close, folder)
            group = os.open(unit, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=folder)
        stack.callback(os.close, group)
        events = os.open('cgroup.events', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=group)
        stack.callback(os.close, events)
        kill = os.open('cgroup.kill', os.O_WRONLY | os.O_NOFOLLOW, dir_fd=group)
        stack.callback(os.close, kill)
        members = os.open('cgroup.procs', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=group)
        with os.fdopen(members) as stream:
            if stream.read().split() != [str(pid)] or self.properties(unit) != properties:
                raise ValueError('bench cgroup ownership changed during launch')
        scope = OwnedScope(invocation, group, events, kill)
        if not populated(os.pread(events, 4096, 0).decode()):
            raise ValueError('bench cgroup is empty before launch')
        return scope


def scoped_exec(data):
    from write_bounds import restrict_writes

    config, mode, command, env, files, file_limit = json.loads(data)
    inputs = Inputs(**{key: Path(value) for key, value in config.items()})
    try:
        with open(os.devnull, 'r+b', buffering=0) as null:
            restrict_writes(files, file_limit)
            invocation = os.environ.get('INVOCATION_ID', '')
            os.write(1, (invocation + '\n').encode('ascii'))
            if os.read(0, 1) != b'R':
                return 1
            os.dup2(null.fileno(), 0)
            os.dup2(null.fileno(), 1)
            for reason in inputs.session_gates().values():
                if reason:
                    raise Busy(reason)
            inputs.require_memory(mode)
            os.dup2(null.fileno(), 2)
            os.execvpe(command[0], command, env)
    except Busy as error:
        log_error(error)
        return 75
    except (OSError, ValueError) as error:
        log_error(error)
        return 1


def guard(scope, owner, request, launcher, grace):
    """The guardian inherits the lock and uses the pinned cgroup even after watcher loss."""
    try:
        ready = select.select([owner, request, launcher], [], [])[0]
        if owner not in ready and request in ready and os.read(request, 1) == b'G':
            select.select([owner, launcher], [], [], grace)
    finally:
        confirmed = scope.stop()
    return 0 if confirmed else 1


def supervise(child, scope, inputs, policy, graceful, disk_reason, launcher, before_release):
    with ExitStack() as stack:
        owner = os.pidfd_open(os.getpid())
        stack.callback(os.close, owner)
        request, notify = os.pipe()
        stack.callback(os.close, request)
        stack.callback(os.close, notify)
        guardian = None
        requested_stop = False
        try:
            with defer_signals() as mask:
                guardian = os.fork()
                if guardian == 0:
                    status = 1
                    try:
                        child.stdin.close()
                        os.close(notify)
                        os.setsid()
                        for sig in SIGNALS:
                            signal.signal(sig, signal.SIG_IGN)
                        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                        status = guard(scope, owner, request, launcher, policy.grace)
                    finally:
                        os._exit(status)
            guardian_fd = os.pidfd_open(guardian)
            stack.callback(os.close, guardian_fd)
            before_release()
            try:
                child.stdin.write(b'R')
                child.stdin.close()
            except BrokenPipeError:
                return 1
            deadline = monotonic() + policy.interval
            while not select.select([guardian_fd], [], [], max(0, deadline - monotonic()))[0]:
                disk = disk_reason()
                reason = disk or policy.reason(inputs)
                if reason:
                    requested_stop = True
                    try:
                        os.write(notify, b'K' if disk else b'G')
                    except BrokenPipeError:
                        pass
                    graceful(reason)
                    break
                deadline = monotonic() + policy.interval
        finally:
            with defer_signals():
                status = 1
                try:
                    try:
                        os.write(notify, b'K')
                    except BrokenPipeError:
                        pass
                    if guardian:
                        _, status = os.waitpid(guardian, 0)
                finally:
                    # The guardian may have died before sending the kill or confirming emptiness.
                    confirmed = scope.stop()
                    result = child.wait()
        if requested_stop or status or not confirmed:
            return 1
        return result if result in (0, 75) else 1


def watch_tree(inputs, mode, command, *, policy, scopes, graceful, env, files, file_limit, disk_reason,
               before_release):
    """Admit the scoped helper before either supervisor allows it to exec the workload."""
    inputs.require(mode)
    unit = f'aresos-bench-{uuid4().hex}.scope'
    payload = scope_payload(inputs, mode, command, env, files, file_limit)
    with ExitStack() as stack:
        with defer_signals():
            child = scopes.start(mode, unit, payload)
            stack.callback(child.stdout.close)
            stack.callback(child.stdin.close)
            stack.callback(reap_launcher, child)
        launcher = os.pidfd_open(child.pid)
        stack.callback(os.close, launcher)
        if not select.select([child.stdout, launcher], [], [], 15)[0]:
            raise RuntimeError('bench scope did not activate')
        reply = os.read(child.stdout.fileno(), 64)
        if not reply:
            return 75 if child.wait() == 75 else 1
        scope = scopes.pin(unit, child.pid, reply.decode('ascii').strip(), stack)
        return supervise(child, scope, inputs, policy, graceful, disk_reason, launcher, before_release)


def reap_launcher(child):
    # Before admission, the launcher's owned PID is the only process we may stop.
    if child.poll() is None:
        child.kill()
        child.wait()


if __name__ == '__main__':
    sys.exit(scoped_exec(sys.argv[1]))
