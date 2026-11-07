"""Fixed streaming Messages test double. No model, sign-in, or external provider.

Only the root supervisor changes managed env in this disposable container; the
launcher has no test options and the assistant cannot select its endpoint.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading

ROOT = Path('/opt/aresos-control')
OUT = Path('/evidence')
POLICY = Path('/etc/claude-code/managed-settings.json')


class Session:
    def __init__(self, blocks, name):
        self.blocks = blocks
        self.name = name
        self.results = {}
        self.requests = []
        self.sent = False
        session = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                messages = request.get('messages', [])
                session.requests.append({'path': self.path, 'stream': request.get('stream'),
                                         'messages': messages,
                                         'tools': [t['name'] for t in request.get('tools', [])]})
                (OUT / (name + '-requests.json')).write_text(json.dumps(session.requests, indent=2))
                for message in messages:
                    for block in message.get('content', []) if isinstance(message.get('content'), list) else []:
                        if block.get('type') == 'tool_result':
                            session.results[block['tool_use_id']] = block
                (OUT / (name + '-results.json')).write_text(json.dumps(session.results, indent=2))
                if self.path.endswith('count_tokens'):
                    data = json.dumps({'input_tokens': 100}).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                content = session.blocks if not session.sent else [{'type': 'text', 'text': 'FIXED_TEST_DONE'}]
                session.sent = True
                reason = 'tool_use' if any(b['type'] == 'tool_use' for b in content) else 'end_turn'
                message = {'id': 'msg_boundary_fixed', 'type': 'message', 'role': 'assistant',
                           'model': request.get('model', 'claude-sonnet-4-6'), 'content': [],
                           'stop_reason': None, 'stop_sequence': None,
                           'usage': {'input_tokens': 100, 'output_tokens': 10}}
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Connection', 'close')
                self.end_headers()

                def event(kind, **data):
                    payload = json.dumps({'type': kind, **data})
                    self.wfile.write(f'event: {kind}\ndata: {payload}\n\n'.encode())
                    self.wfile.flush()

                event('message_start', message=message)
                for index, block in enumerate(content):
                    start = dict(block)
                    if block['type'] == 'tool_use':
                        start['input'] = {}
                        delta = {'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])}
                    else:
                        start['text'] = ''
                        delta = {'type': 'text_delta', 'text': block['text']}
                    event('content_block_start', index=index, content_block=start)
                    event('content_block_delta', index=index, delta=delta)
                    event('content_block_stop', index=index)
                event('message_delta', delta={'stop_reason': reason, 'stop_sequence': None},
                      usage={'output_tokens': 10})
                event('message_stop')

        self.server = ThreadingHTTPServer(('127.0.0.1', 18081), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.original = POLICY.read_bytes()
        policy = json.loads(self.original)
        policy['env'] = {'ANTHROPIC_BASE_URL': 'http://127.0.0.1:18081',
                         'ANTHROPIC_API_KEY': 'SYNTHETIC_BOUNDARY_NONCREDENTIAL'}
        POLICY.write_text(json.dumps(policy))
        self.thread.start()
        return self

    def __exit__(self, *args):
        POLICY.write_bytes(self.original)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def tool(name, inputs, identifier):
    return {'type': 'tool_use', 'id': identifier, 'name': name, 'input': inputs}


def invoke(run, blocks, name, launcher=True, env=None):
    with Session(blocks, name) as session:
        # No additional CLI flags: non-TTY stdin selects print mode natively.
        args = ['/usr/local/bin/aresos-assistant'] if launcher else ['/usr/local/bin/claude', '--setting-sources', '']
        result = run(args, name, env=env, input='Execute the fixed local boundary test.\n',
                     timeout=100, required=False)
        print('NATIVE_RESULTS ' + name + ' ' + json.dumps(session.results), flush=True)
        return result, session.results


def native_checks(run, put, mode, snapshots, stub):
    print('CONTAINER_IDENTITY ' + json.dumps({n: os.readlink('/proc/self/ns/' + n) for n in ('net', 'mnt')}), flush=True)
    # First run exercises the native resolver; absent mode deliberately bypasses
    # launcher checks with the launcher's exact environment/cwd/uid/CLI arguments.
    result, rows = invoke(run, [tool('Bash', {'command': '/usr/bin/python3 -I /opt/aresos-control/hostile.py',
                                            'timeout': 30000}, 'hostile')], 'native-hostile', mode == 'present')
    assert rows, 'native CLI never returned tool results'
    print('NATIVE_DISCOVERY mode=' + mode, flush=True)
