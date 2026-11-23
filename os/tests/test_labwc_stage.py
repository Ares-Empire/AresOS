"""Package 311: the lock for our labwc rebuild, and every refusal of os/labwc/stage.py.

The stage's tools (curl, rpm, rpmbuild, dnf5, rpm2cpio, cpio) are stand-ins on PATH that act on a small state file, so
nothing here needs root, the network or a Fedora system. objcopy is the real one, on small ELF files made here: what it
leaves in a file is what the pins of 311d rest on.
"""
import contextlib
import copy
import fnmatch
import functools
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import py_compile
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('labwc_stage', ROOT / 'labwc/stage.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
spec = importlib.util.spec_from_file_location('labwc_loaded_image', ROOT / 'labwc/loaded_image.py')
loaded_image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loaded_image)

RESULT = 'labwc-0.9.6-1.fc44.aresos2.x86_64'
FEDORA = 'labwc-0.9.6-1.fc44.x86_64'
WLROOTS = 'wlroots0.19-0.19.3-1.fc44.x86_64'
WLROOTS_DEVEL = 'wlroots0.19-devel-0.19.3-1.fc44.x86_64'
# The image the final stage swaps labwc in.
BASE_PACKAGES = ['glibc-2.43-1.fc44.x86_64', FEDORA, WLROOTS]
# The locked fedora:44 the labwc stage builds on.
BUILD_BASE = ['bash-5.3-1.fc44.x86_64', 'glibc-2.43-1.fc44.x86_64']
FEDORA_BASE = 'registry.fedoraproject.org/fedora@sha256:' + 'b' * 64
SPEC = ('Name:       labwc\nRelease:    %autorelease\nSummary:    A compositor\n'
        'Source:     %{forgesource}\n\nBuildRequires: gcc\n')

FAKE_TOOL = r'''
import json, os, pathlib, shutil, sys
tool, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
# cpio is the second half of a pipeline: at the end of its input, rpm2cpio has saved the state.
archive = sys.stdin.read() if tool == 'cpio' else ''
state_path = pathlib.Path(os.environ['FAKE_STATE'])
state = json.loads(state_path.read_text())
state['calls'].append([tool, *args])

def save():
    state_path.write_text(json.dumps(state))

def nevra_of(path):
    name = pathlib.Path(path).name
    return state['nevra_of'].get(name, name.removesuffix('.rpm'))

code = 0
if tool == 'curl':
    url, target = args[-1], args[args.index('-o') + 1]
    if url in state['urls']:
        pathlib.Path(target).write_bytes(bytes.fromhex(state['urls'][url]))
    else:
        code = 22
elif tool == 'dnf5':
    code = state['dnf_exit']
    if code == 0 and 'install' in args:
        files = [arg for arg in args if arg.endswith('.rpm')]
        added = state['dnf_adds'] if state['dnf_adds'] is not None else [nevra_of(path) for path in files]
        removed = state['dnf_removes']
        if removed is None:
            removed = [state['fedora']] if state['result'] in added else []
        state['installed'] = sorted((set(state['installed']) | set(added)) - set(removed))
elif tool == 'rpm2cpio':
    code = state['rpm2cpio_exit']
    if code == 0:
        sys.stdout.write(json.dumps(state['payload']))
elif tool == 'cpio':
    code = state['cpio_exit']
    members = json.loads(archive) if code == 0 and archive else {}
    for member in [arg.removeprefix('./') for arg in args if arg.startswith('./')]:
        if member in members:
            pathlib.Path(member).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(member).write_bytes(bytes.fromhex(members[member]))
elif tool == 'rpmbuild':
    top = pathlib.Path(args[args.index('--define') + 1].split(' ', 1)[1])
    if state['build_exit']:
        code = state['build_exit']
    else:
        folder = top / 'RPMS/x86_64'
        folder.mkdir(parents=True)
        state['built_spec'] = pathlib.Path(args[-1]).read_text()
        state['built_sources'] = sorted(path.name for path in (top / 'SOURCES').iterdir())
        (folder / (state['built'] + '.rpm')).write_bytes(b'built rpm')
        (top / 'RPMS/noarch').mkdir()
        (top / 'RPMS/noarch/labwc-session.rpm').write_bytes(b'not ours to output')
elif tool == 'rpm':
    if '-qa' in args:
        print('\n'.join(state['installed']))
    elif '-V' in args:
        sys.stdout.write(state['verify_output'])
        code = state['verify_exit']
    elif '-qp' in args:
        if '--requires' in args:
            print('gcc\nmeson >= 0.59.0\nrpmlib(CompressedFileNames) <= 3.0.4-1')
        elif '%{SOURCERPM}' in ' '.join(args):
            nevra = nevra_of(args[-1])
            signature = state['signature']
            sys.stdout.write(f'dep-1.0-1.fc44.src.rpm\tx86_64\t{nevra}\t{signature}')
        else:
            sys.stdout.write(nevra_of(args[-1]))
    elif '-q' in args:
        wanted = args[-1]
        lines = [nevra for nevra in state['installed'] if nevra.rsplit('-', 2)[0] == wanted]
        if wanted == 'labwc' and state['labwc_query'] is not None:
            lines = state['labwc_query']
        print('\n'.join(lines) if lines else f'package {wanted} is not installed')
        code = 0 if lines else 1
    elif '-i' in args:
        top = pathlib.Path(args[args.index('--define') + 1].split(' ', 1)[1])
        (top / 'SOURCES').mkdir(parents=True)
        (top / 'SPECS').mkdir(parents=True)
        (top / 'SPECS/labwc.spec').write_text(state['spec'])
save()
sys.exit(code)
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


SHT_PROGBITS, SHT_STRTAB, SHT_NOTE = 1, 3, 7
SHF_ALLOC, SHF_EXECINSTR = 2, 4
VARYING = ('.note.gnu.build-id', '.gnu_debuglink', '.gnu_debugdata')
# Sections of a real labwc, and three whose names only look like the ones that are removed.
ELF_SECTIONS = (
    ('.note.gnu.build-id', SHT_NOTE, SHF_ALLOC, struct.pack('<III', 4, 20, 3) + b'GNU\0' + bytes(range(20))),
    ('.text', SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR, b'\x90' * 32 + b'\xc3'),
    ('.rodata', SHT_PROGBITS, SHF_ALLOC, b'reviewed strings\0'),
    ('.comment', SHT_PROGBITS, 0, b'compiler\0'),
    ('.note.gnu.build-id.kept', SHT_PROGBITS, 0, b'not the build id'),
    ('.gnu_debuglink.kept', SHT_PROGBITS, 0, b'not the debug link'),
    ('.gnu_debugdata.kept', SHT_PROGBITS, 0, b'not the debug data'),
    ('.gnu_debuglink', SHT_PROGBITS, 0, b'labwc.debug\0\x01\x02\x03\x04'),
    ('.gnu_debugdata', SHT_PROGBITS, 0, b'\xfd7zXZ compressed symbols'),
)


def elf_file(**changes):
    """A small x86-64 executable. changes replaces a section's bytes; its key is the name, with _ for each dot."""
    keys = {name.replace('.', '_').replace('-', '_'): name for name, _, _, _ in ELF_SECTIONS}
    contents = {name: data for name, _, _, data in ELF_SECTIONS} | {keys[key]: data for key, data in changes.items()}
    names = b'\0'
    offset = 64 + 2 * 56
    body = bytearray()
    headers = [bytes(64)]
    load_end = note = None

    def place(name, kind, flags, data, align):
        nonlocal names, offset
        padding = -offset % align
        body.extend(bytes(padding))
        offset += padding
        address = offset if flags & SHF_ALLOC else 0
        headers.append(struct.pack('<IIQQQQIIQQ', len(names), kind, flags, address, offset, len(data), 0, 0, align, 0))
        names += name.encode() + b'\0'
        body.extend(data)
        offset += len(data)
        return address

    for name, kind, flags, _ in ELF_SECTIONS:
        address = place(name, kind, flags, contents[name], 16 if flags & SHF_ALLOC else 1)
        if flags & SHF_ALLOC:
            load_end = offset
        if name == '.note.gnu.build-id':
            note = address, len(contents[name])
        if name == '.text':
            entry = address
    name_offset = len(names)
    names += b'.shstrtab\0'
    headers.append(struct.pack('<IIQQQQIIQQ', name_offset, SHT_STRTAB, 0, 0, offset, len(names), 0, 0, 1, 0))
    body.extend(names)
    offset += len(names)
    padding = -offset % 8
    body.extend(bytes(padding))
    offset += padding
    identity = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = identity + struct.pack('<HHIQQQIHHHHHH', 3, 62, 1, entry, 64, offset, 0, 64, 56, 2, 64, len(headers),
                                    len(headers) - 1)
    segments = (struct.pack('<IIQQQQQQ', 1, 5, 0, 0, 0, load_end, load_end, 0x1000) +
                struct.pack('<IIQQQQQQ', 4, 4, note[0], note[0], note[0], note[1], note[1], 4))
    return header + segments + bytes(body) + b''.join(headers)


def section_names(data):
    """The section names of an ELF file, in order."""
    table = struct.unpack_from('<Q', data, 40)[0]
    size, count, strings = struct.unpack_from('<HHH', data, 58)
    rows = [struct.unpack_from('<IIQQQQ', data, table + index * size) for index in range(count)]
    names = data[rows[strings][4]:rows[strings][4] + rows[strings][5]]
    return [names[row[0]:names.index(b'\0', row[0])].decode() for row in rows[1:]]


@functools.lru_cache
def normalized(data):
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / 'binary'
        path.write_bytes(data)
        return stage.normalized_sha256(path)


@functools.lru_cache
def loaded(data):
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / 'binary'
        path.write_bytes(data)
        return loaded_image.loaded_sha256(path)


LABWC_ELF = elf_file(_text=b'\x90' * 16 + b'\xc3')
LABNAG_ELF = elf_file(_text=b'\x90' * 8 + b'\xc3')


class StageCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.tmp = pathlib.Path(folder.name)
        self.tools = self.tmp / 'tools'
        self.tools.mkdir()
        program = self.tools / 'fake-tool'
        program.write_text(f'#!{sys.executable} -I\n{FAKE_TOOL}')
        program.chmod(program.stat().st_mode | stat.S_IEXEC)
        for name in ('curl', 'rpm', 'rpmbuild', 'dnf5', 'rpm2cpio', 'cpio'):
            (self.tools / name).symlink_to(program)
        (self.tools / 'objcopy').symlink_to(shutil.which('objcopy'))

        self.lock_dir = self.tmp / 'labwc'
        self.lock_dir.mkdir()
        # Two patches, as the reviewed lock has: the order in the lock is the order in the spec.
        self.patches = {'0001-fix.patch': b'the patch\n', '0002-gate.patch': b'the second patch\n'}
        for name, data in self.patches.items():
            (self.lock_dir / name).write_bytes(data)
        self.source_url = stage.KOJI + 'labwc/0.9.6/1.fc44/src/labwc-0.9.6-1.fc44.src.rpm'
        self.source_bytes = b'source package'
        self.dependencies = {'aaa-devel-1.0-1.fc44.x86_64': b'first', 'bbb-2.0-3.fc44.noarch': b'second',
                             WLROOTS_DEVEL: b'third'}
        self.lock = dict(
            base=dict(reference=FEDORA_BASE, packages=BUILD_BASE),
            source=dict(url=self.source_url, sha256=digest(self.source_bytes)),
            patches=[dict(file=name, sha256=digest(data)) for name, data in self.patches.items()],
            result=dict(nevra=RESULT, replaces=FEDORA,
                        normalized_sha256={'/usr/bin/labnag': normalized(LABNAG_ELF),
                                           '/usr/bin/labwc': normalized(LABWC_ELF)},
                        loaded_sha256={'/usr/bin/labnag': loaded(LABNAG_ELF), '/usr/bin/labwc': loaded(LABWC_ELF)}),
            build_dependencies=[dict(nevra=nevra, url=self.dep_url(nevra), sha256=digest(data))
                                for nevra, data in sorted(self.dependencies.items())])
        self.write_lock()
        self.write_image_packages(WLROOTS)
        self.write_containerfile(f'FROM {FEDORA_BASE} AS labwc\n')
        self.state = dict(
            calls=[], urls={self.source_url: self.source_bytes.hex(),
                            **{self.dep_url(n): data.hex() for n, data in self.dependencies.items()}},
            nevra_of={}, installed=list(BASE_PACKAGES), dnf_exit=0, dnf_adds=None, dnf_removes=None, build_exit=0,
            built=RESULT, spec=SPEC, verify_output='', verify_exit=0, labwc_query=None, fedora=FEDORA, result=RESULT,
            payload={'usr/bin/labnag': LABNAG_ELF.hex(), 'usr/bin/labwc': LABWC_ELF.hex()}, rpm2cpio_exit=0, cpio_exit=0,
            signature='RSA/SHA256, Mon 1 Jan 2026, Key ID abcdef0123456789')
        self.manifest = self.tmp / 'manifest'
        self.manifest.mkdir()
        self.out = self.tmp / 'out'
        self.rpms = self.tmp / 'rpms'
        self.rpms.mkdir()
        (self.rpms / f'{RESULT}.rpm').write_bytes(b'built rpm')
        self.inputs = self.tmp / 'inputs'

    def write_image_packages(self, *nevras):
        (self.tmp / 'packages.lock.json').write_text(json.dumps(dict(packages=[dict(nevra=n) for n in nevras])))

    def write_containerfile(self, text):
        (self.tmp / 'Containerfile').write_text(text)

    def prepare_inputs(self):
        """What the labwc-inputs stage hands over, on the locked environment install-inputs.sh made."""
        (self.inputs / 'rpms').mkdir(parents=True)
        (self.inputs / stage.SOURCE_FILE).write_bytes(self.source_bytes)
        for nevra, data in self.dependencies.items():
            (self.inputs / 'rpms' / f'{nevra}.rpm').write_bytes(data)
        self.state['installed'] = sorted([*BUILD_BASE, *self.dependencies])

    @staticmethod
    def dep_url(nevra):
        return f'{stage.KOJI}dep/1.0/1.fc44/data/signed/01234567/x86_64/{nevra}.rpm'

    def write_lock(self):
        (self.lock_dir / 'labwc.lock.json').write_text(json.dumps(self.lock))

    def run_stage(self, *arguments):
        state_file = self.tmp / 'state.json'
        state_file.write_text(json.dumps(self.state))
        stderr, stdout = io.StringIO(), io.StringIO()
        environment = dict(PATH=str(self.tools), FAKE_STATE=str(state_file), TMPDIR=str(self.tmp))
        with mock.patch.dict(os.environ, environment), mock.patch.object(stage, 'MANIFEST', self.manifest), \
                contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = stage.main(['stage.py', *map(str, arguments)])
        self.state = json.loads(state_file.read_text())
        self.stderr, self.stdout = stderr.getvalue(), stdout.getvalue()
        return code

    def called(self, tool, *needles):
        return [call for call in self.state['calls'] if call[0] == tool and all(n in call for n in needles)]

    def assert_refused(self, code, pattern):
        self.assertEqual(code, 1, self.stderr)
        lines = self.stderr.strip().splitlines()
        self.assertEqual(len(lines), 1, f'one clear line expected: {lines}')
        self.assertRegex(lines[0], '^LABWC_REFUSED ')
        self.assertRegex(lines[0], pattern)

    def fetch(self):
        return self.run_stage('fetch', self.lock_dir, self.inputs)

    def build(self):
        return self.run_stage('build', self.lock_dir, self.inputs, self.out)

    def install(self):
        return self.run_stage('install', self.rpms, self.lock_dir)


class FetchTest(StageCase):
    def test_exact_inputs_are_handed_over(self):
        self.assertEqual(self.fetch(), 0, self.stderr)
        self.assertEqual((self.inputs / stage.SOURCE_FILE).read_bytes(), self.source_bytes)
        self.assertEqual(sorted(path.name for path in (self.inputs / 'rpms').iterdir()),
                         sorted(f'{nevra}.rpm' for nevra in self.dependencies))

    def test_refuses_a_wrong_source_hash(self):
        self.state['urls'][self.source_url] = b'other source'.hex()
        self.assert_refused(self.fetch(), 'the source package has SHA-256')

    def test_refuses_a_wrong_patch_hash(self):
        for name in self.patches:
            with self.subTest(name):
                (self.lock_dir / name).write_bytes(b'another patch\n')
                self.assert_refused(self.fetch(), f'the patch {name} has SHA-256')
                self.assertFalse(self.called('curl'))
                (self.lock_dir / name).write_bytes(self.patches[name])

    def test_refuses_a_missing_patch(self):
        (self.lock_dir / '0002-gate.patch').unlink()
        self.assert_refused(self.fetch(), 'the patch 0002-gate.patch is missing')

    def test_refuses_a_patch_file_the_lock_does_not_name(self):
        (self.lock_dir / '0003-stray.patch').write_bytes(b'not locked\n')
        self.assert_refused(self.fetch(), r"the patches \['0003-stray\.patch'\] are not in the lock")
        self.assertFalse(self.called('curl'))

    def test_refuses_a_dependency_with_other_bytes(self):
        nevra = 'bbb-2.0-3.fc44.noarch'
        self.state['urls'][self.dep_url(nevra)] = b'newer build'.hex()
        self.assert_refused(self.fetch(), f'build dependency {nevra} has SHA-256')

    def test_refuses_a_dependency_that_is_another_package(self):
        self.state['nevra_of'] = {'aaa-devel-1.0-1.fc44.x86_64.rpm': 'aaa-devel-1.1-1.fc44.x86_64'}
        self.assert_refused(self.fetch(), 'is really aaa-devel-1.1-1.fc44.x86_64')

    def test_refuses_a_download_that_fails(self):
        del self.state['urls'][self.dep_url('aaa-devel-1.0-1.fc44.x86_64')]
        self.assert_refused(self.fetch(), 'could not download')

    def test_guard_1_refuses_headers_of_another_wlroots_build(self):
        for runtime in ('wlroots0.19-0.19.4-1.fc44.x86_64', 'wlroots0.19-0.19.3-2.fc44.x86_64'):
            with self.subTest(runtime):
                self.write_image_packages(runtime)
                self.assert_refused(self.fetch(), f'is not the same build as the image.s {runtime}')
                self.assertFalse(self.called('curl'))

    def test_guard_1_refuses_an_image_without_one_wlroots(self):
        self.write_image_packages('glibc-2.43-1.fc44.x86_64')
        self.assert_refused(self.fetch(), 'must hold exactly one wlroots0.19')


class LockedBaseTest(StageCase):
    """311c: the Fedora image the labwc stage is built from is the one the lock records."""
    OTHER = 'registry.fedoraproject.org/fedora@sha256:' + 'c' * 64

    def assert_base_refused(self, pattern='must be built from the locked'):
        self.assert_refused(self.fetch(), pattern)
        self.assertFalse(self.called('curl'), 'the refusal comes before any download')
        self.assertFalse(self.inputs.exists(), 'the refusal comes before any input is handed over')

    def test_another_digest_in_the_stage_is_refused(self):
        self.write_containerfile(f'FROM {self.OTHER} AS labwc\n')
        self.assert_base_refused(re.escape(f"Containerfile says ['{self.OTHER}']"))

    def test_another_digest_in_the_lock_is_refused(self):
        self.lock['base']['reference'] = self.OTHER
        self.write_lock()
        self.assert_base_refused(re.escape(f"the locked {self.OTHER}, Containerfile says ['{FEDORA_BASE}']"))

    def test_a_stage_it_cannot_read_as_the_locked_digest_is_refused(self):
        cases = {
            'no stage': 'FROM packages AS aresos\n',
            'a second stage': f'FROM {FEDORA_BASE} AS labwc\nFROM {self.OTHER} AS labwc\n',
            'lower case': f'from {self.OTHER} as labwc\n',
            'a tag': 'FROM registry.fedoraproject.org/fedora:44 AS labwc\n',
            'a build argument': 'FROM ${FEDORA} AS labwc\n',
            'a flag': f'FROM --platform=linux/amd64 {FEDORA_BASE} AS labwc\n',
            'two lines': f'FROM {FEDORA_BASE} \\\n    AS labwc\n',
        }
        for name, text in cases.items():
            with self.subTest(name):
                self.state['calls'] = []
                self.write_containerfile(text)
                self.assert_base_refused()

    def test_other_stages_and_comments_are_not_the_labwc_stage(self):
        self.write_containerfile(f'# FROM {self.OTHER} AS labwc\nFROM {self.OTHER} AS labwc-inputs\n'
                                 f'FROM {FEDORA_BASE} AS labwc\nFROM packages AS aresos\n')
        self.assertEqual(self.fetch(), 0, self.stderr)

    def test_a_missing_containerfile_is_refused(self):
        (self.tmp / 'Containerfile').unlink()
        self.assert_base_refused('Containerfile cannot be read')

    def real_files(self):
        """A copy of this repository's Containerfile and lock, as the labwc-inputs stage sees them."""
        tree = self.tmp / 'real'
        (tree / 'labwc').mkdir(parents=True, exist_ok=True)
        for name in ('Containerfile', 'packages.lock.json', 'labwc/labwc.lock.json'):
            (tree / name).write_bytes((ROOT / name).read_bytes())
        return tree

    def test_the_real_files_pass_the_check_and_go_on_to_the_downloads(self):
        stage.require_locked_base(stage.load_lock(ROOT / 'labwc'), ROOT / 'labwc')
        # The stand-in curl has no files here, so the first download is as far as this run gets.
        self.state['urls'] = {}
        self.assert_refused(self.run_stage('fetch', ROOT / 'labwc', self.inputs), 'could not download')
        self.assertEqual(len(self.called('curl')), 1)

    def test_the_real_files_are_refused_when_either_side_changes(self):
        locked = stage.load_lock(ROOT / 'labwc')['base']['reference']
        for name in ('Containerfile', 'labwc/labwc.lock.json'):
            with self.subTest(name):
                tree = self.real_files()
                text = (tree / name).read_text()
                self.assertEqual(text.count(locked), 1)
                (tree / name).write_text(text.replace(locked, self.OTHER))
                self.state['calls'] = []
                self.assert_refused(self.run_stage('fetch', tree / 'labwc', self.inputs),
                                    'must be built from the locked')
                self.assertFalse(self.called('curl'))


class BuildTest(StageCase):
    def setUp(self):
        super().setUp()
        self.prepare_inputs()

    def test_exact_inputs_give_the_rpm_and_nothing_else(self):
        self.assertEqual(self.build(), 0, self.stderr)
        self.assertEqual([path.name for path in self.out.iterdir()], [f'{RESULT}.rpm'])
        self.assertIn(f'LABWC_BUILT {RESULT} ', self.stdout)

    def test_the_build_downloads_and_installs_nothing(self):
        self.assertEqual(self.build(), 0, self.stderr)
        self.assertFalse(self.called('curl'))
        self.assertFalse(self.called('dnf5'))

    def test_the_spec_edit_is_the_release_suffix_and_one_patch_line_each_in_order(self):
        spec_file = self.tmp / 'edited.spec'
        spec_file.write_text(SPEC)
        stage.edit_spec(spec_file, ['0001-fix.patch', '0002-gate.patch'])
        expected = SPEC.replace('Release:    %autorelease\n', 'Release:    %{autorelease}.aresos2\n').replace(
            'Source:     %{forgesource}\n',
            'Source:     %{forgesource}\nPatch0:     0001-fix.patch\nPatch1:     0002-gate.patch\n')
        self.assertEqual(spec_file.read_text(), expected)

    def test_the_build_gives_rpmbuild_every_locked_patch(self):
        self.assertEqual(self.build(), 0, self.stderr)
        self.assertEqual(self.state['built_spec'].count('Patch'), 2, self.state['built_spec'])
        self.assertIn('Patch0:     0001-fix.patch\nPatch1:     0002-gate.patch\n', self.state['built_spec'])
        self.assertEqual(self.state['built_sources'], sorted(self.patches))

    def test_refuses_a_wrong_source_hash(self):
        (self.inputs / stage.SOURCE_FILE).write_bytes(b'other source')
        self.assert_refused(self.build(), 'the source package has SHA-256')
        self.assertFalse(self.called('rpmbuild'))

    def test_refuses_a_missing_source(self):
        (self.inputs / stage.SOURCE_FILE).unlink()
        self.assert_refused(self.build(), 'the source package is missing')

    def test_refuses_a_wrong_patch_hash(self):
        (self.lock_dir / '0002-gate.patch').write_bytes(b'another patch\n')
        self.assert_refused(self.build(), 'the patch 0002-gate.patch has SHA-256')
        self.assertFalse(self.called('rpmbuild'))

    def test_refuses_a_dependency_with_other_bytes(self):
        nevra = 'bbb-2.0-3.fc44.noarch'
        (self.inputs / 'rpms' / f'{nevra}.rpm').write_bytes(b'newer build')
        self.assert_refused(self.build(), f'build dependency {nevra} has SHA-256')
        self.assertFalse(self.called('rpmbuild'))

    def test_refuses_an_input_outside_the_lock(self):
        (self.inputs / 'rpms/surprise-9-1.fc44.x86_64.rpm').write_bytes(b'x')
        self.assert_refused(self.build(), r"outside the lock \['surprise-9-1.fc44.x86_64.rpm'\]")
        self.assertFalse(self.called('rpmbuild'))

    def test_refuses_a_missing_input(self):
        (self.inputs / 'rpms/bbb-2.0-3.fc44.noarch.rpm').unlink()
        self.assert_refused(self.build(), r"missing \['bbb-2.0-3.fc44.noarch.rpm'\]")

    def test_refuses_a_package_outside_the_lock(self):
        self.state['installed'].append('surprise-9-1.fc44.x86_64')
        self.assert_refused(self.build(), r"drifted: outside the lock \['surprise-9-1.fc44.x86_64'\]")
        self.assertFalse(self.called('rpmbuild'))

    def test_refuses_a_locked_package_that_was_not_installed(self):
        self.state['installed'].remove('aaa-devel-1.0-1.fc44.x86_64')
        self.assert_refused(self.build(), r"missing \['aaa-devel-1.0-1.fc44.x86_64'\]")

    def test_refuses_another_base(self):
        self.state['installed'].remove('bash-5.3-1.fc44.x86_64')
        self.state['installed'].append('bash-5.4-1.fc44.x86_64')
        self.assert_refused(self.build(), r"outside the lock \['bash-5.4-1.fc44.x86_64'\], missing "
                                          r"\['bash-5.3-1.fc44.x86_64'\]")
        self.assertFalse(self.called('rpmbuild'))

    def test_a_locked_upgrade_replaces_its_copy_in_the_base(self):
        newer = 'glibc-2.43-9.fc44.x86_64'
        self.lock['build_dependencies'] = sorted([*self.lock['build_dependencies'], dict(
            nevra=newer, url=self.dep_url(newer), sha256=digest(b'newer glibc'))], key=lambda entry: entry['nevra'])
        self.write_lock()
        (self.inputs / 'rpms' / f'{newer}.rpm').write_bytes(b'newer glibc')
        self.state['installed'] = sorted(['bash-5.3-1.fc44.x86_64', newer, *self.dependencies])
        self.assertEqual(self.build(), 0, self.stderr)

    def test_the_signing_keys_are_not_part_of_the_environment(self):
        self.state['installed'].append('gpg-pubkey-6d9f90a6-6786af3b')
        self.assertEqual(self.build(), 0, self.stderr)

    def test_refuses_a_spec_it_does_not_know(self):
        for changed in (SPEC.replace('%autorelease', '2%{?dist}'), SPEC.replace('%{forgesource}', 'other.tar.gz'),
                        SPEC + SPEC):
            with self.subTest(changed=changed):
                self.state.update(spec=changed, calls=[])
                self.assert_refused(self.build(), "Fedora's spec does not have exactly one line")
                self.assertFalse(self.called('rpmbuild'))

    def test_refuses_a_build_with_another_name(self):
        self.state['built'] = 'labwc-0.9.6-1.fc44.x86_64'
        self.assert_refused(self.build(), f'did not produce {RESULT}')
        self.assertFalse(self.out.exists() and any(self.out.iterdir()))

    def test_refuses_an_output_folder_with_other_files(self):
        self.out.mkdir()
        (self.out / 'left-over').write_text('x')
        self.assert_refused(self.build(), 'the RPM and nothing else')


class NormalizedHashTest(unittest.TestCase):
    """311d: what the pins cover, measured with the real objcopy."""
    def test_the_three_sections_are_the_only_ones_named(self):
        self.assertEqual(stage.VARYING_SECTIONS, VARYING)

    def test_the_three_sections_are_the_only_ones_removed(self):
        seen = {}
        real_query = stage.query

        def recording_query(*command):
            output = real_query(*command)
            seen.update(command=command, left=pathlib.Path(command[-1]).read_bytes())
            return output

        with mock.patch.object(stage, 'query', recording_query):
            normalized.__wrapped__(LABWC_ELF)
        self.assertEqual(seen['command'][:-1], ('objcopy', '--remove-section', '.note.gnu.build-id', '--remove-section',
                                                '.gnu_debuglink', '--remove-section', '.gnu_debugdata'))
        before = section_names(LABWC_ELF)
        self.assertLessEqual(set(VARYING), set(before))
        self.assertEqual(section_names(seen['left']), [name for name in before if name not in VARYING])

    def test_a_change_in_any_other_section_gives_another_hash(self):
        for name, _, _, data in ELF_SECTIONS:
            if name in VARYING:
                continue
            key = name.replace('.', '_').replace('-', '_')
            with self.subTest(name):
                changed = bytes([data[0] ^ 1]) + data[1:]
                self.assertNotEqual(normalized(elf_file(**{key: changed})), normalized(elf_file()))

    def test_a_change_in_only_the_three_sections_gives_the_same_hash(self):
        other_id = struct.pack('<III', 4, 20, 3) + b'GNU\0' + bytes(range(100, 120))
        cases = {
            'the build id': dict(_note_gnu_build_id=other_id),
            'the debug link': dict(_gnu_debuglink=b'other.debug\0\x09\x08\x07\x06'),
            'the debug data': dict(_gnu_debugdata=b'\xfd7zXZ other symbols, and more of them'),
            'all three': dict(_note_gnu_build_id=other_id, _gnu_debuglink=b'other.debug\0\x09\x08\x07\x06',
                              _gnu_debugdata=b'\xfd7zXZ other'),
        }
        for name, changes in cases.items():
            with self.subTest(name):
                self.assertNotEqual(elf_file(**changes), elf_file())
                self.assertEqual(normalized(elf_file(**changes)), normalized(elf_file()))

    def test_the_binary_itself_is_not_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / 'labwc'
            path.write_bytes(LABWC_ELF)
            stage.normalized_sha256(path)
            self.assertEqual(path.read_bytes(), LABWC_ELF)
            self.assertEqual(os.listdir(folder), ['labwc'])

    def test_a_file_objcopy_cannot_read_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / 'labwc'
            path.write_bytes(b'not an ELF file')
            with self.assertRaisesRegex(stage.Refusal, 'objcopy --remove-section .* failed'):
                stage.normalized_sha256(path)


PT_NULL, PT_LOAD, PT_INTERP, PT_NOTE, PT_GNU_RELRO = 0, 1, 3, 4, 0x6474e552
P_TYPE, P_OFFSET, P_FILESZ, P_ALIGN = 0, 8, 32, 48
INTERP, FIRST_LOAD, SECOND_LOAD, PROPERTY_NOTES, BUILD_ID_NOTES, RELRO = range(6)
HEADER_COUNT = 6
INTERPRETER = b'/lib64/ld-linux-x86-64.so.2\0'
BUILD_ID = bytes(range(20))


def elf_note(kind, descriptor, alignment=4, name=b'GNU\0'):
    def padded(data):
        return data + bytes(-len(data) % alignment)
    return padded(padded(struct.pack('<III', len(name), len(descriptor), kind) + name) + descriptor)


BUILD_ID_NOTE = elf_note(3, BUILD_ID)
PROPERTY_NOTE = elf_note(5, bytes(16), 8)
GAP = 48


def mapped_file(notes=BUILD_ID_NOTE, note_alignment=4, section_table=0x9000, after_end=b'labwc.debug\0\xfd7zXZ symbols',
                code=b'\x90' * 32 + b'\xc3'):
    """An x86-64 file laid out like a real labwc: mapped headers and notes, a gap, code, then bytes nothing maps."""
    interpreter_at = 64 + HEADER_COUNT * 56
    property_at = interpreter_at + len(INTERPRETER) + (-(interpreter_at + len(INTERPRETER)) % 8)
    notes_at = property_at + len(PROPERTY_NOTE)
    first_end = notes_at + len(notes)
    code_at = first_end + GAP
    end = code_at + len(code)

    def header(kind, offset, size, alignment):
        return struct.pack('<IIQQQQQQ', kind, 4, offset, offset, offset, size, size, alignment)

    table = (header(PT_INTERP, interpreter_at, len(INTERPRETER), 1) + header(PT_LOAD, 0, first_end, 0x1000) +
             header(PT_LOAD, code_at, len(code), 0x1000) + header(PT_NOTE, property_at, len(PROPERTY_NOTE), 8) +
             header(PT_NOTE, notes_at, len(notes), note_alignment) + header(PT_GNU_RELRO, 0, 64, 1))
    identity = b'\x7fELF\x02\x01\x01' + bytes(9)
    elf_header = identity + struct.pack('<HHIQQQIHHHHHH', 3, 62, 1, code_at, 64, section_table, 0, 64, 56, HEADER_COUNT,
                                        64, 0, 0)
    middle = INTERPRETER + bytes(property_at - interpreter_at - len(INTERPRETER)) + PROPERTY_NOTE + notes
    return elf_header + table + middle + bytes(GAP) + code + after_end


MAPPED = mapped_file()


def header_field(index, field):
    return 64 + index * 56 + field


def with_field(data, offset, layout, value):
    changed = bytearray(data)
    struct.pack_into(layout, changed, offset, value)
    return bytes(changed)


def field_of(data, offset, layout):
    return struct.unpack_from(layout, data, offset)[0]


class LoadedImageTest(unittest.TestCase):
    """311e: the bytes the loader maps, measured on the real os/labwc/loaded_image.py."""
    def assert_refused(self, data, pattern):
        with self.assertRaisesRegex(loaded_image.LoadedImageRefused, pattern):
            loaded(data)

    def test_the_fixture_is_accepted(self):
        self.assertRegex(loaded(MAPPED), '^[0-9a-f]{64}$')

    def test_the_hash_is_the_defined_image(self):
        end = field_of(MAPPED, header_field(SECOND_LOAD, P_OFFSET), '<Q') + \
            field_of(MAPPED, header_field(SECOND_LOAD, P_FILESZ), '<Q')
        notes_at = field_of(MAPPED, header_field(BUILD_ID_NOTES, P_OFFSET), '<Q')
        image = bytearray(MAPPED[:end])
        image[0x28:0x30] = bytes(8)
        image[notes_at + 16:notes_at + 36] = bytes(20)
        self.assertEqual(loaded(MAPPED), hashlib.sha256(image).hexdigest())

    def test_a_change_the_loader_would_see_gives_another_hash(self):
        end_of_code = MAPPED.index(b'\xc3', 64 + HEADER_COUNT * 56)
        interpreter_at = field_of(MAPPED, header_field(INTERP, P_OFFSET), '<Q')
        gap_at = field_of(MAPPED, header_field(SECOND_LOAD, P_OFFSET), '<Q') - 1
        other = b'/tmp/other-loader.so\0'
        appended = with_field(with_field(MAPPED + other, header_field(INTERP, P_OFFSET), '<Q', len(MAPPED)),
                              header_field(INTERP, P_FILESZ), '<Q', len(other))
        flipped = lambda offset: MAPPED[:offset] + bytes([MAPPED[offset] ^ 1]) + MAPPED[offset + 1:]
        cases = {
            'a code byte': flipped(end_of_code),
            "PT_INTERP's offset": with_field(MAPPED, header_field(INTERP, P_OFFSET), '<Q', interpreter_at + 1),
            'PT_GNU_RELRO made PT_NULL': with_field(MAPPED, header_field(RELRO, P_TYPE), '<I', PT_NULL),
            'a lower e_phnum': with_field(MAPPED, 0x38, '<H', HEADER_COUNT - 1),
            'an interpreter appended and pointed at': appended,
            'a byte between segments': flipped(gap_at),
        }
        for name, changed in cases.items():
            with self.subTest(name):
                self.assertNotEqual(changed, MAPPED)
                self.assertNotEqual(loaded(changed), loaded(MAPPED))

    def test_what_differs_between_builds_of_the_same_code_keeps_the_hash(self):
        cases = {
            'another build id': mapped_file(notes=elf_note(3, bytes(range(100, 120)))),
            'another e_shoff': mapped_file(section_table=0x123456),
            'an e_shoff outside the file': mapped_file(section_table=2 ** 64 - 1),
            'other bytes after the end': mapped_file(after_end=b'other.debug\0\xfd7zXZ other symbols, and more of them'),
            'nothing after the end': mapped_file(after_end=b''),
        }
        for name, changed in cases.items():
            with self.subTest(name):
                self.assertNotEqual(changed, MAPPED)
                self.assertEqual(loaded(changed), loaded(MAPPED))

    def test_notes_are_walked_with_their_segments_alignment(self):
        # A 20-byte descriptor needs padding at alignment 8 and none at 4: a walk with 4 would misread what follows.
        first = elf_note(5, bytes(20), 8) + elf_note(3, BUILD_ID, 8)
        second = elf_note(5, bytes(20), 8) + elf_note(3, bytes(range(100, 120)), 8)
        self.assertEqual(loaded(mapped_file(first, 8)), loaded(mapped_file(second, 8)))
        # An 8-byte name ends at 20: its descriptor starts at 24 at alignment 8.
        long_name = elf_note(5, bytes(20), 8, name=b'ABCDEFG\0')
        self.assertEqual(loaded(mapped_file(long_name + elf_note(3, BUILD_ID, 8), 8)),
                         loaded(mapped_file(long_name + elf_note(3, bytes(range(100, 120)), 8), 8)))

    def test_a_build_id_outside_the_gnu_name_is_not_the_build_id(self):
        self.assert_refused(mapped_file(elf_note(3, BUILD_ID, name=b'XYZ\0')), '0 GNU build-id notes')

    def test_each_refusal_fires(self):
        size = len(MAPPED)
        same_note_twice = MAPPED
        for field, value in ((P_OFFSET, field_of(MAPPED, header_field(BUILD_ID_NOTES, P_OFFSET), '<Q')),
                             (P_FILESZ, len(BUILD_ID_NOTE)), (P_ALIGN, 4)):
            same_note_twice = with_field(same_note_twice, header_field(PROPERTY_NOTES, field), '<Q', value)
        # Every segment ends at byte 32, inside the ELF header.
        short_image = MAPPED
        for index in range(HEADER_COUNT):
            short_image = with_field(with_field(short_image, header_field(index, P_OFFSET), '<Q', 0),
                                     header_field(index, P_FILESZ), '<Q', 32 if index == FIRST_LOAD else 0)
        # One program header read from offset 0: its p_offset is bytes 8 to 16 and its p_filesz is e_phoff, 0.
        short_of_the_elf_header = with_field(with_field(with_field(MAPPED, 0x20, '<Q', 0), 0x38, '<H', 1), 8, '<Q', 60)
        # The last four bytes of the file: too few for a note header, and nothing after them to read.
        cut_at_the_end_of_the_file = with_field(with_field(MAPPED, header_field(BUILD_ID_NOTES, P_OFFSET), '<Q', size - 4),
                                                header_field(BUILD_ID_NOTES, P_FILESZ), '<Q', 4)
        cases = {
            'not an ELF file': (b'not an ELF file' + bytes(64), 'not an ELF file'),
            'shorter than the ELF header': (MAPPED[:63], 'not an ELF file'),
            'wrong class': (MAPPED[:4] + b'\x01' + MAPPED[5:], 'not ELF64'),
            'wrong byte order': (MAPPED[:5] + b'\x02' + MAPPED[6:], 'not little-endian'),
            'wrong machine': (with_field(MAPPED, 0x12, '<H', 183), 'machine is 183'),
            'wrong e_phentsize': (with_field(MAPPED, 0x36, '<H', 64), 'e_phentsize is 64'),
            'no program headers': (with_field(MAPPED, 0x38, '<H', 0), 'e_phnum is 0'),
            'too many program headers': (with_field(MAPPED, 0x38, '<H', 0xffff), 'e_phnum is 65535'),
            'the table outside the file': (with_field(MAPPED, 0x20, '<Q', size - 55), 'table lies outside the file'),
            'an offset outside the file': (with_field(MAPPED, header_field(RELRO, P_OFFSET), '<Q', size), 'program header 5'),
            'a size outside the file': (with_field(MAPPED, header_field(RELRO, P_FILESZ), '<Q', size + 1), 'program header 5'),
            'a huge size': (with_field(MAPPED, header_field(RELRO, P_FILESZ), '<Q', 2 ** 64 - 1), 'program header 5'),
            'the headers outside the image': (short_image, 'outside the loaded image'),
            'the ELF header outside the image': (short_of_the_elf_header, 'outside the loaded image'),
            'a note header cut by the end of the file': (cut_at_the_end_of_the_file, 'overruns its segment'),
            'no build-id note': (mapped_file(elf_note(1, bytes(4))), '0 GNU build-id notes'),
            'two build-id notes': (mapped_file(BUILD_ID_NOTE + BUILD_ID_NOTE), '2 GNU build-id notes'),
            'one note in two segments': (same_note_twice, '2 GNU build-id notes'),
            'a descriptor that overruns': (mapped_file(struct.pack('<III', 4, 1000, 3) + b'GNU\0'), 'overruns its segment'),
            'a name that overruns': (mapped_file(struct.pack('<III', 1000, 0, 3) + b'GNU\0'), 'overruns its segment'),
            'a cut note header': (mapped_file(BUILD_ID_NOTE + bytes(4)), 'overruns its segment'),
            'a segment cut inside the note': (with_field(MAPPED, header_field(BUILD_ID_NOTES, P_FILESZ), '<Q', 20),
                                              'overruns its segment'),
            'another note alignment': (mapped_file(note_alignment=2), 'alignment 2'),
        }
        for name, (data, pattern) in cases.items():
            with self.subTest(name):
                self.assert_refused(data, pattern)

    def test_a_file_that_cannot_be_read_is_the_same_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(loaded_image.LoadedImageRefused, 'cannot be read'):
                loaded_image.loaded_sha256(pathlib.Path(folder) / 'missing')

    def test_running_the_file_prints_the_hash_or_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            good, bad = pathlib.Path(folder) / 'good', pathlib.Path(folder) / 'bad'
            good.write_bytes(MAPPED)
            bad.write_bytes(MAPPED[:4] + b'\x01' + MAPPED[5:])
            command = [sys.executable, '-I', str(ROOT / 'labwc/loaded_image.py')]
            result = subprocess.run([*command, str(good)], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, f'{loaded(MAPPED)}\n', ''))
            result = subprocess.run([*command, str(bad)], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout), (1, ''))
            self.assertRegex(result.stderr, r'^LOADED_IMAGE_REFUSED .*not ELF64\n$')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)

    def test_the_stage_compiles_the_function_from_its_source(self):
        real = (ROOT / 'labwc/loaded_image.py').read_bytes()
        stand_in = b"def loaded_sha256(path):\n    return 'stand-in'\n"
        with tempfile.TemporaryDirectory() as folder:
            source = pathlib.Path(folder) / 'loaded_image.py'
            shutil.copy(ROOT / 'labwc/stage.py', folder)
            source.write_bytes(stand_in.ljust(len(real), b'#'))
            os.utime(source, (1_000_000_000, 1_000_000_000))
            py_compile.compile(str(source), doraise=True, invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
            source.write_bytes(real)
            os.utime(source, (1_000_000_000, 1_000_000_000))
            # A normal import takes the planted bytecode: this is the trap the stage must not fall into.
            planted = importlib.util.spec_from_file_location('planted', source)
            module = importlib.util.module_from_spec(planted)
            planted.loader.exec_module(module)
            self.assertEqual(module.loaded_sha256('anything'), 'stand-in')
            copied = importlib.util.spec_from_file_location('copied_stage', pathlib.Path(folder) / 'stage.py')
            copy_of_stage = importlib.util.module_from_spec(copied)
            copied.loader.exec_module(copy_of_stage)
            binary = pathlib.Path(folder) / 'binary'
            binary.write_bytes(MAPPED)
            self.assertEqual(copy_of_stage.loaded_image_module().loaded_sha256(binary), loaded(MAPPED))

    def test_it_uses_the_standard_library_and_never_section_headers(self):
        text = (ROOT / 'labwc/loaded_image.py').read_text()
        self.assertEqual(sorted(re.findall(r'^import (\S+)$', text, re.M)), ['hashlib', 'pathlib', 'struct', 'sys'])
        self.assertEqual(re.findall(r'^from ', text, re.M), [])
        # e_shoff is only ever zeroed; e_shentsize (0x3a), e_shnum (0x3c) and e_shstrndx (0x3e) are never read.
        for offset in ('0x3a', '0x3c', '0x3e'):
            self.assertNotIn(offset, text)
        self.assertNotIn('unpack_from(\'<Q\', data, E_SHOFF', text)


class PinnedBinariesTest(StageCase):
    """311d: the labwc stage stops unless the RPM's own binaries match the lock."""
    def setUp(self):
        super().setUp()
        self.prepare_inputs()

    def assert_no_rpm_handed_over(self):
        self.assertFalse(self.out.exists() and any(self.out.iterdir()))

    def test_the_pinned_code_gives_the_rpm_and_prints_both_hashes(self):
        self.assertEqual(self.build(), 0, self.stderr)
        self.assertEqual([path.name for path in self.out.iterdir()], [f'{RESULT}.rpm'])
        self.assertIn(f'LABWC_NORMALIZED /usr/bin/labwc {normalized(LABWC_ELF)}\n', self.stdout)
        self.assertIn(f'LABWC_NORMALIZED /usr/bin/labnag {normalized(LABNAG_ELF)}\n', self.stdout)
        self.assertIn(f'LABWC_LOADED /usr/bin/labwc {loaded(LABWC_ELF)}\n', self.stdout)
        self.assertIn(f'LABWC_LOADED /usr/bin/labnag {loaded(LABNAG_ELF)}\n', self.stdout)

    def test_the_stage_finds_the_function_under_python_I(self):
        state_file = self.tmp / 'state.json'
        state_file.write_text(json.dumps(self.state))
        environment = dict(PATH=str(self.tools), FAKE_STATE=str(state_file), TMPDIR=str(self.tmp))
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'labwc/stage.py'), 'build', str(self.lock_dir),
                                 str(self.inputs), str(self.out)], env=environment, cwd=self.tmp, capture_output=True,
                                text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'LABWC_LOADED /usr/bin/labwc {loaded(LABWC_ELF)}\n', result.stdout)

    def test_the_hashes_come_from_the_rpm_that_was_built(self):
        self.assertEqual(self.build(), 0, self.stderr)
        calls = self.called('rpm2cpio')
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][-1].endswith(f'/rpmbuild/RPMS/x86_64/{RESULT}.rpm'), calls[0])
        names = [call[0] for call in self.state['calls']]
        self.assertLess(names.index('rpmbuild'), names.index('rpm2cpio'))

    def test_another_build_of_the_same_code_passes(self):
        self.state['payload']['usr/bin/labwc'] = elf_file(
            _text=b'\x90' * 16 + b'\xc3', _gnu_debugdata=b'\xfd7zXZ this build', _gnu_debuglink=b'b.debug\0\1\2\3\4',
            _note_gnu_build_id=struct.pack('<III', 4, 20, 3) + b'GNU\0' + bytes(range(50, 70))).hex()
        self.assertEqual(self.build(), 0, self.stderr)

    def test_a_wrong_pin_stops_the_build(self):
        for path, elf in (('/usr/bin/labwc', LABWC_ELF), ('/usr/bin/labnag', LABNAG_ELF)):
            with self.subTest(path):
                lock = copy.deepcopy(self.lock)
                lock['result']['normalized_sha256'][path] = 'a' * 64
                (self.lock_dir / 'labwc.lock.json').write_text(json.dumps(lock))
                self.assert_refused(self.build(), f'normalized SHA-256 of {path} is {normalized(elf)}, '
                                                  f'the lock says {"a" * 64}$')
                self.assert_no_rpm_handed_over()
                self.assertIn(f'LABWC_NORMALIZED {path} {normalized(elf)}\n', self.stdout)

    def test_a_wrong_loaded_pin_stops_the_build(self):
        for path, elf in (('/usr/bin/labwc', LABWC_ELF), ('/usr/bin/labnag', LABNAG_ELF)):
            with self.subTest(path):
                lock = copy.deepcopy(self.lock)
                lock['result']['loaded_sha256'][path] = 'a' * 64
                (self.lock_dir / 'labwc.lock.json').write_text(json.dumps(lock))
                self.assert_refused(self.build(), f'^LABWC_REFUSED the loaded SHA-256 of {path} is {loaded(elf)}, '
                                                  f'the lock says {"a" * 64}$')
                self.assert_no_rpm_handed_over()
                self.assertIn(f'LABWC_LOADED {path} {loaded(elf)}\n', self.stdout)

    def test_a_wrong_pin_of_each_kind_is_one_line_that_names_both(self):
        self.lock['result']['normalized_sha256']['/usr/bin/labwc'] = 'a' * 64
        self.lock['result']['loaded_sha256']['/usr/bin/labnag'] = 'b' * 64
        self.write_lock()
        self.assert_refused(self.build(), 'the normalized SHA-256 of /usr/bin/labwc is .*; '
                                          'the loaded SHA-256 of /usr/bin/labnag is ')
        self.assert_no_rpm_handed_over()

    def test_a_mapped_byte_the_normalized_pin_cannot_see_stops_the_build(self):
        # The gap 311e closes: objcopy writes sections, so padding inside a segment never reaches the normalized hash.
        padding = (field_of(LABWC_ELF, header_field(1, P_OFFSET), '<Q') +
                   field_of(LABWC_ELF, header_field(1, P_FILESZ), '<Q'))
        self.assertEqual(LABWC_ELF[padding], 0)
        edited = with_field(LABWC_ELF, padding, '<B', 0xcc)
        self.assertEqual(normalized(edited), normalized(LABWC_ELF))
        self.state['payload']['usr/bin/labwc'] = edited.hex()
        self.assert_refused(self.build(), f'^LABWC_REFUSED the loaded SHA-256 of /usr/bin/labwc is {loaded(edited)}, ')
        self.assert_no_rpm_handed_over()

    def test_a_file_the_function_refuses_stops_the_build(self):
        # PT_NOTE made PT_NULL: objcopy still reads the file, and the build-id note is gone from the program headers.
        no_note = with_field(LABWC_ELF, header_field(1, P_TYPE), '<I', PT_NULL)
        self.state['payload']['usr/bin/labwc'] = no_note.hex()
        self.assert_refused(self.build(), '^LABWC_REFUSED the loaded image of /usr/bin/labwc cannot be pinned: '
                                          'it holds 0 GNU build-id notes')
        self.assert_no_rpm_handed_over()

    def test_a_missing_function_stops_the_build(self):
        with mock.patch.object(stage, 'LOADED_IMAGE', 'no-such-file.py'):
            self.assert_refused(self.build(), 'no-such-file.py cannot be read')
        self.assert_no_rpm_handed_over()

    def test_two_wrong_pins_are_one_line_that_names_both(self):
        self.lock['result']['normalized_sha256'] = {'/usr/bin/labnag': 'a' * 64, '/usr/bin/labwc': 'b' * 64}
        self.write_lock()
        self.assert_refused(self.build(), '/usr/bin/labnag is .*; /usr/bin/labwc is ')

    def test_changed_code_stops_the_build(self):
        for member, key in (('usr/bin/labwc', '/usr/bin/labwc'), ('usr/bin/labnag', '/usr/bin/labnag')):
            with self.subTest(member):
                payload = dict(self.state['payload'])
                self.state['payload'][member] = elf_file(_rodata=b'unreviewed strings').hex()
                self.assert_refused(self.build(), f'normalized SHA-256 of {key} is ')
                self.assert_no_rpm_handed_over()
                self.state['payload'] = payload

    def test_a_refusal_never_renews_a_pin(self):
        self.lock['result']['normalized_sha256']['/usr/bin/labwc'] = 'a' * 64
        self.write_lock()
        before = (self.lock_dir / 'labwc.lock.json').read_bytes()
        self.assert_refused(self.build(), 'the lock says')
        self.assertEqual((self.lock_dir / 'labwc.lock.json').read_bytes(), before)

    def test_a_missing_binary_stops_the_build(self):
        del self.state['payload']['usr/bin/labnag']
        self.assert_refused(self.build(), 'the RPM holds no file /usr/bin/labnag')
        self.assert_no_rpm_handed_over()

    def test_a_payload_that_cannot_be_read_stops_the_build(self):
        for key in ('rpm2cpio_exit', 'cpio_exit'):
            with self.subTest(key):
                self.state[key] = 1
                self.assert_refused(self.build(), 'cannot be unpacked')
                self.assert_no_rpm_handed_over()
                self.state[key] = 0


class InstallInputsTest(StageCase):
    def run_script(self):
        state_file = self.tmp / 'state.json'
        state_file.write_text(json.dumps(self.state))
        (self.inputs / 'rpms').mkdir(parents=True)
        (self.inputs / 'rpms/one-1-1.fc44.x86_64.rpm').write_bytes(b'x')
        result = subprocess.run(['bash', str(ROOT / 'labwc/install-inputs.sh'), str(self.inputs)], capture_output=True,
                                text=True, env=dict(PATH=f'{self.tools}:/usr/bin:/bin', FAKE_STATE=str(state_file)))
        self.state = json.loads(state_file.read_text())
        return result

    def test_signatures_stay_on_and_repositories_off(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        install = self.called('dnf5', 'install')
        self.assertEqual(len(install), 1)
        self.assertIn('--disable-repo=*', install[0])
        self.assertIn('--setopt=localpkg_gpgcheck=True', install[0])
        self.assertIn('--setopt=install_weak_deps=False', install[0])

    def test_a_failed_install_is_one_clear_line(self):
        self.state['dnf_exit'] = 1
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertRegex(result.stderr, '^LABWC_REFUSED the locked build dependencies do not install')


class InstallTest(StageCase):
    def test_our_rpm_replaces_fedoras(self):
        self.assertEqual(self.install(), 0, self.stderr)
        self.assertEqual(sorted(self.state['installed']), sorted(['glibc-2.43-1.fc44.x86_64', RESULT, WLROOTS]))
        self.assertIn(f'LABWC_INSTALLED {RESULT} replaces {FEDORA}', self.stdout)

    def test_the_signature_exception_covers_this_one_file(self):
        self.assertEqual(self.install(), 0, self.stderr)
        install = self.called('dnf5', 'install')
        self.assertEqual(len(install), 1)
        self.assertIn('--setopt=localpkg_gpgcheck=False', install[0])
        self.assertIn('--disable-repo=*', install[0])
        self.assertEqual([arg for arg in install[0] if arg.endswith('.rpm')], [str(self.rpms / f'{RESULT}.rpm')])

    def test_the_manifest_lists_the_installed_packages_and_the_lock(self):
        self.assertEqual(self.install(), 0, self.stderr)
        self.assertEqual((self.manifest / 'packages.txt').read_text().splitlines(),
                         sorted(['glibc-2.43-1.fc44.x86_64', RESULT, WLROOTS]))
        self.assertEqual(json.loads((self.manifest / 'labwc.lock.json').read_text()), self.lock)

    def test_refuses_both_packages_present(self):
        self.state['labwc_query'] = [FEDORA, RESULT]
        # The first query is the one before the swap, which sees two as well.
        self.assert_refused(self.install(), "expected Fedora's")
        self.assertFalse(self.called('dnf5'))

    def test_refuses_both_packages_present_after_the_swap(self):
        self.state['dnf_removes'] = []
        self.assert_refused(self.install(), 'the lock says exactly')

    def test_refuses_another_labwc_after_the_swap(self):
        self.state['dnf_adds'] = ['labwc-0.9.7-1.fc44.x86_64']
        self.state['dnf_removes'] = [FEDORA]
        self.assert_refused(self.install(), r"installed labwc is \['labwc-0.9.7-1.fc44.x86_64'\]")

    def test_refuses_a_file_with_another_name(self):
        (self.rpms / f'{RESULT}.rpm').rename(self.rpms / 'labwc-0.9.7-1.fc44.x86_64.rpm')
        self.assert_refused(self.install(), f'must hold exactly {RESULT}.rpm')
        self.assertFalse(self.called('dnf5'))

    def test_refuses_a_second_file(self):
        (self.rpms / 'other-1-1.fc44.x86_64.rpm').write_bytes(b'x')
        self.assert_refused(self.install(), f'must hold exactly {RESULT}.rpm')
        self.assertFalse(self.called('dnf5'))

    def test_refuses_a_file_that_is_really_another_package(self):
        self.state['nevra_of'] = {f'{RESULT}.rpm': 'other-1-1.fc44.x86_64'}
        self.assert_refused(self.install(), 'is really other-1-1.fc44.x86_64')
        self.assertFalse(self.called('dnf5'))

    def test_refuses_a_base_without_fedoras_labwc(self):
        self.state['installed'] = ['glibc-2.43-1.fc44.x86_64', 'labwc-0.9.5-1.fc44.x86_64']
        self.assert_refused(self.install(), "expected Fedora's")
        self.assertFalse(self.called('dnf5'))

    def test_refuses_a_failed_install(self):
        self.state['dnf_exit'] = 1
        self.assert_refused(self.install(), 'did not install')

    def test_refuses_a_swap_that_changed_other_packages(self):
        self.state['dnf_adds'] = [RESULT, 'surprise-9-1.fc44.x86_64']
        self.assert_refused(self.install(), 'the swap changed other packages')

    def test_guard_1_refuses_an_image_with_another_wlroots_build(self):
        other = 'wlroots0.19-0.19.3-2.fc44.x86_64'
        self.state['installed'] = ['glibc-2.43-1.fc44.x86_64', FEDORA, other]
        self.assert_refused(self.install(), f'is not the same build as the image.s {other}')
        self.assertFalse(self.called('dnf5'))

    def test_guard_1_refuses_an_image_without_wlroots(self):
        self.state['installed'] = ['glibc-2.43-1.fc44.x86_64', FEDORA]
        self.assert_refused(self.install(), 'wlroots0.19')
        self.assertFalse(self.called('dnf5'))

    def test_guard_2_the_install_keeps_every_dependency_check(self):
        self.assertEqual(self.install(), 0, self.stderr)
        install = self.called('dnf5', 'install')[0]
        for shortcut in ('--nodeps', '--nodigest', '--nosignature', '--no-gpgchecks', '--skip-broken', '--skip-unavailable',
                         '--setopt=gpgcheck=False', '--setopt=pkg_gpgcheck=False'):
            self.assertNotIn(shortcut, install)
        self.assertEqual(self.called('rpm', '-i'), [])

    def test_guard_2_an_unmet_dependency_stops_the_swap(self):
        self.state['dnf_exit'] = 1
        self.assert_refused(self.install(), f'{RESULT} did not install')
        self.assertFalse((self.manifest / 'packages.txt').exists())

    def test_refuses_a_dirty_verify(self):
        self.state['verify_output'] = 'S.5....T.    /usr/bin/labwc\n'
        self.state['verify_exit'] = 1
        self.assert_refused(self.install(), 'rpm -V labwc is not clean')
        self.assertFalse((self.manifest / 'packages.txt').exists())


class ResolveTest(StageCase):
    def setUp(self):
        super().setUp()
        self.resolved = self.tmp / 'resolved'
        (self.resolved / 'downloads').mkdir(parents=True)
        (self.resolved / 'base-packages.txt').write_text('\n'.join(BUILD_BASE) + '\n')
        self.signed = {}
        for nevra, data in self.dependencies.items():
            self.add_download(nevra, data)

    def add_download(self, nevra, data):
        (self.resolved / 'downloads' / f'{nevra}.rpm').write_bytes(data)
        # The stand-in rpm reports every package as x86_64.
        url = f'{stage.KOJI}dep/1.0/1.fc44/data/signed/23456789/x86_64/{nevra}.rpm'
        self.state['urls'][url] = data.hex()
        self.signed[nevra] = url

    def resolve(self):
        return self.run_stage('resolve', self.lock_dir, self.resolved, self.tmp / 'evidence')

    def candidate(self):
        return json.loads((self.tmp / 'evidence/candidate-labwc.lock.json').read_text())

    def test_the_same_resolution_is_current(self):
        self.assertEqual(self.resolve(), 0, self.stderr)
        self.assertIn('LABWC_LOCK_CURRENT', self.stdout)
        self.assertEqual(self.candidate()['base'], self.lock['base'])

    def test_a_new_package_makes_a_valid_candidate(self):
        self.add_download('ccc-3-1.fc44.x86_64', b'fourth')
        self.assertEqual(self.resolve(), 0, self.stderr)
        self.assertIn('NEW ccc-3-1.fc44.x86_64', self.stdout)
        self.assertIn('LABWC_LOCK_DIFFERS', self.stdout)
        stage.validate_lock(self.candidate())

    def test_a_new_resolution_keeps_the_pins_and_says_how_they_are_renewed(self):
        self.add_download('ccc-3-1.fc44.x86_64', b'fourth')
        self.assertEqual(self.resolve(), 0, self.stderr)
        self.assertEqual(self.candidate()['result'], self.lock['result'])
        lines = self.stdout.splitlines()
        self.assertEqual(lines[-2], stage.PIN_RENEWAL)
        self.assertEqual(lines[-1], 'LABWC_LOCK_DIFFERS')
        for words in ('--no-cache --target labwc', 'twice', 'LABWC_NORMALIZED', 'LABWC_LOADED', 'by hand',
                      'result.normalized_sha256', 'result.loaded_sha256', 'no build ever writes either'):
            self.assertIn(words, stage.PIN_RENEWAL)

    def test_a_changed_base_is_reported_and_recorded(self):
        (self.resolved / 'base-packages.txt').write_text('bash-5.4-1.fc44.x86_64\nglibc-2.43-1.fc44.x86_64\n')
        self.assertEqual(self.resolve(), 0, self.stderr)
        self.assertIn('BASE_CHANGED', self.stdout)
        self.assertIn('LABWC_LOCK_DIFFERS', self.stdout)
        self.assertEqual(self.candidate()['base']['packages'], ['bash-5.4-1.fc44.x86_64', 'glibc-2.43-1.fc44.x86_64'])

    def test_guard_1_is_reported_for_a_fresh_resolution(self):
        self.write_image_packages('wlroots0.19-0.19.4-1.fc44.x86_64')
        self.assertEqual(self.resolve(), 0, self.stderr)
        self.assertIn('WLROOTS_DIFFERS', self.stdout)
        self.assertIn('LABWC_LOCK_DIFFERS', self.stdout)

    def test_a_package_koji_does_not_keep_is_reported(self):
        del self.state['urls'][self.signed['bbb-2.0-3.fc44.noarch']]
        self.assertEqual(self.resolve(), 0, self.stderr)
        self.assertIn('NOT_ON_KOJI bbb-2.0-3.fc44.noarch', self.stdout)
        self.assertIn('LABWC_LOCK_DIFFERS', self.stdout)

    def test_refuses_when_nothing_was_resolved(self):
        for path in (self.resolved / 'downloads').iterdir():
            path.unlink()
        self.assert_refused(self.resolve(), 'did not resolve on fedora:44')

    def test_refuses_when_the_base_was_not_listed(self):
        (self.resolved / 'base-packages.txt').unlink()
        self.assert_refused(self.resolve(), 'did not resolve on fedora:44')

    def test_an_epoch_is_not_part_of_the_koji_file_name(self):
        self.assertEqual(stage.file_name('xz-devel-1:5.8.2-2.fc44.x86_64'), 'xz-devel-5.8.2-2.fc44.x86_64.rpm')
        self.assertEqual(stage.file_name('gcc-16-1.fc44.x86_64'), 'gcc-16-1.fc44.x86_64.rpm')

    def test_the_koji_address_is_fedoras_signed_copy(self):
        state_file = self.tmp / 'state.json'
        state_file.write_text(json.dumps(self.state))
        with mock.patch.dict(os.environ, dict(PATH=str(self.tools), FAKE_STATE=str(state_file))):
            nevra, url = stage.koji_url('gcc-16-1.fc44.x86_64.rpm')
        self.assertEqual(nevra, 'gcc-16-1.fc44.x86_64')
        self.assertEqual(url, stage.KOJI + 'dep/1.0/1.fc44/data/signed/23456789/x86_64/gcc-16-1.fc44.x86_64.rpm')

    def test_refuses_an_unsigned_download(self):
        self.state['signature'] = '(none)'
        state_file = self.tmp / 'state.json'
        state_file.write_text(json.dumps(self.state))
        with mock.patch.dict(os.environ, dict(PATH=str(self.tools), FAKE_STATE=str(state_file))):
            with self.assertRaisesRegex(stage.Refusal, 'carries no Fedora signature'):
                stage.koji_url('gcc-16-1.fc44.x86_64.rpm')


class LockShapeTest(StageCase):
    def assert_shape_refused(self, change, pattern):
        lock = copy.deepcopy(self.lock)
        change(lock)
        with self.assertRaisesRegex(stage.Refusal, pattern):
            stage.validate_lock(lock)

    def test_the_fixture_is_valid(self):
        stage.validate_lock(self.lock)

    def test_refuses_each_wrong_shape(self):
        first = lambda lock: lock['build_dependencies'][0]
        cases = {
            'extra key': (lambda lock: lock.update(extra=1), 'expected exactly'),
            'base key': (lambda lock: lock['base'].update(extra=1), 'base needs exactly'),
            'tag instead of digest': (lambda lock: lock['base'].update(
                reference='registry.fedoraproject.org/fedora:44'), 'pinned by digest'),
            'other registry': (lambda lock: lock['base'].update(
                reference='docker.io/library/fedora@sha256:' + 'b' * 64), 'pinned by digest'),
            'no base packages': (lambda lock: lock['base'].update(packages=[]), 'base.packages must list'),
            'loose base package': (lambda lock: lock['base'].update(packages=['bash']), 'base.packages must list'),
            'base order': (lambda lock: lock['base']['packages'].reverse(), 'sorted and without repeats'),
            'no wlroots headers': (lambda lock: lock.update(build_dependencies=lock['build_dependencies'][:2]),
                                   'exactly one wlroots0.19-devel'),
            'source key': (lambda lock: lock['source'].update(name='x'), 'source needs exactly'),
            'source host': (lambda lock: lock['source'].update(url='https://example.com/a.src.rpm'), 'source.url'),
            'source hash': (lambda lock: lock['source'].update(sha256='abc'), 'source.sha256'),
            'patch path': (lambda lock: lock['patches'][1].update(file='../fix.patch'), 'patch.file'),
            'patch hash': (lambda lock: lock['patches'][1].update(sha256='ABC'), 'patch.sha256'),
            'patch key': (lambda lock: lock['patches'][0].update(name='x'), 'each patch needs exactly'),
            'no patches': (lambda lock: lock.update(patches=[]), 'patches must list every patch'),
            'one patch object, as before 321': (lambda lock: lock.update(patches=lock['patches'][0]),
                                                 'patches must list every patch'),
            'patch order': (lambda lock: lock['patches'].reverse(), 'in the order of their file names'),
            'a patch twice': (lambda lock: lock['patches'].append(dict(lock['patches'][1])),
                              'in the order of their file names'),
            'result': (lambda lock: lock['result'].update(nevra='labwc-0.9.6-1.fc44.x86_64'), 'result.nevra'),
            'replaces': (lambda lock: lock['result'].update(replaces='labwc-0.9.5-1.fc44.x86_64'), 'result.replaces'),
            'no pins': (lambda lock: lock['result'].pop('normalized_sha256'), 'result needs exactly'),
            'pins of one binary': (lambda lock: lock['result']['normalized_sha256'].pop('/usr/bin/labnag'),
                                   'normalized_sha256 needs exactly'),
            'a pin too many': (lambda lock: lock['result']['normalized_sha256'].update({'/usr/bin/other': 'a' * 64}),
                               'normalized_sha256 needs exactly'),
            'pin that is no hash': (lambda lock: lock['result']['normalized_sha256'].update({'/usr/bin/labwc': 'abc'}),
                                    'not a SHA-256'),
            'pins of another type': (lambda lock: lock['result'].update(normalized_sha256=['a' * 64]),
                                     'normalized_sha256 needs exactly'),
            'no loaded pins': (lambda lock: lock['result'].pop('loaded_sha256'), 'result needs exactly'),
            'loaded pins of one binary': (lambda lock: lock['result']['loaded_sha256'].pop('/usr/bin/labnag'),
                                          'loaded_sha256 needs exactly'),
            'a loaded pin too many': (lambda lock: lock['result']['loaded_sha256'].update({'/usr/bin/other': 'a' * 64}),
                                      'loaded_sha256 needs exactly'),
            'loaded pin that is no hash': (lambda lock: lock['result']['loaded_sha256'].update({'/usr/bin/labwc': 'abc'}),
                                           'loaded_sha256 holds something'),
            'loaded pins of another type': (lambda lock: lock['result'].update(loaded_sha256=['a' * 64]),
                                            'loaded_sha256 needs exactly'),
            'no dependencies': (lambda lock: lock.update(build_dependencies=[]), 'must list every'),
            'dependency key': (lambda lock: first(lock).update(extra=1), 'needs exactly nevra'),
            'loose name': (lambda lock: first(lock).update(nevra='gcc'), 'not an exact NEVRA'),
            'dependency host': (lambda lock: first(lock).update(url='https://example.com/x.rpm'), 'exact file on'),
            'other file': (lambda lock: first(lock).update(url=stage.KOJI + 'a/other.rpm'), 'exact file on'),
            'dependency hash': (lambda lock: first(lock).update(sha256='0'), 'not a SHA-256'),
            'order': (lambda lock: lock['build_dependencies'].reverse(), 'sorted and without repeats'),
            'repeat': (lambda lock: lock['build_dependencies'].append(lock['build_dependencies'][-1]),
                       'sorted and without repeats'),
        }
        for name, (change, pattern) in cases.items():
            with self.subTest(name):
                self.assert_shape_refused(change, pattern)

    def test_an_unreadable_lock_stops_the_build(self):
        (self.lock_dir / 'labwc.lock.json').write_text('{')
        self.assert_refused(self.build(), 'cannot be read')


class ReviewedLockTest(unittest.TestCase):
    """The lock in this repository."""
    def setUp(self):
        self.folder = ROOT / 'labwc'
        self.lock = stage.load_lock(self.folder)

    def test_it_names_fedoras_source_package(self):
        self.assertEqual(self.lock['source']['url'], 'https://kojipkgs.fedoraproject.org/packages/labwc/0.9.6/1.fc44/'
                                                     'src/labwc-0.9.6-1.fc44.src.rpm')

    def test_it_names_the_result(self):
        self.assertEqual((self.lock['result']['nevra'], self.lock['result']['replaces']), (RESULT, FEDORA))

    def test_it_pins_both_binaries_of_the_package(self):
        self.assertEqual(sorted(self.lock['result']['normalized_sha256']), ['/usr/bin/labnag', '/usr/bin/labwc'])
        self.assertEqual(sorted(self.lock['result']['loaded_sha256']), ['/usr/bin/labnag', '/usr/bin/labwc'])

    def test_it_names_both_patches_in_order_and_no_other_lies_beside_them(self):
        names = [patch['file'] for patch in self.lock['patches']]
        self.assertEqual(names, ['0001-allow-constraints-for-layer-surfaces.patch',
                                 '0002-no-bindings-for-the-capture-layer.patch'])
        self.assertEqual(sorted(path.name for path in self.folder.glob('*.patch')), names)

    def test_each_patch_is_its_pin(self):
        for entry in self.lock['patches']:
            patch = self.folder / entry['file']
            self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(), entry['sha256'], entry['file'])

    def test_the_first_patch_names_the_upstream_commit(self):
        text = (self.folder / self.lock['patches'][0]['file']).read_text()
        self.assertIn('b7820667a24787fdf88a79a006f716d78d7f4ccc', text.split('\n---\n')[0])

    def test_the_second_patch_gates_on_the_namespace_the_backend_gives_its_surface(self):
        # The backend cannot see this patch (321, step 1c): the two strings must stay the same string.
        patch = (self.folder / self.lock['patches'][1]['file']).read_text()
        defined = re.findall(r'^\+#define LAB_INHIBITING_LAYER_NAMESPACE "([^"]+)"$', patch, re.M)
        backend = (ROOT / 'input-portal/src/wayland/state.rs').read_text()
        used = re.findall(r'Layer::Overlay,\s*Some\("([^"]+)"\)', backend)
        self.assertEqual((defined, used), (['aresos-input-barrier'], ['aresos-input-barrier']))

    def test_the_second_patch_changes_code_only(self):
        # Every other file of the RPM stays Fedora's, byte for byte (R29's rule): no man page, no example file.
        patch = (self.folder / self.lock['patches'][1]['file']).read_text()
        touched = re.findall(r'^diff --git a/(\S+) ', patch, re.M)
        self.assertTrue(touched)
        self.assertEqual([path for path in touched if not path.startswith(('src/', 'include/'))], [])

    def test_every_dependency_is_a_signed_copy_on_koji(self):
        for entry in self.lock['build_dependencies']:
            self.assertRegex(entry['url'], r'^https://kojipkgs\.fedoraproject\.org/packages/[^/]+/[^/]+/[^/]+/'
                                           r'data/signed/[0-9a-f]{8}/(x86_64|noarch)/[^/]+\.rpm$')

    def test_guard_1_the_headers_are_the_wlroots_build_the_image_installs(self):
        stage.require_same_wlroots(self.lock, stage.image_wlroots(self.folder))

    def test_python_runs_the_stage_from_the_locked_packages(self):
        names = {stage.split_nevra(entry['nevra'])[0] for entry in self.lock['build_dependencies']}
        self.assertLessEqual({'python3', 'rpm-build', 'redhat-rpm-config', 'wlroots0.19-devel'}, names)

    def test_the_base_is_the_stage_that_builds(self):
        self.assertIn((self.lock['base']['reference'], 'labwc'),
                      re.findall(r'^FROM (\S+) AS (\S+)$', (ROOT / 'Containerfile').read_text(), re.M))

    def test_fedoras_labwc_stays_in_the_package_lock(self):
        # The packages stage installs Fedora's labwc and its dependencies before the swap.
        nevras = [entry['nevra'] for entry in json.loads((ROOT / 'packages.lock.json').read_text())['packages']]
        self.assertIn(FEDORA, nevras)


class WiringTest(unittest.TestCase):
    def setUp(self):
        self.containerfile = (ROOT / 'Containerfile').read_text()

    def stages(self):
        return re.findall(r'^FROM (\S+) AS (\S+)$', self.containerfile, re.M)

    def test_the_inputs_come_from_the_pinned_base(self):
        base = json.loads((ROOT / 'manifest/base.json').read_text())['reference']
        self.assertIn((base, 'labwc-inputs'), self.stages())

    def test_the_stage_is_on_a_digest_pinned_fedora(self):
        reference = dict((name, image) for image, name in self.stages())['labwc']
        self.assertRegex(reference, r'^registry\.fedoraproject\.org/fedora@sha256:[0-9a-f]{64}$')

    def test_the_stages_fetch_build_and_install(self):
        inputs = self.containerfile.split(' AS labwc-inputs\n')[1].split('\nFROM ')[0]
        self.assertIn('COPY packages.lock.json /tmp/aresos/packages.lock.json\n', inputs)
        self.assertIn('RUN python3 -I /tmp/aresos/labwc/stage.py fetch /tmp/aresos/labwc /inputs', inputs)
        section = self.containerfile.split(' AS labwc\n')[1].split('\nFROM ')[0]
        self.assertIn('COPY --from=labwc-inputs /inputs/ /tmp/aresos-labwc-inputs/\n', section)
        self.assertLess(section.index('install-inputs.sh /tmp/aresos-labwc-inputs'), section.index('stage.py build'))
        self.assertIn('stage.py build /tmp/aresos-labwc /tmp/aresos-labwc-inputs /out', section)
        packages = self.containerfile.split(' AS packages\n')[1].split('\nFROM ')[0]
        self.assertIn('COPY --from=labwc /out/ /tmp/aresos-labwc-rpm/\n', packages)
        # Both installs must land in the same layer even when their file metadata matches.
        instructions = packages.replace('\\\n', '').splitlines()
        install, = [line for line in instructions if line.startswith('RUN ')]
        self.assertIn('test ! -e /tmp/aresos/ci && bash /tmp/aresos/build.sh packages "$ARESOS_BUILD_KIND" &&', install)
        self.assertIn('test ! -e /tmp/aresos/input-portal &&', install)
        self.assertIn('python3 -I /tmp/aresos/labwc/stage.py install /tmp/aresos-labwc-rpm /tmp/aresos/labwc &&', install)
        self.assertLess(install.index('build.sh packages'), install.index('stage.py install'))

    def test_the_digest_check_reads_the_containerfile_before_any_dependency_is_installed(self):
        inputs = self.containerfile.split(' AS labwc-inputs\n')[1].split('\nFROM ')[0]
        # The lock folder's parent: where stage.py looks for it.
        self.assertLess(inputs.index('COPY Containerfile /tmp/aresos/Containerfile\n'), inputs.index('stage.py fetch'))
        ignored = (ROOT / '.containerignore').read_text().split('\n')
        self.assertFalse([rule for rule in ignored if rule and fnmatch.fnmatch('Containerfile', rule.rstrip('/'))])
        section = self.containerfile.split(' AS labwc\n')[1].split('\nFROM ')[0]
        # This COPY makes the labwc stage wait for the stage that holds the check.
        self.assertLess(section.index('COPY --from=labwc-inputs '), section.index('install-inputs.sh'))

    def test_guard_2_no_step_skips_a_check(self):
        for name in ('labwc/stage.py', 'labwc/install-inputs.sh', 'labwc/resolve-download.sh', 'Containerfile'):
            text = (ROOT / name).read_text()
            for shortcut in ('--nodeps', '--nodigest', '--no-gpgchecks', '--skip-broken', 'rpm -U', 'rpm -i '):
                self.assertNotIn(shortcut, text, name)

    def test_only_the_swap_turns_the_signature_check_off(self):
        self.assertEqual((ROOT / 'labwc/stage.py').read_text().count("'--setopt=localpkg_gpgcheck=False'"), 1)
        build = (ROOT / 'build.sh').read_text()
        self.assertNotIn('localpkg_gpgcheck=False', build)
        self.assertNotIn('gpgcheck=False', self.containerfile)
        self.assertIn('--setopt=localpkg_gpgcheck=True', build)

    def test_the_resolve_check_prints_a_fresh_resolution(self):
        text = (ROOT / 'ci/check-resolve.sh').read_text()
        self.assertIn('stage.py resolve /tmp/aresos/labwc /evidence/labwc-resolved "$out"', text)
        build = (ROOT / 'ci/check-build.sh').read_text().split('    resolve|resolve-deskflow-stable)\n')[1].split('\n        ;;')[0]
        self.assertIn('"$labwc_base" /tmp/aresos-labwc/resolve-download.sh', build)
        self.assertLess(build.index('/tmp/aresos-labwc/resolve-download.sh'), build.index('/tmp/aresos/ci/check-resolve.sh'))

    def test_the_image_checks_read_the_lock(self):
        text = (ROOT / 'ci/image-checks.sh').read_text()
        self.assertIn('test "$(rpm -q --qf \'%{NEVRA}\\n\' labwc)" = "$labwc_nevra"', text)
        self.assertIn('labwc_verify=$(rpm -V labwc)', text)
        self.assertIn("('labwc.lock.json', json.loads(pathlib.Path('os/labwc/labwc.lock.json').read_text()))",
                      (ROOT / 'ci/check-image.sh').read_text())


class ResolveDownloadTest(StageCase):
    def run_script(self, sha256):
        state_file = self.tmp / 'state.json'
        state_file.write_text(json.dumps(self.state))
        result = subprocess.run(['bash', str(ROOT / 'labwc/resolve-download.sh'), self.source_url, sha256,
                                 str(self.tmp / 'resolved')], capture_output=True, text=True,
                                env=dict(PATH=f'{self.tools}:/usr/bin:/bin', FAKE_STATE=str(state_file),
                                         TMPDIR=str(self.tmp)))
        self.state = json.loads(state_file.read_text())
        return result

    def test_refuses_a_wrong_source_hash(self):
        result = self.run_script('0' * 64)
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stderr, '^LABWC_REFUSED the source package differs from the lock')
        self.assertFalse(self.called('dnf5'))

    def test_refuses_a_failed_resolution(self):
        self.state['dnf_exit'] = 1
        result = self.run_script(digest(self.source_bytes))
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stderr, '^LABWC_REFUSED the build dependencies do not resolve')

    def test_asks_for_the_build_tools_and_the_spec_by_name(self):
        self.run_script(digest(self.source_bytes))
        call = self.called('dnf5', 'install')[0]
        self.assertIn('--downloadonly', call)
        self.assertLessEqual({'python3', 'rpm-build', 'redhat-rpm-config', 'gcc', 'meson'}, set(call))
        self.assertNotIn('rpmlib(CompressedFileNames)', call)


class RuntimeCheckTest(unittest.TestCase):
    """Guards 3 and 4: the real check from os/ci/image-checks.sh, against stand-ins for ldd and rpm."""
    GOOD = ('libwlroots-0.19.so()(64bit)', 'libc.so.6()(64bit)')

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.tmp = pathlib.Path(folder.name)
        source = (ROOT / 'ci/image-checks.sh').read_text()
        self.check = source.split("<<'LABWC_RUNTIME'\n", 1)[1].split('\nLABWC_RUNTIME\n', 1)[0]

    def run_check(self, ldd='\tlibc.so.6 => /usr/lib64/libc.so.6\n', ldd_exit=0, requires=GOOD, providers=None):
        providers = {name: ['glibc'] for name in requires} if providers is None else providers
        (self.tmp / 'data.json').write_text(json.dumps(dict(ldd=ldd, ldd_exit=ldd_exit, requires=list(requires),
                                                            providers=providers)))
        tool = (f'#!{sys.executable} -I\nimport json, pathlib, sys\n'
                f'data = json.loads(pathlib.Path({str(self.tmp / "data.json")!r}).read_text())\n'
                'if pathlib.Path(sys.argv[0]).name == "ldd":\n'
                '    sys.stdout.write(data["ldd"]); sys.exit(data["ldd_exit"])\n'
                'if "--whatprovides" in sys.argv:\n'
                '    found = data["providers"].get(sys.argv[-1], [])\n'
                '    print("\\n".join(found) if found else "no package provides " + sys.argv[-1])\n'
                '    sys.exit(0 if found else 1)\n'
                'print("\\n".join(data["requires"]))\n')
        for name in ('ldd', 'rpm'):
            (self.tmp / name).write_text(tool)
            (self.tmp / name).chmod(0o755)
        return subprocess.run([sys.executable, '-I', '-c', self.check], capture_output=True, text=True,
                              env=dict(PATH=str(self.tmp)))

    def assert_fails(self, result, pattern):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertRegex(result.stderr, 'LABWC_RUNTIME_FAILED ' + pattern)

    def test_a_complete_image_passes(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('LABWC_RUNTIME_OK 2 requirements', result.stdout)

    def test_rpmlib_entries_are_rpm_features(self):
        result = self.run_check(requires=[*self.GOOD, 'rpmlib(CompressedFileNames)'],
                                providers={name: ['glibc'] for name in self.GOOD})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_guard_3_a_missing_library_fails(self):
        self.assert_fails(self.run_check(ldd='\tlibwlroots-0.19.so => not found\n'), 'ldd exit 0, not found')

    def test_guard_3_a_failing_ldd_fails(self):
        self.assert_fails(self.run_check(ldd_exit=1), 'ldd exit 1')

    def test_guard_4_an_unprovided_requirement_fails(self):
        self.assert_fails(self.run_check(providers={self.GOOD[1]: ['glibc']}), 'no package of this image provides')

    def test_guard_4_labwc_cannot_provide_its_own_requirement(self):
        self.assert_fails(self.run_check(providers={self.GOOD[0]: ['labwc'], self.GOOD[1]: ['glibc']}),
                          'no package of this image provides')

    def test_guard_4_a_package_without_requires_fails(self):
        self.assert_fails(self.run_check(requires=()), 'cannot read the Requires')


if __name__ == '__main__':
    unittest.main()
