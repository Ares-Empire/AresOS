#!/usr/bin/python3
# Package 328 rig: runs one scenario against the native client in the rig and reports where the pointer's motion,
# clicks and scrolls went: to the probe (a leak), or to the world (the camera turned, Xwayland got the buttons).
"""usage: trial.py <rig> <scenario>

Every scenario first brings the probe (the test app) to the front with a click on it, as the owner clicks Chrome.
  click     a click on the world beside the probe (the owner's report)
  alttab    the world activated (Alt+Tab's result) while the pointer rests on the probe
  super     Super (the helper's SIGUSR1) while the pointer rests on the probe, then Esc closes the search
  menu      a click on the world, Esc for the menu, the pointer onto the probe, Esc again to close the menu
  testseq   WorldKeepsPointerClientGameTest's order: capture, the probe takes the focus, the world activated with the
            pointer on the probe, the pointer onto the world, a click captures, Esc lets go; then the pointer must
            reach the probe
Then: 40 small relative moves (MOVES=<n> changes the number) that would carry the hidden pointer across the probe, a left click and a scroll.
The trace lines come from Xwayland's WAYLAND_DEBUG in the rig's labwc.log (rig.sh with TRACE=1)."""
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image, ImageChops

rig, scenario = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
env = dict(line.strip().split('=', 1) for line in open(os.path.join(rig, 'env')) if '=' in line)
assert env['DISPLAY'] != ':0' and env['WAYLAND_DISPLAY'] != 'wayland-0'
start = time.monotonic()
TRACE = re.compile(r'lock_pointer|confine_pointer|zwp_locked_pointer_v1#\d+\.(locked|unlocked|destroy)|'
                   r'zwp_confined_pointer_v1#\d+\.(confined|unconfined|destroy)|wl_keyboard#\d+\.(enter|leave)|'
                   r'wl_pointer#\d+\.(enter|leave|button|axis\()')


def say(text):
    print(f'{time.monotonic() - start:7.2f} {text}', flush=True)


def vin(*words):
    out = subprocess.run([sys.executable, '-I', os.path.join(here, 'vinput.py'), rig, *map(str, words)],
                         capture_output=True, text=True)
    assert out.stdout.strip() == 'done', out


def tool(*args):
    return subprocess.run([sys.executable, '-I', os.path.join(here, '..', '..', '40-real-home', 'rig', 'tl.py'), rig,
                           *args], capture_output=True, text=True).stdout


def active():
    return [line.split()[0] for line in tool('list').splitlines() if "'activated'" in line]


def probe():
    return json.load(open(os.path.join(rig, 'probe.json')))


def shot():
    path = os.path.join(rig, 'trial.png')
    subprocess.run([os.path.join(here, 'in-rig.sh'), rig, 'shot', '/usr/bin/grim', '-o', 'HEADLESS-1', path], check=True)
    return Image.open(path).convert('RGB')


def turned(before, after):
    """The share of the world's pixels (the probe's rectangle left out) that changed: the camera moved."""
    diff = ImageChops.difference(before, after).convert('L').point(lambda v: 255 if v > 24 else 0)
    for box in ((320, 160, 960, 560), (0, 560, 1280, 720)):  # the probe, and the hotbar and chat lines
        diff.paste(0, box)
    return sum(1 for v in diff.get_flattened_data() if v) / (1280 * 720 - 640 * 400 - 1280 * 160)


locked = False


def follow(lines):
    """Whether Xwayland holds a lock that labwc granted, from the trace lines so far: the world holds the mouse."""
    global locked
    for line in lines:
        if 'zwp_locked_pointer_v1' in line and line.endswith('.locked()'):
            locked = True
        elif 'zwp_locked_pointer_v1' in line and (line.endswith('.unlocked()') or line.endswith('.destroy()')):
            locked = False


def grabbed():
    return locked


log = os.path.join(rig, 'labwc.log')
mark = os.path.getsize(log)


def trace():
    global mark
    with open(log, 'rb') as handle:
        handle.seek(mark)
        data = handle.read().decode(errors='replace')
        mark = handle.tell()
    lines = [line.split('Queue}')[-1].strip() for line in data.splitlines() if TRACE.search(line)]
    return lines


def show_trace(title):
    lines = trace()
    follow(lines)
    say(f'{title}: Xwayland trace ({len(lines)} lines)')
    for line in lines[:24]:
        print('          ' + line)


# The probe in front, as the owner's click on Chrome puts it there. It takes the focus first: while the world holds
# the mouse the cursor stays where the world was clicked, and a click would land there.
tool('activate', 'aresos.pkg328.probe')
vin('abs', 640, 360)
vin('click', 'left')
vin('sleep', 0.5)
say(f'probe clicked: active={active()} grabbed={grabbed()}')
show_trace('probe click')

if scenario in ('click', 'menu'):
    vin('abs', 100, 100)
    vin('click', 'left')
elif scenario == 'testseq':
    vin('abs', 60, 60)
    vin('click', 'left')
    vin('sleep', 0.5)
    for _ in range(10):
        vin('rel', 12, 8)
    tool('activate', 'aresos.pkg328.probe')
    vin('sleep', 0.8)
    show_trace('the probe took the focus while the world steered')
    vin('abs', 640, 360)
    tool('activate', 'aresos-desktop')
    vin('sleep', 0.8)
    show_trace('the world activated with the pointer on the probe')
    entered = probe()['enter']
    vin('abs', 60, 60)
    for _ in range(12):
        vin('rel', 5, 3)
    vin('sleep', 0.3)
    say(f'free pointer onto the world: probe enter {entered}->{probe()["enter"]} inside={probe()["pointer_inside"]}')
    show_trace('free pointer onto the world')
    vin('click', 'left')
    vin('sleep', 0.5)
    show_trace('a click on the world')
    vin('key', 'esc')
    vin('sleep', 0.8)
    show_trace('Esc')
    vin('abs', 640, 360)
    vin('abs', 650, 370)
    vin('sleep', 0.3)
    say(f'RESULT: after letting go the pointer {"reaches" if probe()["pointer_inside"] else "does NOT reach"} the probe')
    vin('key', 'esc')
    sys.exit(0)
elif scenario == 'alttab':
    # What labwc's Alt+Tab does in the end (the virtual keyboard's Alt+Tab went through its window switcher late).
    tool('activate', 'aresos-desktop')
elif scenario == 'super':
    subprocess.run([os.path.join(here, 'super.sh'), rig], check=True)
vin('sleep', 1.0)
say(f'world entered ({scenario}): active={active()} grabbed={grabbed()}')
show_trace('world entry')
if scenario == 'super':
    vin('key', 'esc')
    vin('sleep', 0.8)
    say(f'search closed with Esc: active={active()} grabbed={grabbed()}')
    show_trace('search closed')
if scenario == 'menu':
    vin('key', 'esc')
    vin('sleep', 0.8)
    say(f'menu open: grabbed={grabbed()}')
    vin('abs', 640, 360)
    vin('key', 'esc')
    vin('sleep', 0.8)
    say(f'menu closed with the pointer on the probe: active={active()} grabbed={grabbed()}')
    show_trace('menu')

captured = grabbed()
before, counts = shot(), probe()
for _ in range(int(os.environ.get('MOVES', '40'))):
    vin('rel', 12, 8)
vin('sleep', 0.3)
after = shot()
now = probe()
say(f'moved: camera turned on {turned(before, after):.0%} of the world; probe enter +{now["enter"] - counts["enter"]} '
    f'motion +{now["motion"] - counts["motion"]} inside={now["pointer_inside"]}')
vin('click', 'left')
vin('scroll', 15)
vin('sleep', 0.5)
now = probe()
say(f'clicked and scrolled: probe presses +{now["button_press"] - counts["button_press"]} '
    f'scrolls +{now["axis"] - counts["axis"]}; active={active()} grabbed={grabbed()}')
show_trace('after capture')
leaked = (now['enter'] - counts['enter']) + (now['motion'] - counts['motion']) + (now['button'] - counts['button']) \
    + (now['axis'] - counts['axis'])
if captured:
    say('RESULT: ' + ('LEAK: the probe got the hidden pointer' if leaked else 'captured, and no event reached the probe'))
else:
    say('RESULT: the world did not take the mouse; the pointer stayed a normal, visible pointer'
        + (' (the probe got what it pointed at)' if leaked else ''))
# Let go of the world, so the next scenario starts the same way.
vin('key', 'esc')
vin('sleep', 0.5)
vin('key', 'esc')
vin('sleep', 0.5)
