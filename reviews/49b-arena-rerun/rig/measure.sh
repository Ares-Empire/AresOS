#!/usr/bin/bash
# DEVELOPMENT AID of package 49b (copied from package 41) (measurement only), headless use only: one measured run of the home screen.
#
#   run.sh <name> [KEY=value ...]
#
# Settings (defaults: package 41's v1 recommendation at his screen size):
#   RD=8 SD=5        render and simulation distance (written into mod/run/options.txt)
#   HEAP=1024 MIN_HEAP=256   -Xmx / -Xms in MiB (Prism's MaxMemAlloc / MinMemAlloc)
#   GC=<v1 ratios>    extra JVM flags, words joined by commas (GC=-XX:G1PeriodicGCInterval=30000)
#   MEMHIGH=2560M       MemoryHigh of the game's own scope (the supervisor's MEMORY_HIGH)
#   SIZE=1920x1080 REFRESH=144   the headless screen
#   SETTLE=120 WINDOW=60 COVER=0  seconds: settle after joining, each frame window, covered by a maximized app
#   SHOTS=1          two pictures after the measurements (from the pad and above the south road)
#   MODE=measure     or MODE=hold: start the game and wait until it quits (setting up the base world by hand);
#                    or MODE=create: no AresHub, the title screen's AresOS button, Home: HOMEKIND, Create, then the
#                    same measurements once the home is ready (flat: "The town is built")
#   HOMEKIND=flat    flat or nether (MODE=create): the choice on the create screen (the Nether with its default seed)
#   WORLD=base       base: a fresh copy of the base world each run; keep: the AresHub as it is
#   BASE=AresHub-base  the base world's folder in .work/pkg49b
#   FLIGHT=roads     roads: the flat town's route; glide: the same three legs at the same speed, moved by the rig's
#                    data pack (/function glide: a teleport of 1.08 blocks every tick) straight through the terrain, for
#                    the Nether, whose caves stop a real flight within blocks (AresOS refuses spectator mode); needs a
#                    save readied with prepare-glide.py; none: no flight
#   QUIT=0           1: at the end close the game's window, so it saves and quits, and keep the save in <rig>/world
#
# What it does (MODE=measure): copies the base world into mod/run/saves/AresHub, sets the distances, starts the rig
# (run.sh: shared lock; start.sh: its own headless labwc and memory check), waits for the world, lets it settle, takes a
# snapshot (snap.py), records 60 s standing at home looking around and 60 s flying at full speed down the roads (north 15 s, turn,
# south 30 s, turn, north 15 s), snapshots after each, then optionally covers the world with a maximized window for
# COVER seconds and snapshots again. Then it stops the game's scope and the rig, and analyze.py writes the summary.
# Raw data stays in .work/pkg49b/rigs/<name>/; the summary and the small files go to reviews/49b-arena-rerun/runs/<name>/.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
name=${1:?usage: run.sh <name> [KEY=value ...]}
[[ $name =~ ^[a-z0-9-]+$ ]] || { echo "name: lowercase letters, digits and dashes" >&2; exit 2; }
shift
RD=8 SD=5 HEAP=1024 MIN_HEAP=256 GC=-XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10 MEMHIGH=2560M SIZE=1920x1080 REFRESH=144 SETTLE=120 WINDOW=60 COVER=0 MODE=measure WORLD=base SHOTS=1
HOMEKIND=flat BASE=AresHub-base FLIGHT=roads QUIT=0
ENV= MODS= PROBE=0 RECLAIM= FREEZE=0 LONG=0 NMT=1 COVER_ACTION=none CREATE_FLOW=manual
for setting; do
    key=${setting%%=*}
    case $key in
        RD|SD|HEAP|MIN_HEAP|GC|MEMHIGH|SIZE|REFRESH|SETTLE|WINDOW|COVER|MODE|WORLD|SHOTS|HOMEKIND|BASE|FLIGHT|QUIT|ENV|MODS|PROBE|RECLAIM|FREEZE|LONG|NMT|COVER_ACTION|CREATE_FLOW)
            printf -v "$key" '%s' "${setting#*=}" ;;
        *) echo "unknown setting $key" >&2; exit 2 ;;
    esac
done
case $MODE/$HOMEKIND/$FLIGHT/$QUIT in
    measure/*/roads/[01] | measure/*/glide/[01] | measure/*/none/[01] | hold/*/*/0 \
        | create/flat/roads/[01] | create/flat/none/[01] | create/nether/none/[01]) ;;
    *) echo "settings do not fit: MODE=$MODE HOMEKIND=$HOMEKIND FLIGHT=$FLIGHT QUIT=$QUIT" >&2; exit 2 ;;
esac
case $CREATE_FLOW/$MODE/$HOMEKIND in
    manual/*/* | automatic/create/flat | menu/create/nether) ;;
    *) echo "creation flow does not fit this mode/home" >&2; exit 2 ;;
esac
[[ $BASE =~ ^[A-Za-z0-9-]+$ ]] || { echo "BASE: a folder name in .work/pkg49b" >&2; exit 2; }
[[ ${PKG49_LOCK_HELD:-0} == 1 ]] || { echo "run through run.sh under the shared lock" >&2; exit 2; }
for value in "$RD" "$SD" "$HEAP" "$MIN_HEAP" "$SETTLE" "$WINDOW" "$COVER" "$LONG"; do
    [[ $value =~ ^[0-9]+$ ]] || { echo "numeric setting required" >&2; exit 2; }
done
[[ $PROBE =~ ^[01]$ && $FREEZE =~ ^[01]$ && $NMT =~ ^[01]$ ]] || exit 2
[[ $COVER_ACTION == none || $COVER_ACTION == gc-trim ]] || exit 2
[[ -z $RECLAIM || $RECLAIM =~ ^(300M|600M)$ ]] || exit 2
if [[ -n $RECLAIM || $FREEZE == 1 || $COVER_ACTION != none ]]; then
    ((COVER >= 60)) || { echo "cover action requires COVER >= 60" >&2; exit 2; }
fi
[[ $FREEZE != 1 || -n $RECLAIM ]] || { echo "freeze must follow reclaim" >&2; exit 2; }
# This rerun never performs a direct cgroup write or a diagnostic collection.
[[ $PROBE == 0 && $FREEZE == 0 && -z $RECLAIM && $COVER_ACTION == none ]] || { echo "cover/probe actions are outside package 49b" >&2; exit 2; }
JDK=${JAVA_HOME:-$HOME/.local/opt/jdk-25}
WORK=$WT/.work/pkg49b
RIG=$WORK/rigs/$name
OUT=$WT/reviews/49b-arena-rerun/runs/$name
APPS=$WORK/apps
HOMEDIR=$WORK/home
BASE=$WORK/$BASE
SAVE=$WT/mod/run/saves/AresHub
FRAMES_JAR=$WORK/pkg41-frames.jar
[[ ! -e $RIG ]] || { echo "$RIG exists already; pick another name" >&2; exit 2; }
# run.sh already holds the shared lock, before any world, options or build preparation.
if [[ -n $(systemctl --user list-units --no-legend --plain 'pkg49b-rig-*' 'pkg49b-game-*' 2>/dev/null) ]]; then
    echo "another run of this rig is going; run one at a time" >&2; exit 75
fi
mkdir -p "$RIG" "$HOMEDIR" "$WT/mod/run/saves"
[[ -d $APPS ]] || python3 -I "$here/make-apps.py" "$APPS"
"$here/../frames/build.sh" "$FRAMES_JAR" >/dev/null
kib=$(awk '$1 == "MemAvailable:" {print $2}' /proc/meminfo)
((kib >= 6 * 1024 * 1024)) || { echo "only $((kib / 1024)) MiB available; a run needs 6 GiB" >&2; mv -- "$RIG" "$RIG-busy-$$"; exit 75; }

# The world and the distances.
if [[ $MODE == measure && $WORLD == base ]]; then
    [[ -d $BASE ]] || { echo "no base world at $BASE (make it with MODE=hold)" >&2; exit 2; }
    rm -rf -- "$SAVE"
    cp -a -- "$BASE" "$SAVE"
fi
# A first creation starts with no AresHub (the rig's working copy; the base worlds stay in .work/pkg49b).
if [[ $MODE == create ]]; then
    rm -rf -- "$SAVE"
    # Package 48 creates flat automatically. Its Nether choice is reached from the real home menu.
    [[ $CREATE_FLOW != menu ]] || cp -a -- "$BASE" "$SAVE"
fi
python3 -I - "$WT/mod/run/options.txt" "$RD" "$SD" <<'PY'
import os, sys
path, rd, sd = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines() if os.path.exists(path) else []
want = {'renderDistance': rd, 'simulationDistance': sd, 'fullscreen': 'false', 'onboardAccessibility': 'false',
        'tutorialStep': 'none', 'maxFps': '120'}
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
export PKG49_JAVA=$RIG/jdk/bin/java PKG49_REAL_JAVA=$JDK/bin/java PKG49_JAVA_LOG=$RIG/java.txt
export PKG49_GAME_UNIT="pkg49b-game-$name-$$.scope" PKG49_MEMORY_HIGH=$MEMHIGH
jvm="-Xms${MIN_HEAP}m -Xmx${HEAP}m -Xlog:gc:file=$RIG/gc.txt:tn,u"
[[ $NMT != 1 ]] || jvm+=" -XX:NativeMemoryTracking=summary"
extra_mods=
if [[ -n $MODS ]]; then
    IFS=, read -ra mod_paths <<<"$MODS"
    for jar in "${mod_paths[@]}"; do [[ -f $jar && $jar == /* && $jar != *' '* ]] || exit 2; done
    extra_mods=":${MODS//,/:}"
fi
jvm+=" -Dfabric.addMods=$FRAMES_JAR$extra_mods -Dpkg41.frames=$RIG/frames.txt ${GC//,/ }"
if [[ $MODE == create && $CREATE_FLOW != manual ]]; then
    jvm+=" -Dpkg49b.ui=$RIG/ui.txt -Dpkg49b.creation_marks=$RIG/creation-marks.txt"
fi
export PKG49_JVM_ARGS=$jvm PKG49_GAME_ENV=$ENV PKG49_PROBE=$PROBE PKG49_NMT=$NMT
cp -- "$WT/mod/run/options.txt" "$RIG/options.txt"
python3 -I "$here/host.py" "$RIG/host-start.json"
if [[ $MODE == measure || -d $SAVE ]]; then export GAME_ARGS="--quickPlaySingleplayer AresHub"; else export GAME_ARGS=; fi
printf '%s\n' "name=$name" "RD=$RD" "SD=$SD" "HEAP=$HEAP" "MIN_HEAP=$MIN_HEAP" "GC=$GC" "MEMHIGH=$MEMHIGH" "SIZE=$SIZE" \
    "REFRESH=$REFRESH" "SETTLE=$SETTLE" "WINDOW=$WINDOW" "COVER=$COVER" "MODE=$MODE" "WORLD=$WORLD" \
    "HOMEKIND=$HOMEKIND" "BASE=$BASE" "FLIGHT=$FLIGHT" "QUIT=$QUIT" "CREATE_FLOW=$CREATE_FLOW" \
    "ENV=$ENV" "MODS=$MODS" "PROBE=$PROBE" "RECLAIM=$RECLAIM" "FREEZE=$FREEZE" "LONG=$LONG" "NMT=$NMT" "COVER_ACTION=$COVER_ACTION" "WAKE_INPUT=active-v3" \
    "JVM_ARGS=$jvm" "GAME_ARGS=$GAME_ARGS" "source_revision=$(git -C "$WT" rev-parse HEAD)" "started=$(date -Is)" >"$RIG/settings.txt"

# A command through chat: / opens it with the slash typed, the text, Enter.
chat() { vin key slash; sleep 0.5; vin type "$1"; sleep 0.3; vin key enter; sleep 0.5; }  # letters, digits, space
shot() { mkdir -p "$RIG/shots"; "$WT/reviews/40-real-home/rig/shot.sh" "$RIG" "$RIG/shots/$1.png" || true; }

source "$here/lifecycle.sh"
rig_start "$here/start.sh"
python3 -I "$here/interference.py" "$RIG/host-watch.jsonl" &
host_watch=$!

echo "$(date +%T) waiting for the lock and the game ($name)"
deadline=$((SECONDS + 1200))
until [[ -n $game ]]; do
    kill -0 "$start_pid" 2>/dev/null || { status=0; wait "$start_pid" || status=$?; echo "the rig ended early ($status); see $RIG/start.txt" >&2; exit "$((status == 0 ? 1 : status))"; }
    ((SECONDS < deadline)) || { echo "no game after 20 min" >&2; exit 1; }
    if systemctl --user --quiet is-active "$PKG49_GAME_UNIT" 2>/dev/null; then
        group=$(systemctl --user show -P ControlGroup "$PKG49_GAME_UNIT")
        game=$(head -1 "/sys/fs/cgroup$group/cgroup.procs" 2>/dev/null || true)
    fi
    sleep 1
done
echo "GAME_PID=$game" >>"$RIG/settings.txt"
echo "$(date +%T) game PID $game in $PKG49_GAME_UNIT"
mark game_detected
python3 -I "$here/provenance.py" "$game" "$RIG"
python3 -I "$here/sample.py" "$game" "$RIG/samples.csv" 2 &
sampler=$!
log=$WT/mod/run/logs/latest.log
if [[ $MODE == create && $CREATE_FLOW == manual ]]; then
    # The title screen (GUI scale 4 at 1920 x 1080: 480 x 270 units). AresOS spans 140..340 x 91..111 with no AresHub;
    # on the create screen "Home: Flat" spans 100..380 x 53..73 and Create 100..236 x 221..241 (HomeCreateScreen).
    until [[ $log -nt $RIG/settings.txt ]] && grep -q 'Sound engine started' "$log"; do
        kill -0 "$game" 2>/dev/null || { echo "the game ended before the title screen" >&2; exit 1; }
        ((SECONDS < deadline)) || { echo "no title screen after 20 min" >&2; exit 1; }
        sleep 1
    done
    sleep 15
    shot title
    vin move 960 404; sleep 0.5; vin click left; sleep 3
    if [[ $HOMEKIND == nether ]]; then vin move 960 252; sleep 0.5; vin click left; sleep 2; fi
    shot create-screen
    vin move 672 924; sleep 0.5
    mark create_start
    vin click left
    vin move 960 1079
fi
if [[ $MODE == create && $CREATE_FLOW == menu ]]; then
    until [[ $log -nt $RIG/settings.txt ]] && grep -q 'joined the game' "$log"; do
        kill -0 "$game" 2>/dev/null || { echo "game ended before the setup flat home" >&2; exit 1; }
        ((SECONDS < deadline)) || exit 1
        sleep 0.2
    done
    mark setup_joined
    sleep 3
    vin key esc
    python3 -I "$here/ui.py" "$RIG" 'New home…'
    python3 -I "$here/ui.py" "$RIG" 'Home:' --prefix
    sleep 0.5
    shot create-screen
    python3 -I "$here/ui.py" "$RIG" 'Create' --prefix
    shot create-confirmation
    python3 -I "$here/ui.py" "$RIG" 'Make the new home' --mark create_start
    until grep -q 'New home: ready' "$log"; do
        kill -0 "$game" 2>/dev/null || { echo "game ended while switching to the Nether" >&2; exit 1; }
        ((SECONDS < deadline)) || { echo "Nether switch did not finish" >&2; exit 1; }
        sleep 0.2
    done
fi
if [[ $MODE == create && $CREATE_FLOW != manual ]]; then
    until [[ -s $RIG/creation-marks.txt ]]; do
        kill -0 "$game" 2>/dev/null || { echo "game ended before creation was observed" >&2; exit 1; }
        ((SECONDS < deadline)) || { echo "no creation observation" >&2; exit 1; }
        sleep 0.1
    done
    python3 -I "$here/creation.py" "$RIG" "$HOMEKIND" "$CREATE_FLOW"
fi
until [[ $log -nt $RIG/settings.txt ]] && grep -q 'joined the game' "$log"; do
    kill -0 "$game" 2>/dev/null || { echo "the game ended before the world opened" >&2; exit 1; }
    ((SECONDS < deadline)) || { echo "no world after 20 min" >&2; exit 1; }
    sleep 0.5
done
mark joined
if [[ $MODE == create && $HOMEKIND == flat ]]; then
    until grep -q 'The town is built' "$log"; do
        ((SECONDS < deadline)) || { echo "no town after 20 min" >&2; exit 1; }
        sleep 0.5
    done
    mark town_built
fi

if [[ $MODE == hold ]]; then
    kill "$health" 2>/dev/null || true; wait "$health" 2>/dev/null || true; health=
    echo "$(date +%T) holding: drive it with $RIG/vin, stop it by quitting the game"
    while kill -0 "$game" 2>/dev/null; do sleep 2; done
    exit 0
fi

# Startup is measured from game-scope PID detection; Gradle preparation and Prism startup are excluded.
mark settling
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
# FLIGHT=glide: the same start, then the rig's data pack moves him along the same legs (1200 ticks, level, through
# the terrain) while the camera turns with him; no keys held. Its glidetick stops by itself after 1200 ticks.
quarter=$((WINDOW / 4))
if [[ $FLIGHT != none ]]; then
    vin key h; sleep 1.5
    vin key lshift down; sleep 1; vin key lshift up; sleep 0.5
    vin key space down; sleep 0.1; vin key space up; sleep 0.1; vin key space down; sleep 0.1; vin key space up
    sleep 0.3
    vin key space down; sleep 2.5; vin key space up
    if [[ $FLIGHT == glide ]]; then chat "function glide"; else vin key w down; vin key lctrl down; fi
    mark flight_start
    sleep "$quarter"
    vin rel 1263 0 20
    sleep $((quarter * 2))
    vin rel 1263 0 20
    sleep $((WINDOW - quarter * 3))
    mark flight_end
    vin key w up; vin key lctrl up
    # Outside the windows: a picture of where the flight ended (above home, over the logos), to check it flew.
    [[ $SHOTS != 1 ]] || shot after-flight
    python3 -I "$here/snap.py" "$game" flight "$RIG"
    # The glide's tick count goes to the game's log ("pkg41 glide ticks: 1200" for the whole route).
    [[ $FLIGHT != glide ]] || { chat "function halt"; sleep 1; }
fi

if ((LONG > 0)); then
    vin key h; sleep 2
    mark idle_start
    # No input: this is deliberately the visible, idle world (vanilla eventually limits to 30 fps).
    for ((minute = 1; minute <= LONG; minute++)); do
        sleep 60
        python3 -I "$here/snap.py" "$game" "idle${minute}m" "$RIG"
    done
    mark idle_end
fi

if ((COVER > 0)); then
    wayland=$(sed -n 's/^WAYLAND_DISPLAY=//p' "$RIG/env")
    [[ -n $wayland && $wayland != wayland-0 ]] || { echo "refusing display '$wayland'" >&2; exit 1; }
    env -u DISPLAY WAYLAND_DISPLAY="$wayland" /usr/bin/foot --app-id=pkg41.Cover --title="Cover" -e /usr/bin/sleep 3600 \
        >"$RIG/cover.txt" 2>&1 &
    cover=$!
    sleep 2
    python3 -I "$WT/reviews/40-real-home/rig/tl.py" "$RIG" max pkg41.Cover >>"$RIG/cover.txt" 2>&1
    mark covered_start
    cover_start=$SECONDS
    python3 -I "$here/snap.py" "$game" covered0 "$RIG"
    if [[ $COVER_ACTION != none || -n $RECLAIM ]]; then
        delay=$((cover_start + 30 - SECONDS)); ((delay <= 0)) || sleep "$delay"
        python3 -I "$here/scope.py" "$game" "$PKG49_GAME_UNIT" gc-trim "$RIG"
        [[ -z $RECLAIM ]] || python3 -I "$here/scope.py" "$game" "$PKG49_GAME_UNIT" "reclaim:$RECLAIM" "$RIG"
        if [[ $FREEZE == 1 ]]; then
            # Set before the write: an interrupted freeze is still thawed by cleanup.
            frozen=1
            python3 -I "$here/scope.py" "$game" "$PKG49_GAME_UNIT" freeze "$RIG"
        fi
    fi
    for ((t = 60; t <= COVER; t += 60)); do
        delay=$((cover_start + t - SECONDS)); ((delay <= 0)) || sleep "$delay"
        PKG49_FROZEN=$frozen python3 -I "$here/snap.py" "$game" "covered$((t / 60))m" "$RIG"
    done
    delay=$((cover_start + COVER - SECONDS)); ((delay <= 0)) || sleep "$delay"
    mark covered_end
    python3 -I "$WT/reviews/40-real-home/rig/tl.py" "$RIG" list >>"$RIG/cover.txt" 2>&1
    # Record the complete return request, then start the ten-second frame window when the cover closes.
    mark return_start
    python3 -I - "$game" "$RIG/faults-return.json" <<'PYFAULT'
import json, sys, time
fields = open(f'/proc/{int(sys.argv[1])}/stat').read().rsplit(')', 1)[1].split()
json.dump({'monotonic_ns': time.monotonic_ns(), 'majflt': int(fields[9]), 'minflt': int(fields[7])}, open(sys.argv[2], 'w'))
PYFAULT
    if [[ $frozen == 1 ]]; then
        python3 -I "$here/scope.py" "$game" "$PKG49_GAME_UNIT" thaw "$RIG"
        frozen=0
    fi
    kill "$cover" 2>/dev/null || true; wait "$cover" 2>/dev/null || true; cover=
    mark wake_start
    python3 -I "$WT/reviews/40-real-home/rig/tl.py" "$RIG" activate aresos-desktop >>"$RIG/cover.txt" 2>&1
    # Repeated input makes this an active return; the probe's single count left vanilla capped at 30 fps.
    python3 -I "$here/wake.py" "$RIG"
    mark wake_end
    python3 -I "$here/snap.py" "$game" wake "$RIG"
fi
# Pictures for the report, after every measurement: from the pad looking south over the biggest group, and from
# above it. Only the rig's own test logos are in them.
if [[ $SHOTS == 1 ]]; then
    [[ -z $cover ]] || { kill "$cover" 2>/dev/null || true; cover=; sleep 2; }
    # Hand the keyboard to the world after the cover closes, as a click on it would.
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
if ((QUIT)); then
    python3 -I "$here/terminal.py" "$game" "$PKG49_GAME_UNIT" "$RIG"
    kill "$health" 2>/dev/null || true; wait "$health" 2>/dev/null || true; health=
    # Close the game's window as he would: the game saves the world and quits; keep that save.
    python3 -I "$WT/reviews/40-real-home/rig/tl.py" "$RIG" close aresos-desktop >/dev/null 2>&1 || true
    for _ in $(seq 240); do kill -0 "$game" 2>/dev/null || break; sleep 0.5; done
    if kill -0 "$game" 2>/dev/null; then
        echo "the game did not quit within 2 min" >&2
        exit 1
    else
        # A vanished PID alone could be a crash. Require the launcher to confirm a clean exit before reusing the save.
        for _ in $(seq 100); do grep -q '^GAME_EXIT=' "$RIG/env" && break; sleep 0.1; done
        game_exit=$(sed -n 's/^GAME_EXIT=//p' "$RIG/env" | tail -n 1)
        [[ $game_exit == 0 ]] || { echo "creation did not exit cleanly: ${game_exit:-unknown}" >&2; exit 1; }
        rm -rf -- "$RIG/world"; cp -a -- "$SAVE" "$RIG/world"
        echo "$(date +%T) the save is in $RIG/world"
    fi
fi
mark done
# Run cleanup in this shell (a subshell would leave its interruptible-sleep child behind).
trap - EXIT
finish_status=0
finish_for_analysis=1
finish
python3 -I "$here/analyze.py" "$RIG" "$OUT"
