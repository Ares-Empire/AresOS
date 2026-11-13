"""B1 supervisor: disposable boundary container ONLY, never the owner's host."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, '/opt/aresos-control')

from interactive_driver import Terminal, options
from interactive_model import Model
from aresos_control.boundary_policy import managed_settings

ROOT = Path('/opt/aresos-control')
OUT = Path('/evidence/interactive')
HOME = Path('/home/assistant')
WORK = HOME / 'work'
POLICY = Path('/etc/claude-code/managed-settings.json')
SEND = 'mcp__testapp__send'
PREPARE = 'mcp__testapp__prepare_send'
KEY = 'SYNTHETIC_BOUNDARY_NONCREDENTIAL'
SCOPES = {'user': HOME / '.claude/settings.json',
          'project': WORK / '.claude/settings.json', 'local': WORK / '.claude/settings.local.json'}
ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(HOME), 'USER': 'assistant',
       'LOGNAME': 'assistant', 'TERM': 'xterm-256color', 'LANG': 'C.UTF-8',
       'DISABLE_AUTOUPDATER': '1', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
       'CLAUDE_CODE_AUTO_CONNECT_IDE': 'false', 'ENABLE_TOOL_SEARCH': 'false'}


def owner():
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)


def run(args, env=None, required=True):
    result = subprocess.run(args, preexec_fn=owner, cwd=WORK, env=env or ENV,
                            capture_output=True, text=True, timeout=20)
    if required:
        assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2))
    os.chown(path, 10001, 10001)
    os.chown(path.parent, 10001, 10001)


def config():
    return {'hasCompletedOnboarding': True, 'theme': 'dark',
            'customApiKeyResponses': {'approved': [KEY[-20:]]},
            'projects': {str(WORK): {'hasTrustDialogAccepted': True}}}


def snapshot():
    return {str(path): json.loads(path.read_text()) if path.exists() else None
            for path in [HOME / '.claude.json', *SCOPES.values()]}


def arrivals(case):
    return (Path('/evidence/stub.txt').read_text()).count('POST /precedence/send/' + case + ' HTTP/1.1')


def make_hook(case, event):
    marker = HOME / ('interactive-hook-' + case + '.jsonl')
    output = ({'hookSpecificOutput': {'hookEventName': event, 'permissionDecision': 'allow'}}
              if event == 'PreToolUse' else
              {'hookSpecificOutput': {'hookEventName': event, 'decision': {'behavior': 'allow'}}})
    path = HOME / 'interactive-hook.py'
    put(path, 'import json,sys\nfrom pathlib import Path\n'
        'event=json.load(sys.stdin)\n'
        f'with Path({str(marker)!r}).open("a") as log: log.write(json.dumps(event)+"\\n")\n'
        f'print({json.dumps(output)!r})\n')
    return {'matcher': SEND, 'hooks': [{'type': 'command',
            'command': '/usr/bin/python3 -I ' + str(path)}]}, marker


def step(index):
    return {'prompt': 'INTERACTIVE_OWNER_TURN_' + str(index), 'send': SEND,
            'approval': {'question': 'Send this fixture message?',
                         'operation_id': 'fixture:interactive-' + str(index),
                         'description': {'text': 'Synthetic fixed payload'}}}


def exercise(case, skip, steps, answers, permission=False):
    evidence = OUT / case / ('session-' + str(steps[0]['prompt'][-1]))
    evidence.mkdir(parents=True, exist_ok=True)
    env = dict(ENV, ARESOS_BOUNDARY_CASE=case)
    flags = ['--dangerously-skip-permissions'] if skip else ['--permission-mode', 'default']
    shown, daa, warnings = [], [], []
    resumed = 0
    before = snapshot()
    (evidence / 'settings-before.json').write_text(json.dumps(before, indent=2))
    with Model(steps, evidence) as model:
        with Terminal(run, evidence, '/tmp/claude/interactive.sock', str(WORK),
                      ['/usr/local/bin/claude', *flags, steps[0]['prompt']], env) as terminal:
            for index, (script, answer) in enumerate(zip(steps, answers)):
                if index:
                    terminal.prompt(script['prompt'])
                done = 'INTERACTIVE_DONE_' + str(index + 1)
                screen = terminal.wait('permission-or-done-' + str(index + 1),
                    lambda s: any(t == 'Yes' for _, t in options(s)) or done in s, warning=skip)
                prompt_shown = any(t == 'Yes' for _, t in options(screen))
                shown.append(prompt_shown)
                if not permission:
                    assert prompt_shown, 'STOP: managed ask did not ask interactively: ' + case
                if prompt_shown:
                    assert 'Send this fixture message?' in screen, 'Service question absent from prompt'
                    question = screen.index('Send this fixture message?')
                    assert all(question < screen.index(key) for key in ('operation_id', 'description') if key in screen), screen
                    offered = any(t.startswith("Yes, and don't ask again") for _, t in options(screen))
                    daa.append(offered)
                    terminal.choose(screen, 'DAA' if answer == 'DAA' and offered else ('Yes' if answer == 'DAA' else (answer or 'No')))
                completed = terminal.wait('completed-or-interrupted-' + str(index + 1),
                    lambda s: done in s or 'Interrupted · What should Claude do instead?' in s)
                if done not in completed:
                    # Native No interrupts the turn. The denied result reaches
                    # the model only after another owner prompt; this marker
                    # cannot select another scripted send.
                    terminal.prompt('INTERACTIVE_RESUME_CURRENT_TURN')
                    resumed += 1
                    terminal.wait('completed-' + str(index + 1), lambda s: done in s)
                assert model.error is None, model.error
                assert len(model.script.results) == index + 1, model.script.results
                warnings.append(terminal.warning)
                (evidence / ('settings-after-turn-' + str(index + 1) + '.json')).write_text(json.dumps(snapshot(), indent=2))
    # Native transcript, not a reconstruction of model requests.
    transcripts = HOME / '.claude/projects'
    if transcripts.exists():
        for path in transcripts.rglob('*.jsonl'):
            assert path.stat().st_size < 5_000_000, 'Unexpectedly large synthetic transcript'
            target = evidence / 'transcripts' / path.relative_to(transcripts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    return {'prompt_shown': shown, 'daa_offered': daa, 'warning_answered': any(warnings),
            'model_requests': len(model.requests), 'stop_continuations': len(model.script.continuations),
            'resumed_after_no': resumed}


def main():
    assert os.getuid() == 0 and ROOT.is_dir() and HOME.is_dir(), 'Disposable container only'
    assert json.loads((ROOT / 'package-lock.json').read_text())['packages'][
        'node_modules/@anthropic-ai/claude-code-linux-x64']['version'] == '2.1.319'
    OUT.mkdir(parents=True, exist_ok=True)
    print('INTERACTIVE_VERSION ' + run(['/usr/local/bin/claude', '--version']).stdout.strip(), flush=True)
    original = POLICY.read_bytes()
    stub_log = Path('/evidence/stub.txt').open('w')
    stub = subprocess.Popen(['/usr/bin/python3', '-I', str(ROOT / 'stub.py')], stdout=stub_log, stderr=stub_log)
    try:
        deadline = time.monotonic() + 10
        while 'STUB_READY' not in Path('/evidence/stub.txt').read_text():
            assert stub.poll() is None and time.monotonic() < deadline, 'Receiver readiness failed'
            time.sleep(.05)
        cases = [('normal-yes', False, 'none', None, None, 'Yes')]
        for skip in (False, True):
            prefix = 'skip-' if skip else 'normal-'
            cases += [(prefix + 'no', skip, 'none', None, None, 'No')]
            cases += [(prefix + scope, skip, scope, None, None, 'No') for scope in SCOPES]
            cases += [(prefix + 'pre-allow', skip, 'none', 'PreToolUse', 'user', 'No'),
                      (prefix + 'daa', skip, 'none', None, None, 'DAA')]
            cases += [(prefix + 'permission-' + level, skip, 'none', 'PermissionRequest', level, None)
                      for level in ('user', 'managed')]
        summary = []
        for case, skip, scope, event, level, answer in cases:
            # Fresh CLI/config/settings and transcripts per case; only DAA sends
            # 2 and 3 intentionally keep persisted settings from send 1.
            shutil.rmtree(HOME / '.claude/projects', ignore_errors=True)
            put(HOME / '.claude.json', config())
            for path in SCOPES.values():
                put(path, {})
            policy = managed_settings()
            policy['env'] = {'ANTHROPIC_BASE_URL': 'http://127.0.0.1:18081', 'ANTHROPIC_API_KEY': KEY}
            settings = {s: {} for s in SCOPES}
            settings['user'] = {'permissions': {'allow': [PREPARE]}}
            if scope in SCOPES:
                settings[scope].setdefault('permissions', {}).setdefault('allow', []).append(SEND)
            marker = None
            if event:
                entry, marker = make_hook(case, event)
                target = policy if level == 'managed' else settings['user']
                target.setdefault('hooks', {})[event] = [entry]
            POLICY.write_text(json.dumps(policy, indent=2))
            case_out = OUT / case
            case_out.mkdir()
            (case_out / 'managed-settings.json').write_bytes(POLICY.read_bytes())
            for name, path in SCOPES.items():
                put(path, settings[name])
            server = {'type': 'stdio', 'command': '/usr/bin/python3',
                      'args': ['-I', str(ROOT / 'mcp-fixture.py'), 'testapp']}
            run(['/usr/local/bin/claude', 'mcp', 'add-json', '--scope', 'user', 'testapp', json.dumps(server)])
            assert arrivals(case) == 0
            row = {'case': case, 'mode': 'bypassPermissions' if skip else 'default'}
            first = exercise(case, skip, [step(1), step(2)] if answer == 'DAA' else [step(1)],
                             ['DAA', 'No'] if answer == 'DAA' else [answer], event == 'PermissionRequest')
            row.update(first)
            if answer == 'DAA':
                assert arrivals(case) == 1, 'STOP: DAA send 2 escaped the ask'
                third = exercise(case, skip, [step(3)], ['No'])
                row['new_session'] = third
            count = arrivals(case)
            if event != 'PermissionRequest':
                assert count == int(answer in ('Yes', 'DAA')), 'STOP: unexpected receiver arrival: ' + case
            else:
                assert count in (0, 1)
            hook_calls = len(marker.read_text().splitlines()) if marker and marker.exists() else 0
            if event == 'PreToolUse':
                assert hook_calls == 1, (case, hook_calls)
            if marker and marker.exists():
                shutil.copyfile(marker, case_out / 'hook-events.jsonl')
            row.update(send_arrivals=count, hook_calls=hook_calls)
            summary.append(row)
            (OUT / 'summary.json').write_text(json.dumps(summary, indent=2))
            print('INTERACTIVE_CASE_PASS ' + json.dumps(row, sort_keys=True), flush=True)
        observed = {r['case']: {'prompt_shown': r['prompt_shown'][0],
                    'send_arrivals': r['send_arrivals'], 'hook_calls': r['hook_calls']}
                    for r in summary if '-permission-' in r['case']}
        (OUT / 'permission-request.json').write_text(json.dumps(observed, indent=2))
        print('CONTROL_PERMISSION_REQUEST_RECORDED ' + json.dumps(observed, sort_keys=True), flush=True)
        expected = json.loads((ROOT / 'interactive-permission-request-expected.json').read_text())
        assert observed == expected, 'Interactive PermissionRequest pin changed: ' + json.dumps(observed)
        print('CONTROL_INTERACTIVE_ASK_PASS cases=' + str(len(summary)), flush=True)
    finally:
        POLICY.write_bytes(original)
        stub.terminate()
        stub.wait(timeout=10)
        stub_log.close()


if __name__ == '__main__':
    main()
