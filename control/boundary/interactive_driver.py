"""Rendered tmux terminal driver. The caller supplies an owner command runner.

This module has no container paths, identity changes, policy edits or model logic.
Use it unchanged from the future VM supervisor with a runuser-backed runner.
"""
import json
from pathlib import Path
import re
import shlex
import time


OPTIONS = re.compile(r'^\s*[❯>]?\s*(\d+)\.\s+(.+?)\s*$', re.MULTILINE)


def options(screen):
    return [(number, text.strip()) for number, text in OPTIONS.findall(screen)]


def answer_option(screen, answer):
    choices = options(screen)
    if answer == 'Yes':
        matches = [(n, t) for n, t in choices if t == 'Yes']
    elif answer == 'No':
        matches = [(n, t) for n, t in choices if t == 'No']
    elif answer == 'DAA':
        matches = [(n, t) for n, t in choices if t.startswith("Yes, and don't ask again")]
    elif answer == 'warning':
        matches = [(n, t) for n, t in choices if t.startswith('Yes, I accept')]
    else:
        raise AssertionError('Unknown answer: ' + answer)
    assert len(matches) == 1, (answer, choices)
    return matches[0]


def selected_option(screen, number, text):
    return re.search(r'^\s*❯\s*' + re.escape(number) + r'\.\s+' + re.escape(text) + r'\s*$',
                     screen, re.MULTILINE) is not None


class Terminal:
    def __init__(self, run, evidence, socket, cwd, argv, env):
        self.run, self.evidence = run, Path(evidence)
        self.base = ['tmux', '-S', str(socket)]
        self.cwd, self.argv, self.env = cwd, argv, env
        self.sequence = 0
        self.warning = False

    def tmux(self, *args, required=True):
        return self.run([*self.base, *args], env=self.env, required=required)

    def save(self, label, screen):
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.sequence += 1
        path = self.evidence / f'{self.sequence:03}-{label}.txt'
        path.write_text(screen)
        return path.name

    def screen(self):
        result = self.tmux('capture-pane', '-p', '-t', 'case:0.0', required=False)
        assert result.returncode == 0, 'Terminal exited before expected text'
        return result.stdout

    def wait(self, label, predicate, timeout=60, warning=False, expected_options=()):
        deadline = time.monotonic() + timeout
        previous = None
        while time.monotonic() < deadline:
            screen = self.screen()
            if screen != previous:
                self.save('wait-' + label, screen)
                previous = screen
            if warning and 'Yes, I accept' in screen:
                assert not self.warning, 'Repeated bypass-permissions warning'
                self.choose(screen, 'warning')
                self.warning = True
            elif predicate(screen):
                self.save(label, screen)
                return screen
            elif options(screen) and options(screen) != expected_options and not any(
                    t == 'Yes' or t == 'No' for _, t in options(screen)):
                raise AssertionError('Unexpected dialog: ' + screen)
            time.sleep(.1)  # Poll cadence only; named rendered text is the proof.
        self.save('TIMEOUT-' + label, self.screen())
        raise AssertionError('Deadline waiting for ' + label)

    def choose(self, screen, answer):
        number, text = answer_option(screen, answer)
        shot = self.save('answer-' + answer, screen)
        with (self.evidence / 'actions.jsonl').open('a') as log:
            log.write(json.dumps({'screen': shot, 'option': text, 'key': number}) + '\n')
        self.tmux('send-keys', '-t', 'case:0.0', number)
        # Numeric shortcuts can submit immediately, or only move the selection.
        # Observe which happened before sending a confirming Enter.
        choices = options(screen)
        after = self.wait('selected-or-submitted-' + answer,
            lambda s: selected_option(s, number, text) or options(s) != choices,
            expected_options=choices)
        if selected_option(after, number, text):
            self.tmux('send-keys', '-t', 'case:0.0', '-l', '\r')

    def prompt(self, marker):
        self.save('owner-prompt', self.screen())
        self.tmux('send-keys', '-t', 'case:0.0', '-l', marker)
        self.tmux('send-keys', '-t', 'case:0.0', '-l', '\r')

    def __enter__(self):
        self.evidence.mkdir(parents=True, exist_ok=True)
        (self.evidence / 'launch.json').write_text(json.dumps({
            'argv': self.argv, 'cwd': self.cwd, 'width': 120, 'height': 40}, indent=2))
        self.tmux('new-session', '-d', '-s', 'case', '-x', '120', '-y', '40',
                  '-c', self.cwd, shlex.join(self.argv))
        return self

    def __exit__(self, *args):
        result = self.tmux('capture-pane', '-p', '-S', '-200', '-t', 'case:0.0', required=False)
        self.save('final-history', result.stdout + result.stderr)
        self.tmux('kill-server', required=False)
