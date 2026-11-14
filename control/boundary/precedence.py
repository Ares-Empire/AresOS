"""Native managed-ask precedence, fixed tool calls and independent arrival logs.

PermissionRequest outcomes are recorded separately from mandatory ask precedence.
The observed version-pinned outcomes are compared only after all four cases run.
"""
import json
import hashlib
from pathlib import Path

from native import ROOT, OUT, POLICY, Session, tool
from boundary_assertions import tool_text
from aresos_control.boundary_policy import managed_settings
from aresos_control.definitions import instructions_for, tools_for

SEND = 'mcp__testapp__send'
LIST = 'mcp__testapp__list'
SCOPES = {'user': Path('/home/assistant/.claude/settings.json'),
          'project': Path('/home/assistant/work/.claude/settings.json'),
          'local': Path('/home/assistant/work/.claude/settings.local.json')}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def model_contract(requests):
    # Native 2.1.319 puts MCP instructions in an environment message. Capture
    # system as well; inspect the whole actual prompt rather than assuming a role.
    prompt = '\n'.join(text for request in requests for text in strings([request['system'], request['messages']]))
    definitions = {t['name']: t for request in requests for t in request['tools']}
    for app in ('testapp', 'mail', 'chrome'):
        expected = instructions_for(app)
        assert '## ' + app + '\n' + expected in prompt, 'Server instructions shortened or absent: ' + app
        for t in tools_for(app):
            sent = definitions['mcp__' + app + '__' + t['name']]
            assert sent['description'] == t['description'], 'Description changed: ' + t['name']
            assert sent['input_schema'] == t['inputSchema'], 'Schema changed: ' + t['name']
    print('MCP_INSTRUCTIONS_OK apps=testapp,mail,chrome full_request_text system_captured full_tool_definitions', flush=True)
    return {app:hashlib.sha256(instructions_for(app).encode()).hexdigest() for app in ('testapp','mail','chrome')}


def hook(put, case, event):
    marker = Path('/tmp/claude/precedence-hook-' + case + '.jsonl')
    output = ({'hookSpecificOutput': {'hookEventName': event, 'permissionDecision': 'allow'}}
              if event == 'PreToolUse' else
              {'hookSpecificOutput': {'hookEventName': event, 'decision': {'behavior': 'allow'}}})
    path = Path('/home/assistant/precedence-hook.py')
    (OUT / ('precedence-' + case + '-hook-output.json')).write_text(json.dumps(output, indent=2))
    put(path, 'import json,sys\nfrom pathlib import Path\n'
        'event=json.load(sys.stdin)\n'
        f'with Path({str(marker)!r}).open("a") as log: log.write(json.dumps(event)+"\\n")\n'
        f'print({json.dumps(output)!r})\n')
    return {'matcher': SEND, 'hooks': [{'type': 'command', 'command': '/usr/bin/python3 -I ' + str(path)}]}, marker


def precedence_checks(run, put):
    policy_original = POLICY.read_bytes()
    originals = {p: p.read_bytes() for p in SCOPES.values()}
    config = Path('/home/assistant/.claude.json')
    config_original = config.read_bytes()
    try:
        put(config, json.dumps({'hasCompletedOnboarding': True, 'theme': 'dark',
            'customApiKeyResponses': {'approved': ['SYNTHETIC_BOUNDARY_NONCREDENTIAL'[-20:]]},
            'projects': {'/home/assistant/work': {'hasTrustDialogAccepted': True}}}))
        # Same syntax as image setup, run as the owner. No managed MCP file exists.
        assert not Path('/etc/claude-code/managed-mcp.json').exists()
        for app in ('testapp', 'mail', 'chrome'):
            server = {'type': 'stdio', 'command': '/usr/bin/python3',
                      'args': ['-I', '/opt/aresos-control/mcp-fixture.py', app]}
            run(['/usr/local/bin/claude', 'mcp', 'add-json', '--scope', 'user', app, json.dumps(server)],
                'precedence-install-' + app)
        installed = json.loads(config.read_text())['mcpServers']
        assert set(installed) == {'testapp', 'mail', 'chrome'}, installed
        cases = []
        for skip in (False, True):
            for scope in ('none', 'user', 'project', 'local', 'all', 'pre_allow', 'pre_allow_all'):
                cases.append((('skip-' if skip else 'normal-') + scope, skip, scope, None, None))
            for level in ('user', 'managed'):
                cases.append((('skip-' if skip else 'normal-') + 'permission-' + level,
                              skip, 'none', 'PermissionRequest', level))
        # A send-arrival positive control proves the fixture has a working send path.
        cases[:0] = [('positive-no-managed-ask-' + scope, False, scope, None, None)
                     for scope in ('user', 'project', 'local', 'all', 'pre_allow')]
        cases.insert(0, ('positive-skip-no-managed-ask', True, 'none', None, None))
        summary = []
        for case, skip, scope, event, level in cases:
            policy = managed_settings()
            settings = {name: {} for name in SCOPES}
            if scope in SCOPES:
                settings[scope]['permissions'] = {'allow': [SEND, LIST]}
            elif scope in ('all', 'pre_allow_all'):
                for value in settings.values():
                    value['permissions'] = {'allow': [SEND, LIST]}
            # Reads through MCP ordinarily ask once too; the list positive control
            # gets its own explicit user allow in every case, never a send grant.
            settings['user'].setdefault('permissions', {}).setdefault('allow', []).append(LIST)
            marker = None
            if scope.startswith('pre_allow') or event:
                event = event or 'PreToolUse'
                entry, marker = hook(put, case, event)
                target = policy if level == 'managed' else settings['user']
                target.setdefault('hooks', {})[event] = [entry]
            if 'no-managed-ask' in case:
                policy['permissions']['ask'].remove(SEND)
            POLICY.write_text(json.dumps(policy))
            for name, path in SCOPES.items():
                put(path, json.dumps(settings[name]))
            (OUT / ('precedence-' + case + '-sources.json')).write_text(json.dumps(settings, indent=2))
            from check import ENV
            env = dict(ENV, ARESOS_BOUNDARY_CASE=case, ENABLE_TOOL_SEARCH='false')
            flags = ['-p', '--output-format', 'stream-json', '--verbose']
            if skip:
                flags.append('--dangerously-skip-permissions')
            blocks = [tool(LIST, {}, 'fixed-list'), tool(SEND, {
                'question': 'Send this fixture message?', 'operation_id': 'fixture:precedence',
                'description': {'text': 'Synthetic fixed payload'}}, 'fixed-send')]
            receiver_before = (OUT / 'stub.txt').read_text()
            with Session(blocks, 'precedence-' + case) as session:
                result = run(['/usr/local/bin/claude', *flags], 'precedence-' + case,
                             env=env, input='Execute the fixed local precedence test.\n', timeout=90, required=False)
                rows = session.results
                assert result.returncode == 0 and len(rows) == 2, (case, result, rows)
                assert not rows['fixed-list'].get('is_error') and 'FIXTURE_LIST_RAN' in tool_text(rows['fixed-list'])
                if case == 'normal-none':
                    model_contract(session.requests)
            delta = (OUT / 'stub.txt').read_text()[len(receiver_before):]
            list_arrivals = delta.count('POST /precedence/list/' + case + ' HTTP/1.1')
            send_arrivals = delta.count('POST /precedence/send/' + case + ' HTTP/1.1')
            expected_send = int('no-managed-ask' in case)
            assert list_arrivals == 1, (case, delta)
            if event != 'PermissionRequest':
                assert send_arrivals == expected_send, (case, delta)
            else:
                assert send_arrivals in (0, 1), (case, delta)
            if send_arrivals:
                assert not rows['fixed-send'].get('is_error') and 'FIXTURE_SEND_RAN' in tool_text(rows['fixed-send'])
            else:
                assert rows['fixed-send'].get('is_error'), (case, rows)
                assert any(s in tool_text(rows['fixed-send']).lower() for s in ('permission', 'approval', 'asks the person')), rows
            events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            init = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
            assert len(init) == 1 and init[0]['permissionMode'] == ('bypassPermissions' if skip else 'default'), init
            hook_calls = len(marker.read_text().splitlines()) if marker and marker.exists() else 0
            if marker and marker.exists():
                (OUT / ('precedence-' + case + '-hook-events.jsonl')).write_bytes(marker.read_bytes())
            if event == 'PreToolUse':
                assert hook_calls == 1, (case, hook_calls)
            row = {'case': case, 'mode': init[0]['permissionMode'], 'list_arrivals': list_arrivals,
                   'send_arrivals': send_arrivals, 'hook_calls': hook_calls,
                   'permission_request_interactive': 'unexercised' if event == 'PermissionRequest' and not hook_calls else None}
            summary.append(row)
            print('PRECEDENCE ' + json.dumps(row, sort_keys=True), flush=True)
            (OUT / 'precedence-summary.json').write_text(json.dumps(summary, indent=2))
        observed = {r['case']: {'send_arrivals': r['send_arrivals'], 'hook_calls': r['hook_calls']}
                    for r in summary if '-permission-' in r['case']}
        expected = json.loads((ROOT / 'permission-request-expected.json').read_text())
        assert observed == expected, 'Pinned PermissionRequest outcome changed: ' + json.dumps(observed)
        from chrome_precedence import chrome_precedence
        chrome_precedence(run,put,model_contract)
        print('PRECEDENCE_OK cases=' + str(len(summary)) + ' PermissionRequest=' + json.dumps(observed, sort_keys=True), flush=True)
    finally:
        POLICY.write_bytes(policy_original)
        config.write_bytes(config_original)
        for path, content in originals.items():
            path.write_bytes(content)
