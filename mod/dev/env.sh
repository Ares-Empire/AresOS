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
# --status act on every daemon of this Gradle version on the laptop. Single-dash long options do the same.
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

# client-test opts in after taking the lock. This process owns the launchers, not just their scope names:
# if the shell dies halfway through starting a scope, it can cancel that launcher before it can start late.
# It inherits the lock, and releases it only after stopping clients first and the CUDA worker last. CUDA calls
# never run here, so even a stuck driver call cannot block parent-death detection or the cleanup deadlines.
ARESOS_GUARD_DIR=
aresos_supervise() {
    ARESOS_GUARD_DIR=$(/usr/bin/mktemp -d -- "$ARESOS_DEV_CACHE/client-test-guard.XXXXXX")
    ARESOS_DEFER=1
    /usr/bin/python3 -I -c '
import array
import json
import os
import select
import signal
import socket
import subprocess
import sys
import time

directory, parent_pid = sys.argv[1:]
for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, signal.SIG_IGN)
parent = os.pidfd_open(int(parent_pid))
server = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
cwd = os.getcwd()
os.chdir(directory)
server.bind("socket")
os.chdir(cwd)
server.listen()
children = {}
watch = None
finishing = None
holder_failed = False

def ctl(*args):
    try:
        return subprocess.run(["systemctl", "--user", *args], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True, timeout=1)
    except subprocess.TimeoutExpired:
        return None

def child_signals():
    # The supervisor ignores terminal signals; its commands must still respond to scope stops.
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.SIG_DFL)

def holder_lost():
    global holder_failed
    if watch and children[watch][0].poll() is not None:
        if not holder_failed:
            print("client-test: NVIDIA power holder exited unexpectedly; aborting client tests.",
                  file=sys.stderr, flush=True)
        holder_failed = True
    return holder_failed

def stop_scopes(units, seconds):
    if not units:
        return True
    # Cancel a launcher that has not yet joined its scope too. Popen retains ownership until it is reaped.
    deadline = time.monotonic() + seconds
    ctl("stop", "--no-block", "--", *units)
    while True:
        if units == ordinary:
            holder_lost()
        result = ctl("show", "--property=ActiveState", "--value", "--", *units)
        live = units if (result is None or
                         any(s not in ("inactive", "failed") for s in result.stdout.split())) else []
        for unit in units:
            child, peer = children[unit]
            if child.poll() is None:
                child.terminate()
        if not live and all(children[u][0].poll() is not None for u in units):
            return True
        if time.monotonic() >= deadline:
            ctl("kill", "--signal=KILL", "--", *units)
            for unit in units:
                child = children[unit][0]
                if child.poll() is None:
                    child.kill()
            # Confirm removal before releasing the lock; an unkillable kernel task is reported, not green.
            until = time.monotonic() + 3
            while time.monotonic() < until:
                if units == ordinary:
                    holder_lost()
                result = ctl("show", "--property=ActiveState", "--value", "--", *units)
                if (result is not None and
                    all(s in ("inactive", "failed") for s in result.stdout.split()) and
                    all(children[u][0].poll() is not None for u in units)):
                    return True
                time.sleep(0.1)
            print("client-test: FAILED to confirm owned scopes stopped: " + " ".join(units),
                  file=sys.stderr, flush=True)
            return False
        ctl("kill", "--signal=TERM", "--", *live) if live else None
        time.sleep(0.1)

def reply(peer, status):
    try:
        peer.send(str(status).encode())
    except (BrokenPipeError, ConnectionResetError):
        pass
    peer.close()

try:
    while True:
        # Check the worker for the entire interval after READY, including probes and game shutdown.
        if holder_lost():
            try:
                signal.pidfd_send_signal(parent, signal.SIGUSR1)
            except ProcessLookupError:
                pass
            break
        ready, _, _ = select.select([parent, server], [], [], 0.05)
        if parent in ready:
            break
        for unit, (child, peer) in children.items():
            status = child.poll()
            if peer is not None and status is not None:
                reply(peer, status if status >= 0 else 128 - status)
                children[unit] = (child, None)
        if server not in ready:
            continue
        peer, _ = server.accept()
        # A dead or stalled RPC sender must not delay the pidfd check.
        peer.settimeout(1)
        fds = array.array("i")
        try:
            data, ancillary, _, _ = peer.recvmsg(131072, socket.CMSG_SPACE(4 * fds.itemsize))
            for level, kind, values in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    fds.frombytes(values)
            request = json.loads(data)
            action = request[0]
            if action == "start":
                _, unit, args, environment = request
                environment["ARESOS_SCOPED_STDERR_FD"] = str(fds[3])
                child = subprocess.Popen(
                    ["systemd-run", "--user", "--scope", "--quiet", "--collect", "--unit=" + unit,
                     "--property=TimeoutStopSec=20", *args],
                    env=environment, stdin=fds[0], stdout=fds[1], stderr=fds[2], pass_fds=(fds[3],),
                    preexec_fn=child_signals)
                children[unit] = (child, peer)
            elif action == "watch":
                watch = request[1]
                reply(peer, 0)
            elif action == "finish":
                finishing = peer
                break
            else:
                raise ValueError("unknown supervisor request")
        except Exception as error:
            print("client-test: supervisor request failed: " + str(error), file=sys.stderr, flush=True)
            reply(peer, 1)
        finally:
            for fd in fds:
                os.close(fd)
finally:
    # Ignore terminal signals during cleanup, just as the shell EXIT trap does.
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.SIG_IGN)
    ordinary = [u for u in children if not u.startswith("aresos-dev-client-test-gpu-holder-")]
    holders = [u for u in children if u not in ordinary]
    clients_stopped = stop_scopes(ordinary, 20)
    # Latch a loss even if it happened during the last scope query (or there were no ordinary scopes).
    holder_lost()
    holder_stopped = stop_scopes(holders, 5)
    for child, peer in children.values():
        if peer is not None:
            status = child.poll()
            reply(peer, status if status is not None and status >= 0 else 1)
    if finishing is not None:
        reply(finishing, 0 if clients_stopped and holder_stopped and not holder_failed else 1)
    server.close()
    os.unlink(directory + "/socket")
    os.rmdir(directory)
' "$ARESOS_GUARD_DIR" "$$" &
    ARESOS_GUARD_JOB=$!
    local deadline=$((SECONDS + 5))
    while [[ ! -S $ARESOS_GUARD_DIR/socket ]]; do
        aresos_job_running "$ARESOS_GUARD_JOB" && ((SECONDS < deadline)) \
            || aresos_fail 1 "Could not start the client-test supervisor."
        /usr/bin/sleep 0.02
    done
    ARESOS_DEFER=0
    ((ARESOS_PENDING == 0)) || exit "$ARESOS_PENDING"
}

# A launcher RPC stays alive until the owned command exits, preserving aresos_scope_start/scoped job semantics.
# Pass the call site descriptors (including the game stderr) and environment so redirections/isolation survive.
aresos_guard_request() {
    /usr/bin/python3 -I -c '
import array
import json
import os
import socket
import sys

try:
    os.close(int(sys.argv[2]))  # Only the shell and independent supervisor retain the lock.
except OSError:
    pass  # The background launcher already closed its copy before starting Python.
request = sys.argv[3:]
if request[0] == "start":
    try:
        extra = os.dup(3)
    except OSError:
        extra = os.dup(2)
peer = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
try:
    os.chdir(sys.argv[1])
    peer.connect("socket")
except (FileNotFoundError, ConnectionRefusedError):
    sys.exit("client-test: supervisor has stopped; aborting.")
if request[0] == "start":
    request = ["start", request[1], request[2:], dict(os.environ)]
    fds = array.array("i", [0, 1, 2, extra])
    peer.sendmsg([json.dumps(request).encode()], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)])
else:
    peer.send(json.dumps(request).encode())
try:
    status = peer.recv(32)
except ConnectionResetError:
    sys.exit("client-test: supervisor has stopped; aborting.")
sys.exit(int(status) if status else 1)
' "$ARESOS_GUARD_DIR" "$ARESOS_LOCK_FD" "$@"
}

# True while the background job with this PID has not ended (bash's own job table, so a reused PID never counts).
aresos_job_running() {
    local pid
    for pid in $(jobs -rp); do [[ $pid != "$1" ]] || return 0; done
    return 1
}

# aresos_scope_start <name> [systemd-run options...] -- <command...>: starts the command in the background in a
# new scope of this script and returns once that scope exists (or the command has already ended). Sets
# ARESOS_UNIT to the scope and ARESOS_JOB to the job. A launcher still awaiting activation is killed and reaped
# after 15 s, before it can launch late. A stop sends TERM to
# everything in the scope and KILL to what is left 20 s later (TimeoutStopSec; an option may set another).
aresos_scope_start() {
    local deadline=$((SECONDS + 15)) units status=0
    while :; do
        ARESOS_UNIT="aresos-dev-$1-$$-$SRANDOM.scope"
        units=$(systemctl --user list-units --all --no-legend --plain "$ARESOS_UNIT") \
            || aresos_fail 1 "Could not check whether $ARESOS_UNIT already exists; not starting it."
        [[ -n $units ]] || break
    done
    shift
    # systemd-run creates the scope before it starts the command in it, so a stop by name before then would miss
    # a command that is about to start. A signal until the scope exists is held, then acted on below.
    ARESOS_DEFER=1
    ARESOS_SCOPES+=("$ARESOS_UNIT")
    if [[ -n $ARESOS_GUARD_DIR ]]; then
        # The RPC subprocess must not keep the lock alive after the supervisor has finished cleanup.
        { exec {ARESOS_LOCK_FD}>&-; aresos_guard_request start "$ARESOS_UNIT" "$@"; } &
    else
        systemd-run --user --scope --quiet --collect --unit="$ARESOS_UNIT" --property=TimeoutStopSec=20 "$@" &
    fi
    ARESOS_JOB=$!
    while ! systemctl --user --quiet is-active "$ARESOS_UNIT"; do
        if ! aresos_job_running "$ARESOS_JOB"; then
            wait "$ARESOS_JOB" || { status=$?; unset 'ARESOS_SCOPES[-1]'; }
            break
        fi
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
    return "$status"
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
    aresos_scope_start "$@" || return $?
    wait "$ARESOS_JOB" || status=$?
    aresos_stop_scopes "$ARESOS_UNIT"
    return "$status"
}

# An idle CUDA context prevents fine-grained RTD3 too; an open graphics device alone does not.
# No toolkit is needed: Python calls the NVIDIA driver's existing libcuda directly.
ARESOS_GPU_HOLDER_UNIT=
aresos_hold_nvidia() {
    local pci=$1 log="$ARESOS_DEV_CACHE/client-test-gpu-holder.log" job deadline=$((SECONDS + 30))
    # cuInit must not need to load UVM or create its device through a privileged driver helper.
    if [[ ! -d /sys/module/nvidia_uvm || ! -c /dev/nvidia-uvm || ! -r /dev/nvidia-uvm || ! -w /dev/nvidia-uvm ]]; then
        aresos_say "NVIDIA power holding needs an already available /dev/nvidia-uvm; skipping its probe."
        return 1
    fi
    if ! aresos_scope_start client-test-gpu-holder --property=TimeoutStopSec=5 -- \
        /usr/bin/python3 -I -c '
import ctypes
import signal
import sys

def stop(*_):
    sys.exit(0)

for sig in (signal.SIGINT, signal.SIGHUP):
    signal.signal(sig, signal.SIG_IGN)
signal.signal(signal.SIGTERM, stop)
cuda = ctypes.CDLL("libcuda.so.1")
cuda.cuInit.argtypes = [ctypes.c_uint]
cuda.cuDeviceGetByPCIBusId.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_char_p]
cuda.cuDevicePrimaryCtxRetain.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_int]
cuda.cuDevicePrimaryCtxRelease_v2.argtypes = [ctypes.c_int]

def check(function, *args):
    status = function(*args)
    if status:
        raise RuntimeError(f"{function.__name__}: CUDA error {status}")

check(cuda.cuInit, 0)
device = ctypes.c_int()
check(cuda.cuDeviceGetByPCIBusId, ctypes.byref(device), sys.argv[1].encode("ascii"))
context = ctypes.c_void_p()
check(cuda.cuDevicePrimaryCtxRetain, ctypes.byref(context), device)
try:
    print("READY", flush=True)
    # Only the independent supervisor releases this worker, after its client scopes are gone.
    while True:
        signal.pause()
finally:
    check(cuda.cuDevicePrimaryCtxRelease_v2, device)
' "$pci" >"$log" 2>&1; then
        aresos_say "Could not start the NVIDIA power holder; see $log."
        return 1
    fi
    ARESOS_GPU_HOLDER_UNIT=$ARESOS_UNIT
    job=$ARESOS_JOB
    while aresos_job_running "$job"; do
        if /usr/bin/grep -qx READY "$log"; then
            aresos_guard_request watch "$ARESOS_GPU_HOLDER_UNIT" || aresos_fail 1 "Could not watch the NVIDIA power holder."
            aresos_say "Holding NVIDIA active until the client scopes have stopped."
            return 0
        fi
        ((SECONDS < deadline)) || break
        /usr/bin/sleep 0.02
    done
    aresos_say "Cannot hold NVIDIA active; skipping its probe (see $log)."
    aresos_stop_scopes "$ARESOS_GPU_HOLDER_UNIT"
    wait "$job" || true
    ARESOS_GPU_HOLDER_UNIT=
    return 1
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
    local status=$? unit scopes=()
    trap - EXIT
    trap '' INT TERM HUP
    # The CUDA context must outlive even the game's shutdown work, including cancellation.
    if [[ -n $ARESOS_GUARD_DIR ]]; then
        aresos_guard_request finish || ((status)) || status=1
        wait "$ARESOS_GUARD_JOB" || ((status)) || status=1
    else
        for unit in "${ARESOS_SCOPES[@]}"; do
            [[ $unit == "$ARESOS_GPU_HOLDER_UNIT" ]] || scopes+=("$unit")
        done
        ((${#scopes[@]} == 0)) || aresos_stop_scopes "${scopes[@]}"
        [[ -z $ARESOS_GPU_HOLDER_UNIT ]] || aresos_stop_scopes "$ARESOS_GPU_HOLDER_UNIT"
    fi
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
trap 'aresos_signal 1' USR1
