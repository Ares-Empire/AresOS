#!/usr/bin/env python3
"""Run invocation lifecycle checks with real user scopes, fake CUDA, and no game.

Requires a working systemd user manager, cc, and the holder's pre-existing UVM
prerequisites. All artifacts live in this worktree's .work/47-review-fix-tests/.
The fake driver is selected through LD_LIBRARY_PATH; it never calls NVIDIA.
"""
import fcntl
import os
from pathlib import Path
import select
import shlex
import signal
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / '.work/47-review-fix-tests'
ROOT.mkdir(parents=True, exist_ok=True)
SOURCE = r'''
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
static void record(const char *event) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    FILE *out = fopen(getenv("TRIAL_EVENTS"), "a");
    if (!out) abort();
    fprintf(out, "%s %.6f %d\n", event, now.tv_sec + now.tv_nsec / 1e9, getpid());
    fclose(out);
}
static void hang(const char *variable) {
    if (getenv(variable)) for (;;) pause();
}
int cuInit(unsigned int flags) {
    record("init"); hang("TRIAL_INIT_HANG");
    return getenv("TRIAL_FAIL") ? 999 : 0;
}
int cuDeviceGetByPCIBusId(int *device, const char *pci) { *device = 0; return 0; }
int cuDevicePrimaryCtxRetain(void **context, int device) {
    record("retain"); hang("TRIAL_RETAIN_HANG"); *context = (void *)1; return 0;
}
int cuDevicePrimaryCtxRelease_v2(int device) {
    record("release"); hang("TRIAL_RELEASE_HANG"); return 0;
}
'''
(ROOT / 'fake-cuda.c').write_text(SOURCE)
subprocess.run(['cc', '-shared', '-fPIC', str(ROOT / 'fake-cuda.c'),
                '-o', str(ROOT / 'libcuda.so.1')], check=True)
CLIENT = r'''
import os, signal, subprocess, sys, time
from pathlib import Path
root = Path(sys.argv[1])
# A descendant tests that cleanup reaches the complete scope, not only its launcher.
child = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(300)"])
if sys.argv[2] == "stubborn":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
(root / "client.pids").write_text(f"{os.getpid()} {child.pid}")
with (root / "events").open("a") as out:
    out.write(f"client-start {time.monotonic():.6f} {os.getpid()}\n")
while True:
    time.sleep(1)
'''
(ROOT / 'client.py').write_text(CLIENT)
TRIAL = f'''#!/usr/bin/bash
set -euo pipefail
source {shlex.quote(str(REPO / 'mod/dev/env.sh'))}
ARESOS_DEV_CACHE=$1
exec {{TRIAL_STDERR}}>&2
mkdir -p "$ARESOS_DEV_CACHE"
aresos_lock "$ARESOS_DEV_CACHE/trial.lock" "another stand-in trial"
aresos_supervise
printf '%s\\n' "$ARESOS_GUARD_JOB" >"$ARESOS_DEV_CACHE/guard.pid"
if ! aresos_hold_nvidia 0000:01:00.0; then exit 7; fi
printf '%s\\n' "$ARESOS_GPU_HOLDER_UNIT" >"$ARESOS_DEV_CACHE/holder.unit"
if [[ $2 == normal || $2 == release-hang ]]; then exit 0; fi
# Exercise stdout, compositor stderr, fd 3, exported variables, and exit-code forwarding too.
if [[ $2 == descriptors ]]; then
    export TRIAL_EXPORTED=preserved
    aresos_scoped trial-descriptors -- /usr/bin/bash -c '
        [[ $TRIAL_EXPORTED == preserved ]]
        echo STDOUT
        echo COMPOSITOR >&2
        exec 2>&"$ARESOS_SCOPED_STDERR_FD"
        echo GAME >&2
        exit 23
    ' 3>&2 2>"$ARESOS_DEV_CACHE/compositor.log"
else
    aresos_scoped trial-client -- /usr/bin/python3 -I {shlex.quote(str(ROOT / 'client.py'))} "$1" "$3"
fi
'''
(ROOT / 'trial.sh').write_text(TRIAL)


def until(predicate, seconds=12):
    deadline = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < deadline, 'deadline expired'
        time.sleep(.025)


def inactive(unit):
    result = subprocess.run(['systemctl', '--user', 'show', '--property=ActiveState',
                             '--value', '--', unit], capture_output=True, text=True, timeout=2)
    return result.stdout.strip() in ('', 'inactive', 'failed')


def run(name, variables=(), trigger=None, expected=0, stubborn=False):
    cache = ROOT / name
    cache.mkdir(exist_ok=True)
    for file in cache.iterdir():
        if file.is_file():
            file.unlink()
    events = cache / 'events'
    # Stale READY must not make a failed/hanging initialization look successful.
    (cache / 'client-test-gpu-holder.log').write_text('READY\n')
    environment = dict(os.environ, LD_LIBRARY_PATH=str(ROOT), TRIAL_EVENTS=str(events))
    environment.update(dict.fromkeys(variables, '1'))
    start = time.monotonic()
    with (cache / 'output.log').open('w') as output:
        process = subprocess.Popen(['bash', str(ROOT / 'trial.sh'), str(cache), name,
                                    'stubborn' if stubborn else 'normal'], env=environment,
                                   stdout=output, stderr=subprocess.STDOUT)
        script_fd = os.pidfd_open(process.pid)
        guard_fd = None
        client_fds = []
        try:
            until(lambda: (cache / 'guard.pid').exists())
            guard_fd = os.pidfd_open(int((cache / 'guard.pid').read_text()))
            if trigger in ('init', 'retain'):
                until(lambda: events.exists() and trigger in events.read_text())
                process.kill()
            elif trigger is not None:
                until(lambda: (cache / 'client.pids').exists())
                client_fds = [os.pidfd_open(int(p)) for p in (cache / 'client.pids').read_text().split()]
                if trigger in ('holder', 'terminal-holder'):
                    until(lambda: (cache / 'holder.unit').exists())
                    holder_pid = int(next(line.split()[2] for line in events.read_text().splitlines()
                                          if line.startswith('retain ')))
                    holder_fd = os.pidfd_open(holder_pid)
                    signal.pidfd_send_signal(holder_fd, signal.SIGKILL if trigger == 'holder' else signal.SIGINT)
                    os.close(holder_fd)
                    if trigger == 'terminal-holder':
                        time.sleep(.2)
                        assert 'release ' not in events.read_text(), 'terminal INT released the holder early'
                        signal.pidfd_send_signal(script_fd, signal.SIGHUP)
                else:
                    signal.pidfd_send_signal(script_fd, trigger)
            result = process.wait(timeout=42)
            assert result == expected, (name, result, expected, (cache / 'output.log').read_text())
            until(lambda: bool(select.select([guard_fd], [], [], 0)[0]), 35)
            for fd in client_fds:
                assert select.select([fd], [], [], 0)[0], (name, 'client survived')
            # Real lock reacquisition, no wait: cleanup must release every inherited copy.
            with (cache / 'trial.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            units = subprocess.run(['systemctl', '--user', 'list-units', '--all', '--no-legend',
                                    '--plain', f'aresos-dev-*-{process.pid}-*.scope'],
                                   capture_output=True, text=True, check=True).stdout
            assert not units.strip(), (name, 'owned scope remains', units)
            if (cache / 'holder.unit').exists():
                assert inactive((cache / 'holder.unit').read_text().strip()), name
            lines = events.read_text().splitlines()
            if name == 'descriptors':
                text = (cache / 'output.log').read_text()
                assert 'STDOUT' in text and 'GAME' in text, text
                assert (cache / 'compositor.log').read_text() == 'COMPOSITOR\n'
            if trigger == 'holder':
                assert 'NVIDIA power holder exited unexpectedly; aborting client tests.' in (cache / 'output.log').read_text()
            if name not in ('init-parent-kill', 'retain-parent-kill', 'init-timeout', 'init-fail', 'holder-kill-client'):
                assert any(line.startswith('release ') for line in lines), (name, lines)
            if name == 'parent-kill-client':
                release_at = float(next(line.split()[1] for line in lines if line.startswith('release ')))
                assert release_at - start >= 19, 'holder released before stubborn client was stopped'
            elapsed = time.monotonic() - start
            assert elapsed < (38 if name == 'init-timeout' else 32), (name, elapsed)
            print(f'{name}: PASS exit {result}, scopes gone, lock free ({elapsed:.2f}s)', flush=True)
        finally:
            if process.poll() is None:
                signal.pidfd_send_signal(script_fd, signal.SIGTERM)
                process.wait(timeout=42)
            for fd in [script_fd, guard_fd, *client_fds]:
                if fd is not None:
                    os.close(fd)


run('normal')
run('descriptors', expected=23)
run('init-fail', ('TRIAL_FAIL',), expected=7)
run('init-parent-kill', ('TRIAL_INIT_HANG',), trigger='init', expected=-9)
run('retain-parent-kill', ('TRIAL_RETAIN_HANG',), trigger='retain', expected=-9)
run('release-hang', ('TRIAL_RELEASE_HANG',))
run('parent-kill-client', trigger=signal.SIGKILL, expected=-9, stubborn=True)
run('parent-kill-release-hang', ('TRIAL_RELEASE_HANG',), trigger=signal.SIGKILL, expected=-9)
run('holder-kill-client', trigger='holder', expected=1)
run('terminal-holder', trigger='terminal-holder', expected=129)
run('int-client', trigger=signal.SIGINT, expected=130)
run('term-client', trigger=signal.SIGTERM, expected=143)
run('hup-client', trigger=signal.SIGHUP, expected=129)
run('init-timeout', ('TRIAL_INIT_HANG',), expected=7)
