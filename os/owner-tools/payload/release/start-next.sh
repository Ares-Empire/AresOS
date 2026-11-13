#!/usr/bin/bash
set -euo pipefail
# The one reorder of the owner tools (package 22c, rule 3): the identity-checked
# deployment becomes the first one, which starts next. Nothing is created or
# removed, and no pin, kernel argument or /etc is touched.
python3 - <<'START_NEXT'
import json, subprocess
def deployments():
    return json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))['deployments']
target = ('@CHECKSUM@', int('@SERIAL@'))
# Read immediately before the call: the index belongs to this list.
before = deployments()
assert before == json.loads(bytes.fromhex('@BEFORE@')), \
    'STOP: deployment list changed outside the tools since the intent; nothing was changed; get help'
assert not any(d.get('staged') for d in before), 'STOP: a staged deployment exists; nothing was changed'
found = [i for i, d in enumerate(before) if (d['checksum'], d['serial']) == target]
assert len(found) == 1, 'STOP: the target deployment is missing or listed twice; nothing was changed'
index = found[0]
row = before[index]
assert row['container-image-reference-digest'] == '@DIGEST@' and row['container-image-reference'] == '@REFERENCE@', \
    'STOP: the target deployment has another digest or reference; nothing was changed'
assert index > 0, 'STOP: the target deployment already starts next; nothing was changed'
subprocess.run(['ostree', 'admin', 'set-default', str(index)], check=True)
# The deployments share their boot entries, so ostree only swaps a link, after
# its own last sync (probe run 43470161858: "bootconfig swap: no"). Without
# this sync a durable record could sit beside an order that is not durable yet.
subprocess.run(['sync'], check=True)
after = deployments()
assert after == [row] + [d for i, d in enumerate(before) if i != index], \
    'STOP: the deployment list after the change is not the intended one; do not restart; get help'
print('Starts next:', '@REFERENCE@')
START_NEXT
