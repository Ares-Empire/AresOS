#!/usr/bin/bash
set -euo pipefail
test -r /etc/ostree/auth.json
python3 - <<'UPDATE'
import json, subprocess
status = json.loads(subprocess.check_output(['bootc', 'status', '--json']))['status']
assert not status.get('staged') and not status.get('rollbackQueued'), 'STOP: pending deployment before update; see EMERGENCY.md / get help'
running = status['booted']['image']
assert running['image']['image'] == '@CURRENT@' and running['imageDigest'] == '@CURRENT_DIGEST@', 'STOP: running release changed before update'
assert '@REFERENCE@' != '@CURRENT@', 'STOP: target equals the running release'
print('Staging the verified release over the running one:', '@REFERENCE@')
UPDATE
bootc switch --retain @REFERENCE@
