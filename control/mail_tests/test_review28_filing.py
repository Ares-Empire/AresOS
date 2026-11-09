"""Round 28: missing roles cannot suppress independent filing evidence."""
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
from test_review23_sweep import Scenario


class Filing28(unittest.TestCase):
    def test_review28_interrupted_move_reports_trash_and_locations_with_only_drafts_unresolved(self):
        self.available_evidence('filing_move')

    def test_review28_interrupted_copy_reports_trash_and_locations_with_only_drafts_unresolved(self):
        self.available_evidence('filing_copy')

    def test_review28_interrupted_rename_reports_trash_with_only_drafts_unresolved(self):
        self.available_evidence('filing_rename')

    def available_evidence(self, flow):
        scenario = Scenario(flow)
        try:
            fixture = scenario.fixture
            write = fixture.engine.store.write
            def refuse(*args, **kwargs):
                if scenario.remote:
                    raise Refused('storage_limit', 'Synthetic post-command result refusal')
                return write(*args, **kwargs)
            with patch.object(fixture.engine.store, 'write', side_effect=refuse):
                scenario.call()
            prefix = 'mail:rename:' if flow.endswith('rename') else 'mail:filing:'
            key, source = fixture.engine.store.items(prefix)[0]
            target = source['target']
            self.assertEqual(fixture.imap.roles[target], ['\\Trash'])
            fixture.imap.roles['Drafts'] = []
            remote = scenario.remote.copy()
            fixture.restart()
            page = fixture.data('filing_notices', {})
            own = next(n for n in page['items'] if n['operation_id'] == source['id'])
            content = own['untrusted_content']
            self.assertIn('Trash', content['reason'])
            self.assertEqual(content['unresolved_roles'], ['drafts'])
            self.assertIn('Roles not yet checked: Drafts.', content['reason'])
            self.assertIn(target, content['reason'])
            self.assertEqual(fixture.engine.store.get(key)['state'], 'started')
            if not flow.endswith('rename'):
                locations = fixture.data('filing_locations', {'filing_id': source['id']})
                observed = locations['untrusted_content']['locations']
                self.assertTrue(all(item['scan_complete'] for item in observed))
                self.assertIn(target, {ref['folder'] for item in observed for ref in item['observed_locations']})
            # Acknowledging the warning cannot certify the missing check.
            fixture.data('notice_ack', {'operation_id': source['id']})
            self.assertTrue(fixture.engine.store.get(key)['check_open'])
            fixture.imap.roles['Drafts'] = ['\\Drafts']
            fixture.data('filing_notices', {})
            self.assertEqual(fixture.engine.store.get(key)['state'], 'partial')
            self.assertFalse(fixture.engine.store.get(key).get('check_open'))
            self.assertEqual(scenario.remote, remote)
        finally:
            scenario.close()

    def test_review28_incomplete_location_scan_preserves_observations_and_only_unavailable_parts_open(self):
        scenario = Scenario('filing_move')
        try:
            fixture = scenario.fixture
            write = fixture.engine.store.write
            def refuse(*args, **kwargs):
                if scenario.remote:
                    raise Refused('storage_limit', 'Synthetic post-command result refusal')
                return write(*args, **kwargs)
            with patch.object(fixture.engine.store, 'write', side_effect=refuse):
                scenario.call()
            key, source = fixture.engine.store.items('mail:filing:')[0]
            fixture.restart()
            from aresos_control.mail.filing import locations
            observed = locations(fixture.mail, fixture.mail.account('box', ready=False), source['records'])
            for item in observed:
                item['scan_complete'] = False
            with patch('aresos_control.mail.filing.locations', return_value=observed):
                page = fixture.data('filing_notices', {})
            content = next(n['untrusted_content'] for n in page['items'] if n['operation_id'] == source['id'])
            self.assertIn('Trash', content['reason'])
            self.assertIn('Locations are not yet checked completely', content['reason'])
            self.assertNotIn('unresolved_roles', content)
            pages = fixture.data('filing_locations', {'filing_id': source['id']})
            self.assertEqual(pages['untrusted_content']['locations'], observed)
            self.assertTrue(fixture.engine.store.get(key)['check_open'])
        finally:
            scenario.close()
