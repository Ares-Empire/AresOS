"""Bind the final review tree to the exact native/probe/Part B source."""
import hashlib
import json
import pathlib
import re
import subprocess

source = '46dc2dd1f62d3a3d4d8051e3ac3b06eb30db4760'
paths = subprocess.check_output(['git', 'ls-files', '--', 'os/ci', 'os/config', 'os/Containerfile',
    'os/release', 'os/tests', 'os/keys', '.github/workflows', '.gitleaks.toml', '.gitleaksignore',
    'os/manifest/base.json', 'os/manifest/release.json', 'os/manifest/installer-isos.json']).decode().splitlines()
assert 'os/tests/test_shell_assertions.py' in paths and 'os/ci/rehearsal_guard.py' in paths
records = []
for name in paths:
    raw = pathlib.Path(name).read_bytes().replace(b'\r\n', b'\n')
    assert raw == subprocess.check_output(['git', 'show', source + ':' + name]), name
    records.append(dict(path=name, sha256=hashlib.sha256(raw).hexdigest()))
guide = pathlib.Path('docs/INSTALL.md').read_text(encoding='utf-8')
old = subprocess.check_output(['git', 'show', source + ':docs/INSTALL.md']).decode()
blocks = lambda text: re.findall(r'^```bash\n(.*?)\n```', text, re.M | re.S)
assert blocks(guide) == blocks(old), 'Executable owner blocks changed after qualification'
reference = json.loads(pathlib.Path('os/manifest/release.json').read_text())['reference']
script = pathlib.Path('os/release/switch.sh').read_text().replace('@REFERENCE@', reference).strip()
assert blocks(guide).count(script) == 1
assert subprocess.check_output(['git', 'show', source + ':os/tests/test_grub_bls.py']) == pathlib.Path('os/tests/test_grub_bls.py').read_bytes().replace(b'\r\n', b'\n')
result = dict(status='source-byte-equivalence-only', qualified_source=source,
              payload_files_unchanged=records, all_owner_bash_blocks_unchanged=True,
              exact_switch_block_and_equality_test_unchanged=True,
              limit='This proves source equivalence, not a VM outcome. Qualification requires the retained run receipts and inspection.')
pathlib.Path('os/manifest/ci/11n/source-invariants.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Qualified source unchanged:', len(records), 'runtime/workflow/test/security/pin files; all executable owner blocks and exact switch equality preserved.')
