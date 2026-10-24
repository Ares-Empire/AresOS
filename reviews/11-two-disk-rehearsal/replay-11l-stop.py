"""Verify the stopped pre-probe result; bookkeeping never authorizes a dispatch."""
import base64
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, 'os/ci')
from rehearsal_guard import job_minutes
root = pathlib.Path('os/manifest/ci/11l')
source = '81592192fd0189c59285a6ab958c0b62b05811af'


def read(name):
    return json.loads((root / name).read_text(encoding='utf-8'))


initial, stop, diagnostic = [read(name) for name in ('initial-budget.json', 'guard-stop.json', 'budget-stop-diagnostic.json')]
assert initial['start'] == '2026-10-23T16:21:00Z' and initial['cap'] == 900
assert initial['consumed_minutes'] == 616 and initial['reserved_minutes'] == 186
assert initial['full_dispatched'] == 5 and initial['part_b_dispatched'] == 0
assert stop['status'] == 'STOP' and stop['source'] == source and stop['exit_code'] == 1
assert stop['stdout_bytes'] == 0 and not stop['new_authorization_written']
assert stop['previous_initial_receipt_unchanged'] and stop['previous_initial_receipt_never_used_for_dispatch']
assert stop['previous_initial_receipt_sha256'] == hashlib.sha256((root / 'initial-budget.json').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
assert stop['reason'] in pathlib.Path(stop['stderr_log']).read_text()
assert diagnostic['diagnostic_only'] and not diagnostic['authorization_written'] and diagnostic['guard_unchanged']
assert diagnostic['pages'][0]['returned'] == 100 and diagnostic['pages'][0]['oldest'] >= initial['start']
assert diagnostic['pages'][1]['newest'] >= initial['start'] > diagnostic['pages'][1]['oldest']
privacy = read('source-privacy-proof.json')
assert len(privacy) == 2
credential = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{25,}|\$(?:6|y)\$[./A-Za-z0-9$=]{15,})')
for proof in privacy:
    assert proof['head'] == source and proof['status'] == 'passed' and not proof['personal_terms_skip_warning']
    assert len(proof['checks']) == 3 and set(proof['checks'].values()) == {'success'}
    archive = pathlib.Path(f'reviews/11-two-disk-rehearsal/artifacts/11l-source-privacy-{proof["run"]}-logs.zip')
    raw = archive.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == proof['logs_zip_sha256']
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            content = z.read(name)
            assert not credential.search(content)
            for candidate in re.findall(rb'[A-Za-z0-9+/]{30,}={0,2}', content):
                try:
                    decoded = base64.b64decode(candidate, validate=True)
                except ValueError:
                    continue
                assert not credential.search(decoded)
        text = z.read('0_scan.txt').decode('utf-8')
    groups = re.findall(r'##\[group\]Run ([^\n]+)', text)
    assert any(g.startswith('docker run --rm') and 'gitleaks:v8.21.2' in g for g in groups)
    assert any(g.startswith('bad=$(git log --all') for g in groups)
    assert any(g.startswith('if [ -z "$PRIVATE_TERMS" ]') for g in groups)
    assert '##[error]' not in text and '##[warning]PRIVATE_TERMS secret is not set' not in text
minutes = sum(job_minutes(job) for proof in privacy for job in proof['jobs'])
assert minutes == 3 and diagnostic['bookkeeping_minutes'] == 616 + minutes == 619
assert set(diagnostic['allowance_run_ids']) == {r['run'] for r in initial['runs']} | {p['run'] for p in privacy}
assert diagnostic['full_dispatched'] == 5 and diagnostic['part_b_dispatched'] == 0 and diagnostic['no_11l_probe']
for path in ('os/ci/disk_audit.py', 'os/ci/two_disk_vm.py', 'os/ci/grub_bls.py', 'os/ci/rehearsal_guard.py',
             'os/ci/stock_probe.py', 'os/ci/rehearsal_auth.py', '.github/workflows/os-image.yml'):
    assert pathlib.Path(path).read_bytes().replace(b'\r\n', b'\n') == subprocess.check_output(['git', 'show', source + ':' + path])
for path in ('.github/workflows/privacy-check.yml', '.gitleaks.toml', '.gitleaksignore', 'os/manifest/base.json',
             'os/manifest/release.json', 'os/release/switch.sh', 'os/release/pause-stock-updates.sh', 'os/release/pin-stock.sh'):
    assert pathlib.Path(path).read_bytes().replace(b'\r\n', b'\n') == subprocess.check_output(['git', 'show', 'ec7b2ba:' + path])
print('11l STOP replay passed: complete-ledger refusal, no dispatch/authorization, 619 bookkeeping minutes, 5 full / 0 B; all source privacy checks and immutable/runtime blobs verified.')
