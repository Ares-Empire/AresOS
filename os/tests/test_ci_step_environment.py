"""Every direct script invocation owns its mode binding, including cleanup.

Discover readers from the CI sources rather than listing only today's native
helpers. Syntax-only wildcard compile checks do not execute script bodies.
"""
import ast
import copy
import pathlib
import re
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODE = 'REHEARSAL_MODE'


def reads_mode(path, source):
    if path.endswith('.py'):
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and ast.unparse(node.value) == 'os.environ':
                if isinstance(node.slice, ast.Constant) and node.slice.value == MODE:
                    return True
            if isinstance(node, ast.Call) and ast.unparse(node.func) in ('os.environ.get', 'os.getenv'):
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == MODE:
                    return True
        return False
    return bool(re.search(r'\$(?:REHEARSAL_MODE\b|\{REHEARSAL_MODE(?:\}|[:?+\-]))', source))


def audit(workflow, sources):
    readers = {path for path, source in sources.items() if reads_mode(path, source)}
    checked = []
    for job_name, job in workflow['jobs'].items():
        for step in job['steps']:
            references = set(re.findall(r'\bos/ci/[\w/-]+\.(?:py|sh)\b', step.get('run', '')))
            invoked = references & readers
            if invoked:
                env = step.get('env', {})
                where = job_name + ': ' + step.get('name', step.get('run', ''))
                assert isinstance(env, dict) and isinstance(env.get(MODE), str) and env[MODE].strip(), (
                    where + ': missing explicit step env REHEARSAL_MODE for ' + ', '.join(sorted(invoked)))
                checked.append((job_name, step, invoked))
    return checked


class CiStepEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
        self.sources = {p.relative_to(ROOT).as_posix(): p.read_text()
                        for p in (ROOT / 'os/ci').rglob('*') if p.suffix in ('.py', '.sh')}

    def test_every_mode_reading_script_has_explicit_step_environment(self):
        checked = audit(self.workflow, self.sources)
        seen = set().union(*(paths for _, _, paths in checked))
        self.assertTrue({'os/ci/owner_devices.py', 'os/ci/owner_capabilities.py',
                         'os/ci/rehearsal_guard.py', 'os/ci/registry_auth.py',
                         'os/ci/rehearsal_auth.py', 'os/ci/build_tools.py'} <= seen)
        native, = [step for _, step, paths in checked if 'os/ci/owner_devices.py' in paths]
        self.assertEqual(native['env'][MODE], '${{ inputs.rehearsal }}')
        self.assertIn('sudo -E env -u GH_TOKEN python3 os/ci/owner_devices.py', native['run'])

    def test_removing_any_callers_binding_refuses_even_with_job_or_global_env(self):
        checked = audit(self.workflow, self.sources)
        for job_name, original, _ in checked:
            changed = copy.deepcopy(self.workflow)
            changed['env'] = {MODE: 'probe'}
            changed['jobs'][job_name]['env'] = {MODE: 'probe'}
            step, = [s for s in changed['jobs'][job_name]['steps'] if s == original]
            step['env'].pop(MODE)
            with self.subTest(job=job_name, step=original.get('name')), self.assertRaisesRegex(AssertionError, 'explicit step env'):
                audit(changed, self.sources)

    def test_empty_or_invalid_step_env_refuses(self):
        for value in (None, [], {}, {MODE: ''}, {MODE: '  '}, {MODE: False}):
            workflow = {'jobs': {'native': {'steps': [{'env': value, 'run': 'python3 os/ci/owner_devices.py'}]}}}
            with self.subTest(env=value), self.assertRaisesRegex(AssertionError, 'explicit step env'):
                audit(workflow, self.sources)

    def test_new_reader_is_discovered_without_a_hardcoded_script_list(self):
        for extension, source in (('py', "import os\nos.environ['REHEARSAL_MODE']"),
                                  ('py', "import os\nos.environ.get('REHEARSAL_MODE')"),
                                  ('py', "import os\nos.getenv('REHEARSAL_MODE')"),
                                  ('sh', 'echo "${REHEARSAL_MODE}"'),
                                  ('sh', 'echo "$REHEARSAL_MODE"')):
            path = 'os/ci/new-reader.' + extension
            workflow = {'jobs': {'new': {'steps': [{'run': ('python3 ' if extension == 'py' else 'bash ') + path}]}}}
            sources = dict(self.sources, **{path: source})
            with self.subTest(source=source), self.assertRaisesRegex(AssertionError, 'explicit step env'):
                audit(workflow, sources)
            workflow['jobs']['new']['steps'][0]['env'] = {MODE: 'probe'}
            self.assertEqual(len(audit(workflow, sources)), 1)


if __name__ == '__main__':
    unittest.main()
