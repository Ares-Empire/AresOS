"""Audit the closed set of job-token REST calls, including imported CI helpers.

Actions run/jobs/artifact GETs require actions:read. The org package GET uses
packages:read, already qualified in package13's frozen job_token_read record.
Billing is scheduling-only; its caller must remain behind `not ci`.
Unknown endpoints, dynamic entry points and writes need a reviewed mapping.
"""
import ast
import collections
import copy
import json
import pathlib
import re
import shlex
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/os-image.yml'


def python_api_commands(text):
    tree = ast.parse(text)
    commands = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not re.search(r'\bgh\s+api\b', node.value), 'Unreviewed Python shell API command'
        if isinstance(node, ast.List) and len(node.elts) >= 2:
            if [ast.literal_eval(n) if isinstance(n, ast.Constant) else None for n in node.elts[:2]] == ['gh', 'api']:
                commands.append(ast.unparse(node))
    return commands


def shell_api_permissions(text):
    required = set()
    for line in text.splitlines():
        if not re.search(r'\bgh\s+api\b', line):
            continue
        words = shlex.split(line)
        offset = words.index('gh')
        assert words[offset + 1] == 'api'
        endpoint = words[offset + 2]
        assert endpoint == 'orgs/Ares-Empire/packages/container/aresos', 'Unreviewed shell API endpoint'
        assert not any(w in ('-f', '-F', '--field', '--raw-field', '--input', '-X', '--method')
                       or w.startswith(('--field=', '--raw-field=', '--input=', '--method=')) for w in words), 'Unreviewed API write/method'
        required.add('packages')
    return required


def api_requirements(sources):
    # Every Python gh-api construction is inventoried, not just the verifier.
    expected = {
        'verify_release.py': ["['gh', 'api', f'repos/{repository}/actions/runs/{run_id}{suffix}']"],
        'registry_auth.py': ["['gh', 'api', 'orgs/Ares-Empire/packages/container/aresos']"],
        'rehearsal_guard.py': ["['gh', 'api', '--method', 'GET', path]"],
    }
    actual = {name: calls for name, text in sources.items() if name.endswith('.py')
              and (calls := python_api_commands(text))}
    normalize = lambda rows: {name: [ast.dump(ast.parse(expr, mode='eval').body) for expr in values]
                              for name, values in rows.items()}
    assert normalize(actual) == normalize(expected), 'Unreviewed Python gh-api construction'
    verifier = ast.parse(sources['verify_release.py'])
    suffixes = [ast.literal_eval(n.args[0]) for n in ast.walk(verifier)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'api']
    assert suffixes == ['', '/jobs?per_page=100'], 'Unreviewed release API suffix'
    guard = ast.parse(sources['rehearsal_guard.py'])
    # Resolve the generic GET wrapper's entire call inventory. This deliberately
    # fails on an extra caller, endpoint or expression rather than guessing.
    calls = collections.Counter((n.func.id, ast.unparse(n.args[0])) for n in ast.walk(guard)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ('api', 'read_only'))
    expected_calls = collections.Counter({
        ('read_only', 'path'): 1,  # organization_budget, never the CI path
        ('read_only', 'budget_path'): 1,  # same host-only organization_budget
        ('read_only', "f'repos/{REPOSITORY}/{path}'"): 2,
        ('read_only', 'f"repos/{REPOSITORY}/actions/artifacts/{artifact[\'id\']}/zip"'): 1,
        ('api', 'RUN_HISTORY_PATH'): 1,
        ('api', 'f"actions/runs/{run[\'id\']}/jobs?per_page=100"'): 2,
        ('api', "'actions/runs/' + str(probes[0]['run'])"): 1,
        ('api', "'actions/runs/' + current"): 1,
        ('api', "'actions/runs/' + probe_id"): 1,
        ('api', "f'actions/runs/{probe_id}/artifacts'"): 1,
    })
    canonical = lambda rows: collections.Counter({(name, ast.dump(ast.parse(expr, mode='eval').body)): count
                                                  for (name, expr), count in rows.items()})
    assert canonical(calls) == canonical(expected_calls), 'Unreviewed guard GET caller'
    history, = [n.value for n in guard.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'RUN_HISTORY_PATH' for t in n.targets)]
    assert ast.dump(history) == ast.dump(ast.parse("f'actions/runs?branch={BRANCH}&per_page=100'", mode='eval').body)
    billing_calls = [n for n in ast.walk(guard) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == 'organization_budget']
    host_only, = [n for n in ast.walk(guard) if isinstance(n, ast.If)
                  and ast.dump(n.test) == ast.dump(ast.parse("PACKAGE in ('13', '14', '16', '27') and not ci", mode="eval").body)]
    assert len(billing_calls) == 1 and billing_calls[0] in list(ast.walk(host_only)), 'Billing must stay outside CI'
    billing, = [n for n in guard.body if isinstance(n, ast.FunctionDef) and n.name == 'organization_budget']
    budget_get, = [n for n in ast.walk(guard) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                  and n.func.id == 'read_only' and ast.unparse(n.args[0]) == 'budget_path']
    assert budget_get in list(ast.walk(billing)), 'Budget GET must stay in host-only billing helper'
    result = {'verify_release.py': {'actions'}, 'registry_auth.py': {'packages'},
              'rehearsal_guard.py': {'actions'}}
    for name, text in sources.items():
        if name.endswith('.sh'):
            result[name] = shell_api_permissions(text)
    return result


def reachable(text, sources):
    # Conservative closure: imports and literal repo script references, even in
    # non-taken branches, count. No endpoint is excused on an input condition.
    seen, pending = set(), [text]
    while pending:
        current = pending.pop()
        references = set(re.findall(r'os/ci/([\w-]+\.(?:py|sh))', current))
        for module in re.findall(r'^\s*(?:from|import)\s+([\w_]+)', current, re.M):
            references.add(module + '.py')
        for name in references.intersection(sources):
            if name not in seen:
                seen.add(name); pending.append(sources[name])
    return seen


def audit(workflow, sources):
    requirements = api_requirements(sources)
    seen = set()
    for name, job in workflow['jobs'].items():
        runs = '\n'.join(step.get('run', '') for step in job['steps'])
        paths = reachable(runs, sources)
        seen.update(paths)
        needed = shell_api_permissions(runs)
        for path in paths:
            needed.update(requirements.get(path, set()))
        permissions = job.get('permissions', workflow.get('permissions', {}))
        assert isinstance(permissions, dict), 'Explicit job permissions required'
        for permission in needed | {'contents'}:
            assert permissions.get(permission) in ('read', 'write'), f'{name}: missing {permission}: read'
        if 'verify_release.py' in paths:
            checkout, = [step for step in job['steps'] if step.get('uses', '').startswith('actions/checkout@')]
            assert str(checkout.get('with', {}).get('fetch-depth')) == '0', f'{name}: verifier needs full history'
    assert set(requirements).intersection({'verify_release.py', 'registry_auth.py', 'rehearsal_guard.py', 'publish.sh'}) <= seen


class CiApiPermissionsTest(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
        self.sources = {p.name: p.read_text() for p in (ROOT / 'os/ci').rglob('*') if p.suffix in ('.py', '.sh')}

    def test_all_remaining_ci_calls_have_declared_permissions_and_history(self):
        record = json.loads((ROOT / 'os/manifest/release.json').read_text())
        self.assertEqual(record['job_token_read']['status'], 'passed')
        self.assertFalse(record['job_token_read']['owner_token_used'])
        audit(self.workflow, self.sources)

    def test_missing_job_permissions_fail_closed(self):
        for job, permission in (('regressions', 'packages'), ('image', 'actions'),
                                ('switch', 'actions'), ('rehearsal', 'packages'), ('rehearsal', 'actions')):
            changed = copy.deepcopy(self.workflow); changed['jobs'][job]['permissions'].pop(permission)
            with self.subTest(job=job, permission=permission), self.assertRaisesRegex(AssertionError, 'missing'):
                audit(changed, self.sources)

    def test_shallow_checkout_in_either_verifier_job_refuses(self):
        for job in ('switch', 'rehearsal'):
            changed = copy.deepcopy(self.workflow)
            changed['jobs'][job]['steps'][0].pop('with')
            with self.subTest(job=job), self.assertRaisesRegex(AssertionError, 'full history'):
                audit(changed, self.sources)

    def test_new_api_endpoint_caller_or_write_refuses(self):
        additions = ["\nsubprocess.run(['gh', 'api', 'repos/Ares-Empire/AresOS/pulls/12'])\n",
                     "\napi('pulls/12')\n", "\nread_only('organizations/Ares-Empire/settings/billing')\n"]
        for addition in additions:
            changed = dict(self.sources); changed['rehearsal_guard.py'] += addition
            with self.subTest(addition=addition), self.assertRaisesRegex(AssertionError, 'Unreviewed'):
                audit(self.workflow, changed)
        for line in ('gh api repos/Ares-Empire/AresOS/pulls/12',
                     'gh api orgs/Ares-Empire/packages/container/aresos --method DELETE'):
            with self.subTest(line=line), self.assertRaisesRegex(AssertionError, 'Unreviewed'):
                shell_api_permissions(line)


if __name__ == '__main__':
    unittest.main()
