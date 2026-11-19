"""Review 16: filing facts and background causes survive failed storage."""
import errno
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
import test_review_fixes_23 as round23


class Filing24(unittest.TestCase):
    setUp = round23.Results23.setUp
    call = round23.Results23.call
    data = round23.Results23.data
    compose = round23.Results23.compose
    approval = round23.Results23.approval
    restart = round23.Results23.restart

    def test_review24_move_and_copy_keep_exact_destination_role_and_deferred_warning(self):
        for verb in ('move', 'copy'):
            with self.subTest(verb=verb):
                ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
                       'uid': 2 if verb == 'copy' else 1, 'message_id': self.imap.mid}
                self.imap.roles['Trash'] = ['\\Trash']
                self.imap.roles['Target'] = []
                write = self.engine.store.write
                def fail(changes, *args, **kwargs):
                    if self.imap.mutations:
                        raise OSError(errno.ENOSPC, 'Synthetic full disk after COPYUID')
                    return write(changes, *args, **kwargs)
                self.imap.mutations.clear()
                with patch.object(self.engine.store, 'write', side_effect=fail):
                    result = self.call(verb, {'references': [ref], 'target': 'Target'})
                    self.assertFalse(result['ok'], result)
                    self.assertIn('Disk full', result['error']['message'])
                    evidence = next(iter(result['observations']['evidence'].values()))
                    dest = {**ref, 'folder': 'Target', 'uidvalidity': self.imap.validities['Target'],
                            'uid': max(self.imap.boxes['Target'])}
                    self.assertEqual(evidence['records'][0]['destination'], dest)
                    self.assertEqual(evidence['observed_role'], 'Trash')
                    self.assertIn('which is now Trash', evidence['reason'])
                    self.assertIn(dest, evidence['locations'][0]['observed_locations'])
                    for action in ('accounts',):
                        next_result = self.call(action, {})
                        self.assertIn('which is now Trash', next_result['pending']['notices'][0]['untrusted_content']['reason'])
                    log = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {}})
                    self.assertIn('which is now Trash', log['data']['notices'][0]['untrusted_content']['reason'])
                self.data('accounts', {})
                self.assertFalse(self.engine.store.deferred_notices)
                stored = self.engine.store.items('notice:')
                self.assertTrue(any('which is now Trash' in n['untrusted_content']['reason'] for _, n in stored))
                self.assertEqual(self.imap.mutations, [(verb.upper(), ref['uid'], 'Target')])

    def test_review24_rename_keeps_observation_and_notice_before_write(self):
        def rename(source, target):
            self.imap.boxes['Renamed'] = self.imap.boxes.pop('Source')
            self.imap.roles['Renamed'] = ['\\Trash']
            self.imap.roles.pop('Source')
            self.imap.roles['Trash'] = []
            self.imap.validities['Renamed'] = self.imap.validities.pop('Source')
            return 'OK', [b'Renamed']
        write = self.engine.store.write
        def fail(changes, *args, **kwargs):
            if 'Renamed' in self.imap.boxes:
                raise OSError(errno.ENOSPC, 'Synthetic full disk after rename')
            return write(changes, *args, **kwargs)
        with patch.object(self.imap, 'rename', side_effect=rename, create=True), \
             patch.object(self.engine.store, 'write', side_effect=fail):
            result = self.call('folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'Renamed'})
            self.assertFalse(result['ok'], result)
            self.assertIn('Disk full', result['error']['message'])
            evidence = next(iter(result['observations']['evidence'].values()))
            self.assertEqual(evidence['rename']['target'], 'Renamed')
            self.assertIn('Trash', evidence['rename']['observed_role'])
            self.assertIn('special folders changed', result['pending']['notices'][0]['untrusted_content']['reason'])
        self.data('accounts', {})
        self.assertFalse(self.engine.store.deferred_notices)

    def test_review24_journal_full_after_move_keeps_warning_in_mail_and_log_while_latched(self):
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
               'uid': 1, 'message_id': self.imap.mid}
        write = self.engine.store.journal.write
        def fail(data):
            if self.imap.mutations:
                raise OSError(errno.ENOSPC, 'Synthetic full disk after MOVE')
            return write(data)
        with patch.object(self.engine.store.journal, 'write', side_effect=fail):
            result = self.call('move', {'references': [ref], 'target': 'Target'})
        self.assertFalse(result['ok'], result)
        self.assertIn('Disk full', result['error']['message'])
        evidence = next(iter(result['observations']['evidence'].values()))
        self.assertEqual(evidence['records'][0]['destination']['uid'], 1)
        self.assertEqual(evidence['observed_role'], 'Trash')
        self.assertFalse(self.engine.store.write_failed)
        self.assertFalse(self.engine.store.items('notice:'))
        for action, args in [('mail_accounts', {}), ('control_log', {})]:
            following = self.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args})
            notices = following['data'] if action == 'control_log' else following['pending']
            self.assertIn('which is now Trash', notices['notices'][0]['untrusted_content']['reason'])
        self.assertEqual(self.imap.mutations, [('MOVE', 1, 'Target')])

    def test_review24_expiry_keeps_first_storage_cause_notice_and_service_log(self):
        for number in (errno.ENOSPC, errno.EDQUOT, errno.EIO):
            with self.subTest(errno=number):
                approval = self.approval('send', self.compose())
                with patch('aresos_control.engine.time.time', return_value=approval['description']['expires_at'] + 1), \
                     patch.object(self.engine.store.journal, 'write', side_effect=OSError(number, 'Synthetic storage failure')), \
                     self.assertLogs('aresos_control.engine', level='ERROR') as logs:
                    with self.assertRaises(Refused):
                        self.engine.expire()
                expected = 'Storage I/O' if number == errno.EIO else 'Disk full'
                self.assertIn(expected, logs.output[0])
                self.assertFalse(self.engine.store.write_failed)
                result = self.call('compose', {'account': 'box', 'to': ['recipient@mail.invalid'], 'text': 'Synthetic'})
                self.assertTrue(result['ok'], result)
                self.assertIn(expected, result['pending']['notices'][0]['untrusted_content']['reason'])
                self.restart()
                self.data('compose', {'account': 'box', 'to': ['recipient@mail.invalid'], 'text': 'Synthetic'})
                self.assertIsNone(self.engine.store.storage_cause)
                self.assertFalse(self.engine.store.write_failed)

    def test_failed_predispatch_flush_blocks_effect_until_next_request(self):
        import json
        import os
        from test_review23_sweep import Scenario
        from aresos_control.common import storage_refusal
        # Exercise both gates: flush/catch before dispatch, and a caller which
        # catches the same failure after admission and reaches a command check.
        for where in ('predispatch', 'admitted'):
            for kind in ('zero', 'short', 'fence-sync'):
                with self.subTest(where=where, kind=kind):
                    scenario = Scenario('send')
                    try:
                        f, store = scenario.fixture, scenario.fixture.engine.store
                        notice = {'id': 'queued', 'app': 'mail', 'state': 'partial', 'ack': False,
                                  'untrusted_content': {'reason': 'Synthetic queued warning.'}}
                        def queue():
                            store.defer_notice('queued', {'notice:queued': notice}, 'control_maintenance', 'Synthetic deferred warning')
                        if where == 'predispatch': queue()
                        before = (store.evidence_dir / 'operations.jsonl').read_bytes()
                        write, sync, failed = store.journal.write, os.fsync, []
                        def journal_write(data):
                            if not failed and kind != 'fence-sync':
                                self.assertNotIn('commit', json.loads(data))
                                failed.append(kind)
                                return write(data[:0 if kind == 'zero' else 13])
                            return write(data)
                        def journal_sync(fd):
                            if fd == store.journal.fileno() and not failed and kind == 'fence-sync':
                                failed.append(kind)
                                raise OSError(errno.ENOSPC, 'Synthetic fence sync failure')
                            return sync(fd)
                        admitted = f.engine._request
                        refused_checks = []
                        def caught(*args, **kwargs):
                            queue()
                            try: store.flush_notices()
                            except Refused: pass
                            # Catching must not remove the barrier at the next
                            # storage check, even though the store is unlatched.
                            try:
                                store.ensure_writable()
                            except Refused as exc:
                                refused_checks.append(exc.code)
                            return admitted(*args, **kwargs)
                        from contextlib import ExitStack
                        with ExitStack() as stack:
                            stack.enter_context(patch.object(store.journal, 'write', side_effect=journal_write))
                            stack.enter_context(patch('os.fsync', side_effect=journal_sync))
                            if where == 'admitted': stack.enter_context(patch.object(f.engine, '_request', side_effect=caught))
                            result = scenario.call()
                        self.assertEqual(scenario.remote['DATA'], 0, 'Failed flush must cause zero SMTP DATA')
                        self.assertFalse(scenario.remote, scenario.remote)
                        if where == 'admitted':
                            self.assertEqual(refused_checks, ['storage_limit'])
                        self.assertEqual(result['error']['code'], 'storage_limit', result)
                        self.assertEqual(result['error']['message'], str(storage_refusal(OSError(errno.ENOSPC, 'Synthetic'))))
                        self.assertEqual(f.engine.operation(scenario.operation_id)['state'], 'reserved')
                        self.assertIn('queued', store.deferred_notices)
                        self.assertEqual((store.evidence_dir / 'operations.jsonl').read_bytes(), before)
                        self.assertFalse(store.write_failed)
                        reply = scenario.call()
                        self.assertTrue(reply['ok'], reply)
                        self.assertFalse(store.deferred_notices)
                        self.assertEqual(scenario.remote['DATA'], 1)
                        self.assertEqual(scenario.remote['APPEND'], 1)
                    finally:
                        scenario.close()

    def test_failed_predispatch_flush_blocks_reads_and_cancellation_until_next_request(self):
        from test_review23_sweep import Scenario
        for action in ('mail_accounts', 'mail_operation_cancel', 'control_pending'):
            with self.subTest(action=action):
                scenario = Scenario('send')
                try:
                    f, store = scenario.fixture, scenario.fixture.engine.store
                    store.defer_notice('queued', {}, 'control_maintenance', 'Synthetic deferred warning')
                    args = {'operation_id': scenario.operation_id} if action.endswith('_cancel') else {}
                    envelope = {'v': 1, 'method': 'call', 'action': action, 'arguments': args}
                    with patch.object(store.journal, 'write', return_value=0):
                        reply = f.engine.request(envelope)
                    self.assertEqual(reply['error']['code'], 'storage_limit', reply)
                    self.assertEqual(f.engine.operation(scenario.operation_id)['state'], 'reserved')
                    self.assertFalse(store.write_failed)
                    self.assertIn('queued', store.deferred_notices)
                    self.assertTrue(f.engine.request(envelope)['ok'])
                    self.assertFalse(store.deferred_notices)
                    self.assertFalse(scenario.remote)
                finally:
                    scenario.close()
