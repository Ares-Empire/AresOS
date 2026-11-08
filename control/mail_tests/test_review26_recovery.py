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
        self.assertFalse(self.data('filing_notices', {})['items'])

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
