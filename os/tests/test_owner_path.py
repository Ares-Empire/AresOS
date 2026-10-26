"""Walk the rendered owner navigation, including detours, without browser Back.

The gate is an explicit conditional instruction, not a runtime tool guarantee.
This checks documentation reachability; it cannot establish physical Windows
proof, human compliance, speed, firmware behavior or localized rendering.
"""
import collections
import json
import pathlib
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = ('INSTALL.md', 'EMERGENCY.md', 'INSTALL-REFERENCE.md',
         'INSTALL-RECORD.md', 'INSTALL-PROCEDURES.md', 'INSTALL-STATUS.md')
STEP5 = '5-prove-windows-and-corrected-stock'
STEP6 = '6-switch-to-aresos'
GATE = ('**Entry gate: require STEP 5 COMPLETE and its evidence before '
        'authentication or switching. If absent, STOP')
MARKER = 'All checks PASS: write **STEP 5 COMPLETE**'
LINK = re.compile(r'(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)')
HEADING = re.compile(r'^#{1,6} (.+)$')


def links(text):
    definitions = dict(re.findall(r'^\[([^\]]+)\]:\s*(\S+)', text, re.M))
    definitions = {key.casefold(): value for key, value in definitions.items()}
    for i, line in enumerate(text.splitlines()):
        if re.match(r'^\[[^\]]+\]:', line):
            continue
        for url in LINK.findall(line):
            yield i, url
        for label, reference in re.findall(r'(?<!!)\[([^\]\n]+)\](?:\[([^\]\n]*)\])?(?!\()', line):
            name = (reference or label).casefold()
            if name in definitions:
                yield i, definitions[name]


def slug(text):
    # GitHub heading anchors retain Unicode, hyphens and underscores.
    return re.sub(r'[^\w\- ]', '', text.lower()).replace(' ', '-')


def anchors(text):
    found, seen = {}, collections.Counter()
    for number, line in enumerate(text.splitlines()):
        match = HEADING.match(line)
        if match:
            base = slug(match[1])
            name = base + (f'-{seen[base]}' if seen[base] else '')
            seen[base] += 1
            found[name] = number
        for name in re.findall(r'<a\s+(?:id|name)="([^"]+)"', line):
            if name in found:
                raise AssertionError('Duplicate anchor: ' + name)
            found[name] = number
    return found


def documents():
    return {name: (ROOT / 'docs' / name).read_text(encoding='utf-8') for name in PAGES}


def target(page, destination, texts):
    url = urlsplit(destination)
    if url.scheme or url.netloc:
        return None
    path = (ROOT / 'docs' / page).parent / unquote(url.path) if url.path else ROOT / 'docs' / page
    path = path.resolve()
    if not path.is_relative_to(ROOT) or not path.exists():
        raise AssertionError(f'Missing local target: {page}: {destination}')
    fragment = unquote(url.fragment)
    if fragment:
        if path.suffix != '.md':
            raise AssertionError('Unwalked non-Markdown fragment: ' + destination)
        available = anchors(path.read_text(encoding='utf-8')) if path.name not in texts else anchors(texts[path.name])
        if fragment not in available:
            raise AssertionError(f'Missing anchor: {page}: {destination}')
        number = available[fragment]
    else:
        number = 0
    if path.parent == ROOT / 'docs' and path.name in texts:
        return path.name, number
    # Source/evidence links are checked for existence, not treated as owner
    # execution routes. Do not follow historical guides as current procedures.
    return None


def walk(texts):
    lines = {name: text.splitlines() for name, text in texts.items()}
    guide = lines['INSTALL.md']
    gates = [i for i, line in enumerate(guide) if line.startswith(GATE)]
    markers = [i for i, line in enumerate(guide) if MARKER in line]
    if len(gates) != 1 or len(markers) != 1:
        raise AssertionError('Missing/ambiguous Windows gate or completion marker')
    gate, marker = gates[0], markers[0]
    sections = anchors(texts['INSTALL.md'])
    if not sections[STEP5] < marker < sections[STEP6] < gate:
        raise AssertionError('Windows proof must precede authentication gate')
    if target('INSTALL.md', '#' + STEP5, texts) not in [
            target('INSTALL.md', url, texts) for url in LINK.findall(guide[gate])]:
        raise AssertionError('Gate must explicitly return to step 5')

    edges = {}
    for page, content in lines.items():
        by_line = collections.defaultdict(list)
        for i, url in links(texts[page]):
            by_line[i].append(url)
        for i, line in enumerate(content):
            outgoing = [(page, i + 1)] if i + 1 < len(content) else []
            for url in by_line[i]:
                resolved = target(page, url, texts)
                if resolved:
                    outgoing.append(resolved)
            edges[page, i] = outgoing

    # Every symptom and later procedure is also a possible phone entry point.
    starts = [(page, 0) for page in texts]
    starts += [('EMERGENCY.md', i) for i, line in enumerate(lines['EMERGENCY.md']) if line.startswith('## ')]
    queue = collections.deque((node, False, ()) for node in starts)
    seen, traversed, sensitive = set(), set(), set()
    while queue:
        node, proof, route = queue.popleft()
        if (node, proof) in seen:
            continue
        seen.add((node, proof))
        page, i = node
        line = lines[page][i]
        route = (*route[-10:], f'{page}:{i + 1}')
        if re.search(r'^sudo /var/lib/ares/at (?:login|switch)$', line):
            if not proof:
                raise AssertionError('Authentication/switch bypasses step 5: ' + ' -> '.join(route))
            sensitive.add(line)
        if node == ('INSTALL.md', marker):
            proof = True
        outgoing = edges[node]
        if node == ('INSTALL.md', gate) and not proof:
            # Follow the visible conditional STOP return, not the success path.
            outgoing = [('INSTALL.md', sections[STEP5])]
        for destination in outgoing:
            traversed.add((node, destination))
            queue.append((destination, proof, route))
    if len(sensitive) != 2:
        raise AssertionError('Authentication and switch must both remain reachable after proof')
    for source, destinations in edges.items():
        for destination in destinations:
            if (source, destination) not in traversed:
                raise AssertionError(f'Unwalked owner edge: {source} -> {destination}')
    return len(seen), len(traversed)


def section(text, anchor):
    lines = text.splitlines()
    start = anchors(text)[anchor]
    level = len(lines[start].split(' ', 1)[0])
    end = next((i for i in range(start + 1, len(lines))
                if HEADING.match(lines[i]) and len(lines[i].split(' ', 1)[0]) <= level), len(lines))
    return '\n'.join(lines[start:end])


def check_context_returns(texts):
    """Resolve visible caller conditions, rather than exploring all links alike."""
    record = texts['INSTALL-RECORD.md']
    dispatch = section(record, 'return-by-calling-context')
    rows = {cells[0]: cells[1] for line in dispatch.splitlines() if line.startswith('| ')
            for cells in [[v.strip() for v in line.strip('|').split('|')]]}
    for anchor in ('b-compare-windows-after-each-stage', 'c-identify-both-drives-in-live-linux',
                   'd-before-erasing-crucial-from-live-media'):
        block = section(record, anchor)
        returns = [line for line in block.splitlines() if line.startswith('**Return by caller:**')]
        if len(returns) != 1 or '#return-by-calling-context' not in returns[0]:
            raise AssertionError('Record must dispatch by caller: ' + anchor)
        # The same after-aresos stage has different meanings for these callers.
        for caller, expected in (
                ('keep-stock', ('INSTALL-PROCEDURES.md', 'keep-stock-records-complete')),
                ('initial after-aresos', ('INSTALL.md', '7-check-the-first-aresos-session'))):
            destinations = LINK.findall(rows[caller])
            if len(destinations) != 1 or target('INSTALL-RECORD.md', destinations[0], texts) != (
                    expected[0], anchors(texts[expected[0]])[expected[1]]):
                raise AssertionError('Wrong record return for caller ' + caller + ': ' + anchor)
    completion = section(texts['INSTALL-PROCEDURES.md'], 'keep-stock-records-complete')
    if 'INSTALL.md#8-everyday-boot-and-recovery' not in completion or 'INSTALL.md#7-' in completion:
        raise AssertionError('Keep-stock completion must return to step 8')

    card = section(texts['EMERGENCY.md'], 'password-not-accepted')
    if 'INSTALL.md#5-' in card or 'INSTALL.md#7-' in card:
        raise AssertionError('AresOS layout recovery must not return to initial stock/AresOS checks')
    if 'INSTALL-PROCEDURES.md#layout-revert' not in card:
        raise AssertionError('Password failure must preserve the revert route')
    procedures = texts['INSTALL-PROCEDURES.md']
    reverted = section(procedures, 'layout-revert')
    proof = section(procedures, 'layout-recovery-proof')
    finished = section(procedures, 'layout-completion')
    if '#layout-recovery-proof' not in reverted or '#layout-completion' not in proof:
        raise AssertionError('Layout recovery must progress through proof/finish/completion')
    commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
    order = (commands['layout-proof'], 'PASS layout proof', commands['layout-finish'], 'PASS layout finish')
    positions = [proof.find(value) for value in order]
    if min(positions) < 0 or positions != sorted(positions):
        raise AssertionError('Layout recovery needs fresh proof then finish before completion')
    if commands['check'] not in finished or 'INSTALL.md#8-everyday-boot-and-recovery' not in finished:
        raise AssertionError('Completed AresOS layout must be checked then return to step 8')
    for block in (reverted, proof, finished):
        if 'INSTALL.md#5-' in block or 'INSTALL.md#7-' in block:
            raise AssertionError('Layout recovery must retain its AresOS context')


class OwnerPathTest(unittest.TestCase):
    def test_record_callers_and_aresos_layout_recovery_keep_their_state(self):
        check_context_returns(documents())

    def test_valid_links_to_the_wrong_operating_system_are_rejected(self):
        mutations = (
            ('INSTALL-RECORD.md',
             'keep-stock | [Return to keep-stock completion](INSTALL-PROCEDURES.md#keep-stock-records-complete)',
             'keep-stock | [Return to step 7](INSTALL.md#7-check-the-first-aresos-session)'),
            ('EMERGENCY.md',
             'and Return to [step 8](INSTALL.md#8-everyday-boot-and-recovery)',
             'and Return to [step 5](INSTALL.md#5-prove-windows-and-corrected-stock)'),
        )
        for page, before, after in mutations:
            texts = documents()
            self.assertIn(before, texts[page])
            texts[page] = texts[page].replace(before, after, 1)
            with self.subTest(page=page), self.assertRaisesRegex(AssertionError, 'Wrong record return|must not return'):
                check_context_returns(texts)

    def test_layout_recovery_cannot_skip_finish_even_with_valid_commands_and_links(self):
        texts = documents()
        start = texts['INSTALL-PROCEDURES.md'].index('### Layout recovery proof')
        head, tail = texts['INSTALL-PROCEDURES.md'][:start], texts['INSTALL-PROCEDURES.md'][start:]
        tail = tail.replace('sudo /var/lib/ares/at layout finish', 'sudo /var/lib/ares/at title', 1)
        texts['INSTALL-PROCEDURES.md'] = head + tail
        with self.assertRaisesRegex(AssertionError, 'fresh proof then finish'):
            check_context_returns(texts)

    def test_each_tool_restart_has_the_canonical_command_and_expected_result(self):
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        for page, text in documents().items():
            for match in re.finditer(re.escape(commands['reboot']), text):
                following = text[match.end():match.end() + 650]
                self.assertIn('PASS reboot', following, (page, match.start()))
                self.assertIn('Reboot requested; Windows stays default; F12 then Linux for one Linux start',
                              following, (page, match.start()))

    def test_battery_action_starts_with_live_power_safety_then_open_case(self):
        block = section(documents()['EMERGENCY.md'], 'battery-warning-sign')
        terms = ('stop using', 'external charger only if safe', 'hot or swollen case',
                 'flammable', 'Already open, battery disconnected', 'do not press', 'service clearance')
        positions = [block.lower().find(term.lower()) for term in terms]
        self.assertGreaterEqual(min(positions), 0)
        self.assertEqual(positions, sorted(positions))
        reference = section(documents()['INSTALL-REFERENCE.md'], 'battery-safety-sources')
        self.assertIn('loq_15_16/html_en/EN/read_first.html', reference)
        self.assertIn('generic_notices_class_b_en.pdf', reference)
        self.assertIn('lenovo_loq_hmm.pdf#page=9', reference)

    def test_boot_order_anomalies_stop_at_help_and_return_to_step_8(self):
        block = section(documents()['INSTALL.md'], '8-everyday-boot-and-recovery')
        for condition in ('Secure Boot changed', 'Windows recovery prompt',
                          'Missing internal boot entry while its SSD is attached'):
            line, = [line for line in block.splitlines() if condition in line]
            self.assertIn('STOP → [Help](INSTALL-REFERENCE.md#help)', line)
            self.assertIn('[Return to step 8](#8-everyday-boot-and-recovery)', line)

    def test_historical_results_cannot_be_read_as_current_release_qualification(self):
        text = documents()['INSTALL-STATUS.md']
        current = json.loads((ROOT/'os/manifest/release.json').read_text())['reference']
        historical = json.loads((ROOT/'os/manifest/ci/11n/b-1/release.json').read_text())['reference']
        self.assertNotEqual(current, historical)
        self.assertIn('**R06 (historical):** `' + historical + '`', text)
        self.assertIn('**R13 (current):** `' + current + '`', text)
        rows = [[v.strip() for v in line.strip('|').split('|')]
                for line in section(text, 'current-gates').splitlines() if line.startswith('| ')]
        for row in rows[2:]:
            self.assertEqual(len(row), 4)
            self.assertTrue(row[2], row[0])
            if row[0].startswith(('Historical signed', 'Live ISO installation', 'Revised boot timing')):
                self.assertEqual(row[2], '**R06 tested**')
            if row[0].startswith('Loaded layouts'):
                self.assertEqual(row[2], '**R13 tested — 13f only**')
                self.assertIn('no 11n-style manual GRUB/promotion qualification', row[3])

    def test_every_local_link_and_return_route_with_and_without_windows_proof(self):
        states, edges = walk(documents())
        self.assertGreater(states, 100)
        self.assertGreater(edges, 100)

    def test_regression_direct_link_below_gate_is_rejected(self):
        for reference_style in (False, True):
            texts = documents()
            texts['INSTALL.md'] = texts['INSTALL.md'].replace(
                '```bash\nsudo /var/lib/ares/at login\n',
                '### Authentication\n\n```bash\nsudo /var/lib/ares/at login\n', 1)
            if reference_style:
                texts['EMERGENCY.md'] = '[escape][bypass]\n' + texts['EMERGENCY.md'] + '\n[bypass]: INSTALL.md#authentication\n'
            else:
                texts['EMERGENCY.md'] = texts['EMERGENCY.md'].replace(
                    '(INSTALL-REFERENCE.md#help)', '(INSTALL.md#authentication)', 1)
            with self.subTest(reference_style=reference_style), self.assertRaisesRegex(AssertionError, 'bypasses step 5'):
                walk(texts)

    def test_missing_gate_and_marker_are_rejected(self):
        for literal in (GATE, MARKER):
            texts = documents()
            texts['INSTALL.md'] = texts['INSTALL.md'].replace(literal, 'REMOVED', 1)
            with self.assertRaisesRegex(AssertionError, 'Missing/ambiguous'):
                walk(texts)

    def test_symptoms_precede_preparation_and_first_actions_are_immediate(self):
        card = documents()['EMERGENCY.md']
        preparation = card.index('## References and preparation')
        symptoms = ('Frozen laptop', 'Failed first switch boot', 'Stale or missing stock title',
                    'Password not accepted', 'Text covers the prompt after stick hotplug or removal',
                    'Forgotten tools stick at power-on', 'Battery warning sign',
                    'Windows missing or not starting', 'Leaving AresOS permanently')
        self.assertNotIn('## ', card[:card.index('## ' + symptoms[0])])
        for symptom in symptoms:
            heading = '## ' + symptom + '\n'
            start = card.index(heading)
            self.assertLess(start, preparation)
            block = card[start + len(heading):].split('\n## ', 1)[0]
            action = next(i for i, line in enumerate(block.splitlines()) if line.startswith('**Action:**'))
            self.assertLessEqual(action, 2, symptom)
            self.assertIn('STOP → go to', block)
            self.assertRegex(block, r'(?i)return to .*\[step [1-9]\]')
        self.assertNotRegex(card[:preparation], r'(?i)qualification|probe[0-9]|audit count|ostree:[01]')

    def test_every_checklist_step_and_detour_supplies_stop_and_return(self):
        texts = documents()
        for block in re.split(r'^## [1-9]\. ', texts['INSTALL.md'], flags=re.M)[1:]:
            self.assertIn('STOP →', block)
            self.assertRegex(block, r'(?i)return to step [1-9]')
            self.assertIn('Record:', block)
        for page in ('INSTALL-REFERENCE.md', 'INSTALL-PROCEDURES.md'):
            for block in re.split(r'^## ', texts[page], flags=re.M)[1:]:
                self.assertRegex(block, r'(?i)return to (?:step|this|the)', page)

    def test_german_shortcuts_always_identify_strg_and_fn_variants_exist(self):
        for name, text in documents().items():
            for line in text.splitlines():
                if 'Ctrl+' in line:
                    self.assertIn('Ctrl = Strg', line, (name, line))
        console = documents()['INSTALL-REFERENCE.md'].split('## Console\n', 1)[1].split('\n## ', 1)[0]
        for key in ('F1', 'F2', 'F3', 'F4'):
            self.assertIn('Ctrl+Alt+Fn+' + key, console)
        self.assertIn('login:', console)
        self.assertIn('Fn+Esc', console)

    def test_retirement_covers_broken_linux_and_all_permanent_branches(self):
        texts = documents()
        retirement = texts['INSTALL.md'].split('## 9. ', 1)[1]
        for phrase in ('Linux cannot boot', 'stays installed', 'removed', 'erased',
                       'Settings → Developer settings → Personal access tokens → Tokens (classic)',
                       '**Delete**', 'fresh authentication/private pull', '2026-10-26',
                       'no deletion command'):
            self.assertIn(phrase, retirement)
        procedures = texts['INSTALL-PROCEDURES.md'].split('## Optional removal or erasure', 1)[1]
        self.assertLess(procedures.index('token retirement'), procedures.index('**Removal:**'))
        self.assertLess(procedures.index('token retirement'), procedures.index('**Erasure for reuse:**'))

    def test_status_history_is_centralized_and_physical_gates_stay_open(self):
        for name in ('INSTALL.md', 'EMERGENCY.md'):
            text = documents()[name]
            self.assertIn('INSTALL-STATUS.md#current-gates', text)
            self.assertNotIn('/actions/runs/', text)
            self.assertNotIn('40184846815', text)
        status = documents()['INSTALL-STATUS.md']
        for phrase in ('NOT RELEASED', 'FnLock states', 'Damaged-battery', 'Unaided-reader',
                       'Expendable-media', 'protected-second', 'not qualified protected-first',
                       'US-then-stock rollback was not run', '1 November'):
            self.assertIn(phrase, status)


if __name__ == '__main__':
    unittest.main()
