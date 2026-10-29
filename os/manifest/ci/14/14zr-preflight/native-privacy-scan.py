import pathlib,subprocess,json,sys
r=pathlib.Path.cwd();run,phase=sys.argv[1:];assert run.isdigit() and phase in ('probe','qualification');b=r/'.work/14'/('run-'+run);p=r/'.work/14/gitleaks'/('14zr-'+phase+'-native.json')
v=subprocess.run([str(r/'.work/14/gitleaks/gitleaks.exe'),'stdin','--redact=100','--no-banner','--log-level','warn','--report-format','json','--report-path',str(p)],input=(b/'native.log').read_bytes(),capture_output=True)
assert v.returncode==0 and json.loads(p.read_text())==[],'STOP native log privacy finding'
print('PASS native log privacy: 0 findings')
