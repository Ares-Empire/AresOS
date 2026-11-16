#!/usr/bin/sh
# DEVELOPMENT AID for run-hub.sh --session: the nested labwc runs this as its startup command. It writes where that
# compositor's clients connect (its Wayland socket, its Xwayland display) and its PID to the file $1, for run-hub.sh
# to start the app helper and the game there.
set -eu
printf 'WAYLAND_DISPLAY=%s\nDISPLAY=%s\nLABWC_PID=%s\n' "${WAYLAND_DISPLAY:?}" "${DISPLAY:-}" "${LABWC_PID:-}" >"$1.tmp"
/usr/bin/mv -f -- "$1.tmp" "$1"
