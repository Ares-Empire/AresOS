"""Remove only the two verified completed probe-replay duplicates."""
import hashlib,json,pathlib,shutil
r=pathlib.Path.cwd().resolve();w=r/'.work/14';old=w/'14zzd-replay-1'
assert not list(w.glob('*replay*.lock')), 'STOP: overlapping ISO reader'
proof=json.loads((old/'result.json').read_text());live,=[p for p in json.loads((r/'os/manifest/installer-isos.json').read_text()) if p['kind']=='live']
assert proof['status']=='passed' and proof['sha256']==live['sha256'] and proof['bytes']==live['bytes']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
canonical=w/'14zd-replay-1/work/squashfs.img';master=w/live['filename']
assert canonical.is_file() and master.is_file() and master.stat().st_size==live['bytes']
targets=[(old/'work'/live['filename'],live['sha256']),(old/'work/squashfs.img',sha(canonical))]
rows=[]
for p,digest in targets:
 assert p.resolve().is_relative_to(old.resolve()) and p.resolve().is_relative_to(r)
 assert p.is_file() and not p.is_symlink() and sha(p)==digest
 rows.append(dict(sha256=digest,path=p.relative_to(r).as_posix(),bytes=p.stat().st_size))
out=w/'14zzd/qualification-cache-reclaim.json';assert not out.exists()
value=dict(status='verified before unlink',files=rows,master_iso_preserved=True,canonical_squashfs_preserved=True,completed_result_preserved=True,failed_diagnostics_preserved=True,recursive_delete=False)
out.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
for p,_ in targets:p.unlink()
value.update(status='two verified completed duplicate files unlinked',free_gib=round(shutil.disk_usage(r).free/1024**3,3))
out.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('CACHE_RECLAIM_VERIFIED',len(rows),'files; free GiB',value['free_gib'])
