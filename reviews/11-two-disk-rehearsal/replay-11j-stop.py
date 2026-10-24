"""Recompute bookkeeping and bind the pre-full STOP without authorizing a run."""
import hashlib
import json
import pathlib
import subprocess
import sys

root = pathlib.Path('os/manifest/ci/11j')
source = '0210e3325fcbe786178d1b7e5cbbd962934dd11b'
inputs = []


def read(path):
    inputs.append(path)
    return json.loads(path.read_text())


stop = read(root / 'dispatch-guard-stop.json')
assert stop['source'] == source and stop['status'] == 'stopped-before-full-dispatch'
assert not stop['authorization_returned'] and not stop['full_dispatched'] and not stop['budget_or_rules_changed']
assert len(stop['attempts']) == 3
assert all(a['exit_code'] == 1 and a['http_status'] == 502 for a in stop['attempts'])
assert stop['staged_update_observed'] is None and stop['staged_update_discarded'] is None
stderr = pathlib.Path(stop['last_stderr'])
inputs.append(stderr)
assert hashlib.sha256(stderr.read_bytes()).hexdigest() == stop['last_stderr_sha256']
assert 'HTTP 502' in stderr.read_text() and '40061023607/jobs?per_page=100' in stderr.read_text()
assert '<worktree>' in stderr.read_text() and '<python>' in stderr.read_text()

sys.path.insert(0, 'os/ci')
from rehearsal_guard import job_minutes
before = read(root / 'before-probe-budget.json')
jobs = read(root / 'probe-1/jobs.json')['jobs']
assert sum(job_minutes(j) for j in jobs) == 34
after = read(root / 'after-probe-ledger-reconstruction.json')
runs = read(root / 'after-probe-runs.json')
assert {r['run'] for r in runs} - {r['run'] for r in before['runs']} == {40112294759}
assert all(r['status'] == 'completed' for r in runs)
assert sum(r['title'] == 'Two-disk rehearsal (full)' for r in runs) == 4
assert before['consumed_minutes'] == 430 and after['consumed_minutes'] == 464
assert not after['full_authorization'] and after['cap'] == 750 and after['full_cap'] == 5
assert before['consumed_minutes'] + 34 == after['consumed_minutes']

run = read(root / 'probe-1/run.json')
assert run['conclusion'] == 'success' and run['head_sha'] == source
proof = read(root / 'probe-1/two-disk/probe-result.json')
assert proof['stock_idle_source_verified'] and proof['both_orders'] and proof['installed'] is False
for folder in (root / 'probe-1/two-disk', root / 'probe-1/two-disk/protected-second'):
    cached = read(folder / 'cached-stock-cli-probe.json')
    assert cached['idle_source']['daemon_comm'] == 'rpm-ostree'
    assert cached['idle_source']['versions'] == {'rpm-ostree': '2026.3', 'uupd': '1.5.0'}
    assert 'ExecStart=+rpm-ostree start-daemon' in cached['idle_source']['service']
    assert read(folder / 'keyboard-reader-probe-result.json')['installed'] is False
    for name in ('installed-keyboard-result.json', 'first-stock-pause.txt', 'first-stock-pin-result.json',
                 'part-a-result.json', 'full-result.json'):
        assert not (folder / name).exists(), 'Do not invent an installed/full result'
assert read(root / 'probe-1/owner-auth-cleanup.json')['removed']
assert read(root / 'probe-1/private-registry-preflight.json')['owner_token_api_calls'] == 0
verified = read(root / 'evidence-verification.json')
assert verified['matching_offline_stages'] == verified['zero_write_records'] == 6
assert not verified['incomplete'] and not verified['pause_decisions']
assert [q['kind'] for q in verified['qualifications']] == ['probe']

unchanged = ('os/release/pause-stock-updates.sh', 'os/release/pin-stock.sh', 'os/ci/two_disk_vm.py',
             'os/ci/stock_probe.py', 'os/ci/rehearsal_guard.py', 'os/ci/disk_audit.py',
             '.github/workflows/os-image.yml', '.github/workflows/privacy-check.yml', '.gitleaks.toml')
for path in unchanged:
    expected = subprocess.check_output(['git', 'show', source + ':' + path])
    assert pathlib.Path(path).read_bytes().replace(b'\r\n', b'\n') == expected
    inputs.append(pathlib.Path(path))
result = dict(status='stopped-before-full', source=source, measured_minutes=464, full_runs=4,
              full_authorized=False, installed_keyboard_both_orders='not run', staged_update_observed=None,
              staged_update_discarded=None, runtime_unchanged=True,
              inputs=[dict(path=p.as_posix(), sha256=hashlib.sha256(
                  p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()) for p in inputs],
              hash_convention='Git canonical LF text; compare with staged/committed blob bytes')
(root / 'stop-analysis.json').write_text(json.dumps(result, indent=2) + '\n', newline='\n')
print('11j STOP replay passed: 464 minutes / 4 full; source/probe verified; no full authorization or installed claims.')
