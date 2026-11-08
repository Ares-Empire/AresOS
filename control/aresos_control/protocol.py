"""Bounded JSON v1 frames; file streams acknowledge each offset before the next."""
import base64
from contextlib import contextmanager
import json
import socket

from .common import CHUNK_SIZE, WIRE_LIMIT, JSONInputError, Refused, display_json, sha256, strict_json_loads, digest
from .requests import changing

READ_TIMEOUT = 10
CHANGE_TIMEOUT = 30
ARCHIVE_TIMEOUT = 600


def receive(connection):
    buffer = bytearray()
    while len(buffer) <= WIRE_LIMIT:
        chunk = connection.recv(min(65536, WIRE_LIMIT + 1 - len(buffer)))
        if not chunk:
            raise Refused("transport_error", "Incomplete socket message; inspect operation_status before any new operation.")
        buffer.extend(chunk)
        if b"\n" in chunk:
            line, rest = bytes(buffer).split(b"\n", 1)
            if rest or len(line) > WIRE_LIMIT:
                break
            try:
                return strict_json_loads(line)
            except JSONInputError as exc:
                raise exc.for_actions(exc.values("action"))
    raise Refused("invalid_input", "Socket frame exceeds 6 MiB or contains extra messages; reduce the request.")


def send(connection, message, *, result=False):
    # Only results get presentation ordering. Requests must expose the caller's order.
    encoded = json.dumps(message, ensure_ascii=True, separators=(",", ":"), allow_nan=False) if not result else display_json(message)
    wire = (encoded + "\n").encode()
    if len(wire) > WIRE_LIMIT:
        raise Refused("invalid_input", "Socket frame too large; reduce the request.")
    connection.sendall(wire)


class Client:
    def __init__(self, socket_path):
        self.socket_path = str(socket_path)

    @contextmanager
    def connection(self, request=None):
        attempted = False
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                timeout = READ_TIMEOUT
                if request and changing(request):
                    timeout = ARCHIVE_TIMEOUT if request.get('action') == 'control_archive' else CHANGE_TIMEOUT
                connection.settimeout(timeout)
                connection.connect(self.socket_path)
                attempted = True
                yield connection
        except (OSError, Refused) as exc:
            if attempted and request and changing(request) and (isinstance(exc, OSError) or exc.code == 'transport_error'):
                # A timeout/EOF says nothing about commit. Give the caller a
                # stable, password-free request reference; never suggest retry.
                reference = {key: request[key] for key in ('method', 'action', 'app', 'sha256', 'export_id') if key in request}
                args = request.get('arguments', {})
                operation_id = args.get('operation_id')
                if operation_id:
                    reference['operation_id'] = operation_id
                    check = f'Check operation_status with operation_id {operation_id}.'
                else:
                    if request.get('method') == 'upload':
                        reference['sha256'] = request['file']['sha256']
                    if request.get('method') == 'mail_account_add':
                        reference['account_id'] = args.get('id')
                        check = 'Check mail_accounts and control_log for this account setup request.'
                    else:
                        check = 'Check control_pending, control_log and the recorded state for this request before any further change.'
                # Hash the actual request, omitting setup secrets entirely.
                reference['request_sha256'] = digest({k: v for k, v in request.items() if k != 'password'})
                raise UnknownRequest(reference, check) from exc
            if isinstance(exc, Refused):
                raise
            raise Refused("transport_error", "Service connection lost; inspect operation_status with the same id, never repeat with a new id.") from exc

    def request(self, request):
        try:
            with self.connection(request) as connection:
                send(connection, {"v": 1, **request})
                return receive(connection)
        except UnknownRequest as exc:
            return exc.result()

    def upload(self, app, file_ref, data):
        request = {"method": "upload", "app": app, "file": file_ref}
        try:
            return self._upload(request, data)
        except UnknownRequest as exc:
            return exc.result()

    def _upload(self, request, data):
        with self.connection(request) as connection:
            send(connection, {"v": 1, **request})
            result = receive(connection)
            if not result["ok"]:
                return result
            for offset in range(0, len(data), CHUNK_SIZE):
                chunk = data[offset:offset + CHUNK_SIZE]
                send(connection, {"offset": offset, "bytes": base64.b64encode(chunk).decode()})
                result = receive(connection)
                if not result["ok"]:
                    return result
                if result["data"] != {"offset": offset + len(chunk)}:
                    raise Refused("transport_error", "Unexpected upload acknowledgement; import again.")
            send(connection, {"end": True, "offset": len(data)})
            return receive(connection)

    def download(self, app, key, limit, export_id=None):
        request = {"method": "download", "app": app, "sha256": key}
        if export_id:
            request['export_id'] = export_id
        try:
            return self._download(request, limit)
        except UnknownRequest as exc:
            return exc.result(), None

    def _download(self, request, limit):
        key = request['sha256']
        with self.connection(request) as connection:
            request = {"v": 1, **request}
            send(connection, request)
            result = receive(connection)
            if not result["ok"]:
                return result, None
            admission = {k: result['data'][k] for k in ('export_id', 'other_holds')}
            size = result["data"]["size"]
            if type(size) is not int or not 0 <= size <= limit or result["data"]["sha256"] != key:
                raise Refused("file_refused", "Download exceeds the caller's limit or has wrong metadata; save refused.")
            data = bytearray()
            while len(data) < size:
                offset = len(data)
                send(connection, {"offset": offset})
                result = receive(connection)
                if not result["ok"]:
                    return result, None
                chunk = base64.b64decode(result["data"]["bytes"], validate=True)
                if result["data"]["offset"] != offset or not 0 < len(chunk) <= min(CHUNK_SIZE, size - offset):
                    raise Refused("file_refused", "Download chunks are out of order or oversized; save refused.")
                data.extend(chunk)
            send(connection, {"end": True, "offset": len(data)})
            result = receive(connection)
            if not result["ok"]:
                return result, None
            if sha256(data) != key:
                raise Refused("file_refused", "Download bytes differ from their hash; save refused.")
            result['data'].update(admission)
            return result, bytes(data)

    def call(self, name, arguments):
        return self.request({"method": "call", "action": name, "arguments": arguments})


class UnknownRequest(Refused):
    def __init__(self, reference, check):
        self.reference = reference
        super().__init__('unknown', 'Request outcome is unknown: the service may have committed after the reply was lost or timed out. '
                         + check + ' Do not repeat this request automatically.')

    def result(self):
        return {'ok': False, 'error': {'code': self.code, 'message': str(self)},
                'data': {'state': 'unknown', 'request': self.reference}, 'pending': {}}
