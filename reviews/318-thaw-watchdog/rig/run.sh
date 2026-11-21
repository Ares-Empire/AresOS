#!/usr/bin/bash
# Take the laptop-wide lock before modifying the run world or starting any heavy work.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
source "$here/../../../mod/dev/env.sh"
aresos_find_java
aresos_check_room 0
mkdir -p "$ARESOS_DEV_CACHE"
aresos_lock "$ARESOS_CLIENT_TEST_LOCK" "another game run on this laptop"
aresos_check_room 0
# Use package 47's independent owner/holder lifecycle for both sides of every pair.
aresos_supervise
node=
for n in /sys/class/drm/renderD*; do
    [[ -r $n/device/vendor && $(<"$n/device/vendor") == 0x10de ]] && { node=$n; break; }
done
[[ -n $node ]] || aresos_fail 1 "No NVIDIA render node."
pci=$(readlink -f -- "$node/device")
aresos_hold_nvidia "${pci##*/}" || aresos_fail 1 "Cannot hold NVIDIA awake."
export PKG49_LOCK_HELD=1
# Package 318 reads this card's power/runtime_status around the freeze and the thaw (read-only).
export PKG318_GPU_PCI=${pci##*/}
# Keep the outer EXIT trap: exec would discard the holder's cleanup.
aresos_scoped pkg318-controller -- "$here/measure.sh" "$@"
