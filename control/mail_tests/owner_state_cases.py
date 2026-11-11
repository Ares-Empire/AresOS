"""Focused matrix contracts in addition to the exhaustive storage boundaries."""
from contextlib import contextmanager
import copy
import errno
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.engine import Engine
from aresos_control.mail.dkim import verify_one_click as verify_dkim
from owner_state_oracle.driver import Driver
from owner_state_oracle.model import Fact
from owner_state_oracle.records import canonical
from test_owner_state_sweep import OwnerScenario


def run(gaps):
    def compare(scenario, driver, name):
        driver.alias_callback = gaps.bind
        gaps.bind(driver.snapshot())
        driver.compare(gaps.checker('contract/' + name))

    # Real clean outcomes: no duplicate-generating APPEND/race in these cases.
    for flow in ('send', 'filing_move', 'filing_copy', 'filing_rename', 'delete_trash', 'delete_permanent',
                 'testapp_send', 'repair', 'settlement', 'status'):
        s = OwnerScenario(flow)
        gaps.aliases = {}
        try:
            f, stack = s.fixture, s.stack
            if flow in {'status', 'settlement'}:
                # Their sweep variants deliberately seed duplicate Sent mail.
                # The ordinary quiet contract has one independently visible copy.
                f.imap.boxes['Sent'].pop(2)
            if flow == 'send':
                def append(account, folder, raw, flags=None):
                    s.remote['APPEND'] += 1
                    f.imap.boxes[folder][1] = raw
                    return {'account': account['id'], 'folder': folder, 'uidvalidity': f.imap.validities[folder], 'uid': 1, 'message_id': f.mail.message_id(s.operation_id)}
                stack.enter_context(patch.object(f.mail, 'append', side_effect=append))
            if flow.startswith('filing_'):
                uid, roles = f.imap.uid, copy.deepcopy(f.imap.roles)
                def ordinary(command, *args):
                    result = uid(command, *args)
                    if command in {'MOVE', 'COPY'}:
                        f.imap.roles = copy.deepcopy(roles)
                        if flow == 'filing_copy':
                            f.imap.roles['Other'] = []
                            f.imap.boxes['Other'] = {}
                            f.imap.validities['Other'] = 999
                    return result
                stack.enter_context(patch.object(f.imap, 'uid', side_effect=ordinary))
                if flow == 'filing_rename':
                    rename = f.imap.rename
                    def ordinary_rename(source, target):
                        result = rename(source, target)
                        current = copy.deepcopy(roles)
                        current[target.strip('"')] = current.pop(source.strip('"'))
                        f.imap.roles = current
                        return result
                    stack.enter_context(patch.object(f.imap, 'rename', side_effect=ordinary_rename))
            d = Driver(s)
            with d.observe():
                reply = s.call()
            d.reply(reply)
            assert reply['ok'], reply
            assert (reply['data'].get('operation') or reply['data'])['state'] == 'done', reply
            assert not reply['pending'].get('notices'), reply
            compare(s, d, 'quiet-' + flow)
            if flow in {'testapp_send', 'repair', 'settlement', 'status'}:
                assert not any(key.startswith('contract/quiet-' + flow + '/') for key in gaps.entries), (flow, gaps.entries)
            assert not [f for f in d.oracle.expected(d.snapshot()) if f.kind not in {'pending'}], (flow, d.oracle.expected(d.snapshot()), d.oracle.lifecycle_errors)
            assert not d.oracle.lifecycle_errors, (flow, d.oracle.lifecycle_errors)
            assert not d.oracle.invalid_clean_results, (flow, d.oracle.invalid_clean_results)
            assert not d.oracle.completion_errors(d.snapshot()), flow
            if flow == 'send':
                key = 'op:' + s.operation_id
                old = copy.deepcopy(d.snapshot().rows[key])
                for field in ('context', 'sent_copy_check', 'warning_checks'):
                    old.pop(field, None)
                # Store.write preserves R2 context by design. The fixture's
                # scripted input must describe the exact legacy migration it
                # actually requests, including that additive context.
                for field in ('context', 'context_version'):
                    if field in d.snapshot().rows[key]:
                        old[field] = copy.deepcopy(d.snapshot().rows[key][field])
                d.fixture_input({key: old}, 'Documented finished legacy operation')
                f.engine.close()
                s.bind(Engine(f.root / 'state', f.root / 'evidence'))
                compare(s, d, 'legacy-finished-send')
                assert not [fact for fact in d.oracle.expected(d.snapshot()) if fact.kind != 'pending']
        finally:
            s.close()

    # Changed sets, acknowledgement, committed clean and recurrence. Compare
    # every view before a second status call can recreate any missing warning.
    s = OwnerScenario('status')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        with d.observe():
            reply = s.call()
        d.reply(reply)
        assert len(f.imap.boxes['Sent']) == 2
        compare(s, d, 'lifecycle-first')
        notices = [f for f in d.oracle.expected(d.snapshot()) if f.kind == 'sent_copies']
        assert len(notices) == 1
        first = notices[0].occurrence
        f.data('notice_ack', {'operation_id': first})
        compare(s, d, 'lifecycle-ack')
        f.imap.boxes['Sent'][3] = f.imap.boxes['Sent'].pop(2)
        with d.observe():
            reply = s.call()
        d.reply(reply)
        compare(s, d, 'lifecycle-changed-set')
        changed = [fact for fact in d.oracle.expected(d.snapshot()) if fact.kind == 'sent_copies']
        assert len(changed) == 1 and changed[0].occurrence != first
        raw = f.imap.boxes['Sent'].pop(3)
        with d.observe():
            reply = s.call()
        d.reply(reply)
        compare(s, d, 'lifecycle-clean-retains-unacked')
        assert changed[0] in d.oracle.expected(d.snapshot())
        f.imap.boxes['Sent'][3] = raw
        with d.observe():
            reply = s.call()
        d.reply(reply)
        compare(s, d, 'lifecycle-recurrence')
        assert len([fact for fact in d.oracle.expected(d.snapshot()) if fact.kind == 'sent_copies']) == 2
        # Archive and expiry cannot remove an unacknowledged occurrence.
        archive_args = {'before': time.time() - .001, 'confirm': 'archive finished history'}
        with d.observe_view('control_archive', archive_args):
            archived = f.engine.request({'v': 1, 'method': 'call', 'action': 'control_archive',
                              'arguments': archive_args}, True)
        d.reply(archived)
        compare(s, d, 'lifecycle-archive')
        with patch('aresos_control.retention.time.time', return_value=time.time() + 90001):
            f.engine.expire()
        compare(s, d, 'lifecycle-expiry')
        f.engine.close()
        s.bind(Engine(f.root / 'state', f.root / 'evidence'))
        compare(s, d, 'lifecycle-restart')
    finally:
        s.close()

    # Conservative old intents remain readable; finished old operations add no
    # interruption warning. No production recovery selector supplies expected IDs.
    s = OwnerScenario('send')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        d.fixture_input({'intent:old': {'id': 'old', 'action': 'mail_flag', 'app': 'mail', 'state': 'started'}},
                        'Documented old context-free intent')
        f.engine.close()
        s.bind(Engine(f.root / 'state', f.root / 'evidence'))
        compare(s, d, 'legacy-open-intent')
        f.data('notice_ack', {'operation_id': 'old'})
        compare(s, d, 'legacy-ack')
        approval = f.approval('send', f.compose())
        new_id = approval['operation_id']
        assert f.engine.store.get('op:' + new_id)['state'] == 'reserved'
        compare(s, d, 'legacy-new-reservation')
        cancelled = f.call('operation_cancel', {'operation_id': new_id})
        assert cancelled['ok'] and cancelled['data']['operation']['state'] == 'failed', cancelled
        assert cancelled['data']['operation']['reason'] == 'cancelled: nothing submitted', cancelled
        compare(s, d, 'legacy-new-cancel')
    finally:
        s.close()

    # Refusal families: independently authored expected codes, on the same live
    # instance. These are current request predicates, never yesterday's refusal.
    s = OwnerScenario('send')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}
        cases = [
            ('permission', 'mail_account_settings', {'id': 'box', 'format': 'plain'}, 'permission_denied'),
            ('cursor', 'mail_filing_notices', {'cursor': 'malformed'}, 'stale_reference'),
            ('account', 'mail_read', {'reference': {**ref, 'account': 'missing'}}, 'account_unavailable'),
            ('reference', 'mail_read', {'reference': {**ref, 'uidvalidity': 999}}, 'stale_reference'),
            ('role', 'mail_move', {'references': [ref], 'target': 'Trash'}, 'refused'),
            ('input', 'mail_compose', {'account': 'box', 'to': ['peer@mail.invalid'], 'text': 'Exact', 'subject': 'bad\nsubject'}, 'invalid_input'),
            ('file-proxy', 'testapp_file_save', {'sha256': '0' * 64, 'folder': '/synthetic', 'name': 'x'}, 'proxy_required'),
        ]
        for family, action, args, expected in cases:
            with d.observe_view(action, args):
                result = f.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args})
            d.reply(result)
            assert not result['ok'], (family, result)
            assert result['error']['code'] == expected, (family, result)
            compare(s, d, 'refusal-' + family)
        # Evidence unavailability is a read failure, with passive disclosures.
        with patch.object(f.mail.transport, 'imap', side_effect=OSError('Synthetic offline')), d.observe_view('mail_read', {'reference': ref}):
            result = f.call('read', {'reference': ref})
        d.reply(result)
        assert result['error']['code'] == 'transport_error', result
        compare(s, d, 'refusal-transport')
    finally:
        s.close()

    # A remote scan failure is distinct from a local result-write failure. Its
    # partial locations must page exactly and its check must remain open.
    s = OwnerScenario('filing_copy')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        uid, failed = f.imap.uid, [False]
        def interrupted(command, *args):
            if command == 'FETCH' and s.remote.get('COPY:1') and not failed[0]:
                failed[0] = True
                raise OSError('Synthetic interrupted location scan')
            return uid(command, *args)
        with patch.object(f.imap, 'uid', side_effect=interrupted), d.observe():
            result = s.call()
        d.reply(result)
        assert failed[0] and s.remote.get('COPY:1'), (failed, s.remote)
        assert result['ok'] and result['data']['state'] == 'partial', result
        compare(s, d, 'scan-incomplete')
    finally:
        s.close()

    # The account result records qualification and a bounded Sent caveat, while
    # CREATE/APPEND/probe DELETE and exact cleanup all have separate server logs.
    s = OwnerScenario('onboarding')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        with d.observe():
            result = s.call()
        d.reply(result)
        assert result['ok'], result
        commands = {e['command'] for e in d.oracle.servers}
        assert {'CREATE', 'APPEND', 'DELETE', 'STORE', 'EXPUNGE', 'DATA'} <= commands, commands
        account = d.snapshot().rows['mail:account:new']
        assert account['onboarded'] and account['sent_policy'] == 'client' and not account['ready'], account
        assert result['data']['notice'] and result['data']['probe_folder'], result
        compare(s, d, 'qualification-probes')
        f.engine.close()
        s.bind(Engine(f.root / 'state', f.root / 'evidence'))
        compare(s, d, 'qualification-probes-restart')
    finally:
        s.close()

    # Admission is a live predicate. Restore capacity without restarting or
    # replaying the uncertain remote action, then make a new harmless write.
    for flow in ('send', 'filing_move', 'attachment_export'):
        s = OwnerScenario(flow)
        gaps.aliases = {}
        try:
            f, d = s.fixture, Driver(s)
            before = (f.root / 'evidence/operations.jsonl').read_bytes()
            with patch.object(f.engine.store.ledger, 'admit', side_effect=Refused('storage_limit', 'Synthetic admission exhaustion')), d.observe():
                result = s.call()
            d.reply(result)
            assert not result['ok'] and result['error']['code'] == 'storage_limit', result
            assert not s.remote, s.remote
            assert (f.root / 'evidence/operations.jsonl').read_bytes() == before
            healthy = f.call('compose', {'account': 'box', 'to': ['peer@mail.invalid'], 'text': 'new local change'})
            assert healthy['ok'], healthy
            compare(s, d, 'admission-restored-' + flow)
        finally:
            s.close()

    s = OwnerScenario('filing_copy')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        response, uid, roles = f.imap.response, f.imap.uid, copy.deepcopy(f.imap.roles)
        def missing(name):
            if name == 'COPYUID':
                response(name)
                return name, [None]
            return response(name)
        def ordinary(command, *args):
            result = uid(command, *args)
            if command == 'COPY':
                f.imap.roles = copy.deepcopy(roles)
            return result
        with patch.object(f.imap, 'response', side_effect=missing), patch.object(f.imap, 'uid', side_effect=ordinary), d.observe():
            result = s.call()
        d.reply(result)
        assert result['ok'] and result['data']['state'] == 'partial', result
        assert any(e['command'] == 'COPY' and e.get('copyuid_delivered') is False for e in d.oracle.servers)
        compare(s, d, 'missing-copyuid')
    finally:
        s.close()

    s = OwnerScenario('status')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        with patch.object(f.engine.store.ledger, 'admit', side_effect=Refused('storage_limit', 'Synthetic refused reopen')), d.observe():
            result = s.call()
        d.reply(result, delivered=False)
        assert not result['ok']
        assert not any(e['command'] == 'SENT' for e in d.oracle.servers)
        f.engine.close()
        s.bind(Engine(f.root / 'state', f.root / 'evidence'))
        args = {'before': time.time() - .001, 'confirm': 'archive finished history'}
        with d.observe_view('control_archive', args):
            result = f.engine.request({'v': 1, 'method': 'call', 'action': 'control_archive', 'arguments': args}, True)
        d.reply(result)
        assert result['ok'], result
        assert 'op:' + s.operation_id in d.snapshot().rows
        assert any(e['command'] == 'SENT' and len(e['identities']) == 2 for e in d.oracle.servers)
        compare(s, d, 'review20-refused-reopen-archive')
    finally:
        s.close()

    s = OwnerScenario('filing_rename')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        write = f.engine.store.write
        def refuse_after_effect(*args, **kwargs):
            if s.remote:
                raise Refused('storage_limit', 'Synthetic refused rename result')
            return write(*args, **kwargs)
        with patch.object(f.engine.store, 'write', side_effect=refuse_after_effect), d.observe():
            result = s.call()
        d.reply(result, delivered=False)
        assert s.remote['RENAME'] == 1
        source = next(row for key, row in d.snapshot().rows.items() if key.startswith('mail:rename:'))
        f.engine.close()
        s.bind(Engine(f.root / 'state', f.root / 'evidence'))
        with patch.object(f.mail.transport, 'imap', side_effect=OSError('Synthetic offline')):
            f.data('notice_ack', {'operation_id': source['id']})
            with patch('aresos_control.retention.time.time', return_value=time.time() + 90001):
                f.engine.expire()
        compare(s, d, 'review21-ack-rename-expiry')
    finally:
        s.close()

    s = OwnerScenario('send')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        f.imap.roles['Drafts'] = []
        for index in range(4):
            target, identity = 'Target' + str(index), 'rename-' + str(index)
            f.imap.boxes[target], f.imap.roles[target], f.imap.validities[target] = {}, ['\\Trash'] if index == 0 else [], 100 + index
            d.fixture_input({'mail:rename:' + identity: {'id': identity, 'state': 'started', 'account': 'box',
                'source': 'Source', 'target': target, 'message_count': 1, 'roles_before': {}}}, 'Synthetic interrupted rename')
        compare(s, d, 'review21-four-renames-all-pages')
    finally:
        s.close()

    s = OwnerScenario('send')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        from aresos_control.mail.transport import Transport
        def tls_refusal():
            with Transport.smtp(f.mail.transport, {'smtp_tls': 'plaintext'}):
                raise AssertionError('Plain SMTP must never open')
        private = f.engine.blobs.put(b'Synthetic private composition', origin='composition_part')
        cases = [('credentials', lambda: f.mail.transport.password({'id': 'missing'}), 'account_password'),
                 ('tls', tls_refusal, 'refused'),
                 ('dkim', lambda: verify_dkim(f.imap.raw), 'unsubscribe_authentication'),
                 ('provenance', lambda: f.engine.blobs.require_origin(private, 'export'), 'file_refused')]
        for family, action, code in cases:
            d.oracle.call('fixture-' + family, {}, time.time(), {'fault': family})
            try:
                action()
            except Refused as error:
                assert error.code == code, (family, error.code)
                d.oracle.reply({'ok': False, 'error': {'code': error.code}})
            else:
                raise AssertionError('Refusal family unexpectedly accepted: ' + family)
            assert f.call('read', {'reference': {'account': 'box', 'folder': 'Source', 'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}})['ok']
            compare(s, d, 'refusal-' + family)
        capabilities = f.imap.capabilities
        f.imap.capabilities = ('MOVE',)
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}
        result = f.call('copy', {'references': [ref], 'target': 'Target'})
        assert not result['ok'] and result['error']['code'] == 'unsupported_server', result
        f.imap.capabilities = capabilities
        compare(s, d, 'refusal-capability')
    finally:
        s.close()

    for acknowledged in (False, True):
        s = OwnerScenario('filing_rename')
        gaps.aliases = {}
        try:
            f, d = s.fixture, Driver(s)
            import sqlite3
            from contextlib import closing
            backup = f.root / 'older.sqlite'
            with closing(sqlite3.connect(backup)) as db:
                f.engine.store.db.backup(db)
            with d.observe():
                result = s.call()
            d.reply(result)
            assert result['ok'] and s.remote['RENAME'] == 1
            compare(s, d, 'restore-before-' + str(acknowledged))
            occurrence = next(fact.occurrence for fact in d.oracle.expected(d.snapshot()) if fact.kind == 'rename')
            if acknowledged:
                f.data('notice_ack', {'operation_id': occurrence})
                compare(s, d, 'restore-ack-before')
            f.engine.close()
            (f.root / 'state/control.sqlite').write_bytes(backup.read_bytes())
            s.bind(Engine(f.root / 'state', f.root / 'evidence'))
            assert f.engine.store.locked
            confirmed = f.engine.request({'v': 1, 'method': 'call', 'action': 'control_restore_confirm',
                'arguments': {'confirm': 'invalidate earlier approvals'}}, True)
            assert confirmed['ok'], confirmed
            compare(s, d, 'restore-after-' + str(acknowledged))
            assert s.remote['RENAME'] == 1
        finally:
            s.close()

    # The first observed reply can itself be a restore. The driver must have
    # established the starting incomplete-account obligation before that call.
    s = OwnerScenario('send')
    gaps.aliases = {}
    try:
        import sqlite3
        from contextlib import closing
        f = s.fixture
        backup = f.root / 'before-account.sqlite'
        with closing(sqlite3.connect(backup)) as db:
            f.engine.store.db.backup(db)
        account = {**f.engine.store.get('mail:account:box'), 'id': 'new', 'onboarded': False, 'ready': False}
        f.engine.store.write({'mail:account:new': account}, 'fixture', 'Explicit initial incomplete account')
        d = Driver(s)
        f.engine.close()
        (f.root / 'state/control.sqlite').write_bytes(backup.read_bytes())
        s.bind(Engine(f.root / 'state', f.root / 'evidence'))
        d._snapshot_key = None
        assert f.engine.store.locked
        with d.observe_view('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}):
            restored = f.engine.request({'v': 1, 'method': 'call', 'action': 'control_restore_confirm',
                'arguments': {'confirm': 'invalidate earlier approvals'}}, True)
        d.reply(restored)
        assert restored['ok'], restored
        recovered = f.engine.store.get('mail:account:new')
        assert recovered is not None and recovered['id'] == 'new'
        assert not recovered['onboarded'] and not recovered['ready']
        assert any(fact.source == 'mail:account:new' and fact.kind == 'recovery' for fact in d.oracle.expected(d.snapshot()))
        compare(s, d, 'initial-account-first-reply-restore')
    finally:
        s.close()

    s = OwnerScenario('send')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        f.imap.roles['Trash'], f.imap.roles['Target'] = [], ['\\Trash']
        with d.observe_view('mail_account_folders', {'id': 'box'}):
            review = f.engine.request({'v': 1, 'method': 'call', 'action': 'mail_account_folders', 'arguments': {'id': 'box'}}, True)
        d.reply(review)
        assert review['ok'], review
        arguments = {'id': 'box', 'roles_hash': review['data']['roles_hash']}
        with d.observe_view('mail_account_folders', arguments):
            recorded = f.engine.request({'v': 1, 'method': 'call', 'action': 'mail_account_folders',
                'arguments': arguments}, True)
        d.reply(recorded)
        assert recorded['ok'], recorded
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}
        refused = f.call('move', {'references': [ref], 'target': 'Trash'})
        assert not refused['ok'] and refused['error']['code'] == 'refused', refused
        assert not s.remote, s.remote
        assert d.snapshot().rows['mail:account:box']['protected_special']['trash']
        compare(s, d, 'qualification-protected-roles')
    finally:
        s.close()

    s = OwnerScenario('testapp_send')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        f.approval('send', f.compose())
        arguments = {'refuse': [], 'failure': 'lost_answer'}
        with d.observe_view('testapp_fixture_configure', arguments):
            configured = f.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_fixture_configure',
                'arguments': arguments}, True)
        d.reply(configured)
        assert configured['ok'], configured
        with d.observe():
            result = s.call()
        d.reply(result)
        assert result['data']['operation']['state'] == 'unknown', result
        assert any(e['command'] == 'RECEIVE' and e['accepted'] and e['reply'] == 'lost' for e in d.oracle.servers)
        compare(s, d, 'mixed-app-lost-reply')
        f.engine.close()
        s.bind(Engine(f.root / 'state', f.root / 'evidence'))
        compare(s, d, 'mixed-app-restart')
    finally:
        s.close()

    s = OwnerScenario('testapp_send')
    gaps.aliases = {}
    try:
        f, d = s.fixture, Driver(s)
        with d.observe():
            result = s.call()
        d.reply(result)
        assert result['ok'] and result['data']['operation']['state'] == 'done', result
        assert any(event['command'] == 'RECEIVE' and event['accepted'] for event in d.oracle.servers)
        with patch.object(d.oracle, 'explicit_faults', {'read_storage': 'ENOSPC'}, create=True), patch.object(f.engine.receiver, 'evidence', side_effect=OSError(errno.ENOSPC, 'Synthetic evidence storage failure')):
            compare(s, d, 'testapp-status-schema-storage')
        assert any(call['action'] == 'testapp_operation_status' and
            call.get('result', {}).get('data', {}).get('evidence_error', {}).get('code') == 'storage_limit'
            for call in d.oracle.script)
        compare(s, d, 'testapp-status-schema-restored')
    finally:
        s.close()
