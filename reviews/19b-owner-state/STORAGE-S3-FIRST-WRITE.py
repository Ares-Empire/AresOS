from importlib.machinery import SourceFileLoader
from test_owner_state_sweep import OwnerScenario
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from storage_faults import OSWrites
from pathlib import Path
import hashlib, json, shutil, tempfile

Path('.work/19b-s3-final').mkdir(parents=True, exist_ok=True)

def inventory(root):
 return {str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
         for area in ('state','evidence') for p in sorted((root/area).rglob('*')) if p.is_file()}
with SourceFileLoader('local_policy','reviews/19b-owner-state/STORAGE-S3-LOCAL-POLICY.py').load_module().local_policy():
 s=OwnerScenario('maintenance',1,'persistent',phase='crash');d=Driver(s)
 try:
  before=inventory(s.fixture.root)
  fault=OSWrites(1,mode='persistent')
  with d.observe(fault),fault.wrap(s.fixture.engine.store):reply=s.call()
  after=inventory(s.fixture.root)
  result={'same_bytes_before_and_after':before==after, 'changed_paths':[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)],
          'before':before,'after':after,'faults':fault.failures, 'reply':reply,
          'deferred_notices':list(s.fixture.engine.store.deferred_notices)}
  # Restore exactly the captured crash bytes; orderly close cannot supply new evidence.
  root=s.fixture.root
  from aresos_control.engine import Engine
  with tempfile.TemporaryDirectory(dir=root,prefix='captured-crash-') as saved:
   saved=Path(saved)
   for area in ('state','evidence'):shutil.copytree(root/area,saved/area)
   s.fixture.engine.close()
   for area in ('state','evidence'):
    shutil.rmtree(root/area);shutil.copytree(saved/area,root/area)
  s.bind(Engine(root/'state',root/'evidence'))
  result['after_restart_pending']=s.fixture.engine.pending(resolve_checks=False)
  g=Gaps(recording=True);d.reply(reply,delivered=False);d.compare(g.checker('maintenance/persistent/1/0/crash-restart'))
  result['gap_count']=len(g.entries)
  result['background_gap_count']=sum('background-storage' in json.dumps(e) for e in g.entries.values())
  result['maintenance_started']=d.oracle.script[d.call_index].get('maintenance_started', False)
  Path('.work/19b-s3-final/first-write-proof.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({k:result[k] for k in ('same_bytes_before_and_after','changed_paths','faults','deferred_notices','after_restart_pending','gap_count','background_gap_count')},indent=2))
  assert not result['maintenance_started'], 'Maintenance ran without its committed warning gate'
  assert 'journal.write' not in fault.points, 'The first maintenance journal write started on an unadmitted disk'
  assert not g.entries, ('First-write recovery lost owner facts', g.entries)
  print('PASS: first-write failure prevents maintenance; restart loses no owner facts')
 finally:s.close()
