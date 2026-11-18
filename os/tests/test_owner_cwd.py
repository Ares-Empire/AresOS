"""D18's three protections, each exercised without the other two. No tools entry runs."""
import ast
import contextlib
import pathlib
import re
import subprocess
import tempfile
import unittest

import test_owner_tools as common

ROOT, owner = common.ROOT, common.owner


class DirectoryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'os/tests')
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.marker = self.root / 'imported'
        for module in ('json', 'subprocess'):
            (self.root / (module + '.py')).write_text('open(' + repr(str(self.marker)) + ', "a").write("' + module + '\\n")\n')

    def test_at_alone_resolves_its_path_before_changing_directory(self):
        payload = self.root / 'payload'
        payload.mkdir()
        (payload / 'at').write_bytes((ROOT / 'os/owner-tools/at').read_bytes())
        (payload / 'owner.py').write_text('import os, sys\nprint(os.getcwd())\nprint(sys.argv[1:])\n')
        # The stand-in has no Step, imports no planted module and runs no tool.
        result = subprocess.run(['/usr/bin/bash', 'payload/at', 'fixture'], cwd=self.root,
                                text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.splitlines(), ['/', "['fixture']"])
        self.assertFalse(self.marker.exists())

    def test_step_directory_alone_uses_nonisolated_python(self):
        with contextlib.chdir(self.root):
            step = owner.Step("python3 - <<'FIXTURE'\nimport json, subprocess, os\nprint(os.getcwd())\nFIXTURE\n", 'cwd-fixture')
            try:
                self.assertEqual(step.wait(10), 'done', step.stderr)
                self.assertEqual(step.stdout.strip(), '/')
                self.assertFalse(self.marker.exists())
            finally:
                if step.process.poll() is None:
                    step.stop()

    def test_host_read_and_mutate_directories_alone(self):
        with contextlib.chdir(self.root):
            host = owner.Host()
            self.assertEqual(host.read('pwd').strip(), '/')
            host.mutate('pwd')  # This stand-in mutation only reports its directory.
            self.assertEqual(host.trace[-1]['stdout'].strip(), '/')

    def test_every_subprocess_start_in_owner_and_media_fixes_its_directory(self):
        calls = []
        for file in ('owner.py', 'media.py'):
            tree = ast.parse((ROOT / 'os/owner-tools' / file).read_text())
            modules = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                for alias in node.names if alias.name == 'subprocess'}
            imported = {alias.asname or alias.name for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module == 'subprocess' for alias in node.names}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in modules or isinstance(node.func, ast.Name) and node.func.id in imported):
                    calls.append((file, node.lineno))
                    directory = next((kw.value for kw in node.keywords if kw.arg == 'cwd'), None)
                    self.assertIsInstance(directory, ast.Constant, (file, node.lineno))
                    self.assertEqual(directory.value, '/', (file, node.lineno))
        self.assertGreaterEqual(len(calls), 4)

    def test_isolation_alone_on_every_embedded_python_start_and_live_control(self):
        starts = []
        for file in common.bundle.PAYLOAD:
            if file.endswith('.sh'):
                text = (ROOT / common.bundle.PAYLOAD[file]).read_text()
                starts.extend(re.findall(r"^(python3[^\n]*<<'([^']+)')$", text, re.M))
        host = type('Recorder', (), {'script': lambda obj, text, name: starts.extend(
            re.findall(r"^(python3[^\n]*<<'([^']+)')$", text, re.M))})()
        tools = owner.Tools(ROOT / 'os/owner-tools/payload', host, self.root)
        tools.pin_step(False)
        self.assertEqual(len(starts), 8)
        body = 'import json, subprocess, os\nprint(os.getcwd())\n'
        # No at and no Step: bash starts in the planted directory, for every start line.
        for line, end in starts:
            with self.subTest(line=line):
                result = subprocess.run(['/usr/bin/bash', '-seu'], input=line + '\n' + body + end + '\n',
                    cwd=self.root, text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout.strip(), str(self.root))
                self.assertFalse(self.marker.exists())
        subprocess.run(['/usr/bin/bash', '-seu'], input="python3 - <<'CONTROL'\n" + body + 'CONTROL\n',
                       cwd=self.root, text=True, capture_output=True, check=True)
        self.assertEqual(set(self.marker.read_text().splitlines()), {'json', 'subprocess'})

    def test_payload_has_no_nonisolated_python_stdin_or_c_start(self):
        for file, source in common.bundle.PAYLOAD.items():
            text = (ROOT / source).read_text()
            for line in text.splitlines():
                if re.search(r'\bpython3\b.*(?:<<|\s-c\s)', line):
                    with self.subTest(file=file, line=line):
                        self.assertRegex(line, r'\bpython3\s+-I\s+')


if __name__ == '__main__':
    unittest.main()
