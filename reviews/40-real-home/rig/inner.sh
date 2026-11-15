#!/bin/bash
# Runs inside the rig's labwc (WAYLAND_DISPLAY and DISPLAY are that compositor's).
set -u
if [[ ${WAYLAND_DISPLAY:-wayland-0} == wayland-0 || ${DISPLAY:-:0} == :0 ]]; then
    echo "refusing: this is not the rig's own display" >"$RIG/env"; kill "$LABWC_PID"; exit 1
fi
PRIVATE="$XDG_RUNTIME_DIR/pkg40-rig"
mkdir -p -m 0700 "$PRIVATE"; rm -f "$PRIVATE/shell.sock" "$PRIVATE/shell-journal.json"
export ARESOS_DESKTOP_INSTANCE="aresdesktop-dev-$(od -An -N6 -tx1 /dev/urandom | tr -d ' \n')"
export ARESOS_LAUNCH_NONCE=$(head -c 24 /dev/urandom | base64 -w0 | tr '+/' '-_' | tr -d '=')
env HOME="$RIG/home" PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin ${HELPER_ENV:-} \
    "$HELPER" --socket "$PRIVATE/shell.sock" --registry "$REGISTRY" >>"$RIG/helper.log" 2>&1 &
helper=$!
{ echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"; echo "DISPLAY=$DISPLAY"; echo "LABWC_PID=$LABWC_PID"; echo "HELPER_PID=$helper"
  echo "SOCKET=$PRIVATE/shell.sock"; echo "INSTANCE=$ARESOS_DESKTOP_INSTANCE"; echo "NONCE=$ARESOS_LAUNCH_NONCE"; } >"$RIG/env"
for _ in $(seq 50); do [[ -S $PRIVATE/shell.sock ]] && break; sleep 0.1; done
here=$(cd -- "$(dirname -- "$0")" && pwd)
"$here/vinput.py" "$RIG" >"$RIG/vinput.log" 2>&1 &
vinput=$!
sleep 1
if [[ ${NO_GAME:-0} == 1 ]]; then wait "$helper"; kill "$vinput" "$LABWC_PID"; exit 0; fi
export ARESOS_SHELL_SOCKET="$PRIVATE/shell.sock"
cd "$WT/mod"
env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __VK_LAYER_NV_optimus=NVIDIA_only ALSOFT_DRIVERS=null \
    "$WT/mod/gradlew" --no-daemon runClient $GAME_ARGS >"$RIG/game.log" 2>&1
echo "game exited $?" >>"$RIG/env"
kill "$helper" "$vinput" 2>/dev/null
kill "$LABWC_PID"
