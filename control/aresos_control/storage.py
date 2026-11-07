"""Full SQLite log plus a compact independently retained restore fence."""
import copy
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .common import Refused, canonical, digest, json_value, visible


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def short_description(operation):
    description = operation["approval"]["description"]
    if operation.get("app") == "mail" and "untrusted_content" in description:
        return {"action": description["action"], "untrusted_content": copy.deepcopy(description["untrusted_content"])}
    result = {k: copy.deepcopy(description[k]) for k in
              ("action", "account", "to", "cc", "bcc", "subject", "title") if k in description}
    result.setdefault("action", operation["action"])
    if "targets" in description:
        result["targets"] = copy.deepcopy(description["targets"])
    if "items" in description:
        result["targets"] = [{k: copy.deepcopy(item[k]) for k in ("reference", "subject", "title") if k in item}
                             for item in description["items"]]
    if "folder" in description:
        result["targets"] = [{k: copy.deepcopy(description[k]) for k in ("folder", "uidvalidity") if k in description}]
    if "target" in description:
        result["targets"] = [copy.deepcopy(description["target"])]
    if "repair_of" in operation:
        result["targets"] = [operation["repair_of"]]
    if operation.get("app") == "mail":
        return {"action": result.pop("action"), "untrusted_content": visible(result)}
    return result


class Store:
    def __init__(self, state_dir, evidence_dir, checkpoint=lambda _: None):
        self.state_dir, self.evidence_dir = Path(state_dir), Path(evidence_dir)
        if self.state_dir.resolve() == self.evidence_dir.resolve() or self.evidence_dir.resolve().is_relative_to(self.state_dir.resolve()):
            raise ValueError("Independent evidence must be outside the backup tree")
        self.checkpoint = checkpoint
        self.write_failed = False
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
                              "INSERT OR IGNORE INTO head VALUES (1,0,'');"
                              "CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, value TEXT NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS operation_versions (id TEXT PRIMARY KEY, seq INTEGER NOT NULL);")
        self.db.commit()
        sync_directory(self.state_dir)
        self.events, self.committed = self._read_journal()
        seq, hash_value = self.db.execute("SELECT seq,hash FROM head WHERE id=1").fetchone()
        expected = self.events[seq - 1]["hash"] if 0 < seq <= len(self.events) else ""
        if seq > len(self.events) or hash_value != expected:
            raise Refused("evidence_mismatch", "The independent record is missing or different; stop and have the owner recover it. No submissions allowed.")
        self.locked = seq < self.committed
        if not self.locked:
            if len(self.events) > self.committed:
                record = self.events[-1]
                event = self._prepared(record["seq"])
                if event is None or event["record"] != record:
                    # A record-only crash and a rollback are indistinguishable.
                    # Keep even unacknowledged reservations for owner confirmation.
                    self.locked = True
                else:
                    self._finish(event)
            else:
                event = self._prepared(seq + 1)
                if event is not None:
                    record = event["record"]
                    if record["previous"] != hash_value or record["seq"] != seq + 1:
                        raise Refused("evidence_mismatch", "Prepared write does not extend the independent record; owner recovery required.")
                    self._append(record)
                    self.events.append(record)
                    self._finish(event)
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
                    if len(events) != committed or row["format"] != 2:
                        raise ValueError("uncommitted event or unsupported record format")
                    hash_value = row.pop("hash")
                    if row["seq"] != len(events) + 1 or row["previous"] != last_hash or digest(row) != hash_value:
                        raise ValueError("broken chain")
                    row["hash"] = hash_value
                    events.append(row)
                    last_hash = hash_value
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise Refused("evidence_corrupt", "Independent record is damaged or has an older format; owner recovery required, no submissions.") from exc
        return events, committed

    def _append(self, value):
        self.journal.write((canonical(value) + "\n").encode())
        os.fsync(self.journal.fileno())

    def _prepared(self, seq):
        row = self.db.execute("SELECT value FROM events WHERE seq=?", (seq,)).fetchone()
        return json.loads(row[0]) if row else None

    def _apply(self, event):
        record = event["record"]
        with self.db:
            for key, value in event["set"].items():
                self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, canonical(value)))
            for operation in record["operations"]:
                self.db.execute("INSERT OR REPLACE INTO operation_versions VALUES (?,?)", (operation["id"], record["seq"]))
            self.db.execute("UPDATE head SET seq=?,hash=? WHERE id=1", (record["seq"], record["hash"]))

    def _finish(self, event):
        self._apply(event)
        self.checkpoint("sqlite_committed")
        record = event["record"]
        self._append({"commit": record["seq"], "hash": record["hash"]})
        self.committed = record["seq"]
        self.checkpoint("journal_committed")

    def write(self, changes, action, summary, operation_id=None, restoring=False, outcome="done", untrusted_content=None):
        self.ensure_writable()
        if self.locked and not restoring:
            raise Refused("restore_required", "Older log detected; sudo aresos admin control restore_confirm must invalidate earlier approvals first.")
        operations = {v["id"]: v for k, v in changes.items() if k.startswith("op:")}
        if operation_id and operation_id not in operations:
            operations[operation_id] = self.get("op:" + operation_id)
        operation = operations.get(operation_id)
        record = {"format": 2, "seq": len(self.events) + 1,
                  "previous": self.events[-1]["hash"] if self.events else "", "time": time.time(),
                  "generation": changes.get("generation", self.generation),
                  "operations": [{"id": op["id"], "generation": op["generation"], "input_hash": op["input_hash"],
                                  "description": short_description(op), "state": op["state"]} for op in operations.values()]}
        record["hash"] = digest(record)
        event = {"seq": record["seq"], "time": record["time"], "action": action, "summary": summary,
                 "outcome": operation["state"] if operation else outcome, "operation_id": operation_id,
                 "set": changes, "record": record}
        if untrusted_content is not None:
            json_value(untrusted_content)
            event["untrusted_content"] = visible(untrusted_content)
        # Validate and serialize the COMPLETE event before the independent fence.
        encoded = canonical(json_value(event))
        # Fence the write before even its prepared event can enter a backup.
        # A crash here may need owner confirmation: compact metadata cannot
        # reconstruct the full event, and absence cannot prove no restore.
        self.write_failed = True
        self._append(record)
        self.events.append(record)
        self.checkpoint("journal_appended")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO events VALUES (?,?)", (record["seq"], encoded))
        self.checkpoint("sqlite_prepared")
        self._finish(event)
        self.write_failed = False

    def ensure_writable(self):
        if self.write_failed:
            raise Refused('journal_incomplete', 'A journal transaction did not finish; all writes are refused until service restart recovery has run.')

    def audit(self):
        head = self.db.execute("SELECT seq FROM head WHERE id=1").fetchone()[0]
        return [event for (value,) in self.db.execute("SELECT value FROM events WHERE seq<=? ORDER BY seq", (head,))
                if (event := json.loads(value))["record"] == self.events[event["seq"] - 1]]

    def get(self, key, default=None):
        row = self.db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def items(self, prefix):
        return [(k, json.loads(v)) for k, v in self.db.execute("SELECT k,v FROM kv WHERE substr(k,1,?)=? ORDER BY k", (len(prefix), prefix))]

    @property
    def generation(self):
        return self.get("generation")

    def confirm_restore(self):
        self.ensure_writable()
        if not self.locked:
            raise Refused("refused", "No older log is awaiting confirmation.")
        if len(self.events) > self.committed:
            last = self.events[-1]
            self._append({"commit": last["seq"], "hash": last["hash"]})
            self.committed = last["seq"]
        latest = {}
        for event in self.events:
            for op in event["operations"]:
                latest[op["id"]] = (op, event["seq"])
        changes = {"generation": uuid.uuid4().hex}
        for op_id, (known, seq) in latest.items():
            key = "op:" + op_id
            old = self.get(key)
            version = self.db.execute("SELECT seq FROM operation_versions WHERE id=?", (op_id,)).fetchone()
            if old is None or version != (seq,) or old["state"] == "submitting":
                if old is None:
                    description = copy.deepcopy(known["description"])
                    if known["description"]["action"].startswith("mail_"):
                        # Keep the historical operation-status shape while its
                        # compact audit record retains the untrusted marking.
                        description.update(description.get("untrusted_content", {}))
                    old = {"id": op_id, "generation": known["generation"], "input_hash": known["input_hash"],
                           "app": known["description"]["action"].split("_", 1)[0], "action": known["description"]["action"],
                           "approval": {"operation_id": op_id, "description": description},
                           "payload": {}, "expires": 0, "stages": {}}
                old.update(state="unknown", reason="Restored log: independent record has newer or missing evidence. Owner must check.")
                changes[key] = old
            elif old["state"] == "reserved":
                old.update(state="failed", reason="Restore invalidated this generation's approval; nothing resumed.")
                changes[key] = old
        result = {"generation": changes["generation"], "unknown": [v["id"] for k, v in changes.items() if k.startswith("op:") and v["state"] == "unknown"]}
        self.write(changes, "control_restore_confirm", "owner confirmed restore; invalidated all earlier approvals", restoring=True)
        self.locked = False
        return result

    def close(self):
        self.db.close()
        self.journal.close()
