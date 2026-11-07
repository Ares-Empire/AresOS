"""Round 10: preserve mail after role races, persistent notices and interrupted scans."""
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import MailCase, WORK
import test_review_fixes_9 as review9
from aresos_control.adapters import Uncertain
from aresos_control.common import validate, sha256
from aresos_control.definitions import BY_NAME
from aresos_control.engine import Engine
from aresos_control.mail import filing
from aresos_control.mail.transport import select, uids, fetch, ok, quote


class FilingReporting10(unittest.TestCase):
    def test_review10_scan_retains_observations_when_transport_raises_uncertain(self):
        source = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 7, 'message_id': '<scan@mail.invalid>'}
        destination = {**source, 'folder': 'Target', 'uidvalidity': 2, 'uid': 9}
        class Mail:
            class transport:
                @staticmethod
                @contextmanager
                def imap(account):
                    yield object()
                    # The production context manager maps IMAP abort to Uncertain.
                    raise Uncertain('Connection lost')
            class wires:
                limit = 1024
        records = [{'source': source, 'destination': destination, 'sha256': sha256(b'preserved')}]
        with patch.object(filing, 'folders', return_value=[{'name': 'Target', 'flags': []}]), \
             patch.object(filing, 'select', return_value=2), patch.object(filing, 'uids', return_value=[9]), \
             patch.object(filing, 'fetch', return_value=(b'preserved', [])):
            result = filing.locations(Mail(), {}, records)
        self.assertFalse(result[0]['scan_complete'])
        self.assertEqual(result[0]['observed_locations'], [destination])
        self.assertEqual(result[0]['last_known_destination'], destination)

    def test_review10_notices_are_separate_from_approval_operations_and_survive_next_day(self):
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            root = Path(directory)
            engine = Engine(root / 'state', root / 'independent')
            try:
                content = {'reason': 'Nothing was deleted. Check them in your mail program.', 'filing_id': 'filing-notice'}
                notice = {'id': 'filing-notice', 'app': 'mail', 'state': 'partial', 'ack': False, 'untrusted_content': content}
                engine.store.write({'notice:filing-notice': notice}, 'mail_move', 'Filing outcome', outcome='partial')
                engine.close()
                engine = Engine(root / 'state', root / 'independent')
                self.assertEqual(engine.store.items('op:'), [])
                # Even with an empty audit page (including a later day's log),
                # the existing result/owner-log notice channel carries the full text.
                with patch.object(engine.store, 'audit', return_value=[]):
                    result = engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {}})
                self.assertTrue(result['ok'], result)
                validate(result, BY_NAME['control_log'].tool()['outputSchema'])
                self.assertEqual(result['data']['notices'][0]['untrusted_content'], content)
                following = engine.request({'v': 1, 'method': 'call', 'action': 'mail_accounts', 'arguments': {}})
                self.assertEqual(following['pending']['notices'][0]['untrusted_content'], content)
                wrong_app = engine.request({'v': 1, 'method': 'call', 'action': 'testapp_notice_ack', 'arguments': {'operation_id': notice['id']}})
                self.assertFalse(wrong_app['ok'])
                self.assertFalse(engine.store.get('notice:filing-notice')['ack'])
                ack = engine.request({'v': 1, 'method': 'call', 'action': 'mail_notice_ack', 'arguments': {'operation_id': notice['id']}})
                self.assertTrue(ack['ok'], ack)
                validate(ack, BY_NAME['mail_notice_ack'].tool()['outputSchema'])
                self.assertTrue(ack['data']['notice']['ack'])
                self.assertNotIn('notices', ack['pending'])
                self.assertEqual(engine.store.items('op:'), [])
            finally:
                engine.close()


class ReviewFixes10(MailCase):
    frontend = review9.ReviewFixes9.frontend
    role_map = review9.ReviewFixes9.role_map
    reassign = review9.ReviewFixes9.reassign
    raw_state = review9.ReviewFixes9.raw_state

    def assert_notice(self, result):
        validate(result, BY_NAME['mail_move' if 'moving' in result['data']['reason'] else 'mail_copy'].tool()['outputSchema'])
        data = result['data']
        self.assertEqual(data['state'], 'partial', result)
        self.assertIn('Nothing was deleted.', data['reason'])
        self.assertIn('Check them in your mail program.', data['reason'])
        notice = result['pending']['notices'][-1]
        self.assertEqual(notice['untrusted_content']['reason'], data['reason'])
        following = self.call('accounts')
        self.assertTrue(following['ok'], following)
        self.assertEqual(following['pending']['notices'][-1], notice)
        log = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {}})
        self.assertTrue(log['ok'], log)
        self.assertEqual(log['data']['notices'][-1], notice)
        intent = self.engine.store.get('mail:filing:' + data['untrusted_content']['filing_id'])
        self.assertEqual(intent['state'], 'partial')
        self.assertEqual(intent['locations'], data['untrusted_content']['locations'])
        events = [e for e in self.engine.store.audit() if e['action'] == 'mail_' + intent['verb']]
        self.assertEqual(events[-1]['outcome'], 'partial')
        self.assertEqual(self.engine.store.items('op:'), [])
        return data

    def assert_no_recovery(self, fixture, verb, count=1):
        mutations = [(command, args) for command, args in fixture.commands if command in (b'EXPUNGE', b'DELETE', b'RENAME') or
                     (command == b'UID' and args.split(b' ', 1)[0] in (b'MOVE', b'COPY', b'STORE', b'EXPUNGE'))]
        self.assertEqual(len(mutations), count, mutations)
        self.assertTrue(all(command == b'UID' and args.startswith(verb.upper().encode() + b' ') for command, args in mutations))

    def test_review10_review_reproductions_preserve_survivors_with_exact_locations_and_notices(self):
        for race in ('trash_source', 'replaced_source', 'copy_original_removed'):
            with self.subTest(race=race), self.frontend() as (fixture, backend):
                source_folder, target = 'Source-' + race, 'Target-' + race
                for name in (source_folder, target):
                    self.data('folder_create', {'account': 'box', 'name': name})
                source = self.fixture(source_folder, text=race)
                raw = self.mail.message(source)['raw']
                unrelated = self.fixture(target, text='Unrelated Deleted survives', flags='(\\Deleted)')
                verb = 'copy' if race == 'copy_original_removed' else 'move'
                fired = False
                def after(command, args):
                    nonlocal fired
                    if not fired and command == b'UID' and args.startswith(verb.upper().encode() + b' '):
                        fired = True
                        self.reassign(fixture, 'trash', source_folder if race == 'trash_source' else target)
                        if race == 'replaced_source':
                            with self.mail.transport.imap(backend) as client:
                                ok(client.rename(quote(source_folder), quote(source_folder + '-old')), 'Fixture renames emptied source')
                                ok(client.create(quote(source_folder)), 'Fixture replaces source')
                        elif race == 'copy_original_removed':
                            with self.mail.transport.imap(backend) as client:
                                self.assertEqual(select(client, source_folder), source['uidvalidity'])
                                ok(client.uid('STORE', str(source['uid']), '+FLAGS.SILENT', '(\\Deleted)'), 'External client deletes original')
                                ok(client.uid('EXPUNGE', str(source['uid'])), 'External client expunges original')
                fixture.after_command = after
                fixture.commands.clear()
                result = self.call(verb, {'references': [source], 'target': target})
                self.assertTrue(fired)
                data = self.assert_notice(result)
                state = self.raw_state([source_folder, target])
                self.assertEqual(state[source_folder], [])
                self.assertEqual(sum(body == raw for _, body, _ in state[target]), 1)
                self.assertIn(unrelated['uid'], [uid for uid, _, _ in state[target]])
                location = data['untrusted_content']['locations'][0]
                self.assertTrue(location['scan_complete'])
                self.assertEqual(location['source'], source)
                self.assertEqual(location['observed_locations'], [location['last_known_destination']])
                destination = location['last_known_destination']
                self.assertEqual(destination['folder'], target)
                self.assertNotEqual(destination['uid'], unrelated['uid'])
                self.assertEqual(self.mail.message(destination)['raw'], raw)
                self.assertIn(target + ', which is now ' + ('an ordinary folder' if race == 'trash_source' else 'Trash'), data['reason'])
                if verb == 'copy':
                    self.assertIn('the originals could not be verified in ' + source_folder, data['reason'])
                    self.assertNotIn('the originals stayed', data['reason'])
                if race == 'replaced_source':
                    with self.mail.transport.imap(backend) as client:
                        self.assertNotEqual(select(client, source_folder), source['uidvalidity'])
                self.assert_no_recovery(fixture, verb)
                ack = self.data('notice_ack', {'operation_id': data['untrusted_content']['filing_id']})
                self.assertTrue(ack['notice']['ack'])
                self.assertNotIn('notices', self.call('accounts')['pending'])

    def test_review10_copy_race_reports_preserved_original_and_copy_without_expunge(self):
        with self.frontend() as (fixture, _):
            target = 'CopyProtected'
            self.data('folder_create', {'account': 'box', 'name': target})
            source = self.fixture(text='Keep both copies')
            def after(command, args):
                if command == b'UID' and args.startswith(b'COPY '):
                    self.reassign(fixture, 'drafts', target)
            fixture.after_command = after
            fixture.commands.clear()
            data = self.assert_notice(self.call('copy', {'references': [source], 'target': target}))
            self.assertIn('The copies are now in ' + target + ', which is now Drafts; the originals stayed in INBOX.', data['reason'])
            locations = data['untrusted_content']['locations'][0]
            self.assertEqual(set(v['folder'] for v in locations['observed_locations']), {'INBOX', target})
            self.assertIn(source, locations['observed_locations'])
            self.assert_no_recovery(fixture, 'copy')

    def test_review10_connection_loss_during_location_scan_persists_partial_observations(self):
        with self.frontend() as (fixture, _):
            target = 'ScanTarget'
            self.data('folder_create', {'account': 'box', 'name': target})
            source = self.fixture(text='Survives an interrupted scan')
            def after(command, args):
                if command == b'UID' and args.startswith(b'MOVE '):
                    self.reassign(fixture, 'trash', target)
            fixture.after_command = after
            original_folders = filing.folders
            def target_first(client):
                listed = original_folders(client)
                return sorted(listed, key=lambda f: f['name'] != target)
            original_locations = filing.locations
            def interrupted(*args):
                fixture.disconnect_before_command = lambda command, arguments: (
                    command in (b'SELECT', b'EXAMINE') and arguments != quote(target).encode())
                try:
                    with patch.object(filing, 'folders', target_first):
                        return original_locations(*args)
                finally:
                    fixture.disconnect_before_command = lambda *_: False
            with patch.object(filing, 'locations', interrupted):
                data = self.assert_notice(self.call('move', {'references': [source], 'target': target}))
            location = data['untrusted_content']['locations'][0]
            self.assertFalse(location['scan_complete'])
            self.assertEqual(location['observed_locations'], [location['last_known_destination']])
            self.assertEqual(location['observed_locations'][0]['folder'], target)
            self.assertIn('location scan was interrupted', data['reason'])
            self.assertTrue(all(v['state'] != 'started' for _, v in self.engine.store.items('mail:filing:')))

    def test_review10_batch_stops_after_race_and_reports_untouched_messages(self):
        with self.frontend() as (fixture, _):
            target = 'BatchTarget'
            self.data('folder_create', {'account': 'box', 'name': target})
            sources = [self.fixture(text='Batch ' + str(i)) for i in range(2)]
            def after(command, args):
                if command == b'UID' and args.startswith(b'MOVE '):
                    self.reassign(fixture, 'trash', target)
            fixture.after_command = after
            fixture.commands.clear()
            data = self.assert_notice(self.call('move', {'references': sources, 'target': target}))
            locations = data['untrusted_content']['locations']
            self.assertEqual([v['source'] for v in locations], sources)
            self.assertEqual([v['folder'] for v in locations[0]['observed_locations']], [target])
            self.assertEqual(locations[1]['observed_locations'], [sources[1]])
            self.assertIsNone(locations[1]['last_known_destination'])
            self.assert_no_recovery(fixture, 'move')

    def test_review10_transient_role_round_trip_is_done_without_recovery(self):
        with self.frontend() as (fixture, _):
            for verb in ('move', 'copy'):
                with self.subTest(verb=verb):
                    target = 'Transient-' + verb
                    self.data('folder_create', {'account': 'box', 'name': target})
                    source = self.fixture(text=target)
                    raw = self.mail.message(source)['raw']
                    stable = {k: list(v) for k, v in fixture.role_map.items()}
                    fired = False
                    def before(command, args):
                        nonlocal fired
                        if not fired and command == b'UID' and args.startswith(verb.upper().encode() + b' '):
                            fired = True
                            self.reassign(fixture, 'trash', target)
                    def after(command, args):
                        if command == b'UID' and args.startswith(verb.upper().encode() + b' '):
                            fixture.role_map = {k: list(v) for k, v in stable.items()}
                    fixture.before_command, fixture.after_command = before, after
                    fixture.commands.clear()
                    result = self.data(verb, {'references': [source], 'target': target})
                    self.assertTrue(fired)
                    self.assertEqual(result['state'], 'done')
                    self.assertEqual(self.mail.message(result['items'][0])['raw'], raw)
                    self.assertEqual(self.engine.store.items('notice:'), [])
                    self.assert_no_recovery(fixture, verb)
                    fixture.before_command = fixture.after_command = lambda *_: None
