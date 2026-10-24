#!/usr/bin/bash
set -euo pipefail
test "$(id -u ares-recovery)" = 1000
if getent passwd ares; then
    echo 'Refusing switch: daily account ares already exists'
    exit 1
fi
test -z "$(getent passwd 1001)"
test -r /etc/ostree/auth.json
python3 - <<'PY'
import json, subprocess
state = json.loads(subprocess.check_output(['bootc', 'status', '--json']))['status']
assert not state.get('staged') and not state.get('rollbackQueued'), 'STOP: pending deployment before switch; see EMERGENCY.md / get help'
PY
bootc switch --retain @REFERENCE@
