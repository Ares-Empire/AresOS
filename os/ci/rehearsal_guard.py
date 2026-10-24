"""Fail closed on the separate 11c allowance and same-commit probe authorization."""
import datetime
import hashlib
import io
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time
import zipfile

REPOSITORY = 'Ares-Empire/AresOS'
BRANCH = 'pkg/11-two-disk-rehearsal'
START = '2026-10-23T16:21:00Z'
MINUTE_CAP = 900
FULL_CAP = 5
PART_B_CAP = 1
RETRY_WAITS = (10, 20, 40, 60)
READ_RETRIES = []
RUN_HISTORY_PATH = f'actions/runs?branch={BRANCH}&per_page=100'
HISTORY_PAGE_LIMIT = 20


def failure_status(stderr):
    # gh api appends (HTTP NNN) to JSON errors, or prints "gh: HTTP NNN"
    # for other HTTP bodies. Unknown/parse/auth errors must not become retries.
    message = stderr.decode('utf-8', errors='replace')
    codes = re.findall(r'^gh: [^\r\n]*\(HTTP ([1-5][0-9]{2})\)|^gh: HTTP ([1-5][0-9]{2})(?:\s|$)', message, re.M)
    if codes:
        return int(next(part for part in codes[-1] if part))
    # Go's http.Client returns a URL error for transport failures. Match only
    # recognizable connection causes; certificate/CLI/unknown failures stop.
    connection = re.search(r'^Get "https://[^"\r\n]+": '
        r'(?:(?:proxyconnect tcp: )?dial (?:tcp|udp)|read tcp|write tcp|EOF$|unexpected EOF$|'
        r'context deadline exceeded|net/http: TLS handshake timeout|'
        r'net/http: request canceled while waiting for connection|http2: client connection lost)', message, re.M)
    return 'connection' if connection else None


def read_only(path):
    command = ['gh', 'api', '--method', 'GET', path]
    for attempt in range(1, len(RETRY_WAITS) + 2):
        try:
            return subprocess.check_output(command, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as error:
            status = failure_status(error.stderr or b'')
            retryable = error.returncode != 4 and (status == 'connection' or
                         isinstance(status, int) and 500 <= status <= 599)
            if not retryable or attempt > len(RETRY_WAITS):
                print('GUARD_READ_FAILED ' + json.dumps(dict(path=path, status=status,
                      attempt=attempt, returncode=error.returncode)), file=sys.stderr, flush=True)
                raise
            record = dict(path=path, status=status, attempt=attempt,
                          next_attempt=attempt + 1, wait_seconds=RETRY_WAITS[attempt - 1])
            READ_RETRIES.append(record)
            print('GUARD_READ_RETRY ' + json.dumps(record), file=sys.stderr, flush=True)
            time.sleep(record['wait_seconds'])


def api(path):
    if path == RUN_HISTORY_PATH:
        return run_history()
    return json.loads(read_only(f'repos/{REPOSITORY}/{path}'))


def run_history():
    """Require one complete, consistent listing; never stitch shifted snapshots."""
    runs, pages, seen = [], [], set()
    total = None
    for page in range(1, HISTORY_PAGE_LIMIT + 1):
        path = f'{RUN_HISTORY_PATH}&page={page}'
        response = json.loads(read_only(f'repos/{REPOSITORY}/{path}'))
        assert isinstance(response, dict), 'STOP: malformed run history response'
        count, batch = response.get('total_count'), response.get('workflow_runs')
        assert type(count) is int and count >= 0 and isinstance(batch, list), 'STOP: missing or malformed history total_count/runs'
        print('GUARD_HISTORY_PAGE ' + json.dumps(dict(page=page, path=path,
              total_count=count, returned=len(batch))), file=sys.stderr, flush=True)
        if total is None:
            total = count
        assert count == total, 'STOP: inconsistent history total_count; pages shifted'
        assert len(batch) <= 100, 'STOP: oversized history page'
        assert batch or len(runs) == total, 'STOP: empty history page before the end'
        assert len(batch) == min(100, total - len(runs)), 'STOP: missing or excess history ids/page length'
        ids = [run.get('id') if isinstance(run, dict) else None for run in batch]
        assert all(type(run_id) is int and run_id > 0 for run_id in ids), 'STOP: missing or malformed history run id'
        assert len(set(ids)) == len(ids) and not seen.intersection(ids), 'STOP: duplicate history run id; pages shifted'
        seen.update(ids)
        runs.extend(batch)
        pages.append(dict(page=page, returned=len(batch), total_count=count,
                          ids_sha256=hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()))
        if len(runs) == total:
            assert len(seen) == total, 'STOP: unique history ids do not match total_count'
            proof = dict(complete=True, pages_read=len(pages), ids_count=len(seen), total_count=total,
                         page_limit=HISTORY_PAGE_LIMIT, snapshot_reads=1, pages=pages,
                         run_ids=[run['id'] for run in runs])
            print('GUARD_HISTORY_COMPLETE ' + json.dumps({k: proof[k] for k in
                  ('pages_read', 'ids_count', 'total_count', 'snapshot_reads')}), file=sys.stderr, flush=True)
            return dict(workflow_runs=runs, history=proof)
    raise AssertionError('STOP: history page limit reached before completeness')


def job_minutes(job):
    if job['conclusion'] == 'skipped':
        return 0
    start = datetime.datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
    end = datetime.datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
    return max(1, math.ceil((end - start).total_seconds() / 60))


def budget(reserve, current=None):
    # Push/PR privacy checks consume the same account minutes as VM dispatches.
    listing = api(RUN_HISTORY_PATH)
    runs = listing['workflow_runs']
    records = []
    full = 0
    part_b = 0
    for run in runs:
        if run['created_at'] < START:
            continue
        if run['display_title'] == 'Two-disk rehearsal (full)':
            full += 1
        if run['display_title'] == 'Two-disk rehearsal (part-b)':
            part_b += 1
        if str(run['id']) == str(current):
            continue
        assert run['status'] == 'completed', 'Another branch workflow is active; cannot reserve its cost'
        jobs = api(f'actions/runs/{run["id"]}/jobs?per_page=100')['jobs']
        records.append(dict(run=run['id'], title=run['display_title'], sha=run['head_sha'],
                            conclusion=run['conclusion'], minutes=sum(job_minutes(job) for job in jobs)))
    consumed = sum(record['minutes'] for record in records)
    assert consumed + reserve <= MINUTE_CAP, f'STOP: {consumed} + {reserve} reserved exceeds {MINUTE_CAP} minutes'
    assert full <= FULL_CAP, 'STOP: full-run allowance exhausted'
    assert part_b <= PART_B_CAP, 'STOP: Part B qualification allowance exhausted'
    return dict(allowance='11c', start=START, cap=MINUTE_CAP, full_cap=FULL_CAP, full_dispatched=full,
                part_b_cap=PART_B_CAP, part_b_dispatched=part_b,
                consumed_minutes=consumed, reserved_minutes=reserve, runs=records,
                history=listing.get('history'))


def require_probe(run, sha):
    assert run['event'] == 'workflow_dispatch'
    assert run['path'] == '.github/workflows/os-image.yml'
    assert run['head_branch'] == BRANCH
    assert run['head_sha'] == sha, 'Full run requires a probe on the exact same harness commit'
    assert run['display_title'] == 'Two-disk rehearsal (probe)'
    assert run['status'] == 'completed' and run['conclusion'] == 'success', 'Probe did not pass'


def main():
    mode = sys.argv[1]
    assert mode != 'full' and not (mode == 'ci' and os.environ.get('REHEARSAL_MODE') == 'full'), 'STOP: 11l permits no further full run'
    reserve = int(sys.argv[2])
    current = os.environ.get('GITHUB_RUN_ID') if mode == 'ci' else None
    result = budget(reserve, current)
    history = result.get('history')
    assert history and history['complete'] and history['ids_count'] == history['total_count'], 'STOP: no complete run-history proof'
    if mode == 'part-b':
        assert result['part_b_dispatched'] < PART_B_CAP, 'STOP: no Part B qualification dispatch remains'
    if mode == 'ci' and os.environ.get('REHEARSAL_MODE') == 'part-b':
        assert result['part_b_dispatched'] == PART_B_CAP, 'STOP: Part B current dispatch is absent or duplicated'
        probe_id = os.environ.get('PROBE_RUN', '')
        assert probe_id.isdigit(), 'Full run requires an explicit passing probe ID'
        require_probe(api('actions/runs/' + probe_id), os.environ['GITHUB_SHA'])
        artifacts = api(f'actions/runs/{probe_id}/artifacts')['artifacts']
        artifact, = [item for item in artifacts if item['name'] == 'two-disk-evidence' and not item['expired']]
        raw = read_only(f'repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip')
        assert artifact['digest'] == 'sha256:' + hashlib.sha256(raw).hexdigest(), 'Probe artifact digest mismatch'
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            proof = json.loads(archive.read('two-disk/probe-result.json'))
        assert proof['status'] == 'passed' and proof['installed'] is False
        assert proof['commit'] == os.environ['GITHUB_SHA']
        assert proof['both_orders'] and proof['review_validated']
        assert proof['detached_windows'] and proof['target_reset']
        assert proof['owner_auth_read_only'] and proof['signature_verified']
        assert proof['firmware_rule'] == '11f-linux-position'
        assert proof['stock_recipe_probe'] and proof['failure_counter_probe']
        assert proof['read_only_keyboard_proof'] and proof['installed_keyboard_reader_probe']
        assert proof['part_b_tools_probe'] and proof['stock_idle_source_verified']
        from rehearsal_auth import REFERENCE, DIGEST
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest = json.loads(archive.read('private-registry-preflight.json'))
            pull = json.loads(archive.read('owner-release-pull.json'))
            cleanup = json.loads(archive.read('owner-auth-cleanup.json'))
        assert manifest['status'] == 'passed' and manifest['reference'] == REFERENCE and manifest['registry_digest'] == DIGEST
        assert manifest['secret'] == 'GHCR_READ_TOKEN' and manifest['owner_token_api_calls'] == 0
        assert pull['status'] == 'passed' and pull['reference'] == REFERENCE and pull['preserved_digest']
        assert cleanup['status'] == 'passed' and cleanup['removed'] and cleanup['outside_workspace']
        result['probe_run'] = probe_id
        result['probe'] = proof
    result['read_retries'] = list(READ_RETRIES)
    directory = pathlib.Path('evidence' if mode == 'ci' else '.work/11c')
    directory.mkdir(parents=True, exist_ok=True)
    (directory / '11c-dispatch-authorization.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
