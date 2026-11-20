import json
import hashlib
import pathlib
import re
import tempfile
import unittest

import test_owner_tools as common
import test_owner_walk as walk
import test_owner_entry as entry
import release28_walk

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
    """Owner commands added after the package 16 walk, walked by no rehearsal yet.

    A rehearsal walks a command when its walk types it, or (package 22d's
    route) when its caller in the desktop session runs it. Each command leaves
    the list once a rehearsal walks it; package 22d's three lines left it in
    22d's step 7b, after run 43737933979 ran them.
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
    A source for a hash establishes provenance only.
    Historical package-14 receipts stay superseded, not rewritten.
    """
    pins=set()
    for name in ('installer-isos.json','media-tools.json','release.json','releases/13.json','ci/11n/b-1/release.json'):
        pins.update(re.findall(r'\b[0-9a-f]{64}\b',(ROOT/'os/manifest'/name).read_text()))
    laptop=json.loads(walk.R27_RECORD.read_text())['reference']
    seen=False
    for page,text in documents.items():
        if page == 'INSTALL-STATUS.md':
            # The package 22d evidence carries the laptop's exact installed fingerprint.
            retired = 'Tools fingerprint `' + release28_walk.TOOLS_V4 + '`'
            text = re.sub(r'(?m)^(\| Owner tools without the stick \(package 22d\) \|[^\n]+? \| )'
                          + re.escape(retired), r'\1', text, count=1)
            text = text.replace('- **R27 (on the laptop):** `' + laptop + '`', '', 1)
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

    def test_rehearsal_iso_is_absent_from_the_owner_route_and_the_install_hold_precedes_the_erase(self):
        records = json.loads((ROOT / 'os/manifest/installer-isos.json').read_text())
        live, = [row for row in records if row['kind'] == 'live']
        self.assertIs(live['rehearsal_only'], True)
        guide, reference, card = [
            (ROOT / 'docs' / name).read_text() for name in ('INSTALL.md', 'INSTALL-REFERENCE.md', 'EMERGENCY.md')
        ]
        for page in (guide, reference, card):
            self.assertNotIn('installer-isos.json', page)
            for key in ('sha256', 'filename', 'url', 'checksum_source'):
                self.assertNotIn(live[key], page)

        start, step2 = guide.split('## 2. Prepare and test the installer stick', 1)
        step2 = step2.split('## 3.', 1)[0]
        step4 = guide.split('## 4. Install and prepare corrected stock', 1)[1].split('## 5.', 1)[0]
        media = reference.split('## Media checksums', 1)[1]
        for section in (start, step2, step4, media, card):
            self.assertIn('Bazzite no longer publishes the installer this guide was checked with.', section)
            self.assertIn('new installer has been checked', section)
            self.assertIn('There is nothing to download or try now.', section)
        self.assertLess(step2.index('**STOP.**'), step2.index('**Schreiben**'))
        self.assertLess(step4.index('**STOP for a fresh install or reinstall.**'), step4.index('**Reinstall only'))
        self.assertIn('**Erase data and install** requires a newly checked installer and all PASS results.', step4)
        self.assertLess(card.index('**STOP before reinstalling.**'), card.index('**Use entire disk**'))

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
        """Decision 5 (F3): line 1 is what he compares with the window on his phone. A blank line keeps it
        apart from the full fingerprint there, since GitHub joins adjacent lines into one paragraph (review 2, N6)."""
        fingerprint=common.bundle.check(ROOT/'os/owner-tools/payload')
        version=json.loads((ROOT/'os/owner-tools/history.json').read_text())['tools_version']
        page=(ROOT/'docs/OWNER-TOOLS.md').read_text().split('\n')
        self.assertEqual(page[:4],['Owner tools version '+str(version)+': '+fingerprint[:8],'',fingerprint,''])
        self.assertEqual(page[5:],[''])
        self.assertEqual(page[4].count('. '),1)
        self.assertTrue(page[4].endswith('.') and 'AresOS owner tools' in page[4])
        bootstrap=common.module('bootstrap')
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        literal='echo "'+fingerprint+'  SHA256SUMS" | sha256sum -c --strict'
        for name in ('install','tools-folder','tools-routine'):
            self.assertEqual(commands[name].count(literal),1,name)
        for name,action in bootstrap.ACTIONS.items():
            self.assertIn(" -p '"+bootstrap.label(fingerprint,action)+"' ",commands[name])
            self.assertTrue(bootstrap.label(fingerprint,action).startswith('AresOS owner tools '+page[0].rsplit(': ',1)[1]+': '))
        # R4: the box prints the page's full address on main; he opens it from his own bookmark.
        guide=(ROOT/'docs/INSTALL.md').read_text()
        self.assertIn('`github.com/Ares-Empire/AresOS/blob/main/docs/OWNER-TOOLS.md`',guide)

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
        changed=dict(documents, **{'INSTALL-STATUS.md': documents['INSTALL-STATUS.md'] + '\n' + release28_walk.TOOLS_V4})
        with self.assertRaisesRegex(AssertionError,'Stale tools fingerprint'):
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
        # The desktop caller reads the new folder and routine lines from package 42's announced commit.
        announced=walk.walk(route='release-28')['local']
        ran=set(announced.ran['r28-tools'].values())
        # The export path was walked by 22d. Its only input that moves with the payload is the label's fingerprint.
        local=walk.walk(route='tools-local')['local']
        exported=local.lines('tl-export')['routine']
        self.assertIn(release28_walk.TOOLS_V4[:8], exported)
        fingerprint=common.bundle.check(ROOT/'os/owner-tools/payload')
        ran.add(exported.replace(release28_walk.TOOLS_V4[:8], fingerprint[:8], 1))
        guide='\n'.join((ROOT/name).read_text() for name in
            ('docs/INSTALL.md', 'docs/INSTALL-PROCEDURES.md'))
        waiting=unwalked_commands()
        self.assertTrue(waiting <= set(commands), waiting)
        for name, command in commands.items():
            self.assertIn(command, guide)
            # A waiting command must not already be walked (typed, or run by
                # the desktop caller), so the list empties as soon as a rehearsal walks
            # it; every other one must be walked.
            if name in waiting:
                self.assertNotIn(command, typed|ran)
            else:
                self.assertIn(command, typed|ran)
        allowed=set(commands.values())
        for block in re.findall(r'```bash\n(.*?)\n```',guide,re.S):
            if block not in allowed:
                for line in block.splitlines(): self.assertIn(line, allowed)
        from tools_local import V3_COMMIT
        for run, install in ((result, commands['install']),
                             (update, json.loads(walk.vm.git_blob(walk.vm.TOOLS_V2_COMMIT, 'os/owner-tools/commands.json'))['install']),
                             (ways_back, json.loads(walk.vm.git_blob(V3_COMMIT, 'os/owner-tools/commands.json'))['install'])):
            self.assertEqual(sum(text.rstrip('\n')==install for text,profile in run['visible_blocks']),1)
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
