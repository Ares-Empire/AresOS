"""Read-only laptop gates and ownership of one capped process tree."""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
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


class Busy(Exception):
    """A safety gate refused work for now."""


class Cancelled(Exception):
    """A signal interrupted the bench."""


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
        data = self.meminfo.read_text()
        match = re.search(r'^MemAvailable:[ \t]+([0-9]+)[ \t]+kB$', data, re.MULTILINE)
        if not match:
            raise ValueError('MemAvailable unavailable')
        return int(match[1])

    def lunar_running(self):
        homes = {self.home, self.home.resolve()}
        for entry in self.proc.iterdir():
            if not entry.name.isdecimal():
                continue
            try:
                executable = (entry / 'exe').readlink()
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
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
            scope = supply / 'scope'
            if scope.exists() and scope.read_text().strip() == 'Device':
                continue
            if (supply / 'type').read_text().strip() == 'Battery':
                internal.append(supply)
            else:
                try:
                    online |= (supply / 'online').read_text().strip() == '1'
                except FileNotFoundError:
                    pass
        if not internal:
            return False
        states = [(supply / 'status').read_text().strip() for supply in internal]
        if any(state == 'Discharging' for state in states):
            return True
        if online or any(state == 'Charging' for state in states):
            return False
        # A full battery is not itself proof of external power.
        return True

    def home_game(self):
        def unreadable(error):
            raise error

        try:
            for parent, dirs, _ in os.walk(self.cgroups, onerror=unreadable):
                for name in dirs:
                    if re.fullmatch(r'aresos-game-.+\.scope', name):
                        try:
                            events = (Path(parent) / name / 'cgroup.events').read_text()
                        except FileNotFoundError:
                            continue
                        if 'populated 1' in events.splitlines():
                            return 'running'
        except OSError:
            return 'unknown'
        return 'idle'

    def pressure_avg10(self):
        data = self.pressure.read_text()
        match = re.search(r'^some avg10=([0-9]+(?:\.[0-9]+)?)[ \t]', data, re.MULTILINE)
        if not match or not 0 <= float(match[1]) <= 100:
            raise ValueError('memory pressure unavailable')
        return float(match[1])

    def gates(self, mode):
        checks = (
            ('memory', lambda: self.available() >= FLOORS[mode],
             f'needs {FLOORS[mode] // GIB_KIB} GiB available'),
            ('Lunar Client', lambda: not self.lunar_running(), 'Lunar Client Java is running'),
            ('power', lambda: not self.on_battery(), 'laptop is on battery or external power is unconfirmed'),
        )
        result = {}
        for name, check, reason in checks:
            try:
                result[name] = None if check() else reason
            except (OSError, ValueError):
                result[name] = f'{name} reading unavailable'
        if mode == 'vm':
            result['KVM'] = None if os.access(self.kvm, os.R_OK | os.W_OK) else 'KVM unavailable'
        try:
            self.pressure_avg10()
            result['pressure'] = None
        except (OSError, ValueError):
            result['pressure'] = 'memory pressure reading unavailable'
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
                not 0 < self.interval <= 2 or not math.isfinite(self.grace) or self.grace <= 0):
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


def scope_command(mode, unit, command):
    return [
        '/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--collect',
        '--expand-environment=no', f'--unit={unit}', '--slice=aresos-bench.slice',
        f'--property=MemoryMax={MEMORY_MAX[mode]}', '--property=CPUWeight=10',
        '--property=KillMode=control-group', '--property=KillSignal=SIGKILL',
        '--property=TimeoutStopSec=2s', '--nice=10',
        '--', '/usr/bin/choom', '-n', '1000', '--', *command,
    ]


class UserScopes:
    def __init__(self, cgroups):
        uid = os.getuid()
        self.env = {'PATH': os.defpath, 'LC_ALL': 'C', 'XDG_RUNTIME_DIR': f'/run/user/{uid}'}
        self.slice = cgroups / f'user.slice/user-{uid}.slice/user@{uid}.service/aresos.slice/aresos-bench.slice'

    def start(self, mode, unit, command, env):
        return subprocess.Popen(scope_command(mode, unit, command),
                                env={**env, **self.env}, stdin=subprocess.DEVNULL)

    def stop(self, unit):
        ctl = ['/usr/bin/systemctl', '--user']
        events = self.slice / unit / 'cgroup.events'
        reported = False
        while True:
            try:
                subprocess.run([*ctl, 'stop', unit], env=self.env, timeout=5, capture_output=True)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                if 'populated 0' in events.read_text().splitlines():
                    return
            except FileNotFoundError:
                # A quick command may have finished and been collected before stop.
                return
            except OSError:
                pass
            if not reported:
                print('bench: waiting for the owned scope to empty before releasing the lock',
                      file=sys.stderr, flush=True)
                reported = True
            sleep(1)


def guard(inputs, mode, unit, command, env, scopes, owner, request, grace):
    """Keep the lock until the owned launcher and scope are both gone."""
    if select.select([owner, request], [], [], 0)[0]:
        return 1
    inputs.require(mode)
    child = scopes.start(mode, unit, command, env)
    try:
        with_fd = os.pidfd_open(child.pid)
        try:
            ready = select.select([owner, request, with_fd], [], [])[0]
            if owner not in ready and request in ready and os.read(request, 1) == b'G':
                select.select([owner, with_fd], [], [], grace)
                return 1
            if with_fd in ready:
                return 0 if child.wait() == 0 else 1
            return 1
        finally:
            os.close(with_fd)
    finally:
        # Cancel the launcher first so it cannot enter the scope after the stop.
        if child.poll() is None:
            child.kill()
            child.wait()
        scopes.stop(unit)


def watch_tree(inputs, mode, command, *, policy, scopes, graceful, env):
    """Run in the locked bench caller, with a separate guardian for watcher loss."""
    unit = f'aresos-bench-{uuid4().hex}.scope'
    owner = os.pidfd_open(os.getpid())
    request, notify = os.pipe()
    guardian = None
    try:
        guardian = os.fork()
        if guardian == 0:
            result = 1
            try:
                os.close(notify)
                os.setsid()
                for sig in SIGNALS:
                    signal.signal(sig, signal.SIG_IGN)
                result = guard(inputs, mode, unit, command, env, scopes, owner, request, policy.grace)
            except Busy as error:
                print(f'bench: {error}', file=sys.stderr, flush=True)
                result = 75
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                print(f'bench: {error}', file=sys.stderr, flush=True)
            finally:
                os._exit(result)
        guardian_fd = os.pidfd_open(guardian)
        try:
            deadline = monotonic() + policy.interval
            while not select.select([guardian_fd], [], [], max(0, deadline - monotonic()))[0]:
                reason = policy.reason(inputs)
                if reason:
                    try:
                        os.write(notify, b'G')
                    except BrokenPipeError:
                        pass  # The guardian was already stopping the scope.
                    graceful(reason)
                    break
                deadline = monotonic() + policy.interval
        finally:
            os.close(guardian_fd)
    finally:
        os.close(notify)
        os.close(request)
        os.close(owner)
        if guardian:
            _, status = os.waitpid(guardian, 0)
    return os.waitstatus_to_exitcode(status)
