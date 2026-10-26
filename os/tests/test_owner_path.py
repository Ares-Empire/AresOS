"""Walk the rendered owner navigation, including detours, without browser Back.

The gate is an explicit conditional instruction, not a runtime tool guarantee.
This checks documentation reachability; it cannot establish physical Windows
proof, human compliance, speed, firmware behavior or localized rendering.
"""
import collections
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


class OwnerPathTest(unittest.TestCase):
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
