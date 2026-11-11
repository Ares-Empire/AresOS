"""Occurrence bookkeeping in the existing source and notice stores."""
import copy
import time
import uuid

from .common import digest


def check_result(store, source, source_key, kind, evidence, content=None, notice_id=None):
    """Return notice changes to commit atomically with the source's check result.

    Reopening a check leaves its last warning fingerprint intact. Only a
    committed clean result or changed evidence starts another occurrence.
    """
    checks = source.setdefault('warning_checks', {})
    previous = checks.get(kind, {})
    if content is None:
        # Fingerprints identify warning evidence. A clean result only ends
        # that condition; keep its previous occurrence for history/ack.
        if previous:
            checks[kind] = {**previous, 'warning': False}
        return {}, None
    fingerprint = digest(evidence)
    if previous.get('warning') and previous.get('fingerprint') == fingerprint:
        return {}, previous['occurrence_id']
    base = notice_id or source['id']
    legacy = store.get('notice:' + base)
    if (not previous and legacy and not legacy.get('check_kind') and
            legacy.get('untrusted_content') == content):
        # Old notices have no evidence identity. Adopt the first new check
        # without undoing an acknowledgement made before this upgrade.
        occurrence_id = base
        notice = copy.deepcopy(legacy)
    else:
        occurrence_id = base if legacy is None and not previous.get('occurrence_id') else base[:47] + '-' + uuid.uuid4().hex
        notice = {'id': occurrence_id, 'app': 'mail', 'state': 'partial', 'ack': False,
                  'created_at': time.time_ns(), 'untrusted_content': copy.deepcopy(content)}
    notice.update(check_kind=kind, evidence_fingerprint=fingerprint, source_key=source_key)
    notice['untrusted_content'].setdefault('intent_key', source_key)
    if 'filing_id' in notice['untrusted_content']:
        notice['untrusted_content']['filing_id'] = occurrence_id
    checks[kind] = {'warning': True, 'fingerprint': fingerprint, 'occurrence_id': occurrence_id}
    return {'notice:' + occurrence_id: notice}, occurrence_id


def source_notices(store, source_key):
    """Include old single-notice sources as well as occurrence-aware records."""
    source_id = source_key.rsplit(':', 1)[-1]
    for _, notice in store.iter_items('notice:'):
        content = notice.get('untrusted_content', {})
        if (notice.get('source_key') == source_key or content.get('intent_key') == source_key or
                source_key.startswith(('mail:filing:', 'mail:rename:')) and notice['id'] == source_id):
            yield notice


def unrecorded_evidence(store, source_key, epoch, check_kind):
    """An interrupted check's generic occurrence survives later clean evidence."""
    identity = ('sent-' + digest(source_key[3:])[:32] if source_key.startswith('op:')
                else source_key.rsplit(':', 1)[-1]) + '-' + format(epoch, '032x')
    existing = store.get('notice:' + identity)
    if existing is not None:
        return {}
    content = {'intent_key': source_key, 'lost_check': epoch, 'check_kind': check_kind,
               'reason': ('An earlier evidence check has no committed result. Sent copies may be duplicated. '
                          'Nothing was deleted. Inspect Sent in your mail program.' if check_kind == 'sent_copies' else
                          'An earlier filing check has no committed result. Messages or folders may have moved into Trash. '
                          'Nothing was deleted. Inspect the filing audit and your mail program.')}
    if source_key.startswith('op:'):
        content['operation_id'] = source_key[3:]
    notice = {'id': identity, 'app': 'mail', 'state': 'partial', 'ack': False,
              'created_at': time.time_ns(), 'source_key': source_key,
              'check_kind': 'evidence_unrecorded',
              'evidence_fingerprint': digest(['unrecorded', source_key, epoch]),
              'untrusted_content': content}
    return {'notice:' + identity: notice}
