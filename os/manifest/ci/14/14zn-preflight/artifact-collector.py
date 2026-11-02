import datetime,hashlib,io,json,pathlib,stat,sys,zipfile
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'os/ci'));import rehearsal_guard as guard
guard.configure('14');run=sys.argv[1];assert run.isdigit();dest=root/'.work/14'/('run-'+run);assert not dest.exists(),'Preserve existing run evidence'
info=guard.api('actions/runs/'+run);assert info['status']=='completed' and info['run_attempt']==1 and info['head_sha']==json.loads((root/'.work/14/14zn-one-push-scan.json').read_text())['checked_commit']
jobs=guard.api(f'actions/runs/{run}/jobs?per_page=100');assert jobs['total_count']==len(jobs['jobs'])<=100
artifacts=guard.api(f'actions/runs/{run}/artifacts?per_page=100');assert artifacts['total_count']==len(artifacts['artifacts'])<=100
artifact,=[a for a in artifacts['artifacts'] if a['name']=='two-disk-evidence' and not a['expired']]
data=guard.read_only(f'repos/{guard.REPOSITORY}/actions/artifacts/{artifact["id"]}/zip');digest=hashlib.sha256(data).hexdigest();assert artifact['digest']=='sha256:'+digest
with zipfile.ZipFile(io.BytesIO(data)) as archive:
 entries=archive.infolist();assert len(entries)<2000 and sum(i.file_size for i in entries)<200_000_000
 names=set()
 for item in entries:
  name=pathlib.PurePosixPath(item.filename);assert not name.is_absolute() and '..' not in name.parts and '\\' not in item.filename and ':' not in item.filename
  assert item.filename.lower() not in names;names.add(item.filename.lower())
  assert stat.S_IFMT(item.external_attr>>16)!=stat.S_IFLNK
  assert name.name not in ('auth.json','config.json'),'Credential-shaped artifact forbidden'
 dest.mkdir();(dest/'evidence.zip').write_bytes(data)
 for item in entries:
  target=dest/'evidence'/item.filename
  assert target.resolve().is_relative_to(dest.resolve())
  if item.is_dir():target.mkdir(parents=True,exist_ok=True)
  else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(item))
logs=guard.read_only(f'repos/{guard.REPOSITORY}/actions/runs/{run}/logs');(dest/'logs.zip').write_bytes(logs)
with zipfile.ZipFile(io.BytesIO(logs)) as archive:
 native=[n for n in archive.namelist() if 'Qualify tools' in n and n.endswith('.txt')]
 if native:
  assert len(native)==1;(dest/'native.log').write_bytes(archive.read(native[0]))
for name,value in [('run.json',info),('jobs.json',jobs)]:
 (dest/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
receipt=dict(sha256=digest,path='evidence.zip',artifact_id=artifact['id'],bytes=len(data),run=int(run),head=info['head_sha'],status=info['conclusion'],members=len(entries),logs=dict(sha256=hashlib.sha256(logs).hexdigest(),path='logs.zip'),downloaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(receipt))
