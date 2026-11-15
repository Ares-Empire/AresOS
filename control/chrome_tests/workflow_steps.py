"""Workflow structure for the browser-free tests, and a runner for single run: steps.

A careful matcher, not a YAML library: PyYAML is not a dependency of the test
environment. It follows the block structure by indentation (a "- " list item
opens a new mapping) and joins every value's continuation lines, so a key is
found however it is written: as a step's first key ("- if: ..."), with a block
scalar ("if: >-" and the condition below), on the next line ("if:" then the
value), or as a plain scalar that continues on deeper lines.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap

KEY = re.compile(r'''(?:(['"])(?P<quoted>[A-Za-z0-9_.\-]+)\1|(?P<plain>[A-Za-z0-9_][A-Za-z0-9_.\-]*))[ \t]*:(?:[ \t]+(?P<value>.*?))?[ \t]*''')
BLOCK_SCALAR = re.compile(r'[|>][-+0-9]*(?:[ \t]+#.*)?')


def _indentation(line):
    return len(line) - len(line.lstrip(' '))


def workflow_structure(source):
    """({job: [(key, value)]}, [{'job', 'name', 'keys': [(key, value)]}]) for every job and step.

    Keys below a job or a step are dotted paths ('if', 'run', 'env.GH_TOKEN',
    'concurrency.group'); values are whole: a literal block is dedented, a
    folded block, a plain scalar and its continuations are joined by spaces.
    """
    lines = source.split('\n')
    index = lines.index('jobs:') + 1
    jobs, steps, stack, current = {}, [], [], None

    def deeper(start, column):
        # The end of every following line that is blank or deeper than column.
        end = position = start
        while position < len(lines) and (not lines[position].strip() or _indentation(lines[position]) > column):
            position += 1
            if lines[position - 1].strip():
                end = position
        return end

    def record(path, value):
        # Files a key under its job or its step; the [key, value] entry stays
        # mutable so a value on the following line can still be filled in.
        entry = None
        if len(path) == 1:
            jobs.setdefault(path[0], [])
        elif len(path) >= 4 and path[1] == 'steps' and path[2] == '-':
            entry = ['.'.join(path[3:]), value]
            current['keys'].append(entry)
        elif path[1] != 'steps':
            entry = ['.'.join(path[1:]), value]
            jobs.setdefault(path[0], []).append(entry)
        return entry

    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith('#'):
            index += 1
            continue
        column = _indentation(line)
        if column == 0:
            break
        text = line[column:]
        dashes = []
        while text == '-' or text.startswith('- '):
            dashes.append(column)
            rest = text[1:]
            column += 1 + _indentation(rest)
            text = rest.lstrip(' ')
        for dash in dashes:
            while stack and stack[-1][0] >= dash:
                stack.pop()
            stack.append([dash, '-', None])
            path = [key for _, key, _ in stack]
            if len(path) == 3 and path[1] == 'steps':
                current = {'job': path[0], 'keys': []}
                steps.append(current)
        if not text:
            index += 1
            continue
        found = KEY.fullmatch(text)
        if not found:
            # A scalar on its own line is the value of the key above it
            # ("if:" then the condition below), with its continuation lines.
            owner = stack[-1] if stack and not dashes else None
            if owner is not None and owner[1] != '-' and owner[2] is not None and not owner[2][1]:
                end = deeper(index + 1, owner[0])
                owner[2][1] = ' '.join(part.strip() for part in lines[index:end] if part.strip())
                stack.pop()
                index = end
            else:
                index += 1
            continue
        key, value = found['quoted'] or found['plain'], found['value'] or ''
        if value.startswith('#'):
            value = ''
        while stack and stack[-1][0] >= column:
            stack.pop()
        path = [name for _, name, _ in stack] + [key]
        if BLOCK_SCALAR.fullmatch(value):
            end = deeper(index + 1, column)
            body = textwrap.dedent('\n'.join(lines[index + 1:end]))
            record(path, body if value.startswith('|') else ' '.join(part.strip() for part in body.split('\n') if part.strip()))
            index = end
        elif value:
            end = deeper(index + 1, column)
            record(path, ' '.join([value] + [part.strip() for part in lines[index + 1:end] if part.strip()]))
            index = end
        else:
            stack.append([column, key, record(path, '')])
            index += 1
    for step in steps:
        names = [value for key, value in step['keys'] if key == 'name']
        step['name'] = names[0] if names else None
        step['keys'] = [tuple(pair) for pair in step['keys']]
    return {job: [tuple(pair) for pair in keys] for job, keys in jobs.items()}, steps


def workflow_conditions(source):
    """(job, step name or None, condition) for every job-level and step-level if:, whitespace folded."""
    jobs, steps = workflow_structure(source)
    rows = [(job, None, ' '.join(value.split())) for job, keys in jobs.items() for key, value in keys if key == 'if']
    rows += [(step['job'], step['name'] or '<unnamed>', ' '.join(value.split()))
             for step in steps for key, value in step['keys'] if key == 'if']
    return rows


def workflow_runs(source):
    """(job, step name, run body) for every step's run:, however it is written."""
    _, steps = workflow_structure(source)
    return [(step['job'], step['name'] or '<unnamed>', value) for step in steps for key, value in step['keys'] if key == 'run']


def workflow_step(source, name):
    """The one step with this name, as a dict of its keys."""
    _, steps = workflow_structure(source)
    found = [dict(step['keys']) for step in steps if step['name'] == name]
    if len(found) != 1:
        raise AssertionError(f'{len(found)} steps named {name!r}')
    return found[0]


FAKE_GH = '''#!{python}
"""Stand-in gh: logs each call; answers --version, attestation verify and api from FAKE_GH_API."""
import hashlib, json, os, sys
from pathlib import Path
arguments = sys.argv[1:]
log = Path(os.environ['FAKE_GH_LOG'])
entry = {{'argv': arguments, 'token': bool(os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN'))}}
if arguments[:2] == ['attestation', 'verify']:
    entry['subject_sha256'] = hashlib.sha256(Path(arguments[2]).read_bytes()).hexdigest()
with log.open('a') as stream:
    stream.write(json.dumps(entry) + '\\n')
if arguments == ['--version']:
    print('gh version 2.102.0 (fixture)')
    sys.exit(0)
if arguments[:2] == ['attestation', 'verify']:
    sys.exit(0)
if arguments[:1] == ['api']:
    answers = json.loads(os.environ.get('FAKE_GH_API', '[]'))
    calls = sum(1 for line in log.read_text().splitlines() if json.loads(line)['argv'][:1] == ['api'])
    if calls > len(answers):
        sys.stderr.write('fixture gh: no recorded answer for this call\\n')
        sys.exit(1)
    answer = answers[calls - 1]
    sys.stdout.write(answer.get('stdout', ''))
    sys.stderr.write(answer.get('stderr', ''))
    sys.exit(answer.get('code', 0))
sys.stderr.write('fixture gh: unexpected command ' + ' '.join(arguments) + '\\n')
sys.exit(2)
'''

FAKE_SLEEP = '''#!/bin/sh
echo "$*" >> "$FAKE_SLEEP_LOG"
'''

# The only expressions a tested step's env may use, and their stand-ins.
EXPRESSIONS = {'${{ github.token }}': 'fixture-token'}


class StepRunner:
    """Runs one workflow step's run: body with bash -e, as a hosted runner does, offline.

    gh and sleep are stand-ins on PATH; the step's own env: block is applied,
    each expression replaced by its stand-in, so a token the step declares
    (or does not) reaches the stand-in gh exactly so.
    """

    def __init__(self, directory, workflow):
        self.directory, self.source = Path(directory), Path(workflow).read_text()
        self.bin = self.directory/'fixture-bin'
        self.bin.mkdir(parents=True, exist_ok=True)
        (self.bin/'gh').write_text(FAKE_GH.format(python=sys.executable))
        (self.bin/'sleep').write_text(FAKE_SLEEP)
        for tool in ['gh', 'sleep']:
            (self.bin/tool).chmod(0o755)
        python = self.bin/'python3'
        if not python.exists():
            python.symlink_to(sys.executable)
        self.gh_log, self.sleep_log = self.directory/'gh-calls.jsonl', self.directory/'sleep-calls.txt'

    def run(self, name, cwd, expressions=None, environment=None, api=()):
        step = workflow_step(self.source, name)
        known = {**EXPRESSIONS, **(expressions or {})}
        declared = {}
        for key, value in step.items():
            if key.startswith('env.'):
                if value.startswith('${{') and value not in known:
                    raise AssertionError('No stand-in for ' + value)
                declared[key[4:]] = known.get(value, value)
        for log in [self.gh_log, self.sleep_log]:
            log.write_text('')
        script = self.directory/'step.sh'
        script.write_text(step['run'] + '\n')
        env = {'PATH': os.pathsep.join([str(self.bin), '/usr/bin', '/bin', '/usr/sbin', '/sbin']),
               'HOME': str(self.directory), 'LANG': 'C.UTF-8', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
               'FAKE_GH_LOG': str(self.gh_log), 'FAKE_SLEEP_LOG': str(self.sleep_log), 'FAKE_GH_API': json.dumps(list(api)),
               **(environment or {}), **declared}
        return subprocess.run(['bash', '-e', str(script)], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)

    def gh_calls(self):
        return [json.loads(line) for line in self.gh_log.read_text().splitlines()]

    def sleeps(self):
        return self.sleep_log.read_text().split()
