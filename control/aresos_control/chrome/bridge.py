"""One authenticated native host. Commands are named and never raw CDP."""
import json
import base64
import binascii
import select
import socket
import uuid

from ..common import Refused, strict_json_loads, canonical, visible
from .qualification import version

LIMIT = 1024 * 1024


class Bridge:
    def __init__(self):
        self.connection = None
        self.session = self.version = self.connection_identity = None
        self.buffer = b''
        self.events = []
        self.on_event = lambda event: self.events.append(event)

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
                readable, _, _ = select.select([self.connection], [], [], 0)
                if not readable or self.connection.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT):
                    raise Refused('permission_denied', 'One native host already controls this Chrome session.')
            except BlockingIOError:
                raise Refused('permission_denied', 'One native host already controls this Chrome session.')
            self.close()
        self.connection, self.buffer = connection, b''
        try:
            hello = self.read()
            if (type(hello) is not dict or set(hello) != {'event','session','version'} or hello['event'] != 'hello' or
                    type(hello['session']) is not str or not 1 <= len(hello['session']) <= 64):
                raise ValueError('Invalid native handshake')
            version(hello['version'])
        except Exception as exc:
            # The accepting daemon still owns this descriptor and must send its
            # refusal before closing it. Closing here killed the entire daemon.
            self.connection, self.buffer = None, b''
            self.session = self.version = self.connection_identity = None
            raise Refused('permission_denied', 'Native host must identify one Chrome session and full version.') from exc
        self.session, self.version = hello['session'], hello['version']
        self.connection_identity = uuid.uuid4().hex

    def call(self, name, **arguments):
        if self.connection is None:
            raise Refused('chrome_unavailable', 'Chrome is not connected; open Chrome with the installed extension, then read again.')
        identity = uuid.uuid4().hex
        body = json.dumps({'id':identity,'command':{'name':name,**arguments}},separators=(',',':')).encode() + b'\n'
        if len(body) > LIMIT:
            raise Refused('asking_input_too_large', 'Chrome command exceeds its wire bound; use a smaller input.')
        try:
            self.connection.sendall(body)
            assembled = bytearray()
            total = None
            event_error = None
            while True:
                reply = self.read()
                if reply.get('event'):
                    try:
                        self.on_event(reply)
                    except Exception as exc:
                        # Drain this command's own response before reporting the failed event commit.
                        # Otherwise its late response poisons the next command identity.
                        event_error = event_error or exc
                    continue
                if reply.get('id') != identity:
                    raise Refused('transport_error', 'Chrome response identity changed; inspect status, never retry.')
                if 'chunk' in reply:
                    chunk = reply['chunk']
                    if (type(chunk) is not dict or set(chunk) != {'offset','total','bytes'} or type(chunk['offset']) is not int or
                            type(chunk['total']) is not int or not 0 < chunk['total'] <= 32*1024*1024 or
                            chunk['offset'] != len(assembled) or total is not None and total != chunk['total']):
                        raise Refused('transport_error','Invalid Chrome response fragment; nothing is retried.')
                    total = chunk['total']
                    data = base64.b64decode(chunk['bytes'],validate=True)
                    if not data or len(data)>64*1024 or len(assembled)+len(data)>total:
                        raise Refused('transport_error','Chrome fragment exceeds its response bound.')
                    assembled.extend(data)
                    if len(assembled)<total:continue
                    reply=strict_json_loads(bytes(assembled))
                    if reply.get('id')!=identity or 'chunk' in reply:
                        raise Refused('transport_error','Chrome assembled response identity changed.')
                elif assembled:
                    raise Refused('transport_error','Incomplete Chrome response fragments.')
                if event_error is not None:
                    raise Refused('unknown','A Chrome owner event could not be committed; inspect status and never replay an input.') from event_error
                if not reply.get('ok'):
                    raw = reply.get('error','refused: Chrome refused input')
                    code, separator, message = raw.partition(':')
                    if not separator: message = raw
                    # Extension errors are literals today; escape them anyway, like page text.
                    raise Refused(code if code in {'stale_reference','stale_approval','reload_required','owner_signin','refused','permission_denied','unknown','transport_error'} else 'refused', visible(message.strip()))
                return reply['data']
        except (OSError, ValueError, binascii.Error, TypeError) as exc:
            self.close()
            raise Refused('transport_error', 'Chrome connection was cut off; the input may have run. Inspect operation status and never replay.') from exc

    def close(self):
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        self.session = self.version = self.connection_identity = None
        self.buffer = b''
