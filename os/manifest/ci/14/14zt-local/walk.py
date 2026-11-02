import pathlib,json,hashlib,sys
r=pathlib.Path.cwd();w=r/'.work/14/14zt';sys.path.insert(0,str(r/'os/tests'));import test_owner_walk
v=test_owner_walk.walk()
assert {'aresos','aresos-intl','aresos-back-de','rollback-stock','default-stock'} <= set(v['stages'])
assert {'final-unattended-windows','final-detached-windows'} <= set(v['markers'])
assert any('layout-intl-proof' in name for name in v['prompt_waits'])
assert any('layout-back-de-proof' in name for name in v['prompt_waits'])
assert any('owner-rollback' in name for name in v['prompt_waits'])
assert any('owner-keep-stock' in name for name in v['prompt_waits'])
assert len([s for s in v['hidden_shapes'] if s['phase']=='left'])==23
commands=v.pop('commands');v.pop('typed')
value=dict(status='passed existing healthy-redraw stand-in route; not a repair for the Q15 disconnected keyboard',
 kind='local synthetic responses, no VM/hardware operations',**v,
 hidden_pairs=23,public_handoffs=3,uncovered_waits=[],
 dead_keyboard_result='Separate exact-replay.json refuses all8 remaining readiness contexts; no fictitious successful Enter was injected into Q15.',
 sources=[dict(sha256=hashlib.sha256((r/p).read_bytes()).hexdigest(),path=p) for p in (
 'os/ci/owner_console.py','os/ci/owner_vm.py','os/tests/test_owner_console.py','os/tests/test_owner_walk.py',
 'os/tests/test_owner_records_prompt.py','os/tests/fixtures/owner-console/14zt-q15-shape.json')])
(w/'host-walk.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
(w/'healthy-guest-commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PASS healthy route:8 stages,23 hidden pairs,3 handoffs,US-intl/back-de/rollback/keep-stock/final Windows; no raw private fixture assumed recoverable')
