#!/usr/bin/python3 -I -S
"""Length-framed Chrome pipe to the service's sole private Unix channel."""
import os
import selectors
import socket
import struct
import sys

LIMIT = 1024 * 1024
SOCKET = '/run/aresos-tools/chrome.sock'


def relay(path=SOCKET, source=0, destination=1):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.connect(path)
        selector = selectors.DefaultSelector()
        selector.register(source, selectors.EVENT_READ, 'chrome')
        selector.register(connection, selectors.EVENT_READ, 'service')
        native, lines = b'', b''
        try:
            while True:
                for key, _ in selector.select():
                    if key.data == 'chrome':
                        chunk = os.read(source, 65536)
                        if not chunk:
                            return
                        native += chunk
                        while len(native) >= 4:
                            size = struct.unpack('=I', native[:4])[0]
                            if size > LIMIT:
                                raise ValueError('Native message exceeds 1 MiB')
                            if len(native) < size + 4:
                                break
                            body, native = native[4:size + 4], native[size + 4:]
                            if b'\n' in body:
                                raise ValueError('Native messages must contain one JSON line')
                            connection.sendall(body + b'\n')
                    else:
                        chunk = connection.recv(65536)
                        if not chunk:
                            return
                        lines += chunk
                        if len(lines) > LIMIT:
                            raise ValueError('Service message exceeds 1 MiB')
                        while b'\n' in lines:
                            body, lines = lines.split(b'\n', 1)
                            output = struct.pack('=I', len(body)) + body
                            while output:
                                output = output[os.write(destination, output):]
        finally:
            selector.close()


if __name__ == '__main__':
    relay()
