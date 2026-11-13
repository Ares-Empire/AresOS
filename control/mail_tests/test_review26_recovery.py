"""Recovery warnings come from intents, even if every final write was refused."""
import errno
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
from aresos_control.common import Refused
import test_review_fixes_23 as prior


class Recovery26(unittest.TestCase):
    setUp = prior.Results23.setUp
    call = prior.Results23.call
    data = prior.Results23.data
    restart = prior.Results23.restart

    def test_review26_move_role_changes_to_trash_all_later_writes_refused_restart_warns(self):
        original_uid, original_write = self.imap.uid, self.engine.store.write
        moved = False
        def uid(command, *args):
            nonlocal moved
            result = original_uid(command, *args)
            if command == 'MOVE':
                moved = True
                self.imap.roles['Target'] = ['\\Trash']
                self.imap.roles['Trash'] = []
            return result
        def write(*args, **kwargs):
            if moved:
                raise Refused('storage_limit', 'Synthetic disk admission refusal')
            return original_write(*args, **kwargs)
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
               'uid': 1, 'message_id': self.imap.mid}
        with patch.object(self.imap, 'uid', side_effect=uid), patch.object(self.engine.store, 'write', side_effect=write):
            result = self.call('move', {'references': [ref], 'target': 'Target'})
        self.assertTrue(moved)
        self.assertFalse(result['ok'])
        self.assertTrue(self.engine.store.deferred_notices)
        self.assertEqual(self.engine.store.items('mail:filing:')[0][1]['state'], 'started')
        self.restart()
        pending = self.engine.pending()
        self.assertTrue(pending['notices'])
        notices = self.data('filing_notices', {})
        self.assertTrue(notices['items'])
        self.assertIn('Trash', str(notices))
        self.assertIn(1, self.imap.boxes['Target'])
        self.assertNotIn(1, self.imap.boxes['Source'])
        self.assertTrue(self.engine.store.items('notice:'))
        self.restart()
        self.assertTrue(self.data('filing_notices', {})['items'])

    def test_review26_every_durable_intent_has_a_notice_and_ack_survives_restart(self):
        intents = {
            'mail:filing:move': {'id': 'move', 'state': 'started'},
            'mail:rename:rename': {'id': 'rename', 'state': 'started'},
            'export:export': {'app': 'mail', 'sha256': '0'*64, 'size': 1, 'created_blob': False},
            'mail:account:incomplete': {'id': 'incomplete', 'ready': False},
        }
        for key, value in intents.items():
            self.engine.store.write({key: value}, 'fixture', 'Synthetic unfinished intent')
        for action in ('mail_draft_save', 'mail_flag', 'mail_folder_create', 'mail_account_settings'):
            self.engine.store.write({}, action, 'Synthetic started change', outcome='started')
        self.restart()
        from aresos_control.recovery import unfinished
        expected = {n for _, n, _, _ in unfinished(self.engine.store)}
        seen, args = set(), {}
        while True:
            page = self.data('filing_notices', args)
            seen.update(n['operation_id'] for n in page['items'])
            if not page['cursor']:
                break
            args = {'cursor': page['cursor']}
        self.assertTrue(expected <= seen, (expected, seen))
        for notice_id in expected:
            self.data('notice_ack', {'operation_id': notice_id})
        self.restart()
        remaining = self.data('filing_notices', {})['items']
        self.assertTrue(remaining)
        self.assertTrue(all(n['untrusted_content'].get('check_open') for n in remaining))
        self.assertFalse(expected & {n['operation_id'] for n in remaining})

    def test_review26_recovery_notice_write_defers_then_becomes_durable(self):
        self.engine.store.write({'mail:filing:interrupted': {'id': 'interrupted', 'state': 'started'}},
                                'fixture', 'Synthetic unfinished filing')
        from aresos_control.recovery import recover_intents
        with patch.object(self.engine.store.ledger, 'admit', side_effect=Refused('storage_limit', 'Synthetic full disk')):
            recover_intents(self.engine.store)
        self.assertTrue(self.engine.pending()['notices'])
        self.assertFalse(self.engine.store.write_failed)
        self.engine.store.write({}, 'fixture', 'First successful write flushes warnings')
        self.assertIsNotNone(self.engine.store.get('notice:interrupted'))

    def test_review26_send_delete_unsubscribe_repair_and_append_recover_notices(self):
        self.engine.store.write({}, 'mail_draft_save', 'Synthetic APPEND intent', outcome='started')
        approval = prior.Results23.approval(self, 'send', prior.Results23.compose(self))
        original = self.engine.operation(approval['operation_id'])
        for index, action in enumerate(('mail_send', 'mail_delete', 'mail_unsubscribe', 'mail_operation_repair')):
            operation = {**original, 'id': original['generation'] + ':' + str(index).zfill(32),
                         'action': action, 'state': 'submitting'}
            if action == 'mail_operation_repair':
                operation['repair_of'] = original['id']
            self.engine.store.write({'op:' + operation['id']: operation}, action, 'Synthetic interrupted operation', operation['id'])
        self.restart()
        from aresos_control.recovery import unfinished
        expected = {n for _, n, _, _ in unfinished(self.engine.store)}
        seen, args = set(), {}
        while True:
            page = self.data('filing_notices', args)
            seen.update(n['operation_id'] for n in page['items'])
            if page['cursor'] is None:
                break
            args = {'cursor': page['cursor']}
        self.assertTrue(expected <= seen)
        self.engine.store.write({}, 'fixture', 'Persist next recovery batch')
        self.assertTrue(expected <= {n['id'] for _, n in self.engine.store.items('notice:')})

    def test_review26_later_success_cannot_erase_prior_interrupted_same_action(self):
        store = self.engine.store
        store.write({}, 'mail_draft_save', 'First APPEND started', outcome='started')
        store.write({}, 'mail_draft_save', 'First APPEND uncertain', outcome='unknown')
        old = store.items('intent:')
        self.assertEqual(len(old), 1)
        store.write({}, 'mail_draft_save', 'Second APPEND started', outcome='started')
        store.write({}, 'mail_draft_save', 'Second APPEND complete', outcome='done')
        self.assertEqual(store.items('intent:'), old)
        self.restart()
        page = self.data('filing_notices', {})
        self.assertIn(old[0][1]['id'], {n['operation_id'] for n in page['items']})

        self.data('notice_ack', {'operation_id': old[0][1]['id']})
        self.assertIsNone(self.engine.store.get(old[0][0]))
        with patch('aresos_control.retention.FILING_COUNT', 1):
            self.engine.store.write({}, 'mail_draft_save', 'Next intent after resolution', outcome='started')
            self.engine.store.write({}, 'mail_draft_save', 'Next intent complete', outcome='done')

    def test_review26_untracked_started_intent_warns_when_metadata_migration_cannot_fit(self):
        key = 'mail:filing:legacy-untracked'
        self.engine.store.write({key: {'id': 'legacy-untracked', 'state': 'started'}},
                                'fixture', 'Synthetic older intent without retention metadata')
        future = 'mail:filing:future-stamp'
        self.engine.store.write({future: {'id': 'future-stamp', 'state': 'started'}}, 'fixture', 'Synthetic older intent with an ahead timestamp')
        import time
        with self.engine.store.db as db:
            db.execute('DELETE FROM retained WHERE k=?', (key,))
            db.execute('UPDATE retained SET created=? WHERE k=?', (time.time() + 3600, future))
        with patch('aresos_control.space.SpaceLedger.admit', side_effect=Refused('storage_limit', 'Synthetic full disk')):
            self.restart()
            from aresos_control.mail.filing import notice_page
            page = notice_page(self.engine.store, app='mail')
            self.assertTrue({'legacy-untracked', 'future-stamp'} <= {n['operation_id'] for n in page['items']})
            self.assertFalse(self.engine.store.write_failed)
        self.engine.store.write({}, 'fixture', 'Disk recovered; persist the warning without restarting')
        self.assertIsNotNone(self.engine.store.get('notice:legacy-untracked'))
        self.assertIsNotNone(self.engine.store.get('notice:future-stamp'))

    def test_review26_archive_keeps_legacy_warning_source_until_acknowledged(self):
        import time
        from aresos_control.archive import archive
        from aresos_control.recovery import recovery_notices
        store = self.engine.store
        # Older adapters recorded unknown without a separate intent key.
        with patch('time.time', return_value=1000):
            for index in range(4):
                store.write({}, 'mail_legacy_change' + str(index), 'Synthetic legacy uncertain change', outcome='unknown')
        source = store.sequence
        with patch('aresos_control.retention.NOTICE_COUNT', 3):
            self.restart()
            notices = list(recovery_notices(self.engine.store))
            notice = next(n for n in notices if n['untrusted_content']['intent_key'].endswith(':' + str(source)))
            self.assertIsNone(self.engine.store.get('notice:' + notice['id']))
            archive(self.engine.store, time.time() - 1)
            self.restart()
            self.assertIn(notice['id'], {n['id'] for n in recovery_notices(self.engine.store)})
            self.assertIn(source, {event['seq'] for event in self.engine.store.iter_audit()})
        self.data('notice_ack', {'operation_id': notice['id']})
        archive(self.engine.store, time.time() - 1)
        self.assertNotIn(source, {event['seq'] for event in self.engine.store.iter_audit()})
        self.restart()
        self.assertFalse(list(recovery_notices(self.engine.store)))
