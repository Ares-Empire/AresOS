import json,pathlib,shlex,subprocess,sys,yaml,re
sys.path.insert(0,'os/tests')
from guest_shell import syntax
root=pathlib.Path.cwd()
commands=json.loads((root/'os/manifest/ci/14/host-walk/guest-commands.json').read_text())
commands+=json.loads((root/'.work/14/14zzd/probe-walk/guest-commands.json').read_text())
embedded=0
for name,source in commands:
    syntax(name,source)
    words=shlex.split(source)
    for i,word in enumerate(words[:-2]):
        if word=='python3' and words[i+1]=='-c':
            compile(words[i+2],name,'exec');embedded+=1
    for body in re.findall(r"python3 - <<'PY'\n(.*?)\nPY(?:\n|$)",source,re.S):
        compile(body,name+'-heredoc','exec');embedded+=1
shells=list(root.glob('os/ci/*.sh'))+list(root.glob('os/release/*.sh'))
for p in shells:
    result=subprocess.run(['bash','--noprofile','--norc','-n',str(p)],capture_output=True,text=True)
    assert result.returncode==0 and not result.stderr and not result.stdout,(p.name,result.stderr)
python=set(root.glob('os/ci/*.py'))|set(root.glob('os/release/*.py'))|set(root.glob('os/config/overlay/**/*.py'))|set(root.glob('os/owner-tools/*.py'))
for p in python:compile(p.read_text(encoding="utf-8"),str(p.relative_to(root)),'exec')
sys.path.insert(0,str(root/'os/ci'))
import owner_login
compile(owner_login.guest_source(),'actual-prepared-login-guest-source','exec')
workflow=yaml.load((root/'.github/workflows/os-image.yml').read_text(),Loader=yaml.BaseLoader)
native,=[s for s in workflow['jobs']['rehearsal']['steps'] if s.get('name')=='Qualify tools, regressions, rewritten release identity and private access']
process=subprocess.run(['bash','--noprofile','--norc','-n'],input=native['run'],capture_output=True,text=True)
assert process.returncode==0 and not process.stdout and not process.stderr
result=dict(prepared_login_helper_compiled=True,native_workflow_shells=1,status='passed',guest_scripts=len(commands),serial_wrappers=len(commands),stderr_policy='any parse stderr, including warnings, refuses',embedded_python=embedded,ci_release_shells=len(shells),ci_overlay_owner_python=len(python),execution='syntax/compile only; no guest, service, privilege or hardware operation')
(root/'.work/14/14zzd-syntax.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
