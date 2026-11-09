"""Warning occurrences, check state and action resolution are independent."""
import time
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.recovery import unfinished
import test_review27_checks as prior


class Lifecycle29(unittest.TestCase):
    setUp = prior.Checks27.setUp
    call = prior.Checks27.call
    data = prior.Checks27.data
    restart = prior.Checks27.restart
    compose = prior.Checks27.compose
    approval = prior.Checks27.approval
    submit = prior.Checks27.submit

    def test_review29_acknowledged_open_check_survives_outage_expiry_and_restart(self):
        key = 'mail:rename:interrupted'
        self.engine.store.write({key: {'id': 'interrupted', 'state': 'started',
            'account': 'box', 'source': 'Source', 'target': 'Target', 'message_count': 1,
            'roles_before': {}}}, 'mail_folder_rename', 'Synthetic interrupted rename')
        self.restart()
        with patch.object(self.mail.transport, 'imap', side_effect=OSError('Synthetic offline')):
            self.data('notice_ack', {'operation_id': 'interrupted'})
            source = self.engine.store.get(key)
            self.assertEqual(source['state'], 'partial')
            self.assertTrue(source['check_open'])
            self.assertIn(key, {k for k, *_ in unfinished(self.engine.store)})
            with patch('aresos_control.retention.time.time', return_value=time.time() + 90000):
                self.engine.expire()
            self.assertIsNotNone(self.engine.store.get(key))
            self.assertTrue(self.engine.store.get('notice:interrupted')['ack'])
            page = self.engine.pending()
            self.assertIn('not yet checked', str(page))
            check_id = page['notices'][0]['operation_id']
            self.assertFalse(self.call('notice_ack', {'operation_id': check_id})['ok'])
            self.assertTrue(self.engine.store.get(key)['check_open'])
        self.restart()
        with patch.object(self.mail.transport, 'imap', side_effect=OSError('Synthetic offline')):
            self.assertIn('not yet checked', str(self.engine.pending()))

    def test_review29_rename_refused_result_offline_ack_expiry_then_trash_is_new_occurrence(self):
        from test_review23_sweep import Scenario
        scenario = Scenario('filing_rename')
        try:
            fixture = scenario.fixture
            write = fixture.engine.store.write
            def refuse(*args, **kwargs):
                if scenario.remote:
                    raise Refused('storage_limit', 'Synthetic refused result')
                return write(*args, **kwargs)
            with patch.object(fixture.engine.store, 'write', side_effect=refuse):
                scenario.call()
            key, intent = fixture.engine.store.items('mail:rename:')[0]
            remote = scenario.remote.copy()
            fixture.restart()
            with patch.object(fixture.mail.transport, 'imap', side_effect=OSError('Synthetic offline')):
                fixture.data('notice_ack', {'operation_id': intent['id']})
                with patch('aresos_control.retention.time.time', return_value=time.time() + 90000):
                    fixture.engine.expire()
                self.assertTrue(fixture.engine.store.get(key)['check_open'])
                self.assertIn('not yet checked', str(fixture.engine.pending()))
            with patch.object(fixture.mail.transport, 'imap', wraps=fixture.mail.transport.imap) as reads:
                page = fixture.data('filing_notices', {})
            self.assertGreater(reads.call_count, 0)
            drift = next(n for n in page['items'] if not n['untrusted_content'].get('check_open'))
            self.assertIn('Trash', drift['untrusted_content']['reason'])
            self.assertNotEqual(drift['operation_id'], intent['id'])
            self.assertTrue(fixture.engine.store.get('notice:' + intent['id'])['ack'])
            self.assertFalse(fixture.engine.store.get(key).get('check_open'))
            self.assertEqual(scenario.remote, remote)
        finally:
            scenario.close()

    def test_review29_four_interrupted_renames_page_oldest_trash_and_keep_three_acknowledged(self):
        self.imap.roles['Drafts'] = []
        for index in range(4):
            target, filing_id = 'Target' + str(index), 'rename-' + str(index)
            self.imap.boxes[target] = {}
            self.imap.roles[target] = ['\\Trash'] if index == 0 else []
            self.engine.store.write({'mail:rename:' + filing_id: {'id': filing_id, 'state': 'started',
                'account': 'box', 'source': 'Source', 'target': target, 'message_count': 1,
                'roles_before': {}}}, 'mail_folder_rename', 'Synthetic interrupted rename')
        first = self.data('filing_notices', {})
        self.assertEqual(first['total'], 4)
        second = self.data('filing_notices', {'cursor': first['cursor']})
        self.assertEqual(len(second['items']), 1)
        self.assertIsNone(second['cursor'])
        self.assertEqual({n['operation_id'] for n in first['items'] + second['items']},
                         {'rename-' + str(i) for i in range(4)})
        self.assertIn('Trash', second['items'][0]['untrusted_content']['reason'])
        before = dict(self.engine.store.items('notice:'))
        for notice in first['items']:
            self.data('notice_ack', {'operation_id': notice['operation_id']})
        for _ in range(5):
            self.data('filing_notices', {})
        for notice in first['items']:
            stored = self.engine.store.get('notice:' + notice['operation_id'])
            self.assertTrue(stored['ack'])
            self.assertEqual(stored['created_at'], before['notice:' + notice['operation_id']]['created_at'])
        self.assertEqual(len(self.engine.store.items('notice:')), 4)

    def duplicate(self):
        operation = self.submit(self.approval('send', self.compose()))
        self.imap.boxes['Sent'][2] = self.imap.boxes['Sent'][1]
        notice = self.engine.pending()['notices'][0]
        return operation, notice['operation_id']

    def test_review29_unchanged_sent_set_preserves_occurrence_order_and_ack_across_reads_and_restart(self):
        op, occurrence = self.duplicate()
        before = self.engine.store.get('notice:' + occurrence)
        for _ in range(10):
            self.data('operation_status', {'operation_id': op['id']})
            self.data('filing_notices', {})
            self.engine.pending()
        self.assertEqual(self.engine.store.get('notice:' + occurrence), before)
        self.data('notice_ack', {'operation_id': occurrence})
        self.restart()
        for _ in range(3):
            self.assertFalse(self.engine.pending().get('notices'))
            self.assertFalse(self.data('filing_notices', {})['items'])
        self.assertEqual(len(self.engine.store.items('notice:')), 1)
        self.assertTrue(self.engine.store.get('notice:' + occurrence)['ack'])

    def test_review29_same_count_changed_sent_set_after_ack_starts_new_occurrence(self):
        op, occurrence = self.duplicate()
        self.data('notice_ack', {'operation_id': occurrence})
        self.imap.boxes['Sent'][3] = self.imap.boxes['Sent'].pop(2)
        new = self.data('filing_notices', {})['items'][0]
        self.assertNotEqual(new['operation_id'], occurrence)
        self.assertEqual(new['untrusted_content']['message_count'], 2)
        self.assertTrue(self.engine.store.get('notice:' + occurrence)['ack'])
        self.assertEqual(self.data('filing_notices', {})['items'], [new])

    def test_review29_legacy_ack_adopts_unchanged_warning_then_distinguishes_changed_evidence(self):
        operation, occurrence = self.duplicate()
        self.data('notice_ack', {'operation_id': occurrence})
        op = self.engine.operation(operation['id'])
        op.pop('warning_checks')
        notice = self.engine.store.get('notice:' + occurrence)
        for field in ('check_kind', 'evidence_fingerprint', 'source_key'):
            notice.pop(field)
        notice['untrusted_content'].pop('intent_key')
        self.engine.store.write({'op:' + op['id']: op, 'notice:' + occurrence: notice},
                                'fixture', 'Synthetic pre-occurrence records')
        self.restart()
        self.assertFalse(self.data('filing_notices', {})['items'])
        adopted = self.engine.store.get('notice:' + occurrence)
        self.assertTrue(adopted['ack'])
        self.assertEqual(adopted['created_at'], notice['created_at'])
        self.imap.boxes['Sent'][3] = self.imap.boxes['Sent'].pop(2)
        new = self.data('filing_notices', {})['items'][0]
        self.assertNotEqual(new['operation_id'], occurrence)

    def test_review29_clean_keeps_unacknowledged_occurrence_and_recurrence_starts_another(self):
        op, occurrence = self.duplicate()
        raw = self.imap.boxes['Sent'].pop(2)
        self.data('operation_status', {'operation_id': op['id']})
        self.assertEqual(self.data('filing_notices', {})['items'][0]['operation_id'], occurrence)
        self.imap.boxes['Sent'][2] = raw
        page = self.data('filing_notices', {})
        self.assertEqual(page['total'], 2)
        self.assertIn(occurrence, {n['operation_id'] for n in page['items']})
        self.assertEqual(len({n['operation_id'] for n in page['items']}), 2)

    def test_review29_failed_new_occurrence_commit_keeps_ack_and_recovers_once_after_restart(self):
        op, occurrence = self.duplicate()
        self.data('notice_ack', {'operation_id': occurrence})
        self.imap.boxes['Sent'][3] = self.imap.boxes['Sent'].pop(2)
        write = self.engine.store.write
        def refuse(changes, action, *args, **kwargs):
            if action == 'mail_sent_copy_check':
                raise Refused('storage_limit', 'Synthetic result refusal')
            return write(changes, action, *args, **kwargs)
        with patch.object(self.engine.store, 'write', side_effect=refuse):
            self.assertFalse(self.call('operation_status', {'operation_id': op['id']})['ok'])
        self.assertEqual(len(self.engine.store.items('notice:')), 1)
        self.restart()
        page = self.data('filing_notices', {})
        self.assertEqual(page['total'], 1)
        self.assertNotEqual(page['items'][0]['operation_id'], occurrence)
        self.assertTrue(self.engine.store.get('notice:' + occurrence)['ack'])
        self.assertEqual(len(self.engine.store.items('notice:')), 2)

    def test_review29_archive_and_expiry_keep_unacknowledged_history_then_never_resurrect_ack(self):
        from aresos_control.archive import archive
        op, first = self.duplicate()
        self.imap.boxes['Sent'][3] = self.imap.boxes['Sent'][1]
        second = self.data('filing_notices', {})['items'][0]['operation_id']
        self.assertNotEqual(first, second)
        self.data('notice_ack', {'operation_id': second})
        archive(self.engine.store, time.time() - 0.001, self.mail)
        self.assertIsNotNone(self.engine.store.get('op:' + op['id']))
        with patch('aresos_control.retention.time.time', return_value=time.time() + 90000):
            self.engine.expire()
        self.assertFalse(self.engine.store.get('notice:' + first)['ack'])
        self.data('notice_ack', {'operation_id': first})
        archive(self.engine.store, time.time() - 0.001, self.mail)
        self.assertIsNone(self.engine.store.get('op:' + op['id']))
        with patch('aresos_control.retention.time.time', return_value=time.time() + 90000):
            self.engine.expire()
        self.restart()
        self.assertFalse(self.data('filing_notices', {})['items'])

    def test_review29_location_occurrences_keep_their_evidence_and_expire_only_after_all_acknowledged(self):
        from aresos_control.common import sha256
        reference = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
                     'uid': 1, 'message_id': self.imap.mid}
        raw = self.mail.message(reference)['raw']
        key = 'mail:filing:scan'
        self.engine.store.write({key: {'id': 'scan', 'account': 'box', 'state': 'started',
            'verb': 'copy', 'sources': [reference], 'target': 'Target', 'roles_before': {},
            'records': [{'source': reference, 'sha256': sha256(raw), 'destination': None}]}},
            'mail_copy', 'Synthetic interrupted copy')
        self.imap.roles['Drafts'] = []
        first = self.data('filing_notices', {})['items'][0]
        first_id = first['untrusted_content']['filing_id']
        first_page = self.data('filing_locations', {'filing_id': first_id})
        self.imap.boxes['Target'][1] = raw
        second = self.data('filing_notices', {})['items'][0]
        second_id = second['untrusted_content']['filing_id']
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(self.data('filing_locations', {'filing_id': first_id}), first_page)
        self.assertNotEqual(self.data('filing_locations', {'filing_id': second_id}), first_page)
        with patch('aresos_control.retention.time.time', return_value=time.time() + 90000):
            self.engine.expire()
        self.assertIsNotNone(self.engine.store.get(key))
        self.assertFalse(self.engine.store.get('notice:' + first_id)['ack'])
        self.data('notice_ack', {'operation_id': first_id})
        self.data('notice_ack', {'operation_id': second_id})
        self.imap.roles['Drafts'] = ['\\Drafts']
        last = self.data('filing_notices', {})['items'][0]
        self.data('notice_ack', {'operation_id': last['operation_id']})
        with patch('aresos_control.retention.time.time', return_value=time.time() + 90000):
            self.engine.expire()
            self.engine.expire()
        self.assertIsNone(self.engine.store.get(key))
        self.assertFalse(self.engine.store.items('mail:filing-locations:'))
        self.restart()
        self.assertFalse(self.data('filing_notices', {})['items'])

