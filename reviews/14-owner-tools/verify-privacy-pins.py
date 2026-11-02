"""Read-only classification, not an exemption from the required privacy scan."""
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
proof = json.loads((ROOT / 'os/manifest/ci/14/privacy-stop/findings.json').read_text())
assert proof['finding_count'] == len(proof['findings']) == 5
for finding in proof['findings']:
    commit = finding['commit']
    assert re.fullmatch('[0-9a-f]{40}', commit)
    manifest = subprocess.check_output(['git', 'show', commit + ':' + finding['file']], cwd=ROOT).decode()
    line = manifest.splitlines()[finding['line'] - 1]
    match = re.fullmatch(r'\s*"([^"]+)": "([0-9a-f]{64})",?\s*', line)
    assert match and match[1] == finding['source_file']
    raw = subprocess.check_output(['git', 'show', commit + ':' + match[1]], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == match[2]
    print('Verified source integrity pin: ' + match[1])
print('PASS classification: five Git blob hashes; privacy remains BLOCKED; no rule/exemption changed')
