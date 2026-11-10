"""Systematic decoded-record mutations. No production imports or classifiers."""
import copy
from .model import Fact
from .compare import compare_proofs
from .records import canonical

STATES = ('reserved', 'submitting', 'unknown', 'partial', 'done', 'failed', 'refused',
          'started', 'checked', 'open', 'clean', 'warning', 'cancelled', 'expired', 'settled')


def is_state(key, path):
    return key in {'state', 'outcome'} or 'stages' in path and (
        key in {'sent_copy', 'answered_flag', 'smtp_data', 'folder_probe', 'folder', 'https_post'} or
        key.startswith(('target:', 'recipient:', 'rcpt:')))


def state_vocabulary(records):
    result = set(STATES)
    def visit(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and is_state(key, path):
                    result.add(child)
                visit(child, path + (key,))
        elif isinstance(value, list):
            for child in value:
                visit(child, path)
    for record in records:
        visit(record.rows)
        visit(record.events)
        visit(record.fences)
        visit(record.prepared)
    return tuple(sorted(result))


def alter(value):
    if isinstance(value, dict):
        return {key: alter(child) for key, child in value.items()}
    if isinstance(value, list):
        return value[:-1] if value else ['perturbed']
    if isinstance(value, str):
        return value + ':perturbed'
    if isinstance(value, int):
        return value + 1000000
    return 'perturbed'


# Every decoded scalar is perturbed. There are deliberately no field-name
# exclusions: a new production field joins the audit without editing a list.
EXCLUSIONS = {}


def scalar_fields(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from scalar_fields(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from scalar_fields(child, path + (index,))
    else:
        yield path


def leaves(value, path=(), states=STATES):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, path + (key,), states)
    elif isinstance(value, list):
        yield path, 'effect', alter(value)
        for index, child in enumerate(value):
            yield from leaves(child, path + (index,), states)
    else:
        key = next((part for part in reversed(path) if isinstance(part, str)), '')
        if isinstance(value, bool):
            yield path, 'boolean', not value
        elif is_state(key, path[:-1]) and isinstance(value, str):
            for state in states:
                if value != state:
                    yield path, 'state', state
        else:
            replacement = ('0' if value[0] != '0' else '1') + value[1:] if ('hash' in key or 'fingerprint' in key) and isinstance(value, str) and value else alter(value)
            yield path, 'effect', replacement


def audited_leaves(value, states):
    seen = set()
    for path, kind, replacement in leaves(value, states=states):
        seen.add(path)
        yield path, kind, replacement
    missing = set(scalar_fields(value)) - seen - EXCLUSIONS.keys()
    assert not missing, ('Unaudited decoded fields', sorted(map(str, missing)))


def mutations(record, states=None):
    states = states or state_vocabulary([record])
    changed = copy.copy(record)
    changed.locked = not changed.locked
    yield 'locked', 'boolean', changed
    for group in ('fences', 'prepared'):
        for index, value in enumerate(getattr(record, group)):
            for path, kind, replacement in audited_leaves(value, states):
                changed = copy.copy(record)
                versions = list(getattr(record, group))
                versions[index] = copy.deepcopy(value)
                setattr(changed, group, versions)
                target = versions[index]
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = replacement
                yield group + '/' + str(index) + '/' + '/'.join(map(str, path)), kind, changed
    # Mutate the projection and every historical version independently. A
    # coherent event/projection variant additionally exercises semantic checks
    # rather than relying only on projection consistency.
    for key, row in record.rows.items():
        changed = copy.copy(record)
        changed.rows = dict(record.rows)
        del changed.rows[key]
        yield 'remove-row:' + key, 'row', changed
        for path, kind, replacement in audited_leaves(row, states):
            changed = copy.copy(record)
            changed.rows = {**record.rows, key: copy.deepcopy(row)}
            value = changed.rows[key]
            for part in path[:-1]:
                value = value[part]
            if path:
                value[path[-1]] = replacement
            else:
                changed.rows[key] = replacement
            yield 'rows/' + key + '/' + '/'.join(map(str, path)), kind, changed
    for index, event in enumerate(record.events):
        seq = event['seq']
        metadata = {key: value for key, value in event.items() if key not in {'set', 'record'}}
        for path, kind, replacement in audited_leaves(metadata, states):
            changed = copy.copy(record)
            changed.events = list(record.events)
            changed.events[index] = {**event, **copy.deepcopy(metadata)}
            target = changed.events[index]
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = replacement
            yield 'event-metadata/' + str(seq) + '/' + '/'.join(map(str, path)), kind, changed
        changed = copy.copy(record)
        changed.events = list(record.events)
        changed.events.pop(index)
        yield 'drop-sequence:' + str(seq), 'sequence', changed
        changed = copy.copy(record)
        changed.events = copy.deepcopy(record.events)
        if index:
            changed.events[index - 1]['action'] = 'control_restore_confirm'
            changed.events[index - 1]['set']['generation'] = 'perturbed-generation'
        else:
            changed.events.insert(0, {'seq': 0, 'time': event['time'], 'action': 'control_restore_confirm', 'set': {'generation': 'perturbed-generation'}})
        yield 'restore-before:' + str(seq), 'restore', changed
        for key, row in event['set'].items():
            changed = copy.copy(record)
            changed.events = list(record.events)
            changed.events[index] = {**event, 'set': dict(event['set'])}
            del changed.events[index]['set'][key]
            yield 'remove-event-row:' + str(seq) + '/' + key, 'row', changed
            for path, kind, replacement in audited_leaves(row, states):
                changed = copy.copy(record)
                changed.events = list(record.events)
                changed.events[index] = {**event, 'set': {**event['set'], key: copy.deepcopy(row)}}
                value = changed.events[index]['set'][key]
                for part in path[:-1]:
                    value = value[part]
                if path:
                    value[path[-1]] = replacement
                else:
                    changed.events[index]['set'][key] = replacement
                # Rebuild the projection for a coherent committed-record lie.
                changed.rows = {}
                for version in changed.events:
                    for name, item in version['set'].items():
                        if item is None:
                            changed.rows.pop(name, None)
                        else:
                            changed.rows[name] = item
                yield 'events/' + str(seq) + '/' + key + '/' + '/'.join(map(str, path)), kind, changed


# Decoder-derived bookkeeping is tested by records.py's integrity tests. Its
# independent commit markers/restore intervals are inputs, not row claims.
# events[*].record duplicates the separately perturbed fence byte-for-byte;
# consistency_errors checks that equality on every comparison.
RECORD_EXCLUSIONS = {
    'committed': 'Independent commit-marker set, decoded with hash validation',
    'working_sequences': 'Physical SQLite membership, checked by archive/decoder tests',
    'unprepared_fences': 'Derived fence minus committed/prepared sets',
    'generation': 'Derived from rows[generation], which is perturbed',
    'restore_intervals': 'Derived from the perturbed restore events',
    'head': 'Independent SQLite head/chain validation has dedicated decoder tests',
    'startup_sequence': 'Test recorder startup boundary, not production-written',
}


def field_paths(record):
    assert set(record.__dict__) == {'rows', 'events', 'fences', 'prepared', 'locked'} | RECORD_EXCLUSIONS.keys(), ('Unaudited decoded record fields', set(record.__dict__))
    result = {'locked'}
    for group in ('fences', 'prepared'):
        for index, value in enumerate(getattr(record, group)):
            result.update(group + '/' + str(index) + '/' + '/'.join(map(str, path)) for path in scalar_fields(value))
    for key, row in record.rows.items():
        result.update('rows/' + key + '/' + '/'.join(map(str, path)) for path in scalar_fields(row))
    for event in record.events:
        prefix = str(event['seq']) + '/'
        metadata = {key: value for key, value in event.items() if key not in {'set', 'record'}}
        result.update('event-metadata/' + prefix + '/'.join(map(str, path)) for path in scalar_fields(metadata))
        for key, row in event['set'].items():
            result.update('events/' + prefix + key + '/' + '/'.join(map(str, path)) for path in scalar_fields(row))
    return result


def clone(oracle):
    result = copy.copy(oracle)
    for key, value in oracle.__dict__.items():
        if key not in {'script', 'servers', 'response_observer', 'seed_events', 'validated_input', 'validated_record'}:
            # Expectation methods replace nested values; only their outer
            # containers are mutated. Script/server inputs are read-only.
            setattr(result, key, copy.copy(value))
    return result


def freeze(oracle):
    """A live recorder must not acquire later calls while its corpus is built."""
    result = copy.copy(oracle)
    for key, value in oracle.__dict__.items():
        if key not in {'response_observer', 'validated_input', 'validated_record'}:
            setattr(result, key, copy.deepcopy(value))
    # The callback retains its live Driver, engine and queued envelopes. It is
    # recorder plumbing, never an expectation input. Frozen replays need none.
    result.response_observer = None
    result.validated_input = None
    result.validated_record = None
    return result


def evaluate(oracle, record):
    current = clone(oracle)
    differences = set()
    def checker(view, expected, actual):
        differences.update((view, f) for f in expected ^ actual)
    expected = compare_proofs(current, record, checker, getattr(current, 'seed_sequence', 0))
    try:
        expected |= current.hold_facts(current.projection(record))
        expected |= current.qualification_facts({}, record)
        expected.update(Fact(source, 'locations', occurrence, canonical(locations))
                        for occurrence, (source, locations) in current.location_evidence.items())
        if current.script:
            expected.add(Fact('request', 'permitted-status', detail=canonical(sorted(
                current.permitted_status(record, current.script[-1])))))
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        # A malformed record counts only if compare_proofs delivered its
        # difference. A helper exception alone is never a detection.
        expected = set()
    return expected, differences


def check(label, oracle, record, states=None, candidates=None):
    expected, errors = evaluate(oracle, record)
    counts, covered = {}, set()
    for field, kind, changed in mutations(record, states) if candidates is None else candidates:
        covered.add(field)
        actual, differences = evaluate(oracle, changed)
        counts[kind] = counts.get(kind, 0) + 1
        if actual != expected and not (differences - errors):
            raise AssertionError(('Silent owner-state perturbation', label, field,
                                  'missing', sorted(expected - actual), 'extra', sorted(actual - expected)))
    if candidates is None:
        missing = field_paths(record) - covered
        assert not missing, ('Unaudited decoded fields', label, sorted(missing))
    return counts
