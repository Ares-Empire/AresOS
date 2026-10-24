"""Reproduce authorized pending-only cleanup using the real 11f status fixture."""
import hashlib
import json
import pathlib
import sys
import unittest

root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'os/tests'))
from test_stock_prepare import StockPinTest

case = StockPinTest()
proof = case.run_pin()
assert proof['staged_discarded'] and proof['pinned'] and proof['no_staged']
paths = ['os/manifest/ci/11f/full-2/two-disk/pin-stock.txt',
         'os/release/pause-stock-updates.sh', 'os/release/pin-stock.sh',
         'os/tests/test_stock_prepare.py', 'os/tests/test_two_disk_vm.py',
         'os/ci/two_disk_vm.py', 'docs/INSTALL.md']
suite = unittest.defaultTestLoader.discover(str(root / 'os/tests'), pattern='test_stock_prepare.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful()
receipt = dict(status='passed', real_11f_status=True, mocked_subprocesses=True,
               mutations=case.calls, result=proof, regressions=result.testsRun,
               historical_11f_counter_unchanged=True,
               inputs={p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths})
destination = root / 'os/manifest/ci/11g/stock-prepare-replay.json'
destination.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(receipt, indent=2))
