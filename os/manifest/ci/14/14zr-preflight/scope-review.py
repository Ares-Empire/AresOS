import ast,pathlib,subprocess,json
r=pathlib.Path.cwd();base='8746282'
def old(p):return subprocess.check_output(['git','show',base+':'+p],text=True,encoding='utf-8')
def functions(s):
 result={}
 for n in ast.parse(s).body:
  if isinstance(n,ast.FunctionDef):result[n.name]=ast.dump(n)
  elif isinstance(n,ast.ClassDef):
   for c in n.body:
    if isinstance(c,ast.FunctionDef):result[n.name+'.'+c.name]=ast.dump(c)
 return result
p='os/owner-tools/owner.py';before=functions(old(p));after=functions((r/p).read_text());changed={n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
assert changed=={'login_properties','Tools.session','Tools.logs'},changed
a=json.loads(old('os/ci/rehearsal-packages.json'));b=json.loads((r/'os/ci/rehearsal-packages.json').read_text());a['14']['minute_cap']=1800;a['14']['dispatch_caps']={'probe':26,'owner-tools':15};assert a==b
guide = old('docs/INSTALL.md').replace('025622f56d61f669912ce9d6320e7171e2007194420c79ce54dc6b89a0570486','320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6')
guide = guide.replace('persistent journal in that root shell (PASS means collected; inspect the saved logind and full journal for the actual button/shutdown evidence):', 'persistent logind journal in that root shell (PASS means collected; inspect the saved, bounded previous-boot logind records for the actual button/shutdown evidence):')
assert (r/'docs/INSTALL.md').read_text()==guide
subprocess.run(['git','diff','--exit-code',base,'--','os/config','os/policy','os/manifest/base.json','os/manifest/release.json','os/keys','os/packages.lock.json','os/Containerfile.keyboard','os/release','os/ci/owner_vm.py','os/tests/audit.py','.github','.gitleaksignore','.gitleaks.toml','reviews/14-owner-tools/classify-artifacts.py'],check=True)
v=dict(status='passed allowed property/journal function and package14-only cap scope',base=base,changed_owner_functions=sorted(changed),package13_unchanged=True,release_scripts_unchanged=True,harness_runtime_unchanged=True,privacy_classifier_unchanged=True,guide_current_fingerprint_and_scoped_journal_description_only=True)
(r/'.work/14/14zr/scope.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print(json.dumps(v))
