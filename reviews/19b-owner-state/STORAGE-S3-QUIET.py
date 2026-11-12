"""All point-zero owner comparisons, using synthetic worktree-only policy files."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import json
from owner_state_oracle.gaps import Gaps
from test_owner_state_sweep import FLOWS, EXTRA, exercise

results = {}
with SourceFileLoader('local_policy', str(Path(__file__).with_name('STORAGE-S3-LOCAL-POLICY.py'))).load_module().local_policy():
    for flow in FLOWS + EXTRA:
        gaps = Gaps(recording=True)
        exercise(flow, gaps=gaps)
        results[flow] = len(gaps.entries)
        print(flow, results[flow], flush=True)
        assert not gaps.entries, ('Fault-free owner-state differences', flow)
output = Path('.work/19b-s3-final')
output.mkdir(parents=True, exist_ok=True)
(output / 'quiet-result.json').write_text(json.dumps(results, indent=2) + '\n')
print('PASS:', len(results), 'fault-free flows; no owner-state differences')
