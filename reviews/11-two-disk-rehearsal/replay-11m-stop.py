"""Replay the failed native probe gate; never treat bookkeeping as VM permission."""
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

ROOT = pathlib.Path('os/manifest/ci/11m')
REVIEW = pathlib.Path('reviews/11-two-disk-rehearsal')
SOURCE = '43e76566ac99ebe07727f6f3d34d0ad34bcdb929'
PROBE = 40134595231
credential = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{25,}|\$(?:6|y)\$[./A-Za-z0-9$=]{15,})')


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def archive(path, digest):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, path
    result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        for name in source.namelist():
            assert not name.endswith('/auth.json') and name != 'auth.json'
            assert 'aresos-11d-ghcr/' not in name
            content = source.read(name)
            assert not credential.search(content), name
            for candidate in re.findall(rb'[A-Za-z0-9+/]{30,}={0,2}', content):
                try:
                    decoded = base64.b64decode(candidate, validate=True)
                except ValueError:
                    continue
                assert not credential.search(decoded), name
            result[name] = content
    return result


def history(label, receipt, log):
    proof = receipt['history']
    ids = proof['run_ids']
    assert proof['complete'] and proof['snapshot_reads'] == 1
    assert len(ids) == len(set(ids)) == proof['ids_count'] == proof['total_count']
    assert proof['page_limit'] == 20 and 1 <= proof['pages_read'] <= 20
    assert len(proof['pages']) == proof['pages_read']
    offset = 0
    for number, page in enumerate(proof['pages'], 1):
        batch = ids[offset:offset + 100]
        assert page['page'] == number and page['total_count'] == len(ids)
        assert page['returned'] == min(100, len(ids) - offset) == len(batch)
        assert page['ids_sha256'] == hashlib.sha256(json.dumps(batch, separators=(',', ':')).encode()).hexdigest()
        offset += len(batch)
    assert offset == len(ids)
    events = [json.loads(line.split('GUARD_HISTORY_PAGE ', 1)[1]) for line in log.splitlines() if 'GUARD_HISTORY_PAGE ' in line]
    assert len(events) == proof['pages_read']
    for event, page in zip(events, proof['pages']):
        assert all(event[key] == page[key] for key in ('page', 'returned', 'total_count'))
        assert event['path'] == f'actions/runs?branch=pkg/11-two-disk-rehearsal&per_page=100&page={page["page"]}'
    completed, = [json.loads(line.split('GUARD_HISTORY_COMPLETE ', 1)[1]) for line in log.splitlines() if 'GUARD_HISTORY_COMPLETE ' in line]
    assert completed == {key: proof[key] for key in ('pages_read', 'ids_count', 'total_count', 'snapshot_reads')}
    assert receipt['read_retries'] == [] and 'GUARD_READ_RETRY ' not in log and 'GUARD_READ_FAILED ' not in log
    assert receipt['start'] == '2026-10-23T16:21:00Z' and receipt['cap'] == 900
    assert (receipt['full_cap'], receipt['full_dispatched'], receipt['part_b_cap'], receipt['part_b_dispatched']) == (5, 5, 1, 0)
    records = receipt['runs']
    assert len({r['run'] for r in records}) == len(records)
    assert {r['run'] for r in records} <= set(ids)
    assert sum(r['minutes'] for r in records) == receipt['consumed_minutes']
    return dict(label=label, pages=proof['pages_read'], page_sizes=[p['returned'] for p in proof['pages']],
                unique_ids=len(ids), total_count=proof['total_count'], minutes=receipt['consumed_minutes'],
                reserve=receipt['reserved_minutes'], retries=0)


run, jobs, artifacts = [read('probe-1/' + name + '.json') for name in ('run', 'jobs', 'artifacts')]
assert run['id'] == PROBE and run['head_sha'] == SOURCE
assert run['status'] == 'completed' and run['conclusion'] == 'failure' and run['run_attempt'] == 1
assert run['display_title'] == 'Two-disk rehearsal (probe)' and run['event'] == 'workflow_dispatch'
assert run['head_branch'] == 'pkg/11-two-disk-rehearsal'
job, = [job for job in jobs['jobs'] if job['conclusion'] != 'skipped']
assert job['conclusion'] == 'failure' and job_minutes(job) == 5
steps = {step['name']: step['conclusion'] for step in job['steps']}
assert steps['Reserve the separate 11c minute budget (including privacy checks)'] == 'success'
assert steps['Qualify tools, regressions, rewritten release identity and private access'] == 'failure'
for name in ('Create runner-temporary pinned-image credentials',
             'Verify exact private manifest with owner read-only credentials',
             'Qualify the exact pinned layer pull without installing',
             'Inspect the exact pinned live ISO before assuming an installer path',
             'Prepare disposable file disks and qualify the real live environment'):
    assert steps[name] == 'skipped', name
assert steps['Remove owner registry credentials'] == 'success'
assert read('probe-1/owner-auth-cleanup.json') == dict(status='passed', secret='GHCR_READ_TOKEN', removed=True, outside_workspace=True)

artifact, = artifacts['artifacts']
assert artifacts['total_count'] == 1 and artifact['name'] == 'two-disk-evidence'
assert artifact['workflow_run']['id'] == PROBE and artifact['workflow_run']['head_sha'] == SOURCE
members = archive(REVIEW / 'artifacts/11m-probe-1-two-disk-evidence.zip', artifact['digest'].removeprefix('sha256:'))
assert not any(name.startswith('two-disk/') or name.endswith('.png') for name in members)
assert not any('private-registry-preflight' in name or 'owner-release-pull' in name for name in members)
for name, raw in members.items():
    retained = (ROOT / 'probe-1' / name).read_bytes().replace(b'\r\n', b'\n')
    if name.endswith('.txt'):
        raw = ('\n'.join(line.rstrip() for line in raw.decode().splitlines()).rstrip() + '\n').encode()
    assert retained == raw, name
logs = archive(REVIEW / 'artifacts/11m-probe-1-workflow-logs.zip', read('probe-1/workflow-logs.json')['sha256'])
native, = [raw.decode('utf-8', errors='replace') for name, raw in logs.items() if '/5_Qualify tools' in name]
failed, = re.findall(r'Z FAIL: ([^\r\n]+)', native)
assert failed.startswith('test_install_transactions_stop_on_failure_and_never_include_the_reboot ')
assert 'AssertionError: 1 != 42 : id:' in native and 'no such user' in native
assert 'Ran 200 tests in 3.757s' in native and 'FAILED (failures=1)' in native
assert len(re.findall(r'Z test_.* \.\.\. ok\r?$', native, re.M)) == 199
assert len(re.findall(r'Z test_.* \.\.\. FAIL\r?$', native, re.M)) == 1
assert len(re.findall(r'Z test_.*\(test_rehearsal_history\..* \.\.\. ok\r?$', native, re.M)) == 9
assert len(re.findall(r'Z test_.*\(test_rehearsal_budget\..* \.\.\. ok\r?$', native, re.M)) == 4
assert len(re.findall(r'Z test_.*\(test_rehearsal_retry\..* \.\.\. ok\r?$', native, re.M)) == 7
native_excerpt = native[native.index(next(line for line in native.splitlines() if re.search(r'Z test_', line))):]
(REVIEW / 'logs/11m/native-tests-stop.txt').write_text('\n'.join(line.rstrip() for line in native_excerpt.splitlines()) + '\n', encoding='utf-8', newline='\n')
ci_log, = [raw.decode('utf-8-sig') for name, raw in logs.items() if '/3_Reserve' in name]
ci_events = '\n'.join(line for line in ci_log.splitlines() if 'GUARD_' in line) + '\n'
(REVIEW / 'logs/11m/probe-ci-guard.txt').write_text(ci_events, encoding='utf-8', newline='\n')
before, ci, after = [read(name) for name in ('before-probe-budget.json', 'probe-1/11c-dispatch-authorization.json', 'after-probe-budget.json')]
checks = [history('before probe', before, (REVIEW / 'logs/11m/before-probe-guard.txt').read_text()),
          history('probe CI (current run excluded from spent)', ci, ci_log),
          history('after failed probe; bookkeeping only', after, (REVIEW / 'logs/11m/after-probe-guard.txt').read_text())]
assert before['consumed_minutes'] == ci['consumed_minutes'] == 628
assert before['reserved_minutes'] == 186 and ci['reserved_minutes'] == 42
assert after['consumed_minutes'] == 633 and after['reserved_minutes'] == 14
assert set(ci['history']['run_ids']) == set(after['history']['run_ids']) == set(before['history']['run_ids']) | {PROBE}
assert ci['runs'] == before['runs']
assert {r['run'] for r in after['runs']} == {r['run'] for r in before['runs']} | {PROBE}
record, = [r for r in after['runs'] if r['run'] == PROBE]
assert record['sha'] == SOURCE and record['conclusion'] == 'failure' and record['minutes'] == 5
assert not any(r['title'] == 'Two-disk rehearsal (part-b)' for r in after['runs'])

privacy = read('source-privacy-proof.json')
assert len(privacy) == 2
for proof in privacy:
    assert proof['head'] == SOURCE and proof['status'] == 'passed' and not proof['personal_terms_skip_warning']
    assert len(proof['checks']) == 3 and set(proof['checks'].values()) == {'success'}
    contents = archive(REVIEW / f'artifacts/11m-source-privacy-{proof["run"]}-logs.zip', proof['logs_zip_sha256'])
    text = contents['0_scan.txt'].decode('utf-8')
    groups = re.findall(r'##\[group\]Run ([^\n]+)', text)
    assert any(g.startswith('docker run --rm') and 'gitleaks:v8.21.2' in g for g in groups)
    assert any(g.startswith('bad=$(git log --all') for g in groups)
    assert any(g.startswith('if [ -z "$PRIVATE_TERMS" ]') for g in groups)
    assert '##[error]' not in text and '##[warning]PRIVATE_TERMS secret is not set' not in text
assert sum(job_minutes(job) for proof in privacy for job in proof['jobs']) == 2
owner_records = [r for r in before['runs'] if r['run'] in (40133641975, 40133636215)]
assert len(owner_records) == 2 and sum(r['minutes'] for r in owner_records) == 4
assert 622 + 4 + 2 == before['consumed_minutes']
for name in ('os/ci/rehearsal_guard.py', 'os/ci/two_disk_vm.py', 'os/ci/grub_bls.py', 'os/ci/disk_audit.py',
             'os/ci/stock_probe.py', 'os/ci/rehearsal_auth.py', '.github/workflows/os-image.yml',
             'os/tests/test_shell_assertions.py', 'os/tests/test_rehearsal_budget.py',
             'os/release/switch.sh', 'os/release/pin-stock.sh', 'os/release/pause-stock-updates.sh',
             '.github/workflows/privacy-check.yml', '.gitleaks.toml', '.gitleaksignore',
             'os/manifest/base.json', 'os/manifest/release.json'):
    assert pathlib.Path(name).read_bytes().replace(b'\r\n', b'\n') == subprocess.check_output(['git', 'show', SOURCE + ':' + name]), name
result = dict(status='STOP', source=SOURCE, probe=PROBE, probe_conclusion='failure',
              native_tests=200, native_passed=199, native_failures=1, native_seconds=3.757,
              failed_test=failed, blocker='Owner switch block prerequisite is not mocked in transaction-failure fixture; exits before injected bootc failure.',
              no_vm=True, no_owner_token_use=True, part_b_dispatched=False, no_second_probe=True,
              acceptance_complete=False, keep_pr_draft=True, protected_captures=0,
              bootnext_write_consumption_captures=0, menu_frames=0, guard_reads=checks,
              minutes_before_closing=633, closing_reserve=14, full_dispatched=5, part_b_count=0)
(ROOT / 'stop.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('11m STOP replay passed: 3 complete two-page guard receipts; 200 native tests / 1 failure; no VM, token use or Part B; 633/900 minutes + closing, 5 full / 0 B; source/privacy unchanged.')
