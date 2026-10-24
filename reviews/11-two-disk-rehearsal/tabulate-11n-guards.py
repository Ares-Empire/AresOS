"""Replay every retained real guard read, including the CI authorization artifacts."""
import hashlib
import json
import pathlib
import re
import zipfile

root = pathlib.Path('os/manifest/ci/11n')
review = pathlib.Path('reviews/11-two-disk-rehearsal')
reads = []
for name, label in [('before-native', 'Before native-only dispatch'), ('before-probe', 'Before probe'),
                    ('before-b', 'Before B'), ('after-probe', 'After failed probe; bookkeeping only'),
                    ('after-b', 'After B; bookkeeping only')]:
    path = root / (name + '-budget.json')
    if path.exists():
        reads.append((label, path, (review / f'logs/11n/{name}-guard.txt').read_text()))
for run in sorted(p for p in root.iterdir() if p.is_dir() and (p / '11c-dispatch-authorization.json').exists()):
    with zipfile.ZipFile(review / f'artifacts/11n-{run.name}-workflow-logs.zip') as archive:
        name, = [n for n in archive.namelist() if '/' in n and '_Reserve the separate 11c minute budget' in n]
        log = archive.read(name).decode('utf-8-sig')
    metadata = json.loads((run / 'run.json').read_text())
    path = run / '11c-dispatch-authorization.json'
    receipt = json.loads(path.read_text())
    assert metadata['id'] in receipt['history']['run_ids']
    assert metadata['id'] not in {r['run'] for r in receipt['runs']}
    reads.append((run.name + ' CI (current job excluded from spent)', path, log))
def sequence(item):
    label = item[0]
    if label == 'Before native-only dispatch': return 0
    if label == 'Before probe': return 1
    if label.startswith('probe-') and ' CI ' in label: return 2
    if label == 'Before B': return 3
    if ' CI ' in label: return 4
    return 5
reads.sort(key=sequence)
rows = []
proofs = []
for label, path, log in reads:
    data = json.loads(path.read_text())
    proof = data['history']
    ids = proof['run_ids']
    assert proof['complete'] and proof['snapshot_reads'] == 1 and proof['page_limit'] == 20
    assert len(ids) == len(set(ids)) == proof['ids_count'] == proof['total_count']
    assert 1 <= proof['pages_read'] == len(proof['pages']) <= 20
    offset = 0
    for number, page in enumerate(proof['pages'], 1):
        batch = ids[offset:offset + 100]
        assert page['page'] == number and page['returned'] == min(100, len(ids) - offset) == len(batch)
        assert page['total_count'] == len(ids)
        assert page['ids_sha256'] == hashlib.sha256(json.dumps(batch, separators=(',', ':')).encode()).hexdigest()
        offset += len(batch)
    assert offset == len(ids)
    events = [json.loads(line.split('GUARD_HISTORY_PAGE ', 1)[1]) for line in log.splitlines() if 'GUARD_HISTORY_PAGE ' in line]
    assert len(events) == proof['pages_read']
    for event, page in zip(events, proof['pages']):
        assert all(event[k] == page[k] for k in ('page', 'returned', 'total_count'))
    completed, = [json.loads(line.split('GUARD_HISTORY_COMPLETE ', 1)[1]) for line in log.splitlines() if 'GUARD_HISTORY_COMPLETE ' in line]
    assert completed == {k: proof[k] for k in ('pages_read', 'ids_count', 'total_count', 'snapshot_reads')}
    retries = [json.loads(line.split('GUARD_READ_RETRY ', 1)[1]) for line in log.splitlines() if 'GUARD_READ_RETRY ' in line]
    assert retries == data['read_retries'] and 'GUARD_READ_FAILED ' not in log
    assert data['start'] == '2026-10-23T16:21:00Z' and data['cap'] == 900
    assert data['full_cap'] == data['full_dispatched'] == 5
    assert data['part_b_cap'] == 1 and data['part_b_dispatched'] in (0, 1)
    assert data['consumed_minutes'] + data['reserved_minutes'] <= 900
    assert len(data['runs']) == len({r['run'] for r in data['runs']})
    assert {r['run'] for r in data['runs']} <= set(ids)
    assert sum(r['minutes'] for r in data['runs']) == data['consumed_minutes']
    proof_record = dict(label=label, path=path.as_posix(), pages=proof['pages_read'],
        returned=[p['returned'] for p in proof['pages']], ids=len(ids), total_count=proof['total_count'],
        spent=data['consumed_minutes'], reserve=data['reserved_minutes'], full=5, b=data['part_b_dispatched'], retries=retries)
    proofs.append(proof_record)
    returned = '+'.join(map(str, proof_record['returned']))
    rows.append(f'| {label} | {proof["pages_read"]} / {returned} | {len(ids)}={proof["total_count"]} | {data["consumed_minutes"]} / {data["reserved_minutes"]} | 5 / {data["part_b_dispatched"]} | {len(retries)} |')
(root / 'guard-replays.json').write_text(json.dumps(proofs, indent=2) + '\n', encoding='utf-8', newline='\n')
(root / 'guard-table.md').write_text('| Real guard read | Pages / returned | Unique IDs = total_count | Spent / reserve | Full / B | Retries |\n|---|---|---:|---:|---|---:|\n' + '\n'.join(rows) + '\n', encoding='utf-8', newline='\n')
print('Complete real guard receipts replayed:', len(proofs), '; retries:', sum(len(p['retries']) for p in proofs))
