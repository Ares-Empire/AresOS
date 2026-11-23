#!/usr/bin/python3
# Package 328 rig: a virtual pointer and keyboard on the rig compositor's seat only (never the owner's).
"""usage: vinput.py <rig>        serve commands on <rig>/vinput.sock, one per line, each answered "done"
       vinput.py <rig> <command...>   send one command to that server and wait for its answer

Commands: abs <x> <y> (layout pixels) | rel <dx> <dy> [<steps>] | button <left|right|middle> <down|up>
          | click <left|right|middle> | scroll <dy> | key <name> [down|up] | sleep <seconds>"""
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wl  # noqa: E402

rig = sys.argv[1]
path = os.path.join(rig, 'vinput.sock')
if len(sys.argv) > 2:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(path)
    client.sendall((' '.join(sys.argv[2:]) + '\n').encode())
    reply = client.makefile().readline().strip()
    print(reply)
    sys.exit(0 if reply == 'done' else 1)

env = wl.rig_env(rig)
extent = (int(env['LAYOUT_W']), int(env['LAYOUT_H']))
conn = wl.Connection(env['WAYLAND_DISPLAY'])
seat = conn.bind('wl_seat', 1)
kbm = conn.bind('zwp_virtual_keyboard_manager_v1', 1)
ptm = conn.bind('zwlr_virtual_pointer_manager_v1', 1)
kb = conn.new()
conn.send(kbm, 0, struct.pack('=II', seat, kb))
pt = conn.new()
conn.send(ptm, 0, struct.pack('=II', seat, pt))
keymap = (b'xkb_keymap { xkb_keycodes { include "evdev+aliases(qwerty)" }; xkb_types { include "complete" }; '
          b'xkb_compat { include "complete" }; xkb_symbols { include "pc+us+inet(evdev)" }; };\0')
fd = os.memfd_create('keymap')
os.write(fd, keymap)
conn.send(kb, 0, struct.pack('=II', 1, len(keymap)), fds=[fd])
conn.roundtrip()
KEYS = dict(esc=1, tab=15, enter=28, space=57, lshift=42, lctrl=29, lalt=56, super=125, f3=61, f1=59,
            left=105, right=106, up=103, down=108,
            **{c: k for c, k in zip('1234567890', range(2, 12))}, **{c: k for c, k in zip('qwertyuiop', range(16, 26))},
            **{c: k for c, k in zip('asdfghjkl', range(30, 39))}, **{c: k for c, k in zip('zxcvbnm', range(44, 51))})
BUTTONS = dict(left=0x110, right=0x111, middle=0x112)


def now():
    return int(time.monotonic() * 1000) & 0xffffffff


def frame():
    conn.send(pt, 4)


def run(words):
    if words[0] == 'abs':
        conn.send(pt, 1, struct.pack('=IIIII', now(), int(words[1]), int(words[2]), *extent))
        frame()
    elif words[0] == 'rel':
        steps = int(words[3]) if len(words) > 3 else 1
        dx, dy = float(words[1]) / steps, float(words[2]) / steps
        for _ in range(steps):
            conn.send(pt, 0, struct.pack('=Iii', now(), int(dx * 256), int(dy * 256)))
            frame()
            conn.roundtrip()
            time.sleep(0.016)
    elif words[0] in ('button', 'click'):
        code = BUTTONS[words[1]]
        states = [1, 0] if words[0] == 'click' else [1 if words[2] == 'down' else 0]
        for state in states:
            conn.send(pt, 2, struct.pack('=III', now(), code, state))
            frame()
            conn.roundtrip()
            time.sleep(0.05)
    elif words[0] == 'scroll':
        conn.send(pt, 3, struct.pack('=IIi', now(), 0, int(float(words[1]) * 256)))
        frame()
    elif words[0] == 'key':
        code = KEYS[words[1]]
        states = [1, 0] if len(words) < 3 else [1 if words[2] == 'down' else 0]
        for state in states:
            conn.send(kb, 1, struct.pack('=III', now(), code, state))
            conn.roundtrip()
            time.sleep(0.04)
    elif words[0] == 'sleep':
        time.sleep(float(words[1]))
    else:
        raise ValueError(words[0])
    conn.roundtrip()


if os.path.exists(path):
    os.unlink(path)
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(path)
server.listen(4)
print('ready', flush=True)
while True:
    client, _ = server.accept()
    with client, client.makefile('rw') as stream:
        for line in stream:
            words = line.split()
            if not words:
                continue
            try:
                run(words)
                stream.write('done\n')
            except Exception as error:  # report, keep serving
                stream.write(f'error {error!r}\n')
            stream.flush()
