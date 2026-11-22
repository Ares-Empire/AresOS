#!/usr/bin/python3
"""An inert X11 surface on the rig's second output, so Xwayland sees the pointer leave the game."""
import os
import re
import sys

from Xlib import X, display

screen = os.environ.get("DISPLAY", "")
if not re.fullmatch(r":[1-9][0-9]*", screen) or os.environ.get("WAYLAND_DISPLAY", "wayland-0") == "wayland-0":
    raise SystemExit("Refusing the owner's displays")

connection = display.Display(screen)
root = connection.screen().root
window = root.create_window(
    int(sys.argv[1]), 0, 300, 200, 0, X.CopyFromParent, X.InputOutput, X.CopyFromParent,
    background_pixel=0x204060, override_redirect=True, event_mask=X.StructureNotifyMask,
)
window.map()
connection.sync()
print("ready", flush=True)
while connection.next_event().type != X.DestroyNotify:
    pass
