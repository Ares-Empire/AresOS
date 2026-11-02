import pathlib,json,hashlib,base64,re,sys
r=pathlib.Path.cwd();w=r/'.work/14';b=w/'run-40617562735';e=b/'evidence/two-disk';sys.path.insert(0,str(r/'os/ci'));from owner_console import screen
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
diag={p.stem:read(p) for p in e.glob('*-owner-diagnostics.json')}
for name,v in diag.items():print('OWNER_RESULT',name,'status',v.get('status'),'command',v.get('command'),'mutations',sum(bool(x.get('mutation')) for x in v.get('trace',[])))
files=list(e.glob('after-first-network-title-completed*.vcsa'));assert files
samples=[]
for p in files:
 raw=p.read_bytes();full,line=screen(raw)
 samples.append(dict(sha256=hashlib.sha256(raw).hexdigest(),path=p.relative_to(b).as_posix(),geometry=list(raw[:4]),cursor_has_prompt=bool(re.search(r'[$#]$',line)),root_prompt_somewhere=bool(re.search(r'root@[^\n]*#',full)),cursor_line_empty=not line,cursor_line_sha256=hashlib.sha256(line.encode()).hexdigest(),network_kernel_message=bool(re.search(r'virtio_net|link.*[Uu]p|IPv6|DHCP|NetworkManager|NETDEV',full)),serial_or_hypervisor_path='captured VCSA; no raw screen text copied to report'))
 print('READINESS_SAMPLE',json.dumps(samples[-1]))
log=(b/'native.log').read_text();m=re.search(r'Ran (\d+) tests in ([\d.]+)s',log);assert m and int(m[1])==451 and re.search(r'Z OK\s*$',log,re.M)
value=dict(status='STOP: title passed; physical prompt readiness deadline',run=40617562735,head=read(b/'receipt.json')['head'],phase='qualification -> after-first-network-title -> Console.prompt(completed)',native_tests=451,native_seconds=float(m[2]),native_skips=0,
 owner_commands=[dict(stage=k,status=v['status'],command=v.get('command'),mutations=sum(bool(x.get('mutation')) for x in v.get('trace',[]))) for k,v in diag.items()],samples=samples,
 sudo_idle_restored=True,owner_install_passed=True,prepare_passed=True,prepare_rerun_zero_mutations=True,network_enabled=True,title_after_network_passed=True,after_network_comparison_reached=False,
 guest_registry_token_typed=False,layout_session_helper_reached=False,switch_aresos_layout_rollback_keep_stock_reached=False,failure_counter=read(e/'tools-stock-failure-counter.json'),privacy=read(b/'14zg-privacy-classification.json'),audits=read(b/'independent-audits.json'))
assert all(v['status']=='passed' for v in diag.values())
assert sum(bool(x.get('mutation')) for x in diag['tools-prepare-rerun-owner-diagnostics']['trace'])==0
(b/'14zg-stop-observations.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print('PASS exported stop observations; native451; no guest registry login or layout helper reached')
