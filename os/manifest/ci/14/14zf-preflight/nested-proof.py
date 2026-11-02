import pathlib,json,sys,hashlib
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/tests'));from test_owner_session import Model,owner
m=Model('tty4');m.rows[40]['ppid']=21;del m.rows[22]
with m.install() as tool:v=tool.session()
assert v['tty']=='tty4' and not m.mutations
n=Model();n.name,n.pts='/dev/pts/3',34819
n.rows[40].update(ppid=31,session=31,tty=34819)
n.rows[31]=dict(ppid=30,session=31,tty=34819,comm='sudo',exe='/usr/bin/sudo')
n.rows[30]=dict(ppid=22,session=21,tty=34818,comm='sudo',exe='/usr/bin/sudo')
with n.install() as tool:
 try:tool.session();raise AssertionError('Unexpected nested admission')
 except owner.Stop as error:reason=str(error)
assert reason==owner.PHYSICAL_LOGIN and not n.mutations
sources=[]
for p in ['os/owner-tools/owner.py','os/owner-tools/commands.json','os/ci/owner_vm.py','docs/INSTALL.md']:
 sources.append(dict(sha256=hashlib.sha256((r/p).read_bytes()).hexdigest(),path=p))
v=dict(status='PLAN-GAP: literal single-pts rule refuses the existing owner/CI nested-sudo route',kind='modelled /proc, not captured guest PIDs',commands=['sudo -i','sudo /var/lib/ares/at layout begin us'],rows=n.rows,reason=reason,mutations=len(n.mutations),direct_fresh_tty4_worker=dict(status='passed',rows=m.rows,physical_tty=v['tty']),sources=sources,decision='No recursive extension or guide change was made; pending integrator decision')
(r/'.work/14/14zf-nested-route.json').write_text(json.dumps(v,indent=2)+'\n',newline='\n')
print('PASS direct fresh tty4 worker; reproduced nested route STOP; mutations0')
