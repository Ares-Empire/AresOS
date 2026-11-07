"""Report socket creation separately from connecting to an unavailable VSOCK host."""
import json
import os
from pathlib import Path
import socket

print('SANDBOX_IDENTITY ' + json.dumps({
    'namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('net', 'mnt')},
    'seccomp': [s for s in Path('/proc/self/status').read_text().splitlines()
                if s.startswith(('Seccomp:', 'Seccomp_filters:'))],
}), flush=True)
for name in ('AF_UNIX', 'AF_VSOCK'):
    try:
        s = socket.socket(getattr(socket, name), socket.SOCK_STREAM)
    except OSError as error:
        print('SOCKET_STATE ' + json.dumps({'family': name, 'errno': error.errno}), flush=True)
    else:
        s.close()
        print('SOCKET_STATE ' + json.dumps({'family': name, 'created': True}), flush=True)
