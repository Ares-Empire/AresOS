"""Request-local facts survive failed transactions; they are never replay authority."""
import copy
from functools import wraps
import sqlite3
import uuid

from .common import RESULT_LIMIT, WIRE_LIMIT, Refused, canonical, storage_refusal, shortened


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
        return bound_result(result, store, WIRE_LIMIT // 4 if 'tools' in result.get('data', {}) else RESULT_LIMIT)


def bound_result(result, store=None, limit=RESULT_LIMIT):
    """One last-step bound, shared by Engine, socket, CLI and MCP serialization.

    Keep the error and pending warnings outside the snapshot. Everything else
    can be recovered as JSON fragments, without a write to the failing disk.
    Callers without a Store shorten detail and explicitly count the loss.
    """
    if len(canonical(result).encode()) <= limit:
        return result
    result = copy.deepcopy(result)
    original_size = len(canonical(result).encode())
    facts = result.pop('observations', {})
    facts.setdefault('stages', {})
    facts.setdefault('evidence', {})
    if 'data' in result:
        facts['data'] = result.pop('data')
    error = result.get('error', {})
    for key in list(error):
        if key not in {'code', 'message'}:
            facts.setdefault('error', {})[key] = error.pop(key)
    # External/proxy exceptions can contain entire caller paths. Keep their
    # plain diagnostic prefix and page the exact original, with a cut count.
    if len(canonical(error).encode()) > limit // 4:
        facts.setdefault('error', {})['message'] = error['message']
        error['message'] = shortened(error['message'], 1024)
    warnings = list(owner_warnings(facts))
    pending = result.get('pending', {})
    if len(canonical(pending).encode()) > limit // 3:
        facts['pending'] = pending
        # Notices are owner warnings; pending operation details are pageable.
        result['pending'] = {k: v for k, v in pending.items() if k != 'items'}
        result['pending']['items'] = []
        warnings.extend(owner_warnings(pending.get('items', []), ('pending', 'items')))
    result['bounds'] = {'original_bytes': original_size, 'detail_characters': len(canonical(facts)),
                        'action': 'control_observations' if store is not None else None}
    if store is not None:
        token = uuid.uuid4().hex
        store.observation_snapshot = {'id': token, 'json': canonical(facts), 'warnings': warnings}
        result['observations'] = observation_page(store, token + ':0')
        if len(canonical(result).encode()) > limit:
            result['observations'].update(fragments=[], cursor=token + ':0')
    else:
        result['observations'] = {'stages': {}, 'evidence': {}, 'warnings': warnings,
                                  'count': len(canonical(facts)), 'cursor': None, 'fragments': []}
    if len(canonical(result).encode()) > limit:
        # Even the warning envelope may exceed one frame (legacy notices).
        # Preserve its full text in fragments and count each omitted warning.
        envelope = {'pending': result.pop('pending', {}), 'warnings': warnings}
        if store is not None:
            facts['warning_envelope'] = envelope
            store.observation_snapshot['json'] = canonical(facts)
            store.observation_snapshot['warnings'] = []
            result['observations'] = observation_page(store, token + ':0')
        else:
            result['observations'] = {'stages': {}, 'evidence': {}, 'count': len(canonical(facts))}
        result['pending'] = {'warning_count': len(envelope['pending'].get('notices', [])) + len(warnings),
                             'warning': 'Owner warnings exceed one frame; read the complete detail pages and mail_filing_notices.'}
        result['bounds']['warning_characters'] = len(canonical(envelope))
    result['bounds']['omitted_characters'] = len(canonical(facts))
    return result



def bounded(method):
    @wraps(method)
    def call(*args, **kwargs):
        return bound_result(method(*args, **kwargs))
    return call


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
