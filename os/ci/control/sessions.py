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
from interactive_model import Model, texts

OWNER = pwd.getpwnam('ares')
HOME = pathlib.Path(OWNER.pw_dir)
WORK = HOME / 'ci-work'
CLAUDE = HOME / '.local/bin/claude'
SOCKETS = pathlib.Path('/tmp/aresos-ci-tmux')
HOOK = '/usr/libexec/aresos-ci/control/own-hook.py'
PORT = 18081
KEY = 'SYNTHETIC_GUEST_NONCREDENTIAL'
NORMAL = ['--permission-mode', 'default']
# B1: a native No interrupts the turn; this owner prompt (no scripted step's marker) lets the denied result reach the
# model without another send. It belongs to the turn it resumes.
RESUME = 'INTERACTIVE_RESUME_CURRENT_TURN'
SKIP = ['--dangerously-skip-permissions']
# The managed Stop hook's own timeout (control/settings/managed-hooks.json) plus a margin: a Stop continuation is
# requested within this window after the model's last answer, or not at all. A session's last turn waits this long:
# nothing after it would see a late continuation.
SETTLE = 20
# A turn that another turn of the same session follows. The managed hooks make one connect attempt and end at once
# (18e; check 6 times them directly, under a second), and a continuation later than this would land in the next
# turn's count and fail that turn, never pass unseen.
SETTLE_NEXT = 10
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


def squeeze(text):
    """Text without whitespace or box-drawing characters: Claude Code wraps a long question inside its prompt's
    border, so the full question is compared with both removed (seen in run 45011020590's C8 screens)."""
    return re.sub(r'[\s\u2500-\u257f]+', '', text)


def question_position(screen, question):
    """Where the whole service question starts on the prompt screen, or -1 if any of it is missing."""
    return squeeze(screen).find(squeeze(question)) if squeeze(question) else -1


def settle(model, deadline, seconds=SETTLE):
    """The turn is over when no model request came for `seconds` after the last one (bounded by deadline). Returns
    when the last request was seen."""
    count, quiet_since = len(model.requests), time.monotonic()
    while time.monotonic() - quiet_since < seconds:
        assert time.monotonic() < deadline, 'the turn did not end within its deadline'
        time.sleep(0.5)
        if len(model.requests) != count:
            count, quiet_since = len(model.requests), time.monotonic()
    return quiet_since


def last_user_text(messages, limit=600):
    """The newest user message of a request as text (a Stop continuation carries the hook's reason there)."""
    users = [message for message in messages if message.get('role') == 'user']
    content = users[-1].get('content') if users else ''
    if isinstance(content, list):
        content = ' '.join(block.get('text') or json.dumps(block.get('content', '')) for block in content
                           if isinstance(block, dict))
    return flat(str(content))[-limit:]


def saved(folder, pattern='*'):
    """The driver's saved screens in order (its numbers grow past three digits in a long session)."""
    found = [(int(path.name.split('-', 1)[0]), path) for path in folder.glob(pattern + '.txt')
             if path.name.split('-', 1)[0].isdigit()]
    return sorted(found)


def ours_on_screen(folder, first, last, prompt):
    """Lines of the screens saved during one turn that show our hooks or our name. A screen still shows the earlier
    turns above this turn's prompt (run 43572578699: turn 2's reminder counted again in turns 3 and 5), so only the
    lines from the first one holding the prompt on count. Screens before the prompt shows (the driver saves one
    before typing it) are the previous turn's; once it has shown, a screen without it has scrolled past it."""
    lines, shown = [], False
    for number, path in saved(folder):
        if first < number <= last:
            screen = path.read_text().splitlines()
            start = next((index for index, line in enumerate(screen) if prompt in line), None)
            if start is None and not shown:
                continue
            shown = True
            for line in screen[start or 0:]:
                line = line.strip()
                if ('AresOS' in line or 'hook' in line.lower()) and line not in lines:
                    lines.append(line)
    return lines


def session(evidence, steps, flags, answers, before_turn=None, turn_seconds=180, *,
            model_factory=Model, before_answer=None, terminal_height=None):
    """One fresh claude as ares. answers[i]: None (no prompt may show), 'Yes' or 'No' (the managed ask must show
    and gets that answer), or 'hook' (a PermissionRequest hook may flash the prompt; never answered)."""
    evidence.mkdir(parents=True, exist_ok=True)
    screens = evidence / 'screens'
    turns = []
    with model_factory(steps, evidence / 'model', port=PORT) as model:
        argv = [str(CLAUDE), *flags, steps[0]['prompt']]
        with Terminal(owner_run, screens, SOCKETS / 'session.sock', str(WORK), argv, ENV) as terminal:
            if terminal_height is not None:
                # The Chrome approval shows a form binding whose details push the question out of 40 rows.
                terminal.tmux('resize-window', '-t', 'case:0', '-y', str(terminal_height))
                launch = screens / 'launch.json'
                launch.write_text(json.dumps(dict(json.loads(launch.read_text()), height=terminal_height), indent=2))
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
                    assert model.error is None, model.error
                    if any(text == 'Yes' for _, text in options(screen)):
                        seen.append(terminal.sequence)
                        return answer != 'hook'
                    return done in screen
                screen = terminal.wait(f'prompt-or-done-{index + 1}', ready, timeout=turn_seconds,
                                       warning=flags == SKIP)
                question = None
                if answer in ('Yes', 'No'):
                    assert seen and done not in screen, f'STOP: the managed ask did not ask ({evidence.name})'
                    if before_answer:
                        before_answer()
                    terminal.choose(screen, answer)
                elif answer is None:
                    assert not seen, f'a permission prompt in a turn that needs none ({evidence.name}): {screen}'
                completed = terminal.wait(f'completed-or-interrupted-{index + 1}',
                                          lambda s: done in s or 'Interrupted · What should Claude do instead?' in s,
                                          timeout=turn_seconds)
                resumed = done not in completed
                if resumed:
                    terminal.prompt(RESUME)
                    terminal.wait(f'completed-{index + 1}', lambda s: done in s, timeout=turn_seconds)
                last_request = settle(model, deadline, SETTLE if index == len(steps) - 1 else SETTLE_NEXT)
                terminal.save(f'settled-{index + 1}', terminal.screen())
                assert model.error is None, model.error
                if step.get('prepare'):
                    approval = model.script.prepared_approval(index)
                    question = approval['question']
                    if answer in ('Yes', 'No'):
                        asked = next(path for number, path in saved(screens, f'*-answer-{answer}')
                                     if number > first_screen).read_text()
                        # The whole question, not a prefix: what Yes authorizes must be on the screen (C8).
                        position = question_position(asked, question)
                        assert position >= 0, ('the full service question is not on the prompt', question)
                        for key in ('operation_id', 'description'):
                            assert position < squeeze(asked).find(key) or key not in asked, ('question not first', key)
                else:
                    approval = None
                result = model.script.results.get(f'send-{index}')
                turns.append(dict(prompt=step['prompt'], answer=answer, prompt_shown=bool(seen),
                                  resumed_after_no=resumed, seconds=round(time.monotonic() - began, 1),
                                  # From the turn's start to its last model request (the quiet window not counted).
                                  active_seconds=round(last_request - began, 1),
                                  model_requests=len(model.requests) - first_request,
                                  stop_continuations=len(model.script.continuations) - first_continuation,
                                  continuation_tails=[last_user_text(item['messages']) for item in
                                                      model.script.continuations[first_continuation:]],
                                  operation_id=approval and approval.get('operation_id'), question=question,
                                  tool_result=result, on_screen=ours_on_screen(screens, first_screen,
                                                                               terminal.sequence, step['prompt'])))
                (evidence / 'turns.json').write_text(json.dumps(turns, indent=2) + '\n')
            final = terminal.screen()
    actions = screens / 'actions.jsonl'
    answered = [json.loads(line) for line in actions.read_text().splitlines()] if actions.exists() else []
    owner_answers = sum(1 for action in answered if action['option'] in ('Yes', 'No'))
    continuations = model.script.continuations
    # The tools Claude Code offered the model (tool search is off here, so every one is listed). It doesn't wait for
    # the MCP servers: run 43669126392's first request carried only the built-in tools and his own fast server, so
    # the record is per request (tools per server) and the list is the last request's, when every server is up.
    offered = [request['tools'] for request in model.requests if isinstance(request.get('tools'), list)]
    return dict(turns=turns, owner_answers=owner_answers, model_requests=len(model.requests),
                continuations=continuations, warning_answered=terminal.warning, final_screen=final,
                tools_per_request=[tools_per_server(tools) for tools in offered],
                tools_offered=sorted(tool.get('name', '') for tool in (offered[-1] if offered else [])))


def tools_per_server(tools):
    counts = {}
    for tool in tools:
        name = tool.get('name', '')
        server = name.split('__')[1] if name.startswith('mcp__') else 'built-in'
        counts[server] = counts.get(server, 0) + 1
    return counts


TRANSCRIPTS = HOME / '.claude/projects'


def transcript_files():
    """Claude Code's own transcripts now: path under ~/.claude/projects → (size, mtime_ns)."""
    found = {}
    for path in TRANSCRIPTS.rglob('*.jsonl') if TRANSCRIPTS.exists() else []:
        status = path.stat()
        found[str(path.relative_to(TRANSCRIPTS))] = (status.st_size, status.st_mtime_ns)
    return found


def transcripts(target, before):
    """The transcripts written or changed since `before` (transcript_files()), copied as they are."""
    copied = []
    for name, state in sorted(transcript_files().items()):
        if before.get(name) == state:
            continue
        assert state[0] < 5_000_000, (name, state)
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((TRANSCRIPTS / name).read_bytes())
        copied.append(dict(name=name, bytes=state[0]))
    return copied
