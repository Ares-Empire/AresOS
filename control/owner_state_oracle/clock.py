"""Make implicit calendar reads follow the scenario's effective test clock."""
from contextlib import contextmanager
import time
from unittest.mock import patch


@contextmanager
def recorded_samples(oracle, index, ttl=900):
    """Record the test clock values consumed by production, outside faults."""
    call = oracle.script[index]
    call['operation_ttl'] = ttl
    samples = call.setdefault('clock_samples', [])
    clock = time.time
    def sampled():
        value = clock()
        if not samples or samples[-1] != value:
            samples.append(value)
        return value
    with patch.object(time, 'time', side_effect=sampled):
        yield


@contextmanager
def scripted_calendar():
    real_localtime = time.localtime
    def localtime(seconds=None):
        return real_localtime(time.time() if seconds is None else seconds)
    with patch.object(time, 'localtime', side_effect=localtime), \
            patch.object(time, 'time_ns', side_effect=lambda: int(time.time() * 1_000_000_000)):
        yield
