"""One Chrome tool call over the service's act socket, as browser.mjs makes it.

The install proof runs as root and the socket answers only the owner, so the
proof starts this file as the owner: python3 tool_call.py tabs '{}'
"""
import json
import socket
import sys


def main(action, arguments):
    request = {'v': 1, 'method': 'call', 'action': 'chrome_' + action, 'arguments': json.loads(arguments)}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(20)
        connection.connect('/run/aresos-tools/act.sock')
        connection.sendall(json.dumps(request).encode() + b'\n')
        reply = b''
        while b'\n' not in reply:
            chunk = connection.recv(65536)
            if not chunk:
                break
            reply += chunk
    sys.stdout.write(reply.decode())


if __name__ == '__main__':
    main(*sys.argv[1:3])
