# shellcheck shell=bash
# Shared setup for the mod's Linux development scripts (build.sh, client-test.sh, run-hub.sh). Sourced, not run.
#
# It finds Java 25 without touching the shell's PATH or ~/.bashrc, and holds the checks that keep a run from
# disturbing the owner or the other sessions on this laptop: the memory floor, his own Minecraft (Lunar Client)
# and the one-client-test-at-a-time lock. The scripts run from mod/, whatever the caller's directory.

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

aresos_say() { printf '%s: %s\n' "${0##*/}" "$*" >&2; }

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

# PIDs of the owner's own Minecraft: a process whose executable lives under ~/.lunarclient (the Lunar Client game).
# Only /proc is read. Matching command lines instead would also match the shell running this check.
aresos_lunar_game_pids() {
    local real
    real=$(cd -- "$HOME" && pwd -P)
    /usr/bin/find /proc -mindepth 2 -maxdepth 2 -name exe \
        \( -lname "$HOME/.lunarclient/*" -o -lname "$real/.lunarclient/*" \) -printf '%h\n' 2>/dev/null \
        | /usr/bin/sed 's|^/proc/||' || true
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
    if (( kib < ARESOS_MIN_AVAILABLE_KIB )); then
        aresos_fail "$ARESOS_EXIT_BUSY" "Only $((kib / 1048576)).$((kib % 1048576 * 10 / 1048576)) GB of memory is available and a run needs 6 GB; try again later, or pass --force."
    fi
}

# The Gradle wrapper without a lasting daemon. Gradle forks a single-use daemon for this build's JVM settings and
# stops it when the build ends. A shared daemon would outlive the run, and `gradlew --stop` would stop every
# daemon of this Gradle version on the laptop, including other sessions' builds in other worktrees.
ARESOS_GRADLE=("$ARESOS_MOD_DIR/gradlew" --no-daemon)

# aresos_scoped <unit prefix> <command...>: runs the command in its own systemd user scope and stops that scope
# afterwards, so nothing it started (Gradle's daemon, a game, a compositor) outlives it, also after Ctrl+C.
ARESOS_SCOPE=
ARESOS_SCOPE_PID=
aresos_stop_scope() {
    [[ -n $ARESOS_SCOPE ]] || return 0
    # The PID first: if systemd-run has not created the scope yet, nothing may start after this.
    [[ -z $ARESOS_SCOPE_PID ]] || kill -TERM "$ARESOS_SCOPE_PID" 2>/dev/null || true
    /usr/bin/systemctl --user stop "$ARESOS_SCOPE" 2>/dev/null || true
    ARESOS_SCOPE= ARESOS_SCOPE_PID=
}
aresos_scoped() {
    local status=0
    ARESOS_SCOPE="$1-$$.scope"
    shift
    # In the background with `wait`, so that a signal to this script alone (TERM, HUP) runs its trap at once
    # rather than after the run. Background commands ignore SIGINT; Ctrl+C reaches them through the trap too.
    /usr/bin/systemd-run --user --scope --quiet --collect --unit="$ARESOS_SCOPE" --property=TimeoutStopSec=20 \
        -- "$@" &
    ARESOS_SCOPE_PID=$!
    wait "$ARESOS_SCOPE_PID" || status=$?
    # Reaped: its PID may belong to another process from now on.
    ARESOS_SCOPE_PID=
    aresos_stop_scope
    return "$status"
}

# aresos_lock <file> <what holds it>: holds an exclusive lock on <file> until this script and everything it
# started have exited, waiting for it (and saying so) while another run holds it. Sets ARESOS_LOCK_WAITED=1 after
# a wait. The wait runs in the background, so a signal still stops this script at once.
ARESOS_LOCK_PID=
ARESOS_LOCK_WAITED=0
aresos_lock() {
    exec {ARESOS_LOCK_FD}>>"$1"
    /usr/bin/flock -n "$ARESOS_LOCK_FD" && return 0
    aresos_say "Waiting for $2 to finish ($1)..."
    /usr/bin/flock "$ARESOS_LOCK_FD" &
    ARESOS_LOCK_PID=$!
    wait "$ARESOS_LOCK_PID" || aresos_fail 1 "Could not lock $1."
    ARESOS_LOCK_PID=
    ARESOS_LOCK_WAITED=1
}

# Every exit (success, failure, Ctrl+C, a closed terminal) first stops the scope with everything in it; a script
# adds its own steps by defining aresos_cleanup, which then runs with the exit code.
aresos_exit() {
    local status=$?
    trap - EXIT INT TERM HUP
    [[ -z $ARESOS_LOCK_PID ]] || kill -TERM "$ARESOS_LOCK_PID" 2>/dev/null || true
    aresos_stop_scope
    if declare -F aresos_cleanup >/dev/null; then aresos_cleanup "$status" || true; fi
    exit "$status"
}
trap aresos_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
