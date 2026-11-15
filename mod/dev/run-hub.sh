#!/usr/bin/bash
# DEVELOPMENT AID, not part of the installed system: on AresOS, package 23's session supervisor (aresos-desktop)
# starts the app helper and the game, and replaces this script.
#
# Starts an AresOS app helper of its own and then the mod's development client (`./gradlew runClient`, game folder mod/run/)
# on the owner's real screen, so that walking into a logo opens the app and closing it returns to the game.
# Run it from a terminal in the AresOS session. Extra arguments go to Gradle.
#
#   mod/dev/run-hub.sh [--force] [--session] [--helper <path>] [--registry <dir>] [gradle arguments...]
#
#   --session         show it as the AresOS session will (package 40): the helper and the game run inside a labwc of
#                     their own with the checkout's os/config/usr/share/aresos/labwc/rc.xml, shown fullscreen on this
#                     desktop. Without it the game is an ordinary window here. See "The session preview" below.
#   --helper <path>   the app helper to start (default /usr/libexec/aresos-shell), e.g. one from a worktree that
#                     is not in the image yet
#   --registry <dir>  its folder of app entries, passed to the helper's own --registry
#                     (default: the helper's, /usr/share/aresos/apps)
#   --force           skip the Lunar Client and 6 GB memory checks (otherwise exit 75); they run at the start and
#                     again right before Gradle starts
#
# Gradle's --daemon, --foreground, --stop and --status are refused (exit 2).
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
# It writes only to mod/run/ (the game), ~/.cache/aresos-dev/ (lock, helper log and the preview's log) and its private
# folder, besides Gradle's own build output and caches.
#
# The session preview (--session). A labwc of this run's own (the wlroots Wayland backend: one window on this
# desktop) gets a copy of the checkout's rc.xml in the private folder and nothing else of the session's labwc folder
# (its autostart would start the session's own supervisor). preview-window.py asks this desktop to show that window
# fullscreen (wlr foreign-toplevel; labwc does it, another desktop may not) and reports when the window closes. The
# helper and the game get that labwc's Wayland socket, Xwayland display and PID instead of this desktop's; the game
# window is then the maximized, frameless, always-on-bottom desktop window of the session, and apps open over it.
# Closing the game, Ctrl+C here, or closing the preview window stops all of it; closing the window first asks the
# game to save and quit, as its close button would. The run also ends when the preview's labwc has no screen left
# (preview-window.py --outputs), so closing the preview ends it even where the watcher never found its window. The
# preview's labwc and the watchers do not get the launch identity: a terminal started from labwc's own menu, and a
# development client started in it, must not take themselves for the session. What it cannot show:
#   - Keys this desktop binds itself reach it first, whatever has the focus: on AresOS Alt+Tab (switches this
#     desktop's windows, the preview being one), Alt+F4 (closes the whole preview window, and with it the preview),
#     Super+Ctrl+Escape (this desktop's recovery terminal). labwc offers no way to hand them on. In the preview,
#     close an app with its own X and switch apps by clicking.
#   - A program that allows one copy and already runs on this desktop hands the request to that copy, whose window
#     opens out here: the preview's helper sees no window of it and says so after its open deadline.
#   - Whatever goes through this desktop's D-Bus session opens out here too: the polkit password prompt, portal
#     dialogs (file choosers), notifications.
#   - One screen only (the preview is one window on the screen it opens on): the world on an external monitor and
#     "covered" per screen are not shown. No package 23 supervisor (no restart, no recovery terminal), and the
#     development client instead of Prism's.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"

usage="usage: run-hub.sh [--force] [--session] [--helper <path>] [--registry <dir>] [gradle arguments...]"
force=0
session=0
helper=/usr/libexec/aresos-shell
registry=
gradle_args=()
while (($#)); do
    case $1 in
        --force) force=1 ;;
        --session) session=1 ;;
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

rc_xml=$(/usr/bin/realpath -m -- "$ARESOS_MOD_DIR/../os/config/usr/share/aresos/labwc/rc.xml")
if ((session)); then
    [[ -f $rc_xml && -r $rc_xml ]] || aresos_fail 2 "--session needs the checkout's labwc configuration, $rc_xml."
    [[ -x /usr/bin/labwc ]] || aresos_fail 1 "--session needs labwc (/usr/bin/labwc)."
    # labwc splits its startup command like a shell; these paths go into it in single quotes.
    [[ $ARESOS_MOD_DIR != *\'* && ${XDG_RUNTIME_DIR:-} != *\'* ]] \
        || aresos_fail 2 "--session cannot run from a folder whose path has a single quote in it."
fi

[[ -n ${XDG_RUNTIME_DIR:-} && -d $XDG_RUNTIME_DIR ]] || aresos_fail 1 "XDG_RUNTIME_DIR is not set; run this from a terminal in the AresOS session."
[[ -n ${WAYLAND_DISPLAY:-} ]] || aresos_fail 1 "WAYLAND_DISPLAY is not set; run this from a terminal in the AresOS session."
aresos_find_java
aresos_check_room "$force"

PRIVATE="$XDG_RUNTIME_DIR/aresos-dev/run-hub-$$"
SOCKET="$PRIVATE/shell.sock"
HELPER_LOG="$ARESOS_DEV_CACHE/run-hub-helper.log"
SESSION_LOG="$ARESOS_DEV_CACHE/run-hub-session.log"
# The session's PATH (package 21): what the supervisor gives the helper.
SYSTEM_PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin

/usr/bin/mkdir -p -- "$ARESOS_DEV_CACHE"
exec {lock_fd}>>"$ARESOS_DEV_CACHE/run-hub.lock"
/usr/bin/flock -n "$lock_fd" || aresos_fail 1 "run-hub.sh is already running; close that game first."

/usr/bin/mkdir -p -m 0700 -- "${PRIVATE%/*}"
for old in "${PRIVATE%/*}"/run-hub-*; do
    pid=${old##*-}
    [[ -d $old && $pid =~ ^[0-9]+$ ]] || continue
    deadline=$((SECONDS + 30))
    while ! units=$(systemctl --user list-units --all --no-legend --plain "aresos-dev-*-$pid-*"); do
        ((SECONDS < deadline)) || aresos_fail 1 "FAILED: scopes not confirmed gone after 30 s: aresos-dev-*-$pid-*; keeping $old."
        /usr/bin/sleep 0.5
    done
    if [[ -z $units ]]; then
        /usr/bin/rm -rf -- "$old"
    fi
done
/usr/bin/mkdir -m 0700 -- "$PRIVATE" 2>/dev/null || aresos_fail 1 "$PRIVATE still belongs to an earlier run; try again."
aresos_cleanup() {
    /usr/bin/rm -rf -- "$PRIVATE"
    aresos_say "Stopped the app helper (its log: $HELPER_LOG)."
}

# --session: starts the preview's labwc, the watcher of its window on this desktop and the watcher of its screens, and
# sets nested_env to the variables that point a program at that labwc instead of this desktop.
nested_env=()
nested_wayland=
labwc_job=
window_job=
outputs_job=
# Neither the preview's labwc nor its watchers get the launch identity (exported below for the helper and the game).
no_identity=(-u ARESOS_DESKTOP_INSTANCE -u ARESOS_LAUNCH_NONCE)
start_session() {
    local config="$PRIVATE/labwc" found="$PRIVATE/nested.env" ready="$PRIVATE/window.ready" tries=0 wayland display pid
    /usr/bin/mkdir -m 0700 -- "$config"
    /usr/bin/cp -- "$rc_xml" "$config/rc.xml"
    printf '\n--- %s run-hub.sh --session starts labwc with %s\n' "$(/usr/bin/date -Is)" "$rc_xml" >>"$SESSION_LOG"
    # The watcher lists this desktop's windows first, so the next new labwc window is the preview's.
    aresos_scope_start run-hub-window -- /usr/bin/env "${no_identity[@]}" /usr/bin/python3 -I \
        "$ARESOS_MOD_DIR/dev/preview-window.py" "$ready" </dev/null >>"$SESSION_LOG" 2>&1
    window_job=$ARESOS_JOB
    until [[ -e $ready ]]; do
        if ! aresos_job_running "$window_job" || ((tries++ >= 50)); then
            aresos_say "The preview cannot cover the screen (see $SESSION_LOG); it opens as a window."
            break
        fi
        /usr/bin/sleep 0.1
    done
    # Nested on this desktop. LABWC_UPDATE_ACTIVATION_ENV=0: never hand this desktop's D-Bus and systemd user
    # environment the preview's displays (labwc leaves them alone when nested anyway; this makes it certain). No
    # LABWC_FALLBACK_OUTPUT: a stand-in screen would keep the preview going after its window closed.
    aresos_scope_start run-hub-labwc -- /usr/bin/env "${no_identity[@]}" -u DISPLAY -u WAYLAND_SOCKET -u LABWC_PID \
        -u LABWC_FALLBACK_OUTPUT WLR_BACKENDS=wayland LABWC_UPDATE_ACTIVATION_ENV=0 PATH="$SYSTEM_PATH" \
        /usr/bin/labwc --config-dir "$config" \
        --startup "'$ARESOS_MOD_DIR/dev/preview-env.sh' '$found'" </dev/null >>"$SESSION_LOG" 2>&1
    labwc_job=$ARESOS_JOB
    tries=0
    until [[ -s $found ]]; do
        aresos_job_running "$labwc_job" && ((tries++ < 150)) \
            || aresos_fail 1 "The preview's labwc did not start; see $SESSION_LOG."
        /usr/bin/sleep 0.1
    done
    wayland=$(/usr/bin/sed -n 's/^WAYLAND_DISPLAY=//p' "$found")
    display=$(/usr/bin/sed -n 's/^DISPLAY=//p' "$found")
    pid=$(/usr/bin/sed -n 's/^LABWC_PID=//p' "$found")
    [[ $wayland =~ ^wayland-[0-9]+$ && $wayland != "${WAYLAND_DISPLAY:-}" ]] \
        || aresos_fail 1 "The preview's labwc reported no Wayland socket of its own ('$wayland'); see $SESSION_LOG."
    [[ $display =~ ^:[0-9]+$ && $display != "${DISPLAY:-}" ]] \
        || aresos_fail 1 "The preview's labwc reported no Xwayland display of its own ('$display'); see $SESSION_LOG."
    [[ $pid =~ ^[0-9]+$ ]] || aresos_fail 1 "The preview's labwc reported no PID; see $SESSION_LOG."
    # LABWC_PID too: `labwc --exit` in a terminal opened in the preview must end the preview, not this desktop.
    nested_env=(WAYLAND_DISPLAY="$wayland" DISPLAY="$display" LABWC_PID="$pid")
    nested_wayland=$wayland
    # Its window on this desktop closing takes its only screen away; the run ends then (wait_session).
    aresos_scope_start run-hub-outputs -- /usr/bin/env "${no_identity[@]}" "${nested_env[@]}" /usr/bin/python3 -I \
        "$ARESOS_MOD_DIR/dev/preview-window.py" --outputs --display "$wayland" </dev/null >>"$SESSION_LOG" 2>&1
    outputs_job=$ARESOS_JOB
    aresos_say "Session preview running in labwc $pid ($wayland, $display; its log: $SESSION_LOG)."
}

# --session: the preview's window is gone but its labwc still runs: close the game's window there, as its close button
# would, so it saves the world and quits; after 60 s the cleanup stops what is left.
close_game() {
    local tries=0
    /usr/bin/env "${nested_env[@]}" /usr/bin/python3 -I "$ARESOS_MOD_DIR/dev/preview-window.py" --close aresos-desktop \
        --display "$nested_wayland" </dev/null >>"$SESSION_LOG" 2>&1 || return 0
    while aresos_job_running "$game_job" && ((tries++ < 120)); do /usr/bin/sleep 0.5; done
}

# --session: waits for the game, and stops when the preview's labwc ends, its window is closed or it has no screen left.
wait_session() {
    local ended status
    while :; do
        status=0
        ended=
        wait -n -p ended "$game_job" "$labwc_job" ${window_job:+"$window_job"} ${outputs_job:+"$outputs_job"} \
            || status=$?
        case $ended in
            "$game_job") return "$status" ;;
            "$labwc_job") aresos_say "The preview's labwc stopped (status $status; its log: $SESSION_LOG)."; return 1 ;;
            "$window_job")
                window_job=
                if ((status == 0)); then
                    aresos_say "The preview window was closed; asking the game to save and quit."
                    close_game
                    return 0
                fi ;;  # it could not cover the screen: the preview stays a window
            "$outputs_job")
                outputs_job=
                if ((status == 0)); then
                    aresos_say "The preview has no screen left; asking the game to save and quit."
                    close_game
                    return 0
                fi ;;  # it lost that labwc: the labwc's own end stops the run
        esac
    done
}

new_token() { /usr/bin/head -c "$1" /dev/urandom | /usr/bin/base64 -w0 | /usr/bin/tr '+/' '-_' | /usr/bin/tr -d '='; }

# The launch identity goes to the helper and the game through the environment, never on a command line.
instance="aresdesktop-dev-$(/usr/bin/od -An -N6 -tx1 /dev/urandom | /usr/bin/tr -d ' \n')"
nonce=$(new_token 24)
export ARESOS_DESKTOP_INSTANCE=$instance ARESOS_LAUNCH_NONCE=$nonce
helper_args=(--socket "$SOCKET")
[[ -z $registry ]] || helper_args+=(--registry "$registry")
((session == 0)) || start_session
printf '\n--- %s run-hub.sh starts %s\n' "$(/usr/bin/date -Is)" "$helper" >>"$HELPER_LOG"
# The supervisor's way: the session's environment without launch plumbing, the system PATH, and SIGTERM if this
# script dies without its cleanup (SIGKILL).
aresos_scope_start run-hub-helper --property=TimeoutStopSec=5 -- /usr/bin/env -u ARESOS_SHELL_SOCKET \
    -u ARESOS_SHELL_STATUS_FD -u NOTIFY_SOCKET -u LISTEN_FDS -u LISTEN_PID -u LISTEN_FDNAMES -u WATCHDOG_PID \
    -u WATCHDOG_USEC PATH="$SYSTEM_PATH" "${nested_env[@]}" /usr/bin/setpriv --pdeathsig TERM -- "$helper" "${helper_args[@]}" \
    </dev/null >>"$HELPER_LOG" 2>&1
helper_unit=$ARESOS_UNIT
# Only this run's helper can serve a socket in this run's private folder.
tries=0
until [[ -n $(/usr/bin/ss -xlH src "$SOCKET" 2>/dev/null) ]]; do
    systemctl --user --quiet is-active "$helper_unit" && ((tries++ < 100)) \
        || aresos_fail 1 "The app helper did not start serving $SOCKET; see $HELPER_LOG."
    /usr/bin/sleep 0.1
done
systemctl --user --quiet is-active "$helper_unit" || aresos_fail 1 "The app helper stopped; see $HELPER_LOG."
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
if ((session == 0)); then
    aresos_scoped run-hub-game -- "${ARESOS_GRADLE[@]}" runClient "${gradle_args[@]}"
    exit
fi
export "${nested_env[@]}"
aresos_scope_start run-hub-game -- "${ARESOS_GRADLE[@]}" runClient "${gradle_args[@]}"
game_job=$ARESOS_JOB
wait_session
