import json
import hashlib
import pathlib
import re
import tempfile
import unittest

import test_owner_tools as common
import test_owner_walk as walk
import test_owner_entry as entry

ROOT = common.ROOT
OWNER_PAGES = ('INSTALL.md', 'INSTALL-PROCEDURES.md', 'INSTALL-REFERENCE.md',
               'INSTALL-RECORD.md', 'EMERGENCY.md', 'INSTALL-STATUS.md', 'OWNER-TOOLS.md')


PENDING = ROOT/'os/manifest/ci/16/pending-rebind.json'


def fingerprint_documents():
    documents={name:(ROOT/'docs'/name).read_text() for name in OWNER_PAGES}
    # Reports retain historical receipts. Each tools change replaces the
    # fingerprint the earlier reports gave (packages 14, 15, 15f, 22, 27, then
    # 22c), so those stay history, not rewritten. Package 22d's report joins
    # here when its record step writes it; until then OWNER-TOOLS.md is current.
    return documents


def unwalked_commands():
    """Owner commands added after the package 16 walk, typed by no rehearsal yet.

    Package 22's update commands need a newer signed release, which does not
    exist yet; the release package's rehearsal types them and empties this list.
    """
    return set(json.loads(PENDING.read_text()).get('unwalked_commands', []))


def check_bootstrap(guide, commands):
    """Both literal stick blocks (step 4 and the update route) are exactly what
    package 14's tamper tests run. Every other block that starts a shell with
    bash -c is one of the lines bootstrap.py generates (brief 22d: Claude's
    folder line and the routine lines), byte for byte, as commands.json holds it.
    Any prefix counts, not only sudo bash -c (review 1, F17): a changed copy is
    a block no test runs and refuses. Returns how many generated lines the guide
    quotes besides the stick blocks."""
    fingerprint=common.bundle.check(ROOT/'os/owner-tools/payload')
    bootstrap=common.module('bootstrap')
    expected=bootstrap.command(fingerprint).encode('utf-8')
    generated={name:line.encode('utf-8') for name,line in bootstrap.lines(fingerprint).items()}
    blocks=re.findall(rb'```bash\n(.*?)\n```',guide,re.S)
    shells=[block for block in blocks if b'bash -c' in block]
    stick=[block for block in shells if block.startswith(b'sudo bash -c ')]
    if stick != [expected, expected] or commands['install'].encode('utf-8') != expected or len(expected.splitlines()) != 13:
        raise AssertionError('Trusted bootstrap differs from the tested 13-line block')
    for name,line in generated.items():
        if name in commands and commands[name].encode('utf-8') != line:
            raise AssertionError('Trusted routine line differs from the generated one: '+name)
    others=[block for block in shells if block not in stick]
    if any(block not in generated.values() for block in others):
        raise AssertionError('Trusted routine line differs from the generated one in the guide')
    return len(others)


def check_fingerprints(documents, fingerprint):
    """Every current owner-page hash must have an identified current source.

    Image/media pins are distinct from the tools manifest. Checking all full
    hashes catches an extra stale copy even when the correct copy remains.
    Historical package-14 receipts stay superseded, not rewritten.
    """
    pins=set()
    for name in ('installer-isos.json','media-tools.json','release.json','releases/13.json','ci/11n/b-1/release.json'):
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
    outside = []
    for line in guide.splitlines():
        if line.lstrip().startswith('```'):
            fenced = not fenced
            outside.append('')
        else:
            outside.append('' if fenced else line)
    text = '\n'.join(outside)
    for match in re.finditer(r'(?<!`)`([^`]+)`(?!`)', text):
        code = match[1]
        words = code.split()
        first = words[1] if len(words) > 1 and words[0] == 'sudo' else words[0]
        if ('/var/lib/ares/at' in code or '/mnt/ares-tools/at' in code or first in verbs
                or words[:3] == ['sudo', 'bash', '-c'] or words[0].startswith('SUDO_ASKPASS=')
                or '/var/home/ares/ares-tools' in code):
            if code not in allowed:
                number = text[:match.start()].count('\n') + 1
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
        self.assertEqual(hashlib.sha256((ROOT/'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest(),fingerprint)
        self.assertIn('-I -B', (ROOT/'os/owner-tools/at').read_text())

    def test_bootstrap_is_byte_equal_to_the_block_exercised_by_package_14_tamper_tests(self):
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        guide=(ROOT/'docs/INSTALL.md').read_bytes()
        check_bootstrap(guide,commands)
        # Each mutation in each block that holds it: the two stick blocks, and the tools-only
        # routine line for the lines it shares with them.
        for before,after,copies in ((b'ro,nodev,nosuid,noexec',b'ro',2),
                                    (b'sha256sum -c --strict SHA256SUMS',b'true',3),
                                    (b'bash ./at install',b'bash ./at install ',3)):
            parts = guide.split(before)
            self.assertEqual(len(parts), copies+1)
            for index in range(copies):
                changed = before.join(parts[:index+1]) + after + before.join(parts[index+1:])
                with self.subTest(mutation=before, copy=index), self.assertRaisesRegex(AssertionError,'Trusted (bootstrap|routine line) differs'):
                    check_bootstrap(changed,commands)
        block = b'```bash\n' + commands['install'].encode('utf-8') + b'\n```'
        self.assertEqual(guide.count(block), 2)
        with self.assertRaisesRegex(AssertionError,'Trusted bootstrap differs'):
            check_bootstrap(guide.replace(block, b'', 1), commands)

    def test_every_generated_line_is_quoted_once_byte_equal_and_any_changed_copy_refuses(self):
        """Brief 22d: Claude's folder line, the tools-only routine line and the routine export line,
        each generated by bootstrap.py, held in commands.json and quoted once in the update route."""
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        guide=(ROOT/'docs/INSTALL.md').read_bytes()
        fingerprint=common.bundle.check(ROOT/'os/owner-tools/payload')
        generated=common.module('bootstrap').lines(fingerprint)
        self.assertEqual(check_bootstrap(guide,commands),len(generated))
        for name,line in generated.items():
            with self.subTest(line=name):
                self.assertEqual(commands[name],line)
                self.assertEqual(guide.count(b'```bash\n'+line.encode()+b'\n```'),1)
                with self.assertRaisesRegex(AssertionError,'Trusted routine line differs.*'+name):
                    check_bootstrap(guide,dict(commands,**{name:line+' '}))
                lines=line.encode().split(b'\n')
                for index in range(len(lines)):
                    changed=b'\n'.join(lines[:index]+[lines[index]+b' ']+lines[index+1:])
                    with self.subTest(line=name,index=index),self.assertRaisesRegex(AssertionError,'Trusted routine line differs'):
                        check_bootstrap(guide.replace(line.encode(),changed),commands)
        # F17: a block with the new prefix, or any other shell start, is pinned too.
        for extra in (b'SUDO_ASKPASS=/usr/bin/ksshaskpass /usr/bin/sudo -k -A -p x bash -c true',
                      b'/usr/bin/sudo bash -c true', b'sudo bash -c true'):
            with self.subTest(extra=extra),self.assertRaisesRegex(AssertionError,'Trusted (bootstrap|routine line) differs'):
                check_bootstrap(guide+b'\n```bash\n'+extra+b'\n```\n',commands)

    def test_owner_tools_page_is_exactly_the_payload_fingerprint_the_blocks_and_the_labels_carry(self):
        """Decision 5 (F3): line 1 is what he compares with the window on his phone."""
        fingerprint=common.bundle.check(ROOT/'os/owner-tools/payload')
        version=json.loads((ROOT/'os/owner-tools/history.json').read_text())['tools_version']
        page=(ROOT/'docs/OWNER-TOOLS.md').read_text().split('\n')
        self.assertEqual(page[:3],['Owner tools version '+str(version)+': '+fingerprint[:8],fingerprint,''])
        self.assertEqual(page[4:],[''])
        self.assertEqual(page[3].count('. '),1)
        self.assertTrue(page[3].endswith('.') and 'AresOS owner tools' in page[3])
        bootstrap=common.module('bootstrap')
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        literal='echo "'+fingerprint+'  SHA256SUMS" | sha256sum -c --strict'
        for name in ('install','tools-folder','tools-routine'):
            self.assertEqual(commands[name].count(literal),1,name)
        for name,action in bootstrap.ACTIONS.items():
            self.assertIn(" -p '"+bootstrap.label(fingerprint,action)+"' ",commands[name])
            self.assertTrue(bootstrap.label(fingerprint,action).startswith('AresOS owner tools '+page[0].rsplit(': ',1)[1]+': '))
        guide=(ROOT/'docs/INSTALL.md').read_text()
        self.assertIn('[OWNER-TOOLS.md](OWNER-TOOLS.md)',guide)

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
        result=walk.walk()
        # Package 27's update route types update and previous on top of the qualification;
        # package 22c's rehearsal (stage 2) types forward, from plain Bazzite and after previous.
        update=walk.walk(route='update')
        ways_back=walk.walk(route='ways-back')
        typed={text.rstrip('\n') for text,profile in result['visible_blocks']+update['visible_blocks']+ways_back['visible_blocks']}
        guide='\n'.join((ROOT/name).read_text() for name in
            ('docs/INSTALL.md', 'docs/INSTALL-PROCEDURES.md'))
        waiting=unwalked_commands()
        self.assertTrue(waiting <= set(commands), waiting)
        for name, command in commands.items():
            self.assertIn(command, guide)
            # A waiting command must not already be typed, so the list empties
            # as soon as a rehearsal walks it; every other one must be typed.
            if name in waiting:
                self.assertNotIn(command, typed)
            else:
                self.assertIn(command, typed)
        allowed=set(commands.values())
        for block in re.findall(r'```bash\n(.*?)\n```',guide,re.S):
            if block not in allowed:
                for line in block.splitlines(): self.assertIn(line, allowed)
        for run in (result, update, ways_back):
            self.assertEqual(sum(text.rstrip('\n')==commands['install'] for text,profile in run['visible_blocks']),1)
        self.assertIn(commands['forward'],{text.rstrip('\n') for text,profile in ways_back['visible_blocks']})
        self.assertIn('layout-reset-trial-QMP-system-reset',result['checks'])
        self.assertIn(commands['layout-abandon'],typed)
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
