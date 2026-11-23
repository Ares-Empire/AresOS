#!/usr/bin/bash
# Package 328 rig: runs a command against the rig's own displays and private D-Bus only, in a scope of its own
# (pkg328-<name>-<pid>), so stop.sh can end it. Refuses wayland-0 and :0.
#
#   in-rig.sh <run folder> <name> <command...>
set -euo pipefail
RIG=$(/usr/bin/realpath -- "${1:?usage: in-rig.sh <run folder> <name> <command...>}")
name=${2:?}
shift 2
wayland=$(/usr/bin/sed -n 's/^WAYLAND_DISPLAY=//p' "$RIG/env")
display=$(/usr/bin/sed -n 's/^DISPLAY=//p' "$RIG/env")
bus=$(/usr/bin/sed -n 's/^DBUS_SESSION_BUS_ADDRESS=//p' "$RIG/env")
[[ $wayland =~ ^wayland-[0-9]+$ && $wayland != wayland-0 ]] || { echo "refusing Wayland display '$wayland'" >&2; exit 1; }
[[ $display =~ ^:[0-9]+$ && $display != :0 ]] || { echo "refusing X display '$display'" >&2; exit 1; }
[[ -n $bus ]] || { echo "the rig has no private D-Bus" >&2; exit 1; }
exec /usr/bin/systemd-run --user --scope --collect --quiet --unit="pkg328-$name-$$" -- \
    /usr/bin/env -u ARESOS_LAUNCH_NONCE -u ARESOS_DESKTOP_INSTANCE -u ARESOS_SHELL_SOCKET -u WAYLAND_SOCKET \
    -u WAYLAND_DEBUG WAYLAND_DISPLAY="$wayland" DISPLAY="$display" DBUS_SESSION_BUS_ADDRESS="$bus" RIG="$RIG" "$@"
