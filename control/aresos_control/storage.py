"""SQLite mirror plus an independently retained, append-only, fsynced operation journal."""
import copy
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .common import Refused, canonical, digest


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Store:
    def __init__(self, state_dir, evidence_dir, checkpoint=lambda _: None):
        self.state_dir, self.evidence_dir = Path(state_dir), Path(evidence_dir)
        if self.state_dir.resolve() == self.evidence_dir.resolve() or self.evidence_dir.resolve().is_relative_to(self.state_dir.resolve()):
            raise ValueError("Independent evidence must be outside the backup tree")
        self.checkpoint = checkpoint
        for directory in (self.state_dir, self.evidence_dir):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.journal = open(self.evidence_dir / "operations.jsonl", "a+b", buffering=0)
        fcntl.flock(self.journal, fcntl.LOCK_EX | fcntl.LOCK_NB)
        sync_directory(self.evidence_dir)
        self.db = sqlite3.connect(self.state_dir / "control.sqlite")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS head (id INTEGER PRIMARY KEY CHECK(id=1), seq INTEGER, hash TEXT);"
                              "INSERT OR IGNORE INTO head VALUES (1,0,'');")
        self.db.commit()
        sync_directory(self.state_dir)
        self.events, self.committed = self._read_journal()
        seq, hash_value = self.db.execute("SELECT seq,hash FROM head WHERE id=1").fetchone()
        expected = self.events[seq - 1]["hash"] if 0 < seq <= len(self.events) else ""
        if seq > len(self.events) or hash_value != expected:
            raise Refused("evidence_mismatch", "The independent record is missing or different; stop and have the owner recover it. No submissions allowed.")
        self.locked = seq < self.committed
        if not self.locked and len(self.events) > self.committed:
            # A single unacknowledged event can only be a crash between append, SQL and commit.
            event = self.events[-1]
            if seq < event["seq"]:
                self._apply(event)
            self._append({"commit": event["seq"], "hash": event["hash"]})
            self.committed = event["seq"]
        if not self.events:
            self.write({"generation": uuid.uuid4().hex}, "control_initialize", "initialize operation log")
        if not self.locked:
            for key, op in self.items("op:"):
                if op["state"] == "submitting":
                    op["state"], op["reason"] = "unknown", "Service restarted during submission; inspect evidence, never resubmit."
                    self.write({key: op}, op["action"], "restart: outcome unknown", op["id"])

    def _read_journal(self):
        self.journal.seek(0)
        events, committed, last_hash = [], 0, ""
        for raw in self.journal:
            try:
                row = json.loads(raw)
                if not raw.endswith(b"\n"):
                    raise ValueError("torn record")
                if "commit" in row:
                    if row != {"commit": committed + 1, "hash": events[-1]["hash"]}:
                        raise ValueError("invalid commit")
                    committed += 1
                else:
                    if len(events) != committed:
                        raise ValueError("uncommitted event before another event")
                    hash_value = row.pop("hash")
                    if row["seq"] != len(events) + 1 or row["previous"] != last_hash or digest(row) != hash_value:
                        raise ValueError("broken chain")
                    row["hash"] = hash_value
                    events.append(row)
                    last_hash = hash_value
            except (ValueError, KeyError, IndexError) as exc:
                raise Refused("evidence_corrupt", "Independent record is damaged; owner recovery required, no submissions.") from exc
        return events, committed

    def _append(self, value):
        self.journal.write((canonical(value) + "\n").encode())
        os.fsync(self.journal.fileno())

    def _apply(self, event):
        with self.db:
            for key, value in event["set"].items():
                self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, canonical(value)))
            self.db.execute("UPDATE head SET seq=?,hash=? WHERE id=1", (event["seq"], event["hash"]))

    def write(self, changes, action, summary, operation_id=None, restoring=False):
        if self.locked and not restoring:
            raise Refused("restore_required", "Older log detected; sudo aresos admin control restore_confirm must invalidate earlier approvals first.")
        event = {"seq": len(self.events) + 1, "previous": self.events[-1]["hash"] if self.events else "",
                 "time": time.time(), "action": action, "summary": summary, "operation_id": operation_id, "set": changes}
        event["hash"] = digest(event)
        self._append(event)
        self.checkpoint("journal_appended")
        self._apply(event)
        self.checkpoint("sqlite_committed")
        self._append({"commit": event["seq"], "hash": event["hash"]})
        self.events.append(event)
        self.committed = event["seq"]
        self.checkpoint("journal_committed")

    def get(self, key, default=None):
        row = self.db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def items(self, prefix):
        return [(k, json.loads(v)) for k, v in self.db.execute("SELECT k,v FROM kv WHERE substr(k,1,?)=? ORDER BY k", (len(prefix), prefix))]

    @property
    def generation(self):
        return self.get("generation")

    def confirm_restore(self):
        if not self.locked:
            raise Refused("refused", "No older log is awaiting confirmation.")
        if len(self.events) > self.committed:
            # A restore confirmation may itself have died before its commit marker.
            # The owner is confirming again: retain that evidence, never append over
            # an uncommitted tail and never replay app work from the older database.
            last = self.events[-1]
            self._append({"commit": last["seq"], "hash": last["hash"]})
            self.committed = last["seq"]
        latest = {}
        for event in self.events:
            latest.update({k: copy.deepcopy(v) for k, v in event["set"].items() if k.startswith("op:")})
        changes = {"generation": uuid.uuid4().hex}
        for key, known in latest.items():
            old = self.get(key)
            if old != known or old is None or old["state"] == "submitting":
                known["state"], known["reason"] = "unknown", "Restored log: independent record has newer or missing evidence. Owner must check."
                changes[key] = known
            elif old["state"] == "reserved":
                old["state"], old["reason"] = "failed", "Restore invalidated this generation's approval; nothing resumed."
                changes[key] = old
        result = {"generation": changes["generation"], "unknown": [v["id"] for k, v in changes.items() if k.startswith("op:") and v["state"] == "unknown"]}
        self.write(changes, "control_restore_confirm", "owner confirmed restore; invalidated all earlier approvals", restoring=True)
        self.locked = False
        return result

    def close(self):
        self.db.close()
        self.journal.close()
