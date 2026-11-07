#!/usr/bin/env python3
"""Experimental native messaging <-> private Unix socket relay, no TCP listener."""
import json
import os
import selectors
import socket
import struct
import sys

sock = socket.socket(socket.AF_UNIX)
sock.connect(os.environ['CHROME_CHECK_SOCKET'])
selector = selectors.DefaultSelector()
selector.register(sys.stdin.buffer, selectors.EVENT_READ, 'chrome')
selector.register(sock, selectors.EVENT_READ, 'tool')
native = b''
lines = b''
while True:
    for key, _ in selector.select():
        if key.data == 'chrome':
            data = os.read(sys.stdin.fileno(), 65536)
            if not data:
                sys.exit(0)
            native += data
            while len(native) >= 4:
                length = struct.unpack('=I', native[:4])[0]
                if length > 16 * 1024 * 1024:
                    sys.exit('oversize native message')
                if len(native) < length + 4:
                    break
                sock.sendall(native[4:length + 4] + b'\n')
                native = native[length + 4:]
        else:
            data = sock.recv(65536)
            if not data:
                sys.exit(0)
            lines += data
            while b'\n' in lines:
                line, lines = lines.split(b'\n', 1)
                json.loads(line)
                sys.stdout.buffer.write(struct.pack('=I', len(line)) + line)
                sys.stdout.buffer.flush()
