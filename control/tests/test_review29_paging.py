"""Every warning catalogue and detail continuation shares cursor invalidation."""
from unittest.mock import patch

from aresos_control.common import canonical
from aresos_control.definitions import BY_NAME
from aresos_control.mail.filing import notice_page, location_page
from aresos_control.results import bound_result, observation_page
from support import EngineCase


class Paging29(EngineCase):
    def seed_notices(self):
        changes = {'notice:' + str(i): {'id': str(i), 'app': 'mail', 'state': 'partial',
            'ack': False, 'created_at': i, 'untrusted_content': {'reason': 'Synthetic warning ' + str(i)}}
                   for i in range(4)}
        self.engine.store.write(changes, 'fixture', 'Synthetic warning catalogue')

    def test_review29_shared_helper_binds_creation_order_and_contents_and_restarts_nonempty(self):
        from aresos_control.paging import ordered_page
        rows = [((i, str(i)), {'id': str(i)}) for i in range(4)]
        for newest in (False, True):
            with self.subTest(newest=newest):
                first = ordered_page(lambda: iter(rows), {'limit': 3}, 'synthetic', newest=newest)
                second = ordered_page(lambda: iter(reversed(rows)), {'cursor': first['cursor']}, 'synthetic', newest=newest)
                self.assertEqual(len(second['items']), 1)
                self.assertEqual({v['id'] for v in first['items'] + second['items']}, {'0', '1', '2', '3'})
                moved = [((10 + key[0], key[1]), value) for key, value in rows]
                changed = ordered_page(lambda: iter(moved), {'cursor': first['cursor']}, 'synthetic', newest=newest)
                self.assertIn('restarted', changed['page_changed'])
                self.assertTrue(changed['items'])
                self.assertEqual(changed['total'], 4)

    def test_review29_warning_catalogue_and_all_first_three_envelopes_share_order_and_restart(self):
        self.seed_notices()
        first = notice_page(self.engine.store)
        self.assertEqual([n['operation_id'] for n in first['items']], ['3', '2', '1'])
        for response in (self.data('control_pending'), self.data('control_log'),
                         self.call('testapp_list')['pending']):
            self.assertEqual(response['notices'], first['items'])
            self.assertEqual(response['notices_more']['count'], 1)
        second = notice_page(self.engine.store, {'cursor': first['cursor']})
        self.assertEqual([n['operation_id'] for n in second['items']], ['0'])
        self.data('mail_notice_ack', {'operation_id': '3'})
        changed = self.data('mail_filing_notices', {'cursor': first['cursor']})
        self.assertIn('restarted', changed['page_changed'])
        self.assertEqual([n['operation_id'] for n in changed['items']], ['2', '1', '0'])

    def test_review29_pending_summaries_follow_creation_then_id_and_changed_set_restarts(self):
        ids = sorted([self.reserve()['operation_id'] for _ in range(4)], reverse=True)
        with self.engine.store.db as db:
            for index, op_id in enumerate(ids):
                db.execute('UPDATE retained SET created=? WHERE k=?', (index + 100, 'op:' + op_id))
        first = self.data('control_pending', {'limit': 3})
        self.assertEqual([op['operation_id'] for op in first['items']], ids[:3])
        second = self.data('control_pending', {'cursor': first['cursor']})
        self.assertEqual([op['operation_id'] for op in second['items']], ids[3:])
        self.data('testapp_operation_cancel', {'operation_id': ids[0]})
        changed = self.data('control_pending', {'cursor': first['cursor']})
        self.assertIn('restarted', changed['page_changed'])
        self.assertTrue(changed['items'])
        self.assertEqual(changed['items'][0]['state'], 'failed')

    def test_review29_audit_pages_reach_every_entry_and_changed_audit_restarts(self):
        for i in range(4):
            self.engine.store.write({}, 'fixture', 'Synthetic audit ' + str(i))
        first = self.data('control_log', {'limit': 3})
        second = self.data('control_log', {'cursor': first['cursor']})
        all_ids = [event['seq'] for event in first['items'] + second['items']]
        self.assertEqual(len(set(all_ids)), first['total'])
        self.engine.store.write({}, 'fixture', 'Synthetic audit change')
        changed = self.data('control_log', {'cursor': first['cursor']})
        self.assertIn('restarted', changed['page_changed'])
        self.assertEqual(changed['items'][0]['seq'], first['items'][0]['seq'])

    def test_review29_observation_fragments_keep_frozen_order_and_new_snapshot_restarts(self):
        result = {'ok': False, 'pending': {}, 'observations': {'stages': {}, 'evidence': {
            'synthetic': {'owner_warning': 'Synthetic warning', 'text': 'x' * 60000}}}}
        bounded = bound_result(result, self.engine.store)
        cursor = bounded['observations']['cursor']
        page = observation_page(self.engine.store, cursor)
        self.assertEqual(page['fragments'][0]['offset'], 6000)
        self.assertEqual(page['warnings'], bounded['observations']['warnings'])
        bound_result(result, self.engine.store)
        restarted = self.data('control_observations', {'cursor': cursor})
        self.assertIn('restarted', restarted['page_changed'])
        self.assertEqual(restarted['fragments'][0]['offset'], 0)
        self.assertTrue(restarted['fragments'][0]['json'])

    def test_review29_location_details_changed_under_cursor_restart_instead_of_skipping(self):
        prefix = 'mail:filing-locations:synthetic:'
        self.engine.store.write({prefix + 'meta': {'pages': 2, 'total_messages': 2},
            prefix + '0': {'locations': [{'id': 'one'}]}, prefix + '1': {'locations': [{'id': 'two'}]}},
            'fixture', 'Synthetic location pages')
        first = location_page(self.engine.store, {'filing_id': 'synthetic'})
        self.engine.store.write({prefix + '0': {'locations': [{'id': 'changed'}]}}, 'fixture', 'Synthetic evidence change')
        changed = self.data('mail_filing_locations', {'filing_id': 'synthetic', 'cursor': first['cursor']})
        self.assertIn('restarted', changed['page_changed'])
        self.assertEqual(changed['untrusted_content']['locations'], [{'id': 'changed'}])

    def test_stage3_restore_result_and_description_confirm_independent_reconciliation(self):
        sentence = ('Free-change checks, warnings and acknowledgements are re-derived from the independent owner record. '
                    'No remote work is replayed.')
        old = {'generation': '0' * 32, 'unknown': []}
        with patch.object(self.engine.store, 'confirm_restore', return_value=old):
            result = self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        self.assertEqual(result, old | {'warning': sentence})
        self.assertIn(sentence, BY_NAME['control_restore_confirm'].description)
        self.assertLess(len(canonical(result).encode()), 49152)
