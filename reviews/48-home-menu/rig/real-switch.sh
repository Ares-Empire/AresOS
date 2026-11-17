#!/usr/bin/bash
# DEVELOPMENT AID of package 48 (one check by hand), headless use only: starts the development client as a session
# game (package 41's rig: its own headless labwc, the restricted helper, virtual input; never the owner's display)
# with no AresHub in mod/run/saves, so the first start makes the flat home, and holds until the game quits. Drive it
# with "echo '<command>' > <rig>/vin" (vinput.py's commands) and take pictures with
# reviews/40-real-home/rig/shot.sh <rig> <file.png>; quit with
# "python3 -I reviews/40-real-home/rig/tl.py <rig> close aresos-desktop" (the game saves and quits).
#
#   real-switch.sh <name>
#
# Scratch in .work/pkg48/<name>/; earlier saves in mod/run/saves are moved there first (nothing is deleted).
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
rig41=$WT/reviews/41-home-memory/rig
name=${1:?usage: real-switch.sh <name>}
[[ $name =~ ^[a-z0-9-]+$ ]] || { echo "name: lowercase letters, digits and dashes" >&2; exit 2; }
JDK=${JAVA_HOME:-$HOME/.local/opt/jdk-25}
WORK=$WT/.work/pkg48
RIG=$WORK/$name
APPS=$WORK/apps
HOMEDIR=$WORK/home
SAVES=$WT/mod/run/saves
[[ ! -e $RIG ]] || { echo "$RIG exists already; pick another name" >&2; exit 2; }
if [[ -n $(systemctl --user list-units --no-legend --plain 'pkg41-rig-*' 'pkg41-game-*' 'pkg48-game-*' 2>/dev/null) ]]; then
    echo "another run of this rig is going; run one at a time" >&2; exit 75
fi
mkdir -p "$RIG" "$HOMEDIR" "$SAVES"
[[ -d $APPS ]] || python3 -I "$rig41/make-apps.py" "$APPS"
# A first start: no AresHub (nor any earlier run's folders) in the development client's saves.
if [[ -n $(ls -A -- "$SAVES") ]]; then mv -- "$SAVES" "$RIG/saves-before"; mkdir -p "$SAVES"; fi
python3 -I - "$WT/mod/run/options.txt" <<'PY'
import os, sys
path = sys.argv[1]
lines = open(path).read().splitlines() if os.path.exists(path) else []
want = {'fullscreen': 'false', 'onboardAccessibility': 'false', 'tutorialStep': 'none', 'guiScale': '4'}
seen = set()
for i, line in enumerate(lines):
    key = line.split(':', 1)[0]
    if key in want:
        lines[i] = f'{key}:{want[key]}'; seen.add(key)
lines += [f'{k}:{v}' for k, v in want.items() if k not in seen]
open(path, 'w').write('\n'.join(lines) + '\n')
PY
# Gradle's JDK folder whose bin/java puts the game in a scope of its own (package 41's java-wrapper.sh).
mkdir -p "$RIG/jdk/bin"
for entry in "$JDK"/*; do [[ ${entry##*/} == bin ]] || ln -s -- "$entry" "$RIG/jdk/${entry##*/}"; done
for entry in "$JDK"/bin/*; do [[ ${entry##*/} == java ]] || ln -s -- "$entry" "$RIG/jdk/bin/${entry##*/}"; done
cp -- "$rig41/java-wrapper.sh" "$RIG/jdk/bin/java"
export RIG APPS HOMEDIR SIZE=1920x1080 REFRESH=60 GAME_ARGS=
export PKG41_JAVA=$RIG/jdk/bin/java PKG41_REAL_JAVA=$JDK/bin/java PKG41_JAVA_LOG=$RIG/java.txt
export PKG41_GAME_UNIT="pkg48-game-$name-$$.scope" PKG41_MEMORY_HIGH=5G PKG41_JVM_ARGS="-Xms512m -Xmx3072m"
date -Is >"$RIG/started"
"$rig41/start.sh" >"$RIG/start.txt" 2>&1 &
start_pid=$!
game=
finish() {
    local status=$?
    trap - EXIT
    systemctl --user stop "$PKG41_GAME_UNIT" 2>/dev/null || true
    for _ in $(seq 120); do kill -0 "$start_pid" 2>/dev/null || break; sleep 0.5; done
    kill -0 "$start_pid" 2>/dev/null && systemctl --user stop "pkg41-rig-$start_pid.scope" 2>/dev/null || true
    wait "$start_pid" 2>/dev/null || true
    cp -f -- "$WT/mod/run/logs/latest.log" "$RIG/game.txt" 2>/dev/null || true
    ls -la -- "$SAVES" >"$RIG/saves-after.txt" 2>&1 || true
    exit "$status"
}
trap finish EXIT
trap 'exit 130' INT TERM
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
echo "GAME_PID=$game" | tee -a "$RIG/started"
# Holds until the game quits, at most an hour.
for _ in $(seq 1800); do kill -0 "$game" 2>/dev/null || break; sleep 2; done
