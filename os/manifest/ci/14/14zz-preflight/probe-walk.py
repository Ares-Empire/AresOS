import pathlib,json,sys,hashlib
from unittest.mock import patch
import os
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'));sys.path.insert(0,str(r/'os/tests'))
import owner_vm as vm
from guest_shell import syntax
from test_owner_tools import bundle
d=r/'.work/14/14zz/probe-walk';d.mkdir(exist_ok=True);commands=[];keys=[];media_events=[]
class Guest:
 def keys(self,names):keys.append(names)
 def capture_json(self,name,source):
  syntax(name,source);commands.append((name,source))
  if name=='counter-kernel-proof':
   from test_owner_counter_flush import result
   return result()
  if name.endswith('-start'):return dict(status='ready',counts_only=True,path='/run/ares-input-fixture1',pid=1,device='/dev/input/event4')
  if name=='probe-active-vt':return dict(active='tty2')
  if name=='probe-unicode-console':return dict(status='passed',getter_only=True,unicode_cells=8000)
  return dict(status='passed',complete=True,keys_released=True,sequence=1,counts=dict(press=0,release=0,repeat=0,syn_dropped=0))
 def command(self,name,source):syntax(name,source);commands.append((name,source))
class Media:
 fingerprint=bundle.check(r/'os/owner-tools/payload')
 def attach(self,guest,stage):media_events.append('attach')
 def detach(self,guest,stage):media_events.append('detach')
original_read=pathlib.Path.read_text
def receipt(p,*a,**kw):
 if p.as_posix()=='evidence/14-counter-kernel.json':return json.dumps(dict(status='guest-required',sha='a'*40,skipped=False))
 return original_read(p,*a,**kw)
with patch.object(vm.td,'save'),patch.object(pathlib.Path,'read_text',receipt),patch.dict(os.environ,GITHUB_SHA='a'*40):
 guest=Guest();vm.Guest.counter_kernel_proof(guest);vm.probe_media(guest,Media())
assert keys==[['ctrl','alt','f3'],['ctrl','alt','f2']] and media_events==['attach','detach']
(d/'guest-commands.json').write_text(json.dumps(commands,indent=2)+'\n',newline='\n')
value=dict(status='passed stand-in probe path; not VM acceptance',commands=len(commands),vt_selection_restored=True,
 event_counter_checkpoint_exercised=True,unicode_getter_exercised=True,media_hotplug_after_checks=True,
 bundle_fingerprint=Media.fingerprint,sources=[dict(sha256=hashlib.sha256((r/p).read_bytes()).hexdigest(),path=p)
 for p in ('os/ci/owner_vm.py','os/ci/owner_key_counter.py','os/ci/owner_hidden.py')])
(d/'result.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print('PASS entire probe host path, including checkpoint/Unicode getter/restored VT; no commands executed')
