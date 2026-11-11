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
                self.store.owner_read_failed = True
        if selected(key):
            if key.startswith('notice:'):
                from itertools import islice
                from .retention import NOTICE_COUNT
                if not hasattr(self, '_notice_rows'):
                    rows = dict(islice(self.iter_items('notice:'), NOTICE_COUNT + 1))
                    self._notice_rows = rows if len(rows) <= NOTICE_COUNT else None
                if self._notice_rows is not None:
                    return self._notice_rows.get(key, default)
            return next((v for k,v in self.iter_items(key) if k == key), default)
        return self.store.get(key, default)

    def iter_items(self, prefix='', restore_outcomes=True):
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
                self.store.owner_read_failed = True
        for key, projected in self.store.owner_projection.iter_items(prefix):
            if key <= last:
                continue
            try:
                detailed = self.store.get(key)
            except (OSError, sqlite3.Error) as exc:
                if storage_refusal(exc) is None:
                    raise
                self.store.observations.storage(exc)
                self.store.owner_read_failed = True
                detailed = None
            value = detailed if fact(key, detailed) == projected else self.inflate(key, projected)
            latest = 0
            if restore_outcomes and key.startswith('op:') and self.store.locked:
                try:
                    found = self.store.index.execute('SELECT seq FROM latest WHERE id=?', (key[3:],)).fetchone() if self.store.index else None
                    latest = found[0] if found else max((f['seq'] for f in self.store.owner_projection.journal_records() if any(op['id'] == key[3:] for op in f['operations'])), default=0)
                except (OSError, sqlite3.Error) as exc:
                    if not isinstance(exc, sqlite3.Error) and storage_refusal(exc) is None:
                        raise
                    latest = max((f['seq'] for f in self.store.owner_projection.journal_records() if any(op['id'] == key[3:] for op in f['operations'])), default=0)
            if restore_outcomes and key.startswith('op:') and self.store.locked and (latest > self.store.restore_head or value.get('state') == 'submitting'):
                value = {**value, 'state': 'unknown', 'reason': 'Restored log: independent record has newer or missing evidence. Owner must check.'}
            yield key, value
        if restore_outcomes and self.store.locked and (not prefix or prefix.startswith('op:')):
            yield from self.missing_operations(prefix)

    def missing_operations(self, prefix):
        from .storage import missing_operation
        projection = self.store.owner_projection
        projected = iter(projection.iter_items('op:'))
        archived = iter(projection.iter_items('archived:'))
        current = next(projected, None)
        retired = next(archived, None)
        # All three streams are sorted by identity. A bounded merge avoids a
        # complete projection/journal rescan for every restored operation.
        for identity, _, known in self.store.iter_latest():
            key = 'op:' + identity
            if not key.startswith(prefix):
                continue
            while current and current[0] < key:
                current = next(projected, None)
            archive_key = 'archived:' + identity
            while retired and retired[0] < archive_key:
                retired = next(archived, None)
            if current and current[0] == key or retired and retired[0] == archive_key:
                continue
            yield key, missing_operation(known)

    def iter_audit(self):
        if self.store.write_failed or self.store.locked:
            yield from self.store.owner_projection.audit()
            return
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
            try:
                row = self.store.index.execute('SELECT created FROM births WHERE id=?', (key[3:],)).fetchone() if self.store.index else None
                if row is not None:
                    return row[0]
            except (OSError, sqlite3.Error) as exc:
                if storage_refusal(exc) is None:
                    raise
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
        if key.startswith('mail:filing-locations:'):
            return row
        row['_owner_encoded'] = True
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
            if row.get('repair_of') and row.get('state') == 'reserved':
                row['reason'] = 'Reserved local repair only.'
            if reason_kind == 'smtp_local':
                row['reason'] = 'Delivery evidence is recorded. Missing local stages; repair without SMTP.'
            elif reason_kind == 'smtp_partial_local':
                row['reason'] = 'Some recipients refused; accepted recipients must never be sent again. Missing local stages; repair without SMTP.'
            elif reason_kind in {'expired', 'cancelled'}:
                row['reason'] = reason_kind + ': nothing submitted'
            elif reason_kind == 'repair_uncertain':
                row['reason'] = 'Local repair uncertain; inspect far-side stage evidence. Never submit.'
            elif reason_kind == 'repair_storage':
                row['reason'] = 'Local repair storage failed; inspect evidence, never submit.'
            elif reason_kind == 'restored':
                row['reason'] = 'Restored log: independent record has newer or missing evidence. Owner must check.'
        if key.startswith(('mail:filing:', 'mail:rename:')):
            role = row.get('observed_role', 'an unverified role').lstrip('\\')
            row['reason'] = 'Filing needs inspection. Its current location is ' + str(row.get('target', 'unknown')) + ', inside ' + role + '. Nothing was deleted. Check your mail program.'
        if key.startswith('notice:'):
            content = dict(row.get('untrusted_content', {}))
            content['reason'] = 'Evidence needs inspection. Nothing was deleted automatically. Check your mail program.'
            if row.get('check_kind') == 'maintenance':
                content['reason'] = 'Background maintenance has no committed result. Storage may have failed; inspect the log and disk before continuing.'
            if row.get('check_kind') in {'rename', 'filing'}:
                source = self.get(row.get('source_key', '')) or {}
                role = row.get('observed_role')
                if role is None:
                    # A source may have newer evidence than this occurrence.
                    # Its original publication binds the occurrence's own role.
                    for _, changes in self.store.owner_projection.records():
                        notice = changes.get(key) or {}
                        original = changes.get(row.get('source_key')) or {}
                        binding = original.get('warning_checks', {}).get(row['check_kind'], {})
                        if (notice.get('evidence_fingerprint') == row.get('evidence_fingerprint') and
                                binding.get('occurrence_id') == row.get('id') and original.get('observed_role')):
                            role = original['observed_role']
                            break
                role = (role or source.get('observed_role', 'an unverified role')).lstrip('\\')
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
