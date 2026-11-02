"""Local synthetic route; no VM, hardware query, dispatch or credentials."""
import hashlib
import json
import pathlib
import sys

r=pathlib.Path.cwd()
sys.path[:0]=[str(r/'os/tests'),str(r/'os/ci')]
import test_owner_walk

walk=test_owner_walk.walk(ps2=True)
assert len([s for s in walk['hidden_shapes'] if s['phase']=='left'])==23
assert len([s for s in walk['hidden_shapes'] if s['phase']=='handoff'])==3
assert {'final-unattended-windows','final-detached-windows'}<=set(walk['markers'])
commands=walk.pop('commands');walk.pop('typed')
folder=r/'os/manifest/ci/14/host-walk'
old=json.loads((folder/'result.json').read_text())
sources={row['path'] for row in old['sources']}
sources.update(p.relative_to(r).as_posix() for p in (r/'os/manifest/ci/14/14zu-local').iterdir() if p.suffix=='.gz')
sources.update(('os/ci/rehearsal_guard.py','os/tests/test_organization_budget.py','os/tests/test_owner_guard.py','os/ci/owner_xhci.py','os/ci/keyboard_vm.py','os/tests/test_owner_ps2.py',
 'os/manifest/ci/14/14zu-local/sources.json','os/manifest/ci/14/14zu-local/source-proof.json',
 'os/manifest/ci/14/14zu-local/walk.py','os/manifest/ci/14/14zu-local/source-proof.py',
 'os/tests/test_owner_records_prompt.py','os/tests/fixtures/owner-console/14zt-q15-shape.json'))
old.update(status='passed',kind='local synthetic PS2/xHCI health route, not VM qualification',
 stages=walk['stages'],markers=walk['markers'],checks=walk['checks'],
 cluttered_prompt_waits=walk['prompt_waits'],fresh_idle_answers=walk['fresh_idle_answers'],prompt_resyncs=walk['resyncs'],
 hidden_read_receipts=walk['hidden_reads'],hidden_transition_shapes=walk['hidden_shapes'],cursor_wait_shapes=walk['wait_shapes'],
 typed_profiles=['de','us-intl'],ps2_health=True,
 sources=[dict(sha256=hashlib.sha256((r/p).read_bytes()).hexdigest(),path=p) for p in sorted(sources)])
old.pop('local_suite',None);old.pop('tests',None)
old['current_verification']='os/manifest/ci/14/14zv-preflight/preparation.json'
(folder/'result.json').write_text(json.dumps(old,indent=2)+'\n',encoding='utf-8',newline='\n')
(folder/'guest-commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8',newline='\n')
result=dict(status='passed',kind='local synthetic guest responses; no VM qualification',
 stages=walk['stages'],markers=walk['markers'],cluttered_prompt_waits=len(walk['prompt_waits']),
 idle_authorized_resyncs=len(walk['resyncs']),hidden_pairs=23,public_handoffs=3,
 health_boundaries=len([name for name,source in commands if name.endswith('-xhci-health')]),
 composed_guest_commands=len(commands),strict_bash_syntax=True,uncovered_waits=[],
 keyboard='AT selection/counter/source tests; physical redraw simulated',
 clutter='Q15 exact geometry/content shape after tools-stock; synthetic healthy kernel journal. The historical VCSA remains clutter only and never grants authority.',
 pending='Actual PS2 event delivery, FUSE hotplug and health timing need November native/VM runs')
(r/'os/manifest/ci/14/14zv-preflight/walk.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
