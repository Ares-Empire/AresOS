"""User-scope synthetic MCP app; the independent HTTP listener logs every call."""
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

sys.path.insert(0, '/opt/aresos-control')
from aresos_control.definitions import tools_for, instructions_for

app = sys.argv[1] if len(sys.argv) > 1 else 'testapp'
for line in sys.stdin:
    message = json.loads(line)
    if 'id' not in message:
        continue
    if message['method'] == 'initialize':
        result = {'protocolVersion': message['params']['protocolVersion'], 'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'boundary-' + app, 'version': '1'}, 'instructions': instructions_for(app)}
    elif message['method'] == 'tools/list':
        result = {'tools': tools_for(app)}
    elif message['method'] == 'tools/call':
        name = message['params']['name']
        assert app == 'testapp' and name in ('list', 'send'), 'Unexpected fixed test call'
        case = os.environ['ARESOS_BOUNDARY_CASE']
        request = Request('http://127.0.0.1:18080/precedence/' + name + '/' + case,
                          data=json.dumps(message['params']['arguments']).encode(), method='POST')
        with urlopen(request, timeout=5) as response:
            assert response.read() == b'OK'
        result = {'content': [{'type': 'text', 'text': 'FIXTURE_' + name.upper() + '_RAN'}], 'isError': False}
    else:
        result = {}
    print(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}), flush=True)
