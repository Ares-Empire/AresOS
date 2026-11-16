"""Package 42: release 28's diff rules, its release job and the dry run that cannot publish."""
import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import stat
import struct
import subprocess
import sys
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
GITHUB = dict(base.UPDATE_GITHUB, GITHUB_REF_NAME=BRANCH)


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


class Release27SourceTest(unittest.TestCase):
    def test_the_previous_source_holds_release_27s_recorded_trees_and_is_on_main(self):
        release = json.loads((ROOT / rd.PREVIOUS_28).read_text())
        self.assertEqual(len(release['source_trees']), 10)
        for row in release['source_trees']:
            with self.subTest(path=row['path']):
                self.assertEqual(git('rev-parse', rd.PREVIOUS_SOURCE_28 + ':' + row['path']), row['tree'])
        subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', rd.PREVIOUS_SOURCE_28, 'HEAD'], check=True)
        self.assertEqual(rd.RELEASES['28']['previous_release'], '27')
        self.assertEqual(json.loads((ROOT / rd.PREVIOUS_28).read_text())['reference'],
                         json.loads((ROOT / 'os/manifest/release.json').read_text())['reference'])


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
        with self.assertRaises(ValueError):
            rd.gvdb_entries(b'not a compiled file' * 4)
        with self.assertRaises(ValueError):
            rd.gvariant('(si)', b'ab\0\0\0')


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


class AlternativesAdminTest(unittest.TestCase):
    def test_links_and_targets_are_read_with_and_without_a_family(self):
        plain = b'auto\n/usr/bin/ld\n\n/usr/bin/ld.bfd\n50\n'
        self.assertEqual(rd.alternatives_admin(plain), ({'/usr/bin/ld': None}, ['/usr/bin/ld.bfd']))
        java = (b'auto\n/usr/bin/java\nkeytool\n/usr/bin/keytool\njre\n/usr/lib/jvm/jre\n\n'
                b'@java-25-openjdk.x86_64@/usr/lib/jvm/java-25/bin/java\n25000500\n/usr/lib/jvm/java-25/bin/keytool\n\n')
        links, targets = rd.alternatives_admin(java)
        self.assertEqual(links, {'/usr/bin/java': None, '/usr/bin/keytool': 'keytool', '/usr/lib/jvm/jre': 'jre'})
        self.assertEqual(targets, ['/usr/lib/jvm/java-25/bin/java', '/usr/lib/jvm/java-25/bin/keytool'])
        for bad in (b'maybe\n/usr/bin/ld\n\n/usr/bin/ld.bfd\n50\n', b'auto\nld\n\n/usr/bin/ld.bfd\n50\n',
                    b'auto\n/usr/bin/ld\n\n', b'auto\n/usr/bin/ld\n\n/usr/bin/ld.bfd\nfifty\n'):
            with self.subTest(bad=bad):
                self.assertIsNone(rd.alternatives_admin(bad))


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
    JAVA_MAN = 'usr/lib/jvm/java-25-openjdk/man/man1/java.1'

    @staticmethod
    def audit(*added, **changes):
        """An updater audit (os/tests/audit.py's output) of two units; user.slice gains `added` and `changes`."""
        unit = lambda name, sources: dict(scope='system', name=name, state='static', suspicious=False, commands=[],
                                          active_state=None, load_state=None, sub_state=None, sources=sources)
        units = [unit('ModemManager.service', ['/usr/lib/systemd/system/ModemManager.service']),
                 dict(unit('user.slice', ['/usr/lib/systemd/system/user.slice', *added]), **changes)]
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
                                                b'@java-25@' + self.JAVA.encode() + b'\n25\n' + self.KEYTOOL.encode() + b'\n'),
               rd.ALTERNATIVES + 'java': ('link', self.JAVA), rd.ALTERNATIVES + 'keytool': ('link', self.KEYTOOL),
               'usr/bin/java': ('link', '/etc/alternatives/java'), 'usr/bin/keytool': ('link', '/etc/alternatives/keytool'),
               self.JAVA[1:]: b'java'}
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
        self.attributes = {}
        real_entry = rd.entry

        def as_image(root, rel):
            value = real_entry(root, rel)
            if value is not None:
                value.update(uid=0, gid=0, xattrs=self.attributes.get(rel, {}))
            return value
        self.enterContext(patch.object(rd, 'entry', side_effect=as_image))
        inventory = {rel: dict(value, uid=0, gid=0, xattrs={}) for rel, value in image_diff.inventory(self.new).items()}
        owned = dict(old=set(), new={self.JAVA, self.KEYTOOL, '/usr/lib/jvm/java-25/lib/libjvm.so', '/' + self.JAVA_MAN})
        packages = dict(old=[], new=[])
        self.classifier = rd.Classifier28(self.roots, packages, owned,
                                          dict(executables=rd.CHMOD_0755_28, inventory=inventory))
        self.classifier.pins = {rd.MINECRAFT + '/libraries/x-1.jar': (hashlib.sha256(b'x').hexdigest(), 1, 'pinned x')}

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
            rd.JAVA_MAN_FOLDERS[0]: 'package', rd.JAVA_MAN_FOLDERS[1]: 'package', self.JAVA_MAN: 'package'}
        for rel, rule in expected.items():
            with self.subTest(rel=rel):
                found = self.explain(rel) if rel != 'var/log/dnf5.log' else self.classifier.generated_rule(rel, {}, {})
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
        self.assertEqual(extra['alternatives'], {'java': [self.JAVA, self.KEYTOOL]})
        self.assertEqual(problems, [f'the Ares-Crown theme in the image (None) is not the one image-checks.sh pins ({PACKAGE31_CROWN})'])
        # Release 27's regenerated font caches are no blanket rule any more.
        self.assertIsNone(self.classifier.generated_rule('usr/lib/fontconfig/cache/x', {}, {}))

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
                            (inputs(**{'inputs.check_build': 'resolve'}), 'resolve'),
                            (inputs(**{'inputs.checks_only': True}), 'checks')):
            with self.subTest(kind=kind):
                self.assertEqual(run_name(world), ledger['titles'][kind])
        expression = re.fullmatch(r'\$\{\{(.*)\}\}', WORKFLOW['env']['REHEARSAL_PACKAGE'].strip()).group(1)
        self.assertEqual(base.workflow_expression(expression, inputs()), '42')
        for job, mode in (('release-28', 'publish-28'), ('release-28-dry-run', 'dry-run-28')):
            modes = {step['env']['REHEARSAL_MODE'] for step in WORKFLOW['jobs'][job]['steps'] if 'REHEARSAL_MODE' in step.get('env', {})}
            self.assertEqual(modes, {mode})

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

    def test_the_ledger_counts_every_dispatch_and_allows_one_publish(self):
        ledger = guard.PACKAGES['42']
        self.assertEqual(guard.BRANCH, BRANCH)
        self.assertIn('42', guard.TITLED_PACKAGES)
        self.assertEqual(set(ledger['titles']), set(ledger['dispatch_caps']))
        self.assertEqual(set(ledger['job_bounds']), set(ledger['dispatch_caps']))
        self.assertEqual(ledger['publish_cap'], 1)
        self.assertEqual(ledger['dispatch_caps']['publish-28'], 1)
        self.assertEqual(ledger['job_bounds']['publish-28'], int(WORKFLOW['jobs']['release-28']['timeout-minutes']))
        self.assertEqual(ledger['job_bounds']['dry-run-28'], int(WORKFLOW['jobs']['release-28-dry-run']['timeout-minutes']))
        self.assertEqual(ledger['job_bounds']['resolve'], int(WORKFLOW['jobs']['check-build']['timeout-minutes']))
        titles = ledger['titles']
        runs, api = self.history([titles['resolve'], titles['dry-run-28'], titles['dry-run-28']])
        with patch.object(guard, 'api', side_effect=api):
            result = guard.budget(0)
            self.assertEqual(result['dispatch_counts'], {'dry-run-28': 2, 'publish-28': 0, 'resolve': 1, 'checks': 0})
            self.assertEqual(result['consumed_minutes'], 180)
            runs.append(dict(runs[-1], id=99, display_title=titles['dry-run-28']))
            with self.assertRaisesRegex(AssertionError, 'dry-run-28 dispatch allowance exhausted'):
                guard.budget(0)
            runs[-1]['display_title'] = 'Two-disk rehearsal (release-28)'
            with self.assertRaises(ValueError):  # a title the ledger does not know (step 3 adds the rehearsal)
                guard.budget(0)

    def run_main(self, mode, kind):
        titles = guard.PACKAGES['42']['titles']
        runs, api = self.history([titles['dry-run-28']])
        current = dict(runs[0], id=50, status='in_progress', conclusion=None, display_title=titles[kind],
                       head_branch=BRANCH, created_at='2026-11-16T05:00:00Z')
        runs.append(current)
        environment = dict(REHEARSAL_PACKAGE='42', REHEARSAL_MODE=kind, GITHUB_REF_NAME=BRANCH, GITHUB_RUN_ID='50',
                           GITHUB_SHA='a' * 40, GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS')
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory, contextlib.chdir(directory), \
                patch.object(guard, 'api', side_effect=api), patch.dict(os.environ, environment, clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', mode, '180' if mode == 'ci' else '0']), \
                contextlib.redirect_stdout(io.StringIO()):
            guard.main()
            return sorted(path.name for path in pathlib.Path('evidence').iterdir())

    def test_only_the_publishing_kind_passes_the_publish_gate(self):
        self.assertIn('publish-authorization.json', self.run_main('publish-ci', 'publish-28'))
        with self.assertRaises(AssertionError):
            self.run_main('publish-ci', 'dry-run-28')
        self.assertIn('42-dispatch-authorization.json', self.run_main('ci', 'dry-run-28'))
        self.assertEqual(guard.PUBLISH_KINDS, ('release-13', 'release-27', 'publish-28'))

    @unittest.skipIf(os.name == 'nt' or shutil.which('bash') is None, 'needs a Linux bash')
    def test_publish_sh_accepts_only_the_release_branches_before_its_guard(self):
        text = (ROOT / 'os/ci/publish.sh').read_text()
        self.assertIn('    pkg/42-release-28) release=28 ;;\n', text)
        self.assertLess(text.index('esac'), text.index('rehearsal_guard.py publish-ci'))
        environment = dict(os.environ, GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS',
                           GITHUB_REF_NAME='pkg/42-release-28-other', PATH=os.environ.get('PATH', ''))
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
        for mode in ('publish-28', 'dry-run-28'):
            with patch.dict(os.environ, dict(self.ENVIRONMENT, REHEARSAL_MODE=mode), clear=True):
                registry_auth.require_dispatch()
        for changes in (dict(REHEARSAL_MODE='release-27'), dict(REHEARSAL_MODE='update'), dict(REHEARSAL_MODE='release-28'),
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
               rd.RC_XML: show('os/config/' + rd.RC_XML), 'usr/share/aresos/apps/terminal.json': show('os/config/usr/share/aresos/apps/terminal.json'),
               updaters: Classifier28Test.audit(), tag: b'tag'}
        new = {**policy, 'etc/hostname': b'aresos\n', 'usr/share/aresos/manifest/packages.lock.json': (ROOT / 'os/packages.lock.json').read_bytes(),
               rd.RC_XML: (ROOT / 'os/config' / rd.RC_XML).read_bytes(),
               'usr/share/aresos/apps/terminal.json': (ROOT / 'os/config/usr/share/aresos/apps/terminal.json').read_bytes(),
               self.JAVA: b'java', Classifier28Test.JAVA_MAN: b'.TH java 1\n', tag: b'tag',
               updaters: Classifier28Test.audit('/' + dropin), dropin: (ROOT / 'os/config' / dropin).read_bytes(),
               # 23b's font folder with its real caches in both formats (fixtures/release28-fontcache).
               **{rd.FONT_CACHES + path.name: path.read_bytes() for path in FontCacheTest.FIXTURES.glob('*.cache-9')},
               **{f'usr/share/fonts/aresos/{path.name}': path.read_bytes() for path in (ROOT / 'os/config/usr/share/fonts/aresos').iterdir()}}
        for path in (ROOT / 'os/config' / rd.CROWN).iterdir():
            new[f'{rd.CROWN}/{path.name}'] = path.read_bytes()
        self.roots = {}
        for name, files in (('old', old), ('new', new), ('base', {})):
            root = self.work / name
            root.mkdir()
            base.ClassifierTest.tree(None, root, files)
            for path in root.rglob('*'):
                if path.is_dir():
                    path.chmod(0o755)
            self.roots[name] = root
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
        self.enterContext(patch.dict(os.environ, GITHUB_SHA='a' * 40))

    def command(self, tool, *args):
        if args[0] in ('create', 'mount') and tool == 'podman':
            return str(self.roots[self.images[args[-1]]]) if args[0] == 'mount' else args[-1]
        if args[0] in ('unmount', 'rm'):
            return ''
        if args[0] == 'run':
            image = self.images[args[args.index('--entrypoint=/usr/bin/rpm') + 1]]
            if '-qa' in args:
                return '\n'.join(f'{nevra}\t{base.name_of(nevra)}' for nevra in self.rpms[image])
            # rpm -ql names a package's folders too (javapackages-filesystem owns /usr/lib/jvm).
            # Like the real headless package, it names its man pages but not their folders.
            owned = {'headless': ['/usr/lib/jvm/java-25', '/usr/lib/jvm/java-25/bin', '/' + self.JAVA,
                                  '/usr/lib/jvm/java-25-openjdk', '/' + Classifier28Test.JAVA_MAN],
                     'javapackages-filesystem': ['/usr/lib/jvm']}
            return '\n'.join(path for nevra in args[args.index('-ql') + 1:]
                             for key, paths in owned.items() if key in nevra for path in paths)
        if tool == 'skopeo':
            return json.dumps(self.configs[self.images[args[-1].removeprefix('containers-storage:')]])
        raise AssertionError(f'unexpected command {tool} {args}')

    def run_main(self):
        evidence = self.work / 'evidence'
        try:
            rd.main({name: sys.executable for name in build_tools.NAMES}, release='28', evidence=evidence)
        finally:
            result = json.loads((evidence / 'result.json').read_text()) if (evidence / 'result.json').exists() else None
            shutil.rmtree(evidence, ignore_errors=True)
        return result

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
        self.assertEqual(result['updaters'], [dict(scope='system', unit='user.slice', added=['/' + Classifier28Test.DROPIN],
                                                   **{'from': ['23 (#36)']})])

    def test_an_unexplained_path_or_another_theme_stops(self):
        (self.roots['new'] / 'etc/surprise').write_bytes(b'?')
        (self.roots['new'] / 'etc/surprise').chmod(0o644)
        with self.assertRaisesRegex(AssertionError, 'STOP: 1 unexplained image differences'):
            self.run_main()
        (self.roots['new'] / 'etc/surprise').unlink()
        (self.roots['new'] / rd.CROWN / 'themerc').write_bytes(b'')
        with self.assertRaisesRegex(AssertionError, 'Ares-Crown theme in the image'):
            self.run_main()


if __name__ == '__main__':
    unittest.main()
