"""One authenticated native host. Commands are named and never raw CDP."""
import json
import base64
import binascii
from collections import OrderedDict
from contextlib import contextmanager
import select
import socket
import time
import uuid

from ..common import Refused, strict_json_loads, canonical, visible
from .qualification import version

LIMIT = 1024 * 1024
# Brief 28, item 4. A command sent inside `bounded` carries the milliseconds it
# has left (`time_left_ms`), and the bridge waits for its reply that long plus
# GRACE seconds, then gives it up. A late reply is dropped by its id and never
# passes for the next command's. If it still hasn't come SOCKET_BOUND seconds
# after its command was sent (the daemon's settimeout on this socket), the
# connection is closed as a silent socket closes it. The bridge remembers the
# last GIVEN_UP ids it gave up on.
GRACE, SOCKET_BOUND, GIVEN_UP = .5, 15, 64


class GaveUp(Exception):
    """No reply came in a command's time plus GRACE."""


class TimeLeft:
    """The end (a time.monotonic() value) by which the commands sent now must answer; None sends them without time."""
    end = None

    @contextmanager
    def bounded(self, end):
        """Inside, every command carries the time left to `end`, or to an earlier end already in force."""
        previous = self.end
        self.end = end if previous is None else min(previous, end)
        try:
            yield
        finally:
            self.end = previous


class Bridge(TimeLeft):
    def __init__(self):
        self.connection = None
        self.session = self.version = self.connection_identity = None
        # pid, uid and start time of the process that connected (SO_PEERCRED and
        # /proc), the polkit subject for the owner's password (F7).
        self.peer = None
        self.buffer = b''
        self.events = []
        self.on_event = lambda event: self.events.append(event)
        # Commands given up on: id -> when their reply is overdue, None once it came.
        self.given_up = OrderedDict()

    def read(self, until=None):
        while b'\n' not in self.buffer:
            self.wait(until)
            chunk = self.connection.recv(65536)
            if not chunk:
                raise Refused('transport_error', 'Chrome host disconnected; inspect committed operations, never retry an input.')
            self.buffer += chunk
            if len(self.buffer) > LIMIT:
                raise Refused('invalid_input', 'Chrome message exceeds 1 MiB; read a smaller view.')
        line, self.buffer = self.buffer.split(b'\n', 1)
        message = strict_json_loads(line)
        # A late reply has come, here or in the daemon's loop between requests
        # (which passes it to on_event, where a message without an event does
        # nothing). Bridge.call drops it by its id.
        if type(message) is dict and not message.get('event') and self.late(message):
            self.given_up[message['id']] = None
        return message

    def late(self, message):
        """A reply to a command this bridge gave up on."""
        return type(message.get('id')) is str and message['id'] in self.given_up

    def wait(self, until):
        """Wait for the socket until `until`, or until a given-up reply is overdue.

        With neither, nothing waits here and recv's own socket bound applies, as
        before brief 28. GaveUp at `until`; at the overdue point a timeout, which
        closes the connection like the socket's own.
        """
        overdue = min((at for at in self.given_up.values() if at is not None), default=None)
        if until is None and overdue is None:
            return
        limit = min(at for at in (until, overdue) if at is not None)
        if select.select([self.connection], [], [], max(0, limit - time.monotonic()))[0]:
            return
        if overdue is not None and time.monotonic() >= overdue:
            raise TimeoutError('A Chrome command given up on never answered within the socket bound.')
        raise GaveUp()

    def give_up(self, identity, sent):
        self.given_up[identity] = sent + SOCKET_BOUND
        while len(self.given_up) > GIVEN_UP:
            self.given_up.popitem(last=False)

    def accept(self, connection, peer=None):
        if self.connection is not None:
            try:
                readable, _, _ = select.select([self.connection], [], [], 0)
                if not readable or self.connection.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT):
                    raise Refused('permission_denied', 'One native host already controls this Chrome session.')
            except BlockingIOError:
                raise Refused('permission_denied', 'One native host already controls this Chrome session.')
            self.close()
        self.connection, self.buffer = connection, b''
        self.given_up.clear()
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
        self.peer = peer

    def call(self, name, **arguments):
        if self.connection is None:
            raise Refused('chrome_unavailable', 'Chrome is not connected; open Chrome with the installed extension, then read again.')
        identity = uuid.uuid4().hex
        message = {'id':identity,'command':{'name':name,**arguments}}
        until = None
        if self.end is not None:
            left = int((self.end - time.monotonic()) * 1000)
            if left <= 0:
                raise Refused('expired', 'Time ran out before this command was sent; nothing was sent.')
            message['time_left_ms'] = left
            until = self.end + GRACE
        body = json.dumps(message,separators=(',',':')).encode() + b'\n'
        if len(body) > LIMIT:
            raise Refused('asking_input_too_large', 'Chrome command exceeds its wire bound; use a smaller input.')
        try:
            self.connection.sendall(body)
            sent = time.monotonic()
            assembled = bytearray()
            total = None
            event_error = None
            while True:
                try:
                    reply = self.read(until)
                except GaveUp:
                    self.give_up(identity, sent)
                    if event_error is not None:
                        raise Refused('unknown','A Chrome owner event could not be committed; inspect status and never replay an input.') from event_error
                    raise Refused('expired', "No answer came in this command's time; it was given up.") from None
                if reply.get('event'):
                    try:
                        self.on_event(reply)
                    except Exception as exc:
                        # Drain this command's own response before reporting the failed event commit.
                        # Otherwise its late response poisons the next command identity.
                        event_error = event_error or exc
                    continue
                if reply.get('id') != identity:
                    if self.late(reply):
                        continue  # dropped by its id
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
                    raise Refused(code if code in {'stale_reference','stale_approval','reload_required','owner_signin','refused','permission_denied','unknown','transport_error','expired'} else 'refused', visible(message.strip()))
                return reply['data']
        except (OSError, ValueError, binascii.Error, TypeError) as exc:
            self.close()
            raise Refused('transport_error', 'Chrome connection was cut off; the input may have run. Inspect operation status and never replay.') from exc

    def close(self):
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        self.session = self.version = self.connection_identity = self.peer = None
        self.buffer = b''
        self.given_up.clear()
