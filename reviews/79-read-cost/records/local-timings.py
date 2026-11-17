"""Local exact-line hit versus cold full check; setup and copying excluded."""
import json
from pathlib import Path
import statistics
import tempfile
import time
from unittest.mock import patch

from aresos_control.chrome.qualification import Qualification
from aresos_control.storage import Store
from qualification_fixture import history, harness_record

ROOT = Path.cwd()
results = []
for count in (301, 1001):
    shipped = {'format': 1, 'entries': history(count - 1)}
    held = harness_record(shipped, 'c' * 64, '157.0.8103.78')
    with tempfile.TemporaryDirectory(dir=ROOT/'.work/79-read-cost/part2') as directory:
        root = Path(directory)
        store = Store(root/'state', root/'evidence')
        try:
            store.write({'chrome:qualification': held}, 'chrome_test_setup', 'Synthetic timing history')
            qualification = Qualification(store, 'c' * 64, shipped)
            qualification.switches('157.0.8103.78')
            for mode in ('hit', 'full'):
                elapsed = []
                if mode == 'full':
                    qualification._slot = None
                with patch('aresos_control.chrome.qualification.validate_record', wraps=__import__(
                        'aresos_control.chrome.qualification', fromlist=['validate_record']).validate_record) as validate:
                    qualification.switches('157.0.8103.78')
                    assert validate.call_count == (1 if mode == 'full' else 0)
                for _ in range(101):
                    if mode == 'full':
                        qualification._slot = None
                    start = time.perf_counter_ns()
                    qualification.switches('157.0.8103.78')
                    elapsed.append((time.perf_counter_ns() - start) / 1_000_000)
                results.append({'entries': count, 'mode': mode, 'samples': len(elapsed),
                                'median_ms': statistics.median(elapsed),
                                'p95_ms': sorted(elapsed)[95], 'validations_per_call': validate.call_count})
        finally:
            store.close()
print(json.dumps(results, indent=2))
