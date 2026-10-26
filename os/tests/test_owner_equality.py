import json
import pathlib
import re
import tempfile
import unittest

import test_owner_tools as common
import test_owner_walk as walk
import test_owner_entry as entry

ROOT = common.ROOT
OWNER_PAGES = ('INSTALL.md', 'INSTALL-PROCEDURES.md', 'INSTALL-REFERENCE.md',
               'INSTALL-RECORD.md', 'EMERGENCY.md', 'INSTALL-STATUS.md')


def fingerprint_documents():
    documents={name:(ROOT/'docs'/name).read_text() for name in OWNER_PAGES}
    # Reports explicitly retain historical receipts below their current delta.
    # Check the live sections without rewriting those superseded fingerprints.
    for package,boundary in (('14-owner-tools','## 14m '),('15-owner-path','## 15b ')):
        documents[package+' current report']=(ROOT/'reviews'/package/'REPORT.md').read_text().split(boundary,1)[0]
    return documents


def check_fingerprints(documents, fingerprint):
    """Every current owner-page hash must have an identified current source.

    Image/media pins are distinct from the tools manifest. Checking all full
    hashes catches an extra stale copy even when the correct copy remains.
    Historical package-14 receipts stay superseded, not rewritten.
    """
    pins=set()
    for name in ('installer-isos.json','media-tools.json','release.json','ci/11n/b-1/release.json'):
        pins.update(re.findall(r'\b[0-9a-f]{64}\b',(ROOT/'os/manifest'/name).read_text()))
    seen=False
    for page,text in documents.items():
        for value in re.findall(r'\b[0-9a-f]{64}\b',text):
            if value not in pins | {fingerprint}:
                raise AssertionError(f'Stale tools fingerprint or unbound hash in {page}: {value}')
            seen |= value == fingerprint
        for value in re.findall(r'PASS tools manifest SHA256 ([0-9a-f]{64})',text):
            if value != fingerprint:
                raise AssertionError('Stale tools fingerprint in '+page)
    if not seen:
        raise AssertionError('Missing current tools fingerprint')


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
        check_fingerprints(fingerprint_documents(),fingerprint)
        inventory=json.loads((ROOT/'os/manifest/ci/14/14n-replay/fingerprint-references.json').read_text())
        self.assertEqual(inventory['current']['sha256'],fingerprint)
        self.assertIn('-I -B', (ROOT/'os/owner-tools/at').read_text())

    def test_extra_stale_fingerprint_is_rejected_in_every_owner_page(self):
        fingerprint=common.bundle.check(ROOT/'os/owner-tools/payload')
        documents=fingerprint_documents()
        stale=json.loads((ROOT/'os/manifest/ci/14/14n-replay/fingerprint-references.json').read_text())['retired']['value']
        self.assertNotEqual(stale,fingerprint)
        for page in documents:
            changed=dict(documents)
            changed[page]+='\nTools manifest fingerprint: `'+stale+'`.\n'
            with self.subTest(page=page), self.assertRaisesRegex(AssertionError,'Stale tools fingerprint'):
                check_fingerprints(changed,fingerprint)
        changed=dict(documents)
        wrong=json.loads((ROOT/'os/manifest/media-tools.json').read_text())['writer']['sha256']
        changed['INSTALL.md']=changed['INSTALL.md'].replace(fingerprint,wrong)
        with self.assertRaisesRegex(AssertionError,'Stale tools fingerprint'):
            check_fingerprints(changed,fingerprint)

    def test_every_documented_owner_pass_equals_captured_entry_stdout(self):
        entry.check_documented_pass_lines({name:(ROOT/'docs'/name).read_text() for name in entry.OWNER_PAGES})

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
