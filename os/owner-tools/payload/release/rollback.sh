#!/usr/bin/bash
set -euo pipefail
python3 - <<'PY'
import json, subprocess
status = json.loads(subprocess.check_output(['bootc', 'status', '--json']))
previous = status['status']['rollback']['image']
reference = previous['image']['image']
assert reference.startswith(('ghcr.io/ublue-os/bazzite-nvidia-open@sha256:', 'ghcr.io/ublue-os/bazzite-nvidia-open:')), reference
assert previous['imageDigest'] == '@BASE_DIGEST@', previous
print('Returning to retained Bazzite:', reference, previous['imageDigest'])
PY
bootc rollback
