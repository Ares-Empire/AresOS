"""Review 14: interrupted writes preserve complete fences and storage errors."""
import errno
import json
import os
from contextlib import ExitStack
import sqlite3
from unittest.mock import patch

from aresos_control.common import Refused, storage_refusal
from aresos_control.engine import Engine
from aresos_control.results import RESTART_ADVICE
from support import EngineCase, message


class Journal22(EngineCase):
    def test_review22_short_commit_prepare_fails_and_full_replay_clears_latch(self):
        store = self.engine.store
        write = store.journal.write
        def short_commit(data):
            return write(data[:13]) if 'commit' in json.loads(data) else write(data)
        with patch.object(store.journal, 'write', side_effect=short_commit):
            result = self.call('testapp_prepare_send', message())
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'storage_limit')
        self.assertIn('Disk full', result['error']['message'])
        self.assertTrue(store.write_failed)
        before = (store.evidence_dir / 'operations.jsonl').read_bytes()
        self.assertTrue(before.endswith(b'\n'))
        self.assertNotIn('commit', json.loads(before.splitlines()[-1]))
        refused = self.call('testapp_prepare_send', message())
        self.assertEqual(refused['error']['code'], 'journal_incomplete')
        self.assertEqual(refused['error']['message'], RESTART_ADVICE)
        self.assertTrue(store.write_failed)
        self.assertEqual((store.evidence_dir / 'operations.jsonl').read_bytes(), before)
        self.restart()
        self.assertFalse(self.engine.store.write_failed)
        self.assertFalse(self.engine.store.locked)
        self.assertEqual(self.engine.store.committed, self.engine.store.sequence)
        self.reserve(subject='Full write after space returned')

    def test_review22_short_event_then_enospc_discards_partial_and_syncs(self):
        store = self.engine.store
        before = (store.evidence_dir / 'operations.jsonl').read_bytes()
        write = store.journal.write
        def interrupted(data):
            write(data[:13])
            raise OSError(errno.ENOSPC, 'Synthetic disk full after partial event')
        with patch.object(store.journal, 'write', side_effect=interrupted), \
             patch('aresos_control.storage.os.fsync', wraps=__import__('os').fsync) as sync:
            result = self.call('testapp_prepare_send', message())
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'storage_limit')
        self.assertIn('Disk full', result['error']['message'])
        self.assertFalse(store.write_failed)
        self.assertEqual((store.evidence_dir / 'operations.jsonl').read_bytes(), before)
        sync.assert_called_once_with(store.journal.fileno())
        self.reserve()

    def test_review22_zero_and_short_event_writes_are_not_success(self):
        for count in (0, 13):
            store = self.engine.store
            before = (store.evidence_dir / 'operations.jsonl').read_bytes()
            write = store.journal.write
            def short(data):
                return write(data[:count])
            with self.subTest(count=count), patch.object(store.journal, 'write', side_effect=short):
                result = self.call('testapp_prepare_send', message())
            self.assertEqual(result['error']['code'], 'storage_limit', result)
            self.assertFalse(store.write_failed)
            self.assertEqual((store.evidence_dir / 'operations.jsonl').read_bytes(), before)
            self.reserve()

    def test_review22_startup_truncates_torn_event_or_commit_and_replays_prepared(self):
        for tail in ('event', 'commit'):
            with self.subTest(tail=tail):
                approval = self.reserve()
                self.engine.close()
                path = self.root / 'independent/operations.jsonl'
                rows = path.read_bytes().splitlines(keepends=True)
                if tail == 'event':
                    path.write_bytes(b''.join(rows) + b'{"format":2,"seq":')
                else:
                    path.write_bytes(b''.join(rows[:-1]) + rows[-1][:13])
                self.engine = Engine(self.root / 'state', self.root / 'independent')
                self.assertFalse(self.engine.store.locked)
                self.assertEqual(self.engine.store.committed, self.engine.store.sequence)
                self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
                self.reserve()

    def test_review22_corrupt_committed_record_and_middle_tail_still_rejected(self):
        self.reserve()
        self.engine.close()
        path = self.root / 'independent/operations.jsonl'
        before = path.read_bytes()
        for damaged in (before.replace(b'"format":2', b'"format":3', 1),
                        before + b'{"format":\n' + before.splitlines(keepends=True)[-1]):
            with self.subTest(damaged=damaged[-40:]):
                path.write_bytes(damaged)
                with self.assertRaises(Refused) as error:
                    Engine(self.root / 'state', self.root / 'independent')
                self.assertEqual(error.exception.code, 'evidence_corrupt')
                self.assertEqual(path.read_bytes(), damaged)
        path.write_bytes(before)
        self.engine = Engine(self.root / 'state', self.root / 'independent')

    def test_review22_storage_errno_and_sqlite_errors_never_become_mail_transport(self):
        errors = [(OSError(errno.ENOSPC, 'Synthetic full disk'), 'storage_limit'),
                  (OSError(errno.EDQUOT, 'Synthetic quota'), 'storage_limit'),
                  (OSError(errno.EIO, 'Synthetic disk error'), 'storage_error')]
        for code in (sqlite3.SQLITE_FULL, sqlite3.SQLITE_IOERR):
            error = sqlite3.OperationalError('Synthetic SQLite storage failure')
            error.sqlite_errorcode = code
            errors.append((error, 'storage_limit' if code == sqlite3.SQLITE_FULL else 'storage_error'))
        for error, code in errors:
            with self.subTest(error=error), patch.object(self.engine.store, '_append', side_effect=error):
                result = self.call('testapp_prepare_send', message())
            self.assertFalse(result['ok'], result)
            self.assertEqual(result['error']['code'], code)
            self.assertNotIn('transport', result['error']['message'].lower())
            self.engine.store.write_failed = False

    def test_first_fence_fsync_rollback_and_later_phase_failures(self):
        errors = [(lambda n=n: OSError(n, 'Synthetic storage failure'),
                   'storage_error' if n == errno.EIO else 'storage_limit')
                  for n in (errno.ENOSPC, errno.EDQUOT, errno.EIO)]
        for n in (sqlite3.SQLITE_FULL, sqlite3.SQLITE_IOERR):
            def sql_error(n=n):
                error = sqlite3.OperationalError('Synthetic SQLite failure')
                error.sqlite_errorcode = n
                return error
            errors.append((sql_error, 'storage_limit' if n == sqlite3.SQLITE_FULL else 'storage_error'))
        for phase in ('fence-sync', 'truncate', 'rollback-sync', 'index', 'staging', 'apply', 'marker-write', 'marker-sync'):
            for error, code in errors:
                # Raw journal calls raise OSError; SQLite phases cover FULL/IOERR.
                if phase not in ('index', 'staging', 'apply') and isinstance(error(), sqlite3.Error):
                    continue
                with self.subTest(phase=phase, code=code, error=type(error()).__name__):
                    self.restart()
                    store = self.engine.store
                    journal = store.evidence_dir / 'operations.jsonl'
                    before = journal.read_bytes()
                    write, sync = store.journal.write, os.fsync
                    writes = []
                    def write_fault(data):
                        marker = 'commit' in json.loads(data)
                        writes.append(marker)
                        if phase in ('truncate', 'rollback-sync') and not marker or phase == 'marker-write' and marker:
                            raise error()
                        return write(data)
                    failed = []
                    def sync_fault(fd):
                        if fd == store.journal.fileno():
                            marker = bool(writes and writes[-1])
                            if (phase == 'fence-sync' and not failed or
                                    phase == 'rollback-sync' or phase == 'marker-sync' and marker and not failed):
                                failed.append(fd)
                                raise error()
                        return sync(fd)
                    # A proxy preserves SQLite's real transaction semantics,
                    # while failing precisely the event-staging statement.
                    db = store.db
                    class StageFailure:
                        def __getattr__(self, name): return getattr(db, name)
                        def __enter__(self): db.__enter__(); return self
                        def __exit__(self, *args): return db.__exit__(*args)
                        def execute(self, sql, *args):
                            if sql.startswith('INSERT OR REPLACE INTO events'): raise error()
                            return db.execute(sql, *args)
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(store.journal, 'write', side_effect=write_fault))
                        stack.enter_context(patch('os.fsync', side_effect=sync_fault))
                        if phase == 'truncate':
                            stack.enter_context(patch.object(store.journal, 'truncate', side_effect=OSError(errno.EIO, 'Synthetic cleanup failure')))
                        if phase in ('index', 'apply'):
                            stack.enter_context(patch.object(store, '_index_record' if phase == 'index' else '_apply', side_effect=error()))
                        if phase == 'staging': stack.enter_context(patch.object(store, 'db', StageFailure()))
                        result = self.call('testapp_prepare_send', message())
                    self.assertEqual(result['error']['code'], code, result)
                    latched = phase != 'fence-sync'
                    self.assertEqual(store.write_failed, latched)
                    self.assertEqual(RESTART_ADVICE in result['error']['message'], latched)
                    if phase in ('truncate', 'rollback-sync'):
                        self.assertTrue(any('Cleanup journal truncation failed:' in note for note in result['error']['notes']))
                    after = journal.read_bytes()
                    if latched:
                        refused = self.call('testapp_prepare_send', message())
                        self.assertEqual(refused['error']['code'], 'journal_incomplete', refused)
                        self.assertEqual(refused['error']['message'], RESTART_ADVICE)
                        self.assertEqual(journal.read_bytes(), after)
                        self.assertEqual(store.storage_cause.code, code)
                        self.restart()
                        if self.engine.store.locked:
                            self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
                    else:
                        self.assertEqual(after, before)
                    self.reserve(subject='Explicit healthy request')

    def test_admission_refusal_and_successful_read_keep_exact_text(self):
        store = self.engine.store
        expected = self.call('control_pending')
        with patch.object(store.ledger, 'admit', side_effect=Refused('storage_limit', 'Synthetic admission only.')):
            result = self.call('testapp_prepare_send', message())
        self.assertEqual(result['error'], {'code': 'storage_limit', 'message': 'Synthetic admission only.'})
        self.assertFalse(store.write_failed)
        self.assertEqual(self.call('control_pending'), expected)
        self.reserve()

    def test_applied_cancel_ack_and_account_rows_survive_failed_markers_and_restart(self):
        for kind in ('cancel', 'ack', 'account'):
            for mode in ('single', 'persistent', 'rollback-failure', 'staged-only'):
                with self.subTest(kind=kind, mode=mode):
                    self.restart()
                    approval = self.reserve()
                    operation_id = approval['operation_id']
                    if kind == 'ack':
                        self.data('testapp_operation_cancel', {'operation_id': operation_id})
                    store = self.engine.store
                    key = 'mail:account:synthetic' if kind == 'account' else 'op:' + operation_id
                    before = store.get(key)
                    account = {'id': 'synthetic', 'ready': False, 'revision': mode}
                    write, attempted = store.journal.write, []
                    def fail(data):
                        if 'commit' in json.loads(data) and (not attempted or mode == 'persistent'):
                            attempted.append(1)
                            raise OSError(errno.ENOSPC, 'Synthetic failed marker')
                        return write(data)
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(store.journal, 'write', side_effect=fail))
                        if mode == 'rollback-failure':
                            stack.enter_context(patch.object(store, '_truncate_journal', side_effect=OSError(errno.EIO, 'Synthetic rollback failure')))
                        if mode == 'staged-only':
                            stack.enter_context(patch.object(store, '_apply', side_effect=OSError(errno.ENOSPC, 'Synthetic application failure')))
                        if kind == 'account':
                            with self.assertRaises((Refused, OSError)) as error:
                                store.write({key: account}, 'fixture', 'Synthetic account-like row')
                            self.assertEqual(storage_refusal(error.exception).code, 'storage_limit')
                        else:
                            reply = self.call('testapp_operation_cancel' if kind == 'cancel' else 'testapp_notice_ack', {'operation_id': operation_id})
                            self.assertEqual(reply['error']['code'], 'storage_limit')
                    self.assertTrue(store.write_failed)
                    applied = store.get(key)
                    if mode == 'staged-only':
                        self.assertEqual(applied, before)
                    elif kind == 'cancel': self.assertEqual(applied['state'], 'failed')
                    elif kind == 'ack': self.assertIs(applied['ack'], True)
                    else: self.assertEqual(applied, account)
                    self.assertEqual(self.engine.receiver.evidence(operation_id)['arrivals'], [])
                    journal = store.evidence_dir / 'operations.jsonl'
                    raw = journal.read_bytes()
                    self.assertEqual(self.call('testapp_prepare_send', message())['error']['code'], 'journal_incomplete')
                    self.assertEqual(journal.read_bytes(), raw)
                    self.restart()
                    self.assertFalse(self.engine.store.locked)
                    if mode != 'staged-only': self.assertEqual(self.engine.store.get(key), applied)
                    elif kind == 'cancel': self.assertEqual(self.engine.store.get(key)['state'], 'failed')
                    elif kind == 'ack': self.assertIs(self.engine.store.get(key)['ack'], True)
                    else: self.assertEqual(self.engine.store.get(key), account)
                    self.assertEqual(self.engine.receiver.evidence(operation_id)['arrivals'], [])
