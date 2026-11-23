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
# Package 47's independent owner/holder lifecycle, as the rig this one is copied from uses it.
aresos_supervise
node=
for n in /sys/class/drm/renderD*; do
    [[ -r $n/device/vendor && $(<"$n/device/vendor") == 0x10de ]] && { node=$n; break; }
done
[[ -n $node ]] || aresos_fail 1 "No NVIDIA render node."
pci=$(readlink -f -- "$node/device")
aresos_hold_nvidia "${pci##*/}" || aresos_fail 1 "Cannot hold NVIDIA awake."
export PKG25_LOCK_HELD=1
# Keep the outer EXIT trap: exec would discard the holder's cleanup.
aresos_scoped pkg25-controller -- "$here/check.sh" "$@"
