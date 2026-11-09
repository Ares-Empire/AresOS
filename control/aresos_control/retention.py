"""Admission and expiry for caller-created private working data.

The immutable audit history has its own hard admission cap; expiry never rewrites
it. Warnings and operation evidence are retained until the owner resolves them.
"""
import time

from .common import Refused, canonical

TTL = 24 * 60 * 60
COMPOSITION_COUNT = 128
COMPOSITION_BYTES = 4 * 1024 * 1024
IMPORT_COUNT = 256
IMPORT_BYTES = 1024 * 1024
FILING_COUNT = 512
FILING_BYTES = 128 * 1024 * 1024
NOTICE_COUNT = 512
NOTICE_BYTES = 2 * 1024 * 1024
BLOB_COUNT = 256
BLOB_BYTES = 512 * 1024 * 1024
HISTORY_BYTES = 1024 * 1024 * 1024
FILING_RESERVE = 48 * 1024 * 1024
NOTICE_RESERVE = 16 * 1024
REQUEST_RESERVE = 128 * 1024 * 1024
RECOVERY_RESERVE = 64 * 1024 * 1024
RECOVERY_REQUEST = 1024 * 1024
RECOVERY_ACTIONS = {'control_restore_confirm', 'control_archive'}
OPEN = {'reserved', 'submitting', 'partial', 'unknown'}


def size(value):
    return len(canonical(value).encode())


def refuse(label, count, total):
    raise Refused('storage_limit', f'{label} limit: {count} records / {total} bytes. '
                  'Unused working data expires after 24 hours; acknowledge resolved notices, '
                  'or ask the owner to archive retained history. Never retry an uncertain operation.')


def admit(store, prefixes, count, total, additions=None, label='Stored working data', extra_count=0, extra_bytes=0):
    rows = {k: v for prefix in prefixes for k, v in store.items(prefix)}
    for k, v in (additions or {}).items():
        if v is None:
            rows.pop(k, None)
        else:
            rows[k] = v
    if len(rows) + extra_count > count or sum(size(v) for v in rows.values()) + extra_bytes > total:
        refuse(label, count, total)


def recovery_action(name):
    return name in RECOVERY_ACTIONS or any(name.endswith('_' + verb) for verb in
                                          ('operation_cancel', 'notice_ack', 'operation_repair'))


def hashes(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if (k == 'sha256' or k.endswith('_sha256')) and isinstance(v, str):
                yield v
            else:
                yield from hashes(v)
    elif isinstance(value, list):
        for v in value:
            yield from hashes(v)


def expire(engine):
    from .warnings import source_notices
    store = engine.store
    if store.locked or store.write_failed:
        return
    now = time.time()
    operations = [op for _, op in store.items('op:')]
    pinned_comps = {op.get('payload', {}).get('composition', {}).get('id')
                    for op in operations if op['state'] in OPEN}
    changes = {}
    protected_hashes = set()
    for op in operations:
        if op['state'] in OPEN:
            protected_hashes.update(hashes(op))
    for _, comp in store.items('mail:composition:'):
        if comp['id'] in pinned_comps or now - comp.get('created_at', store.retained_at('mail:composition:' + comp['id'])) < TTL:
            protected_hashes.update(hashes(comp))
    for key, comp in store.items('mail:composition:'):
        if comp['id'] not in pinned_comps and now - comp.get('created_at', store.retained_at('mail:composition:' + comp['id'])) >= TTL:
            changes[key] = None
    # Unresolved intents/notices never expire. Resolved records remain in audit.
    for prefix in ('mail:filing:', 'mail:rename:', 'notice:', 'blob:'):
        for key, value in store.items(prefix):
            created = store.retained_at(key)
            resolved = (prefix == 'blob:' or (prefix == 'notice:' and value.get('ack'))
                        or (prefix in {'mail:filing:', 'mail:rename:'} and value.get('state') == 'done'))
            notice = store.get('notice:' + value.get('id', ''))
            if notice:
                resolved = bool(notice.get('ack')) and value.get('state') in {'done', 'partial'}
            if prefix in {'mail:filing:', 'mail:rename:'} and (value.get('check_open') or value.get('state') == 'started'):
                resolved = False
            if prefix in {'mail:filing:', 'mail:rename:'} and any(not n.get('ack') for n in source_notices(store, key)):
                resolved = False
            if prefix == 'notice:':
                content = value.get('untrusted_content', {})
                source_key = value.get('source_key') or content.get('intent_key')
                if source_key and store.get(source_key) is not None:
                    resolved = False
            if prefix == 'blob:' and value['sha256'] in protected_hashes:
                resolved = False
            if now - created >= TTL and resolved:
                changes[key] = None
                if prefix == 'mail:filing:' or prefix == 'notice:':
                    changes.update({k: None for k, _ in store.items('mail:filing-locations:' + value['id'] + ':')})
    if changes:
        store.write(changes, 'control_expire', 'expired unused working data; operation evidence and unresolved warnings retained')
    pinned = set()
    for _, comp in store.items('mail:composition:'):
        pinned.update(hashes(comp))
    # Keep wires and attachment bytes referenced by any retained operation: even
    # completed operations can be inspected/repaired. They are bounded by caps.
    for op in operations:
        pinned.update(hashes(op))
    for blob_store in (engine.blobs, engine.adapters['mail'].wires):
        blob_store.expire(pinned, now, TTL)
