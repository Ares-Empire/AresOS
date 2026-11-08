"""One physical-space ledger shared by every local durable writer.

Rights are reconstructed from verified evidence on startup, never from the
disposable index. Amounts include serialization, SQLite rollback and page slack.
The service serializes requests; admission therefore precedes each whole write.
"""
import shutil

from .common import Refused, canonical

SAFETY_FLOOR = 4 * 1024 * 1024


def record_budget(value):
    return len(canonical(value).encode()) * 16 + 128 * 1024


class SpaceLedger:
    def __init__(self, paths, history_usage=lambda: 0):
        self.paths = paths
        self.history_usage = history_usage
        self.holds = {}

    @property
    def held(self):
        return sum(self.holds.values())

    def right(self, operation, original=None):
        if operation is None:
            return {}
        if operation.get('repair_of') and operation['state'] in {'reserved', 'submitting', 'unknown'}:
            return {'settle:' + operation['id']: record_budget(operation) + record_budget(original or {})}
        if operation['state'] == 'reserved':
            return {'cancel:' + operation['id']: record_budget(operation)}
        return {}

    def admit(self, cost, *, updates=None, consume=(), paths=None,
              history_cost=None, recovery=False, owner_recovery=False, cancellation=False):
        """Spend unheld bytes, or only the named right's own held bytes.

        Updates are applied only after the caller durably finishes. A failed
        admission neither changes the journal nor creates/releases a right.
        """
        if history_cost is not None and not (owner_recovery or cancellation or consume):
            from . import retention
            # This is the compactable audit quota, not another disk floor.
            protected = 0 if recovery else retention.RECOVERY_RESERVE
            if self.history_usage() + history_cost + protected > retention.HISTORY_BYTES:
                retention.refuse('Recovery audit history' if recovery else
                                 'Free-work audit history (recovery capacity reserved)', 'retained', retention.HISTORY_BYTES)
        after = self.holds | (updates or {})
        credit = sum(self.holds.get(key, 0) for key in consume)
        if consume and cost > credit:
            raise Refused('storage_limit', 'Recovery record exceeds its held reservation; free storage and ask the owner to inspect it.')
        remaining = sum(value for key, value in after.items() if key not in consume)
        for path in paths or self.paths:
            # Blobs and passwords can be admitted before their directory exists.
            while not path.exists():
                path = path.parent
            if shutil.disk_usage(path).free < cost + remaining + SAFETY_FLOOR:
                raise Refused('storage_limit', f'Storage ledger holds {remaining} bytes for recovery plus '
                              f'{SAFETY_FLOOR} safety bytes; this write needs {cost} bytes. '
                              'Ask the owner to free storage. No journal transaction started.')

    def finish(self, updates, consume=()):
        self.holds.update(updates)
        for key in consume:
            self.holds.pop(key, None)
        self.holds = {key: value for key, value in self.holds.items() if value}
