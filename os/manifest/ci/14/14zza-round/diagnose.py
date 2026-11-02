"""Curate retained qualification evidence; never overrides failed acceptance."""
import collections,hashlib,importlib.util,json,pathlib,re,subprocess,zipfile
r=pathlib.Path.cwd();w=r/'.work/14';b=w/'run-41305049425';e=b/'evidence/two-disk';H='10921f81f481bd2b2c7bfb2da9e13deabdb1267f'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def bind(p):return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(r).as_posix())
assert read(b/'run.json')['conclusion']=='failure' and read(b/'receipt.json')['head']==H
jobs=read(b/'jobs.json');job,=[x for x in jobs['jobs'] if x['name']=='Pinned live ISO inspection and two-disk rehearsal']
vm,=[x for x in job['steps'] if x['number']==16];assert vm['conclusion']=='failure'
basic=w/'14zz/basic-41305049425';step=basic/'full-logs'/job['name']/('16_'+vm['name']+'.txt');text=step.read_text(encoding='utf-8')
assert 'has timed out after 106 minutes.' in text
assert not (e/'owner-tools-result.json').exists()
landmark_names=['tools-install','tools-prepare','tools-prepare-rerun','after-first-network-records','tools-record-export','private-owner-login','owner-signature','owner-switch','layout-us-begin','layout-us-revert','layout-reverted-proof','layout-revert-finish','layout-intl-begin','layout-intl-proof','layout-intl-finish','aresos-intl-check','layout-de-begin','layout-back-de-proof','layout-de-finish','aresos-back-de-check','owner-rollback']
landmarks=[]
for name in landmark_names:
 p=e/(name+'-owner-result.json');v=read(p);assert v['status']=='passed',name
 landmarks.append(dict(**bind(p),stage=name,status=v['status'],command=v.get('command',['install'])))
refused=read(e/'layout-unproved-reboot-refusal-owner-result.json');assert refused['status']=='stopped' and not any(x.get('mutation') for x in refused['trace'])
logins=[]
for name,expected in [('layout-plain-us','expected-rejection'),('layout-reverted-login','passed'),('layout-intl-login','passed'),('layout-back-de-login','passed'),('aresos-back-de','passed'),('rollback-stock','passed')]:
 p=e/(name+'-physical-login-result.json');v=read(p);assert v['status']==expected and v['timing']['within_half_timeout'] and not v['value_recorded']
 logins.append(dict(**bind(p),stage=name,status=v['status'],tty=v['tty'],attempts=v['attempts'],elapsed_seconds=v['timing']['elapsed_seconds']))
feet=[]
for name,layout in [('aresos-intl','us-intl'),('aresos-back-de','de')]:
 p=e/(name+'-foot-physical.json');v=read(p);assert v['status']=='passed' and v['layout']==layout
 feet.append(dict(**bind(p),stage=name,status='passed',layout=layout))
def stock(name):
 v=read(e/(name+'-deployments.json'));row,=[x for x in v['rpm']['deployments'] if x['booted']]
 assert v['rpm']['transaction'] is None and row['pinned'] and not any(x.get('staged') for x in v['rpm']['deployments'])
 return {k:row[k] for k in ('checksum','serial','osname')}
identity=stock('corrected-stock');assert stock('rollback-stock')==identity
counts=read(e/'rollback-stock-sudo-hidden-read-wait-224-key-counter-result.json');assert counts['comparison']['matches'] and counts['received']['counts']==dict(press=33,release=33,repeat=0,syn_dropped=0)
assert counts['received']['counts_only'] and not counts['received']['codes_recorded'] and not counts['received']['values_recorded']
transport=read(e/'rollback-stock-sudo-hidden-read-wait-224-left-transport.json');assert transport['verified'] and transport['steps'][-1]['phase']=='syntax' and all(x['status']=='passed' for x in transport['steps'])
assert not (e/'rollback-stock-sudo-hidden-read-wait-224-left.json').exists()
assert not (e/'rollback-from-stock-refused-owner-result.json').exists() and not (e/'owner-keep-stock-owner-result.json').exists()
assert not list(e.glob('*taint*.json'))
with zipfile.ZipFile(b/'evidence.zip') as z:
 stamps=[dict(path=n,zip_utc_time=list(z.getinfo(n).date_time),granularity_seconds=2) for n in ['two-disk/rollback-stock-physical-login-result.json','two-disk/rollback-stock-sudo-hidden-read-wait-224-key-counter-result.json','two-disk/rollback-stock-sudo-hidden-read-wait-224-left-transport.json']]
native=(b/'native.log').read_text(encoding='utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',native);assert m and m[1]=='597' and re.search(r'Z OK\s*$',native,re.M)
privacy=read(b/'14zz-privacy-classification.json');assert privacy['status']=='passed' and privacy['findings']==523 and privacy['iso_listing_findings']==507 and len(privacy['kernel_certificate_findings'])==16
logs=read(b/'14zz-log-classification.json');assert logs['status']=='passed' and logs['findings']==4 and logs['combined_log'].startswith('1_')
assert read(w/'gitleaks/14zza-qualification-native.json')==[]
closed=read(w/'14zza/closed.json');s=importlib.util.spec_from_file_location('guard',r/'os/ci/rehearsal_guard.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);g.configure('14')
comparison=g.ledger_organization_check(closed['ledger'],closed['organization'],dict(authorization=read(w/'14zza/authorization.json'),dispatched_run=41305049425))
assert comparison['package_increase']==comparison['organization_increase']==122 and closed['ledger']['consumed_minutes']==2144
row,=[x for x in closed['ledger']['runs'] if x['run']==41305049425];assert row['minutes']==122
value=dict(status='STOP: global 106-minute VM step deadline; no rerun',run=41305049425,head=H,artifact=read(b/'receipt.json'),native=dict(tests=597,seconds=float(m[2]),skips=0,scan_findings=0,timing=read(b/'native-timing-proof.json')),privacy=privacy,full_log_privacy=logs,kernel=read(b/'14zz-kernel-proof.json'),independent_audits=read(b/'independent-audits.json'),landmarks=landmarks,physical_logins=logins,physical_foot=feet,stock_identity=identity,rollback_stock_login_passed=True,last_sudo_key_counts=counts['comparison'],last_sudo_codes_or_values_recorded=False,last_completion_transport=dict(**bind(e/'rollback-stock-sudo-hidden-read-wait-224-left-transport.json'),bytes=transport['bytes'],chunks=transport['chunks'],verified=transport['verified'],last_phase='syntax',all_acknowledgements_passed=True,completed_observation_result=False),archive_times=stamps,job_vm_step=vm,timeout_log=bind(step),proven_cause='GitHub terminated the step at its configured106-minute deadline, during the post-rollback sudo completion observation',not_proven=['A stuck sudo reader','A dropped key event','An owner-tool refusal','Whether the last completion observation executed or returned before termination'],visual_taint_recorded=False,remaining=['Complete post-rollback sudo readiness/check/public-typing/homebrew/greeter','Rollback-from-stock refusal and zero-mutation proof','keep-stock, refreshed title and reboot','Default-stock boot/identity/keyboard/homebrew/greeter checks','Final unattended and detached Windows markers','Final protected-disk/NVRAM/BootNext audits and aggregate owner-tools result'],organization_ledger_comparison=comparison,ledger=closed['ledger'],organization=closed['organization'],new_pushes=0,new_probes=0,qualification_attempts=1,reruns=0,acceptance_met=False)
(w/'14zza/diagnosis.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('DIAGNOSED actual global deadline;21 owner milestones,USintl/de physical proof and rollback passed; finaltail notverified; native597/202.891; trusted2144 net122/122')
