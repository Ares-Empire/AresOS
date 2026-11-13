"""Fixed streaming Messages test double. No model, sign-in, or external provider.

Only the root supervisor installs synthetic loopback auth in this disposable
container. The CLI starts normally, with user settings and user-scope MCP servers.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import os
from pathlib import Path
import subprocess
import threading
from boundary_assertions import (container_identity, validate_identity, validate_sandbox_result,
                                 policy_mounts, observed_processes, tool_text)
from boundary_assertions import mount_view

ROOT = Path('/opt/aresos-control')
OUT = Path('/evidence')
POLICY = Path('/etc/claude-code/managed-settings.json')


class Session:
    def __init__(self, blocks, name, credential=True, grants=()):
        self.blocks = blocks
        self.name = name
        self.results = {}
        self.requests = []
        self.error = None
        self.before = None
        self.integrity = None
        self.observer = None
        self.observer_log = None
        self.sent = False
        self.credential = credential
        self.grants = grants
        session = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                messages = request.get('messages', [])
                session.requests.append({'path': self.path, 'stream': request.get('stream'),
                                         'messages': messages,
                                         'system': request.get('system'), 'tools': request.get('tools', [])})
                (OUT / (name + '-requests.json')).write_text(json.dumps(session.requests, indent=2))
                for message in messages:
                    for block in message.get('content', []) if isinstance(message.get('content'), list) else []:
                        if block.get('type') == 'tool_result':
                            session.results[block['tool_use_id']] = block
                (OUT / (name + '-results.json')).write_text(json.dumps(session.results, indent=2))
                if session.before is not None and len(session.results) == len(session.blocks):
                    session.integrity = {p: {'before': before, 'after': file_digest(p)}
                                         for p, before in session.before.items()}
                    (OUT / (name + '-integrity.json')).write_text(json.dumps(session.integrity, indent=2))
                if self.path.endswith('count_tokens'):
                    data = json.dumps({'input_tokens': 100}).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                content = session.blocks if not session.sent else [{'type': 'text', 'text': 'FIXED_TEST_DONE'}]
                if not session.sent and session.blocks:
                    fixtures = json.loads((ROOT / 'fixtures.json').read_text())
                    paths = fixtures['reads'] + fixtures['writes'] + fixtures['notebooks'] + ['/home/assistant/outside.txt', '/home/assistant/outside-new.txt', '/dev/uinput']
                    # Snapshot when the CLI is about to execute the calls, after
                    # its legitimate startup metadata writes and before attacks.
                    session.before = {p: file_digest(p) for p in paths}
                    if any(b.get('name') == 'Bash' for b in session.blocks):
                        session.observer_log = open(OUT / (name + '-processes.txt'), 'w')
                        session.observer = subprocess.Popen(['/usr/bin/python3', '-I', str(ROOT / 'observe.py')],
                            stdout=session.observer_log, stderr=session.observer_log)
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
                         'ANTHROPIC_API_KEY': 'SYNTHETIC_BOUNDARY_NONCREDENTIAL' if self.credential else ''}
        assert all(command in ('/usr/bin/python3 -I boundary-hostile.py',
                               '/usr/bin/python3 -I boundary-socket-state.py') for command in self.grants)
        if self.grants:
            policy['permissions'].setdefault('allow', []).extend('Bash(' + c + ')' for c in self.grants)
        (OUT / (self.name + '-managed-settings.json')).write_text(json.dumps(policy, indent=2))
        POLICY.write_text(json.dumps(policy))
        self.thread.start()
        return self

    def __exit__(self, *args):
        POLICY.write_bytes(self.original)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        if self.observer is not None:
            self.observer.terminate()
            self.observer.wait(timeout=10)
            self.observer_log.close()


def file_digest(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def tool(name, inputs, identifier):
    return {'type': 'tool_use', 'id': identifier, 'name': name, 'input': inputs}


def invoke(run, blocks, name, env=None, credential=True, grants=(), flags=()):
    with Session(blocks, name, credential, grants) as session:
        # No additional CLI flags: non-TTY stdin selects print mode natively.
        args = ['/usr/local/bin/claude', *flags]
        result = run(args, name, env=env, input='Execute the fixed local boundary test.\n',
                     timeout=100, required=False)
        if session.before is not None and session.results:
            assert session.integrity is not None, 'incomplete tool result observation'
            assert all(row['before'] == row['after'] for row in session.integrity.values()), 'native target changed: ' + name
        for block in blocks:
            if block.get('name') == 'Bash' and block['id'] in session.results:
                row = session.results[block['id']]
                if block['id'] != 'identity':
                    validate_sandbox_result(row, container_identity())
                elif not row.get('is_error'):
                    observed = observed_processes(OUT / (name + '-processes.txt'))
                    assert observed, 'unobserved simple Bash'
                    for context in observed:
                        validate_identity(context, container_identity())
        print('NATIVE_RESULTS ' + name + ' returned=' + str(len(session.results)), flush=True)
        return result, session.results


def native_checks(run, put, mode, snapshots, stub):
    binary = Path('/usr/local/bin/claude').resolve().read_bytes()
    for needle in [b'function swr', b'ARGV0=', b'seccompConfig:', b'function Fno', b'CLAUDE_CODE_AUTO_CONNECT_IDE']:
        snippets = []
        start = 0
        while len(snippets) < 30:
            position = binary.find(needle, start)
            if position < 0:
                break
            snippets.append(binary[max(0, position-500):position+1800].decode('utf-8', errors='replace'))
            start = position + len(needle)
        (OUT / ('native-discovery-' + needle.decode().replace(':','') + '.txt')).write_text('\n'.join(snippets))
    # All documented file fallbacks are poisoned at once. Each has a distinct
    # execution marker; native socket results must remain filtered, and none may
    # run. The primary external helper's missing/corrupt checks are separate.
    bases = ['/usr/lib/node_modules/@anthropic-ai/sandbox-runtime',
             '/opt/homebrew/lib/node_modules/@anthropic-ai/sandbox-runtime',
             '/home/assistant/.npm/lib/node_modules/@anthropic-ai/sandbox-runtime',
             '/home/assistant/.npm-global/lib/node_modules/@anthropic-ai/sandbox-runtime',
             '/opt/aresos-control/node_modules/@anthropic-ai/claude-code-linux-x64',
             '/opt/aresos-control/node_modules/@anthropic-ai',
             '/opt/aresos-control/node_modules', '/$bunfs/root', '/$bunfs', '/']
    planted = []
    for index, base in enumerate(bases):
        path = Path(base) / 'vendor/seccomp/x64/apply-seccomp'
        assert not path.exists(), str(path)
        put(path, '#!/bin/sh\necho ran > /tmp/claude/planted-helper-' + str(index) + '\nexit 0\n',
            uid=10001 if base.startswith('/home/') else 0)
        path.chmod(0o755)
        planted.append(path)
    (OUT / 'native-planted-helper-paths.json').write_text(json.dumps([str(p) for p in planted], indent=2))
    native_before = (OUT / 'stub.txt').read_text().splitlines()
    print('CONTAINER_IDENTITY ' + json.dumps({n: os.readlink('/proc/self/ns/' + n) for n in ('net', 'mnt')}), flush=True)
    # The baseline receives no test grant. Both helper modes start the native
    # CLI normally with the same owner, environment and optional user settings.
    baseline_result, baseline = invoke(run, [tool('Bash', {'command': 'sleep 2'}, 'identity')],
                                      'native-baseline')
    assert baseline_result.returncode == 0 and not baseline['identity'].get('is_error')
    hostile = '/usr/bin/python3 -I boundary-hostile.py'
    state_command = '/usr/bin/python3 -I boundary-socket-state.py'
    name = 'native-hostile-approved'
    result, rows = invoke(run, [tool('Bash', {'command': hostile, 'timeout': 30000}, 'hostile'),
                               tool('Bash', {'command': state_command}, 'socket-state')],
                          name, grants=(hostile, state_command))
    assert result.returncode == 0 and len(rows) == 2, 'native CLI never returned tool results'
    executed = 'HOSTILE_DONE' in tool_text(rows['hostile'])
    if not executed:
        assert validate_sandbox_result(rows['hostile'], container_identity()) is None
        (OUT / 'native-not-executed.json').write_text(json.dumps({
            'reason': rows['hostile'], 'attempts': 1,
            'policy': 'exact fixed-command managed allow simulates one owner approval'}, indent=2))
        print('NATIVE_NOT_EXECUTED mode=' + mode + ' exact_command_approval_denied see=' +
              name + '-results.json', flush=True)
        # The brief forbids widening the grant after a real denial.
        raise AssertionError('Optional native hostile commands did not execute; no qualification claimed')
    else:
        identities = {key: validate_sandbox_result(rows[key], container_identity()) for key in rows}
        assert all(identities.values()), 'approved native socket-state did not execute'
        baseline_contexts = observed_processes(OUT / 'native-baseline-processes.txt')
        contexts = observed_processes(OUT / (name + '-processes.txt'))
        assert len(baseline_contexts) == 1 and len(contexts) == 2, 'incomplete native outside observation'
        settings = json.loads((ROOT / 'optional-sandbox.json').read_text())
        baseline_view = policy_mounts(baseline_contexts[0]['mountinfo'], settings)
        baseline_tree = mount_view(baseline_contexts[0]['mountinfo'])
        trees = {'baseline': baseline_tree}
        views = {}
        for key, identity in identities.items():
            matches = [c for c in contexts if c['namespaces'] == identity['namespaces'] and
                       c['inner_pid'] == identity['pid']]
            assert len(matches) == 1, 'self report and outside observer disagree: ' + key
            context = matches[0]
            validate_identity(context, container_identity())
            views[key] = policy_mounts(context['mountinfo'], settings)
            trees[key] = mount_view(context['mountinfo'])
            differences = [{'index': index, 'baseline': baseline_tree[index] if index < len(baseline_tree) else None,
                            'approved': trees[key][index] if index < len(trees[key]) else None}
                           for index in range(max(len(baseline_tree), len(trees[key])))
                           if index >= min(len(baseline_tree), len(trees[key])) or
                           baseline_tree[index] != trees[key][index]]
            (OUT / 'native-mount-trees.json').write_text(json.dumps(trees, indent=2))
            (OUT / (key + '-mount-tree-differences.json')).write_text(json.dumps(differences, indent=2))
            (OUT / 'native-policy-mounts.json').write_text(json.dumps({
                'baseline': baseline_view, **views}, indent=2))
            assert not differences, 'approval changed native full mount tree: ' + json.dumps(differences)
            assert views[key] == baseline_view, 'approval changed native policy mount view'
        (OUT / 'native-policy-mounts.json').write_text(json.dumps({
            'baseline': baseline_view, **views}, indent=2))
        native_after = (OUT / 'stub.txt').read_text().splitlines()
        (OUT / 'native-stub-delta.json').write_text(json.dumps(native_after[len(native_before):]))
        assert native_after == native_before, 'native hostile arrival'
        integrity = json.loads((OUT / (name + '-integrity.json')).read_text())
        hostile_rows = [json.loads(line[8:]) for line in tool_text(rows['hostile']).splitlines()
                        if line.startswith('HOSTILE ')]
        (OUT / 'native-hostile-rows.json').write_text(json.dumps(hostile_rows, indent=2))
        fixtures = json.loads((ROOT / 'fixtures.json').read_text())
        expected = len(fixtures['sockets']) + 2 + len(fixtures['reads']) + 3 * len(fixtures['writes']) + 16
        assert len(hostile_rows) == expected and 'HOSTILE_DONE ' + str(expected) in tool_text(rows['hostile'])
        opened = [r for r in hostile_rows if not r['blocked']]
        (OUT / 'native-open-routes.json').write_text(json.dumps(opened, indent=2))
        assert not opened, 'BLOCKING PLAN-GAP native open routes: ' + str(opened)
        assert stub.poll() is None, 'native listener died'
        print('NATIVE_BOUNDARY_OK mode=' + mode + ' attacks=' + str(len(hostile_rows)) +
              ' isolated_net_mnt filters_above_container AF_UNIX=EPERM AF_VSOCK=EPERM unchanged=' + str(len(integrity)) +
              ' hostile_connections=0 approval_mount_tree_unchanged mounts=' + str(len(baseline_tree)), flush=True)
    try:
        run(['/usr/local/bin/node', str(ROOT / 'run.mjs'), '--native-canary'], 'native-embedded-canary-planted')
    finally:
        for path in planted:
            path.unlink(missing_ok=True)
    assert not list(Path('/tmp/claude').glob('planted-helper-*')), 'native used a non-pinned fallback'
    print('NATIVE_HELPER_PATHS_OK non_pinned_candidates_unused=' + str(len(planted)), flush=True)
