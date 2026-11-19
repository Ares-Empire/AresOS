#!/usr/bin/bash
# DEVELOPMENT AID of package 25 (the real-game check; copied from package 49b's rig, its measure.sh), headless use only:
# one launch of the real game for briefs/25-guardian.md's Acceptance.
#
#   run.sh <name> MODE=create|close|stop|verify [PROBE=n] [VERIFY=n,n]
#
#   MODE=create   no AresHub yet: the game makes the first home (a session with no home makes the flat one at once),
#                 its window is closed as he would, and the rig's probe data pack goes into the save
#   MODE=close    the close alone: probe block PROBE, no save asked, SIGTERM to the rig's own game, Java's exit
#   MODE=stop     the path: the real supervisor adopts the game; block PROBE, `save`, block PROBE+1, `stop`
#   MODE=verify   reopen the world, look, and quit by closing the window
#   VERIFY=n,n    blocks of the launch before: the reopened game is asked whether each is there (every mode but create)
#
# The home lives where the test supervisor looks for it, $WORK/home/.local/share/aresos/worlds/AresHub, as a real
# folder; mod/run/saves is a link to that worlds folder, as the instance's minecraft/saves is in the image
# (aresos-desktop, provision). The game's JVM alone gets the run's temporary XDG_RUNTIME_DIR ($RIG/rt) and, for
# close and stop, the gate (java-wrapper.py). check.py does the check; raw data stays in .work/pkg25/rigs/<name>/,
# the evidence goes to reviews/25-guardian/runs/<name>.json.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
name=${1:?usage: run.sh <name> MODE=create|close|stop|verify [PROBE=n] [VERIFY=n,n]}
[[ $name =~ ^[a-z0-9-]+$ ]] || { echo "name: lowercase letters, digits and dashes" >&2; exit 2; }
shift
MODE= PROBE=0 VERIFY= RD=8 SD=5 HEAP=1024 MIN_HEAP=256 MEMHIGH=2560M SIZE=1280x720 REFRESH=60
for setting; do
    key=${setting%%=*}
    case $key in
        MODE|PROBE|VERIFY|RD|SD|HEAP|MIN_HEAP|MEMHIGH|SIZE|REFRESH) printf -v "$key" '%s' "${setting#*=}" ;;
        *) echo "unknown setting $key" >&2; exit 2 ;;
    esac
done
case $MODE in create|close|stop|verify) ;; *) echo "MODE: create, close, stop or verify" >&2; exit 2 ;; esac
[[ $PROBE =~ ^[0-9]+$ && $VERIFY =~ ^([0-9]+(,[0-9]+)*)?$ ]] || { echo "PROBE: a number; VERIFY: numbers" >&2; exit 2; }
case $MODE in close) ((PROBE >= 1 && PROBE <= 56)) || exit 2 ;; stop) ((PROBE >= 1 && PROBE <= 55)) || exit 2 ;; esac
[[ ${PKG25_LOCK_HELD:-0} == 1 ]] || { echo "run through run.sh under the shared lock" >&2; exit 2; }
JDK=${JAVA_HOME:-$HOME/.local/opt/jdk-25}
WORK=$WT/.work/pkg25
RIG=$WORK/rigs/$name
OUT=$WT/reviews/25-guardian/runs/$name.json
APPS=$WORK/apps
HOMEDIR=$WORK/helper-home
WORLDS=$WORK/home/.local/share/aresos/worlds
SAVES=$WT/mod/run/saves
[[ ! -e $RIG ]] || { echo "$RIG exists already; pick another name" >&2; exit 2; }
# run.sh already holds the shared lock, before any world, options or build preparation.
if [[ -n $(systemctl --user list-units --no-legend --plain 'pkg25-rig-*' 'pkg25-game-*' 2>/dev/null) ]]; then
    echo "another run of this rig is going; run one at a time" >&2; exit 75
fi
kib=$(awk '$1 == "MemAvailable:" {print $2}' /proc/meminfo)
((kib >= 6 * 1024 * 1024)) || { echo "only $((kib / 1024)) MiB available; a run needs 6 GiB" >&2; exit 75; }
mkdir -p "$RIG" "$HOMEDIR" "$WORLDS" "$WT/mod/run"
[[ -d $APPS ]] || python3 -I "$here/make-apps.py" "$APPS"

# The world: never deleted or replaced here. The game's saves folder is the test supervisor's worlds folder.
if [[ -L $SAVES ]]; then
    [[ $(readlink -- "$SAVES") == "$WORLDS" ]] || { echo "$SAVES links somewhere else" >&2; exit 2; }
elif [[ -e $SAVES ]]; then
    rmdir -- "$SAVES" 2>/dev/null || { echo "$SAVES holds another run's worlds; move it aside first" >&2; exit 2; }
    ln -s -- "$WORLDS" "$SAVES"
else
    ln -s -- "$WORLDS" "$SAVES"
fi
if [[ $MODE == create ]]; then
    [[ ! -e $WORLDS/AresHub ]] || { echo "there is a home already; MODE=create makes the first one" >&2; exit 2; }
else
    [[ -d $WORLDS/AresHub/datapacks/pkg25-probe ]] || { echo "no home with the rig's data pack; MODE=create first" >&2; exit 2; }
fi
python3 -I - "$WT/mod/run/options.txt" "$RD" "$SD" <<'PY'
import os, sys
path, rd, sd = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines() if os.path.exists(path) else []
want = {'renderDistance': rd, 'simulationDistance': sd, 'fullscreen': 'false', 'onboardAccessibility': 'false',
        'tutorialStep': 'none', 'maxFps': '60'}
seen = set()
for i, line in enumerate(lines):
    key = line.split(':', 1)[0]
    if key in want:
        lines[i] = f'{key}:{want[key]}'; seen.add(key)
lines += [f'{k}:{v}' for k, v in want.items() if k not in seen]
open(path, 'w').write('\n'.join(lines) + '\n')
PY

# A folder Gradle takes for the JDK, whose bin/java starts the game as java-wrapper.py says.
mkdir -p "$RIG/jdk/bin"
for entry in "$JDK"/*; do [[ ${entry##*/} == bin ]] || ln -s -- "$entry" "$RIG/jdk/${entry##*/}"; done
for entry in "$JDK"/bin/*; do [[ ${entry##*/} == java ]] || ln -s -- "$entry" "$RIG/jdk/bin/${entry##*/}"; done
cp -- "$here/java-wrapper.py" "$RIG/jdk/bin/java"
chmod 755 "$RIG/jdk/bin/java"

export RIG APPS HOMEDIR SIZE REFRESH
export PKG25_JAVA=$RIG/jdk/bin/java PKG25_GAME_UNIT="pkg25-game-$name-$$.scope"
export PKG25_JVM_ARGS="-Xms${MIN_HEAP}m -Xmx${HEAP}m"
python3 -I -B "$here/check.py" prepare "$RIG" "$MODE" "$PKG25_GAME_UNIT" "$MEMHIGH" "$JDK/bin/java"
if [[ $MODE == create ]]; then export GAME_ARGS=; else export GAME_ARGS="--quickPlaySingleplayer AresHub"; fi
printf '%s\n' "name=$name" "MODE=$MODE" "PROBE=$PROBE" "VERIFY=$VERIFY" "RD=$RD" "SD=$SD" "HEAP=$HEAP" \
    "MEMHIGH=$MEMHIGH" "SIZE=$SIZE" "REFRESH=$REFRESH" "source_revision=$(git -C "$WT" rev-parse HEAD)" \
    "started=$(date -Is)" >"$RIG/settings.txt"

source "$here/lifecycle.sh"
rig_start "$here/start.sh"

echo "$(date +%T) waiting for the game ($name, $MODE)"
deadline=$((SECONDS + 1200))
until [[ -n $game ]]; do
    kill -0 "$start_pid" 2>/dev/null || { status=0; wait "$start_pid" || status=$?; echo "the rig ended early ($status); see $RIG/start.txt" >&2; exit "$((status == 0 ? 1 : status))"; }
    ((SECONDS < deadline)) || { echo "no game after 20 min" >&2; exit 1; }
    if systemctl --user --quiet is-active "$PKG25_GAME_UNIT" 2>/dev/null; then
        group=$(systemctl --user show -P ControlGroup "$PKG25_GAME_UNIT")
        game=$(head -1 "/sys/fs/cgroup$group/cgroup.procs" 2>/dev/null || true)
    fi
    sleep 1
done
mark game_detected
status=0
python3 -I -B "$here/check.py" run "$RIG" "$MODE" "$PROBE" "$VERIFY" "$health" || status=$?
mark checked
# Gradle's own word on how the game ended (inner.sh notes it), then the evidence.
for _ in $(seq 300); do grep -q '^GAME_EXIT=' "$RIG/env" 2>/dev/null && break; kill -0 "$start_pid" 2>/dev/null || break; sleep 0.2; done
python3 -I -B "$here/check.py" evidence "$RIG" "$OUT" || status=1
echo "$(date +%T) $name: check.py exit $status; evidence in ${OUT#"$WT"/}"
exit "$status"
