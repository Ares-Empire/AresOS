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

    def duplicate_loss(self, restart, catalogue):
        operation = self.submit(self.approval('send', self.compose()))
        self.assertFalse(self.engine.pending().get('notices'))
        self.assertTrue(self.engine.operation(operation['id'])['sent_copy_check']['clean'])
        self.imap.boxes['Sent'][2] = self.imap.boxes['Sent'][1]
        write = self.engine.store.write
        def refuse(changes, action, *args, **kwargs):
            if action == 'mail_sent_copy_check':
                raise Refused('storage_limit', 'Synthetic result admission refusal')
            return write(changes, action, *args, **kwargs)
        with patch.object(self.engine.store, 'write', side_effect=refuse):
            result = self.call('operation_status', {'operation_id': operation['id']})
            self.assertIn('2 copies', result['data']['evidence']['sent_copy_warning'])
            self.assertEqual(self.engine.operation(operation['id'])['state'], 'done')
            self.assertEqual(self.engine.operation(operation['id'])['sent_copy_check']['state'], 'open')
            self.assertTrue(any('not yet checked' in n['untrusted_content']['reason']
                                for n in result['pending']['notices']))
        if restart:
            self.restart()
        # No status read may recreate the warning before these assertions.
        with patch.object(self.mail, 'append', side_effect=AssertionError('Read-only recovery')):
            notices = self.data('filing_notices', {})['items'] if catalogue else self.engine.pending()['notices']
        own = [n for n in notices if n['untrusted_content'].get('operation_id') == operation['id']]
        self.assertEqual(len(own), 1, notices)
        self.assertEqual(own[0]['untrusted_content']['message_count'], 2)
        self.assertIn('2 copies', own[0]['untrusted_content']['reason'])
        self.assertEqual(self.engine.operation(operation['id'])['sent_copy_check']['state'], 'checked')

    def test_review27_duplicate_result_refused_pending_recovers_without_status_or_restart(self):
        self.duplicate_loss(False, False)

    def test_review27_duplicate_result_refused_catalogue_recovers_after_restart_before_status(self):
        self.duplicate_loss(True, True)

    def test_review27_clean_send_is_quiet_and_unreachable_recheck_is_explicit(self):
        operation = self.submit(self.approval('send', self.compose()))
        self.assertFalse(self.engine.pending().get('notices'))
        self.assertFalse(self.data('filing_notices', {})['items'])
        with patch.object(self.mail, 'sent_matches', side_effect=OSError('Synthetic unreachable server')):
            for notices in (self.engine.pending()['notices'], self.data('filing_notices', {})['items']):
                own = [n for n in notices if n['untrusted_content'].get('operation_id') == operation['id']]
                self.assertEqual(len(own), 1)
                self.assertIn('not yet checked', own[0]['untrusted_content']['reason'])
        self.assertFalse(self.engine.pending().get('notices'))

    def test_review27_open_check_and_warning_source_cannot_be_archived(self):
        import time
        from aresos_control.archive import archive
        operation = self.submit(self.approval('send', self.compose()))
        stored = self.engine.operation(operation['id'])
        stored['sent_copy_check'] = {'state': 'open'}
        self.engine.store.write({'op:' + stored['id']: stored}, 'fixture', 'Synthetic unresolved check')
        archive(self.engine.store, time.time() - 0.001)
        self.assertIsNotNone(self.engine.store.get('op:' + stored['id']))
