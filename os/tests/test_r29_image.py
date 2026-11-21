"""Package 323's resolve requests and image checks."""
import pathlib
import unittest

OS = pathlib.Path(__file__).resolve().parents[1]


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
