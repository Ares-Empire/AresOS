"""17e qualification instrument, NOT product code. No body/header/URL logging.

The SQLite ledger stores only synthetic case labels, hashes and state. Captured
bytes live only in bounded RAM. Approval releases the paused flow, never a URL.
"""
import asyncio
import contextlib
import dataclasses
import functools
import hashlib
import json
import os
import pathlib
import resource
import signal
import sqlite3
import time
import traceback
import uuid
from urllib.parse import urlsplit, parse_qs

from mitmproxy import addonmanager, ctx, http
from mitmproxy.proxy import commands, events
from mitmproxy.proxy.layers import http as http_layer
from mitmproxy.proxy.layers import websocket as ws_layer

ROOT = pathlib.Path(os.environ['CHECKPOINT_PRIVATE'])
MAX_BODY = 32 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
diagnostic_reserve = bytearray(65536)


def fatal(kind, error=None):
    global diagnostic_reserve
    diagnostic_reserve = None
    try:
        frames = traceback.extract_tb(error.__traceback__, limit=6) if error else []
        row = dict(kind=kind, error=type(error).__name__, frames=[dict(file=pathlib.Path(f.filename).name, function=f.name, line=f.lineno) for f in frames])
        with (ROOT/'fatal-events.jsonl').open('a') as stream:
            stream.write(json.dumps(row)+'\n')
    finally:
        os._exit(70)


@contextlib.contextmanager
def fatal_addon_error():
    # Upstream normally logs addon exceptions and continues. That behavior is
    # unsuitable for a send boundary, including failures outside our own hook.
    try:
        yield
    except BaseException as error:
        fatal('fatal-addon', error)


addonmanager.safecall = fatal_addon_error

original_body_size = http_layer.HttpStream.check_body_size
original_consume = http_layer.HttpStream.state_consume_request_body


def body_size(self, request):
    if request:
        declared = self.flow.request.headers.get('content-length')
        if declared is not None and int(declared) > MAX_BODY:
            self.flow.metadata['checkpoint_oversized'] = True
            return False
    return (yield from original_body_size(self, request))


def consume(self, event):
    if self.flow.metadata.get('checkpoint_oversized') and isinstance(event, http_layer.RequestData):
        # Drain rejected finite uploads without buffering or sending any byte
        # upstream. Chrome can otherwise leave fetch pending on an early close.
        yield from ()
    else:
        yield from original_consume(self, event)


http_layer.HttpStream.check_body_size = body_size
http_layer.HttpStream.state_consume_request_body = consume


def fail_closed(handler):
    # An addon exception normally gets logged and processing may continue. A
    # safety hook must kill its flow before returning control to mitmproxy.
    @functools.wraps(handler)
    async def wrapped(self, arg):
        try:
            return await handler(self, arg)
        except BaseException as error:
            flow = arg.flow if isinstance(arg, CheckpointFrameHook) else arg
            flow.kill()
            if isinstance(arg, CheckpointFrameHook):
                flow.metadata['checkpoint_frame_denied'] = True
            self.record('hook-failed-closed', error=type(error).__name__)
    return wrapped


@dataclasses.dataclass
class CheckpointFrameHook(commands.StartHook):
    flow: http.HTTPFlow
    data: bytes

    def args(self):
        return [self]


# mitmproxy 12.2.1's public websocket_end hook runs AFTER forwarding the close.
# This small pinned-core seam gates commands before the server socket write.
# TLS, HTTP/2, WS parsing/reassembly all remain in the upstream implementation.
original_relay = ws_layer.WebsocketLayer.relay_messages


def relay(self, event):
    gate = ctx.master.addons.get('checkpoint')
    if isinstance(event, events.DataReceived) and event.connection == self.context.client:
        self._checkpoint_size = getattr(self, '_checkpoint_size', 0) + len(event.data)
        if self._checkpoint_size > MAX_BODY:
            gate.record('refused', case=gate.case(self.flow), reason='ws-input-limit')
            yield commands.CloseConnection(self.context.server)
            yield commands.CloseConnection(self.context.client)
            return
    for command in original_relay(self, event):
        if isinstance(command, ws_layer.WebsocketMessageHook):
            yield command
            self._checkpoint_size = 0
        elif isinstance(command, commands.SendData) and command.connection == self.context.server:
            # Messages were held by websocket_message. Close, ping and pong have
            # no public pre-forward hook and are captured at this versioned seam.
            if command.data and (command.data[0] & 15) in (8, 9, 10):
                hook = CheckpointFrameHook(self.flow, bytes(command.data))
                yield hook
                if self.flow.metadata.pop('checkpoint_frame_denied', False):
                    yield commands.CloseConnection(self.context.server)
                    yield commands.CloseConnection(self.context.client)
                    return
            yield command
        else:
            yield command


ws_layer.WebsocketLayer.relay_messages = relay


class Checkpoint:
    name = 'checkpoint'

    def __init__(self):
        ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db = sqlite3.connect(ROOT / 'ledger.sqlite')
        self.db.execute('pragma journal_mode=WAL')
        self.db.execute('pragma synchronous=FULL')
        self.db.execute('create table if not exists state (key text primary key, value text)')
        self.db.execute('create table if not exists operations (id text primary key, info text, status text)')
        self.db.execute('create table if not exists quota_probe (padding blob)')
        self.db.execute("insert or ignore into state values ('guard','false')")
        # A consumed operation might have reached the peer. Never retry either
        # that operation or a pending operation whose RAM bytes died with us.
        self.db.execute("update operations set status=case when status='consumed' then 'unknown' else 'lost' end where status in ('consumed','held')")
        self.db.commit()
        self.guard = json.loads(self.db.execute("select value from state where key='guard'").fetchone()[0])
        self.context = 0
        self.pending = {}
        self.tokens = set()
        self.total = 0
        self.fault = None
        self.stall = None

    def record(self, event, **fields):
        operation_kind = fields.pop('kind', None)
        if operation_kind:
            fields['operationKind'] = operation_kind
        with (ROOT / 'events.jsonl').open('a') as f:
            f.write(json.dumps(dict(kind=event, at=time.time()*1000, **fields))+'\n')

    def case(self, flow):
        value = parse_qs(urlsplit(flow.request.pretty_url).query).get('case', [''])[0]
        return value if value.startswith('e-') and len(value) < 100 else 'unlabelled'

    def rows(self):
        return [dict(id=r[0], **json.loads(r[1]), status=r[2]) for r in self.db.execute('select * from operations')]

    async def running(self):
        asyncio.get_running_loop().set_exception_handler(lambda loop, context: fatal('fatal-loop', context.get('exception')))
        socket = ROOT / 'control.sock'
        socket.unlink(missing_ok=True)
        self.server = await asyncio.start_unix_server(self.control, path=socket)
        os.chmod(socket, 0o660)
        self.record('ready', guard=self.guard, addressSpaceLimit=resource.getrlimit(resource.RLIMIT_AS)[0], recovered=self.rows())

    async def control(self, reader, writer):
        try:
            p = json.loads(await reader.readline())
            action = p['action']
            if action == 'guard':
                self.db.execute("update state set value=? where key='guard'", (json.dumps(p['enabled']),))
                self.db.commit()
                self.guard = p['enabled']
                self.record('barrier', enabled=self.guard)
                result = dict(guard=self.guard, at=time.time()*1000)
            elif action == 'context':
                self.context += 1
                self.tokens = set(p.get('tokens', []))
                result = dict(context=self.context)
            elif action == 'approve':
                op = self.pending.get(p['id'])
                if not op or op['future'].done():
                    raise ValueError('NOT_PENDING')
                if op['context'] != self.context:
                    raise ValueError('CONTEXT_CHANGED')
                op['future'].set_result(True)
                result = dict(accepted=True)
            elif action == 'cancel':
                op = self.pending.get(p['id'])
                if op and not op['future'].done():
                    op['future'].set_result(False)
                result = dict(cancelled=bool(op))
            elif action == 'fault':
                self.fault = p.get('point')
                if self.fault == 'ledger-full':
                    pages = self.db.execute('pragma page_count').fetchone()[0]
                    self.db.execute(f'pragma max_page_count={pages}')
                else:
                    self.db.execute('pragma max_page_count=1073741823')
                result = dict(fault=self.fault)
            elif action == 'stall':
                self.stall = p.get('point')
                result = dict(stall=self.stall)
            elif action == 'state':
                result = dict(guard=self.guard, context=self.context, buffered=self.total, rows=self.rows())
            elif action == 'exhaust-memory':
                try:
                    bytearray(1024*1024*1024)
                except MemoryError:
                    self.record('memory-refusal')
                    os.kill(os.getpid(), signal.SIGKILL)
                raise RuntimeError('memory ceiling did not hold')
            else:
                raise ValueError('UNKNOWN_COMMAND')
            writer.write(json.dumps(dict(result=result)).encode()+b'\n')
        except Exception as e:
            writer.write(json.dumps(dict(error=str(e))).encode()+b'\n')
        await writer.drain()
        writer.close()

    def status(self, oid, state):
        self.db.execute('update operations set status=? where id=?', (state, oid))
        self.db.commit()
        self.record(state, id=oid)

    async def hold(self, flow, kind, data):
        if not self.guard:
            return True
        oid = uuid.uuid4().hex
        # Supporting attribution never changes whether an operation is held.
        token = flow.metadata.get('attribution', '')
        origin = flow.request.headers.get('origin')
        info = dict(case=self.case(flow), kind=kind, capturedAt=time.time()*1000, originState='absent' if origin is None else 'opaque' if origin == 'null' else 'present', length=len(data), sha256=hashlib.sha256(data).hexdigest(), context=self.context, attribution='current' if token in self.tokens else 'uncertain')
        if kind in ('http', 'handshake'):
            info['bodySha256'] = flow.metadata.get('captured_body_hash')
            info['method'] = flow.request.method
        if kind == 'ws-control' and flow.websocket.close_reason is not None:
            info['payloadSha256'] = hashlib.sha256(flow.websocket.close_reason.encode()).hexdigest()
        if len(self.pending) >= 256 or self.total+len(data) > MAX_TOTAL or len(data) > MAX_BODY:
            self.record('refused', **info, reason='buffer-limit')
            return False
        future = asyncio.get_running_loop().create_future()
        op = dict(future=future, context=self.context, flow=flow, **{'info':info})
        try:
            if self.fault == 'ledger-full':
                # Exercise SQLite's real disk-full error without filling the
                # runner filesystem or logging/writing any captured payload.
                self.db.execute('insert into quota_probe values (zeroblob(1048576))')
            self.db.execute('insert into operations values (?,?,?)', (oid, json.dumps(info), 'held'))
            self.db.commit()
        except sqlite3.Error as error:
            self.db.rollback()
            self.record('refused', **info, reason='ledger-unavailable', sqliteError=getattr(error, 'sqlite_errorname', 'unknown'))
            return False
        self.pending[oid] = op
        flow.metadata.setdefault('checkpoint_operations', []).append(oid)
        self.total += len(data)
        self.record('held', id=oid, **info)
        try:
            decision = await asyncio.wait_for(future, 90)
            if not decision or op['context'] != self.context or flow.client_conn.timestamp_end:
                self.status(oid, 'cancelled')
                return False
            if self.fault == 'before-consume':
                os.kill(os.getpid(), signal.SIGKILL)
            while self.stall == 'before-consume':
                await asyncio.sleep(.02)
            if op['context'] != self.context or flow.client_conn.timestamp_end:
                self.status(oid, 'cancelled')
                return False
            self.status(oid, 'consumed')
            if self.fault == 'after-consume':
                os.kill(os.getpid(), signal.SIGKILL)
            while self.stall == 'after-consume':
                await asyncio.sleep(.02)
            if op['context'] != self.context or flow.client_conn.timestamp_end:
                self.status(oid, 'cancelled')
                return False
            return True
        except (asyncio.TimeoutError, asyncio.CancelledError):
            self.status(oid, 'cancelled')
            return False
        except sqlite3.Error:
            return False
        finally:
            self.total -= len(data)
            self.pending.pop(oid, None)
            # Waiting flows retain only the operation currently being captured.

    def requestheaders(self, flow):
        if self.fault == 'addon-dispatch':
            self.record('fatal-addon-test', case=self.case(flow))
            raise RuntimeError('deliberate unwrapped addon exception')
        flow.request.stream = False
        flow.metadata['attribution'] = flow.request.headers.pop('x-ares-check', '')
        declared = flow.request.headers.get('content-length')
        if declared is not None and int(declared) > MAX_BODY:
            self.record('refused', case=self.case(flow), reason='declared-body-limit', limit=MAX_BODY)
            flow.metadata['checkpoint_oversized'] = True
            flow.response = http.Response.make(413, b'Checkpoint: operation exceeds 32 MiB limit')
            return
        # Reject a page's arbitrary CONNECT tunnel. Chrome's outer CONNECT is
        # handled by the proxy before this decrypted HTTP request hook.
        if flow.request.method == 'CONNECT':
            flow.response = http.Response.make(403, b'Unsupported tunnel')

    @fail_closed
    async def request(self, flow):
        if flow.metadata.get('checkpoint_oversized'):
            flow.response = http.Response.make(413, b'Checkpoint: operation exceeds 32 MiB limit')
            return
        if flow.response:
            return
        if flow.request.host.endswith(('.googleapis.com', '.google.com')):
            self.record('service-traffic', host=flow.request.host, method=flow.request.method, guarded=self.guard)
        body = flow.request.raw_content
        if body is None:
            flow.response = http.Response.make(413, b'Incomplete operation refused')
            return
        # Hash covers actual request fields and body. Approval identifies the
        # immutable flow, not this hash; identical competitors have separate IDs.
        captured = (flow.request.method+' '+flow.request.url+'\n').encode()+bytes(flow.request.headers)+b'\n'+body
        flow.metadata['captured_body_hash'] = hashlib.sha256(body).hexdigest()
        if not await self.hold(flow, 'handshake' if flow.request.headers.get('upgrade','').lower() == 'websocket' else 'http', captured):
            flow.response = http.Response.make(409, b'Checkpoint refused or cancelled')

    @fail_closed
    async def websocket_message(self, flow):
        message = flow.websocket.messages[-1]
        if message.from_client and not await self.hold(flow, 'ws-message', message.content):
            message.drop()
        # mitmproxy normally retains every message for its UI. This headless
        # check retains only the current one, consumed synchronously by the layer.
        flow.websocket.messages[:] = [message]

    @fail_closed
    async def checkpoint_frame(self, hook):
        if not await self.hold(hook.flow, 'ws-control', hook.data):
            hook.flow.metadata['checkpoint_frame_denied'] = True

    def error(self, flow):
        for oid, op in list(self.pending.items()):
            if op['flow'] is flow and not op['future'].done():
                op['future'].set_result(False)
                self.record('observed-cancellation', id=oid)

    def tls_failed_client(self, data):
        error = (getattr(data.conn, 'error', '') or '').lower()
        category = 'certificate' if any(s in error for s in ['unknown ca', 'bad certificate', 'certificate unknown', 'certificate verify']) else 'disconnect' if any(s in error for s in ['closed', 'disconnect', 'eof']) else 'other'
        self.record('client-tls-failure', host=data.context.client.sni, category=category)

    def tls_failed_server(self, data):
        self.record('upstream-tls-failure', host=data.context.server.sni)

    def response(self, flow):
        if flow.request.host.endswith(('.googleapis.com', '.google.com')):
            self.record('service-response', host=flow.request.host, status=flow.response.status_code)
        # A response is evidence of a response, not business success.
        for row in self.rows():
            if row['status'] == 'consumed' and row['id'] in flow.metadata.get('checkpoint_operations', []):
                self.status(row['id'], 'response')

    def done(self):
        self.db.close()


addons = [Checkpoint()]
