import pathlib,sys,unittest,json,time
r=pathlib.Path.cwd();sys.path[:0]=[str(r/'os/tests'),str(r/'os/ci')]
prior=json.loads((r/'os/manifest/ci/14/14zs-preflight/preparation.json').read_text())['whole_suite']['documented_host_limitations']
suite=unittest.defaultTestLoader.discover(str(r/'os/tests'))
count=suite.countTestCases();start=time.monotonic()
result=unittest.TextTestRunner(verbosity=2).run(suite)
failed=sorted({case.id() for case,_ in result.errors+result.failures})
def display(testid):
    module,cls,method=testid.rsplit('.',2)
    return method+' ('+module+'.'+cls+'.'+method+')'
known={name.split(' (',1)[1][:-1] for name in prior}
unknown=sorted(set(failed)-known)
value=dict(tests=count,seconds=round(time.monotonic()-start,3),executed=result.testsRun,
 distinct_passed=count-len(failed),skips=len(result.skipped),actual_host_limitations=[display(x) for x in failed if x in known],
 documented_host_limitations=prior,unknown_failures=unknown,
 status='all checks passed' if result.wasSuccessful() else 'known local host limitations; native suite mandatory' if not unknown and not result.skipped else 'stopped')
(r/'.work/14/14zx/whole-suite.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(value),flush=True)
assert result.testsRun==count and not result.skipped and not unknown, 'STOP: new local failure; preserve diagnostics'
