"""Disposable child for owner archive crash durability tests."""
import os
from pathlib import Path
import signal
import sys
import time
from aresos_control.engine import Engine

root, point = Path(sys.argv[1]), sys.argv[2]
engine = Engine(root / 'state', root / 'independent')
def checkpoint(name):
    if name == point:
        os.kill(os.getpid(), signal.SIGKILL)
engine.store.checkpoint = checkpoint
result = engine.request({'v': 1, 'method': 'call', 'action': 'control_archive',
                         'arguments': {'before': time.time() - 1, 'confirm': 'archive finished history'}}, admin=True)
raise SystemExit('Checkpoint not reached: ' + str(result))
