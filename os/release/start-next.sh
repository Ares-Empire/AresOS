#!/usr/bin/bash
set -euo pipefail
# The one reorder of the owner tools (package 22c, rule 3): the identity-checked
# deployment becomes the first one, which starts next. Nothing is created or
# removed, and no pin, kernel argument or /etc is touched.
python3 - <<'START_NEXT'
import json, subprocess, sys
def deployments():
    return json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))['deployments']
def refuse(reason):
    # Exit status 3 means only this: refused before set-default ran, so nothing was
    # changed, and the tools close their intent. Every other failure exits otherwise
    # and may follow the change: the tools keep their journal open (review 2).
    print('STOP: ' + reason + '; nothing was changed', file=sys.stderr, flush=True)
    sys.exit(3)
target = ('@CHECKSUM@', int('@SERIAL@'))
# Read immediately before the call: the index belongs to this list.
before = deployments()
if before != json.loads(bytes.fromhex('@BEFORE@')):
    refuse('deployment list changed outside the tools since the intent')
if any(d.get('staged') for d in before):
    refuse('a staged deployment exists')
found = [i for i, d in enumerate(before) if (d['checksum'], d['serial']) == target]
if len(found) != 1:
    refuse('the target deployment is missing or listed twice')
index = found[0]
row = before[index]
if row['container-image-reference-digest'] != '@DIGEST@' or row['container-image-reference'] != '@REFERENCE@':
    refuse('the target deployment has another digest or reference')
if index == 0:
    refuse('the target deployment already starts next')
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
