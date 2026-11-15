"""One extra test-only qualification input; actual gating remains in the service."""
import copy
import os
from pathlib import Path
import sys


def install(daemon):
    if sys.platform != 'linux' or os.environ.get('GITHUB_ACTIONS') != 'true' or not Path('/.dockerenv').exists():
        raise RuntimeError('Adapter browser fixtures run only in GitHub Linux containers')
    original = daemon.engine.request

    def request(value, admin=False):
        path = Path('/run/aresos-tools/fixture-qualification')
        mode = path.read_text() if path.exists() else ''
        if mode.startswith('adapter-off-'):
            site = mode.removeprefix('adapter-off-')
            candidate = copy.deepcopy(daemon.engine.store.get('chrome:qualification'))
            if not candidate or not candidate['entries'] or site not in candidate['entries'][-1]['adapters']:
                raise ValueError('Unknown adapter qualification fixture')
            path.unlink()
            candidate['entries'][-1]['adapters'][site] = False
            daemon.engine.store.write({'chrome:qualification': candidate}, 'chrome_test_adapter_qualification',
                                      'Synthetic failed adapter qualification input')
        return original(value, admin)

    daemon.engine.request = request
