"""Zero-cost qualification sizing, from retained q17/q19 log checkpoints."""
import datetime,hashlib,json,pathlib,re,zipfile
R=pathlib.Path.cwd();W=R/'.work/14';D=W/'14zzb'
def stamp(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def order(v):
 if isinstance(v,list):return [order(x) for x in v]
 if isinstance(v,dict):
  keys=[k for k in v if k.endswith('sha256')];return {k:order(v[k]) for k in keys+[k for k in v if k not in keys]}
 return v
inputs=[(17,41278848542,W/'14zx/basic-41278848542'),(19,41305049425,W/'14zz/basic-41305049425')]
observed=[];sources=[]
for number,run,basic in inputs:
 jobs_path=basic/'jobs.json';jobs=read(jobs_path);job,=[x for x in jobs['jobs'] if x['name']=='Pinned live ISO inspection and two-disk rehearsal']
 assert job['run_id']==run and job['status']=='completed'
 vm,=[s for s in job['steps'] if s['name']=='Prepare disposable file disks and qualify the real live environment']
 with zipfile.ZipFile(basic/'logs.zip') as z:
  name,=[n for n in z.namelist() if n.endswith('_Prepare disposable file disks and qualify the real live environment.txt')]
  raw=z.read(name);lines=raw.decode('utf-8-sig').splitlines()
 checkpoints=[]
 for line_no,line in enumerate(lines,1):
  m=re.fullmatch(r'(\d{4}-\d\d-\d\dT[^ ]+Z) OFFLINE PROTECTED DISK UNCHANGED: ([a-z0-9-]+) [0-9a-f]{64}',line)
  if m:checkpoints.append(dict(stage=m[2],completed_at=m[1],log_line=line_no))
 assert checkpoints and len({x['stage'] for x in checkpoints})==len(checkpoints)
 previous=stamp(vm['started_at']);stages=[]
 for row in checkpoints:
  end=stamp(row['completed_at']);seconds=(end-previous).total_seconds();assert seconds>0
  stages.append(dict(**row,started_at=previous.isoformat(),seconds=seconds,minutes=seconds/60))
  previous=end
 observed.append(dict(qualification=number,run=run,head=job['head_sha'],job_started_at=job['started_at'],job_completed_at=job['completed_at'],vm_started_at=vm['started_at'],vm_completed_at=vm['completed_at'],before_vm_seconds=(stamp(vm['started_at'])-stamp(job['started_at'])).total_seconds(),vm_seconds=(stamp(vm['completed_at'])-stamp(vm['started_at'])).total_seconds(),after_vm_seconds=(stamp(job['completed_at'])-stamp(vm['completed_at'])).total_seconds(),stages=stages,tail_after_last_checkpoint_seconds=(stamp(vm['completed_at'])-previous).total_seconds(),checkpoint_caution='A failure-unwind audit checkpoint is not proof that every stage assertion completed'))
 sources.extend([dict(sha256=sha(jobs_path.read_bytes()),path=jobs_path.relative_to(R).as_posix()),dict(sha256=sha((basic/'logs.zip').read_bytes()),path=(basic/'logs.zip').relative_to(R).as_posix(),member=name,member_sha256=sha(raw))])
q17=W/'run-41278848542/evidence/two-disk'
facts=[]
for filename,status in [('rollback-from-stock-refused-owner-result.json','stopped'),('owner-keep-stock-owner-result.json','passed'),('owner-keep-stock-title-owner-result.json','passed')]:
 p=q17/filename;v=read(p);assert v['status']==status;facts.append(dict(sha256=sha(p.read_bytes()),path=p.relative_to(R).as_posix(),status=status,command=v['command']))
assert not (q17/'default-stock-check-owner-result.json').exists() and not (q17/'owner-tools-result.json').exists()
known=['baseline-firmware','protected-second-install','boot-3-pre-login-reset','offline-first-stock','offline-roundtrip-unattended-windows','offline-roundtrip-detached-windows','tools-stock','prepared-unattended-windows','corrected-stock','aresos','aresos-intl','aresos-back-de']
projected=[]
for stage in known:
 rows=[dict(qualification=x['qualification'],**s) for x in observed for s in x['stages'] if s['stage']==stage]
 assert len(rows)==2,stage
 slow=max(rows,key=lambda x:x['seconds']);projected.append(dict(stage=stage,seconds=slow['seconds'],minutes=slow['seconds']/60,rule='slower completed checkpoint interval across q17/q19',selected_qualification=slow['qualification'],observations=rows))
# These boots do not perform the one-time private image pull/switch or the
# initial intentional layout-failure/revert matrix. tools-stock is deliberately
# heavier than the remaining stock checks: install/prepare/rerun/USB export.
stock_candidates=[dict(qualification=x['qualification'],**s) for x in observed for s in x['stages'] if s['stage'] in ('boot-3-pre-login-reset','offline-first-stock','tools-stock','rollback-stock')]
slow_stock=max(stock_candidates,key=lambda x:x['seconds'])
windows_candidates=[dict(qualification=x['qualification'],**s) for x in observed for s in x['stages'] if s['stage'] in ('offline-roundtrip-unattended-windows','offline-roundtrip-detached-windows','prepared-unattended-windows')]
slow_windows=max(windows_candidates,key=lambda x:x['seconds'])
for stage in ('rollback-from-stock-refusal','keep-stock/title/reboot','default-stock-verification'):
 projected.append(dict(stage=stage,seconds=slow_stock['seconds'],minutes=slow_stock['seconds']/60,rule='one entire slowest comparable stock-boot interval per remaining logical group; deliberately overallocates boot cost for the two command groups',comparable_stage=slow_stock['stage'],selected_qualification=slow_stock['qualification']))
for stage in ('final-unattended-windows','final-detached-windows'):
 projected.append(dict(stage=stage,seconds=slow_windows['seconds'],minutes=slow_windows['seconds']/60,rule='slowest observed comparable Windows marker boot',comparable_stage=slow_windows['stage'],selected_qualification=slow_windows['qualification']))
seconds=sum(x['seconds'] for x in projected);vm_margin=seconds*1.25
before=max(x['before_vm_seconds'] for x in observed);after=max(x['after_vm_seconds'] for x in observed)
whole_margin=(seconds+before+after)*1.25
v=dict(status='passed' if vm_margin<=180*60 and whole_margin<=220*60 else 'STOP: retained timing projection exceeds approved limit',sources=sources,observed_runs=observed,qualification17_completed_command_facts=facts,brief_fact_note='q17 did complete rollback-from-stock refusal and keep-stock/title commands; its default-stock checkpoint was failure unwind, not successful verification. The projection nevertheless uses fresh conservative whole-boot allowances for every remaining logical group.',projection=projected,comparable_stock_candidates=stock_candidates,comparable_windows_candidates=windows_candidates,excluded_from_tail_comparison=[dict(stage='corrected-stock',reason='one-time registry dummy/real login, signature verification and image switch/pull; retained in full known projection, not comparable to the already-installed stock tail'),dict(stage='aresos',reason='initial intentional plain-US rejection/revert and multiple physical login/proof branches; retained in full known projection, not a stock-only tail boot'),dict(stage='protected-second-install',reason='installation, not a boot of already-installed stock')],vm_projection_minutes=seconds/60,margin_fraction=0.25,vm_with_margin_minutes=vm_margin/60,vm_limit_minutes=180,before_vm_slower_minutes=before/60,after_vm_slower_minutes=after/60,whole_job_projection_minutes=(seconds+before+after)/60,whole_job_with_margin_minutes=whole_margin/60,qualification_bound_minutes=220,probe_bound_minutes=72,cap_minutes=2750,starting_minutes=2144,round_worst_case_minutes=2144+72+220,new_pushes=0,dispatches=0,privacy_changes=False)
(D/'projection.json').write_text(json.dumps(order(v),indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v[k] for k in ('status','vm_projection_minutes','vm_with_margin_minutes','before_vm_slower_minutes','after_vm_slower_minutes','whole_job_with_margin_minutes','round_worst_case_minutes')},indent=2))
assert v['status']=='passed','STOP: no limit change, push or dispatch permitted'
