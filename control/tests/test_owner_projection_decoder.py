"""Cross-check the independent decoder and publication integrity at file boundaries."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from aresos_control.common import canonical
from aresos_control.storage import Store
from owner_state_oracle.records import decode, fingerprint

WORK = Path(__file__).resolve().parents[2] / '.work' / 'owner-decoder-tests'
WORK.mkdir(parents=True, exist_ok=True)


class OwnerDecoder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'state', self.root / 'evidence')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_context_identities_survive_without_authored_text_or_raw_recipients(self):
        key = 'intent:' + 'a' * 32
        context = {'command': 'MOVE', 'account': 'box', 'source': 'Source', 'destination': 'Target',
                   'roles': {'trash': ['Trash']}, 'identities': [{'account': 'box', 'folder': 'Source',
                   'uidvalidity': 9, 'uid': 7}], 'recipients': ['one@mail.invalid'],
                   'arguments': {'text': 'Authored text stays outside the projection'}}
        self.store.write({key: {'id': 'recovery-' + 'a' * 32, 'app': 'mail', 'action': 'mail_move',
                               'state': 'started', 'context_version': 1, 'context': context}}, 'fixture', 'Synthetic context')
        record = decode(self.root / 'state', self.root / 'evidence')
        actual = record.owner_rows[key]['context']
        self.assertEqual({'account': 'box', 'folder': 'Source', 'uidvalidity': 9, 'uid': 7}, actual['identities'][0])
        self.assertEqual('Target', actual['destination'])
        self.assertEqual({'trash': ['Trash']}, actual['roles'])
        self.assertEqual(1, actual['recipient_count'])
        self.assertEqual([fingerprint('one@mail.invalid')], actual['recipients'])
        self.assertNotIn('arguments', actual)
        self.assertNotIn('one@mail.invalid', canonical(record.owner_versions))
        self.assertNotIn('Authored text', canonical(record.owner_versions))

    def test_committed_source_without_projection_is_not_a_quiet_empty_view(self):
        with patch.object(self.store.owner_projection, 'prepare'):
            self.store.write({'intent:missing': {'id': 'recovery-missing', 'app': 'mail', 'state': 'started'}},
                             'fixture', 'Planted missing owner source')
        with self.assertRaisesRegex(ValueError, 'Missing committed owner projection'):
            decode(self.root / 'state', self.root / 'evidence')

    def test_rechained_false_ack_cannot_change_the_independent_publication(self):
        self.store.write({'notice:warning': {'id': 'warning', 'app': 'mail', 'ack': False,
                         'state': 'partial', 'source_key': 'intent:open',
                         'untrusted_content': {'reason': 'Synthetic warning'}}}, 'fixture', 'Synthetic warning')
        path = self.store.owner_projection.path
        raw = path.read_bytes()
        offset, previous = 8, bytes(32)
        output = bytearray(raw[:8])
        while offset < len(raw):
            size, seq = struct.unpack('>IQ', raw[offset:offset + 12])
            payload = raw[offset + 12:offset + 12 + size]
            data = json.loads(zlib.decompress(payload))
            if 'notice:warning' in data:
                data['notice:warning']['facts']['ack'] = True
                payload = zlib.compress(canonical(data).encode(), 9)
            header = struct.pack('>IQ', len(payload), seq)
            fence = next(row for row in self.store.events if row['seq'] == seq)
            chain = hashlib.sha256(previous + header + payload + bytes.fromhex(fence['hash'])).digest()
            output.extend(header + payload + chain)
            previous, offset = chain, offset + size + 44
        path.write_bytes(output)
        with self.assertRaisesRegex(ValueError, 'Owner publication hash mismatch'):
            decode(self.root / 'state', self.root / 'evidence')

    def test_projection_fields_are_all_in_the_alteration_audit(self):
        from owner_state_oracle.perturb import field_paths, mutations
        self.store.write({'intent:open': {'id': 'recovery-open', 'app': 'mail', 'state': 'started'}},
                         'fixture', 'Synthetic open source')
        record = decode(self.root / 'state', self.root / 'evidence')
        required = {path for path in field_paths(record) if path.startswith(('owner_rows/', 'owner_sequences/', 'owner_versions/'))}
        changed = {path for path,_,_ in mutations(record)}
        self.assertTrue(required)
        self.assertTrue(required <= changed, required - changed)


if __name__ == '__main__':
    unittest.main()
