"""Disposable CI child: kill -9 at a named durable boundary, never in production."""
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys

from aresos_control.engine import Engine

root, point, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
engine = Engine(root / "state", root / "independent")
occurrence = int(sys.argv[4]) if len(sys.argv) > 4 else 1
hits = 0


def checkpoint(name):
    global hits
    if name == point:
        hits += 1
        if hits == occurrence:
            os.kill(os.getpid(), signal.SIGKILL)


if len(sys.argv) > 5:
    write = engine.store.write
    writes = 0

    def backup_before_write(*args, **kwargs):
        global writes
        writes += 1
        if writes == occurrence:
            # Save the immediately preceding state, including earlier stages of
            # this same operation. The parent restores it before ANY restart.
            backup = sqlite3.connect(root / "preceding.sqlite")
            engine.store.db.backup(backup)
            backup.close()
            (root / "preceding-seq.json").write_text(json.dumps({"seq": len(engine.store.events) + 1}))
        return write(*args, **kwargs)

    engine.store.write = backup_before_write


engine.store.checkpoint = checkpoint
engine.receiver.checkpoint = checkpoint
if mode in {"reserve", "reserve_delete"}:
    engine.dispatch("testapp_prepare_" + ("send" if mode == "reserve" else "delete"),
                    json.loads((root / "arguments.json").read_text()))
elif mode == "repair":
    engine.dispatch("testapp_operation_repair", json.loads((root / "arguments.json").read_text()))
elif mode == "restore":
    engine.dispatch("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
else:
    engine.dispatch("testapp_" + mode, json.loads((root / "approval.json").read_text()))
raise SystemExit("Checkpoint was never reached: " + point)
