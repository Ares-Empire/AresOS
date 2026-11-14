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
import subprocess
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
# Package 27b: the laptop's step 8 update as INSTALL-STATUS records it. Each
# clause is pinned whole, between its neighbours, so no word in it or next to
# it changes unnoticed: (line start, before, clause, after); an empty after
# means the clause ends the line.
STEP8_RECORD = (
    ('This is the **single current gate/status table**', 'table**, ',
     "as of **2026-11-13**, based on the retained reports, the owner decision in brief 16, the maintainer's checks "
     "of Stage A's and Stage B's records, the step 4 result supplied in brief 15g, the step 5–7 records the "
     "maintainer checked on 2026-11-08/09 and the step 8 update records the maintainer checked on 2026-11-13 "
     "(brief 27b).",
     ' Historical results'),
    ('- **R13 (previous):**', '13.json)). ',
     "Installed on the laptop at step 6 and ran there until the owner's step 8 update on 2026-11-13; since then "
     "it is the laptop's rollback.",
     ' Its VM evidence'),
    ('- **R27 (current):**', 'REPORT.md)). ',
     "A fresh install's step 6 switches to it. The laptop runs it since 2026-11-13, reached through the step 8 "
     "update route, with R13 as its rollback and the corrected stock still pinned.",
     ''),
    ('| **Physical installation** |', '| ',
     '**R13 installed; steps 4–7 passed 2026-11-08/09, step 7 with two items OPEN; step 8 update to R27 passed '
     '2026-11-13**',
     ' |'),
    ('| Stage C —', 'stay OPEN under Early hardware. ',
     "**Step 8 PASSED 2026-11-13** (board #189, [brief 27b](../briefs/27b-laptop-update-record.md)), the first "
     "update, guided: the tools updated themselves from version 1 to 2, then `at update`, `at title`, `at export` "
     "and `at reboot` passed; after the restart the check was confirmed, and records, typing and password sudo "
     "passed; the owner set `ares`'s password and `sudo -v` passed. `at previous` was not used. Two earlier "
     "bootstrap attempts stopped on typing mistakes before anything was installed.",
     " Send each step's record"),
    ('| Update route (packages 22 and 27) |', '| Update route (packages 22 and 27) | ',
     '**R27 PUBLISHED; VM REHEARSAL PASSED; USED ONCE ON THE LAPTOP 2026-11-13** | '
     '**R27 on the laptop since 2026-11-13, R13 its rollback; R27 published privately**',
     ' | '),
    ('| Update route (packages 22 and 27) |', 'REPORT.md)). ',
     "On the laptop step 8 is the owner's own step; the owner ran it once on 2026-11-13, guided (Stage C row): "
     "the tools updated themselves from version 1 to 2, `at update`, `at title`, `at export` and `at reboot` "
     "passed, and after the restart the check was confirmed and records, typing, password sudo and (once the "
     "owner had set `ares`'s password) `sudo -v` passed. A read-only check on the laptop the same day: the "
     "booted deployment is R27, the second R13 and the third the pinned stock `bazzite-nvidia-open:stable`, the "
     "transaction state is idle and `ares` is in `wheel`. `at previous` has run only in the VM rehearsal, never on "
     "the laptop. After this first update the stock rollback, keep-stock, recovery-menu and layout-trial "
     "procedures refuse, as the [step 8 update route](INSTALL.md#update-aresos-to-a-new-release) says, until "
     "package 22c. Raw records stay private and off this public repository.",
     ' **Announcement for step 8:**'),
)
HEADING = re.compile(r'^#{1,6} (.+)$')
# Package 22c, rule 7: what layout abandon says when there is no trial and no repair note.
NO_TRIAL = 'No layout trial and no half-written layout to abandon on this system; nothing changed'
# Package 22c: the sentence the stock procedures and the notice list carry word for word.
NO_BAZZITE_UPDATE = ('Never start a Bazzite update while AresOS is installed: '
                     'it deletes both AresOS versions at the next shutdown.')


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


def destination_space(ledger):
    """Every state of the reference ledger that update, previous, rollback, keep-stock, title, each
    restart and each lost finish reach from the model's starts (750 states; no cut, no layout trial)."""
    reached, todo = set(), list(ledger.starts())
    while todo:
        state = todo.pop()
        if state in reached:
            continue
        reached.add(state)
        restarts = (state.stage, state.running, 'S') if state.stage else state.rows
        events = [(word, 'full') for word in ('update', 'previous', 'rollback', 'keep-stock', 'title')]
        events += [('restart', row) for row in ('default', *restarts)]
        events += [('power-off', row) for row in ('default', *state.rows[1:])] if state.stage else []
        todo += [result.state for result in (ledger.transition(state, e) for e in events) if not result.stop and not result.cut]
    return reached


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
    missing = NO_TRIAL
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
                      '`Unknown deployment beside AresOS and the saved stock; get help`', 'Stock KDE after a switch is STOP',
                      'step 5 proof rechecked'):
            self.assertIn(value, ref)
        self.assertIn('Stock KDE returning after the switch', section(texts['INSTALL.md'], '7-check-the-first-aresos-session'))
        # 22c: version 2's final-pair refusal is gone; the quoted refusal is the one the tools print.
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        self.assertIn("'Unknown deployment beside AresOS and the saved stock; get help'", source)
        self.assertNotIn('Final pair has extra/missing deployments', source)
        self.assertNotIn('Final pair has extra/missing deployments', ref)
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
        # its two open items.
        for value in ('RELEASED 2026-11-07', 'Step 4 PASSED 2026-11-08', 'Step 5 COMPLETE 2026-11-09',
                      'Step 6 PASSED 2026-11-09', 'Step 7 PASSED 2026-11-09 with two items OPEN',
                      'board #139', 'board #140'):
            self.assertIn(value, stage)
        # Step 8 is recorded as it happened (27b), word for word.
        for start, before, clause, after in STEP8_RECORD:
            line = next(line for line in status.splitlines() if line.startswith(start))
            with self.subTest(clause=clause[:60]):
                self.assertIn(before + clause + after, line)
                if not after:
                    self.assertTrue(line.endswith(clause))
        self.assertNotIn('No step 8 update has run', stage)
        hardware = next(line for line in status.splitlines() if line.startswith('| Early hardware / P1a |'))
        for value in ('**Brightness FAIL** (board #139)', '**Power-button gate OPEN** (board #140)', 'stay OPEN'):
            self.assertIn(value, hardware)
        update = next(line for line in status.splitlines() if line.startswith('| Update route (packages 22 and 27) |'))
        # Package 27's rehearsal passed and recorded its bindings before the
        # laptop's first update (27b); its evidence and announcement stay.
        self.assertTrue((ROOT/'os/manifest/ci/27/source-bindings.json').exists())
        for value in ('VM REHEARSAL PASSED', 'actions/runs/', '27 report', '`daily_wheel: true`', 'one-time password box'):
            self.assertIn(value, update)
        for value in ('NOT USED', 'R13 on the laptop', 'not installed', 'still to come'):
            self.assertNotIn(value, update)
        previous = next(line for line in status.splitlines() if line.startswith('- **R13 (previous):**'))
        self.assertNotIn('running there until', previous)
        tools =next(line for line in status.splitlines() if line.startswith('| Post-release tools change |'))
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
            with self.assertRaisesRegex(setup.owner.Stop, '^' + re.escape(NO_TRIAL) + '$'):
                fixture.tools.layout('abandon')
            self.assertEqual(abandon_card_route(documents(), pending=False, recorded_pass=True,
                             refusal=NO_TRIAL), ['completion'])
            self.assertEqual(abandon_card_route(documents(), pending=False,
                             refusal=NO_TRIAL), ['Help'])
            # 22c: the guides quote the refusal the tools print now, never version 2's.
            for page in ('INSTALL-PROCEDURES.md', 'EMERGENCY.md'):
                self.assertIn('`' + NO_TRIAL + '`', documents()[page])
                self.assertNotIn('Missing private layout-pending record', documents()[page])
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
        # 15e read release 13's image; that evidence stays release 13's.
        release = json.loads((ROOT/'os/manifest/releases/13.json').read_text())
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
        previous = json.loads((ROOT/'os/manifest/releases/13.json').read_text())['reference']
        self.assertIn('**R27 (current):** `' + current + '`', text)
        self.assertIn('**R13 (previous):** `' + previous + '`', text)
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
                 '**Tools updated from version**',
                 # 22c: the tools-only update ends after check and title, before any stage.
                 '**Tools only**', '```bash\n' + commands['check'] + '\n' + commands['title'] + '\n```', pass_line('check'),
                 pass_line('title'), '**Boot menu at the next start:**', 'unplug it', 'no stage, no restart',
                 '[Return to step 8](#8-everyday-boot-and-recovery)',
                 commands['update'], pass_line('update'), '**Signed exact release staged**',
                 '**… is removed when the update finishes at shutdown**',
                 "**The new release starts with this system's settings (Wi-Fi, passwords, layout), not …'s**",
                 commands['title'], commands['export'], 'SAFE TO REMOVE ARESTOOLS',
                 '**Boot menu after the update finishes at shutdown (expected):**', commands['reboot'], pass_line('reboot'),
                 '10-minute rule', '**F12** (or **Fn+F12**) → **Bazzite**', commands['check'], commands['title'],
                 commands['records'], pass_line('check'), '**Update to … confirmed after the restart**',
                 '**Update to … was not applied: the deployments are as before it, and nothing is waiting**',
                 '**Update to … is in place and has not started yet**', '**… did not finish as recorded**',
                 'sudo passwd ares', commands['previous'], pass_line('previous'), '**Return to … confirmed after the restart**',
                 '**forward again**',
                 # 22c: forward again after previous, and back from plain Bazzite, with no download and,
                 # since review 4, never a new release.
                 '**Forward again, or back from plain Bazzite**', 'it never installs a release',
                 # Review 5: update only where the running system does not start next, read from check.
                 'so this box runs update only where that is not so', '`' + commands['check'] + '`',
                 '  - **plain Bazzite …**', '**this start was not the default**', '  - **older AresOS … runs and starts next**',
                 'do **not** run update here', commands['reboot'], pass_line('reboot'), '**newer AresOS**',
                 '  - **newer AresOS … runs and starts next**',
                 '```bash\n' + commands['update'] + '\n' + commands['title'] + '\n```',
                 pass_line('update'), pass_line('title'), 'No stick, no login and no network',
                 '  - **Newest AresOS starts next** or **Newest installed AresOS starts next**', '**starts next, after the restart**',
                 commands['reboot'], pass_line('reboot'), '**Update to … confirmed after the restart**',
                 '  - **… already starts next; nothing changed**', '  - **The release of these tools is newer still**',
                 '**previous**', '**Return to … confirmed after the restart**',
                 '**Record:**', '[Return to step 8](#8-everyday-boot-and-recovery)')
        position = 0
        for value in order:
            found = route.find(value, position)
            self.assertGreaterEqual(found, 0, value)
            position = found + len(value)
        boxes = [line for line in route.splitlines() if line.startswith('- [ ]')]
        # Windows, tools, tools only, stage, title and stick, restart, check, password, misbehaves, forward again.
        self.assertEqual(len(boxes), 10)
        self.assertTrue(boxes[2].startswith('- [ ] **Tools only**') and boxes[-1].startswith('- [ ] **Forward again'))
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
        # 22c: the paragraph on three deployments says what works now, and what the old tools' STOP means.
        intro = route.split('- [ ]', 1)[0]
        for value in ('current AresOS as rollback', 'corrected stock pinned', 'three systems are installed',
                      '**newer AresOS**', '**older AresOS**', '**plain Bazzite**', 'works from every installed system',
                      'never creates or deletes one', 'forward again', 'back from plain Bazzite', '**rollback** (on an AresOS)',
                      '**keep-stock** (on plain Bazzite)', 'Layout trials work', "boot menu's rows",
                      '**Expected exact stock/AresOS pair**', '**install the current tools first**', 'tools-only box',
                      '(INSTALL-PROCEDURES.md#recovery-menu)', '(INSTALL-PROCEDURES.md#what-you-notice-on-each-system)',
                      '**Another owner command is running**'):
            self.assertIn(value, intro)
        for value in ('provisional', 'INVALID', '[Failed or bad update](EMERGENCY.md#failed-or-bad-update)',
                      'take only a row your last title named', 'never repeat the update without Help',
                      '**interrupted before its result was recorded; do not reboot**',
                      'Help decides each repeat', 'STOPs while anything uses the installed tools',
                      'a STOP always leaves working tools in place', '**Newest installed AresOS starts next**'):
            self.assertIn(value, route)
        # Rule 5 replaced these; the guide never quotes them again (PLAN-GAP 4 of stage 1b, step 1).
        for value in ('did not finish at the restart', 'three deployments', 'refuse with three', 'guessed GRUB title'):
            self.assertNotIn(value, route)
        # The quoted tool messages are the ones the tools print.
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("' did not finish as recorded ('", "'Another owner command is running;",
                      "' was interrupted before its result was recorded; do not reboot; run '",
                      "'An owner command of the installed tools is running (pid '",
                      "' confirmed after the restart'", "'Previous AresOS queued for the next start '",
                      "'Signed exact release staged '", "'Running release stays as rollback '", "'Tools updated from version '",
                      "' was not applied: the deployments are as before it, and nothing is waiting'",
                      "' is in place and has not started yet'", "' already starts next; nothing changed'",
                      "'It runs now'", "'It does not run yet: it starts at the next restart'",
                      "'Newest AresOS starts next '", "'Newest installed AresOS starts next '",
                      "'The release of these tools is newer still and is not installed ('",
                      "' is removed when the update finishes at shutdown'",
                      "\"The new release starts with this system's settings (Wi-Fi, passwords, layout), not \"",
                      "' runs and starts next'", "' starts next, after the restart'", "' starts next; this start was not the default'",
                      "'Boot menu at the next start: '", "'Boot menu after the update finishes at shutdown (expected): '",
                      "'update to '", "'return to '"):
            self.assertIn(value, source)
        self.assertNotIn(' did not finish at the restart', source)
        # The line the guide explains is version 2's, the tools on the laptop until 22c's are installed.
        version2 = subprocess.check_output(['git', 'show', '41b06513:os/owner-tools/payload/owner.py'], cwd=ROOT).decode()
        self.assertIn("'Expected exact stock/AresOS pair'", version2)
        self.assertNotIn('INSTALL.md#5-', route)

    def test_failed_update_card_checks_first_then_previous_only_where_the_update_is_in_place(self):
        """22c, C, and review 4 (finding 1): the failed-update card. A new AresOS that does not start:
        the boot-menu row the last title named for the AresOS before the update; one that misbehaves, or
        the old one returning by itself: stay. Then check first, however Linux started, and previous only
        where check shows the update in place; never after "was not applied". Then rollback, then Windows.
        Changed on purpose from package 22's "Windows first, never a GRUB title" (rules 4, 5 and 8 make
        every row safe) and from stage 1b's "the titled row, then previous" (review 4: if the update did
        not finish at shutdown, that row is another system and previous goes one release further back)."""
        texts = documents()
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        card = section(texts['EMERGENCY.md'], 'failed-or-bad-update')
        for value in ('Windows Boot Manager', commands['previous'], pass_line('previous'), commands['reboot'],
                      pass_line('reboot'), '**Bazzite**', '(INSTALL-PROCEDURES.md#recovery-menu)',
                      'take the row your last title named for the AresOS that ran before the update',
                      '**Boot menu after the update finishes at shutdown (expected):**', 'or the old AresOS returns by itself',
                      'Whatever started, and however', '`' + commands['check'] + '` **first**, never previous before it',
                      '**Previous AresOS queued for the next start**', '**Return to … confirmed after the restart**',
                      '**newer AresOS … runs and starts next**', 'with that confirmation in your record',
                      '**this start was not the default**', 'the AresOS from before the update starts again',
                      'choose the row the last title named', 'any row is safe',
                      'Do **not** run previous: it would go one release further back', 'Help decides each repeat',
                      '**did not finish as recorded**', '**interrupted before its result was recorded**',
                      'repeat the update without Help', '**Expected exact stock/AresOS pair**', 'install the current tools first',
                      '(INSTALL-PROCEDURES.md#rollback-from-running-aresos)', '10-minute wait',
                      '(INSTALL.md#8-everyday-boot-and-recovery)', '(INSTALL.md#update-aresos-to-a-new-release)'):
            self.assertIn(value, card)
        # The titled row; check before anything; previous where the update is in place or the new one runs;
        # never after "was not applied"; then rollback, then Windows.
        positions = [card.index(value) for value in (
            'the row your last title named', commands['check'], '- **Update to … is in place and has not started yet**',
            commands['previous'], '- **Update to … confirmed after the restart**', 'It misbehaves: **previous** the same way',
            '- **Update to … was not applied**', 'Do **not** run previous', '**rollback** to plain Bazzite',
            '**Windows Boot Manager**')]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(card.count(commands['previous']), 1)
        not_applied = next(line for line in card.splitlines() if line.startswith('- **Update to … was not applied**'))
        self.assertNotIn(commands['previous'], not_applied)
        for value in ('did not finish at the restart', 'guessed GRUB title', 'three deployments', 'they refuse',
                      'That AresOS starts: tty3', 'misbehaves: **previous** first'):
            self.assertNotIn(value, card)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("' was not applied: the deployments are as before it, and nothing is waiting'",
                      "' is in place and has not started yet'", "' confirmed after the restart'", "'update to '",
                      "'return to '", "'Previous AresOS queued for the next start '", "' runs and starts next'",
                      "' starts next; this start was not the default'", "'newer AresOS'",
                      "' did not finish as recorded ('", "' was interrupted before its result was recorded; do not reboot; run '"):
            self.assertIn(value, source)
        # The update route's boxes with the same way back: check first, never previous after "was not applied".
        route = section(texts['INSTALL.md'], UPDATE)
        applied = next(line for line in route.splitlines() if line.startswith('  - **Update to … was not applied'))
        self.assertIn('Do **not** run previous (it would go one release further back)', applied)
        misbehaves = next(line for line in route.splitlines() if line.startswith('- [ ] **If the new release misbehaves**'))
        for value in ('`' + commands['check'] + '` first', 'Run previous only on the newer release this route installed',
                      '**Update to … confirmed after the restart**', '**newer AresOS … runs and starts next**',
                      'with that confirmation in your record', '**was not applied**', '(EMERGENCY.md#failed-or-bad-update)',
                      'never previous'):
            self.assertIn(value, misbehaves)
        # The procedures say what works now with three installed systems.
        menu = section(texts['INSTALL-PROCEDURES.md'], 'recovery-menu')
        for value in ('**three rows after it, which differ only in `(ostree:N)`**', '**Boot menu at the next start:**',
                      '**Take the row the last title named**', 'A wrong choice is harmless', commands['check'],
                      'what runs and what starts next', 'every command still works', '(#keep-stock)',
                      '(#back-to-aresos-from-stock)', 'Never rollback from plain Bazzite', '**Expected exact stock/AresOS pair**',
                      'Install the current tools first', 'A failed **first** switch boot', '**Windows → Help**',
                      'that check comes first after any boot-menu choice', '**Update to … was not applied**',
                      'previous would then go one release further back', '(EMERGENCY.md#failed-or-bad-update)'):
            self.assertIn(value, menu)
        layout = section(texts['INSTALL-PROCEDURES.md'], 'later-layout').split('### Layout revert', 1)[0]
        for value in ('**Each installed system keeps its own layout**', 'a running AresOS that starts next',
                      "**Plain Bazzite keeps the installer's German layout: no layout trial here**",
                      '**Expected exact stock/AresOS pair**', 'install the current tools first'):
            self.assertIn(value, layout)
        self.assertIn('"Plain Bazzite keeps the installer\'s German layout: no layout trial here; "', source)
        for anchor in ('recovery-menu', 'later-layout'):
            self.assertNotIn('three deployments', section(texts['INSTALL-PROCEDURES.md'], anchor))
        console = section(texts['INSTALL-REFERENCE.md'], 'console')
        self.assertIn('[update](INSTALL.md#update-aresos-to-a-new-release)', console)
        self.assertIn('[back to AresOS from stock](INSTALL-PROCEDURES.md#back-to-aresos-from-stock)', console)
        hang = section(texts['INSTALL-REFERENCE.md'], 'hung-shutdown-or-restart')
        self.assertIn('[update route](INSTALL.md#update-aresos-to-a-new-release)', hang)

    def test_failed_update_card_routes_every_traced_case_to_the_aresos_from_before_the_update(self):
        """Review 4, finding 1, traced as the reviewer did: in the reference ledger (ways_back_ledger, which
        the model test holds to the tools on every reachable edge), every update the model stages, both
        ends of its shutdown (finished, or lost with the staged release discarded) and every boot-menu row,
        including the row the provisional title named for the AresOS before the update and no choice.
        The card's branch for what check shows ends on the AresOS from before the update, or on the new
        release when it runs and works; the stage 1b card (previous straight after the boot) does not."""
        import ways_back_ledger as ledger
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        card = section(documents()['EMERGENCY.md'], 'failed-or-bad-update')
        quotes = {'in-place-not-started': '- **Update to … is in place and has not started yet**',
                  'target-boot-confirmed': '- **Update to … confirmed after the restart**',
                  'not-applied': '- **Update to … was not applied**'}
        branch = {outcome: next(line for line in card.splitlines() if line.startswith(quote)) for outcome, quote in quotes.items()}
        back = (commands['previous'], '**Previous AresOS queued for the next start**', commands['reboot'],
                'no choice', '**Return to … confirmed after the restart**')
        positions = [branch['in-place-not-started'].index(value) for value in back]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('It misbehaves: **previous** the same way', branch['target-boot-confirmed'])
        self.assertNotIn(commands['previous'], branch['not-applied'])
        restart = branch['not-applied'].index(commands['reboot'])
        self.assertLess(branch['not-applied'].index('**this start was not the default**'), restart)
        self.assertLess(restart, branch['not-applied'].index('no choice'))

        def run(state, events):
            confirmed = False
            for event in events:
                result = ledger.transition(state, event)
                self.assertFalse(result.stop, (event, state))
                state, confirmed = result.state, confirmed or result.confirmation
            return state, confirmed

        # previous, save the title, reboot, F12 → Bazzite with no choice, check.
        previous = [('previous', 'full'), ('title', 'full'), ('restart', 'default'), ('check', 'full')]
        traced, wrong_before = 0, []
        for start in ledger.starts():
            staged = ledger.transition(start, ('update', 'full')).state
            if not staged.stage:
                continue
            before = staged.running
            for finish in ('restart', 'power-off'):
                rows = (staged.stage, staged.running, 'S') if finish == 'restart' else staged.rows[1:]
                for choice in ('default', *rows):
                    booted = ledger.transition(staged, (finish, choice)).state
                    outcome = booted.outcome()
                    self.assertIn(outcome, branch, (finish, choice, booted))
                    checked = ledger.transition(booted, ('check', 'full'))
                    self.assertFalse(checked.stop)
                    cases = [(False, booted.running if outcome == 'target-boot-confirmed' else before)]
                    if outcome == 'target-boot-confirmed':
                        cases.append((True, before))
                    for misbehaves, intended in cases:
                        with self.subTest(start=start.rows, bundle=start.bundle, finish=finish, choice=choice, misbehaves=misbehaves):
                            if outcome == 'not-applied':
                                events = [('restart', 'default')] if booted.running != booted.rows[0] else []
                            elif outcome == 'in-place-not-started' or misbehaves:
                                events = previous
                            else:
                                events = []  # it works after all: the update route's check box
                            end, confirmed = run(checked.state, events)
                            self.assertEqual((end.running, end.rows[0]), (intended, intended))
                            self.assertEqual(confirmed, events == previous)
                            traced += 1
                    # Stage 1b's card: previous straight after the boot of the row the provisional title
                    # named for the AresOS before the update ((ostree:1), the second row), without check first.
                    if choice == rows[1]:
                        old = ledger.transition(booted, ('previous', 'full'))
                        if not old.stop and ledger.transition(old.state, ('restart', 'default')).state.rows[0] != before:
                            wrong_before.append((start.rows, start.bundle, finish, choice))
        # Four starts stage (13+S with bundle 27 or 28, 27+13+S and 27+S with 28). A finished shutdown:
        # no choice and each of its three rows, the new release's two ways counted twice (6 each); a
        # lost one: no choice and each row as before (4 from three rows, 3 from two).
        self.assertEqual(traced, 4 * 6 + 4 + 3 * 3)
        # The revert: review 4's case, an update from three installed systems whose finish was lost.
        self.assertEqual(wrong_before, [(('27', '13', 'S'), '28', 'power-off', '13')])

    def forward_box(self, texts):
        """The box "Forward again, or back from plain Bazzite" and its dispatch on check's running line."""
        route = section(texts['INSTALL.md'], UPDATE)
        start = route.index('- [ ] **Forward again, or back from plain Bazzite**')
        box = route[start:route.index('**Record:**', start)]
        bullets = box.split('```bash', 1)[0].splitlines()
        dispatch = dict(block=next(line for line in bullets if line.startswith('  - **plain Bazzite …**')),
                        first=next(line for line in bullets if line.startswith('  - **older AresOS … runs and starts next**')),
                        done=next(line for line in bullets if line.startswith('  - **newer AresOS … runs and starts next**')))
        return box, dispatch

    @staticmethod
    def running_line(state):
        """Which of the box's cases check's running line is (rule 8's standing line, in the ledger's terms)."""
        releases = sorted(row for row in state.rows if row != 'S')
        if state.running == 'S' or state.running != state.rows[0]:
            return 'block'  # "plain Bazzite …", or "… runs; … starts next; this start was not the default"
        if state.outcome() == 'selection-applied' or len(releases) != 2:
            return 'help'  # "… runs and now starts next; no restart is waiting", or one release: anything else
        return 'first' if state.running == releases[0] else 'done'

    def test_forward_and_back_box_never_installs_a_release(self):
        """Reviews 4 and 5: the box "Forward again, or back from plain Bazzite" never stages. update runs
        there only where check's running line shows plain Bazzite or a system that does not start next;
        forward again from the older AresOS that starts next first takes the newer AresOS's boot-menu row
        (review 5's two-step path); "The release of these tools is newer still" is not followed. Traced in
        the reference ledger from every idle state of the destination commands, whether or not the tools'
        release is installed (no check or title line names it)."""
        import ways_back_ledger as ledger
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        texts = documents()
        box, dispatch = self.forward_box(texts)
        for value in ('This box only chooses between installed systems; it never installs a release',
                      'Update could stage one only on an AresOS that runs and starts next (if the release of your tools '
                      'is not installed, which no line shows before update runs), so this box runs update only where that '
                      'is not so', 'First `' + commands['check'] + '`, then go by its line naming what runs'):
            self.assertIn(value, box)
        self.assertNotIn('the last update route you followed finished', box)
        self.assertIn('a line ending **this start was not the default**', dispatch['block'])
        self.assertIn('run the block below', dispatch['block'])
        first = dispatch['first']
        positions = [first.index(value) for value in ('do **not** run update here', commands['reboot'], pass_line('reboot'),
                     '**Bazzite**', '(INSTALL-PROCEDURES.md#recovery-menu)', '**Boot menu at the next start:**',
                     '**newer AresOS**', 'start this box over with check')]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn(commands['update'], first)
        for value in ('nothing to do', 'Anything else → **STOP → [Help](INSTALL-REFERENCE.md#help)**'):
            self.assertIn(value, dispatch['done'])
        self.assertLess(box.index(dispatch['done']), box.index('```bash\n' + commands['update']))
        newer = next(line for line in box.splitlines() if line.startswith('  - **The release of these tools is newer still**'))
        for value in ('(after either line)', 'do **not** follow it here', 'without its announcement',
                      'This box ends once the installed release runs', "with the maintainer's announcement"):
            self.assertIn(value, newer)
        self.assertNotIn(commands['update'], newer)
        self.assertNotIn('follow it.', section(texts['INSTALL.md'], UPDATE))
        back = section(texts['INSTALL-PROCEDURES.md'], 'back-to-aresos-from-stock')
        for value in ('This way never installs a release', '**The release of these tools is newer still**',
                      'do not follow that line here', "with the maintainer's announcement"):
            self.assertIn(value, back)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("'The release of these tools is newer still and is not installed ('",
                      "('run ' if newest is booted else 'restart, then run ') + typed('update') + ' again'",
                      "if booted is shape['stock'] or rows[0] is not booted:", "' runs and now starts next; no restart is waiting'"):
            self.assertIn(value, source)

        traced = collections.Counter()
        for state in destination_space(ledger):
            releases = sorted(row for row in state.rows if row != 'S')
            if state.stage or state.trial or state.outcome() in ('waiting', 'retry', 'complete') or not (state.running == 'S' or len(releases) == 2):
                continue
            with self.subTest(state=state):
                case = self.running_line(state)
                here = state
                if case == 'first':
                    # Why the box never runs update here: without the tools' release installed it stages at once.
                    traced['first step; update at once would stage' if ledger.transition(state, ('update', 'full')).state.stage
                           else 'first step; update at once would reorder'] += 1
                    here = ledger.transition(ledger.transition(state, ('check', 'full')).state, ('restart', releases[-1])).state
                    case = self.running_line(here)
                    self.assertEqual((case, here.running), ('block', releases[-1]))
                if case in ('done', 'help'):
                    traced[case] += 1
                    continue
                traced['block from plain Bazzite' if here.running == 'S' else 'block where the running system is not the default'] += 1
                update = ledger.transition(ledger.transition(here, ('check', 'full')).state, ('update', 'full'))
                self.assertFalse(update.stop or update.state.stage)
                after = update.state
                changed = after.journal is not None and after.journal.word == 'update' and after.rows != here.rows
                if changed or after.running != after.rows[0]:
                    after = ledger.transition(ledger.transition(after, ('title', 'full')).state, ('restart', 'default')).state
                titled = ledger.transition(after, ('title', 'full'))
                self.assertFalse(ledger.transition(after, ('check', 'full')).stop)
                newest = max(row for row in here.rows if row != 'S')
                self.assertEqual((after.running, after.rows[0]), (newest, newest))
                if changed:
                    self.assertTrue(titled.confirmation)
                if state.bundle not in releases:
                    # update printed "newer still"; following it (restart unless the newest runs, then
                    # update again) stages that release without its announcement.
                    following = update.state if update.state.running == newest else ledger.transition(update.state, ('restart', 'default')).state
                    self.assertTrue(ledger.transition(following, ('update', 'full')).state.stage)
                    traced['newer still: following it would stage'] += 1
                if state.running == 'S':
                    self.assertFalse(ledger.transition(state, ('previous', 'full')).state.stage)
        self.assertEqual(set(traced), {'first step; update at once would stage', 'first step; update at once would reorder',
                                       'block from plain Bazzite', 'block where the running system is not the default',
                                       'done', 'help', 'newer still: following it would stage'}, traced)

    def test_forward_again_after_a_failed_update_a_stock_return_and_previous_never_stages(self):
        """Review 5, finding 1, the connected sequence: tools of release 28 installed, its update's finish
        lost (27, 13 and plain Bazzite stay); rollback to plain Bazzite and back with update (confirmed);
        later previous to 13. Forward again by the box: check shows the older AresOS running and starting
        next, so the newer AresOS's boot-menu row first, then update, which only reorders: 27 runs and
        starts next, confirmed, 28 is not staged. Round 3's box (update at once) staged 28 and the restart
        removed 27."""
        import ways_back_ledger as ledger
        _, dispatch = self.forward_box(documents())

        def run(state, *events):
            for event in events:
                result = ledger.transition(state, event)
                self.assertFalse(result.stop, (event, state))
                state = result.state
            return state

        start = next(s for s in ledger.starts() if s.bundle == '28' and s.rows == ('27', '13', 'S'))
        state = run(start, ('update', 'full'), ('power-off', 'default'))
        self.assertEqual((state.rows, state.running, state.outcome()), (('27', '13', 'S'), '27', 'not-applied'))
        state = run(state, ('check', 'full'), ('rollback', 'full'), ('title', 'full'), ('restart', 'default'), ('check', 'full'))
        state = run(state, ('update', 'full'), ('title', 'full'), ('restart', 'default'))
        self.assertTrue(ledger.transition(state, ('title', 'full')).confirmation)  # "Update to … confirmed": not proof of 28
        state = run(state, ('check', 'full'), ('previous', 'full'), ('title', 'full'), ('restart', 'default'), ('check', 'full'))
        self.assertEqual((state.rows, state.running), (('13', '27', 'S'), '13'))
        # Round 3's box: update at once stages 28, and the shutdown keeps 28, 13 and plain Bazzite: 27 is gone.
        staged = ledger.transition(state, ('update', 'full')).state
        self.assertEqual((staged.stage, ledger.transition(staged, ('restart', 'default')).state.rows), ('28', ('28', '13', 'S')))
        # This box: check's running line is "older AresOS … runs and starts next", the first step.
        self.assertEqual(self.running_line(state), 'first')
        self.assertIn('do **not** run update here', dispatch['first'])
        state = run(state, ('restart', '27'))
        self.assertEqual((self.running_line(state), state.running, state.rows[0]), ('block', '27', '13'))
        update = ledger.transition(run(state, ('check', 'full')), ('update', 'full'))
        self.assertFalse(update.stop or update.state.stage)
        state = run(update.state, ('title', 'full'), ('restart', 'default'))
        titled = ledger.transition(state, ('title', 'full'))
        self.assertTrue(titled.confirmation)
        self.assertEqual((state.rows, state.running, state.stage), (('27', '13', 'S'), '27', ''))

    def test_a_return_that_changes_nothing_completes_without_a_confirmation(self):
        """Review 4, finding 3: when the system a command names already starts next, the tools write no
        journal (rule 4), so no "… confirmed after the restart" can follow. The guides tell the two apart:
        after a change, the confirmation; after nothing to do, PASS check with that system running and
        starting next. Traced in the reference ledger for update, previous, rollback and keep-stock."""
        import ways_back_ledger as ledger
        texts = documents()
        route = section(texts['INSTALL.md'], UPDATE)
        start = route.index('- [ ] **Forward again, or back from plain Bazzite**')
        box = route[start:route.index('**Record:**', start)]
        change = next(line for line in box.splitlines() if line.startswith('  - **Newest AresOS starts next**'))
        nothing = next(line for line in box.splitlines() if line.startswith('  - **… already starts next; nothing changed**'))
        self.assertIn('`PASS check` must show **Update to … confirmed after the restart**', change)
        for value in ('nothing was recorded, so no confirmation line is needed (one can still appear for an earlier change)',
                      '**It runs now**',
                      '**It does not run yet: it starts at the next restart**', 'no boot-menu choice',
                      '`PASS check` showing that AresOS with **… runs and starts next**'):
            self.assertIn(value, nothing)
        self.assertNotIn('confirmed after the restart', nothing)
        self.assertNotIn('no confirmation line follows', texts['INSTALL.md'] + texts['INSTALL-PROCEDURES.md'])
        self.assertIn('**Previous AresOS queued for the next start**, and after the restart its check shows '
                      '**Return to … confirmed after the restart**; or **… already starts next; nothing changed**, '
                      'complete as above', box)
        procedures = texts['INSTALL-PROCEDURES.md']
        back = section(procedures, 'back-to-aresos-from-stock')
        self.assertIn('When the command changed nothing (**… already starts next; nothing changed**), nothing was recorded '
                      'and no confirmation is needed: **PASS** is then `PASS check` showing that AresOS with '
                      '**… runs and starts next**', back)
        # check prints its console lines before the title's: "check's first line" named the wrong line (round 3).
        self.assertNotIn('whose first line', texts['INSTALL.md'] + texts['INSTALL-PROCEDURES.md'])
        rollback = section(procedures, 'rollback-from-running-aresos')
        for value in ('**Plain Bazzite … already starts next; nothing changed**', '**It does not run yet: it starts at the next restart**',
                      'no confirmation line is needed', '`PASS check` with **plain Bazzite … runs and starts next**',
                      '(after nothing changed, no confirmation is needed'):
            self.assertIn(value, rollback)
        keep = section(procedures, 'keep-stock')
        self.assertIn('(after a boot-menu choice with **Change to … confirmed after the restart**)', keep)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("' already starts next; nothing changed'", "'It runs now'", "'It does not run yet: it starts at the next restart'",
                      "' runs and starts next'", "'plain Bazzite'", 'Already first: nothing changes and no journal is written'):
            self.assertIn(value, source)

        traced = collections.Counter()
        for state in destination_space(ledger):
            if state.stage or state.trial or state.outcome() in ('waiting', 'retry', 'complete'):
                continue
            releases = [row for row in state.rows if row != 'S']
            # An earlier change still open (in place, not started) may confirm itself at that start.
            open_change = state.outcome() not in ('none', 'not-applied')
            for word, target in (('update', max(releases)), ('previous', min(releases)), ('rollback', 'S'), ('keep-stock', 'S')):
                result = ledger.transition(state, (word, 'full'))
                if result.stop or result.state.stage:
                    continue  # a refusal with nothing changed, or (update) the gated stage box
                with self.subTest(state=state, word=word):
                    after = result.state
                    unchanged = after.rows == state.rows and (after.journal is None if state.outcome() == 'not-applied'
                                                              else after.journal == state.journal)
                    if not unchanged:
                        self.assertEqual(after.journal.word, word)
                    # A change: always the restart with no choice. Nothing changed: a restart only for
                    # "It does not run yet"; "It runs now" is there already.
                    if not unchanged or after.running != after.rows[0]:
                        after = ledger.transition(after, ('restart', 'default')).state
                    titled = ledger.transition(after, ('title', 'full'))
                    self.assertFalse(ledger.transition(after, ('check', 'full')).stop)
                    self.assertEqual((after.running, after.rows[0]), (target, target))
                    if unchanged:
                        # Only an earlier change that is still open can confirm itself here.
                        self.assertTrue(open_change or not titled.confirmation)
                        traced[word + ': nothing changed' + ('' if titled.confirmation else ', no confirmation')] += 1
                    else:
                        self.assertTrue(titled.confirmation)
                        traced[word + ': confirmed'] += 1
        for word in ('update', 'previous', 'rollback', 'keep-stock'):
            self.assertGreater(traced[word + ': confirmed'], 0, traced)
            self.assertGreater(traced[word + ': nothing changed, no confirmation'], 0, traced)

    def test_stock_procedures_go_back_to_aresos_and_never_update_bazzite(self):
        """22c, C: rollback and keep-stock beside two releases, the new way back from stock, and the
        notice list, each with the sentence about Bazzite's own updates."""
        texts = documents()
        procedures = texts['INSTALL-PROCEDURES.md']
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        back = section(procedures, 'back-to-aresos-from-stock')
        keep = section(procedures, 'keep-stock')
        notice = section(procedures, 'what-you-notice-on-each-system')
        for block in (back, keep, notice):
            self.assertIn(NO_BAZZITE_UPDATE, block)
        self.assertNotIn('until the owner chooses stock permanently', procedures)
        self.assertIn('[step 9](INSTALL.md#9-retire-access-and-return-to-windows)', keep)
        # Back from stock: the update route's last box, behind its gate; no fenced update outside it.
        for value in ('**update** the newest AresOS', '**previous** the older one', 'no stick, no login and no network',
                      '**Forward again, or back from plain Bazzite**', '(INSTALL.md#update-aresos-to-a-new-release)',
                      'STEP 5 COMPLETE', '**Update to … confirmed after the restart**', '**A Bazzite update is waiting. Do not restart**',
                      'STOP → [Help](INSTALL-REFERENCE.md#help)', 'Return to step 8'):
            self.assertIn(value, back)
        self.assertNotIn('```bash\n' + commands['update'], back)
        route = section(texts['INSTALL.md'], UPDATE)
        self.assertIn('- [ ] **Forward again, or back from plain Bazzite**', route)
        for value in ('**Saved stock is default**', '**plain Bazzite … runs and now starts next; no restart is waiting**',
                      '**Plain Bazzite … already starts next; nothing changed**', '**It runs now**',
                      '**Bazzite must not update while AresOS is installed**', '(#back-to-aresos-from-stock)',
                      '**Change to … confirmed after the restart**', '**WARNING: … Bazzite must not update while AresOS is installed**',
                      '**Expected exact stock/AresOS pair**'):
            self.assertIn(value, keep)
        rollback = section(procedures, 'rollback-from-running-aresos')
        for value in ('newer or the older one', '**Saved stock rollback queued**',
                      '**… runs; plain Bazzite … starts next, after the restart**', 'every AresOS still installed',
                      '**Plain Bazzite runs here: use … keep-stock**', '**Rollback to … confirmed after the restart**',
                      '(#back-to-aresos-from-stock)', '**Expected exact stock/AresOS pair**'):
            self.assertIn(value, rollback)
        for value in ('**Your files in your home folder stay**', '**its own passwords, Wi-Fi and keyboard layout**',
                      '**Plain Bazzite** has no `ares` account', '**German**',
                      '**The AresOS from before your first update** (release 13) has no `ares` password and no administrator rights',
                      'A later update starts the new release with the settings of the system it runs on',
                      'packages 34 and 35', 'stays empty until you go forward again with update', 'Nothing is lost'):
            self.assertIn(value, notice)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("'Saved stock is default'", "'Saved stock rollback queued'", "' runs and now starts next; no restart is waiting'",
                      "'Plain Bazzite runs here: use '", "'. Bazzite must not update while AresOS is installed: run '",
                      "'A Bazzite update is waiting. Do not restart: the restart deletes {}. Get help.'", "'change to '", "'rollback to '",
                      "'The trial began on another system and its finish had started: run '",
                      "\"This system's half-written layout is restored to the settings before its trial\""):
            self.assertIn(value, source)

    def test_status_names_22c_built_not_rehearsed_and_not_on_the_laptop(self):
        status = documents()['INSTALL-STATUS.md']
        fingerprint = hashlib.sha256((ROOT/'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest()
        row = next(line for line in status.splitlines() if line.startswith('| Ways back after an update (package 22c) |'))
        for value in ('**BUILT AND REVIEWED; NOT REHEARSED YET; NOT ON THE LAPTOP**', "the laptop's tools stay `851eb742…`",
                      '`' + fingerprint + '`', '(../reviews/22c-ways-back-after-update/REPORT.md)', '**Not rehearsed yet:**',
                      'tools-only update', '**Before this row may say "on the laptop":**', 'the owner installs these tools',
                      'calm test', "the title's row map", 'stays OPEN'):
            self.assertIn(value, row)
        update = next(line for line in status.splitlines() if line.startswith('| Update route (packages 22 and 27) |'))
        self.assertIn("the laptop's tools until the owner installs package 22c's", update)
        self.assertNotIn(fingerprint, update)
        menu = next(line for line in status.splitlines() if line.startswith('| LOQ shortcuts and recovery menu |'))
        self.assertIn('**OPEN**', menu)

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
