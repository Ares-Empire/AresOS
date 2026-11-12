"""Named review 20–22 cases. Setup/positive triggers precede the sole gap assert."""
import errno
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
from owner_state_oracle.compare import retained_role
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from owner_state_oracle.model import Fact, Oracle
from owner_state_oracle.records import decode
from test_review23_sweep import Scenario
import test_review27_checks as prior
import test_review28_checks as checks28
import test_review29_lifecycle as lifecycle29


class ReviewRegressions(unittest.TestCase):
    setUp = prior.Checks27.setUp
    call = prior.Checks27.call
    data = prior.Checks27.data
    restart = prior.Checks27.restart
    compose = prior.Checks27.compose
    approval = prior.Checks27.approval
    submit = prior.Checks27.submit
    owner_archive = checks28.Checks28.owner_archive

    def known_gap(self, gap, expected, actual):
        registry = Gaps()
        check = registry.checker(gap)
        check('assertion', expected, actual)
        check.finish()
        registry.verify({gap})

    def test_review22_live_rename_trash_with_unresolved_drafts_M03_C03(self):
        scenario = Scenario('filing_rename')
        try:
            f = scenario.fixture
            rename = f.imap.rename
            def changed(*args):
                reply = rename(*args)
                f.imap.roles['Drafts'] = []
                return reply
            d = Driver(scenario)
            with patch.object(f.imap, 'rename', side_effect=changed), d.observe():
                reply = scenario.call()
            d.reply(reply)
            self.assertTrue(reply['ok'], reply)
            self.assertEqual(scenario.remote['RENAME'], 1)
            self.assertEqual(f.imap.roles['Renamed'], ['\\Trash'])
            self.assertEqual(f.imap.roles['Drafts'], [])
            self.assertTrue(any(e['command'] == 'LIST' and e['roles'].get('Renamed') == ['\\Trash'] for e in d.oracle.servers))
            # One precise equality: observed Trash may not become "unverified".
            expected = {Fact('rename', 'role', detail='Trash')}
            reason = reply['data']['reason']
            actual = {Fact('rename', 'role', detail='Trash' if 'Trash' in reason else 'unverified')}
            self.known_gap('G22-rename', expected, actual)
        finally:
            scenario.close()

    def test_review22_refused_recovery_result_keeps_changed_evidence_M03_C03(self):
        key = 'mail:rename:interrupted'
        self.imap.roles['Drafts'] = []
        self.engine.store.write({key: {'id': 'interrupted', 'state': 'started', 'account': 'box',
            'source': 'Source', 'target': 'Target', 'message_count': 1, 'roles_before': {}}},
            'fixture', 'Synthetic interrupted rename')
        first = self.data('filing_notices', {})['items'][0]
        self.data('notice_ack', {'operation_id': first['operation_id']})
        self.imap.roles['Trash'], self.imap.roles['Target'] = [], ['\\Trash']
        fake = SimpleNamespace(fixture=self, action='mail_filing_notices', args={})
        driver = Driver(fake)
        original = self.engine.store.write
        def refuse(changes, action, *args, **kwargs):
            if action == 'mail_filing_check':
                raise Refused('storage_limit', 'Synthetic refused recovery result')
            return original(changes, action, *args, **kwargs)
        with patch.object(self.engine.store, 'write', side_effect=refuse), driver.observe():
            failed = self.call('filing_notices', {})
        driver.reply(failed)
        self.assertTrue(any(e['command'] == 'LIST' and e['roles'].get('Target') == ['\\Trash'] for e in driver.oracle.servers))
        self.imap.roles['Target'], self.imap.roles['Trash'] = [], ['\\Trash']
        self.imap.roles['Drafts'] = ['\\Drafts']
        page = self.data('filing_notices', {})
        wanted = {Fact(key, 'observed-role', detail='Trash')}
        actual = retained_role(key, 'Trash', decode(self.root / 'state', self.root / 'evidence'), page)
        self.known_gap('G22-evidence', wanted, actual)

    def test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13(self):
        oracle = Oracle()
        oracle.call('mail_compose', {'text': 'local only'}, 100, {'at': 'journal.write', 'bytes_written': 0})
        journal = self.engine.store.journal
        size = journal.seek(0, 2)
        with patch.object(journal, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic before any bytes')):
            failed = self.call('compose', {'account': 'box', 'to': ['peer@mail.invalid'], 'text': 'local only'})
        self.assertFalse(failed['ok'])
        self.assertEqual(failed['error']['code'], 'storage_limit')
        self.assertEqual(journal.seek(0, 2), size)
        oracle.reply(failed)
        oracle.call('mail_compose', {'text': 'healthy local write'}, 101)
        reply = self.call('compose', {'account': 'box', 'to': ['peer@mail.invalid'], 'text': 'healthy local write'})
        oracle.reply(reply)
        self.known_gap('G22-latch',
            oracle.request_state(decode(self.root / 'state', self.root / 'evidence'), oracle.script[-1]), {Fact('request', 'allowed' if reply['ok'] else reply['error']['code'])})

    # These remain named regression tests (not expected failures), and the
    # independent sweep separately exercises their operations/views.
    test_review20_refused_reopen_then_archive = checks28.Checks28.test_review28_refused_reopening_then_crash_archive_preserves_late_duplicate
    test_review21_acknowledged_rename_expiry = lifecycle29.Lifecycle29.test_review29_rename_refused_result_offline_ack_expiry_then_trash_is_new_occurrence
    test_review21_paging_changed_warnings = lifecycle29.Lifecycle29.test_review29_four_interrupted_renames_page_oldest_trash_and_keep_three_acknowledged
