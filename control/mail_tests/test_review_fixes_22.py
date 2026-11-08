"""Review 14: observed Sent duplicates survive storage failures."""
import errno
import json
import sqlite3
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
import test_review_fixes_21 as round21


class Duplicates22(unittest.TestCase):
    setUp = round21.LateDuplicates21.setUp
    call = round21.LateDuplicates21.call
    data = round21.LateDuplicates21.data
    compose = round21.LateDuplicates21.compose
    approval = round21.LateDuplicates21.approval
    send = round21.LateDuplicates21.send
    pending_append = round21.LateDuplicates21.pending_append
    restart = round21.LateDuplicates21.restart

    def assert_observation(self, result):
        self.assertFalse(result['ok'], result)
        self.assertIn(result['error']['code'], {'storage_limit', 'storage_error', 'journal_incomplete'})
        evidence = result['data']['evidence']
        self.assertEqual([copy['uid'] for copy in evidence['sent']], [1, 2])
        self.assertIn('2 copies', evidence['sent_copy_warning'])
        self.assertEqual(evidence['warning_storage_error']['code'], 'storage_limit')
        self.assertIn('Disk full', evidence['warning_storage_error']['message'])
        operation = result['data'].get('original', result['data']['operation'])
        self.assertIn('2 copies', operation['reason'])
        self.assertEqual(len(self.imap.boxes['Sent']), 2)
        self.assertEqual(self.imap.mutations, [])

    def test_review22_status_returns_two_copies_warning_and_enospc(self):
        old, args, repair, raw, ended = self.pending_append()
        self.imap.boxes['Sent'].update({1: raw, 2: raw})
        # First settle normally, then discover a new count on completed send.
        self.imap.boxes['Sent'].pop(2)
        self.data('operation_repair', args)
        self.imap.boxes['Sent'][2] = raw
        with patch.object(self.engine.store.journal, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic disk full')):
            self.assert_observation(self.call('operation_status', {'operation_id': old['id']}))
        self.assertTrue(self.engine.store.write_failed)

    def test_review22_completed_repair_returns_two_copies_warning_and_enospc(self):
        old, args, repair, raw, ended = self.pending_append()
        self.imap.boxes['Sent'][1] = raw
        self.data('operation_repair', args)
        self.imap.boxes['Sent'][2] = raw
        with patch.object(self.engine.store.journal, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic disk full')):
            self.assert_observation(self.call('operation_repair', args))

    def test_review22_settlement_returns_two_copies_warning_and_enospc_without_false_done(self):
        old, args, repair, raw, ended = self.pending_append()
        self.imap.boxes['Sent'].update({1: raw, 2: raw})
        with patch.object(self.engine.store.journal, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic disk full')):
            result = self.call('operation_repair', args)
        self.assert_observation(result)
        self.assertEqual(result['data']['operation']['state'], 'unknown')
        self.assertEqual(self.engine.operation(repair['id'])['state'], 'unknown')
        self.assertEqual(self.engine.operation(old['id'])['stages']['sent_copy'], 'failed')
        self.restart()
        self.assertEqual(self.data('operation_repair', args)['operation']['state'], 'done')

    def test_review22_observation_survives_every_storage_exception_while_recording(self):
        old, args, repair, raw, ended = self.pending_append()
        self.imap.boxes['Sent'].update({1: raw, 2: raw})
        errors = [OSError(errno.ENOSPC, 'Synthetic full disk'), OSError(errno.EDQUOT, 'Synthetic quota'),
                  OSError(errno.EIO, 'Synthetic I/O'), OSError('Synthetic storage write failure'),
                  sqlite3.OperationalError('Synthetic SQLite write failure'),
                  Refused('storage_limit', 'Disk full'), Refused('journal_incomplete', 'Interrupted write')]
        for error in errors:
            for verb, arguments in [('operation_status', {'operation_id': old['id']}), ('operation_repair', args)]:
                with self.subTest(error=error, verb=verb), patch.object(self.engine.store, 'write', side_effect=error):
                    result = self.call(verb, arguments)
                self.assertFalse(result['ok'], result)
                self.assertIn(result['error']['code'], {'storage_limit', 'storage_error', 'journal_incomplete'})
                evidence = result['data']['evidence']
                self.assertEqual(len(evidence['sent']), 2)
                self.assertIn('2 copies', evidence['sent_copy_warning'])
                self.assertIn(evidence['warning_storage_error']['code'], {'storage_limit', 'storage_error', 'journal_incomplete'})
        self.assertEqual(self.imap.mutations, [])

    def test_review22_new_repair_returns_observation_before_admitting_another_attempt(self):
        old = self.send('sent_copy')
        raw = ('Message-ID: ' + self.mail.message_id(old['id']) + '\r\nSubject: Synthetic\r\n\r\nCopy').encode()
        self.imap.boxes['Sent'].update({1: raw, 2: raw})
        with patch.object(self.engine.store.journal, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic disk full')):
            self.assert_observation(self.call('operation_repair', {'operation_id': old['id'], 'stage': 'sent_copy'}))
        self.assertEqual([op for _, op in self.engine.store.iter_items('op:') if op.get('repair_of') == old['id']], [])

    def test_review22_settlement_write_failure_preserves_observation_and_recorded_state(self):
        old, args, repair, raw, ended = self.pending_append()
        self.imap.boxes['Sent'].update({1: raw, 2: raw})
        self.data('operation_status', {'operation_id': old['id']})
        with patch.object(self.engine.store.journal, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic disk full')):
            result = self.call('operation_repair', args)
        self.assertFalse(result['ok'], result)
        self.assertIn(result['error']['code'], {'storage_limit', 'storage_error', 'journal_incomplete'})
        evidence = result['data']['evidence']
        self.assertEqual(len(evidence['sent']), 2)
        self.assertIn('2 copies', evidence['sent_copy_warning'])
        self.assertEqual(evidence['settlement_storage_error']['code'], 'storage_limit')
        self.assertEqual(result['data']['operation']['state'], 'unknown')
        self.assertEqual(result['data']['original']['stages']['sent_copy'], 'failed')

    def test_review22_short_settlement_commit_does_not_report_done_before_replay(self):
        old, args, repair, raw, ended = self.pending_append()
        self.imap.boxes['Sent'].update({1: raw, 2: raw})
        self.data('operation_status', {'operation_id': old['id']})
        write = self.engine.store.journal.write
        def short_commit(data):
            return write(data[:13]) if 'commit' in json.loads(data) else write(data)
        with patch.object(self.engine.store.journal, 'write', side_effect=short_commit):
            result = self.call('operation_repair', args)
        self.assertFalse(result['ok'], result)
        self.assertIn(result['error']['code'], {'storage_limit', 'storage_error', 'journal_incomplete'})
        self.assertEqual(result['data']['operation']['state'], 'unknown')
        self.assertEqual(len(result['data']['evidence']['sent']), 2)
        self.assertEqual(result['data']['evidence']['settlement_storage_error']['code'], 'storage_limit')
        self.assertTrue(self.engine.store.write_failed)
        self.restart()
        self.assertEqual(self.data('operation_status', {'operation_id': repair['id']})['operation']['state'], 'done')
