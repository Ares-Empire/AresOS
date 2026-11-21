#!/usr/bin/python3
# Package 56 test fixture. Virtual input goes only to the private headless compositor named by the test.
"""Rig tool: a virtual keyboard and pointer on the rig compositor's seat (never the owner's). Reads commands from stdin: key <name> [down|up] | mods <alt|shift|ctrl|super ...> | type <text> | move <x> <y> | rel <dx> <dy> | click <left|right>
| button <left|right> <down|up> | quit"""
import array, os, socket, struct, sys, time
rig = sys.argv[1]
env = dict(line.strip().split('=', 1) for line in open(os.path.join(rig, 'env')) if '=' in line)
assert env['WAYLAND_DISPLAY'] != 'wayland-0'
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(os.path.join(os.environ['XDG_RUNTIME_DIR'], env['WAYLAND_DISPLAY']))
next_id = [2]
def new():
    next_id[0] += 1
    return next_id[0] - 1
def send(obj, op, payload=b'', fds=()):
    msg = struct.pack('=II', obj, ((8 + len(payload)) << 16) | op) + payload
    if fds:
        sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', fds))])
    else:
        sock.sendall(msg)
def string(value):
    data = value.encode() + b'\0'
    return struct.pack('=I', len(data)) + data + b'\0' * (-len(data) % 4)
buf = bytearray()
globals_ = {}
done = set()
def pump(until):
    while until not in done:
        buf.extend(sock.recv(65536))
        while len(buf) >= 8:
            obj, word = struct.unpack_from('=II', buf)
            size, op = word >> 16, word & 0xffff
            if len(buf) < size: break
            payload = bytes(buf[8:size]); del buf[:size]
            if obj == 1 and op == 0:
                sys.exit('wayland error: ' + repr(payload))
            if obj == registry and op == 0:
                (name,) = struct.unpack_from('=I', payload)
                (length,) = struct.unpack_from('=I', payload, 4)
                interface = payload[8:8 + length - 1].decode()
                globals_[interface] = (name, struct.unpack_from('=I', payload, 8 + length + (-length % 4))[0])
            elif obj in callbacks:
                done.add(obj)
callbacks = set()
def roundtrip():
    cb = new(); callbacks.add(cb)
    send(1, 0, struct.pack('=I', cb)); pump(cb)
registry = new(); send(1, 1, struct.pack('=I', registry)); roundtrip()
def bind(interface, version):
    obj = new()
    send(registry, 0, struct.pack('=I', globals_[interface][0]) + string(interface) + struct.pack('=II', version, obj))
    return obj
seat = bind('wl_seat', 1)
kbm = bind('zwp_virtual_keyboard_manager_v1', 1)
ptm = bind('zwlr_virtual_pointer_manager_v1', 1)
kb = new(); send(kbm, 0, struct.pack('=II', seat, kb))
pt = new(); send(ptm, 0, struct.pack('=II', seat, pt))
keymap = (b'xkb_keymap { xkb_keycodes { include "evdev+aliases(qwerty)" }; xkb_types { include "complete" }; '
          b'xkb_compat { include "complete" }; xkb_symbols { include "pc+us+inet(evdev)" }; };\0')
fd = os.memfd_create('keymap'); os.write(fd, keymap)
send(kb, 0, struct.pack('=II', 1, len(keymap)), fds=[fd])
roundtrip()
KEYS = dict(esc=1, tab=15, enter=28, space=57, slash=53, f4=62, f11=87, f3=61, minus=12, dot=52, lshift=42, lalt=56, lctrl=29, super=125,
            **{c: k for c, k in zip('1234567890', range(2, 12))}, **{c: k for c, k in zip('qwertyuiop', range(16, 26))},
            **{c: k for c, k in zip('asdfghjkl', range(30, 39))}, **{c: k for c, k in zip('zxcvbnm', range(44, 51))})
MODS = dict(shift=1, ctrl=4, alt=8, super=64)
now = lambda: int(time.monotonic() * 1000) & 0xffffffff
def key(code, state):
    send(kb, 1, struct.pack('=III', now(), code, state))
def tap(code):
    key(code, 1); roundtrip(); time.sleep(0.04); key(code, 0); roundtrip(); time.sleep(0.04)
print('ready', flush=True)
for line in sys.stdin:
    words = line.split()
    if not words: continue
    if words[0] == 'quit': sys.exit(0)
    if words[0] == 'key':
        if len(words) > 2: key(KEYS[words[1]], 1 if words[2] == 'down' else 0)
        else: tap(KEYS[words[1]])
    elif words[0] == 'mods':
        send(kb, 2, struct.pack('=IIII', sum(MODS[m] for m in words[1:]), 0, 0, 0))
    elif words[0] == 'type':
        for ch in line.rstrip('\n')[5:]:
            name = {' ': 'space', '/': 'slash', '-': 'minus', '.': 'dot'}.get(ch, ch)
            tap(KEYS[name])
    elif words[0] == 'rel':
        send(pt, 0, struct.pack('=Iii', now(), int(float(words[1])*256), int(float(words[2])*256))); send(pt, 4)
    elif words[0] == 'move':
        send(pt, 1, struct.pack('=IIIII', now(), int(words[1]), int(words[2]), 1280, 720)); send(pt, 4)
    elif words[0] in ('click', 'button'):
        code = {'left': 0x110, 'right': 0x111}[words[1]]
        states = [1, 0] if words[0] == 'click' else [1 if words[2] == 'down' else 0]
        for state in states:
            send(pt, 2, struct.pack('=III', now(), code, state)); send(pt, 4); roundtrip(); time.sleep(0.05)
    roundtrip()
    print('done', flush=True)
