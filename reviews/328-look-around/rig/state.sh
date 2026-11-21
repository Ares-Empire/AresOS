#!/usr/bin/bash
# Package 328 rig: what the rig shows right now: the windows and which one is active, the probe's counts, and where
# the rig's X server has its pointer, and whether an X client holds a pointer grab. Reads only the rig's displays.
#
#   state.sh <run folder>
RIG=${1:?usage: state.sh <run folder>}
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
display=$(/usr/bin/sed -n 's/^DISPLAY=//p' "$RIG/env")
[[ $display =~ ^:[0-9]+$ && $display != :0 ]] || { echo "refusing X display '$display'" >&2; exit 1; }
/usr/bin/python3 -I "$here/../../40-real-home/rig/tl.py" "$RIG" list
echo "probe: $(cat "$RIG/probe.json" 2>/dev/null)"
echo "X pointer: $(/usr/bin/env -u WAYLAND_DISPLAY DISPLAY="$display" /usr/bin/xdotool getmouselocation 2>&1)"
# Whether some X client holds a pointer grab: a grab of our own fails then (and is given back at once otherwise).
/usr/bin/env -u WAYLAND_DISPLAY DISPLAY="$display" /usr/bin/python3 -I -c '
from Xlib import X, display
d = display.Display(); status = d.screen().root.grab_pointer(False, 0, X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE, X.CurrentTime)
if status == X.GrabSuccess: d.ungrab_pointer(X.CurrentTime); d.sync()
print("X pointer grab:", "held by another client" if status == X.AlreadyGrabbed else "free" if status == X.GrabSuccess else status)'
