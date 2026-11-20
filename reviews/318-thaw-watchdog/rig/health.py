"""Watch owned children with pidfds, including during long sleeps, and abort through EXIT cleanup."""
import json
import os
from pathlib import Path
import select
import signal
import sys
import time


def watch(rig, parent, starter):
    rig = Path(rig)
    parent_fd = os.pidfd_open(parent)
    peers = {os.pidfd_open(starter): 'rig launcher'}
    deadline = time.monotonic() + 120
    registered = False
    while True:
        if not registered:
            env = dict(line.split('=', 1) for line in (rig/'env').read_text().splitlines() if '=' in line) if (rig/'env').exists() else {}
            if 'VINPUT_PID' in env:
                for key in ('LABWC_PID', 'VINPUT_PID'):
                    try:
                        peers[os.pidfd_open(int(env[key]))] = key
                    except ProcessLookupError:
                        fail(rig, parent_fd, key + ' already exited', parent)
                registered = True
            elif time.monotonic() >= deadline:
                fail(rig, parent_fd, 'no compositor/input readiness within 120 seconds', parent)
        ready = select.select([parent_fd, *peers], [], [], .1)[0]
        if parent_fd in ready:
            return
        for fd in ready:
            fail(rig, parent_fd, peers[fd] + ' exited', parent)


def fail(rig, parent_fd, reason, parent):
    (rig/'health-failure.json').write_text(json.dumps({'monotonic_ns':time.monotonic_ns(), 'reason':reason})+'\n')
    print(reason, file=sys.stderr, flush=True)
    # Bash also defers traps during a foreground Python/jcmd/UI command. Retain pidfds for
    # only its direct children in the controller's own cgroup, then interrupt them too.
    # The compositor/game live in separate scopes and are stopped by normal EXIT cleanup.
    children = []
    try:
        base = Path('/proc')/str(parent)
        group = (base/'cgroup').read_text()
        for pid in (base/'task'/str(parent)/'children').read_text().split():
            if int(pid) == os.getpid(): continue
            fd = None
            try:
                fd = os.pidfd_open(int(pid))
                proc = Path('/proc')/pid
                ppid = next(line.split()[1] for line in (proc/'status').read_text().splitlines() if line.startswith('PPid:'))
                if int(ppid) == parent and (proc/'cgroup').read_text() == group:
                    children.append(fd)
                    fd = None
            except (OSError, StopIteration): pass
            finally:
                if fd is not None: os.close(fd)
    except OSError: pass
    try:
        signal.pidfd_send_signal(parent_fd, signal.SIGUSR1)
    except ProcessLookupError:
        pass
    for fd in children:
        try: signal.pidfd_send_signal(fd, signal.SIGTERM)
        except ProcessLookupError: pass
        finally: os.close(fd)
    raise SystemExit(1)


if __name__ == '__main__':
    watch(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
