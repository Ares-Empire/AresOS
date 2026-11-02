import pathlib,json,sys,hashlib
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/tests'))
import test_owner_walk
walk=test_owner_walk.walk()
p=r/'os/manifest/ci/14/host-walk/result.json';proof=json.loads(p.read_text())
proof.update(status='passed',kind='standalone current host control flow; synthetic responses, not VM acceptance',
 stages=walk['stages'],markers=walk['markers'],checks=walk['checks'],cluttered_prompt_waits=walk['prompt_waits'],
 fresh_idle_answers=walk['fresh_idle_answers'],prompt_resyncs=walk['resyncs'],hidden_read_receipts=walk['hidden_reads'],
 hidden_transition_shapes=walk['hidden_shapes'],cursor_wait_shapes=walk['wait_shapes'],
 typed_profiles=sorted({profile for text,profile in walk['typed']}))
files={v['path'] for v in proof['sources']}|{'os/ci/owner_read_diagnostics.py','os/tests/test_owner_read_diagnostics.py','os/ci/owner_login.py','os/tests/test_owner_login.py','os/tests/owner_login_shim.py'}
proof['sources']=[dict(sha256=hashlib.sha256((r/name).read_bytes()).hexdigest(),path=name) for name in sorted(files)]
files.update({"os/tests/test_owner_finalize.py","os/tests/fixtures/owner-tools/finalize-hold.json","os/ci/owner_key_counter.py","os/tests/test_owner_key_counter.py","os/tests/test_owner_reliable_typing.py"})
proof["sources"]=[dict(sha256=hashlib.sha256((r/name).read_bytes()).hexdigest(),path=name) for name in sorted(files)]
proof.pop('local_suite',None)
p.write_text(json.dumps(proof,indent=2)+'\n',newline='\n')
p.with_name('guest-commands.json').write_text(json.dumps(walk['commands'],indent=2)+'\n',newline='\n')
assert len([s for s in walk['hidden_shapes'] if s['phase']=='left'])==23
assert len([s for s in walk['hidden_shapes'] if s['phase']=='handoff'])==3
names=[n for n,c in walk['commands'] if n.endswith('-diagnostics-completion-start')]
assert len(names)==2 and names[0].endswith('-diagnostics-completion-start')
print('PASS all8 stages;23 hidden pairs,3 public handoffs,2 token-start diagnostic; all composed Bash parsed')
