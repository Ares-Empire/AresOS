#!/usr/bin/python3 -I
"""Test-only native host of the install probe (brief 18c-b, item 2). Never part of a release.

Chrome starts it for the probe extension and for nothing else (its manifest
allows that one origin). It writes down every message in both directions and
relays them between the probe (Chrome's length-framed pipe) and the check's
socket (one JSON value per line), so the checks can ask Chrome questions
without a debugging port.
"""
import json
import os
import selectors
import socket
import struct
import sys
import time

LIMIT = 1024 * 1024
SOCKET = '/run/aresos-install-test/probe.sock'
LOG = '/out/install/probe.jsonl'


def main():
    origin = sys.argv[1] if len(sys.argv) > 1 else None
    log = open(LOG, 'a', buffering=1)

    def note(direction, body):
        try:
            value = json.loads(body)
        except ValueError:
            value = repr(body[:200])
        log.write(json.dumps({'time': round(time.time(), 3), 'host': os.getpid(), 'origin': origin, direction: value}) + '\n')

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.connect(SOCKET)
        selector = selectors.DefaultSelector()
        selector.register(0, selectors.EVENT_READ, 'probe')
        selector.register(connection, selectors.EVENT_READ, 'check')
        native, lines = b'', b''
        while True:
            for key, _ in selector.select():
                if key.data == 'probe':
                    chunk = os.read(0, 65536)
                    if not chunk:
                        return
                    native += chunk
                    while len(native) >= 4:
                        size = struct.unpack('=I', native[:4])[0]
                        if size > LIMIT:
                            raise ValueError('The probe sent more than 1 MiB')
                        if len(native) < size + 4:
                            break
                        body, native = native[4:size + 4], native[size + 4:]
                        note('probe', body)
                        connection.sendall(body.replace(b'\n', b' ') + b'\n')
                else:
                    chunk = connection.recv(65536)
                    if not chunk:
                        return
                    lines += chunk
                    while b'\n' in lines:
                        body, lines = lines.split(b'\n', 1)
                        note('check', body)
                        output = struct.pack('=I', len(body)) + body
                        while output:
                            output = output[os.write(1, output):]


if __name__ == '__main__':
    main()
