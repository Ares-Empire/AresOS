"""One bounded newline-delimited JSON v1 request/response per Unix connection."""
import json
import socket

from .common import WIRE_LIMIT, Refused, canonical


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

    def request(self, request):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(10)
                connection.connect(self.socket_path)
                send(connection, {"v": 1, **request})
                return receive(connection)
        except OSError as exc:
            raise Refused("transport_error", "Service connection lost; inspect operation_status with the same id, never repeat with a new id.") from exc

    def call(self, name, arguments):
        return self.request({"method": "call", "action": name, "arguments": arguments})
