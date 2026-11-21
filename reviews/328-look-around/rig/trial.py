#!/usr/bin/python3
# Package 328 rig: runs one scenario against the native client in the rig and reports where the pointer's motion,
# clicks and scrolls went: to the probe (a leak), or to the world (the camera turned, Xwayland got the buttons).
"""usage: trial.py <rig> <scenario>

Every scenario first brings the probe (the test app) to the front with a click on it, as the owner clicks Chrome.
  click     a click on the world beside the probe (the owner's report)
  alttab    Alt+Tab back to the world while the pointer rests on the probe
  super     Super (the helper's SIGUSR1) while the pointer rests on the probe, then Esc closes the search
  menu      a click on the world, Esc for the menu, the pointer onto the probe, Esc again to close the menu
Then: 40 small relative moves (MOVES=<n> changes the number) that would carry the hidden pointer across the probe, a left click and a scroll.
The trace lines come from Xwayland's WAYLAND_DEBUG in the rig's labwc.log (rig.sh with TRACE=1)."""
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image, ImageChops
from Xlib import X, display

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


def grabbed():
    """Whether the game holds the X pointer grab: a grab of our own then fails with AlreadyGrabbed."""
    d = display.Display(env['DISPLAY'])
    status = d.screen().root.grab_pointer(False, 0, X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE,
                                          X.CurrentTime)
    if status == X.GrabSuccess:
        d.ungrab_pointer(X.CurrentTime)
    d.close()
    return status == X.AlreadyGrabbed


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
    say(f'{title}: Xwayland trace ({len(lines)} lines)')
    for line in lines[:24]:
        print('          ' + line)


# The probe in front, as the owner's click on Chrome puts it there.
vin('abs', 640, 360)
vin('click', 'left')
vin('sleep', 0.5)
say(f'probe clicked: active={active()} grabbed={grabbed()}')
show_trace('probe click')

if scenario in ('click', 'menu'):
    vin('abs', 100, 100)
    vin('click', 'left')
elif scenario == 'alttab':
    vin('key', 'lalt', 'down')
    vin('key', 'tab')
    vin('key', 'lalt', 'up')
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
say('RESULT: ' + ('LEAK: the probe got the hidden pointer' if leaked else 'no event reached the probe'))
# Let go of the world, so the next scenario starts the same way.
vin('key', 'esc')
vin('sleep', 0.5)
vin('key', 'esc')
vin('sleep', 0.5)
