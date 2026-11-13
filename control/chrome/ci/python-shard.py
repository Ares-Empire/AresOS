"""A disjoint file partition of the complete plain-Python Chrome discovery suite."""
import json
import os
from pathlib import Path
import sys
import unittest

root=Path(__file__).resolve().parents[2]
index=int(os.environ['PYTHON_SHARD']);count=4
assert 0<=index<count
files=sorted((root/'chrome_tests').glob('test_*.py'))
modules=[p.stem for position,p in enumerate(files) if position%count==index]
sys.path[:0]=[str(root),str(root/'chrome_tests')]
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
out=Path(os.environ.get('TEST_OUT','/out'));out.mkdir(parents=True,exist_ok=True)
(out/f'python-shard-{index}.json').write_text(json.dumps({'index':index,'count':count,'head':os.environ.get('RUNTIME_COMMIT',os.environ.get('GITHUB_SHA')),'run':os.environ.get('GITHUB_RUN_ID'),'modules':modules,'tests':result.testsRun,'successful':result.wasSuccessful()}))
raise SystemExit(0 if result.wasSuccessful() else 1)
