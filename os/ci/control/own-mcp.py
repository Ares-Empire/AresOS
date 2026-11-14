"""An MCP server of "his own", for the CI guest only (package 18c, B2 checks 5 and 6).

It stands for a server the owner added himself at user scope: our install step must leave its entry alone, and an
ordinary session calls its one tool. Standard library only, MCP over stdio (one JSON-RPC message per line).
"""
import json
import sys

TOOL = {'name': 'note', 'description': 'Answer with the fixed note for one word (CI fixture).',
        'inputSchema': {'type': 'object', 'properties': {'word': {'type': 'string', 'maxLength': 64}},
                        'required': ['word'], 'additionalProperties': False}}


def answer(message):
    method, ident = message.get('method'), message.get('id')
    if ident is None:
        return None
    params = message.get('params') or {}
    if method == 'initialize':
        result = {'protocolVersion': params.get('protocolVersion', '2025-06-18'), 'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'own-notes', 'version': '1'}}
    elif method == 'tools/list':
        result = {'tools': [TOOL]}
    elif method == 'tools/call' and params.get('name') == TOOL['name']:
        word = str((params.get('arguments') or {}).get('word', ''))[:64]
        result = {'content': [{'type': 'text', 'text': f'OWN_NOTE {word}'}], 'isError': False}
    elif method == 'ping':
        result = {}
    else:
        return {'jsonrpc': '2.0', 'id': ident, 'error': {'code': -32601, 'message': f'Unknown method: {method}'}}
    return {'jsonrpc': '2.0', 'id': ident, 'result': result}


def main():
    for line in sys.stdin:
        if line.strip():
            reply = answer(json.loads(line))
            if reply is not None:
                sys.stdout.write(json.dumps(reply) + '\n')
                sys.stdout.flush()


if __name__ == '__main__':
    main()
