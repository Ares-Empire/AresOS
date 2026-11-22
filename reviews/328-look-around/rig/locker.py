#!/usr/bin/python3
# Package 328 rig: labwc's half of the leak without Xwayland or the game. A Wayland window with the desktop's
# app_id (so the image's rules make it maximized and always on bottom, below the probe) locks the pointer with a
# position hint at its centre, the way Xwayland's warp emulation does for a captured game, and then drops the lock.
"""usage: locker.py <rig>

After its first click, while it has the keyboard, it sends lock_pointer with set_cursor_position_hint(centre), waits for
locked, holds the lock half a second, destroys it, and writes "dropped" to <rig>/locker.log. It then stays inert.
With HOLD=1 in its environment it keeps the lock instead."""
import mmap
import os
import selectors
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wl  # noqa: E402

rig = sys.argv[1]
env = wl.rig_env(rig)
conn = wl.Connection(env['WAYLAND_DISPLAY'])
log = open(os.path.join(rig, 'locker.log'), 'a', buffering=1)
start = time.monotonic()


def note(text):
    log.write(f'{time.monotonic() - start:8.3f} {text}\n')


state = dict(size=None, keyboard=False, locked=False, phase='waiting')
surface = pointer = keyboard = locked_pointer = None


def pointer_event(op, payload):
    if op == 0:
        note(f'pointer ENTER {wl.fixed(struct.unpack_from("=i", payload, 8)[0]):.0f},'
             f'{wl.fixed(struct.unpack_from("=i", payload, 12)[0]):.0f}')
    elif op == 1:
        note('pointer LEAVE')
    elif op == 3:
        down = struct.unpack_from('=I', payload, 12)[0]
        state['clicked'] = state.get('clicked') or not down
        note('pointer BUTTON ' + ('down' if down else 'up'))


def keyboard_event(op, payload):
    while conn.fds:
        os.close(conn.fds.pop())
    if op == 1:
        state['keyboard'] = True
        note('keyboard ENTER')
    elif op == 2:
        state['keyboard'] = False
        note('keyboard LEAVE')


def seat_event(op, payload):
    global pointer, keyboard
    if op == 0:
        (caps,) = struct.unpack_from('=I', payload)
        if caps & 1 and pointer is None:
            pointer = conn.new(pointer_event)
            conn.send(seat, 0, struct.pack('=I', pointer))
        if caps & 2 and keyboard is None:
            keyboard = conn.new(keyboard_event)
            conn.send(seat, 1, struct.pack('=I', keyboard))


def lock_event(op, payload):
    if op == 0:
        state['locked'] = True
        note('LOCKED')
    elif op == 1:
        state['locked'] = False
        note('UNLOCKED')


compositor = conn.bind('wl_compositor', 4)
shm = conn.bind('wl_shm', 1)
wm_base = conn.bind('xdg_wm_base', 2, lambda op, payload: op == 0 and conn.send(wm_base, 3, payload[:4]))
seat = conn.bind('wl_seat', 5, seat_event)
constraints = conn.bind('zwp_pointer_constraints_v1', 1)
surface = conn.new()
conn.send(compositor, 0, struct.pack('=I', surface))


def attach(width, height):
    stride = width * 4
    fd = os.memfd_create('pkg328-locker')
    os.ftruncate(fd, stride * height)
    pixels = mmap.mmap(fd, stride * height)
    pixels.write(struct.pack('=I', 0xff203040) * (width * height))
    pool = conn.new()
    conn.send(shm, 0, struct.pack('=Ii', pool, stride * height), fds=[fd])
    buffer = conn.new()
    conn.send(pool, 0, struct.pack('=IiiiiI', buffer, 0, width, height, stride, 0))
    conn.send(surface, 1, struct.pack('=Iii', buffer, 0, 0))
    conn.send(surface, 2, struct.pack('=iiii', 0, 0, width, height))


def toplevel_event(op, payload):
    if op == 0:
        w, h = struct.unpack_from('=ii', payload)
        if w and h:
            state['pending'] = (w, h)


def xdg_surface_event(op, payload):
    if op == 0:
        conn.send(xdg_surface, 4, payload[:4])
        size = state.get('pending') or (1280, 720)
        if size != state['size']:
            state['size'] = size
            attach(*size)
        conn.send(surface, 6)


xdg_surface = conn.new(xdg_surface_event)
conn.send(wm_base, 2, struct.pack('=II', xdg_surface, surface))
toplevel = conn.new(toplevel_event)
conn.send(xdg_surface, 1, struct.pack('=I', toplevel))
conn.send(toplevel, 3, wl.string('aresos-desktop'))
conn.send(surface, 6)
note('STARTED')
selector = selectors.DefaultSelector()
selector.register(conn.sock, selectors.EVENT_READ)
while True:
    if state['phase'] == 'waiting' and state['keyboard'] and state.get('clicked'):
        width, height = state['size']
        locked_pointer = conn.new(lock_event)
        conn.send(constraints, 1, struct.pack('=IIIII', locked_pointer, surface, pointer, 0, 2))
        conn.send(locked_pointer, 1, struct.pack('=ii', width // 2 * 256, height // 2 * 256))
        conn.send(surface, 6)
        state['phase'] = 'locking'
        note(f'lock_pointer with hint {width // 2},{height // 2}')
    if state['phase'] == 'locking' and state['locked']:
        state['phase'] = 'holding'
        state['until'] = time.monotonic() + 0.5
    if state['phase'] == 'holding' and time.monotonic() > state['until'] and not os.environ.get('HOLD'):
        conn.send(locked_pointer, 0)
        conn.roundtrip()
        state['phase'] = 'dropped'
        note('dropped')
    if selector.select(0.05):
        conn.read()
