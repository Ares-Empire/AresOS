"""Shared passive owner-state reads; SQLite adds detail, never obligations."""
import sqlite3

from .common import storage_refusal
from .owner_projection import selected


class OwnerView:
    def __init__(self, store):
        self.store = store

    def __getattr__(self, name):
        return getattr(self.store, name)

    def get(self, key, default=None):
        if not (self.store.locked or self.store.write_failed):
            try:
                return self.store.get(key, default)
            except (OSError, sqlite3.Error) as exc:
                if storage_refusal(exc) is None:
                    raise
                self.store.observations.storage(exc)
        if selected(key):
            return next((v for k,v in self.iter_items(key) if k == key), default)
        return self.store.get(key, default)

    def iter_items(self, prefix=''):
        from .owner_projection import fact
        last = ''
        if not (self.store.locked or self.store.write_failed):
            try:
                for key, value in self.store.iter_items(prefix):
                    last = key
                    yield key, value
                return
            except (OSError, sqlite3.Error) as exc:
                if storage_refusal(exc) is None:
                    raise
                self.store.observations.storage(exc)
        for key, projected in self.store.owner_projection.iter_items(prefix):
            if key <= last:
                continue
            try:
                detailed = self.store.get(key)
            except (OSError, sqlite3.Error) as exc:
                if storage_refusal(exc) is None:
                    raise
                self.store.observations.storage(exc)
                detailed = None
            value = detailed if fact(key, detailed) == projected else self.inflate(key, projected)
            latest = max((f['seq'] for f in self.store.owner_projection.journal_records() if any(op['id'] == key[3:] for op in f['operations'])), default=0) if key.startswith('op:') and self.store.locked else 0
            if key.startswith('op:') and self.store.locked and (latest > self.store.restore_head or value.get('state') == 'submitting'):
                value = {**value, 'state': 'unknown', 'reason': 'Restored log: independent record has newer or missing evidence. Owner must check.'}
            yield key, value
        if self.store.locked and (not prefix or prefix.startswith('op:')):
            yield from self.missing_operations(prefix)

    def missing_operations(self, prefix):
        from .storage import missing_operation
        cursor = ''
        projection = self.store.owner_projection
        while True:
            batch = {}
            for fence in projection.journal_records():
                for op in fence['operations']:
                    identity = op['id']
                    if identity <= cursor or not ('op:' + identity).startswith(prefix):
                        continue
                    if identity not in batch and len(batch) == 32:
                        largest = max(batch)
                        if identity > largest:
                            continue
                        del batch[largest]
                    batch[identity] = op
            if not batch:
                return
            for identity, known in sorted(batch.items()):
                if any(k == 'op:' + identity for k,_ in projection.iter_items('op:' + identity)):
                    continue
                if any(k == 'archived:' + identity for k,_ in projection.iter_items('archived:' + identity)):
                    continue
                yield 'op:' + identity, missing_operation(known)
            cursor = max(batch)

    def iter_audit(self):
        try:
            yield from self.store.iter_audit()
        except (OSError, sqlite3.Error) as exc:
            if storage_refusal(exc) is None:
                raise
            self.store.observations.storage(exc)
            yield from self.store.owner_projection.audit()

    def items(self, prefix):
        return list(self.iter_items(prefix))

    def retained_at(self, key):
        try:
            row = self.store.db.execute('SELECT created FROM retained WHERE k=?', (key,)).fetchone()
            if row is not None:
                return row[0]
        except (OSError, sqlite3.Error) as exc:
            if storage_refusal(exc) is None:
                raise
            self.store.observations.storage(exc)
        if key.startswith('op:'):
            for fence in self.store.owner_projection.journal_records():
                if any(op['id'] == key[3:] for op in fence['operations']):
                    return fence['time']
        for seq, changes in self.store.owner_projection.records():
            if changes.get(key) is not None:
                return self.store.owner_projection.fence(seq)['time']
        return 0

    def inflate(self, key, row):
        if not isinstance(row, dict):
            return row
        row = dict(row)
        row.pop('reason_code', None)
        reason_kind = row.pop('reason_kind', None)
        if key.startswith('mail:account:'):
            code = row.pop('qualification_code', None)
            if code:
                row['folder_delete_reason'] = {
                    'qualified': 'Qualified: exact probe survival and cleanup were verified.',
                    'probe_missing': 'Probe folder did not survive nonempty DELETE.',
                    'exact_cleanup_failed': 'Exact probe UID EXPUNGE cleanup failed; inspect setup.',
                    'empty_cleanup_failed': 'Empty probe folder DELETE cleanup failed; inspect setup.',
                    'generic_cleaned': 'Exact probe removed; empty folder retained for owner cleanup.',
                    'survival_unverified': 'Probe survival or cleanup could not be verified.',
                    'unqualified': 'Folder deletion has not been qualified.'}[code]
        if key.startswith('op:'):
            row.setdefault('approval', {'unavailable': True})
            row.setdefault('expires', 0)
            row.setdefault('stages', {})
            row['reason'] = {'reserved': 'Awaiting exact approval; nothing submitted.',
                'submitting': 'Durably submitting; do not cancel or retry.',
                'unknown': 'Outcome is unknown; inspect the server before repeating.',
                'partial': 'Operation is unfinished; inspect its local stages before repeating.',
                'done': 'Operation finished.', 'failed': 'Operation did not finish.'}.get(row.get('state'), 'Inspect operation status.')
            if row.get('repair_of') and row.get('state') == 'submitting':
                row['reason'] = 'Repairing local stage only.'
            if reason_kind == 'smtp_local':
                row['reason'] = 'Delivery evidence is recorded. Missing local stages; repair without SMTP.'
            elif reason_kind == 'smtp_partial_local':
                row['reason'] = 'Some recipients refused; accepted recipients must never be sent again. Missing local stages; repair without SMTP.'
        if key.startswith(('mail:filing:', 'mail:rename:')):
            role = row.get('observed_role', 'an unverified role').lstrip('\\')
            row['reason'] = 'Filing needs inspection. Its current location is ' + str(row.get('target', 'unknown')) + ', inside ' + role + '. Nothing was deleted. Check your mail program.'
        if key.startswith('notice:'):
            content = dict(row.get('untrusted_content', {}))
            content['reason'] = 'Evidence needs inspection. Nothing was deleted automatically. Check your mail program.'
            if row.get('check_kind') in {'rename', 'filing'}:
                source = self.get(row.get('source_key', '')) or {}
                role = source.get('observed_role', 'an unverified role').lstrip('\\')
                location = ('inside ' + role if row['check_kind'] == 'rename' else
                            'The target ' + str(source.get('target', 'unknown'))[:64] + ' is now ' + role)
                content['reason'] = 'Filing needs inspection. ' + location + '. Nothing was deleted. Check your mail program.'
            if row.get('check_kind') == 'evidence_unrecorded':
                content['reason'] = ('An earlier Sent check has no committed result. Sent copies may be duplicated. Nothing was deleted. Check your mail program.'
                                     if content.get('check_kind') == 'sent_copies' else
                                     'An earlier filing check has no committed result. Messages or folders may have moved into Trash. Nothing was deleted. Check your mail program.')
            if row.get('check_kind') == 'sent_copies':
                content['reason'] = f"Sent contains {content.get('message_count', 0)} copies. Nothing was deleted. Check your mail program."
            row['untrusted_content'] = content
        return row


def owner_view(store):
    return store if isinstance(store, OwnerView) else OwnerView(store)
