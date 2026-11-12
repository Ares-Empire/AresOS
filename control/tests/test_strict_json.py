import io
import json
import socket
import unittest
from contextlib import ExitStack, redirect_stdout, redirect_stderr
from unittest.mock import patch

from aresos_control.common import JSONInputError, strict_json_loads
from aresos_control import cli, daemon, hooks
from aresos_control.protocol import receive
from raw_json_test_support import duplicate_arguments, socket_request
from support import EngineCase


class StrictJSON(unittest.TestCase):
    def test_decoder_refuses_duplicate_decoded_keys_at_every_depth_and_nonfinite(self):
        for raw in ('{"a":1,"a":2}', '{"a":1,"\\u0061":2}', '{"a":[{"b":0,"b":1}]}',
                    'NaN', 'Infinity', '-Infinity', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(JSONInputError) as error:
                strict_json_loads(raw)
            self.assertEqual(error.exception.code, 'invalid_input')
        self.assertEqual(strict_json_loads('{"b": [1, true, null], "a": {"x": 2}}'),
                         {'b': [1, True, None], 'a': {'x': 2}})
        self.assertEqual(list(strict_json_loads('{"b":1,"a":2}')), ['b', 'a'])

    def test_config_and_hook_refuse_before_daemon_or_pending_call(self):
        for raw in ('{"owner_uid":1,"owner_uid":2}', '{"owner_uid":NaN}'):
            with patch('sys.argv', ['daemon', '--config', 'unused']), patch('builtins.open', return_value=io.StringIO(raw)), patch.object(daemon, 'Daemon') as constructor:
                with self.assertRaises(JSONInputError):
                    daemon.main()
                constructor.assert_not_called()
        for name in ('Stop', 'UserPromptSubmit'):
            for raw in ('{"hook_event_name":"' + name + '","hook_event_name":"' + name + '"}',
                        '{"hook_event_name":"' + name + '","nested":{"x":1,"x":2}}'):
                stdin = io.TextIOWrapper(io.BytesIO(raw.encode()))
                with patch('sys.stdin', stdin), patch.object(hooks, 'Client') as client, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    if name == 'Stop':
                        with self.assertRaises(SystemExit) as error:
                            hooks.main({}, name)
                        self.assertEqual(error.exception.code, 2)
                    else:
                        hooks.main({}, name)
                    client.assert_not_called()

    def test_cli_nonasking_and_admin_config_refuse_before_proxy(self):
        for words, raw in ((['testapp', 'list'], '{"cursor":null,"cursor":null}'),
                           (['admin', 'mail', 'account_add'], '{"id":"a","id":"b"}')):
            output = io.StringIO()
            with patch('sys.stdin.isatty', return_value=True), patch.object(cli, 'Proxy') as proxy, redirect_stdout(output):
                self.assertEqual(cli.main({}, [*words, '--input', raw]), 1)
            self.assertEqual(json.loads(output.getvalue())['error']['code'], 'invalid_input')
            proxy.assert_not_called()


class RawApprovalJSON(EngineCase):
    def test_raw_mcp_process_refuses_duplicates_before_service_then_executes_once(self):
        from concurrent.futures import ThreadPoolExecutor
        import os
        import sys
        from aresos_control.protocol import send
        from raw_json_test_support import RawMCP, mcp_request
        ref = self.data('testapp_list')['items'][0]['reference']
        approvals = [('send', self.reserve(to=['alpha'], bcc=[])),
                     ('delete', self.data('testapp_prepare_delete', {'references': [ref]})['approval'])]
        path = str(self.root / 'raw.sock')
        code = 'import json,sys; from aresos_control.proxy import main; main("testapp",json.loads(sys.argv[1]))'
        requests = []
        def conversation():
            with RawMCP([sys.executable, '-c', code, json.dumps({'act_socket': path})], env=os.environ.copy()) as client:
                for verb, approval in approvals:
                    before = len(requests)
                    for label, raw in duplicate_arguments(approval):
                        response = client.exchange(mcp_request(label, verb, raw, label == 'envelope'))
                        self.assertEqual(response['id'], label)
                        self.assertEqual(response['error']['data']['code'], 'stale_approval', response)
                        self.assertEqual(len(requests), before, 'Refused JSON reached service')
                    raw = json.dumps(approval)
                    result = client.exchange(mcp_request('correct', verb, raw))['result']['structuredContent']
                    self.assertTrue(result['ok'], result)
                    self.assertEqual(result['data']['operation']['state'], 'done')
                    self.assertEqual(client.exchange(mcp_request('replay', verb, raw))['result']['structuredContent']['data'], result['data'])
                for raw in ('{"cursor":null,"cursor":null}', '{"limit":NaN}', '{"limit":Infinity}', '{"limit":-Infinity}'):
                    before = len(requests)
                    response = client.exchange(mcp_request('nonasking', 'list', raw))
                    self.assertEqual(response['error']['data']['code'], 'invalid_input', response)
                    self.assertEqual(len(requests), before)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(path)
            listener.listen()
            listener.settimeout(0.1)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(conversation)
                while not future.done():
                    try:
                        connection, _ = listener.accept()
                    except socket.timeout:
                        continue
                    with connection:
                        payload = receive(connection)
                        requests.append(payload)
                        send(connection, self.engine.request(payload), result=True)
                future.result()
        for verb, approval in approvals:
            op = self.engine.operation(approval['operation_id'])
            self.assertEqual(op['state'], 'done')
            self.assertEqual(self.engine.receiver.evidence(op['id'])['arrivals'], ['alpha'] if verb == 'send' else [])
        self.assertNotIn(ref, [item['reference'] for item in self.data('testapp_list')['items']])

    def test_raw_testapp_socket_and_cli_refuse_before_any_operation_work(self):
        ref = self.data('testapp_list')['items'][0]['reference']
        for verb, approval in (('send', self.reserve()), ('delete', self.data('testapp_prepare_delete', {'references': [ref]})['approval'])):
            before = self.engine.store.get('testapp')
            adapter = self.engine.adapters['testapp']
            for label, raw in duplicate_arguments(approval):
                with self.subTest(verb=verb, duplicate=label), ExitStack() as stack:
                    guards = [stack.enter_context(patch.object(obj, name, wraps=getattr(obj, name))) for obj, name in (
                        (self.engine, 'request'), (self.engine, 'reserve'), (self.engine, 'submit'), (self.engine, 'stage'),
                        (adapter, 'revalidate'), (adapter, 'has_submission_evidence'), (adapter, 'execute'))]
                    caller, service = socket.socketpair()
                    with caller, service:
                        caller.sendall((socket_request('testapp_' + verb, raw, label == 'envelope') + '\n').encode())
                        with self.assertRaises(JSONInputError) as error:
                            self.engine.request(receive(service))
                        self.assertEqual(error.exception.code, 'stale_approval')
                    output = io.StringIO()
                    with patch.object(cli, 'Proxy') as proxy, redirect_stdout(output):
                        self.assertEqual(cli.main({}, ['testapp', verb, '--input', raw]), 1)
                    self.assertEqual(json.loads(output.getvalue())['error']['code'], 'stale_approval')
                    proxy.assert_not_called()
                    for guard in guards:
                        guard.assert_not_called()
                op = self.engine.operation(approval['operation_id'])
                self.assertEqual((op['state'], op['stages']), ('reserved', {}))
                self.assertEqual(self.engine.store.get('testapp'), before)
                self.assertEqual(self.engine.receiver.evidence(approval['operation_id'])['arrivals'], [])
