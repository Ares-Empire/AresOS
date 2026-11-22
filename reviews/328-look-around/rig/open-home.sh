#!/usr/bin/bash
# Package 328 rig: after game.sh, opens AresHub from the title screen and puts the probe over the world's centre.
# The first start of a fresh mod/run shows Minecraft's accessibility screen first: click Continue by hand then.
#
#   open-home.sh <run folder>
set -euo pipefail
RIG=$(/usr/bin/realpath -- "${1:?usage: open-home.sh <run folder>}")
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# The probe would hide the title screen's buttons.
units=$(systemctl --user list-units --no-legend --plain 'pkg328-probe-*' | /usr/bin/awk '{print $1}')
[[ -z $units ]] || systemctl --user stop $units
button() {
    "$here/in-rig.sh" "$RIG" shot /usr/bin/grim -o HEADLESS-1 "$RIG/title.png"
    /usr/bin/python3 -I -c 'import sys; from PIL import Image
r, g, b = Image.open(sys.argv[1]).convert("RGB").getpixel((435, 270))
sys.exit(0 if abs(r - g) < 8 and abs(g - b) < 8 and 90 < r < 200 else 1)' "$RIG/title.png"
}
for _ in $(seq 120); do button && break; sleep 1; done
button || { echo "no title screen with the AresOS button" >&2; exit 1; }
joined=$(/usr/bin/grep -c 'joined the game' "$RIG/game.log" || true)
"$here/vinput.py" "$RIG" abs 435 281 >/dev/null
"$here/vinput.py" "$RIG" click left >/dev/null
for _ in $(seq 120); do
    (( $(/usr/bin/grep -c 'joined the game' "$RIG/game.log" || true) > joined )) && break
    sleep 1
done
sleep 4
"$here/in-rig.sh" "$RIG" probe /usr/bin/python3 -I "$here/probe.py" "$RIG" 640 400 >>"$RIG/probe.out" 2>&1 &
sleep 1.5
"$here/state.sh" "$RIG"
