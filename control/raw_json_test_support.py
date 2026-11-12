"""Raw-wire regression helpers, shared by the base and Mail suites only."""
import json
import select
import subprocess


def duplicate_arguments(approval):
    raw = json.dumps(approval, separators=(',', ':'))
    for label, key, first in (
            ('question', '"question"', '"Do nothing?"'),
            ('escaped_question', '"\\u0071uestion"', '"Do nothing?"'),
            ('operation_id', '"operation_id"', '"wrong-id"'),
            ('description', '"description"', '{}')):
        # The original field's position and final value survive ordinary loads.
        marker = '"' + ('question' if label == 'escaped_question' else label) + '":'
        yield label, raw.replace(marker, key + ':' + first + ',' + marker, 1)
    description = json.dumps(approval['description'], separators=(',', ':'))
    key = next(iter(approval['description']))
    marker = json.dumps(key) + ':'
    nested = description.replace(marker, marker + 'null,' + marker, 1)
    yield 'nested_description', raw.replace('"description":' + description, '"description":' + nested, 1)
    # The CLI has no outer transport envelope: its approval is the envelope.
    yield 'envelope', raw.replace('"question":', '"question":"Do nothing?","question":', 1)


def socket_request(action, raw, envelope=False):
    return ('{"v":1,"method":"call","action":' +
            ('"testapp_list","action":' if envelope else '') + json.dumps(action) + ',"arguments":' + raw + '}')


def mcp_request(request_id, verb, raw, envelope=False):
    params = '{"name":' + json.dumps(verb) + ',"arguments":' + raw + '}'
    return ('{"jsonrpc":"2.0","id":' + json.dumps(request_id) + ',"method":"tools/call","params":' +
            ('{},"params":' if envelope else '') + params + '}')


class RawMCP:
    def __init__(self, command, **kwargs):
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, **kwargs)

    def exchange(self, raw):
        self.process.stdin.write(raw + '\n')
        self.process.stdin.flush()
        if not select.select([self.process.stdout], [], [], 20)[0]:
            raise AssertionError('Raw MCP request hung without a JSON-RPC reply')
        line = self.process.stdout.readline()
        if not line:
            raise AssertionError('Raw MCP proxy exited: ' + self.process.stderr.read())
        return json.loads(line)

    def __enter__(self):
        from mcp_types.version import LATEST_HANDSHAKE_VERSION
        response = self.exchange(json.dumps({'jsonrpc': '2.0', 'id': 'init', 'method': 'initialize', 'params': {
            'protocolVersion': LATEST_HANDSHAKE_VERSION, 'capabilities': {}, 'clientInfo': {'name': 'raw-regression', 'version': '1'}}}))
        if 'result' not in response:
            raise AssertionError(response)
        self.process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.process.stdin.flush()
        return self

    def __exit__(self, *args):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        stderr = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        if not args[0] and self.process.returncode:
            raise AssertionError(stderr)
