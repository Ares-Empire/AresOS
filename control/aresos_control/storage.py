"""Full SQLite log plus a compact independently retained restore fence."""
import copy
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from . import retention
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


class JournalRecords:
    """A disk-backed sequence; compatibility reads never cache historical objects."""
    def __init__(self, store):
        self.store = store

    def __len__(self):
        return self.store.sequence

    def __getitem__(self, index):
        if index < 0:
            index += len(self)
        row = self.store.index.execute('SELECT offset FROM records WHERE seq=?', (index + 1,)).fetchone()
        if row is None:
            raise IndexError(index)
        with open(self.store.journal.name, 'rb') as stream:
            stream.seek(row[0])
            return json.loads(stream.readline())

    def __iter__(self):
        with open(self.store.journal.name, 'rb') as stream:
            for (offset,) in self.store.index.execute('SELECT offset FROM records ORDER BY seq'):
                stream.seek(offset)
                yield json.loads(stream.readline())


class Store:
    def __init__(self, state_dir, evidence_dir, checkpoint=lambda _: None):
        self.state_dir, self.evidence_dir = Path(state_dir), Path(evidence_dir)
        if self.state_dir.resolve() == self.evidence_dir.resolve() or self.evidence_dir.resolve().is_relative_to(self.state_dir.resolve()):
            raise ValueError("Independent evidence must be outside the backup tree")
        self.checkpoint = checkpoint
        self.write_failed = False
        self.recovering = False
        self.archiving = False
        for directory in (self.state_dir, self.evidence_dir):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.journal = open(self.evidence_dir / "operations.jsonl", "a+b", buffering=0)
        fcntl.flock(self.journal, fcntl.LOCK_EX | fcntl.LOCK_NB)
        sync_directory(self.evidence_dir)
        self.db = sqlite3.connect(self.state_dir / "control.sqlite")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS retained (k TEXT PRIMARY KEY, created REAL NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS head (id INTEGER PRIMARY KEY CHECK(id=1), seq INTEGER, hash TEXT);"
                              "INSERT OR IGNORE INTO head VALUES (1,0,'');"
                              "CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, value TEXT NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS operation_versions (id TEXT PRIMARY KEY, seq INTEGER NOT NULL);")
        self.db.execute('INSERT OR IGNORE INTO retained SELECT k, ? FROM kv', (time.time(),))
        self.db.commit()
        sync_directory(self.state_dir)
        # Derived, disposable index outside the backed-up state. Never trust it
        # across restarts: rebuild solely from the verified permanent journal.
        index_path = self.evidence_dir / 'journal-index.sqlite'
        index_path.unlink(missing_ok=True)
        self.index = sqlite3.connect(index_path)
        self.index.execute('PRAGMA journal_mode=OFF')
        self.index.execute('PRAGMA synchronous=OFF')
        self.index.execute('PRAGMA cache_size=-1024')
        self.index.executescript('DROP TABLE IF EXISTS records; DROP TABLE IF EXISTS latest;'
                                'CREATE TABLE records (seq INTEGER PRIMARY KEY, hash TEXT NOT NULL, offset INTEGER NOT NULL);'
                                'CREATE TABLE latest (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, value TEXT NOT NULL);')
        self.sequence, self.head_hash = 0, ''
        self.events = JournalRecords(self)
        try:
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
                        offset = self._append(record)
                        with self.index:
                            self._index_record(record, offset)
                        self._finish(event)
            if not self.events:
                self.write({"generation": uuid.uuid4().hex}, "control_initialize", "initialize operation log")
            if not self.locked:
                for key, op in self.items("op:"):
                    if op["state"] == "submitting":
                        op["state"], op["reason"] = "unknown", "Service restarted during submission; inspect evidence, never resubmit."
                        self.write({key: op}, op["action"], "restart: outcome unknown", op["id"], recovery=True)
        except BaseException:
            self.close()
            raise

    def _index_record(self, record, offset):
        self.index.execute('INSERT INTO records VALUES (?,?,?)', (record['seq'], record['hash'], offset))
        for op in record['operations']:
            self.index.execute('INSERT OR REPLACE INTO latest VALUES (?,?,?)',
                               (op['id'], record['seq'], canonical(op)))
        self.sequence, self.head_hash = record['seq'], record['hash']

    def _read_journal(self):
        self.sequence, self.head_hash = 0, ''
        committed, offset = 0, 0
        with self.index:
            self.index.execute('DELETE FROM records')
            self.index.execute('DELETE FROM latest')
            with open(self.journal.name, 'rb') as stream:
                for raw in stream:
                    try:
                        row = json.loads(raw)
                        if not raw.endswith(b"\n"):
                            raise ValueError('torn record')
                        if 'commit' in row:
                            if (self.sequence != committed + 1 or
                                    row != {'commit': self.sequence, 'hash': self.head_hash}):
                                raise ValueError('invalid commit')
                            committed = self.sequence
                        else:
                            if self.sequence != committed or row['format'] != 2:
                                raise ValueError('uncommitted event or unsupported record format')
                            hash_value = row.pop('hash')
                            if (row['seq'] != self.sequence + 1 or row['previous'] != self.head_hash
                                    or digest(row) != hash_value):
                                raise ValueError('broken chain')
                            row['hash'] = hash_value
                            self._index_record(row, offset)
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        raise Refused('evidence_corrupt', 'Independent record is damaged or has an older format; owner recovery required, no submissions.') from exc
                    offset += len(raw)
        return self.events, committed

    def _append(self, value):
        self.journal.seek(0, os.SEEK_END)
        offset = self.journal.tell()
        self.journal.write((canonical(value) + "\n").encode())
        os.fsync(self.journal.fileno())
        return offset

    def _prepared(self, seq):
        row = self.db.execute("SELECT value FROM events WHERE seq=?", (seq,)).fetchone()
        return json.loads(row[0]) if row else None

    def _apply(self, event):
        record = event["record"]
        with self.db:
            for key, value in event["set"].items():
                if value is None:
                    self.db.execute("DELETE FROM kv WHERE k=?", (key,))
                    self.db.execute("DELETE FROM retained WHERE k=?", (key,))
                else:
                    self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, canonical(value)))
                    self.db.execute("INSERT OR IGNORE INTO retained VALUES (?,?)", (key, record["time"]))
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

    def write(self, changes, action, summary, operation_id=None, restoring=False, outcome="done", untrusted_content=None, recovery=False):
        self.ensure_writable()
        if self.locked and not restoring:
            raise Refused("restore_required", "Older log detected; sudo aresos admin control restore_confirm must invalidate earlier approvals first.")
        operations = {k[3:]: v if v is not None else self.get(k)
                      for k, v in changes.items() if k.startswith("op:")}
        if operation_id and operation_id not in operations:
            operations[operation_id] = self.get("op:" + operation_id)
        operation = operations.get(operation_id)
        record = {"format": 2, "seq": self.sequence + 1,
                  "previous": self.head_hash, "time": time.time(),
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
        # Admission happens before the restore fence, so a quota refusal cannot
        # turn into journal_incomplete or demand owner restore confirmation.
        cost = len(encoded.encode()) * 3 + len(canonical(record).encode()) * 3 + 32768
        recovery = recovery or self.recovering or retention.recovery_action(action) or action == 'control_expire'
        owner_recovery = restoring or self.archiving
        cancellation = action.endswith('_operation_cancel')
        self.admit_history(cost, recovery=recovery, owner_recovery=owner_recovery, cancellation=cancellation)
        retention.disk_space(self.state_dir, cost, recovery, owner_recovery, cancellation)
        retention.disk_space(self.evidence_dir, cost, recovery, owner_recovery, cancellation)
        self.admit_changes(changes)
        # Fence the write before even its prepared event can enter a backup.
        # A crash here may need owner confirmation: compact metadata cannot
        # reconstruct the full event, and absence cannot prove no restore.
        self.write_failed = True
        offset = self._append(record)
        with self.index:
            self._index_record(record, offset)
        self.checkpoint("journal_appended")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO events VALUES (?,?)", (record["seq"], encoded))
        self.checkpoint("sqlite_prepared")
        self._finish(event)
        self.write_failed = False

    def retained_at(self, key):
        row = self.db.execute('SELECT created FROM retained WHERE k=?', (key,)).fetchone()
        return row[0] if row else time.time()

    def history_size(self):
        # The independently retained fence has a separate physical-disk budget.
        # Counting it here would make owner SQLite compaction eventually useless.
        pages = self.db.execute('PRAGMA page_count').fetchone()[0]
        page_size = self.db.execute('PRAGMA page_size').fetchone()[0]
        return pages * page_size

    def admit_history(self, reserve=retention.REQUEST_RESERVE, recovery=None, owner_recovery=False, cancellation=False):
        self.ensure_writable()
        if owner_recovery or self.archiving or cancellation:
            return
        recovery = self.recovering if recovery is None else recovery
        # Owner restore/archival has a separate, quota-exempt maintenance path.
        protected = 0 if recovery else retention.RECOVERY_RESERVE
        if self.history_size() + reserve + protected > retention.HISTORY_BYTES:
            retention.refuse('Recovery audit history' if recovery else 'Free-work audit history (recovery capacity reserved)',
                             'retained', retention.HISTORY_BYTES)

    def admit_changes(self, changes):
        groups = [(('mail:composition:',), retention.COMPOSITION_COUNT, retention.COMPOSITION_BYTES, 'Compositions'),
                  (('blob:',), retention.IMPORT_COUNT, retention.IMPORT_BYTES, 'Imported file references'),
                  (('mail:filing:', 'mail:rename:'), retention.FILING_COUNT, retention.FILING_BYTES, 'Filing intents'),
                  (('mail:filing-locations:',), retention.FILING_COUNT * 20000, retention.FILING_BYTES, 'Filing location pages'),
                  (('notice:',), retention.NOTICE_COUNT, retention.NOTICE_BYTES, 'Retained notices')]
        for prefixes, count, total, label in groups:
            additions = {k: v for k, v in changes.items() if k.startswith(prefixes)}
            if additions:
                retention.admit(self, prefixes, count, total, additions, label)

    def ensure_writable(self):
        if self.write_failed:
            raise Refused('journal_incomplete', 'A journal transaction did not finish; all writes are refused until service restart recovery has run.')

    def iter_audit(self):
        head = self.db.execute("SELECT seq FROM head WHERE id=1").fetchone()[0]
        for (value,) in self.db.execute("SELECT value FROM events WHERE seq<=? ORDER BY seq", (head,)):
            event = json.loads(value)
            record = dict(event['record'])
            claimed = record.pop('hash')
            known = self.index.execute('SELECT hash FROM records WHERE seq=?', (event['seq'],)).fetchone()
            if known == (claimed,) and digest(record) == claimed:
                yield event

    def audit(self):
        return list(self.iter_audit())

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
        changes = {"generation": uuid.uuid4().hex}
        for op_id, seq, encoded in self.index.execute('SELECT id,seq,value FROM latest ORDER BY id'):
            known = json.loads(encoded)
            key = "op:" + op_id
            old = self.get(key)
            if old is None and self.get('archived:' + op_id) == {'seq': seq}:
                continue
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
        self.index.close()
        self.journal.close()
