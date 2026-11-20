mono() { python3 -I -c 'import time; print(time.monotonic_ns())'; }
mark() { echo "$1 $(mono)" >>"$RIG/marks.txt"; echo "$(date +%T) $1"; }
vin() { python3 -I "$here/input.py" "$RIG" "$@"; }
# Bash defers a trap during foreground sleep. Waiting on a child lets health failure interrupt it now.
sleep_pid=
sleep() { /usr/bin/sleep "$@" & sleep_pid=$!; wait "$sleep_pid"; sleep_pid=; }
# Package 318: the only writes to the game's scope (scope.py) and its threads (rt.py). Named so the offline lifecycle
# test can put stand-ins in their place and never write a real cgroup.freeze.
rig_scope() { python3 -I "$here/scope.py" "$@"; }
rig_rt() { python3 -I "$here/rt.py" "$@"; }
rig_card() { python3 -I "$here/records.py" status "$RIG" "$1" || true; }

# Every thaw comes through here, on the normal return and in cleanup: the watcher (thaw.py) starts first and takes its
# first sample, then the thaw write. It keeps the pidfd until 60 s after the return request.
thaw_watcher=
rig_thaw() {
    if [[ -z $thaw_watcher ]]; then
        rm -f -- "$RIG/thaw-ready" "$RIG/thaw-sampled"
        python3 -I "$here/thaw.py" "$game" "$RIG" "${RT:-keep}" --hold "${PKG318_THAW_HOLD:-60}" >"$RIG/thaw.txt" 2>&1 &
        thaw_watcher=$!
        local i
        for ((i = 0; i < 300; i++)); do
            [[ -e $RIG/thaw-ready ]] && break
            kill -0 "$thaw_watcher" 2>/dev/null || break
            /usr/bin/sleep .01
        done
    fi
    rig_scope "$game" "$PKG49_GAME_UNIT" thaw "$RIG"
}
# Wait (interruptibly) until the watcher's 10 ms sampling ends or the watcher ends.
wait_thaw_sampling() {
    while [[ -n $thaw_watcher && ! -e $RIG/thaw-sampled ]] && kill -0 "$thaw_watcher" 2>/dev/null; do sleep .1; done
}
# RT=demote with a thread of the game still realtime at the thaw: the run doesn't count. It is thawed and recorded like
# any other, then stopped.
invalid() {
    mark invalid
    python3 -I -c 'import json, sys, time; json.dump({"monotonic_ns": time.monotonic_ns(), "reason": sys.argv[2]}, open(sys.argv[1], "w"))' \
        "$RIG/invalid.json" "$1"
    echo "INVALID: $1" >&2
    wait_thaw_sampling
    exit 3
}

# The return from a freeze: check the policies just before the thaw, thaw through the watcher, stop an INVALID run.
rig_return_thaw() {
    rig_card pre-thaw
    local rt_status=0
    rig_rt check "$game" "$PKG49_GAME_UNIT" "$RIG" "${RT:-keep}" || rt_status=$?
    ((rt_status == 0 || rt_status == 3)) || exit "$rt_status"
    rig_thaw
    frozen=0
    ((rt_status == 0)) || invalid "a thread of the game was still realtime at the thaw (RT=${RT:-keep})"
}
# Hold the game until the watcher's deadline (60 s after the return request), so a survivor is recorded alive then.
rig_hold() {
    [[ -n $thaw_watcher ]] || return 0
    wait "$thaw_watcher" || true
    thaw_watcher=
    mark held
}

finish() {
    local status=$?
    trap - EXIT
    trap '' INT TERM HUP USR1
    # First: the exit watcher compares the game's exit with this mark (a death after it doesn't count).
    mark cleanup_start || true
    [[ -z $health ]] || { kill "$health" 2>/dev/null || true; wait "$health" 2>/dev/null || true; }
    [[ -z $sleep_pid ]] || { kill "$sleep_pid" 2>/dev/null || true; wait "$sleep_pid" 2>/dev/null || true; }
    if [[ $frozen == 1 ]]; then
        rig_thaw || true
    fi
    [[ -z ${host_watch:-} ]] || { kill "$host_watch" 2>/dev/null || true; wait "$host_watch" 2>/dev/null || true; }
    [[ -z $sampler ]] || kill "$sampler" 2>/dev/null || true
    [[ -z $cover ]] || kill "$cover" 2>/dev/null || true
    if [[ -n $game && ! -f $RIG/terminal.json ]]; then
        python3 -I "$here/terminal.py" "$game" "$PKG49_GAME_UNIT" "$RIG" || status=1
    fi
    # Stop both owned scopes immediately; never wait for a dead input reader to end the game.
    timeout 2 systemctl --user stop --no-block "$PKG49_GAME_UNIT" "pkg318-rig-$start_pid.scope" 2>/dev/null || true
    local unit state deadline=$((SECONDS + 15)) live
    while :; do
        live=0
        for unit in "$PKG49_GAME_UNIT" "pkg318-rig-$start_pid.scope"; do
            state=$(timeout 2 systemctl --user show -P ActiveState "$unit" 2>/dev/null) || state=unknown
            case $state in inactive|failed) ;; *) live=1 ;; esac
        done
        ((live)) || break
        if ((SECONDS >= deadline)); then
            echo "owned scopes did not stop within 15 seconds" >&2
            status=1
            timeout 2 systemctl --user kill --signal=KILL "$PKG49_GAME_UNIT" "pkg318-rig-$start_pid.scope" 2>/dev/null || true
            break
        fi
        /usr/bin/sleep .1
    done
    kill "$start_pid" 2>/dev/null || true
    wait "$start_pid" 2>/dev/null || true
    # The game is gone with its scope, so the watcher records that exit and ends; bounded all the same.
    if [[ -n $thaw_watcher ]]; then
        local waited
        for ((waited = 0; waited < 100; waited++)); do kill -0 "$thaw_watcher" 2>/dev/null || break; /usr/bin/sleep .1; done
        kill "$thaw_watcher" 2>/dev/null || true
        wait "$thaw_watcher" 2>/dev/null || true
        thaw_watcher=
    fi
    cp -f -- "$WT/mod/run/logs/latest.log" "$RIG/game.txt" 2>/dev/null || true
    python3 -I "$here/host.py" "$RIG/host-end.json" || true
    # Journal and card records, and the public copies, on every exit path (a game death never reaches analyze.py).
    if ((status != 75)) && [[ -n ${OUT:-} ]]; then python3 -I "$here/records.py" final "$RIG" "$OUT" || true; fi
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
