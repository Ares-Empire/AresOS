#!/usr/bin/bash
set -euo pipefail
python3 - <<'PY'
import json, subprocess
status = json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))
booted = [(i, d) for i, d in enumerate(status['deployments']) if d.get('booted')]
assert len(booted) == 1 and not any(d.get('staged') for d in status['deployments']), status
index, deployment = booted[0]
assert 'bazzite-nvidia-open' in deployment.get('container-image-reference', ''), deployment
subprocess.run(['ostree', 'admin', 'pin', str(index)], check=True)
print('Pinned booted stock deployment:', deployment['checksum'])
PY
