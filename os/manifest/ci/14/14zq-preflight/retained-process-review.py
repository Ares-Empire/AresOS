import pathlib,json,hashlib
r=pathlib.Path.cwd();b=r/'.work/14/run-40826092372';found=[]
def visit(value,p,pointer):
    if isinstance(value,dict):
        if 'exe' in value and pathlib.PurePosixPath(str(value['exe']).removesuffix(' (deleted)')).name in ('ostree','bootc','rpm-ostree'):
            found.append(dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(b).as_posix(),pointer=pointer,process={k:value[k] for k in ('pid','exe','cmdline','cgroup','excluded_as_daemon','excluded_as_system_helper') if k in value}))
        for k,v in value.items():visit(v,p,pointer+'/'+str(k))
    elif isinstance(value,list):
        for i,v in enumerate(value):visit(v,p,pointer+'/'+str(i))
    elif isinstance(value,str):
        if value.lstrip().startswith(('{','[')):
            try:parsed=json.loads(value)
            except (ValueError,RecursionError):pass
            else:visit(parsed,p,pointer+'/decoded-json')
        for line in value.splitlines():
            if line.startswith(('ARESOS_STOCK_UPDATERS_PAUSED ','ARESOS_STOCK_PAUSE_STOP ')):
                visit(json.loads(line.split(' ',1)[1]),p,pointer+'/decoded-pause')
for p in sorted((b/'evidence/two-disk').rglob('*.json')):
    visit(json.loads(p.read_text(encoding='utf-8')),p,'')
dest=r/'.work/14/14zq/retained-processes.json';dest.write_text(json.dumps(dict(run=40826092372,records=found),indent=2)+'\n',newline='\n')
unique={json.dumps(v['process'],sort_keys=True) for v in found}
print('PROCESS_RECORDS',len(found),'UNIQUE',len(unique))
for v in sorted(unique):print(v)
