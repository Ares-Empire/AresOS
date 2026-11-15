#!/usr/bin/bash
# DEVELOPMENT AID of package 41 (measurement only): checks that run.sh's flight flies at full speed. Run it against a
# rig started with `run.sh <name> MODE=hold` once the world is open: it flies run.sh's first two legs with the F3
# screen on and takes a picture just before each half turn, where F3 shows the position (XYZ). At sprint-flying speed
# (21.6 blocks a second) the first leg ends about 300 blocks north (Z about -300), the second about 300 south.
# With "spectator" (run.sh FLIGHT=spectator, a save with commands allowed) it flies the legs in spectator mode, as
# run.sh does in the Nether, and switches back to survival at the end.
set -euo pipefail
rig=${1:?usage: check-flight.sh <rig folder> [spectator]}
how=${2:-roads}
shot=$(cd -- "$(dirname -- "$0")/../../40-real-home/rig" && pwd)/shot.sh
vin() { echo "$*" >"$rig/vin"; }
mkdir -p "$rig/shots"
chat() { vin key slash; sleep 0.5; vin type "$1"; sleep 0.3; vin key enter; sleep 0.5; }
vin key h; sleep 1.5
if [[ $how == spectator ]]; then
    chat "gamemode spectator"; sleep 1
    vin key f3; sleep 0.5
else
    # Shift brings him down if he is still flying; landing ends flying, so the double jump starts it.
    vin key lshift down; sleep 1; vin key lshift up; sleep 0.5
    vin key f3; sleep 0.5
    # A double jump that every tick sees: each press and each gap lasts two ticks (a 40 ms tap can fall between ticks).
    vin key space down; sleep 0.1; vin key space up; sleep 0.1; vin key space down; sleep 0.1; vin key space up
    sleep 0.3
fi
vin key space down; sleep 2.5; vin key space up
"$shot" "$rig" "$rig/shots/check-start.png"
vin key w down; vin key lctrl down
sleep 14
"$shot" "$rig" "$rig/shots/check-leg1.png"
sleep 1
vin rel 1263 0 20
sleep 29
"$shot" "$rig" "$rig/shots/check-leg2.png"
sleep 1
vin key w up; vin key lctrl up
vin key f3
[[ $how != spectator ]] || { vin key h; sleep 1.5; chat "gamemode survival"; }
echo "pictures: $rig/shots/check-leg1.png (expect Z about -300) and check-leg2.png (expect Z about +300)"
