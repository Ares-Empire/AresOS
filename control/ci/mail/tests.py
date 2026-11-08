"""Disjoint CI selections; together they run every Mail test exactly once."""
from pathlib import Path
import sys
import time
import unittest

selection = sys.argv[1]
if selection not in {'all', 'suite', 'sweep'}:
    raise SystemExit('Choose all, suite or sweep')
root = Path(__file__).resolve().parents[2] / 'mail_tests'
sys.path.insert(0, str(root))
sweep = {'test_review23_sweep', 'test_review24_io'}
names = [p.stem for p in sorted(root.glob('test*.py'))
         if selection == 'all' or (p.stem in sweep) == (selection == 'sweep')]
started = time.monotonic()
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
print(f'Mail selection={selection}: {result.testsRun} tests; elapsed={time.monotonic() - started:.3f}s', flush=True)
raise SystemExit(not result.wasSuccessful())
