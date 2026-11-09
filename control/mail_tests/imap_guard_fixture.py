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
from owner_state_oracle.transcript import TRACE, Transcript


class GuardedIMAPFixture:
    def __init__(self, host='greenmail', port=3993, mode='guard', error_text=b'Synthetic failure', backend_password=None):
        fixture = self
        self.mode, self.error_text = mode, error_text
        self.trace = TRACE
        # Optional raw received-message literals: preserve binary octets that a
        # real backend may canonicalize during BODY[] retrieval. Test-only.
        self.exact_sources = {}
        self.special_roles = {}
        self.role_map = None
        self.separators = {}
        self.before_command = lambda command, arguments: None
        self.after_command = lambda command, arguments: None
        self.disconnect_before_command = lambda command, arguments: False
        self.hide_copyuid = False
        self.commands = []
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
                        selected, account, event = None, None, None
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
                                if destination and line.startswith(b'* LIST ') and fixture.role_map is not None:
                                    match = re.fullmatch(rb'\* LIST \(([^)]*)\) ("[^"]*"|NIL) (.*?)\r\n', line)
                                    if match:
                                        name = match[3].strip(b'"').decode()
                                        flags = [v for v in match[1].split() if v.lower() not in {b'\\sent', b'\\drafts', b'\\trash', b'\\archive', b'\\junk'}]
                                        flags += [v.encode() for v in fixture.role_map.get(name, [])]
                                        delimiter = ('"' + fixture.separators[name] + '"').encode() if name in fixture.separators else match[2]
                                        line = b'* LIST (' + b' '.join(flags) + b') ' + delimiter + b' ' + match[3] + b'\r\n'
                                if destination and fixture.hide_copyuid:
                                    line = re.sub(rb'\[COPYUID [^]]*\]', b'', line)
                                if destination and line.startswith(b'* LIST ') and fixture.special_roles:
                                    for name, flag in fixture.special_roles.items():
                                        if line.rstrip().endswith((b'"' + name.encode() + b'"', b' ' + name.encode())):
                                            line = line.replace(b'(', b'(' + flag.encode() + b' ', 1)
                                collected.append(line)
                                literal = re.search(rb'\{(\d+)\}\r\n$',line)
                                if literal:
                                    data = exact(backend,int(literal[1]))
                                    if event is not None:
                                        uid = re.search(rb'UID (\d+)', line)
                                        event['identities'].append(Transcript.message(data, account=account, folder=selected, uid=int(uid[1]) if uid else None))
                                    if destination:
                                        mid = re.search(rb'(?im)^Message-ID: ([^\r\n]+)', data)
                                        if b'BODY[]' in line and mid and mid[1] in fixture.exact_sources:
                                            data = fixture.exact_sources[mid[1]]
                                            line = line[:literal.start()] + b'{' + str(len(data)).encode() + b'}\r\n'
                                        self.wfile.write(line)
                                        self.wfile.write(data)
                                elif destination:
                                    self.wfile.write(line)
                                if line.startswith(tag + b' '):
                                    if event is not None:
                                        event.update(accepted=line.split(b' ', 2)[1] == b'OK', reply='delivered' if destination else 'lost')
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
                                arguments = rest[0].strip() if rest else b''
                                fixture.commands.append((command.upper(), arguments))
                                if command.upper() == b'LOGIN':
                                    account = arguments.split(b' ', 1)[0].strip(b'"').decode()
                                if command.upper() in {b'SELECT', b'EXAMINE'}:
                                    selected = arguments.strip(b'"').decode()
                                event = fixture.trace.command(command.decode().upper(), None, selected,
                                    dict(fixture.role_map or fixture.special_roles), principal=account, delimiters=dict(fixture.separators),
                                    arguments=arguments.decode(errors='replace') if command.upper() != b'LOGIN' else '[credentials omitted]')
                                if fixture.disconnect_before_command(command.upper(), arguments):
                                    self.wfile.write(b'* BYE Scripted connection loss during reporting\r\n')
                                    return
                                refusal = fixture.before_command(command.upper(), arguments)
                                if refusal:
                                    self.wfile.write(tag + b' NO ' + refusal + b'\r\n')
                                    event.update(accepted=False, reply='delivered')
                                    continue
                                if fixture.mode == 'echo_disconnect_expunge' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'EXPUNGE '):
                                    backend.write(line)
                                    response(tag,False)
                                    self.wfile.write(b'* BYE ' + fixture.error_text + b'\r\n')
                                    return
                                if ((fixture.mode == 'echo_login' and command.upper() == b'LOGIN')
                                    or (fixture.mode == 'echo_store' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'STORE '))
                                    or (fixture.mode == 'echo_expunge' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'EXPUNGE '))):
                                    self.wfile.write(tag + b' BAD ' + fixture.error_text + b'\r\n')
                                    event.update(accepted=False, reply='delivered')
                                    continue
                                if fixture.mode == 'expunge_failure' and command.upper() == b'UID' and rest and rest[0].upper().startswith(b'EXPUNGE '):
                                    self.wfile.write(tag + b' NO [UNAVAILABLE] Synthetic cleanup failure\r\n')
                                    event.update(accepted=False, reply='delivered')
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
                                            event.update(accepted=False, reply='delivered')
                                            continue
                                        if fixture.mode == 'missing_probe':
                                            backend.write(b'ERASE SELECT ' + name + b'\r\n')
                                            response(b'ERASE',False)
                                            backend.write(b'MARK UID STORE 1:* +FLAGS.SILENT (\\Deleted)\r\n')
                                            response(b'MARK',False)
                                            backend.write(b'EXPUNGE UID EXPUNGE 1:*\r\n')
                                            response(b'EXPUNGE',False)
                                        self.wfile.write(tag + b' NO [CANNOT] Nonempty DELETE forbidden by fixture policy\r\n')
                                        event.update(accepted=False, reply='delivered')
                                        continue
                                    if fixture.mode == 'empty_delete_failure':
                                        self.wfile.write(tag + b' NO [UNAVAILABLE] Empty cleanup failed\r\n')
                                        event.update(accepted=False, reply='delivered')
                                        continue
                                backend.write(line)
                                literal = re.search(rb'\{(\d+)(\+)?\}\r\n$',line)
                                if literal:
                                    if not literal[2]:
                                        continuation = backend.readline()
                                        self.wfile.write(continuation)
                                        if not continuation.startswith(b'+'):
                                            event.update(accepted=False, reply='delivered')
                                            continue
                                    data = exact(self.rfile,int(literal[1]) + 2)
                                    event['identities'].append(Transcript.message(data[:-2], account=account, folder=arguments.split(b' ',1)[0].strip(b'"').decode()))
                                    backend.write(data)
                                response(tag,True)
                                fixture.after_command(command.upper(), arguments)
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
