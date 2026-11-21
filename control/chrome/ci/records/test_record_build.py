"""record_build.py: builds.json is recorded by a tool, not by hand (brief 18c-b, item 4).

Runs in control-chrome-records.yml on the runner. `add` runs against synthetic repositories made here: commits
of a small control/ tree that carries the checkout's build.py. `check` runs against synthetic checkouts and
once against this one. No test reaches the network.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'control/chrome'))
import record_build  # noqa: E402
from record_build import Refused  # noqa: E402

BUILD_PY = ROOT / 'control/chrome/build.py'
GIT_ENV = {
    'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': '/nonexistent', 'LANG': 'C.UTF-8',
    'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
    'GIT_AUTHOR_NAME': 'Records Test', 'GIT_AUTHOR_EMAIL': 'records@example.invalid',
    'GIT_COMMITTER_NAME': 'Records Test', 'GIT_COMMITTER_EMAIL': 'records@example.invalid',
}
TREE = {
    'control/aresos_control/__init__.py': '"""Synthetic service package."""\n',
    'control/generated/tools.json': '{"tools":[]}\n',
    'control/settings/managed.json': '{}\n',
    'control/packaging/unit.service': '[Service]\n',
    'control/chrome/extension/manifest.json': '{"manifest_version":3,"version":"1.0.0"}\n',
    'control/chrome/packaging/policy.json': '{}\n',
    'control/launch.py': '# synthetic launcher\n',
    'control/requirements.lock': '',
    'control/chrome/native_host.py': '# synthetic host\n',
}
T = ['2026-11-01T08:00:00Z', '2026-11-02T08:00:00Z', '2026-11-03T08:00:00Z', '2026-11-04T08:00:00Z',
     '2026-11-05T08:00:00Z']


class Repository:
    """A synthetic git repository whose commits hold a control/ tree build.py can hash."""

    def __init__(self, folder):
        self.path = Path(folder)
        self.path.mkdir(parents=True)
        self.git('init', '-q', '-b', 'main')
        self.build_py = BUILD_PY.read_text()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.path), *args], check=True, capture_output=True,
                              env=GIT_ENV, timeout=60).stdout.decode().strip()

    def commit(self, version, build_py=None, extra=None):
        files = dict(TREE, **{'control/aresos_control/version.py': f'VERSION = {version!r}\n',
                              'control/chrome/build.py': build_py or self.build_py}, **(extra or {}))
        for name, text in files.items():
            (self.path / name).parent.mkdir(parents=True, exist_ok=True)
            (self.path / name).write_text(text)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'synthetic ' + str(version))
        return self.git('rev-parse', 'HEAD')

    def expected(self, commit):
        """What that commit's build.py prints over that commit's archived tree."""
        archive = subprocess.run(['git', '-C', str(self.path), 'archive', '--format=tar', commit],
                                 check=True, capture_output=True, env=GIT_ENV, timeout=60).stdout
        with tempfile.TemporaryDirectory() as folder:
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(folder, filter='data')
            return subprocess.run([sys.executable, '-I', '-B', 'control/chrome/build.py'], cwd=folder, check=True,
                                  capture_output=True, timeout=60).stdout.decode().strip()


class Add(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.repo = Repository(Path(folder.name) / 'repo')
        self.registry = Path(folder.name) / 'builds.json'
        self.registry.write_text('{"format":1,"builds":[]}\n')

    def add(self, commit, shipped_at, expect=None):
        return record_build.add(commit, shipped_at, expect, self.registry, self.repo.path)

    def rows(self):
        return json.loads(self.registry.read_text())['builds']

    def test_add_records_the_hash_of_the_commit_s_own_build_py_over_its_archived_tree(self):
        first = self.repo.commit(1)
        expected = self.repo.expected(first)
        self.assertRegex(expected, '^[0-9a-f]{64}$')
        row, outcome = self.add(first, T[0], expect=expected)
        self.assertEqual(outcome, 'recorded')
        self.assertEqual(row, {'commit': first, 'build': expected, 'shipped_at': T[0]})
        self.assertEqual(self.rows(), [row])
        self.assertEqual(self.registry.read_text(), '{"format":1,"builds":[\n' + json.dumps(row, separators=(',', ':')) + '\n]}\n')

    def test_each_commit_is_hashed_by_its_own_build_py_never_the_checkout_s_or_the_working_tree(self):
        first = self.repo.commit(1)
        # A later build.py with another algorithm: rows keep the algorithm their commit shipped with.
        variant = self.repo.build_py.replace('digest = hashlib.sha256()', "digest = hashlib.sha256(b'variant\\0')")
        self.assertNotEqual(variant, self.repo.build_py)
        second = self.repo.commit(1, build_py=variant)
        expected_first, expected_second = self.repo.expected(first), self.repo.expected(second)
        sys.path.insert(0, str(BUILD_PY.parent))
        from build import build_hash
        with tempfile.TemporaryDirectory() as folder:
            archive = subprocess.run(['git', '-C', str(self.repo.path), 'archive', '--format=tar', second],
                                     check=True, capture_output=True, env=GIT_ENV).stdout
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(folder, filter='data')
            self.assertNotEqual(build_hash(Path(folder)), expected_second, 'the checkout\'s build.py must not be the one used')
        # Uncommitted changes in the repository's working tree are not part of any commit.
        (self.repo.path / 'control/aresos_control/version.py').write_text('VERSION = "uncommitted"\n')
        self.assertEqual(self.add(second, T[1])[0]['build'], expected_second)
        self.assertEqual(self.add(first, T[0])[0]['build'], expected_first)
        self.assertEqual([row['build'] for row in self.rows()], [expected_second, expected_first])

    def test_a_wrong_expect_is_refused_and_builds_json_is_left_alone(self):
        first = self.repo.commit(1)
        before = self.registry.read_bytes()
        with self.assertRaisesRegex(Refused, 'not the expected'):
            self.add(first, T[0], expect='0' * 64)
        self.assertEqual(self.registry.read_bytes(), before)

    def test_a_repeated_commit_is_kept_once_and_a_conflicting_row_is_refused(self):
        first = self.repo.commit(1)
        row, _ = self.add(first, T[0])
        before = self.registry.read_bytes()
        again, outcome = self.add(first, T[1], expect=row['build'])
        self.assertEqual((again, outcome), (row, 'already recorded; builds.json unchanged'))
        self.assertEqual(self.registry.read_bytes(), before)
        self.registry.write_text(json.dumps({'format': 1, 'builds': [dict(row, build='e' * 64)]}))
        before = self.registry.read_bytes()
        with self.assertRaisesRegex(Refused, 'but it hashes to'):
            self.add(first, T[1])
        self.assertEqual(self.registry.read_bytes(), before)

    def test_only_the_newest_three_by_shipped_at_are_kept(self):
        commits = [self.repo.commit(index) for index in range(5)]
        # Added out of order: pruning goes by shipped_at, not by when add ran.
        for index in [1, 0, 3, 2]:
            self.add(commits[index], T[index])
        self.assertEqual([(row['commit'], row['shipped_at']) for row in self.rows()],
                         [(commits[3], T[3]), (commits[2], T[2]), (commits[1], T[1])])
        before = self.registry.read_bytes()
        with self.assertRaisesRegex(Refused, 'pruned at once'):
            self.add(commits[4], T[0])
        self.assertEqual(self.registry.read_bytes(), before)
        self.add(commits[4], T[4])
        self.assertEqual([row['commit'] for row in self.rows()], [commits[4], commits[3], commits[2]])

    def test_a_later_commit_with_the_same_build_takes_over_its_row(self):
        # qualify.plan refuses a build named twice; a release that changed nothing under control/ hashes the same.
        first = self.repo.commit(1)
        second = self.repo.commit(1, extra={'README.md': 'outside control/\n'})
        self.assertEqual(self.repo.expected(first), self.repo.expected(second))
        self.add(first, T[0])
        row, outcome = self.add(second, T[1])
        self.assertIn('replacing', outcome)
        self.assertEqual(self.rows(), [row])

    def test_newer_same_build_shipment_matches_the_current_manifest_in_either_order(self):
        older = self.repo.commit(1)
        newer = self.repo.commit(1, extra={'README.md': 'outside control/\n'})
        build = self.repo.expected(newer)
        self.assertEqual(self.repo.expected(older), build)
        root = self.repo.path
        registry = root / record_build.REGISTRY
        release = root / record_build.RELEASE
        release.parent.mkdir(parents=True)
        release.write_text(json.dumps({'source_commit': newer,
                                        'control': {'source_revision': newer, 'chrome_build': build}}))
        latest = {'commit': newer, 'build': build, 'shipped_at': T[1]}
        for order in ([(older, T[0]), (newer, T[1])], [(newer, T[1]), (older, T[0])]):
            with self.subTest(first=order[0][1]):
                registry.write_text('{"format":1,"builds":[]}\n')
                for commit, shipped_at in order:
                    row, _ = record_build.add(commit, shipped_at, repo=root)
                self.assertEqual(record_build.check(root)[0], [])
                self.assertEqual(row, latest)
                self.assertEqual(record_build.load(registry)['builds'], [latest])
        before = registry.read_bytes()
        self.assertEqual(record_build.add(older, T[1], repo=root)[0], latest)
        self.assertEqual(registry.read_bytes(), before)

    def test_bad_input_is_refused_before_anything_is_written(self):
        first = self.repo.commit(1)
        before = self.registry.read_bytes()
        for commit, shipped_at, expect in [
            (first[:12], T[0], None),
            (first.upper(), T[0], None),
            ('1' * 40, T[0], None),
            (first, '2026-11-01T08:00:00', None),
            (first, '2026-11-01T08:00:00+00:00', None),
            (first, '2026-02-30T08:00:00Z', None),
            (first, T[0], 'ccd0fd79'),
        ]:
            with self.subTest(commit=commit, shipped_at=shipped_at, expect=expect), self.assertRaises(Refused):
                self.add(commit, shipped_at, expect)
        self.assertEqual(self.registry.read_bytes(), before)
        bare = Repository(self.repo.path.parent / 'bare')
        (bare.path / 'notes.txt').write_text('no control tree\n')
        bare.git('add', '-A'); bare.git('commit', '-q', '-m', 'no control')
        with self.assertRaises(Refused):
            record_build.add(bare.git('rev-parse', 'HEAD'), T[0], None, self.registry, bare.path)

    def test_an_invalid_builds_json_is_refused(self):
        first = self.repo.commit(1)
        row = {'commit': 'a' * 40, 'build': 'b' * 64, 'shipped_at': T[0]}
        for registry in [{'format': 2, 'builds': []}, {'format': True, 'builds': []}, {'builds': []},
                         {'format': 1, 'builds': [dict(row, extra=1)]},
                         {'format': 1, 'builds': [row, dict(row, commit='c' * 40)]},
                         {'format': 1, 'builds': [row, dict(row, build='d' * 64)]},
                         {'format': 1, 'builds': [dict(row, shipped_at='2026-11-01')]}]:
            self.registry.write_text(json.dumps(registry))
            with self.subTest(registry=registry), self.assertRaises(Refused):
                self.add(first, T[1])
        self.registry.write_text('{"format":1,')
        with self.assertRaisesRegex(Refused, 'not JSON'):
            self.add(first, T[1])

    def test_what_add_writes_is_what_the_planner_accepts(self):
        sys.path.insert(0, str(BUILD_PY.parent))
        import qualify
        for index in range(4):
            self.add(self.repo.commit(index), T[index])
        record = json.loads((ROOT / 'control/chrome/qualification.json').read_text())
        self.assertEqual(qualify.plan(json.loads(self.registry.read_text()), {}, record, 'f' * 40, 'f' * 64), {'include': []})

    def test_the_command_line(self):
        first = self.repo.commit(1)
        expected = self.repo.expected(first)
        script = ROOT / 'control/chrome/record_build.py'
        common = ['--commit', first, '--shipped-at', T[0], '--registry', str(self.registry), '--repo', str(self.repo.path)]
        wrong = subprocess.run([sys.executable, '-I', '-B', str(script), 'add', *common, '--expect', '0' * 64],
                               capture_output=True, text=True, timeout=120)
        self.assertEqual(wrong.returncode, 1)
        self.assertIn('record_build: refused:', wrong.stderr)
        done = subprocess.run([sys.executable, '-I', '-B', str(script), 'add', *common, '--expect', expected],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout.splitlines()[0])['build'], expected)
        self.assertEqual(self.rows()[0]['build'], expected)


ABSENT = object()


class Check(unittest.TestCase):
    COMMIT, OTHER = '1' * 40, '2' * 40
    BUILD, ELSE = '3' * 64, '4' * 64

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        (self.root / 'os/manifest/releases').mkdir(parents=True)
        (self.root / 'control/chrome').mkdir(parents=True)
        self.rows([])

    def rows(self, rows):
        (self.root / 'control/chrome/builds.json').write_text(json.dumps({'format': 1, 'builds': rows}))

    def row(self, commit=None, build=None):
        return {'commit': commit or self.COMMIT, 'build': build or self.BUILD, 'shipped_at': T[0]}

    def manifest(self, name, commit=None, control=True, tag='synthetic'):
        # control: True for the matching object, ABSENT for none, anything else as it stands.
        data = {'tag': tag, 'source_commit': commit or self.COMMIT}
        if control is True:
            data['control'] = {'source_revision': commit or self.COMMIT, 'chrome_build': self.BUILD}
        elif control is not ABSENT:
            data['control'] = control
        path = self.root / 'os/manifest' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def check(self):
        return record_build.check(self.root)

    def test_a_release_with_its_row_passes(self):
        self.manifest('release.json')
        self.rows([self.row()])
        failures, notes = self.check()
        self.assertEqual(failures, [])
        self.assertIn(f'os/manifest/release.json: {self.COMMIT} {self.BUILD} matches builds.json', notes)

    def test_a_release_without_its_row_fails(self):
        self.manifest('release.json')
        self.rows([self.row(commit=self.OTHER)])
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn('has no row for ' + self.COMMIT, failures[0])

    def test_a_release_with_an_unequal_row_fails(self):
        self.manifest('release.json')
        self.rows([self.row(build=self.ELSE)])
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn('builds.json records', failures[0])

    def test_manifests_without_a_control_object_pass_with_an_info_line(self):
        self.manifest('release.json', control=ABSENT)
        self.manifest('releases/06.json', commit=self.OTHER, control=ABSENT)
        failures, notes = self.check()
        self.assertEqual(failures, [])
        self.assertEqual(notes, ['os/manifest/release.json: no control object; nothing to check',
                                 'os/manifest/releases/06.json: no control object; nothing to check'])

    def test_only_the_published_release_28_can_have_a_source_only_control_object(self):
        commit = record_build.RELEASE_28_SOURCE
        release = dict(commit=commit, control={'source_revision': commit}, tag=f'28-{commit}')
        self.manifest('release.json', **release)
        self.manifest('releases/28.json', **release)
        failures, notes = self.check()
        self.assertEqual(failures, [])
        self.assertEqual(notes, ['os/manifest/release.json: release 28 predates Chrome build records',
                                 'os/manifest/releases/28.json: release 28 predates Chrome build records'])
        self.manifest('releases/29.json', **release)
        self.manifest('release.json', **dict(release, tag=f'29-{commit}'))
        failures, _ = self.check()
        self.assertEqual(len(failures), 2)
        self.assertTrue(all('control must be exactly' in failure for failure in failures))

    def test_a_malformed_control_object_fails(self):
        self.rows([self.row()])
        good = {'source_revision': self.COMMIT, 'chrome_build': self.BUILD}
        for control in [None, [], 'x', {}, {'source_revision': self.COMMIT}, dict(good, extra=1),
                        dict(good, source_revision=self.COMMIT[:12]), dict(good, chrome_build='A' * 64),
                        dict(good, chrome_build=1)]:
            for name in ['release.json', 'releases/99.json']:
                with self.subTest(control=control, name=name):
                    for path in (self.root / 'os/manifest').rglob('*.json'):
                        path.unlink()
                    self.manifest('release.json', control=ABSENT)
                    self.manifest(name, control=control)
                    failures, _ = self.check()
                    self.assertEqual(len(failures), 1, failures)
                    self.assertIn('control must be exactly', failures[0])

    def test_source_revision_must_equal_the_manifest_s_source_commit(self):
        self.rows([self.row()])
        self.manifest('release.json', control={'source_revision': self.COMMIT, 'chrome_build': self.BUILD})
        data = json.loads((self.root / 'os/manifest/release.json').read_text())
        data['source_commit'] = self.OTHER
        (self.root / 'os/manifest/release.json').write_text(json.dumps(data))
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn("is not the manifest's source_commit", failures[0])

    def test_releases_need_an_equal_row_only_when_one_is_kept(self):
        self.manifest('release.json', control=ABSENT)
        self.manifest('releases/41.json')
        self.manifest('releases/40.json', commit=self.OTHER)
        self.rows([self.row()])
        failures, notes = self.check()
        self.assertEqual(failures, [])
        self.assertIn(f'os/manifest/releases/40.json: no row for {self.OTHER} (only the newest 3 are kept)', notes)
        self.assertIn(f'os/manifest/releases/41.json: {self.COMMIT} {self.BUILD} matches builds.json', notes)
        self.rows([self.row(build=self.ELSE)])
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn('os/manifest/releases/41.json', failures[0])

    def test_releases_are_read_in_subfolders_too(self):
        self.manifest('release.json', control=ABSENT)
        self.manifest('releases/archive/39.json')
        self.rows([self.row(build=self.ELSE)])
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn('os/manifest/releases/archive/39.json', failures[0])

    def test_an_invalid_registry_or_a_missing_release_manifest_fails(self):
        self.manifest('release.json', control=ABSENT)
        (self.root / 'control/chrome/builds.json').write_text('{"format":1,"builds":[{}]}')
        self.assertEqual(len(self.check()[0]), 1)
        self.rows([])
        (self.root / 'os/manifest/release.json').unlink()
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn('cannot read', failures[0])
        (self.root / 'os/manifest/release.json').write_text('[]')
        self.assertEqual(self.check()[0], ['os/manifest/release.json: not a JSON object'])

    def test_the_command_line_exit_codes(self):
        self.manifest('release.json')
        self.rows([])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(record_build.main(['check', '--root', str(self.root)]), 1)
        self.assertIn('FAIL: os/manifest/release.json: builds.json has no row', out.getvalue())
        self.rows([self.row()])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(record_build.main(['check', '--root', str(self.root)]), 0)
        self.assertTrue(out.getvalue().endswith('record_build check passed\n'))

    def test_this_checkout_passes(self):
        failures, notes = record_build.check(ROOT)
        self.assertEqual(failures, [])
        self.assertTrue(notes)


if __name__ == '__main__':
    unittest.main()
