import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
from release_layers import BENCH_PATHS, INSTALLED_PATHS, BenchFile, scan


class BenchLayerTest(unittest.TestCase):
    def test_raw_layer_rejects_planted_file_hidden_from_top(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            top, old = (pathlib.Path(directory) / name for name in ('top', 'old'))
            top.mkdir()
            old.mkdir()
            image = {'GraphDriver': {'Name': 'overlay', 'Data': {'UpperDir': str(top), 'LowerDir': str(old)}},
                     'RootFS': {'Layers': ['sha256:one', 'sha256:two']}}
            self.assertEqual(scan(image), 2)
            for name in BENCH_PATHS:
                planted = old / name.replace('*', 'planted')
                planted.parent.mkdir(parents=True, exist_ok=True)
                planted.touch()
                with self.subTest(name=name), self.assertRaises(BenchFile):
                    scan(image)
                planted.unlink()
            image['GraphDriver']['Data'].pop('LowerDir')
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                scan(image)

    def test_release_build_inputs_exclude_bench(self):
        names = subprocess.check_output(['git', 'ls-files', 'os'], cwd=ROOT, text=True).splitlines()
        for name in names:
            if not name.startswith('os/ci/') and not re.fullmatch(r'os/tests/test_bench_[a-z0-9_]+\.py', name):
                self.assertNotRegex(name.lower(), r'(?:^|[/_-])bench(?:[/_.-]|$)')
        ignore = (ROOT / 'os/.containerignore').read_text().splitlines()
        for pattern in ('ci/', 'tests/test_bench_*', 'tests/__pycache__/'):
            self.assertIn(pattern, ignore)
        self.assertIn('test ! -e /tmp/aresos/ci', (ROOT / 'os/Containerfile').read_text())

    def test_release_isolation_refuses_each_planted_path(self):
        workflow = (ROOT / '.github/workflows/os-image.yml').read_text()
        blocks = list(re.finditer(r"(?ms)^          sudo podman run [^\n]+ -ec '\n(.*?)^          '", workflow))
        isolation = [block for block in blocks if 'test ! -e /usr/libexec/aresos-ci' in block.group(1)]
        self.assertGreaterEqual(len(isolation), 4)
        fixture = '''
test() {
  case "$*" in
    '! -e /'*|'! -L /'*) builtin test "$1" "$2" "$ISOLATION_ROOT$3" ;;
    *) builtin test "$@" ;;
  esac
}
systemd-analyze() { echo Storage=persistent; }
getent() { echo 'fixture:!:0::::::'; }
'''
        for match in isolation:
            block = match.group(1)
            line = workflow.count('\n', 0, match.start()) + 1
            paths = re.findall(r'test ! -e /([^\s]+)', block)
            with self.subTest(line=line), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                self.assertTrue(set(INSTALLED_PATHS).issubset(paths))
                env = {'PATH': '/usr/bin:/bin', 'ISOLATION_ROOT': directory}

                def run_block():
                    return subprocess.run(['/usr/bin/bash', '-ec', fixture + block], env=env,
                                          cwd=ROOT, capture_output=True, text=True)

                clean = run_block()
                self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
                for name in paths:
                    planted = pathlib.Path(directory) / name
                    planted.parent.mkdir(parents=True, exist_ok=True)
                    planted.touch()
                    with self.subTest(path=name):
                        result = run_block()
                        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    planted.unlink()
                    if name in INSTALLED_PATHS:
                        planted.symlink_to('missing-image-file')
                        with self.subTest(dangling_link=name):
                            result = run_block()
                            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                        planted.unlink()
