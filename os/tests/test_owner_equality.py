import json
import pathlib
import re
import tempfile
import unittest

import test_owner_tools as common
import test_owner_walk as walk

ROOT = common.ROOT


class EqualityTest(unittest.TestCase):
    def test_package_hash_manifests_put_hashes_before_paths(self):
        def check(value):
            if isinstance(value, list):
                for row in value: check(row)
            elif isinstance(value, dict):
                hashes = [key for key in value if key.endswith('sha256')]
                names = [key for key in value if key in ('path', 'file', 'member', 'archive', 'url', 'log')]
                for digest in hashes:
                    for name in names: self.assertLess(list(value).index(digest), list(value).index(name))
                self.assertFalse(value and all(isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v)
                                               for v in value.values()), 'Old path-to-hash map')
                for child in value.values(): check(child)
        for folder in ('os/manifest/ci/14', 'os/tests/fixtures/owner-tools', 'os/owner-tools/payload'):
            for path in (ROOT/folder).rglob('*.json'):
                if not path.name.startswith('qapi_'): check(json.loads(path.read_text()))

    def test_reviewed_windows_payload_is_exact_generated_ci_payload(self):
        fingerprint = common.bundle.check(ROOT/'os/owner-tools/payload')
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary:
            other=pathlib.Path(temporary)/'payload'
            self.assertEqual(common.bundle.build(other), fingerprint)
            self.assertEqual(common.owner.checked_bundle(other), fingerprint)
        self.assertIn(fingerprint, (ROOT/'docs/INSTALL.md').read_text())
        self.assertIn('-I -B', (ROOT/'os/owner-tools/at').read_text())

    def test_every_owner_command_equals_the_command_physically_typed_by_ci(self):
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        result=walk.walk()
        typed={text.rstrip('\n') for text,profile in result['visible_blocks']}
        guide=(ROOT/'docs/INSTALL.md').read_text()
        for command in commands.values():
            self.assertIn(command, typed)
            self.assertIn(command, guide)
        allowed=set(commands.values())
        for block in re.findall(r'```bash\n(.*?)\n```',guide,re.S):
            if block not in allowed:
                for line in block.splitlines(): self.assertIn(line, allowed)
        self.assertEqual(sum(text.rstrip('\n')==commands['install'] for text,profile in result['visible_blocks']),1)
        self.assertIn('layout-reset-trial-QMP-system-reset',result['checks'])
        self.assertIn(commands['layout-abandon'],typed)
        for name,source in common.bundle.PAYLOAD.items():
            self.assertEqual((ROOT/'os/owner-tools/payload'/name).read_bytes(), (ROOT/source).read_bytes())

    def test_privileged_tool_refusals_never_offer_an_alternate_target(self):
        script=(ROOT/'os/owner-tools/owner.py').read_text()
        self.assertNotIn('GHCR_READ_TOKEN',script)
        self.assertIn("'--password-stdin'",script)
        self.assertNotIn('Authorization',script[script.index('class Tools:'):])
        self.assertIn("require(media.find(self.host, require) is None",script)
        self.assertNotIn('/var/lib/ares', (ROOT/'os/Containerfile.keyboard').read_text())


if __name__=='__main__': unittest.main()
