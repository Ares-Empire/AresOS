"""Fixed streaming Messages test double. No model, sign-in, or external provider.

Only the root supervisor changes managed env in this disposable container; the
launcher has no test options and the assistant cannot select its endpoint.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import os
from pathlib import Path
import subprocess
import threading
from boundary_assertions import (container_identity, validate_identity, validate_sandbox_result,
                                 require_source_positive, policy_mounts, observed_processes, tool_text)
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
                                         'tools': [t['name'] for t in request.get('tools', [])]})
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
        # Root-only, disposable-image stand-in for the owner approving exactly
        # these fixed commands. No wildcard, other tool, or production change.
        assert all(command in ('/usr/bin/python3 -I boundary-hostile.py',
                               '/usr/bin/python3 -I boundary-socket-state.py') for command in self.grants)
        policy['permissions']['allow'] += ['Bash(' + command + ')' for command in self.grants]
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


def invoke(run, blocks, name, launcher=True, env=None, sources='', credential=True, grants=()):
    with Session(blocks, name, credential, grants) as session:
        # No additional CLI flags: non-TTY stdin selects print mode natively.
        args = ['/usr/local/bin/aresos-assistant'] if launcher else ['/usr/local/bin/claude', '--setting-sources', sources]
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
    # The baseline receives no test grant. In absent mode only the launcher's
    # checks are bypassed, keeping its environment/uid/cwd/native arguments.
    baseline_result, baseline = invoke(run, [tool('Bash', {'command': 'sleep 2'}, 'identity')],
                                      'native-baseline', mode == 'present')
    assert baseline_result.returncode == 0 and not baseline['identity'].get('is_error')
    hostile = '/usr/bin/python3 -I boundary-hostile.py'
    state_command = '/usr/bin/python3 -I boundary-socket-state.py'
    name = 'native-hostile-approved'
    result, rows = invoke(run, [tool('Bash', {'command': hostile, 'timeout': 30000}, 'hostile'),
                               tool('Bash', {'command': state_command}, 'socket-state')],
                          name, mode == 'present', grants=(hostile, state_command))
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
    else:
        identities = {key: validate_sandbox_result(rows[key], container_identity()) for key in rows}
        assert all(identities.values()), 'approved native socket-state did not execute'
        baseline_contexts = observed_processes(OUT / 'native-baseline-processes.txt')
        contexts = observed_processes(OUT / (name + '-processes.txt'))
        assert len(baseline_contexts) == 1 and len(contexts) == 2, 'incomplete native outside observation'
        settings = json.loads(POLICY.read_text())
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
    failures = []
    checks = [('ide', lambda: ide_checks(run, put, mode))]
    if mode == 'present':
        checks += [('file-tools', lambda: file_tool_checks(run)),
                   ('sources', lambda: source_checks(run, put))]
    for name, check in checks:
        try:
            check()
        except Exception:
            import traceback
            failure = traceback.format_exc()
            (OUT / ('native-' + name + '-failure.txt')).write_text(failure)
            failures.append(name + ': ' + failure)
    assert (OUT / 'stub.txt').read_text().splitlines() == native_before, 'native file/web receiver arrival'
    assert not failures, '\n'.join(failures)



def file_tool_checks(run):
    fixtures = json.loads((ROOT / 'fixtures.json').read_text())
    blocks = []
    mapping = {}
    for name in ('Edit', 'Write', 'NotebookEdit'):
        for index, path in enumerate(fixtures['writes'] + fixtures['notebooks'] + ['/home/assistant/outside.txt']):
            identifier = name + '-' + str(index)
            inputs = {'file_path': path, 'old_string': 'synthetic fixture', 'new_string': 'HOSTILE_FILE_TOOL'}
            if name == 'Write':
                inputs = {'file_path': path, 'content': 'HOSTILE_FILE_TOOL'}
            elif name == 'NotebookEdit':
                inputs = {'notebook_path': path, 'new_source': 'HOSTILE_FILE_TOOL',
                          'cell_type': 'code', 'edit_mode': 'insert'}
            mapping[identifier] = path
            blocks.append(tool(name, inputs, identifier))
    for index, path in enumerate(fixtures['reads']):
        blocks.append(tool('Read', {'file_path': path}, 'Read-' + str(index)))
    blocks += [tool('Write', {'file_path': '/home/assistant/outside-new.txt',
                               'content': 'HOSTILE_OUTSIDE'}, 'Write-outside-new'),
               tool('WebFetch', {'url': 'http://blocked.boundary.localhost:18080/payload',
                                'prompt': 'Read this fixed synthetic page.'}, 'WebFetch'),
               tool('WebSearch', {'query': 'fixed boundary synthetic query'}, 'WebSearch'),
               tool('Bash', {'command': '/usr/bin/python3 -I boundary-socket-state.py',
                             'dangerouslyDisableSandbox': True}, 'disable-sandbox')]
    results = []
    for attempt in (1, 2):
        result, rows = invoke(run, blocks, 'native-file-tools-' + str(attempt))
        assert result.returncode == 0 and len(rows) == len(blocks)
        results.append(rows)
    # Retain parser/validation failures as unqualified; never relabel them as
    # permission refusals. Some fixed filenames cannot be NotebookEdit targets.
    unresolved = {}
    for attempt, batch in enumerate(results, 1):
        for identifier, row in batch.items():
            text = tool_text(row)
            if identifier == 'disable-sandbox':
                if validate_sandbox_result(row, container_identity()) is None:
                    unresolved[str(attempt) + ':' + identifier] = text
            else:
                assert row.get('is_error'), 'file/web tool unexpectedly ran: ' + identifier
                if not any(word in text for word in ('permission', 'permissions', 'outside')):
                    unresolved[str(attempt) + ':' + identifier] = text
    (OUT / 'native-file-unqualified.json').write_text(json.dumps(unresolved, indent=2))
    (OUT / 'native-file-tool-paths.json').write_text(json.dumps(mapping, indent=2))
    print('NATIVE_FILE_DISCOVERY ' + str(len(rows)), flush=True)


def ide_checks(run, put, mode):
    import base64
    import hashlib
    class IDE(BaseHTTPRequestHandler):
        arrivals = []
        def log_message(self, *args):
            pass
        def do_GET(self):
            IDE.arrivals.append(dict(self.headers))
            key = self.headers.get('Sec-WebSocket-Key', '')
            accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', accept)
            if self.headers.get('Sec-WebSocket-Protocol'):
                self.send_header('Sec-WebSocket-Protocol', self.headers['Sec-WebSocket-Protocol'].split(',')[0].strip())
            self.end_headers()
    class Listener(ThreadingHTTPServer):
        connections = 0
        def get_request(self):
            accepted = super().get_request()
            self.connections += 1
            return accepted
    server = Listener(('127.0.0.1', 18082), IDE)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = Path('/home/assistant/.claude.json')
    original = config.read_bytes()
    put(config, json.dumps({'autoConnectIde': True, 'hasCompletedOnboarding': True, 'theme': 'dark',
                            'customApiKeyResponses': {'approved': ['SYNTHETIC_BOUNDARY_NONCREDENTIAL'[-20:]]},
                            'projects': {'/home/assistant/work': {'hasTrustDialogAccepted': True}}}))
    lock = Path('/home/assistant/.claude/ide/18082.lock')
    put(lock, json.dumps({'pid': os.getpid(), 'workspaceFolders': ['/home/assistant/work'],
                          'ideName': 'Visual Studio Code', 'transport': 'ws',
                          'authToken': 'SYNTHETIC_IDE_TOKEN', 'runningInWindows': False}))
    try:
        from check import ENV
        positive_env = dict(ENV)
        positive_env.pop('CLAUDE_CODE_AUTO_CONNECT_IDE')
        invoke(run, [], 'ide-positive', launcher=False, env=positive_env)
        if not IDE.arrivals:
            interactive_probe('ide-positive-interactive', positive_env)
        positive = len(IDE.arrivals)
        positive_connections = server.connections
        invoke(run, [], 'ide-launcher', launcher=mode == 'present')
        if positive and mode == 'present':
            interactive_probe('ide-launcher-interactive', ENV, launcher=True)
        (OUT / 'ide-arrivals.json').write_text(json.dumps({'positive': positive, 'after_launcher': len(IDE.arrivals),
                                                          'positive_tcp': positive_connections, 'final_tcp': server.connections,
                                                          'requests': IDE.arrivals}, indent=2))
        assert positive and len(IDE.arrivals) == positive and server.connections == positive_connections, 'IDE positive control or launcher suppression failed'
        print('IDE_OK positive=' + str(positive) + ' launched=' + str(len(IDE.arrivals)-positive), flush=True)
    finally:
        config.write_bytes(original)
        lock.unlink()
        server.shutdown()
        server.server_close()
        thread.join()


def source_checks(run, put):
    scopes = {'user': Path('/home/assistant/.claude/settings.json'),
              'project': Path('/home/assistant/work/.claude/settings.json'),
              'local': Path('/home/assistant/work/.claude/settings.local.json')}
    originals = {p: p.read_bytes() for p in scopes.values()}
    global_config = Path('/home/assistant/.claude.json')
    originals[global_config] = global_config.read_bytes()
    put(global_config, json.dumps({'hasCompletedOnboarding': True, 'theme': 'dark',
        'customApiKeyResponses': {'approved': ['SYNTHETIC_BOUNDARY_NONCREDENTIAL'[-20:]]},
        'projects': {'/home/assistant/work': {'hasTrustDialogAccepted': True}}}))
    policy_original = POLICY.read_bytes()
    markers = []
    for scope, path in scopes.items():
        prefix = '/tmp/claude/source-' + scope + '-'
        markers += [Path(prefix + k) for k in ('hook', 'status', 'key', 'permission', 'plugin')]
        command = lambda k: 'echo ran > ' + prefix + k
        put(path, json.dumps({'permissions': {'allow': ['Write', 'Read', 'WebFetch', 'WebSearch']},
                              'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': command('hook')}]}]},
                              'statusLine': {'type': 'command', 'command': command('status')},
                              'apiKeyHelper': command('key') + '; echo SYNTHETIC_BOUNDARY_NONCREDENTIAL',
                              'enabledPlugins': {'fixture@boundary': True}}))
    plugin = Path('/home/assistant/.claude/plugins/cache/boundary/fixture/1.0.0')
    put(plugin / '.claude-plugin/plugin.json', json.dumps({'name': 'fixture', 'version': '1.0.0'}))
    put(plugin / 'hooks/hooks.json', json.dumps({'hooks': {'SessionStart': [{'hooks': [{'type': 'command',
        'command': 'echo ran > /tmp/claude/source-user-plugin'}]}]}}))
    registry = Path('/home/assistant/.claude/plugins/installed_plugins.json')
    put(registry, json.dumps({'version': 2, 'plugins': {'fixture@boundary': [{'scope': 'user',
        'installPath': str(plugin), 'version': '1.0.0', 'installedAt': '2026-11-07T00:00:00Z',
        'lastUpdated': '2026-11-07T00:00:00Z'}]}}))
    report = {}
    try:
        # Working positive controls remove ONLY the managed source gates, and
        # explicitly enable the lower scopes. They are not launcher sessions.
        positive = json.loads(policy_original)
        positive['allowManagedPermissionRulesOnly'] = False
        positive['allowManagedHooksOnly'] = False
        POLICY.write_text(json.dumps(positive))
        assert not Path('/home/assistant/work/source-permission.txt').exists(), 'stale Write positive'
        for attempt in (1, 2):
            positive_result, positive_rows = invoke(run, [tool('Write', {'file_path': '/home/assistant/work/source-permission.txt',
                                       'content': 'positive source allow'}, 'source-permission')],
                   'sources-positive-' + str(attempt), launcher=False,
                   sources='user,project,local', credential=False)
            assert positive_result.returncode == 0 and not positive_rows['source-permission'].get('is_error')
        from check import ENV
        for attempt in (1, 2):
            interactive_probe('sources-positive-tty-' + str(attempt), ENV,
                              sources='user,project,local', credential=False)
        report['positive_markers'] = [str(p) for p in markers if p.exists()]
        permission = Path('/home/assistant/work/source-permission.txt')
        report['positive_permission'] = permission.exists() and permission.read_text() == 'positive source allow'
        require_source_positive(report)
        print('SOURCES_POSITIVE_OK three_hooks local_status local_helper ordinary_Write', flush=True)
        POLICY.write_bytes(policy_original)
        refused = run(['/usr/local/bin/aresos-assistant'], 'sources-installed-plugin', required=False)
        assert refused.returncode == 78 and 'no installed plugins' in refused.stderr
        registry.unlink()
        for p in markers + [Path('/home/assistant/work/source-permission.txt')]:
            p.unlink(missing_ok=True)
        for attempt in (1, 2):
            result, rows = invoke(run, [tool('Write', {'file_path': '/home/assistant/work/source-permission.txt',
                                                      'content': 'HOSTILE_SOURCE'}, 'source-permission')],
                                  'sources-launcher-' + str(attempt))
            report['launcher_results_' + str(attempt)] = rows
            assert result.returncode == 0 and rows
        # A supplied key would bypass apiKeyHelper even if a lower setting
        # leaked. Repeat without a managed key: exclusion must leave no auth
        # source and must still execute no planted helper.
        for attempt in (1, 2):
            no_key, no_key_rows = invoke(run, [], 'sources-launcher-no-key-' + str(attempt), credential=False)
            report['no_key_exit_' + str(attempt)] = no_key.returncode
            assert no_key.returncode != 0 and not no_key_rows
        for attempt in (1, 2):
            interactive_probe('sources-launcher-tty-' + str(attempt), ENV, launcher=True)
        report['launcher_markers'] = [str(p) for p in markers if p.exists()]
        assert not report['launcher_markers'], report
        assert not Path('/home/assistant/work/source-permission.txt').exists()
        print('SOURCES_OK lower_scopes_no_markers_no_permission_grant', flush=True)
    finally:
        registry.unlink(missing_ok=True)
        POLICY.write_bytes(policy_original)
        for p, data in originals.items():
            p.write_bytes(data)
        (OUT / 'source-checks.json').write_text(json.dumps(report, indent=2))


def interactive_probe(name, env, launcher=False, sources='', credential=True):
    """Real TTY startup for integrations that print mode intentionally omits."""
    import fcntl
    import pty
    import select
    import signal
    import struct
    import termios
    import time
    from check import owner
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
    def prepare():
        owner()
        os.setsid()
        fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
    args = ['/usr/local/bin/aresos-assistant'] if launcher else ['/usr/local/bin/claude', '--setting-sources', sources]
    output = bytearray()
    with Session([], name, credential):
        process = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=slave,
                                   env=env, cwd='/home/assistant/work', preexec_fn=prepare)
        os.close(slave)
        try:
            until = time.monotonic() + 12
            while time.monotonic() < until and process.poll() is None:
                if select.select([master], [], [], .2)[0]:
                    try:
                        output.extend(os.read(master, 65536))
                    except OSError:
                        break
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
            os.close(master)
    (OUT / (name + '-tty.txt')).write_bytes(output)
    print('TTY_PROBE ' + name + ' bytes=' + str(len(output)), flush=True)
