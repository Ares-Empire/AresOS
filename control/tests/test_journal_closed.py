"""Invalid values cannot fence a write; incomplete transactions stop further writes."""
from unittest.mock import patch

from aresos_control.common import Refused, sha256
from support import EngineCase, message


class JournalClosed(EngineCase):
    def snapshot(self):
        store = self.engine.store
        return ((store.evidence_dir / 'operations.jsonl').read_bytes(), list(store.db.iterdump()),
                list(self.engine.blobs.directory.iterdir()))

    def test_complete_event_serialized_before_any_durable_change(self):
        for value in (float('inf'), float('nan'), 2**63, '\ud800', object(), {'bad': {1: 'key'}}):
            for field in ('changes', 'content'):
                with self.subTest(value=repr(value), field=field):
                    before = self.snapshot()
                    with self.assertRaises((ValueError, TypeError, UnicodeError)):
                        self.engine.store.write({'bad': value} if field == 'changes' else {}, 'fixture', 'bad event',
                            untrusted_content=None if field == 'changes' else {'bad': value})
                    self.assertEqual(self.snapshot(), before)
                    self.assertFalse(self.engine.store.write_failed)
        self.reserve()

    def test_every_envelope_and_payload_validated_before_dispatch_including_saved(self):
        file = {'sha256': sha256(b'x'), 'size': 1, 'name': 'x', 'real_path': '/fixture/x'}
        requests = [({'method': 'tools', 'app': 'mail'}, False),
                    ({'method': 'call', 'action': 'testapp_list', 'arguments': {}}, False),
                    ({'method': 'upload', 'app': 'mail', 'file': file}, False),
                    ({'method': 'download', 'app': 'mail', 'sha256': file['sha256']}, False),
                    ({'method': 'saved', 'app': 'mail', 'outcome': 'refused'}, False),
                    ({'method': 'mail_account_add', 'arguments': {}, 'password': 'pass'}, True)]
        for payload, admin in requests:
            valid = {'v': 1, **payload}
            bad = [{**valid, 'extra': 1}, {**valid, 'v': True}]
            bad += [{k: v for k, v in valid.items() if k != missing} for missing in valid]
            bad += [{**valid, key: []} for key in payload]
            for request in bad:
                with self.subTest(request=request):
                    before = self.snapshot()
                    with patch.object(self.engine, 'dispatch') as dispatch:
                        result = self.engine.request(request, admin)
                    self.assertFalse(result['ok'], result)
                    dispatch.assert_not_called()
                    self.assertEqual(self.snapshot(), before)
        for outcome in (None, 42, 1e400, [], {}, {'path': 'x', 'sha256': 'x', 'size': True}, 'done'):
            before = self.snapshot()
            self.assertFalse(self.engine.request({'v': 1, 'method': 'saved', 'app': 'mail', 'outcome': outcome})['ok'])
            self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.engine.request({'v': 1, 'method': 'saved', 'app': 'mail',
            'outcome': {'path': '/fixture/x', 'sha256': file['sha256'], 'size': 1}})['ok'])

    def test_incomplete_submission_stage_stops_before_next_recipient(self):
        approval = self.reserve()
        writes = 0
        def fail(name):
            nonlocal writes
            if name == 'journal_appended':
                writes += 1
                if writes == 2:
                    raise OSError('injected stage write failure')
        self.engine.store.checkpoint = fail
        self.assertFalse(self.call('testapp_send', approval)['ok'])
        self.assertTrue(self.engine.store.write_failed)
        self.assertEqual(self.engine.receiver.evidence(approval['operation_id'])['arrivals'], ['alpha'])
        before = self.snapshot()
        self.assertEqual(self.call('testapp_send', approval)['error']['code'], 'storage_error')
        self.assertEqual(self.snapshot(), before)

    def test_incomplete_transaction_blocks_requests_blobs_expiry_and_restore_until_restart(self):
        for point in ('journal_appended', 'sqlite_prepared', 'sqlite_committed', 'journal_committed'):
            with self.subTest(point=point):
                def fail(name):
                    if name == point:
                        raise OSError('injected incomplete write')
                self.engine.store.checkpoint = fail
                self.assertFalse(self.call('testapp_prepare_send', message())['ok'])
                self.assertTrue(self.engine.store.write_failed)
                before = self.snapshot()
                for action, args, admin in [('testapp_prepare_send', message(), False),
                        ('testapp_fixture_configure', {'failure': 'none', 'refuse': []}, True),
                        ('mail_compose', {'account': 'box'}, False),
                        ('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, True)]:
                    self.assertEqual(self.call(action, args, admin)['error']['code'], 'storage_error')
                for blob_store in (self.engine.blobs, self.engine.adapters['mail'].wires):
                    with self.assertRaises(Refused) as error:
                        blob_store.put(b'no write')
                    self.assertEqual(error.exception.code, 'storage_error')
                self.engine.expire()
                self.data('testapp_list')
                self.assertEqual(self.snapshot(), before)
                self.restart()
                self.assertFalse(self.engine.store.write_failed)
                if self.engine.store.locked:
                    self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
                self.reserve()
