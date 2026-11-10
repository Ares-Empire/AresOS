"""Walk the rendered owner navigation, including detours, without browser Back.

The gate is an explicit conditional instruction, not a runtime tool guarantee.
This checks documentation reachability; it cannot establish physical Windows
proof, human compliance, speed, firmware behavior or localized rendering.
"""
import collections
import hashlib
import json
import pathlib
import re
import unittest

from test_owner_entry import pass_line
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = ('INSTALL.md', 'EMERGENCY.md', 'INSTALL-REFERENCE.md',
         'INSTALL-RECORD.md', 'INSTALL-PROCEDURES.md', 'INSTALL-STATUS.md')
STEP5 = '5-prove-windows-and-corrected-stock'
STEP6 = '6-switch-to-aresos'
GATE = ('**Entry gate: require STEP 5 COMPLETE and its evidence before '
        'authentication or switching. If absent, STOP')
MARKER = 'All checks PASS: write **STEP 5 COMPLETE**'
UPDATE = 'update-aresos-to-a-new-release'
UPDATE_GATE = ('**Update gate: require STEP 5 COMPLETE and a checked running AresOS '
               'before authentication or updating.**')
SENSITIVE = re.compile(r'^sudo /var/lib/ares/at (?:login|switch|update)$')
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
    # The update route has its own gate after step 7: without the step 5
    # proof only its STOP links are followed, never the route below it.
    updates = [i for i, line in enumerate(guide) if line.startswith(UPDATE_GATE)]
    if len(updates) != 1 or UPDATE not in sections:
        raise AssertionError('Missing/ambiguous update gate')
    update_gate = updates[0]
    route_end = next((i for i in range(sections[UPDATE] + 1, len(guide)) if HEADING.match(guide[i])
                      and len(guide[i].split(' ', 1)[0]) <= 3), len(guide))
    if not (sections['8-everyday-boot-and-recovery'] < sections[UPDATE] < update_gate < route_end):
        raise AssertionError('Update gate must open the update route inside step 8')
    gate_exits = [target('INSTALL.md', url, texts) for url in LINK.findall(guide[update_gate])]
    if not gate_exits or any(t is None or t[0] == 'INSTALL.md' and sections[UPDATE] <= t[1] < route_end for t in gate_exits):
        raise AssertionError('Update gate must STOP outside the update route')
    for i, line in enumerate(guide):
        if line == 'sudo /var/lib/ares/at update' and not update_gate < i < route_end:
            raise AssertionError('Update command outside the gated update route')

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
        if SENSITIVE.search(line):
            if not proof:
                raise AssertionError('Authentication/switch bypasses step 5: ' + ' -> '.join(route))
            sensitive.add(line)
        if node == ('INSTALL.md', marker):
            proof = True
        outgoing = edges[node]
        if node == ('INSTALL.md', gate) and not proof:
            # Follow the visible conditional STOP return, not the success path.
            outgoing = [('INSTALL.md', sections[STEP5])]
        if node == ('INSTALL.md', update_gate) and not proof:
            outgoing = gate_exits
        for destination in outgoing:
            traversed.add((node, destination))
            queue.append((destination, proof, route))
    if len(sensitive) != 3:
        raise AssertionError('Authentication, switch and update must all remain reachable after proof')
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


def abandon_card_route(texts, *, pending, recorded_pass=False, refusal=None, invoke=None):
    """Follow the card's successful jump with the real pending-record state."""
    commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
    card = section(texts['EMERGENCY.md'], 'crashed-or-restarted-during-a-keyboard-layout-trial')
    procedure = section(texts['INSTALL-PROCEDURES.md'], 'abandoned-layout-trial')
    missing = 'Missing private layout-pending record'
    events = []
    if recorded_pass:
        already = next(line for line in procedure.splitlines() if line.startswith('**Already cleared:**'))
        if missing not in already or 'only with the prior recorded PASS' not in already:
            raise AssertionError('Already-cleared route must require its prior PASS')
        if refusal not in (None, missing):
            return ['Help']
        destination = next(url for url in LINK.findall(already) if 'abandon-completion' in url)
        page = 'INSTALL-PROCEDURES.md'
    else:
        if refusal or not pending:
            return ['Help']
        if card.count(commands['layout-abandon']) != 1 or pass_line('layout-abandon') not in card:
            raise AssertionError('Card must invoke abandon once and require its exact PASS')
        if invoke:
            invoke()
        events.append('abandon')
        pending = False
        recorded_pass = True
        after = next(line for line in card.splitlines() if line.startswith('**After `PASS layout abandon`:**'))
        destination = LINK.findall(after)[0]
        page = 'EMERGENCY.md'
    resolved = target(page, destination, texts)
    if resolved is None:
        raise AssertionError('Unresolved abandon completion')
    name, line = resolved
    headings = anchors(texts[name])
    anchor = next(key for key, value in headings.items() if value == line)
    completion = section(texts[name], anchor)
    if name != 'INSTALL-PROCEDURES.md' or anchor != 'abandon-completion':
        raise AssertionError('Card must jump directly to abandon completion')
    if commands['layout-abandon'] in completion and not pending:
        raise AssertionError('Card route repeats abandon after clearing its pending record')
    if 'only after that PASS' not in completion or 'Do not invoke abandon again' not in completion:
        raise AssertionError('Completion must preserve the already-cleared state')
    return events + ['completion']


def bounded_layout_login(texts, *, interrupted, successes, prior_failures=0):
    """Use the visible old/new order and budget, never reset it by changing tty."""
    block = section(texts['INSTALL-PROCEDURES.md'], 'abandoned-layout-trial')
    before = block.split('### Abandon completion', 1)[0]
    branch = next(line for line in before.splitlines() if line.startswith('- **Finish invoked'))
    old, new, stop = (branch.find(term) for term in ('last confirmed layout **once**',
                     'proven new layout **once**', 'Two failed logins'))
    if min(old, new, stop) < 0 or not old < new < stop or 'no third attempt' not in branch:
        raise AssertionError('Interrupted finish needs old once, proven new once, then Help')
    begin = next(line for line in before.splitlines() if line.startswith('- **Begin/revert'))
    if 'last confirmed layout' not in begin or 'did not persist' not in begin:
        raise AssertionError('Begin/revert must use the confirmed boot layout')
    if 'Any earlier failures' not in before or 'two-failed-login total limit for the incident' not in before:
        raise AssertionError('Login budget must include earlier failures')
    if prior_failures:
        return ['Help']
    allowed = ['old', 'new'] if interrupted == 'finish' else ['old']
    events = []
    for profile, success in zip(allowed, successes):
        events.append(profile)
        if success:
            return events + ['authenticated']
    return events + ['Help']


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
                ('everyday boot-order restoration', ('INSTALL.md', '8-everyday-boot-and-recovery')),
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
    order = (commands['layout-proof'], pass_line('layout-proof'),
             commands['layout-finish'], pass_line('layout-finish'))
    positions = [proof.find(value) for value in order]
    if min(positions) < 0 or positions != sorted(positions):
        raise AssertionError('Layout recovery needs fresh proof then finish before completion')
    if commands['check'] not in finished or 'INSTALL.md#8-everyday-boot-and-recovery' not in finished:
        raise AssertionError('Completed AresOS layout must be checked then return to step 8')
    for block in (reverted, proof, finished):
        if 'INSTALL.md#5-' in block or 'INSTALL.md#7-' in block:
            raise AssertionError('Layout recovery must retain its AresOS context')
    abandoned = section(procedures, 'abandoned-layout-trial')
    if (commands['layout-abandon'] not in abandoned or pass_line('layout-abandon') not in abandoned
            or 'fresh physical tty3' not in abandoned or 'last confirmed layout' not in abandoned):
        raise AssertionError('Abandon needs confirmed layout and a fresh physical login')
    complete_abandon = section(procedures, 'abandon-completion')
    ares, stock = complete_abandon.split('**Return by booted OS:**', 1)[1].split('On **retained stock**', 1)
    if (commands['check'] not in ares or 'INSTALL.md#8-everyday-boot-and-recovery' not in ares
            or '(#keep-stock)' in ares or '[return to keep-stock](#keep-stock)' not in stock):
        raise AssertionError('Abandon must retain the booted OS return route')
    if any(command in abandoned for command in (commands['layout-proof'], commands['layout-finish'])):
        raise AssertionError('Abandon must not finish a cleared trial')
    if abandon_card_route(texts, pending=True) != ['abandon', 'completion']:
        raise AssertionError('Card abandon route is incomplete')


class OwnerPathTest(unittest.TestCase):
    def test_install_night_serials_join_windows_eui_to_printed_linux_serial(self):
        texts = documents()
        record = section(texts['INSTALL-RECORD.md'], 'c-identify-both-drives-in-live-linux')
        for value in ('Disk.Serial', 'EUI-64', 'xxxx_xxxx_xxxx_xxxx.', 'lsblk',
                      "Get-PhysicalDisk | Where-Object FriendlyName -like 'Micron*'",
                      'SerialNumber = record A\'s Disk.Serial', 'Guid = record A\'s Disk.Guid',
                      "($aresMicron[0].AdapterSerialNumber -split '_')[0].Trim()",
                      'exactly one', 'Blank/different/ambiguous', 'printed label serial'):
            self.assertIn(value, record)
        step4 = section(texts['INSTALL.md'], '4-install-and-prepare-corrected-stock')
        prompt = step4.split('At **Windows baseline Micron serial**', 1)[1].split('Require `PASS install`', 1)[0]
        for value in ('printed Micron serial', 'AdapterSerialNumber', 'before `_`, trimmed',
                      'SerialNumber = Disk.Serial', 'matching disk GUID', 'do not enter the EUI-64'):
            self.assertIn(value, prompt)
        self.assertNotIn('all matching `windows-before.json`', record)

    def test_windows_serial_checkpoint_returns_before_linux_identification(self):
        texts = documents()
        record = texts['INSTALL-RECORD.md']
        checkpoint = section(record, 'windows-printed-serial-checkpoint')
        step4 = section(texts['INSTALL.md'], '4-install-and-prepare-corrected-stock')
        box1 = next(line for line in step4.splitlines() if line.startswith('- [ ]'))
        self.assertIn('(INSTALL-RECORD.md#windows-printed-serial-checkpoint)', box1)
        for value in ('Get-PhysicalDisk', 'SerialNumber = record A\'s Disk.Serial',
                      'Guid = record A\'s Disk.Guid', 'Blank/different/ambiguous', 'STOP'):
            self.assertIn(value, checkpoint)
        returned = checkpoint.splitlines()[-1]
        self.assertTrue(returned.startswith('**PASS → [Return to step 4, box 1]'))
        self.assertIn('continue with the offline live boot', returned)
        self.assertEqual([target('INSTALL-RECORD.md', url, texts) for url in LINK.findall(returned)],
                         [('INSTALL.md', anchors(texts['INSTALL.md'])['4-install-and-prepare-corrected-stock'])])
        self.assertLess(record.index(returned), record.index('### Live Linux identification'))
        self.assertLess(record.index(returned), record.index('sudo lsblk'))
        self.assertNotIn('sudo ', checkpoint)
        self.assertIn('[record C](INSTALL-RECORD.md#live-linux-identification)', step4)

    def test_live_keyboard_command_precedes_typing_test_and_keeps_installer_de(self):
        texts = documents()
        for page, anchor in (('INSTALL.md', '4-install-and-prepare-corrected-stock'),
                             ('INSTALL-RECORD.md', 'c-identify-both-drives-in-live-linux')):
            block = section(texts[page], anchor)
            command = block.index('sudo localectl set-x11-keymap de')
            typing = block.index('y z / - " $ ä ö ü')
            self.assertLess(command, typing)
            for value in ('**ß** (right of **0**)', '**Z** (between **T** and **U**)',
                          'spacebar', 'before Enter', 'every character matches', 'STOP →',
                          'every live boot'):
                self.assertIn(value, block)
        self.assertIn('add German, remove US, **Save**', texts['INSTALL.md'])
        self.assertIn('summary contains only **de**', texts['INSTALL.md'])

        # Check the public typing advice against the exact retained ISO maps.
        folder = ROOT/'os/manifest/ci/14/keyboard-sources'
        maps = {}
        for profile in ('de', 'us'):
            raw = (folder/(profile+'.map')).read_bytes()
            receipt = next(row for row in json.loads((folder/'index.json').read_text())
                           if row['file'] == profile+'.map')
            self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt['sha256'])
            maps[profile] = {int(code): symbol.lstrip('+') for code, symbol in
                            re.findall(r'^keycode\s+(\d+)\s*=\s*(\S+)', raw.decode(), re.M)}
        for code, german, us in ((12, 'U+00df', 'U+002d'), (21, 'U+007a', 'U+0079'),
                                  (57, 'U+0020', 'U+0020')):
            self.assertEqual((maps['de'][code].lower(), maps['us'][code].lower()),
                             (german.lower(), us.lower()))
        for char in 'abcdefghijklmnopqrstuvwx0123456789':
            symbol = ('U+'+format(ord(char), '04x')).lower()
            positions = [{code for code, value in maps[p].items() if value.lower() == symbol}
                         for p in ('de', 'us')]
            self.assertTrue(positions[0])
            self.assertEqual(*positions)

    def test_reinstall_exception_stays_before_tools_and_rejects_other_crucial_data(self):
        texts = documents()
        step4 = section(texts['INSTALL.md'], '4-install-and-prepare-corrected-stock')
        retry = step4.split('**Reinstall only', 1)[1].split('- [ ]', 1)[0]
        for value in ('failed first install', 'before the tools are installed',
                      'Return to step 4, box 1', 'EFI, boot and system partitions, nothing else',
                      'saved plan/records', 'Micron', 'unchanged/unmounted',
                      'Anything else on Crucial', 'STOP', '**Use entire disk** on **Crucial only**',
                      'After tools installation'):
            self.assertIn(value, retry)
        record = section(texts['INSTALL-RECORD.md'], 'c-identify-both-drives-in-live-linux')
        self.assertIn('**zero partition children**', record)
        retry_row = next(line for line in record.splitlines() if '| **Failed first install,' in line)
        for value in ('before tools installation only', 'nothing else', 'no mounts', 'Micron unchanged',
                      'Anything else on Crucial', '**STOP**', 'Once record C passes',
                      'box 3 — installer keyboard/destination', '**current live session**'):
            self.assertIn(value, retry_row)
        self.assertNotIn('box 1', retry_row)
        # The return must land at the keyboard box, not merely at a valid step-4 link.
        guide = texts['INSTALL.md']
        installer = anchors(guide)['installer-keyboard-and-destination']
        after_anchor = guide.splitlines()[installer + 1:]
        self.assertTrue(next(line for line in after_anchor if line.strip()).startswith(
            '- [ ] Installer **English (United States)'))
        self.assertIn('**Installation method → Change destination**', '\n'.join(after_anchor[:4]))
        dispatch_row = next(line for line in texts['INSTALL-RECORD.md'].splitlines()
                            if line.startswith('| initial live mapping'))
        for returned in (retry_row, dispatch_row):
            self.assertEqual([target('INSTALL-RECORD.md', url, texts) for url in LINK.findall(returned)],
                             [('INSTALL.md', installer)])
        self.assertIn('bounded reinstall', dispatch_row)
        self.assertIn('current live session', dispatch_row)
        self.assertIn('[Return to step 4, box 3](#installer-keyboard-and-destination)', step4)
        self.assertIn('without rebooting', step4)
        card = section(texts['EMERGENCY.md'], 'password-not-accepted')
        for value in ('failed first install before tools installation', 'box 1', 'nothing else',
                      'Micron must be unchanged/unmounted', 'STOP', '**Crucial only**'):
            self.assertIn(value, card)
        account = next(line for line in step4.splitlines() if '**Create Account**' in line)
        for value in ('every install', 'lowercase letters a–x and top-row digits 0–9', 'long, unique',
                      'several randomly chosen words', 'No y/z', 'Enter it twice yourself'):
            self.assertIn(value, account)

    def test_only_expected_mok_menu_allows_continue_without_key_changes(self):
        texts = documents()
        blocks = (section(texts['INSTALL.md'], '4-install-and-prepare-corrected-stock'),
                  section(texts['INSTALL-REFERENCE.md'], 'mok-screen'),
                  section(texts['EMERGENCY.md'], 'blue-mok-menu-on-first-stock-boot'))
        for block in blocks:
            for value in ('Perform MOK management', 'Continue boot', 'STOP', 'signature', 'enrollment'):
                self.assertIn(value, block)
            self.assertRegex(block, r'(?i)never enroll')
        reference = blocks[1]
        for value in ('blue text menu', 'shim/blob/16.1/MokManager.c', 'MOK_BOOT',
                      'password request', 'return to the menu', 'Return to step 4'):
            self.assertIn(value, reference)

    def test_maintainer_windows_role_and_owner_hands_and_secrets_are_explicit(self):
        texts = documents()
        for name in ('INSTALL.md', 'INSTALL-RECORD.md'):
            intro = texts[name].split('\n## ', 1)[0]
            for value in ('maintainer (Claude)', 'runs the Windows-side commands itself',
                          'owner', 'firmware', 'offline Linux commands with a guiding session',
                          'Codex does not run disk or boot tools on the real laptop'):
                self.assertIn(value, intro)
        guide = texts['INSTALL.md'].split('\n## ', 1)[0]
        for value in ('F2/F12', 'every passphrase or token himself', "owner's OK", 'what could go wrong'):
            self.assertIn(value, guide)
        for text in texts.values():
            self.assertNotRegex(text, r'Agents (?:do none|never run|never perform)')

    def test_steps_4_to_7_name_bazzite_and_keep_fedora_explanation(self):
        guide = documents()['INSTALL.md']
        blocks = [section(guide, anchor) for anchor in
                  ('4-install-and-prepare-corrected-stock', '5-prove-windows-and-corrected-stock',
                   '6-switch-to-aresos', '7-check-the-first-aresos-session')]
        for block in blocks:
            self.assertIn('**Bazzite**', block)
            for line in block.splitlines():
                if 'recorded Linux' in line:
                    self.assertIn('Bazzite', line)
            self.assertNotIn('→ Linux.', block)
        self.assertIn('[step 8 explains Fedora](#8-everyday-boot-and-recovery)', blocks[0])
        self.assertIn('**Fedora**', section(guide, '8-everyday-boot-and-recovery'))

    def test_bootstrap_history_and_console_fallback_keep_completion_guards(self):
        texts = documents()
        step4 = section(texts['INSTALL.md'], '4-install-and-prepare-corrected-stock')
        for value in ('same root shell', 'display it first', 'all 13 lines', '**line 8**',
                      'before Enter', 'Only after help resolves it'):
            self.assertIn(value, step4)
        console = section(texts['INSTALL-REFERENCE.md'], 'console')
        for value in ('Black screen', 'one minute', 'do not reboot', 'accidental dead key',
                      'Ctrl+Alt+F4', 'Ctrl+Alt+Fn+F4', 'same `ares-recovery` login',
                      'Do not repeat a command whose result is unknown', 'failed-login budget'):
            self.assertIn(value, console)

    def test_hung_restart_does_not_claim_check_proves_the_switch_finished(self):
        texts = documents()
        ref = section(texts['INSTALL-REFERENCE.md'], 'hung-shutdown-or-restart')
        for value in ('at least 10 minutes', 'keep waiting', 'finished successfully',
                      'firmware/BIOS update', 'media write/export or layout trial',
                      'completion is unknown', 'switch/title PASS', 'Windows Boot Manager',
                      'Do not repeat the switch', 'v2026.4', 'removes staged state before the merge',
                      'without a resumable staged entry', 'PASS check', 'unchanged prepared stock',
                      'Final pair has extra/missing deployments', 'Stock KDE after a switch is STOP',
                      'step 5 proof rechecked'):
            self.assertIn(value, ref)
        self.assertIn('Stock KDE returning after the switch', section(texts['INSTALL.md'], '7-check-the-first-aresos-session'))
        for anchor in ('frozen-laptop', 'failed-first-switch-boot', 'shutdown-or-restart-hangs'):
            self.assertIn('10 minutes' if anchor != 'failed-first-switch-boot' else '10-minute',
                          section(texts['EMERGENCY.md'], anchor))
        self.assertNotIn('Still on? Hold power', texts['EMERGENCY.md'])

    def test_idle_live_shutdown_exception_matches_and_preserves_recovery_guards(self):
        texts = documents()
        ref = section(texts['INSTALL-REFERENCE.md'], 'hung-shutdown-or-restart')
        card = section(texts['EMERGENCY.md'], 'shutdown-or-restart-hangs')
        exception = ('**Idle-live-session exception:** no successful install/tool command is required '
                     'for an idle live session after requesting desktop shutdown. In either case, '
                     'no firmware/BIOS update, media write/export or layout trial may be in progress.')
        for block in (ref, card):
            self.assertEqual(block.count(exception), 1)
            for value in ('at least 10 minutes', 'progress', 'switch/title PASS',
                          'checked reboot request first', 'Windows Boot Manager',
                          'do not force off', 'once', 'provisional GRUB title', 'step 5 proof rechecked'):
                self.assertIn(value, block)
            self.assertRegex(block, r'(?i)(completion is unknown|unknown completion)')
            self.assertIn('error', block)
            after_windows = block.split('Windows Boot Manager', 1)[1]
            self.assertIn('Help', after_windows)
            self.assertRegex(after_windows, r'only after (?:Help resolves|resolution)')

    def test_layout_password_stays_typeable_and_public_proof_drives_negative_trial(self):
        texts = documents()
        layout = section(texts['INSTALL-PROCEDURES.md'], 'later-layout').split('### Layout revert', 1)[0]
        for value in ('lowercase a–x and top-row digits 0–9',
                      'stays typeable in German, US International and plain US',
                      'public `yz-/!ü` proof exercises the layout difference',
                      '**tty3 ares-recovery → sudo -i** session **OPEN**',
                      'do not reboot or change the password', 'fresh `ares-recovery` password login',
                      'sudo -k; sudo /var/lib/ares/at layout proof', 'AltGr+y'):
            self.assertIn(value, layout)
        negative = layout.split('Require `PASS layout begin us`', 1)[1]
        for value in ('only in the supervised layout gate', 'unchanged password stays typeable',
                      'plain US cannot type the ü in the public `yz-/!ü` proof',
                      'original tty3 root session open', '[Layout revert](#layout-revert)',
                      'Reboot must refuse unfinished proof', 'never test refusal by forcing a restart'):
            self.assertIn(value, negative)
        self.assertNotIn('umlaut password', layout)
        self.assertNotIn('password may be untypeable', layout)
        check_context_returns(texts)

    def test_step4_pass_and_reviewed_tools_do_not_release_a_new_stage_or_vm_result(self):
        status = documents()['INSTALL-STATUS.md']
        stage = next(line for line in status.splitlines() if line.startswith('| Stage C —'))
        # Steps 5-7 are recorded as they happened (package 22), step 7 with
        # its two open items; no update has run.
        for value in ('RELEASED 2026-11-07', 'Step 4 PASSED 2026-11-08', 'Step 5 COMPLETE 2026-11-09',
                      'Step 6 PASSED 2026-11-09', 'Step 7 PASSED 2026-11-09 with two items OPEN',
                      'board #139', 'board #140', 'No step 8 update has run'):
            self.assertIn(value, stage)
        hardware = next(line for line in status.splitlines() if line.startswith('| Early hardware / P1a |'))
        for value in ('**Brightness FAIL** (board #139)', '**Power-button gate OPEN** (board #140)', 'stay OPEN'):
            self.assertIn(value, hardware)
        update = next(line for line in status.splitlines() if line.startswith('| Update route tools (package 22) |'))
        for value in ('NOT USED', 'no newer release exists yet', 'no real update and no VM rehearsal',
                      "with the owner's OK", 'pending-rebind.json', 'no new image or stage'):
            self.assertIn(value, update)
        tools = next(line for line in status.splitlines() if line.startswith('| Post-release tools change |'))
        for value in ('PR #22', '3ef85c4a', 'unit-tested and reviewed', 'without a new VM rehearsal',
                      'pending-rebind.json', 'no new image or stage'):
            self.assertIn(value, tools)

    def test_abandoned_trial_card_uses_bounded_login_fresh_session_exact_pass_and_completion(self):
        texts = documents()
        card = section(texts['EMERGENCY.md'], 'crashed-or-restarted-during-a-keyboard-layout-trial')
        for value in ('last confirmed layout', 'fresh physical', 'ares-recovery password login',
                      'sudo /var/lib/ares/at layout abandon', pass_line('layout-abandon'),
                      'INSTALL-PROCEDURES.md#abandon-completion', 'INSTALL-PROCEDURES.md#keep-stock',
                      'Finish invoked', 'proven new layout **once**', 'two failed logins'):
            self.assertIn(value, card)
        check_context_returns(texts)
        before = 'run `sudo /var/lib/ares/at check` (require `PASS check`), prove confirmed-layout password/text typing, then [Return to step 8](INSTALL.md#8-everyday-boot-and-recovery)'
        self.assertIn(before, texts['INSTALL-PROCEDURES.md'])
        texts['INSTALL-PROCEDURES.md'] = texts['INSTALL-PROCEDURES.md'].replace(
            before, '[return to keep-stock](#keep-stock)', 1)
        with self.assertRaisesRegex(AssertionError, 'Abandon must retain'):
            check_context_returns(texts)

    def test_card_clears_real_pending_state_then_completion_does_not_abandon_again(self):
        import test_owner_setup_resume as setup
        from unittest.mock import patch
        import time
        with setup.preparation() as fixture:
            fixture.pair()
            administrator = dict(tty='tty3', session='original', boot='first', started_us=1)
            fixture.tools.session = lambda: administrator
            fixture.tools.layout('begin', 'us')
            pending = fixture.store/'layout-pending.json'
            self.assertTrue(pending.exists())
            fixture.tools.session = lambda: dict(administrator, session='fresh', started_us=int(time.monotonic()*1e6)+1)
            with patch.object(fixture.tools, 'title', return_value=['fresh verified title']):
                events = abandon_card_route(documents(), pending=pending.exists(),
                    invoke=lambda: fixture.tools.layout('abandon'))
            self.assertEqual(events, ['abandon', 'completion'])
            self.assertFalse(pending.exists())
            self.assertEqual(abandon_card_route(documents(), pending=False, recorded_pass=True), ['completion'])
            with self.assertRaisesRegex(setup.owner.Stop, 'Missing private layout-pending record'):
                fixture.tools.layout('abandon')
            self.assertEqual(abandon_card_route(documents(), pending=False, recorded_pass=True,
                             refusal='Missing private layout-pending record'), ['completion'])
            self.assertEqual(abandon_card_route(documents(), pending=False,
                             refusal='Missing private layout-pending record'), ['Help'])
            self.assertEqual(abandon_card_route(documents(), pending=False, recorded_pass=True,
                             refusal='Another identity refusal'), ['Help'])

    def test_card_start_link_and_extra_completion_invocation_mutations_are_rejected(self):
        texts = documents()
        texts['EMERGENCY.md'] = texts['EMERGENCY.md'].replace(
            '(INSTALL-PROCEDURES.md#abandon-completion)', '(INSTALL-PROCEDURES.md#abandoned-layout-trial)', 1)
        with self.assertRaisesRegex(AssertionError, 'directly to abandon completion'):
            abandon_card_route(texts, pending=True)
        texts = documents()
        texts['INSTALL-PROCEDURES.md'] = texts['INSTALL-PROCEDURES.md'].replace(
            '### Abandon completion\n', '### Abandon completion\n\nsudo /var/lib/ares/at layout abandon\n', 1)
        with self.assertRaisesRegex(AssertionError, 'repeats abandon'):
            abandon_card_route(texts, pending=True)

    def test_interrupted_finish_tries_confirmed_then_proven_map_with_a_two_attempt_stop(self):
        texts = documents()
        for action in ('begin', 'revert'):
            self.assertEqual(bounded_layout_login(texts, interrupted=action, successes=[True]), ['old', 'authenticated'])
            self.assertEqual(bounded_layout_login(texts, interrupted=action, successes=[False, True]), ['old', 'Help'])
        self.assertEqual(bounded_layout_login(texts, interrupted='finish', successes=[True]), ['old', 'authenticated'])
        self.assertEqual(bounded_layout_login(texts, interrupted='finish', successes=[False, True]), ['old', 'new', 'authenticated'])
        self.assertEqual(bounded_layout_login(texts, interrupted='finish', successes=[False, False, True]), ['old', 'new', 'Help'])
        self.assertEqual(bounded_layout_login(texts, interrupted='finish', successes=[True], prior_failures=1), ['Help'])
        texts['INSTALL-PROCEDURES.md'] = texts['INSTALL-PROCEDURES.md'].replace('proven new layout **once**', 'proven new layout repeatedly', 1)
        with self.assertRaisesRegex(AssertionError, 'Interrupted finish needs'):
            bounded_layout_login(texts, interrupted='finish', successes=[False, True])

    def test_login_budget_is_below_hash_bound_shipped_policy_without_claiming_active_faillock(self):
        folder = ROOT/'reviews/15-owner-path/15e-login-policy'
        evidence = json.loads((folder/'index.json').read_text())
        release = json.loads((ROOT/'os/manifest/release.json').read_text())
        self.assertEqual(evidence['image'], release['reference'])
        self.assertEqual(evidence['base'], release['base'])
        self.assertIn('FROM '+release['base'], (ROOT/'os/Containerfile').read_text())
        self.assertTrue(release['image_diff']['packages_equal'])
        self.assertEqual(set(release['image_diff']['files']),
                         {'usr/bin/aresos-session', 'usr/libexec/aresos-keyboard'})
        packages = json.loads((ROOT/'os/packages.lock.json').read_text())['packages']
        self.assertFalse(any(row['nevra'].startswith(('pam-', 'authselect-')) for row in packages))
        self.assertNotRegex((ROOT/'os/build.sh').read_text(), r'faillock|authselect')
        self.assertFalse(any('pam.d' in path.parts or 'authselect' in path.parts or path.name == 'faillock.conf'
                             for path in (ROOT/'os/config').rglob('*')))
        manifest = ROOT/evidence['manifest']['path']
        self.assertEqual(hashlib.sha256(manifest.read_bytes()).hexdigest(), evidence['manifest']['sha256'])
        self.assertTrue(release['base'].endswith(evidence['manifest']['sha256']))
        layers = {row['digest'].split(':', 1)[1] for row in json.loads(manifest.read_text())['layers']}
        for row in evidence['files']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(), row['sha256'])
            self.assertIn(row['layer_sha256'], layers)
        config = (folder/'faillock.conf').read_text()
        self.assertFalse(re.search(r'^\s*(deny|fail_interval|unlock_time)\s*=', config, re.M))
        defaults = {key:int(value) for key,value in re.findall(r'^#\s*(deny|fail_interval|unlock_time)\s*=\s*(\d+)', config, re.M)}
        self.assertEqual(defaults, {'deny':3, 'fail_interval':900, 'unlock_time':600})
        self.assertEqual((folder/'authselect.conf').read_text().splitlines()[0], 'local')
        for name in ('system-auth', 'password-auth', 'postlogin', 'login.pam', 'sudo.pam', 'sudo-i.pam'):
            self.assertNotIn('pam_faillock', (folder/name).read_text())
        self.assertIn('auth       substack     system-auth', (folder/'login.pam').read_text())
        self.assertIn('auth       include      sudo', (folder/'sudo-i.pam').read_text())
        self.assertIn('auth       include      system-auth', (folder/'sudo.pam').read_text())
        self.assertEqual(evidence['links']['etc/pam.d/system-auth'], '/etc/authselect/system-auth')
        self.assertFalse(evidence['policy']['pam_faillock_in_generated_login_stack'])
        budget = evidence['policy']['recovery_attempt_limit']
        self.assertEqual(budget, 2)
        self.assertLess(budget, defaults['deny'])
        reference = section(documents()['INSTALL-REFERENCE.md'], 'layout-recovery-login-limit')
        for value in ('default `deny = 3`', '`fail_interval = 900`', '`unlock_time = 600`',
                      'does **not enable `pam_faillock`**', 'at most two failed login submissions total',
                      'without following its retry prompts', 'changed/unknown policy'):
            self.assertIn(value, reference)

    def test_mounted_protected_child_condition_requires_native_evidence_before_stage_c(self):
        status = documents()['INSTALL-STATUS.md']
        mounted = next(line for line in status.splitlines() if line.startswith('| Protected child mounted at runtime |'))
        for value in ('protected disk was unmounted', 'native runtime check', 'real loop fixture',
                      'mounted protected child partition', 'zero mutations', 'cleanup', 'VM acceptance remains met'):
            self.assertIn(value, mounted)
        if '**MET' in mounted:
            self.assertRegex(mounted, r'https://github.com/Ares-Empire/AresOS/actions/runs/[0-9]+')
            self.assertIn('missing-check stand-in', mounted)
        else:
            self.assertIn('OPEN — native probe required before Stage C', mounted)
        accepted = next(line for line in status.splitlines() if line.startswith('| Package 14 owner tools |'))
        self.assertIn('Qualification 21 PASSED; VM acceptance met', accepted)

    def test_staged_owner_decision_and_all_stage_boundaries(self):
        texts=documents(); status=texts['INSTALL-STATUS.md']; guide=texts['INSTALL.md']
        self.assertIn('Owner decision: staged release (2026-11-02)', status)
        self.assertIn('owner as first reader', status)
        self.assertIn('maintainer (Claude) checking each stage', status)
        for label,state in (('Stage A — preparation','CHECKED 2026-11-05'),
                            ('Stage B — fitting','CHECKED 2026-11-07'),
                            ('Stage C — installation','RELEASED 2026-11-07')):
            row=next(line for line in status.splitlines() if line.startswith('| '+label+' |'))
            self.assertIn('**'+state+'**',row)
        c=next(line for line in status.splitlines() if line.startswith('| Stage C —'))
        for term in ('maintainer has checked A and B','native mounted-child check has passed',
                     'maintainer has updated this table','each step'):
            self.assertIn(term,c)
        self.assertNotIn('Until it permits physical installation, read only',guide)
        # The guide's step 4 header must agree with the Stage C row.
        step4=section(guide,'4-install-and-prepare-corrected-stock')
        if '**RELEASED' in c:
            self.assertNotIn('NOT RELEASED',step4)
            self.assertIn('Stage C — released',step4)
        else:
            self.assertIn('Stage C — NOT RELEASED',step4)
        for anchor in ('1-backups-recovery-and-windows-preparation','3-fit-and-identify-both-drives',
                       '4-install-and-prepare-corrected-stock'):
            self.assertIn('stop here and send your records to the maintainer',section(guide,anchor))
        for anchor in ('2-prepare-and-test-the-installer-stick','3-fit-and-identify-both-drives'):
            self.assertIn('End of Stage',section(guide,anchor))
        fitting=next(line for line in status.splitlines() if line.startswith('| Fitting,'))
        for term in ('seating and battery photos','firmware screen showing both drives',
                     'after-fit','2026-11-09','qualified repairer first'):
            self.assertIn(term,fitting)
        # The negative fitting trials stay visible until the maintainer checks their results.
        for term in ('Expendable fitting trial','Damaged-battery photograph','**before screw**',
                     '**before connectors/reconnection**'):
            self.assertIn(term,fitting)
        gates=('Media pins','LOQ shortcuts and recovery menu','Live KDE / installed keyboard',
               'Tools-stick physical lifecycle','NVIDIA deferred Flatpak work',
               'Windows record helper / independent undo','Token retirement','Early hardware / P1a')
        for gate in gates:
            row=next(line for line in status.splitlines() if line.startswith('| '+gate+' |'))
            self.assertIn('OPEN',row)
            self.assertIn('owner performs',row)
            self.assertIn('maintainer checks',row)

    def test_tools_stop_exports_persistent_diagnostics_without_authorizing_retry(self):
        card = section(documents()['EMERGENCY.md'], 'a-tools-command-stopped')
        for value in ('keep the entire screen', 'administrator session open',
                      'sudo /var/lib/ares/at export', pass_line('export'),
                      '/var/lib/ares/diagnostics', 'diagnostic-', 'SAFE TO REMOVE',
                      'bootstrap failure', 'Return to the failed recorded step only after resolution'):
            self.assertIn(value, card)

    def test_everyday_boot_order_record_b_returns_to_step_8(self):
        texts = documents()
        self.assertIn('record B', section(texts['INSTALL.md'], '8-everyday-boot-and-recovery'))
        check_context_returns(texts)

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
                self.assertIn(pass_line('reboot'), following, (page, match.start()))
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
                    'Password not accepted', 'Crashed or restarted during a keyboard layout trial',
                    'A tools command stopped', 'Text covers the prompt after stick hotplug or removal',
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

    def test_update_route_orders_windows_tools_update_title_reboot_check_with_pass_stop_and_returns(self):
        import hashlib
        import test_owner_tools as common
        texts = documents()
        guide = texts['INSTALL.md']
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        fingerprint = hashlib.sha256((ROOT/'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest()
        route = section(guide, UPDATE)
        self.assertIn(route, section(guide, '8-everyday-boot-and-recovery'))
        self.assertTrue(route.splitlines()[2].startswith(UPDATE_GATE))
        order = ('Copy-AresOwnerTools', 'PASS tools manifest SHA256 ' + fingerprint, 'Safely eject and unplug',
                 '**F12** (or **Fn+F12**) → **Bazzite**', '```bash\n' + commands['install'] + '\n```', pass_line('install'),
                 '**Tools updated from version**', commands['update'], pass_line('update'), '**Signed exact release staged**',
                 commands['title'], commands['export'], 'SAFE TO REMOVE ARESTOOLS', commands['reboot'], pass_line('reboot'),
                 '10-minute rule', '**F12** (or **Fn+F12**) → **Bazzite**', commands['check'], commands['title'],
                 commands['records'], pass_line('check'), 'sudo passwd ares', commands['previous'], pass_line('previous'),
                 '**Record:**', '[Return to step 8](#8-everyday-boot-and-recovery)')
        position = 0
        for value in order:
            found = route.find(value, position)
            self.assertGreaterEqual(found, 0, value)
            position = found + len(value)
        boxes = [line for line in route.splitlines() if line.startswith('- [ ]')]
        self.assertEqual(len(boxes), 8)
        self.assertGreaterEqual(route.count('STOP →'), 4)
        self.assertGreaterEqual(route.count('Return to this update route'), 4)
        # A login refusal points to login, then the same update once more.
        refusal = common.owner.LOGIN_REFUSAL.split(':', 1)[0]
        self.assertIn('**If it STOPs with `' + refusal + '`:**', route)
        after = route.split(refusal, 1)[1]
        self.assertTrue(after.index('```bash\n' + commands['login'] + '\n' + commands['update'] + '\n```') < after.index(pass_line('login')))
        for value in ('read:packages-only', 'only at the hidden token prompt', 'never retry with another target'):
            self.assertIn(value, route)
        password = next(line for line in route.splitlines() if 'sudo passwd ares' in line)
        for value in ('lowercase a–x and top-row digits 0–9', 'German, US International and US',
                      'Never photograph, record or send it', 'keep it private', '`sudo -v`', 'once'):
            self.assertIn(value, password)
        for value in ('current AresOS as rollback', 'corrected stock pinned', 'three deployments', 'refuse',
                      '**previous** box', '**F12 → Windows → Help**', 'provisional', 'INVALID',
                      '[Failed or bad update](EMERGENCY.md#failed-or-bad-update)', 'never a guessed GRUB title',
                      '**Update to … confirmed after the restart**', '**Return to … confirmed after the restart**',
                      '**did not finish at the restart**', '**interrupted before its result was recorded**',
                      'Help decides each repeat', 'STOPs while anything uses the installed tools',
                      'a STOP always leaves working tools in place',
                      '**Another owner command is running**'):
            self.assertIn(value, route)
        # The quoted tool messages are the ones the tools print.
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("' did not finish at the restart (", "'Another owner command is running;",
                      "' was interrupted before its result was recorded; ", "'An owner command of the installed tools is running (pid '",
                      "' confirmed after the restart'", "'Previous AresOS queued for the next start '",
                      "'Signed exact release staged '", "'Running release stays as rollback '", "'Tools updated from version '"):
            self.assertIn(value, source)
        self.assertNotIn('INSTALL.md#5-', route)

    def test_failed_update_card_returns_to_previous_aresos_or_windows_never_a_grub_title(self):
        texts = documents()
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        card = section(texts['EMERGENCY.md'], 'failed-or-bad-update')
        for value in ('Windows Boot Manager', commands['previous'], pass_line('previous'), commands['reboot'],
                      pass_line('reboot'), '**Bazzite**', 'Never choose a guessed GRUB title', 'repeat the update without Help',
                      '**did not finish at the restart**', '**interrupted before its result was recorded**', 'Help decides each repeat',
                      'stock rollback or keep-stock', '10-minute wait', '(INSTALL.md#8-everyday-boot-and-recovery)',
                      '(INSTALL.md#update-aresos-to-a-new-release)'):
            self.assertIn(value, card)
        self.assertLess(card.index('Windows Boot Manager'), card.index(commands['previous']))
        for page, anchor in (('INSTALL-PROCEDURES.md', 'recovery-menu'), ('INSTALL-PROCEDURES.md', 'later-layout')):
            self.assertIn('three deployments', section(texts[page], anchor))
        console = section(texts['INSTALL-REFERENCE.md'], 'console')
        self.assertIn('[update](INSTALL.md#update-aresos-to-a-new-release)', console)
        hang = section(texts['INSTALL-REFERENCE.md'], 'hung-shutdown-or-restart')
        self.assertIn('[update route](INSTALL.md#update-aresos-to-a-new-release)', hang)

    def test_update_gate_mutations_are_rejected(self):
        texts = documents()
        texts['INSTALL.md'] = texts['INSTALL.md'].replace(UPDATE_GATE, 'REMOVED', 1)
        with self.assertRaisesRegex(AssertionError, 'Missing/ambiguous update gate'):
            walk(texts)
        texts = documents()
        texts['INSTALL.md'] = texts['INSTALL.md'].replace(
            '- [ ] **Stage the new release:**', '#### Fast update\n\n- [ ] **Stage the new release:**', 1)
        texts['EMERGENCY.md'] = texts['EMERGENCY.md'].replace('(INSTALL-REFERENCE.md#help)', '(INSTALL.md#fast-update)', 1)
        with self.assertRaisesRegex(AssertionError, 'bypasses step 5'):
            walk(texts)
        texts = documents()
        line = next(l for l in texts['INSTALL.md'].splitlines() if l.startswith(UPDATE_GATE))
        texts['INSTALL.md'] = texts['INSTALL.md'].replace(line, line.replace('(INSTALL-REFERENCE.md#help)', '(#' + UPDATE + ')'), 1)
        with self.assertRaisesRegex(AssertionError, 'STOP outside the update route'):
            walk(texts)
        texts = documents()
        texts['INSTALL.md'] = texts['INSTALL.md'].replace(
            '## 8. Everyday boot', '```bash\nsudo /var/lib/ares/at update\n```\n\n## 8. Everyday boot', 1)
        with self.assertRaisesRegex(AssertionError, 'outside the gated update route'):
            walk(texts)

    def test_status_history_is_centralized_and_physical_gates_stay_open(self):
        for name in ('INSTALL.md', 'EMERGENCY.md'):
            text = documents()[name]
            self.assertIn('INSTALL-STATUS.md#current-gates', text)
            self.assertNotIn('/actions/runs/', text)
            self.assertNotIn('40184846815', text)
        status = documents()['INSTALL-STATUS.md']
        for phrase in ('Physical gates close through checked step evidence', 'FnLock states', 'Damaged-battery', 'Unaided-reader',
                       'Expendable-media', 'protected-second', 'not qualified protected-first',
                       'US-then-stock rollback was not run', 'Qualification 21 PASSED'):
            self.assertIn(phrase, status)
        owner = next(line for line in status.splitlines() if line.startswith('| Package 14 owner tools |'))
        self.assertIn('**R13 tested; protected-second**', owner)
        for phrase in ('3fd7916', '41374876561', 'mid-trial', 'German', 'abandon'):
            self.assertIn(phrase, owner)
        self.assertNotIn('before first tools command', owner)
        self.assertIn('not that exact STOP/export/reboot sequence in a VM', status)


if __name__ == '__main__':
    unittest.main()
