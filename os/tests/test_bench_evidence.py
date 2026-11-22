import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
import evidence


class BenchEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.directory.cleanup)
        self.folder = pathlib.Path(self.directory.name) / 'bench'
        self.folder.mkdir()
        (self.folder / 'run.json').write_text('{}\n')

    def test_bounded_regular_files_pass(self):
        (self.folder / '001.exec.txt').write_text('pass\n')
        self.assertEqual(evidence.scan(self.folder), (2, 8))

    def test_oversize_file_and_aggregate_are_refused(self):
        with (self.folder / '001.exec.txt').open('wb') as stream:
            stream.truncate(evidence.MAX_TEXT + 1)
        with self.assertRaisesRegex(ValueError, 'size cap'):
            evidence.scan(self.folder)
        (self.folder / '001.exec.txt').write_text('1234')
        with patch.object(evidence, 'MAX_TOTAL', 6), self.assertRaisesRegex(ValueError, 'size cap'):
            evidence.scan(self.folder)

    def test_token_refuses_before_upload_output(self):
        tokens = [b'ghp_' + b'x' * 36, b'Bearer ' + b'x' * 30, b'"nonce": "' + b'x' * 32 + b'"']
        for token in tokens:
            with self.subTest(prefix=token[:4]):
                (self.folder / '001.exec.txt').write_bytes(token)
                with self.assertRaisesRegex(ValueError, 'Token-shaped'):
                    evidence.scan(self.folder)
        flag = self.folder.parent / 'output'
        flag.touch()
        result = subprocess.run([sys.executable, '-B', evidence.__file__, self.folder],
                                capture_output=True, env=dict(os.environ, GITHUB_OUTPUT=str(flag)))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(flag.read_bytes(), b'')
        self.assertNotIn(tokens[-1], result.stderr)

    def test_links_are_refused(self):
        outside = self.folder.parent / 'outside'
        outside.write_text('text')
        path = self.folder / '001.exec.txt'
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'regular files'):
            evidence.scan(self.folder)
        path.unlink()
        os.link(outside, path)
        with self.assertRaisesRegex(ValueError, 'regular files'):
            evidence.scan(self.folder)
        alias = self.folder.parent / 'alias'
        alias.symlink_to(self.folder)
        with self.assertRaisesRegex(ValueError, 'real directory'):
            evidence.scan(alias)

    def test_unexpected_paths_and_special_files_are_refused(self):
        nested = self.folder / 'extra'
        nested.mkdir()
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            evidence.scan(self.folder)
        nested.rmdir()
        os.mkfifo(self.folder / '001.exec.txt')
        with self.assertRaisesRegex(ValueError, 'regular files'):
            evidence.scan(self.folder)
