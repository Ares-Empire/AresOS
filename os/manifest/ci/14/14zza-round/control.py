"""14zza: qualification19 only, on the existing pushed probe30 head."""
import hashlib,importlib.util,json,pathlib,subprocess,sys
R=pathlib.Path.cwd();W=R/'.work/14';LOCAL='e3f4c937a56b1c65687bcf8c2a3fa2ef099db426';TARGET='10921f81f481bd2b2c7bfb2da9e13deabdb1267f'
s=importlib.util.spec_from_file_location('previous_control',W/'14zz-control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
c.TARGET=TARGET
original_source=c.source_gate

def source_gate():
 assert c.out('git','rev-parse','HEAD')==LOCAL,'STOP: local review commit changed'
 assert c.out('git','rev-parse','origin/'+c.BRANCH)==TARGET,'STOP: remote-tracking head changed'
 changed=c.out('git','diff','--name-only',TARGET,LOCAL).splitlines()
 allowed={'briefs/14zza-classify-whole-lines.md','reviews/14-owner-tools/REPORT.md','reviews/14-owner-tools/BUDGET.json'}
 assert changed and all(x in allowed or x.startswith('os/manifest/ci/14/14zz-round/') for x in changed),'STOP: pushed implementation differs from local execution tree'
 assert original_source()==TARGET
 seal=json.loads((W/'14zza/local-bindings.json').read_text())
 assert seal['target']==TARGET and seal['local_head']==LOCAL
 for row in seal['files']:
  assert hashlib.sha256((R/row['path']).read_bytes()).hexdigest()==row['sha256'],'STOP: new local tool changed: '+row['path']
 return TARGET
c.source_gate=source_gate

def authorize():
 assert json.loads((W/'14zz-probe-run.json').read_text())['id']==41301148135
 assert json.loads((W/'run-41301148135/14zz-probe-proof.json').read_text())['head']==TARGET
 c.authorize('owner-tools')
 (W/'14zza/authorization.json').write_bytes((W/'14zz-pre-owner-tools-authorization.json').read_bytes())

def dispatch():
 c.dispatch('owner-tools')
 (W/'14zza/run.json').write_bytes((W/'14zz-owner-tools-run.json').read_bytes())

if __name__=='__main__':
 action=sys.argv[1]
 if action=='source':print('PASS existing pushed implementation and sealed local-only adapters',source_gate())
 elif action=='privacy':c.privacy()
 elif action=='authorize':authorize()
 elif action=='dispatch':dispatch()
 elif action=='monitor':c.monitor(sys.argv[2])
 else:raise AssertionError('STOP: 14zza permits no push or probe dispatch')
