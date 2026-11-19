"""Release 28 carries Control Part A, with exact diff rules and image-derived provenance."""
import contextlib
import copy
import hashlib
import io
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import release_diff as rd
import release28_record
import test_release28 as r28


class ControlRulesTest(unittest.TestCase):
    def setUp(self):
        self.f = r28.Classifier28Test('test_every_rule_explains_its_paths')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.c, self.root = self.f.classifier, self.f.new
        self.record = r28.install_control_fixture(self.root)
        # The expected map comes from the real build interface; it stays fixed while image rows are mutated.
        self.enterContext(patch.object(rd, 'control_install_map', return_value=rd.control_install_map()))
        self.enterContext(patch.dict(os.environ, GITHUB_SHA='a' * 40))

    def explain(self, rel):
        self.c.control, self.c.control_error = None, None
        return self.f.explain(rel)

    def write_record(self, record):
        (self.root / rd.CONTROL_RECORD).write_text(json.dumps(record))

    def test_every_installed_path_and_the_manifest_has_a_rule(self):
        paths = {*self.record['files'], *self.record['directories'], *self.record['links'], *self.record['vendor'], '/' + rd.CONTROL_RECORD}
        for path in sorted(paths):
            with self.subTest(path=path):
                found = self.explain(path[1:])
                self.assertEqual(found[0], 'control')
                self.assertIn('#58', found[1])
        self.assertIsNone(self.c.control_error)

    def test_each_control_area_rejects_neighbours_bytes_types_and_metadata(self):
        paths = ['etc/claude-code/managed-settings.json', 'usr/bin/aresos', rd.CONTROL_UNIT,
                 'usr/lib/sysusers.d/aresos-tools.conf', 'usr/lib/tmpfiles.d/aresos-tools.conf',
                 'usr/lib/tmpfiles.d/aresos-control-folders.conf', 'usr/share/aresos/control/service.json',
                 'usr/libexec/aresos-control/aresos_control/daemon.py', 'usr/libexec/aresos-control/chrome/build-id.json',
                 'usr/lib/aresos-control/vendor/fixture.py', rd.CONTROL_RECORD]
        for path in paths:
            for field, value in (('uid', 250), ('gid', 250), ('mode', 0o666), ('kind', stat.S_IFLNK), ('xattrs', {'user.extra': '00'})):
                with self.subTest(path=path, field=field), self.f.image(path, **{field: value}):
                    self.assertIsNone(self.explain(path))
            with self.subTest(path=path), self.f.content(path, b'changed\n'):
                self.assertIsNone(self.explain(path))
            with self.f.content(path + '.neighbour', b'neighbour'):
                self.assertIsNone(self.explain(path + '.neighbour'))
        for path in ('etc/claude-code', 'usr/libexec/aresos-control', 'usr/lib/aresos-control/vendor'):
            with self.subTest(folder=path), self.f.image(path, mode=0o775):
                self.assertIsNone(self.explain(path))

    def test_missing_or_extra_recorded_paths_stop_even_outside_the_diff(self):
        paths = ['etc/claude-code/CLAUDE.md', 'usr/libexec/aresos-control/launch.py', 'usr/lib/aresos-control/vendor/fixture.py']
        for path in paths:
            with self.subTest(path=path), self.f.content(path, None):
                self.explain(rd.CONTROL_RECORD)
                self.assertFalse(self.c.control_entries())
        for top in rd.CONTROL_ROOTS:
            with self.subTest(top=top), self.f.content(top + '/extra', b'not recorded'):
                self.assertIsNone(self.explain(rd.CONTROL_RECORD))
        for key in ('files', 'directories', 'links', 'vendor'):
            changed = copy.deepcopy(self.record)
            changed[key]['/usr/libexec/aresos-control/extra'] = next(iter(changed[key].values()))
            self.write_record(changed)
            with self.subTest(key=key):
                self.assertIsNone(self.explain(rd.CONTROL_RECORD))
            self.write_record(self.record)

    def test_the_manifest_cannot_redefine_sources_wheels_or_the_vendor_boundary(self):
        mutations = [dict(source_revision='b' * 40), dict(requirements_lock='0' * 64), dict(format=2), dict(format=True), dict(extra=True)]
        for changes in mutations:
            with self.subTest(changes=changes):
                self.write_record(dict(self.record, **changes))
                self.assertIsNone(self.explain(rd.CONTROL_RECORD))
        for mutation in ('missing', 'extra', 'hash', 'version'):
            changed = copy.deepcopy(self.record)
            if mutation == 'missing': changed['wheels'].pop()
            if mutation == 'extra': changed['wheels'].append(changed['wheels'][0])
            if mutation == 'hash': changed['wheels'][0]['sha256'] = '0' * 64
            if mutation == 'version': changed['wheels'][0]['version'] = 'unlocked'
            self.write_record(changed)
            with self.subTest(wheels=mutation): self.assertIsNone(self.explain(rd.CONTROL_RECORD))
        for name in ('/usr/lib/aresos-control/neighbour', '/usr/lib/aresos-control/vendor/../escape'):
            changed = copy.deepcopy(self.record)
            changed['vendor'][name] = dict(mode='0644', sha256='0' * 64)
            self.write_record(changed)
            with self.subTest(vendor=name): self.assertIsNone(self.explain(rd.CONTROL_RECORD))

    def test_enable_link_needs_the_exact_target_path_and_metadata(self):
        name, target = next(iter(self.record['links'].items()))
        path = name[1:]
        for value in ('/usr/lib/systemd/system/other.service', '../aresos-toold.service', 'folder'):
            with self.subTest(value=value), self.f.content(path, 'folder' if value == 'folder' else ('link', value)):
                self.assertIsNone(self.explain(path))
        for fields in (dict(uid=250), dict(mode=0o755), dict(xattrs={'user.extra': '00'})):
            with self.subTest(fields=fields), self.f.image(path, **fields):
                self.assertIsNone(self.explain(path))
        with self.f.content(path + '.other', ('link', target)):
            self.assertIsNone(self.explain(path + '.other'))

    def test_account_table_rules_reject_metadata_neighbours_and_extra_rows(self):
        for kind, row in ControlAccountsTest.ROWS.items():
            before = (ControlAccountsTest.OLD[kind] + '\n').encode()
            after = before + (row + '\n').encode()
            for suffix in ('', '-'):
                path = 'etc/' + kind + suffix
                with self.subTest(path=path), self.f.content(path, before, root=self.f.old), self.f.content(path, after):
                    self.assertIsNotNone(self.explain(path))
                    with self.f.image(path, mode=0o666): self.assertIsNone(self.explain(path))
                    with self.f.image(path, uid=250): self.assertIsNone(self.explain(path))
                    with self.f.image(path, xattrs={'user.extra': '00'}): self.assertIsNone(self.explain(path))
                    with self.f.content(path, after + b'neighbour:!::\n'): self.assertIsNone(self.explain(path))
                    with self.f.content(path + '.neighbour', after): self.assertIsNone(self.explain(path + '.neighbour'))

    def test_audit_accepts_only_the_exact_control_row_with_the_exact_installed_unit(self):
        path = self.f.UPDATERS
        existing = json.loads((self.root / path).read_text())
        row = dict(scope='system', name='aresos-toold.service', state='enabled', suspicious=False,
            commands=['ExecStart=' + next(line.split('=', 1)[1] for line in (ROOT / 'control/packaging/aresos-toold.service').read_text().splitlines() if line.startswith('ExecStart='))],
            sources=['/usr/lib/systemd/system/aresos-toold.service'], active_state=None, load_state=None, sub_state=None)
        def audit(rows):
            return json.dumps(sorted(rows, key=lambda r: (r['scope'], r['name']))).encode()
        with self.f.content(path, audit(existing + [row])):
            found = self.explain(path)
            self.assertIsNotNone(found)
            self.assertIn('aresos-toold.service', found[1])
            for key, wrong in (('name', 'aresos-toold-other.service'), ('state', 'disabled'), ('suspicious', True),
                               ('commands', []), ('sources', ['/usr/lib/systemd/system/neighbour.service'])):
                with self.subTest(key=key), self.f.content(path, audit(existing + [dict(row, **{key: wrong})])):
                    self.assertIsNone(self.explain(path))
            with self.f.content(path, audit(existing + [row, row])):
                self.assertIsNone(self.explain(path))
            with self.f.content(rd.CONTROL_UNIT, b'changed unit'):
                self.assertIsNone(self.explain(path))
        # Unchanged audit with a missing required row also fails the converse check.
        self.explain(path)
        self.assertIsNone(self.c.audit_rows())


class ControlAccountsTest(unittest.TestCase):
    ROWS = {'passwd': 'aresos-tools:x:250:250:AresOS tool service:/var/lib/aresos-tools:/usr/sbin/nologin',
            'group': 'aresos-tools:x:250:', 'shadow': 'aresos-tools:!*:20409::::::', 'gshadow': 'aresos-tools:!::'}
    OLD = {'passwd': 'root:x:0:0:root:/root:/bin/bash', 'group': 'root:x:0:',
           'shadow': 'root:!*:20400::::::', 'gshadow': 'root:!::'}

    def test_exact_account_addition_and_backup_rows(self):
        for kind, row in self.ROWS.items():
            for suffix in ('', '-'):
                path = 'etc/' + kind + suffix
                before, after = (self.OLD[kind] + '\n').encode(), (self.OLD[kind] + '\n' + row + '\n').encode()
                with self.subTest(path=path):
                    self.assertTrue(rd.control_accounts(path, before, after))
                    self.assertTrue(rd.control_accounts(path, after, after))
                    self.assertFalse(rd.control_accounts(path, after, before))
                    self.assertFalse(rd.control_accounts(path, before, after + b'neighbour:!::\n'))
                    self.assertFalse(rd.control_accounts(path, before, after + (row + '\n').encode()))
                    self.assertFalse(rd.control_accounts(path, before, after.replace(b'aresos-tools', b'aresos-other')))
                    for index in range(len(row.split(':'))):
                        parts = row.split(':')
                        parts[index] = 'unexpected'
                        with self.subTest(field=index):
                            self.assertFalse(rd.control_accounts(path, before, before + (':'.join(parts) + '\n').encode()))

    def test_other_rows_and_uid_gid_250_cannot_change(self):
        for kind, row in self.ROWS.items():
            before = (self.OLD[kind] + '\n').encode()
            after = before + (row + '\n').encode()
            with self.subTest(kind=kind):
                self.assertFalse(rd.control_accounts('etc/' + kind, before, after.replace(b'root:', b'other:', 1)))
        for kind, other in (('passwd', 'other:x:250:251::/nonexistent:/usr/sbin/nologin'),
                            ('passwd', 'other:x:251:250::/nonexistent:/usr/sbin/nologin'), ('group', 'other:x:250:')):
            before = (self.OLD[kind] + '\n' + other + '\n').encode()
            self.assertFalse(rd.control_accounts('etc/' + kind, before, before + (self.ROWS[kind] + '\n').encode()))


class ReleaseRecordTest(unittest.TestCase):
    def test_record_uses_image_source_revision_and_binds_control_with_all_image_sources(self):
        release = dict(source_commit='a' * 40, reference='fixture')
        control = dict(format=1, source_revision='a' * 40, files={'file': {}}, vendor={'folder': {}}, wheels=[{}])
        calls = []
        def output(argv, **kwargs):
            calls.append(argv)
            return 'b' * 40 + '\n'
        with patch.dict(os.environ, GITHUB_SHA='a' * 40), patch.object(subprocess, 'check_output', side_effect=output):
            result = release28_record.complete(release, control)
        self.assertEqual(result['control'], {'source_revision': control['source_revision']})
        self.assertEqual({r['path'] for r in result['source_trees']}, set(rd.IMAGE_SOURCES))
        self.assertIn(['git', 'rev-parse', 'HEAD:control'], calls)
        for changed in (dict(source_revision='b' * 40), dict(source_revision='bad'), dict(format=2), dict(format=True), dict(wheels=[]), dict(chrome_build='unreviewed')):
            with self.subTest(changed=changed), patch.dict(os.environ, GITHUB_SHA='a' * 40), self.assertRaises(AssertionError):
                release28_record.complete(release, dict(control, **changed))
        publish = (ROOT / 'os/ci/publish.sh').read_text()
        self.assertIn('if [[ $release == 28 ]]; then\n    python3 os/ci/release28_record.py evidence/release.json evidence/image/manifest/control.json', publish)


class VerifyControlBindingTest(unittest.TestCase):
    def verify(self, *, missing=None, changed=None, control_source=None, job=None):
        source = 'a' * 40
        trees = {path: hashlib.sha1(path.encode()).hexdigest() for path in rd.IMAGE_SOURCES}
        release = dict(source_commit=source, reference='ghcr.io/ares-empire/aresos@sha256:' + '28' * 32,
            visibility='private', base=json.loads((ROOT / 'os/manifest/base.json').read_text())['reference'],
            run='https://github.com/Ares-Empire/AresOS/actions/runs/101',
            signature=dict(method='cosign keyless', identity='https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/42-release-28',
                           issuer='https://token.actions.githubusercontent.com'), image_diff=dict(status='passed', unexplained=[]),
            job_token_read=dict(status='passed', owner_token_used=False), control=dict(source_revision=control_source or source),
            source_trees=[dict(tree=value, path=path) for path, value in trees.items() if path != missing])
        calls = []
        run = dict(head_sha=source, path='.github/workflows/os-image.yml', head_branch='pkg/42-release-28',
                   event='workflow_dispatch', display_title='Package 28 image release', run_attempt=1)
        def output(argv, **kwargs):
            calls.append(argv)
            if argv == ['git', 'rev-parse', '--is-shallow-repository']: return b'false\n'
            if argv[:2] == ['git', 'rev-parse']:
                path = argv[-1].removeprefix('HEAD:')
                return ((('c' * 40) if path == changed else trees[path]) + '\n').encode()
            self.assertEqual(argv[:2], ['gh', 'api'])
            data = dict(total_count=1, jobs=[dict(name=job or 'Package 28 release build, image diff, VM and publish', conclusion='success')]) if '/jobs?' in argv[-1] else run
            return json.dumps(data).encode()
        original = pathlib.Path.read_text
        def read(path, *args, **kwargs):
            return json.dumps(release) if path.as_posix() == 'evidence/release.json' else original(path, *args, **kwargs)
        code = (ROOT / 'os/ci/verify_release.py').read_text()
        with patch.object(sys, 'argv', ['verify_release.py', '101']), patch.dict(os.environ, GITHUB_REPOSITORY='Ares-Empire/AresOS'), \
                patch.object(pathlib.Path, 'read_text', read), patch.object(subprocess, 'check_output', side_effect=output), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as done:
            exec(compile(code, 'verify_release.py', 'exec'), {'__name__': '__main__'})
        self.assertEqual(done.exception.code, 0)
        return calls

    def test_control_and_every_os_source_is_bound(self):
        calls = self.verify()
        self.assertIn(['git', 'rev-parse', 'HEAD:control'], calls)
        for path in rd.IMAGE_SOURCES:
            with self.subTest(path=path), self.assertRaisesRegex(AssertionError, 'runtime payload changed'):
                self.verify(changed=path)
        for missing in ('control', 'os/build.sh'):
            with self.subTest(missing=missing), self.assertRaisesRegex(AssertionError, 'source paths differ'):
                self.verify(missing=missing)
        with self.assertRaisesRegex(AssertionError, 'Control source differs'):
            self.verify(control_source='d' * 40)
        with self.assertRaisesRegex(AssertionError, 'job must have succeeded'):
            self.verify(job='image')


class BranchRefTest(unittest.TestCase):
    def test_tags_or_missing_full_refs_stop_the_guard_before_api_reads(self):
        self.addCleanup(r28.guard.configure, '11c')
        fixture = r28.Guard42Test('test_resolve_and_checks_runs_stop_at_their_own_guard')
        for ref in ('refs/tags/pkg/42-release-28', '', 'pkg/42-release-28'):
            with self.subTest(ref=ref), self.assertRaisesRegex(AssertionError, 'branch ref is required'):
                fixture.run_main('ci', 'dry-run-28', ref=ref)

    def test_publish_rejects_tag_or_missing_ref_before_any_command(self):
        for ref in ('refs/tags/pkg/42-release-28', '', 'pkg/42-release-28'):
            env = dict(PATH=os.environ['PATH'], GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS',
                       GITHUB_REF_NAME='pkg/42-release-28', GITHUB_REF=ref)
            done = subprocess.run(['bash', 'os/ci/publish.sh'], cwd=ROOT, env=env, capture_output=True, text=True)
            with self.subTest(ref=ref):
                self.assertEqual(done.returncode, 1)
                self.assertIn('Refusing to publish without a branch ref', done.stderr)



class ControlBuildBytecodeTest(unittest.TestCase):
    """R28's fifth dry run (44514249982): the Control install's Python ran as root without -B and rewrote 353 of the
    base's own bytecode files (pip, attrs, the standard library), whose sources have mtime 0 in the image. Every
    Python run of build.sh's Control branch must leave /usr's bytecode alone."""

    def control_branch(self):
        text = (ROOT / 'os/build.sh').read_text()
        start = text.index('if [[ $1 == control || $1 == control-tree ]]; then')
        end = text.index('    rm -rf /tmp/ares-control\n    exit 0\nfi\n', start)
        return text[start:end]

    def test_every_python_run_writes_no_import_bytecode(self):
        runs = [line.strip() for line in self.control_branch().splitlines()
                if not line.lstrip().startswith('#') and ('python3 ' in line or 'python3\t' in line)]
        self.assertGreaterEqual(len(runs), 5, runs)
        for line in runs:
            self.assertRegex(line, r'python3 (-I )?-B ', line)

    def test_the_cli_check_runs_as_an_ordinary_user(self):
        branch = self.control_branch()
        self.assertIn('runuser -u nobody -- /usr/bin/aresos --help > /tmp/ares-control/help.txt\n', branch)
        self.assertNotRegex(branch, r'\n\s+/usr/bin/aresos --help')


if __name__ == '__main__':
    unittest.main()
