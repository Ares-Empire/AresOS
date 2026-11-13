"""Read each public surface in isolation; drain and validate its own pages."""
import json
import re
from .model import Fact
from .records import canonical, fingerprint, visible


def compare_proofs(oracle, record, check, after_sequence=0, context=True):
    """The sweep and alteration test deliver record defects to one checker."""
    expected = set()
    for view, compute in [('expectations', lambda: oracle.expected(record)),
                          ('completion', lambda: oracle.completion_errors(record)),
                          *([('R2.context-before-command', lambda: oracle.context_errors() | oracle.local_context_errors(record, after_sequence))] if context else [])]:
        try:
            value = compute()
            if view == 'expectations':
                expected = value
            else:
                if view == 'completion' and getattr(oracle, '_trace_validators', False):
                    oracle._validator_proofs.setdefault('completion_errors', set()).update(value)
                check(view, set(), value)
        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
            check('record-format.' + view, set(), {Fact('record', 'invalid-record', detail=type(error).__name__)})
    check('clean-result-proof', set(), oracle.invalid_clean_results)
    check('lifecycle-proof', set(), oracle.lifecycle_errors)
    return expected


def notice_facts(notice, record, oracle):
    occurrence = notice['operation_id']
    content = notice.get('untrusted_content', {})
    if occurrence == 'background-storage':
        reason = content.get('reason', '')
        cause = 'storage_limit' if 'Disk full or storage quota exhausted' in reason else 'storage_error' if 'Storage I/O failed' in reason else 'unknown'
        return {Fact('background:storage', 'background-storage', occurrence, cause)}
    saved = record.rows.get('notice:' + occurrence, {})
    source = saved.get('source_key') or content.get('intent_key')
    if content.get('check') == 'sent_copies':
        return {Fact('op:' + content['operation_id'], 'unchecked-handle', occurrence), Fact('op:' + content['operation_id'], 'unchecked'), Fact('op:' + content['operation_id'], 'unchecked-context', detail=canonical({'app': notice.get('app'), 'state': notice.get('state'), 'operation_identity': content.get('operation_id') == content['operation_id'], 'check': content.get('check'), 'not_yet_checked': 'not yet checked' in content.get('reason', '')}))}
    if source is None and content.get('operation_id'):
        source = 'op:' + content['operation_id']
    if source is None:
        # Opaque recovery IDs are bound only to independently decoded sources.
        for key, row in record.rows.items():
            if isinstance(row, dict) and row.get('id') == occurrence and key.startswith(('intent:', 'mail:filing:', 'mail:rename:')):
                source = key
                break
    if source is None:
        return {Fact('unbound:' + occurrence, 'unexpected')}
    if content.get('recovery_warning') or content.get('check_open') or saved.get('check_kind') == 'recovery':
        return {Fact(source, 'recovery-handle', occurrence), Fact(source, 'recovery'), Fact(source, 'recovery-context', detail=canonical({'app': notice.get('app'), 'state': notice.get('state'), 'intent_identity': content.get('intent_key') == source, 'reason_present': bool(content.get('reason', '').strip())}))}
    kind = saved.get('check_kind', 'rename' if source.startswith('mail:rename:') else 'filing')
    evidence = next((f.detail for f in oracle.detected if f.occurrence == occurrence), '')
    # Public catalogues disclose count/role, not full server identities. Exact
    # evidence stays in the independent fingerprint and location pages.
    if kind == 'sent_copies':
        evidence = canonical({'count': content.get('message_count')})
    elif kind in {'rename', 'filing'}:
        reason = content.get('reason', '')
        role_name = r'(?:Sent|Drafts|Trash|Junk|Archive|All|Flagged|Important)'
        context = oracle.warning_contexts.get(source, {})
        target = context.get('target', '')
        shown = target[:64] + ('…' if len(target) > 64 else '')
        prefix = r'inside ' if kind == 'rename' else r'(?:which is now |The target ' + re.escape(shown) + r' is now )'
        # Direct SPECIAL-USE flags retain their slash, doubled by public
        # escaping. Ancestor roles are displayed as bare names.
        role = r'\\{0,2}' + role_name
        matches = re.findall(prefix + r'(' + role + r'(?:, ?' + role + r')*)', reason)
        names = sorted(set(re.findall(role_name, ' '.join(matches))))
        evidence = canonical({'role': ', '.join(names) if names else 'unverified' if 'unverified role' in reason else 'ordinary'})
    result = {Fact(source, kind, occurrence, evidence)}
    expected_meta = next((json.loads(f.detail) for f in oracle.expected_context_facts if f.occurrence == occurrence), None) if hasattr(oracle, 'expected_context_facts') else None
    if expected_meta is None:
        context = oracle.warning_contexts.get(source, {})
        fields = {'app', 'state', 'intent_identity', 'preserves_messages'}
        fields |= {'operation_identity', 'message_count', 'reason_family'} if kind == 'sent_copies' else {'filing_identity'}
        if kind == 'rename' and 'message_count' in context or kind == 'filing' and context.get('sources'):
            fields |= {'message_count', 'folders', 'folders_more', 'folders_more_text'}
    else:
        fields = set(expected_meta)
    reason = content.get('reason', '')
    values = {'app': notice.get('app'), 'state': notice.get('state'), 'intent_identity': content.get('intent_key') == source,
              'preserves_messages': 'nothing' in reason.lower() and 'deleted' in reason.lower(),
              'operation_identity': content.get('operation_id') == source.removeprefix('op:'),
              'filing_identity': content.get('filing_id') == occurrence,
              'message_count': content.get('message_count'), 'folders': content.get('folders'),
              'folders_more': content.get('folders_more'), 'folders_more_text': content.get('folders_more_text'),
              'reason_family': 'sent_copies' if str(content.get('message_count')) + ' copies' in reason and 'Sent' in reason else 'other'}
    result.add(Fact(source, 'notice-context', occurrence, canonical({field: values[field] for field in fields})))
    if content.get('unresolved_roles') or content.get('scan_complete') is False:
        result.add(Fact(source, 'recovery-handle', occurrence))
        result.add(Fact(source, 'recovery', occurrence))
        result.add(Fact(source, 'recovery-context', occurrence, canonical({'app': notice.get('app'), 'state': notice.get('state'), 'intent_identity': content.get('intent_key') == source, 'reason_present': bool(content.get('reason', '').strip())})))
    return result


def pending_facts(page):
    result = {Fact('op:' + row['operation_id'], 'pending', detail=canonical({'state': row['state'], 'reason': 'RESTORED_EVIDENCE' if 'restored' in row.get('reason', '').lower() and any(word in row.get('reason', '').lower() for word in ('newer', 'missing')) else row.get('reason')})) for row in page.get('items', [])}
    for row in page.get('items', []):
        for kind in ('expired', 'cancelled'):
            if kind + ':' in row.get('reason', '').lower():
                result.add(Fact('op:' + row['operation_id'], 'operation-notice', row['operation_id'], kind))
    return result


def pending_page(rows, expected):
    sources = {fact.source for fact in rows}
    return set(rows) | {fact for fact in expected if fact.kind == 'operation-notice' and fact.source in sources}


def restart_count(count, label):
    count += 1
    assert count <= 3, ('Nonconvergent changed catalogue', label)
    return count


def pages(read, action, arguments=None, section='data'):
    args, seen, restarts = dict(arguments or {}), set(), 0
    while True:
        reply = read(action, args)
        page = reply.get(section, {'items': [], 'total': 0, 'cursor': None, 'unavailable': reply.get('error', {}).get('code', 'missing')})
        if page.get('page_changed'):
            restarts = restart_count(restarts, action)
            seen.clear()
        yield page
        cursor = page.get('cursor')
        if cursor is None:
            break
        assert cursor not in seen, ('Cursor did not advance', action, cursor)
        seen.add(cursor)
        assert len(seen) <= 20000, ('Unbounded page traversal', action)
        args['cursor'] = cursor


def source_order(record, source):
    known = next(((event['time'], event['seq']) for event in record.events if event['set'].get(source) is not None), None)
    if known is None and source.startswith('op:'):
        known = next(((fence['time'], fence['seq']) for fence in record.fences if any(op['id'] == source[3:] for op in fence.get('operations', []))), None)
    return known or (0, 0)


def source_app(record, source):
    app = record.rows.get(source, {}).get('app')
    if app is None and source.startswith('op:'):
        action = next((op.get('description', {}).get('action', '') for fence in reversed(record.fences) for op in fence.get('operations', []) if op['id'] == source[3:]), '')
        app = action.split('_', 1)[0]
    return app


def ordered_pending(record, expected, app=None):
    return sorted((f for f in expected if f.kind == 'pending' and
                   (app is None or source_app(record, f.source) == app)),
                  key=lambda f: (source_order(record, f.source)[0], f.source))


def notice_identity(record, fact):
    if fact.occurrence:
        return fact.occurrence
    source = fact.source
    row = record.rows.get(source, {})
    if fact.kind in {'unchecked', 'unchecked-context'}:
        return 'sent-check-' + fingerprint(source.removeprefix('op:'))[:32]
    if source.startswith(('op:', 'export:')):
        return 'recovery-' + source.split(':', 1)[1]
    if source.startswith(('mail:filing:', 'mail:rename:')):
        identity = row.get('id', source.rsplit(':', 1)[1])
        if record.rows.get('notice:' + identity, {}).get('ack'):
            return 'check-' + fingerprint(source)[:32]
        return identity
    if source.startswith(('mail:account:', 'legacy-intent:')):
        return 'recovery-' + fingerprint(source)[:32]
    return row.get('id', source)


def ordered_notices(record, expected, app=None):
    def order(fact):
        identity = notice_identity(record, fact)
        saved = record.rows.get('notice:' + identity, {})
        created = saved.get('created_at')
        if created is None:
            created = int(source_order(record, fact.source)[0] * 1_000_000_000)
        return created, identity
    groups = {}
    for fact in expected:
        if fact.kind not in {'pending', 'operation-notice'} and (app is None or record.rows.get(fact.source, {}).get('app', 'mail') == app):
            family = 'unchecked' if fact.kind.startswith('unchecked') else 'recovery' if fact.kind.startswith('recovery') else ''
            handle = next((f.occurrence for f in expected if f.source == fact.source and f.kind == family + '-handle'), None)
            group = handle or notice_identity(record, fact)
            groups.setdefault(group, set()).add(fact)
    return sorted(groups.values(), key=lambda group: max(order(f) for f in group), reverse=True)


def count_fact(value):
    return {Fact('catalogue', 'count', detail=str(value))}


def audit_fact(event, expected=False):
    entry = {k: event.get(k) for k in ('seq', 'time', 'action', 'summary', 'outcome', 'operation_id')}
    content = event.get('untrusted_content')
    if expected and event['action'].startswith('mail_'):
        entry['summary'] = 'Mail audit event'
        content = dict(content or {})
        if event['action'] in {'mail_move', 'mail_copy'}:
            filing = content.get('filing', {})
            if 'records' in filing or 'locations' in filing:
                content = {'filing': {'filing_id': filing['id'], 'state': filing['state'], 'message_count': len(filing['sources']), 'locations_action': 'mail_filing_locations'}}
            elif 'references' in content:
                content = {'message_count': len(content['references']), 'locations_action': 'mail_filing_locations'}
        content = {'summary': visible(event['summary']), **content}
    if content is not None:
        entry['untrusted_content'] = content
    return Fact('event:' + str(event['seq']), event['action'], detail=canonical(entry))


def compare_status(reply, oracle, record, call, check, label):
    status = 'allowed' if reply.get('ok') is True else reply.get('error', {}).get('code', 'missing-status')
    permitted = oracle.permitted_status(record, call)
    check(label + '.status', {Fact('request', 'permitted', detail=canonical(sorted(permitted)))},
          {Fact('request', 'permitted', detail=canonical(sorted(permitted)))} if status in permitted else {Fact('request', status)})


def compare_envelope(label, reply, record, oracle, expected, check, app=None):
    record = oracle.projection(record)
    check(label + '.present', {Fact('response', 'pending-envelope')},
          {Fact('response', 'pending-envelope')} if isinstance(reply.get('pending'), dict) else set())
    page = reply.get('pending', {})
    wanted = ordered_pending(record, expected, app)
    check(label + '.pending-head', pending_page(wanted[:5], expected), pending_facts(page))
    check(label + '.pending-total', count_fact(len(wanted)), count_fact(page.get('total', 0)))
    check(label + '.pending-continuation', {Fact('pending', 'cursor')} if len(wanted) > 5 else set(),
          {Fact('pending', 'cursor')} if page.get('cursor') else set())
    notice_head(label, page, record, oracle, expected, check)


def notice_head(label, page, record, oracle, expected, check):
    record = oracle.projection(record)
    wanted = ordered_notices(record, expected)
    actual = [fact for n in page.get('notices', []) for fact in notice_facts(n, record, oracle)]
    check(label + '.restore-lock', {Fact('restore', 'locked', detail=str(record.locked))},
          {Fact('restore', 'locked', detail=str(page.get('restore_required', False)))})
    check(label + '.notice-head', set().union(*wanted[:3]), set(actual))
    check(label + '.notice-duplicates', set(), {Fact('catalogue', 'duplicate', detail=repr(f)) for f in actual if actual.count(f) > 1})
    count = len(page.get('notices', [])) + page.get('notices_more', {}).get('count', 0)
    check(label + '.notice-count', count_fact(len(wanted)), count_fact(count))
    advertised = page.get('notices_more', {}).get('action')
    check(label + '.notice-continuation', {Fact('catalogue', 'action', detail='mail_filing_notices')} if len(wanted) > 3 else set(),
          {Fact('catalogue', 'action', detail=advertised)} if advertised else set())
    return advertised


def compare_views(read, oracle, snapshot, check, ordinary='mail_accounts'):
    """No view borrows another view's values. Validate heads and every page.

    Log and pending advertise a named notice continuation rather than a notice
    cursor. Validate their head/count/advertisement first, then follow exactly
    that advertised action as part of that view's disclosure.
    """
    def notices(page, record):
        result = []
        for notice in page.get('notices', []):
            result.extend(notice_facts(notice, record, oracle))
        return result

    def head(label, page, record, expected):
        return notice_head(label, page, record, oracle, expected, check)

    def catalogue(label, action):
        offset, seen = 0, []
        for number, page in enumerate(pages(read, action)):
            record = snapshot()
            expected = oracle.expected(record, live=True, app='mail' if action == 'mail_filing_notices' else None)
            record = oracle.projection(record)
            if page.get('page_changed'):
                offset, seen = 0, []
            wanted = ordered_notices(record, expected, app='mail' if action == 'mail_filing_notices' else None)
            actual = []
            for notice in page.get('items', []):
                actual.extend(notice_facts(notice, record, oracle))
            check(label + '.page', set().union(*wanted[offset:offset + 3]), set(actual))
            check(label + '.total', count_fact(len(wanted)), count_fact(page.get('total', 0)))
            check(label + '.duplicates', set(), {Fact('catalogue', 'duplicate', detail=repr(f)) for f in actual if f in seen or actual.count(f) > 1})
            seen.extend(actual)
            offset += len(page.get('items', []))
        check(label + '.complete', set().union(*wanted), set(seen))

    record = snapshot()
    expected = oracle.expected(record)
    record = oracle.projection(record)
    reply = read(ordinary, {})
    page = reply.get('pending', {})
    wanted = ordered_pending(record, expected, app=ordinary.split('_', 1)[0])
    check('passive.pending-head', pending_page(wanted[:5], expected), pending_facts(page))
    check('passive.pending-total', count_fact(len(wanted)), count_fact(page.get('total', 0)))
    check('passive.pending-continuation', {Fact('pending', 'cursor')} if len(wanted) > 5 else set(),
          {Fact('pending', 'cursor')} if page.get('cursor') else set())
    if page.get('cursor'):
        args, offset, visited = {'cursor': page['cursor']}, 5, set()
        while True:
            continuation = read('control_pending', args).get('data', {})
            record = snapshot()
            fresh = oracle.expected(record, live=True)
            record = oracle.projection(record)
            wanted = ordered_pending(record, fresh, app=ordinary.split('_', 1)[0])
            # No pending membership/state changed between the envelope and
            # this continuation; a scope mismatch must not pretend it did.
            check('passive.pending-page-changed', set(), {Fact('pending', 'page_changed')} if continuation.get('page_changed') else set())
            if continuation.get('page_changed'):
                offset = 0
            check('passive.pending-page', pending_page(wanted[offset:offset + 5], fresh), pending_facts(continuation))
            check('passive.pending-page-total', count_fact(len(wanted)), count_fact(continuation.get('total', 0)))
            offset += len(continuation.get('items', []))
            cursor = continuation.get('cursor')
            if cursor is None:
                break
            assert cursor not in visited, 'Passive pending continuation loop'
            visited.add(cursor)
            args['cursor'] = cursor
    advertised = head('passive', page, record, expected)
    if advertised:
        catalogue('passive.advertised', advertised)
    for view, action in [('control_pending', 'control_pending'), ('aresos log', 'control_log')]:
        offset, seen, audit_seen, advertised = 0, [], [], None
        for page in pages(read, action, {'limit': 1 if action == 'control_pending' else 5}):
            record = snapshot()
            expected = oracle.expected(record, live=True)
            record = oracle.projection(record)
            if page.get('page_changed'):
                offset, seen, audit_seen = 0, [], []
            if action == 'control_pending':
                wanted = ordered_pending(record, expected)
                actual = list(pending_facts(page))
                check(view + '.page', pending_page(wanted[offset:offset + 1], expected), set(actual))
                check(view + '.total', count_fact(len(wanted)), count_fact(page.get('total', 0)))
                check(view + '.duplicates', set(), {Fact('pending', 'duplicate', detail=repr(f)) for f in actual if f in seen})
                seen.extend(actual)
            else:
                # Audit inclusion is determined by the test clock and committed
                # events, independent of the service's iterator/filter.
                import time
                day = time.strftime('%Y-%m-%d', time.localtime())
                audit = sorted((e for e in record.events if e['seq'] in record.working_sequences and time.strftime('%Y-%m-%d', time.localtime(e['time'])) == day), key=lambda e: (e['time'], e['seq']))
                wanted = [audit_fact(e, expected=True) for e in audit]
                actual = [audit_fact(e) for e in page.get('items', [])]
                check(view + '.page', set(wanted[offset:offset + 5]), set(actual))
                check(view + '.total', count_fact(len(wanted)), count_fact(page.get('total', 0)))
                check(view + '.duplicates', set(), {Fact('audit', 'duplicate', detail=repr(f)) for f in actual if f in audit_seen or actual.count(f) > 1})
                audit_seen.extend(actual)
            offset += len(page.get('items', []))
            advertised = head(view, page, record, expected) or advertised
        check(view + '.complete', pending_page(wanted, expected) if action == 'control_pending' else set(wanted), set(seen if action == 'control_pending' else audit_seen))
        if advertised:
            catalogue(view + '.advertised', advertised)
    catalogue('mail catalogue', 'mail_filing_notices')


def retained_role(source, role, record, page):
    """D3 permits a committed generic warning only while its check is open."""
    facts = set()
    check = record.rows.get(source, {})
    open_check = check.get('state') == 'started' or check.get('check_open')
    for notice in page.get('items', []):
        content = notice.get('untrusted_content', {})
        saved = record.rows.get('notice:' + str(notice.get('operation_id')), {})
        belongs = saved.get('source_key', content.get('intent_key')) == source
        if belongs and 'inside ' + role in content.get('reason', ''):
            facts.add(Fact(source, 'observed-role', detail=role))
            continue
        saved = record.rows.get('notice:' + str(notice.get('operation_id')), {})
        stored = saved.get('untrusted_content', {})
        reason = stored.get('reason', '')
        if (open_check and not saved.get('ack') and saved.get('source_key', stored.get('intent_key')) == source and
                content == stored and 'evidence was seen' in reason.lower() and
                "couldn't be recorded" in reason.lower() and 'check ' + role.lower() in reason.lower()):
            facts.add(Fact(source, 'observed-role', detail=role))
    return facts
