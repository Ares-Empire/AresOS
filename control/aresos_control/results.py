"""Request-local facts survive failed transactions; they are never replay authority."""
import copy
from functools import wraps
import sqlite3
import uuid

from .common import RESULT_LIMIT, Refused, canonical, storage_refusal


def owner_warnings(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            if 'warning' in key or (key == 'reason' and
                    any(k in value for k in ('locations', 'observed_role', 'rename'))):
                yield {'path': list(path + (key,)), 'value': copy.deepcopy(item)}
            else:
                yield from owner_warnings(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from owner_warnings(item, path + (index,))


def observation_page(store, cursor):
    snapshot = store.observation_snapshot
    try:
        token, raw_offset = cursor.split(':')
        offset = int(raw_offset)
        if snapshot is None or token != snapshot['id'] or not 0 <= offset < len(snapshot['json']):
            raise ValueError()
    except (ValueError, AttributeError) as exc:
        raise Refused('stale_reference', 'Observation snapshot changed or service restarted; inspect operation status and filing locations.') from exc
    end = min(offset + 6000, len(snapshot['json']))
    return {'stages': {}, 'evidence': {}, 'warnings': snapshot['warnings'],
            'count': len(snapshot['json']), 'cursor': f'{token}:{end}' if end < len(snapshot['json']) else None,
            'fragments': [{'offset': offset, 'json': snapshot['json'][offset:end]}]}


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
        elif error is not None:
            for note in getattr(error, '__notes__', ()):
                if note not in getattr(self.error, '__notes__', ()):
                    self.error.add_note(note)
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

    def finish(self, result, store):
        if self.error is not None:
            result = {**result, 'ok': False,
                      'error': {'code': self.error.code, 'message': str(self.error)}}
            if getattr(self.error, '__notes__', None):
                result['error']['notes'] = list(dict.fromkeys(self.error.__notes__))
        if not result['ok'] and (self.stages or self.evidence):
            result['observations'] = {'stages': self.stages, 'evidence': self.evidence}
        if 'observations' in result and len(canonical(result).encode()) > RESULT_LIMIT:
            facts = result.pop('observations')
            warnings = list(owner_warnings(facts))
            # Retain one complete failed-request snapshot without writing to the
            # failing disk. Reading its pages never replaces the snapshot.
            token = uuid.uuid4().hex
            store.observation_snapshot = {'id': token, 'json': canonical(facts), 'warnings': warnings}
            page = observation_page(store, token + ':0')
            result['observations'] = page
            if len(canonical(result).encode()) > RESULT_LIMIT:
                # A nearly-full data envelope may leave no room even for one
                # fragment. The entire data is observational on this failure.
                if 'data' in result:
                    facts['data'] = result.pop('data')
                    warnings.extend(owner_warnings(facts['data'], ('data',)))
                    store.observation_snapshot['json'] = canonical(facts)
                page = observation_page(store, token + ':0')
                result['observations'] = page
                if len(canonical(result).encode()) > RESULT_LIMIT:
                    page.update(fragments=[], cursor=token + ':0')
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
