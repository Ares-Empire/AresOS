"""Synthetic stdio MCP fixture. Never contacts the tool service or a model."""
import json
from pathlib import Path
import sys

Path('/home/assistant/work/mcp-started').write_text('unmanaged process started\n')
for line in sys.stdin:
    message = json.loads(line)
    if 'id' not in message:
        continue
    if message['method'] == 'initialize':
        result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'boundary-fixture', 'version': '1'}}
    elif message['method'] == 'tools/list':
        result = {'tools': []}
    else:
        result = {}
    print(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}), flush=True)
