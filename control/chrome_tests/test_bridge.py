import json
import socket
import selectors
from types import SimpleNamespace
import unittest

from aresos_control.chrome.bridge import Bridge
from aresos_control.common import Refused
from aresos_control.daemon import Daemon


class Handshake(unittest.TestCase):
    def test_invalid_replacement_removes_eof_peer_and_next_host_can_connect(self):
        bridge = Bridge()
        daemon = Daemon.__new__(Daemon)
        daemon.engine = SimpleNamespace(adapters={'chrome':SimpleNamespace(bridge=bridge)})
        daemon.selector = selectors.DefaultSelector()
        connections=[]
        try:
            def peer(hello):
                server,client=socket.socketpair();connections.extend([server,client])
                client.sendall(hello+b'\n')
                return server,client
            original,client=peer(b'{"event":"hello","session":"old","version":"157.0.1.0"}')
            daemon.register_chrome_host(original)
            old_fd=original.fileno()
            client.close()
            invalid,_=peer(b'{"v":1,"method":"tools"}')
            with self.assertRaises(Refused): daemon.register_chrome_host(invalid)
            self.assertNotIn(old_fd, daemon.selector.get_map())
            self.assertIsNone(bridge.connection)
            invalid.close()
            replacement,_=peer(b'{"event":"hello","session":"new","version":"157.0.1.0"}')
            daemon.register_chrome_host(replacement)
            self.assertEqual(bridge.session, 'new')
            self.assertEqual(daemon.selector.get_key(replacement).data, 'chrome-peer')
            rejected,_=peer(b'{"event":"hello","session":"other","version":"157.0.1.0"}')
            with self.assertRaises(Refused): daemon.register_chrome_host(rejected)
            self.assertIs(bridge.connection,replacement)
            self.assertEqual(daemon.selector.get_key(replacement).data, 'chrome-peer')
        finally:
            daemon.selector.close()
            for connection in connections: connection.close()

    def test_invalid_chrome_handshake_leaves_descriptor_for_daemon_refusal(self):
        bridge = Bridge()
        server, client = socket.socketpair()
        try:
            client.sendall(b'{"v":1,"method":"tools","app":"testapp"}\n')
            with self.assertRaises(Refused) as error:
                bridge.accept(server)
            self.assertEqual(error.exception.code, 'permission_denied')
            self.assertIsNone(bridge.connection)
            server.sendall(b'{"ok":false}\n')
            self.assertEqual(json.loads(client.recv(1024)), {'ok':False})
        finally:
            server.close(); client.close()

    def test_invalid_full_version_also_refuses_and_resets_session(self):
        bridge = Bridge()
        server, client = socket.socketpair()
        try:
            client.sendall(b'{"event":"hello","session":"fixture","version":"invalid"}\n')
            with self.assertRaises(Refused) as error:
                bridge.accept(server)
            self.assertEqual(error.exception.code, 'permission_denied')
            self.assertIsNone(bridge.session)
            self.assertIsNone(bridge.version)
            self.assertIsNone(bridge.connection)
            self.assertGreaterEqual(server.fileno(), 0)
        finally:
            server.close(); client.close()
