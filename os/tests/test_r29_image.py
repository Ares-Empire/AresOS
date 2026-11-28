"""Package 323's resolve requests and image checks."""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

OS = pathlib.Path(__file__).resolve().parents[1]
IMAGE_CHECKS = (OS / 'ci/image-checks.sh').read_text()


class ResolveRequestsTest(unittest.TestCase):
    def test_layer_shell_is_in_all_four_resolve_commands(self):
        script = (OS / 'ci/check-resolve.sh').read_text().replace('\\\n', ' ')
        inventory = script.split('section packages\n', 1)[1].split('section filesystem', 1)[0]
        transaction = script.split('section transaction-preview\n', 1)[1].split('section available', 1)[0]
        available = script.split('section available\n', 1)[1].split('section existing-lock-availability', 1)[0]
        candidate = script.split('names=()\n', 1)[1].split('resolve_deskflow_candidate', 1)[0]
        self.assertRegex(inventory, r'rpm -q [^\n]*\bgtk4-layer-shell\b')
        self.assertRegex(transaction, r'install --assumeno [^\n]*\bgtk4-layer-shell\b')
        self.assertRegex(available, r'repoquery [^\n]*\bgtk4-layer-shell\b')
        self.assertIn('names+=(gtk4-layer-shell.x86_64)', candidate)
        self.assertIn('resolve_deskflow_candidate "$mode" /tmp/ares-rpms "${names[@]}"', script)


class JetBrainsMonoTest(unittest.TestCase):
    FONT_DIR = '/usr/share/fonts/aresos'
    HASHES = {
        'JetBrainsMono-Variable.ttf': '48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda',
        'OFL-JetBrainsMono.txt': 'b2fe5e8987594e9ffd1d2ca52a2f5d73eb8335243893c5d6254b5ad69269591d',
    }

    def test_the_image_checks_pin_the_copied_font_and_licence(self):
        pins = IMAGE_CHECKS.split("sha256sum -c <<'JETBRAINS_MONO_SHA256'\n", 1)[1].split('\nJETBRAINS_MONO_SHA256', 1)[0]
        self.assertEqual(pins.splitlines(), [f'{digest}  {self.FONT_DIR}/{name}' for name, digest in self.HASHES.items()])
        for name, digest in self.HASHES.items():
            with self.subTest(name=name):
                path = OS / 'config' / self.FONT_DIR.lstrip('/') / name
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_fontconfig_must_choose_our_font_as_the_everyday_user(self):
        self.assertIn("font=$(runuser -u ares -- env -i HOME=/tmp PATH=/usr/bin /usr/bin/fc-match "
                      "--format '%{file}' 'JetBrains Mono')\n"
                      f'test "$font" = {self.FONT_DIR}/JetBrainsMono-Variable.ttf', IMAGE_CHECKS)


class LayerShellCheckTest(unittest.TestCase):
    def test_the_image_checks_the_pin_and_preloads_the_library_for_laptop_home(self):
        self.assertIn("layer_nevra=$(python3 -I - /usr/share/aresos/manifest/packages.lock.json <<'LAYER_NEVRA'",
                      IMAGE_CHECKS)
        self.assertIn('test "$(rpm -q --qf \'%{NEVRA}\\n\' gtk4-layer-shell)" = "$layer_nevra"', IMAGE_CHECKS)
        self.assertIn('layer_verify=$(rpm -V gtk4-layer-shell)\ntest -z "$layer_verify"', IMAGE_CHECKS)
        self.assertIn('layer_library=/usr/lib64/libgtk4-layer-shell.so.0\ntest -f "$layer_library"', IMAGE_CHECKS)
        self.assertIn('runuser -u ares -- env -i HOME=/tmp PATH=/usr/bin LD_PRELOAD="$layer_library" '
                      "/usr/bin/python3 - <<'LAPTOP_HOME_LAYER'", IMAGE_CHECKS)
        body = IMAGE_CHECKS.split("<<'LAPTOP_HOME_LAYER'\n", 1)[1].split('\nLAPTOP_HOME_LAYER\n', 1)[0]
        self.assertIn("SourceFileLoader('aresos_laptop_home', '/usr/libexec/aresos-laptop-home')", body)
        self.assertIn('layer = home.load_gui().layer\nassert layer is not None', body)


class DriverManifestCheckTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        body = IMAGE_CHECKS.split("<<'DRIVER_MANIFESTS'\n", 1)[1].split('\nDRIVER_MANIFESTS\n', 1)[0]
        self.check = compile(body, 'image-checks.sh DRIVER_MANIFESTS', 'exec')

    def check_manifests(self, libraries, cache=''):
        manifests = []
        for index, library in enumerate(libraries):
            manifest = self.root / f'icd-{index}.json'
            manifest.write_text(json.dumps({'ICD': {'library_path': str(library)}}))
            manifests.append(str(manifest))
        with mock.patch.object(sys, 'argv', ['-', *manifests]), \
                mock.patch('subprocess.check_output', return_value=cache) as ldconfig, \
                mock.patch('builtins.print'):
            exec(self.check, {})
        return ldconfig

    def test_the_image_checks_both_regular_package_owned_manifests(self):
        self.assertIn('mesa_egl=/usr/share/glvnd/egl_vendor.d/50_mesa.json\n'
                      'intel_vulkan=/usr/share/vulkan/icd.d/intel_icd.x86_64.json\n'
                      'for manifest in "$mesa_egl" "$intel_vulkan"; do\n'
                      '    test -f "$manifest"\n'
                      '    test ! -L "$manifest"\n'
                      '    rpm -qf "$manifest"\n'
                      'done\n'
                      'python3 -I - "$mesa_egl" "$intel_vulkan" <<\'DRIVER_MANIFESTS\'', IMAGE_CHECKS)

    def test_absolute_library_is_checked_directly(self):
        library = self.root / 'libEGL_mesa.so.0'
        with self.assertRaisesRegex(AssertionError, 'missing library'):
            self.check_manifests([library])
        library.touch()
        self.check_manifests([library]).assert_not_called()

    def test_soname_requires_an_existing_x86_64_cache_entry(self):
        soname = 'libvulkan_intel.so'
        library = self.root / soname
        library.touch()
        cache = (f'\t{soname} (libc6) => {library}\n'
                 f'\t{soname} (libc6,x86-64) => {self.root / "missing.so"}\n')
        with self.assertRaisesRegex(AssertionError, 'missing library'):
            self.check_manifests([soname], cache)
        cache += f'\t{soname} (libc6,x86-64, hwcap: "x86-64-v3") => {library}\n'
        self.check_manifests([soname], cache).assert_called_once_with(['ldconfig', '-p'], text=True)

    def test_relative_library_path_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'expected an absolute library path or soname'):
            self.check_manifests(['drivers/libvulkan_intel.so'])


class PackageLockTest(unittest.TestCase):
    """The R29 candidate plus the two RPMs reviewed for B321."""
    RUN = OS.parent / 'reviews/323-r29-image/runs/resolve-44912634031/candidate-packages.lock.json'

    def test_the_lock_is_the_resolved_candidate_in_its_order(self):
        lock = json.loads((OS / 'packages.lock.json').read_text())
        expected = json.loads(self.RUN.read_text())
        expected['packages'].extend([
            {'nevra': 'deskflow-1.27.0-1.fc44.x86_64',
             'sha256': '21a404d8bd0488fdc7ec635ed26447d623b132dc4ae3d12e5f944991ab76484b'},
            {'nevra': 'libportal-0.10.0-1.fc44.x86_64',
             'sha256': 'bd56170a54a8b8a397fb06c7ad4b07b3cae480449d6fdbb471973941f75031cb'},
        ])
        expected['packages'].sort(key=lambda package: package['nevra'])
        self.assertEqual(lock, expected)

    def test_only_the_x86_64_layer_library_is_pinned(self):
        pinned = [p for p in json.loads((OS / 'packages.lock.json').read_text())['packages']
                  if p['nevra'].rsplit('-', 2)[0] == 'gtk4-layer-shell']
        self.assertEqual(pinned, [{'nevra': 'gtk4-layer-shell-1.3.0-1.fc44.x86_64',
                                   'sha256': '9dd6c2bfc53b9dd1a7a03c9c18f381dcbd350a0abd692a9cae7377d658f852a1'}])
