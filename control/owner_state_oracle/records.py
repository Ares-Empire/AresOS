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


def pending_reason(reason):
    value = str(reason or '')
    if 'restored' in value.lower() and any(word in value.lower() for word in ('newer', 'missing')):
        return 'RESTORED_EVIDENCE'
    marker = ' Missing local stages; repair without SMTP.'
    if value.endswith(marker):
        prefix = value[:-len(marker)]
        if prefix.startswith('Some recipients refused;'):
            return 'RECIPIENT_REFUSALS_AND_LOCAL_STAGES'
        if prefix in {'SMTP accepted delivery to every recipient.', 'Synthetic DATA accepted', 'Delivery evidence is recorded.'}:
            return 'ACCEPTED_DELIVERY_AND_LOCAL_STAGES'
    return reason


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
    owner_rows: dict = field(default_factory=dict)
    owner_sequences: dict = field(default_factory=dict)
    owner_versions: dict = field(default_factory=dict)
    owner_retired: list = field(default_factory=list)
    owner_kinds: dict = field(default_factory=dict)


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
            first, last = event.get('restore_range', (lower + 1, event['seq'] - 1))
            if not 1 <= first <= last + 1 <= event['seq']:
                raise ValueError('Invalid restore interval')
            intervals.append((first, last, event['seq']))
        present.append(event['seq'])
    return intervals


def unexplained_sequences(record):
    present = {event['seq'] for event in record.events}
    explained = {seq for first, last, _ in restore_intervals(record.events)
                 for seq in record.committed if first <= seq <= last}
    if record.locked and record.head is not None:
        head, claimed = record.head
        known = next((f['hash'] for f in record.fences if f['seq'] == head), '' if head == 0 else None)
        if claimed == known:
            explained.update(seq for seq in record.committed if seq > head)
    return record.committed - present - explained


def consistency_errors(record):
    """Compare the decoded projection to its commits, including compact fences."""
    errors, rows = [], {}
    fences = {f['seq']: f for f in record.fences}
    if record.head is not None:
        seq, claimed_hash = record.head
        expected_hash = fences.get(seq, {}).get('hash', '' if seq == 0 else None)
        locked = bool(record.rows.get('restore_pending')) or bool(record.fences and (
            seq != max(record.committed, default=0) or claimed_hash != expected_hash))
        startup_lock = any(seq <= record.startup_sequence for seq in record.unprepared_fences)
        if (locked or startup_lock) != record.locked:
            errors.append(('restore', 'unjustified-lock', ''))
    for seq in unexplained_sequences(record):
        errors.append(('sequence:' + str(seq), 'missing-committed-history', ''))
    for event in record.events:
        seq = event['seq']
        if record.committed and seq not in record.committed:
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
    if record.owner_versions or record.owner_retired:
        from .projection import fact, selected, publication, record_kind
        owner_rows, owner_sequences = {}, {}
        for sequence, changes in sorted([*record.owner_versions.items(), *record.owner_retired], key=lambda item: item[0]):
            for key,value in changes.items():
                if value is None:
                    owner_rows.pop(key, None)
                else:
                    owner_rows[key] = value
                owner_sequences[key] = sequence
        if owner_rows != record.owner_rows:
            errors.append(('owner', 'changed-owner-rows', ''))
        if owner_sequences != record.owner_sequences:
            errors.append(('owner', 'changed-owner-sequences', ''))
        events = {event['seq']: event for event in record.events}
        for sequence, changes in record.owner_versions.items():
            fence = fences.get(sequence, {})
            if fence.get('owner') in (None, publication(changes, record.owner_kinds.get(sequence, {}))):
                continue
            event = events.get(sequence)
            original = {k: fact(k,v) for k,v in event['set'].items() if selected(k)} if event else {}
            if (not event or publication(original, {k:record_kind(event,k,v) for k,v in event['set'].items() if selected(k)}) != fence.get('owner') or
                    any(k not in original or value != original[k] or
                        record.owner_kinds.get(sequence, {}).get(k) != record_kind(event,k,event['set'][k])
                        for k,value in changes.items())):
                errors.append(('owner', 'changed-owner-publication', str(sequence)))
    if record.fences:
        for key in rows.keys() | record.rows.keys():
            if rows.get(key) != record.rows.get(key):
                errors.append((key, 'changed-decoded-projection', ''))
    return errors


def decode(state, evidence):
    """Only hash-valid, commit-marked events supply committed local outcomes.

    A valid fence with no working event is restore evidence, not a completion.
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
    from .projection import decode as decode_owner
    result.owner_rows, result.owner_sequences, owner_history, owner_full, result.owner_versions, result.owner_retired, result.owner_kinds = decode_owner(evidence, result.fences, result.committed)
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
    archived, queue, visited = dict(owner_history), list(result.events) + list(owner_history.values()), set()
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
    for event in result.events:
        for key, value in event['set'].items():
            if value is None:
                result.rows.pop(key, None)
            else:
                result.rows[key] = value
    result.generation = result.rows.get('generation')
    result.unprepared_fences = set(fences) - result.committed - {event['seq'] for event in result.prepared}
    expected_head = fences[head[0]]['hash'] if head and head[0] in fences else '' if head and head[0] == 0 else None
    result.locked = bool(result.rows.get('restore_pending')) or bool(fences and
        (head is None or head[0] != max(result.committed, default=0) or head[1] != expected_head))
    return result
