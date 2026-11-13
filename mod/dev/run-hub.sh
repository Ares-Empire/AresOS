#!/usr/bin/bash
# DEVELOPMENT AID, not part of the installed system: on AresOS, package 23's session supervisor (aresos-desktop)
# starts the app helper and the game, and replaces this script.
#
# Starts the AresOS app helper and then the mod's development client (`./gradlew runClient`, game folder mod/run/)
# on the owner's real screen, so that walking into a logo opens the app and closing it returns to the game.
# Run it from a terminal in the AresOS session. Extra arguments go to Gradle.
#
#   mod/dev/run-hub.sh [--force] [--helper <path>] [--registry <dir>] [gradle arguments...]
#
#   --helper <path>   the app helper to start (default /usr/libexec/aresos-shell), e.g. one from a worktree that
#                     is not in the image yet
#   --registry <dir>  its folder of app entries, passed to the helper's own --registry
#                     (default: the helper's, /usr/share/aresos/apps)
#   --force           skip the Lunar Client and 6 GB memory checks (otherwise exit 75)
#
# Like the supervisor, it gives the helper and the game the same desktop instance ID and launch nonce
# (ARESOS_DESKTOP_INSTANCE, ARESOS_LAUNCH_NONCE); the helper gets the session's environment with the system PATH
# and serves $XDG_RUNTIME_DIR/aresos/shell.sock, and the game gets the session's environment plus the RTX 4060
# offload variables. When the game exits, the helper this script started stops too. A helper already serving the
# socket is reused only if an earlier run of this script started it (it is then left running); any other helper
# stops this script with a sentence. Only one run at a time.
#
# It writes only to mod/run/ (the game), ~/.cache/aresos-dev/ (lock and helper log) and $XDG_RUNTIME_DIR/aresos/
# (socket, launch journal and this script's helper record), besides Gradle's own build output and caches.
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

RUNTIME="$XDG_RUNTIME_DIR/aresos"
SOCKET="$RUNTIME/shell.sock"
# "<pid> <start time> <instance> <nonce>" of the helper this script started; private like the socket.
RECORD="$RUNTIME/run-hub.helper"
HELPER_LOG="$ARESOS_DEV_CACHE/run-hub-helper.log"
# The session's PATH (package 21): what the supervisor gives the helper.
SYSTEM_PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin

/usr/bin/mkdir -p -- "$ARESOS_DEV_CACHE"
exec {lock_fd}>>"$ARESOS_DEV_CACHE/run-hub.lock"
/usr/bin/flock -n "$lock_fd" || aresos_fail 1 "run-hub.sh is already running; close that game first."

serving() { [[ -n $(/usr/bin/ss -xlH src "$SOCKET" 2>/dev/null) ]]; }

# Field 22 of /proc/<pid>/stat: with the PID it names one process, even after the PID is reused.
start_time() {
    local stat fields
    read -r stat 2>/dev/null <"/proc/$1/stat" || return 1
    stat=${stat##*) }
    read -r -a fields <<<"$stat"
    printf '%s\n' "${fields[19]}"
}

# True when the helper serving the socket is one an earlier run of this script started; sets its identity.
own_helper() {
    local pid started id secret
    [[ -r $RECORD ]] || return 1
    read -r pid started id secret <"$RECORD" || return 1
    [[ $pid =~ ^[0-9]+$ && -n $secret ]] || return 1
    [[ $(start_time "$pid" 2>/dev/null) == "$started" ]] || return 1
    serving || return 1
    helper_pid=$pid instance=$id nonce=$secret
}

new_token() { /usr/bin/head -c "$1" /dev/urandom | /usr/bin/base64 -w0 | /usr/bin/tr '+/' '-_' | /usr/bin/tr -d '='; }

helper_pid=
started_helper=0
aresos_cleanup() {
    [[ $started_helper == 1 ]] || return 0
    if [[ -n $helper_pid ]] && kill -0 "$helper_pid" 2>/dev/null; then
        kill -TERM "$helper_pid" 2>/dev/null || true
        local tries=0
        while kill -0 "$helper_pid" 2>/dev/null && ((tries++ < 50)); do /usr/bin/sleep 0.1; done
        kill -KILL "$helper_pid" 2>/dev/null || true
    fi
    /usr/bin/rm -f -- "$RECORD"
    aresos_say "Stopped the app helper (its log: $HELPER_LOG)."
}

if own_helper; then
    aresos_say "Reusing the app helper an earlier run-hub.sh started (PID $helper_pid); it stays running afterwards."
elif serving; then
    aresos_fail 1 "Another AresOS app helper is already serving $SOCKET and run-hub.sh did not start it; stop it first."
else
    instance="aresdesktop-dev-$(/usr/bin/od -An -N6 -tx1 /dev/urandom | /usr/bin/tr -d ' \n')"
    nonce=$(new_token 24)
    helper_args=()
    [[ -z $registry ]] || helper_args=(--registry "$registry")
    started_helper=1
    printf '\n--- %s run-hub.sh starts %s\n' "$(/usr/bin/date -Is)" "$helper" >>"$HELPER_LOG"
    # The supervisor's way: the session's environment without launch plumbing, the system PATH, the launch
    # identity in the environment (never on a command line), and SIGTERM when its parent (this script) dies.
    (
        unset ARESOS_SHELL_SOCKET ARESOS_SHELL_STATUS_FD NOTIFY_SOCKET LISTEN_FDS LISTEN_PID LISTEN_FDNAMES \
            WATCHDOG_PID WATCHDOG_USEC
        export PATH=$SYSTEM_PATH ARESOS_DESKTOP_INSTANCE=$instance ARESOS_LAUNCH_NONCE=$nonce
        exec {lock_fd}>&-
        exec /usr/bin/setpriv --pdeathsig TERM -- "$helper" "${helper_args[@]}"
    ) </dev/null >>"$HELPER_LOG" 2>&1 &
    helper_pid=$!
    tries=0
    until serving; do
        if ! kill -0 "$helper_pid" 2>/dev/null || ((tries++ >= 100)); then
            aresos_fail 1 "The app helper did not start serving $SOCKET; see $HELPER_LOG."
        fi
        /usr/bin/sleep 0.1
    done
    (umask 077 && printf '%s %s %s %s\n' "$helper_pid" "$(start_time "$helper_pid")" "$instance" "$nonce" >"$RECORD")
    aresos_say "App helper running (PID $helper_pid, desktop instance $instance, log $HELPER_LOG)."
fi

# The game: the session's environment, the same launch identity as the helper and the default socket.
unset ARESOS_SHELL_SOCKET
export ARESOS_DESKTOP_INSTANCE=$instance ARESOS_LAUNCH_NONCE=$nonce
if [[ -n $(/usr/bin/ls -A /proc/driver/nvidia/gpus 2>/dev/null) ]]; then
    export "${ARESOS_NVIDIA_OFFLOAD[@]}"
else
    aresos_say "No NVIDIA GPU found; the game renders on the default GPU."
fi
aresos_scoped aresos-dev-run-hub "${ARESOS_GRADLE[@]}" runClient "${gradle_args[@]}"
