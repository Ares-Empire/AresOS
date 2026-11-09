"""Make implicit calendar reads follow the scenario's effective test clock."""
from contextlib import contextmanager
import time
from unittest.mock import patch


@contextmanager
def scripted_calendar():
    real_localtime = time.localtime
    def localtime(seconds=None):
        return real_localtime(time.time() if seconds is None else seconds)
    with patch.object(time, 'localtime', side_effect=localtime), \
            patch.object(time, 'time_ns', side_effect=lambda: int(time.time() * 1_000_000_000)):
        yield
