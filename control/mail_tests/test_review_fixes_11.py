"""Round 11: adapter/Engine regressions without a provider or container."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import WORK
from aresos_control.common import RESULT_LIMIT, WIRE_LIMIT, canonical, validate, visible
from aresos_control.definitions import BY_NAME
from aresos_control.engine import Engine
from aresos_control.mail import codec, filing
from aresos_control.mail.roles import resolve
from aresos_control.mail.transport import folders, quote


class MemoryIMAP:
    """IMAP command substitute; production selection, fetch, parsing and filing run."""
    capabilities = ('UIDPLUS', 'MOVE')

    def __init__(self, count, mid, target='Target'):
        self.raw = (b'From: sender@mail.invalid\r\nTo: owner@mail.invalid\r\nSubject: Filing\r\nMessage-ID: '
                    + mid + b'\r\n\r\nPreserved message\r\n')
        self.mid = str(codec.parse(self.raw)['Message-ID'])
        self.roles = {'INBOX': [], 'Source': [], target: [], 'Sent': ['\\Sent'],
                      'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']}
        self.boxes = {name: {} for name in self.roles}
        self.boxes['Source'] = {i: self.raw for i in range(1, count + 1)}
        self.validities = {name: i for i, name in enumerate(self.roles, 1)}
        self.selected = None
        self.copyuid = None
        self.mutations = []

    def list(self):
        return 'OK', [('(' + ' '.join(flags) + ') "/" ' + quote(name)).encode()
                      for name, flags in self.roles.items()]

    def select(self, folder, readonly=True):
        self.selected = codec.unutf7(folder.strip('"'))
        return 'OK', [str(len(self.boxes[self.selected])).encode()]

    def response(self, name):
        if name == 'COPYUID':
            result, self.copyuid = self.copyuid, None
            return name, [result]
        return name, [str(self.validities[self.selected]).encode()]

    def uid(self, command, *args):
        box = self.boxes[self.selected]
        if command == 'SEARCH':
            return 'OK', [b' '.join(str(uid).encode() for uid in box)]
        if command == 'FETCH':
            uid, query = int(args[0]), args[1]
            raw = box[uid]
            meta = f'1 (UID {uid} FLAGS () RFC822.SIZE {len(raw)})'.encode()
            return 'OK', [(meta, raw)] if 'BODY.PEEK' in query else [meta]
        if command in ('MOVE', 'COPY'):
            uid, target = int(args[0]), codec.unutf7(args[1].strip('"'))
            destination_uid = max(self.boxes[target], default=0) + 1
            self.boxes[target][destination_uid] = box[uid]
            if command == 'MOVE':
                del box[uid]
            self.copyuid = f'{self.validities[target]} {uid} {destination_uid}'.encode()
            self.mutations.append((command, uid, target))
            self.roles['Trash'] = []
            self.roles[target] = ['\\Trash']
            return 'OK', [b'Filed']
        raise AssertionError(('Unexpected IMAP command', command, args))


class FilingNotices11(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: self.engine.close())

    def request(self, action, arguments=None):
        result = self.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': arguments or {}})
        self.assertTrue(result['ok'], result)
        self.assertLessEqual(len(canonical(result).encode()), RESULT_LIMIT)
        self.assertLess(len(canonical(result).encode()), WIRE_LIMIT)
        validate(result, BY_NAME[action].tool()['outputSchema'])
        return result

    def seed(self, fixture):
        mail = self.engine.adapters['mail']
        @contextmanager
        def imap(account):
            yield fixture
        patcher = patch.object(mail.transport, 'imap', imap)
        patcher.start()
        self.addCleanup(patcher.stop)
        account = {'id': 'box', 'addresses': ['owner@mail.invalid'], 'ready': True,
                   'capabilities': list(fixture.capabilities), 'smtp_capabilities': [], 'sent_policy': 'client',
                   'safe_folder_delete': False, 'format': 'plain', 'signature': '', **resolve(folders(fixture))}
        self.engine.store.write({'mail:account:box': account}, 'fixture', 'Synthetic in-memory account')
        return [{'account': 'box', 'folder': 'Source', 'uidvalidity': fixture.validities['Source'],
                 'uid': uid, 'message_id': fixture.mid} for uid in range(1, 21)]

    def read_locations(self, filing_id, first=None):
        records, chunks = [], {}
        page = first or self.request('mail_filing_locations', {'filing_id': filing_id})['data']
        cursors = set()
        while True:
            content = page['untrusted_content']
            self.assertLessEqual(len(canonical(content)), filing.LOCATION_PAGE_BYTES + 256)
            records.extend(content['locations'])
            for part in content['fragments']:
                value = chunks.setdefault(part['message_index'], '')
                self.assertEqual(len(value), part['offset'])
                value += part['json']
                self.assertLessEqual(len(value), part['total_characters'])
                if len(value) == part['total_characters']:
                    records.append(json.loads(value))
                chunks[part['message_index']] = value
            cursor = page['cursor']
            if cursor is None:
                return records
            self.assertNotIn(cursor, cursors)
            cursors.add(cursor)
            page = self.request('mail_filing_locations', {'filing_id': filing_id, 'cursor': cursor})['data']

    def exercise_race(self, count, mid, verb='move', target='Target'):
        fixture = MemoryIMAP(count, mid, target)
        refs = self.seed(fixture)
        result = self.request('mail_' + verb, {'references': refs, 'target': target})
        data = result['data']
        self.assertEqual(data['state'], 'partial')
        content = data['untrusted_content']
        filing_id = content['filing_id']
        saved = self.engine.store.get('mail:filing:' + filing_id)
        self.assertEqual(content['message_count'], 20)
        self.assertEqual(saved['state'], 'partial')
        notice = result['pending']['notices'][0]
        self.assertNotIn('locations', notice['untrusted_content'])
        self.assertNotIn('fragments', notice['untrusted_content'])
        self.assertEqual(notice['untrusted_content']['reason'], data['reason'])
        self.assertLess(len(canonical(notice)), 3072)
        self.assertIn('Nothing was deleted.', data['reason'])
        self.assertEqual(fixture.mutations, [(verb.upper(), 1, target)])
        self.assertEqual(len(fixture.boxes['Source']), count - (verb == 'move'))
        self.assertEqual(fixture.boxes[target], {1: fixture.raw})
        self.assertEqual(self.engine.store.items('op:'), [])
        for action in ('control_log', 'control_pending', 'mail_accounts'):
            response = self.request(action, {'limit': 1} if action.startswith('control_') else {})
            section = response['data'] if action.startswith('control_') else response['pending']
            self.assertEqual(section['notices'][0], notice)
        # Every audit page works, including entries containing the filing outcome.
        cursor = None
        while True:
            args = {'limit': 10, **({'cursor': cursor} if cursor else {})}
            response = self.request('control_log', args)
            cursor = response['data']['cursor']
            if cursor is None:
                break
        with patch.object(self.engine.store, 'audit', return_value=[]):
            self.assertEqual(self.request('control_log', {'limit': 1})['data']['notices'][0], notice)
        self.request('mail_read', {'reference': {**refs[1], 'uid': 2}})
        first = {'untrusted_content': {k: content[k] for k in ('locations', 'fragments')}, 'cursor': content['cursor']}
        actual = self.read_locations(filing_id, first)
        self.assertEqual(actual, visible(saved['locations']))
        self.assertEqual(len(actual), 20)
        for record in actual:
            self.assertEqual(len(record['observed_locations']), count + (verb == 'copy'))
            identities = [(r['folder'], r['uidvalidity'], r['uid']) for r in record['observed_locations']]
            self.assertEqual(len(set(identities)), len(identities))
        return fixture, filing_id, saved

    def test_review11_twenty_identical_messages_long_ids_deliver_and_page_exactly_once(self):
        self.exercise_race(20, b'<' + b'a' * 1400 + b'@mail.invalid>')

    def test_review11_four_thousand_identical_messages_deliver_and_page_exactly_once(self):
        self.exercise_race(4000, b'<identical@mail.invalid>')

    def test_review11_encoded_bidi_id_is_escaped_in_notices_and_location_pages(self):
        _, filing_id, saved = self.exercise_race(20, b'=?utf-8?b?PHJpZ2h04oCuaWRA bWFpbC5pbnZhbGlkPg==?='.replace(b' ', b''), 'copy', 'Target\u202e')
        self.assertIn('\u202e', saved['sources'][0]['message_id'])
        self.assertIn('\\u202e', self.read_locations(filing_id)[0]['source']['message_id'])
        notices = self.request('control_log')['data']['notices']
        self.assertIn('\\u202e', notices[0]['untrusted_content']['reason'])
        self.assertNotIn('\u202e', str(notices))
        self.assertNotIn('\u202e', str(self.request('control_pending')))
        self.assertNotIn('\u202e', str(self.request('mail_accounts')))
        ack = self.request('mail_notice_ack', {'operation_id': filing_id})
        self.assertTrue(ack['data']['notice']['ack'])
        self.assertNotIn('notices', ack['pending'])
        self.assertEqual(self.read_locations(filing_id), visible(saved['locations']))

    def test_review11_many_notices_are_bounded_newest_first_and_all_remain_reachable(self):
        changes = {}
        for index in range(150):
            filing_id = f'notice-{index}'
            names = ['界' * 510 + str(i) for i in range(8)]
            observed = [{'source': {'folder': name}, 'last_known_destination': None,
                         'observed_locations': [], 'scan_complete': True} for name in names]
            intent = {'id': filing_id, 'sources': [v['source'] for v in observed], 'target': names[-1],
                      'locations': observed, 'reason': filing.warning('move', [], observed, True)}
            content = filing.summary(intent)
            self.assertEqual(content['folders_more_text'], 'and 5 more')
            self.assertEqual(len(content['folders']), 3)
            self.assertTrue(all(len(name) <= filing.FOLDER_CHARS + 1 for name in content['folders']))
            changes['notice:' + filing_id] = {'id': filing_id, 'app': 'mail', 'state': 'partial',
                'ack': False, 'created_at': index, 'untrusted_content': content}
        self.engine.store.write(changes, 'fixture', 'Many synthetic notices')
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        expected = ['notice-' + str(i) for i in range(149, -1, -1)]
        for action in ('control_log', 'control_pending', 'mail_accounts'):
            response = self.request(action)
            section = response['data'] if action.startswith('control_') else response['pending']
            self.assertEqual([n['operation_id'] for n in section['notices']], expected[:3])
            self.assertEqual(section['notices_more'], {'count': 147, 'action': 'mail_filing_notices'})
        error = self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_read', 'arguments': {}})
        self.assertFalse(error['ok'])
        self.assertLessEqual(len(canonical(error).encode()), RESULT_LIMIT)
        self.assertEqual(len(error['pending']['notices']), 3)
        actual, cursor = [], None
        while True:
            response = self.request('mail_filing_notices', {'cursor': cursor} if cursor else {})['data']
            actual.extend(n['operation_id'] for n in response['items'])
            cursor = response['cursor']
            if not cursor:
                break
        self.assertEqual(actual, expected)
        stale_cursor = self.request('mail_filing_notices')['data']['cursor']
        self.request('mail_notice_ack', {'operation_id': expected[0]})
        stale = self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_filing_notices', 'arguments': {'cursor': stale_cursor}})
        self.assertEqual(stale['error']['code'], 'stale_reference')
        self.assertEqual(self.request('mail_filing_notices')['data']['total'], 149)

    def test_review11_legacy_large_notice_is_compact_escaped_and_details_stay_readable(self):
        source = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 1,
                  'message_id': '<' + 'x' * 2000 + '\u202e@mail.invalid>'}
        destination = {**source, 'folder': 'Target\u202e', 'uidvalidity': 2, 'uid': 2}
        observed = [{'source': source, 'last_known_destination': destination,
                     'observed_locations': [destination] * 30, 'scan_complete': True}]
        intent = {'id': 'legacy', 'verb': 'move', 'sources': [source], 'target': destination['folder'],
                  'state': 'partial', 'locations': observed, 'reason': 'Old oversized warning. ' * 4000}
        notice = {'id': 'legacy', 'app': 'mail', 'state': 'partial', 'ack': False,
                  'untrusted_content': {'filing_id': 'legacy', 'reason': intent['reason'], 'locations': observed}}
        self.engine.store.write({'mail:filing:legacy': intent, 'notice:legacy': notice}, 'fixture', 'Legacy filing state')
        for action in ('control_log', 'control_pending', 'mail_accounts'):
            response = self.request(action)
            section = response['data'] if action.startswith('control_') else response['pending']
            self.assertNotIn('locations', section['notices'][0]['untrusted_content'])
            self.assertNotIn('\u202e', str(section['notices']))
        self.assertEqual(self.read_locations('legacy'), visible(observed))
        self.assertTrue(self.request('mail_notice_ack', {'operation_id': 'legacy'})['data']['notice']['ack'])
        self.assertEqual(self.engine.store.get('mail:filing:legacy'), intent)

    def test_review11_location_cursors_are_filing_bound_and_jumbo_references_survive_restart(self):
        source = {'account': 'box', 'folder': 'Folder\u202e', 'uidvalidity': 1, 'uid': 1,
                  'message_id': '<' + 'é' * 20000 + '\u202e@mail.invalid>'}
        observed = [{'source': source, 'last_known_destination': None, 'observed_locations': [source], 'scan_complete': False}]
        pages = filing.location_pages(observed)
        changes = {}
        for filing_id in ('one', 'two'):
            prefix = 'mail:filing-locations:' + filing_id + ':'
            changes[prefix + 'meta'] = {'pages': len(pages), 'total_messages': 1}
            changes.update({prefix + str(i): page for i, page in enumerate(pages)})
        self.engine.store.write(changes, 'fixture', 'Synthetic jumbo references')
        cursor = self.request('mail_filing_locations', {'filing_id': 'one'})['data']['cursor']
        for bad in (cursor, 'two:-1', 'two:999999', 'malformed'):
            response = self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_filing_locations',
                                           'arguments': {'filing_id': 'two', 'cursor': bad}})
            self.assertFalse(response['ok'])
            self.assertEqual(response['error']['code'], 'stale_reference')
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.assertEqual(self.read_locations('one'), visible(observed))

