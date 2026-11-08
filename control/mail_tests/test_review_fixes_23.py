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

