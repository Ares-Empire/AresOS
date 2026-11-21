"""Recover final bookkeeping from completed attempts; never launch or replace a game run."""
import importlib.util
import json
from pathlib import Path
import re
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
WORK=HERE.parents[2]/'.work/pkg49b'
expected=[]
for i,order in enumerate(('AB','BA','BA','AB','AB','BA'),1):
    expected.extend(f'flat-{i}-'+('control' if k=='A' else 'arena') for k in order)
for i,order in enumerate(('AB','BA'),1):
    expected.extend(f'create-{i}-'+('control' if k=='A' else 'arena') for k in order)
expected+=['nether-control','nether-arena']
accepted={}
for slot in expected:
    matches=[]
    for path in (ROOT/'runs').glob('*/attempt.json'):
        item=json.loads(path.read_text())
        if item['slot']==slot and item['accepted']:matches.append(item['attempt'])
    assert len(matches)==1,(slot,matches)
    name=matches[0]
    assert (ROOT/'runs'/name/'summary.json').exists()
    exits=re.findall(r'attempt=\d+ exit=(\d+)$',(WORK/(name+'.txt')).read_text(),re.M)
    assert exits and exits[-1]=='0',(slot,exits)
    accepted[slot]=name
spec=importlib.util.spec_from_file_location('schedule',HERE/'schedule.py')
schedule=importlib.util.module_from_spec(spec);spec.loader.exec_module(schedule)
fixtures=json.loads((ROOT/'fixture-hashes.json').read_text())
for kind,name in [('flat','AresHub-base'),('nether','AresHub-nether-base')]:
    assert schedule.fingerprint(WORK/name)==fixtures[kind],kind
(ROOT/'accepted.json').write_text(json.dumps(accepted,indent=2)+'\n')
path=ROOT/'verification/scheduler-finalization.json'
record=json.loads(path.read_text())
record.update(finalization_command='python3 reviews/49b-arena-rerun/rig/finalize.py',finalized_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
path.write_text(json.dumps(record,indent=2)+'\n')
print('Finalized 18 completed measurement slots; both fixture hashes unchanged; no game launched or replaced.')
