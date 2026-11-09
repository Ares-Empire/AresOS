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
        daemon.engine = SimpleNamespace(adapters={'chrome':SimpleNamespace(bridge=bridge,maintenance=lambda:None)})
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

    def test_transport_closed_outside_selector_can_reconnect_on_reused_descriptor(self):
        bridge=Bridge();daemon=Daemon.__new__(Daemon)
        daemon.engine=SimpleNamespace(adapters={'chrome':SimpleNamespace(bridge=bridge,maintenance=lambda:None)})
        daemon.selector=selectors.DefaultSelector();pairs=[]
        try:
            for session in ['old','new']:
                server,client=socket.socketpair();pairs.extend([server,client]);client.sendall(json.dumps({'event':'hello','session':session,'version':'157.0.1.0'}).encode()+b'\n')
                daemon.register_chrome_host(server)
                if session=='old':bridge.close()
            self.assertEqual(bridge.session,'new');self.assertEqual(len(daemon.selector.get_map()),1)
        finally:
            daemon.selector.close()
            for connection in pairs:connection.close()

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

class FragmentedReplies(unittest.TestCase):
    def test_large_multibyte_page_reassembles_before_paging_and_rejects_wrong_offsets(self):
        import base64
        import json
        from aresos_control.chrome.bridge import Bridge
        class Peer:
            def __init__(self,broken=False):self.buffer=b'';self.broken=broken
            def sendall(self,data):
                identity=json.loads(data)['id'];value=json.dumps({'id':identity,'ok':True,'data':{'text':'é🦊'*300000}},ensure_ascii=False).encode()
                for offset in range(0,len(value),65536):
                    message={'id':identity,'chunk':{'offset':offset+(1 if self.broken else 0),'total':len(value),'bytes':base64.b64encode(value[offset:offset+65536]).decode()}}
                    self.buffer+=(json.dumps(message)+'\n').encode()
            def recv(self,size):value=self.buffer[:size];self.buffer=self.buffer[size:];return value
            def close(self):pass
        bridge=Bridge();bridge.connection=Peer()
        self.assertEqual(bridge.call('read',tab=1)['text'],'é🦊'*300000)
        bridge.connection=Peer(True)
        with self.assertRaises(Refused):bridge.call('read',tab=1)

    def test_failed_owner_event_drains_its_reply_before_the_next_command(self):
        import json
        from aresos_control.chrome.bridge import Bridge
        class Peer:
            def __init__(self):self.buffer=b''
            def sendall(self,data):
                identity=json.loads(data)['id']
                self.buffer+=(json.dumps({'event':'released','tab':1})+'\n'+json.dumps({'id':identity,'ok':True,'data':{'reply':identity}})+'\n').encode()
            def recv(self,size):value=self.buffer[:size];self.buffer=self.buffer[size:];return value
            def close(self):pass
        bridge=Bridge();bridge.connection=Peer();bridge.on_event=lambda event:(_ for _ in ()).throw(OSError('Synthetic failed event commit'))
        with self.assertRaises(Refused) as error:bridge.call('input')
        self.assertEqual(error.exception.code,'unknown')
        bridge.on_event=lambda event:None
        self.assertIn('reply',bridge.call('tabs'))


class ConnectionDelivery(unittest.TestCase):
    def test_accepted_connection_refreshes_before_any_tool_and_rejected_replacement_does_not(self):
        calls=[];bridge=Bridge();daemon=Daemon.__new__(Daemon)
        daemon.engine=SimpleNamespace(adapters={'chrome':SimpleNamespace(bridge=bridge,maintenance=lambda:calls.append(bridge.version))})
        daemon.selector=selectors.DefaultSelector();pairs=[]
        try:
            for session in ['first','rejected']:
                server,client=socket.socketpair();pairs.extend([server,client]);client.sendall(json.dumps({'event':'hello','session':session,'version':'157.0.1.0'}).encode()+b'\n')
                if session=='first':daemon.register_chrome_host(server)
                else:
                    with self.assertRaises(Refused):daemon.register_chrome_host(server)
            self.assertEqual(calls,['157.0.1.0'])
        finally:
            daemon.selector.close()
            for connection in pairs:connection.close()
