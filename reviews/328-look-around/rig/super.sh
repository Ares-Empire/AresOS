#!/usr/bin/bash
# Package 328 rig: Super, as the supervisor's `aresos-desktop search` sends it: SIGUSR1 to the rig's own helper. The
# helper then activates the world's window and sends the mod shell_search. Only a helper whose socket lies in this
# rig's run-hub.sh folder is signalled, never the session's own aresos-shell.
#
#   super.sh <run folder>
RIG=${1:?usage: super.sh <run folder>}
runhub=$(/usr/bin/sed -n 's/^RUNHUB_PID=//p' "$RIG/env")
[[ $runhub =~ ^[0-9]+$ ]] || { echo "the rig's game is not running" >&2; exit 1; }
for pid in $(/usr/bin/pgrep -f -- "$RIG/helper|aresos-shell --socket $XDG_RUNTIME_DIR/aresos-dev/run-hub-$runhub/"); do
    if /usr/bin/tr '\0' ' ' <"/proc/$pid/cmdline" | /usr/bin/grep -q -- "--socket $XDG_RUNTIME_DIR/aresos-dev/run-hub-$runhub/shell.sock"; then
        kill -USR1 "$pid" && echo "Super sent to the rig's helper $pid"
        exit 0
    fi
done
echo "the rig's helper was not found" >&2
exit 1
