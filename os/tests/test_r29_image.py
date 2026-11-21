"""Package 323's resolve requests and image checks."""
import hashlib
import pathlib
import unittest

OS = pathlib.Path(__file__).resolve().parents[1]
IMAGE_CHECKS = (OS / 'ci/image-checks.sh').read_text()


class ResolveRequestsTest(unittest.TestCase):
    def test_layer_shell_is_in_all_four_resolve_commands(self):
        script = (OS / 'ci/check-resolve.sh').read_text().replace('\\\n', ' ')
        inventory = script.split('section packages\n', 1)[1].split('section filesystem', 1)[0]
        transaction = script.split('section transaction-preview\n', 1)[1].split('section available', 1)[0]
        available = script.split('section available\n', 1)[1].split('section existing-lock-availability', 1)[0]
        candidate = script.split('names=()\n', 1)[1].split('download --resolve', 1)[0]
        self.assertRegex(inventory, r'rpm -q [^\n]*\bgtk4-layer-shell\b')
        self.assertRegex(transaction, r'install --assumeno [^\n]*\bgtk4-layer-shell\b')
        self.assertRegex(available, r'repoquery [^\n]*\bgtk4-layer-shell\b')
        self.assertIn('names+=(gtk4-layer-shell)', candidate)
        self.assertIn('download --resolve --destdir=/tmp/ares-rpms "${names[@]}"', script)


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
