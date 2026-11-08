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
        fixture = filing11.MemoryIMAP(1, b'<' + b'x' * 20000 + b'@mail.invalid>')
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

    def test_review25_central_harness_rejects_transport_oversize_on_success_and_failure(self):
        for ok in (False, True):
            with self.subTest(ok=ok), patch.object(self.engine, '_admitted_request', return_value={
                    'ok': ok, 'pending': {}, 'data': {'text': 'x' * WIRE_LIMIT}}):
                with self.assertRaises(Refused):
                    self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_accounts', 'arguments': {}})
