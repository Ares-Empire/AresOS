#!/usr/bin/bash
set -euo pipefail
python3 - <<'PREVIOUS'
import json, subprocess
status = json.loads(subprocess.check_output(['bootc', 'status', '--json']))['status']
assert not status.get('staged') and not status.get('rollbackQueued'), 'STOP: pending deployment before previous; see EMERGENCY.md / get help'
slot = status['rollback']
assert slot['image']['image']['image'] == '@PREVIOUS@' and slot['image']['imageDigest'] == '@PREVIOUS_DIGEST@', 'STOP: rollback is not the previous AresOS'
assert slot['ostree']['checksum'] == '@PREVIOUS_CHECKSUM@' and not slot['pinned'], 'STOP: rollback identity differs'
print('Returning to the previous AresOS:', '@PREVIOUS@')
PREVIOUS
bootc rollback
