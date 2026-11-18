"""Package 311: the lock for our labwc rebuild, and every refusal of os/labwc/stage.py.

The stage's tools (curl, rpm, rpmbuild, dnf5) are stand-ins on PATH that act on a small state file, so nothing here
needs root, the network or a Fedora system.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('labwc_stage', ROOT / 'labwc/stage.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)

RESULT = 'labwc-0.9.6-1.fc44.aresos1.x86_64'
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
elif tool == 'rpmbuild':
    top = pathlib.Path(args[args.index('--define') + 1].split(' ', 1)[1])
    if state['build_exit']:
        code = state['build_exit']
    else:
        folder = top / 'RPMS/x86_64'
        folder.mkdir(parents=True)
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
        for name in ('curl', 'rpm', 'rpmbuild', 'dnf5'):
            (self.tools / name).symlink_to(program)

        self.lock_dir = self.tmp / 'labwc'
        self.lock_dir.mkdir()
        self.patch_bytes = b'the patch\n'
        (self.lock_dir / 'fix.patch').write_bytes(self.patch_bytes)
        self.source_url = stage.KOJI + 'labwc/0.9.6/1.fc44/src/labwc-0.9.6-1.fc44.src.rpm'
        self.source_bytes = b'source package'
        self.dependencies = {'aaa-devel-1.0-1.fc44.x86_64': b'first', 'bbb-2.0-3.fc44.noarch': b'second',
                             WLROOTS_DEVEL: b'third'}
        self.lock = dict(
            base=dict(reference=FEDORA_BASE, packages=BUILD_BASE),
            source=dict(url=self.source_url, sha256=digest(self.source_bytes)),
            patch=dict(file='fix.patch', sha256=digest(self.patch_bytes)),
            result=dict(nevra=RESULT, replaces=FEDORA),
            build_dependencies=[dict(nevra=nevra, url=self.dep_url(nevra), sha256=digest(data))
                                for nevra, data in sorted(self.dependencies.items())])
        self.write_lock()
        self.write_image_packages(WLROOTS)
        self.state = dict(
            calls=[], urls={self.source_url: self.source_bytes.hex(),
                            **{self.dep_url(n): data.hex() for n, data in self.dependencies.items()}},
            nevra_of={}, installed=list(BASE_PACKAGES), dnf_exit=0, dnf_adds=None, dnf_removes=None, build_exit=0,
            built=RESULT, spec=SPEC, verify_output='', verify_exit=0, labwc_query=None, fedora=FEDORA, result=RESULT,
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
        (self.lock_dir / 'fix.patch').write_bytes(b'another patch\n')
        self.assert_refused(self.fetch(), 'the patch has SHA-256')
        self.assertFalse(self.called('curl'))

    def test_refuses_a_missing_patch(self):
        (self.lock_dir / 'fix.patch').unlink()
        self.assert_refused(self.fetch(), 'the patch fix.patch is missing')

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

    def test_the_spec_edit_is_the_release_suffix_and_one_patch_line(self):
        spec_file = self.tmp / 'edited.spec'
        spec_file.write_text(SPEC)
        stage.edit_spec(spec_file, 'fix.patch')
        expected = SPEC.replace('Release:    %autorelease\n', 'Release:    %{autorelease}.aresos1\n').replace(
            'Source:     %{forgesource}\n', 'Source:     %{forgesource}\nPatch0:     fix.patch\n')
        self.assertEqual(spec_file.read_text(), expected)

    def test_refuses_a_wrong_source_hash(self):
        (self.inputs / stage.SOURCE_FILE).write_bytes(b'other source')
        self.assert_refused(self.build(), 'the source package has SHA-256')
        self.assertFalse(self.called('rpmbuild'))

    def test_refuses_a_missing_source(self):
        (self.inputs / stage.SOURCE_FILE).unlink()
        self.assert_refused(self.build(), 'the source package is missing')

    def test_refuses_a_wrong_patch_hash(self):
        (self.lock_dir / 'fix.patch').write_bytes(b'another patch\n')
        self.assert_refused(self.build(), 'the patch has SHA-256')
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
            'patch path': (lambda lock: lock['patch'].update(file='../fix.patch'), 'patch.file'),
            'patch hash': (lambda lock: lock['patch'].update(sha256='ABC'), 'patch.sha256'),
            'result': (lambda lock: lock['result'].update(nevra='labwc-0.9.6-1.fc44.x86_64'), 'result.nevra'),
            'replaces': (lambda lock: lock['result'].update(replaces='labwc-0.9.5-1.fc44.x86_64'), 'result.replaces'),
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
        self.assertEqual(self.lock['result'], dict(nevra=RESULT, replaces=FEDORA))

    def test_the_patch_is_its_pin(self):
        patch = self.folder / self.lock['patch']['file']
        self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(), self.lock['patch']['sha256'])

    def test_the_patch_names_the_upstream_commit(self):
        text = (self.folder / self.lock['patch']['file']).read_text()
        self.assertIn('b7820667a24787fdf88a79a006f716d78d7f4ccc', text.split('\n---\n')[0])

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
        # The packages stage still installs Fedora's labwc and its dependencies; the final stage swaps it.
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
        final = self.containerfile.split(' AS aresos\n')[1]
        self.assertIn('COPY --from=labwc /out/ /tmp/aresos-labwc-rpm/\n', final)
        swap = final.index('stage.py install /tmp/aresos-labwc-rpm /tmp/aresos/labwc')
        self.assertLess(swap, final.index('build.sh configure'))

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
        build = (ROOT / 'ci/check-build.sh').read_text().split('    resolve)\n')[1].split('\n        ;;')[0]
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
