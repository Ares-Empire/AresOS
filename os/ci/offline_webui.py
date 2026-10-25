"""HTTP/WebSocket byte transport over virtio-serial while the NIC is link-down.

Only the original guest loopback WebUI is reachable. No frame or request body
is logged: installer passwords stay in memory. This is not a network bypass
for guest programs; the guest side has one hard-coded loopback destination.
"""
import base64
import json
import os
import socket
import socketserver
import struct
import threading

LIMIT = 131072


class Channel:
    def __init__(self, read, write):
        self.read, self.write = read, write
        self.lock = threading.Lock()

    def exact(self, size):
        result = bytearray()
        while len(result) < size:
            part = self.read(size - len(result))
            if not part:
                raise EOFError('Offline WebUI channel closed')
            result.extend(part)
        return bytes(result)

    def receive(self):
        size, = struct.unpack('!I', self.exact(4))
        if not 0 < size <= LIMIT:
            raise ValueError('Offline WebUI frame bound')
        value = json.loads(self.exact(size))
        if set(value) != {'id', 'op', 'data'} or type(value['id']) is not int or value['id'] < 1 or value['op'] not in ('open', 'data', 'close'):
            raise ValueError('Offline WebUI frame shape')
        value['data'] = base64.b64decode(value['data'], validate=True)
        return value

    def send(self, identifier, operation, data=b''):
        raw = json.dumps(dict(id=identifier, op=operation, data=base64.b64encode(data).decode()), separators=(',', ':')).encode()
        if len(raw) > LIMIT:
            raise ValueError('Offline WebUI send bound')
        with self.lock:
            data = struct.pack('!I', len(raw)) + raw
            while data:
                count = self.write(data)
                if count is None:  # socket.sendall
                    break
                if count <= 0:
                    raise EOFError('Offline WebUI short write')
                data = data[count:]


class Bridge:
    def __init__(self, channel):
        self.channel = channel
        self.peers = {}
        self.next_id = 1
        self.lock = threading.Lock()

    def close(self, identifier):
        peer = self.peers.pop(identifier, None)
        if peer:
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            peer.close()

    def copy(self, identifier, peer):
        try:
            while chunk := peer.recv(32768):
                self.channel.send(identifier, 'data', chunk)
        except (OSError, EOFError):
            # HTTP clients may reset individual connections; close only this
            # stream. Framing/protocol failures in loop still fail the channel.
            pass
        finally:
            try:
                self.channel.send(identifier, 'close')
            except (OSError, EOFError):
                pass
            self.close(identifier)

    def loop(self, guest=False, destination=('127.0.0.1', 8080)):
        try:
            while True:
                frame = self.channel.receive()
                identifier = frame['id']
                if frame['op'] == 'open':
                    if not guest or identifier in self.peers or frame['data']:
                        raise ValueError('Unexpected offline WebUI open')
                    peer = socket.create_connection(destination, timeout=30)
                    peer.settimeout(None)
                    self.peers[identifier] = peer
                    threading.Thread(target=self.copy, args=(identifier, peer), daemon=True).start()
                elif frame['op'] == 'data':
                    peer = self.peers.get(identifier)
                    if peer:
                        try:
                            peer.sendall(frame['data'])
                        except OSError:
                            # A cancelled browser request must not tear down
                            # unrelated HTTP/WebSocket streams on this channel.
                            self.channel.send(identifier, 'close')
                            self.close(identifier)
                else:
                    self.close(identifier)
        except (EOFError, OSError):
            pass
        finally:
            for identifier in list(self.peers):
                self.close(identifier)

    def server(self, port=18080):
        bridge = self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                with bridge.lock:
                    identifier = bridge.next_id
                    bridge.next_id += 1
                    bridge.peers[identifier] = self.request
                bridge.channel.send(identifier, 'open')
                bridge.copy(identifier, self.request)
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        server = Server(('127.0.0.1', port), Handler)
        threading.Thread(target=self.loop, daemon=True).start()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server


def guest():
    fd = os.open('/dev/virtio-ports/ares.webui', os.O_RDWR)
    Bridge(Channel(lambda n: os.read(fd, n), lambda data: os.write(fd, data))).loop(guest=True)


if __name__ == '__main__':
    guest()
