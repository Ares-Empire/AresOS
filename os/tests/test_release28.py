"""Package 42: release 28's diff rules, its release job and the dry run that cannot publish."""
import contextlib
import copy
import hashlib
import io
import json
import os
import pathlib
import re
import shlex
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
sys.path.insert(0, str(ROOT / 'os/tests'))
import build_tools
import image_diff
import registry_auth
import rehearsal_guard as guard
import release_diff as rd
import test_release27 as base
from test_ci_api_permissions import reachable
from test_owner_staged_release import condition

BRANCH = 'pkg/42-release-28'
WORKFLOW = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
FIXTURES = ROOT / 'os/tests/fixtures/release28-schemas'
OVERRIDE = (ROOT / 'os/config' / rd.SCHEMA_OVERRIDE).read_text()
# Package 31's reviewed theme checksum (reviews/31-window-frame/REVIEW-2.md, computed from the committed blobs).
PACKAGE31_CROWN = 'cf01b9b105fc38847e6bf6382056862f3c460d8fc6864cc6d0932794fbd2153e'
PACKAGE31_COMMIT = '29e4fbc6'
GITHUB = dict(base.UPDATE_GITHUB, GITHUB_REF_NAME=BRANCH, GITHUB_REF='refs/heads/' + BRANCH)


def corrupt_schema_lookup(data):
    """Corrupt only runtime lookup metadata, leaving all enumerated names and values intact."""
    start, end = struct.unpack_from('<II', data, 16)
    bloom, buckets = struct.unpack_from('<II', data, start)
    bucket_start = start + 8 + 4 * (bloom & ((1 << 27) - 1))
    first = bucket_start + 4 * buckets
    count = (end - first) // 24
    for index in range(count):
        _, _, key, size = struct.unpack_from('<IIIH', data, first + 24 * index)
        if data[key:key + size] == b'org.gnome.desktop.wm.preferences':
            hashed = bytearray(data)
            hashed[first + 24 * index] ^= 1
            break
    else:
        raise AssertionError('fixture must contain the reviewed schema')
    bucketed = bytearray(data)
    old = struct.unpack_from('<I', data, bucket_start)[0]
    struct.pack_into('<I', bucketed, bucket_start, (old + 1) % (count + 1))
    return {'hash': bytes(hashed), 'bucket': bytes(bucketed)}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def inputs(**changes):
    """A dispatch on the package 42 branch: no rehearsal, every other input off unless changed."""
    return dict(base.UPDATE_INPUTS, **{'github.ref_name': BRANCH, 'inputs.rehearsal': ''}, **changes)


def run_name(world):
    expression = re.fullmatch(r'\$\{\{(.*)\}\}', WORKFLOW['run-name'].strip()).group(1)
    for name, value in world.items():
        expression = expression.replace(name, repr(value))
    expression = re.sub(r'!(?!=)', ' not ', expression.replace('&&', ' and ').replace('||', ' or '))
    return eval(expression, {'__builtins__': {}}, {'format': lambda text, *values: text.format(*values)})


def job_steps(job, world):
    """Each run step of a job for this dispatch, with the environment it really gets."""
    merged = {**WORKFLOW.get('env', {}), **WORKFLOW['jobs'][job].get('env', {})}
    environment = dict(GITHUB, **{k: base.workflow_text(v, world) for k, v in merged.items()})
    for step in WORKFLOW['jobs'][job]['steps']:
        if 'run' in step and base.workflow_expression(step.get('if', 'success()'), world):
            yield step, dict(environment, **{k: base.workflow_text(v, world) for k, v in step.get('env', {}).items()})


def install_control_fixture(root):
    """The real install map plus a synthetic, locked wheel record; never install pip packages on this host."""
    result = subprocess.run(['bash', 'os/build.sh', 'control-tree', 'os', 'control', str(root)],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    record = json.loads((root / rd.CONTROL_RECORD).read_text())
    from test_control_image import lock_pins
    wheels = [dict(name=name, version=version, file=f'{name}-{version}-py3-none-any.whl', sha256=digests[0])
              for (name, version), digests in lock_pins().items()]
    vendor = root / 'usr/lib/aresos-control/vendor'
    vendor.mkdir(parents=True)
    (vendor / 'fixture.py').write_text('# synthetic wheel file\n')
    paths = [vendor.parent, vendor, vendor / 'fixture.py']
    for path in paths:
        path.chmod(0o755 if path.is_dir() else 0o644)
    record.update(source_revision='a' * 40, wheels=wheels, vendor={
        '/' + p.relative_to(root).as_posix(): dict(mode=f'{stat.S_IMODE(p.stat().st_mode):04o}',
            sha256=None if p.is_dir() else rd.file_sha256(p)) for p in paths})
    (root / rd.CONTROL_RECORD).write_text(json.dumps(record))
    return record


class Release27SourceTest(unittest.TestCase):
    def test_the_previous_source_holds_release_27s_recorded_trees_and_is_on_main(self):
        release = json.loads((ROOT / rd.PREVIOUS_28).read_text())
        self.assertEqual(len(release['source_trees']), 10)
        for row in release['source_trees']:
            with self.subTest(path=row['path']):
                self.assertEqual(git('rev-parse', rd.PREVIOUS_SOURCE_28 + ':' + row['path']), row['tree'])
        subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', rd.PREVIOUS_SOURCE_28, 'HEAD'], check=True)
        self.assertEqual(rd.RELEASES['28']['previous_release'], '27')
        historical = json.loads(git('show', '41b06513:os/owner-tools/payload/release.json'))
        self.assertEqual(release['reference'], historical['reference'])


class PackageDiff28Test(unittest.TestCase):
    def test_the_lock_change_since_release_27_is_package_23s_java(self):
        source = rd.PREVIOUS_SOURCE_28
        chrome = lambda raw: json.loads(raw)['nevra']
        old_lock = base.lock_nevras(rd.git_bytes(source, 'os/packages.lock.json'))
        old_lock.append(chrome(rd.git_bytes(source, 'os/google-chrome.lock.json')))
        new_lock = base.lock_nevras((ROOT / 'os/packages.lock.json').read_bytes())
        new_lock.append(chrome((ROOT / 'os/google-chrome.lock.json').read_bytes()))
        # Release 27's image: the base's packages (release 6's list) with its lock applied.
        installed = (ROOT / 'os/manifest/ci/06c/image-full-1/packages.txt').read_text().split()
        def image(lock):
            replaced = {(base.name_of(n), rd.arch(n)) for n in lock}
            return {n: base.name_of(n) for n in [n for n in installed if (base.name_of(n), rd.arch(n)) not in replaced] + lock}
        old, new = image(old_lock), image(new_lock)
        rows, added, removed = rd.package_diff(old, new, old_lock, new_lock, rd.PACKAGE_REASONS_28)
        self.assertEqual(added, ['java-25-openjdk-crypto-adapter-1:25.0.5.0.8-3.1.fc44.x86_64',
                                 'java-25-openjdk-headless-1:25.0.5.0.8-3.1.fc44.x86_64',
                                 'javapackages-filesystem-6.4.1-10.fc44.noarch', 'tzdata-java-2026f-1.fc44.noarch'])
        self.assertEqual(removed, [])
        self.assertTrue(all(row['reason'].startswith('package 23:') for row in rows))
        # Release 27's own changes are no reason in release 28.
        with self.assertRaisesRegex(AssertionError, 'unexplained package change'):
            rd.package_diff(old, new, old_lock, new_lock, {})
        self.assertNotIn('google-chrome-stable', rd.PACKAGE_REASONS_28)
        # A package that left the image without its locked replacement stops, even with a reason.
        old_image = dict(old, **{'gone-1-1.fc44.x86_64': 'gone'})
        with self.assertRaisesRegex(AssertionError, 'removed package without its locked replacement: gone-1-1.fc44.x86_64'):
            rd.package_diff(old_image, new, old_lock, new_lock, dict(rd.PACKAGE_REASONS_28, gone='made up'))


class SchemaTest(unittest.TestCase):
    """gschemas.compiled: only package 31's key may differ, and only by its override."""

    def compiled(self, name):
        return (FIXTURES / (name + '.compiled')).read_bytes()

    def test_the_reader_decodes_every_kind_of_value(self):
        entries = rd.gvdb_entries(self.compiled('before'))
        text = {name: rd.gv_text(*rd.gvariant('v', raw)) for name, raw in entries.items() if not name.endswith('/')}
        self.assertEqual(text['org.aresos.test/names'], "(['a', 'bc'],)")
        self.assertEqual(text['org.aresos.test/pairs'], "({'k': 'v'},)")
        self.assertEqual(text['org.aresos.test/point'], '((3, -4),)')
        self.assertEqual(text['org.aresos.test/maybe'], "(just 'x',)")
        self.assertEqual(text['org.aresos.test/flag'], '(true,)')
        self.assertEqual(text['org.aresos.test/big'], '(1234567890123,)')
        self.assertEqual(text['org.aresos.test/scale'], '(1.5,)')
        self.assertTrue(text['org.aresos.test/mode'].startswith("('off', (0x65, ["))
        self.assertEqual(text['org.gnome.desktop.wm.preferences/num-workspaces'], '(4, (0x72, (1, 36)))')
        self.assertEqual(text['org.gnome.desktop.wm.preferences/button-layout'], "('appmenu:close',)")
        self.assertEqual(entries['org.aresos.test//'], b'big\nflag\nmaybe\nmode\nnames\npairs\npoint\nscale')
        self.assertEqual(rd.schema_key(entries['org.gnome.desktop.wm.preferences/num-workspaces']), ('4', {'r': '(1, 36)'}))

    def test_package_31s_override_is_the_only_change_and_carries_its_value(self):
        rows = rd.schema_changes(self.compiled('before'), self.compiled('after'), OVERRIDE)
        self.assertEqual(rows, [dict(schema='org.gnome.desktop.wm.preferences', key='button-layout',
                                     before="('appmenu:close',)",
                                     after="('appmenu:close', (0x64, {'AresOS': <'appmenu:minimize,maximize,close'>}))")])
        self.assertEqual(rd.schema_overrides(OVERRIDE), {('org.gnome.desktop.wm.preferences', 'button-layout'): [
            ('AresOS', "'appmenu:minimize,maximize,close'")]})

    def test_any_other_change_stops(self):
        # Another key changed too (an override of another package).
        self.assertIsNone(rd.schema_changes(self.compiled('before'), self.compiled('extra'), OVERRIDE))
        # The override's value is not the one compiled, or it names a key the new file lacks.
        self.assertIsNone(rd.schema_changes(self.compiled('before'), self.compiled('after'), OVERRIDE.replace('minimize,', '')))
        self.assertIsNone(rd.schema_changes(self.compiled('before'), self.compiled('after'),
                                            OVERRIDE.replace('button-layout', 'missing-key')))
        # Without the override, the compiled key differs from what the override file says.
        self.assertIsNone(rd.schema_changes(self.compiled('after'), self.compiled('before'), OVERRIDE))
        self.assertEqual(rd.schema_changes(self.compiled('before'), self.compiled('before'), OVERRIDE), None)
        # Review 1, S4: a key's default changed beside the override's desktop value (another override set it), or
        # its choices changed: both stop, though the override's own value is there.
        self.assertIsNone(rd.schema_changes(self.compiled('before'), self.compiled('default'), OVERRIDE))
        self.assertIsNone(rd.schema_changes(self.compiled('before'), self.compiled('choices'), OVERRIDE))
        # Another desktop's value beside the override's (another override set it).
        self.assertIsNone(rd.schema_changes(self.compiled('before'), self.compiled('desktops'), OVERRIDE))
        # The override sets a key the new file does not carry with that value, although nothing else differs there.
        self.assertIsNone(rd.schema_changes(self.compiled('before'), self.compiled('after'),
                                            OVERRIDE + '[org.gnome.desktop.wm.preferences]\nnum-workspaces=5\n'))
        with self.assertRaises(ValueError):
            rd.gvdb_entries(b'not a compiled file' * 4)
        with self.assertRaises(ValueError):
            rd.gvariant('(si)', b'ab\0\0\0')


class SchemaRebuildTest(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp(dir=ROOT / 'os/tests'))
        self.addCleanup(shutil.rmtree, self.work)
        self.schemas, self.output = self.work / 'schemas', self.work / 'output'
        self.schemas.mkdir()
        self.output.mkdir()
        self.expected = (FIXTURES / 'after.compiled').read_bytes()
        self.compiled = self.schemas / 'gschemas.compiled'
        self.compiled.write_bytes(self.expected)
        # An image compiler stand-in: an independent deterministic result, never the file under test.
        self.compiler = self.work / 'compiler'
        self.compiler.write_text(f'#!{sys.executable}\nimport pathlib, sys\n'
                                 f'assert sys.argv[1:] == ["--strict", "--targetdir={self.output}", "{self.schemas}"]\n'
                                 f'pathlib.Path({str(self.output / "gschemas.compiled")!r}).write_bytes(bytes.fromhex({self.expected.hex()!r}))\n')
        self.compiler.chmod(0o755)
        self.enterContext(patch.object(image_diff, 'command', side_effect=self.command))

    def command(self, *args):
        self.assertEqual(args[:-1], ('podman', 'run', '--pull=never', '--network=none', '--read-only', '--rm',
                                    '--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m', '--entrypoint=/usr/bin/python3', rd.NEW, '-c'))
        program = args[-1].replace('/usr/bin/glib-compile-schemas', str(self.compiler)) \
            .replace('/usr/share/glib-2.0/schemas', str(self.schemas)) \
            .replace("'--targetdir=/tmp'", repr('--targetdir=' + str(self.output))) \
            .replace("'/tmp/gschemas.compiled'", repr(str(self.output / 'gschemas.compiled')))
        # Execute the actual comparison program; a stand-in container only substitutes its paths.
        return subprocess.check_output([sys.executable, '-c', program], text=True, stderr=subprocess.PIPE).strip()

    def test_rebuild_checks_the_actual_bytes_including_hashes_and_buckets(self):
        self.assertTrue(rd.rebuild_schemas(rd.NEW)['matches'])
        for kind, corrupt in corrupt_schema_lookup(self.expected).items():
            with self.subTest(kind=kind):
                self.compiled.write_bytes(corrupt)
                result = rd.rebuild_schemas(rd.NEW)
                self.assertFalse(result['matches'])
                self.assertNotEqual(result['exit_code'], 0)
        # A compiler failure also stops; no accepted result can be inferred from an old output file.
        self.compiled.write_bytes(self.expected)
        self.compiler.write_text(f'#!{sys.executable}\nraise SystemExit(7)\n')
        self.assertFalse(rd.rebuild_schemas(rd.NEW)['matches'])


class FontCacheTest(unittest.TestCase):
    FIXTURES = ROOT / 'os/tests/fixtures/release28-fontcache'
    ARESOS = '/usr/share/fonts/aresos'

    @staticmethod
    def cache(folder, version=9, magic=rd.FONT_CACHE_MAGIC, layout='le64', offset=None):
        """A minimal cache in one of fontconfig's formats: its header, then the folder's name (at `offset`)."""
        header, end_of_header = rd.FONT_CACHE_LAYOUTS[layout]
        offset = end_of_header if offset is None else offset
        name = folder.encode() + b'\0'
        start = struct.pack(header, magic, version, 0, offset).ljust(end_of_header, b'\0')
        data = bytearray(start[:offset] + name + bytes(8) if offset < end_of_header else start + bytes(offset - end_of_header) + name + bytes(8))
        struct.pack_into(header, data, 0, magic, version, len(data), offset)
        return bytes(data)

    def test_the_cache_names_its_folder(self):
        for layout in rd.FONT_CACHE_LAYOUTS:
            with self.subTest(layout=layout):
                self.assertEqual(rd.font_cache(self.cache(self.ARESOS, layout=layout), layout), (9, self.ARESOS))
                # A name inside the header is no cache (the folder's name follows the header).
                inside = rd.FONT_CACHE_LAYOUTS[layout][1] - 8
                for data in (self.cache('/x', magic=0x1234, layout=layout), self.cache('relative', layout=layout), b'short',
                             self.cache('/x', layout=layout)[:-1], self.cache('/x', layout=layout, offset=inside)):
                    with self.subTest(data=data[:8]), self.assertRaises(ValueError):
                        rd.font_cache(data, layout)

    def test_real_caches_of_both_formats_are_read_and_each_only_in_its_own_format(self):
        # fontconfig 2.17's fc-cache-32 and fc-cache-64 output for 23b's folder (SOURCE.txt).
        digest = hashlib.md5(self.ARESOS.encode()).hexdigest()
        for layout, other in (('le32d4', 'le64'), ('le64', 'le32d4')):
            with self.subTest(layout=layout):
                data = (self.FIXTURES / f'{digest}-{layout}.cache-9').read_bytes()
                self.assertEqual(rd.font_cache(data, layout), (9, self.ARESOS))
                with self.assertRaises(ValueError):
                    rd.font_cache(data, other)


class SourceChangesTest(unittest.TestCase):
    """Review 1, S2: the image's sources on the built commit are main's at the merge base, but for the jar's pin."""
    LOCK = 'os/minecraft/desktop.lock.json'

    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp(dir=ROOT / 'os/tests'))
        self.addCleanup(shutil.rmtree, self.repo)
        self.enterContext(contextlib.chdir(self.repo))
        self.environment = dict(os.environ, GIT_AUTHOR_NAME='fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                                GIT_COMMITTER_NAME='fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.git('init', '-q', '-b', 'main')
        lock = dict(prism=dict(version='1'), mods=[dict(file='fabric-api.jar', url='https://example.invalid/f.jar', sha256='f' * 64),
                                                   dict(file='aresos.jar', name='AresOS', sha256='a' * 64)])
        self.write({self.LOCK: json.dumps(lock, indent=2) + '\n', 'os/build.sh': 'build\n', 'os/config/etc/x': 'x\n',
                    'os/tests/audit.py': 'audit\n', 'os/tests/test_x.py': 'test\n', 'os/ci/x.py': 'ci\n',
                    'mod/src/A.java': 'class A {}\n', 'docs/x.md': 'doc\n'})
        self.base = self.commit('main')
        self.lock = lock

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, env=self.environment, text=True).strip()

    def write(self, files):
        for rel, text in files.items():
            path = self.repo / rel
            if text is None:
                path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def lock_text(self, jar=None, **changes):
        lock = json.loads(json.dumps(self.lock))
        lock.update(changes)
        if jar:
            lock['mods'][1]['sha256'] = jar
        return json.dumps(lock, indent=2) + '\n'

    def test_only_the_jar_pin_and_files_the_image_is_not_built_from_may_differ(self):
        self.write({self.LOCK: self.lock_text(jar='b' * 64), 'os/tests/test_x.py': 'changed\n', 'os/ci/x.py': 'changed\n',
                    'docs/x.md': None})
        self.commit('branch: the jar pin and harness files')
        allowed, differing = rd.source_changes(self.base)
        self.assertEqual((allowed, differing), ({self.LOCK: rd.BRANCH_SOURCE_CHANGES[self.LOCK][0]}, []))
        self.assertEqual(rd.source_changes(self.base, self.base), ({}, []))

    def test_every_other_source_change_is_named(self):
        cases = {
            'os/config/etc/x': {'os/config/etc/x': 'changed on the branch\n'},
            'os/config/etc/new': {'os/config/etc/new': 'new\n'},
            'os/build.sh': {'os/build.sh': None},
            'os/tests/audit.py': {'os/tests/audit.py': 'changed\n'},
            'mod/src/B.java': {'mod/src/B.java': 'class B {}\n'},
            'control/launch.py': {'control/launch.py': '# changed Control source\n'},
            self.LOCK: {self.LOCK: self.lock_text(jar='b' * 64, prism=dict(version='2'))},
        }
        for name, files in cases.items():
            with self.subTest(name=name):
                self.git('checkout', '-q', '-B', 'branch', self.base)
                self.write(files)
                self.commit('branch: ' + name)
                self.assertEqual(rd.source_changes(self.base), ({}, [name]))
        # Two at once: each is named.
        self.git('checkout', '-q', '-B', 'branch', self.base)
        self.write({'os/config/etc/x': 'changed\n', 'mod/src/A.java': 'class A { int x; }\n', self.LOCK: self.lock_text(jar='c' * 64)})
        self.commit('branch: two changes and the pin')
        self.assertEqual(rd.source_changes(self.base), ({self.LOCK: rd.BRANCH_SOURCE_CHANGES[self.LOCK][0]},
                                                        ['mod/src/A.java', 'os/config/etc/x']))

    def test_the_merge_base_follows_main_merged_in_at_the_cut(self):
        # Step 4 merges main at the cut: the base moves to main's commit, and the branch's own change still is only the pin.
        self.git('checkout', '-q', '-b', 'branch')
        self.write({self.LOCK: self.lock_text(jar='b' * 64)})
        self.commit('branch: the jar pin')
        self.git('checkout', '-q', 'main')
        self.write({'os/config/etc/x': 'a merged package\n', 'mod/src/A.java': 'class A { int merged; }\n'})
        cut = self.commit('Package 99: a merged change (#99)')
        self.git('checkout', '-q', 'branch')
        self.git('merge', '-q', '--no-edit', 'main')
        self.git('update-ref', 'refs/remotes/origin/main', cut)
        self.assertEqual(rd.main_merge_base(), cut)
        self.assertEqual(rd.source_changes(cut), ({self.LOCK: rd.BRANCH_SOURCE_CHANGES[self.LOCK][0]}, []))
        # A wrong resolution of the merge (the old file kept) is a difference from main.
        self.write({'os/config/etc/x': 'x\n'})
        self.commit('branch: wrong resolution')
        self.assertEqual(rd.source_changes(cut)[1], ['os/config/etc/x'])
        # Without main in the checkout, the diff stops at once with a line that says why.
        self.git('update-ref', '-d', 'refs/remotes/origin/main')
        with self.assertRaisesRegex(AssertionError, 'STOP: no merge base with origin/main'):
            rd.main_merge_base()

    def test_the_jar_pin_rule(self):
        same = self.lock_text()
        self.assertTrue(rd.jar_pin_only(same, self.lock_text(jar='b' * 64)))
        self.assertTrue(rd.jar_pin_only(same, same))
        for other in (self.lock_text(jar='b' * 64, prism=dict(version='2')), self.lock_text(mods=self.lock['mods'][:1]),
                      self.lock_text(mods=self.lock['mods'] + [dict(file='aresos.jar', sha256='c' * 64)]), '{', None):
            with self.subTest(other=other):
                self.assertFalse(rd.jar_pin_only(same, other))
                self.assertFalse(rd.jar_pin_only(other, same))
        # Another mod's pin is not the AresOS jar's.
        fabric = json.loads(same)
        fabric['mods'][0]['sha256'] = 'e' * 64
        self.assertFalse(rd.jar_pin_only(same, json.dumps(fabric)))

    def test_a_jar_pin_renewal_cannot_change_the_git_mode_or_type(self):
        for kind in ('executable', 'symlink'):
            with self.subTest(kind=kind):
                self.git('checkout', '-q', '-B', 'branch', self.base)
                self.write({self.LOCK: self.lock_text(jar='b' * 64)})
                path = self.repo / self.LOCK
                if kind == 'executable':
                    path.chmod(0o755)
                else:
                    # A link's blob can itself be parseable JSON; content validation alone is insufficient.
                    text = path.read_text()
                    path.unlink()
                    path.symlink_to(text)
                self.commit('branch: pin with another mode or type')
                self.assertEqual(rd.source_changes(self.base), ({}, [self.LOCK]))


class ImageSourcesTest(unittest.TestCase):
    def test_this_branch_changes_no_image_source_but_the_jar_pin(self):
        with contextlib.chdir(ROOT):
            try:
                main_base = rd.main_merge_base()
            except AssertionError:
                self.skipTest('this checkout has no origin/main')
            allowed, differing = rd.source_changes(main_base)
        self.assertEqual(differing, [])
        self.assertLessEqual(set(allowed), set(rd.BRANCH_SOURCE_CHANGES))

    def test_the_cut_fix_is_the_only_build_sh_change_allowed(self):
        # Review 11: exactly CUT_BYTECODE_FIX on main's build.sh at the cut, and nothing else, passes the source stop.
        with contextlib.chdir(ROOT):
            try:
                main_base = rd.main_merge_base()
            except AssertionError:
                self.skipTest('this checkout has no origin/main')
            before = rd.blob(main_base, 'os/build.sh')
        after = (ROOT / 'os/build.sh').read_bytes()
        self.assertTrue(rd.cut_bytecode_fix_only(before, after))
        self.assertFalse(rd.cut_bytecode_fix_only(before, after + b'echo extra\n'))
        self.assertFalse(rd.cut_bytecode_fix_only(before, before))
        self.assertFalse(rd.cut_bytecode_fix_only(before, after.replace(b'--clear-groups', b'--keep-groups')))
        self.assertFalse(rd.cut_bytecode_fix_only(None, after))

    def test_the_source_list_covers_what_the_build_reads(self):
        build, containerfile = (ROOT / 'os/build.sh').read_text(), (ROOT / 'os/Containerfile').read_text()
        # check-build.sh builds os/Containerfile with os/ as its context; the Containerfile copies it to /tmp/aresos.
        self.assertIn('--file os/Containerfile os ', (ROOT / 'os/ci/check-build.sh').read_text())
        self.assertIn('\nCOPY . /tmp/aresos/\n', containerfile)
        read = {os.path.normpath(rel) for rel in re.findall(r'/tmp/aresos/([\w.-]+(?:/[\w.-]+)*)', build + containerfile)}
        read -= {'ci'}  # the Containerfile checks it is absent (os/.containerignore)
        self.assertLessEqual({'packages.lock.json', 'google-chrome.lock.json', 'minecraft/desktop.lock.json', 'build.sh',
                              'tests/audit.py', 'policy', 'config'}, read)
        for rel in sorted(read):
            with self.subTest(rel=rel):
                path = rel if rel == 'control' or rel.startswith('control/') else 'os/' + rel
                self.assertTrue(any((path + '/').startswith(source + '/') for source in rd.IMAGE_SOURCES), rel)
        # Chrome's signing key, named by its lock; the source stage keeps only mod/ of this commit.
        key = json.loads((ROOT / 'os/google-chrome.lock.json').read_text())['signing_key']['file']
        self.assertTrue(('os/' + key).startswith('os/keys/'))
        self.assertIn('keep only mod/', build)
        self.assertIn('mod', rd.IMAGE_SOURCES)
        self.assertIn('control', rd.IMAGE_SOURCES)
        self.assertIn('os/.containerignore', rd.IMAGE_SOURCES)
        # Every listed source exists here, and the branch's exceptions are among them.
        for source in rd.IMAGE_SOURCES:
            self.assertTrue((ROOT / source).exists(), source)
        # The jar pin, and the cut's build.sh fix (review 11), which test_the_cut_fix_is_the_only_build_sh_change_allowed holds.
        self.assertEqual(set(rd.BRANCH_SOURCE_CHANGES), {'os/minecraft/desktop.lock.json', 'os/build.sh'})


class PrismListPinTest(unittest.TestCase):
    def test_the_reviewed_prism_list_belongs_to_the_pinned_prism(self):
        # Review 1, N4: dry run 3's prism-files.sha256 (run 43847257976, 679 files), for the Prism tarball the lock pins.
        lock = json.loads((ROOT / 'os/minecraft/desktop.lock.json').read_text())
        self.assertEqual(rd.PRISM_FILE_LISTS, {lock['prism']['sha256']: '9df32315bf6a3116992df8df23387f1cf5d060bf1c655cfae9cf89ed00994a03'})


class PrismInventoryTest(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp(dir=ROOT / 'os/tests'))
        self.addCleanup(shutil.rmtree, self.work)

    def archive(self, target='bin/prismlauncher'):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, raw in (('bin/prismlauncher', b'prism'), ('portable.txt', b''), ('bin/prismlauncher_updater', b'updater'),
                              ('shared/bin/prismlauncher_updater', b'updater')):
                member = tarfile.TarInfo(name)
                member.size, member.mode = len(raw), 0o755 if name.startswith('bin/') else 0o644
                archive.addfile(member, io.BytesIO(raw))
            member = tarfile.TarInfo('libprism.so')
            member.type, member.linkname = tarfile.SYMTYPE, target
            archive.addfile(member)
        raw = stream.getvalue()
        return raw, dict(url='https://example.invalid/prism.tar.gz', sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))

    def test_the_pinned_archive_binds_every_type_mode_target_and_expected_path(self):
        raw, pin = self.archive()
        with patch.object(rd.urllib.request, 'urlopen', return_value=io.BytesIO(raw)) as download:
            expected = rd.prism_inventory(pin, self.work)
        self.assertEqual(download.call_args.args, (pin['url'],))
        self.assertEqual(set(expected), {rd.PRISM, *(rd.PRISM + '/' + path for path in
                          ('bin', 'bin/prismlauncher', 'libprism.so', 'shared', 'shared/bin'))})
        self.assertEqual(expected[rd.PRISM + '/bin/prismlauncher'], dict(kind=stat.S_IFREG, mode=0o755, uid=0, gid=0,
                         xattrs={}, bytes=5, sha256=hashlib.sha256(b'prism').hexdigest()))
        self.assertEqual(expected[rd.PRISM + '/libprism.so'], dict(kind=stat.S_IFLNK, mode=0o777, uid=0, gid=0,
                                                                 xattrs={}, target='bin/prismlauncher'))
        self.assertEqual(expected[rd.PRISM]['mode'], 0o755)
        with patch.object(rd.urllib.request, 'urlopen', side_effect=AssertionError('verified cache must be reused')):
            self.assertEqual(rd.prism_inventory(pin, self.work), expected)
            with contextlib.chdir(self.work.parent):
                self.assertEqual(rd.prism_inventory(pin, self.work.name), expected)
        self.assertEqual([path.name for path in self.work.iterdir()], ['prism-' + pin['sha256'] + '.tar.gz'])

    def test_a_bad_archive_pin_is_fatal_and_partial_or_unverified_copies_do_not_survive(self):
        raw, pin = self.archive()
        for change in (dict(sha256='0' * 64), dict(size=pin['size'] + 1)):
            with self.subTest(change=change), patch.object(rd.urllib.request, 'urlopen', return_value=io.BytesIO(raw)):
                with self.assertRaisesRegex(AssertionError, 'Prism archive differs from its pin'):
                    rd.prism_inventory(dict(pin, **change), self.work)
                self.assertEqual(list(self.work.iterdir()), [])
        cached = self.work / ('prism-' + pin['sha256'] + '.tar.gz')
        cached.write_bytes(b'corrupt cached archive')
        with self.assertRaisesRegex(AssertionError, 'cached Prism archive differs from its pin'):
            rd.prism_inventory(pin, self.work)
        self.assertFalse(cached.exists())

    def test_even_a_pinned_archive_must_not_supply_a_dangling_or_escaping_link(self):
        for target in ('missing.so', '../outside'):
            raw, pin = self.archive(target)
            with self.subTest(target=target), patch.object(rd.urllib.request, 'urlopen', return_value=io.BytesIO(raw)):
                with self.assertRaises((FileNotFoundError, tarfile.FilterError, AssertionError)):
                    rd.prism_inventory(pin, self.work)
                self.assertFalse(any(path.is_dir() for path in self.work.iterdir()))


class AlternativesAdminTest(unittest.TestCase):
    @staticmethod
    def scriptlet_groups():
        """Independent expectations from the committed, pinned RPM's postinstall scriptlet."""
        source = ROOT / 'reviews/23-minecraft-starts/runs/resolve-43466199049/candidate.txt'
        script = source.read_text().split('postinstall scriptlet (using /bin/sh):', 1)[1].split('preuninstall scriptlet', 1)[0]
        groups = {}
        for line in script.replace('\\\n', ' ').splitlines():
            args = shlex.split(line)
            if args[:2] == ['alternatives', '--install']:
                public, group, target, priority, *slaves = args[2:]
                links, targets = {public: group}, {group: target}
                for at in range(0, len(slaves), 4):
                    flag, public, name, target = slaves[at:at + 4]
                    assert flag == '--slave'
                    links[public], targets[name] = name, target
                groups[group] = dict(links=links, choices=[dict(priority=int(priority), targets=targets)])
            elif args[:2] == ['alternatives', '--add-slave']:
                group, master, public, name, target = args[2:]
                choice, = groups[group]['choices']
                assert choice['targets'][group] == master
                groups[group]['links'][public], choice['targets'][name] = name, target
        return groups

    def test_reviewed_manifest_matches_the_pinned_scriptlets_and_all_observed_groups(self):
        lock = json.loads((ROOT / 'os/packages.lock.json').read_text())
        packages = dict(new=[package['nevra'] for package in lock['packages']])
        expected = self.scriptlet_groups()
        self.assertEqual(set(expected), {'java', 'jre_openjdk', 'jre_25', 'jre_25_openjdk'})
        self.assertEqual(sum(len(group['links']) for group in expected.values()), 12)
        self.assertEqual(rd.reviewed_alternatives(packages), expected)
        manifest = json.loads((ROOT / rd.ALTERNATIVES_MANIFEST_28).read_text())
        resolved = json.loads((ROOT / 'reviews/23-minecraft-starts/runs/resolve-43466199049/candidate-packages.lock.json').read_text())
        self.assertIn(manifest['package'], resolved['packages'])

    def test_the_manifest_stops_on_a_renewed_nevra_or_hash_or_an_absent_package(self):
        lock = json.loads((ROOT / 'os/packages.lock.json').read_text())
        package, = [row for row in lock['packages'] if row['nevra'].startswith('java-25-openjdk-headless-')]
        for change in ({'sha256': '0' * 64}, {'nevra': package['nevra'].replace('3.1.fc44', '3.2.fc44')}):
            changed = copy.deepcopy(lock)
            next(row for row in changed['packages'] if row['nevra'] == package['nevra']).update(change)
            read_text = pathlib.Path.read_text
            def source_text(path, *args, **kwargs):
                return json.dumps(changed) if str(path) == 'os/packages.lock.json' else read_text(path, *args, **kwargs)
            with self.subTest(change=change), patch.object(pathlib.Path, 'read_text', source_text):
                with self.assertRaisesRegex(AssertionError, 'alternatives manifest does not match'):
                    rd.reviewed_alternatives(dict(new=[package['nevra']]))
        with self.assertRaisesRegex(AssertionError, 'alternatives manifest does not match'):
            rd.reviewed_alternatives(dict(new=[]))

    def test_links_and_targets_are_read_with_and_without_a_family(self):
        plain = b'auto\n/usr/bin/ld\n\n/usr/bin/ld.bfd\n50\n'
        self.assertEqual(rd.alternatives_admin(plain), dict(mode='auto', links={'/usr/bin/ld': None},
                                                          choices=[dict(priority=50, targets={None: '/usr/bin/ld.bfd'})]))
        java = (b'auto\n/usr/bin/java\nkeytool\n/usr/bin/keytool\njre\n/usr/lib/jvm/jre\n\n'
                b'/usr/lib/jvm/java-25/bin/java\n@java-25-openjdk.x86_64@25000500\n/usr/lib/jvm/java-25/bin/keytool\n\n')
        record = rd.alternatives_admin(java)
        self.assertEqual(record['links'], {'/usr/bin/java': None, '/usr/bin/keytool': 'keytool', '/usr/lib/jvm/jre': 'jre'})
        self.assertEqual(record['choices'], [dict(priority=25000500, targets={None: '/usr/lib/jvm/java-25/bin/java',
                                                                            'keytool': '/usr/lib/jvm/java-25/bin/keytool', 'jre': ''})])
        for bad in (b'maybe\n/usr/bin/ld\n\n/usr/bin/ld.bfd\n50\n', b'auto\nld\n\n/usr/bin/ld.bfd\n50\n',
                    b'auto\n/usr/bin/ld\n\n', b'auto\n/usr/bin/ld\n\n/usr/bin/ld.bfd\nfifty\n'):
            with self.subTest(bad=bad):
                self.assertIsNone(rd.alternatives_admin(bad))

    def test_the_entire_record_structure_is_required(self):
        record = b'auto\n/usr/bin/java\nkeytool\n/usr/bin/keytool\n\n/jdk/bin/java\n25\n/jdk/bin/keytool\n'
        for bad in (record.replace(b'25\n', b''), record.replace(b'25\n', b'25\n99\n'),
                    record.removesuffix(b'/jdk/bin/keytool\n'), record + b'7\n', record[:-1],
                    record.replace(b'keytool\n/usr/bin/keytool', b'bad/name\n/usr/bin/keytool'),
                    record.replace(b'\n\n/jdk', b'\nkeytool\n/usr/bin/other\n\n/jdk'),
                    record.replace(b'/usr/bin/keytool', b'/usr/bin/java'),
                    record.replace(b'/jdk/bin/keytool', b'/jdk/../bin/keytool'),
                    record.replace(b'/jdk/bin/java\n25', b'@java@/jdk/bin/java\n25'),
                    record.replace(b'25\n', b'@@25\n'), record.replace(b'25\n', b'@unterminated25\n'),
                    record.replace(b'25\n', b'25 unexpected-service\n')):
            with self.subTest(bad=bad):
                self.assertIsNone(rd.alternatives_admin(bad))
        # Multiple alternatives retain separate target maps; an empty slave consumes its own line.
        multiple = record + b'/other/bin/java\n20\n\n'
        parsed = rd.alternatives_admin(multiple)
        self.assertEqual(parsed['choices'][1], dict(priority=20, targets={None: '/other/bin/java', 'keytool': ''}))


class ThemeAndRcXmlTest(unittest.TestCase):
    def test_the_theme_checksum_in_image_checks_is_package_31s(self):
        # brief 42, A.3: a theme change moves its checksum; release 28 carries package 31's theme unchanged.
        self.assertEqual(rd.crown_pin(ROOT / 'os/ci/image-checks.sh'), PACKAGE31_CROWN)
        self.assertEqual(rd.crown_digest(ROOT / 'os/config' / rd.CROWN), PACKAGE31_CROWN)
        theme = 'os/config/usr/share/themes/Ares-Crown'
        self.assertEqual(git('rev-parse', 'HEAD:' + theme), git('rev-parse', PACKAGE31_COMMIT + ':' + theme))
        self.assertIn(PACKAGE31_CROWN, git('show', PACKAGE31_COMMIT + ':os/ci/image-checks.sh'))

    def test_the_rc_xml_changes_since_release_27_are_23s_23bs_31s_and_40s(self):
        old = subprocess.check_output(['git', '-C', str(ROOT), 'show', rd.PREVIOUS_SOURCE_28 + ':os/config/' + rd.RC_XML])
        changes = rd.rc_xml_changes(old, (ROOT / 'os/config' / rd.RC_XML).read_bytes())
        self.assertEqual([row.split(':')[0] for row in changes['removed']], ['keyboard', 'theme'])
        self.assertIn('<name>Default</name>', changes['removed'][1])
        added = changes['added']
        self.assertEqual([row.split(':')[0] for row in added],
                         ['keyboard', 'theme', 'windowRules', 'windowRules', 'windowRules', 'windowSwitcher'])
        self.assertIn('aresos-desktop hide-cover', added[0])  # 23b: the recovery keys end the cover
        self.assertIn('<name>Ares-Crown</name>', added[1])  # 31: the frame
        rules = ' '.join(added[2:5])
        self.assertIn('identifier="aresos-desktop" serverDecoration="no"', rules)  # 23: the borderless game
        self.assertIn('ToggleAlwaysOnBottom', rules)  # 40: apps stay above the world
        self.assertIn('identifier="aresos.cover"', rules)  # 23b: the cover
        # Comments and layout are not settings.
        self.assertEqual(rd.rc_xml_changes(old, old.replace(b'<keyboard>', b'<!-- note -->\n  <keyboard>')),
                         dict(added=[], removed=[]))

    def test_the_executables_are_build_sh_s_chmod_line(self):
        script = (ROOT / 'os/build.sh').read_text()
        line = re.search(r'^chmod 0755 ((?:[^\n]*\\\n)*[^\n]*)$', script, re.M).group(1)
        self.assertEqual(rd.CHMOD_0755_28, {path.lstrip('/') for path in line.replace('\\\n', ' ').split()})
        self.assertIn(f'ln -sfn {rd.DESKTOP_COMMAND[1]} /{rd.DESKTOP_COMMAND[0]}', script)
        self.assertIn(f"os.symlink('{rd.PRISM_COMMAND[1]}', '/{rd.PRISM_COMMAND[0]}')", script)
        self.assertIn('glib-compile-schemas --strict /usr/share/glib-2.0/schemas', script)
        self.assertIn('fc-cache --system-only --really-force', script)


@unittest.skipIf(os.name == 'nt', 'symlinks and modes need Linux')
class Classifier28Test(unittest.TestCase):
    """Each release 28 rule explains exactly its own paths; near misses stay unexplained."""
    JAVA = '/usr/lib/jvm/java-25/bin/java'
    KEYTOOL = '/usr/lib/jvm/java-25/bin/keytool'
    STEAM = 'usr/share/aresos/apps/hints/steam.json'
    CACHE_FOLDER = '/usr/share/fonts/aresos'
    # The base's link to a font folder, which fc-cache caches under the link's own name.
    LINKED = '/usr/share/fonts/noto-cjk'
    LINK_TARGET = '/usr/share/fonts/google-noto-sans-cjk-fonts'
    UPDATERS = 'usr/share/aresos/manifest/updaters.json'
    DROPIN = 'usr/lib/systemd/system/user.slice.d/50-aresos-recovery.conf'  # package 23's
    CONSOLE_UNIT = 'usr/lib/systemd/system/aresos-console-keymap.service'
    CONSOLE_LINK = 'etc/systemd/system/graphical.target.wants/aresos-console-keymap.service'
    JAVA_MAN = 'usr/lib/jvm/java-25-openjdk/man/man1/java.1'
    CACERTS = 'usr/lib/jvm/java-25/lib/security/cacerts'  # a link of the package, as Java's is
    LOCK = 'usr/share/aresos/manifest/packages.lock.json'
    PACKAGES = 'usr/share/aresos/manifest/packages.txt'
    INSTALLED = ['java-25-openjdk-headless-1:25.0.5.0.8-3.1.fc44.x86_64', 'tzdata-java-2026f-1.fc44.noarch']

    @staticmethod
    def audit(*added, console_keymap=False, **changes):
        """An updater audit (os/tests/audit.py's output) of two units; user.slice gains `added` and `changes`."""
        unit = lambda name, sources: dict(scope='system', name=name, state='static', suspicious=False, commands=[],
                                          active_state=None, load_state=None, sub_state=None, sources=sources)
        units = [unit('ModemManager.service', ['/usr/lib/systemd/system/ModemManager.service']),
                 dict(unit('user.slice', ['/usr/lib/systemd/system/user.slice', *added]), **changes)]
        if console_keymap:
            # Independent expectation from package 50's release note, not the classifier's constant.
            units.append(dict(scope='system', name='aresos-console-keymap.service', state='enabled', suspicious=False,
                              commands=['ExecStart=/usr/lib/systemd/systemd-vconsole-setup /dev/tty3'],
                              sources=['/usr/lib/systemd/system/aresos-console-keymap.service'],
                              active_state=None, load_state=None, sub_state=None))
            units.sort(key=lambda row: (row['scope'], row['name']))
        return json.dumps(units, indent=2).encode() + b'\n'

    @staticmethod
    def cache_paths(folder):
        digest = hashlib.md5(folder.encode()).hexdigest()
        return {layout: f'{rd.FONT_CACHES}{digest}-{layout}.cache-9' for layout in rd.FONT_CACHE_LAYOUTS}

    def setUp(self):
        self.enterContext(contextlib.chdir(ROOT))
        cache = FontCacheTest.cache(self.CACHE_FOLDER)
        self.cache_path = self.cache_paths(self.CACHE_FOLDER)['le64']
        self.cache_path32 = self.cache_paths(self.CACHE_FOLDER)['le32d4']
        caches = {self.cache_path32: FontCacheTest.cache(self.CACHE_FOLDER, layout='le32d4'),
                  **{path: FontCacheTest.cache(self.LINKED, layout=layout) for layout, path in self.cache_paths(self.LINKED).items()}}
        prism = {'usr/lib/prismlauncher/bin/prismlauncher': b'prism', 'usr/lib/prismlauncher/lib/libq.so.6.1': b'qt'}
        listing = ''.join(f'{hashlib.sha256(raw).hexdigest()}  /{rel}\n' for rel, raw in sorted(prism.items()))
        shadow = b'root:!*:20384:0:99999:7:::\nares:!*:20402::::::\n'
        old = {'etc/shadow': shadow, rd.SCHEMAS: (FIXTURES / 'before.compiled').read_bytes(),
               'usr/share/aresos/apps/terminal.json': b'{}', self.LINKED[1:]: ('link', self.LINK_TARGET),
               self.UPDATERS: self.audit()}
        new = {'etc/shadow': shadow.replace(b'20402', b'20408'), rd.SCHEMAS: (FIXTURES / 'after.compiled').read_bytes(),
               self.LINKED[1:]: ('link', self.LINK_TARGET), **caches, self.UPDATERS: self.audit('/' + self.DROPIN),
               self.DROPIN: (ROOT / 'os/config' / self.DROPIN).read_bytes(), self.JAVA_MAN: b'.TH java 1\n',
               rd.SCHEMA_OVERRIDE: OVERRIDE.encode(), 'usr/share/aresos/apps/terminal.json': b'{}',
               self.STEAM: (ROOT / 'os/config' / self.STEAM).read_bytes(),
               rd.DESKTOP_COMMAND[0]: ('link', rd.DESKTOP_COMMAND[1]), rd.PRISM_COMMAND[0]: ('link', rd.PRISM_COMMAND[1]),
               **prism, 'usr/lib/prismlauncher/lib/libq.so.6': ('link', 'libq.so.6.1'), rd.PRISM_FILES: listing.encode(),
               rd.MINECRAFT + '/libraries/x-1.jar': b'x', self.cache_path: cache,
               rd.ALTERNATIVES_ADMIN + 'java': (b'auto\n/usr/bin/java\nkeytool\n/usr/bin/keytool\n\n'
                                                + self.JAVA.encode() + b'\n@java-25@25\n' + self.KEYTOOL.encode() + b'\n'),
               rd.ALTERNATIVES + 'java': ('link', self.JAVA), rd.ALTERNATIVES + 'keytool': ('link', self.KEYTOOL),
               'usr/bin/java': ('link', '/etc/alternatives/java'), 'usr/bin/keytool': ('link', '/etc/alternatives/keytool'),
               self.JAVA[1:]: b'java', self.CACERTS: ('link', '/etc/pki/java/cacerts'),
               self.LOCK: (ROOT / 'os/packages.lock.json').read_bytes(), self.PACKAGES: '\n'.join(self.INSTALLED).encode() + b'\n'}
        self.roots = []
        for files in (old, new, {}):
            root = pathlib.Path(tempfile.mkdtemp(dir=ROOT / 'os/tests'))
            self.addCleanup(shutil.rmtree, root)
            base.ClassifierTest.tree(None, root, files)
            self.roots.append(root)
        self.old, self.new, _ = self.roots
        (self.new / self.CACHE_FOLDER.lstrip('/')).mkdir(parents=True)
        for root in (self.old, self.new):
            (root / self.LINK_TARGET[1:]).mkdir(parents=True)
            for path in root.rglob('*'):
                if path.is_dir() and not path.is_symlink():
                    path.chmod(0o755)
        (self.new / 'usr/lib/prismlauncher/bin/prismlauncher').chmod(0o755)
        # The image's files are root's and carry no extended attributes; this fixture's are the test user's.
        # self.attributes sets a path's attributes in both images; self.meta any field of one image's path.
        self.attributes, self.meta = {}, {}
        real_entry = rd.entry

        def as_image(root, rel):
            value = real_entry(root, rel)
            if value is not None:
                value.update(uid=0, gid=0, xattrs=self.attributes.get(rel, {}))
                value.update(self.meta.get((pathlib.Path(root), rel), {}))
            return value
        self.enterContext(patch.object(rd, 'entry', side_effect=as_image))
        inventory = {rel: dict(value, uid=0, gid=0, xattrs={}) for rel, value in image_diff.inventory(self.new).items()}
        owned = dict(old=set(), new={self.JAVA, self.KEYTOOL, '/usr/lib/jvm/java-25/lib/libjvm.so', '/' + self.JAVA_MAN})
        packages = dict(old=[], new=list(self.INSTALLED))
        # The added packages' files as their rpm database records them (release_diff.rpm_files).
        self.records = {rel: [self.rpm_record(rel)] for rel in (self.JAVA[1:], self.JAVA_MAN, self.CACERTS, 'usr/lib/jvm/java-25')}
        self.classifier = rd.Classifier28(self.roots, packages, owned, dict(
            executables=rd.CHMOD_0755_28, inventory=inventory, main_base='HEAD', records=self.records, new_image=rd.NEW,
            prism_inventory={rel: value for rel, value in inventory.items() if rel == rd.PRISM or rel.startswith(rd.PRISM + '/')}))
        # This small image has its own independent reviewed mapping; production uses the pinned manifest.
        self.classifier.expected_alternatives = {'java': dict(
            links={'/usr/bin/java': 'java', '/usr/bin/keytool': 'keytool'},
            choices=[dict(priority=25, targets={'java': self.JAVA, 'keytool': self.KEYTOOL})])}
        self.enterContext(patch.object(rd, 'rebuild_schemas', side_effect=lambda image: dict(
            matches=(self.new / rd.SCHEMAS).read_bytes() == (FIXTURES / 'after.compiled').read_bytes())))
        self.classifier.pins = {rd.MINECRAFT + '/libraries/x-1.jar': (hashlib.sha256(b'x').hexdigest(), 1, 'pinned x')}
        # The fixture's Prism file list stands in for the reviewed one of the real Prism pin.
        self.enterContext(patch.dict(rd.PRISM_FILE_LISTS, {self.classifier.prism_pin: hashlib.sha256(listing.encode()).hexdigest()}))

    def rpm_record(self, rel, **changes):
        """The rpm database's record of a fixture path, as release_diff.rpm_files reads it; `changes` alter fields."""
        path = self.new / rel
        meta = path.lstat()
        regular = stat.S_ISREG(meta.st_mode)
        record = dict(user='root', group='root', flags=0, size=meta.st_size if regular else 4096, algorithm=rd.RPM_SHA256,
                      digest=hashlib.sha256(path.read_bytes()).hexdigest() if regular else '',
                      target=os.readlink(path) if stat.S_ISLNK(meta.st_mode) else '', caps='', mode=meta.st_mode)
        return dict(record, **changes)

    @contextlib.contextmanager
    def image(self, rel, root=None, **fields):
        """One image's (the new one's by default) entry for rel gets other fields, e.g. uid=1000 or xattrs={...}."""
        key = (root or self.new, rel)
        self.meta[key] = fields
        try:
            yield
        finally:
            del self.meta[key]

    @contextlib.contextmanager
    def mode(self, rel, mode, root=None):
        path = (root or self.new) / rel
        before = stat.S_IMODE(path.lstat().st_mode)
        path.chmod(mode)
        try:
            yield
        finally:
            path.chmod(before)

    @contextlib.contextmanager
    def content(self, rel, value, root=None):
        """rel in one image holds other bytes, becomes a link (('link', target)), a folder ('folder') or vanishes (None)."""
        path = (root or self.new) / rel
        saved = ('link', os.readlink(path)) if path.is_symlink() else 'folder' if path.is_dir() \
            else (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) if path.exists() else None
        missing = [folder for folder in path.parents if not folder.exists()]  # made for the change, removed after it

        def put(value):
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
            if value is None:
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(value, tuple) and value[0] == 'link':
                path.symlink_to(value[1])
            elif value == 'folder':
                path.mkdir()
                path.chmod(0o755)
            else:
                data, mode = value if isinstance(value, tuple) else (value, 0o644)
                path.write_bytes(data)
                path.chmod(mode)
        put(value)
        try:
            yield
        finally:
            put(saved)
            if missing:
                shutil.rmtree(missing[-1])

    def assert_near_misses(self, cases):
        """Each (what, rel, change) leaves rel unexplained while the change holds, and explained again after it."""
        for what, rel, change in cases:
            with self.subTest(what, rel=rel):
                self.assertIsNotNone(self.fresh_explain(rel), 'the fixture explains it before the change')
                with change:
                    self.assertIsNone(self.fresh_explain(rel))
                self.assertIsNotNone(self.fresh_explain(rel), 'the fixture explains it again after the change')

    def fresh_explain(self, rel):
        # The classifier keeps what it read once (Prism's list, the alternatives, the origins); read again.
        self.classifier.prism, self.classifier.groups, self.classifier.origins = None, None, {}
        self.classifier.schema_rebuild = None
        # main() inventories after the image is complete; these tests mutate it between classifications.
        inventory = self.classifier.policy['inventory']
        for path in [path for path in inventory if path == rd.PRISM or path.startswith(rd.PRISM + '/')]:
            del inventory[path]
        for path in [self.new / rd.PRISM, *(self.new / rd.PRISM).rglob('*')]:
            path_rel = str(path.relative_to(self.new))
            if (value := rd.entry(self.new, path_rel)) is not None:
                inventory[path_rel] = value
        return self.explain(rel)

    def explain(self, rel):
        return self.classifier.classify(rel, rd.entry(self.old, rel), rd.entry(self.new, rel))

    def test_every_rule_explains_its_paths(self):
        expected = {
            self.STEAM: 'config', 'usr/share/aresos/apps/hints': 'config',
            rd.DESKTOP_COMMAND[0]: 'build', rd.PRISM_COMMAND[0]: 'build', 'usr/lib/prismlauncher': 'build',
            'usr/lib/prismlauncher/bin/prismlauncher': 'build', 'usr/lib/prismlauncher/lib/libq.so.6': 'build',
            'usr/lib/prismlauncher/lib/libq.so.6.1': 'build', rd.PRISM_FILES: 'manifest',
            rd.MINECRAFT + '/libraries/x-1.jar': 'build', rd.MINECRAFT + '/libraries': 'build',
            self.cache_path: 'build', rd.SCHEMAS: 'build', 'etc/shadow': 'build',
            rd.ALTERNATIVES_ADMIN + 'java': 'package', rd.ALTERNATIVES + 'java': 'package',
            rd.ALTERNATIVES + 'keytool': 'package', 'usr/bin/java': 'package', 'usr/bin/keytool': 'package',
            self.JAVA[1:]: 'package', 'var/log/dnf5.log': 'generated',
            self.cache_path32: 'build', **{path: 'build' for path in self.cache_paths(self.LINKED).values()},
            self.UPDATERS: 'manifest', self.DROPIN: 'config',
            rd.JAVA_MAN_FOLDERS[0]: 'package', rd.JAVA_MAN_FOLDERS[1]: 'package', self.JAVA_MAN: 'package',
            self.CACERTS: 'package', 'usr/lib/jvm/java-25': 'package', self.LOCK: 'manifest', self.PACKAGES: 'manifest'}
        for rel, rule in expected.items():
            with self.subTest(rel=rel):
                regular = dict(kind=stat.S_IFREG, uid=0, gid=0, mode=0o644, xattrs={})
                found = self.explain(rel) if rel != 'var/log/dnf5.log' else self.classifier.generated_rule(rel, regular, regular)
                self.assertIsNotNone(found)
                self.assertEqual(found[0], rule)
        self.assertRegex(self.explain(self.STEAM)[1], r'from .*\(#[0-9]+\)')
        self.assertEqual(self.classifier.schema_rows[0]['key'], 'button-layout')
        self.assertIn('fc-cache-32', self.explain(self.cache_path32)[1])
        self.assertNotIn('fc-cache-32', self.explain(self.cache_path)[1])
        self.assertIn('linked font folder', self.explain(self.cache_paths(self.LINKED)['le64'])[1])
        self.assertIn('man pages', self.explain(rd.JAVA_MAN_FOLDERS[0])[1])
        self.assertIn('user.slice from 23 (#36)', self.explain(self.UPDATERS)[1])
        rows = {(row['path'], row['folder'], row['format'], row['folder_kind'], row['change'])
                for row in self.classifier.font_caches}
        self.assertEqual(rows, {(self.cache_path, self.CACHE_FOLDER, 'le64', 'folder', 'added'),
                                (self.cache_path32, self.CACHE_FOLDER, 'le32d4', 'folder', 'added'),
                                *((path, self.LINKED, layout, 'link', 'added') for layout, path in self.cache_paths(self.LINKED).items())})
        extra, problems = self.classifier.extra()
        self.assertEqual(extra['updaters'], [dict(scope='system', unit='user.slice', added=['/' + self.DROPIN], **{'from': ['23 (#36)']})])
        self.assertEqual(extra['alternatives'], {'java': {'java': self.JAVA, 'keytool': self.KEYTOOL}})
        self.assertEqual(problems[0], f'the Ares-Crown theme in the image (None) is not the one image-checks.sh pins ({PACKAGE31_CROWN})')
        # The fixture holds only two of the os/config files changed since release 27: the converse names the others.
        lacking, = problems[1:2]
        self.assertIn('Control install differs', problems[2])
        self.assertTrue(lacking.startswith('os/config files changed since release 27 that the image lacks or holds with other bytes: '))
        self.assertIn(rd.RC_XML, lacking.split(': ', 1)[1].split(', '))
        self.assertNotIn(self.STEAM, lacking)
        self.assertNotIn(self.DROPIN, lacking)
        # Review 1, N5: a changed os/config file the image holds with other bytes, or one removed since release 27
        # (none is, so a made-up one) that the image still has.
        with self.content(self.STEAM, b'{"other": true}\n'):
            self.assertIn(self.STEAM, self.classifier.extra()[1][1])
        self.classifier.config = self.classifier.config | {'etc/removed-since-27'}
        (self.new / 'etc/removed-since-27').write_bytes(b'kept')
        problems = self.classifier.extra()[1]
        self.assertEqual(problems[2], 'os/config files removed since release 27 that the image still has: etc/removed-since-27')
        # Release 27's regenerated font caches are no blanket rule any more.
        self.assertIsNone(self.classifier.generated_rule('usr/lib/fontconfig/cache/x', {}, {}))
        self.assertIn('as its rpm database records them', self.explain(self.JAVA[1:])[1])

    # Review 1, S4: one near miss per condition of each rule; each must stay unexplained.
    def test_near_misses_of_os_config_files_and_their_folders(self):
        folder = 'usr/share/aresos/apps/hints'
        self.assert_near_misses([
            ('another owner', self.STEAM, self.image(self.STEAM, uid=1000)),
            ('another group', self.STEAM, self.image(self.STEAM, gid=1000)),
            ('a link where os/config has a file', self.STEAM, self.content(self.STEAM, ('link', 'terminal.json'))),
            ('a new folder of another owner', folder, self.image(folder, uid=1000)),
            ('a new folder of another mode', folder, self.mode(folder, 0o775)),
            ('a new folder with an extended attribute', folder, self.image(folder, xattrs={'user.x': '00'})),
            ('a folder release 27 had', folder, self.content(folder, 'folder', root=self.old)),
        ])
        # A new folder os/config has, holding nothing changed since release 27 (os/config/etc/greetd).
        (self.new / 'etc/greetd').mkdir()
        (self.new / 'etc/greetd').chmod(0o755)
        self.assertIsNone(self.fresh_explain('etc/greetd'))

    def test_a_change_that_is_not_on_main_has_no_origin_and_stops(self):
        # origin() reads main's history up to the merge base (review 1, S2): a change made on this branch has none.
        self.classifier.main_base = rd.PREVIOUS_SOURCE_28
        for rel in (self.STEAM, 'usr/share/aresos/apps/hints', self.UPDATERS):
            with self.subTest(rel=rel):
                self.assertIsNone(self.fresh_explain(rel))
        self.classifier.main_base = 'HEAD'
        self.assertIsNotNone(self.fresh_explain(self.STEAM))

    def test_near_misses_of_the_manifest(self):
        mod = 'usr/share/aresos/manifest/aresos-mod.json'
        pin = self.classifier.mod_pin
        (self.new / mod).write_text(json.dumps(dict(sha256=pin, source_revision='a' * 40, pinned_sha256=pin)))
        (self.new / mod).chmod(0o644)
        self.enterContext(patch.dict(os.environ, GITHUB_SHA='a' * 40))
        lock = json.loads((self.new / self.LOCK).read_text())
        self.assert_near_misses([
            ('the lock is not the source', self.LOCK, self.content(self.LOCK, json.dumps(dict(lock, packages=lock['packages'][1:])).encode())),
            ('the lock of another mode', self.LOCK, self.mode(self.LOCK, 0o755)),
            ('the lock of another owner', self.LOCK, self.image(self.LOCK, uid=1000)),
            ('packages.txt is not rpm -qa', self.PACKAGES, self.content(self.PACKAGES, b'\n'.join(
                [*(name.encode() for name in self.INSTALLED), b'extra-1-1.noarch']) + b'\n')),
            ('packages.txt is not sorted', self.PACKAGES, self.content(self.PACKAGES, '\n'.join(self.INSTALLED[::-1]).encode() + b'\n')),
            ("Prism's list in release 27 already", rd.PRISM_FILES, self.content(rd.PRISM_FILES, (self.new / rd.PRISM_FILES).read_bytes(), root=self.old)),
            ("Prism's list not the reviewed one", rd.PRISM_FILES, patch.dict(rd.PRISM_FILE_LISTS, {self.classifier.prism_pin: '0' * 64})),
            ("the bundle's files when the list is not the reviewed one", 'usr/lib/prismlauncher/bin/prismlauncher',
             patch.dict(rd.PRISM_FILE_LISTS, {self.classifier.prism_pin: '0' * 64})),
            ("the mod's record in release 27 already", mod, self.content(mod, (self.new / mod).read_bytes(), root=self.old)),
            ('the updater audit new in release 28', self.UPDATERS, self.content(self.UPDATERS, None, root=self.old)),
        ])
        # A line listed twice is no list.
        listing = (self.new / rd.PRISM_FILES).read_bytes()
        twice = listing + listing.splitlines(keepends=True)[0]
        with patch.dict(rd.PRISM_FILE_LISTS, {self.classifier.prism_pin: hashlib.sha256(twice).hexdigest()}), \
                self.content(rd.PRISM_FILES, twice):
            self.assertIsNone(self.fresh_explain(rd.PRISM_FILES))

    def test_near_misses_of_the_minecraft_inputs(self):
        jar = rd.MINECRAFT + '/libraries/x-1.jar'
        self.assert_near_misses([
            ('a pinned file release 27 had', jar, self.content(jar, b'x', root=self.old)),
            ('a pinned file with an extended attribute', jar, self.image(jar, xattrs={'user.x': '00'})),
            ('a pinned file of another owner', jar, self.image(jar, uid=1000)),
            ('a pinned file of another mode', jar, self.mode(jar, 0o755)),
            ('a pinned file of another size', jar, patch.dict(self.classifier.pins, {jar: (hashlib.sha256(b'x').hexdigest(), 2, 'pinned x')})),
            ('a folder of another mode', rd.MINECRAFT + '/libraries', self.mode(rd.MINECRAFT + '/libraries', 0o775)),
            ('a folder with an extended attribute', rd.MINECRAFT + '/libraries', self.image(rd.MINECRAFT + '/libraries', xattrs={'user.x': '00'})),
        ])
        other = rd.MINECRAFT + '/other'
        (self.new / other).mkdir()
        (self.new / other).chmod(0o755)
        self.assertIsNone(self.fresh_explain(other))

    def test_near_misses_of_prisms_bundle(self):
        file, link = 'usr/lib/prismlauncher/bin/prismlauncher', 'usr/lib/prismlauncher/lib/libq.so.6'
        self.assert_near_misses([
            ('a file of another owner', file, self.image(file, uid=1000)),
            ('a file of another group', file, self.image(file, gid=1000)),
            ('a file with an extended attribute', file, self.image(file, xattrs={'user.x': '00'})),
            ('a file release 27 had', file, self.content(file, b'prism', root=self.old)),
            ('a file with other bytes', file, self.content(file, (b'other', 0o755))),
            ('a group-writable file', file, self.mode(file, 0o775)),
            ('an absolute link inside the bundle', link, self.content(link, ('link', '/usr/lib/prismlauncher/lib/libq.so.6.1'))),
            ('a folder of another owner', 'usr/lib/prismlauncher/bin', self.image('usr/lib/prismlauncher/bin', uid=1000)),
            ('a world-writable folder', 'usr/lib/prismlauncher/bin', self.mode('usr/lib/prismlauncher/bin', 0o757)),
        ])

    def test_prisms_typed_inventory_rejects_dangling_missing_or_different_links_and_modes(self):
        link = rd.PRISM + '/lib/libq.so.6'
        self.assert_near_misses([
            ('a dangling internal link', link, self.content(link, ('link', 'nonexistent.so'))),
            ('a link to another existing file', link, self.content(link, ('link', '../bin/prismlauncher'))),
            ('an executable loses its execute bits', rd.PRISM + '/bin/prismlauncher', self.mode(rd.PRISM + '/bin/prismlauncher', 0o644)),
            ('a directory gains execute restrictions', rd.PRISM + '/lib', self.mode(rd.PRISM + '/lib', 0o700)),
        ])
        for target in (link, rd.PRISM + '/lib/libq.so.6.1'):
            with self.subTest(target=target), self.content(target, None):
                self.assertIsNone(self.fresh_explain(rd.PRISM_FILES))
                self.assertIn('Prism bundle differs', ' '.join(self.classifier.extra()[1]))

    def test_near_misses_of_the_alternatives_and_the_commands(self):
        record = rd.ALTERNATIVES_ADMIN + 'java'
        self.assert_near_misses([
            ('a record release 27 had', record, self.content(record, (self.new / record).read_bytes(), root=self.old)),
            ('a record of another owner', record, self.image(record, uid=1000)),
            ('a record of another mode', record, self.mode(record, 0o600)),
            ('a record with an extended attribute', record, self.image(record, xattrs={'user.x': '00'})),
            ('an alternatives link of another owner', rd.ALTERNATIVES + 'java', self.image(rd.ALTERNATIVES + 'java', uid=1000)),
            ('a command link of another owner', 'usr/bin/java', self.image('usr/bin/java', uid=1000)),
            ('a command link release 27 had', 'usr/bin/java', self.content('usr/bin/java', ('link', '/etc/alternatives/java'), root=self.old)),
            ("the desktop's command of another owner", rd.DESKTOP_COMMAND[0], self.image(rd.DESKTOP_COMMAND[0], uid=1000)),
            ("Prism's command of another owner", rd.PRISM_COMMAND[0], self.image(rd.PRISM_COMMAND[0], uid=1000)),
        ])
        # A record release 27 had takes its links with it.
        with self.content(record, (self.new / record).read_bytes(), root=self.old):
            for rel in ('usr/bin/java', rd.ALTERNATIVES + 'java'):
                with self.subTest(rel=rel):
                    self.assertIsNone(self.fresh_explain(rel))

    def test_swapping_alternatives_targets_stops_the_record_and_both_commands(self):
        java, keytool = rd.ALTERNATIVES + 'java', rd.ALTERNATIVES + 'keytool'
        for changes in (((java, self.KEYTOOL),), ((keytool, self.JAVA),), ((java, self.KEYTOOL), (keytool, self.JAVA))):
            with self.subTest(changes=changes), contextlib.ExitStack() as stack:
                for rel, target in changes:
                    stack.enter_context(self.content(rel, ('link', target)))
                for rel in (rd.ALTERNATIVES_ADMIN + 'java', java, keytool, 'usr/bin/java', 'usr/bin/keytool'):
                    self.assertIsNone(self.fresh_explain(rel), rel)

    def test_swapping_the_record_and_links_together_cannot_redefine_java(self):
        record = rd.ALTERNATIVES_ADMIN + 'java'
        raw = (self.new / record).read_bytes()
        swapped = raw.replace(self.JAVA.encode(), b'/temporary-swap').replace(
            self.KEYTOOL.encode(), self.JAVA.encode()).replace(b'/temporary-swap', self.KEYTOOL.encode())
        with self.content(record, swapped), self.content(rd.ALTERNATIVES + 'java', ('link', self.KEYTOOL)), \
                self.content(rd.ALTERNATIVES + 'keytool', ('link', self.JAVA)):
            for rel in (record, rd.ALTERNATIVES + 'java', rd.ALTERNATIVES + 'keytool', 'usr/bin/java', 'usr/bin/keytool'):
                with self.subTest(rel=rel):
                    self.assertIsNone(self.fresh_explain(rel), rel)

    def test_missing_public_links_stop_even_when_absent_from_both_images(self):
        for paths in (('usr/bin/java',), ('usr/bin/keytool',), ('usr/bin/java', 'usr/bin/keytool')):
            with self.subTest(paths=paths), contextlib.ExitStack() as stack:
                for rel in paths:
                    self.assertIsNone(rd.entry(self.old, rel))
                    stack.enter_context(self.content(rel, None))
                self.classifier.groups = None
                self.assertIn('alternatives groups missing or different from the reviewed mapping: java',
                              self.classifier.extra()[1])

    def test_every_public_link_requires_its_type_metadata_and_target_even_when_unchanged(self):
        for rel in ('usr/bin/java', 'usr/bin/keytool'):
            target = '/etc/alternatives/' + pathlib.PurePosixPath(rel).name
            for fields in (dict(kind=stat.S_IFREG), dict(uid=1000), dict(gid=1000), dict(mode=0o755),
                           dict(xattrs={'user.x': '00'}), dict(target=self.KEYTOOL)):
                with self.subTest(rel=rel, fields=fields), self.content(rel, ('link', target), root=self.old), \
                        self.image(rel, **fields), self.image(rel, root=self.old, **fields):
                    self.assertEqual(rd.entry(self.old, rel), rd.entry(self.new, rel))
                    self.classifier.groups = None
                    self.assertIn('alternatives groups missing or different from the reviewed mapping: java',
                                  self.classifier.extra()[1])

    def test_a_slave_without_a_target_requires_both_links_absent_and_rejects_an_extra_public_link(self):
        record = rd.ALTERNATIVES_ADMIN + 'java'
        raw = (self.new / record).read_bytes().replace(self.KEYTOOL.encode(), b'')
        self.classifier.expected_alternatives['java']['choices'][0]['targets']['keytool'] = ''
        with self.content(record, raw), self.content(rd.ALTERNATIVES + 'keytool', None), self.content('usr/bin/keytool', None):
            self.assertIsNotNone(self.fresh_explain(record))
            for extra in (('link', '/etc/alternatives/keytool'), ('link', self.KEYTOOL), b'unexpected', 'folder'):
                with self.subTest(extra=extra), self.content('usr/bin/keytool', extra):
                    self.classifier.groups = None
                    self.assertIn('alternatives groups missing or different from the reviewed mapping: java',
                                  self.classifier.extra()[1])
                    self.assertIsNone(self.fresh_explain(record))
            with self.content(rd.ALTERNATIVES + 'keytool', ('link', self.KEYTOOL)):
                self.assertIsNone(self.fresh_explain(record))

    def test_record_names_public_paths_and_priorities_cannot_redefine_the_reviewed_mapping(self):
        record = rd.ALTERNATIVES_ADMIN + 'java'
        raw = (self.new / record).read_bytes()
        for changed in (raw.replace(b'@java-25@25', b'@java-25@26'),
                        raw.replace(b'keytool\n/usr/bin/keytool', b'renamed\n/usr/bin/keytool'),
                        raw.replace(b'/usr/bin/keytool\n', b'/usr/bin/renamed\n')):
            with self.subTest(changed=changed), self.content(record, changed), \
                    self.content(rd.ALTERNATIVES + 'renamed', ('link', self.KEYTOOL)), \
                    self.content('usr/bin/renamed', ('link', '/etc/alternatives/renamed')):
                self.assertIsNone(self.fresh_explain(record))
        with self.content(record, None), self.content(rd.ALTERNATIVES_ADMIN + 'renamed', raw):
            self.assertIsNone(self.fresh_explain(rd.ALTERNATIVES_ADMIN + 'renamed'))

    def test_all_four_real_scriptlet_groups_and_their_twelve_chains_are_accepted(self):
        expected = AlternativesAdminTest.scriptlet_groups()
        with contextlib.ExitStack() as stack:
            for group, spec in expected.items():
                choice, = spec['choices']
                targets = choice['targets']
                master, = [public for public, name in spec['links'].items() if name == group]
                slaves = [(public, name) for public, name in spec['links'].items() if name != group]
                lines = ['auto', master, *(part for public, name in slaves for part in (name, public)), '',
                         targets[group], str(choice['priority']), *(targets[name] for _, name in slaves)]
                record = rd.ALTERNATIVES_ADMIN + group
                stack.enter_context(self.content(record, ('\n'.join(lines) + '\n').encode()))
                for public, name in spec['links'].items():
                    stack.enter_context(self.content(public.lstrip('/'), ('link', '/etc/alternatives/' + name)))
                    stack.enter_context(self.content(rd.ALTERNATIVES + name, ('link', targets[name])))
                self.classifier.owned['new'].update(targets.values())
            self.classifier.expected_alternatives = rd.reviewed_alternatives(self.classifier.packages)
            for group, spec in expected.items():
                for rel in (rd.ALTERNATIVES_ADMIN + group, *(public.lstrip('/') for public in spec['links']),
                            *(rd.ALTERNATIVES + name for name in spec['links'].values())):
                    self.assertIsNotNone(self.fresh_explain(rel), rel)
            self.assertEqual(self.classifier.alternatives().keys(), expected.keys())
            self.assertFalse(any('alternatives groups' in problem for problem in self.classifier.extra()[1]))

    def test_alternatives_cannot_mix_two_choices_or_choose_a_lower_automatic_priority(self):
        record = rd.ALTERNATIVES_ADMIN + 'java'
        raw = (self.new / record).read_bytes()
        other_java, other_keytool = '/jdk2/bin/java', '/jdk2/bin/keytool'
        self.classifier.owned['new'].update((other_java, other_keytool))
        for priority in (24, 26):
            # Both independently reviewed choices are allowed; their selected links must remain coherent.
            self.classifier.expected_alternatives['java']['choices'] = [
                dict(priority=25, targets={'java': self.JAVA, 'keytool': self.KEYTOOL}),
                dict(priority=priority, targets={'java': other_java, 'keytool': other_keytool})]
            with self.subTest(priority=priority), self.content(record, raw + f'{other_java}\n{priority}\n{other_keytool}\n'.encode()):
                if priority == 24:
                    self.assertIsNotNone(self.fresh_explain(record))
                else:
                    self.assertIsNone(self.fresh_explain(record))
                with self.content(rd.ALTERNATIVES + 'keytool', ('link', other_keytool)):
                    self.assertIsNone(self.fresh_explain(record))

    def test_near_misses_of_shadow_and_the_font_caches(self):
        old_cache = FontCacheTest.cache(self.CACHE_FOLDER)
        self.assert_near_misses([
            ('shadow of another mode', 'etc/shadow', self.mode('etc/shadow', 0o600)),
            ('shadow of another owner', 'etc/shadow', self.image('etc/shadow', uid=1000)),
            ('a cache of another owner', self.cache_path, self.image(self.cache_path, uid=1000)),
            ('a cache of another mode', self.cache_path, self.mode(self.cache_path, 0o600)),
            ('a cache with an extended attribute', self.cache_path, self.image(self.cache_path, xattrs={'user.x': '00'})),
            ("a rebuilt cache whose old one was not root's 0644", self.cache_path,
             self.content(self.cache_path, (old_cache, 0o600), root=self.old)),
            ('a rebuilt cache whose old one was a link', self.cache_path,
             self.content(self.cache_path, ('link', 'elsewhere'), root=self.old)),
        ])
        # Rebuilt from root's 0644 cache: explained, and listed as rebuilt.
        with self.content(self.cache_path, (old_cache, 0o644), root=self.old):
            self.classifier.font_caches.clear()
            self.assertIsNotNone(self.fresh_explain(self.cache_path))
            self.assertEqual([row['change'] for row in self.classifier.font_caches], ['rebuilt'])

    def test_the_rpm_database_keeps_its_metadata(self):
        same = dict(kind=stat.S_IFREG, uid=0, gid=0, mode=0o644, sha256='a' * 64, bytes=1, xattrs={})
        self.assertEqual(self.classifier.generated_rule(rd.RPM_DATABASE, same, dict(same, sha256='b' * 64))[0], 'generated')
        for change in (dict(uid=1000), dict(gid=1000), dict(mode=0o600), dict(kind=stat.S_IFLNK)):
            with self.subTest(change=change):
                self.assertIsNone(self.classifier.generated_rule(rd.RPM_DATABASE, same, dict(same, **change)))
        self.assertIsNone(self.classifier.generated_rule(rd.RPM_DATABASE, None, same))

    def test_only_the_dry_runs_regenerated_paths_are_generated(self):
        # Review 1, S1: what run 43847257976 needed, each by its own pattern.
        needed = ['usr/lib/sysimage/libdnf5/nevras.toml', 'usr/lib/sysimage/libdnf5/packages.toml',
                  'usr/lib/sysimage/libdnf5/system.toml', 'usr/lib/sysimage/libdnf5/transaction_history.sqlite',
                  'usr/lib/sysimage/libdnf5/transaction_history.sqlite-shm', 'usr/lib/sysimage/libdnf5/transaction_history.sqlite-wal',
                  'var/cache/ldconfig/aux-cache', 'var/lib/dnf/repos/fedora-cff72538bc9825a4/countme',
                  'var/lib/dnf/repos/updates-3cc07c89a20302f2/countme', 'var/log/dnf5.log']
        used = set()
        for rel in needed:
            with self.subTest(rel=rel):
                regular = dict(kind=stat.S_IFREG, uid=0, gid=0, mode=0o600 if rel.endswith('aux-cache') else 0o644, xattrs={})
                found = self.classifier.generated_rule(rel, regular, regular)
                self.assertEqual(found[0], 'generated')
                used.add(found[1])
        self.assertEqual(used, {reason for _, reason in rd.GENERATED_28})
        # Release 27's other patterns explain nothing in release 28: a change there stops.
        changed = dict(kind=stat.S_IFREG, uid=0, gid=0, mode=0o644, sha256='b' * 64, bytes=1, xattrs={})
        for rel in ('etc/selinux/targeted/policy/policy.33', 'var/lib/selinux/targeted/active/commit_num',
                    'usr/share/icons/hicolor/icon-theme.cache', 'usr/share/applications/mimeinfo.cache', 'run/x',
                    'var/cache/libdnf5', 'var/cache/libdnf5/fedora/repodata', 'etc/ld.so.cache', 'usr/lib/sysimage/rpm/x',
                    'usr/lib/sysimage/libdnf5', 'usr/lib/fontconfig/cache/x', 'var/cache/fontconfig/x'):
            with self.subTest(rel=rel):
                self.assertIsNone(self.classifier.generated_rule(rel, {}, {}))
                self.assertIsNone(self.classifier.classify(rel, dict(changed, sha256='a' * 64), changed))

    def test_generated_exceptions_reject_neighbours_and_every_unreviewed_operation_or_metadata(self):
        regular = dict(kind=stat.S_IFREG, uid=0, gid=0, mode=0o644, xattrs={})
        # Review 3's three probes, plus close neighbours of every retained filename family.
        for rel in ('usr/lib/sysimage/libdnf5/unreviewed.sh',
                    'var/lib/dnf/repos/fedora-cff72538bc9825a4/not-countme',
                    'var/lib/dnf/repos/unreviewed-0000000000000000/countme',
                    'usr/lib/sysimage/libdnf5/transaction_history.sqlite-backup',
                    'usr/lib/sysimage/libdnf5/packages.toml/child', 'var/log/dnf5.log.1'):
            with self.subTest(rel=rel):
                self.assertIsNone(self.classifier.generated_rule(rel, regular, dict(regular, mode=0o4755)))
                self.assertIsNone(self.classifier.generated_rule(rel, regular, regular))
        for rel in [rd.RPM_DATABASE, *(path for path, _ in rd.GENERATED_28)]:
            good = dict(regular, mode=0o600 if rel.endswith('aux-cache') else 0o644)
            for before, after in ((None, good), (good, None)):
                with self.subTest(rel=rel, before=before, after=after):
                    self.assertIsNone(self.classifier.generated_rule(rel, before, after))
            for change in (dict(uid=1000), dict(gid=1000), dict(mode=0o4755), dict(mode=0o755),
                           dict(kind=stat.S_IFDIR), dict(kind=stat.S_IFLNK), dict(xattrs={'user.x': '00'})):
                with self.subTest(rel=rel, change=change):
                    bad = dict(good, **change)
                    self.assertIsNone(self.classifier.generated_rule(rel, good, bad))
                    self.assertIsNone(self.classifier.generated_rule(rel, bad, good))

    def test_files_of_the_added_packages_must_be_what_their_rpm_database_records(self):
        # Review 1, S5: owner, mode, link target and bytes as rpm records them; no attribute, setuid or writable bit.
        java, folder = self.JAVA[1:], 'usr/lib/jvm/java-25'

        def recorded(rel, **changes):
            return patch.dict(self.records, {rel: [self.rpm_record(rel, **changes)]})
        self.assert_near_misses([
            ('a %ghost record', java, recorded(java, flags=rd.RPMFILE_GHOST)),
            ("a record of another user", java, recorded(java, user='ares')),
            ("a record of another group", java, recorded(java, group='wheel')),
            ('a record with a file capability', java, recorded(java, caps='cap_net_raw=p')),
            ('a record of another mode', java, recorded(java, mode=stat.S_IFREG | 0o755)),
            ('a record of another kind', java, recorded(java, mode=stat.S_IFLNK | 0o644)),
            ('a record of other bytes', java, recorded(java, digest='0' * 64)),
            ('a record of another size', java, recorded(java, size=5)),
            ('a record with another digest algorithm', java, recorded(java, algorithm='1')),
            ('a link with another recorded target', self.CACERTS, recorded(self.CACERTS, target='/etc/pki/other')),
            ('a folder of another recorded mode', folder, recorded(folder, mode=stat.S_IFDIR | 0o750)),
            ('a second record that differs', java, patch.dict(self.records, {java: [self.rpm_record(java), self.rpm_record(java, size=5)]})),
            ('no record at all', java, patch.dict(self.records, {java: []})),
            ('a file of another owner', java, self.image(java, uid=1000)),
            ('a file with an extended attribute', java, self.image(java, xattrs={'security.capability': '01'})),
            ('a link of another owner', self.CACERTS, self.image(self.CACERTS, gid=1000)),
        ])
        # A setuid or group-writable file stops even when its record says so too.
        for mode in (0o4755, 0o2755, 0o664, 0o646):
            with self.subTest(mode=oct(mode)), self.mode(java, mode), recorded(java, mode=stat.S_IFREG | mode):
                self.assertIsNone(self.fresh_explain(java))
        with self.mode(folder, 0o1777), recorded(folder, mode=stat.S_IFDIR | 0o1777):
            self.assertIsNone(self.fresh_explain(folder))
        # A shared non-ghost record still requires the file, even if another package marks it ghost.
        with patch.dict(self.records, {java: [self.rpm_record(java), self.rpm_record(java, flags=rd.RPMFILE_GHOST)]}):
            self.assertIsNotNone(self.fresh_explain(java))
        fifo = 'usr/lib/jvm/java-25/lib/fifo'
        os.mkfifo(self.new / fifo, 0o644)
        (self.new / fifo).chmod(0o644)
        with recorded(fifo, mode=stat.S_IFIFO | 0o644):
            self.assertIsNone(self.fresh_explain(fifo))
        # A removed package's path is explained only when it is gone.
        self.classifier.owned['old'] = {'/' + self.STEAM}
        self.assertIsNone(self.classifier.package_rule(self.STEAM, rd.entry(self.new, self.STEAM), rd.entry(self.new, self.STEAM)))
        self.assertEqual(self.classifier.package_rule(self.STEAM, rd.entry(self.new, self.STEAM), None)[1], 'file of a removed package')

    def test_rpm_files_reads_the_query_and_stops_on_what_it_cannot_read(self):
        line = '\t'.join(['/usr/bin/x', 'root', 'root', '0', '3', '8', 'a' * 64, '', '', '33261'])
        link = '\t'.join(['/usr/bin/y', 'root', 'root', '64', '1', '8', '', 'x', '(none)', '41471'])
        self.assertEqual(rd.rpm_files(line + '\n' + link), {
            'usr/bin/x': [dict(user='root', group='root', flags=0, size=3, algorithm='8', digest='a' * 64, target='', caps='', mode=0o100755)],
            'usr/bin/y': [dict(user='root', group='root', flags=64, size=1, algorithm='8', digest='', target='x', caps='(none)', mode=0o120777)]})
        for bad in (line + '\textra', line.replace('/usr/bin/x', 'usr/bin/x'), line.replace('\t33261', '\t'),
                    line.replace('root\t0', 'root\tzero'), 'a file\twith\ttabs'):
            with self.subTest(bad=bad), self.assertRaisesRegex(AssertionError, 'unreadable rpm file record'):
                rd.rpm_files(bad)
        # The query's own words: the path first and the mode last, so neither end of rpm's output is an empty field.
        fields = re.findall(r'%\{=?(\w+)\}', rd.RPM_FILE_FORMAT)
        self.assertEqual(fields, ['FILENAMES', 'FILEUSERNAME', 'FILEGROUPNAME', 'FILEFLAGS', 'FILESIZES', 'FILEDIGESTALGO',
                                  'FILEDIGESTS', 'FILELINKTOS', 'FILECAPS', 'FILEMODES'])
        self.assertEqual(len(fields), len(rd.RPM_FILE_FIELDS))

    def test_near_misses_of_the_compiled_schemas(self):
        self.assert_near_misses([
            ('another mode', rd.SCHEMAS, self.mode(rd.SCHEMAS, 0o600)),
            ('another owner', rd.SCHEMAS, self.image(rd.SCHEMAS, uid=1000)),
            ('an extended attribute added', rd.SCHEMAS, self.image(rd.SCHEMAS, xattrs={'user.x': '00'})),
            ("the image's override is not os/config's", rd.SCHEMAS, self.content(rd.SCHEMA_OVERRIDE, OVERRIDE.replace('minimize,', '').encode())),
            ('no key differs at all', rd.SCHEMAS, self.content(rd.SCHEMAS, (FIXTURES / 'before.compiled').read_bytes())),
            ('release 27 compiled the override already', rd.SCHEMAS,
             self.content(rd.SCHEMAS, (FIXTURES / 'after.compiled').read_bytes(), root=self.old)),
            ("another desktop's value beside the override", rd.SCHEMAS,
             self.content(rd.SCHEMAS, (FIXTURES / 'desktops.compiled').read_bytes())),
            ('a default changed beside the override', rd.SCHEMAS, self.content(rd.SCHEMAS, (FIXTURES / 'default.compiled').read_bytes())),
            ("the key's choices changed", rd.SCHEMAS, self.content(rd.SCHEMAS, (FIXTURES / 'choices.compiled').read_bytes())),
            ('not a compiled file', rd.SCHEMAS, self.content(rd.SCHEMAS, b'GVariant' + bytes(40))),
        ])

    def test_corrupted_schema_hashes_and_buckets_are_not_explained(self):
        for kind, corrupted in corrupt_schema_lookup((FIXTURES / 'after.compiled').read_bytes()).items():
            with self.subTest(kind=kind), self.content(rd.SCHEMAS, corrupted):
                self.assertIsNone(self.fresh_explain(rd.SCHEMAS))
                self.assertIn('compiled schemas differ from deterministic rebuild', ' '.join(self.classifier.extra()[1]))

    def replace(self, rel, value):
        path = self.new / rel
        path.unlink()
        if isinstance(value, tuple):
            os.symlink(value[1], path)
        else:
            path.write_bytes(value)
            path.chmod(0o644)

    def test_near_misses_stay_unexplained(self):
        cases = [
            (rd.DESKTOP_COMMAND[0], ('link', '/usr/libexec/aresos-desktop')),
            (rd.PRISM_COMMAND[0], ('link', '/usr/lib/prismlauncher/bin/other')),
            ('usr/lib/prismlauncher/lib/libq.so.6', ('link', '/usr/lib64/libq.so.6')),
            ('usr/lib/prismlauncher/lib/libq.so.6', ('link', '../../../../usr/lib64/libq.so.6')),
            (rd.MINECRAFT + '/libraries/x-1.jar', b'y'),
            (self.STEAM, b'{"other": true}\n'),
            ('usr/bin/java', ('link', '/usr/lib/jvm/java-25/bin/java')),
            (rd.ALTERNATIVES + 'keytool', ('link', '/usr/bin/other-keytool')),
            ('etc/shadow', b'root:!*:20384:0:99999:7:::\nares:$6$hash:20408::::::\n'),
            (self.cache_path, FontCacheTest.cache('/usr/share/fonts/other')),
        ]
        for rel, value in cases:
            with self.subTest(rel=rel, value=value):
                saved = (self.new / rel).readlink() if (self.new / rel).is_symlink() else (self.new / rel).read_bytes()
                self.replace(rel, value)
                try:
                    self.assertIsNone(self.explain(rel))
                finally:
                    self.replace(rel, ('link', str(saved)) if isinstance(saved, pathlib.Path) else saved)
        # Other modes, an extended attribute, or a 64-bit cache under the 32-bit format's name.
        (self.new / self.STEAM).chmod(0o755)
        self.assertIsNone(self.explain(self.STEAM))
        (self.new / self.STEAM).chmod(0o644)
        self.attributes[self.STEAM] = {'user.x': '00'}
        self.assertIsNone(self.explain(self.STEAM))
        (self.new / 'usr/lib/prismlauncher/bin/prismlauncher').chmod(0o4755)
        self.assertIsNone(self.explain('usr/lib/prismlauncher/bin/prismlauncher'))
        le32 = self.cache_path.replace('-le64.', '-le32d4.')
        shutil.copyfile(self.new / self.cache_path, self.new / le32)
        self.assertIsNone(self.explain(le32))
        # An alternatives target outside the added packages takes the whole record with it.
        self.classifier.groups = None
        self.classifier.owned['new'].discard(self.KEYTOOL)
        for rel in (rd.ALTERNATIVES_ADMIN + 'java', 'usr/bin/java', rd.ALTERNATIVES + 'java'):
            with self.subTest(rel=rel):
                self.assertIsNone(self.explain(rel))

    def test_font_caches_need_both_formats_their_own_folder_and_a_folder_release_27_had_as_it_is(self):
        cache32 = (self.new / self.cache_path32).read_bytes()
        linked = list(self.cache_paths(self.LINKED).values())

        def stays_unexplained(paths, change, undo):
            change()
            try:
                for rel in paths:
                    with self.subTest(rel=rel, change=change.__name__):
                        self.assertIsNone(self.explain(rel))
            finally:
                undo()

        def restore_32_bit_cache():
            (self.new / self.cache_path32).write_bytes(cache32)

        def link(target, roots=None):
            for root in roots or (self.old, self.new):
                (root / self.LINKED[1:]).unlink(missing_ok=True)
                (root / self.LINKED[1:]).symlink_to(target)

        def without_the_64_bit_sibling():
            (self.new / self.cache_path).rename(self.new / (self.cache_path + '.away'))
        stays_unexplained([self.cache_path32], without_the_64_bit_sibling,
                          lambda: (self.new / (self.cache_path + '.away')).rename(self.new / self.cache_path))

        def without_the_32_bit_sibling():
            (self.new / self.cache_path32).unlink()
        stays_unexplained([self.cache_path], without_the_32_bit_sibling, restore_32_bit_cache)

        def another_folder_in_the_32_bit_cache():
            (self.new / self.cache_path32).write_bytes(FontCacheTest.cache('/usr/share/fonts/other', layout='le32d4'))
        stays_unexplained([self.cache_path32], another_folder_in_the_32_bit_cache, restore_32_bit_cache)

        def another_version_in_the_32_bit_cache():
            (self.new / self.cache_path32).write_bytes(FontCacheTest.cache(self.CACHE_FOLDER, version=8, layout='le32d4'))
        stays_unexplained([self.cache_path32], another_version_in_the_32_bit_cache, restore_32_bit_cache)

        # The linked folder: release 27's link, unchanged, to a folder under /usr.
        (self.new / 'opt/fonts').mkdir(parents=True)

        def an_unchanged_link_out_of_usr():
            link('/opt/fonts')
        stays_unexplained(linked, an_unchanged_link_out_of_usr, lambda: link(self.LINK_TARGET))

        def an_unchanged_link_to_nothing():
            link('/usr/share/fonts/missing')
        stays_unexplained(linked, an_unchanged_link_to_nothing, lambda: link(self.LINK_TARGET))

        def a_link_that_changed():
            link(self.CACHE_FOLDER, roots=[self.new])
        stays_unexplained(linked, a_link_that_changed, lambda: link(self.LINK_TARGET))

        def a_link_new_in_release_28():
            (self.old / self.LINKED[1:]).unlink()
        stays_unexplained(linked, a_link_new_in_release_28, lambda: link(self.LINK_TARGET))

        def a_link_above_the_folder():
            fonts = self.new / 'usr/share/fonts'
            fonts.rename(self.new / 'usr/share/fonts-real')
            fonts.symlink_to('fonts-real')

        def undo_link_above():
            (self.new / 'usr/share/fonts').unlink()
            (self.new / 'usr/share/fonts-real').rename(self.new / 'usr/share/fonts')
        stays_unexplained([self.cache_path, self.cache_path32], a_link_above_the_folder, undo_link_above)

        # A folder outside /usr, cached in both formats.
        outside = self.cache_paths('/opt/fonts')
        for layout, rel in outside.items():
            (self.new / rel).write_bytes(FontCacheTest.cache('/opt/fonts', layout=layout))
            (self.new / rel).chmod(0o644)
        for rel in outside.values():
            with self.subTest(rel=rel):
                self.assertIsNone(self.explain(rel))
        # Every change was undone: the fixture's caches are explained again.
        for rel in (self.cache_path, self.cache_path32, *linked):
            with self.subTest(rel=rel, state='restored'):
                self.assertIsNotNone(self.explain(rel))

    def test_the_updater_audit_may_only_gain_drop_ins_merged_packages_added_to_os_config(self):
        path = self.new / self.UPDATERS
        dropin = '/' + self.DROPIN
        other = 'usr/lib/systemd/system/user.slice.d/99-other.conf'
        (self.new / other).write_bytes(b'[Slice]\n')
        (self.new / other).chmod(0o644)
        cases = {
            'a command changed': self.audit(dropin, commands=['ExecStart=/usr/bin/true']),
            'the unit became suspicious': self.audit(dropin, suspicious=True),
            'its state changed': self.audit(dropin, state='enabled'),
            'an old source removed': json.dumps([json.loads(self.audit())[0], dict(json.loads(self.audit(dropin))[1],
                                                 sources=[dropin])]).encode(),
            'a drop-in os/config does not have': self.audit(dropin, '/' + other),
            "another unit's folder": self.audit('/usr/lib/systemd/system/ModemManager.service.d/50-aresos-recovery.conf'),
            'a unit added': json.dumps(json.loads(self.audit(dropin)) + [json.loads(self.audit())[0]]).encode(),
            'not JSON': b'{',
        }
        for name, data in cases.items():
            with self.subTest(case=name):
                path.write_bytes(data)
                self.assertIsNone(self.explain(self.UPDATERS))
        path.write_bytes(self.audit(dropin))
        self.assertIsNotNone(self.explain(self.UPDATERS))
        # Package 23's drop-in for another unit, in the image as os/config has it, listed under user.slice.
        sibling = 'usr/lib/systemd/system/user-1001.slice.d/50-aresos-recovery.conf'
        (self.new / sibling).parent.mkdir()
        (self.new / sibling).write_bytes((ROOT / 'os/config' / sibling).read_bytes())
        (self.new / sibling).chmod(0o644)
        path.write_bytes(self.audit(dropin, '/' + sibling))
        self.assertIsNone(self.explain(self.UPDATERS))
        path.write_bytes(self.audit(dropin))
        # An os/config drop-in that did not change since release 27.
        self.classifier.config = self.classifier.config - {self.DROPIN}
        self.assertIsNone(self.explain(self.UPDATERS))
        self.classifier.config = self.classifier.config | {self.DROPIN}
        self.assertIsNotNone(self.explain(self.UPDATERS))
        # The drop-in in the image differs from os/config's, or release 27 had it already.
        source = (self.new / self.DROPIN).read_bytes()
        (self.new / self.DROPIN).write_bytes(source + b'# changed\n')
        self.assertIsNone(self.explain(self.UPDATERS))
        (self.new / self.DROPIN).write_bytes(source)
        (self.old / self.DROPIN).parent.mkdir(parents=True)
        (self.old / self.DROPIN).write_bytes(source)
        self.assertIsNone(self.explain(self.UPDATERS))

    def test_the_audit_comparison_keeps_old_sources_in_order(self):
        unit = lambda *sources: dict(scope='user', name='a@b.service', state='static', sources=list(sources))
        dump = lambda *units: json.dumps(list(units)).encode()
        seen = []
        allow = lambda scope, name, path: seen.append((scope, name, path)) or path.endswith('/new.conf')
        self.assertEqual(rd.audit_changes(dump(unit('/x', '/y')), dump(unit('/x', '/d/new.conf', '/y')), allow),
                         [dict(scope='user', unit='a@b.service', added=['/d/new.conf'])])
        self.assertEqual(seen, [('user', 'a@b.service', '/d/new.conf')])
        self.assertEqual(rd.audit_changes(dump(unit('/x')), dump(unit('/x')), allow), [])
        for new in (dump(unit('/y', '/x', '/d/new.conf')), dump(unit('/x', '/d/other.conf')), dump(unit('/x', 5)),
                    dump(dict(unit('/x', '/d/new.conf'), state='masked')), dump(unit('/x'), unit('/x')), b'[1]'):
            with self.subTest(new=new):
                self.assertIsNone(rd.audit_changes(dump(unit('/x', '/y')) if b'/y' in new else dump(unit('/x')), new, allow))
        # The template's drop-in folder counts for an instance, as the audit reads it.
        self.classifier.config = self.classifier.config | {'usr/lib/systemd/user/a@.service.d/x.conf'}
        self.assertFalse(self.classifier.audit_dropin('user', 'a@b.service', '/usr/lib/systemd/user/c@.service.d/x.conf'))
        self.assertFalse(self.classifier.audit_dropin('user', 'a@b.service', '/usr/lib/systemd/user/a@.service.d/../x.conf'))

    @contextlib.contextmanager
    def console_keymap(self):
        with self.content(self.CONSOLE_UNIT, (ROOT / 'os/config' / self.CONSOLE_UNIT).read_bytes()), \
                self.content(self.CONSOLE_LINK, ('link', '/' + self.CONSOLE_UNIT)), \
                self.content(self.UPDATERS, self.audit('/' + self.DROPIN, console_keymap=True)):
            yield

    def test_package_50s_exact_unit_is_already_accepted_by_config_rule(self):
        with self.console_keymap():
            after = rd.entry(self.new, self.CONSOLE_UNIT)
            self.assertEqual(after, dict(kind=stat.S_IFREG, mode=0o644, uid=0, gid=0, xattrs={},
                                        sha256=rd.file_sha256(ROOT / 'os/config' / self.CONSOLE_UNIT),
                                        bytes=len((ROOT / 'os/config' / self.CONSOLE_UNIT).read_bytes())))
            self.assertEqual(self.classifier.origin(self.CONSOLE_UNIT), ['50 (#101)'])
            self.assertEqual(self.classifier.config_rule(self.CONSOLE_UNIT, None, after),
                             ('config', 'os/config file new since release 27, bytes equal the source; from 50 (#101)'))
            self.assert_near_misses([
                ('different bytes', self.CONSOLE_UNIT, self.content(self.CONSOLE_UNIT, b'[Unit]\n')),
                ('another owner', self.CONSOLE_UNIT, self.image(self.CONSOLE_UNIT, uid=1000)),
                ('another group', self.CONSOLE_UNIT, self.image(self.CONSOLE_UNIT, gid=1000)),
                ('another mode', self.CONSOLE_UNIT, self.mode(self.CONSOLE_UNIT, 0o755)),
                ('an extended attribute', self.CONSOLE_UNIT, self.image(self.CONSOLE_UNIT, xattrs={'user.x': '00'})),
            ])

    def test_package_50s_enable_link_requires_its_exact_path_target_and_metadata(self):
        with self.console_keymap():
            self.assertEqual(self.fresh_explain(self.CONSOLE_LINK),
                             ('build', 'package 50: systemctl enable console keymap link; from 50 (#101)'))
            self.assert_near_misses([
                ('another target', self.CONSOLE_LINK, self.content(self.CONSOLE_LINK, ('link', '/usr/lib/systemd/system/other.service'))),
                ('a relative target', self.CONSOLE_LINK, self.content(self.CONSOLE_LINK, ('link', '../../../../' + self.CONSOLE_UNIT))),
                ('another owner', self.CONSOLE_LINK, self.image(self.CONSOLE_LINK, uid=1000)),
                ('another group', self.CONSOLE_LINK, self.image(self.CONSOLE_LINK, gid=1000)),
                ('another mode', self.CONSOLE_LINK, self.image(self.CONSOLE_LINK, mode=0o755)),
                ('an extended attribute', self.CONSOLE_LINK, self.image(self.CONSOLE_LINK, xattrs={'user.x': '00'})),
                ('a regular file', self.CONSOLE_LINK, self.content(self.CONSOLE_LINK, b'not a link\n')),
                ('already in release 27', self.CONSOLE_LINK, self.content(self.CONSOLE_LINK, ('link', '/' + self.CONSOLE_UNIT), root=self.old)),
                ('the unit is missing', self.CONSOLE_LINK, self.content(self.CONSOLE_UNIT, None)),
                ('the unit has other bytes', self.CONSOLE_LINK, self.content(self.CONSOLE_UNIT, b'[Unit]\n')),
                ('the unit has other metadata', self.CONSOLE_LINK, self.image(self.CONSOLE_UNIT, uid=1000)),
            ])
            for rel in ('etc/systemd/system/multi-user.target.wants/aresos-console-keymap.service',
                        'etc/systemd/system/graphical.target.wants/other.service'):
                with self.subTest(rel=rel), self.content(rel, ('link', '/' + self.CONSOLE_UNIT)):
                    self.assertIsNone(self.fresh_explain(rel))

    def test_package_50s_rules_require_its_merged_origin(self):
        with self.console_keymap():
            self.classifier.main_base = 'ff51cac4^'
            for rel in (self.CONSOLE_UNIT, self.CONSOLE_LINK, self.UPDATERS):
                with self.subTest(rel=rel):
                    self.assertIsNone(self.fresh_explain(rel))
            self.classifier.main_base = 'HEAD'
            for rel in (self.CONSOLE_UNIT, self.CONSOLE_LINK, self.UPDATERS):
                with self.subTest(rel=rel):
                    self.assertIsNotNone(self.fresh_explain(rel))

    def test_package_50s_audit_addition_preserves_the_release_28_dropin_change(self):
        with self.console_keymap():
            rule, reason = self.fresh_explain(self.UPDATERS)
            self.assertEqual(rule, 'manifest')
            self.assertIn('aresos-console-keymap.service from 50 (#101)', reason)
            self.assertIn('user.slice from 23 (#36)', reason)
            expected = dict(scope='system', unit='aresos-console-keymap.service', added=['/' + self.CONSOLE_UNIT],
                            change='added unit', **{'from': ['50 (#101)']})
            self.assertEqual(self.classifier.updater_rows, [expected, dict(
                scope='system', unit='user.slice', added=['/' + self.DROPIN], **{'from': ['23 (#36)']})])
            with self.content(self.UPDATERS, self.audit(console_keymap=True)):
                self.assertIsNotNone(self.fresh_explain(self.UPDATERS))
                self.assertEqual(self.classifier.updater_rows, [expected])

    def test_package_50s_audit_rejects_every_near_miss_of_the_added_row(self):
        with self.console_keymap():
            units = json.loads((self.new / self.UPDATERS).read_bytes())
            row = next(row for row in units if row['name'] == 'aresos-console-keymap.service')
            cases = [dict(commands=['ExecStart=/usr/bin/true']), dict(scope='user'), dict(state='static'),
                     dict(suspicious=True), dict(suspicious=0), dict(active_state='active'), dict(load_state='loaded'),
                     dict(sub_state='exited'), dict(sources=[]), dict(sources=['/' + self.CONSOLE_UNIT, '/' + self.DROPIN]),
                     dict(extra=None)]
            for change in cases:
                changed = [dict(unit, **change) if unit is row else unit for unit in units]
                changed.sort(key=lambda unit: (unit['scope'], unit['name']))
                with self.subTest(change=change), self.content(self.UPDATERS, json.dumps(changed).encode()):
                    self.assertIsNone(self.fresh_explain(self.UPDATERS))
            for key in row:
                changed = [{name: value for name, value in unit.items() if name != key} if unit is row else unit for unit in units]
                with self.subTest(missing=key), self.content(self.UPDATERS, json.dumps(changed).encode()):
                    self.assertIsNone(self.fresh_explain(self.UPDATERS))
            self.assertIsNotNone(self.fresh_explain(self.UPDATERS))

    def test_package_50s_audit_still_rejects_other_rows_changes_and_unsorted_or_duplicate_units(self):
        with self.console_keymap():
            units = json.loads((self.new / self.UPDATERS).read_bytes())
            extra = dict(units[1], name='z-unreviewed.service')
            cases = {
                'a second new audit row': units + [extra],
                'a duplicate of the expected row': [*units[:2], units[1], *units[2:]],
                'the expected row in the wrong position': [units[1], units[0], units[2]],
                'old rows reordered': units[::-1],
                'an old row removed': units[1:],
                'an old command changed': [dict(units[0], commands=['ExecStart=/usr/bin/true']), *units[1:]],
                'an old source removed': [*units[:2], dict(units[2], sources=['/' + self.DROPIN])],
                'an unreviewed drop-in': [*units[:2], dict(units[2], sources=[*units[2]['sources'],
                    '/usr/lib/systemd/system/user.slice.d/99-other.conf'])],
            }
            for what, changed in cases.items():
                with self.subTest(what), self.content(self.UPDATERS, json.dumps(changed).encode()):
                    self.assertIsNone(self.fresh_explain(self.UPDATERS))
            for what, change in (
                    ('missing row while unit is present', self.content(self.UPDATERS, self.audit('/' + self.DROPIN))),
                    ('missing unit while row is present', self.content(self.CONSOLE_UNIT, None)),
                    ('unit with different metadata', self.image(self.CONSOLE_UNIT, mode=0o755)),
                    ('unit with different bytes', self.content(self.CONSOLE_UNIT, b'[Unit]\n')),
                    ('unit already in release 27', self.content(self.CONSOLE_UNIT,
                        (ROOT / 'os/config' / self.CONSOLE_UNIT).read_bytes(), root=self.old))):
                with self.subTest(what), change:
                    self.assertIsNone(self.fresh_explain(self.UPDATERS))
            self.assertIsNotNone(self.fresh_explain(self.UPDATERS))

    def test_only_javas_two_man_folders_with_its_pages_are_explained_as_folders_rpm_made(self):
        folder, sub = rd.JAVA_MAN_FOLDERS
        self.assertIsNotNone(self.explain(folder))
        # Another folder that is not in the package's file list, even with one of its files in it.
        extra = 'usr/lib/jvm/java-25-openjdk/extra'
        (self.new / extra).mkdir()
        (self.new / extra / 'x').write_bytes(b'x')
        self.classifier.owned['new'].add(f'/{extra}/x')
        self.classifier.policy['inventory'][f'{extra}/x'] = dict(kind=stat.S_IFREG, sha256='0' * 64)
        self.assertIsNone(self.explain(extra))
        # Another mode, an extended attribute, release 27 having it, or no page of the package in it.
        (self.new / sub).chmod(0o775)
        self.assertIsNone(self.explain(sub))
        (self.new / sub).chmod(0o755)
        self.attributes[sub] = {'user.x': '00'}
        self.assertIsNone(self.explain(sub))
        del self.attributes[sub]
        (self.old / sub).mkdir(parents=True)
        self.assertIsNone(self.explain(sub))
        (self.old / sub).rmdir()
        self.assertIsNotNone(self.explain(sub))
        del self.classifier.policy['inventory'][self.JAVA_MAN]
        for rel in (folder, sub):
            with self.subTest(rel=rel):
                self.assertIsNone(self.explain(rel))

    def test_a_file_missing_from_prisms_list_stops_the_whole_bundle(self):
        self.classifier.policy['inventory']['usr/lib/prismlauncher/extra'] = dict(kind=stat.S_IFREG, sha256='0' * 64)
        for rel in (rd.PRISM_FILES, 'usr/lib/prismlauncher/bin/prismlauncher'):
            with self.subTest(rel=rel):
                self.assertIsNone(self.explain(rel))

    def test_the_mod_record_must_be_its_pin_from_this_commit(self):
        rel = 'usr/share/aresos/manifest/aresos-mod.json'
        pin = self.classifier.mod_pin
        for record, explained in ((dict(sha256=pin, source_revision='a' * 40, pinned_sha256=pin), True),
                                  (dict(sha256='b' * 64, source_revision='a' * 40, pinned_sha256=pin), False),
                                  (dict(sha256=pin, source_revision='c' * 40, pinned_sha256=pin), False)):
            (self.new / rel).write_text(json.dumps(record))
            (self.new / rel).chmod(0o644)
            with self.subTest(record=record), patch.dict(os.environ, GITHUB_SHA='a' * 40):
                self.assertEqual(self.explain(rel) is not None, explained)

    def test_the_real_pins_cover_every_input_build_sh_installs(self):
        lock = json.loads((ROOT / 'os/minecraft/desktop.lock.json').read_text())
        pins = rd.minecraft_pins(lock, ROOT / 'os/minecraft/desktop.lock.json')
        self.assertEqual(len(pins), len(lock['fabric_loader']['libraries']) + len(lock['mods']) + len(lock['components']) + 1)
        jar = pins[rd.MINECRAFT + '/mods/aresos.jar']
        self.assertEqual(jar[0], self.classifier.mod_pin)
        self.assertIn('equal to its pin', jar[2])


class WorkflowGateTest(unittest.TestCase):
    """Only release_28 reaches the publishing job; the dry run cannot publish by its structure."""

    def test_each_input_runs_only_its_job_and_only_on_the_package_42_branch(self):
        on_branch = {'github.ref_name': BRANCH}
        for name, job in WORKFLOW['jobs'].items():
            with self.subTest(job=name):
                self.assertEqual(condition(job['if'], mode='', **on_branch, **{'inputs.release_28': True}), name == 'release-28')
                self.assertEqual(condition(job['if'], mode='', **on_branch, **{'inputs.dry_run_28': True}),
                                 name == 'release-28-dry-run')
                self.assertFalse(condition(job['if'], mode='', **on_branch,
                                           **{'inputs.release_28': True, 'inputs.dry_run_28': True}))
                self.assertEqual(condition(job['if'], mode='', **on_branch, **{'inputs.check_build': 'resolve'}),
                                 name == 'check-build')
                self.assertFalse(condition(job['if'], mode='', **on_branch))
                for other in ('main', 'pkg/27-first-update-release', 'pkg/22d-tools-without-stick'):
                    for flag in ('inputs.release_28', 'inputs.dry_run_28'):
                        self.assertFalse(condition(job['if'], mode='', **{'github.ref_name': other, flag: True})
                                         and name.startswith('release-28'))
                # The publishing job needs release_28 whatever else is dispatched.
                if name == 'release-28':
                    for other in ('inputs.dry_run_28', 'inputs.release_27', 'inputs.release_13', 'inputs.checks_only'):
                        self.assertFalse(condition(job['if'], mode='', **on_branch, **{other: True}))

    def test_the_dry_run_has_no_write_permission_no_signing_and_no_publish_step(self):
        job = WORKFLOW['jobs']['release-28-dry-run']
        self.assertEqual(job['permissions'], {'contents': 'read', 'packages': 'read', 'actions': 'read'})
        runs = '\n'.join(step.get('run', '') for step in job['steps'])
        sources = {p.name: p.read_text() for p in (ROOT / 'os/ci').rglob('*') if p.suffix in ('.py', '.sh')}
        self.assertNotIn('publish.sh', reachable(runs, sources))
        self.assertNotIn('publish.sh', runs)
        for word in ('cosign sign', 'skopeo copy', 'podman push', 'docker push', 'id-token'):
            self.assertNotIn(word, yaml.dump(job))
        # Only the job's own token, whose permissions are the ones above: no owner token that could push anyway.
        self.assertEqual(set(re.findall(r'secrets\.(\w+)', yaml.dump(job))), {'GITHUB_TOKEN'})
        self.assertFalse([step for step in job['steps'] if rd_publish_step(step)])
        publisher = WORKFLOW['jobs']['release-28']
        self.assertEqual(publisher['permissions'], {'contents': 'read', 'packages': 'write', 'id-token': 'write', 'actions': 'read'})
        self.assertEqual(len([step for step in publisher['steps'] if rd_publish_step(step)]), 1)

    def test_the_dry_run_is_the_release_job_without_its_publish_step(self):
        def normal(job, mode):
            steps = []
            for step in WORKFLOW['jobs'][job]['steps']:
                if rd_publish_step(step):
                    continue
                text = yaml.dump(step).replace('REHEARSAL_MODE: ' + mode, 'REHEARSAL_MODE: <mode>')
                steps.append(text.replace('release-28-dry-run-evidence', 'os-image-evidence'))
            return steps
        self.assertEqual(normal('release-28-dry-run', 'dry-run-28'), normal('release-28', 'publish-28'))
        for key in ('runs-on', 'timeout-minutes'):
            self.assertEqual(WORKFLOW['jobs']['release-28-dry-run'][key], WORKFLOW['jobs']['release-28'][key])

    def test_the_release_job_has_release_27s_reviewed_shape(self):
        def normal(job, mode, previous):
            return [yaml.dump(step).replace('REHEARSAL_MODE: ' + mode, 'REHEARSAL_MODE: <mode>')
                    .replace('release ' + previous, 'release <previous>').replace('package 27 release', 'package <n> release')
                    .replace('package 42 release', 'package <n> release') for step in WORKFLOW['jobs'][job]['steps']]
        self.assertEqual(normal('release-28', 'publish-28', '27'), normal('release-27', 'release-27', '13'))
        for key in ('runs-on', 'timeout-minutes', 'permissions'):
            self.assertEqual(WORKFLOW['jobs']['release-28'][key], WORKFLOW['jobs']['release-27'][key])

    def test_titles_and_package_follow_the_inputs(self):
        ledger = guard.PACKAGES['42']
        for world, kind in ((inputs(**{'inputs.release_28': True}), 'publish-28'),
                            (inputs(**{'inputs.dry_run_28': True}), 'dry-run-28'),
                            # Review 1, N1: both inputs run no job; the slip is counted as a dry run, not as the publish.
                            (inputs(**{'inputs.release_28': True, 'inputs.dry_run_28': True}), 'dry-run-28'),
                            (inputs(**{'inputs.check_build': 'resolve'}), 'resolve'),
                            (inputs(**{'inputs.checks_only': True}), 'checks')):
            with self.subTest(kind=kind):
                self.assertEqual(run_name(world), ledger['titles'][kind])
        expression = re.fullmatch(r'\$\{\{(.*)\}\}', WORKFLOW['env']['REHEARSAL_PACKAGE'].strip()).group(1)
        self.assertEqual(base.workflow_expression(expression, inputs()), '42')
        for job, mode in (('release-28', 'publish-28'), ('release-28-dry-run', 'dry-run-28')):
            modes = {step['env']['REHEARSAL_MODE'] for step in WORKFLOW['jobs'][job]['steps'] if 'REHEARSAL_MODE' in step.get('env', {})}
            self.assertEqual(modes, {mode})

    def test_resolve_and_checks_runs_read_their_caps_before_their_work(self):
        # Review 1, S3: on this branch the check build's guard step comes right after the checkout, before the tools.
        steps = WORKFLOW['jobs']['check-build']['steps']
        self.assertTrue(steps[0]['uses'].startswith('actions/checkout@'))
        self.assertEqual(steps[0]['with'], {'persist-credentials': 'false'})
        reserve = steps[1]
        self.assertEqual((reserve['run'], reserve['env']['REHEARSAL_MODE']), ('python3 os/ci/rehearsal_guard.py ci 120', 'resolve'))
        self.assertEqual(reserve['env']['GH_TOKEN'], '${{ secrets.GITHUB_TOKEN }}')
        self.assertTrue(condition(reserve['if'], mode='', **{'github.ref_name': BRANCH}))
        for other in ('main', 'pkg/22d-tools-without-stick', 'pkg/27-first-update-release'):
            self.assertFalse(condition(reserve['if'], mode='', **{'github.ref_name': other}))
        self.assertEqual([step.get('env', {}).get('GH_TOKEN') for step in steps[2:] if step.get('env', {}).get('GH_TOKEN')], [])
        # The checks-only run reads its cap on this branch before the suite.
        steps = WORKFLOW['jobs']['regressions']['steps']
        reserve, = [i for i, step in enumerate(steps) if 'rehearsal_guard.py ci' in step.get('run', '')]
        suite, = [i for i, step in enumerate(steps) if 'unittest discover' in step.get('run', '')]
        self.assertLess(reserve, suite)
        self.assertEqual(steps[reserve]['env']['REHEARSAL_MODE'], 'checks')
        self.assertTrue(condition(steps[reserve]['if'], mode='', **{'github.ref_name': BRANCH}))
        self.assertFalse(condition(steps[reserve]['if'], mode='', **{'github.ref_name': 'main'}))
        # Both jobs read the run history with the job token.
        for job in ('check-build', 'regressions'):
            self.assertEqual(WORKFLOW['jobs'][job]['permissions'].get('actions'), 'read')

    def test_every_step_script_accepts_the_environment_its_job_gives_it(self):
        """GateScan (test_release27): each environment and argument gate the job's scripts surely reach.

        GateScan cannot follow registry_auth's command table or build_tools' release table, so each step's
        environment also goes through those gates directly: the job-token read, the release build, the guard.
        """
        for job, flag in (('release-28', 'inputs.release_28'), ('release-28-dry-run', 'inputs.dry_run_28')):
            world = inputs(**{flag: True})
            self.assertTrue(base.workflow_expression(WORKFLOW['jobs'][job]['if'], world))
            failures, evaluated, scripts = [], set(), set()
            for step, environment in job_steps(job, world):
                self.assertEqual(environment['REHEARSAL_PACKAGE'], '42')
                runs = list(base.step_runs(step, environment, world))
                if any(argv[1:2] == ['launch'] for script, argv, _ in runs if script == 'os/ci/build_tools.py'):
                    # launch runs `build_tools.py privileged` through sudo -E: the same environment.
                    runs.append(('os/ci/build_tools.py', ['os/ci/build_tools.py', 'privileged', '/tmp/build-tools.json'], []))
                for script, argv, removed in runs:
                    scripts.add((script, tuple(argv[1:2])))
                    if script == 'os/ci/registry_auth.py' and argv[1] != 'cleanup':
                        with patch.dict(os.environ, environment, clear=True):
                            registry_auth.require_dispatch()
                    if script == 'os/ci/build_tools.py' and argv[1] == 'privileged':
                        release = build_tools.RELEASE_MODES[environment['REHEARSAL_MODE']]
                        self.assertEqual((release, build_tools.RELEASE_BUILDS[release]['branch']), ('28', BRANCH))
                    if script == 'os/ci/rehearsal_guard.py':
                        ledger = guard.PACKAGES[environment['REHEARSAL_PACKAGE']]
                        self.assertEqual(ledger['titles'][environment['REHEARSAL_MODE']], run_name(world))
                    for path, line, text, passed in base.GateScan(
                            {k: v for k, v in environment.items() if k not in removed}, argv).run(script):
                        evaluated.add(path)
                        if not passed:
                            failures.append(f"{job}: {step['name']}: {path}:{line}: {text}")
            with self.subTest(job=job):
                self.assertEqual(failures, [])
                self.assertIn('os/ci/rehearsal_guard.py', evaluated)
                self.assertLessEqual({('os/ci/rehearsal_guard.py', ('ci',)), ('os/ci/registry_auth.py', ('create',)),
                                      ('os/ci/build_tools.py', ('privileged',)), ('os/ci/registry_auth.py', ('cleanup',))}, scripts)


@unittest.skipIf(os.name == 'nt' or shutil.which('bash') is None, 'runs check-build.sh with stand-ins for podman')
class ReleaseChecksTest(unittest.TestCase):
    """The release job publishes the image its check build checked as a release (18c's security review, K6).

    Release 28's image checks (os/ci/check-image.sh, and through it image-checks.sh, Control's included once
    it rides) run inside `bash os/ci/check-build.sh build`, not as steps of the job. This holds that the job
    runs that step, that it checks localhost/aresos:check as a release and tags exactly that image
    localhost/aresos:ci, that nothing later in the job builds, pulls or tags that name, and that publish.sh
    copies and signs localhost/aresos:ci.
    """
    CHECK_BUILD = 'bash os/ci/check-build.sh build'

    def run_check_build(self, job):
        """The real check-build.sh build under GITHUB_JOB=<job>, every privileged command a stand-in; its calls in order."""
        work = pathlib.Path(tempfile.mkdtemp(dir=ROOT / 'os/tests'))
        self.addCleanup(shutil.rmtree, work)
        (work / 'os/ci').mkdir(parents=True)
        shutil.copy(ROOT / 'os/ci/check-build.sh', work / 'os/ci/check-build.sh')
        (work / 'os/ci/check-image.sh').write_text('echo "check-image $*" >> calls\n')
        (work / 'evidence/vm-pass-1').mkdir(parents=True)
        (work / 'evidence/vm-pass-1/policy-result.json').write_text('ARESOS_ACTIVE_SESSION_POLKIT_PASSED\n')
        (work / 'evidence/vm-pass-1/console-keymap-result.json').write_text('CONSOLE_KEYMAP_PASSED\n')
        stubs = work / 'bin'
        stubs.mkdir()
        revision = 'a' * 40
        for name, body in (('jq', 'echo stand-in'), ('git', f'echo {revision}'), ('python3', 'echo "python3 $*" >> calls'),
                           ('sudo', 'echo "sudo $*" >> calls\nif [ "$2" = build ]; then\n'
                                    f'echo "MOD_SOURCE {revision} {"c" * 64}"\necho "MOD_JAR_BUILT {"d" * 64} from {revision}"\n'
                                    f'echo "MOD_JAR_PINNED {"d" * 64}"\nfi\n')):
            (stubs / name).write_text('#!/bin/sh\n' + body)
            (stubs / name).chmod(0o755)
        result = subprocess.run(['bash', 'os/ci/check-build.sh', 'build'], cwd=work, capture_output=True, text=True,
                                timeout=60, env={'PATH': f'{stubs}:/usr/bin:/bin', 'GITHUB_JOB': job})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CHECK_BUILD_VM_PASSED', result.stdout)
        return (work / 'calls').read_text().splitlines()

    def test_the_release_jobs_check_the_image_they_publish_as_a_release(self):
        for job in ('release-28', 'release-28-dry-run'):
            with self.subTest(job=job):
                steps = WORKFLOW['jobs'][job]['steps']
                runs = [step.get('run', '') for step in steps]
                checked, = [index for index, run in enumerate(runs) if run.strip() == self.CHECK_BUILD]
                # Nothing in the step sets the build kind; check-build.sh takes it from the job's own name.
                self.assertNotIn('env', steps[checked])
                calls = self.run_check_build(job)
                build, = [i for i, call in enumerate(calls) if call.startswith('sudo podman build') and 'os/Containerfile' in call]
                self.assertIn('--build-arg ARESOS_BUILD_KIND=release', calls[build])
                self.assertIn('--tag localhost/aresos:check', calls[build])
                check, = [i for i, call in enumerate(calls) if call.startswith('check-image ')]
                self.assertEqual(calls[check], 'check-image localhost/aresos:check release')
                tag, = [i for i, call in enumerate(calls) if call == 'sudo podman tag localhost/aresos:check localhost/aresos:ci']
                self.assertLess(build, check)
                self.assertLess(check, tag)
                # No other command of the check build writes the name the job publishes.
                writers = [call for call in calls if 'localhost/aresos:ci' in call and call != calls[tag]
                           and re.search(r'podman (build|tag|pull|load|import|commit)\b', call)
                           and not re.search(r'--tag localhost/aresos:vm\b', call)]
                self.assertEqual(writers, [])
                # Later steps only read localhost/aresos:ci: the isolation check and the diff (build_tools, release_diff).
                for run in runs[checked + 1:]:
                    self.assertNotRegex(run, r'podman (build|tag|pull|load|import|commit)\b[^\n]*localhost/aresos:ci')
        import inspect
        source = inspect.getsource(build_tools.build_release)
        self.assertEqual(re.findall(r"tools\['podman'\], '(\w+)'", source), ['pull', 'run'])
        self.assertIn("previous['reference']]", source.split("'pull'")[1].split('\n')[0])
        self.assertEqual(set(re.findall(r"command\('podman', '(\w+)'", inspect.getsource(rd.main))),
                         {'create', 'mount', 'run', 'unmount', 'rm'})
        # publish.sh copies exactly that image, and signs and records the digest of that copy.
        publish = (ROOT / 'os/ci/publish.sh').read_text()
        self.assertEqual(re.findall(r'containers-storage:\S+', publish), ['containers-storage:localhost/aresos:ci'])
        self.assertIn('--digestfile evidence/published-digest.txt \\\n    containers-storage:localhost/aresos:ci', publish)
        self.assertIn('digest=$(cat evidence/published-digest.txt)', publish)
        self.assertIn('cosign sign --yes "$reference"', publish)
        publishing = WORKFLOW['jobs']['release-28']['steps']
        self.assertLess([step.get('run', '').strip() for step in publishing].index(self.CHECK_BUILD),
                        [i for i, step in enumerate(publishing) if rd_publish_step(step)][0])

    def test_only_the_check_build_job_checks_a_throwaway(self):
        self.assertIn('check-image localhost/aresos:check throwaway', self.run_check_build('check-build'))


def rd_publish_step(step):
    return 'publish.sh' in step.get('run', '') or step.get('name') == guard.PUBLISH_STEP


class Guard42Test(unittest.TestCase):
    def setUp(self):
        guard.configure('42')
        self.addCleanup(guard.configure, '11c')

    def history(self, titles):
        runs = [dict(id=10 + n, event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, status='completed',
                     conclusion='success', created_at=f'2026-11-16T0{n}:00:00Z', display_title=title)
                for n, title in enumerate(titles)]
        job = dict(name='job', conclusion='success', started_at='2026-11-16T00:00:00Z', completed_at='2026-11-16T01:00:00Z',
                   steps=[dict(name='Set up job', conclusion='success', started_at='2026-11-16T00:00:00Z',
                               completed_at='2026-11-16T01:00:00Z')])

        def api(path):
            if path.startswith('actions/runs?'):
                return dict(workflow_runs=runs, history=dict(complete=True, ids_count=len(runs), total_count=len(runs)))
            if path.startswith('actions/runs/') and path.endswith('/jobs?per_page=100'):
                return dict(total_count=1, jobs=[job])
            return next(run for run in runs if path == f"actions/runs/{run['id']}")
        return runs, api

    def test_the_ledger_counts_every_dispatch_and_keeps_publishing_shut(self):
        ledger = guard.PACKAGES['42']
        self.assertEqual(guard.BRANCH, BRANCH)
        self.assertIn('42', guard.TITLED_PACKAGES)
        self.assertEqual(set(ledger['titles']), set(ledger['dispatch_caps']))
        self.assertEqual(set(ledger['job_bounds']), set(ledger['dispatch_caps']))
        # Review 1, B1: publishing stayed shut until the owner's OK; step 5 raised both caps to 1 under his standing
        # rule (board #388, 2026-11-19), for exactly one publishing dispatch.
        self.assertEqual(ledger['publish_cap'], 1)
        self.assertEqual(ledger['dispatch_caps']['publish-28'], 1)
        self.assertIn("the owner's standing rule (board #388, 2026-11-19", ledger['publish_gate'])
        self.assertIn('nothing is pinned for the laptop until it passes', ledger['publish_gate'])
        self.assertIn('Step 5 (2026-11-19): publish-28 and publish_cap from 0 to 1', ledger['budget'])
        self.assertEqual(ledger['job_bounds']['publish-28'], int(WORKFLOW['jobs']['release-28']['timeout-minutes']))
        self.assertEqual(ledger['job_bounds']['dry-run-28'], int(WORKFLOW['jobs']['release-28-dry-run']['timeout-minutes']))
        # The check-build job's limit depends on its mode since 18c (131 for control, 120 otherwise); the ledger
        # bounds the resolve mode, the only check build package 42 dispatches.
        resolve = dict(base.UPDATE_INPUTS, **{'github.ref_name': 'pkg/42-release-28', 'inputs.rehearsal': '',
                                              'inputs.check_build': 'resolve'})
        self.assertEqual(str(ledger['job_bounds']['resolve']),
                         base.workflow_text(str(WORKFLOW['jobs']['check-build']['timeout-minutes']), resolve))
        titles = ledger['titles']
        # The dry-run cap (7 since 2026-11-19, the cut's bytecode fix) is read from the ledger, then exceeded by one.
        dry_runs = ledger['dispatch_caps']['dry-run-28']
        self.assertEqual(dry_runs, 7)
        runs, api = self.history([titles['resolve']] + [titles['dry-run-28']] * dry_runs)
        with patch.object(guard, 'api', side_effect=api):
            result = guard.budget(0)
            # Step 3 added the rehearsal kind release-28 (cap 0; test_release28_rehearsal holds it).
            self.assertEqual(result['dispatch_counts'],
                             {'dry-run-28': dry_runs, 'publish-28': 0, 'resolve': 1, 'checks': 0, 'release-28': 0})
            self.assertEqual(result['consumed_minutes'], 60 * (1 + dry_runs))
            runs.append(dict(runs[-1], id=99, display_title=titles['dry-run-28']))
            with self.assertRaisesRegex(AssertionError, 'dry-run-28 dispatch allowance exhausted'):
                guard.budget(0)
            # Step 3's rehearsal kind (cap 0 until step 6 raised it to 3, then 4): four dispatches pass, a fifth stops.
            runs[-1]['display_title'] = 'Two-disk rehearsal (release-28)'
            self.assertEqual(guard.budget(0)['dispatch_counts']['release-28'], 1)
            runs.extend(dict(runs[-1], id=200 + n) for n in range(4))
            with self.assertRaisesRegex(AssertionError, 'STOP: release-28 dispatch allowance exhausted'):
                guard.budget(0)
            del runs[-4:]
            # A title the ledger does not know stops with a line that names it.
            runs[-1]['display_title'] = 'Two-disk rehearsal (tools-local)'
            with self.assertRaisesRegex(AssertionError, r"^STOP: run 99 is titled 'Two-disk rehearsal \(tools-local\)', "
                                                        "which package 42's ledger does not know"):
                guard.budget(0)
            # The one publishing dispatch counts; a second stops.
            runs[-1]['display_title'] = titles['publish-28']
            self.assertEqual(guard.budget(0)['dispatch_counts']['publish-28'], 1)
            runs.append(dict(runs[-1], id=101))
            with self.assertRaisesRegex(AssertionError, 'STOP: publish-28 dispatch allowance exhausted'):
                guard.budget(0)
            runs.pop()
            runs[-1]['display_title'] = titles['resolve']
            self.assertEqual(guard.budget(0)['dispatch_counts']['resolve'], 2)
            runs.append(dict(runs[-1], id=100))
            with self.assertRaisesRegex(AssertionError, 'STOP: resolve dispatch allowance exhausted'):
                guard.budget(0)

    def run_main(self, mode, kind, history=None, title=None, ref=None):
        titles = guard.PACKAGES['42']['titles']
        runs, api = self.history([titles['dry-run-28']] if history is None else history)
        current = dict(event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, id=50, status='in_progress', conclusion=None,
                       display_title=title or titles[kind], head_branch=BRANCH, created_at='2026-11-16T09:00:00Z')
        runs.append(current)
        environment = dict(REHEARSAL_PACKAGE='42', REHEARSAL_MODE=kind, GITHUB_REF_NAME=BRANCH, GITHUB_REF=ref if ref is not None else 'refs/heads/' + BRANCH, GITHUB_RUN_ID='50',
                           GITHUB_SHA='a' * 40, GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS')
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory, contextlib.chdir(directory), \
                patch.object(guard, 'api', side_effect=api), patch.dict(os.environ, environment, clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', mode, '180' if mode == 'ci' else '0']), \
                contextlib.redirect_stdout(io.StringIO()):
            guard.main()
            return sorted(path.name for path in pathlib.Path('evidence').iterdir())

    def test_a_publish_dispatch_stops_at_its_first_guard_until_the_owners_ok(self):
        # Review 1, B1, with the branch's history then: run 43828756952 (resolve), dry runs 1 to 3; the gate as it was
        # before step 5 opened it (both caps 0).
        with patch.dict(guard.PACKAGES['42']['dispatch_caps'], {'publish-28': 0}), patch.dict(guard.PACKAGES['42'], publish_cap=0):
            self.shut_gate()

    def shut_gate(self):
        titles = guard.PACKAGES['42']['titles']
        today = [titles['resolve'], titles['dry-run-28'], titles['dry-run-28'], titles['dry-run-28']]
        # The cut's dry run, the cut's resolve and the checks-only run still pass their guards.
        for kind in ('dry-run-28', 'resolve', 'checks'):
            with self.subTest(kind=kind):
                self.assertIn('42-dispatch-authorization.json', self.run_main('ci', kind, today))
        # release_28 stops at its job's guard, the first step after checkout, and at publish.sh's guard.
        for mode in ('ci', 'publish-ci'):
            with self.subTest(mode=mode), self.assertRaisesRegex(AssertionError, 'STOP: publish-28 dispatch allowance exhausted'):
                self.run_main(mode, 'publish-28', today)
        # Such a slip counts, and stops every later dispatch on the branch until a ledger commit records it.
        with self.assertRaisesRegex(AssertionError, 'STOP: publish-28 dispatch allowance exhausted'):
            self.run_main('ci', 'dry-run-28', today + [titles['publish-28']])
        # Raising only the dispatch cap opens nothing: publish_cap 0 allows no publish.
        with patch.dict(guard.PACKAGES['42']['dispatch_caps'], {'publish-28': 1}), \
                self.assertRaisesRegex(AssertionError, 'STOP: the ledger allows no publish'):
            self.run_main('publish-ci', 'publish-28', today)
        self.assertEqual(guard.PUBLISH_KINDS, ('release-13', 'release-27', 'publish-28'))

    def test_the_opened_gate_passes_one_publish_and_only_the_publishing_kind(self):
        # Step 5 raised both caps to 1 (board #388): the release_28 dispatch passes its job's guard and publish.sh's.
        titles = guard.PACKAGES['42']['titles']
        today = [titles['resolve'], titles['dry-run-28'], titles['dry-run-28'], titles['dry-run-28']]
        for mode in ('ci', 'publish-ci'):
            with self.subTest(mode=mode):
                self.assertIn('42-dispatch-authorization.json', self.run_main(mode, 'publish-28', today))
        self.assertIn('publish-authorization.json', self.run_main('publish-ci', 'publish-28', today))
        # Only the publishing kind passes the publish gate.
        with self.assertRaises(AssertionError):
            self.run_main('publish-ci', 'dry-run-28', today)
        # A second release_28 dispatch stops at its first guard.
        with self.assertRaisesRegex(AssertionError, 'STOP: publish-28 dispatch allowance exhausted'):
            self.run_main('ci', 'publish-28', today + [titles['publish-28']])

    def test_resolve_and_checks_runs_stop_at_their_own_guard(self):
        # Review 1, S3: the job's guard counts the run itself.
        titles = guard.PACKAGES['42']['titles']
        with self.assertRaisesRegex(AssertionError, 'STOP: resolve dispatch allowance exhausted'):
            self.run_main('ci', 'resolve', [titles['resolve'], titles['resolve']])
        # Step 6 raised the checks cap to 3, then 5, 6, 7 and 8 (the model gate needs one on each rehearsal head;
        # run 44710509866 hit the regressions job's time limit, 44717214380 a test binding it, 44722199520 was
        # cancelled for the preflight step's limit): the ninth stops.
        self.assertIn('42-dispatch-authorization.json', self.run_main('ci', 'checks', [titles['checks']] * 7))
        with self.assertRaisesRegex(AssertionError, 'STOP: checks dispatch allowance exhausted'):
            self.run_main('ci', 'checks', [titles['checks']] * 8)
        # A check build of another kind is no dispatch this ledger knows: its own guard names its title.
        with self.assertRaisesRegex(AssertionError, r"STOP: run 50 is titled 'OS image check build \(build, never published\)'"):
            self.run_main('ci', 'resolve', [], title='OS image check build (build, never published)')

    @unittest.skipIf(os.name == 'nt' or shutil.which('bash') is None, 'needs a Linux bash')
    def test_publish_sh_accepts_only_the_release_branches_before_its_guard(self):
        text = (ROOT / 'os/ci/publish.sh').read_text()
        self.assertIn('    pkg/42-release-28) release=28 ;;\n', text)
        self.assertLess(text.index('esac'), text.index('rehearsal_guard.py publish-ci'))
        environment = dict(os.environ, GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS',
                           GITHUB_REF_NAME='pkg/42-release-28-other', GITHUB_REF='refs/heads/pkg/42-release-28-other', PATH=os.environ.get('PATH', ''))
        result = subprocess.run(['bash', 'os/ci/publish.sh'], cwd=ROOT, env=environment, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to publish from pkg/42-release-28-other', result.stderr)


class ReleaseBuildGateTest(unittest.TestCase):
    ENVIRONMENT = dict(GITHUB_REPOSITORY='Ares-Empire/AresOS', GITHUB_REF_NAME=BRANCH, REHEARSAL_PACKAGE='42',
                       GITHUB_EVENT_NAME='workflow_dispatch')

    def test_both_kinds_build_release_28_against_release_27(self):
        self.assertEqual(build_tools.RELEASE_MODES, {'release-27': '27', 'publish-28': '28', 'dry-run-28': '28'})
        self.assertEqual(build_tools.RELEASE_BUILDS['28']['previous'], rd.PREVIOUS_28)
        self.assertEqual(build_tools.RELEASE_BUILDS['27']['previous'], rd.PREVIOUS)
        tools = {name: sys.executable for name in build_tools.NAMES}
        for changes in (dict(GITHUB_REF_NAME='pkg/27-first-update-release'), dict(REHEARSAL_MODE='release-27'),
                        dict(REHEARSAL_MODE='checks'), dict(GHCR_READ_TOKEN='SYNTHETIC-NOT-USED'),
                        dict(GITHUB_REPOSITORY='elsewhere/AresOS')):
            environment = dict(self.ENVIRONMENT, REHEARSAL_MODE='dry-run-28')
            environment.update(changes)
            with self.subTest(changes=changes), patch.dict(os.environ, environment, clear=True), \
                    patch.object(subprocess, 'run', side_effect=AssertionError('no command may run')):
                with self.assertRaises(AssertionError):
                    build_tools.build_release(tools, '28')

    def test_the_job_token_read_accepts_only_package_42s_kinds_on_its_branch(self):
        # Step 3's rehearsal (release-28) reads with the job token too; test_release28_rehearsal holds its gates.
        for mode in ('publish-28', 'dry-run-28', 'release-28'):
            with patch.dict(os.environ, dict(self.ENVIRONMENT, REHEARSAL_MODE=mode), clear=True):
                registry_auth.require_dispatch()
        for changes in (dict(REHEARSAL_MODE='release-27'), dict(REHEARSAL_MODE='update'), dict(REHEARSAL_MODE='tools-local'),
                        dict(REHEARSAL_PACKAGE='27'), dict(GITHUB_REF_NAME='main'), dict(GITHUB_EVENT_NAME='push')):
            environment = dict(self.ENVIRONMENT, REHEARSAL_MODE='dry-run-28')
            environment.update(changes)
            with self.subTest(changes=changes), patch.dict(os.environ, environment, clear=True), self.assertRaises(AssertionError):
                registry_auth.require_dispatch()


@unittest.skipIf(os.name == 'nt', 'symlinks and modes need Linux')
class MainSmokeTest(unittest.TestCase):
    """release_diff.main for release 28, end to end on small stand-in images (podman and skopeo emulated)."""
    JAVA = 'usr/lib/jvm/java-25/bin/java'

    def setUp(self):
        self.enterContext(contextlib.chdir(ROOT))
        self.work = pathlib.Path(tempfile.mkdtemp(dir=ROOT / 'os/tests'))
        self.addCleanup(shutil.rmtree, self.work)
        source = rd.PREVIOUS_SOURCE_28
        show = lambda path: subprocess.check_output(['git', 'show', f'{source}:{path}'])
        policy = {f'usr/share/aresos/policy/{name}': (ROOT / 'os/policy' / name).read_bytes()
                  for name in ('masked-system-units.txt', 'masked-user-units.txt')}
        updaters, dropin = Classifier28Test.UPDATERS, Classifier28Test.DROPIN
        tag = rd.FONT_CACHES + 'CACHEDIR.TAG'
        old = {**policy, 'etc/hostname': b'aresos\n', 'usr/share/aresos/manifest/packages.lock.json': show('os/packages.lock.json'),
               rd.SCHEMAS: (FIXTURES / 'before.compiled').read_bytes(),
               rd.RC_XML: show('os/config/' + rd.RC_XML), 'usr/share/aresos/apps/terminal.json': show('os/config/usr/share/aresos/apps/terminal.json'),
               updaters: Classifier28Test.audit(), tag: b'tag'}
        new = {**policy, 'etc/hostname': b'aresos\n', 'usr/share/aresos/manifest/packages.lock.json': (ROOT / 'os/packages.lock.json').read_bytes(),
               rd.SCHEMAS: (FIXTURES / 'after.compiled').read_bytes(),
               rd.PRISM + '/bin/prismlauncher': b'prism', rd.PRISM + '/libprism.so': ('link', 'bin/prismlauncher'),
               rd.PRISM_FILES: f'{hashlib.sha256(b"prism").hexdigest()}  /{rd.PRISM}/bin/prismlauncher\n'.encode(),
               rd.RC_XML: (ROOT / 'os/config' / rd.RC_XML).read_bytes(),
               'usr/share/aresos/apps/terminal.json': (ROOT / 'os/config/usr/share/aresos/apps/terminal.json').read_bytes(),
               self.JAVA: b'java', Classifier28Test.JAVA_MAN: b'.TH java 1\n', tag: b'tag',
               rd.ALTERNATIVES_ADMIN + 'java': f'auto\n/usr/bin/java\n\n/{self.JAVA}\n25\n'.encode(),
               rd.ALTERNATIVES + 'java': ('link', '/' + self.JAVA), 'usr/bin/java': ('link', '/etc/alternatives/java'),
               updaters: Classifier28Test.audit('/' + dropin, console_keymap=True),
               Classifier28Test.CONSOLE_LINK: ('link', '/' + Classifier28Test.CONSOLE_UNIT),
               dropin: (ROOT / 'os/config' / dropin).read_bytes(),
               # 23b's font folder with its real caches in both formats (fixtures/release28-fontcache).
               **{rd.FONT_CACHES + path.name: path.read_bytes() for path in FontCacheTest.FIXTURES.glob('*.cache-9')},
               **{f'usr/share/fonts/aresos/{path.name}': path.read_bytes() for path in (ROOT / 'os/config/usr/share/fonts/aresos').iterdir()}}
        for path in (ROOT / 'os/config' / rd.CROWN).iterdir():
            new[f'{rd.CROWN}/{path.name}'] = path.read_bytes()
        # As the build copies them: every os/config file changed since release 27 (review 1, N5: each must arrive).
        changed = rd.git_changed(rd.PREVIOUS_SOURCE_28, 'os/config')
        new.update({rel: (ROOT / 'os/config' / rel).read_bytes() for rel in changed if (ROOT / 'os/config' / rel).is_file()})
        self.roots = {}
        for name, files in (('old', old), ('new', new), ('base', {})):
            root = self.work / name
            root.mkdir()
            base.ClassifierTest.tree(None, root, files)
            # Release 27 already has the alternatives folders and greetd's graphical wants folder.
            for folder in (rd.ALTERNATIVES, rd.ALTERNATIVES_ADMIN, 'usr/bin', 'etc/systemd/system/graphical.target.wants',
                           'etc/systemd/system/multi-user.target.wants', 'usr/lib/sysusers.d', 'usr/lib/tmpfiles.d'):
                (root / folder).mkdir(parents=True, exist_ok=True)
            for path in root.rglob('*'):
                if path.is_dir():
                    path.chmod(0o755)
            self.roots[name] = root
        install_control_fixture(self.roots['new'])
        audit_path = self.roots['new'] / updaters
        rows = json.loads(audit_path.read_text()) + [rd.CONTROL_AUDIT]
        audit_path.write_text(json.dumps(sorted(rows, key=lambda row: (row['scope'], row['name']))))
        for rel in changed:  # build.sh's chmod 0755 line, and os/config's own executables
            if rel in rd.CHMOD_0755_28 or os.access(ROOT / 'os/config' / rel, os.X_OK):
                (self.roots['new'] / rel).chmod(0o755)
        nevras = lambda raw: base.lock_nevras(raw) + [json.loads((ROOT / 'os/google-chrome.lock.json').read_text())['nevra']]
        self.rpms = dict(old=nevras(show('os/packages.lock.json')), new=nevras((ROOT / 'os/packages.lock.json').read_bytes()))
        release = json.loads((ROOT / rd.PREVIOUS_28).read_text())
        self.images = {release['reference']: 'old', rd.NEW: 'new', json.loads((ROOT / 'os/manifest/base.json').read_text())['reference']: 'base'}
        labels = lambda revision: {'org.opencontainers.image.source': 'https://github.com/Ares-Empire/AresOS',
                                   'org.opencontainers.image.revision': revision}
        self.configs = dict(old=dict(rootfs=dict(diff_ids=['sha256:b', 'sha256:o']), config=dict(Cmd=['bash'], Labels=labels(release['source_commit']))),
                            new=dict(rootfs=dict(diff_ids=['sha256:b', 'sha256:n']), config=dict(Cmd=['bash'], Labels=labels('a' * 40))),
                            base=dict(rootfs=dict(diff_ids=['sha256:b']), config=dict(Cmd=['bash'], Labels={})))
        for name in ('inventory',):
            real = getattr(image_diff, name)
            self.enterContext(patch.object(image_diff, name, side_effect=lambda root, real=real: {
                rel: dict(value, uid=0, gid=0, xattrs={}) for rel, value in real(root).items()}))
        real_entry = rd.entry
        self.enterContext(patch.object(rd, 'entry', side_effect=lambda root, rel: None if real_entry(root, rel) is None
                                       else dict(real_entry(root, rel), uid=0, gid=0, xattrs={})))
        self.enterContext(patch.object(image_diff, 'command', side_effect=self.command))
        # The independently pinned tarball's expected inventory stays fixed while tests mutate the image.
        inventory = image_diff.inventory(self.roots['new'])
        self.enterContext(patch.object(rd, 'prism_inventory', return_value={rel: value for rel, value in inventory.items()
                          if rel == rd.PRISM or rel.startswith(rd.PRISM + '/')}))
        prism_pin = json.loads((ROOT / 'os/minecraft/desktop.lock.json').read_text())['prism']['sha256']
        self.enterContext(patch.dict(rd.PRISM_FILE_LISTS, {prism_pin: rd.file_sha256(self.roots['new'] / rd.PRISM_FILES)}))
        self.enterContext(patch.dict(os.environ, GITHUB_SHA='a' * 40))
        # main's merge base: this commit itself, so the image sources equal main's (S2's own tests change it).
        self.enterContext(patch.object(rd, 'main_merge_base', return_value='HEAD'))
        # Independent reviewed expectation for the smoke test's single-command stand-in package.
        self.enterContext(patch.object(rd, 'reviewed_alternatives', return_value={'java': dict(
            links={'/usr/bin/java': 'java'}, choices=[dict(priority=25, targets={'java': '/' + self.JAVA})])}))
        self.record_changes, self.verify = {}, (0, '')

    # rpm -ql names a package's folders too (javapackages-filesystem owns /usr/lib/jvm).
    # Like the real headless package, it names its man pages but not their folders.
    OWNED = {'headless': ['/usr/lib/jvm/java-25', '/usr/lib/jvm/java-25/bin', '/' + JAVA, '/usr/lib/jvm/java-25-openjdk',
                          '/' + Classifier28Test.JAVA_MAN],
             'javapackages-filesystem': ['/usr/lib/jvm']}

    def rpm_query(self, nevras):
        """Independent package records: never derive expected presence or bytes from the image under test."""
        lines = []
        for path in (path for nevra in nevras for key, paths in self.OWNED.items() if key in nevra for path in paths):
            data = {'/' + self.JAVA: b'java', '/' + Classifier28Test.JAVA_MAN: b'.TH java 1\n',
                    '/usr/lib/jvm/java-25/bin/keytool': b'keytool'}.get(path)
            record = dict(user='root', group='root', flags='0', size=str(len(data) if data is not None else 4096), algorithm='8',
                          digest=hashlib.sha256(data).hexdigest() if data is not None else '', target='', caps='',
                          mode=str((stat.S_IFREG | 0o644) if data is not None else (stat.S_IFDIR | 0o755)))
            record.update(self.record_changes.get(path, {}))
            lines.append('\t'.join([path] + [record[field] for field in rd.RPM_FILE_FIELDS[1:]]))
        return '\n'.join(lines)

    def command(self, tool, *args):
        if args[0] in ('create', 'mount') and tool == 'podman':
            return str(self.roots[self.images[args[-1]]]) if args[0] == 'mount' else args[-1]
        if args[0] in ('unmount', 'rm'):
            return ''
        if args[0] == 'run':
            if '--entrypoint=/usr/bin/python3' in args:
                self.assertEqual(args, ('run', '--pull=never', '--network=none', '--read-only', '--rm',
                                       '--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m', '--entrypoint=/usr/bin/python3',
                                       rd.NEW, '-c', rd.SCHEMA_REBUILD))
                if (self.roots['new'] / rd.SCHEMAS).read_bytes() != (FIXTURES / 'after.compiled').read_bytes():
                    raise subprocess.CalledProcessError(1, ['schema rebuild'], output='compiled schemas differ from deterministic rebuild')
                return 'SCHEMA_REBUILD_MATCHED'
            image = self.images[args[args.index('--entrypoint=/usr/bin/rpm') + 1]]
            if '-qa' in args:
                return '\n'.join(f'{nevra}\t{base.name_of(nevra)}' for nevra in self.rpms[image])
            if '--qf' in args:
                self.assertEqual((image, args[args.index('--qf') + 1]), ('new', rd.RPM_FILE_FORMAT))
                return self.rpm_query(args[args.index('--qf') + 2:])
            if '-V' in args:
                self.assertEqual(image, 'new')
                code, output = self.verify
                if code:
                    raise subprocess.CalledProcessError(code, ['rpm', '-V'], output=output)
                return output
            return '\n'.join(path for nevra in args[args.index('-ql') + 1:]
                             for key, paths in self.OWNED.items() if key in nevra for path in paths)
        if tool == 'skopeo':
            return json.dumps(self.configs[self.images[args[-1].removeprefix('containers-storage:')]])
        raise AssertionError(f'unexpected command {tool} {args}')

    def run_main(self):
        evidence = self.work / 'evidence'
        try:
            rd.main({name: sys.executable for name in build_tools.NAMES}, release='28', evidence=evidence)
        finally:
            # Kept for a test that expects a stop, too.
            self.result = json.loads((evidence / 'result.json').read_text()) if (evidence / 'result.json').exists() else None
            shutil.rmtree(evidence, ignore_errors=True)
        return self.result

    def test_release_28_passes_when_every_difference_is_explained(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            result = self.run_main()
        self.assertIn('IMAGE_DIFF_PASSED', printed.getvalue())
        self.assertEqual((result['status'], result['release'], result['previous_source']), ('passed', '28', rd.PREVIOUS_SOURCE_28))
        self.assertEqual(result['method'], 'full rebuild compared with release 27; every difference classified')
        self.assertEqual([row['nevra'].split('-1:')[0].split('-6.4')[0].split('-2026')[0] for row in result['packages']],
                         ['java-25-openjdk-crypto-adapter', 'java-25-openjdk-headless', 'javapackages-filesystem', 'tzdata-java'])
        self.assertEqual(result['theme'], dict(image=PACKAGE31_CROWN, image_checks=PACKAGE31_CROWN, equal=True))
        self.assertTrue(result['rc_xml']['added'] and result['rc_xml']['removed'])
        self.assertTrue(result['base_ancestry_verified'])
        rules = ' '.join(result['rules'])
        for expected in ('config: os/config file changed since release 27', 'config: os/config file new since release 27',
                         'manifest: package lock (package 23', 'package: file of a package added by package 23',
                         "package: package 23: folder of java-25-openjdk-headless's man pages",
                         'manifest: updater audit output', 'rebuilt the system font cache (32-bit'):
            self.assertIn(expected, rules)
        self.assertEqual(sorted((row['format'], row['folder'], row['change']) for row in result['font_caches']),
                         [('le32d4', FontCacheTest.ARESOS, 'added'), ('le64', FontCacheTest.ARESOS, 'added')])
        self.assertIn('build: package 50: systemctl enable console keymap link; from 50 (#101)', rules)
        self.assertEqual(result['updaters'], [dict(scope='system', unit='aresos-toold.service',
                                               added=['/usr/lib/systemd/system/aresos-toold.service'], change='added unit',
                                               **{'from': ['18c Part A (#58)']}),
                                         dict(scope='system', unit='aresos-console-keymap.service',
                                                   added=['/' + Classifier28Test.CONSOLE_UNIT], change='added unit', **{'from': ['50 (#101)']}),
                                             dict(scope='system', unit='user.slice', added=['/' + Classifier28Test.DROPIN],
                                                   **{'from': ['23 (#36)']})])
        # S2: the merge base, and no image source differs from it; S5: rpm -V's evidence, clean here.
        self.assertEqual(result['main'], dict(merge_base='HEAD', branch_changes={}, differing=[]))
        self.assertEqual(result['rpm_verify'], dict(packages=[row['nevra'] for row in result['packages']], exit_code=0,
                                                    line_count=0, lines=[]))
        self.assertIn('package: file of a package added by package 23 (Java 25 and its dependencies): owner, mode, link target '
                      'and bytes as its rpm database records them', result['rules'])
        self.assertNotIn('unexplained', ' '.join(result['rules']))

    def test_package_50s_unit_requires_its_audit_row_even_when_the_audit_is_unchanged(self):
        for dropins in (['/' + Classifier28Test.DROPIN], []):
            with self.subTest(dropins=dropins):
                (self.roots['new'] / Classifier28Test.UPDATERS).write_bytes(Classifier28Test.audit(*dropins))
                self.assertTrue((self.roots['new'] / Classifier28Test.CONSOLE_UNIT).is_file())
                with self.assertRaisesRegex(AssertionError, 'package 50 updater audit row missing or different'):
                    self.run_main()
                self.assertEqual(self.result['status'], 'stopped')
                self.assertEqual(self.result['unexplained'], [Classifier28Test.UPDATERS] if dropins else [])

    def test_an_unexplained_path_or_another_theme_stops(self):
        (self.roots['new'] / 'etc/surprise').write_bytes(b'?')
        (self.roots['new'] / 'etc/surprise').chmod(0o644)
        with self.assertRaisesRegex(AssertionError, 'STOP: 1 unexplained image differences'):
            self.run_main()
        # publish.sh publishes only a result whose status is passed.
        self.assertEqual((self.result['status'], self.result['unexplained'], self.result['unexplained_count']),
                         ('stopped', ['etc/surprise'], 1))
        (self.roots['new'] / 'etc/surprise').unlink()
        (self.roots['new'] / rd.CROWN / 'themerc').write_bytes(b'')
        with self.assertRaisesRegex(AssertionError, 'Ares-Crown theme in the image'):
            self.run_main()
        self.assertEqual(self.result['status'], 'stopped')

    def test_a_missing_expected_prism_link_stops_even_when_absent_from_both_images(self):
        link = rd.PRISM + '/libprism.so'
        (self.roots['new'] / link).unlink()
        with self.assertRaisesRegex(AssertionError, 'Prism bundle differs from the complete typed inventory'):
            self.run_main()
        self.assertEqual(self.result['status'], 'stopped')
        self.assertNotIn(link, self.result['unexplained'])

    def test_missing_public_link_stops_main_even_when_absent_from_both_images(self):
        public = 'usr/bin/java'
        (self.roots['new'] / public).unlink()
        self.assertFalse((self.roots['old'] / public).exists())
        with self.assertRaisesRegex(AssertionError, 'alternatives groups missing or different from the reviewed mapping: java'):
            self.run_main()
        self.assertEqual(self.result['status'], 'stopped')
        self.assertNotIn(public, self.result['unexplained'])

    def test_missing_whole_group_stops_main_without_any_changed_alternatives_path(self):
        for rel in (rd.ALTERNATIVES_ADMIN + 'java', rd.ALTERNATIVES + 'java', 'usr/bin/java'):
            (self.roots['new'] / rel).unlink()
        with self.assertRaisesRegex(AssertionError, 'alternatives groups missing or different from the reviewed mapping: java'):
            self.run_main()
        self.assertEqual(self.result['status'], 'stopped')
        self.assertEqual(self.result['unexplained'], [])

    def test_corrupted_schema_lookup_metadata_stops_the_result(self):
        for kind, corrupted in corrupt_schema_lookup((FIXTURES / 'after.compiled').read_bytes()).items():
            with self.subTest(kind=kind):
                (self.roots['new'] / rd.SCHEMAS).write_bytes(corrupted)
                with self.assertRaisesRegex(AssertionError, 'compiled schemas differ from deterministic rebuild'):
                    self.run_main()
                self.assertEqual(self.result['status'], 'stopped')
                self.assertFalse(self.result['schema_rebuild']['matches'])
                self.assertIn(rd.SCHEMAS, self.result['unexplained'])

    def test_the_image_sources_must_be_mains_at_the_merge_base(self):
        # Review 1, S2: built from a commit whose image sources differ from main's (here: release 27's source as
        # "main"), the diff stops and names each differing file, beside the paths main's history cannot explain.
        with patch.object(rd, 'main_merge_base', return_value=rd.PREVIOUS_SOURCE_28), \
                self.assertRaisesRegex(AssertionError, f'STOP: .*image sources differ from main at the merge base {rd.PREVIOUS_SOURCE_28}: '):
            self.run_main()
        differing = self.result['main']['differing']
        self.assertEqual(self.result['main']['merge_base'], rd.PREVIOUS_SOURCE_28)
        for path in ('os/build.sh', 'os/minecraft/desktop.lock.json', 'os/config/' + rd.RC_XML):
            self.assertIn(path, differing)
        self.assertIn(', '.join(differing), ' '.join(self.result['problems']))

    def test_rpm_verification_failure_is_fatal_even_when_every_path_is_explained(self):
        for verification in ((1, 'S.5....T.    /usr/lib/jvm/java-25/bin/java'), (2, 'rpm: unexpected failure'), (1, ''),
                             (0, 'unexpected output')):
            with self.subTest(verification=verification):
                self.verify = verification
                with self.assertRaisesRegex(AssertionError, 'rpm verification of the added packages failed'):
                    self.run_main()
                self.assertEqual(self.result['status'], 'stopped')
                self.assertEqual(self.result['rpm_verify']['exit_code'], verification[0])
                self.assertEqual(self.result['unexplained'], [])

    def test_a_package_file_other_than_its_rpm_record_stops(self):
        # The rule itself stops on a file whose bytes or mode are not its record's.
        for change in (dict(digest='0' * 64), dict(mode=str(stat.S_IFREG | 0o755)), dict(user='ares'), dict(flags='64')):
            with self.subTest(change=change):
                self.record_changes = {'/' + self.JAVA: change}
                with self.assertRaisesRegex(AssertionError, 'STOP: '):
                    self.run_main()
                self.assertEqual(self.result['unexplained'], [self.JAVA])

    def test_a_missing_expected_rpm_file_stops_even_when_absent_from_both_images(self):
        keytool = '/usr/lib/jvm/java-25/bin/keytool'
        # The package says keytool exists; neither image has it, so no changed path can expose it.
        with patch.dict(self.OWNED, headless=[*self.OWNED['headless'], keytool]):
            for verification in ((0, ''), (1, 'missing     ' + keytool)):
                with self.subTest(verification=verification):
                    self.verify = verification
                    with self.assertRaisesRegex(AssertionError, 'expected RPM paths missing or different.*keytool'):
                        self.run_main()
                    self.assertEqual(self.result['status'], 'stopped')
                    self.assertEqual(self.result['unexplained'], [])
            # Ghost files are allowed to be absent, even with an independently recorded path.
            self.verify = (0, '')
            self.record_changes[keytool] = dict(flags=str(rd.RPMFILE_GHOST))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.run_main()['status'], 'passed')

    def test_an_unchanged_rpm_file_must_still_match_its_record(self):
        (self.roots['old'] / self.JAVA).parent.mkdir(parents=True)
        (self.roots['old'] / self.JAVA).write_bytes(b'java')
        (self.roots['old'] / self.JAVA).chmod(0o644)
        self.record_changes['/' + self.JAVA] = dict(digest='0' * 64)
        with self.assertRaisesRegex(AssertionError, 'expected RPM paths missing or different.*bin/java'):
            self.run_main()
        self.assertEqual(self.result['status'], 'stopped')
        self.assertNotIn(self.JAVA, self.result['unexplained'])

    def test_each_stop_of_main(self):
        """Review 1, S4: each check main() makes beside the rules stops the diff, with its own words."""
        release = json.loads((ROOT / rd.PREVIOUS_28).read_text())
        other_base = self.work / '27-other-base.json'
        other_base.write_text(json.dumps(dict(release, base='ghcr.io/example/other@sha256:' + '0' * 64)))
        masked = self.roots['old'] / 'usr/share/aresos/policy/masked-system-units.txt'
        lock = self.roots['old'] / 'usr/share/aresos/manifest/packages.lock.json'
        unit = self.roots['new'] / 'var/lib/dnf/systemd/x.service'
        labels = lambda: self.configs['new']['config']['Labels']

        def write(path, data):
            def change():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            return change

        @contextlib.contextmanager
        def generated_unit():
            # The narrowed exceptions cannot match units. Exercise main's independent guard with a
            # stand-in future classifier that accidentally introduces such an exception.
            write(unit, b'[Unit]\n')()
            original = rd.Classifier28.generated_rule
            def generated(classifier, rel, before, after):
                return ('generated', 'stand-in generated unit') if '/systemd/' in rel else original(classifier, rel, before, after)
            with patch.object(rd.Classifier28, 'generated_rule', generated):
                yield
        cases = [
            ('the revision label is not this run', 'release 28 source labels differ from this run',
             lambda: labels().update({'org.opencontainers.image.revision': 'b' * 40})),
            ('the source label is another repository', 'release 28 source labels differ from this run',
             lambda: labels().update({'org.opencontainers.image.source': 'https://example.invalid/other'})),
            ('another label changed', 'unexplained label change: org.opencontainers.image.revision, x.label',
             lambda: labels().update({'x.label': 'y'})),
            ('the OCI runtime configuration changed', 'unrelated OCI runtime configuration changed: Cmd',
             lambda: self.configs['new']['config'].update(Cmd=['sh'])),
            ("release 28's base ancestry", 'release 28 base ancestry differs',
             lambda: self.configs['new']['rootfs'].update(diff_ids=['sha256:x', 'sha256:n'])),
            ("release 27's base ancestry", 'release 27 base ancestry differs',
             lambda: self.configs['old']['rootfs'].update(diff_ids=['sha256:x', 'sha256:o'])),
            ('a unit changed only as a generated file', 'a unit changed only as a generated file', generated_unit()),
            ('release 27 was built on another base', 'release 27 was built on another base',
             patch.dict(rd.RELEASES['28'], previous=str(other_base))),
            ("release 27's lock is not its source", 'release 27 lock differs from its source',
             write(lock, json.dumps(dict(packages=json.loads(lock.read_text())['packages'][1:])).encode())),
            ('a unit unmasked that no rule reviewed', 'unreviewed unit unmasked',
             write(masked, masked.read_bytes() + b'surprise.service\n')),
        ]
        configs, saved = copy.deepcopy(self.configs), {path: path.read_bytes() for path in (masked, lock)}
        made = not (self.roots['new'] / 'var').exists()
        # These three stop before the result is written: publish.sh then finds no result and refuses.
        early = ('release 27 was built on another base', "release 27's lock is not its source", 'a unit unmasked that no rule reviewed')
        for what, message, change in cases:
            with self.subTest(what):
                context = change if hasattr(change, '__enter__') else contextlib.nullcontext()
                if not hasattr(change, '__enter__'):
                    change()
                try:
                    with context, self.assertRaisesRegex(AssertionError, 'STOP: .*' + re.escape(message)):
                        self.run_main()
                    self.assertEqual(self.result and self.result['status'], None if what in early else 'stopped')
                finally:
                    self.configs.clear()
                    self.configs.update(copy.deepcopy(configs))
                    for path, data in saved.items():
                        path.write_bytes(data)
                    if made:
                        shutil.rmtree(self.roots['new'] / 'var', ignore_errors=True)
        # Every change was undone: the stand-in passes again.
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.run_main()['status'], 'passed')

if __name__ == '__main__':
    unittest.main()
