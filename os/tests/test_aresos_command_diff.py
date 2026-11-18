"""Package 43: the release classifier must explain the dispatcher, helper and moved Control wrapper."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import release_diff as rd


class CommandDiffTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.old, self.new, self.base = [pathlib.Path(folder.name) / name for name in ('old', 'new', 'base')]
        for root in (self.old, self.new, self.base):
            root.mkdir()
        result = subprocess.run(['bash', str(ROOT / 'os/build.sh'), 'control-tree', str(ROOT / 'os'),
                                 str(ROOT / 'control'), str(self.new)], capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Classification reads the staged checkout sources. git_changed normally sees them after the lead commits.
        self.config = {'usr/bin/aresos', 'usr/libexec/aresos-askpass'}
        for rel in self.config:
            target = self.new / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / 'os/config' / rel, target)
        # R28 carries Control's original wrapper at this path; R29 replaces it with the dispatcher.
        old_cli = self.old / 'usr/bin/aresos'
        old_cli.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'control/packaging/aresos', old_cli)
        with mock.patch.object(rd, 'git_changed', side_effect=lambda commit, prefix:
                               self.config if prefix == 'os/config' else set()):
            self.classifier = rd.Classifier((self.old, self.new, self.base), dict(old=[], new=[]),
                                            dict(old=set(), new=set()), dict(unmasked=set(), executables=set()))

    @staticmethod
    def image_entry(root, rel):
        # Inventory of the installed image: the temporary copy belongs to the tester, not root.
        value = rd.entry(root, rel)
        return dict(value, uid=0, gid=0) if value else None

    def test_all_three_paths_are_explained_by_the_existing_release_rules(self):
        for rel in sorted(self.config | {'usr/libexec/aresos-control/cli'}):
            with self.subTest(path=rel):
                found = self.classifier.classify(rel, self.image_entry(self.old, rel), self.image_entry(self.new, rel))
                self.assertIsNotNone(found, f'PLAN-GAP D16: release_diff.py cannot explain /{rel}')
                if rel in self.config:
                    self.assertEqual(found[0], 'config')

    def test_config_explanations_require_the_source_bytes_root_and_mode_0755(self):
        for rel in self.config:
            before, after = self.image_entry(self.old, rel), self.image_entry(self.new, rel)
            self.assertEqual(after['mode'], 0o755)
            self.assertEqual(self.classifier.classify(rel, before, after)[0], 'config')
            for bad in (dict(after, sha256='0' * 64), dict(after, uid=1001), dict(after, gid=1001),
                        dict(after, mode=0o644), dict(after, kind=0o120000), None):
                with self.subTest(path=rel, bad=bad):
                    self.assertIsNone(self.classifier.classify(rel, before, bad))


if __name__ == '__main__':
    unittest.main()
