import copy
import io
import json
import socket
from contextlib import ExitStack, contextmanager, redirect_stdout
from itertools import permutations
from unittest.mock import patch

from aresos_control.common import ASK_LIMIT, QUESTION_LIMIT, Refused, approval_input, canonical, display_json, visible
from aresos_control.definitions import APPROVAL
from aresos_control.protocol import Client, send, receive
from aresos_control.proxy import Proxy
from aresos_control.cli import main
from support import EngineCase


class ApprovalQuestions(EngineCase):
    def test_round13_wrong_orders_and_extra_or_missing_keys_stop_before_submission(self):
        ref = self.data('testapp_list')['items'][0]['reference']
        for verb, approval in (('send', self.reserve()), ('delete', self.data('testapp_prepare_delete', {'references': [ref]})['approval'])):
            before = self.engine.store.get('testapp')
            wrong = [{k: approval[k] for k in order} for order in permutations(approval) if list(order) != list(approval)]
            wrong += [{**approval, 'extra': True}, {}, *[{k: v for k, v in approval.items() if k != missing} for missing in approval]]
            adapter = self.engine.adapters['testapp']
            proxy = Proxy('testapp', {'act_socket': 'unused'})
            for altered in wrong:
                with self.subTest(verb=verb, keys=list(altered)), ExitStack() as stack:
                    guards = [stack.enter_context(patch.object(obj, name, wraps=getattr(obj, name))) for obj, name in
                              ((self.engine, 'submit'), (self.engine, 'stage'), (adapter, 'revalidate'),
                               (adapter, 'has_submission_evidence'), (adapter, 'execute'))]
                    result = self.call('testapp_' + verb, altered)
                    self.assertEqual(result['error']['code'], 'stale_approval', result)
                    with patch.object(proxy.client, 'call', side_effect=lambda name, args: self.call(name, args)) as outbound:
                        result = proxy.call(verb, altered)
                    self.assertEqual(result['error']['code'], 'stale_approval', result)
                    self.assertEqual([c.args[0] for c in outbound.call_args_list], ['control_pending'])
                    for guard in guards:
                        guard.assert_not_called()
                self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
                self.assertEqual(self.engine.store.get('testapp'), before)
                self.assertEqual(self.engine.receiver.evidence(approval['operation_id'])['arrivals'], [])
            first = self.data('testapp_' + verb, approval)
            self.assertEqual(first['operation']['state'], 'done')
            self.assertEqual(self.data('testapp_' + verb, approval), first)

    def test_round13_client_serializes_caller_order_without_result_presentation(self):
        approval = self.reserve()
        altered = {k: approval[k] for k in ('description', 'operation_id', 'question')}
        caller, service = socket.socketpair()
        @contextmanager
        def connection(request=None):
            yield caller
        client = Client('unused')
        with caller, service, patch.object(client, 'connection', connection), patch('aresos_control.protocol.receive', return_value={'ok': True}):
            client.call('testapp_send', altered)
            payload = json.loads(service.recv(65536))
        self.assertEqual(list(payload['arguments']), list(altered))

    def test_question_required_first_escaped_and_counts_toward_exact_limit(self):
        question = 'Send café \\ \x00\u202e?'
        template = approval_input('fixed-id', {'text': ''}, question)
        self.assertEqual(list(template), ['question', 'operation_id', 'description'])
        self.assertEqual(list(APPROVAL['properties']), list(template))
        self.assertEqual(APPROVAL['required'], list(template))
        self.assertEqual(template['question'], visible(question))
        room = ASK_LIMIT - len(canonical(template).encode())
        at_limit = approval_input('fixed-id', {'text': 'x' * room}, question)
        self.assertEqual(len(canonical(at_limit).encode()), ASK_LIMIT)
        with self.assertRaises(Refused) as error:
            approval_input('fixed-id', {'text': 'x' * (room + 1)}, question)
        self.assertEqual(error.exception.code, 'asking_input_too_large')
        self.assertEqual(len(at_limit['description']['text']), room)
        with self.assertRaises(Refused):
            approval_input('fixed-id', {}, 'x' * (QUESTION_LIMIT + 1))

    def test_testapp_changed_and_removed_question_never_send_or_delete(self):
        ref = self.data('testapp_list')['items'][0]['reference']
        for verb, approval in (('send', self.reserve()), ('delete', self.data('testapp_prepare_delete', {'references': [ref]})['approval'])):
            before = self.engine.store.get('testapp')
            for remove in (False, True):
                altered = copy.deepcopy(approval)
                if remove:
                    del altered['question']
                else:
                    altered['question'] = 'Do something different?'
                result = self.call('testapp_' + verb, altered)
                self.assertEqual(result['error']['code'], 'stale_approval', result)
                self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
                self.assertEqual(self.engine.receiver.evidence(approval['operation_id'])['arrivals'], [])
                self.assertEqual(self.engine.store.get('testapp'), before)
                proxy = Proxy('testapp', {'act_socket': 'unused'})
                with patch.object(proxy.client, 'call', side_effect=lambda name, args: self.call(name, args)):
                    self.assertEqual(proxy.call(verb, altered)['error']['code'], 'stale_approval')

    def test_question_first_after_restart_socket_cli_and_mcp_text_serialization(self):
        approval = self.reserve()
        self.restart()
        result = self.call('testapp_operation_status', {'operation_id': approval['operation_id']})
        saved = result['data']['operation']['approval']
        self.assertEqual(list(saved), ['question', 'operation_id', 'description'])
        self.assertEqual(saved, approval)
        self.assertEqual(list(json.loads(display_json(result))['data']['operation']['approval']), list(saved))
        caller, service = socket.socketpair()
        with caller, service:
            send(service, result)
            self.assertEqual(list(receive(caller)['data']['operation']['approval']), list(saved))
        output = io.StringIO()
        with patch('aresos_control.cli.Proxy.call', return_value=result), redirect_stdout(output):
            self.assertEqual(main({'act_socket': 'unused'}, ['testapp', 'operation_status', '--input', json.dumps({'operation_id': approval['operation_id']})]), 0)
        self.assertEqual(list(json.loads(output.getvalue())['data']['operation']['approval']), list(saved))

    def test_repair_question_is_stored_first_without_resubmission(self):
        self.configure('sent_copy')
        approval = self.reserve()
        self.data('testapp_send', approval)
        self.configure()
        arrivals = self.engine.receiver.evidence(approval['operation_id'])['arrivals']
        repair = self.data('testapp_operation_repair', {'operation_id': approval['operation_id'], 'stage': 'sent_copy'})['operation']
        self.assertEqual(list(repair['approval']), ['question', 'operation_id', 'description'])
        self.assertEqual(repair['approval']['question'], 'Repair this fixture local stage without sending again?')
        self.assertEqual(self.engine.receiver.evidence(approval['operation_id'])['arrivals'], arrivals)
