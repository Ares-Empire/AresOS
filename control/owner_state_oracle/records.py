"""Decode the documented Mail format, without Store or any production helper."""
from contextlib import closing
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sqlite3
import shutil
import tempfile


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


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
    restored = any(e['action'] == 'control_restore_confirm' and e['set'].get('generation') for e in result.events)
    if head and head[0] == max(result.committed, default=0) and not restored and result.committed - {e['seq'] for e in result.events}:
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
