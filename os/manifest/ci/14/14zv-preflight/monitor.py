import sys,pathlib,json,time,importlib.util
w=pathlib.Path('.work/14');spec=importlib.util.spec_from_file_location('control',w/'14zv-control.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
run=sys.argv[1];assert run.isdigit()
while True:
 c.monitor(run)
 status=json.loads((w/('run-'+run+'-status.json')).read_text())
 if status['status']=='completed':raise SystemExit(0 if status['conclusion']=='success' else 20)
 time.sleep(45)
