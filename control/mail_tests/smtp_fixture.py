"""Small real TLS SMTP failure server; never relays, no automatic deduplication."""
import base64
from contextlib import closing
import json
import socketserver
import sqlite3
import ssl
import threading

from support import CERT
from owner_state_oracle.transcript import TRACE, Transcript


class SMTPFixture:
    def __init__(self, root, mode='normal', on_data=None, starttls=False, advertise_starttls=True, error_text=b'Synthetic failure'):
        self.trace = TRACE
        self.database = root / 'smtp.sqlite'
        with closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS arrivals(id INTEGER PRIMARY KEY, recipients TEXT, raw BLOB)')
            db.commit()
        self.mode, self.on_data, self.auth_count = mode, on_data, 0
        self.error_text = error_text
        self.starttls, self.advertise_starttls = starttls, advertise_starttls
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(CERT / 'tls.crt', CERT / 'tls.key')
        fixture = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                event = None
                def send(value):
                    self.wfile.write(value + b'\r\n')
                    self.wfile.flush()
                    if event is not None:
                        event.update(accepted=value.startswith((b'2', b'3')), reply='delivered')
                send(b'220 synthetic SMTP')
                recipients = []
                encrypted = not fixture.starttls
                while True:
                    line = self.rfile.readline(100000)
                    if not line:
                        return
                    verb = line.split(b' ',1)[0].upper().strip()
                    event = fixture.trace.command(verb.decode(), recipients=list(recipients))
                    if verb in {b'EHLO', b'HELO'}:
                        send(b'250-localhost')
                        if fixture.starttls and not encrypted and fixture.advertise_starttls:
                            send(b'250-STARTTLS')
                        send(b'250 AUTH PLAIN LOGIN')
                    elif verb == b'STARTTLS':
                        send(b'220 start TLS')
                        self.connection = fixture.context.wrap_socket(self.connection,server_side=True)
                        self.rfile = self.connection.makefile('rb')
                        self.wfile = self.connection.makefile('wb')
                        encrypted = True
                    elif verb == b'AUTH':
                        if not encrypted:
                            raise AssertionError('Password before TLS')
                        fixture.auth_count += 1
                        send(b'535 ' + fixture.error_text if fixture.mode == 'echo_auth' else b'235 authenticated')
                    elif verb == b'MAIL':
                        send(b'550 ' + fixture.error_text if fixture.mode == 'echo_mail' else b'250 sender ok')
                    elif verb == b'RCPT':
                        recipient = line.decode().split('<',1)[1].split('>',1)[0]
                        if recipient.startswith('refuse'):
                            send(b'550 synthetic refused')
                        else:
                            recipients.append(recipient)
                            send(b'250 recipient ok')
                    elif verb == b'DATA':
                        if fixture.mode == 'before_data':
                            send(b'554 no DATA accepted')
                            continue
                        send(b'354 continue')
                        chunks = []
                        while True:
                            data = self.rfile.readline(100000)
                            if data in {b'.\r\n', b'.\n', b''}:
                                break
                            chunks.append(data[1:] if data.startswith(b'..') else data)
                        raw = b''.join(chunks)
                        event.update(identities=[Transcript.message(raw)], recipients=list(recipients), accepted=True, reply='lost')
                        with closing(sqlite3.connect(fixture.database)) as db:
                            db.execute('INSERT INTO arrivals(recipients,raw) VALUES (?,?)', (json.dumps(recipients),raw))
                            db.commit()
                        if fixture.on_data:
                            fixture.on_data(raw)
                        if fixture.mode == 'lost_answer':
                            event['reply'] = 'lost'
                            return
                        send(b'554 ' + fixture.error_text if fixture.mode == 'echo_data' else b'250 accepted')
                    elif verb == b'QUIT':
                        send(b'221 bye')
                        return
                    else:
                        send(b'250 ok')

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
            def get_request(self):
                connection, address = super().get_request()
                try:
                    return (connection if fixture.starttls else fixture.context.wrap_socket(connection, server_side=True)), address
                except Exception:
                    connection.close()
                    raise
        self.server = Server(('0.0.0.0',0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def arrivals(self):
        with closing(sqlite3.connect(self.database)) as db:
            return [(json.loads(r), bytes(raw)) for r,raw in db.execute('SELECT recipients,raw FROM arrivals ORDER BY id')]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
