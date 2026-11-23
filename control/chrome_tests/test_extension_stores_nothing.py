"""The extension keeps nothing in the browser (brief 18c-b, item 1).

Each image build signs the extension with a fresh key and throws the key away
(control/chrome/packaging/pack.py), so each image has its own extension ID.
Chrome removes the old extension and its stored data when the ID changes.
"""
import json
from pathlib import Path
import re
import unittest

EXTENSION = Path(__file__).resolve().parents[1] / 'chrome/extension'
STORES = re.compile(r'''chrome\s*\??\.\s*storage\b|\[\s*['"`]storage['"`]\s*\]|navigator\s*\??\.\s*storage\b|indexeddb|localstorage|sessionstorage''', re.IGNORECASE)
DECIDE_FIRST = ('The extension would start keeping data in the browser. Every AresOS image has its own extension identity, so Chrome '
                'drops that data at every update and when going back a version. This needs the owner\'s decision first '
                '(keeping data means keeping one identity, and so a signing key somewhere); see briefs/18c-b-chrome-image.md, '
                '"The design, as settled".')


class StoresNothing(unittest.TestCase):
    def test_the_sources_use_no_browser_storage(self):
        files = sorted(path for path in EXTENSION.rglob('*') if path.is_file())
        self.assertIn(EXTENSION / 'background.js', files)
        found = [f'{path.relative_to(EXTENSION)}:{number}: {match.group(0)}' for path in files
                 for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1)
                 for match in STORES.finditer(line)]
        self.assertEqual(found, [], DECIDE_FIRST)

    def test_the_manifest_asks_for_no_storage_permission(self):
        manifest = json.loads((EXTENSION / 'manifest.json').read_text())
        asked = set(manifest.get('permissions', [])) | set(manifest.get('optional_permissions', []))
        self.assertEqual(asked & {'storage', 'unlimitedStorage'}, set(), DECIDE_FIRST)

    def test_the_pin_sees_each_kind_of_storage(self):
        for line in ['await chrome.storage.local.set({a:1})', 'chrome?.storage.session.get()', "chrome['storage'].sync", 'indexedDB.open("x")',
                     'const db=self.IndexedDB', 'window.localStorage.setItem("a","b")', 'sessionStorage.getItem("a")', 'navigator.storage.persist()']:
            with self.subTest(line=line):
                self.assertIsNotNone(STORES.search(line))
        for line in ['chrome.tabs.query({})', 'const restored=state.storageKey', 'chrome.runtime.connectNative("org.aresos.chrome")']:
            with self.subTest(line=line):
                self.assertIsNone(STORES.search(line))


if __name__ == '__main__':
    unittest.main()
