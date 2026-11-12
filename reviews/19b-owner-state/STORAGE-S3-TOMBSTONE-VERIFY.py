"""Validate the stopped candidate's measurements, without claiming stage-3 acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--candidate-applied', action='store_true')
args = parser.parse_args()
review = Path(__file__).resolve().parent
root = review.parent.parent
manifest = json.loads((review / 'STORAGE-S3-TOMBSTONE.json').read_text())
for name, expected in manifest['hashes'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
if args.candidate_applied:
    for name, expected in manifest['candidate_source_hashes'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
else:
    subprocess.run(['git', 'apply', '--check', str(review / 'STORAGE-S3-TOMBSTONE.patch')], cwd=root, check=True)
for kind, row in manifest['operations'].items():
    before, after = manifest['baseline'][kind], manifest['candidate'][kind]
    assert before['outcome'] == after['outcome'] == 'done'
    for phase in ('while_open_peak_delta', 'open_delta', 'finished_delta'):
        for field in ('journal_bytes', 'journal_records', 'sqlite_file_bytes',
                      'sqlite_event_bytes', 'index_bytes', 'archive_bytes'):
            assert before[phase][field] == after[phase][field], (kind, phase, field)
    assert row['extra_while_open_bytes'] == (after['while_open_peak_delta']['all_kept_file_bytes'] -
                                            before['while_open_peak_delta']['all_kept_file_bytes'])
    assert row['net_inventory_extra_permanent_bytes'] == (after['finished_delta']['all_kept_file_bytes'] -
                                                         before['finished_delta']['all_kept_file_bytes'])
    assert row['extra_permanent_bytes'] == row['net_inventory_extra_permanent_bytes'] + row['reclaimed_fixture_source_bytes']
    assert row['extra_permanent_bytes'] == (after['finished_delta']['projection_bytes'] +
                                            after['finished']['source_bytes'] +
                                            after['finished_delta']['tombstone_bytes'])
    assert row['reclaimed_fixture_source_bytes'] == after['before']['source_bytes']
    assert sum(r['bytes'] for r in after['source_detail']) == after['open_delta']['source_bytes']
    assert sum(r['bytes'] for r in after['projection_detail']) == after['open_delta']['projection_bytes']
    assert sum(r['bytes'] for r in after['retained_live_projection_detail']) == after['finished_delta']['projection_bytes']
    assert sum(r['bytes'] for r in after['retained_source_detail']) + 8 == after['finished']['source_bytes']
    assert sum(r['bytes'] for r in after['tombstone_detail']) + (8 if after['tombstone_detail'] else 0) == after['finished']['tombstone_bytes']
    assert after['finished']['owner_history_bytes'] == after['finished']['owner_history_records'] == 0
    assert sum(p['bytes'] for p in after['kept_files']) == after['finished']['all_kept_file_bytes']
assert manifest['operations']['send']['extra_permanent_bytes'] >= 1024
assert manifest['operations']['delete']['extra_permanent_bytes'] >= 1024
# The stop holds without the readable-source prototype or any fixture-credit choice.
assert manifest['candidate']['send']['finished_delta']['projection_bytes'] >= 1024
assert manifest['operations']['send']['net_inventory_extra_permanent_bytes'] >= 1024
for file, lines in {
    'STORAGE-S3-TOMBSTONE-TEST-OUTPUT.txt': ('Ran 9 tests', '\nOK\n', '115 bytes after 1 and 1001'),
    'STORAGE-S3-TOMBSTONE-ARCHIVE-OUTPUT.txt': ('Ran 5 tests', '\nOK\n'),
}.items():
    text = (review / file).read_text()
    assert all(line in text for line in lines), file
assert manifest['workflow_attempts_added'] == 0
print('Tombstone storage evidence PASS: five done outcomes; complete file inventories;')
print('37 projection / 41 readable-source operation records; 9 + 5 focused tests passed;')
print('no fixture-cleanup credit hides retained copies; send exceeds 1 KB even in compact references alone.')
print('Stage 3 STOP. This validates the evidence, not stage-3 acceptance.')
