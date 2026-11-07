"""Disposable CI child: kill -9 at a named durable boundary, never in production."""
import json
import os
from pathlib import Path
import signal
import sys

from aresos_control.engine import Engine

root, point, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
engine = Engine(root / "state", root / "independent")


def checkpoint(name):
    if name == point:
        os.kill(os.getpid(), signal.SIGKILL)


engine.store.checkpoint = checkpoint
engine.receiver.checkpoint = checkpoint
if mode == "reserve":
    engine.dispatch("testapp_prepare_send", json.loads((root / "arguments.json").read_text()))
elif mode == "repair":
    engine.dispatch("testapp_operation_repair", json.loads((root / "arguments.json").read_text()))
else:
    engine.dispatch("testapp_" + mode, json.loads((root / "approval.json").read_text()))
raise SystemExit("Checkpoint was never reached: " + point)
