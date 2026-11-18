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
export PKG49_LOCK_HELD=1
exec "$here/measure.sh" "$@"
