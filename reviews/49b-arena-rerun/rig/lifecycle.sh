mono() { python3 -I -c 'import time; print(time.monotonic_ns())'; }
mark() { echo "$1 $(mono)" >>"$RIG/marks.txt"; echo "$(date +%T) $1"; }
vin() { python3 -I "$here/input.py" "$RIG" "$@"; }
# Bash defers a trap during foreground sleep. Waiting on a child lets health failure interrupt it now.
sleep_pid=
sleep() { /usr/bin/sleep "$@" & sleep_pid=$!; wait "$sleep_pid"; sleep_pid=; }

finish() {
    local status=$?
    trap - EXIT
    trap '' INT TERM HUP USR1
    [[ -z $health ]] || { kill "$health" 2>/dev/null || true; wait "$health" 2>/dev/null || true; }
    [[ -z $sleep_pid ]] || { kill "$sleep_pid" 2>/dev/null || true; wait "$sleep_pid" 2>/dev/null || true; }
    if [[ $frozen == 1 ]]; then
        python3 -I "$here/scope.py" "$game" "$PKG49_GAME_UNIT" thaw "$RIG" || true
    fi
    [[ -z ${host_watch:-} ]] || { kill "$host_watch" 2>/dev/null || true; wait "$host_watch" 2>/dev/null || true; }
    [[ -z $sampler ]] || kill "$sampler" 2>/dev/null || true
    [[ -z $cover ]] || kill "$cover" 2>/dev/null || true
    if [[ -n $game && ! -f $RIG/terminal.json ]]; then
        python3 -I "$here/terminal.py" "$game" "$PKG49_GAME_UNIT" "$RIG" || status=1
    fi
    # Stop both owned scopes immediately; never wait for a dead input reader to end the game.
    timeout 2 systemctl --user stop --no-block "$PKG49_GAME_UNIT" "pkg49b-rig-$start_pid.scope" 2>/dev/null || true
    local unit state deadline=$((SECONDS + 15)) live
    while :; do
        live=0
        for unit in "$PKG49_GAME_UNIT" "pkg49b-rig-$start_pid.scope"; do
            state=$(timeout 2 systemctl --user show -P ActiveState "$unit" 2>/dev/null) || state=unknown
            case $state in inactive|failed) ;; *) live=1 ;; esac
        done
        ((live)) || break
        if ((SECONDS >= deadline)); then
            echo "owned scopes did not stop within 15 seconds" >&2
            status=1
            timeout 2 systemctl --user kill --signal=KILL "$PKG49_GAME_UNIT" "pkg49b-rig-$start_pid.scope" 2>/dev/null || true
            break
        fi
        /usr/bin/sleep .1
    done
    kill "$start_pid" 2>/dev/null || true
    wait "$start_pid" 2>/dev/null || true
    cp -f -- "$WT/mod/run/logs/latest.log" "$RIG/game.txt" 2>/dev/null || true
    python3 -I "$here/host.py" "$RIG/host-end.json" || true
    if ((status == 75)); then mv -- "$RIG" "$RIG-busy-$$"; fi
    if [[ ${finish_for_analysis:-0} != 1 ]]; then exit "$status"; fi
    return "$status"
}

rig_start() {
"$@" >"$RIG/start.txt" 2>&1 &
start_pid=$!
game=
sampler=
cover=
frozen=0
health=
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
trap 'echo "private input/compositor lost; aborting" >&2; exit 1' USR1
python3 -I "$here/health.py" "$RIG" "$$" "$start_pid" >"$RIG/health.txt" 2>&1 &
health=$!

}
