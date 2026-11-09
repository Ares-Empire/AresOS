"""Read each public surface in isolation; drain and validate its own pages."""
from .model import Fact
from .records import canonical


def notice_facts(notice, record, oracle):
    occurrence = notice['operation_id']
    content = notice.get('untrusted_content', {})
    saved = record.rows.get('notice:' + occurrence, {})
    source = saved.get('source_key') or content.get('intent_key')
    if content.get('check') == 'sent_copies':
        return {Fact('op:' + content['operation_id'], 'unchecked')}
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
        return {Fact(source, 'recovery')}
    kind = saved.get('check_kind', 'rename' if source.startswith('mail:rename:') else 'filing')
    evidence = next((f.detail for f in oracle.detected if f.occurrence == occurrence), '')
    # Public catalogues disclose count/role, not full server identities. Exact
    # evidence stays in the independent fingerprint and location pages.
    if kind == 'sent_copies':
        evidence = canonical({'count': content.get('message_count')})
    elif kind in {'rename', 'filing'}:
        reason = content.get('reason', '')
        evidence = canonical({'role': 'Trash' if 'Trash' in reason else 'Drafts' if 'inside Drafts' in reason else 'ordinary'})
    result = {Fact(source, kind, occurrence, evidence)}
    if content.get('unresolved_roles') or content.get('scan_complete') is False:
        result.add(Fact(source, 'recovery'))
    return result


def pending_facts(page):
    return {Fact('op:' + row['operation_id'], 'pending', detail=row['state']) for row in page.get('items', [])}


def pages(read, action, arguments=None, section='data'):
    args, seen, restarts = dict(arguments or {}), set(), 0
    while True:
        reply = read(action, args)
        page = reply.get(section, {'items': [], 'total': 0, 'cursor': None, 'unavailable': reply.get('error', {}).get('code', 'missing')})
        if page.get('page_changed'):
            restarts += 1
            assert restarts <= 3, ('Nonconvergent changed catalogue', action)
            seen.clear()
        yield page
        cursor = page.get('cursor')
        if cursor is None:
            break
        assert cursor not in seen, ('Cursor did not advance', action, cursor)
        seen.add(cursor)
        assert len(seen) <= 20000, ('Unbounded page traversal', action)
        args['cursor'] = cursor


def compare_views(read, oracle, snapshot, check, ordinary='mail_accounts'):
    """check(view, expected, actual) may classify one known assertion failure.

    Each view computes its own actual set. An earlier view's successful warning
    must never be used to fill a later view. Passive disclosure is checked first,
    before explicit reads can recreate evidence. All log and pending pages run.
    """
    record = snapshot()
    expected = oracle.expected(record)
    reply = read(ordinary, {})
    page = reply.get('pending', {})
    actual = pending_facts(page)
    for n in page.get('notices', []):
        actual |= notice_facts(n, record, oracle)
    # Pending envelopes are a bounded first page with explicit continuation.
    exp_pending = {f for f in expected if f.kind == 'pending'}
    exp_notices = expected - exp_pending
    limit = len(page.get('items', [])) + (page.get('total', 0) - len(page.get('items', [])))
    check('passive.pending-count', {Fact('count', 'count', detail=str(len(exp_pending)))},
          {Fact('count', 'count', detail=str(limit))})
    if len(exp_pending) <= len(page.get('items', [])):
        check('passive.pending', exp_pending, {f for f in actual if f.kind == 'pending'})
    if len(exp_notices) <= 3:
        check('passive.notices', exp_notices, {f for f in actual if f.kind != 'pending'})
    else:
        count = len(page.get('notices', [])) + page.get('notices_more', {}).get('count', 0)
        check('passive.notice-count', {Fact('count', 'count', detail=str(len(exp_notices)))},
              {Fact('count', 'count', detail=str(count))})
    for view, action in [('control_pending', 'control_pending'), ('aresos log', 'control_log'),
                         ('mail catalogue', 'mail_filing_notices')]:
        actual_pending, actual_notices = set(), set()
        for page in pages(read, action, {'limit': 1} if action.startswith('control_') else {}):
            record = snapshot()
            expected = oracle.expected(record, live=True, app='mail' if action == 'mail_filing_notices' else None)
            if page.get('page_changed'):
                actual_pending, actual_notices = set(), set()
            if action == 'control_pending':
                actual_pending |= pending_facts(page)
            notices = page.get('items', []) if action == 'mail_filing_notices' else page.get('notices', [])
            for n in notices:
                actual_notices |= notice_facts(n, record, oracle)
        if action != 'mail_filing_notices' and len(expected - {f for f in expected if f.kind == 'pending'}) > 3:
            wanted_head = sorted((f for f in expected if f.kind != 'pending'),
                key=lambda f: (record.rows.get('notice:' + f.occurrence, {}).get('created_at', 0), f.occurrence), reverse=True)[:3]
            check(view + '.notice-head', set(wanted_head), actual_notices)
        if action == 'control_pending':
            check(view + '.pending', {f for f in expected if f.kind == 'pending'}, actual_pending)
        wanted = {f for f in expected if f.kind != 'pending'}
        # Log/pending use the catalogue continuation for notices beyond three;
        # its pages are read for THIS view, with no union from another view.
        if action != 'mail_filing_notices' and len(wanted) > 3:
            actual_notices = set()
            for page in pages(read, 'mail_filing_notices'):
                record = snapshot()
                expected = oracle.expected(record, live=True)
                for n in page['items']:
                    actual_notices |= notice_facts(n, record, oracle)
            wanted = {f for f in expected if f.kind != 'pending'}
        check(view + '.notices', wanted, actual_notices)
