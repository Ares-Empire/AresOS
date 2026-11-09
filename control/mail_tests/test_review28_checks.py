"""Round 28: reopen before evidence and retain every unfinished check source."""
import time
import unittest
from unittest.mock import patch

from aresos_control.archive import archive
from aresos_control.common import Refused
import test_review27_checks as prior


class Checks28(unittest.TestCase):
    setUp = prior.Checks27.setUp
    call = prior.Checks27.call
    data = prior.Checks27.data
    compose = prior.Checks27.compose
    approval = prior.Checks27.approval
    submit = prior.Checks27.submit
    restart = prior.Checks27.restart

    def owner_archive(self):
        return self.engine.request({'v': 1, 'method': 'call', 'action': 'control_archive',
            'arguments': {'before': time.time() - 0.001, 'confirm': 'archive finished history'}}, admin=True)

    def test_review28_refused_reopening_then_crash_archive_preserves_late_duplicate(self):
        operation = self.submit(self.approval('send', self.compose()))
        self.assertTrue(self.engine.operation(operation['id'])['sent_copy_check']['clean'])
        self.imap.boxes['Sent'][2] = self.imap.boxes['Sent'][1]
        with patch.object(self.engine.store, 'write', side_effect=Refused('storage_limit', 'Synthetic admission refusal')), \
             patch.object(self.mail, 'sent_matches', side_effect=AssertionError('No read before committed reopening')):
            result = self.call('operation_status', {'operation_id': operation['id']})
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'storage_limit')
        self.assertIn('Synthetic admission refusal', result['error']['message'])
        self.assertIn('not yet checked', result['data']['evidence_error']['message'])
        self.assertNotIn('evidence', result['data'])
        self.assertNotIn('observations', result)
        self.assertNotIn('2 copies', str(result))
        self.restart()  # Discard every volatile observation before any pending read.
        remote = dict(self.imap.boxes['Sent'])
        result = self.owner_archive()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data']['operations'], 0)
        self.assertIsNotNone(self.engine.store.get('op:' + operation['id']))
        pending = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_pending', 'arguments': {}})
        own = next(n for n in pending['data']['notices']
                   if n['untrusted_content'].get('operation_id') == operation['id'])
        self.assertEqual(own['untrusted_content']['message_count'], 2)
        self.assertIn('2 copies', own['untrusted_content']['reason'])
        self.assertEqual(self.imap.boxes['Sent'], remote)
        self.assertEqual(self.imap.mutations, [])

    def test_review28_every_sent_evidence_read_starts_with_a_committed_open_check(self):
        operation = self.submit(self.approval('send', self.compose()))
        original = self.mail.sent_matches
        def matches(*args):
            self.assertEqual(self.engine.operation(operation['id'])['sent_copy_check']['state'], 'open')
            return original(*args)
        with patch.object(self.mail, 'sent_matches', side_effect=matches):
            self.data('operation_status', {'operation_id': operation['id']})
            self.engine.pending()
            self.data('filing_notices', {})
        self.assertEqual(self.engine.operation(operation['id'])['sent_copy_check']['state'], 'checked')

    def test_review28_archive_recheck_refusal_protects_previously_clean_send(self):
        operation = self.submit(self.approval('send', self.compose()))
        write = self.engine.store.write
        def refuse(changes, action, *args, **kwargs):
            if action == 'mail_sent_copy_check_open':
                raise Refused('storage_limit', 'Synthetic reopen refusal')
            return write(changes, action, *args, **kwargs)
        with patch.object(self.engine.store, 'write', side_effect=refuse), \
             patch.object(self.mail, 'sent_matches', side_effect=AssertionError('No unrecorded read')):
            result = self.owner_archive()
        self.assertEqual(result['data']['operations'], 0)
        self.assertIsNotNone(self.engine.store.get('op:' + operation['id']))

    def test_review28_clean_checked_send_archives_and_unchanged_duplicate_ack_survives_recheck(self):
        operation = self.submit(self.approval('send', self.compose()))
        self.imap.boxes['Sent'][2] = self.imap.boxes['Sent'][1]
        notice = self.engine.pending()['notices'][0]
        self.data('notice_ack', {'operation_id': notice['operation_id']})
        self.assertFalse(self.engine.pending().get('notices'))
        result = self.owner_archive()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data']['operations'], 1)
        clean = self.submit(self.approval('send', self.compose()))
        self.imap.boxes['Sent'].pop(2)
        result = self.owner_archive()
        self.assertTrue(result['ok'], result)
        self.assertIsNone(self.engine.store.get('op:' + clean['id']))

    def test_review28_archive_protects_every_warning_check_kind_until_closed_and_acknowledged(self):
        store = self.engine.store
        for kind in ('move', 'copy', 'destination', 'rename', 'location_scan', 'setup'):
            with self.subTest(kind=kind):
                prefix = 'mail:account:' if kind == 'setup' else 'mail:rename:' if kind == 'rename' else 'mail:filing:'
                key = prefix + kind
                opened = {'id': kind, 'state': 'started', 'ready': False}
                store.write({key: opened}, 'fixture', 'Synthetic open ' + kind + ' check')
                source = store.events[-1]['seq']
                archive(store, time.time() - 0.001)
                self.assertIn(source, {e['seq'] for e in store.iter_audit()})
                self.assertEqual(store.get(key), opened)
                notice_key = 'notice:' + kind
                closed = {**opened, 'state': 'partial', 'onboarded': True}
                notice = {'id': kind, 'app': 'mail', 'state': 'partial', 'ack': False,
                          'untrusted_content': {'reason': 'Synthetic committed warning'}}
                # Setup warnings must retain their qualification source too.
                notice['untrusted_content']['intent_key'] = key
                store.write({key: closed, notice_key: notice}, 'fixture', 'Synthetic warning result')
                warning_source = store.events[-1]['seq']
                archive(store, time.time() - 0.001)
                self.assertIn(warning_source, {e['seq'] for e in store.iter_audit()})
                notice['ack'] = True
                store.write({notice_key: notice}, 'fixture', 'Synthetic owner acknowledgement')
                archive(store, time.time() - 0.001)
                self.assertNotIn(warning_source, {e['seq'] for e in store.iter_audit()})

    def test_review28_acknowledging_an_unchecked_filing_does_not_close_its_check_for_archive(self):
        for prefix in ('mail:filing:', 'mail:rename:'):
            name = prefix.split(':')[1]
            key = prefix + name
            self.engine.store.write({key: {'id': name, 'state': 'started'}}, 'fixture', 'Synthetic interrupted check')
            source = self.engine.store.events[-1]['seq']
            self.restart()
            self.data('notice_ack', {'operation_id': name})
            archive(self.engine.store, time.time() - 0.001)
            self.assertIn(source, {e['seq'] for e in self.engine.store.iter_audit()})
            self.assertTrue(self.engine.store.get(key)['check_open'])
