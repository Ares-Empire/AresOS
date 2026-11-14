"""Scripted multi-turn streaming Messages double, shared by container and VM.

No native.py behavior is reused or changed. Each owner prompt selects one script
step; tool continuations and Stop-hook continuations cannot start another send.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def texts(content):
    """A tool result's text: Claude Code sends a real MCP server's result as one string, a fixture's as blocks."""
    if isinstance(content, str):
        return [content]
    return [block.get('text', '') for block in content if isinstance(block, dict)]


def tool(name, inputs, identifier):
    return {'type': 'tool_use', 'id': identifier, 'name': name, 'input': inputs}


class Script:
    """Steps: prompt, optional prepare={name,input}, send=name, approval=dict.

    With prepare, copy data.approval unchanged out of its successful tool result.
    Without prepare the boundary fixture uses the fixed approval, as in 18d.
    """
    def __init__(self, steps):
        self.steps = steps
        self.issued = set()
        self.finished = set()
        self.continuations = []
        self.results = {}

    def respond(self, request):
        messages = request.get('messages', [])
        for message in messages:
            for block in message.get('content', []) if isinstance(message.get('content'), list) else []:
                if block.get('type') == 'tool_result':
                    self.results[block['tool_use_id']] = block
        # Only a new owner marker can select another send. Hook messages contain
        # no marker and remain continuations of the last owner turn.
        prompt_text = '\n'.join(strings([m.get('content') for m in messages if m.get('role') == 'user']))
        active = [i for i, step in enumerate(self.steps) if step['prompt'] in prompt_text]
        assert active, 'No scripted owner prompt in model request'
        index = max(active)
        step = self.steps[index]
        prepare_id, send_id = f'prepare-{index}', f'send-{index}'
        if step.get('prepare') and prepare_id not in self.issued:
            self.issued.add(prepare_id)
            return [tool(step['prepare']['name'], step['prepare']['input'], prepare_id)]
        if send_id not in self.issued:
            approval = step.get('approval')
            if step.get('prepare'):
                result = self.results[prepare_id]
                assert not result.get('is_error'), result
                payloads = [json.loads(s) for s in texts(result['content']) if s.startswith('{')]
                approvals = [p['data']['approval'] for p in payloads if p.get('ok') and 'approval' in p.get('data', {})]
                assert len(approvals) == 1, payloads
                approval = approvals[0]
            assert isinstance(approval, dict)
            self.issued.add(send_id)
            return [tool(step['send'], approval, send_id)]
        assert send_id in self.results, 'Send returned no tool result'
        if index in self.finished:
            self.continuations.append({'step': index, 'messages': messages})
            return [{'type': 'text', 'text': f'INTERACTIVE_CONTINUATION_DONE_{index + 1}'}]
        self.finished.add(index)
        return [{'type': 'text', 'text': f'INTERACTIVE_DONE_{index + 1}'}]


class Model:
    def __init__(self, steps, evidence, port=18081):
        self.script = Script(steps)
        self.evidence = Path(evidence)
        self.requests = []
        self.error = None
        model = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    if self.path.endswith('count_tokens'):
                        data = b'{"input_tokens":100}'
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    model.requests.append({'path': self.path, **request})
                    content = model.script.respond(request)
                    model.save()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Connection', 'close')
                    self.end_headers()

                    def event(kind, **data):
                        payload = json.dumps({'type': kind, **data})
                        self.wfile.write(f'event: {kind}\ndata: {payload}\n\n'.encode())
                        self.wfile.flush()

                    event('message_start', message={'id': 'msg_interactive_fixed', 'type': 'message',
                        'role': 'assistant', 'model': request.get('model', 'fixture'), 'content': [],
                        'stop_reason': None, 'stop_sequence': None,
                        'usage': {'input_tokens': 100, 'output_tokens': 10}})
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
                    event('message_delta', delta={'stop_reason': 'tool_use' if any(
                        b['type'] == 'tool_use' for b in content) else 'end_turn', 'stop_sequence': None},
                        usage={'output_tokens': 10})
                    event('message_stop')
                except Exception as error:
                    model.error = repr(error)
                    model.save()
                    self.send_error(500)

        self.server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def save(self):
        self.evidence.mkdir(parents=True, exist_ok=True)
        for name, value in [('requests', self.requests), ('results', self.script.results),
                            ('continuations', self.script.continuations), ('error', self.error)]:
            (self.evidence / (name + '.json')).write_text(json.dumps(value, indent=2))

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.save()
