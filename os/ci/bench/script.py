"""Read a bench script from the dispatched commit and validate its steps."""
import hashlib
import json
import os
import pathlib
import re
import subprocess

PATH = re.compile(r'reviews/[a-z0-9][a-z0-9_-]*/bench/[a-z0-9][a-z0-9_-]*\.json')
SHA = re.compile(r'[0-9a-f]{40}')
CHECKS = {'active_session', 'helper_health'}
KINDS = {'status', 'shot', 'journal', 'exec', 'wait', 'expect', 'reboot'}
MAX_STEPS = 32
MAX_SCRIPT = 32 * 1024
BOOLEAN_CONFLICTS = ('release_13', 'release_27', 'release_28', 'dry_run_28', 'checks_only', 'full_model')
STRING_CONFLICTS = ('rehearsal', 'switch_from_run', 'probe_run')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', repo, *args], stderr=subprocess.DEVNULL)


def validate_dispatch(event, mode):
    inputs = event.get('inputs', {})
    if inputs.get('check_build') != mode or mode != 'bench':
        raise ValueError('Bench requires a bench dispatch')
    if (any(inputs.get(name) not in (None, '', False, 'false') for name in BOOLEAN_CONFLICTS)
            or any(inputs.get(name) not in (None, '') for name in STRING_CONFLICTS)):
        raise ValueError('Bench dispatch must be exclusive')


def parse(raw):
    if len(raw) > MAX_SCRIPT:
        raise ValueError('Bench script exceeds size limit')

    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError('Duplicate script key')
        return result

    script = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(script, dict) or not script.keys() <= {'network', 'steps'} or script.get('network', 'none') != 'none':
        raise ValueError('Bench script must use network none')
    steps = script.get('steps')
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError('Invalid step count')
    for step in steps:
        kind = step.get('kind') if isinstance(step, dict) else None
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError('Invalid step kind')
        fields = {'kind'}
        if kind in ('wait', 'expect'):
            fields.add('for')
            if not isinstance(step.get('for'), str) or step['for'] not in CHECKS:
                raise ValueError('Unknown session check')
        if kind == 'exec':
            fields.add('argv')
            argv = step.get('argv')
            if (not isinstance(argv, list) or not 1 <= len(argv) <= 32
                    or not all(isinstance(arg, str) and '\0' not in arg and len(arg) <= 4096 for arg in argv)
                    or not argv[0]):
                raise ValueError('Invalid exec argv')
        if step.keys() != fields:
            raise ValueError('Unexpected step fields')
    if sum(step['kind'] == 'reboot' for step in steps) > 1:
        raise ValueError('Bench allows one reboot per dispatch')
    return steps


def load(repo, sha, name):
    if not SHA.fullmatch(sha) or not PATH.fullmatch(name) or git(repo, 'rev-parse', 'HEAD').decode().strip() != sha:
        raise ValueError('Invalid bench path or head')
    entry = git(repo, 'ls-tree', sha, '--', name)
    if not entry.startswith((b'100644 blob ', b'100755 blob ')):
        raise ValueError('Bench script must be a regular file in the dispatched commit')
    blob = f'{sha}:{name}'
    if int(git(repo, 'cat-file', '-s', blob)) > MAX_SCRIPT:
        raise ValueError('Bench script exceeds size limit')
    raw = git(repo, 'cat-file', 'blob', blob)
    return parse(raw), hashlib.sha256(raw).hexdigest()


def dispatch():
    if (os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or os.environ.get('GITHUB_JOB') != 'check-build'):
        raise ValueError('Bench runs only in hosted dispatches')
    event = json.loads(pathlib.Path(os.environ['GITHUB_EVENT_PATH']).read_bytes())
    validate_dispatch(event, 'bench')
    sha, name = os.environ['GITHUB_SHA'], os.environ['BENCH_SCRIPT']
    if event['inputs'].get('bench_script') != name:
        raise ValueError('Bench script input differs from dispatch')
    steps, digest = load('.', sha, name)
    return steps, dict(head_sha=sha, script=name, script_sha256=digest, network='none')


if __name__ == '__main__':
    try:
        dispatch()
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError):
        raise SystemExit('Bench dispatch refused (incompatible inputs or invalid script at dispatched head)') from None
    print('Bench dispatch validated')
