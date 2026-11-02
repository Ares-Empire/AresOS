"""Run the final real-chain regression against the retained faulty adapter, locally only."""
import ast, contextlib, hashlib, json, pathlib, subprocess, sys, unittest
from unittest.mock import patch
r=pathlib.Path.cwd();sys.path[:0]=[str(r/'os/ci'),str(r/'os/tests')]
import owner_vm as vm
import test_owner_walk as walk
source=json.loads((r/'.work/14/14zx/retained-source.json').read_text())
raw=(r/source['path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==source['sha256']
node,=[n for n in ast.parse(raw.decode()).body if isinstance(n,ast.FunctionDef) and n.name=='public_typing']
namespace=dict(vm.__dict__)
exec(compile(ast.Module(body=[node],type_ignores=[]),'retained-14zw-public_typing','exec'),namespace)
with contextlib.ExitStack() as stack:
    stack.enter_context(patch.object(vm,'public_typing',namespace['public_typing']))
    for name in ('TEXT','type_text','physical_keys'):
        stack.enter_context(patch.object(vm.kb,name,getattr(vm.kb,name)))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        walk.OwnerWalkTest('test_real_typing_chain_emits_exact_keys_through_every_remaining_stage')]))
assert result.testsRun==1 and len(result.failures)==1 and not result.errors
assert 'Unknown or untypeable physical character' in result.failures[0][1]
proof=dict(status='expected regression failure on retained faulty adapter',
    source=dict(sha256=hashlib.sha256(raw).hexdigest(),path='os/ci/owner_vm.py',commit='75a2c638cecff042b528eb07e3089eda9129de02'),
    test='test_real_typing_chain_emits_exact_keys_through_every_remaining_stage',
    assertion='Unknown or untypeable physical character',tests=1,failures=1,errors=0,
    no_source_rewrite=True,no_vm=True,no_dispatch=True)
(r/'.work/14/14zx/old-adapter-regression.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PASS: the final regression rejects the actual retained 14zw adapter; no source or VM changed')
