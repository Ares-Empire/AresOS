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
                        fail(rig, parent_fd, key + ' already exited')
                registered = True
            elif time.monotonic() >= deadline:
                fail(rig, parent_fd, 'no compositor/input readiness within 120 seconds')
        ready = select.select([parent_fd, *peers], [], [], .1)[0]
        if parent_fd in ready:
            return
        for fd in ready:
            fail(rig, parent_fd, peers[fd] + ' exited')


def fail(rig, parent_fd, reason):
    (rig/'health-failure.json').write_text(json.dumps({'monotonic_ns':time.monotonic_ns(), 'reason':reason})+'\n')
    print(reason, file=sys.stderr, flush=True)
    try:
        signal.pidfd_send_signal(parent_fd, signal.SIGUSR1)
    except ProcessLookupError:
        pass
    raise SystemExit(1)


if __name__ == '__main__':
    watch(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
