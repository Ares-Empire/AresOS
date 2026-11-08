"""Review 11: unresolved repair reuse, proof-only settlement and cancellation room."""
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

from aresos_control import retention
from aresos_control.common import Refused
import test_review_fixes_18 as round18


class Recovery19(unittest.TestCase):
    setUp = round18.Recovery18.setUp
    call = round18.Recovery18.call
    data = round18.Recovery18.data
    compose = round18.Recovery18.compose
    approval = round18.Recovery18.approval
    snapshot = round18.Recovery18.snapshot
    restart = round18.Recovery18.restart
    send = round18.Recovery18.send
    owner = round18.Recovery18.owner

    def uncertain(self, stage='sent_copy'):
        old = self.send(stage)
        if stage == 'answered_flag':
            self.reply_reference(old['id'])
        args = {'operation_id': old['id'], 'stage': stage}
        with patch.object(self.mail, 'local_stage', side_effect=OSError('Disconnected after local action')):
            repair = self.data('operation_repair', args)['operation']
        self.assertEqual(repair['state'], 'unknown')
        return old, args, repair

    def reply_reference(self, operation_id):
        op = self.engine.operation(operation_id)
        op['payload']['composition']['mail']['answered_reference'] = {
            'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
            'uid': 1, 'message_id': self.imap.mid}
        self.engine.store.write({'op:' + op['id']: op}, 'fixture', 'Synthetic reply reference')

    def test_review19_38_uncertain_repairs_with_archives_keep_one_and_cancel_works(self):
        old = self.send('sent_copy')
        pending = self.approval('send', self.compose(text='Pending cancellation'))
        args = {'operation_id': old['id'], 'stage': 'sent_copy'}
        cap = self.engine.store.history_size() + retention.RECOVERY_REQUEST + 256 * 1024
        with patch.object(retention, 'HISTORY_BYTES', cap), \
             patch.object(self.mail, 'local_stage', side_effect=OSError('Disconnected')), \
             patch.object(self.mail, 'sent_matches', side_effect=OSError('Still disconnected')):
            first = self.data('operation_repair', args)
            for _ in range(38):
                before = self.snapshot()
                self.assertEqual(self.data('operation_repair', args), first)
                self.assertEqual(self.snapshot(), before)
                self.owner('control_archive', {'before': time.time() - 1,
                                              'confirm': 'archive finished history'})
            repairs = [op for _, op in self.engine.store.items('op:') if op.get('repair_of') == old['id']]
            self.assertEqual(len(repairs), 1)
            self.assertEqual(repairs[0]['state'], 'unknown')
            self.assertEqual(self.data('operation_cancel', {'operation_id': pending['operation_id']})['operation']['state'], 'failed')

    def test_review19_unknown_sent_repair_settles_done_by_original_message_id_after_restart(self):
        old, args, repair = self.uncertain()
        self.restart()
        mid = self.mail.message_id(old['id'])
        self.imap.boxes['Sent'][1] = (f'Message-ID: {mid}\r\nSubject: Synthetic copy\r\n\r\nCopy').encode()
        with patch.object(self.mail, 'local_stage', side_effect=AssertionError('Must only read')):
            result = self.data('operation_repair', args)
            self.assertEqual(result['operation']['id'], repair['id'])
            self.assertEqual(result['operation']['state'], 'done')
            self.assertEqual(result['original']['stages']['sent_copy'], 'done')
            self.assertEqual(result['original']['state'], 'done')
            before = self.snapshot()
            self.assertEqual(self.data('operation_repair', args), result)
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.imap.mutations, [])

    def test_review19_unknown_sent_repair_proved_absent_fails_then_allows_new_attempt(self):
        old, args, repair = self.uncertain()
        # A different Message-ID is not evidence for this send.
        self.imap.boxes['Sent'][1] = self.imap.raw
        with patch.object(self.mail, 'local_stage', side_effect=AssertionError('Settlement must only read')):
            result = self.data('operation_repair', args)
        self.assertEqual(result['operation']['id'], repair['id'])
        self.assertEqual(result['operation']['state'], 'failed')
        self.assertEqual(result['original']['stages']['sent_copy'], 'failed')
        with patch.object(self.mail, 'local_stage', return_value='done') as local:
            next_result = self.data('operation_repair', args)
        self.assertNotEqual(next_result['operation']['id'], repair['id'])
        self.assertEqual(next_result['operation']['state'], 'done')
        local.assert_called_once()

    def test_review19_each_stage_reuses_reserved_running_unknown_without_writes_when_inconclusive(self):
        for stage in ('sent_copy', 'answered_flag'):
            old, args, repair = self.uncertain(stage)
            for state in ('reserved', 'submitting', 'unknown'):
                op = self.engine.operation(repair['id'])
                op['state'] = state
                self.engine.store.write({'op:' + op['id']: op}, 'fixture', 'Synthetic interrupted repair')
                before = self.snapshot()
                with patch.object(self.mail, 'sent_matches', side_effect=OSError('Disconnected')), \
                     patch.object(self.mail, 'message', side_effect=OSError('Disconnected')), \
                     patch.object(self.mail, 'local_stage', side_effect=AssertionError('Must not retry')):
                    for _ in range(5):
                        result = self.data('operation_repair', args)['operation']
                        self.assertEqual((result['id'], result['state']), (repair['id'], state))
                self.assertEqual(self.snapshot(), before)
            self.assertEqual(len([op for _, op in self.engine.store.items('op:')
                                  if op.get('repair_of') == old['id']]), 1)

    def test_review19_two_failed_stages_each_keep_their_own_single_unresolved_repair(self):
        approval = self.approval('send', self.compose())
        def accepted(operation, composition, raw, stage):
            stage('smtp_data', 'accepted:250')
            return 'done', 'Synthetic DATA acceptance'
        with patch.object(self.mail, 'send_smtp', side_effect=accepted), \
             patch.object(self.mail, 'local_stage', side_effect=OSError('Both local stages disconnected')):
            old = self.data('send', approval)['operation']
            self.reply_reference(old['id'])
            repairs = {}
            for stage in ('sent_copy', 'answered_flag'):
                args = {'operation_id': old['id'], 'stage': stage}
                repairs[stage] = self.data('operation_repair', args)
            before = self.snapshot()
            with patch.object(self.mail, 'sent_matches', side_effect=OSError('Still disconnected')), \
                 patch.object(self.mail, 'message', side_effect=OSError('Still disconnected')):
                for _ in range(10):
                    for stage in repairs:
                        self.assertEqual(self.data('operation_repair', {'operation_id': old['id'], 'stage': stage}), repairs[stage])
            self.assertEqual(self.snapshot(), before)
        unresolved = [op for _, op in self.engine.store.items('op:') if op.get('repair_of') == old['id']]
        self.assertEqual(len(unresolved), 2)
        self.assertEqual({op['payload']['stage'] for op in unresolved}, {'sent_copy', 'answered_flag'})
        self.assertTrue(all(op['state'] == 'unknown' for op in unresolved))

    def test_review19_answered_evidence_uses_readonly_pinned_reference_and_flags(self):
        for present in (False, True):
            old, args, repair = self.uncertain('answered_flag')
            op = self.engine.operation(old['id'])
            reference = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
                         'uid': 1, 'message_id': self.imap.mid}
            op['payload']['composition']['mail']['answered_reference'] = reference
            self.engine.store.write({'op:' + op['id']: op}, 'fixture', 'Synthetic reply reference')
            original_uid = self.imap.uid
            def uid(command, *values):
                result = original_uid(command, *values)
                if present and command == 'FETCH':
                    result = (result[0], [(row[0].replace(b'FLAGS ()', b'FLAGS (\\Answered)'), row[1])
                                         if isinstance(row, tuple) else row.replace(b'FLAGS ()', b'FLAGS (\\Answered)')
                                         for row in result[1]])
                return result
            with patch.object(self.imap, 'uid', side_effect=uid), \
                 patch.object(self.imap, 'select', wraps=self.imap.select) as select, \
                 patch.object(self.mail, 'local_stage', side_effect=AssertionError('Must only read')):
                result = self.data('operation_repair', args)
            self.assertEqual(result['operation']['id'], repair['id'])
            self.assertEqual(result['operation']['state'], 'done' if present else 'failed')
            self.assertEqual(result['original']['stages']['answered_flag'], 'done' if present else 'failed')
            self.assertTrue(select.call_args.kwargs['readonly'])
            self.assertEqual(self.imap.mutations, [])

    def test_review19_cancel_works_above_history_cap_and_other_paths_leave_its_physical_room(self):
        pending = self.approval('send', self.compose())
        cancel_room = 4 * 1024 * 1024
        with patch.object(retention, 'HISTORY_BYTES', 0), \
             patch('aresos_control.retention.shutil.disk_usage',
                   return_value=SimpleNamespace(free=retention.RESTORE_RESERVE + cancel_room)):
            self.assertEqual(self.data('operation_cancel', {'operation_id': pending['operation_id']})['operation']['state'], 'failed')
        with patch('aresos_control.retention.shutil.disk_usage',
                   return_value=SimpleNamespace(free=cancel_room)):
            for options in ({}, {'recovery': True}, {'owner_recovery': True}):
                with self.assertRaises(Refused):
                    retention.disk_space(self.root, 1, **options)
        self.restart()
        self.assertEqual(self.engine.operation(pending['operation_id'])['state'], 'failed')
        before = self.snapshot()
        with patch.object(self.mail, 'send_smtp', side_effect=AssertionError('Cancelled approval must not submit')):
            self.assertEqual(self.data('send', pending)['operation']['state'], 'failed')
        self.assertEqual(self.snapshot(), before)
