"""Derive sanitized completed-run timing and owner-action evidence."""
import datetime, hashlib, json, pathlib, re, zipfile
r = pathlib.Path.cwd()
w = r / '.work/14'
b = w / 'run-41324240079'
e = b / 'evidence/two-disk'
basic = w / '14zzb/basic-41324240079'

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def stamp(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
def bind(p): return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), path=p.relative_to(r).as_posix())

job, = [x for x in read(basic/'jobs.json')['jobs'] if x['name'] == 'Pinned live ISO inspection and two-disk rehearsal']
vm, = [x for x in job['steps'] if x['name'] == 'Prepare disposable file disks and qualify the real live environment']
assert vm['conclusion'] == job['conclusion'] == 'success'
with zipfile.ZipFile(basic/'logs.zip') as z:
    member, = [n for n in z.namelist() if n.endswith('_Prepare disposable file disks and qualify the real live environment.txt')]
    raw = z.read(member)
stages = []
start = stamp(vm['started_at'])
for no, line in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
    m = re.fullmatch(r'(\d{4}-\d\d-\d\dT[^ ]+Z) OFFLINE PROTECTED DISK UNCHANGED: ([a-z0-9-]+) [0-9a-f]{64}', line)
    if m:
        end = stamp(m[1]); assert end > start
        stages.append(dict(stage=m[2], started_at=start.isoformat(), completed_at=m[1],
            seconds=(end-start).total_seconds(), log_line=no))
        start = end
assert len(stages) == 16 and stages[-2]['stage'] == 'final-unattended-windows' and stages[-1]['stage'] == 'final-detached-windows'

actions = []
for p in sorted(e.glob('*-owner-result.json')):
    v = read(p)
    actions.append(dict(**bind(p), command=v.get('command'), status=v['status'],
        mutations=sum(bool(t.get('mutation')) for t in v.get('trace', []))))
assert len(actions) == 38
byname = {pathlib.Path(x['path']).name: x for x in actions}
for name in ['rollback-from-stock-refused-owner-result.json', 'layout-unproved-reboot-refusal-owner-result.json', 'private-owner-dummy-login-owner-result.json']:
    assert byname[name]['status'] == 'stopped' and byname[name]['mutations'] == 0
assert byname['tools-prepare-rerun-owner-result.json']['mutations'] == 0
assert all(x['status'] == 'passed' for x in actions if pathlib.Path(x['path']).name not in {
    'rollback-from-stock-refused-owner-result.json', 'layout-unproved-reboot-refusal-owner-result.json', 'private-owner-dummy-login-owner-result.json'})

default = read(e/'default-stock-default-verified-deployments.json')['rpm']['deployments']
assert default[0]['booted'] and default[0]['pinned']
value = dict(status='passed actual completed qualification20 milestones', run=41324240079, head=job['head_sha'],
    sources=[bind(basic/'jobs.json'),dict(**bind(basic/'logs.zip'),member=member,member_sha256=hashlib.sha256(raw).hexdigest())],
    before_vm_seconds=(stamp(vm['started_at'])-stamp(job['started_at'])).total_seconds(),
    vm_seconds=(stamp(vm['completed_at'])-stamp(vm['started_at'])).total_seconds(),
    after_vm_seconds=(stamp(job['completed_at'])-stamp(vm['completed_at'])).total_seconds(),
    whole_job_seconds=(stamp(job['completed_at'])-stamp(job['started_at'])).total_seconds(),
    stages=stages, actions=actions, expected_refusals_zero_mutations=True, prepare_rerun_zero_mutations=True,
    stock_default_first_booted_and_pinned=True, final_windows_marker_boots_completed=2,
    private_raw_console_or_secret_values_included=False)
(w/'14zzb/terminal-facts.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('REAL_QUALIFICATION20_TIMINGS', {k:value[k]/60 for k in ('before_vm_seconds','vm_seconds','after_vm_seconds','whole_job_seconds')})
print('REAL_COMPLETED_STAGES', [x['stage'] for x in stages])
