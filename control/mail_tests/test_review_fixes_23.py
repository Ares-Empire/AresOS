"""Review 15: observations and the original storage error survive every handler."""
import errno
import os
import stat
import unittest
from unittest.mock import patch

import test_review_fixes_22 as round22


class Results23(unittest.TestCase):
    setUp = round22.Duplicates22.setUp
    call = round22.Duplicates22.call
    data = round22.Duplicates22.data
    compose = round22.Duplicates22.compose
    approval = round22.Duplicates22.approval
    send = round22.Duplicates22.send
    pending_append = round22.Duplicates22.pending_append
    restart = round22.Duplicates22.restart

    def test_review23_live_send_and_repair_keep_duplicate_observation_on_failed_warning_write(self):
        for repairing in (False, True):
            with self.subTest(repairing=repairing):
                approval = self.approval('send', self.compose())
                if repairing:
                    old = self.send('sent_copy')
                    op_id = old['id']
                    verb, args = 'operation_repair', {'operation_id': op_id, 'stage': 'sent_copy'}
                else:
                    op_id = approval['operation_id']
                    verb, args = 'send', approval
                def append(account, folder, raw, flags):
                    self.imap.boxes[folder].update({1: raw, 2: raw})
                    return {'uid': 2}
                write = self.engine.store.write
                def fail(changes, action, *args, **kwargs):
                    if action == 'mail_sent_copy_check':
                        raise OSError(errno.ENOSPC, 'Synthetic full disk')
                    return write(changes, action, *args, **kwargs)
                def smtp(operation, composition, raw, stage):
                    stage('smtp_data', 'accepted:250')
                    return 'done', 'Synthetic DATA acceptance'
                with patch.object(self.mail, 'append', side_effect=append), \
                     patch.object(self.engine.store, 'write', side_effect=fail), \
                     patch.object(self.mail, 'send_smtp', side_effect=smtp):
                    result = self.call(verb, args)
                self.assertFalse(result['ok'], result)
                self.assertIn('Disk full', result['error']['message'])
                evidence = result['observations']['evidence'][op_id]
                self.assertEqual(len(evidence['sent']), 2)
                self.assertIn('2 copies', evidence['sent_copy_warning'])
                self.assertEqual(result['observations']['stages'][op_id]['sent_copy'], 'done')
                self.assertEqual(len(self.imap.boxes['Sent']), 2)
                self.restart()
                self.assertIn('2 copies', self.data('operation_status', {'operation_id': op_id})['evidence']['sent_copy_warning'])
                self.imap.boxes['Sent'].clear()

    def test_review23_first_stage_storage_error_survives_outcome_latch_and_restart(self):
        for number in (errno.ENOSPC, errno.EDQUOT, errno.EIO):
            with self.subTest(errno=number):
                approval = self.approval('send', self.compose())
                write = self.engine.store.journal.write
                count = 0
                def fail(data):
                    nonlocal count
                    count += 1
                    # submitting's fence and marker succeed, first stage fails.
                    if count == 3:
                        raise OSError(number, 'Synthetic storage failure')
                    return write(data)
                with patch.object(self.engine.store.journal, 'write', side_effect=fail), \
                     patch.object(self.mail, 'send_smtp', side_effect=AssertionError('No DATA after stage failure')):
                    result = self.call('send', approval)
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error']['code'], 'storage_error' if number == errno.EIO else 'storage_limit')
                self.assertIn('Storage I/O' if number == errno.EIO else 'Disk full', result['error']['message'])
                self.assertEqual(result['observations']['stages'][approval['operation_id']]['message_id'],
                                 self.mail.message_id(approval['operation_id']))
                self.assertTrue(self.engine.store.write_failed)
                self.restart()
                self.assertEqual(self.data('operation_status', {'operation_id': approval['operation_id']})['operation']['state'], 'unknown')
                with patch.object(self.mail, 'send_smtp', side_effect=AssertionError('Must never resubmit')):
                    self.assertEqual(self.data('send', approval)['operation']['state'], 'unknown')

    def test_review23_short_stage_writes_and_failed_cleanup_keep_the_first_error(self):
        for fault in ('zero', 'short', 'cleanup'):
            with self.subTest(fault=fault):
                approval = self.approval('send', self.compose())
                write, sync = self.engine.store.journal.write, os.fsync
                count = 0
                def fail(data):
                    nonlocal count
                    count += 1
                    if count == 3:
                        if fault == 'cleanup':
                            raise OSError(errno.ENOSPC, 'Synthetic original full disk')
                        return write(data[:0 if fault == 'zero' else 13])
                    return write(data)
                def cleanup(fd):
                    if count == 3 and fault == 'cleanup':
                        raise OSError(errno.EIO, 'Synthetic subsequent cleanup failure')
                    return sync(fd)
                with patch.object(self.engine.store.journal, 'write', side_effect=fail), \
                     patch('os.fsync', side_effect=cleanup):
                    result = self.call('send', approval)
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error']['code'], 'storage_limit')
                self.assertIn('Disk full', result['error']['message'])
                self.assertIn('message_id', result['observations']['stages'][approval['operation_id']])
                self.restart()
                self.assertEqual(self.data('operation_status', {'operation_id': approval['operation_id']})['operation']['state'], 'unknown')

    def test_review23_private_wire_io_error_survives_blob_and_execution_handlers(self):
        approval = self.approval('send', self.compose())
        sync = os.fsync
        def fail(fd):
            if fd != self.engine.store.journal.fileno() and stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError(errno.EIO, 'Synthetic private wire I/O failure')
            return sync(fd)
        with patch('os.fsync', side_effect=fail), \
             patch.object(self.mail, 'send_smtp', side_effect=AssertionError('No DATA after wire failure')):
            result = self.call('send', approval)
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'storage_error')
        self.assertIn('Storage I/O', result['error']['message'])
        self.assertEqual(list(self.mail.wires.directory.iterdir()), [])
