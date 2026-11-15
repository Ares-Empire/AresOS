#!/usr/bin/bash
# DEVELOPMENT AID of package 41 (measurement only), headless use only: one measured run of the home screen.
#
#   run.sh <name> [KEY=value ...]
#
# Settings (defaults: today's product at his screen size):
#   RD=8 SD=5        render and simulation distance (written into mod/run/options.txt)
#   HEAP=3072 MIN_HEAP=512   -Xmx / -Xms in MiB (Prism's MaxMemAlloc / MinMemAlloc)
#   GC=""            extra JVM flags, words joined by commas (GC=-XX:G1PeriodicGCInterval=30000)
#   MEMHIGH=5G       MemoryHigh of the game's own scope (the supervisor's MEMORY_HIGH)
#   SIZE=1920x1080 REFRESH=144   the headless screen
#   SETTLE=120 WINDOW=60 COVER=0  seconds: settle after joining, each frame window, covered by a maximized app
#   SHOTS=1          two pictures after the measurements (from the pad and above the south road)
#   MODE=measure     or MODE=hold: start the game and wait until it quits (setting up the base world by hand)
#   WORLD=base       base: a fresh copy of the base world each run; keep: the AresHub as it is
#
# What it does (MODE=measure): copies the base world into mod/run/saves/AresHub, sets the distances, starts the rig
# (start.sh: its own headless labwc, the lock, the memory check), waits for the world, lets it settle, takes a
# snapshot (snap.py), records 60 s standing at home looking around and 60 s flying at full speed down the roads (north 15 s, turn,
# south 30 s, turn, north 15 s), snapshots after each, then optionally covers the world with a maximized window for
# COVER seconds and snapshots again. Then it stops the game's scope and the rig, and analyze.py writes the summary.
# Raw data stays in .work/pkg41/rigs/<name>/; the summary and the small files go to reviews/41-home-memory/runs/<name>/.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
name=${1:?usage: run.sh <name> [KEY=value ...]}
[[ $name =~ ^[a-z0-9-]+$ ]] || { echo "name: lowercase letters, digits and dashes" >&2; exit 2; }
shift
RD=8 SD=5 HEAP=3072 MIN_HEAP=512 GC= MEMHIGH=5G SIZE=1920x1080 REFRESH=144 SETTLE=120 WINDOW=60 COVER=0 MODE=measure WORLD=base SHOTS=1
for setting; do
    key=${setting%%=*}
    case $key in
        RD|SD|HEAP|MIN_HEAP|GC|MEMHIGH|SIZE|REFRESH|SETTLE|WINDOW|COVER|MODE|WORLD|SHOTS) printf -v "$key" '%s' "${setting#*=}" ;;
        *) echo "unknown setting $key" >&2; exit 2 ;;
    esac
done
JDK=${JAVA_HOME:-$HOME/.local/opt/jdk-25}
WORK=$WT/.work/pkg41
RIG=$WORK/rigs/$name
OUT=$WT/reviews/41-home-memory/runs/$name
APPS=$WORK/apps
HOMEDIR=$WORK/home
BASE=$WORK/AresHub-base
SAVE=$WT/mod/run/saves/AresHub
FRAMES_JAR=$WORK/pkg41-frames.jar
[[ ! -e $RIG ]] || { echo "$RIG exists already; pick another name" >&2; exit 2; }
mkdir -p "$RIG" "$HOMEDIR" "$WT/mod/run/saves"
[[ -d $APPS ]] || python3 -I "$here/make-apps.py" "$APPS"
"$here/../frames/build.sh" "$FRAMES_JAR" >/dev/null
kib=$(awk '$1 == "MemAvailable:" {print $2}' /proc/meminfo)
((kib >= 6 * 1024 * 1024)) || { echo "only $((kib / 1024)) MiB available; a run needs 6 GiB" >&2; exit 75; }

# The world and the distances.
if [[ $MODE == measure && $WORLD == base ]]; then
    [[ -d $BASE ]] || { echo "no base world at $BASE (make it with MODE=hold)" >&2; exit 2; }
    rm -rf -- "$SAVE"
    cp -a -- "$BASE" "$SAVE"
fi
python3 -I - "$WT/mod/run/options.txt" "$RD" "$SD" <<'PY'
import os, sys
path, rd, sd = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines() if os.path.exists(path) else []
want = {'renderDistance': rd, 'simulationDistance': sd, 'fullscreen': 'false', 'onboardAccessibility': 'false',
        'tutorialStep': 'none'}
seen = set()
for i, line in enumerate(lines):
    key = line.split(':', 1)[0]
    if key in want:
        lines[i] = f'{key}:{want[key]}'; seen.add(key)
lines += [f'{k}:{v}' for k, v in want.items() if k not in seen]
open(path, 'w').write('\n'.join(lines) + '\n')
PY

# A folder Gradle takes for the JDK, whose bin/java puts the game in a scope of its own with MemoryHigh.
mkdir -p "$RIG/jdk/bin"
for entry in "$JDK"/*; do [[ ${entry##*/} == bin ]] || ln -s -- "$entry" "$RIG/jdk/${entry##*/}"; done
for entry in "$JDK"/bin/*; do [[ ${entry##*/} == java ]] || ln -s -- "$entry" "$RIG/jdk/bin/${entry##*/}"; done
cp -- "$here/java-wrapper.sh" "$RIG/jdk/bin/java"

export RIG APPS HOMEDIR SIZE REFRESH
export PKG41_JAVA=$RIG/jdk/bin/java PKG41_REAL_JAVA=$JDK/bin/java PKG41_JAVA_LOG=$RIG/java.txt
export PKG41_GAME_UNIT="pkg41-game-$name-$$.scope" PKG41_MEMORY_HIGH=$MEMHIGH
jvm="-Xms${MIN_HEAP}m -Xmx${HEAP}m -XX:NativeMemoryTracking=summary -Xlog:gc:file=$RIG/gc.txt:tn,u"
jvm+=" -Dfabric.addMods=$FRAMES_JAR -Dpkg41.frames=$RIG/frames.txt ${GC//,/ }"
export PKG41_JVM_ARGS=$jvm
if [[ $MODE == measure || -d $SAVE ]]; then export GAME_ARGS="--quickPlaySingleplayer AresHub"; else export GAME_ARGS=; fi
printf '%s\n' "name=$name" "RD=$RD" "SD=$SD" "HEAP=$HEAP" "MIN_HEAP=$MIN_HEAP" "GC=$GC" "MEMHIGH=$MEMHIGH" "SIZE=$SIZE" \
    "REFRESH=$REFRESH" "SETTLE=$SETTLE" "WINDOW=$WINDOW" "COVER=$COVER" "MODE=$MODE" "WORLD=$WORLD" \
    "JVM_ARGS=$jvm" "GAME_ARGS=$GAME_ARGS" "started=$(date -Is)" >"$RIG/settings.txt"

mono() { python3 -I -c 'import time; print(time.monotonic_ns())'; }
mark() { echo "$1 $(mono)" >>"$RIG/marks.txt"; echo "$(date +%T) $1"; }
vin() { echo "$*" >"$RIG/vin"; }

"$here/start.sh" >"$RIG/start.txt" 2>&1 &
start_pid=$!
game=
sampler=
cover=
finish() {
    local status=$?
    trap - EXIT
    [[ -z $sampler ]] || kill "$sampler" 2>/dev/null || true
    [[ -z $cover ]] || kill "$cover" 2>/dev/null || true
    systemctl --user stop "$PKG41_GAME_UNIT" 2>/dev/null || true
    for _ in $(seq 120); do kill -0 "$start_pid" 2>/dev/null || break; sleep 0.5; done
    if kill -0 "$start_pid" 2>/dev/null; then
        echo "the rig did not end within 60 s; stopping its scope" >&2
        systemctl --user stop "pkg41-rig-$start_pid.scope" 2>/dev/null || true
    fi
    wait "$start_pid" 2>/dev/null || true
    cp -f -- "$WT/mod/run/logs/latest.log" "$RIG/game.txt" 2>/dev/null || true
    exit "$status"
}
trap finish EXIT
trap 'exit 130' INT TERM

echo "$(date +%T) waiting for the lock and the game ($name)"
deadline=$((SECONDS + 1200))
until [[ -n $game ]]; do
    kill -0 "$start_pid" 2>/dev/null || { echo "the rig ended early; see $RIG/start.txt" >&2; exit 1; }
    ((SECONDS < deadline)) || { echo "no game after 20 min" >&2; exit 1; }
    if systemctl --user --quiet is-active "$PKG41_GAME_UNIT" 2>/dev/null; then
        group=$(systemctl --user show -P ControlGroup "$PKG41_GAME_UNIT")
        game=$(head -1 "/sys/fs/cgroup$group/cgroup.procs" 2>/dev/null || true)
    fi
    sleep 1
done
echo "GAME_PID=$game" >>"$RIG/settings.txt"
echo "$(date +%T) game PID $game in $PKG41_GAME_UNIT"
python3 -I "$here/sample.py" "$game" "$RIG/samples.csv" 2 &
sampler=$!
log=$WT/mod/run/logs/latest.log
until [[ $log -nt $RIG/settings.txt ]] && grep -q 'joined the game' "$log"; do
    kill -0 "$game" 2>/dev/null || { echo "the game ended before the world opened" >&2; exit 1; }
    ((SECONDS < deadline)) || { echo "no world after 20 min" >&2; exit 1; }
    sleep 1
done
mark joined

if [[ $MODE == hold ]]; then
    echo "$(date +%T) holding: drive it with $RIG/vin, stop it by quitting the game"
    while kill -0 "$game" 2>/dev/null; do sleep 2; done
    exit 0
fi

sleep "$SETTLE"
python3 -I "$here/snap.py" "$game" settled "$RIG"

# Standing at home, looking around: a slow 30-degree turn right and back every 3 s. Without input for 60 s the game
# drops to 30 frames a second (vanilla's inactivity limit, his default too), which would hide the frame times.
vin key h; sleep 2
mark stand_start
for ((t = 0; t < WINDOW; t += 6)); do
    vin rel 200 0 15; sleep 2.85
    vin rel -200 0 15; sleep 2.85
done
mark stand_end
python3 -I "$here/snap.py" "$game" stand "$RIG"

# Flight: H puts him on the pad facing north (standing, so not flying); a double jump starts flying and 2.5 s up
# take him above the logos (12 blocks) and their signs; then sprint-flying (21.6 blocks a second) north along the
# road, a half turn (1263 counts of relative motion: 180 degrees, measured), south past home and down the south road
# (the 28 System & Tools logos), a half turn, and north again towards home.
# (check-flight.sh confirmed: about 21 blocks up, 21.6 blocks a second, and 1263 counts for the half turn.)
# Every key press and gap lasts two ticks: a 40 ms tap can fall between two game ticks and go unseen.
quarter=$((WINDOW / 4))
vin key h; sleep 1.5
vin key lshift down; sleep 1; vin key lshift up; sleep 0.5
vin key space down; sleep 0.1; vin key space up; sleep 0.1; vin key space down; sleep 0.1; vin key space up
sleep 0.3
vin key space down; sleep 2.5; vin key space up
mark flight_start
vin key w down; vin key lctrl down
sleep "$quarter"
vin rel 1263 0 20
sleep $((quarter * 2))
vin rel 1263 0 20
sleep $((WINDOW - quarter * 3))
mark flight_end
vin key w up; vin key lctrl up
# Outside the windows: a picture of where the flight ended (above home, over the logos), to check it flew.
[[ $SHOTS != 1 ]] || { mkdir -p "$RIG/shots"; "$WT/reviews/40-real-home/rig/shot.sh" "$RIG" "$RIG/shots/after-flight.png" || true; }
python3 -I "$here/snap.py" "$game" flight "$RIG"

if ((COVER > 0)); then
    wayland=$(sed -n 's/^WAYLAND_DISPLAY=//p' "$RIG/env")
    [[ -n $wayland && $wayland != wayland-0 ]] || { echo "refusing display '$wayland'" >&2; exit 1; }
    env -u DISPLAY WAYLAND_DISPLAY="$wayland" /usr/bin/foot --app-id=pkg41.Cover --title="Cover" -e /usr/bin/sleep 3600 \
        >"$RIG/cover.txt" 2>&1 &
    cover=$!
    sleep 2
    python3 -I "$WT/reviews/40-real-home/rig/tl.py" "$RIG" max pkg41.Cover >>"$RIG/cover.txt" 2>&1
    mark covered_start
    python3 -I "$here/snap.py" "$game" covered0 "$RIG"
    for ((t = 60; t <= COVER; t += 60)); do
        sleep 60
        python3 -I "$here/snap.py" "$game" "covered$((t / 60))m" "$RIG"
    done
    mark covered_end
    python3 -I "$WT/reviews/40-real-home/rig/tl.py" "$RIG" list >>"$RIG/cover.txt" 2>&1
fi
# Pictures for the report, after every measurement: from the pad looking south over the biggest group, and from
# above it. Only the rig's own test logos are in them.
if [[ $SHOTS == 1 ]]; then
    [[ -z $cover ]] || { kill "$cover" 2>/dev/null || true; cover=; sleep 2; }
    # The closed cover leaves no keyboard focus; give it back to the world, as a click would.
    python3 -I "$WT/reviews/40-real-home/rig/tl.py" "$RIG" activate aresos-desktop >/dev/null 2>&1 || true
    sleep 1
    mkdir -p "$RIG/shots"
    # He may still be flying after H (hovering on the pad); Shift brings him down, and landing ends flying.
    vin key h; sleep 2; vin key lshift down; sleep 1; vin key lshift up; vin rel 1263 0 20; sleep 3
    "$WT/reviews/40-real-home/rig/shot.sh" "$RIG" "$RIG/shots/home-south.png" || true
    vin key space down; sleep 0.1; vin key space up; sleep 0.1; vin key space down; sleep 0.1; vin key space up
    sleep 0.3; vin key space down; sleep 3; vin key space up; sleep 3
    "$WT/reviews/40-real-home/rig/shot.sh" "$RIG" "$RIG/shots/above-south.png" || true
fi
mark done
trap - EXIT
finish_status=0
( finish ) || finish_status=$?
python3 -I "$here/analyze.py" "$RIG" "$OUT"
