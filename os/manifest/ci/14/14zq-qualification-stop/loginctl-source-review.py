import pathlib,json,subprocess,hashlib
r=pathlib.Path.cwd();w=r/'.work/14/14zq';tag=json.loads(subprocess.check_output(['gh','api','repos/systemd/systemd/git/tags/bcc1b11ee1a215114b067ae0f8a722f8e2fcd34d']))
assert tag['object']['type']=='commit';commit=tag['object']['sha'];rows=[]
for path in ('src/login/loginctl.c','src/shared/bus-print-properties.c'):
    raw=subprocess.check_output(['gh','api','-H','Accept: application/vnd.github.raw+json','repos/systemd/systemd/contents/'+path+'?ref='+commit])
    name='systemd-'+path.replace('/','_');(w/name).write_bytes(raw)
    rows.append(dict(sha256=hashlib.sha256(raw).hexdigest(),path=name,url='https://github.com/systemd/systemd/blob/'+commit+'/'+path,tag='v259.9',commit=commit))
(w/'loginctl-source.json').write_text(json.dumps(dict(status='read-only primary source, no fix or retry',sources=rows),indent=2)+'\n',newline='\n')
print('READ_ONLY_SYSTEMD259_9_SOURCE',commit)
