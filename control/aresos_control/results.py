"""Request-local facts survive failed transactions; they are never replay authority."""
import copy
from functools import wraps
import sqlite3

from .common import Refused, storage_refusal


class Observations:
    def __init__(self):
        self.error = None
        self.stages = {}
        self.evidence = {}

    def storage(self, exc, generic=False):
        error = storage_refusal(exc)
        if error is None and generic and isinstance(exc, (OSError, sqlite3.Error)):
            error = Refused('storage_error', 'Storage write failed; check the disk and operation status before doing more.')
        if error is not None and self.error is None:
            self.error = error
        return error

    def stage(self, operation_id, name, outcome):
        self.stages.setdefault(operation_id, {})[name] = copy.deepcopy(outcome)

    def observe(self, operation_id, evidence):
        previous = self.evidence.setdefault(operation_id, {})
        # A subsequent empty search cannot erase copies already seen this request.
        copies = previous.get('sent', [])
        if 'sent' in evidence:
            evidence = {**evidence, 'sent': copies + [item for item in evidence['sent'] if item not in copies]}
        previous.update(copy.deepcopy(evidence))

    def require_storage(self):
        if self.error is not None:
            raise self.error

    def finish(self, result):
        if self.error is not None:
            result = {**result, 'ok': False,
                      'error': {'code': self.error.code, 'message': str(self.error)}}
        if not result['ok'] and (self.stages or self.evidence):
            result['observations'] = {'stages': self.stages, 'evidence': self.evidence}
        return result


def recorded_write(method):
    @wraps(method)
    def write(store, *args, **kwargs):
        try:
            result = method(store, *args, **kwargs)
        except Exception as exc:
            store.observations.storage(exc, generic=True)
            store.remember_storage(exc)
            raise
        store.storage_cause = None
        if not store.flushing_notices:
            store.flush_notices()
        return result
    return write
