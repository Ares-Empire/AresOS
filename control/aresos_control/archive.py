"""Owner-requested export and SQLite compaction; never rewrites the restore fence."""
import hashlib
import imaplib
import sqlite3
import os
import time
import uuid

from . import retention
from .adapters import Uncertain
from .common import storage_stream, Refused, canonical, cleanup, digest
from .storage import sync_directory


def archive(store, before, mail=None):
    store.ensure_writable()
    if store.locked:
        raise Refused('restore_required', 'Confirm the restored log before archiving history.')
    if before >= time.time():
        raise Refused('invalid_input', 'Archive cutoff must be in the past (Unix seconds).')
    closed, protected = {}, set()
    # A refused reopening leaves yesterday's clean result intact. After a
    # crash it cannot certify today's mailbox: recheck before removing it.
    operations = store.items('op:')
    dependencies = {op.get('repair_of') for _, op in operations if op['state'] in retention.OPEN}
    candidates = {op['id'] for key, op in operations if op['state'] in {'done', 'failed', 'refused'}
                  and store.retained_at(key) < before and op['id'] not in dependencies
                  and (not op.get('notice') or op.get('ack'))}
    candidates = set(sorted(candidates)[:100])
    unchecked = None
    verified_ids = set()
    name = 'history-' + uuid.uuid4().hex + '.jsonl'
    verification_key = 'intent:archive-' + name[8:-6]
    verification_sequences = set()
    if mail:
        sends = [op for _, op in operations if op['id'] in candidates and op['app'] == 'mail'
                 and op.get('payload', {}).get('composition') and
                 not (op['state'] in {'reserved', 'failed', 'refused'} and 'sent_copy_check' not in op)]
        unchecked = set()
        if sends:
            # One archive owns its verification. No newer per-operation event
            # can fall outside the export cutoff and require a second archive.
            run = {'id': 'recovery-' + verification_key[7:], 'app': 'mail', 'action': 'control_archive', 'state': 'started', 'check_open': True,
                   'checks': {op['id']: {'state': 'open'} for op in sends}}
            store.archiving = True
            try:
                store.write({verification_key: run}, 'control_archive', 'Archive verification opened')
                verification_sequences.add(store.sequence)
                updates = {}
                for op in sends:
                    try:
                        account = mail.account(op['payload']['composition']['mail']['account'], ready=False)
                        matches = mail.sent_matches(account, mail.message_id(op['id']))
                        run['checks'][op['id']] = {'state': 'checked', 'count': len(matches),
                                                  'matches': matches}
                        if len(matches) <= 1:
                            verified_ids.add(op['id'])
                        if len(matches) > 1:
                            from .warnings import check_result
                            content = {'operation_id': op['id'], 'message_count': len(matches),
                                       'reason': f'Sent contains {len(matches)} copies with this Message-ID. Check them in your mail program; nothing was deleted.'}
                            notices, _ = check_result(store, op, 'op:' + op['id'], 'sent_copies',
                                sorted(canonical(m) for m in matches), content, 'sent-' + digest(op['id'])[:32])
                            op['sent_copy_check'] = {'state': 'checked', 'count': len(matches), 'clean': False}
                            op['stages']['sent_copy_warning'] = content['reason']
                            updates.update(notices)
                            updates['op:' + op['id']] = op
                    except (Refused, OSError, sqlite3.Error, imaplib.IMAP4.error, Uncertain, KeyError, TypeError, ValueError):
                        unchecked.add(op['id'])
                if updates:
                    # These sources have a new unacknowledged occurrence and
                    # cannot retire. Their results never join the run's own
                    # export-eligible verification record.
                    store.write(updates, 'mail_sent_copy_check', 'Archive found changed Sent evidence')
                run.update(state='done', check_open=bool(unchecked))
                store.write({verification_key: run}, 'control_archive', 'Archive verification result')
                verification_sequences.add(store.sequence)
            finally:
                store.archiving = False
    operations = store.items('op:')
    dependencies = {op.get('repair_of') for _, op in operations if op['state'] in retention.OPEN}
    for key, op in operations:
        if (op['id'] not in dependencies and op['state'] in {'done', 'failed', 'refused'} and
                (not op.get('sent_copy_check') and not op.get('payload', {}).get('composition') or
                 unchecked is not None and op['id'] in verified_ids) and
                (not op.get('notice') or op.get('ack'))):
            if store.retained_at(key) < before and len(closed) < 100:
                closed[key] = op
        else:
            protected.add(key)
    for key, notice in store.items('notice:'):
        if not notice.get('ack'):
            intent_key = notice.get('source_key') or notice.get('untrusted_content', {}).get('intent_key')
            if intent_key:
                protected.add(intent_key)
            operation_id = notice.get('untrusted_content', {}).get('operation_id')
            if operation_id:
                closed.pop('op:' + operation_id, None)
                protected.add('op:' + operation_id)
            protected.update((key, 'mail:filing:' + notice['id'], 'mail:rename:' + notice['id'],
                              'mail:filing-locations:' + notice['id'] + ':'))
    for prefix in ('mail:filing:', 'mail:rename:'):
        for key, intent in store.items(prefix):
            notice = store.get('notice:' + intent['id'])
            if (intent.get('check_open') or intent.get('state') not in {'done', 'partial'} or
                    intent.get('state') == 'partial' and not (notice and notice.get('ack'))):
                protected.add(key)
                protected.add('mail:filing-locations:' + intent['id'] + ':')
    for key, account in store.items('mail:account:'):
        if not account.get('onboarded', account.get('ready', False)):
            protected.add(key)

    def eligible(event):
        keys = set(event['set']) | {'op:' + op['id'] for op in event['record']['operations']}
        return ((event['time'] < before or event['seq'] in verification_sequences) and event['seq'] not in legacy_sources and
                not any(key.startswith(p) for key in keys for p in protected))

    # Calculate space before making an export. Recovery can use the physical
    # reserve ordinary work leaves untouched; the private export is never public.
    estimate = store.db.execute('SELECT coalesce(sum(length(CAST(value AS BLOB)) + 128),0) FROM events').fetchone()[0]
    estimate += sum(retention.size(v) + 128 for v in closed.values()) + 65536
    # Include the export, its audit transaction and VACUUM's temporary database.
    store.ledger.admit(estimate + store.history_size() * 2 + 256 * 1024)
    # An older unfinished action may have no separate intent row, and a full
    # notice table may still need its audit row as the only warning source.
    from .recovery import unfinished
    legacy_sources = {int(key.rsplit(':', 1)[1]) for key, notice_id, _, _ in unfinished(store)
                      if key.startswith('legacy-intent:') and
                      not (store.get('notice:' + notice_id) or {}).get('ack')}
    directory = store.evidence_dir / 'archives'
    directory.mkdir(mode=0o700, exist_ok=True)
    temporary, destination = directory / (name + '.partial'), directory / name
    checksum, sequences = hashlib.sha256(), []
    exported_count = 0
    head = store.events[-1]
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with storage_stream(os.fdopen(fd, 'wb')) as stream:
            def emit(value):
                encoded = (canonical(value) + '\n').encode()
                stream.write(encoded)
                checksum.update(encoded)
            emit({'format': 'aresos-history-1', 'before': before, 'head': {'seq': head['seq'], 'hash': head['hash']}})
            for event in store.iter_audit():
                can_prune = eligible(event)
                shared_closed = event['time'] < before and any(key in closed for key in event['set'])
                if can_prune or shared_closed:
                    emit({'event': event})
                    exported_count += 1
                    if can_prune:
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
                    'events': exported_count, 'operations': len(closed), 'head': head['hash']}
        changes['archive:' + name] = manifest
        if verification_sequences and not unchecked:
            changes[verification_key] = None
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
        store.owner_projection.compact()
        return {**manifest, 'history_bytes': store.history_size(), 'independent_record_retained': True,
                'read_with': 'sudo cat ' + str(destination)}
    finally:
        with cleanup('archive temporary unlink'):
            temporary.unlink(missing_ok=True)
