import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
import script

SCRIPT = 'reviews/334a-bench-hosted/bench/session-health.json'


class BenchScriptTest(unittest.TestCase):
    def test_acceptance_script(self):
        network, steps = script.parse((ROOT / SCRIPT).read_bytes())
        self.assertEqual(network, 'none')
        self.assertEqual([step['kind'] for step in steps], ['wait', 'expect', 'shot', 'reboot', 'wait', 'expect'])
        self.assertEqual(steps[1], steps[-1])

    def test_invalid_scripts(self):
        for document in [
            {'network': 'host', 'steps': [{'kind': 'shot'}]},
            {'steps': []},
            {'steps': [{'kind': 'shot'}] * (script.MAX_STEPS + 1)},
            {'steps': [{'kind': 'reboot'}, {'kind': 'reboot'}]},
            {'steps': [{'kind': 'wait', 'for': 'boot_id'}]},
            {'steps': [{'kind': 'exec', 'argv': '/bin/true'}]},
            {'steps': [{'kind': 'exec', 'argv': ['a\0b']}]},
            {'steps': [{'kind': 'shot', 'path': '/tmp/file'}]},
            {'steps': [{'kind': 'net'}]},
        ]:
            with self.subTest(document=document), self.assertRaises(ValueError):
                script.parse(json.dumps(document).encode())
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            script.parse(b'{"steps":[{"kind":"reboot","kind":"shot"}]}')

    def test_reads_exact_commit_and_rejects_symlinks_and_untracked_inputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            repo = pathlib.Path(folder)
            subprocess.run(['git', 'init', '-q', folder], check=True)
            path = repo / SCRIPT
            path.parent.mkdir(parents=True)
            contents = b'{"steps":[{"kind":"shot"}]}'
            path.write_bytes(contents)
            path.with_name('linked.json').symlink_to(path.name)
            subprocess.run(['git', '-C', folder, 'add', '.'], check=True)
            subprocess.run(['git', '-C', folder, '-c', 'user.name=Bench tests', '-c', 'user.email=bench@example.org',
                            '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Commit script'], check=True)
            path.write_bytes(b'{"steps":[{"kind":"reboot"}]}')
            path.with_name('untracked.json').write_bytes(contents)
            sha = script.git(folder, 'rev-parse', 'HEAD').decode().strip()
            self.assertEqual(script.load(folder, sha, SCRIPT),
                             ('none', [{'kind': 'shot'}], hashlib.sha256(contents).hexdigest()))
            for name in ('linked.json', 'untracked.json', '../session-health.json', 'session-health.json;echo'):
                bad = f'reviews/334a-bench-hosted/bench/{name}'
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    script.load(folder, sha, bad)
            with self.assertRaises(ValueError):
                script.load(folder, '0' * 40, SCRIPT)
