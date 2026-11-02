"""Unprivileged real pts; invoke only the owner's actual read-only session guard."""
import pathlib,subprocess,pty,os,json,hashlib
root=pathlib.Path.cwd()
source='''import pathlib,sys,importlib.util,json,os
root=pathlib.Path.cwd()
spec=importlib.util.spec_from_file_location('owner',root/'os/owner-tools/owner.py')
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
class RefuseHost:
 def __init__(self):self.calls=[]
 def __getattr__(self,name):
  def refuse(*args,**kwargs):
   self.calls.append(name);raise AssertionError('No host query or mutation expected')
  return refuse
tool=object.__new__(owner.Tools);tool.host=RefuseHost()
value=dict(stdin_isatty=sys.stdin.isatty(),stdin_is_pts=os.ttyname(0).startswith('/dev/pts/'))
try:
 tool.session()
 raise AssertionError('Unexpected session acceptance')
except owner.Stop as error:
 value.update(status='STOP reproduced by unchanged real Tools.session',reason=str(error),host_calls=tool.host.calls,mutations=0)
 print(json.dumps(value))
'''
master,slave=pty.openpty()
try:
 result=subprocess.run(['python3','-c',source],stdin=slave,capture_output=True,text=True,timeout=15)
 assert result.returncode==0 and not result.stderr,(result.returncode,result.stderr)
 value=json.loads(result.stdout);assert value['stdin_isatty'] and value['stdin_is_pts'] and not value['host_calls']
 assert value['reason']=='Use a physical tty3/tty4 recovery login'
 value.update(kind='PLAN-GAP: retained pinned sudo use_pty gives real owner layout stdin a pts, which the payload rejects',
   default_use_pty_verified=True,root_console='owner_vm.Console.become_root uses sudo -i',
   affected_commands=['layout begin us','layout revert','layout proof','layout finish','layout begin us-intl','layout begin de'],
   no_sudo_executed=True,no_privilege_or_disk_access=True,no_owner_or_harness_source_modified_for_proof=True,
   sources=[dict(sha256=hashlib.sha256((root/p).read_bytes()).hexdigest(),path=p) for p in ('os/owner-tools/owner.py','os/owner-tools/at','os/owner-tools/commands.json','os/ci/owner_vm.py')],
   exact_python_source=source)
 (root/'.work/14/14ze-pts-plan-gap.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({k:value[k] for k in ('status','stdin_isatty','stdin_is_pts','reason','mutations')}))
finally:
 os.close(master);os.close(slave)
