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
        self.restart()
        with patch.object(self.mail.transport, 'imap', side_effect=OSError('Synthetic offline')):
            self.assertIn('not yet checked', str(self.engine.pending()))

