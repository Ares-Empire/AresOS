import json
import pathlib
import re
import tempfile
import unittest

import test_owner_tools as common
import test_owner_walk as walk

ROOT = common.ROOT
OWNER_PAGES = ('INSTALL.md', 'INSTALL-PROCEDURES.md', 'INSTALL-REFERENCE.md',
               'INSTALL-RECORD.md', 'EMERGENCY.md', 'INSTALL-STATUS.md')


def check_inline_commands(guide, commands):
    """Inline code naming an owner invocation must be the complete command.

    Descriptive tool names stay in ordinary prose; PASS/output snippets and
    unrelated shell commands are not invocations. This conservative convention
    lets the check catch shorthand without guessing the author's intent.
    """
    allowed = set(commands.values())
    verbs = set(commands) | {'layout'}
    fenced = False
    for number, line in enumerate(guide.splitlines(), 1):
        if line.lstrip().startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        for code in re.findall(r'(?<!`)`([^`]+)`(?!`)', line):
            words = code.split()
            first = words[1] if len(words) > 1 and words[0] == 'sudo' else words[0]
            if '/var/lib/ares/at' in code or '/mnt/ares-tools/at' in code or first in verbs:
                if code not in allowed:
                    raise AssertionError(f'Noncanonical inline owner command at line {number}: {code}')


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
        typed={text.rstrip('\n') for text,profile in walk.walk()['typed']}
        guide='\n'.join((ROOT/name).read_text() for name in
            ('docs/INSTALL.md', 'docs/INSTALL-PROCEDURES.md'))
        for command in commands.values():
            self.assertIn(command, typed)
            self.assertIn(command, guide)
        allowed=set(commands.values())
        for block in re.findall(r'```bash\n(.*?)\n```',guide,re.S):
            for line in block.splitlines(): self.assertIn(line, allowed)
        for name in OWNER_PAGES:
            check_inline_commands((ROOT/'docs'/name).read_text(), commands)
        for name,source in common.bundle.PAYLOAD.items():
            self.assertEqual((ROOT/'os/owner-tools/payload'/name).read_bytes(), (ROOT/source).read_bytes())

    def test_bare_inline_reboot_mutation_is_rejected(self):
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        guide = (ROOT/'docs/INSTALL.md').read_text()
        correct = '`' + commands['reboot'] + '`'
        self.assertIn(correct, guide)
        mutated = guide.replace(correct, '`reboot`', 1)
        with self.assertRaisesRegex(AssertionError, 'Noncanonical inline owner command.*reboot'):
            check_inline_commands(mutated, commands)

    def test_inline_equality_covers_all_owner_verbs_and_rejects_extra_arguments(self):
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        for name, command in commands.items():
            with self.subTest(command=name):
                check_inline_commands('Run `' + command + '`.', commands)
                with self.assertRaisesRegex(AssertionError, 'Noncanonical inline owner command'):
                    check_inline_commands('Run `' + command + ' extra`.', commands)
                shorthand = 'layout proof' if name == 'layout-proof' else name
                with self.assertRaisesRegex(AssertionError, 'Noncanonical inline owner command'):
                    check_inline_commands('Then `' + shorthand + '`.', commands)

    def test_privileged_tool_refusals_never_offer_an_alternate_target(self):
        script=(ROOT/'os/owner-tools/owner.py').read_text()
        self.assertNotIn('GHCR_READ_TOKEN',script)
        self.assertIn("'--password-stdin'",script)
        self.assertNotIn('Authorization',script[script.index('class Tools:'):])
        self.assertIn("require(media.find(self.host, require) is None",script)
        self.assertNotIn('/var/lib/ares', (ROOT/'os/Containerfile.keyboard').read_text())


if __name__=='__main__': unittest.main()
