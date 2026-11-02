import pathlib,json,subprocess,hashlib,sqlite3,struct,re
r=pathlib.Path.cwd();w=r/'.work/14/14zq';sq=r/'.work/14/14zd-replay-1/work/squashfs.img'
assert sq.is_file() and not sq.is_symlink()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while data:=f.read(8*1024*1024):h.update(data)
    return h.hexdigest()
def cat(path):
    return subprocess.check_output(['wsl','--exec','unsquashfs','-cat','/mnt/c/Users/pab/AresOS-14-owner-tools/.work/14/14zd-replay-1/work/squashfs.img',path])
units=[]
for name in ('ostree-finalize-staged-hold.service','ostree-finalize-staged.service','bootc-finalize-staged.service'):
    path='usr/lib/systemd/system/'+name;data=cat(path);(w/name).write_bytes(data)
    lines=data.decode().splitlines()
    units.append(dict(sha256=hashlib.sha256(data).hexdigest(),path=path,unit=name,
        exec_start=[x.split('=',1)[1] for x in lines if x.startswith('ExecStart=')],
        exec_stop=[x.split('=',1)[1] for x in lines if x.startswith('ExecStop=')],
        dependencies=[x for x in lines if x.startswith(('Wants=','Requires=','Before=','After=','Conflicts=','Condition','Type=','RemainAfterExit='))],
        cgroup='/system.slice/'+name,cgroup_basis='default non-template system service; no Slice override in unit'))
listing=(r/'.work/14/squashfs-files.txt').read_text(encoding='utf-8')
paths=[]
dropins=[]
for line in listing.splitlines():
    if ' squashfs-root/' not in line:continue
    path=line.split(' squashfs-root/',1)[1].split(' -> ',1)[0]
    if not path.startswith(('etc/systemd/system/','usr/lib/systemd/system/')):continue
    if 'finalize-staged' in path:paths.append(line)
    directories=('service.d/','ostree-.service.d/','ostree-finalize-.service.d/','ostree-finalize-staged-.service.d/','ostree-finalize-staged.service.d/','ostree-finalize-staged-hold.service.d/','bootc-.service.d/','bootc-finalize-.service.d/','bootc-finalize-staged.service.d/')
    short=path.split('systemd/system/',1)[1]
    if line.startswith('-') and short.endswith('.conf') and short.startswith(directories):
        data=cat(path);target=w/('dropin-'+str(len(dropins))+'.conf');target.write_bytes(data)
        assert not any(x.startswith(('Slice=','ExecStart=','ExecStop=','ControlGroup=')) for x in data.decode().splitlines()),'STOP: drop-in changes verified helper: '+path
        dropins.append(dict(sha256=hashlib.sha256(data).hexdigest(),path=path,local=target.name))
db=r/'.work/14/14v/rpmdb.sqlite';expected=json.loads((r/'os/manifest/ci/14/parser-sources/packages.json').read_text())
assert sha(db)==expected['rpmdb']['sha256']
connection=sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True);packages=[]
for name in ('ostree','ostree-libs','bootc','systemd'):
    for blob, in connection.execute('SELECT blob FROM Packages JOIN Name USING(hnum) WHERE key=?',(name,)):
        count,size=struct.unpack('>II',blob[:8]);data=blob[8+16*count:];assert len(data)==size;tags={}
        for offset in range(count):
            tag,kind,start,number=struct.unpack('>IIII',blob[8+16*offset:24+16*offset])
            if tag in (1000,1001,1002,1022,1044):assert kind==6;tags[tag]=data[start:].split(b'\0',1)[0].decode()
        packages.append(dict(name=tags[1000],version=tags[1001],release=tags[1002],arch=tags[1022],source_rpm=tags[1044]))
connection.close()
value=dict(status='read-only pinned squashfs unit verification',squashfs=dict(sha256=sha(sq),path=sq.relative_to(r).as_posix()),rpmdb=dict(sha256=sha(db),path=db.relative_to(r).as_posix()),units=units,packages=packages,trigger_and_dependency_paths=paths,dropins=dropins,path_units_present=False,trigger_note='No finalize-staged .path unit in pinned listing; inspect upstream programmatic service start',retained_q12_process_snapshot='No post-staging client list retained; only rpm-ostreed PID12599 from earlier prepare',systemd_reference='https://www.freedesktop.org/software/systemd/man/260/systemd.slice.html')
(w/'image-verification.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print(json.dumps(dict(packages=packages,units=units,dropins=dropins),indent=2))
