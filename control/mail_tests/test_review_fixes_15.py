"""Review 7: folder rename notices, boundary gating and journal overflow regression."""
import copy
from contextlib import contextmanager
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from aresos_control.boundary import Boundary
from aresos_control.common import JSONInputError, RESULT_LIMIT, canonical, validate
from aresos_control.definitions import BY_NAME
from aresos_control.engine import Engine
from aresos_control.mail import codec
from aresos_control.protocol import receive
from boundary_test_support import install_boundary
import test_review_fixes_12 as round12


class Review15(unittest.TestCase):
    setUp = round12.PlainQuestions12.setUp
    call = round12.PlainQuestions12.call
    data = round12.PlainQuestions12.data
    compose = round12.PlainQuestions12.compose
    reference = round12.PlainQuestions12.reference
    approval = round12.PlainQuestions12.approval

    def rename_command(self, source, target):
        source, target = (codec.unutf7(value.strip('"')) for value in (source, target))
        self.imap.mutations.append(('RENAME', source, target))
        self.imap.roles[target] = self.imap.roles.pop(source)
        self.imap.boxes[target] = self.imap.boxes.pop(source)
        self.imap.validities[target] = self.imap.validities.pop(source)
        return 'OK', [b'Renamed']

    def test_review15_cross_parent_reproduction_and_separator_use_exact_target(self):
        source = 'Source'
        before = copy.deepcopy(self.imap.boxes[source])
        for name in ('Parent/Subfolder', 'Source/Child', '/Other', 'Other/'):
            with self.subTest(name=name), patch.object(self.imap, 'rename', self.rename_command, create=True):
                expected = copy.deepcopy(self.imap.boxes)
                expected[name] = expected.pop(source)
                result = self.data('folder_rename', {'account': 'box', 'folder': source, 'name': name})
                self.assertEqual(result['state'], 'done')
                self.assertEqual(result['folder'], name)
                self.assertEqual(self.imap.mutations[-1], ('RENAME', source, name))
                self.assertNotIn(source, self.imap.boxes)
                self.assertEqual(self.imap.boxes[name], before)
                self.assertEqual(self.imap.boxes, expected)
                self.assertEqual(self.engine.store.items('op:'), [])
                self.assertEqual(self.engine.store.items('notice:'), [])
                source = name

    def test_review15_leaf_rename_retains_parent_and_all_messages(self):
        for values in (self.imap.roles, self.imap.boxes, self.imap.validities):
            values['Parent/Source'] = values.pop('Source')
        before = copy.deepcopy(self.imap.boxes['Parent/Source'])
        with patch.object(self.imap, 'rename', self.rename_command, create=True):
            result = self.data('folder_rename', {'account': 'box', 'folder': 'Parent/Source', 'name': 'New'})
        self.assertEqual(result['folder'], 'Parent/New')
        self.assertEqual(self.imap.mutations, [('RENAME', 'Parent/Source', 'Parent/New')])
        self.assertEqual(self.imap.boxes['Parent/New'], before)
        self.assertEqual(self.engine.store.items('notice:'), [])

    def test_review15_role_assigned_by_rename_persists_bounded_warning_and_ack(self):
        before = copy.deepcopy(self.imap.boxes['Source'])
        def rename(source, target):
            result = self.rename_command(source, target)
            self.imap.roles['New'] = ['\\Flagged']
            return result
        with patch.object(self.imap, 'rename', rename, create=True):
            result = self.call('folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'New'})
        self.assertTrue(result['ok'], result)
        validate(result, BY_NAME['mail_folder_rename'].tool()['outputSchema'])
        self.assertEqual(result['data']['state'], 'partial')
        self.assertIn('Flagged', result['data']['reason'])
        self.assertEqual(self.imap.boxes['New'], before)
        notices = result['pending']['notices']
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]['untrusted_content']['message_count'], len(before))
        filing_id = notices[0]['operation_id']
        self.assertEqual(self.engine.store.get('mail:rename:' + filing_id)['observed_role'], '\\Flagged')
        self.assertEqual(self.data('filing_notices', {})['total'], 1)
        log = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {}})
        self.assertEqual(log['data']['notices'], notices)
        self.assertLessEqual(len(canonical(result)), RESULT_LIMIT)
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        self.assertEqual(self.engine.pending('mail')['notices'], notices)
        ack = self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_notice_ack', 'arguments': {'operation_id': filing_id}})
        self.assertTrue(ack['ok'], ack)
        self.assertNotIn('notices', ack['pending'])

    def test_review15_repeated_special_role_flags_keep_notice_bounded(self):
        def rename(source, target):
            result = self.rename_command(source, target)
            self.imap.roles['New'] = ['\\Flagged', '\\fLAGGED', '\\Archive'] * 10000
            return result
        with patch.object(self.imap, 'rename', rename, create=True):
            result = self.call('folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'New'})
        self.assertTrue(result['ok'], result)
        self.assertLess(len(canonical(result)), RESULT_LIMIT)
        self.assertEqual(result['data']['state'], 'partial')
        self.assertEqual(result['data']['reason'].count('Flagged'), 1)
        self.assertEqual(result['data']['reason'].count('Archive'), 1)
        self.assertLess(len(canonical(result['pending']['notices'])), 2048)

    def test_review15_exact_saved_overflow_then_composition_restart_keeps_valid_evidence(self):
        before = (self.root / 'evidence/operations.jsonl').read_bytes()
        caller, service = socket.socketpair()
        with caller, service:
            caller.sendall(b'{"v":1,"method":"saved","app":"mail","outcome":1e400}\n')
            with self.assertRaises(JSONInputError):
                self.engine.request(receive(service))
        self.assertEqual((self.root / 'evidence/operations.jsonl').read_bytes(), before)
        composition = self.compose()
        self.assertIn('composition_id', composition)
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        self.assertFalse(self.engine.store.locked)
        self.assertFalse(self.engine.store.write_failed)
        self.assertTrue(self.engine.store.audit())

    def test_review15_mail_preparations_submissions_and_onboarding_require_boundary(self):
        cases = [('send', self.compose()), ('delete', {'items': [self.mail.named_item(self.reference())], 'mode': 'permanent'}),
                 ('folder_delete', {'account': 'box', 'folder': 'Target'})]
        approvals = [(verb, args, self.approval(verb, args)) for verb, args in cases]
        config = install_boundary(self.root / 'boundary')
        boundary_patch = patch.multiple('aresos_control.boundary', DEFAULT_SETTINGS=config['managed_settings'], DEFAULT_MCP=config['managed_mcp'])
        boundary_patch.start()
        self.addCleanup(boundary_patch.stop)
        self.engine.boundary = Boundary()
        Path(config['managed_settings']).unlink()
        for verb, args, approval in approvals:
            for action, data in [('prepare_' + verb, args), (verb, approval)]:
                result = self.call(action, data)
                self.assertEqual(result['error']['code'], 'boundary_not_installed', result)
            self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
        self.compose()
        self.assertTrue(self.call('accounts', {})['ok'])
        from aresos_control.mail.onboarding import onboard
        with patch.object(self.mail.transport, 'store_password') as password:
            with self.assertRaisesRegex(Exception, 'managed-settings.json'):
                onboard(self.engine, {'id': 'new'}, 'pass')
            password.assert_not_called()
        self.assertIsNone(self.engine.store.get('mail:account:new'))

    def test_review15_onboarding_rechecks_policy_before_marking_account_ready(self):
        from types import SimpleNamespace
        from aresos_control.mail.onboarding import onboard
        config = install_boundary(self.root / 'boundary')
        boundary_patch = patch.multiple('aresos_control.boundary', DEFAULT_SETTINGS=config['managed_settings'], DEFAULT_MCP=config['managed_mcp'])
        boundary_patch.start()
        self.addCleanup(boundary_patch.stop)
        self.engine.boundary = Boundary()
        @contextmanager
        def smtp(account):
            yield SimpleNamespace(esmtp_features={})
        def sent_matches(*args):
            Path(config['managed_settings']).unlink(missing_ok=True)
            return True
        arguments = {'id': 'new', 'addresses': ['owner@mail.invalid'], 'username': 'fixture',
            'imap_host': 'fixture', 'imap_port': 993, 'smtp_host': 'fixture', 'smtp_port': 465, 'smtp_tls': 'implicit'}
        with patch.object(self.mail.transport, 'store_password'), patch.object(self.mail.transport, 'smtp', smtp), \
                patch.object(self.imap, 'create', return_value=('OK', []), create=True), \
                patch.object(self.mail, 'append', return_value=self.reference()), \
                patch('aresos_control.mail.onboarding.qualify_folder_delete'), \
                patch.object(self.mail, 'compose', return_value={}), \
                patch.object(self.engine, 'reserve', return_value={'approval': {}}), \
                patch.object(self.engine, 'submit', return_value={'operation': {'id': 'probe', 'stages': {'smtp_data': 'accepted:250'}}}), \
                patch.object(self.mail, 'sent_matches', sent_matches):
            with self.assertRaisesRegex(Exception, 'managed-settings.json'):
                onboard(self.engine, arguments, 'pass')
        account = self.engine.store.get('mail:account:new')
        self.assertFalse(account['ready'])
        self.assertFalse(account.get('onboarded', False))
