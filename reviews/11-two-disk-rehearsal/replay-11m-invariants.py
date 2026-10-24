"""Confirm 11m changes only the guard; preserve the 11l route and 11k captures."""
import ast
import hashlib
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, 'os/ci')
import rehearsal_guard as guard
from disk_audit import boot_variables, check_boot_next

source = '81592192fd0189c59285a6ab958c0b62b05811af'
paths = ['os/ci/two_disk_vm.py', 'os/ci/grub_bls.py', 'os/ci/disk_audit.py', 'os/ci/stock_probe.py',
         'os/ci/rehearsal_auth.py', '.github/workflows/os-image.yml', 'os/manifest/base.json',
         'os/manifest/release.json', 'os/release/switch.sh', 'os/release/pin-stock.sh',
         'os/release/pause-stock-updates.sh', 'os/release/default-stock.sh',
         '.github/workflows/privacy-check.yml', '.gitleaks.toml', '.gitleaksignore',
         'os/tests/test_rehearsal_budget.py']
hashes = []
for name in paths:
    raw = pathlib.Path(name).read_bytes().replace(b'\r\n', b'\n')
    assert raw == subprocess.check_output(['git', 'show', source + ':' + name]), name
    hashes.append(dict(path=name, sha256=hashlib.sha256(raw).hexdigest()))
old = ast.parse(subprocess.check_output(['git', 'show', source + ':os/ci/rehearsal_guard.py']))
new = ast.parse(pathlib.Path('os/ci/rehearsal_guard.py').read_text())
for name in ('failure_status', 'read_only', 'job_minutes', 'require_probe'):
    nodes = [next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name) for tree in (old, new)]
    assert ast.dump(nodes[0]) == ast.dump(nodes[1]), name
assert (guard.START, guard.MINUTE_CAP, guard.FULL_CAP, guard.PART_B_CAP) == ('2026-10-23T16:21:00Z', 900, 5, 1)
assert guard.RETRY_WAITS == (10, 20, 40, 60)
captures = []
for path in sorted(pathlib.Path('os/manifest/ci/11k').rglob('*-nvram.json')):
    raw = path.with_name(path.name.replace('-nvram.json', '-vars.fd'))
    store = json.loads(path.read_text())
    assert boot_variables(raw) == store and 'BootNext' not in store
    check_boot_next(store, windows_default=True)
    captures.append(dict(path=path.as_posix(), vars=raw.as_posix(),
        receipt_sha256=hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
        vars_sha256=hashlib.sha256(raw.read_bytes()).hexdigest()))
assert len(captures) == 32
result = dict(status='passed', unchanged_source=source, unchanged_files=hashes,
              unchanged_retry_functions=['failure_status', 'read_only'], unchanged_accounting_functions=['job_minutes', 'require_probe'],
              bootnext_replay_captures=32, records=captures,
              limit='Historical post-boot absence only; no historical pre-boot write receipt is manufactured.')
root = pathlib.Path('os/manifest/ci/11m'); root.mkdir(parents=True, exist_ok=True)
(root / 'invariants.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('11m invariants passed: 11l route/workflow/security/pins/budget tests unchanged; retry/cost/probe checks unchanged; 32 original BootNext captures replayed.')
