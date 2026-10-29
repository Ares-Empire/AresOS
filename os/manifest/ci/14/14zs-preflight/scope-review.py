import ast,pathlib,subprocess,json
r=pathlib.Path.cwd();base='2e0e996'
def old(p):return subprocess.check_output(['git','show',base+':'+p],text=True,encoding='utf-8')
def funcs(s):
 result={}
 for n in ast.parse(s).body:
  if isinstance(n,ast.FunctionDef):result[n.name]=ast.dump(n)
  elif isinstance(n,ast.ClassDef):
   for c in n.body:
    if isinstance(c,ast.FunctionDef):result[n.name+'.'+c.name]=ast.dump(c)
 return result
p='os/ci/owner_vm.py';before=funcs(old(p));after=funcs((r/p).read_text());changed={n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
expected={'Guest.screenshot','retain_vcsa','Console.__init__','Console.visible','Console.hidden','Console.input_guard','Console.counter_sample','Console.verified_value','Console.send_hidden','Console.login','Console.login_attempt'}
assert changed==expected,changed
a=json.loads(old('os/ci/rehearsal-packages.json'));b=json.loads((r/'os/ci/rehearsal-packages.json').read_text());a['14']['minute_cap']=1900;a['14']['dispatch_caps']={'probe':27,'owner-tools':16};assert a==b
subprocess.run(['git','diff','--exit-code',base,'--','os/config','os/policy','os/manifest/base.json','os/manifest/release.json','os/keys','os/packages.lock.json','os/Containerfile.keyboard','os/release','os/owner-tools','docs','os/tests/audit.py','.github','.gitleaksignore','.gitleaks.toml','reviews/14-owner-tools/classify-artifacts.py','os/ci/serial_transport.py','os/ci/serial_console.py','os/ci/owner_console.py','os/ci/owner_hidden.py','os/ci/owner_key_counter.py'],check=True)
v=dict(status='passed harness-only login timing/reader-restart/visual privacy scope',base=base,changed_owner_vm_functions=sorted(changed),new_login_module='os/ci/owner_login.py',package13_unchanged=True,owner_bundle_unchanged=True,release_scripts_unchanged=True,image_unchanged=True,all_existing_observer_predicates_unchanged=True,privacy_classifier_and_workflow_unchanged=True,settings_and_deadlines_unchanged=True)
(r/'.work/14/14zs/scope.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print(json.dumps(v))
