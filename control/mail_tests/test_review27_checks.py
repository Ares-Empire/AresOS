"""Round 27: committed check sources outlive failed result writes."""
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
import test_review_fixes_23 as prior


class Checks27(unittest.TestCase):
    setUp = prior.Results23.setUp
    call = prior.Results23.call
    data = prior.Results23.data
    compose = prior.Results23.compose
    approval = prior.Results23.approval
    restart = prior.Results23.restart

    def submit(self, approval):
        def smtp(operation, composition, raw, stage):
            stage('smtp_data', 'accepted:250')
            return 'done', 'Synthetic DATA acceptance'
        def append(account, folder, raw, flags):
            self.imap.boxes[folder][1] = raw
            return {'uid': 1}
        with patch.object(self.mail, 'send_smtp', side_effect=smtp), patch.object(self.mail, 'append', side_effect=append):
            return self.data('send', approval)['operation']

    def test_review27_reserved_at_startup_then_successful_send_has_no_recovery_notice(self):
        approval = self.approval('send', self.compose())
        self.restart()
        self.assertEqual(self.submit(approval)['state'], 'done')
        self.assertFalse(self.engine.pending().get('notices'))
        self.assertFalse(self.data('filing_notices', {})['items'])

    def test_review27_submitting_at_startup_still_has_recovery_notice(self):
        approval = self.approval('send', self.compose())
        operation = self.engine.operation(approval['operation_id'])
        operation['state'] = 'submitting'
        self.engine.store.write({'op:' + operation['id']: operation}, 'mail_send', 'Synthetic interrupted submission', operation['id'])
        self.restart()
        notices = self.data('filing_notices', {})['items']
        self.assertIn('recovery-' + operation['id'], {n['operation_id'] for n in notices})
