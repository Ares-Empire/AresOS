"""Full SQLite log plus a compact independently retained restore fence."""
import copy
import errno
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from . import retention
from .common import Refused, canonical, storage_stream, cleanup, digest, json_value, visible, storage_refusal
from .results import Observations, recorded_write
from .space import SpaceLedger, record_budget
from .owner_projection import OwnerProjection

RESTORE_BATCH_BYTES = 64 * 1024
RESTORE_BATCH_COUNT = 32
CHECK_RESULT_BYTES = retention.FILING_RESERVE


def replay_budget(event):
    # The fence and prepared row already exist. Only SQLite application and
    # the short commit marker remain, within the original write's admission.
    return len(canonical(event).encode()) * 2 + 8192


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        with cleanup('directory descriptor close'):
            os.close(fd)


def short_description(operation):
    description = operation["approval"]["description"]
    if operation.get("app") == "mail" and "untrusted_content" in description:
        result = {"action": description["action"], "untrusted_content": copy.deepcopy(description["untrusted_content"])}
        if operation.get('repair_of'):
            result['repair'] = {'repair_of': operation['repair_of'],
                                'stage': operation.get('payload', {}).get('stage'),
                                'attempt_ended_at': operation.get('attempt_ended_at')}
        return result
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
        result = {"action": result.pop("action"), "untrusted_content": visible(result)}
        if operation.get('repair_of'):
            # System identity is permanent even when the full working log is
            # rolled back. It is separate from escaped mail/user content.
            result['repair'] = {'repair_of': operation['repair_of'],
                                'stage': operation.get('payload', {}).get('stage'),
                                'attempt_ended_at': operation.get('attempt_ended_at')}
        return result
    return result


def missing_operation(known):
    description = copy.deepcopy(known['description'])
    action = description['action']
    if action.startswith('mail_'):
        description.update(description.get('untrusted_content', {}))
    op = {'id': known['id'], 'generation': known['generation'], 'input_hash': known['input_hash'],
          'app': action.split('_', 1)[0], 'action': action,
          'approval': {'operation_id': known['id'], 'description': description},
          'payload': {}, 'expires': 0, 'stages': {}, 'state': 'unknown',
          'reason': 'Restored log: independent record has newer or missing evidence. Owner must check.'}
    if action == 'mail_operation_repair':
        identity = description.get('repair', {})
        # Older compact evidence retained the original ID as a target, but
        # omitted the stage. Keep that relationship and block both stages.
        targets = description.get('targets', [])
        original = identity.get('repair_of') or description.get('repair_of')
        if not original and len(targets) == 1 and isinstance(targets[0], str):
            original = targets[0]
        stage = identity.get('stage')
        if identity.get('attempt_ended_at') is not None:
            op['attempt_ended_at'] = identity['attempt_ended_at']
        op['repair_of'] = original
        if original and stage in {'sent_copy', 'answered_flag'}:
            op['payload'] = {'operation_id': original, 'stage': stage}
        else:
            op['repair_identity_missing'] = True
    return op


class JournalRecords:
    """A disk-backed sequence; compatibility reads never cache historical objects."""
    def __init__(self, store):
        self.store = store

    def __len__(self):
        return self.store.sequence

    def __getitem__(self, index):
        if index < 0:
            index += len(self)
        if self.store.index is None:
            for record in self:
                if record['seq'] == index + 1:
                    return record
            raise IndexError(index)
        row = self.store.index.execute('SELECT offset FROM records WHERE seq=?', (index + 1,)).fetchone()
        if row is None:
            raise IndexError(index)
        with storage_stream(open(self.store.journal.name, 'rb')) as stream:
            stream.seek(row[0])
            return json.loads(stream.readline())

    def __iter__(self):
        with storage_stream(open(self.store.journal.name, 'rb')) as stream:
            for raw in stream:
                record = json.loads(raw)
                if 'commit' not in record:
                    yield record


class Store:
    def __init__(self, state_dir, evidence_dir, checkpoint=lambda _: None):
        self.db = self.index = self.journal = self.owner_projection = None
        try:
            self._initialize(state_dir, evidence_dir, checkpoint)
        except BaseException as exc:
            with cleanup('store initialization', exc):
                self.close()
            raise

    def _initialize(self, state_dir, evidence_dir, checkpoint):
        self.state_dir, self.evidence_dir = Path(state_dir), Path(evidence_dir)
        if self.state_dir.resolve() == self.evidence_dir.resolve() or self.evidence_dir.resolve().is_relative_to(self.state_dir.resolve()):
            raise ValueError("Independent evidence must be outside the backup tree")
        self.checkpoint = checkpoint
        self.write_failed = False
        self.storage_cause = None
        self.deferred_notices = {}
        self.active_intents = {}
        self.flushing_notices = False
        self.observations = Observations()
        self.observation_snapshot = None
        self.recovering = False
        self.archiving = False
        self.index = None
        self.ledger = SpaceLedger((self.state_dir, self.evidence_dir), self.history_size)
        if not (self.state_dir / 'control.sqlite').exists() or not (self.evidence_dir / 'operations.jsonl').exists():
            self.ledger.admit(128 * 1024)
        for directory in (self.state_dir, self.evidence_dir):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.journal = open(self.evidence_dir / "operations.jsonl", "a+b", buffering=0)
        fcntl.flock(self.journal, fcntl.LOCK_EX | fcntl.LOCK_NB)
        sync_directory(self.evidence_dir)
        self.db = sqlite3.connect(self.state_dir / "control.sqlite")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("PRAGMA synchronous=FULL")
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='operation_versions'").fetchone():
            self.ledger.admit(128 * 1024)
            self.db.executescript("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS retained (k TEXT PRIMARY KEY, created REAL NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS head (id INTEGER PRIMARY KEY CHECK(id=1), seq INTEGER, hash TEXT);"
                              "INSERT OR IGNORE INTO head VALUES (1,0,'');"
                              "CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, value TEXT NOT NULL);"
                              "CREATE TABLE IF NOT EXISTS operation_versions (id TEXT PRIMARY KEY, seq INTEGER NOT NULL);")
        sync_directory(self.state_dir)
        # Derived, disposable index outside the backed-up state. Never trust it
        # across restarts: rebuild solely from the verified permanent journal.
        index_path = self.evidence_dir / 'journal-index.sqlite'
        index_path.unlink(missing_ok=True)
        self.sequence, self.head_hash = 0, ''
        self.events = JournalRecords(self)
        try:
            self.events, self.committed = self._read_journal()
            self.owner_projection = OwnerProjection(self)
            self.owner_projection.seed()
            seq, hash_value = self.db.execute("SELECT seq,hash FROM head WHERE id=1").fetchone()
            expected = self.events[seq - 1]["hash"] if 0 < seq <= len(self.events) else ""
            if seq > len(self.events) or hash_value != expected:
                raise Refused("evidence_mismatch", "The independent record is missing or different; stop and have the owner recover it. No submissions allowed.")
            self.restore_head = seq
            self.restore_unprepared = {self.events[-1]['seq']} if len(self.events) > self.committed and self._prepared(self.events[-1]['seq']) is None else set()
            self.locked = seq < self.committed or bool(self.get('restore_pending'))
            if len(self.events) > self.committed:
                last = self.events[-1]
                prepared = self._prepared(last['seq'])
                self.locked = self.locked or prepared is None or prepared['record'] != last
            self._load_reservations()
            from .recovery import recover_intents
            recover_intents(self, persist=False)
            # Optional retention metadata is migrated only after all recovery
            # rights have been loaded. A full disk may defer this bookkeeping;
            # retained_at then conservatively treats an untracked row as new.
            missing = self.db.execute('SELECT count(*) FROM kv WHERE k NOT IN (SELECT k FROM retained)').fetchone()[0]
            if missing:
                try:
                    self.ledger.admit(missing * 1024 + 32768)
                except Refused as exc:
                    if exc.code != 'storage_limit':
                        raise
                else:
                    self.db.execute('INSERT OR IGNORE INTO retained SELECT k, ? FROM kv', (time.time(),))
                    self.db.commit()
            self.index_refusal = None
            try:
                self.require_index()
            except Refused as exc:
                if exc.code != 'storage_limit':
                    raise
            prepared = self._pending_event()
            if prepared and prepared.get('space', {}).get('restoring'):
                # Owner confirmation was already prepared, even if an earlier
                # batch deliberately kept restore_pending set across a crash.
                self._replay(prepared)
                self.locked = bool(self.get('restore_pending'))
            elif not self.locked:
                if len(self.events) > self.committed:
                    record = self.events[-1]
                    event = self._prepared(record["seq"])
                    if event is None or event["record"] != record:
                        # A record-only crash and a rollback are indistinguishable.
                        # Keep even unacknowledged reservations for owner confirmation.
                        self.locked = True
                    else:
                        self._replay(event)
                else:
                    event = self._prepared(seq + 1)
                    if event is not None:
                        record = event["record"]
                        if record["previous"] != hash_value or record["seq"] != seq + 1:
                            raise Refused("evidence_mismatch", "Prepared write does not extend the independent record; owner recovery required.")
                        self._replay(event, append=True)
            self._load_reservations()
            if not self.events:
                self.write({"generation": uuid.uuid4().hex}, "control_initialize", "initialize operation log")
            if not self.locked:
                for key, op in self.iter_items("op:"):
                    if op["state"] == "submitting":
                        op["state"], op["reason"] = "unknown", "Service restarted during submission; inspect evidence, never resubmit."
                        if op.get('repair_of'):
                            op['attempt_ended_at'] = time.time()
                        if op.get('sent_append_started_at'):
                            op['sent_append_ended_at'] = time.time()
                        try:
                            self.write({key: op}, op["action"], "restart: outcome unknown", op["id"], recovery=True)
                        except Refused as exc:
                            if exc.code != 'storage_limit':
                                raise
                            # Submitting is already nonrepeatable. Keep status and
                            # cancellation available if this annotation cannot fit.
            from .recovery import recover_intents
            recover_intents(self)
        except BaseException as exc:
            with cleanup('index rebuild', exc):
                self.close()
            raise

    def _index_record(self, record, offset):
        if self.index is not None:
            self.index.execute('INSERT INTO records VALUES (?,?,?)', (record['seq'], record['hash'], offset))
            for op in record['operations']:
                self.index.execute('INSERT OR REPLACE INTO latest VALUES (?,?,?)',
                                   (op['id'], record['seq'], canonical(op)))
            self.index.commit()
        self.sequence, self.head_hash = record['seq'], record['hash']

    def _read_journal(self, indexing=False):
        self.sequence, self.head_hash = 0, ''
        committed, offset = 0, 0
        if indexing:
            self.index.execute('DELETE FROM records')
            self.index.execute('DELETE FROM latest')
        with storage_stream(open(self.journal.name, 'rb')) as stream:
            for raw in stream:
                if not raw.endswith(b'\n'):
                    try:
                        tail = json.loads(raw)
                    except (ValueError, UnicodeError):
                        tail = None
                    if isinstance(tail, dict) and 'commit' in tail:
                        # A complete commit marker with damaged framing is
                        # corruption, rather than an interrupted uncommitted
                        # tail. Keep the existing committed-record rejection.
                        raise Refused('evidence_corrupt', 'Independent commit record framing is damaged; owner recovery required, no submissions.')
                    # A torn final write was never acknowledged. Preserve every
                    # complete fence, including one needing prepared replay or
                    # owner restore; only discard the incomplete line itself.
                    self._truncate_journal(offset)
                    break
                try:
                    row = json.loads(raw)
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
                        if indexing:
                            self._index_record(row, offset)
                        else:
                            self.sequence, self.head_hash = row['seq'], row['hash']
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise Refused('evidence_corrupt', 'Independent record is damaged or has an older format; owner recovery required, no submissions.') from exc
                offset += len(raw)
        return self.events, committed

    def iter_latest(self, through=None):
        """Bounded streaming fallback when even a disposable index is too costly.

        Keep the next 32 IDs in sort order, rescan for the next window. It is
        slower than an index but needs neither writable disk nor history RAM.
        """
        if self.index is not None:
            through = self.sequence if through is None else through
            for op_id, seq, encoded in self.index.execute('SELECT id,seq,value FROM latest WHERE seq<=? ORDER BY id', (through,)):
                yield op_id, seq, json.loads(encoded)
            return
        cursor = ''
        through = self.sequence if through is None else through
        while True:
            batch = {}
            for record in self.events:
                if record['seq'] > through:
                    break
                for op in record['operations']:
                    op_id = op['id']
                    if op_id <= cursor:
                        continue
                    if op_id not in batch and len(batch) == 32:
                        largest = max(batch)
                        if op_id > largest:
                            continue
                        del batch[largest]
                    batch[op_id] = (record['seq'], op)
            if not batch:
                return
            for op_id in sorted(batch):
                yield op_id, *batch[op_id]
            cursor = max(batch)

    def _load_reservations(self):
        self.ledger.holds.clear()
        from .exports import budget as export_budget
        for key, transfer in self.iter_items('export:'):
            self.ledger.holds[key] = export_budget(transfer)
        for _, op in self.iter_items('op:'):
            self.ledger.holds.update(self.ledger.right(op, self.get('op:' + (op.get('repair_of') or ''))))
        if self.sequence > self.committed and not self.locked:
            prepared = self._prepared(self.sequence)
            if prepared is not None:
                # A pending prepared approval already owns its cancellation
                # right, even before replay publishes it in kv.
                for key, op in prepared['set'].items():
                    if key.startswith('op:') and op is not None:
                        self.ledger.holds.update(self.ledger.right(op, self.get('op:' + (op.get('repair_of') or ''))))
        if self.locked:
            budget = 256 * 1024
            for restored in self._restore_operations():
                budget += record_budget(restored)
                self.ledger.holds.update(self.ledger.right(restored, self.get('op:' + (restored.get('repair_of') or ''))))
            for _, changes in self.owner_projection.retired(full=True):
                budget += record_budget(changes)
            for key,value in self.owner_projection.iter_items():
                if key.startswith(('intent:', 'notice:', 'mail:filing:', 'mail:rename:', 'mail:account:')) and not self.owner_projection.same(key, self.get(key), value):
                    budget += record_budget(value)
            self.ledger.holds['restore'] = budget
        for prefix in ('op:', 'intent:', 'mail:filing:', 'mail:rename:'):
            for key, value in self.iter_items(prefix):
                if (value.get('check_open') or value.get('sent_copy_check', {}).get('state') == 'open' or
                        prefix in {'mail:filing:', 'mail:rename:'} and value.get('state') == 'started'):
                    self.ledger.holds['check:' + key] = CHECK_RESULT_BYTES
        prepared = self._pending_event()
        if prepared is not None:
            plan = prepared.get('space')
            if plan:
                # Reconstruct the already-admitted transaction, replacing its
                # spent cancel/settlement/restore bytes with just replay work.
                self.ledger.finish(plan['updates'], plan['consume'])
                self.ledger.holds['replay'] = replay_budget(prepared)

    def _pending_event(self):
        seq = self.sequence if self.sequence > self.committed else self.sequence + 1
        event = self._prepared(seq)
        if event is None:
            return None
        record = event['record']
        if seq == self.sequence:
            return event if record == self.events[-1] else None
        if record['seq'] == seq and record['previous'] == self.head_hash:
            return event
        return None

    def _replay(self, event, append=False):
        if event.get('space'):
            self.ledger.admit(replay_budget(event), consume=('replay',))
        else:
            # Pre-upgrade prepared events lack a saved plan. Their live right
            # can still fund completion rather than being counted twice.
            consume = []
            for op in event['set'].values():
                if isinstance(op, dict) and 'id' in op and op.get('state') in {'done', 'failed'}:
                    consume.extend(key for key in ('cancel:' + op['id'], 'settle:' + op['id'])
                                   if key in self.ledger.holds)
            self.ledger.admit(replay_budget(event), consume=consume)
        if append:
            offset = self._append(event['record'])
            self._index_record(event['record'], offset)
        self._finish(event)
        self.write_failed = False
        self.ledger.finish({}, ('replay',))

    def _restore_operations(self, through=None):
        # Admission and confirmation must enumerate exactly the same work.
        # Unchanged closed history costs no reconstruction space.
        for op_id, seq, known in self.iter_latest(through):
            if any('archived:' + op_id in changes for _, changes in self.owner_projection.retired()):
                continue
            old = self.get('op:' + op_id)
            if old is None and self.get('archived:' + op_id) == {'seq': seq}:
                continue
            version = self.db.execute('SELECT seq FROM operation_versions WHERE id=?', (op_id,)).fetchone()
            if old is None or version != (seq,) or old['state'] == 'submitting':
                if old is None:
                    old = missing_operation(known)
                old.update(state='unknown', reason='Restored log: independent record has newer or missing evidence. Owner must check.')
            elif old['state'] == 'reserved':
                old.update(state='failed', reason="Restore invalidated this generation's approval; nothing resumed.")
            else:
                continue
            yield old

    def require_index(self):
        # An admission refusal is only a diagnostic. Reconstruct disposable
        # state through this same path on startup and the next write attempt.
        if self.index is not None:
            return
        self.ensure_writable()
        try:
            self.ledger.admit(os.fstat(self.journal.fileno()).st_size * 3 + 256 * 1024)
            path = self.evidence_dir / 'journal-index.sqlite'
            path.unlink(missing_ok=True)
            index = sqlite3.connect(path)
            sequence, head_hash = self.sequence, self.head_hash
            try:
                index.execute('PRAGMA journal_mode=OFF')
                index.execute('PRAGMA synchronous=OFF')
                index.execute('PRAGMA cache_size=-1024')
                index.executescript('CREATE TABLE records (seq INTEGER PRIMARY KEY, hash TEXT NOT NULL, offset INTEGER NOT NULL);'
                                    'CREATE TABLE latest (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, value TEXT NOT NULL);')
                self.index = index
                self._read_journal(indexing=True)
            except BaseException as exc:
                self.index = None
                self.sequence, self.head_hash = sequence, head_hash
                with cleanup('index retry close', exc):
                    index.close()
                raise
        except Refused as exc:
            self.index_refusal = 'Journal index build refused by the storage ledger. ' + str(exc)
            raise Refused(exc.code, self.index_refusal) from exc
        self.index_refusal = None


    def _append(self, value):
        self.journal.seek(0, os.SEEK_END)
        offset = self.journal.tell()
        data = (canonical(value) + "\n").encode()
        try:
            # A short unbuffered write is a failed transaction, even if the
            # next write might fit. Never acknowledge a partial fence/marker.
            if self.journal.write(data) != len(data):
                raise OSError(errno.ENOSPC, 'Short journal write')
            os.fsync(self.journal.fileno())
        except OSError as exc:
            self.observations.storage(exc, generic=True)
            self.write_failed = True
            with cleanup('journal truncation', exc):
                self._truncate_journal(offset)
                if 'operations' in value and value['seq'] == self.sequence + 1:
                    self.write_failed = False
                    self.owner_projection._recover_tail()
            raise storage_refusal(exc) or Refused('storage_error', 'Journal storage write failed; restart the service and check the recorded operation.') from exc
        return offset

    def _truncate_journal(self, offset):
        self.journal.truncate(offset)
        os.fsync(self.journal.fileno())

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

    @recorded_write
    def write(self, changes, action, summary, operation_id=None, restoring=False, outcome="done", untrusted_content=None, recovery=False, intent_context=None, intent_arguments=None):
        # Stage/outcome writers may hold an earlier object. Preserve additive
        # mutation context while keeping the exact older versions in history.
        if not restoring:
            changes = dict(changes)
            for key, value in changes.items():
                if isinstance(value, dict) and key.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:')):
                    previous = self.get(key) or {}
                    for field in ('context', 'context_version'):
                        if field not in value and field in previous:
                            value = {**value, field: previous[field]}
                    changes[key] = value
        if any(key.startswith(('mail:filing:', 'mail:rename:')) for key in changes):
            self._open_filings = None
        self.ensure_writable()
        cancellation = action.endswith('_operation_cancel')
        if not (restoring or self.archiving or cancellation or recovery or self.recovering):
            self.require_index()
        if self.locked and not restoring:
            raise Refused("restore_required", "Older log detected; sudo aresos admin control restore_confirm must invalidate earlier approvals first.")
        # Every free change needs a durable completion marker too. Explicit
        # operations, filing, exports and onboarding already carry an identity.
        # This covers APPEND/draft, flags, folder creation, settings and future
        # adapters using started/done, in the same admitted transaction.
        intent_key = self.active_intents.get(action)
        explicit = operation_id or any(k.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:',
                                                     'export:', 'mail:account:')) for k in changes)
        tracked_intent = (not explicit or intent_context is not None) and (outcome == 'started' or intent_key is not None)
        if tracked_intent:
            changes = dict(changes)
            if outcome == 'started':
                # A later successful call must not close an earlier interrupted
                # attempt of the same action. Only this live call owns its key.
                intent_key = 'intent:' + uuid.uuid4().hex
                changes[intent_key] = {'id': 'recovery-' + intent_key[7:], 'action': action,
                    'app': action.split('_', 1)[0], 'state': 'started', 'context_version': 1}
                if intent_context is not None:
                    changes[intent_key]['context'] = copy.deepcopy(intent_context)
                if intent_arguments is not None:
                    changes[intent_key]['arguments'] = copy.deepcopy(intent_arguments)
            elif outcome in {'done', 'partial', 'refused'}:
                changes[intent_key] = None
            else:
                changes[intent_key] = self.get(intent_key)
        operations = {k[3:]: v if v is not None else self.get(k)
                      for k, v in changes.items() if k.startswith("op:")}
        if operation_id and operation_id not in operations:
            operations[operation_id] = self.get("op:" + operation_id)
        operation = operations.get(operation_id)
        updates, consume = {}, []
        from .exports import budget as export_budget
        for key, transfer in changes.items():
            if key.startswith('export:'):
                updates[key] = export_budget(transfer) if transfer is not None else 0
                if transfer is None and key in self.ledger.holds:
                    consume.append(key)
        # A warning-producing read owns its result space before the remote
        # evidence is requested. A failed result leaves this right and source.
        for key, value in changes.items():
            if not key.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:')):
                continue
            held_key = 'check:' + key
            opened = isinstance(value, dict) and (value.get('check_open') or
                value.get('sent_copy_check', {}).get('state') == 'open' or
                key.startswith(('mail:filing:', 'mail:rename:')) and value.get('state') == 'started')
            if opened and held_key not in self.ledger.holds:
                updates[held_key] = CHECK_RESULT_BYTES
            elif not opened and held_key in self.ledger.holds:
                updates[held_key] = 0
                consume.append(held_key)
        compact = []
        for op in operations.values():
            rights = self.ledger.right(op, self.get('op:' + (op.get('repair_of') or '')))
            for prefix in ('cancel:', 'settle:'):
                key = prefix + op['id']
                if key in self.ledger.holds and key not in rights:
                    updates[key] = 0
                    if cancellation or recovery or op['state'] in {'done', 'failed'}:
                        consume.append(key)
            updates.update(rights)
            compact.append({"id": op["id"], "generation": op["generation"], "input_hash": op["input_hash"],
                            "description": short_description(op), "state": op["state"]})
        record = {"format": 2, "seq": self.sequence + 1,
                  "previous": self.head_hash, "time": time.time(),
                  "generation": changes.get("generation", self.generation),
                  "operations": compact}
        record["hash"] = digest(record)
        if restoring and len(canonical(record).encode()) > RESTORE_BATCH_BYTES:
            raise Refused('storage_limit', 'One restore evidence record exceeds the bounded confirmation batch; ask the owner to inspect it.')
        event = {"seq": record["seq"], "time": record["time"], "action": action, "summary": summary,
                 "outcome": operation["state"] if operation else outcome, "operation_id": operation_id,
                 "set": changes, "record": record}
        if restoring:
            event['restore_range'] = [self.restore_head + 1, self.committed]
        if untrusted_content is not None:
            json_value(untrusted_content)
            event["untrusted_content"] = visible(untrusted_content)
        event['restoring'] = restoring
        owner_data = self.owner_projection.changes(event)
        event.pop('restoring')
        if owner_data:
            record['owner'] = self.owner_projection.publication_hash(owner_data)
            record['hash'] = digest({k: v for k, v in record.items() if k != 'hash'})
        # Validate and serialize the COMPLETE event before the independent fence.
        event['space'] = {'updates': updates, 'consume': consume, 'restoring': restoring}
        encoded = canonical(json_value(event))
        # Admission happens before the restore fence, so a quota refusal cannot
        # turn into journal_incomplete or demand owner restore confirmation.
        # Leave room for the restore balance added to the saved plan below.
        cost = len(encoded.encode()) * 5 + len(canonical(record).encode()) * 3 + 36864
        recovery = recovery or self.recovering or retention.recovery_action(action) or action == 'control_expire'
        owner_recovery = restoring or self.archiving
        if restoring:
            # Batches spend the confirmation right, retaining its unspent part.
            remaining = self.ledger.holds.get('restore', 0) - cost
            if remaining < 0:
                raise Refused('storage_limit', 'Restore confirmation exceeds its held reservation; free storage before confirming.')
            updates['restore'] = remaining
            consume = []
            event['space'] = {'updates': updates, 'consume': consume, 'restoring': True}
            encoded = canonical(json_value(event))
        self.ledger.admit(cost, updates=updates, consume=consume, history_cost=cost,
                          recovery=recovery, owner_recovery=owner_recovery, cancellation=cancellation)
        self.admit_changes(changes)
        # Fence the write before even its prepared event can enter a backup.
        # A crash here may need owner confirmation: compact metadata cannot
        # reconstruct the full event, and absence cannot prove no restore.
        self.owner_projection.prepare(event, owner_data)
        self.write_failed = True
        offset = self._append(record)
        self._index_record(record, offset)
        self.checkpoint("journal_appended")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO events VALUES (?,?)", (record["seq"], encoded))
        self.checkpoint("sqlite_prepared")
        self._finish(event)
        self.write_failed = False
        self.ledger.finish(updates, consume)
        if tracked_intent:
            if outcome == 'started':
                self.active_intents[action] = intent_key
            else:
                self.active_intents.pop(action, None)

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
        self.ledger.admit(0, history_cost=reserve, recovery=self.recovering if recovery is None else recovery,
                          owner_recovery=owner_recovery or self.archiving, cancellation=cancellation)

    def admit_changes(self, changes):
        groups = [(('intent:',), retention.FILING_COUNT, retention.FILING_BYTES, 'Unfinished changes'),
                  (('mail:composition:',), retention.COMPOSITION_COUNT, retention.COMPOSITION_BYTES, 'Compositions'),
                  (('blob:',), retention.IMPORT_COUNT, retention.IMPORT_BYTES, 'Imported file references'),
                  (('mail:filing:', 'mail:rename:'), retention.FILING_COUNT, retention.FILING_BYTES, 'Filing intents'),
                  (('mail:filing-locations:',), retention.FILING_COUNT * 20000, retention.FILING_BYTES, 'Filing location pages'),
                  (('notice:',), retention.NOTICE_COUNT, retention.NOTICE_BYTES, 'Retained notices')]
        for prefixes, count, total, label in groups:
            additions = {k: v for k, v in changes.items() if k.startswith(prefixes)}
            if additions:
                retention.admit(self, prefixes, count, total, additions, label)

    def ensure_writable(self):
        if not self.write_failed:
            # The only persistent refusal is a transaction that may have begun.
            # Ledger/quota checks and optional derived-state admission run anew.
            self.storage_cause = None
        if self.write_failed:
            raise Refused('journal_incomplete', 'A journal transaction did not finish; all writes are refused until service restart recovery has run.')

    def remember_storage(self, exc):
        error = self.observations.error or storage_refusal(exc)
        if error is not None and self.storage_cause is None:
            self.storage_cause = error

    def defer_notice(self, notice_id, changes, action, summary):
        self.deferred_notices[notice_id] = (copy.deepcopy(changes), action, summary)

    def flush_notices(self):
        if self.locked:
            return
        self.flushing_notices = True
        try:
            for notice_id, (changes, action, summary) in list(self.deferred_notices.items()):
                self.write(changes, action, summary, recovery=True)
                del self.deferred_notices[notice_id]
        finally:
            self.flushing_notices = False

    def iter_audit(self):
        head = self.db.execute("SELECT seq FROM head WHERE id=1").fetchone()[0]
        records = iter(self.events) if self.index is None else None
        verified = None
        for (value,) in self.db.execute("SELECT value FROM events WHERE seq<=? ORDER BY seq", (head,)):
            event = json.loads(value)
            record = dict(event['record'])
            claimed = record.pop('hash')
            if self.index is not None:
                known = self.index.execute('SELECT hash FROM records WHERE seq=?', (event['seq'],)).fetchone()
            else:
                # Collate the two ordered streams once. Startup recovery must
                # not rescan the entire journal for every legacy audit row.
                while verified is None or verified['seq'] < event['seq']:
                    verified = next(records)
                known = (verified['hash'],) if verified['seq'] == event['seq'] else None
            if known == (claimed,) and digest(record) == claimed:
                yield event

    def audit(self):
        return list(self.iter_audit())

    def get(self, key, default=None):
        row = self.db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def iter_items(self, prefix):
        for k, v in self.db.execute("SELECT k,v FROM kv WHERE substr(k,1,?)=? ORDER BY k", (len(prefix), prefix)):
            yield k, json.loads(v)

    def items(self, prefix):
        return list(self.iter_items(prefix))

    @property
    def generation(self):
        from .owner_state import owner_view
        return owner_view(self).get("generation")

    def confirm_restore(self):
        self.ensure_writable()
        if not self.locked:
            raise Refused("refused", "No older log is awaiting confirmation.")
        if len(self.events) > self.committed:
            last = self.events[-1]
            self.ledger.admit(4096, updates={'restore': self.ledger.holds['restore'] - 4096})
            self._append({"commit": last["seq"], "hash": last["hash"]})
            self.ledger.holds['restore'] -= 4096
            self.committed = last["seq"]
        # Keep the lock durable across every batch and crash. Only the final
        # marker advances generation; nothing is resumed in an intermediate DB.
        through = self.sequence
        changes = {}
        batch_bytes = 0
        # A backup cannot undo a confirmed retirement or acknowledgement.
        # Re-read the export through its tombstone before using these rows.
        for _, retired in self.owner_projection.retired(full=True):
            for key, value in retired.items():
                if self.get(key) == value:
                    continue
                amount = len(canonical(value).encode()) + 1024
                if changes and (len(changes) >= RESTORE_BATCH_COUNT or batch_bytes + amount > RESTORE_BATCH_BYTES):
                    changes['restore_pending'] = True
                    self.write(changes, 'control_restore_confirm', 'bounded archive reconciliation batch', restoring=True)
                    changes, batch_bytes = {}, 0
                changes[key] = value
                batch_bytes += amount
        from .owner_state import owner_view
        view = owner_view(self)
        abort_sources = {key for seq,data,_,_ in self.owner_projection._records(self.owner_projection.path)
                         if seq in self.restore_unprepared for key,row in data.items()
                         if key.startswith(('intent:', 'mail:filing:', 'mail:rename:')) and
                         isinstance(row['facts'], dict) and row['facts'].get('state') == 'started'}
        for key, value in self.owner_projection.iter_items():
            if not key.startswith(('intent:', 'notice:', 'mail:filing:', 'mail:rename:', 'mail:account:')):
                continue
            old = self.get(key)
            if old is not None and self.owner_projection.same(key, old, value):
                continue
            value = None if key in abort_sources else view.inflate(key, value)
            amount = len(canonical(value).encode()) + 1024
            if changes and (len(changes) >= RESTORE_BATCH_COUNT or batch_bytes + amount > RESTORE_BATCH_BYTES):
                changes['restore_pending'] = True
                self.write(changes, 'control_restore_confirm', 'bounded owner-state reconciliation batch', restoring=True)
                changes, batch_bytes = {}, 0
            changes[key] = value
            batch_bytes += amount
        for old in self._restore_operations(through):
            key = 'op:' + old['id']
            amount = len(canonical(old).encode()) + len(canonical(short_description(old)).encode()) + 1024
            if changes and (len(changes) >= RESTORE_BATCH_COUNT or batch_bytes + amount > RESTORE_BATCH_BYTES):
                changes['restore_pending'] = True
                self.write(changes, 'control_restore_confirm', 'bounded restore evidence batch', restoring=True)
                changes, batch_bytes = {}, 0
            changes[key] = old
            batch_bytes += amount
        generation = uuid.uuid4().hex
        changes.update(generation=generation, restore_pending=None)
        self.write(changes, 'control_restore_confirm',
                   'owner confirmed restore; invalidated all earlier approvals', restoring=True)
        self.locked = False
        self.ledger.holds.pop('restore', None)
        from .recovery import recover_intents
        recover_intents(self, persist=False)
        # A large recovery must not complete and then return result_too_large.
        # Every operation remains available through the existing pending pages.
        result = {'generation': generation, 'unknown': []}
        count = 0
        for _, op in self.iter_items('op:'):
            if op['state'] == 'unknown':
                count += 1
                if len(result['unknown']) < 100:
                    result['unknown'].append(op['id'])
        if count > len(result['unknown']):
            result['unknown_more'] = {'count': count - len(result['unknown']), 'action': 'control_pending'}
        return result

    def close(self):
        if self.db is not None:
            self.db.close()
        if self.index is not None:
            self.index.close()
        if self.journal is not None:
            self.journal.close()
