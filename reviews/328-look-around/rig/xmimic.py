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
  churn    as click, then the capture is let go and taken again at once (GLFW's enableCursor and disableCursor, as
           on an X focus change), and no motion follows
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
if scenario in ('click', 'press', 'keyboard', 'churn'):
    vin('abs', 100, 100)
if scenario == 'over':
    vin('abs', 640, 360)
if scenario in ('click', 'churn'):
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
if os.environ.get('ARGB_CURSOR'):
    # GLFW's own kind of hidden cursor (argbcursor.py): an Xcursor ARGB image, every pixel transparent.
    hidden = d.create_resource_object('cursor', int(os.environ['ARGB_CURSOR']))
if hide_cursor:
    d.xfixes_query_version()
    window.xfixes_hide_cursor()
# ORDER names the capture's X requests in order (default: the first stand-in's, the hidden cursor before any warp):
#   prewarp  XWarpPointer to the centre (Minecraft's glfwSetCursorPos before it switches the mode)
#   here     XWarpPointer to where the pointer already is
#   hide     the transparent cursor image (GLFW's updateCursorImage)
#   centre   XWarpPointer to the centre (GLFW's _glfwCenterCursorInContentArea)
#   grab     XGrabPointer confined to the window (GLFW's captureCursor)
#   ungrab   XUngrabPointer (GLFW's releaseCursor, part of every switch to a mode that does not capture)
#   xfhide   XFixesHideCursor on the window (X then draws no cursor at all)
# ARGB_CURSOR=<xid> (from argbcursor.py) makes "hide" use GLFW's kind of transparent cursor instead of a pixmap one.
# GLFW 3.5 with Minecraft's grabMouse, as the game's trace shows it: prewarp,centre,grab,hide
grab = None
for step in os.environ.get('ORDER', 'hide,centre,grab').split(','):
    if step in ('prewarp', 'centre'):
        window.warp_pointer(geometry.width // 2, geometry.height // 2)
    elif step == 'here':
        where = window.query_pointer()
        window.warp_pointer(where.win_x, where.win_y)
    elif step == 'hide':
        window.change_attributes(cursor=hidden)
    elif step == 'xfhide':
        d.xfixes_query_version()
        window.xfixes_hide_cursor()
        hide_cursor = True
    elif step == 'ungrab':
        d.ungrab_pointer(X.CurrentTime)
    elif step == 'grab':
        grab = window.grab_pointer(True, X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask,
                                   X.GrabModeAsync, X.GrabModeAsync, window, X.NONE, X.CurrentTime)
    d.sync()
say(f'captured ({scenario}{" hide" if hide_cursor else ""}, order {os.environ.get("ORDER", "hide,centre,grab")}); grab status {grab}')
if scenario == 'press':
    vin('button', 'left', 'up')
pump(0.5)

if scenario == 'churn':
    d.ungrab_pointer(X.CurrentTime)
    window.change_attributes(cursor=X.NONE)
    window.warp_pointer(geometry.width // 2, geometry.height // 2)
    d.sync()
    window.change_attributes(cursor=hidden)
    window.warp_pointer(geometry.width // 2, geometry.height // 2)
    window.grab_pointer(True, X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask,
                        X.GrabModeAsync, X.GrabModeAsync, window, X.NONE, X.CurrentTime)
    d.sync()
    pump(0.5)
    say('let go and captured again')
before = probe()
pressed_before = counts['ButtonPress']
# The owner moves the mouse while the world steers: towards and across the probe's rectangle.
for step in range(0 if scenario == 'churn' else int(os.environ.get('MOVES', '40'))):
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
