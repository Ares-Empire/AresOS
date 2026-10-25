import base64
import io
import json
import pathlib
import socket
import socketserver
import struct
import sys
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from offline_webui import Bridge, Channel, LIMIT


class TransportTest(unittest.TestCase):
    def test_cancelled_stream_does_not_end_other_streams(self):
        from unittest.mock import Mock
        channel=Mock()
        channel.receive.side_effect=[dict(id=1,op='data',data=b'cancelled'),dict(id=2,op='data',data=b'keep-going'),EOFError()]
        bridge=Bridge(channel)
        bad,good=Mock(),Mock()
        bad.sendall.side_effect=ConnectionResetError('synthetic browser cancellation')
        bridge.peers={1:bad,2:good}
        bridge.loop()
        good.sendall.assert_called_once_with(b'keep-going')
        channel.send.assert_called_once_with(1,'close')

    def test_partial_reads_and_writes_preserve_every_binary_byte(self):
        output = bytearray()
        def write(raw):
            output.extend(raw[:3])
            return min(3, len(raw))
        sender = Channel(None, write)
        raw = bytes(range(256)) * 40
        sender.send(3, 'data', raw)
        stream = io.BytesIO(output)
        receiver = Channel(lambda count: stream.read(min(count, 2)), None)
        self.assertEqual(receiver.receive(), dict(id=3, op='data', data=raw))
        with self.assertRaises(EOFError): receiver.receive()

    def test_bad_frame_bounds_shapes_and_base64_refuse(self):
        for raw in (struct.pack('!I', 0), struct.pack('!I', LIMIT+1), b'\0\0',
                    json.dumps(dict(id=0, op='open', data='')).encode(),
                    json.dumps(dict(id=1, op='other', data='')).encode(),
                    json.dumps(dict(id=1, op='data', data='!')).encode(),
                    json.dumps(dict(id=True, op='close', data='')).encode()):
            if raw.startswith(b'{'): raw = struct.pack('!I', len(raw)) + raw
            stream = io.BytesIO(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, EOFError)):
                Channel(stream.read, None).receive()

    def test_parallel_http_and_websocket_bytes_over_socket_channel(self):
        class Echo(socketserver.BaseRequestHandler):
            def handle(self):
                while chunk := self.request.recv(4096): self.request.sendall(chunk)
        server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Echo)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        host_socket, guest_socket = socket.socketpair()
        guest = Bridge(Channel(guest_socket.recv, guest_socket.send))
        thread = threading.Thread(target=guest.loop, kwargs=dict(guest=True, destination=server.server_address), daemon=True)
        thread.start()
        host = Bridge(Channel(host_socket.recv, host_socket.send))
        listener = host.server(port=0)
        try:
            peers = [socket.create_connection(listener.server_address) for _ in range(3)]
            for index, peer in enumerate(peers):
                raw = (b'GET / HTTP/1.1\r\nUpgrade: websocket\r\n\r\n' + bytes(range(256))) * (index + 1)
                peer.settimeout(5)
                peer.sendall(raw)
                result = bytearray()
                while len(result) < len(raw): result.extend(peer.recv(len(raw)-len(result)))
                self.assertEqual(result, raw)
            for peer in peers: peer.close()
        finally:
            listener.shutdown(); listener.server_close()
            host_socket.shutdown(socket.SHUT_RDWR); host_socket.close()
            guest_socket.shutdown(socket.SHUT_RDWR); guest_socket.close()
            server.shutdown(); server.server_close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())


if __name__ == '__main__': unittest.main()
