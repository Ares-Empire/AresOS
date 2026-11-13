"""Small test-only Wayland client; refuses the owner's runtime/display.

Uses virtual-keyboard, virtual-pointer and foreign-toplevel protocols on the
private headless compositor, with the system xkbcommon library for its keymap.
"""
import array
import ctypes
import os
from pathlib import Path
import select
import socket
import struct
import time


def uints(*values):
    return struct.pack('=' + 'I' * len(values), *values)


def string(value):
    data = value.encode() + b'\0'
    return uints(len(data)) + data + b'\0' * (-len(data) % 4)


class Input:
    def __init__(self):
        runtime = Path(os.environ['XDG_RUNTIME_DIR']).resolve()
        assert runtime.is_relative_to(Path(__file__).resolve().parents[2] / '.work/31-window-frame')
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(str(runtime / os.environ['WAYLAND_DISPLAY']))
        self.buffer = b''
        self.next_id = 3
        self.globals = {}
        self.windows = {}
        self.send(1, 1, uints(2))  # wl_display.get_registry
        self.roundtrip()
        self.bind('wl_seat', 4, 1)
        self.bind('zwp_virtual_keyboard_manager_v1', 5, 1)
        self.bind('zwlr_virtual_pointer_manager_v1', 6, 1)
        self.send(5, 0, uints(4, 7))  # create_virtual_keyboard
        self.bind('zwlr_foreign_toplevel_manager_v1', 8, 3)
        self.send(6, 0, uints(4, 9))  # create_virtual_pointer
        self.next_id = 10
        self.keymap()
        self.roundtrip()

    def send(self, obj, opcode, data=b'', fd=None):
        message = uints(obj, ((8 + len(data)) << 16) | opcode) + data
        ancillary = [] if fd is None else [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [fd]))]
        self.sock.sendmsg([message], ancillary)

    def bind(self, interface, obj, version):
        name, supported = self.globals[interface]
        self.send(2, 0, uints(name) + string(interface) + uints(min(version, supported), obj))

    def events(self, timeout=0.1):
        if select.select([self.sock], [], [], timeout)[0]:
            data = self.sock.recv(65536)
            if not data:
                raise RuntimeError('Wayland display disconnected')
            self.buffer += data
        while len(self.buffer) >= 8:
            obj, header = struct.unpack_from('=II', self.buffer)
            size, opcode = header >> 16, header & 65535
            if len(self.buffer) < size:
                break
            data = self.buffer[8:size]
            self.buffer = self.buffer[size:]
            if obj == 1 and opcode == 0:
                raise RuntimeError('Wayland protocol error: ' + repr(data))
            if obj == 2 and opcode == 0:
                name, length = struct.unpack_from('=II', data)
                interface = data[8:8 + length - 1].decode()
                version, = struct.unpack_from('=I', data, 8 + ((length + 3) & ~3))
                self.globals[interface] = (name, version)
            if obj == 8 and opcode == 0:
                window, = struct.unpack('=I', data)
                self.windows[window] = {}
            if obj in self.windows:
                if opcode in (0, 1):
                    length, = struct.unpack_from('=I', data)
                    self.windows[obj]['title' if opcode == 0 else 'app_id'] = data[4:4 + length - 1].decode()
                elif opcode == 6:
                    del self.windows[obj]
            if obj == getattr(self, 'sync', None) and opcode == 0:
                self.synced = True

    def roundtrip(self):
        self.sync = self.next_id
        self.next_id += 1
        self.synced = False
        self.send(1, 0, uints(self.sync))
        deadline = time.monotonic() + 5
        while not self.synced:
            assert time.monotonic() < deadline, 'Wayland sync timed out'
            self.events()

    def keymap(self):
        lib = ctypes.CDLL('libxkbcommon.so.0')
        lib.xkb_context_new.argtypes = [ctypes.c_int]
        lib.xkb_context_new.restype = ctypes.c_void_p
        lib.xkb_keymap_new_from_names.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        lib.xkb_keymap_new_from_names.restype = ctypes.c_void_p
        lib.xkb_keymap_get_as_string.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.xkb_keymap_get_as_string.restype = ctypes.c_char_p
        context = lib.xkb_context_new(0)
        keymap = lib.xkb_keymap_new_from_names(context, None, 0)
        data = lib.xkb_keymap_get_as_string(keymap, 1) + b'\0'
        fd = os.memfd_create('pkg31-keymap')
        try:
            os.write(fd, data)
            self.send(7, 0, uints(1, len(data)), fd)
        finally:
            os.close(fd)

    def modifiers(self, mask):
        self.send(7, 2, uints(mask, 0, 0, 0))
        self.roundtrip()

    def key(self, code):
        for state in (1, 0):
            self.send(7, 1, uints(int(time.monotonic() * 1000) & 0xffffffff, code, state))
            self.roundtrip()

    def move(self, x, y):
        self.send(9, 1, uints(int(time.monotonic() * 1000) & 0xffffffff, x, y, 1920, 1080))
        self.send(9, 4)
        self.roundtrip()

    def button(self, state):
        self.send(9, 2, uints(int(time.monotonic() * 1000) & 0xffffffff, 272, state))
        self.send(9, 4)
        self.roundtrip()

    def drag(self, x, y, target_x, target_y):
        self.move(x, y)
        self.button(1)
        time.sleep(0.1)
        for step in range(1, 11):
            self.move(round(x + (target_x - x) * step / 10), round(y + (target_y - y) * step / 10))
            time.sleep(0.03)
        self.button(0)
        time.sleep(0.4)

    def activate(self, app_id):
        self.roundtrip()
        obj, = [obj for obj, props in self.windows.items() if props.get('app_id') == app_id]
        self.send(obj, 4, uints(4))
        self.roundtrip()
        time.sleep(0.3)
