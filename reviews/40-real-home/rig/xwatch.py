#!/usr/bin/python3
# DEVELOPMENT AID of package 40, headless use only: this rig calls Gradle directly (inner.sh runs gradlew runClient).
"""Rig tool: log focus/map/state events of an X window on the rig's Xwayland. usage: xwatch.py <rig> <window id> <seconds>"""
import os, sys, time
rig = sys.argv[1]
env = dict(line.strip().split('=', 1) for line in open(os.path.join(rig, 'env')) if '=' in line)
assert env['DISPLAY'] != ':0'
os.environ.pop('WAYLAND_DISPLAY', None)
from Xlib import X, display
d = display.Display(env['DISPLAY'])
w = d.create_resource_object('window', int(sys.argv[2]))
w.change_attributes(event_mask=X.StructureNotifyMask | X.FocusChangeMask | X.PropertyChangeMask)
d.flush()
start = time.time(); end = start + float(sys.argv[3])
NAMES = {X.FocusIn: 'FocusIn', X.FocusOut: 'FocusOut', X.MapNotify: 'MapNotify', X.UnmapNotify: 'UnmapNotify', X.ConfigureNotify: 'Configure', X.PropertyNotify: 'Property'}
while time.time() < end:
    while d.pending_events():
        e = d.next_event()
        extra = ''
        if e.type == X.PropertyNotify:
            extra = d.get_atom_name(e.atom)
            if extra not in ('WM_STATE', '_NET_WM_STATE'): continue
        elif e.type in (X.FocusIn, X.FocusOut): extra = f'mode={e.mode} detail={e.detail}'
        elif e.type == X.ConfigureNotify: extra = f'{e.width}x{e.height}+{e.x}+{e.y}'
        print(f'{time.time() - start:6.3f} {NAMES.get(e.type, e.type)} {extra}', flush=True)
    time.sleep(0.005)
