"""Small real TLS SMTP failure server; never relays, no automatic deduplication."""
import base64
from contextlib import closing
import json
import socketserver
import sqlite3
import ssl
import threading

from support import CERT


class SMTPFixture:
    def __init__(self, root, mode='normal', on_data=None):
        self.database = root / 'smtp.sqlite'
        with closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS arrivals(id INTEGER PRIMARY KEY, recipients TEXT, raw BLOB)')
            db.commit()
        self.mode, self.on_data, self.auth_count = mode, on_data, 0
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(CERT / 'tls.crt', CERT / 'tls.key')
        fixture = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                def send(value):
                    self.wfile.write(value + b'\r\n')
                    self.wfile.flush()
                send(b'220 synthetic SMTP')
                recipients = []
                while True:
                    line = self.rfile.readline(100000)
                    if not line:
                        return
                    verb = line.split(b' ',1)[0].upper().strip()
                    if verb in {b'EHLO', b'HELO'}:
                        send(b'250-localhost')
                        send(b'250 AUTH PLAIN LOGIN')
                    elif verb == b'AUTH':
                        fixture.auth_count += 1
                        send(b'235 authenticated')
                    elif verb == b'MAIL':
                        send(b'250 sender ok')
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
                        with closing(sqlite3.connect(fixture.database)) as db:
                            db.execute('INSERT INTO arrivals(recipients,raw) VALUES (?,?)', (json.dumps(recipients),raw))
                            db.commit()
                        if fixture.on_data:
                            fixture.on_data(raw)
                        if fixture.mode == 'lost_answer':
                            return
                        send(b'250 accepted')
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
                    return fixture.context.wrap_socket(connection, server_side=True), address
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
