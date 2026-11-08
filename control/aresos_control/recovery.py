"""One recovery catalogue for every durable intent; it never resumes work."""
import time
from .common import digest, storage_refusal


def unfinished(store):
    for key, value in store.iter_items(''):
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


def recovery_notices(store):
    for key, notice_id, app, reason in unfinished(store):
        created = store.retained_at(key) if not key.startswith('legacy-intent:') else 0
        if created <= getattr(store, 'recovery_cutoff', 0) and store.get('notice:' + notice_id) is None:
            yield {'id': notice_id, 'app': app, 'state': 'unknown', 'ack': False,
                   'created_at': int(created * 1_000_000_000), 'untrusted_content': {
                       'reason': reason, 'intent_key': key, 'recovery_warning': True}}


def recover_intents(store, persist=True):
    # A durable intent is also the source of its notice until the notice's own
    # bounded batch fits. Reads synthesize every remaining notice, so neither a
    # full disk nor 10,000 restored operations need an unbounded RAM queue.
    from itertools import islice
    store.recovery_cutoff = time.time()
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
