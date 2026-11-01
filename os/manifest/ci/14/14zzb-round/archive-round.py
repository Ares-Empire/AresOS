"""Archive terminal round evidence only; never pushes or dispatches."""
import collections, hashlib, json, pathlib, shutil, subprocess, sys

r = pathlib.Path.cwd()
w = r / '.work/14'
head = '211df982b5bf080b0167b8fe6e8dd3c5eb264fe8'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == head
assert not subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()
sys.path.insert(0, str(r / 'os/ci'))
import rehearsal_guard as guard
guard.configure('14')

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def order(v):
    if isinstance(v, list):
        return [order(x) for x in v]
    if isinstance(v, dict):
        keys = [k for k in v if k.endswith('sha256')]
        return {k: order(v[k]) for k in keys + [k for k in v if k not in keys]}
    return v

closed = read(w / '14zzb/closed.json')
assert closed['head'] == head and len(closed['runs']) == 2
assert closed['ledger']['dispatch_counts'] == {'probe': 31, 'owner-tools': 20}
assert closed['ledger']['history']['complete']
assert closed['organization']['other_repos_reserve'] == 150
assert closed['organization']['paid_budget_read'] is False
comparison = guard.ledger_organization_check(
    closed['ledger'], closed['organization'],
    dict(authorization=read(w / '14zzb-pre-owner-tools-authorization.json'),
         dispatched_run=41324240079))
assert comparison['status'].startswith('passed')
out = r / 'os/manifest/ci/14/14zzb-round'
assert not out.exists()
out.mkdir()

def write(name, value):
    (out / name).write_text(json.dumps(order(value), indent=2) + '\n', encoding='utf-8', newline='\n')

write('ledger.json', dict(**closed, organization_ledger_comparison=comparison,
    job_rule_counts=dict(collections.Counter(j['rule'] for run in closed['ledger']['runs'] for j in run['jobs'])),
    package_minute_ledger_trusted=True))
write('probe-authorization.json', read(w / '14zzb-pre-probe-authorization.json'))
write('qualification-authorization.json', read(w / '14zzb-pre-owner-tools-authorization.json'))
write('push.json', read(w / '14zzb-push-attempt.json'))
write('local-privacy-pushed-head.json', read(w / '14zzb-one-push-scan.json'))
write('qualification-replay.json', read(w / '14zzb-owner-tools-local.json'))
write('qualification-replay-attempts.json', read(w / '14zzb-qualification-replay-attempts.json'))
write('terminal-facts.json', read(w / '14zzb/terminal-facts.json'))
write('reviewer-correction.json', dict(status='local zero-cost post-run reviewer correction only; CI success unchanged',
    cause='handoff glob also selected associated transport and public-echo JSON files',
    correction='select only names ending handoff-<integer>.json; exact count3 and every field assertion unchanged',
    tests=6, all_other_reviewer_AST_nodes_identical=True, new_pushes=0, new_dispatches=0,
    original=dict(sha256=sha(w/'14zzb/qualification-proof-at-dispatch.py'),path='.work/14/14zzb/qualification-proof-at-dispatch.py'),
    reviewed=dict(sha256=sha(w/'14zzb-qualification-proof.py'),path='.work/14/14zzb-qualification-proof.py')))

for label, run, mode in [('probe31', 41321806985, 'probe'), ('qualification20', 41324240079, 'owner-tools')]:
    base = w / ('run-' + str(run))
    basic = w / '14zzb' / ('basic-' + str(run))
    receipt = read(base / 'receipt.json')
    assert receipt['head'] == head and receipt['run'] == run
    write(label + '-artifact.json', receipt)
    for source, suffix in [
        ('14zzb-privacy-classification.json', 'artifact-review'),
        ('14zzb-log-classification.json', 'log-review'),
        ('14zzb-kernel-proof.json', 'kernel-proof'),
        ('14zzb-ps2-health-proof.json', 'ps2-health'),
        ('independent-audits.json', 'independent-audits'),
        ('native-timing-proof.json', 'native-timing'),
        ('14zzb-' + ('probe' if mode == 'probe' else 'qualification') + '-proof.json', 'acceptance')]:
        p = base / source
        if p.exists():
            write(label + '-' + suffix + '.json', read(p))
    write(label + '-source-bindings.json', dict(files=[
        dict(sha256=sha(p), path=p.relative_to(r).as_posix())
        for p in sorted(basic.iterdir()) if p.is_file()]))

tools = [
    w / '14zzb-classify.py', w / '14zzb-control.py', w / '14zzb-qualification-proof.py',
    w / '14zzb' / 'post-run.py', w / '14zzb' / 'log-review.py',
    w / '14zzb' / 'close-guard.py', w / '14zzb' / 'archive-round.py',
    w / '14zzb' / 'commit-report.py', w / '14zzb' / 'terminal-facts.py',
    w / '14zzb' / 'test_review_receipts.py', w / '14zzb' / 'qualification-proof-at-dispatch.py']
bindings = []
for p in tools:
    target = p.name
    assert not (out / target).exists()
    shutil.copyfile(p, out / target)
    bindings.append(dict(sha256=sha(p), path=p.relative_to(r).as_posix(), archive=target))
write('review-tools.json', dict(status='local read-only review and closing tools; dispatch tools sealed before push', files=bindings))
print('ARCHIVED_TERMINAL_ROUND', closed['ledger']['consumed_minutes'], comparison)
