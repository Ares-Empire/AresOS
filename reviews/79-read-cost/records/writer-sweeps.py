"""Exercise the seven requested writer flows through the actual isolated runner."""
import json
import time
from state_sweeps import isolated_flows
from test_fault_surface import Writers

if __name__ == '__main__':
    started = time.perf_counter()
    counts = isolated_flows(Writers(methodName='runTest'), [
        'qualification', 'delivery', 'readonly', 'drop', 'allow', 'trusted', 'stopped_submit'])
    print('Selected writer surface', json.dumps(counts), flush=True)
    print('Seconds', round(time.perf_counter() - started, 3), flush=True)
