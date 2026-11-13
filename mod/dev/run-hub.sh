#!/usr/bin/bash
# DEVELOPMENT AID, not part of the installed system: on AresOS, package 23's session supervisor (aresos-desktop)
# starts the app helper and the game, and replaces this script.
#
# Starts an AresOS app helper of its own and then the mod's development client (`./gradlew runClient`, game folder mod/run/)
# on the owner's real screen, so that walking into a logo opens the app and closing it returns to the game.
# Run it from a terminal in the AresOS session. Extra arguments go to Gradle.
#
#   mod/dev/run-hub.sh [--force] [--helper <path>] [--registry <dir>] [gradle arguments...]
#
#   --helper <path>   the app helper to start (default /usr/libexec/aresos-shell), e.g. one from a worktree that
#                     is not in the image yet
#   --registry <dir>  its folder of app entries, passed to the helper's own --registry
#                     (default: the helper's, /usr/share/aresos/apps)
#   --force           skip the Lunar Client and 6 GB memory checks (otherwise exit 75); they run at the start and
#                     again right before Gradle starts
#
# Gradle's --daemon, --stop and --status are refused (exit 2).
#
# Every run has a helper and a socket of its own: the private folder $XDG_RUNTIME_DIR/aresos-dev/run-hub-<pid>/
# (mode 0700) holds the socket and the helper's launch journal, and the game gets that socket in
# ARESOS_SHELL_SOCKET. It never uses $XDG_RUNTIME_DIR/aresos/shell.sock, where the session's own helper lives once
# package 23 is installed; while this script runs, that helper and this one then both watch the same windows,
# which is accepted for a development aid. Like the supervisor, it gives the helper and the game the same desktop
# instance ID and launch nonce (ARESOS_DESKTOP_INSTANCE, ARESOS_LAUNCH_NONCE). The helper gets the session's
# environment with the system PATH, the game the session's environment plus the RTX 4060 offload variables.
#
# The helper and the game each run in a systemd user scope of this script's own (env.sh). Every exit (the game
# closing, Ctrl+C, a closed terminal) stops both and removes the private folder; a helper is never reused. A
# folder left by an earlier run that died is removed at the start once no scope of that run exists. Only one run
# at a time.
#
# It writes only to mod/run/ (the game), ~/.cache/aresos-dev/ (lock and helper log) and its private folder,
# besides Gradle's own build output and caches.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"

usage="usage: run-hub.sh [--force] [--helper <path>] [--registry <dir>] [gradle arguments...]"
force=0
helper=/usr/libexec/aresos-shell
registry=
gradle_args=()
while (($#)); do
    case $1 in
        --force) force=1 ;;
        --helper)
            (($# >= 2)) || aresos_fail 2 "--helper needs a path; $usage"
            helper=$2
            shift ;;
        --registry)
            (($# >= 2)) || aresos_fail 2 "--registry needs a directory; $usage"
            registry=$2
            shift ;;
        --) shift; gradle_args+=("$@"); break ;;
        *) gradle_args+=("$1") ;;
    esac
    shift
done
aresos_check_gradle_args "${gradle_args[@]}"
[[ $helper == /* ]] || helper="$ARESOS_CALLER_DIR/$helper"
[[ -f $helper && -r $helper ]] || aresos_fail 2 "--helper $helper is not a readable regular file."
[[ -x $helper ]] || aresos_fail 2 "--helper $helper is not executable."
helper=$(/usr/bin/realpath -- "$helper")
if [[ -n $registry ]]; then
    [[ $registry == /* ]] || registry="$ARESOS_CALLER_DIR/$registry"
    [[ -d $registry && -r $registry && -x $registry ]] || aresos_fail 2 "--registry $registry is not a readable directory."
    registry=$(/usr/bin/realpath -- "$registry")
fi

[[ -n ${XDG_RUNTIME_DIR:-} && -d $XDG_RUNTIME_DIR ]] || aresos_fail 1 "XDG_RUNTIME_DIR is not set; run this from a terminal in the AresOS session."
[[ -n ${WAYLAND_DISPLAY:-} ]] || aresos_fail 1 "WAYLAND_DISPLAY is not set; run this from a terminal in the AresOS session."
aresos_find_java
aresos_check_room "$force"

PRIVATE="$XDG_RUNTIME_DIR/aresos-dev/run-hub-$$"
SOCKET="$PRIVATE/shell.sock"
HELPER_LOG="$ARESOS_DEV_CACHE/run-hub-helper.log"
# The session's PATH (package 21): what the supervisor gives the helper.
SYSTEM_PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin

/usr/bin/mkdir -p -- "$ARESOS_DEV_CACHE"
exec {lock_fd}>>"$ARESOS_DEV_CACHE/run-hub.lock"
/usr/bin/flock -n "$lock_fd" || aresos_fail 1 "run-hub.sh is already running; close that game first."

/usr/bin/mkdir -p -m 0700 -- "${PRIVATE%/*}"
for old in "${PRIVATE%/*}"/run-hub-*; do
    pid=${old##*-}
    [[ -d $old && $pid =~ ^[0-9]+$ ]] || continue
    if [[ -z $(/usr/bin/systemctl --user list-units --all --no-legend --plain "aresos-dev-*-$pid-*") ]]; then
        /usr/bin/rm -rf -- "$old"
    fi
done
/usr/bin/mkdir -m 0700 -- "$PRIVATE" 2>/dev/null || aresos_fail 1 "$PRIVATE still belongs to an earlier run; try again."
aresos_cleanup() {
    /usr/bin/rm -rf -- "$PRIVATE"
    aresos_say "Stopped the app helper (its log: $HELPER_LOG)."
}

new_token() { /usr/bin/head -c "$1" /dev/urandom | /usr/bin/base64 -w0 | /usr/bin/tr '+/' '-_' | /usr/bin/tr -d '='; }

# The launch identity goes to the helper and the game through the environment, never on a command line.
instance="aresdesktop-dev-$(/usr/bin/od -An -N6 -tx1 /dev/urandom | /usr/bin/tr -d ' \n')"
nonce=$(new_token 24)
export ARESOS_DESKTOP_INSTANCE=$instance ARESOS_LAUNCH_NONCE=$nonce
helper_args=(--socket "$SOCKET")
[[ -z $registry ]] || helper_args+=(--registry "$registry")
printf '\n--- %s run-hub.sh starts %s\n' "$(/usr/bin/date -Is)" "$helper" >>"$HELPER_LOG"
# The supervisor's way: the session's environment without launch plumbing, the system PATH, and SIGTERM if this
# script dies without its cleanup (SIGKILL).
aresos_scope_start run-hub-helper --property=TimeoutStopSec=5 -- /usr/bin/env -u ARESOS_SHELL_SOCKET \
    -u ARESOS_SHELL_STATUS_FD -u NOTIFY_SOCKET -u LISTEN_FDS -u LISTEN_PID -u LISTEN_FDNAMES -u WATCHDOG_PID \
    -u WATCHDOG_USEC PATH="$SYSTEM_PATH" /usr/bin/setpriv --pdeathsig TERM -- "$helper" "${helper_args[@]}" \
    </dev/null >>"$HELPER_LOG" 2>&1
helper_unit=$ARESOS_UNIT
# Only this run's helper can serve a socket in this run's private folder.
tries=0
until [[ -n $(/usr/bin/ss -xlH src "$SOCKET" 2>/dev/null) ]]; do
    /usr/bin/systemctl --user --quiet is-active "$helper_unit" && ((tries++ < 100)) \
        || aresos_fail 1 "The app helper did not start serving $SOCKET; see $HELPER_LOG."
    /usr/bin/sleep 0.1
done
/usr/bin/systemctl --user --quiet is-active "$helper_unit" || aresos_fail 1 "The app helper stopped; see $HELPER_LOG."
aresos_say "App helper running (desktop instance $instance, socket $SOCKET, log $HELPER_LOG)."

# Waiting for the helper took a moment: check again right before the game.
aresos_check_room "$force"
# The game: the session's environment, the same launch identity as the helper, this run's socket and the RTX 4060.
export ARESOS_SHELL_SOCKET=$SOCKET
if [[ -n $(/usr/bin/ls -A /proc/driver/nvidia/gpus 2>/dev/null) ]]; then
    export "${ARESOS_NVIDIA_OFFLOAD[@]}"
else
    aresos_say "No NVIDIA GPU found; the game renders on the default GPU."
fi
aresos_scoped run-hub-game -- "${ARESOS_GRADLE[@]}" runClient "${gradle_args[@]}"
