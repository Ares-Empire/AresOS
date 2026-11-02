import pathlib,json,hashlib
r=pathlib.Path.cwd();w=r/'.work/14';folder=w/'14zq-qualification-replay-1/work';live=next(x for x in json.loads((r/'os/manifest/installer-isos.json').read_text()) if x['kind']=='live')
assert json.loads((w/'14zq-qualification-replay-attempts.json').read_text())['status']=='passed'
assert not (w/'14zq-qualification-replay.lock').exists()
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while data:=f.read(8*1024*1024):h.update(data)
 return h.hexdigest()
iso=folder/live['filename'];sq=folder/'squashfs.img';canonical=w/'14zd-replay-1/work/squashfs.img'
for p in (iso,sq):assert p.resolve().is_relative_to(folder.resolve()) and folder.resolve().is_relative_to(w.resolve()) and p.is_file() and not p.is_symlink()
assert (w/live['filename']).is_file()
assert iso.stat().st_size==live['bytes'] and digest(iso)==live['sha256']
s=digest(sq);assert s==digest(canonical)
rows=[dict(sha256=live['sha256'],path=iso.relative_to(r).as_posix(),bytes=iso.stat().st_size),dict(sha256=s,path=sq.relative_to(r).as_posix(),bytes=sq.stat().st_size)]
for p in (iso,sq):p.unlink()
(w/'14zr/cache-reclaim.json').write_text(json.dumps(dict(status='verified completed14zq qualification duplicate files only; canonical master ISO/squashfs and all diagnostics retained',files=rows),indent=2)+'\n',newline='\n')
print('PASS ended duplicate ISO/squashfs reclaimed; canonical preserved')
