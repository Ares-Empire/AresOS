import json
from pathlib import Path
import os
import signal
import sys

from aresos_control.engine import Engine

root = Path(sys.argv[1])
args = json.loads((root / 'crash.json').read_text())
engine = Engine(root / 'state', root / 'independent')
counts = {}
def checkpoint(name):
    counts[name] = counts.get(name,0) + 1
    if name == args['checkpoint'] and counts[name] == args.get('occurrence',1):
        os.kill(os.getpid(),signal.SIGKILL)
engine.store.checkpoint = checkpoint
try:
    result = engine.request({'v':1,'method':'call','action':args['action'],'arguments':args['approval']})
    print(json.dumps({'result':result,'counts':counts}))
finally:
    engine.close()
