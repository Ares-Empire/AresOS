# DEVELOPMENT AID of package 25 (the real-game check; copied from package 49b's rig): the controller's start and cleanup.
# Sourced by check.sh. Package 49b's lifecycle.sh without its measurement parts (sampler, cover, freezer, host notes),
# plus the end of the test supervisor and its stand-ins (check.py sweep).
mono() { python3 -I -c 'import time; print(time.monotonic_ns())'; }
mark() { echo "$1 $(mono)" >>"$RIG/marks.txt"; echo "$(date +%T) $1"; }
# Bash defers a trap during foreground sleep. Waiting on a child lets health failure interrupt it now.
sleep_pid=
sleep() { /usr/bin/sleep "$@" & sleep_pid=$!; wait "$sleep_pid"; sleep_pid=; }

finish() {
    local status=$?
    trap - EXIT
    trap '' INT TERM HUP USR1
    [[ -z $health ]] || { kill "$health" 2>/dev/null || true; wait "$health" 2>/dev/null || true; }
    [[ -z $sleep_pid ]] || { kill "$sleep_pid" 2>/dev/null || true; wait "$sleep_pid" 2>/dev/null || true; }
    # Stop both owned scopes immediately; never wait for a dead input reader to end the game.
    timeout 2 systemctl --user stop --no-block "$PKG25_GAME_UNIT" "pkg25-rig-$start_pid.scope" 2>/dev/null || true
    local unit state deadline=$((SECONDS + 15)) live
    while :; do
        live=0
        for unit in "$PKG25_GAME_UNIT" "pkg25-rig-$start_pid.scope"; do
            state=$(timeout 2 systemctl --user show -P ActiveState "$unit" 2>/dev/null) || state=unknown
            case $state in inactive|failed) ;; *) live=1 ;; esac
        done
        ((live)) || break
        if ((SECONDS >= deadline)); then
            echo "owned scopes did not stop within 15 seconds" >&2
            status=1
            timeout 2 systemctl --user kill --signal=KILL "$PKG25_GAME_UNIT" "pkg25-rig-$start_pid.scope" 2>/dev/null || true
            break
        fi
        /usr/bin/sleep .1
    done
    kill "$start_pid" 2>/dev/null || true
    wait "$start_pid" 2>/dev/null || true
    # The test supervisor and its stand-ins: only processes whose own environment names this run's runtime folder.
    python3 -I -B "$here/check.py" sweep "$RIG" || status=1
    cp -f -- "$WT/mod/run/logs/latest.log" "$RIG/game.txt" 2>/dev/null || true
    # The runtime folder held the launch's nonce and the supervisor's socket: it ends with the run.
    rm -rf -- "$RIG/rt" "$RIG/private"
    if ((status == 75)); then mv -- "$RIG" "$RIG-busy-$$"; fi
    exit "$status"
}

rig_start() {
"$@" >"$RIG/start.txt" 2>&1 &
start_pid=$!
game=
health=
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
trap 'echo "private input/compositor lost; aborting" >&2; exit 1' USR1
python3 -I "$here/health.py" "$RIG" "$$" "$start_pid" >"$RIG/health.txt" 2>&1 &
health=$!
}
