import ast,pathlib,subprocess,json,hashlib
r=pathlib.Path.cwd();base='4ae5f14'
def old(path):return subprocess.check_output(['git','show',base+':'+path],text=True,encoding='utf-8')
def functions(source):
    tree=ast.parse(source);result={}
    for n in tree.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):result[n.name]=ast.dump(n)
        elif isinstance(n,ast.ClassDef):
            for c in n.body:
                if isinstance(c,ast.FunctionDef):result[n.name+'.'+c.name]=ast.dump(c)
    return result
p='os/owner-tools/owner.py';before=functions(old(p));after=functions((r/p).read_text());changed={n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
assert changed=={'deployment_client','idle','preflight_prepare','Tools.processes'},changed
pin=(r/'os/release/pin-stock.sh').read_text();pause=(r/'os/release/pause-stock-updates.sh').read_text()
assert pin.split('\nPAUSE_STOCK\n',1)[0]==pause.split('\nPAUSE_STOCK\n',1)[0]
assert pin.split('\nPAUSE_STOCK\n',1)[1]==old('os/release/pin-stock.sh').split('\nPAUSE_STOCK\n',1)[1]
source=lambda s:s.split("<<'PAUSE_STOCK'\n",1)[1].split('\nPAUSE_STOCK',1)[0]
a=functions(source(old('os/release/pause-stock-updates.sh')));b=functions(source(pause))
changed_pause={n for n in a.keys()|b.keys() if a.get(n)!=b.get(n)}
assert changed_pause=={'deployment_client','deployment_processes','pause_stock'},changed_pause
assert ast.dump(ast.parse(source(old('os/release/pause-stock-updates.sh'))).body[4])==ast.dump(ast.parse(source(pause)).body[4])
oldconfig=json.loads(old('os/ci/rehearsal-packages.json'));newconfig=json.loads((r/'os/ci/rehearsal-packages.json').read_text())
expected=json.loads(json.dumps(oldconfig));expected['14']['minute_cap']=1700;expected['14']['dispatch_caps']={'probe':25,'owner-tools':14}
assert expected==newconfig
assert (r/'docs/INSTALL.md').read_text()==old('docs/INSTALL.md').replace('683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974','025622f56d61f669912ce9d6320e7171e2007194420c79ce54dc6b89a0570486')
subprocess.run(['git','diff','--exit-code',base,'--','os/config','os/policy','os/manifest/base.json','os/manifest/release.json','os/keys','os/packages.lock.json','os/Containerfile.keyboard','os/tests/audit.py','.github','.gitleaksignore','.gitleaks.toml'],check=True)
v=dict(status='passed allowed function/config/documentation scope; frozen image and safety workflows unchanged',base=base,changed_owner_functions=sorted(changed),changed_pause_functions=sorted(changed_pause),pin_tail_unchanged=True,package13_unchanged=True,other_release_files_unchanged=True,guide_only_current_fingerprint_changed=True)
(r/'.work/14/14zq/scope.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n');print(json.dumps(v))
