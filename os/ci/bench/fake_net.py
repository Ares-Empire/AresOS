"""Disposable loopback fixtures for the desk and the hosted VM."""
from contextlib import contextmanager, ExitStack
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import ssl
import subprocess
from threading import Thread
import time

from network import HOST

ENV = {'PATH': os.defpath, 'LC_ALL': 'C'}
NAMESPACE_ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'}
REPLY = b'bench fixture\n'


def offline_namespace(argv):
    # Setup needs namespace-local privileges. Drop them before the driver starts.
    return ['/usr/bin/unshare', '--user', '--map-current-user', '--keep-caps', '--net', '--',
            '/usr/bin/bash', '-ec', 'ip link set lo up; exec setpriv --no-new-privs '
            '--inh-caps=-all --ambient-caps=-all --bounding-set=-all -- "$@"', 'bench', *argv]


def fresh_ca(folder):
    folder = Path(folder)
    ca_key, ca, key, csr, cert = (folder / name for name in ('ca.key', 'ca.pem', 'stub.key', 'stub.csr', 'stub.pem'))
    extensions = folder / 'stub.cnf'
    extensions.write_text(f'basicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:{HOST}\n')

    def openssl(*args):
        subprocess.run(['/usr/bin/openssl', *args], check=True, timeout=15, env=ENV,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=AresOS bench fixture CA',
            '-keyout', ca_key, '-out', ca, '-addext', 'basicConstraints=critical,CA:TRUE',
            '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    openssl('req', '-new', '-newkey', 'rsa:2048', '-nodes', '-subj', f'/CN={HOST}', '-keyout', key, '-out', csr)
    openssl('x509', '-req', '-in', csr, '-CA', ca, '-CAkey', ca_key, '-CAcreateserial',
            '-days', '1', '-extfile', extensions, '-out', cert)
    ca_key.unlink()
    return ca, cert, key


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/slow':
            time.sleep(0.3)
        self.send_response(503 if self.path == '/wrong' else 200)
        self.end_headers()
        self.wfile.write(b'wrong fixture\n' if self.path == '/wrong' else REPLY)

    def log_message(self, *_):
        pass


class Listener(HTTPServer):
    allow_reuse_address = True

    def __init__(self, port, tls=None):
        self.connections = 0
        self.tls = tls
        super().__init__(('127.0.0.1', port), Handler)

    def get_request(self):
        connection, address = super().get_request()
        self.connections += 1
        connection.settimeout(1)
        if self.tls:
            try:
                connection = self.tls.wrap_socket(connection, server_side=True)
            except (OSError, ssl.SSLError):
                connection.close()
                raise
        return connection, address

    def handle_error(self, *_):
        pass


@contextmanager
def listening(port=0, tls=None):
    with Listener(port, tls) as listener:
        thread = Thread(target=listener.serve_forever, kwargs={'poll_interval': 0.05})
        thread.start()
        try:
            yield listener
        finally:
            listener.shutdown()
            thread.join()


class Stubs:
    def __init__(self, folder, port):
        self.ca, certificate, key = fresh_ca(folder)
        self.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.tls.load_cert_chain(certificate, key)
        key.unlink()
        self.port = port
        self.server = ExitStack()
        self.running = False

    def up(self):
        if not self.running:
            listener = self.server.enter_context(listening(self.port, self.tls))
            self.port = listener.server_port
            self.running = True

    def down(self):
        self.server.close()
        self.running = False
