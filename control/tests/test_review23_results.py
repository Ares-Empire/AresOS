"""Shared response validation covers failures as well as successful data helpers."""
from unittest.mock import patch

from jsonschema import ValidationError
from jsonschema import Draft202012Validator

from aresos_control.definitions import BY_NAME
from support import EngineCase


class ResponseSchemas23(EngineCase):
    def test_review23_repaired_responses_allow_observed_evidence(self):
        approval = self.reserve()
        op = self.engine.public_operation(self.engine.operation(approval['operation_id']))
        response = {'ok': True, 'data': {'operation': op, 'original': op, 'evidence': {'sent': []}}, 'pending': {}}
        Draft202012Validator(BY_NAME['mail_operation_repair'].tool()['outputSchema']).validate(response)

    def test_review23_storage_error_envelope_advertises_observations(self):
        response = {'ok': False, 'error': {'code': 'storage_limit', 'message': 'Disk full'},
                    'observations': {'stages': {'synthetic': {'smtp_data': 'accepted:250'}},
                                     'evidence': {'synthetic': {'sent': []}}}, 'pending': {}}
        Draft202012Validator(BY_NAME['mail_send'].tool()['outputSchema']).validate(response)

    def test_review23_shared_harness_rejects_success_and_error_schema_drift(self):
        for ok in (True, False):
            with self.subTest(ok=ok), patch.object(self.engine, '_admitted_request', return_value={
                    'ok': ok, 'data': {'unexpected': 'Synthetic schema drift'}, 'pending': {}}):
                with self.assertRaises(ValidationError):
                    self.call('testapp_prepare_send')

    def test_review23_shared_harness_checks_direct_requests_and_mail_evidence(self):
        response = {'ok': False, 'data': {'operation': {}, 'original': {}, 'evidence': {}}, 'pending': {}}
        with patch.object(self.engine, '_admitted_request', return_value=response):
            with self.assertRaises(ValidationError):
                self.engine.request({'v': 1, 'method': 'call', 'action': 'mail_operation_repair', 'arguments': {}})

    def test_first_storage_error_notes_and_restart_advice_survive_bounding(self):
        import errno
        import json
        from aresos_control.results import Observations, RESTART_ADVICE
        from aresos_control.common import Refused
        store = self.engine.store
        facts = Observations()
        first = Refused('storage_error', 'Synthetic original I/O refusal. ' + 'detail ' * 10000)
        first.add_note('Cleanup journal truncation failed: Synthetic cleanup error.')
        facts.storage(first)
        facts.storage(OSError(errno.ENOSPC, 'Synthetic later error'))
        facts.observe('synthetic', {'detail': 'Synthetic observation ' * 10000})
        store.write_failed = True
        result = facts.finish({'ok': False, 'error': {'code': 'journal_incomplete', 'message': 'Later refusal'}, 'pending': {}}, store)
        self.assertEqual(result['error']['code'], 'storage_error')
        self.assertTrue(result['error']['message'].startswith('Synthetic original I/O refusal.'))
        self.assertEqual(result['error']['message'].count(RESTART_ADVICE), 1)
        saved = json.loads(store.observation_snapshot['json'])
        self.assertEqual(saved['error']['notes'], first.__notes__)
        self.assertEqual(result['error']['message'], str(first) + ' ' + RESTART_ADVICE)
        from aresos_control.results import bound_result
        oversized = bound_result({'ok': False, 'error': {'code': 'storage_error',
            'message': 'Synthetic original. ' * 10000 + RESTART_ADVICE}, 'pending': {}}, store)
        self.assertEqual(oversized['error']['message'].count(RESTART_ADVICE), 1)
        # A successful read keeps its exact reply even on the latched store.
        self.assertEqual(Observations().finish({'ok': True, 'data': {}, 'pending': {}}, store),
                         {'ok': True, 'data': {}, 'pending': {}})
