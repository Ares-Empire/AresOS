import hashlib,json,pathlib,sys
r=pathlib.Path.cwd();run=int(sys.argv[1]);b=r/'.work/14'/('run-'+str(run));e=b/'evidence';receipt=json.loads((b/'receipt.json').read_text())
def read(p):return json.loads(p.read_text())
native=read(e/'14-counter-kernel.json');actual=read(e/'two-disk/counter-kernel-proof.json')
assert native['sha']==receipt['head'] and actual['sha']==receipt['head']
assert actual['status']=='passed' and actual['real_kernel'] is True and actual['skipped'] is False
assert actual['negative_control']['counts']==dict(press=0,release=1,repeat=0,syn_dropped=0)
assert actual['negative_control']['comparison']['matches'] is False
assert actual['fixed']['counts']==dict(press=1,release=1,repeat=0,syn_dropped=0)
assert actual['fixed']['comparison']['matches'] is True
if native['status']=='passed':assert actual['location']=='native' and native==actual
else:assert native['status']=='guest-required' and actual['location']=='guest-before-hidden-input'
value=dict(status='passed',run=run,head=receipt['head'],location=actual['location'],skipped=False,proof=actual,native=native,files=[dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(e).as_posix()) for p in (e/'14-counter-kernel.json',e/'two-disk/counter-kernel-proof.json')])
(b/'14zzb-kernel-proof.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PASS real kernel negative flush and positive separate-client preservation;',actual['location'])
