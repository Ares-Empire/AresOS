import hashlib,json,pathlib,re,sys
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'os/ci'))
from disk_audit import all_variables,boot_variables,check_boot_next,compare_disk,nvram_audit
run=sys.argv[1];assert run.isdigit();base=root/'.work/14'/('run-'+run);td=base/'evidence/two-disk'
def read(p):return json.loads(p.read_text())
receipt=read(base/'receipt.json');assert hashlib.sha256((base/'evidence.zip').read_bytes()).hexdigest()==receipt['sha256']
baseline=read(td/'protected-baseline.json');captures=list(td.glob('*-protected.json'))
for p in captures:compare_disk(baseline,read(p));assert read(p)==baseline
stats=list(td.glob('*-blockstats.json'))
for p in stats:
 value,=[row['stats'] for row in read(p) if row.get('device')=='protected'];assert value['wr_bytes']==value['wr_operations']==value['unmap_operations']==0,p.name
bootproofs=list(td.glob('*-bootnext-audit.json'));nvproofs=list(td.glob('*-nvram-diff.json'));stages=[]
for p in bootproofs:
 expected=read(p);stage=p.name.removesuffix('-bootnext-audit.json');store=read(td/(stage+'-nvram.json'));raw=td/(stage+'-vars.fd')
 assert boot_variables(raw)==store and all_variables(raw)==read(td/(stage+'-all-variables.json'))
 efi=td/(stage+'-target-efi.json');esp=None
 if efi.exists():esp,=[v for v in read(efi)['gpt']['partitions'] if v['type_guid']=='c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
 auth=read(td/expected['authorization']);selected=auth if auth['written'] else None
 observed=check_boot_next(store,authorization=selected,windows_default=expected['windows_default'],target_esp=esp)
 assert dict(**observed,boot=expected['boot'],authorization=expected['authorization'],windows_default=expected['windows_default'])==expected,stage
for p in nvproofs:
 expected=read(p);stage=p.name.removesuffix('-nvram-diff.json');previous=expected['from_stage'];efi=td/(stage+'-target-efi.json');esp=None
 if efi.exists():esp,=[v for v in read(efi)['gpt']['partitions'] if v['type_guid']=='c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
 observed=nvram_audit(read(td/(previous+'-nvram.json')),read(td/(stage+'-nvram.json')),before_devices=read(td/(previous+'-devices.json')),after_devices=read(td/(stage+'-devices.json')),target_esp=esp,windows_first=read(td/(stage+'-bootnext-audit.json'))['windows_default'])
 assert dict(from_stage=previous,**observed)==expected,stage
 before=read(td/(previous+'-all-variables.json'));after=read(td/(stage+'-all-variables.json'));delta={k:dict(before=before.get(k),after=after.get(k)) for k in before.keys()|after.keys() if before.get(k)!=after.get(k)}
 assert delta==read(td/(stage+'-all-variables-diff.json')),stage;stages.append(stage)
assert captures and stats and len(bootproofs)==len(captures) and len(nvproofs)==len(captures)-1
value=dict(status='passed independent replay of actual raw files and counters',run=int(run),head=receipt['head'],protected_captures=len(captures),zero_write_unmap_samples=len(stats),raw_varstores_decoded=len(bootproofs),bootnext_exact_replays=len(bootproofs),nvram_rule_exact_replays=len(nvproofs),all_variable_delta_recomputations=len(nvproofs),stages=stages)
(base/'independent-audits.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(value))
