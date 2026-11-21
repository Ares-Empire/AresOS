#!/usr/bin/bash
# Package 328 rig: labwc's startup command. Arranges the two outputs, starts the virtual input and writes the env file
# the other rig tools read. Runs inside the rig's labwc only.
set -u
unset WAYLAND_DEBUG
if [[ ${WAYLAND_DISPLAY:-wayland-0} == wayland-0 || ${DISPLAY:-:0} == :0 ]]; then
    echo "refusing: not the rig's own display" >"$RIG/refused"; kill "$LABWC_PID"; exit 1
fi
W=1280 H=720
# The laptop screen on the left, the monitor on the right, as in the owner's layout.
/usr/bin/wlr-randr --output HEADLESS-1 --on --custom-mode "${W}x${H}" --pos 0,0 \
    --output HEADLESS-2 --on --custom-mode "${W}x${H}" --pos "$W,0" >>"$RIG/inner.log" 2>&1
/usr/bin/wlr-randr --json >"$RIG/outputs.json" 2>>"$RIG/inner.log"
{
    echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
    echo "DISPLAY=$DISPLAY"
    echo "LABWC_PID=$LABWC_PID"
    echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
    echo "LAYOUT_W=$((2 * W))"
    echo "LAYOUT_H=$H"
    echo "OUTPUT_W=$W"
} >"$RIG/env.tmp"
mv -f -- "$RIG/env.tmp" "$RIG/env"
here=$(cd -- "$(dirname -- "$0")" && pwd)
/usr/bin/python3 -I "$here/vinput.py" "$RIG" >>"$RIG/vinput.log" 2>&1 &
for _ in $(seq 50); do [[ -S $RIG/vinput.sock ]] && break; sleep 0.1; done
# The pointer starts at the centre of the left output, where the game will map.
/usr/bin/python3 -I "$here/vinput.py" "$RIG" abs $((W / 2)) $((H / 2)) >/dev/null
echo ready >"$RIG/ready"
wait
