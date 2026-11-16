#!/usr/bin/python3
"""DEVELOPMENT AID for run-hub.sh --session: makes the preview's window cover the screen, and says when it closes.

usage: preview-window.py <ready-file>
       preview-window.py --close <app-id> [--display <wayland-socket>]
       preview-window.py --outputs [--display <wayland-socket>]

Talks to the desktop the preview runs on ($WAYLAND_DISPLAY, the owner's own session) through the wlr
foreign-toplevel protocol, which labwc offers. It lists the windows that exist, then creates <ready-file>; run-hub.sh
starts the nested labwc only after that. The first window that appears afterwards with the app ID "labwc" (the
nested labwc's output window, "labwc - WL-1") is asked to go fullscreen, as far as that desktop allows. When that window
closes (Alt+F4 on it reaches the outer desktop, which closes it), this exits 0 so run-hub.sh stops the preview.

Exit codes: 0 the preview window closed; 3 the desktop does not offer the protocol (the preview stays an ordinary
window); 4 the connection to the desktop ended.

--close and --outputs act on the preview's own labwc, never on the owner's session: the compositor is --display or
else $WAYLAND_DISPLAY (run-hub.sh gives both as the preview's), and wayland-0 is refused with exit 2, whichever way it
is given. Once package 23 is installed, the owner's real game window has the same app ID as the preview's game.

With --close it asks that compositor to close every window with that app ID, as its close button would: the game then
saves its world and quits. Exit 0 when it asked at least one window, 1 when there was none.

With --outputs it waits until that compositor has had a screen and has none left, then exits 0: the preview's window on
the owner's desktop is gone (the nested labwc outlives it, without a screen). That ends the run also when the watcher
above never found the preview's window. Exit 4 when the compositor itself ended.

Standard library only.
"""
import os
import socket
import struct
import sys
import time

MANAGER = 'zwlr_foreign_toplevel_manager_v1'
# set_fullscreen came with version 2 of the protocol.
FULLSCREEN_SINCE = 2
NESTED_APP_ID = 'labwc'
# The owner's own session: --close and --outputs never act on it.
OWNER_DISPLAY = 'wayland-0'


class Closed(Exception):
    pass


class Client:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(path)
        self.buffer = bytearray()
        self.next_id = 2
        self.kinds = {1: 'display'}
        self.globals = {}
        self.callbacks = set()
        self.app_ids = {}
        self.ready = False
        self.new_after_ready = set()
        self.preview = None
        self.preview_closed = False
        self.registry = self.new('registry')
        self.send(1, 1, struct.pack('=I', self.registry))

    def new(self, kind):
        object_id = self.next_id
        self.next_id += 1
        self.kinds[object_id] = kind
        return object_id

    def send(self, object_id, opcode, payload=b''):
        self.sock.sendall(struct.pack('=II', object_id, ((8 + len(payload)) << 16) | opcode) + payload)

    @staticmethod
    def string(value):
        data = value.encode('utf-8') + b'\0'
        return struct.pack('=I', len(data)) + data + b'\0' * (-len(data) % 4)

    @staticmethod
    def read_string(payload, offset):
        """The string at offset, and the offset after it."""
        (length,) = struct.unpack_from('=I', payload, offset)
        offset += 4
        if length == 0:
            return None, offset
        return payload[offset:offset + length - 1].decode('utf-8', 'replace'), offset + length + (-length % 4)

    def roundtrip(self):
        callback = self.new('callback')
        self.callbacks.add(callback)
        self.send(1, 0, struct.pack('=I', callback))
        while callback in self.callbacks:
            self.receive()

    def receive(self):
        data = self.sock.recv(65536)
        if not data:
            raise Closed('the desktop closed the connection')
        self.buffer += data
        while len(self.buffer) >= 8:
            object_id, word = struct.unpack_from('=II', self.buffer)
            size, opcode = word >> 16, word & 0xffff
            if size < 8 or size % 4:
                raise Closed('invalid message from the desktop')
            if len(self.buffer) < size:
                return
            payload = bytes(self.buffer[8:size])
            del self.buffer[:size]
            self.dispatch(object_id, opcode, payload)

    def bind_manager(self):
        offered = next(((name, version) for name, (interface, version) in self.globals.items()
                        if interface == MANAGER), None)
        if offered is None or offered[1] < FULLSCREEN_SINCE:
            return False
        manager = self.new('manager')
        self.send(self.registry, 0, struct.pack('=I', offered[0]) + self.string(MANAGER)
                  + struct.pack('=II', min(offered[1], 3), manager))
        return True

    def dispatch(self, object_id, opcode, payload):
        kind = self.kinds.get(object_id)
        if kind == 'display' and opcode == 0:
            (_, code) = struct.unpack_from('=II', payload)
            raise Closed(f'desktop error {code}: {self.read_string(payload, 8)[0]}')
        if kind == 'registry' and opcode == 0:
            (name,) = struct.unpack_from('=I', payload)
            interface, offset = self.read_string(payload, 4)
            (version,) = struct.unpack_from('=I', payload, offset)
            self.globals[name] = (interface, version)
        elif kind == 'registry' and opcode == 1:
            (name,) = struct.unpack_from('=I', payload)
            self.globals.pop(name, None)
        elif kind == 'callback':
            self.callbacks.discard(object_id)
            self.kinds.pop(object_id, None)
        elif kind == 'manager' and opcode == 0:
            (handle,) = struct.unpack_from('=I', payload)
            self.kinds[handle] = 'toplevel'
            if self.ready:
                self.new_after_ready.add(handle)
        elif kind == 'manager' and opcode == 1:
            raise Closed(MANAGER + ' finished')
        elif kind == 'toplevel':
            if opcode == 1:
                self.app_ids[object_id] = self.read_string(payload, 0)[0]
            elif opcode == 5 and self.preview is None and object_id in self.new_after_ready \
                    and self.app_ids.get(object_id) == NESTED_APP_ID:
                self.preview = object_id
                # set_fullscreen with no output: the desktop picks the screen the window is on.
                self.send(object_id, 8, struct.pack('=I', 0))
                say('asked the desktop to show the preview fullscreen')
            elif opcode == 6:
                self.kinds.pop(object_id, None)
                self.send(object_id, 7)  # destroy
                if object_id == self.preview:
                    self.preview_closed = True


def say(message):
    print(f'preview-window.py: {message}', file=sys.stderr, flush=True)


def close(path, app_id):
    """Asks the compositor to close every window with this app ID; True when there was one."""
    client = Client(path)
    client.roundtrip()
    if not client.bind_manager():
        say(f'the compositor does not offer {MANAGER}')
        return False
    client.roundtrip()  # the windows
    client.roundtrip()  # their app IDs and first done events
    handles = [handle for handle, value in client.app_ids.items() if value == app_id and handle in client.kinds]
    for handle in handles:
        client.send(handle, 5)
    client.roundtrip()
    say(f'asked {len(handles)} window(s) with app ID {app_id!r} to close')
    return bool(handles)


def no_output_left(path):
    """Waits until the compositor has had a screen and has none left, then returns."""
    client = Client(path)
    client.roundtrip()
    seen = False
    while True:
        if any(interface == 'wl_output' for interface, _ in client.globals.values()):
            seen = True
        elif seen:
            return
        client.receive()


def socket_path(display):
    return display if os.path.isabs(display) else os.path.join(os.environ.get('XDG_RUNTIME_DIR', ''), display)


def on_the_preview(argv):
    """--close <app-id> or --outputs, each with an optional --display, on the preview's own labwc."""
    mode, rest = argv[1], argv[2:]
    app_id = None
    if mode == '--close':
        if not rest or rest[0].startswith('--'):
            say(USAGE)
            return 2
        app_id, rest = rest[0], rest[1:]
    display = os.environ.get('WAYLAND_DISPLAY')
    if len(rest) == 2 and rest[0] == '--display':
        display, rest = rest[1], []
    if rest:
        say(USAGE)
        return 2
    if not display:
        say('WAYLAND_DISPLAY is not set')
        return 3
    if os.path.basename(display.rstrip('/')) == OWNER_DISPLAY:
        say(f"refusing {display}: {mode} acts only on the preview's own labwc, never on the owner's session")
        return 2
    try:
        if mode == '--outputs':
            no_output_left(socket_path(display))
            say("the preview's labwc has no screen left")
            return 0
        return 0 if close(socket_path(display), app_id) else 1
    except (OSError, Closed) as error:
        say(f'lost the compositor: {error}')
        return 4


USAGE = 'usage: preview-window.py <ready-file> | --close <app-id> [--display <socket>] | --outputs [--display <socket>]'


def main(argv):
    if len(argv) >= 2 and argv[1] in ('--close', '--outputs'):
        return on_the_preview(argv)
    if len(argv) != 2 or argv[1].startswith('--'):
        say(USAGE)
        return 2
    display = os.environ.get('WAYLAND_DISPLAY')
    if not display:
        say('WAYLAND_DISPLAY is not set')
        return 3
    path = socket_path(display)
    try:
        client = Client(path)
        client.roundtrip()
        if not client.bind_manager():
            say(f'this desktop does not offer {MANAGER} version {FULLSCREEN_SINCE}; the preview stays a window')
            return 3
        client.roundtrip()  # the windows that exist now
        client.ready = True
        with open(argv[1], 'x'):
            pass
        warned = False
        started = time.monotonic()
        client.sock.settimeout(5)
        while not client.preview_closed:
            try:
                client.receive()
            except socket.timeout:
                if client.preview is None and not warned and time.monotonic() - started > 30:
                    say('no preview window appeared within 30 s; it is not shown fullscreen')
                    warned = True
    except (OSError, Closed) as error:
        say(f'lost the desktop: {error}')
        return 4
    say('the preview window was closed')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
