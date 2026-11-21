#!/usr/bin/bash
# Package 328 rig: the native development client (`runClient`, real pointer capture) as the session's desktop window
# in the rig's headless labwc, through mod/dev/run-hub.sh (its memory and Lunar checks, its own helper socket, its scope
# cleanup). Run it through in-rig.sh, so it reaches only the rig's displays and private D-Bus:
#
#   in-rig.sh <run folder> game reviews/328-look-around/rig/game.sh
#
# - It holds the shared client-test lock (~/.cache/aresos-dev/client-test.lock) for the whole run: one game client
#   at a time on the laptop.
# - The helper is the checkout's own aresos-shell (unchanged), through a wrapper that gives it an empty home folder,
#   so it sees none of the owner's apps; its registry holds only the rig's probe. Super is its SIGUSR1, as the
#   supervisor's `aresos-desktop search` sends it (super.sh).
# - The save is the development client's own mod/run/saves/AresHub in this worktree: the first start makes the flat
#   home there (package 48). Never the owner's Prism instance, ~/.minecraft or ~/AresOS-try.
set -euo pipefail
: "${RIG:?run through in-rig.sh}"
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
[[ ${WAYLAND_DISPLAY:-wayland-0} != wayland-0 && ${DISPLAY:-:0} != :0 ]] || { echo "refusing the owner's display" >&2; exit 1; }
/usr/bin/mkdir -p -- "$RIG/home" "$RIG/registry"
cat >"$RIG/helper" <<EOF
#!/usr/bin/bash
# The rig's helper: the checkout's aresos-shell with an empty home folder (written by game.sh).
exec /usr/bin/env HOME="$RIG/home" XDG_DATA_HOME="$RIG/home/.local/share" /usr/bin/python3 -I "$WT/os/config/usr/libexec/aresos-shell" "\$@"
EOF
/usr/bin/chmod +x -- "$RIG/helper"
cat >"$RIG/registry/probe.json" <<EOF
{"schema": 1, "id": "probe", "name": "Probe", "argv": ["/usr/bin/python3", "-I", "$here/probe.py", "$RIG"],
 "working_directory": "~", "window": {"app_ids": ["aresos.pkg328.probe"], "instance": "multi"}}
EOF
exec {lock}>>"$HOME/.cache/aresos-dev/client-test.lock"
echo "waiting for the client-test lock" >&2
/usr/bin/flock "$lock"
echo "holding the client-test lock" >&2
# Another worktree's Gradle (a build.sh, which takes no lock) or too little memory: wait, up to 30 minutes.
others() {
    local pid exe cwd
    for pid in $(/usr/bin/pgrep -f 'org\.gradle\.(wrapper\.GradleWrapperMain|launcher\.daemon\.bootstrap\.GradleDaemon)'); do
        exe=$(/usr/bin/readlink "/proc/$pid/exe" 2>/dev/null) || continue
        [[ $exe == */java ]] || continue
        cwd=$(/usr/bin/readlink "/proc/$pid/cwd" 2>/dev/null) || continue
        [[ $cwd == "$WT" || $cwd == "$WT"/* ]] || return 0
    done
    return 1
}
for _ in $(seq 360); do
    kib=$(/usr/bin/awk '$1 == "MemAvailable:" { print $2 }' /proc/meminfo)
    if ! others && ((kib >= 6 * 1024 * 1024)); then break; fi
    sleep 5
done
echo "starting: $((kib / 1024)) MiB available" >&2
# The game maps on the output under the pointer: the left one, where the probe and trial.py expect it.
/usr/bin/python3 -I "$here/vinput.py" "$RIG" abs 640 360 >/dev/null
# run-hub.sh starts the helper with --socket in its private folder and the game with the same launch identity.
"$WT/mod/dev/run-hub.sh" --helper "$RIG/helper" --registry "$RIG/registry" "$@" &
echo "RUNHUB_PID=$!" >>"$RIG/env"
wait
