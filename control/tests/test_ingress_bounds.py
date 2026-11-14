"""Raw decoder limits at socket, CLI, MCP stdio and hook ingress."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import select
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from aresos_control import cli, hooks
from aresos_control.common import JSONInputError, JSON_INTEGER_LIMIT, WIRE_LIMIT, Refused, strict_json_loads
from aresos_control.protocol import receive
from raw_json_test_support import RawMCP


def raw_cases(prefix, suffix):
    for name, bad in [('overflow', b'1e400'), ('integer', b'9223372036854775808'),
                      ('constant', b'NaN'), ('depth', b'[' * 1200 + b'0' + b']' * 1200),
                      ('escaped_surrogate', b'"\\ud800"'), ('utf8_surrogate', b'"\xed\xa0\x80"'),
                      ('surrogateescape', b'"\xff"')]:
        yield name, prefix + bad + suffix
    yield 'bom', b'\xef\xbb\xbf' + prefix + b'0' + suffix
    yield 'bytes', prefix + b'"' + b'x' * WIRE_LIMIT + b'"' + suffix


class IngressBounds(unittest.TestCase):
    def test_strict_and_error_classification_decoders_share_all_bounds(self):
        for name, raw in raw_cases(b'{"value":', b'}'):
            with self.subTest(case=name), self.assertRaises(JSONInputError) as error:
                strict_json_loads(raw)
            self.assertIsNone(error.exception.pairs)
        self.assertEqual(strict_json_loads(str(JSON_INTEGER_LIMIT)), JSON_INTEGER_LIMIT)
        self.assertEqual(strict_json_loads(str(-JSON_INTEGER_LIMIT)), -JSON_INTEGER_LIMIT)
        self.assertEqual(strict_json_loads('"\\ud83d\\ude00"'), '\U0001f600')
        self.assertEqual(strict_json_loads('"' + '[{' * 1200 + '"'), '[{' * 1200)
        self.assertEqual(strict_json_loads('[' * 63 + '0' + ']' * 63), strict_json_loads('[' * 63 + '0' + ']' * 63))

    def test_socket_raw_bounds_refuse_before_engine_dispatch(self):
        for name, raw in raw_cases(b'{"v":1,"method":"saved","app":"mail","outcome":', b'}'):
            with self.subTest(case=name):
                caller, service = socket.socketpair()
                def write():
                    with caller:
                        try:
                            caller.sendall(raw + b'\n')
                        except BrokenPipeError:
                            pass
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(write)
                    with service, patch('aresos_control.engine.Engine.request') as dispatch:
                        with self.assertRaises(Refused) as error:
                            receive(service)
                        self.assertEqual(error.exception.code, 'invalid_input')
                        dispatch.assert_not_called()
                    future.result()

    def test_cli_raw_bounds_refuse_before_proxy_or_admin_password_prompt(self):
        for name, raw in raw_cases(b'{"value":', b'}'):
            for words in (['testapp', 'prepare_send'], ['admin', 'mail', 'account_add']):
                with self.subTest(case=name, words=words), patch.object(cli, 'Proxy') as proxy, \
                        patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass') as password, redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main({}, words + ['--input', raw.decode('utf-8', errors='surrogateescape')]), 1)
                    proxy.assert_not_called()
                    password.assert_not_called()

    def test_hook_raw_bounds_refuse_before_pending_read(self):
        for event in ('Stop', 'UserPromptSubmit'):
            for name, raw in raw_cases(b'{"hook_event_name":' + json.dumps(event).encode() + b',"prompt":', b'}'):
                with self.subTest(case=name, event=event), patch('sys.stdin', io.TextIOWrapper(io.BytesIO(raw))), \
                        patch.object(hooks, 'Client') as client, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    if event == 'Stop':
                        with self.assertRaises(SystemExit) as error:
                            hooks.main({}, event)
                        self.assertEqual(error.exception.code, 2)
                    else:
                        hooks.main({}, event)
                    client.assert_not_called()

    def test_hook_explicit_payload_schema_refuses_wrong_types(self):
        for event in ({'hook_event_name': 'Stop', 'stop_hook_active': 1},
                      {'hook_event_name': 'Stop', 'stop_hook_active': 'true', 'prompt_id': 'p'},
                      {'hook_event_name': 7, 'stop_hook_active': False},
                      {'hook_event_name': 'SessionStart'},
                      {'hook_event_name': 'UserPromptSubmit', 'stop_hook_active': False},
                      {'stop_hook_active': False, 'extra': 'field'}):
            with self.subTest(event=event), patch('sys.stdin', io.TextIOWrapper(io.BytesIO(json.dumps(event).encode()))), \
                    patch.object(hooks, 'Client') as client, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    hooks.main({}, 'Stop')
                self.assertEqual(error.exception.code, 2)
                client.assert_not_called()

    def test_hook_accepts_and_ignores_fields_it_does_not_read(self):
        # Claude Code 2.1.319 sends `prompt_id` and more than the documented fields; a closed list broke every turn.
        # Fields it doesn't read may change type too (a later version sending null must not break every turn).
        extra = {'prompt_id': 'prompt-marker-7', 'unknown_later_field': {'nested': [1, None]}, 'agent_id': 'a',
                 'session_id': None, 'transcript_path': 7}
        pending = {'total': 1, 'operations': [{'operation_id': 'op-1', 'state': 'held'}]}
        for name in ('Stop', 'UserPromptSubmit'):
            event = {'hook_event_name': name, 'cwd': '/unused', 'permission_mode': 'default', **extra,
                     **({'stop_hook_active': False, 'last_assistant_message': ['x']} if name == 'Stop' else {'prompt': None})}
            stdout = io.StringIO()
            with self.subTest(event=name), patch('sys.stdin', io.TextIOWrapper(io.BytesIO(json.dumps(event).encode()))), \
                    patch.object(hooks, 'Client') as client, redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                client.return_value.call.return_value = {'ok': True, 'data': pending}
                hooks.main({'act_socket': '/unused'}, name)
                client.return_value.call.assert_called_once_with('control_pending', {})
                result = json.loads(stdout.getvalue())
                if name == 'Stop':
                    self.assertEqual(result['decision'], 'block')
                    self.assertIn('op-1', result['reason'])
                else:
                    self.assertIn('op-1', result['hookSpecificOutput']['additionalContext'])
                self.assertNotIn('prompt-marker-7', stdout.getvalue())
                self.assertNotIn('unknown_later_field', stdout.getvalue())

    def test_stop_failure_blocks_once_and_honours_the_continuation_guard(self):
        for active, broken in ((False, 'service'), (True, 'service'), (False, 'input'), (True, 'input'), ('yes', 'input')):
            event = {'hook_event_name': 'Stop', 'stop_hook_active': active, 'prompt_id': 'p'}
            if broken == 'input':
                event['hook_event_name'] = 'UserPromptSubmit'  # valid fields, but not the launcher's event
            stderr = io.StringIO()
            with self.subTest(active=active, broken=broken), \
                    patch('sys.stdin', io.TextIOWrapper(io.BytesIO(json.dumps(event).encode()))), \
                    patch.object(hooks, 'Client') as client, redirect_stdout(io.StringIO()) as stdout, redirect_stderr(stderr):
                client.return_value.call.return_value = {'unexpected': 'reply'}
                if active is True:
                    hooks.main({'act_socket': '/unused'}, 'Stop')
                    self.assertEqual((stdout.getvalue(), stderr.getvalue()), ('', ''))
                else:
                    with self.assertRaises(SystemExit) as error:
                        hooks.main({'act_socket': '/unused'}, 'Stop')
                    self.assertEqual(error.exception.code, 2)
                    self.assertIn('AresOS hook failed', stderr.getvalue())
                if broken == 'input':
                    client.assert_not_called()

    def test_real_mcp_binary_stdio_bounds_refuse_without_dispatch_and_stream_recovers(self):
        from aresos_control.definitions import tools_for
        work = Path(__file__).resolve().parents[2] / '.work'
        with tempfile.TemporaryDirectory(dir=work) as directory:
            marker = Path(directory) / 'called'
            code = ('import sys; from pathlib import Path; from aresos_control.proxy import Proxy,main; '
                    'from aresos_control.definitions import tools_for; '
                    'Proxy.tools=lambda self: tools_for("testapp"); '
                    'Proxy.call=lambda *args: Path(sys.argv[1]).write_text("CALLED"); main("testapp",{"act_socket":"unused"})')
            with RawMCP([sys.executable, '-c', code, str(marker)], env=os.environ.copy()) as client:
                prefix = b'{"jsonrpc":"2.0","id":"bounds","method":"tools/call","params":{"name":"prepare_send","arguments":{"value":'
                for name, raw in raw_cases(prefix, b'}}}'):
                    with self.subTest(case=name):
                        client.process.stdin.buffer.write(raw + b'\n')
                        client.process.stdin.buffer.flush()
                        self.assertTrue(select.select([client.process.stdout], [], [], 20)[0], 'No MCP refusal')
                        response = json.loads(client.process.stdout.readline())
                        self.assertEqual(response['error']['data']['code'], 'invalid_input', response)
                        self.assertFalse(marker.exists())
                response = client.exchange('{"jsonrpc":"2.0","id":"recovered","method":"tools/list","params":{}}')
                self.assertIn('tools', response['result'])
                for raw in ('{"jsonrpc":"2.0","id":"shape","method":"tools/call","params":{"name":"list","arguments":[]}}',
                            '{"jsonrpc":"2.0","id":"shape","method":"tools/list","extra":true}',
                            '{"jsonrpc":"2.0","id":"shape","method":"tools/call","params":{"name":"list","extra":true}}'):
                    response = client.exchange(raw)
                    self.assertEqual(response['error']['data']['code'], 'invalid_input', response)
                self.assertFalse(marker.exists())
