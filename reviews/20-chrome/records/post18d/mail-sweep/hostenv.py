"""Host stand-ins so the unchanged Mail fixtures run outside the CI container.

Only the managed-settings precondition differs: CI installs a root-owned
/etc/claude-code/managed-settings.json, which this Mac must not get. The
stand-in returns the same policy and reproduces the production read's
descriptor shape (three directory descriptors closed with os.close plus one
leaf stream), so the fault sweep sees the same file.close points as on CI.
Applied identically to both compared commits.
"""
import atexit
import json
import os
import tempfile

from aresos_control import boundary
from aresos_control.boundary_policy import asking_rules

_SETTINGS = None


def install():
    global _SETTINGS
    handle, _SETTINGS = tempfile.mkstemp(prefix='managed-settings-', suffix='.json')
    with os.fdopen(handle, 'w') as stream:
        json.dump({'permissions': {'ask': asking_rules()}}, stream)
    atexit.register(os.unlink, _SETTINGS)

    def read(self, path):
        first = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        second = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        os.close(first)
        third = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        os.close(second)
        try:
            leaf = os.open(_SETTINGS, os.O_RDONLY)
            with os.fdopen(leaf, 'rb') as stream:
                return json.loads(stream.read())
        finally:
            os.close(third)

    boundary.Boundary.read = read
