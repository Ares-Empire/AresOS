# shellcheck shell=bash
# Shared setup for the mod's Linux development scripts (build.sh, client-test.sh, run-hub.sh). Sourced, not run.
#
# It finds Java 25 without touching the shell's PATH or ~/.bashrc, and holds the checks that keep a run from
# disturbing the owner or the other sessions on this laptop: the memory floor, his own Minecraft (Lunar Client)
# and the one-client-test-at-a-time lock. It also owns everything a script starts: every process runs in a
# systemd user scope that the script created and named, and every exit stops those scopes. The scripts run from
# mod/, whatever the caller's directory.

ARESOS_CALLER_DIR=$PWD
ARESOS_MOD_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
ARESOS_DEV_CACHE="$HOME/.cache/aresos-dev"
# Fixed: other sessions on the laptop use the same lock and the same memory floor (brief 29).
ARESOS_CLIENT_TEST_LOCK="$ARESOS_DEV_CACHE/client-test.lock"
ARESOS_MIN_AVAILABLE_KIB=$((6 * 1024 * 1024))
# "Not now": too little memory, or the owner's game is running. Retrying later may succeed.
ARESOS_EXIT_BUSY=75
# Renders one process on the RTX 4060 (PRIME render offload), the same set package 23's supervisor gives the game.
ARESOS_NVIDIA_OFFLOAD=(__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __VK_LAYER_NV_optimus=NVIDIA_only)

cd -- "$ARESOS_MOD_DIR"

# Messages go to the caller's stderr even while a call's own stderr is redirected (a log, /dev/null), which is
# where a signal during that call would otherwise send the cleanup's messages.
exec {ARESOS_STDERR}>&2
aresos_say() { printf '%s: %s\n' "${0##*/}" "$*" >&"$ARESOS_STDERR"; }

# aresos_fail <exit code> <sentence>
aresos_fail() {
    local code=$1
    shift
    aresos_say "$*"
    exit "$code"
}

# Prints the feature version of the JDK in $1 (25 for 25.0.5), or nothing when it is not a usable JDK.
aresos_jdk_major() {
    local home=$1 out
    [[ -x $home/bin/java && -x $home/bin/javac ]] || return 0
    out=$("$home/bin/java" -version 2>&1) || return 0
    if [[ $out =~ version\ \"([0-9]+) ]]; then printf '%s\n' "${BASH_REMATCH[1]}"; fi
}

# Exports JAVA_HOME: the caller's if it is a Java 25 JDK, otherwise ~/.local/opt/jdk-25.
aresos_find_java() {
    local own=${JAVA_HOME:-} home="$HOME/.local/opt/jdk-25"
    if [[ -n $own && $(aresos_jdk_major "$own") == 25 ]]; then
        export JAVA_HOME=$own
        return 0
    fi
    if [[ $(aresos_jdk_major "$home") == 25 ]]; then
        [[ -z $own ]] || aresos_say "JAVA_HOME ($own) is not a Java 25 JDK; using $home instead."
        export JAVA_HOME=$home
        return 0
    fi
    aresos_fail 1 "No Java 25 JDK found: set JAVA_HOME to one, or unpack Temurin 25 as ~/.local/opt/jdk-25 (mod/README.md, On Linux)."
}

# PIDs of the owner's own Minecraft: a Java process whose executable lives under ~/.lunarclient (the Lunar Client
# game, run by Lunar's own Java runtime). Its launcher and other programs there do not count. Only /proc is read.
# Matching command lines instead would also match the shell running this check.
aresos_lunar_game_pids() {
    local real
    real=$(cd -- "$HOME" && pwd -P)
    /usr/bin/find /proc -mindepth 2 -maxdepth 2 -name exe \
        \( -lname "$HOME/.lunarclient/*/bin/java" -o -lname "$real/.lunarclient/*/bin/java" \) -printf '%h\n' \
        2>/dev/null | /usr/bin/sed 's|^/proc/||' || true
}

aresos_available_kib() {
    /usr/bin/awk '$1 == "MemAvailable:" { print $2 }' /proc/meminfo
}

# Refuses (exit 75, one sentence) while the owner's game runs or less than 6 GB of memory is available. $1 = 1 skips.
aresos_check_room() {
    local force=$1 pids kib
    if [[ $force == 1 ]]; then
        aresos_say "--force: not checking for Lunar Client or free memory."
        return 0
    fi
    pids=$(aresos_lunar_game_pids)
    if [[ -n $pids ]]; then
        aresos_fail "$ARESOS_EXIT_BUSY" "The owner's Minecraft (Lunar Client, PID ${pids//$'\n'/, }) is running; try again once it has closed, or pass --force."
    fi
    kib=$(aresos_available_kib)
    if ((kib < ARESOS_MIN_AVAILABLE_KIB)); then
        aresos_fail "$ARESOS_EXIT_BUSY" "Only $((kib / 1048576)).$((kib % 1048576 * 10 / 1048576)) GB of memory is available and a run needs 6 GB; try again later, or pass --force."
    fi
}

# The Gradle wrapper without a lasting daemon. Gradle forks a single-use daemon for this build's JVM settings and
# stops it when the build ends. A shared daemon would outlive the run, and `gradlew --stop` would stop every
# daemon of this Gradle version on the laptop, including other sessions' builds in other worktrees.
ARESOS_GRADLE=("$ARESOS_MOD_DIR/gradlew" --no-daemon)

# Refuses Gradle's own daemon switches among the forwarded arguments: --daemon would win over --no-daemon (Gradle
# takes the last of the two), --foreground starts a daemon that other sessions' builds could use, and --stop and
# --status act on every daemon of this Gradle version on the laptop.
aresos_check_gradle_args() {
    local arg
    for arg; do
        case $arg in
            --daemon | -daemon | --foreground | -foreground | --stop | -stop | --status | -status)
                aresos_fail 2 "Gradle's $arg is refused: these scripts run Gradle without a lasting daemon and leave other sessions' daemons alone." ;;
        esac
    done
}

# Everything a script starts runs in a systemd user scope that the script created and named
# (aresos-dev-<name>-<pid>-<random>.scope). A script stops things only by stopping its own scopes: never by a
# remembered PID, which may belong to another process by then, and never something an earlier run left behind.
ARESOS_SCOPES=()
ARESOS_DEFER=0
ARESOS_PENDING=0

# True while the background job with this PID has not ended (bash's own job table, so a reused PID never counts).
aresos_job_running() {
    local pid
    for pid in $(jobs -rp); do [[ $pid != "$1" ]] || return 0; done
    return 1
}

# aresos_scope_start <name> [systemd-run options...] -- <command...>: starts the command in the background in a
# new scope of this script and returns once that scope exists (or the command has already ended). Sets
# ARESOS_UNIT to the scope and ARESOS_JOB to the job, which is only ever waited for. A stop sends TERM to
# everything in the scope and KILL to what is left 20 s later (TimeoutStopSec; an option may set another).
aresos_scope_start() {
    local deadline=$((SECONDS + 15))
    ARESOS_UNIT="aresos-dev-$1-$$-$SRANDOM.scope"
    shift
    # systemd-run creates the scope before it starts the command in it, so a stop by name before then would miss
    # a command that is about to start. A signal until the scope exists is held, then acted on below.
    ARESOS_DEFER=1
    ARESOS_SCOPES+=("$ARESOS_UNIT")
    systemd-run --user --scope --quiet --collect --unit="$ARESOS_UNIT" --property=TimeoutStopSec=20 "$@" &
    ARESOS_JOB=$!
    while aresos_job_running "$ARESOS_JOB" && ! systemctl --user --quiet is-active "$ARESOS_UNIT"; do
        if ((SECONDS >= deadline)); then
            # This is still our live launcher job. Reap it before cleanup so it cannot launch a command later.
            kill -KILL "$ARESOS_JOB" 2>/dev/null || true
            wait "$ARESOS_JOB" 2>/dev/null || true
            ARESOS_DEFER=0
            aresos_say "Scope $ARESOS_UNIT did not activate within 15 s; cancelled its launcher."
            exit "$((ARESOS_PENDING == 0 ? 1 : ARESOS_PENDING))"
        fi
        /usr/bin/sleep 0.02
    done
    ARESOS_DEFER=0
    ((ARESOS_PENDING == 0)) || exit "$ARESOS_PENDING"
}

# aresos_stop_scopes <unit...>: stops these scopes of this script and returns once they are gone. systemd sends
# TERM once to what is in a scope at that moment, so a process started just after it (cage starting its client
# while it had the TERM held for its event loop, Gradle forking a JVM) would run on until the KILL; everything
# still in a scope therefore gets TERM again every half second.
aresos_stop_scopes() {
    local unit state live deadline=$((SECONDS + 30))
    while :; do
        systemctl --user stop --no-block -- "$@" 2>/dev/null || true
        live=()
        for unit; do
            if state=$(systemctl --user show --property=ActiveState --value -- "$unit" 2>/dev/null); then
                case $state in inactive | failed) continue ;; esac
            fi
            live+=("$unit")
        done
        ((${#live[@]})) || return 0
        if ((SECONDS >= deadline)); then
            # Absence is unknown: leave private folders intact, and do not repeat cleanup on EXIT.
            trap - EXIT
            aresos_fail 1 "FAILED: scopes not confirmed gone after 30 s: ${live[*]}."
        fi
        /usr/bin/sleep 0.5
        systemctl --user kill --signal=TERM -- "${live[@]}" 2>/dev/null || true
    done
}

# aresos_scoped <name> [systemd-run options...] -- <command...>: aresos_scope_start, then waits for the command and
# stops its scope, so nothing it started (Gradle's daemon, a game, a compositor) outlives it. The command runs in
# the background with `wait`, so a signal to this script alone (TERM, HUP) runs its trap at once rather than after
# the command. Background commands ignore SIGINT; Ctrl+C reaches them through the trap too.
aresos_scoped() {
    local status=0
    aresos_scope_start "$@"
    wait "$ARESOS_JOB" || status=$?
    aresos_stop_scopes "$ARESOS_UNIT"
    return "$status"
}

# aresos_lock <file> <what holds it>: holds an exclusive lock on <file> until this script and everything it
# started have exited, waiting for it (and saying so) while another run holds it. The wait is one blocking `flock`
# on that file in a scope of this script: it keeps its place in line with the other waiting runs (looking every
# half second instead, a run lost the lock to every run that blocked), and a signal ends it at once.
aresos_lock() {
    exec {ARESOS_LOCK_FD}>>"$1"
    /usr/bin/flock -n "$ARESOS_LOCK_FD" && return 0
    aresos_say "Waiting for $2 to finish ($1)..."
    aresos_scoped lock-wait -- /usr/bin/flock "$ARESOS_LOCK_FD"
}

# Every exit (success, failure, Ctrl+C, a closed terminal) first stops this script's scopes with everything in
# them; signals are ignored meanwhile, so a second Ctrl+C cannot cut that short. A script adds its own steps by
# defining aresos_cleanup, which runs with the exit code; if it fails, an exit code of 0 becomes 1.
aresos_exit() {
    local status=$?
    trap - EXIT
    trap '' INT TERM HUP
    ((${#ARESOS_SCOPES[@]} == 0)) || aresos_stop_scopes "${ARESOS_SCOPES[@]}"
    if declare -F aresos_cleanup >/dev/null; then aresos_cleanup "$status" || ((status)) || status=1; fi
    exit "$status"
}
# A signal ends the script with 128 + its number; while a scope is being started, only once it exists.
aresos_signal() {
    if ((ARESOS_DEFER)); then ARESOS_PENDING=$1; else exit "$1"; fi
}
trap aresos_exit EXIT
trap 'aresos_signal 130' INT
trap 'aresos_signal 143' TERM
trap 'aresos_signal 129' HUP
