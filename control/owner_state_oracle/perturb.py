"""Systematic decoded-record mutations. No production imports or classifiers."""
import copy
from .model import Fact
from .records import canonical

STATES = ('reserved', 'submitting', 'unknown', 'partial', 'done', 'failed', 'refused',
          'started', 'checked', 'open', 'clean', 'warning', 'cancelled', 'expired', 'settled')
EFFECT_FIELDS = {'target', 'destination', 'last_known_destination', 'recipients', 'to', 'cc', 'bcc',
                 'flags', 'add', 'remove', 'sha256', 'raw_sha256', 'wire_sha256', 'sent_wire_sha256',
                 'hash', 'input_hash', 'composition_hash', 'evidence_fingerprint', 'fingerprint',
                 'source', 'sources', 'reference', 'references', 'identities', 'items', 'folder', 'uid',
                 'message_id', 'account', 'mode', 'repair_of', 'operation_id', 'stage', 'app', 'id'}


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


def leaves(value, path=(), states=STATES):
    if isinstance(value, dict):
        for key, child in value.items():
            here = path + (key,)
            if isinstance(child, bool):
                yield here, 'boolean', not child
            elif is_state(key, path) and isinstance(child, str):
                for state in states:
                    if child != state:
                        yield here, 'state', state
            elif key in EFFECT_FIELDS:
                replacement = ('0' if child[0] != '0' else '1') + child[1:] if ('hash' in key or 'fingerprint' in key) and isinstance(child, str) and child else alter(child)
                yield here, 'effect', replacement
            if isinstance(child, (dict, list)):
                yield from leaves(child, here, states)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, path + (index,), states)


def mutations(record, states=None):
    states = states or state_vocabulary([record])
    changed = copy.copy(record)
    changed.locked = not changed.locked
    yield 'locked', 'boolean', changed
    for group in ('fences', 'prepared'):
        for index, value in enumerate(getattr(record, group)):
            for path, kind, replacement in leaves(value, states=states):
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
        for path, kind, replacement in leaves(row, states=states):
            changed = copy.copy(record)
            changed.rows = {**record.rows, key: copy.deepcopy(row)}
            value = changed.rows[key]
            for part in path[:-1]:
                value = value[part]
            value[path[-1]] = replacement
            yield 'rows/' + key + '/' + '/'.join(map(str, path)), kind, changed
    for index, event in enumerate(record.events):
        seq = event['seq']
        metadata = {key: value for key, value in event.items() if key not in {'set', 'record'}}
        for path, kind, replacement in leaves(metadata, states=states):
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
            for path, kind, replacement in leaves(row, states=states):
                changed = copy.copy(record)
                changed.events = list(record.events)
                changed.events[index] = {**event, 'set': {**event['set'], key: copy.deepcopy(row)}}
                value = changed.events[index]['set'][key]
                for part in path[:-1]:
                    value = value[part]
                value[path[-1]] = replacement
                # Rebuild the projection for a coherent committed-record lie.
                changed.rows = {}
                for version in changed.events:
                    for name, item in version['set'].items():
                        if item is None:
                            changed.rows.pop(name, None)
                        else:
                            changed.rows[name] = item
                yield 'events/' + str(seq) + '/' + key + '/' + '/'.join(map(str, path)), kind, changed


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
    return result


def evaluate(oracle, record):
    current = clone(oracle)
    expected = current.expected(record)
    expected |= current.hold_facts(current.projection(record))
    expected |= current.qualification_facts({}, record)
    expected.update(Fact(source, 'locations', occurrence, canonical(locations))
                    for occurrence, (source, locations) in current.location_evidence.items())
    if current.script:
        expected.add(Fact('request', 'permitted-status', detail=canonical(sorted(
            current.permitted_status(record, current.script[-1])))))
    errors = current.completion_errors(record) | current.context_errors() | current.local_context_errors(record, getattr(current, 'seed_sequence', 0))
    errors |= current.lifecycle_errors | current.invalid_clean_results
    return expected, errors


def check(label, oracle, record, states=None):
    expected, errors = evaluate(oracle, record)
    counts = {}
    for field, kind, changed in mutations(record, states):
        actual, differences = evaluate(oracle, changed)
        counts[kind] = counts.get(kind, 0) + 1
        if actual != expected and not (differences - errors):
            raise AssertionError(('Silent owner-state perturbation', label, field,
                                  'missing', sorted(expected - actual), 'extra', sorted(actual - expected)))
    return counts
