"""Bounded JSON frames on a dedicated byte stream, never a terminal."""
import base64
import hashlib
import json

MAX_FRAME = 4 * 1024 * 1024


class Frames:
    def __init__(self, read):
        self.read = read
        self.buffer = bytearray()

    def receive(self):
        while b'\n' not in self.buffer:
            chunk = self.read(65536)
            if not chunk:
                raise EOFError('Check channel closed before a complete frame')
            self.buffer.extend(chunk)
            if len(self.buffer) > MAX_FRAME:
                raise ValueError('Check channel frame exceeds limit')
        line, _, rest = self.buffer.partition(b'\n')
        self.buffer = bytearray(rest)
        return json.loads(line)


def frame(value):
    data = json.dumps(value, separators=(',', ':')).encode() + b'\n'
    if len(data) > MAX_FRAME:
        raise ValueError('Check channel frame exceeds limit')
    return data


def export_bytes(raw):
    return dict(base64=base64.b64encode(raw).decode(), sha256=hashlib.sha256(raw).hexdigest())


def import_bytes(value):
    raw = base64.b64decode(value['base64'], validate=True)
    if hashlib.sha256(raw).hexdigest() != value['sha256']:
        raise ValueError('Guest export checksum mismatch')
    return raw
