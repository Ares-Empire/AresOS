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
            yield path + (key,), 'key-deletion', None
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


def put(value, path, kind, replacement):
    for part in path[:-1]:
        value = value[part]
    if kind == 'key-deletion':
        value.pop(path[-1], None)
    else:
        value[path[-1]] = copy.deepcopy(replacement)


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
                put(versions[index], path, kind, replacement)
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
            if path:
                put(changed.rows[key], path, kind, replacement)
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
            put(changed.events[index], path, kind, replacement)
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
                if path:
                    put(changed.events[index]['set'][key], path, kind, replacement)
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


# These compare redundant encodings, not a rule's independent authority. They
# remain useful integrity checks but cannot establish a coherent lie was caught.
STRUCTURAL = {'changed-decoded-projection', 'changed-observed-commit', 'changed-fixture-input',
              'missing-committed-history', 'uncommitted-event', 'changed-independent-fence',
              'changed-fenced-operation', 'unjustified-lock', 'invalid-record'}
SNAPSHOTS = ('committed_before', 'created_before', 'check_sources')


def snapshot_fields(oracle):
    for index, event in enumerate(oracle.servers):
        for group in SNAPSHOTS:
            if group in event:
                for path in scalar_fields(event[group]):
                    yield 'servers/' + str(index) + '/' + group + '/' + '/'.join(map(str, path))
    for sequence, rows in oracle.commit_observations.items():
        for path in scalar_fields(rows):
            yield 'commit_observations/' + str(sequence) + '/' + '/'.join(map(str, path))


def snapshot_mutations(oracle, record, states):
    for index, event in enumerate(oracle.servers):
        for group in SNAPSHOTS:
            if group not in event:
                continue
            for path, kind, replacement in audited_leaves(event[group], states):
                changed = copy.copy(oracle)
                changed.servers = list(oracle.servers)
                changed.servers[index] = {**event, group: copy.deepcopy(event[group])}
                if path:
                    put(changed.servers[index][group], path, kind, replacement)
                else:
                    changed.servers[index][group] = replacement
                yield 'servers/' + str(index) + '/' + group + '/' + '/'.join(map(str, path)), kind, (changed, record)
    for sequence, rows in oracle.commit_observations.items():
        for path, kind, replacement in audited_leaves(rows, states):
            changed = copy.copy(oracle)
            changed.commit_observations = {**oracle.commit_observations, sequence: copy.deepcopy(rows)}
            put(changed.commit_observations[sequence], path, kind, replacement)
            yield 'commit_observations/' + str(sequence) + '/' + '/'.join(map(str, path)), kind, (changed, record)


def coherent_change(oracle, record, key, path=(), kind='row', replacement=None, since=0):
    """Write one production lie into every later encoding of that row claim."""
    changed, replay = copy.deepcopy(record), freeze(oracle)
    def update(rows):
        if key not in rows:
            return
        if kind == 'row':
            rows.pop(key, None)
            return
        if not path:
            rows[key] = copy.deepcopy(replacement)
            return
        target = rows[key]
        try:
            put(target, path, kind, replacement)
        except (KeyError, IndexError, TypeError, AttributeError):
            pass  # A later version may no longer contain this nested field.
    for event in changed.events + changed.prepared:
        if event['seq'] >= since:
            update(event['set'])
    update(changed.rows)
    for event in replay.servers:
        if event.get('before_seq', -1) >= since:
            update(event.get('committed_before', {}))
            if kind == 'row':
                event.get('created_before', {}).pop(key, None)
                event['check_sources'] = [v for v in event.get('check_sources', []) if v != key]
    for sequence, rows in replay.commit_observations.items():
        if sequence >= since:
            update(rows)
    # Compact fences contain a subset of operation fields. Re-encode the same
    # claim there and in the event's copy, just as Store.write would do.
    versions = {e['seq']: e for e in changed.events + changed.prepared}
    for fence in changed.fences:
        if fence['seq'] < since or fence['seq'] not in versions:
            continue
        event = versions[fence['seq']]
        if key.startswith('op:'):
            for op in list(fence.get('operations', [])):
                if 'op:' + op['id'] != key:
                    continue
                row = event['set'].get(key)
                if kind == 'row':
                    fence['operations'].remove(op)
                elif path and path[0] in op and path[0] != 'description':
                    if path[0] in row:
                        op[path[0]] = copy.deepcopy(row[path[0]])
                    else:
                        op.pop(path[0], None)
        event['record'] = copy.deepcopy(fence)
    replay.validated_input = replay.validated_record = None
    return replay, changed


def coherent_mutations(oracle, record, states):
    seen = set()
    seed = getattr(oracle, 'seed_sequence', 0)
    for event in record.events:
        if event['seq'] <= seed or any(c['action'] == 'fixture_input' and
                c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', -1) for c in oracle.script):
            continue  # Independent fixture input, not a production claim.
        for key, row in event['set'].items():
            if row is None:
                continue
            candidates = [((), 'row', None), *audited_leaves(row, states)]
            for path, kind, replacement in candidates:
                signature = key, path, kind, canonical(replacement)
                if signature in seen:
                    continue
                seen.add(signature)
                yield ('coherent/' + str(event['seq']) + '/' + key + '/' + '/'.join(map(str, path)),
                       kind, coherent_change(oracle, record, key, path, kind, replacement, event['seq']))


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
    current.lifecycle_errors = set()
    current.stages_examined = set()
    current.validated_input = current.validated_record = None
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


VALIDATOR_KINDS = {
    'script_differences': {'R2.DATA', 'R2.APPEND', 'R2.STORE', 'R2.MOVE', 'R2.COPY', 'R2.RENAME', 'R2.POST', 'R2.RECEIVE'},
    'stage_claims': {'unjustified-stage'},
    'completion_errors': {'false-completion', 'duplicate-effect'},
    'payload_claims': {'unapproved-payload', 'unapproved-recorded-approval', 'unapproved-input-hash', 'unapproved-expiry', 'unapproved-composition'},
    'filing_claims': {'unapproved-filing-context', 'unapproved-filing-records', 'unverified-source-hash'},
    'transition': {'unsupported-resolution', 'unjustified-resolution', 'unjustified-resolution-reason'},
    'local.errors': {'R2.LOCAL_FLAG', 'R2.LOCAL_CHANGE', 'R2.LOCAL_DELETE'},
}


def check(label, oracle, record, states=None, candidates=None, statistics=None):
    expected, errors = evaluate(oracle, record)
    counts, covered = {}, set()
    def all_candidates():
        yield from mutations(record, states)
        yield from snapshot_mutations(oracle, record, states)
        yield from coherent_mutations(oracle, record, states)
    states = states or state_vocabulary([record])
    for field, kind, changed in all_candidates() if candidates is None else candidates:
        covered.add(field)
        replay, value = changed if isinstance(changed, tuple) else (oracle, changed)
        actual, differences = evaluate(replay, value)
        new = differences - errors
        if field.startswith('coherent/'):
            new = {(view, fact) for view, fact in new if fact.kind not in STRUCTURAL}
        counts[kind] = counts.get(kind, 0) + 1
        if statistics is not None and actual != expected:
            statistics['changed'] = statistics.get('changed', 0) + 1
            for validator, kinds in VALIDATOR_KINDS.items():
                own = any(f.kind in kinds and (validator != 'script_differences' or 'script.' in f.detail) for _, f in new)
                if own:
                    statistics[validator] = statistics.get(validator, 0) + 1
        if actual != expected and not new:
            raise AssertionError(('Silent owner-state perturbation', label, field,
                                  'missing', sorted(expected - actual), 'extra', sorted(actual - expected)))
    if candidates is None:
        missing = (field_paths(record) | set(snapshot_fields(oracle))) - covered
        assert not missing, ('Unaudited decoded fields', label, sorted(missing))
    return counts
