"""One authenticated native host. Commands are named and never raw CDP."""
import json
import socket
import uuid

from ..common import Refused, strict_json_loads, canonical
from .qualification import version

LIMIT = 1024 * 1024


class Bridge:
    def __init__(self):
        self.connection = None
        self.session = self.version = None
        self.buffer = b''
        self.events = []

    def read(self):
        while b'\n' not in self.buffer:
            chunk = self.connection.recv(65536)
            if not chunk:
                raise Refused('transport_error', 'Chrome host disconnected; inspect committed operations, never retry an input.')
            self.buffer += chunk
            if len(self.buffer) > LIMIT:
                raise Refused('invalid_input', 'Chrome message exceeds 1 MiB; read a smaller view.')
        line, self.buffer = self.buffer.split(b'\n', 1)
        return strict_json_loads(line)

    def accept(self, connection):
        if self.connection is not None:
            try:
                if self.connection.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT):
                    raise Refused('permission_denied', 'One native host already controls this Chrome session.')
            except BlockingIOError:
                raise Refused('permission_denied', 'One native host already controls this Chrome session.')
            self.close()
        self.connection, self.buffer = connection, b''
        hello = self.read()
        if (type(hello) is not dict or set(hello) != {'event','session','version'} or hello['event'] != 'hello' or
                type(hello['session']) is not str or not 1 <= len(hello['session']) <= 64):
            self.close()
            raise Refused('permission_denied', 'Native host must identify one Chrome session and full version.')
        version(hello['version'])
        self.session, self.version = hello['session'], hello['version']

    def call(self, name, **arguments):
        if self.connection is None:
            raise Refused('chrome_unavailable', 'Chrome is not connected; open Chrome with the installed extension, then read again.')
        identity = uuid.uuid4().hex
        body = json.dumps({'id':identity,'command':{'name':name,**arguments}},separators=(',',':')).encode() + b'\n'
        if len(body) > LIMIT:
            raise Refused('asking_input_too_large', 'Chrome command exceeds its wire bound; use a smaller input.')
        try:
            self.connection.sendall(body)
            while True:
                reply = self.read()
                if reply.get('event'):
                    self.events.append(reply)
                    continue
                if reply.get('id') != identity:
                    raise Refused('transport_error', 'Chrome response identity changed; inspect status, never retry.')
                if not reply.get('ok'):
                    code, _, message = reply.get('error','refused: Chrome refused input').partition(':')
                    raise Refused(code if code in {'stale_reference','stale_approval','owner_signin','refused','permission_denied'} else 'refused', message.strip())
                return reply['data']
        except (OSError, ValueError) as exc:
            self.close()
            raise Refused('transport_error', 'Chrome connection was cut off; the input may have run. Inspect operation status and never replay.') from exc

    def close(self):
        if self.connection is not None:
            self.connection.close()
        self.connection = None
