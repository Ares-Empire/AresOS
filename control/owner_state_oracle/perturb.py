"""Systematic decoded-record mutations. No production imports or classifiers."""
import copy
from .model import Fact
from .compare import compare_proofs
from .records import canonical, fingerprint, restore_intervals, visible

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
        for group in ('owner_rows', 'owner_sequences', 'owner_versions', 'owner_retired', 'owner_kinds'):
            visit(getattr(record, group))
    return tuple(sorted(result))


def alter(value):
    if isinstance(value, dict):
        return {key: alter(child) for key, child in value.items()}
    if isinstance(value, list):
        return value[:-1] if value else ['perturbed']
    if isinstance(value, str):
        return value + ':perturbed'
    if isinstance(value, (int, float)):
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
    for group in ('owner_rows', 'owner_sequences', 'owner_versions', 'owner_retired', 'owner_kinds'):
        value = getattr(record, group)
        for path,kind,replacement in audited_leaves(value, states):
            changed = copy.copy(record)
            setattr(changed, group, copy.deepcopy(value))
            if path:
                put(getattr(changed, group), path, kind, replacement)
            else:
                setattr(changed, group, copy.deepcopy(replacement))
            yield group + '/' + '/'.join(map(str, path)), kind, changed
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
    assert set(record.__dict__) == {'rows', 'events', 'fences', 'prepared', 'locked', 'owner_rows', 'owner_sequences', 'owner_versions', 'owner_retired', 'owner_kinds'} | RECORD_EXCLUSIONS.keys(), ('Unaudited decoded record fields', set(record.__dict__))
    result = {'locked'}
    for group in ('fences', 'prepared'):
        for index, value in enumerate(getattr(record, group)):
            result.update(group + '/' + str(index) + '/' + '/'.join(map(str, path)) for path in scalar_fields(value))
    for group in ('owner_rows', 'owner_sequences', 'owner_versions', 'owner_retired', 'owner_kinds'):
        result.update(group + '/' + '/'.join(map(str, path)) for path in scalar_fields(getattr(record, group)))
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
              'changed-fenced-operation', 'unjustified-lock', 'changed-owner-rows', 'changed-owner-sequences', 'changed-owner-publication', 'invalid-record', 'changed-stage-event', 'unjustified-filing-start'}
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


def compact_description(row):
    """Encode the documented compact copy, never an expectation or authority."""
    description = row.get('approval', {}).get('description')
    if not isinstance(description, dict):
        return None
    if row.get('app') == 'mail' and 'untrusted_content' in description:
        result = {name: copy.deepcopy(description[name]) for name in ('action', 'untrusted_content') if name in description}
    else:
        result = {name: copy.deepcopy(description[name]) for name in
                  ('action', 'account', 'to', 'cc', 'bcc', 'subject', 'title') if name in description}
        result.setdefault('action', row.get('action'))
        if 'targets' in description:
            result['targets'] = copy.deepcopy(description['targets'])
        if 'items' in description:
            result['targets'] = [{name: copy.deepcopy(item[name]) for name in ('reference', 'subject', 'title') if name in item}
                                 for item in description['items'] if isinstance(item, dict)]
        if 'folder' in description:
            result['targets'] = [{name: copy.deepcopy(description[name]) for name in ('folder', 'uidvalidity') if name in description}]
        if 'target' in description:
            result['targets'] = [copy.deepcopy(description['target'])]
        if 'repair_of' in row:
            result['targets'] = [row['repair_of']]
        if row.get('app') == 'mail':
            action = result.pop('action')
            result = {'action': action, 'untrusted_content': visible(result)}
    if row.get('app') == 'mail' and row.get('repair_of'):
        result['repair'] = {'repair_of': row['repair_of'], 'stage': row.get('payload', {}).get('stage'),
                            'attempt_ended_at': row.get('attempt_ended_at')}
    return result


def coherent_change(oracle, record, key, path=(), kind='row', replacement=None, since=0):
    """Write one production lie into every later encoding of that row claim."""
    changed, replay = copy.copy(record), clone(oracle)
    changed.rows = dict(record.rows)
    # Copy the affected path and writable envelopes, sharing other immutable
    # decoded inputs. This keeps the complete historical corpus practical.
    def versions(events):
        result = []
        for event in events:
            result.append({**event, 'set': dict(event['set'])})
        return result
    changed.events = versions(record.events)
    changed.prepared = versions(record.prepared)
    changed.fences = list(record.fences)
    replay.servers = [dict(event) for event in oracle.servers]
    replay.commit_observations = dict(oracle.commit_observations)
    replay.response_observer = None
    origin = next((event['set'][key] for event in record.events if event['seq'] >= since and key in event['set']), record.rows.get(key))
    original = origin
    for part in path:
        original = original[part]
    def update(rows):
        if key not in rows:
            return
        if kind == 'row':
            if rows[key] == original:
                rows.pop(key, None)
            return
        if not path:
            if rows[key] == original:
                rows[key] = copy.deepcopy(replacement)
            return
        target = rows[key]
        try:
            previous = target
            for part in path:
                previous = previous[part]
            if previous == original:
                changed_row = copy.copy(rows[key])
                parent = changed_row
                for part in path[:-1]:
                    parent[part] = copy.copy(parent[part])
                    parent = parent[part]
                put(changed_row, path, kind, replacement)
                rows[key] = changed_row
        except (KeyError, IndexError, TypeError, AttributeError):
            pass  # A later version may no longer contain this nested field.
    for event in changed.events + changed.prepared:
        if event['seq'] >= since:
            before = event['set'].get(key)
            update(event['set'])
            after = event['set'].get(key)
            if isinstance(before, dict) and isinstance(after, dict):
                if before.get('state') != after.get('state') and event.get('outcome') == before.get('state'):
                    if 'state' in after:
                        event['outcome'] = after['state']
                    else:
                        event.pop('outcome', None)
                content = event.get('untrusted_content', {})
                stage = content.get('stage')
                old_stages, new_stages = before.get('stages', {}), after.get('stages', {})
                if stage in old_stages and content.get('outcome') == old_stages[stage] and old_stages.get(stage) != new_stages.get(stage):
                    content = copy.deepcopy(content)
                    if stage in new_stages:
                        content['outcome'] = new_stages[stage]
                    else:
                        content.pop('stage', None)
                        content.pop('outcome', None)
                    event['untrusted_content'] = content
                for name in ('filing', 'rename'):
                    claim = content.get(name)
                    if isinstance(claim, dict) and claim.get('state') == before.get('state') and before.get('state') != after.get('state'):
                        content = copy.deepcopy(content)
                        if 'state' in after:
                            content[name]['state'] = after['state']
                        else:
                            content[name].pop('state', None)
                        event['untrusted_content'] = content
    prefix, created, cursor, fence_rows = {}, {}, 0, {}
    server_sequences = {}
    for server in replay.servers:
        if isinstance(server.get('before_seq'), int):
            server_sequences.setdefault(server['before_seq'], []).append(server)
    snapshots = sorted({event.get('before_seq') for event in replay.servers if isinstance(event.get('before_seq'), int)} |
                       set(replay.commit_observations) | {fence['seq'] for fence in record.fences} | {max(record.committed, default=max((e['seq'] for e in changed.events), default=0))})
    for sequence in snapshots:
        while cursor < len(changed.events) and changed.events[cursor]['seq'] <= sequence:
            event = changed.events[cursor]
            fence_rows[event['seq']] = event['set'].get(key) or prefix.get(key)
            for name, row in event['set'].items():
                if row is None:
                    prefix.pop(name, None)
                else:
                    prefix[name] = row
                    created.setdefault(name, event['seq'])
            cursor += 1
        if sequence >= since and sequence in replay.commit_observations:
            rows = dict(replay.commit_observations[sequence])
            if key in prefix:
                rows[key] = prefix[key]
            else:
                rows.pop(key, None)
            replay.commit_observations[sequence] = rows
        for server in server_sequences.get(sequence, ()):
            if sequence >= since and 'committed_before' in server:
                rows = dict(server['committed_before'])
                if key in rows and key not in prefix and key in server.get('check_sources', []):
                    server['check_sources'] = [source for source in server['check_sources'] if source != key]
                if key in prefix:
                    rows[key] = prefix[key]
                else:
                    rows.pop(key, None)
                server['committed_before'] = rows
                creation = dict(server.get('created_before', {}))
                if key in created:
                    creation[key] = created[key]
                else:
                    creation.pop(key, None)
                server['created_before'] = creation
        if sequence == max(record.committed, default=max((e['seq'] for e in changed.events), default=0)):
            if key in prefix:
                changed.rows[key] = prefix[key]
            else:
                changed.rows.pop(key, None)
    altered_origin = {key: origin}
    update(altered_origin)
    origin_description = compact_description(origin) if isinstance(origin, dict) else None
    new_origin = altered_origin.get(key)
    changed_description = compact_description(new_origin) if isinstance(new_origin, dict) else None
    for event in changed.events + changed.prepared:
        if event['seq'] < since or not key.startswith('op:') or event.get('operation_id') != key[3:]:
            continue
        old_fence = next((fence for fence in record.fences if fence['seq'] == event['seq']), {})
        old_op = next((op for op in old_fence.get('operations', []) if op.get('id') == key[3:]), None)
        row = event['set'].get(key) or fence_rows.get(event['seq'])
        if old_op and event.get('outcome') == old_op.get('state'):
            if row and 'state' in row:
                event['outcome'] = row['state']
            else:
                event.pop('outcome', None)
    # Re-encode matching compact copies, including approval-derived descriptions.
    # A fence can refer to the pre-existing row when this event omits it.
    versions = {e['seq']: e for e in changed.events + changed.prepared}
    compact_inputs = {'id', 'generation', 'input_hash', 'state', 'approval', 'action', 'app',
                      'repair_of', 'payload', 'attempt_ended_at'}
    previous, dirty = '', False
    for index, original_fence in enumerate(record.fences):
        fence = original_fence
        if fence['seq'] >= since and key.startswith('op:') and (kind == 'row' or not path or path[0] in compact_inputs):
            operations = []
            for op in fence.get('operations', []):
                rewritten = op
                if 'op:' + str(op.get('id')) == key:
                    event = versions.get(fence['seq'])
                    if event and key not in event['set'] and event.get('operation_id') != key[3:]:
                        continue
                    row = (event['set'].get(key) or fence_rows.get(fence['seq'])) if event else None
                    if row is not None:
                        rewritten = {name: copy.deepcopy(row[name]) for name in ('id', 'generation', 'input_hash', 'state') if name in row}
                        description = compact_description(row)
                        if description is not None:
                            rewritten['description'] = description
                    elif event:
                        continue
                    else:
                        rewritten = dict(op)
                        if path and len(path) == 1 and path[0] in op and op[path[0]] == original:
                            put(rewritten, path, kind, replacement)
                        if kind != 'row' and op.get('description') == origin_description and origin_description != changed_description:
                            if changed_description is None:
                                rewritten.pop('description', None)
                            else:
                                rewritten['description'] = copy.deepcopy(changed_description)
                operations.append(rewritten)
            if operations != fence.get('operations', []):
                fence = {**fence, 'operations': operations}
                dirty = True
        if fence['seq'] >= since and key == 'generation' and fence.get('generation') == original:
            fence = dict(fence)
            if kind == 'row':
                fence.pop('generation', None)
            else:
                fence['generation'] = replacement
            dirty = True
        if dirty and 'hash' in fence:
            fence = {**fence, 'previous': previous}
            fence['hash'] = fingerprint({name: value for name, value in fence.items() if name != 'hash'})
        changed.fences[index] = fence
        previous = fence.get('hash', previous)
        if fence is not original_fence and fence['seq'] in versions:
            versions[fence['seq']]['record'] = fence
        if changed.head and changed.head[0] == fence['seq']:
            changed.head = (changed.head[0], fence.get('hash', changed.head[1]))
    changed.generation = changed.rows.get('generation')
    changed.restore_intervals = restore_intervals(changed.events)
    if changed.head is not None:
        sequence, head_hash = changed.head
        fence = next((value for value in changed.fences if value['seq'] == sequence), {})
        expected_hash = fence.get('hash', '' if sequence == 0 else None)
        changed.locked = bool(changed.rows.get('restore_pending')) or bool(changed.fences and (
            sequence != max(changed.committed, default=0) or head_hash != expected_hash)) or any(
            seq <= changed.startup_sequence for seq in changed.unprepared_fences)
    replay.validated_input = replay.validated_record = None
    return replay, changed


def coherent_mutations(oracle, record, states):
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
        if key in {'_completion_cache', '_binding_cache', '_approved_cache', '_payload_cache'}:
            setattr(result, key, {})
            continue
        if key == '_effect_record':
            result._effect_record = None
            continue
        if key == '_evidence_index':
            result._evidence_index = None
            continue
        if key not in {'response_observer', 'validated_input', 'validated_record'}:
            setattr(result, key, copy.deepcopy(value))
    # The callback retains its live Driver, engine and queued envelopes. It is
    # recorder plumbing, never an expectation input. Frozen replays need none.
    result.response_observer = None
    result.validated_input = None
    result.validated_record = None
    return result


def evaluate(oracle, record, proofs=None):
    current = clone(oracle)
    current.lifecycle_errors = set()
    current._trace_validators = proofs is not None
    current._validator_proofs = {}
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
    if proofs is not None:
        proofs.update(current._validator_proofs)
    return expected, differences


VALIDATORS = ('script_differences', 'stage_claims', 'completion_errors', 'payload_claims',
              'filing_claims', 'transition', 'local.errors')


def check(label, oracle, record, states=None, candidates=None, statistics=None, partition=None):
    expected, errors = evaluate(oracle, record)
    counts, covered = {}, set()
    def all_candidates():
        yield from mutations(record, states)
        yield from snapshot_mutations(oracle, record, states)
        yield from coherent_mutations(oracle, record, states)
    states = states or state_vocabulary([record])
    if partition is not None:
        part, parts = partition
        assert parts > 0 and part in range(parts), ('Invalid alteration partition', partition)
    for ordinal, (field, kind, changed) in enumerate(all_candidates() if candidates is None else candidates):
        covered.add(field)
        if partition is not None and ordinal % parts != part:
            continue
        replay, value = changed if isinstance(changed, tuple) else (oracle, changed)
        own_proofs = {} if statistics is not None else None
        actual, differences = evaluate(replay, value, own_proofs)
        new = differences - errors
        if field.startswith('coherent/'):
            new = {(view, fact) for view, fact in new if fact.kind not in STRUCTURAL}
        counts[kind] = counts.get(kind, 0) + 1
        if statistics is not None:
            statistics['alterations'] = statistics.get('alterations', 0) + 1
            if actual != expected:
                statistics['changed'] = statistics.get('changed', 0) + 1
            if field.startswith('coherent/'):
                statistics['coherent'] = statistics.get('coherent', 0) + 1
            for validator in VALIDATORS:
                own = any(f in own_proofs.get(validator, set()) for _, f in new)
                if own:
                    statistics[validator + '.own_catches'] = statistics.get(validator + '.own_catches', 0) + 1
                    if actual != expected:
                        statistics[validator + '.changed'] = statistics.get(validator + '.changed', 0) + 1
        if actual != expected and not new:
            raise AssertionError(('Silent owner-state perturbation', label, field,
                                  'missing', sorted(expected - actual), 'extra', sorted(actual - expected)))
    if candidates is None:
        missing = (field_paths(record) | set(snapshot_fields(oracle))) - covered
        assert not missing, ('Unaudited decoded fields', label, sorted(missing))
    return counts
