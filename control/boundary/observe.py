"""Outside /proc observer for the fixed native and standalone probes, same uid.

The root supervisor supplies stdout; the child cannot open the evidence directory.
Sampling starts only after the API is about to dispatch tools, after launcher
canaries have exited, so their namespaces cannot be mistaken for native Bash's.
"""
import json
import os
from pathlib import Path
import signal
import time

running = True
seen = set()


def stop(*args):
    global running
    running = False


signal.signal(signal.SIGTERM, stop)
print('OBSERVER ' + json.dumps({n: os.readlink('/proc/self/ns/' + n) for n in ('net', 'mnt')}), flush=True)
while running:
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit() or directory.name in seen:
            continue
        try:
            executable = os.readlink(directory / 'exe')
            command = directory.joinpath('cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            if executable != '/usr/bin/sleep' and not (executable.startswith('/usr/bin/python3') and
                    any(name in command for name in ('boundary-hostile.py', 'boundary-socket-state.py',
                                                      '/opt/aresos-control/hostile.py'))):
                continue
            seen.add(directory.name)
            pid = int(directory.name)
            ancestry = []
            for _ in range(8):
                proc = Path('/proc') / str(pid)
                status = proc.joinpath('status').read_text().splitlines()
                command = proc.joinpath('cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
                try:
                    exe = os.readlink(proc / 'exe')
                except OSError:
                    exe = 'unreadable'
                ancestry.append({'pid': pid, 'command': command, 'exe': exe,
                                 'inner_pid': int(next(s.split()[-1] for s in status if s.startswith('NSpid:'))),
                                 'namespaces': {n: os.readlink(proc / 'ns' / n) for n in ('net', 'mnt')},
                                 'seccomp': [s for s in status if s.startswith(('Seccomp:', 'Seccomp_filters:'))]})
                if len(ancestry) == 1:
                    ancestry[-1]['mountinfo'] = proc.joinpath('mountinfo').read_text()
                pid = int(next(s.split()[1] for s in status if s.startswith('PPid:')))
                if not pid or pid == os.getpid():
                    break
            print('NATIVE_PROCESS ' + json.dumps(ancestry), flush=True)
        except (OSError, StopIteration):
            continue
    time.sleep(.01)
