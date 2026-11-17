"""Hook stand-in, installed only in the disposable native harness: the real hook code with a stand-in service.

`aresos_control.hooks.main` runs unchanged: the real usage gate, input checks, decisions and continuation guard. Only
the service is stood in: `control_pending` answers the held work the supervisor put in HELD for this case, or nothing.
Each Stop hook's output is also logged, in order, for the supervisor's held-work cases (lead, 2026-11-16).
"""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys

assert sys.argv[1:] in (['hook', 'Stop'], ['hook', 'UserPromptSubmit'])
sys.path.insert(0, '/opt/aresos-control')
from process_chain import FOLDER, record
record('hook-' + sys.argv[2])
from aresos_control import hooks

HELD = Path('/home/assistant/held-work.json')


class Service:
    """The service's answer to the one call a hook makes."""
    def __init__(self, path, connect_wait):
        pass

    def call(self, action, arguments):
        assert (action, arguments) == ('control_pending', {}), (action, arguments)
        return {'ok': True, 'data': json.loads(HELD.read_text()) if HELD.exists() else {'items': [], 'total': 0}}


hooks.Client = Service
output = io.StringIO()
with redirect_stdout(output):
    hooks.main({'act_socket': '/unused'}, sys.argv[2])
if sys.argv[2] == 'Stop' and FOLDER.is_dir():
    with (FOLDER / 'stop-decisions.jsonl').open('a') as log:
        log.write(json.dumps({'output': output.getvalue()}) + '\n')
sys.stdout.write(output.getvalue())
