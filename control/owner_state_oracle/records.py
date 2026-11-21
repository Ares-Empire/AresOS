"""Decode the documented Mail format, without Store or any production helper."""
from contextlib import closing
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sqlite3
import shutil
import tempfile
import unicodedata


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def visible(value):
    if isinstance(value, str):
        return ''.join('\\u%04x' % ord(c) if unicodedata.category(c) in {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'} else '\\\\' if c == '\\' else c for c in value)
    if isinstance(value, dict):
        return {visible(k): visible(v) for k, v in value.items()}
    if isinstance(value, list):
        return [visible(v) for v in value]
    return value


@dataclass
class Record:
    rows: dict = field(default_factory=dict)
    events: list = field(default_factory=list)
    fences: list = field(default_factory=list)
    prepared: list = field(default_factory=list)
    committed: set = field(default_factory=set)
    working_sequences: set = field(default_factory=set)
    unprepared_fences: set = field(default_factory=set)
    generation: str = None
    locked: bool = False
    restore_intervals: list = field(default_factory=list)
    head: tuple = None
    startup_sequence: int = 0
    interrupted_confirm: bool = False
    journal_history: tuple = ()


@dataclass(frozen=True)
class JournalAttempt:
    phase: str
    sequence: int
    hash: str
    offset: int
    write: bool
    sync: bool
    truncate: bool
    rollback_sync: bool


@dataclass(frozen=True)
class StartupReplay:
    # Canonical bytes keep the pre-start authority independent of later records.
    event: str
    generation: str


def startup_obligation(record, calls, generation):
    """A full, fenced restore plan plus the recorded owner confirm permits replay.

    A fence alone, an ordinary prepared write, or an unrelated confirm grants
    no authority to finish a restore. This expectation is saved BEFORE startup.
    """
    if not record.fences:
        return None
    fence = record.fences[-1]
    event = next((e for e in [*record.events, *record.prepared] if e['seq'] == fence['seq']), None)
    if not event or event.get('record') != fence or event.get('time') != fence['time']:
        return None
    if event.get('action') != 'control_restore_confirm' or not event.get('space', {}).get('restoring'):
        return None
    if not any(c['action'] == 'control_restore_confirm' and c.get('restore_precondition') is True and
               c.get('start_seq', -1) < event['seq'] <= c.get('staged_end_seq', c.get('end_seq', -1))
               for c in calls):
        return None
    changes = event['set']
    if not (changes.get('restore_pending') is True or
            isinstance(changes.get('generation'), str) and changes.get('restore_pending', False) is None):
        return None
    return StartupReplay(canonical(event), generation)


def startup_errors(obligation, record, rows, locked):
    """Check the successful start itself, before a request can repair it."""
    if obligation is None:
        return []
    event = json.loads(obligation.event)
    seq, fence = event['seq'], event['record']
    errors, previous = [], ''
    chain = True
    for index, entry in enumerate(record.fences, 1):
        chain &= (entry.get('seq') == index and entry.get('previous') == previous and
                  entry.get('hash') == fingerprint({k: v for k, v in entry.items() if k != 'hash'}))
        previous = entry.get('hash')
    fences = {f['seq']: f for f in record.fences}
    if not chain or fences.get(seq) != fence or seq not in record.committed:
        errors.append(('sequence:' + str(seq), 'missing-startup-marker', ''))
    if not record.head or record.head[0] < seq or fences.get(record.head[0], {}).get('hash') != record.head[1]:
        errors.append(('sequence:' + str(seq), 'unapplied-startup-head', ''))
    if not any(e == event for e in record.events):
        errors.append(('sequence:' + str(seq), 'changed-startup-event', ''))
    for key, value in event['set'].items():
        if (key in rows if value is None else rows.get(key) != value):
            errors.append((key, 'unapplied-startup-effect', canonical(value)))
    final = event['set'].get('restore_pending') is None
    generation = event['set']['generation'] if final else obligation.generation
    if rows.get('generation') != generation:
        errors.append(('generation', 'wrong-startup-generation', canonical(generation)))
    if bool(locked) != (not final) or bool(rows.get('restore_pending')) != (not final):
        errors.append(('restore', 'wrong-startup-lock', str(not final)))
    return errors


def write_latched(record):
    """Running transaction state from raw journal phases and validated bytes.

    Only a failed first fence with proven truncation AND rollback sync can be
    retried live. A failed marker stays latched even if its bytes survived.
    Startup ends this running history; old prepared bytes are recovery input.
    """
    latched = False
    fences = {f['seq']: f['hash'] for f in record.fences}
    for attempt in record.journal_history:
        complete = attempt.write and attempt.sync
        if attempt.phase == 'fence':
            undone = (not complete and attempt.truncate and attempt.rollback_sync and
                      fences.get(attempt.sequence) != attempt.hash)
            latched = not undone
        elif attempt.phase == 'marker':
            latched = not (complete and attempt.sequence in record.committed and
                           fences.get(attempt.sequence) == attempt.hash)
    return latched or any(e['seq'] > record.startup_sequence for e in record.prepared) or any(
        f['seq'] > record.startup_sequence and f['seq'] not in record.committed for f in record.fences)


def latch_refusal_first(record, call):
    """A later passive-pending fault cannot replace an earlier latch refusal."""
    if not call.get('write_attempted'):
        return False
    checks = call.get('latch_checks', ())
    faults = call.get('faults', {}).get('trace', ())
    # SQLite ignores xClose errors from the read handles preceding a write
    # check. They are fault sites, but cannot supply the request's first error.
    # Python file.close errors do propagate and must keep their precedence.
    faults = [f for f in faults if not (f[1].startswith('sqlite.') and f[1].endswith('.close'))]
    if faults:
        return any(point < faults[0][0] for point in checks)
    return bool(checks) or write_latched(record)


def behind(sequence, committed):
    """A restore lock needs the working head *behind* the last commit marker.

    Only then is SQLite older than the journal's committed history, which the
    owner must confirm (storage.py's startup lock, control/README.md). A head
    *ahead* is the service's own write that failed at its marker: startup
    finishes it and there is nothing to confirm. decoded_lock uses this rule,
    and through it the decoder, consistency_errors and the alteration suite's
    recompute. The lock's other terms stay as they are: restore_pending, a head
    hash that differs from its record, and the startup rule for an unprepared
    record.
    """
    return sequence < max(committed, default=0)


def decoded_lock(rows, fences, committed, head):
    """The restore lock a record's bytes decode to.

    `fences` maps each sequence to its independent record. A pending restore
    locks. Otherwise a store with independent records locks when its working
    head is missing, behind the last commit marker, or carries a hash that
    differs from its record's. The decoder, consistency_errors and the
    alteration suite's recompute all use this one formula, so its terms cannot
    drift apart; service_lock adds what a running service holds beyond it.
    """
    if rows.get('restore_pending'):
        return True
    if not fences:
        return False
    if head is None:
        return True
    sequence, head_hash = head
    expected_hash = fences.get(sequence, {}).get('hash', '' if sequence == 0 else None)
    return behind(sequence, committed) or head_hash != expected_hash


def service_lock(record):
    """The lock a running service holds beyond what its bytes decode to.

    The driver sets both inputs. An unprepared record from before the last
    start locks at startup. A confirm on a locked store that met a storage
    fault keeps the lock until the next restart, even when the rollback of its
    last commit marker failed and the marker's bytes stayed.
    """
    return any(seq <= record.startup_sequence for seq in record.unprepared_fences) or record.interrupted_confirm


def restore_intervals(events):
    """A restore can explain only earlier holes, up to its old working head.

    The restore fence is appended after the independent head. Its immediately
    preceding *present* event bounds the working history that survived rollback.
    Script validation is separate; a marker is never a wildcard for later loss.
    """
    intervals, present = [], []
    for event in sorted(events, key=lambda e: e['seq']):
        if event['action'] == 'control_restore_confirm' and (
                event['set'].get('generation') or event['set'].get('restore_pending')):
            lower = max(present, default=0)
            intervals.append((lower + 1, event['seq'] - 1, event['seq']))
        present.append(event['seq'])
    return intervals


def unexplained_sequences(record):
    present = {event['seq'] for event in record.events}
    explained = {seq for first, last, _ in restore_intervals(record.events)
                 for seq in record.committed if first <= seq <= last}
    return record.committed - present - explained


def staged_sequence(record):
    """Bind a write to its producing call even before application or marking."""
    return max((f['seq'] for f in record.fences), default=max(
        (e['seq'] for e in [*record.events, *record.prepared]), default=0))


def visible_history(record):
    """Marked history plus the ordinary tail proven applied by SQLite's head.

    Decode already checked the entire fence chain and full events. Recheck the
    tail's identity here so altered records cannot promote a different claim.
    Restore batches keep their own lock/replay rules, never this live-row rule.
    """
    if not record.head or not record.fences:
        return record.events
    fence = record.fences[-1]
    seq = fence['seq']
    if record.head != (seq, fence.get('hash')) or seq <= max(record.committed, default=0):
        return record.events
    for event in record.prepared:
        if (event.get('seq') == seq and event.get('record') == fence and event.get('time') == fence.get('time') and
                event.get('action') != 'control_restore_confirm' and not event.get('space', {}).get('restoring') and
                all(isinstance(op.get('id'), str) and (event['set'].get('op:' + op['id']) is None or all(
                    event['set']['op:' + op['id']].get(k) == op.get(k) for k in ('id', 'generation', 'input_hash', 'state')))
                    for op in fence.get('operations', []))):
            return [*record.events, event]
    return record.events


def history_rows(events):
    rows = {}
    for event in events:
        for key, value in event['set'].items():
            if value is None:
                rows.pop(key, None)
            else:
                rows[key] = value
    return rows


def applied_sequence(record):
    # Restore projections retain their existing marked-history rules. Only a
    # validated ordinary applied tail can extend a local observation boundary.
    return max(max(record.committed, default=0), max((e['seq'] for e in visible_history(record)), default=0))


def consistency_errors(record):
    """Compare visible rows to validated history, including compact fences."""
    errors, rows = [], {}
    fences = {f['seq']: f for f in record.fences}
    previous = ''
    for index, fence in enumerate(record.fences, 1):
        # Minimal unit records can omit physical encodings. A decoded fence
        # carries these fields even when its working event was lost in restore.
        if 'hash' in fence and 'previous' in fence and (
                fence['seq'] != index or fence['previous'] != previous or
                fence['hash'] != fingerprint({k: v for k, v in fence.items() if k != 'hash'})):
            errors.append(('sequence:' + str(fence['seq']), 'changed-independent-chain', ''))
        previous = fence.get('hash', '')
    if record.head is not None:
        locked = decoded_lock(record.rows, fences, record.committed, record.head)
        if (locked or service_lock(record)) != record.locked:
            errors.append(('restore', 'unjustified-lock', ''))
    for seq in unexplained_sequences(record):
        errors.append(('sequence:' + str(seq), 'missing-committed-history', ''))
    # Rejected tail candidates still carry claims. Dropping them from visible
    # history must not erase a mismatch between the full event and its fence.
    for event in record.prepared:
        seq = event['seq']
        fence = fences.get(seq)
        if not fence or event.get('record') != fence or event.get('time') != fence.get('time'):
            errors.append(('sequence:' + str(seq), 'changed-independent-fence', ''))
        for op in (fence or {}).get('operations', []):
            row = event['set'].get('op:' + str(op.get('id')))
            if row is not None and any(row.get(k) != op.get(k) for k in ('id', 'generation', 'input_hash', 'state')):
                errors.append(('op:' + str(op.get('id')), 'changed-fenced-operation', str(seq)))
        restoring = event.get('space', {}).get('restoring', False)
        if 'restoring' in event.get('space', {}) and (type(restoring) is not bool or
                restoring != (event['action'] == 'control_restore_confirm')):
            errors.append(('sequence:' + str(seq), 'invalid-restore-plan', ''))
    marked_sequences = {e['seq'] for e in record.events}
    for event in visible_history(record):
        seq = event['seq']
        if seq in marked_sequences and record.committed and seq not in record.committed:
            errors.append(('sequence:' + str(seq), 'uncommitted-event', ''))
        fence = fences.get(seq)
        if fence and event.get('record') != fence:
            errors.append(('sequence:' + str(seq), 'changed-independent-fence', ''))
        for op in (fence or {}).get('operations', []):
            source = 'op:' + str(op.get('id'))
            row = event['set'].get(source)
            if row is None:
                row = rows.get(source)
            if row is None or any(row.get(field) != op.get(field) for field in ('id', 'generation', 'input_hash', 'state')):
                errors.append((source, 'changed-fenced-operation', str(seq)))
        for key, value in event['set'].items():
            if value is None:
                rows.pop(key, None)
            else:
                rows[key] = value
    if record.fences:
        for key in rows.keys() | record.rows.keys():
            if rows.get(key) != record.rows.get(key):
                errors.append((key, 'changed-decoded-projection', ''))
    return errors


def decode(state, evidence):
    """Only hash-valid, commit-marked events supply committed local outcomes.

    Ordinary applied rows additionally use visible_history, without inventing
    a commit marker. A fence alone is restore evidence, not a completion.
    Archive exports are read only after checking the committed manifest hash.
    A torn final journal line is ignored; a corrupt complete line is an error.
    """
    result = Record()
    path = Path(evidence) / 'operations.jsonl'
    previous, fences = '', {}
    for line in path.read_bytes().splitlines(keepends=True):
        if not line.endswith(b'\n'):
            break
        value = json.loads(line)
        if 'commit' in value:
            seq = value['commit']
            if seq not in fences or fences[seq]['hash'] != value['hash']:
                raise ValueError('Commit marker without its matching fence')
            result.committed.add(seq)
            continue
        if value.get('format') not in (1, 2):
            raise ValueError('Unsupported independent record format')
        body = {k: v for k, v in value.items() if k != 'hash'}
        if value['previous'] != previous or value['hash'] != fingerprint(body):
            raise ValueError('Independent record hash chain mismatch')
        if value['seq'] != len(fences) + 1:
            raise ValueError('Nonconsecutive independent record')
        previous = value['hash']
        fences[value['seq']] = value
    result.fences = list(fences.values())
    # Failed rollback can leave a hot rollback journal and make even SELECT
    # require recovery writes. Recover a byte copy, never the service's DB.
    with tempfile.TemporaryDirectory(prefix='oracle-decode-', dir=Path(state).parent) as temporary:
        copied = Path(temporary) / 'control.sqlite'
        shutil.copyfile(Path(state) / 'control.sqlite', copied)
        journal = Path(state) / 'control.sqlite-journal'
        if journal.exists():
            shutil.copyfile(journal, Path(str(copied) + '-journal'))
        with closing(sqlite3.connect(copied)) as db:
            events = [json.loads(v) for (v,) in db.execute('SELECT value FROM events ORDER BY seq')]
            head = db.execute('SELECT seq,hash FROM head WHERE id=1').fetchone()
    result.head = head
    result.working_sequences = {event['seq'] for event in events}
    def valid_event(event):
        fence = fences.get(event['seq'])
        if fence is None or event['record'] != fence or event['time'] != fence['time']:
            raise ValueError('Working event does not match independent fence')
        for operation in fence['operations']:
            full = event['set'].get('op:' + operation['id'])
            if full is not None and any(full.get(name) != operation[name] for name in ('id', 'generation', 'input_hash', 'state')):
                raise ValueError('Operation differs from independent fence')
    for event in events:
        seq = event['seq']
        valid_event(event)
        if seq not in result.committed:
            result.prepared.append(event)
        else:
            result.events.append(event)
    # Pruned working history lives in a hash-qualified archive. Discover only
    # manifests in committed events, never by trusting the directory listing.
    archived, queue, visited = {}, list(result.events), set()
    while queue:
        event = queue.pop()
        for key, manifest in event['set'].items():
            if not key.startswith('archive:') or not manifest or manifest['path'] in visited:
                continue
            visited.add(manifest['path'])
            raw = Path(manifest['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest['sha256']:
                raise ValueError('Archive publication hash mismatch')
            for line in raw.splitlines():
                entry = json.loads(line)
                if 'event' in entry:
                    old = entry['event']
                    if old['seq'] in result.committed and old['record'] == fences.get(old['seq']) and old['seq'] not in archived:
                        valid_event(old)
                        archived[old['seq']] = old
                        queue.append(old)
    result.events = sorted({e['seq']: e for e in [*archived.values(), *result.events]}.values(), key=lambda e: e['seq'])
    result.restore_intervals = restore_intervals(result.events)
    if head and head[0] == max(result.committed, default=0) and unexplained_sequences(result):
        raise ValueError('Committed history missing from working log and qualified archives')
    result.rows = history_rows(visible_history(result))
    result.generation = result.rows.get('generation')
    result.unprepared_fences = set(fences) - result.committed - {event['seq'] for event in result.prepared}
    result.locked = decoded_lock(result.rows, fences, result.committed, head)
    return result
