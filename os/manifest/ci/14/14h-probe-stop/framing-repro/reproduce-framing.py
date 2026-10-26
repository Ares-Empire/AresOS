import hashlib,json,pathlib,subprocess,sys
sys.path.insert(0,'os/ci')
from switch_vm import framed
from serial_console import decode_export
root=pathlib.Path.cwd();out=root/'.work/14/14h-framing-repro';out.mkdir(exist_ok=True)
results=[]
for name,command in [('heredoc',"python3 - <<'PY'\nimport json\nprint(json.dumps({'status':'passed'}))\nPY"),('single-line',"python3 -c \"import json; print(json.dumps({'status':'passed'}))\"")]:
    script=framed(command).replace('mktemp /run/aresos-json.XXXXXX','mktemp '+'.work/14/14h-framing-repro/result.XXXXXX')
    run=subprocess.run(['bash'],input=script,text=True,capture_output=True)
    (out/(name+'.sh')).write_text(script)
    (out/(name+'-stdout.txt')).write_text(run.stdout)
    (out/(name+'-stderr.txt')).write_text(run.stderr)
    if name=='heredoc':
        assert run.returncode==1 and "NameError: name 'PY' is not defined" in run.stderr
        assert json.loads(run.stdout)=={'status':'passed'}
    else:
        assert run.returncode==0 and json.loads(decode_export(run.stdout))=={'status':'passed'}
    results.append(dict(case=name,exit_code=run.returncode,expected_failure=name=='heredoc'))
proof=dict(status='reproduced current framed heredoc failure; single-line control passes',kind='local pure Bash/Python and workspace files; no network/device/privilege',adapter='only mktemp directory changed from /run to this workspace',cases=results,
    files=[dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.name) for p in sorted(out.iterdir()) if p.is_file() and p.name!='result.json'])
(out/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
