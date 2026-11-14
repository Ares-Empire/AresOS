"""Verify the complete file partition before presenting its combined evidence."""
import json
import os
from pathlib import Path
import shutil
import sys

root,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
proofs=[];modules=[]
for index in range(4):
    files=list(root.rglob(f'python-shard-{index}.json'));assert len(files)==1,(index,files)
    proof=json.loads(files[0].read_text())
    assert proof['index']==index and proof['count']==4 and proof['successful'] is True and proof['tests']>0
    assert proof['head']==os.environ.get('RUNTIME_COMMIT',os.environ['GITHUB_SHA']) and proof['run']==os.environ['GITHUB_RUN_ID']
    modules+=proof['modules'];proofs.append(proof)
    shutil.copyfile(files[0].parent/'python.txt',out/f'python-shard-{index}.txt')
expected=sorted(path.stem for path in Path('control/chrome_tests').glob('test_*.py'))
assert sorted(modules)==expected and len(set(modules))==len(modules)
(out/'python-shards.json').write_text(json.dumps({'shards':proofs,'tests':sum(row['tests'] for row in proofs),'modules':expected},indent=2)+'\n')
print('All Python modules PASS:',len(modules),'modules,',sum(row['tests'] for row in proofs),'tests')
