"""Package 18c, B2 checks 6 and 9, and check 7's send through Claude Code: interactive Claude Code sessions as `ares`
in the booted guest, with the managed files exactly as the image shipped them.

B1's terminal driver and model double (control/boundary/interactive_driver.py and interactive_model.py) run here
unchanged: the driver types into a tmux pane as `ares` through runuser, the double answers on the guest's loopback.
The API address and the synthetic key come from the session's environment, never from the managed settings.
"""
import json
import os
import pathlib
import pwd
import re
import subprocess
import time

from interactive_driver import Terminal, options
from interactive_model import Model

OWNER = pwd.getpwnam('ares')
HOME = pathlib.Path(OWNER.pw_dir)
WORK = HOME / 'ci-work'
CLAUDE = HOME / '.local/bin/claude'
SOCKETS = pathlib.Path('/tmp/aresos-ci-tmux')
HOOK = '/usr/libexec/aresos-ci/control/own-hook.py'
PORT = 18081
KEY = 'SYNTHETIC_GUEST_NONCREDENTIAL'
NORMAL = ['--permission-mode', 'default']
SKIP = ['--dangerously-skip-permissions']
# The managed Stop hook's own timeout (control/settings/managed-hooks.json) plus a margin: a Stop continuation is
# requested within this window after the model's last answer, or not at all.
SETTLE = 20
# Not ~/.local/bin (the CI layer's exit-97 stand-ins live there); Claude Code is called by its full path.
ENV = {'HOME': str(HOME), 'USER': 'ares', 'LOGNAME': 'ares', 'TERM': 'xterm-256color', 'LANG': 'C.UTF-8',
       'PATH': '/usr/local/bin:/usr/bin:/usr/sbin', 'DISABLE_AUTOUPDATER': '1',
       'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'CLAUDE_CODE_AUTO_CONNECT_IDE': 'false',
       'ENABLE_TOOL_SEARCH': 'false', 'ANTHROPIC_BASE_URL': f'http://127.0.0.1:{PORT}', 'ANTHROPIC_API_KEY': KEY}


def owner_run(args, env=None, required=True, timeout=30):
    """The driver's runner: every tmux call runs as ares with the session environment only."""
    result = subprocess.run(['runuser', '-u', 'ares', '--', 'env', '-i',
                             *[f'{key}={value}' for key, value in (env or ENV).items()], *args],
                            capture_output=True, text=True, timeout=timeout, cwd=WORK)
    if required:
        assert result.returncode == 0, (args, result.stdout[-2000:], result.stderr[-2000:])
    return result


def owned(path):
    os.chown(path, OWNER.pw_uid, OWNER.pw_gid)


def put(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    owned(path.parent)
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')
    os.chmod(path, 0o600)
    owned(path)


def prepare_home():
    """First-run state as 18d's precedence.py seeds it: onboarding done, the synthetic key approved, the work folder
    trusted. ~/.claude.json keeps what check 5 put there (his server, ours, testapp)."""
    WORK.mkdir(exist_ok=True)
    owned(WORK)
    SOCKETS.mkdir(mode=0o700, exist_ok=True)
    owned(SOCKETS)
    path = HOME / '.claude.json'
    config = json.loads(path.read_text())
    config.update(hasCompletedOnboarding=True, theme='dark')
    approved = config.setdefault('customApiKeyResponses', {}).setdefault('approved', [])
    if KEY[-20:] not in approved:
        approved.append(KEY[-20:])
    config.setdefault('projects', {}).setdefault(str(WORK), {})['hasTrustDialogAccepted'] = True
    put(path, config)


def user_settings(allow, hooks=None):
    value = {'permissions': {'allow': list(allow)}}
    if hooks:
        value['hooks'] = hooks
    put(HOME / '.claude/settings.json', value)
    return value


def own_hook(event, log, matcher=None):
    entry = {'hooks': [{'type': 'command', 'command': f'/usr/bin/python3 -I {HOOK} {event} {log}'}]}
    return [dict(entry, matcher=matcher) if matcher else entry]


def hook_lines(log):
    return [json.loads(line) for line in pathlib.Path(log).read_text().splitlines()] if pathlib.Path(log).exists() \
        else []


def flat(text):
    return re.sub(r'\s+', ' ', text)


def settle(model, deadline):
    """The turn is over when no model request came for SETTLE seconds after the last one (bounded by deadline)."""
    count, quiet_since = len(model.requests), time.monotonic()
    while time.monotonic() - quiet_since < SETTLE:
        assert time.monotonic() < deadline, 'the turn did not end within its deadline'
        time.sleep(0.5)
        if len(model.requests) != count:
            count, quiet_since = len(model.requests), time.monotonic()


def saved(folder, pattern='*'):
    """The driver's saved screens in order (its numbers grow past three digits in a long session)."""
    found = [(int(path.name.split('-', 1)[0]), path) for path in folder.glob(pattern + '.txt')
             if path.name.split('-', 1)[0].isdigit()]
    return sorted(found)


def ours_on_screen(folder, first, last):
    """Lines of the screens saved during one turn that show our hooks or our name."""
    lines = []
    for number, path in saved(folder):
        if first < number <= last:
            for line in path.read_text().splitlines():
                line = line.strip()
                if ('AresOS' in line or 'hook' in line.lower()) and line not in lines:
                    lines.append(line)
    return lines


def session(evidence, steps, flags, answers, before_turn=None, turn_seconds=180):
    """One fresh claude as ares. answers[i]: None (no prompt may show), 'Yes' or 'No' (the managed ask must show
    and gets that answer), or 'hook' (a PermissionRequest hook may flash the prompt; never answered)."""
    evidence.mkdir(parents=True, exist_ok=True)
    screens = evidence / 'screens'
    turns = []
    with Model(steps, evidence / 'model', port=PORT) as model:
        argv = [str(CLAUDE), *flags, steps[0]['prompt']]
        with Terminal(owner_run, screens, SOCKETS / 'session.sock', str(WORK), argv, ENV) as terminal:
            for index, (step, answer) in enumerate(zip(steps, answers)):
                if before_turn:
                    before_turn(index)
                first_screen, first_request = terminal.sequence, len(model.requests)
                first_continuation = len(model.script.continuations)
                began = time.monotonic()
                deadline = began + turn_seconds
                if index:
                    terminal.prompt(step['prompt'])
                done = f'INTERACTIVE_DONE_{index + 1}'
                seen = []

                def ready(screen):
                    if any(text == 'Yes' for _, text in options(screen)):
                        seen.append(terminal.sequence)
                        return answer != 'hook'
                    return done in screen
                screen = terminal.wait(f'prompt-or-done-{index + 1}', ready, timeout=turn_seconds,
                                       warning=flags == SKIP)
                question = None
                if answer in ('Yes', 'No'):
                    assert seen and done not in screen, f'STOP: the managed ask did not ask ({evidence.name})'
                    terminal.choose(screen, answer)
                elif answer is None:
                    assert not seen, f'a permission prompt in a turn that needs none ({evidence.name}): {screen}'
                completed = terminal.wait(f'completed-or-interrupted-{index + 1}',
                                          lambda s: done in s or 'Interrupted · What should Claude do instead?' in s,
                                          timeout=turn_seconds)
                resumed = done not in completed
                if resumed:
                    # B1: a native No interrupts the turn; this marker (no scripted step) lets the denied result reach
                    # the model without another send.
                    terminal.prompt('INTERACTIVE_RESUME_CURRENT_TURN')
                    terminal.wait(f'completed-{index + 1}', lambda s: done in s, timeout=turn_seconds)
                settle(model, deadline)
                terminal.save(f'settled-{index + 1}', terminal.screen())
                assert model.error is None, model.error
                if step.get('prepare'):
                    prepared = model.script.results.get(f'prepare-{index}')
                    approval = json.loads(next(block['text'] for block in prepared['content']
                                               if block.get('text', '').startswith('{')))['data']['approval']
                    question = approval['question']
                    if answer in ('Yes', 'No'):
                        asked = next(path for number, path in saved(screens, f'*-answer-{answer}')
                                     if number > first_screen).read_text()
                        position = flat(asked).find(flat(question)[:40])
                        assert position >= 0, ('the service question is not on the prompt', question)
                        for key in ('operation_id', 'description'):
                            assert position < flat(asked).find(key) or key not in asked, ('question not first', key)
                else:
                    approval = None
                result = model.script.results.get(f'send-{index}')
                turns.append(dict(prompt=step['prompt'], answer=answer, prompt_shown=bool(seen),
                                  resumed_after_no=resumed, seconds=round(time.monotonic() - began, 1),
                                  model_requests=len(model.requests) - first_request,
                                  stop_continuations=len(model.script.continuations) - first_continuation,
                                  operation_id=approval and approval.get('operation_id'), question=question,
                                  tool_result=result, on_screen=ours_on_screen(screens, first_screen,
                                                                               terminal.sequence)))
                (evidence / 'turns.json').write_text(json.dumps(turns, indent=2) + '\n')
            final = terminal.screen()
    actions = screens / 'actions.jsonl'
    answered = [json.loads(line) for line in actions.read_text().splitlines()] if actions.exists() else []
    owner_answers = sum(1 for action in answered if action['option'] in ('Yes', 'No'))
    continuations = model.script.continuations
    return dict(turns=turns, owner_answers=owner_answers, model_requests=len(model.requests),
                continuations=continuations, warning_answered=terminal.warning, final_screen=final)


def transcripts(target):
    """Claude Code's own transcripts of this check, copied as they are."""
    source = HOME / '.claude/projects'
    copied = []
    for path in sorted(source.rglob('*.jsonl')) if source.exists() else []:
        assert path.stat().st_size < 5_000_000, path
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
        copied.append(str(path.relative_to(source)))
    return copied
