"""Bounded JSON v1 frames; file streams acknowledge each offset before the next."""
import base64
from contextlib import contextmanager
import json
import socket

from .common import CHUNK_SIZE, WIRE_LIMIT, Refused, canonical, sha256


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
                return json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise Refused("invalid_input", "Malformed JSON; use a single version-1 request.") from exc
    raise Refused("invalid_input", "Socket frame exceeds 6 MiB or contains extra messages; reduce the request.")


def send(connection, message):
    wire = (canonical(message) + "\n").encode()
    if len(wire) > WIRE_LIMIT:
        raise Refused("invalid_input", "Socket frame too large; reduce the request.")
    connection.sendall(wire)


class Client:
    def __init__(self, socket_path):
        self.socket_path = str(socket_path)

    @contextmanager
    def connection(self):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(10)
                connection.connect(self.socket_path)
                yield connection
        except OSError as exc:
            raise Refused("transport_error", "Service connection lost; inspect operation_status with the same id, never repeat with a new id.") from exc

    def request(self, request):
        with self.connection() as connection:
            send(connection, {"v": 1, **request})
            return receive(connection)

    def upload(self, app, file_ref, data):
        with self.connection() as connection:
            send(connection, {"v": 1, "method": "upload", "app": app, "file": file_ref})
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

    def download(self, app, key, limit):
        with self.connection() as connection:
            send(connection, {"v": 1, "method": "download", "app": app, "sha256": key})
            result = receive(connection)
            if not result["ok"]:
                return result, None
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
            return result, bytes(data)

    def call(self, name, arguments):
        return self.request({"method": "call", "action": name, "arguments": arguments})
