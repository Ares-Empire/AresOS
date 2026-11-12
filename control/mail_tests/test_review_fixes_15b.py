"""Owner-approved folder moves: durable intent, post-check and no recovery."""
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

from support import MailCase
import test_review_fixes_15 as round15
import test_review_fixes_9 as round9
from aresos_control.common import RESULT_LIMIT, canonical, validate
from aresos_control.adapters import Uncertain
from aresos_control.definitions import BY_NAME
from aresos_control.engine import Engine
from aresos_control.mail.transport import folders


class RenamePolicy15b(unittest.TestCase):
    setUp = round15.Review15.setUp
    call = round15.Review15.call
    data = round15.Review15.data
    rename_command = round15.Review15.rename_command

    def test_review15b_protected_ancestors_warn_with_bounded_escaped_names(self):
        source = 'Source'
        for role in ('Trash', 'Drafts', 'Sent', 'Junk', 'Archive'):
            target = 'Parent\u202e' + 'x' * 100 + '/' + role
            before = copy.deepcopy(self.imap.boxes[source])
            stable = copy.deepcopy(self.imap.roles)
            def rename(old, new):
                self.imap.roles.update({name: [f for f in flags if f.casefold() != ('\\' + role).casefold()]
                                        for name, flags in self.imap.roles.items()})
                self.imap.roles[target.rpartition('/')[0]] = ['\\' + role]
                return self.rename_command(old, new)
            with self.subTest(role=role), patch.object(self.imap, 'rename', rename, create=True):
                result = self.call('folder_rename', {'account': 'box', 'folder': source, 'name': target})
            self.assertTrue(result['ok'], result)
            self.assertEqual(result['data']['state'], 'partial')
            self.assertIn('inside ' + role, result['data']['reason'])
            self.assertNotIn('\u202e', canonical(result))
            notice = result['pending']['notices'][0]
            self.assertIn('\\u202e', notice['untrusted_content']['reason'])
            self.assertLess(len(canonical(notice)), 4096)
            self.assertEqual(self.imap.boxes[target], before)
            self.assertEqual(self.imap.mutations[-1], ('RENAME', source, target))
            self.data('notice_ack', {'operation_id': notice['operation_id']})
            self.imap.roles = {**stable, target: []}
            del self.imap.roles[source]
            source = target

    def test_review15b_crash_after_rename_keeps_started_intent_and_never_replays(self):
        before = copy.deepcopy(self.imap.boxes['Source'])
        def crash(old, new):
            intent = self.engine.store.items('mail:rename:')[0][1]
            self.assertEqual(intent['state'], 'started')
            self.assertEqual(intent['source'], 'Source')
            self.assertEqual(intent['target'], 'Parent/Subfolder')
            self.assertEqual(intent['message_count'], len(before))
            self.assertEqual(intent['roles_before']['special'], self.account['special'])
            self.rename_command(old, new)
            raise SystemExit('Simulated crash after remote RENAME')
        with patch.object(self.imap, 'rename', crash, create=True), self.assertRaises(SystemExit):
            self.call('folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'Parent/Subfolder'})
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        intent = self.engine.store.items('mail:rename:')[0][1]
        self.assertEqual(intent['state'], 'started')
        self.assertEqual(self.imap.boxes['Parent/Subfolder'], before)
        self.assertEqual(self.imap.mutations, [('RENAME', 'Source', 'Parent/Subfolder')])
        log = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {}})
        self.assertTrue(log['ok'], log)
        self.assertIn('folder rename intent', canonical(log))
        self.assertIn('started', canonical(log))

    def test_review15b_special_source_and_destination_subtrees_still_refuse(self):
        for role in ('Trash', 'Drafts', 'Sent'):
            for source, target in (('Source', role + '/Child'), (role, 'Parent/Child')):
                with self.subTest(source=source, target=target):
                    result = self.call('folder_rename', {'account': 'box', 'folder': source, 'name': target})
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'refused')
                    self.assertEqual(self.imap.mutations, [])
                    self.assertEqual(self.engine.store.items('mail:rename:'), [])

    def test_review15b_unverifiable_postcheck_warns_without_recovery(self):
        from aresos_control.mail import filing
        before = copy.deepcopy(self.imap.boxes['Source'])
        with patch.object(self.imap, 'rename', self.rename_command, create=True), \
                patch.object(filing, 'folders', side_effect=Uncertain('Post-rename LIST disconnected')):
            result = self.call('folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'Parent/Subfolder'})
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data']['state'], 'partial')
        self.assertIn('unverified role', result['data']['reason'])
        self.assertEqual(len(result['pending']['notices']), 1)
        self.assertEqual(self.imap.boxes['Parent/Subfolder'], before)
        self.assertEqual(self.imap.mutations, [('RENAME', 'Source', 'Parent/Subfolder')])


class Review15b(MailCase):
    frontend = round9.ReviewFixes9.frontend
    role_map = round9.ReviewFixes9.role_map
    reassign = round9.ReviewFixes9.reassign
    raw_state = round9.ReviewFixes9.raw_state

    def run_rename(self, race=False, same_parent=False):
        with self.frontend() as (fixture, _):
            source = 'Parent/Source' if same_parent else 'Source'
            target = 'Parent/Subfolder'
            for name in ('Parent', source):
                self.data('folder_create', {'account': 'box', 'name': name})
            refs = [self.fixture(source, text='Preserved folder message ' + str(i)) for i in range(3)]
            original = [self.mail.message(ref)['raw'] for ref in refs]
            before_intents = []
            def before(command, arguments):
                if command == b'RENAME':
                    # Independent connection: this must already be committed before the wire command.
                    with sqlite3.connect(self.root / 'state/control.sqlite') as db:
                        before_intents.extend(json.loads(row[0]) for row in db.execute(
                            "SELECT v FROM kv WHERE k LIKE 'mail:rename:%'"))
                    if race:
                        self.reassign(fixture, 'trash', 'Parent')
            fixture.before_command = before
            fixture.commands.clear()
            result = self.call('folder_rename', {'account': 'box', 'folder': source,
                                               'name': 'Subfolder' if same_parent else target})
            self.assertTrue(result['ok'], result)
            validate(result, BY_NAME['mail_folder_rename'].tool()['outputSchema'])
            self.assertEqual(len(before_intents), 1)
            intent = before_intents[0]
            self.assertEqual((intent['source'], intent['target'], intent['message_count'], intent['state']),
                             (source, target, 3, 'started'))
            self.assertEqual(intent['roles_before']['special'], self.account['special'])
            mutations = [(cmd, args) for cmd, args in fixture.commands if cmd in (b'RENAME', b'DELETE', b'EXPUNGE')
                         or (cmd == b'UID' and args.split(b' ', 1)[0] in (b'MOVE', b'COPY', b'STORE', b'EXPUNGE'))]
            self.assertEqual(mutations, [(b'RENAME', ('"' + source + '" "' + target + '"').encode())])
            with self.mail.transport.imap(self.account) as client:
                names = [f['name'] for f in folders(client)]
            self.assertNotIn(source, names)
            self.assertIn(target, names)
            self.assertEqual([raw for _, raw, _ in self.raw_state([target])[target]], original)
            self.assertEqual(self.engine.store.items('op:'), [])
            final = self.engine.store.get('mail:rename:' + intent['id'])
            self.assertEqual(result['data']['folder'], target)
            self.assertEqual(final['state'], 'partial' if race else 'done')
            self.assertEqual(result['data']['state'], final['state'])
            if race:
                expected = ('The special folders changed while Claude was moving this folder. Nothing was deleted. '
                            'It is now Parent/Subfolder, inside Trash. Check it in your mail program.')
                self.assertEqual(result['data']['reason'], expected)
                self.assertEqual(final['roles_after']['special']['trash'], 'Parent')
                notice = result['pending']['notices'][0]
                self.assertEqual(notice['operation_id'], intent['id'])
                self.assertEqual(notice['untrusted_content']['message_count'], 3)
                self.assertEqual(notice['untrusted_content']['reason'], expected)
                self.assertEqual(self.data('filing_notices')['items'], [notice])
                self.assertEqual(self.call('accounts')['pending']['notices'], [notice])
                log = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {}})
                self.assertEqual(log['data']['notices'], [notice])
                self.assertLess(len(canonical(result)), RESULT_LIMIT)
                self.engine.close()
                self.engine = Engine(self.root / 'state', self.root / 'independent')
                self.mail = self.engine.adapters['mail']
                self.assertEqual(self.data('filing_notices')['items'], [notice])
                ack = self.data('notice_ack', {'operation_id': intent['id']})
                self.assertTrue(ack['notice']['ack'])
                self.assertNotIn('notices', self.call('accounts')['pending'])
                self.assertEqual([raw for _, raw, _ in self.raw_state([target])[target]], original)
            else:
                self.assertNotIn('reason', result['data'])
                self.assertNotIn('notices', result['pending'])
                self.assertEqual(self.data('filing_notices')['total'], 0)
                self.assertEqual(self.engine.store.items('notice:'), [])

    def test_review15b_review7_trash_parent_race_preserves_three_messages_and_repeats_notice(self):
        self.run_rename(race=True)

    def test_review15b_ordinary_cross_parent_move_done_without_warning(self):
        self.run_rename()

    def test_review15b_same_parent_rename_done_without_warning(self):
        self.run_rename(same_parent=True)
