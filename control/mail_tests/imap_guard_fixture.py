"""Test-only serialized IMAP frontend for a real TLS backend.

GreenMail and Dovecot both delete nonempty folders. This fixture adds the missing
server policy, under one command lock covering ALL frontend writers. It is NOT a
claim that either upstream server has that policy, nor a production workaround.
"""
import re
import socket
import socketserver
import ssl
import threading

from support import CERT


class GuardedIMAPFixture:
    def __init__(self, host='greenmail', port=3993, mode='guard', error_text=b'Synthetic failure', backend_password=None):
        fixture = self
        self.mode, self.error_text = mode, error_text
        self.lock = threading.Lock()
        self.server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.server_context.load_cert_chain(CERT / 'tls.crt',CERT / 'tls.key')
        self.client_context = ssl.create_default_context(cafile=str(CERT / 'tls.crt'))
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                with socket.create_connection((host,port),timeout=10) as raw:
                    with fixture.client_context.wrap_socket(raw,server_hostname=host) as conn:
                        backend = conn.makefile('rwb',buffering=0)
                        self.wfile.write(backend.readline())
                        def exact(stream, count):
                            data = b''
                            while len(data) < count:
                                chunk = stream.read(count - len(data))
                                if not chunk:
                                    raise OSError('Truncated literal')
                                data += chunk
                            return data
                        def response(tag, destination):
                            collected = []
                            while True:
                                line = backend.readline()
                                if not line:
                                    raise OSError('Backend disconnected')
                                collected.append(line)
                                if destination:
                                    self.wfile.write(line)
                                literal = re.search(rb'\{(\d+)\}\r\n$',line)
                                if literal:
                                    data = exact(backend,int(literal[1]))
                                    if destination:
                                        self.wfile.write(data)
                                if line.startswith(tag + b' '):
                                    return b''.join(collected)
                        while True:
                            try:
                                line = self.rfile.readline()
                            except (BrokenPipeError, ConnectionResetError):
                                return
                            if not line:
                                return
                            tag,command,*rest = line.split(b' ',2)
                            with fixture.lock:
                                if fixture.mode == 'echo_disconnect_expunge' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'EXPUNGE '):
                                    backend.write(line)
                                    response(tag,False)
                                    self.wfile.write(b'* BYE ' + fixture.error_text + b'\r\n')
                                    return
                                if ((fixture.mode == 'echo_login' and command.upper() == b'LOGIN')
                                    or (fixture.mode == 'echo_store' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'STORE '))
                                    or (fixture.mode == 'echo_expunge' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'EXPUNGE '))):
                                    self.wfile.write(tag + b' BAD ' + fixture.error_text + b'\r\n')
                                    continue
                                if fixture.mode == 'expunge_failure' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'EXPUNGE '):
                                    self.wfile.write(tag + b' NO [UNAVAILABLE] Synthetic cleanup failure\r\n')
                                    continue
                                if command.upper() == b'LOGIN' and backend_password is not None:
                                    # Accept the test's distinct secret while the real backend uses its fixed fixture password.
                                    line = tag + b' LOGIN ' + rest[0].split(b' ',1)[0] + b' "' + backend_password.encode() + b'"\r\n'
                                if command.upper() == b'DELETE' and rest and fixture.mode != 'unsafe':
                                    name = rest[0].strip()
                                    backend.write(b'GUARD STATUS ' + name + b' (MESSAGES)\r\n')
                                    state = response(b'GUARD',False)
                                    count = re.search(rb'MESSAGES (\d+)',state)
                                    if not count or int(count[1]) != 0:
                                        if fixture.mode in {'inuse','permission','generic'}:
                                            reason = {'inuse':b'[INUSE] Temporary refusal', 'permission':b'[NOPERM] Nonempty folder inaccessible', 'generic':b'Permission denied'}[fixture.mode]
                                            self.wfile.write(tag + b' NO ' + reason + b'\r\n')
                                            continue
                                        if fixture.mode == 'missing_probe':
                                            backend.write(b'ERASE SELECT ' + name + b'\r\n')
                                            response(b'ERASE',False)
                                            backend.write(b'MARK UID STORE 1:* +FLAGS.SILENT (\\Deleted)\r\n')
                                            response(b'MARK',False)
                                            backend.write(b'EXPUNGE UID EXPUNGE 1:*\r\n')
                                            response(b'EXPUNGE',False)
                                        self.wfile.write(tag + b' NO [CANNOT] Nonempty DELETE forbidden by fixture policy\r\n')
                                        continue
                                    if fixture.mode == 'empty_delete_failure':
                                        self.wfile.write(tag + b' NO [UNAVAILABLE] Empty cleanup failed\r\n')
                                        continue
                                backend.write(line)
                                literal = re.search(rb'\{(\d+)(\+)?\}\r\n$',line)
                                if literal:
                                    if not literal[2]:
                                        continuation = backend.readline()
                                        self.wfile.write(continuation)
                                        if not continuation.startswith(b'+'):
                                            continue
                                    data = exact(self.rfile,int(literal[1]) + 2)
                                    backend.write(data)
                                response(tag,True)
                            if command.upper() == b'LOGOUT':
                                return
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
            def get_request(self):
                raw,address = super().get_request()
                return fixture.server_context.wrap_socket(raw,server_side=True),address
        self.server = Server(('0.0.0.0',0),Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def __enter__(self):
        return self

    def __exit__(self,*exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
