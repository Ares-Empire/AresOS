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

    def test_review27_current_session_legacy_filing_checks_are_not_yet_checked(self):
        for prefix in ('mail:filing:', 'mail:rename:'):
            name = prefix.split(':')[1]
            self.engine.store.write({prefix + name: {'id': name, 'state': 'started'}}, 'fixture', 'Synthetic legacy check')
        for notices in (self.engine.pending()['notices'], self.data('filing_notices', {})['items']):
            self.assertEqual({n['operation_id'] for n in notices}, {'filing', 'rename'})
            self.assertTrue(all('not yet checked' in n['untrusted_content']['reason'] for n in notices))

    def test_review27_move_copy_and_rename_recheck_after_failed_result_commit(self):
        from test_review23_sweep import Scenario
        for flow in ('filing_move', 'filing_copy', 'filing_rename'):
            with self.subTest(flow=flow):
                scenario = Scenario(flow)
                try:
                    fixture = scenario.fixture
                    write = fixture.engine.store.write
                    def refuse(*args, **kwargs):
                        if scenario.remote:
                            raise Refused('storage_limit', 'Synthetic all post-filing result writes refused')
                        return write(*args, **kwargs)
                    with patch.object(fixture.engine.store, 'write', side_effect=refuse):
                        scenario.call()
                    prefix = 'mail:rename:' if flow.endswith('rename') else 'mail:filing:'
                    key, source = fixture.engine.store.items(prefix)[0]
                    self.assertEqual(source['state'], 'started')
                    self.assertEqual(source['account'], 'box')
                    self.assertIn('roles_before', source)
                    remote = scenario.remote.copy()
                    fixture.restart()
                    if not flow.endswith('rename'):
                        # A live scan that cannot finish leaves the check open.
                        with patch('aresos_control.mail.filing.locations', return_value=[{'scan_complete': False}]):
                            page = fixture.data('filing_notices', {})
                        self.assertEqual(fixture.engine.store.get(key)['state'], 'started')
                        own = next(n for n in page['items'] if n['operation_id'] == source['id'])
                        self.assertIn('not yet checked', own['untrusted_content']['reason'])
                    page = fixture.data('filing_notices', {})
                    self.assertEqual(fixture.engine.store.get(key)['state'], 'partial')
                    self.assertIn(source['id'], {n['operation_id'] for n in page['items']})
                    self.assertEqual(scenario.remote, remote)
                    if not flow.endswith('rename'):
                        locations = fixture.data('filing_locations', {'filing_id': source['id']})
                        self.assertTrue(all(v['scan_complete'] for v in locations['untrusted_content']['locations']))
                finally:
                    scenario.close()

    def test_review27_warning_assertion_rejects_review19_loss_before_status(self):
        from test_review23_sweep import Scenario
        from aresos_control.mail.filing import notice_page
        scenario = Scenario('status')
        try:
            fixture = scenario.fixture
            scenario.copies[scenario.operation_id] = [{'uid': 1}, {'uid': 2}]
            fixture.engine.store.write({'notice:unrelated': {'id': 'unrelated', 'app': 'mail',
                'state': 'partial', 'ack': False, 'untrusted_content': {'reason': 'Synthetic unrelated warning'}}},
                'fixture', 'A different owner warning')
            # Model review 19: no committed duplicate notice, and the old
            # pending/catalogue implementation never rediscovers a done send.
            with patch.object(fixture.mail, 'resolve_sent_checks', return_value=[]):
                self.assertGreater(notice_page(fixture.engine.store)['total'], 0)  # old oracle passes
                with self.assertRaisesRegex(AssertionError, 'Lost operation duplicate warning'):
                    scenario.assert_duplicate_warnings()
            # The new public view resolves it without an operation_status call.
            scenario.assert_duplicate_warnings()
        finally:
            scenario.close()
