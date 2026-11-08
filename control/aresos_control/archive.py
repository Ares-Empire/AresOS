"""Owner-requested export and SQLite compaction; never rewrites the restore fence."""
import hashlib
import os
import time
import uuid

from . import retention
from .common import Refused, canonical
from .storage import sync_directory


def archive(store, before):
    store.ensure_writable()
    if store.locked:
        raise Refused('restore_required', 'Confirm the restored log before archiving history.')
    if before >= time.time():
        raise Refused('invalid_input', 'Archive cutoff must be in the past (Unix seconds).')
    closed, protected = {}, set()
    operations = store.items('op:')
    dependencies = {op.get('repair_of') for _, op in operations if op['state'] in retention.OPEN}
    for key, op in operations:
        if op['id'] not in dependencies and op['state'] in {'done', 'failed', 'refused'} and (not op.get('notice') or op.get('ack')):
            if store.retained_at(key) < before and len(closed) < 100:
                closed[key] = op
        else:
            protected.add(key)
    for key, notice in store.items('notice:'):
        if not notice.get('ack'):
            protected.update((key, 'mail:filing:' + notice['id'], 'mail:rename:' + notice['id'],
                              'mail:filing-locations:' + notice['id'] + ':'))
    for prefix in ('mail:filing:', 'mail:rename:'):
        for key, intent in store.items(prefix):
            if intent.get('state') != 'done':
                protected.add(key)
                protected.add('mail:filing-locations:' + intent['id'] + ':')

    def eligible(event):
        keys = set(event['set']) | {'op:' + op['id'] for op in event['record']['operations']}
        return event['time'] < before and not any(key.startswith(p) for key in keys for p in protected)

    # Calculate space before making an export. Recovery can use the physical
    # reserve ordinary work leaves untouched; the private export is never public.
    estimate = store.db.execute('SELECT coalesce(sum(length(CAST(value AS BLOB)) + 128),0) FROM events').fetchone()[0]
    estimate += sum(retention.size(v) + 128 for v in closed.values()) + 65536
    # Include the export, its audit transaction and VACUUM's temporary database.
    store.ledger.admit(estimate + store.history_size() * 2 + 256 * 1024)
    directory = store.evidence_dir / 'archives'
    directory.mkdir(mode=0o700, exist_ok=True)
    name = 'history-' + uuid.uuid4().hex + '.jsonl'
    temporary, destination = directory / (name + '.partial'), directory / name
    checksum, sequences = hashlib.sha256(), []
    head = store.events[-1]
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            def emit(value):
                encoded = (canonical(value) + '\n').encode()
                stream.write(encoded)
                checksum.update(encoded)
            emit({'format': 'aresos-history-1', 'before': before, 'head': {'seq': head['seq'], 'hash': head['hash']}})
            for event in store.iter_audit():
                if eligible(event):
                    emit({'event': event})
                    sequences.append(event['seq'])
            for key, value in closed.items():
                emit({'key': key, 'value': value})
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(temporary, destination)
        sync_directory(directory)
        sync_directory(store.evidence_dir)
        store.checkpoint('archive_exported')
        # The independent journal retains every compact operation record and
        # commit. Tombstones distinguish intentional archival from missing data.
        next_seq = len(store.events) + 1
        changes = {key: None for key in closed}
        changes.update({'archived:' + key[3:]: {'seq': next_seq} for key in closed})
        manifest = {'path': str(destination), 'sha256': checksum.hexdigest(), 'before': before,
                    'events': len(sequences), 'operations': len(closed), 'head': head['hash']}
        changes['archive:' + name] = manifest
        # Export is durable before any source row is removed. Permit temporary
        # quota excess here so a pre-upgrade full store can also be compacted.
        store.archiving = True
        try:
            store.write(changes, 'control_archive', 'owner exported finished history before compaction')
        finally:
            store.archiving = False
        with store.db:
            store.ledger.admit(store.history_size() + 65536)
            for offset in range(0, len(sequences), 500):
                batch = sequences[offset:offset + 500]
                store.db.execute('DELETE FROM events WHERE seq IN (' + ','.join('?' for _ in batch) + ')', batch)
        store.checkpoint('archive_pruned')
        store.ledger.admit(store.history_size() * 2 + 65536)
        store.db.execute('VACUUM')
        sync_directory(store.state_dir)
        store.checkpoint('archive_compacted')
        return {**manifest, 'history_bytes': store.history_size(), 'independent_record_retained': True,
                'read_with': 'sudo cat ' + str(destination)}
    finally:
        temporary.unlink(missing_ok=True)
