"""Check the running image against the checkout, including when an image is reused."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, '/harness')
from loaded_image import loaded_sha256

result = json.loads(Path('/harness/labwc.lock.json').read_text())['result']
assert subprocess.check_output(['rpm', '-q', 'labwc'], text=True).strip() == result['nevra']
for path, expected in sorted(result['loaded_sha256'].items()):
    actual = loaded_sha256(path)
    assert actual == expected, f'{path} does not match the checkout lock'
    print(f'HARNESS_LABWC {path} loaded_sha256 {actual} matches the lock')
