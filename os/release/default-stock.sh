#!/usr/bin/bash
set -euo pipefail
python3 - <<'PY'
import json, re, subprocess
expected = '@STOCK_CHECKSUM@'
assert re.fullmatch(r'[0-9a-f]{64}', expected), 'Supply the privately recorded stock checksum'
status = json.loads(subprocess.check_output(['bootc', 'status', '--json']))['status']
stock = status['booted']
assert stock['ostree']['checksum'] == expected, stock
assert stock['image']['imageDigest'] == '@BASE_DIGEST@', stock
assert stock['image']['image']['image'].startswith(('ghcr.io/ublue-os/bazzite-nvidia-open@sha256:', 'ghcr.io/ublue-os/bazzite-nvidia-open:')), stock
deployments = json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))['deployments']
assert not any(d.get('staged') for d in deployments), deployments
booted = [(i, d) for i, d in enumerate(deployments) if d.get('booted')]
assert len(booted) == 1 and booted[0][1]['checksum'] == expected, deployments
index, deployment = booted[0]
subprocess.run(['ostree', 'admin', 'set-default', str(index)], check=True)
after = json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))['deployments']
assert after[0]['booted'] and after[0]['checksum'] == expected, after
print('Default is the identity-checked booted stock deployment:', expected)
PY
