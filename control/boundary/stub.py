"""Live listeners, not a tool implementation. All data is synthetic.

The supervisor owns the listening descriptors, then drops to aresos-tools.
admin.sock remains root:root 0600; act/chrome are tools:assistant 0660.
"""
import json
import os
from pathlib import Path
import selectors
import socket

fixtures = json.loads(Path('/opt/aresos-control/fixtures.json').read_text())
selector = selectors.DefaultSelector()
listeners = []
for name, address in fixtures['sockets'].items():
    if address.startswith('@'):
        address = '\0' + address[1:]
    else:
        Path(address).parent.mkdir(parents=True, exist_ok=True)
        Path(address).unlink(missing_ok=True)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(address)
    if not address.startswith('\0'):
        os.chown(address, 0 if name == 'admin' else 10002, 0 if name == 'admin' else 10001)
        os.chmod(address, 0o600 if name == 'admin' else 0o660)
    listener.listen()
    selector.register(listener, selectors.EVENT_READ, name)
    listeners.append(listener)
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(('127.0.0.1', 18080))
listener.listen()
selector.register(listener, selectors.EVENT_READ, 'network')
listeners.append(listener)
os.setgroups([])
os.setgid(10002)
os.setuid(10002)
print('STUB_READY uid=' + str(os.getuid()), flush=True)
while True:
    for key, _ in selector.select():
        connection, _ = key.fileobj.accept()
        print('CONNECTION ' + json.dumps({'listener': key.data}), flush=True)
        with connection:
            if key.data == 'network':
                connection.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK')
