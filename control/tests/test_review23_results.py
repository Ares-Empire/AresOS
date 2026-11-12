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
