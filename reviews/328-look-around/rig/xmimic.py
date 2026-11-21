#!/usr/bin/python3
# Package 328 rig: an X11 stand-in for the game's window under the rig's Xwayland. It takes the desktop's identity
# (WM_CLASS aresos-desktop, so the image's rules make it maximized and always on bottom) and captures the pointer the
# way GLFW 3.5 does for GLFW_CURSOR_DISABLED on X11: a transparent cursor image, a warp to the window's centre, then
# XGrabPointer confined to the window. Then it drives the virtual pointer and reports where motion and clicks went.
"""usage: xmimic.py <rig> <scenario> [hide]

Scenarios, each starting with the probe (the test app) in front and holding the keyboard:
  click    a click on the world beside the probe, then capture after the release
  press    a click on the world beside the probe, capture while the button is still down (HomePointer's path)
  keyboard capture while the probe keeps the keyboard and the pointer rests on the world (a regrab path)
  over     the world activated through foreign-toplevel while the pointer rests on the probe (Super, Alt+Tab,
           the helper's return), then capture
hide: XFixesHideCursor on the window before capturing (a cursor X does not draw at all)."""
import json
import os
import subprocess
import sys
import time

from Xlib import X, Xatom, display
from Xlib.ext import xfixes  # noqa: F401  (registers the extension methods)

rig, scenario = sys.argv[1], sys.argv[2]
hide_cursor = 'hide' in sys.argv[3:]
env = dict(line.strip().split('=', 1) for line in open(os.path.join(rig, 'env')) if '=' in line)
assert env['DISPLAY'] != ':0' and env['WAYLAND_DISPLAY'] != 'wayland-0'
here = os.path.dirname(os.path.abspath(__file__))
d = display.Display(env['DISPLAY'])
screen = d.screen()
start = time.monotonic()
counts = dict(ButtonPress=0, ButtonRelease=0, MotionNotify=0, EnterNotify=0, LeaveNotify=0, FocusIn=0, FocusOut=0)


def say(text):
    print(f'{time.monotonic() - start:7.3f} {text}', flush=True)


def vin(*words):
    out = subprocess.run([sys.executable, '-I', os.path.join(here, 'vinput.py'), rig, *map(str, words)],
                         capture_output=True, text=True)
    assert out.stdout.strip() == 'done', out


def probe():
    return json.load(open(os.path.join(rig, 'probe.json')))


def pump(seconds=0.2):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while d.pending_events():
            e = d.next_event()
            name = {X.ButtonPress: 'ButtonPress', X.ButtonRelease: 'ButtonRelease', X.MotionNotify: 'MotionNotify',
                    X.EnterNotify: 'EnterNotify', X.LeaveNotify: 'LeaveNotify', X.FocusIn: 'FocusIn',
                    X.FocusOut: 'FocusOut'}.get(e.type)
            if name:
                counts[name] += 1
                if name != 'MotionNotify':
                    say(f'X {name} ' + (f'{e.event_x},{e.event_y}' if hasattr(e, 'event_x') else ''))
        time.sleep(0.01)


window = screen.root.create_window(0, 0, 1280, 720, 0, screen.root_depth, X.InputOutput, X.CopyFromParent,
                                   background_pixel=0x204060,
                                   event_mask=X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask
                                   | X.EnterWindowMask | X.LeaveWindowMask | X.FocusChangeMask | X.StructureNotifyMask)
window.set_wm_class('aresos-desktop', 'aresos-desktop')
window.set_wm_name('xmimic')
window.map()
d.sync()
pump(1.5)
geometry = window.get_geometry()
say(f'mapped {geometry.width}x{geometry.height}; probe {probe()}')

# The probe comes to the front and takes the keyboard, as an app does when it opens or is clicked.
subprocess.run([sys.executable, '-I', os.path.join(here, '..', '..', '40-real-home', 'rig', 'tl.py'), rig, 'activate',
                'aresos.pkg328.probe'], check=True, capture_output=True)
pump(0.3)
if scenario in ('click', 'press', 'keyboard'):
    vin('abs', 100, 100)
if scenario == 'over':
    vin('abs', 640, 360)
if scenario == 'click':
    vin('click', 'left')
elif scenario == 'press':
    vin('button', 'left', 'down')
elif scenario == 'over':
    subprocess.run([sys.executable, '-I', os.path.join(here, '..', '..', '40-real-home', 'rig', 'tl.py'), rig, 'activate',
                    'aresos-desktop'], check=True, capture_output=True)
pump(0.5)
say(f'before capture ({scenario}): probe {probe()} X presses={counts["ButtonPress"]}')

# GLFW 3.5 disableCursor(): updateCursorImage (hidden cursor image), _glfwCenterCursorInContentArea, captureCursor.
pixmap = window.create_pixmap(16, 16, 1)
gc = pixmap.create_gc(foreground=0)
pixmap.fill_rectangle(gc, 0, 0, 16, 16)
hidden = pixmap.create_cursor(pixmap, (0, 0, 0), (0, 0, 0), 0, 0)
if hide_cursor:
    d.xfixes_query_version()
    window.xfixes_hide_cursor()
window.change_attributes(cursor=hidden)
window.warp_pointer(geometry.width // 2, geometry.height // 2)
grab = window.grab_pointer(True, X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask,
                           X.GrabModeAsync, X.GrabModeAsync, window, X.NONE, X.CurrentTime)
d.sync()
say(f'captured ({scenario}{" hide" if hide_cursor else ""}); grab status {grab}')
if scenario == 'press':
    vin('button', 'left', 'up')
pump(0.5)

before = probe()
pressed_before = counts['ButtonPress']
# The owner moves the mouse while the world steers: towards and across the probe's rectangle.
for step in range(40):
    vin('rel', 12, 8)
    # GLFW re-centres the X pointer at every poll while disabled.
    window.warp_pointer(geometry.width // 2, geometry.height // 2)
    d.sync()
    pump(0.02)
after = probe()
say(f'motion: probe enter {before["enter"]}->{after["enter"]} motion {before["motion"]}->{after["motion"]} '
    f'inside={after["pointer_inside"]}; X motion events {counts["MotionNotify"]}')
vin('click', 'left')
vin('scroll', 15)
pump(0.5)
after = probe()
say(f'click: probe button_press {before["button_press"]}->{after["button_press"]} axis {before["axis"]}->{after["axis"]}; '
    f'X presses {pressed_before}->{counts["ButtonPress"]}')
pointer = window.query_pointer()
say(f'X pointer at {pointer.win_x},{pointer.win_y}')
d.ungrab_pointer(X.CurrentTime)
if hide_cursor:
    window.xfixes_show_cursor()
d.sync()
pump(0.5)
say(f'released; probe {probe()}')
window.destroy()
d.sync()
