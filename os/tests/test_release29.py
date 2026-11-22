"""Package 331 image diff. Mounts and RPM queries use fixtures, ELF checks use synthetic binaries."""
import ast
import gzip
import hashlib
import json
import os
import pathlib
import re
import shlex
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import audit
import test_labwc_stage as r311
import test_release28 as r28
from test_release27 import lock_nevras, name_of, released

import build_tools
import image_diff
import release_diff as rd

ROOT = r28.ROOT
R28 = json.loads((ROOT / rd.PREVIOUS_29).read_text())
MAIN = 'a9863055b2987127cd1cd684182deed9ece24ce0'
# Exercise the reviewed step 1 and 2 cut until the late-package profile is built.
PROFILE_HEAD = '028cc3158404035c1155da33048155eb7654b6cc'
REAL_GIT = rd.git
FONT_64 = rd.FONT_CACHES + '50471fd4bd417ff5c0731b6a17aa3708-le64.cache-9'
FONT_32 = FONT_64.replace('le64', 'le32d4')
GTK = 'usr/lib64/libgtk4-layer-shell.so.0.0.0'
TYPELIB = 'usr/lib64/girepository-1.0/Gtk4LayerShell-1.0.typelib'
GHOST = 'usr/lib64/gtk-layer-ghost'
BLANK = b''
LABWC = 'usr/bin/labwc'
LABNAG = 'usr/bin/labnag'
FEDORA = 'labwc-0.9.6-1.fc44.x86_64'
REBUILT = 'labwc-0.9.6-1.fc44.aresos1.x86_64'
REPORT_311 = rd.git_bytes('67e1e60c746aea6159daeab8a3256fbf582dd5ff', 'reviews/311-labwc-pointer-lock/PROGRESS.md').decode()
FIXED_311 = {path[1:] for path in REPORT_311.split('## Final NEVRA and file list')[1].splitlines()
             if path.startswith('/usr/') and not path.startswith('/usr/lib/.build-id/')}
FEDORA_IDS = {LABWC: '6e61cec6435d39a5126a1ec7b1bd109152327f8b',
              LABNAG: 'ecbdf3ff0423bb879b79912f84b3e5f06f8786fd'}
REBUILT_IDS = {LABWC: 'a1' * 20, LABNAG: 'b2' * 20}


def lock29():
    return rd.git_bytes(MAIN, 'os/packages.lock.json')


def profile_git(*args, **kwargs):
    # Pin Git's committed lookups for the fixture, while retaining real checkout
    # dirtiness checks and allowing individual tests to inject bad Git results.
    pinned = args[0] in ('ls-tree', 'rev-parse') or args[:4] == ('diff', '-z', '--name-only', '--no-renames')
    if pinned:
        args = tuple(PROFILE_HEAD if word == 'HEAD' else word for word in args)
    return REAL_GIT(*args, **kwargs)


def package_inputs():
    chrome = json.loads(released('28', 'os/google-chrome.lock.json'))['nevra']
    old_lock = lock_nevras(released('28', 'os/packages.lock.json')) + [chrome]
    new_lock = lock_nevras(lock29()) + [chrome]
    old = {nevra: name_of(nevra) for nevra in old_lock}
    new = {nevra: name_of(nevra) for nevra in new_lock if nevra != rd.LABWC_FEDORA_29}
    new[REBUILT] = 'labwc'
    return old, new, old_lock, new_lock


class CurrentMainTest(unittest.TestCase):
    def test_source_stops_keep_the_historical_source_lists(self):
        self.assertEqual(rd.RELEASES['29']['previous_source'], R28['source_commit'])
        self.assertEqual(rd.IMAGE_SOURCES_29, rd.IMAGE_SOURCES + ('os/labwc',))
        self.assertEqual(set(rd.BRANCH_SOURCE_CHANGES_29), {'os/minecraft/desktop.lock.json'})
        self.assertIn('os/build.sh', rd.BRANCH_SOURCE_CHANGES)
        self.assertEqual(rd.source_changes(MAIN, PROFILE_HEAD, sources=rd.IMAGE_SOURCES_29,
                                           exceptions=rd.BRANCH_SOURCE_CHANGES_29), ({}, []))
        with patch.dict(os.environ, GITHUB_SHA=PROFILE_HEAD), patch.object(rd, 'ignored_build_files29', return_value=[]), \
                patch.object(rd, 'git', side_effect=profile_git):
            self.assertEqual(rd.verify_source29(R28, MAIN)[1], [])
            damaged = dict(R28, source_trees=R28['source_trees'][1:])
            self.assertIn('does not match', rd.verify_source29(damaged, MAIN)[1][0])

    def test_build_source_list_covers_actual_inputs(self):
        container = rd.git_bytes(MAIN, 'os/Containerfile').decode()
        build = rd.git_bytes(MAIN, 'os/build.sh').decode()
        # Explicit context COPYs, local script inputs and the staged Git tar paths.
        copies = set(re.findall(r'^COPY (?!-)([\w./-]+) ', container, re.M)) - {'.'}
        self.assertEqual(copies, {'build.sh', 'labwc/', 'packages.lock.json', 'Containerfile'})
        paths = {'os/' + path.rstrip('/') for path in copies}
        for content in (container, build):
            paths.update('os/' + path for path in re.findall(r'/tmp/aresos/([\w.-]+(?:/audit\.py)?)', content))
        paths -= {'os/ci', 'os/control'}  # explicitly refused, and copied from source respectively
        paths.update(('os/.containerignore', 'os/manifest/base.json'))
        paths.update(('control', 'mod'))
        self.assertIn('/tmp/aresos-mod/build.sh source', container)
        tar, = [shlex.split(line) for line in build.splitlines() if line.strip().startswith('tar -xzf')]
        self.assertEqual(tar[-2:], ['*/mod/*', 'AresOS-$revision/control'])
        self.assertEqual(paths, set(rd.IMAGE_SOURCES_29))

    def test_git_diff_uses_modes_and_labwc_and_disallows_the_old_build_exception(self):
        path = 'os/minecraft/desktop.lock.json'
        cases = {
            path: ('100755 blob newid', [path]),
            'os/build.sh': ('100644 blob newid', ['os/build.sh']),
            'os/labwc/stage.py': ('100644 blob newid', ['os/labwc/stage.py']),
            rd.LABWC_LOCK_29: ('120000 blob newid', [rd.LABWC_LOCK_29]),
            rd.LABWC_ELF_29: ('100644 blob newid', [rd.LABWC_ELF_29]),
        }
        for changed, (new_entry, unexpected) in cases.items():
            def git(*args, **kwargs):
                if args[0] == 'diff':
                    self.assertIn('os/labwc', args)
                    return changed + '\0'
                self.assertEqual(args[0], 'ls-tree')
                return '100644 blob oldid' if args[1] == 'main' else new_entry
            with self.subTest(path=changed), patch.object(rd, 'git', side_effect=git):
                self.assertEqual(rd.source_changes('main', 'merge', sources=rd.IMAGE_SOURCES_29,
                                                   exceptions=rd.BRANCH_SOURCE_CHANGES_29), ({}, unexpected))

    def test_all_current_main_config_changes_and_modes_have_reasons(self):
        before, after = rd.config_tree(R28['source_commit']), rd.config_tree(MAIN)
        changed = {rel for rel in before.keys() | after.keys() if before.get(rel) != after.get(rel)}
        self.assertEqual(changed, set(rd.CONFIG_REASONS_29))
        self.assertFalse(set(before) - set(after))
        for name in ('aresos-level', 'aresos-indicator', 'aresos-settings', 'aresos-laptop-home'):
            path = 'usr/libexec/' + name
            self.assertEqual(after[path][0], '100755')
            self.assertNotIn(path, rd.CHMOD_0755_29)
        configure = rd.git_bytes(MAIN, 'os/build.sh').decode().replace('\\\n', ' ')
        line, = [line for line in configure.splitlines() if line.startswith('chmod 0755 /usr/bin/aresos-session ')]
        self.assertEqual({part[1:] for part in line.split()[2:]}, rd.CHMOD_0755_29)

    def test_rc_xml_rows_and_guardian_audit_come_from_the_reviewed_sources(self):
        path = 'os/config/' + rd.RC_XML
        old = rd.git_bytes(R28['source_commit'], path)
        self.assertEqual(rd.config_tree(R28['source_commit'])[rd.RC_XML][2],
                         r28.git('rev-parse', f"{R28['source_commit']}:{path}").strip())
        rows = rd.rc_xml_changes(old, rd.git_bytes(MAIN, path))
        expected = {'XF86MonBrightnessUp': 'brightness-up', 'XF86MonBrightnessDown': 'brightness-down',
                    'XF86AudioRaiseVolume': 'volume-up', 'XF86AudioLowerVolume': 'volume-down',
                    'XF86AudioMute': 'mute', 'XF86AudioMicMute': 'mic-mute'}
        self.assertEqual(set(re.findall(r'key="(\w+)"', '\n'.join(rows['removed']))), set(expected))
        self.assertEqual(len(rows['removed']), 6)
        self.assertEqual(len(rows['added']), 7)
        for key, action in expected.items():
            row, = [row for row in rows['added'] if f'key="{key}"' in row]
            self.assertIn(f'command="/usr/libexec/aresos-level {action}"', row)
        black, = [row for row in rows['added'] if 'aresos.black' in row]
        self.assertIn('serverDecoration="no"', black)
        self.assertIn('ToggleAlwaysOnTop', black)
        unit = rd.git_bytes(MAIN, 'os/config/' + rd.GUARDIAN_UNIT).decode()
        self.assertEqual(rd.GUARDIAN_AUDIT['commands'], [line for line in unit.splitlines() if line.startswith('Exec')])
        self.assertFalse(audit.PATTERN.search(unit))
        self.assertIn('WantedBy=graphical.target', unit)

    def test_control_build_python_and_nonprivileged_help_have_the_reviewed_flags(self):
        build = rd.git_bytes(MAIN, 'os/build.sh').decode()
        block = build.split('if [[ $1 == control ||', 1)[1].split('if [[ $1 == packages ]]', 1)[0]
        python = [line for line in block.splitlines() if 'python3' in line and not line.lstrip().startswith('#')]
        self.assertEqual(len(python), 5)
        self.assertTrue(all(' -B ' in line for line in python))
        child = next(node for node in ast.walk(ast.parse(block.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]))
                     if isinstance(node, ast.Call) and ast.unparse(node.func) == 'subprocess.run')
        self.assertEqual(ast.literal_eval(ast.List(elts=child.args[0].elts[1:3], ctx=ast.Load())), ['-I', '-B'])
        self.assertIn('setpriv --reuid=nobody --regid=nobody --clear-groups -- /usr/bin/aresos --help', block)
        self.assertIn('--invalidation-mode checked-hash "$vendor"', block)

    def test_installed_rpm_delta_is_exact(self):
        old, new, old_lock, new_lock = package_inputs()
        labwc = json.loads(rd.git_bytes(MAIN, 'os/labwc/labwc.lock.json'))['result']
        rows, added, removed = rd.package_diff29(old, new, old_lock, new_lock, labwc)
        self.assertEqual({row['reason'] for row in rows}, set(rd.PACKAGE_REASONS_29.values()))
        self.assertEqual(added, [rd.GTK_LAYER_29, REBUILT])
        self.assertEqual(removed, [FEDORA])
        with self.assertRaisesRegex(AssertionError, 'exactly Fedora labwc'):
            rd.package_diff29(old, dict(new, **{rd.LABWC_FEDORA_29: 'labwc'}), old_lock, new_lock, labwc)
        for replacement, name in ((REBUILT.replace('x86_64', 'aarch64'), 'labwc'), (REBUILT, 'gtk4-layer-shell')):
            candidate = {nevra: rpm for nevra, rpm in new.items() if nevra != REBUILT} | {replacement: name}
            with self.subTest(replacement=replacement, name=name), self.assertRaisesRegex(
                    AssertionError, 'removed package without its locked replacement'):
                rd.package_diff29(old, candidate, old_lock, new_lock, dict(labwc, nevra=replacement))
        with self.assertRaisesRegex(AssertionError, 'added packages differ from the lock change'):
            rd.package_diff29(old, new, old_lock, new_lock, dict(labwc, nevra=REBUILT.replace('aresos1', 'aresos2')))
        with self.assertRaisesRegex(AssertionError, 'unexpected R29 download lock delta'):
            rd.package_diff29(old, new, old_lock, new_lock + ['unreviewed-1-1.x86_64'], labwc)
        with self.assertRaisesRegex(AssertionError, 'unexpected R29 download lock delta'):
            rd.package_diff29(old, new, old_lock, new_lock + [rd.GTK_LAYER_29], labwc)

    def test_reviewed_labwc_inputs(self):
        self.assertEqual(rd.LABWC_FIXED_PATHS_29, FIXED_311)
        self.assertEqual(len(FIXED_311), 60)
        lock = json.loads(rd.git_bytes(MAIN, rd.LABWC_LOCK_29))['result']
        self.assertEqual((lock['replaces'], lock['nevra']), (FEDORA, REBUILT))
        for kind in ('normalized_sha256', 'loaded_sha256'):
            self.assertEqual(set(lock[kind]), {'/' + LABWC, '/' + LABNAG})
            for value in lock[kind].values():
                self.assertIn(value, REPORT_311)


class ImageDiffTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.work = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory(dir=ROOT)))
        self.roots = {name: self.work / name for name in ('old', 'new', 'base')}
        self.rpms = dict(zip(('old', 'new'), package_inputs()[:2]))
        self.mounts = {R28['reference']: 'old', rd.NEW: 'new', R28['base']: 'base'}
        self.versions = dict(old=R28['source_commit'], new=PROFILE_HEAD)
        mask = {'usr/share/aresos/policy/' + name: rd.git_bytes(R28['source_commit'], 'os/policy/' + name)
                for name in ('masked-system-units.txt', 'masked-user-units.txt')}
        self.jar = {}
        java = json.loads(rd.git_bytes(R28['source_commit'], rd.ALTERNATIVES_MANIFEST_28))['groups']
        for side, version in self.versions.items():
            self.roots[side].mkdir()
            for path, raw in mask.items():
                self.write(side, path, raw)
            self.write(side, rd.MANIFEST + 'packages.txt', '\n'.join(sorted(self.rpms[side])) + '\n')
            raw = released('28', 'os/packages.lock.json') if side == 'old' else lock29()
            self.write(side, rd.MANIFEST + 'packages.lock.json', json.dumps(json.loads(raw), indent=2) + '\n')
            raw = rd.git_bytes(version, 'os/minecraft/desktop.lock.json')
            self.write(side, rd.DESKTOP_LOCK, raw)
            self.jar[side] = next(mod['sha256'] for mod in json.loads(raw)['mods'] if mod['file'] == 'aresos.jar')
            self.write(side, rd.MOD_JAR, b'jar fixture')
            self.write(side, rd.MOD_RECORD, json.dumps(dict(sha256=self.jar[side], source_revision=version,
                                                           pinned_sha256=self.jar[side]), indent=2) + '\n')
            tree = rd.config_tree(version)
            paths = rd.CONFIG_REASONS_29.keys() | {rel for rel in tree if rel.startswith(rd.CROWN + '/')}
            for rel in paths & tree.keys():
                mode = 0o755 if tree[rel][0] == '100755' or rel in rd.CHMOD_0755_29 else 0o644
                self.write(side, rel, rd.git_bytes(version, 'os/config/' + rel), mode)
            self.write(side, 'usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf',
                       rd.git_bytes(R28['source_commit'], 'os/config/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf'))
            for rel in FONT_32, FONT_64:
                raw = rd.git_bytes(R28['source_commit'], str((r28.FontCacheTest.FIXTURES / pathlib.Path(rel).name).relative_to(ROOT)))
                self.write(side, rel, raw if side == 'old' else raw[:-1] + bytes([raw[-1] ^ 1]))
            self.write(side, rd.SCHEMAS, rd.git_bytes(R28['source_commit'], 'os/tests/fixtures/release28-schemas/after.compiled'))
            self.write(side, rd.PRISM + '/bin/prismlauncher', b'prism', 0o755)
            self.link(side, (rd.PRISM + '/launcher', 'bin/prismlauncher'))
            self.write(side, rd.PRISM_FILES, f"{hashlib.sha256(b'prism').hexdigest()}  /{rd.PRISM}/bin/prismlauncher\n")
            for link in (rd.CONSOLE_KEYMAP_LINK, rd.DESKTOP_COMMAND, rd.PRISM_COMMAND):
                self.link(side, link)
            self.install_alternatives(side, java)
            r28.install_control_fixture(self.roots[side])
            record = self.roots[side] / rd.CONTROL_RECORD
            record.write_text(record.read_text().replace('a' * 40, version))
            for name, raw in {
                'passwd': 'aresos-tools:x:250:250:AresOS tool service:/var/lib/aresos-tools:/usr/sbin/nologin\n',
                'group': 'aresos-tools:x:250:\n', 'gshadow': 'aresos-tools:!::\n',
                'shadow': f'aresos-tools:!*:{20111 if side == "old" else 20112}::::::\n',
            }.items():
                self.write(side, 'etc/' + name, raw, 0o600 if name == 'shadow' else 0o644)
            self.write(side, rd.CONSOLE_KEYMAP_UNIT, rd.git_bytes(version, 'os/config/' + rd.CONSOLE_KEYMAP_UNIT))
            self.write(side, rd.RPM_DATABASE, side)
            (self.roots[side] / pathlib.PurePosixPath(TYPELIB).parent).mkdir(parents=True)
        self.link('new', rd.GUARDIAN_LINK)
        for side in self.versions:
            self.write_audit(side)
        self.labwc_lock = json.loads(rd.git_bytes(MAIN, rd.LABWC_LOCK_29))
        self.labwc_records, self.labwc_lists = {}, {}
        for side, ids in (('old', FEDORA_IDS), ('new', REBUILT_IDS)):
            self.install_labwc(side, ids)
        self.write('new', rd.LABWC_RECORD, self.labwc_lock_bytes())
        self.write('new', GTK, b'library')
        self.write('new', TYPELIB, b'typelib')
        self.verify = ''
        self.verify_labwc = {'old': '', 'new': ''}
        self.rebuilt = True
        self.xattrs = {}
        old_inventory, old_entry = image_diff.inventory, rd.entry
        def typed(side, rel, value):
            if value is None:
                return None
            row = dict(value, uid=0, gid=0, xattrs=self.xattrs.get((side, rel), {}))
            if rel == rd.MOD_JAR:
                row['sha256'] = self.jar[side]
            return row
        self.enterContext(patch.object(image_diff, 'inventory', side_effect=lambda root: {
            rel: typed(root.name, rel, val) for rel, val in old_inventory(root).items()}))
        self.enterContext(patch.object(rd, 'entry', side_effect=lambda root, rel: typed(root.name, rel, old_entry(root, rel))))
        inventory = image_diff.inventory(self.roots['new'])
        self.enterContext(patch.object(rd, 'prism_inventory', return_value={
            rel: row for rel, row in inventory.items() if rel == rd.PRISM or rel.startswith(rd.PRISM + '/')}))
        prism_pin = json.loads(rd.git_bytes(R28['source_commit'], 'os/minecraft/desktop.lock.json'))['prism']['sha256']
        self.enterContext(patch.dict(rd.PRISM_FILE_LISTS, {prism_pin: inventory[rd.PRISM_FILES]['sha256']}))
        self.enterContext(patch.dict(os.environ, GITHUB_SHA=PROFILE_HEAD))
        self.enterContext(patch.object(rd, 'main_merge_base', return_value=MAIN))
        self.enterContext(patch.object(rd, 'git', side_effect=profile_git))
        real_git_bytes = rd.git_bytes
        self.enterContext(patch.object(rd, 'git_bytes', side_effect=lambda version, rel:
                                       self.labwc_lock_bytes() if (version, rel) == (PROFILE_HEAD, rd.LABWC_LOCK_29)
                                       else real_git_bytes(version, rel)))
        self.scan_ignored = rd.ignored_build_files29
        self.enterContext(patch.object(rd, 'ignored_build_files29', return_value=[]))
        self.commands = self.enterContext(patch.object(image_diff, 'command', side_effect=self.command))

    def labwc_lock_bytes(self):
        return (json.dumps(self.labwc_lock, indent=2) + '\n').encode()

    def install_labwc(self, side, ids):
        folders = {'usr/share/doc/labwc', 'usr/share/licenses/labwc', 'usr/lib/.build-id'}
        for rel in FIXED_311 - folders - ids.keys():
            self.write(side, rel, f'unchanged: {rel}\n', 0o755 if rel.startswith('usr/bin/') else 0o644)
        for rel in folders:
            path = self.roots[side] / rel
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o755)
        paths = set(FIXED_311)
        for rel, build_id in ids.items():
            text = b'\x90' if side == 'old' else b'\xcc'
            raw = r311.elf_file(_note_gnu_build_id=struct.pack('<III', 4, 20, 3) + b'GNU\0' + bytes.fromhex(build_id),
                                _text=text * 31 + (b'\x91' if rel == LABWC else b'\x92') + b'\xc3')
            self.write(side, rel, raw, 0o755)
            folder = 'usr/lib/.build-id/' + build_id[:2]
            link = folder + '/' + build_id[2:]
            self.link(side, (link, '../../../../' + rel))
            (self.roots[side] / folder).chmod(0o755)
            paths.update((folder, link))
            if side == 'new':
                with patch.object(tempfile, 'tempdir', str(self.work)):
                    self.labwc_lock['result']['normalized_sha256']['/' + rel] = r311.normalized(raw)
                    self.labwc_lock['result']['loaded_sha256']['/' + rel] = r311.loaded(raw)
        self.labwc_lists[side] = sorted(paths)
        self.labwc_records[side] = {path: self.rpm_record(side, path) for path in paths}

    def rpm_record(self, side, rel):
        path = self.roots[side] / rel
        mode = path.lstat().st_mode
        raw = path.read_bytes() if stat.S_ISREG(mode) else BLANK
        return ['/' + rel, 'root', 'root', '0', str(len(raw)), '8', hashlib.sha256(raw).hexdigest(),
                os.readlink(path) if stat.S_ISLNK(mode) else '', '', str(mode)]

    def write_audit(self, side):
        root = self.roots[side]
        output = root / rd.UPDATERS
        inventory, read_text = audit.inventory, pathlib.Path.read_text

        def read_fixture(path, *args, **kwargs):
            if path == pathlib.Path('/usr/share/aresos/policy/updater-allowlist.json'):
                return '{}'
            return read_text(path, *args, **kwargs)

        def unit_files(args, *, text):
            self.assertIn(f'--root={root}', args)
            self.assertEqual(args[-1], 'list-unit-files')
            if '--global' in args:
                return ''
            return ''.join(f'{path.name} enabled\n' for path in (root / 'usr/lib/systemd/system').glob('*.service'))

        with patch.object(sys, 'argv', ['audit.py', '--output', str(output)]), \
                patch.object(audit, 'inventory', side_effect=lambda *, live: inventory(root, live=live)), \
                patch.object(audit.subprocess, 'check_output', side_effect=unit_files), \
                patch.object(pathlib.Path, 'read_text', read_fixture), patch.object(audit, 'print', create=True):
            audit.main()
        # The offline image audit runs at /, so its source paths have no fixture root prefix.
        self.write(side, rd.UPDATERS, output.read_bytes().replace(os.fsencode(root) + b'/', b'/'))

    def install_alternatives(self, side, groups):
        for group, data in groups.items():
            links = {name: public for public, name in data['links'].items()}
            choice, = data['choices']
            slaves = sorted(links.keys() - {group})
            public = [item for name in slaves for item in (name, links[name])]
            targets = choice['targets']
            raw = ['auto', links[group], *public, '', targets[group], str(choice['priority']),
                   *(targets[name] for name in slaves), '']
            self.write(side, rd.ALTERNATIVES_ADMIN + group, '\n'.join(raw))
            for name, path in links.items():
                if targets[name]:
                    self.link(side, (rd.ALTERNATIVES + name, targets[name]))
                    self.link(side, (path[1:], '/' + rd.ALTERNATIVES + name))
            for target in targets.values():
                if target.endswith('/java-25-openjdk'):
                    (self.roots[side] / target[1:]).mkdir(parents=True, exist_ok=True)
                elif target:
                    self.write(side, target[1:], b'pinned Java fixture')

    def write(self, side, rel, raw, mode=0o644):
        path = self.roots[side] / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw.encode() if isinstance(raw, str) else raw)
        path.chmod(mode)
        return path

    def link(self, side, pair):
        path = self.roots[side] / pair[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(pair[1])

    def command(self, tool, action, *args):
        if tool == 'skopeo':
            side = self.mounts[args[-1].removeprefix('containers-storage:')]
            base = dict(rootfs=dict(diff_ids=['base']))
            if side == 'base':
                return json.dumps(base)
            labels = {'org.opencontainers.image.source': 'https://github.com/Ares-Empire/AresOS',
                      'org.opencontainers.image.revision': self.versions[side]}
            return json.dumps(dict(rootfs=dict(diff_ids=['base', side]), config=dict(Labels=labels)))
        self.assertEqual(tool, 'podman')
        if action == 'create':
            return args[-1]
        if action == 'mount':
            return str(self.roots[self.mounts[args[-1]]])
        if action in ('unmount', 'rm'):
            return ''
        self.assertEqual(action, 'run')
        if 'SCHEMA_REBUILD_MATCHED' in args[-1]:
            return 'SCHEMA_REBUILD_MATCHED' if self.rebuilt else 'schema byte mismatch'
        if '--entrypoint=/usr/bin/python3' in args:
            self.assertEqual(args[:args.index(rd.NEW)], ('--pull=never', '--network=none', '--read-only', '--tmpfs',
                '/tmp', '--rm', '--env=PATH=/usr/bin:/bin', '--entrypoint=/usr/bin/python3'))
            _, isolated, flag, code, source, *paths = args[args.index(rd.NEW):]
            self.assertEqual((isolated, flag, source), ('-I', '-c', rd.git_bytes(MAIN, rd.LABWC_STAGE_29).decode()))
            self.assertEqual(paths, ['/' + LABNAG, '/' + LABWC])
            # Run the submitted checker, with the input paths redirected into the fixture.
            rooted = [str(self.roots['new'] / path[1:]) for path in paths]
            output = subprocess.check_output([sys.executable, isolated, flag, code, source, *rooted], text=True,
                                             env=dict(os.environ, TMPDIR=str(self.work)))
            hashes = json.loads(output)
            return json.dumps({path: hashes[fixture] for path, fixture in zip(paths, rooted)})
        image, op, *params = args[args.index('--entrypoint=/usr/bin/rpm') + 1:]
        side = self.mounts[image]
        labwc = FEDORA if side == 'old' else REBUILT
        if op == '-qa':
            return '\n'.join(f'{nevra}\t{name}' for nevra, name in self.rpms[side].items())
        if op == '-V':
            if (side, params) == ('new', [rd.GTK_LAYER_29]):
                return self.verify
            self.assertEqual(params, [labwc])
            mocked = self.verify_labwc[side]
            if isinstance(mocked, subprocess.CalledProcessError):
                raise mocked
            return mocked
        if op == '-ql':
            if (side, params) == ('new', [rd.GTK_LAYER_29]):
                return '\n'.join('/' + path for path in (GTK, TYPELIB, GHOST))
            self.assertEqual(params, [labwc])
            return '\n'.join('/' + path for path in self.labwc_lists[side])
        if op == '-q' and params[-1] == labwc:
            self.assertEqual(params, ['--qf', rd.RPM_FILE_FORMAT, labwc])
            return '\n'.join('\t'.join(row) for row in self.labwc_records[side].values())
        self.assertEqual((side, op, params), ('new', '-q', ['--qf', rd.RPM_FILE_FORMAT, rd.GTK_LAYER_29]))
        return '\n'.join('\t'.join(('/' + path, 'root', 'root', str(flags), str(len(raw)), '8',
                                    hashlib.sha256(raw).hexdigest(), '', '', str(stat.S_IFREG | 0o644)))
                         for path, raw, flags in ((GTK, b'library', 0), (TYPELIB, b'typelib', 0),
                                                  (GHOST, BLANK, rd.RPMFILE_GHOST)))

    def diff(self, name='evidence', status='stopped'):
        evidence = self.work / name
        if status == 'passed':
            rd.main({name: sys.executable for name in build_tools.NAMES}, release='29', evidence=evidence)
        else:
            with self.assertRaisesRegex(AssertionError, '^STOP:'):
                rd.main({name: sys.executable for name in build_tools.NAMES}, release='29', evidence=evidence)
        result = json.loads((evidence / 'result.json').read_text())
        self.assertEqual(result['status'], status)
        return evidence, result

    def test_full_diff_explains_the_current_main_paths_including_labwc(self):
        evidence, result = self.diff(status='passed')
        self.assertEqual(result['problems'], [])
        self.assertEqual(result['unexplained'], [])
        labwc = result['labwc']
        self.assertEqual((labwc['replaces'], labwc['nevra']), (FEDORA, REBUILT))
        for side, nevra in (('old', FEDORA), ('new', REBUILT)):
            self.assertEqual(labwc[side + '_rpm_verify'], dict(packages=[nevra], exit_code=0, line_count=0, lines=[]))
            self.assertEqual(len(labwc[side]['paths']), 64)
        self.assertEqual(labwc['varying_sections'], list(r311.VARYING))
        for kind in ('normalized_sha256', 'loaded_sha256'):
            self.assertEqual(labwc[kind], self.labwc_lock['result'][kind])
        inputs = result['main']['labwc_inputs']
        for path, mode in rd.LABWC_INPUT_MODES_29.items():
            self.assertEqual(inputs[path], dict(mode=mode, blob=r28.git('rev-parse', f'{MAIN}:{path}').strip()))
        self.assertEqual(result['packages'][0]['nevra'], rd.GTK_LAYER_29)
        self.assertEqual(set(result['units']), {rd.GUARDIAN_UNIT, rd.GUARDIAN_LINK[0], rd.GUARDIAN_DROPIN,
                                              str(pathlib.PurePosixPath(rd.GUARDIAN_DROPIN).parent)})
        self.assertEqual(result['updaters'][0]['unit'], 'aresos-guardian.service')
        self.assertEqual(len(result['rc_xml']['added']), 7)
        self.assertEqual({row['format'] for row in result['font_caches']}, {'le64', 'le32d4'})
        with gzip.open(evidence / 'classified-files.json.gz', 'rt') as stream:
            files = json.load(stream)
        self.assertEqual(files[rd.CONTROL_RECORD]['rule'], 'control')
        self.assertEqual(files[GTK]['rule'], 'package')
        self.assertEqual(files[rd.LABWC_RECORD]['rule'], 'manifest')
        for side in ('old', 'new'):
            for binary in labwc[side]['binaries'].values():
                link = binary['link'][1:]
                for rel in (link, str(pathlib.PurePosixPath(link).parent)):
                    self.assertEqual(files[rel]['rule'], 'package')
        self.assertEqual(files[LABWC]['rule'], files[LABNAG]['rule'])

    def test_guardian_audit_requires_exact_fields_types_and_row_order(self):
        raw = (self.roots['new'] / rd.UPDATERS).read_text()
        console, guardian, control = json.loads(raw)
        cases = {
            'extra-field': [console, dict(guardian, extra=None), control],
            'missing-field': [console, {key: value for key, value in guardian.items() if key != 'sub_state'}, control],
            'guardian-type': [console, dict(guardian, suspicious=0), control],
            'existing-type': [dict(console, suspicious=0), guardian, control],
            'command-order': [console, dict(guardian, commands=guardian['commands'][::-1]), control],
            'row-order': [guardian, console, control],
        }
        payloads = {name: json.dumps(rows, sort_keys=True) for name, rows in cases.items()}
        payloads['duplicate-field'] = raw.replace('"sub_state": null', '"sub_state": "running", "sub_state": null', 1)
        for name, payload in payloads.items():
            with self.subTest(name=name):
                self.write('new', rd.UPDATERS, payload)
                _, result = self.diff(name)
                self.assertIn(rd.UPDATERS, result['unexplained'])
                self.assertIn('guardian updater audit row missing or different, or existing rows changed', result['problems'])

    def test_missing_paths_and_near_misses_stop_even_without_a_diff(self):
        for side in ('old', 'new'):
            for rel in (rd.GUARDIAN_LINK[0], rd.GUARDIAN_DROPIN, rd.PRISM + '/launcher', rd.UPDATERS,
                        '/usr/bin/java', rd.ALTERNATIVES_ADMIN + 'jre_25_openjdk', rd.CONTROL_UNIT, FONT_32):
                path = self.roots[side] / rel.lstrip('/')
                path.unlink(missing_ok=True)
        (self.roots['new'] / TYPELIB).unlink()
        (self.roots['new'] / rd.RC_XML).chmod(0o755)
        (self.roots['old'] / 'usr/libexec/aresos-shell').chmod(0o644)
        self.rebuilt = False
        self.verify = 'missing     /' + TYPELIB
        _, result = self.diff()
        for reason in (rd.GUARDIAN_DROPIN, 'guardian enable link', 'updater audit', TYPELIB, 'complete typed inventory',
                       'deterministic rebuild', 'alternatives groups', 'font caches missing', 'Control install',
                       rd.RC_XML, 'usr/libexec/aresos-shell', 'rpm verification'):
            self.assertTrue(any(reason in problem for problem in result['problems']), reason)

    def test_labwc_detects_a_file_missing_from_both_images_and_both_rpm_lists(self):
        rel = 'usr/share/doc/labwc/NEWS.md'
        for root in self.roots['old'], self.roots['new']:
            (root / rel).unlink()
        _, result = self.diff('missing-from-both-images')
        self.assertIn('missing or different non-ghost RPM file: /' + rel, result['labwc']['error'])
        self.assertNotIn(rel, result['unexplained'])
        for side in 'old', 'new':
            self.labwc_lists[side].remove(rel)
            del self.labwc_records[side][rel]
        _, result = self.diff('also-missing-from-rpms')
        self.assertIn('RPM file list differs from the reviewed', result['labwc']['error'])

    def test_labwc_requires_both_rpm_records_and_unchanged_payload_bytes(self):
        rel = 'usr/share/doc/labwc/NEWS.md'
        for side in 'old', 'new':
            row = self.labwc_records[side][rel]
            for index, value in ((3, str(rd.RPMFILE_GHOST)), (6, '0' * 64)):
                with self.subTest(side=side, index=index):
                    original, row[index] = row[index], value
                    _, result = self.diff(f'record-{side}-{index}')
                    self.assertIn(f'labwc {side}: missing or different non-ghost RPM file: /{rel}',
                                  result['labwc']['error'])
                    row[index] = original
        self.write('new', rel, 'changed doc and matching RPM digest\n')
        self.labwc_records['new'][rel] = self.rpm_record('new', rel)
        _, result = self.diff('changed-doc')
        self.assertIn('changed bytes or metadata outside the two binaries: ' + rel, result['labwc']['error'])
        self.assertIn(rel, result['unexplained'])

    def test_labwc_requires_exact_build_id_links_and_metadata(self):
        rel = 'usr/lib/.build-id/a1/' + REBUILT_IDS[LABWC][2:]
        link = self.roots['new'] / rel
        link.unlink()
        link.symlink_to('../../../../' + LABNAG)
        self.labwc_records['new'][rel] = self.rpm_record('new', rel)
        _, result = self.diff('wrong-link-target')
        self.assertIn('missing or different build-ID link: /' + rel, result['labwc']['error'])
        link.unlink()
        link.symlink_to('../../../../' + LABWC)
        self.labwc_records['new'][rel] = self.rpm_record('new', rel)
        stale = 'usr/lib/.build-id/6e/' + FEDORA_IDS[LABWC][2:]
        self.link('new', (stale, '../../../../' + LABWC))
        _, result = self.diff('stale-link')
        self.assertIn('build-ID link occurs in both images', result['labwc']['error'])
        (self.roots['new'] / stale).unlink()
        self.xattrs['old', LABWC] = {'user.unexpected': '31'}
        _, result = self.diff('unexpected-xattr')
        self.assertIn('labwc old: missing or different executable metadata: /' + LABWC, result['labwc']['error'])

    def test_labwc_requires_fedoras_build_ids_and_exact_candidate_link_names(self):
        for side, build_id in (('old', FEDORA_IDS[LABWC]), ('new', REBUILT_IDS[LABWC])):
            path = self.roots[side] / LABWC
            raw = path.read_bytes().replace(bytes.fromhex(build_id), bytes.fromhex('37' * 20))
            self.write(side, LABWC, raw, 0o755)
            self.labwc_records[side][LABWC] = self.rpm_record(side, LABWC)
            _, result = self.diff(f'wrong-build-id-{side}')
            self.assertIn('build ID differs from Fedora labwc' if side == 'old' else
                          'missing or different build-ID link', result['labwc']['error'])
            self.write(side, LABWC, raw.replace(bytes.fromhex('37' * 20), bytes.fromhex(build_id)), 0o755)
            self.labwc_records[side][LABWC] = self.rpm_record(side, LABWC)

    def test_labwc_can_share_one_build_id_directory(self):
        for build_id in REBUILT_IDS.values():
            folder = self.roots['new'] / 'usr/lib/.build-id' / build_id[:2]
            (folder / build_id[2:]).unlink()
            folder.rmdir()
        self.install_labwc('new', {LABWC: '6e' + 'a1' * 19, LABNAG: '6e' + 'b2' * 19})
        self.write('new', rd.LABWC_RECORD, self.labwc_lock_bytes())
        _, result = self.diff(status='passed')
        self.assertEqual(len(result['labwc']['old']['paths']), 64)
        self.assertEqual(len(result['labwc']['new']['paths']), 63)
        self.write('new', 'usr/lib/.build-id/6e/unreviewed', 'extra')
        _, result = self.diff('unreviewed-build-id-neighbor')
        self.assertEqual(result['unexplained'], ['usr/lib/.build-id/6e/unreviewed'])

    def test_labwc_needs_both_clean_rpm_verifications(self):
        self.verify_labwc['old'] = 'missing     /' + LABWC
        _, result = self.diff('old-rpm-verification')
        self.assertIn('labwc old: rpm verification failed', result['labwc']['error'])
        self.assertEqual(result['labwc']['old_rpm_verify']['line_count'], 1)
        self.verify_labwc['old'] = ''
        self.verify_labwc['new'] = subprocess.CalledProcessError(1, ['rpm'], output='')
        _, result = self.diff('new-rpm-verification')
        self.assertIn('labwc new: rpm verification failed', result['labwc']['error'])
        self.assertEqual(result['labwc']['new_rpm_verify']['exit_code'], 1)
        self.assertIn(LABWC, result['unexplained'])

    def test_labwc_requires_each_of_the_four_cut_pins(self):
        for kind in ('normalized_sha256', 'loaded_sha256'):
            for path in ('/' + LABWC, '/' + LABNAG):
                with self.subTest(kind=kind, path=path):
                    original = self.labwc_lock['result'][kind][path]
                    self.labwc_lock['result'][kind][path] = '0' * 64
                    self.write('new', rd.LABWC_RECORD, self.labwc_lock_bytes())
                    _, result = self.diff(f'{kind}-{path.rsplit("/", 1)[1]}')
                    self.assertIn(kind + ' differs from the lock', result['labwc']['error'])
                    self.labwc_lock['result'][kind][path] = original

    def test_labwc_refuses_swapped_executables_even_with_the_expected_build_ids(self):
        raw = {rel: (self.roots['new'] / rel).read_bytes() for rel in REBUILT_IDS}
        for target, source in ((LABWC, LABNAG), (LABNAG, LABWC)):
            swapped = raw[source].replace(bytes.fromhex(REBUILT_IDS[source]), bytes.fromhex(REBUILT_IDS[target]))
            self.write('new', target, swapped, 0o755)
            self.labwc_records['new'][target] = self.rpm_record('new', target)
        _, result = self.diff()
        self.assertIn('normalized_sha256 differs from the lock', result['labwc']['error'])
        for kind in ('normalized_sha256', 'loaded_sha256'):
            pins = self.labwc_lock['result'][kind]
            self.assertNotEqual(pins['/' + LABWC], pins['/' + LABNAG])
            self.assertEqual(result['labwc'][kind], {'/' + LABWC: pins['/' + LABNAG], '/' + LABNAG: pins['/' + LABWC]})

    def test_labwc_rejects_an_extra_rpm_path(self):
        rel = 'usr/share/doc/labwc/extra'
        self.write('new', rel, b'extra RPM payload')
        self.labwc_lists['new'].append(rel)
        self.labwc_records['new'][rel] = self.rpm_record('new', rel)
        _, result = self.diff()
        self.assertIn('labwc new: RPM file list differs from the reviewed', result['labwc']['error'])

    def test_labwc_rejects_a_duplicate_rpm_record(self):
        self.labwc_records['new']['duplicate'] = self.labwc_records['new'][LABWC]
        _, result = self.diff()
        self.assertIn('labwc new: missing or different non-ghost RPM file: /' + LABWC, result['labwc']['error'])

    def test_labwc_rejects_a_valid_but_stale_installed_lock(self):
        stale = rd.git_bytes(MAIN, rd.LABWC_LOCK_29)
        self.assertNotEqual(stale, self.labwc_lock_bytes())
        self.write('new', rd.LABWC_RECORD, stale)
        _, result = self.diff()
        self.assertNotIn('error', result['labwc'])
        self.assertIn(rd.LABWC_RECORD, result['unexplained'])

    def test_labwc_accepts_reviewed_debug_variation_and_rejects_loaded_padding_changes(self):
        path = self.roots['new'] / LABWC
        raw = path.read_bytes()
        debug = raw.replace(b'labwc.debug\0\x01', b'labwc.debug\0\x02')
        self.assertNotEqual(debug, raw)
        path.write_bytes(debug)
        self.labwc_records['new'][LABWC] = self.rpm_record('new', LABWC)
        self.diff('debuglink', status='passed')
        headers, _ = r311.loaded_image.program_headers(raw)
        offset = next(start + size for kind, start, size, _ in headers if kind == r311.PT_NOTE)
        path.write_bytes(raw[:offset] + bytes([raw[offset] ^ 1]) + raw[offset + 1:])
        self.labwc_records['new'][LABWC] = self.rpm_record('new', LABWC)
        _, result = self.diff('loaded-padding')
        self.assertEqual(result['labwc']['normalized_sha256'], self.labwc_lock['result']['normalized_sha256'])
        self.assertIn('loaded_sha256 differs from the lock', result['labwc']['error'])

    def test_labwc_refuses_an_unreviewed_version_even_with_matching_rpm_nevra(self):
        unreviewed = REBUILT.replace('aresos1', 'aresos2')
        self.labwc_lock['result']['nevra'] = unreviewed
        self.rpms['new'][unreviewed] = self.rpms['new'].pop(REBUILT)
        self.write('new', rd.LABWC_RECORD, self.labwc_lock_bytes())
        _, result = self.diff()
        self.assertIn('result.nevra is not the reviewed build', result['problems'][0])

    def test_labwc_refuses_download_pin_drift_without_a_nevra_change(self):
        raw = json.loads(lock29())
        next(row for row in raw['packages'] if row['nevra'] == FEDORA)['sha256'] = '0' * 64
        git_bytes = rd.git_bytes
        with patch.object(rd, 'git_bytes', side_effect=lambda rev, path:
                          json.dumps(raw).encode() if (rev, path) == (PROFILE_HEAD, 'os/packages.lock.json') else git_bytes(rev, path)):
            _, result = self.diff()
        self.assertEqual(result['problems'], ['R29 download lock changes existing RPM pins'])

    def test_renewed_mod_pin_binds_jar_lock_and_record_in_both_images(self):
        lock_path = 'os/minecraft/desktop.lock.json'
        real_git_bytes = rd.git_bytes
        lock = json.loads(real_git_bytes(PROFILE_HEAD, lock_path))
        jar = next(mod for mod in lock['mods'] if mod['file'] == 'aresos.jar')
        jar['sha256'] = self.jar['new'] = 'c' * 64
        raw = (json.dumps(lock, indent=2) + '\n').encode()
        self.write('new', rd.DESKTOP_LOCK, raw)
        self.write('new', rd.MOD_RECORD, json.dumps(dict(sha256=jar['sha256'], source_revision=PROFILE_HEAD,
                                                        pinned_sha256=jar['sha256']), indent=2) + '\n')
        def git_bytes(revision, path):
            return raw if (revision, path) == (PROFILE_HEAD, lock_path) else real_git_bytes(revision, path)
        with patch.object(rd, 'git_bytes', side_effect=git_bytes):
            evidence, result = self.diff(status='passed')
            self.assertEqual(result['unexplained'], [])
            with gzip.open(evidence / 'classified-files.json.gz', 'rt') as stream:
                self.assertEqual(json.load(stream)[rd.MOD_JAR]['reason'], rd.JAR_REASON_29)
            self.jar['old'] = 'd' * 64
            _, result = self.diff('bad-old-jar')
            self.assertIn(rd.MOD_JAR, result['unexplained'])

    def test_mode_attribute_and_unreviewed_generated_changes_stay_unexplained(self):
        self.write('new', 'usr/lib/sysimage/libdnf5/unreviewed.toml', 'update')
        self.write('new', rd.RPM_DATABASE, 'changed', 0o600)
        self.write('new', rd.LABWC_RECORD, '{}')
        self.xattrs['old', 'usr/libexec/aresos-cover'] = {'user.unexpected': '31'}
        self.write('new', 'usr/share/aresos/policy/masked-system-units.txt', '')
        _, result = self.diff()
        self.assertIn(rd.RPM_DATABASE, result['unexplained'])
        self.assertIn(rd.LABWC_RECORD, result['unexplained'])
        self.assertIn('usr/libexec/aresos-cover', result['unexplained'])
        self.assertIn('usr/lib/sysimage/libdnf5/unreviewed.toml', result['unexplained'])
        self.assertTrue(any('unreviewed unit unmasked' in problem for problem in result['problems']))

    def test_missing_input_and_wrong_cut_merge_write_stopped_result_before_mounting(self):
        real_git = rd.git
        cases = [
            (('ls-tree', '--name-only', 'HEAD', *rd.IMAGE_SOURCES_29), 'os/labwc', 'missing from HEAD'),
            (('diff', '-z', '--name-only', '--no-renames', MAIN, 'HEAD', '--', *rd.IMAGE_SOURCES_29),
             'os/labwc/stage.py\0', 'differ from main'),
            (('ls-tree', 'HEAD', '--', *rd.LABWC_INPUT_MODES_29), rd.LABWC_ELF_29, 'wrong Git type or mode'),
        ]
        for index, (intercept, path, expected) in enumerate(cases):
            def git(*args, **kwargs):
                if args == intercept:
                    if args[0] == 'ls-tree':
                        return '\n'.join(line for line in real_git(*args, **kwargs).splitlines()
                                         if line.split('\t')[-1] != path)
                    return path
                return real_git(*args, **kwargs)
            with self.subTest(expected=expected), patch.object(rd, 'git', side_effect=git):
                _, result = self.diff(f'evidence-{index}')
                self.assertIn(expected, result['problems'][0])
                self.commands.assert_not_called()

    def test_ignored_files_copied_from_os_stop_before_mounting(self):
        real_git = rd.git
        checkout = self.work / 'checkout'
        checkout.mkdir()
        real_git('-C', checkout, 'init', '--quiet')
        (checkout / '.gitignore').write_bytes(rd.git_bytes(PROFILE_HEAD, '.gitignore') + b'\n.env\n')
        copied = ('os/.env', 'os/config/var/log/dnf5.log', 'os/tests/ci/.env')
        for rel in (*copied, 'os/ci/.env', 'os/manifest/ci/.env', 'mod/.env'):
            path = checkout / rel
            path.parent.mkdir(parents=True)
            path.write_text('ignored fixture log\n')
            real_git('-C', checkout, 'check-ignore', '--quiet', '--', rel)

        def git(*args, **kwargs):
            if args[0] == 'ls-files':
                return real_git('-C', checkout, *args, **kwargs)
            return real_git(*args, **kwargs)

        with patch.object(rd, 'git', side_effect=git), patch.object(rd, 'ignored_build_files29', self.scan_ignored):
            _, result = self.diff()
            self.assertEqual(result['problems'], [
                'Git-ignored files in the os/ build context. Move or remove these paths before rebuilding: '
                + ', '.join(copied)])
            self.commands.assert_not_called()
            for rel in copied:
                (checkout / rel).unlink()
            self.assertEqual(rd.verify_source29(R28, MAIN)[1], [])
