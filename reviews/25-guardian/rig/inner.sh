#!/usr/bin/bash
# DEVELOPMENT AID of package 25 (the real-game check; copied from package 49b's rig), headless use only: runs inside the rig's labwc (start.sh).
# Package 40's rig/inner.sh with the screen set to $SIZE at $REFRESH Hz, the restricted helper (helper41.py) and the
# game's JVM settings from jvm.gradle.
set -u
if [[ ${WAYLAND_DISPLAY:-wayland-0} == wayland-0 || ${DISPLAY:-:0} == :0 ]]; then
    echo "refusing: this is not the rig's own display" >"$RIG/env"; kill "$LABWC_PID"; exit 1
fi
here=$(cd -- "$(dirname -- "$0")" && pwd)
output=$(/usr/bin/wlr-randr | awk 'NR==1{print $1}')
/usr/bin/wlr-randr --output "$output" --custom-mode "${SIZE}@${REFRESH}Hz" >"$RIG/randr.txt" 2>&1
/usr/bin/wlr-randr >>"$RIG/randr.txt" 2>&1
PRIVATE="$XDG_RUNTIME_DIR/pkg25-rig-$$"
mkdir -p -m 0700 "$PRIVATE"
# The session's identity is the one check.py wrote for this launch (private/identity, mode 0600): the adoption runtime
# file names the same instance and nonce. The helper and the game get it, as in a session.
while IFS='=' read -r key value; do
    case $key in ARESOS_DESKTOP_INSTANCE|ARESOS_LAUNCH_NONCE) export "$key=$value" ;; esac
done <"$RIG/private/identity"
: "${ARESOS_DESKTOP_INSTANCE:?}" "${ARESOS_LAUNCH_NONCE:?}"
env HOME="$HOMEDIR" PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin \
    /usr/bin/python3 -I "$here/helper41.py" "$APPS" --socket "$PRIVATE/shell.sock" --registry "$APPS/registry" \
    >>"$RIG/helper.txt" 2>&1 &
helper=$!
{ echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"; echo "DISPLAY=$DISPLAY"; echo "LABWC_PID=$LABWC_PID"; echo "HELPER_PID=$helper"
  echo "SOCKET=$PRIVATE/shell.sock"; echo "SIZE=$SIZE"; echo "INNER_PID=$$"; } >"$RIG/env"
for _ in $(seq 50); do [[ -S $PRIVATE/shell.sock ]] && break; sleep 0.1; done
/usr/bin/python3 -I "$here/vinput.py" "$RIG" >"$RIG/vinput.txt" 2>&1 &
vinput=$!
cleanup_inner() {
    trap - EXIT
    kill "$helper" "$vinput" 2>/dev/null || true
    wait "$helper" "$vinput" 2>/dev/null || true
    rm -rf -- "$PRIVATE"
    kill "$LABWC_PID" 2>/dev/null || true
}
trap cleanup_inner EXIT
trap 'exit 143' TERM
trap 'exit 129' HUP
trap 'exit 130' INT
echo "VINPUT_PID=$vinput" >>"$RIG/env"
sleep 1
export ARESOS_SHELL_SOCKET="$PRIVATE/shell.sock"
# The gate (ARESOS_DESKTOP_LIFECYCLE=1) and the test supervisor's XDG_RUNTIME_DIR are not set here: Gradle and its
# `systemd-run --user` need this session's runtime folder. The rig's java wrapper (java-wrapper.py, $PKG25_JAVA) sets
# both for the game's JVM alone, on its own command line.
cd "$WT/mod"
env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __VK_LAYER_NV_optimus=NVIDIA_only ALSOFT_DRIVERS=null \
    "$WT/mod/gradlew" --no-daemon -I "$here/jvm.gradle" runClient ${GAME_ARGS:+"--args=$GAME_ARGS"} \
    >"$RIG/gradle.txt" 2>&1
echo "GAME_EXIT=$?" >>"$RIG/env"
exit 0
