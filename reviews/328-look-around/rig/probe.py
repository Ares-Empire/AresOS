#!/usr/bin/python3
# Package 328 rig: the inert test app. A plain Wayland window of one colour that never reacts to input; it only counts
# the pointer and keyboard events the compositor gives it, so a click that leaks out of the world shows up here.
"""usage: probe.py <rig> [<width> <height> [<app_id>]]

Writes <rig>/probe.json after every event: counts of pointer enter/leave/motion/button/axis, whether the pointer and
the keyboard are on it now, and the last pointer position. Lines in <rig>/probe.log say what happened, with times."""
import json
import mmap
import os
import selectors
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wl  # noqa: E402

rig = sys.argv[1]
width = int(sys.argv[2]) if len(sys.argv) > 2 else 640
height = int(sys.argv[3]) if len(sys.argv) > 3 else 400
app_id = sys.argv[4] if len(sys.argv) > 4 else 'aresos.pkg328.probe'
env = wl.rig_env(rig)
conn = wl.Connection(env['WAYLAND_DISPLAY'])
start = time.monotonic()
log = open(os.path.join(rig, 'probe.log'), 'a', buffering=1)
stats = dict(enter=0, leave=0, motion=0, button=0, button_press=0, axis=0, key=0, keyboard_enter=0,
             keyboard_leave=0, pointer_inside=False, keyboard_focus=False, last=None, configured=None)


def note(text):
    log.write(f'{time.monotonic() - start:9.3f} {text}\n')


def save():
    path = os.path.join(rig, 'probe.json')
    with open(path + '.tmp', 'w') as handle:
        json.dump(stats, handle)
    os.replace(path + '.tmp', path)


surface = None


def pointer_event(op, payload):
    if op == 0:
        _, target, x, y = struct.unpack_from('=IIii', payload)
        if target != surface:
            return
        stats['enter'] += 1
        stats['pointer_inside'] = True
        stats['last'] = [wl.fixed(x), wl.fixed(y)]
        note(f'ENTER {wl.fixed(x):.1f} {wl.fixed(y):.1f}')
    elif op == 1:
        stats['leave'] += 1
        stats['pointer_inside'] = False
        note('LEAVE')
    elif op == 2:
        _, x, y = struct.unpack_from('=Iii', payload)
        stats['motion'] += 1
        stats['last'] = [wl.fixed(x), wl.fixed(y)]
        note(f'MOTION {wl.fixed(x):.1f} {wl.fixed(y):.1f}')
    elif op == 3:
        _, _, button, state = struct.unpack_from('=IIII', payload)
        stats['button'] += 1
        stats['button_press'] += state == 1
        note(f'BUTTON {button:#x} {"down" if state else "up"}')
    elif op == 4:
        _, axis, value = struct.unpack_from('=IIi', payload)
        stats['axis'] += 1
        note(f'AXIS {axis} {wl.fixed(value):.1f}')
    else:
        return
    save()


def keyboard_event(op, payload):
    while conn.fds:
        os.close(conn.fds.pop())
    if op == 1:
        stats['keyboard_enter'] += 1
        stats['keyboard_focus'] = True
        note('KBD_ENTER')
    elif op == 2:
        stats['keyboard_leave'] += 1
        stats['keyboard_focus'] = False
        note('KBD_LEAVE')
    elif op == 3:
        _, _, key, state = struct.unpack_from('=IIII', payload)
        stats['key'] += 1
        note(f'KEY {key} {"down" if state else "up"}')
    else:
        return
    save()


pointer = keyboard = None


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


def wm_base_event(op, payload):
    if op == 0:
        conn.send(wm_base, 3, payload[:4])  # pong


compositor = conn.bind('wl_compositor', 4)
shm = conn.bind('wl_shm', 1)
wm_base = conn.bind('xdg_wm_base', 2, wm_base_event)
seat = conn.bind('wl_seat', 5, seat_event)

# One opaque buffer in a colour no game frame has: magenta.
stride = width * 4
size = stride * height
fd = os.memfd_create('pkg328-probe')
os.ftruncate(fd, size)
pixels = mmap.mmap(fd, size)
pixels.write(struct.pack('=I', 0xffff00ff) * (width * height))
pool = conn.new()
conn.send(shm, 0, struct.pack('=Ii', pool, size), fds=[fd])
buffer = conn.new()
conn.send(pool, 0, struct.pack('=IiiiiI', buffer, 0, width, height, stride, 0))  # ARGB8888

surface = conn.new()
conn.send(compositor, 0, struct.pack('=I', surface))
configured = []


def xdg_surface_event(op, payload):
    if op == 0:
        (serial,) = struct.unpack_from('=I', payload)
        conn.send(xdg_surface, 4, struct.pack('=I', serial))  # ack_configure
        if not configured:
            conn.send(surface, 1, struct.pack('=Iii', buffer, 0, 0))
            conn.send(surface, 2, struct.pack('=iiii', 0, 0, width, height))
        configured.append(serial)
        conn.send(surface, 6)
        note('CONFIGURED')


def toplevel_event(op, payload):
    if op == 0:
        w, h = struct.unpack_from('=ii', payload)
        stats['configured'] = [w, h]
    elif op == 1:
        note('CLOSE asked; the probe stays (it is inert)')


xdg_surface = conn.new(xdg_surface_event)
conn.send(wm_base, 2, struct.pack('=II', xdg_surface, surface))
toplevel = conn.new(toplevel_event)
conn.send(xdg_surface, 1, struct.pack('=I', toplevel))
conn.send(toplevel, 2, wl.string('Package 328 probe'))
conn.send(toplevel, 3, wl.string(app_id))
# A fixed size: labwc must not resize it (it is not foot, so no Maximize rule applies).
conn.send(toplevel, 8, struct.pack('=ii', width, height))
conn.send(toplevel, 7, struct.pack('=ii', width, height))
conn.send(surface, 6)
save()
note(f'STARTED {width}x{height} {app_id}')

selector = selectors.DefaultSelector()
selector.register(conn.sock, selectors.EVENT_READ)
while True:
    selector.select()
    conn.read()
