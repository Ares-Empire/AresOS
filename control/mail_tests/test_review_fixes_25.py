"""Review 17: bounded disclosures, admission recovery and paired cleanup faults."""
import errno
import json
import os
import time
import unittest
from unittest.mock import patch

from aresos_control.common import RESULT_LIMIT, WIRE_LIMIT, canonical, Refused
from aresos_control.results import Observations
from response_checks import transport_response
import test_review_fixes_11 as filing11
import test_review_fixes_23 as results23


class Responses25(unittest.TestCase):
    setUp = filing11.FilingNotices11.setUp
    seed = filing11.FilingNotices11.seed

    def test_review25_long_id_350_copies_post_move_enospc_keeps_warning_and_location_pages(self):
        fixture = filing11.MemoryIMAP(1, b'<' + b'x' * 980 + b'@mail.invalid>')
        refs = self.seed(fixture)[:1]
        fixture.boxes['Target'].update({uid: fixture.raw for uid in range(1, 350)})
        write = self.engine.store.journal.write
        def fail_after_move(data):
            if fixture.mutations:
                raise OSError(errno.ENOSPC, 'Synthetic full disk after MOVE')
            return write(data)
        with patch.object(self.engine.store.journal, 'write', side_effect=fail_after_move):
            result = self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_move',
                                          'arguments': {'references': refs, 'target': 'Target'}})
            self.assertFalse(result['ok'], result)
            self.assertIn('Disk full', result['error']['message'])
            evidence = next(iter(result['observations']['evidence'].values()))
            self.assertIn('Nothing was deleted', evidence['reason'])
            self.assertIn('Trash', evidence['reason'])
            self.assertEqual(evidence['count'], 350)
            self.assertTrue(evidence['cursor'])
            self.assertTrue(evidence['fragments'])
            self.assertIn('Nothing was deleted', result['pending']['notices'][0]['untrusted_content']['reason'])
            self.assertLessEqual(len(canonical(result).encode()), RESULT_LIMIT)
            transport_response(result)
            print(f'Review25 jumbo filing response: {len(canonical(result).encode()) + 1} serialized bytes including newline; 350 observed locations', flush=True)
            # The failed write's deferred pages are readable without persisting.
            filing_id = evidence['filing_id']
            page = self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_filing_locations',
                'arguments': {'filing_id': filing_id, 'cursor': evidence['cursor']}})
            self.assertFalse(page['ok'], page)
            self.assertIn('Disk full', page['error']['message'])
            self.assertGreater(page['data']['untrusted_content']['fragments'][0]['offset'], 0)
            self.assertEqual(len(fixture.boxes['Target']), 350)
            self.assertEqual(fixture.mutations, [('MOVE', 1, 'Target')])

    def test_review25_final_size_check_pages_all_observations_and_keeps_every_warning(self):
        observation = Observations()
        warning = '2 copies found; inspect before further changes.'
        facts = {'sent': [{'uid': uid, 'message_id': 'x' * 20000} for uid in range(350)],
                 'sent_copy_warning': warning, 'reason': 'Nothing was deleted.', 'observed_role': 'Trash'}
        observation.observe('synthetic', facts)
        observation.storage(OSError(errno.ENOSPC, 'Synthetic full disk'))
        result = observation.finish({'ok': True, 'data': {'untrusted_content': {'text': 'x' * 45000}}, 'pending': {}}, self.engine.store)
        self.assertIn('Disk full', result['error']['message'])
        self.assertIn(warning, [item['value'] for item in result['observations']['warnings']])
        self.assertIn('Nothing was deleted.', [item['value'] for item in result['observations']['warnings']])
        self.assertLessEqual(len(canonical(result).encode()), RESULT_LIMIT)
        transport_response(result)
        first = result['observations']
        pieces = first['fragments'][:]
        cursor = first['cursor']
        while cursor:
            response = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_observations',
                                           'arguments': {'cursor': cursor}})
            self.assertTrue(response['ok'], response)
            self.assertLessEqual(len(canonical(response).encode()), RESULT_LIMIT)
            self.assertEqual(response['data']['warnings'], first['warnings'])
            pieces.extend(response['data']['fragments'])
            cursor = response['data']['cursor']
        raw = ''
        for piece in pieces:
            self.assertEqual(piece['offset'], len(raw))
            raw += piece['json']
        self.assertEqual(len(raw), first['count'])
        self.assertEqual(json.loads(raw)['evidence']['synthetic'], facts)
        self.assertEqual(json.loads(raw)['data']['untrusted_content']['text'], 'x' * 45000)

    def test_review25_central_harness_rejects_transport_oversize_on_success_and_failure(self):
        for ok in (False, True):
            with self.subTest(ok=ok), patch.object(self.engine, '_admitted_request', return_value={
                    'ok': ok, 'pending': {}, 'data': {'text': 'x' * WIRE_LIMIT}}):
                result = self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_accounts', 'arguments': {}})
                self.assertEqual(result['ok'], ok)
                self.assertLessEqual(len(canonical(result)), RESULT_LIMIT)
                self.assertGreater(result['bounds']['omitted_characters'], WIRE_LIMIT)
                transport_response(result)


class Admission25(unittest.TestCase):
    setUp = results23.Results23.setUp
    compose = results23.Results23.compose
    data = results23.Results23.data
    call = results23.Results23.call

    def test_review25_background_blob_expiry_admission_recovers_without_restart(self):
        key = self.engine.blobs.put(b'Synthetic expired bytes')
        path = self.engine.blobs.directory / key
        old = time.time() - 86401
        os.utime(path, (old, old))
        before = self.engine.store.sequence
        def no_space(*args, **kwargs):
            raise Refused('storage_limit', 'Storage ledger: free storage. No journal transaction started.')
        with patch.object(self.engine.store.ledger, 'admit', side_effect=no_space), self.assertLogs('aresos_control.engine', level='ERROR'):
            with self.assertRaises(Refused):
                self.engine.expire()
        self.assertEqual(self.engine.store.sequence, before)
        self.assertFalse(self.engine.store.write_failed)
        self.assertTrue(path.exists())
        pending = self.engine.pending('mail')
        self.assertIn('No journal transaction started', pending['notices'][0]['untrusted_content']['reason'])
        self.assertIn('composition_id', self.compose())
        self.engine.expire()
        self.assertFalse(path.exists())
        self.assertFalse(self.engine.store.write_failed)
        self.assertTrue(self.engine.store.get('notice:background-storage'))


class Cleanup25(unittest.TestCase):
    setUp = results23.Results23.setUp
    compose = results23.Results23.compose
    approval = results23.Results23.approval
    call = results23.Results23.call
    data = results23.Results23.data

    def paired_write(self, call):
        from contextlib import contextmanager
        opened = os.fdopen
        @contextmanager
        def fdopen(*args, **kwargs):
            with opened(*args, **kwargs) as stream:
                with patch.object(stream, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic primary full disk')):
                    yield stream
        def unlink(path, *args, **kwargs):
            raise OSError(errno.EIO, 'Synthetic cleanup I/O failure')
        with patch('os.fdopen', side_effect=fdopen), patch('os.unlink', side_effect=unlink):
            return call()

    def assert_pair(self, result):
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'storage_limit')
        self.assertIn('Disk full', result['error']['message'])
        self.assertTrue(any('Cleanup' in note and 'Storage I/O' in note for note in result['error']['notes']), result)
        transport_response(result)

    def test_review25_outgoing_wire_enospc_then_unlink_eio_preserves_primary_and_note(self):
        approval = self.approval('send', self.compose())
        put = self.mail.wires.put
        def paired(*args, **kwargs):
            return self.paired_write(lambda: put(*args, **kwargs))
        with patch.object(self.mail.wires, 'put', side_effect=paired), \
             patch.object(self.mail, 'send_smtp', side_effect=AssertionError('DATA forbidden after wire failure')):
            self.assert_pair(self.call('send', approval))

    def test_review25_password_enospc_then_unlink_eio_preserves_primary_and_note(self):
        arguments = {'id': 'new', 'addresses': ['owner@mail.invalid'], 'username': 'synthetic',
            'imap_host': 'mail.invalid', 'imap_port': 993, 'smtp_host': 'mail.invalid',
            'smtp_port': 465, 'smtp_tls': 'implicit'}
        store_password = self.mail.transport.store_password
        def paired(*args, **kwargs):
            return self.paired_write(lambda: store_password(*args, **kwargs))
        with patch.object(self.mail.transport, 'store_password', side_effect=paired):
            self.assert_pair(self.engine.request({'v': 1, 'method': 'mail_account_add',
                'arguments': arguments, 'password': 'Synthetic test credential'}, admin=True))
        self.assertIsNone(self.engine.store.get('mail:account:new'))


class Pending25(unittest.TestCase):
    setUp = filing11.FilingNotices11.setUp

    def test_review25_pending_read_failure_keeps_storage_error_snapshot_and_new_warning(self):
        import sqlite3
        old = {'id': 'old', 'app': 'mail', 'state': 'partial', 'ack': False,
               'untrusted_content': {'reason': 'Earlier filing needs inspection.'}}
        self.engine.store.write({'notice:old': old}, 'fixture', 'Synthetic warning')
        self.engine.pending()
        fresh = {**old, 'id': 'fresh', 'untrusted_content': {'reason': 'Nothing was deleted. Check Target.'}}
        self.engine.store.defer_notice('fresh', {'notice:fresh': fresh}, 'mail_move', 'Synthetic deferred warning')
        failure = sqlite3.OperationalError('Synthetic full disk during rollback')
        failure.sqlite_errorcode = sqlite3.SQLITE_FULL
        items = self.engine.store.iter_items
        def unreadable(prefix):
            if prefix == 'op:':
                raise failure
            return items(prefix)
        with patch.object(self.engine.store, 'iter_items', side_effect=unreadable), \
             patch.object(self.engine.store, 'iter_operations', side_effect=failure) as failed_operations, \
             patch.object(self.engine.store, 'flush_notices', side_effect=failure):
            result = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_pending', 'arguments': {}})
        self.assertGreater(failed_operations.call_count, 0)
        self.assertFalse(result['ok'], result)
        self.assertIn('Disk full', result['error']['message'])
        self.assertIn('snapshot', result['pending']['unavailable'])
        self.assertEqual({n['operation_id'] for n in result['data']['notices']}, {'old', 'fresh'})
        self.assertEqual(result['observations']['evidence']['fresh']['filing_warning']['reason'], fresh['untrusted_content']['reason'])

    def test_review25_caller_proxy_also_checks_final_serialized_response(self):
        from types import SimpleNamespace
        from aresos_control.proxy import Proxy
        proxy = Proxy('mail', {'act_socket': 'unused'})
        proxy.client = SimpleNamespace(call=lambda *args: {'ok': False, 'pending': {}, 'error': {'message': 'x' * WIRE_LIMIT}})
        from aresos_control.results import bound_result
        from aresos_control.protocol import send
        raw = proxy.client.call()
        class Frame:
            def sendall(self, wire):
                pass
        with self.assertRaises(Refused):
            send(Frame(), raw)
        proxy.client.call = lambda *args: bound_result(raw)
        result = proxy.call('accounts', {})
        self.assertFalse(result['ok'])
        self.assertLessEqual(len(canonical(result)), RESULT_LIMIT)
