"""Size the review-fix round before changing limits or dispatching."""
import datetime,hashlib,json,pathlib,re,zipfile
r=pathlib.Path.cwd(); w=r/'.work/14'; out=r/'os/manifest/ci/14/14zzc-timing'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def bind(p):return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(r).as_posix())
def order(v):
    if isinstance(v,list):return [order(x) for x in v]
    if isinstance(v,dict):
        keys=[k for k in v if k.endswith('sha256')];return {k:order(v[k]) for k in keys+[k for k in v if k not in keys]}
    return v
oldpath=r/'os/manifest/ci/14/14zzb-timing/projection.json'; old=read(oldpath)
q20path=r/'os/manifest/ci/14/14zzb-round/terminal-facts.json'; q20=read(q20path)
assert q20['status'].startswith('passed') and q20['run']==41324240079
observed=old['observed_runs']+[dict(qualification=20,stages=q20['stages'])]
projection=[]
for stage in [x['stage'] for x in old['projection'][:12]]+['rollback-stock','default-stock']:
    rows=[dict(qualification=v['qualification'],**s) for v in observed for s in v['stages'] if s['stage']==stage
          and not (stage=='default-stock' and v['qualification']!=20)]
    slow=max(rows,key=lambda x:x['seconds'])
    projection.append(dict(stage=stage,seconds=slow['seconds'],selected_qualification=slow['qualification'],rule='slowest completed retained interval; failure-unwind default-stock excluded'))
windows=old['comparable_windows_candidates']+[dict(qualification=20,**s) for s in q20['stages'] if 'windows' in s['stage']]
slow_windows=max(windows,key=lambda x:x['seconds'])
for stage in ('final-unattended-windows','final-detached-windows'):
    projection.append(dict(stage=stage,seconds=slow_windows['seconds'],selected_qualification=slow_windows['qualification'],comparable=slow_windows['stage'],rule='slowest complete Windows-marker interval'))
boots=old['comparable_stock_candidates']+[dict(qualification=v['qualification'],**s) for v in observed for s in v['stages'] if s['stage'] in ('aresos-intl','aresos-back-de')]
slow_boot=max(boots,key=lambda x:x['seconds'])
for stage in ('layout-reset-trial','layout-reset-recovery'):
    projection.append(dict(stage=stage,seconds=slow_boot['seconds'],selected_qualification=slow_boot['qualification'],comparable=slow_boot['stage'],rule='one whole slowest comparable boot, including its existing owner-command work'))
artifact=w/'run-41324240079/evidence.zip'
assert hashlib.sha256(artifact.read_bytes()).hexdigest()==read(r/'os/manifest/ci/14/14zzb-round/qualification20-artifact.json')['sha256']
with zipfile.ZipFile(artifact) as z:
    ready=[x for x in z.infolist() if re.search(r'/tools-install-ready-wait-[0-9]+-(?:sample|resync|idle)-[0-9]+\.json$',x.filename)]
    echo,=[x for x in z.infolist() if re.search(r'/tools-install-command-echo-[0-9]+-transport\.json$',x.filename)]
    assert ready
    before=max(ready,key=lambda x:x.date_time)
    interval=(datetime.datetime(*echo.date_time)-datetime.datetime(*before.date_time)).total_seconds()+4
    assert interval>0
command=read(r/'os/owner-tools/commands.json')['install']
assert max(map(len,command.splitlines()))<120
extra_lines=len(command.splitlines())-1
projection.append(dict(stage='extra-bootstrap-lines',seconds=extra_lines*interval,
    rule='one whole retained original113-character typing/record-list/echo interval per extra line; +4s DOS timestamp granularity allowance',
    lines=len(command.splitlines()),maximum_line_chars=max(map(len,command.splitlines())),old_line_chars=113,
    seconds_per_extra_line=interval,source_ready=before.filename,source_echo=echo.filename))
total=sum(x['seconds'] for x in projection)/60
margin=total*1.25
before=max(old['before_vm_slower_minutes'],q20['before_vm_seconds']/60)
after=max(old['after_vm_slower_minutes'],q20['after_vm_seconds']/60)
whole=(total+before+after)*1.25
assert margin<=200,'STOP: review-fix VM projection exceeds approved200 minutes'
vm=180 if margin<=180 else 200;bound=220 if vm==180 else 240
assert whole<=bound,'STOP: full-job projection exceeds qualification bound'
value=dict(status='passed',sources=[bind(oldpath),bind(q20path),bind(artifact),bind(r/'os/owner-tools/commands.json')],
    projection=projection,vm_projection_minutes=total,margin_fraction=.25,vm_with_margin_minutes=margin,
    vm_limit_minutes=vm,before_vm_slower_minutes=before,after_vm_slower_minutes=after,
    whole_job_with_margin_minutes=whole,qualification_bound_minutes=bound,probe_bound_minutes=72,
    starting_minutes=2301,cap_minutes=2750,round_worst_case_minutes=2301+72+bound,
    caps=dict(probe=32,**{'owner-tools':21}),limit_decision='briefs/14zzc-review-fixes.md')
out.mkdir(exist_ok=False)
(out/'projection.json').write_text(json.dumps(order(value),indent=2)+'\n',encoding='utf-8',newline='\n')
(w/'14zzc/projection.json').write_text(json.dumps(order(value),indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:value[k] for k in ('vm_projection_minutes','vm_with_margin_minutes','vm_limit_minutes','whole_job_with_margin_minutes','qualification_bound_minutes','round_worst_case_minutes')},indent=2))
