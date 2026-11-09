import json
import socket
import unittest

from aresos_control.chrome.bridge import Bridge
from aresos_control.common import Refused


class Handshake(unittest.TestCase):
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
