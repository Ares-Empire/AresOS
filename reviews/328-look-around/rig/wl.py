# Package 328 rig: a minimal Wayland wire client, standard library only. Used by probe.py and vinput.py.
# It connects only to the rig's own compositor (the env file the rig writes) and refuses the owner's wayland-0.
import array
import os
import socket
import struct


def rig_env(rig):
    env = dict(line.strip().split('=', 1) for line in open(os.path.join(rig, 'env')) if '=' in line)
    if env.get('WAYLAND_DISPLAY', 'wayland-0') == 'wayland-0':
        raise SystemExit('refusing: the rig has no Wayland display of its own')
    return env


def string(value):
    data = value.encode() + b'\0'
    return struct.pack('=I', len(data)) + data + b'\0' * (-len(data) % 4)


def read_string(payload, offset):
    (length,) = struct.unpack_from('=I', payload, offset)
    text = payload[offset + 4:offset + 4 + length - 1].decode(errors='replace')
    return text, offset + 4 + length + (-length % 4)


def fixed(value):
    return value / 256.0


class Connection:
    def __init__(self, display):
        if display == 'wayland-0':
            raise SystemExit('refusing wayland-0')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(os.path.join(os.environ['XDG_RUNTIME_DIR'], display))
        self.next_id = 2
        self.buf = bytearray()
        self.fds = []
        self.handlers = {}
        self.globals = {}
        self.done = set()
        self.registry = self.new(self._registry_event)
        self.send(1, 1, struct.pack('=I', self.registry))
        self.roundtrip()

    def new(self, handler=None):
        obj = self.next_id
        self.next_id += 1
        if handler is not None:
            self.handlers[obj] = handler
        return obj

    def send(self, obj, op, payload=b'', fds=()):
        msg = struct.pack('=II', obj, ((8 + len(payload)) << 16) | op) + payload
        if fds:
            self.sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', fds))])
        else:
            self.sock.sendall(msg)

    def _registry_event(self, op, payload):
        if op == 0:
            (name,) = struct.unpack_from('=I', payload)
            interface, offset = read_string(payload, 4)
            (version,) = struct.unpack_from('=I', payload, offset)
            self.globals[interface] = (name, version)

    def bind(self, interface, version, handler=None):
        name, offered = self.globals[interface]
        obj = self.new(handler)
        self.send(self.registry, 0, struct.pack('=I', name) + string(interface)
                  + struct.pack('=II', min(version, offered), obj))
        return obj

    def read(self):
        data, ancdata, _, _ = self.sock.recvmsg(65536, socket.CMSG_SPACE(16 * 4))
        if not data:
            raise SystemExit('compositor closed the connection')
        for level, kind, extra in ancdata:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                fds = array.array('i')
                fds.frombytes(extra[:len(extra) - len(extra) % fds.itemsize])
                self.fds.extend(fds)
        self.buf.extend(data)
        while len(self.buf) >= 8:
            obj, word = struct.unpack_from('=II', self.buf)
            size, op = word >> 16, word & 0xffff
            if len(self.buf) < size:
                break
            payload = bytes(self.buf[8:size])
            del self.buf[:size]
            if obj == 1 and op == 0:
                raise SystemExit('wayland error: ' + repr(payload))
            handler = self.handlers.get(obj)
            if handler is not None:
                handler(op, payload)

    def roundtrip(self):
        cb = self.new()
        self.handlers[cb] = lambda op, payload: self.done.add(cb)
        self.send(1, 0, struct.pack('=I', cb))
        while cb not in self.done:
            self.read()
        self.done.discard(cb)
