"""Run independent fault scenarios in isolated Python processes, never threads.

The raw write injector patches process-wide functions. Separate processes keep
every fault interval and temporary store independent while leaving CI enough
time to run the browser matrix after the exhaustive state sweeps.
"""
from concurrent.futures import ProcessPoolExecutor
import importlib
import multiprocessing


def sweep_flow(module, name, flow):
    case=getattr(importlib.import_module(module),name)(methodName='runTest')
    case.setUp()
    try:
        return case.sweep_flow(flow)
    finally:
        case.tearDown()


def isolated_flows(case, flows):
    assert len(flows)==len(set(flows)), 'Repeated fault scenario'
    counts={'single':0,'persistent':0,'pairs':0}
    with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(sweep_flow,type(case).__module__,type(case).__name__,flow) for flow in flows]
        # Every result is required. A worker assertion or process failure fails
        # the parent test; no scenario is retried or accepted without a result.
        for flow,future in zip(flows,futures):
            result=future.result()
            assert set(result)==set(counts) and all(isinstance(value,int) and value>=0 for value in result.values()), (flow,result)
            assert result['single']>0 and result['persistent']==result['single'], (flow,result)
            for key,value in result.items():counts[key]+=value
            print('Chrome isolated fault flow',flow,result,flush=True)
    return counts
