"""Validate the archived measurement, not stage-3 acceptance."""
import hashlib
import json
from pathlib import Path

review = Path(__file__).resolve().parent
root = review.parent.parent
data = json.loads((review / 'STORAGE-S3-REDESIGN.json').read_text())
for name, expected in data['hashes'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
for kind, summary in data['operations'].items():
    baseline, candidate = data['baseline'][kind], data['candidate'][kind]
    for phase in ('open_delta', 'while_open_peak_delta', 'finished_delta'):
        for key in ('journal_bytes', 'journal_records', 'sqlite_file_bytes',
                    'sqlite_event_bytes', 'index_bytes', 'archive_bytes'):
            assert baseline[phase][key] == candidate[phase][key], (kind, phase, key)
    assert summary['extra_while_open_bytes'] == (candidate['while_open_peak_delta']['all_kept_file_bytes'] -
                                                baseline['while_open_peak_delta']['all_kept_file_bytes'])
    assert summary['extra_permanent_bytes'] == (candidate['finished_delta']['all_kept_file_bytes'] -
                                               baseline['finished_delta']['all_kept_file_bytes'])
    assert summary['extra_permanent_bytes'] == summary['extra_retired_projection_history_bytes']
    assert summary['extra_live_projection_after_archive_bytes'] == 0
    assert sum(row['bytes'] for row in candidate['projection_detail']) == candidate['open_delta']['projection_bytes']
    assert sum(row['bytes'] for row in candidate['retained_projection_detail']) + 8 == summary['extra_permanent_bytes']
    assert len(candidate['projection_detail']) == summary['projection_records_during_operation']
    assert len(candidate['retained_projection_detail']) == summary['projection_records_after_archive']
    assert candidate['outcome'] == 'done'
assert data['operations']['send']['extra_permanent_bytes'] >= 1024
assert data['operations']['delete']['extra_permanent_bytes'] >= 1024
output = (review / 'STORAGE-S3-REDESIGN-TEST-OUTPUT.txt').read_text()
for line in ('Ran 6 tests', 'FAILED (failures=8)', 'AGREEMENT sampled scenario count 420',
             'AGREEMENT actual SQLite read failures 32', 'AGREEMENT successful compact comparisons 549',
             '261 bytes after one and after 1001 synthetic terminal send records'):
    assert line in output, line
assert data['workflow_attempts_added'] == 0
print('Storage redesign evidence PASS: hashes; five done outcomes; 37 operation / 46 retained records;')
print('all kept copies counted; send and permanent delete exceed 1,024 bytes;')
print('candidate test failures preserved (8), not reported as green. Stage 3 STOP.')
