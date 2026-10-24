"""Apply the new checkpoint rule to every original 11k capture; do not invent old write receipts."""
import ast
import hashlib
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, 'os/ci')
from disk_audit import boot_variables, check_boot_next
from grub_bls import stock_bls_entry

root = pathlib.Path('os/manifest/ci/11k')
records = []
for path in sorted(root.rglob('*-nvram.json')):
    store = json.loads(path.read_text())
    raw = path.with_name(path.name.replace('-nvram.json', '-vars.fd'))
    assert raw.is_file() and boot_variables(raw) == store
    proof = check_boot_next(store, windows_default=True)
    assert 'BootNext' not in store
    records.append(dict(path=path.as_posix(), vars=raw.as_posix(), result=proof,
        receipt_sha256=hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
        vars_sha256=hashlib.sha256(raw.read_bytes()).hexdigest()))
assert len(records) == 32
source = subprocess.check_output(['git', 'show', '2524823:os/ci/rehearsal_guard.py']).decode()
current = pathlib.Path('os/ci/rehearsal_guard.py').read_text()
for name in ('failure_status', 'read_only', 'api'):
    nodes = [next(n for n in ast.parse(s).body if isinstance(n, ast.FunctionDef) and n.name == name) for s in (source, current)]
    assert ast.dump(nodes[0]) == ast.dump(nodes[1]), name
entries = json.loads((root / 'full-5/two-disk/protected-second/b-bls-entries.json').read_text())
deployments = json.loads((root / 'full-5/two-disk/protected-second/b-aresos-order.json').read_text())['deployments']
stock = json.loads((root / 'full-5/two-disk/protected-second/result.json').read_text())['retained_stock_checksum']
selection = stock_bls_entry(entries, stock, deployments)
assert selection['id'] == 'ostree-1' and selection['menu_index'] == 1
result = dict(status='passed', captures=32, absent_bootnext=32, records=records, retained_11k_selection=selection,
              retry_functions_unchanged=True,
              limit='11k retained post-boot stores contain no BootNext. This verifies all checkpoint absences, not historical pre-boot write authorization; 11l adds those receipts prospectively.')
pathlib.Path('os/manifest/ci/11l/11k-bootnext-replay.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('11l replay passed: all 32 original 11k raw/JSON captures have no BootNext; actual stock selects at position1; 11k retry functions unchanged.')
