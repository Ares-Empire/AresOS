"""Fail closed on the 11b CI budget and same-commit probe authorization."""
import datetime
import hashlib
import io
import json
import math
import os
import pathlib
import subprocess
import sys
import zipfile

REPOSITORY = 'carlsenares/AresOS'
BRANCH = 'pkg/11-two-disk-rehearsal'
START = '2026-10-22T23:39:21Z'
MINUTE_CAP = 350
FULL_CAP = 3


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPOSITORY}/{path}']))


def job_minutes(job):
    if job['conclusion'] == 'skipped':
        return 0
    start = datetime.datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
    end = datetime.datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
    return max(1, math.ceil((end - start).total_seconds() / 60))


def budget(reserve, current=None):
    runs = api(f'actions/workflows/os-image.yml/runs?branch={BRANCH}&event=workflow_dispatch&per_page=100')['workflow_runs']
    assert len(runs) < 100 or runs[-1]['created_at'] < START, 'Budget history requires pagination; refuse an incomplete ledger'
    records = []
    full = 0
    for run in runs:
        if run['created_at'] < START:
            continue
        if run['display_title'] == 'Two-disk rehearsal (full)':
            full += 1
        if str(run['id']) == str(current):
            continue
        assert run['status'] == 'completed', 'Another 11b dispatch is active; cannot reserve its cost'
        jobs = api(f'actions/runs/{run["id"]}/jobs?per_page=100')['jobs']
        records.append(dict(run=run['id'], title=run['display_title'], sha=run['head_sha'],
                            conclusion=run['conclusion'], minutes=sum(job_minutes(job) for job in jobs)))
    consumed = sum(record['minutes'] for record in records)
    assert consumed + reserve <= MINUTE_CAP, f'STOP: {consumed} + {reserve} reserved exceeds {MINUTE_CAP} minutes'
    assert full <= FULL_CAP, 'STOP: full-run allowance exhausted'
    return dict(cap=MINUTE_CAP, full_cap=FULL_CAP, full_dispatched=full,
                consumed_minutes=consumed, reserved_minutes=reserve, runs=records)


def require_probe(run, sha):
    assert run['event'] == 'workflow_dispatch'
    assert run['path'] == '.github/workflows/os-image.yml'
    assert run['head_branch'] == BRANCH
    assert run['head_sha'] == sha, 'Full run requires a probe on the exact same harness commit'
    assert run['display_title'] == 'Two-disk rehearsal (probe)'
    assert run['status'] == 'completed' and run['conclusion'] == 'success', 'Probe did not pass'


def main():
    mode = sys.argv[1]
    reserve = int(sys.argv[2])
    current = os.environ.get('GITHUB_RUN_ID') if mode == 'ci' else None
    result = budget(reserve, current)
    if mode == 'full':
        assert result['full_dispatched'] < FULL_CAP, 'STOP: no full dispatches remain'
    if mode == 'ci' and os.environ.get('REHEARSAL_MODE') == 'full':
        probe_id = os.environ.get('PROBE_RUN', '')
        assert probe_id.isdigit(), 'Full run requires an explicit passing probe ID'
        require_probe(api('actions/runs/' + probe_id), os.environ['GITHUB_SHA'])
        artifacts = api(f'actions/runs/{probe_id}/artifacts')['artifacts']
        artifact, = [item for item in artifacts if item['name'] == 'two-disk-evidence' and not item['expired']]
        raw = subprocess.check_output(['gh', 'api', f'repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip'])
        assert artifact['digest'] == 'sha256:' + hashlib.sha256(raw).hexdigest(), 'Probe artifact digest mismatch'
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            proof = json.loads(archive.read('two-disk/probe-result.json'))
        assert proof['status'] == 'passed' and proof['installed'] is False
        assert proof['commit'] == os.environ['GITHUB_SHA']
        assert proof['both_orders'] and proof['review_validated']
        result['probe_run'] = probe_id
        result['probe'] = proof
    directory = pathlib.Path('evidence' if mode == 'ci' else '.work/11b')
    directory.mkdir(parents=True, exist_ok=True)
    (directory / '11b-dispatch-authorization.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
