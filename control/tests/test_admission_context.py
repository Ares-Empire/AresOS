"""Policy refusals must precede R2 context commits and remain inert on restart.

Only the policy file read is replaced here; protected filesystem admission is
exercised by test_boundary in the root-run Linux container.
"""
from contextlib import ExitStack
from dataclasses import replace
from unittest.mock import patch

from aresos_control.boundary import Boundary
from aresos_control.boundary_policy import asking_rules, managed_settings
from aresos_control.common import Refused
from aresos_control.definitions import BY_NAME
from aresos_control.recovery import unfinished
from support import EngineCase, message


class AdmissionContext(EngineCase):
    def snapshot(self):
        return (self.engine.store.items(''), list(self.engine.store.iter_audit()))

    def before_mutation(self, stack):
        adapter = self.engine.adapters['testapp']
        return [stack.enter_context(patch.object(target, name, wraps=getattr(target, name)))
                for target, name in ((self.engine.store, 'write'), (adapter, 'prepare'),
                                     (adapter, 'revalidate'), (adapter, 'submission_context'),
                                     (adapter, 'execute'))]

    def assert_reserved_without_context(self, approvals):
        for approval in approvals:
            op = self.engine.operation(approval['operation_id'])
            self.assertEqual(op['state'], 'reserved')
            self.assertEqual(op['approval'], approval)
            self.assertEqual(op['stages'], {})
            self.assertNotIn('context', op)
            self.assertIn('nothing submitted', op['reason'])
            self.assertEqual(self.engine.receiver.evidence(op['id'])['arrivals'], [])
        self.assertEqual(list(unfinished(self.engine.store)), [])

    def test_each_missing_or_misnamed_ask_refuses_reserve_and_submit_before_context(self):
        policy = managed_settings()
        with patch.object(Boundary, 'read', return_value=policy):
            reference = self.data('testapp_list')['items'][0]['reference']
            arguments = {'send': message(), 'delete': {'references': [reference]}}
            approvals = {verb: self.data('testapp_prepare_' + verb, args)['approval']
                         for verb, args in arguments.items()}
            before = self.snapshot()
            for rule in asking_rules():
                for replacement in (None, rule + '_wrong'):
                    policy['permissions']['ask'] = [other for other in asking_rules() if other != rule]
                    if replacement:
                        policy['permissions']['ask'].append(replacement)
                    with self.subTest(rule=rule, replacement=replacement), ExitStack() as stack:
                        guards = self.before_mutation(stack)
                        for verb in approvals:
                            for name, args in (('testapp_prepare_' + verb, arguments[verb]),
                                               ('testapp_' + verb, approvals[verb])):
                                result = self.call(name, args)
                                self.assertFalse(result['ok'], result)
                                self.assertEqual(result['error']['code'], 'boundary_not_installed', result)
                                self.assertIn(rule, result['error']['message'])
                        for guard in guards:
                            guard.assert_not_called()
                        self.assertEqual(self.snapshot(), before)
                        self.assert_reserved_without_context(approvals.values())
            # Recovery sees the same reservation even with the policy repaired.
            policy['permissions']['ask'] = asking_rules()
            self.restart()
            self.engine.boundary.require()
            self.assertEqual(self.snapshot(), before)
            self.assert_reserved_without_context(approvals.values())

    def test_missing_or_revoked_trusted_entry_refuses_before_context_and_restart(self):
        action = replace(BY_NAME['testapp_send'], trusted_send=True)
        with patch.object(Boundary, 'read', return_value=managed_settings()):
            approval = self.reserve()
            adapter = self.engine.adapters['testapp']
            entry_key = 'fixture:owner-trusted-recipients'
            recipients = {kind: self.engine.operation(approval['operation_id'])['payload'][kind]
                          for kind in ('to', 'cc', 'bcc')}
            self.engine.store.write({entry_key: recipients}, 'fixture_admin', 'Owner fixture entry')
            self.engine.store.write({entry_key: None}, 'fixture_admin', 'Owner revoked fixture entry')

            def current_entry(verb, operation):
                return self.engine.store.get(entry_key) == {kind: operation['payload'][kind]
                                                          for kind in ('to', 'cc', 'bcc')}

            before = self.snapshot()
            for check in (None, current_entry):
                with self.subTest(check='missing' if check is None else 'revoked'), ExitStack() as stack:
                    stack.enter_context(patch.object(adapter, 'require_trusted_send', check, create=True))
                    guards = self.before_mutation(stack)
                    with self.assertRaisesRegex(Refused, 'owner-only') as refused:
                        self.engine.submit(action, approval)
                    self.assertEqual(refused.exception.code, 'permission_denied')
                    for guard in guards:
                        guard.assert_not_called()
                    self.assertEqual(self.snapshot(), before)
                    self.assert_reserved_without_context([approval])
            self.restart()
            self.assertEqual(self.snapshot(), before)
            self.assert_reserved_without_context([approval])
