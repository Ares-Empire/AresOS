#!/bin/bash
# Rig tool: xdotool against the rig's own Xwayland only. usage: x.sh <rig> <xdotool args...>
rig=$1; shift
d=$(sed -n 's/^DISPLAY=//p' "$rig/env")
[[ -n $d && $d != :0 ]] || { echo "refusing display '$d'" >&2; exit 1; }
exec env -u WAYLAND_DISPLAY DISPLAY="$d" /usr/bin/xdotool "$@"
