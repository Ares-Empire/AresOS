"""One recovery catalogue for every durable intent; it never resumes work."""
import json
from .common import digest, storage_refusal


def open_filings(store):
    if getattr(store, '_open_filings', None) is None:
        store._open_filings = {key for prefix in ('mail:filing:', 'mail:rename:')
                              for key, value in store.iter_items(prefix)
                              if value.get('state') == 'started' or value.get('check_open')}
    return store._open_filings


def unfinished(store, cutoff=None, keys=None):
    if keys is not None:
        rows = ((key, value) for key in sorted(keys) if (value := store.get(key)) is not None)
    elif cutoff is None:
        from itertools import chain
        rows = chain.from_iterable(store.iter_items(prefix) for prefix in
            ('mail:filing:', 'mail:rename:', 'op:', 'export:', 'mail:account:', 'intent:'))
    else:
        # Filter before decoding: current-session filing pages/compositions can
        # contain megabytes and cannot be startup recovery candidates.
        encoded = store.db.execute("SELECT source.k,source.v FROM kv AS source "
            "LEFT JOIN retained AS age ON age.k=source.k WHERE COALESCE(age.created,0)<=? AND ("
            "substr(source.k,1,3)='op:' OR substr(source.k,1,7) IN ('intent:','export:') OR "
            "substr(source.k,1,12) IN ('mail:filing:','mail:rename:') OR "
            "substr(source.k,1,13)='mail:account:') ORDER BY source.k", (cutoff,))
        rows = ((key, json.loads(value)) for key, value in encoded)
    for key, value in rows:
        if key.startswith(('mail:filing:', 'mail:rename:')) and value.get('state') == 'started':
            yield key, value['id'], 'mail', 'Filing was interrupted. Messages or folders may have moved into a special folder, including Trash. Nothing is moved back or deleted automatically. Check your mail program and the filing audit before repeating.'
        elif key.startswith('op:') and value.get('state') in {'submitting', 'unknown', 'partial'}:
            yield key, 'recovery-' + value['id'], value['app'], 'An approved operation or local repair is unfinished. Delivery, deletion, POST or APPEND may already have happened, and Sent copies may be duplicated. Inspect operation_status and the server; never resubmit automatically.'
        elif key.startswith('export:'):
            yield key, 'recovery-' + key[7:], value['app'], 'A caller export is unfinished. Its recovery space is still held. Inspect the destination file and recorded export before repeating or resolving it.'
        elif key.startswith('mail:account:') and not value.get('onboarded', value.get('ready', False)):
            yield key, 'recovery-' + digest(key)[:32], 'mail', 'Owner account setup is unfinished. Probes may already have sent mail or created folders. Inspect the setup log and server; never repeat probes automatically.'
        elif key.startswith('intent:'):
            yield key, value['id'], value['app'], 'A change was interrupted before its completion was recorded. It may already have changed the server. Inspect the audit and your app before repeating.'

    if not hasattr(store, 'legacy_intents'):
        latest = {}
        for event in store.iter_audit():
            if event.get('operation_id') is None:
                changes = event.get('set', {})
                explicit = any(key.startswith(('intent:', 'mail:filing:', 'mail:rename:', 'export:', 'mail:account:'))
                               for key in changes)
                latest[event['action']] = (event.get('outcome'), explicit, event['seq'])
        store.legacy_intents = []
        for action, (outcome, explicit, seq) in latest.items():
            if outcome in {'started', 'unknown'} and not explicit:
                key = 'legacy-intent:' + action + ':' + str(seq)
                store.legacy_intents.append((key, 'recovery-' + digest(key)[:32], action.split('_', 1)[0],
                    'A change in the older audit log has no recorded completion. It may already have changed the server. Inspect the audit and your app before repeating.'))
    yield from store.legacy_intents


def recovery_notices(store, include_checks=True):
    candidates = getattr(store, 'startup_intents', set())
    keys = {key for key, _ in candidates if not key.startswith('legacy-intent:')}
    if include_checks:
        keys.update(open_filings(store))
        keys.update(key for key, value in store.iter_items('mail:account:')
                    if not value.get('onboarded', value.get('ready', False)))
    for key, notice_id, app, reason in unfinished(store, keys=keys):
        filing = key.startswith(('mail:filing:', 'mail:rename:'))
        account = key.startswith('mail:account:')
        if (key, notice_id) not in candidates and not (include_checks and (filing or account)):
            continue
        if filing:
            reason = ('Filing roles and locations are not yet checked. The interrupted check has no committed result. '
                      'Messages or folders may have moved into a special folder, including Trash. '
                      'Nothing is moved back or deleted automatically. Inspect the filing audit and your mail program.')
        elif account:
            reason = ('Owner account setup is unfinished; its qualification is not yet checked. '
                      'Probes may already have sent mail or changed folders. Inspect the setup log and server; '
                      'no probes are repeated automatically.')
        row = store.db.execute('SELECT created FROM retained WHERE k=?', (key,)).fetchone()
        created = row[0] if row is not None else 0
        if store.get('notice:' + notice_id) is None:
            yield {'id': notice_id, 'app': app, 'state': 'unknown', 'ack': False,
                   'created_at': int(created * 1_000_000_000), 'untrusted_content': {
                       'reason': reason, 'intent_key': key, 'recovery_warning': True}}


def recover_intents(store, persist=True):
    # A durable intent is also the source of its notice until the notice's own
    # bounded batch fits. Reads synthesize every remaining notice, so neither a
    # full disk nor 10,000 restored operations need an unbounded RAM queue.
    from itertools import islice
    store._open_filings = None
    # Capture identities in their actual unfinished state, before and after
    # prepared replay. A reservation that starts later was never interrupted.
    store.startup_intents = getattr(store, 'startup_intents', set()) | {
        (key, notice_id) for key, notice_id, _, _ in unfinished(store)}
    for notice in islice(recovery_notices(store), 3):
        store.defer_notice(notice['id'], {'notice:' + notice['id']: notice},
                           'control_intent_recovery', 'Unfinished durable intent needs owner inspection')
    if persist:
        try:
            store.flush_notices()
        except Exception as exc:
            if storage_refusal(exc) is None:
                raise
            store.observations.storage(exc)
            store.remember_storage(exc)
