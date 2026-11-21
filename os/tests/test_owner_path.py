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
SAVE_HOME = 'save-the-minecraft-home-before-restarting'
INSTALL_HOLD = '**STOP for a fresh install or reinstall.**'
STICK_EXPORT = 'SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart'
LOCAL_EXPORT = 'Tools stick absent: records copied to /run/ares-records with SHA256 readback'
UPDATE_GATE = ('**Update gate: require STEP 5 COMPLETE and a checked running AresOS '
               'before authentication or updating.**')
SENSITIVE = re.compile(r'^sudo /var/lib/ares/at (?:login|switch|update)$')
LINK = re.compile(r'(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)')
# Packages 27b and 22d: the laptop's update records in INSTALL-STATUS. Each
# clause is pinned whole, between its neighbours, so no word in it or next to
# it changes unnoticed: (line start, before, clause, after); an empty after
# means the clause ends the line.
STEP8_RECORD = (
    ('This is the **single current gate/status table**', 'table**, ',
     "as of **2026-11-17**, based on the retained reports, the owner decision in brief 16, the maintainer's checks "
     "of Stage A's and Stage B's records, the step 4 result supplied in brief 15g, the step 5–7 records the "
     "maintainer checked on 2026-11-08/09 and the step 8 update records the maintainer checked on 2026-11-13 "
     "(brief 27b), plus the laptop tools session supplied by the lead on 2026-11-17.",
     ' Historical results'),
    ('- **R13 (previous):**', '13.json)). ',
     "Installed on the laptop at step 6 and ran there until the owner's step 8 update on 2026-11-13; since then "
     "it is the laptop's rollback.",
     ' Its VM evidence'),
    ('- **R27 (on the laptop):**', 'REPORT.md)). ',
     "The laptop runs it since 2026-11-13, reached through the step 8 "
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
     "the laptop. Version 4, installed on 2026-11-17, brings package 22c's stock rollback, keep-stock, recovery-menu "
     "and layout-trial procedures after an update, as the "
     "[step 8 update route](INSTALL.md#update-aresos-to-a-new-release) says (next row). "
     "Raw records stay private and off this public repository.",
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
    """Every state of the reference ledger that update, forward, previous, rollback, keep-stock, title,
    each restart and each lost finish reach from the model's starts (758 states; no cut, no layout
    trial). Since update only stages, forward is what reaches most returns (427 states without it)."""
    reached, todo = set(), list(ledger.starts())
    while todo:
        state = todo.pop()
        if state in reached:
            continue
        reached.add(state)
        restarts = (state.stage, state.running, 'S') if state.stage else state.rows
        events = [(word, 'full') for word in ('update', 'forward', 'previous', 'rollback', 'keep-stock', 'title')]
        events += [('restart', row) for row in ('default', *restarts)]
        events += [('power-off', row) for row in ('default', *state.rows[1:])] if state.stage else []
        todo += [result.state for result in (ledger.transition(state, e) for e in events) if not result.stop and not result.cut]
    assert len(reached) == 758, len(reached)
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
    boot_check = section(texts['INSTALL.md'], 'run-at-check')
    if commands['check'] not in boot_check or pass_line('check') not in boot_check:
        raise AssertionError('The shared boot check must invoke check and require its PASS')
    if '(INSTALL.md#run-at-check)' not in finished or 'INSTALL.md#8-everyday-boot-and-recovery' not in finished:
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
    if ('(INSTALL.md#run-at-check)' not in ares or 'INSTALL.md#8-everyday-boot-and-recovery' not in ares
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
        prompt = step4.split('Look for **Windows baseline Micron serial:**', 1)[1].split('Require `PASS install`', 1)[0]
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
        for value in ('was released on 2026-11-07 for the checked installer', 'Step 4 PASSED 2026-11-08', 'Step 5 COMPLETE 2026-11-09',
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
        before = '[run the boot check](INSTALL.md#run-at-check) and require `PASS check`, prove confirmed-layout password/text typing, then [Return to step 8](INSTALL.md#8-everyday-boot-and-recovery)'
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
                            ('Stage B — fitting','CHECKED 2026-11-07')):
            row=next(line for line in status.splitlines() if line.startswith('| '+label+' |'))
            self.assertIn('**'+state+'**',row)
        c=next(line for line in status.splitlines() if line.startswith('| Stage C —'))
        for term in ('maintainer checked A and B', 'native mounted-child check passed', 'each step'):
            self.assertIn(term,c)
        physical = next(line for line in status.splitlines() if line.startswith('| **Physical installation**'))
        for row in (physical, c):
            self.assertIn(INSTALL_HOLD, row.split('|')[2])
            self.assertIn('Wait until a new installer has been checked.', row)
        update = next(line for line in status.splitlines() if line.startswith('| Signed update on an existing AresOS install'))
        self.assertIn('**Step 8, `at update`**', update)
        self.assertIn(f'(INSTALL.md#{UPDATE})', update)
        self.assertNotIn(INSTALL_HOLD, update.split('|')[2])
        self.assertNotIn('Until it permits physical installation, read only',guide)
        self.assertIn(INSTALL_HOLD, section(guide,'4-install-and-prepare-corrected-stock'))
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
        laptop = json.loads((ROOT/'os/manifest/releases/27.json').read_text())['reference']
        self.assertIn('**R27 (on the laptop):** `' + laptop + '`', text)
        self.assertIn('**R28 (published):** `' + current + '`', text)
        announced, = [line for line in text.splitlines() if line.startswith('- **R28 ')]
        self.assertTrue(announced.endswith('Published privately and rehearsed in the VM on 2026-11-21 (signed-update row below). '
                                           'The laptop update is pending.'))
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
                 # One word per meaning: where update may not stage it names forward, and the last box is forward.
                 '**Update installs a new release only from a running AresOS that starts next**',
                 '**The release of these tools is installed already**', 'Use the last box',
                 '**Title and export:**', commands['title'], commands['export'], pass_line('title'), pass_line('export'),
                 '**With ARESTOOLS:** `' + STICK_EXPORT + '`', 'Unplug the stick.',
                 '**Without ARESTOOLS:** `' + LOCAL_EXPORT + '`', 'Save the new title off the laptop as **provisional**',
                 '**Boot menu after the update finishes at shutdown (expected):**', commands['reboot'], pass_line('reboot'),
                 '10-minute rule', '**F12** (or **Fn+F12**) → **Bazzite**', '(#run-at-check)', pass_line('check'), '**Update to … confirmed after the restart**',
                 '**Update to … was not applied: the deployments are as before it, and nothing is waiting**',
                 '**Update to … is in place and has not started yet**', '**did not finish as recorded**',
                 'sudo passwd ares', '(#return-to-the-older-aresos)',
                 # 22c: forward again after previous, and back from plain Bazzite, never a new release.
                 # One word per meaning: the box runs forward, from every system, with no check-first
                 # dispatch and no boot-menu step (review 5's two-step path is gone with update's reorder).
                 '**Forward again, or back from plain Bazzite**', 'from any system GRUB started',
                 'This box runs **forward**', 'without a stick, login or network',
                 '```bash\n' + commands['forward'] + '\n' + commands['title'] + '\n```',
                 pass_line('forward'), pass_line('title'),
                 '  - **Newest installed AresOS starts next**', '**… runs and now starts next; no restart is waiting**',
                 '**… starts next, after the restart**', commands['reboot'], pass_line('reboot'), 'leave GRUB alone', '**Forward to … confirmed after the restart**',
                 '  - **… already starts next; nothing changed**',
                 '(#return-to-the-older-aresos)',
                 '**Record:**', '[Return to step 8](#8-everyday-boot-and-recovery)')
        position = 0
        for value in order:
            found = route.find(value, position)
            self.assertGreaterEqual(found, 0, value)
            position = found + len(value)
        boxes = [line for line in route.splitlines() if line.startswith('- [ ]')]
        # 22d: the routine box first; then Windows, tools, tools only (the stick route), stage, title and export,
        # restart, check, password, misbehaves, forward again.
        self.assertEqual(len(boxes), 11)
        self.assertTrue(boxes[0].startswith("- [ ] **New tools from Claude's terminal**"))
        self.assertTrue(boxes[1].startswith('- [ ] **Windows side** (the stick route for new tools, second after the routine box'))
        self.assertTrue(boxes[3].startswith('- [ ] **Tools only**') and boxes[-1].startswith('- [ ] **Forward again'))
        self.assertGreaterEqual(route.count('STOP →'), 4)
        self.assertGreaterEqual(route.count('Return to this update route'), 4)
        # A login refusal points to login, then the same update once more.
        refusal = common.owner.LOGIN_REFUSAL.split(':', 1)[0]
        self.assertIn('If it STOPs with `' + refusal + '`:', route)
        after = route.split(refusal, 1)[1]
        order = (commands['login'], '**GitHub username:**', '**Read-only token (hidden):**',
                 pass_line('login'), 'before retrying the same stage command once')
        positions = [after.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        for value in ('read:packages-only', 'Look for **Read-only token (hidden):**. Enter the token', 'before retrying the same stage command once'):
            self.assertIn(value, route)
        password = next(line for line in route.splitlines() if 'sudo passwd ares' in line)
        for value in ('lowercase a–x and top-row digits 0–9', 'German, US International and US',
                      'Never photograph, record or send it', 'keep it private', '`sudo -v`', 'once'):
            self.assertIn(value, password)
        # 22c: the paragraph on three deployments says what works now, and what the old tools' STOP means.
        intro = route.split('- [ ]', 1)[0]
        for value in ('current AresOS as rollback', 'corrected stock pinned', 'three systems are installed',
                      '**newer AresOS**', '**older AresOS**', '**plain Bazzite**', 'works from every installed system',
                      'never creates or deletes one', '**forward** the newest installed AresOS (forward again after **previous**, '
                      'back from plain Bazzite)', 'A new release comes only through **update** (the stage box)', '**rollback** (on an AresOS)',
                      '**keep-stock** (on plain Bazzite)', 'Layout trials work', "boot menu's rows",
                      '**Expected exact stock/AresOS pair**', '**install the current tools first**', 'the routine box below',
                      "or the stick's Windows box, tools box and tools-only box after it",
                      '(INSTALL-PROCEDURES.md#recovery-menu)', '(INSTALL-PROCEDURES.md#what-you-notice-on-each-system)',
                      '**Another owner command is running**'):
            self.assertIn(value, intro)
        for value in ('provisional', 'INVALID', '[Failed or bad update](EMERGENCY.md#failed-or-bad-update)',
                      'leave GRUB alone', 'Never repeat the update without Help',
                      '**interrupted before its result was recorded; do not reboot**',
                      '**was stopped safely**, the deployment list stayed as it was',
                      'run the same update once to continue it', 'STOPs while anything uses the installed tools',
                      'a STOP always leaves working tools in place', '**Newest installed AresOS starts next**'):
            self.assertIn(value, route)
        # Rule 5 replaced these; the guide never quotes them again (PLAN-GAP 4 of stage 1b, step 1).
        for value in ('did not finish at the restart', 'three deployments', 'refuse with three', 'guessed GRUB title'):
            self.assertNotIn(value, route)
        # A closed window ends in the stop routine, whose clean end closes the intent, and a power cut
        # leaves no same start (22c review 8, findings 2 and 7).
        self.assertNotIn('(power, closed window)', route)
        # One word per meaning: update's reorder and its lines are gone, and update never returns anywhere.
        for value in ('Newest AresOS starts next', 'newer still', 'release of your tools', 'do **not** run update',
                      '**update** the newest', 'update makes', 'start this box over'):
            self.assertNotIn(value, route)
        self.assertEqual(route.count('```bash\n' + commands['update']), 1)
        # The quoted tool messages are the ones the tools print.
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("' did not finish as recorded ('", "'Another owner command is running;",
                      "' was interrupted before its result was recorded; do not reboot; run '", "' and was stopped safely: '",
                      "'An owner command of the installed tools is running (pid '",
                      "' confirmed after the restart'", "'Previous AresOS queued for the next start '",
                      "'Signed exact release staged '", "'Running release stays as rollback '", "'Tools updated from version '",
                      "' was not applied: the deployments are as before it, and nothing is waiting'",
                      "' is in place and has not started yet'", "' already starts next; nothing changed'",
                      "'It runs now'", "'It does not run yet: it starts at the next restart'",
                      "'Newest installed AresOS starts next '", "'forward to '",
                      "'Update installs a new release only from a running AresOS that starts next: run '",
                      "'The release of these tools is installed already, so update has nothing to install: run '",
                      "' is removed when the update finishes at shutdown'",
                      "\"The new release starts with this system's settings (Wi-Fi, passwords, layout), not \"",
                      "' runs and starts next'", "' starts next, after the restart'", "' starts next; this start was not the default'",
                      "'Boot menu at the next start: '", "'Boot menu after the update finishes at shutdown (expected): '",
                      "'update to '", "'return to '"):
            self.assertIn(value, source)
        self.assertNotIn(' did not finish at the restart', source)
        for value in ('Newest AresOS starts next', 'newer still'):
            self.assertNotIn(value, source)
        # The line the guide explains is version 2's, the tools on the laptop until 22c's are installed.
        version2 = subprocess.check_output(['git', 'show', '41b06513:os/owner-tools/payload/owner.py'], cwd=ROOT).decode()
        self.assertIn("'Expected exact stock/AresOS pair'", version2)
        self.assertNotIn('INSTALL.md#5-', route)

    def test_failed_update_card_checks_first_then_previous_only_where_the_update_is_in_place(self):
        texts = documents()
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        card = section(texts['EMERGENCY.md'], 'failed-or-bad-update')
        order = ('Restart normally once.', '**Bazzite**, then leave GRUB alone',
                 '**Check whichever system started.**', commands['check'],
                 '**Require `PASS check` before acting on any deployment result.**',
                 '- **Update to … is in place and has not started yet**', '(INSTALL.md#return-to-the-older-aresos)',
                 '**Return to … confirmed after the restart**', '- **Update to … confirmed after the restart**',
                 '- **Update to … was not applied**', 'Do **not** run previous',
                 'then leave GRUB alone',
                 'Get Help before repeating the update.')
        position = 0
        for value in order:
            position = card.index(value, position) + len(value)
        for value in ('**did not finish as recorded**', '**interrupted before its result was recorded**',
                      '(INSTALL-PROCEDURES.md#rollback-from-running-aresos)',
                      '**Windows Boot Manager**', '10-minute wait', '(INSTALL.md#8-everyday-boot-and-recovery)'):
            self.assertIn(value, card)
        self.assertNotIn(commands['previous'], card)
        self.assertNotIn(commands['update'], card)
        returned = section(texts['INSTALL.md'], 'return-to-the-older-aresos')
        self.assertIn(commands['previous'], returned)
        self.assertIn(pass_line('previous'), returned)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("' was not applied: the deployments are as before it, and nothing is waiting'",
                      "' is in place and has not started yet'", "' confirmed after the restart'", "'update to '",
                      "'return to '", "'Previous AresOS queued for the next start '", "' runs and starts next'",
                      "' starts next; this start was not the default'", "'newer AresOS'", "'forward to '",
                      "' did not finish as recorded ('", "' was interrupted before its result was recorded; do not reboot; run '"):
            self.assertIn(value, source)
        # The card returns with previous, a restart with no choice, rollback and Windows; never with update.
        self.assertNotIn(commands['update'], card)
        # The update route's boxes with the same way back: check first, never previous after "was not applied".
        route = section(texts['INSTALL.md'], UPDATE)
        applied = next(line for line in route.splitlines() if line.startswith('  - **Update to … was not applied'))
        self.assertIn('Do **not** run previous (it would go one release further back)', applied)
        self.assertIn("(EMERGENCY.md#failed-or-bad-update) with this check's result (it shows only once)", applied)
        misbehaves = next(line for line in route.splitlines() if line.startswith('- [ ] **If the new release misbehaves**'))
        for value in ('(#run-at-check) first', '`PASS check`',
                      '**Update to … confirmed after the restart**', '**newer AresOS … runs and starts next**',
                      'confirmation in your saved record', '**was not applied**',
                      '(EMERGENCY.md#failed-or-bad-update)', '(#return-to-the-older-aresos)'):
            self.assertIn(value, misbehaves)
        # The procedures say what works now with three installed systems.
        menu = section(texts['INSTALL-PROCEDURES.md'], 'recovery-menu')
        for value in ('**three rows after it, which differ only in `(ostree:N)`**', '**Boot menu at the next start:**',
                      '**Take the row the last title named**', 'A wrong choice is harmless', commands['check'],
                      'what runs and what starts next', '`PASS check`', '(#keep-stock)',
                      '(#back-to-aresos-from-stock)', 'Never rollback from plain Bazzite', '**Expected exact stock/AresOS pair**',
                      'Install the current tools first', 'A failed **first** switch boot', '**Windows → Help**',
                      'After a boot-menu choice, [run the boot check](INSTALL.md#run-at-check) before acting', '**Update to … was not applied**',
                      'previous would then go one release further back',
                      "(EMERGENCY.md#failed-or-bad-update) with that check's result (it shows only once)"):
            self.assertIn(value, menu)
        for text in (card, route, menu):
            self.assertNotIn('first line says', text)
            self.assertNotIn("check's first line", text)
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

    def test_release28_checks_keep_the_terminal_open_and_restarts_wait_for_minecraft(self):
        texts = documents()
        guide = texts['INSTALL.md']
        route = section(guide, UPDATE)
        save = section(guide, SAVE_HOME)
        card = section(texts['EMERGENCY.md'], 'failed-or-bad-update')
        procedures = texts['INSTALL-PROCEDURES.md']
        for text in (section(guide, 'run-at-check'),
                     route.split('- [ ] **Forward again', 1)[1], card,
                     section(procedures, 'layout-completion'), section(procedures, 'abandon-completion'),
                     section(procedures, 'recovery-menu'), texts['INSTALL-REFERENCE.md']):
            self.assertIn('**Terminal** app', text)
            self.assertRegex(text, r'open until the PASS lines')
        for text in (section(guide, 'return-to-the-older-aresos'), card):
            self.assertIn("release 27's desktop", text)
            self.assertIn('Your Minecraft home files are there again when you return to release 28.', text)
        self.assertIn('**Alt+F4**', save)
        self.assertIn('**Minecraft was closed. Nothing is wrong.**', save)
        for box in ('Restart into the new release', 'Check:', 'Forward again'):
            text = route.split(f'- [ ] **{box}', 1)[1].split('- [ ]', 1)[0]
            self.assertLess(text.index(f'(#{SAVE_HOME})'), text.index('sudo /var/lib/ares/at reboot'))
        returned = section(guide, 'return-to-the-older-aresos')
        self.assertLess(returned.index(f'(#{SAVE_HOME})'), returned.index('sudo /var/lib/ares/at reboot'))
        layout = section(procedures, 'layout-completion')
        self.assertLess(layout.index(f'(INSTALL.md#{SAVE_HOME})'), layout.index('sudo /var/lib/ares/at reboot'))
        self.assertIn('save and close Minecraft again before that second restart', layout)
        terminal = section(texts['INSTALL-REFERENCE.md'], 'terminal-for-at-check')
        shortcut = '**Super+Ctrl+Esc (Ctrl = Strg)**'
        self.assertIn(shortcut, terminal)
        self.assertLess(card.index(shortcut), card.index('sudo /var/lib/ares/at check'))
        for text in (section(procedures, 'rollback-from-running-aresos'),
                     *(line for line in card.splitlines() if 'sudo /var/lib/ares/at reboot' in line)):
            self.assertLess(text.index(f'(INSTALL.md#{SAVE_HOME})'), text.index('sudo /var/lib/ares/at reboot'))

    def test_release27_keymap_recovery_requires_a_passing_check_on_the_same_boot(self):
        texts = documents()
        recovery = section(texts['INSTALL-REFERENCE.md'], 'release-27-console-keys')
        order = ('STOP: Loaded console keys differ from system layout; get help', '`localectl status`',
                 'loadkeys -C /dev/tty3 -- de', 'sudo /var/lib/ares/at check', '`PASS check`',
                 'Keep the first result', 'Use it only after `PASS check` on this boot')
        positions = [recovery.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        for page, anchor in (('INSTALL.md', 'return-to-the-older-aresos'),
                             ('EMERGENCY.md', 'failed-or-bad-update')):
            route = section(texts[page], anchor)
            self.assertIn('(INSTALL-REFERENCE.md#release-27-console-keys)', route)
            self.assertIn('before acting on any', route)

    def test_install_hold_covers_direct_writer_restore_and_erasure_routes(self):
        texts = documents()
        for page, anchor, hold, action in (
            ('INSTALL.md', '2-prepare-and-test-the-installer-stick', '**STOP', '**Schreiben**'),
            ('INSTALL.md', '4-install-and-prepare-corrected-stock', '**STOP until a new installer',
             '**Wiederherstellen**'),
            ('INSTALL-REFERENCE.md', 'writer-labels', '**STOP while the', '**Schreiben**'),
            ('INSTALL-REFERENCE.md', 'writer-labels', '**STOP before restore', 'pressing **Wiederherstellen**'),
            ('INSTALL-PROCEDURES.md', 'optional-removal-or-erasure', '**STOP before writing', '**Erasure for reuse:**'),
            ('INSTALL-PROCEDURES.md', 'optional-removal-or-erasure', '**STOP before writing', '**Apply**'),
        ):
            with self.subTest(page=page, action=action):
                route = section(texts[page], anchor)
                self.assertLess(route.index(hold), route.index(action))
        status = section(texts['INSTALL-STATUS.md'], 'current-gates')
        self.assertIn('before writing or restoring the installer stick, installing, reinstalling, or erasing Crucial', status)

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
        return_link = '(INSTALL.md#return-to-the-older-aresos)'
        self.assertIn(return_link, branch['in-place-not-started'])
        self.assertIn(return_link, branch['target-boot-confirmed'])
        returned = section(documents()['INSTALL.md'], 'return-to-the-older-aresos')
        order = (commands['previous'], pass_line('previous'), '**Previous AresOS queued for the next start**',
                 commands['reboot'], 'leave GRUB alone', '`PASS check`', '**Return to … confirmed after the restart**')
        positions = [returned.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn(return_link, branch['not-applied'])
        restart = branch['not-applied'].index(commands['reboot'])
        self.assertLess(branch['not-applied'].index('**this start was not the default**'), restart)
        self.assertLess(restart, branch['not-applied'].index('leave GRUB alone'))

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

    def test_failed_update_card_keeps_the_result_of_a_check_just_run(self):
        """Review 5, finding 2: the update route's check box and misbehaves box and the boot menu run check,
        then link to the card. That check shows "Update to … was not applied" once (rule 5 archives the
        journal); a second check shows no update line. The card uses the check just run and sends any result
        it does not name to Help, never previous. Traced for every staged update, both ends of its shutdown
        and every boot-menu row, review 5's sequence (finish lost, the titled row boots 13) among them."""
        import ways_back_ledger as ledger
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        card = section(documents()['EMERGENCY.md'], 'failed-or-bad-update')
        entry = card[:card.index('\n- ')]
        positions = [entry.index(value) for value in ('If you just ran a check', 'keep that result',
                     '**was not applied** shows only once', 'Otherwise', '`' + commands['check'] + '`',
                     'Require `PASS check` before acting on any deployment result', '(INSTALL-REFERENCE.md#release-27-console-keys)')]
        self.assertEqual(positions, sorted(positions))
        quotes = {'in-place-not-started': '- **Update to … is in place and has not started yet**',
                  'target-boot-confirmed': '- **Update to … confirmed after the restart**',
                  'not-applied': '- **Update to … was not applied**', 'none': '- A STOP containing'}
        branch = {outcome: next(line for line in card.splitlines() if line.startswith(quote)) for outcome, quote in quotes.items()}
        for outcome in ('not-applied', 'none'):
            self.assertNotIn('return-to-the-older-aresos', branch[outcome])
        self.assertIn('**STOP → go to [Help](INSTALL-REFERENCE.md#help)**', branch['none'])
        self.assertLess(card.index(branch['not-applied']), card.index(branch['none']))

        traced = collections.Counter()
        for start in ledger.starts():
            staged = ledger.transition(start, ('update', 'full')).state
            if not staged.stage:
                continue
            for finish in ('restart', 'power-off'):
                rows = (staged.stage, staged.running, 'S') if finish == 'restart' else staged.rows[1:]
                for choice in ('default', *rows):
                    with self.subTest(start=start.rows, bundle=start.bundle, finish=finish, choice=choice):
                        booted = ledger.transition(staged, (finish, choice)).state
                        shown = booted.outcome()  # what the linked page's check shows
                        checked = ledger.transition(booted, ('check', 'full')).state
                        again = checked.outcome()  # what a second check would show
                        if shown != 'not-applied':
                            self.assertEqual(again, shown if shown == 'in-place-not-started' else 'none')
                            traced[shown] += 1
                            continue
                        self.assertEqual(again, 'none')  # shown once
                        # With the result kept: no previous; a restart with no choice where another row runs.
                        end = checked if booted.running == booted.rows[0] else ledger.transition(checked, ('restart', 'default')).state
                        self.assertEqual((end.running, end.rows[0]), (staged.running, staged.running))
                        traced['not applied, kept'] += 1
        # Every lost finish (13) is a "not applied" whose second check would show nothing the card names.
        self.assertEqual(traced, collections.Counter({'not applied, kept': 13, 'target-boot-confirmed': 8,
                                                      'in-place-not-started': 8}))
        # Review 5's sequence: release 28's finish lost, the provisional title's (ostree:1) boots 13.
        start = next(s for s in ledger.starts() if s.bundle == '28' and s.rows == ('27', '13', 'S'))
        booted = ledger.transition(ledger.transition(start, ('update', 'full')).state, ('power-off', '13')).state
        self.assertEqual((booted.running, booted.rows[0], booted.outcome()), ('13', '27', 'not-applied'))
        checked = ledger.transition(booted, ('check', 'full')).state
        self.assertEqual(checked.outcome(), 'none')
        self.assertEqual(ledger.transition(checked, ('restart', 'default')).state.running, '27')

    def forward_box(self, texts):
        """The box "Forward again, or back from plain Bazzite" and its two outcome bullets."""
        route = section(texts['INSTALL.md'], UPDATE)
        start = route.index('- [ ] **Forward again, or back from plain Bazzite**')
        box = route[start:route.index('**Record:**', start)]
        lines = box.splitlines()
        outcome = dict(change=next(line for line in lines if line.startswith('  - **Newest installed AresOS starts next**')),
                       nothing=next(line for line in lines if line.startswith('  - **… already starts next; nothing changed**')))
        return box, outcome

    def test_forward_and_back_box_never_installs_a_release(self):
        """One word per meaning (briefs/22c-forward-command.md), replacing reviews 4 and 5's dispatch: the box
        "Forward again, or back from plain Bazzite" runs forward from every system, with no check first,
        no boot-menu step and no word about the tools' release. Traced in the reference ledger from every
        state of the destination commands with nothing staged and no layout trial: forward never stages
        and never changes the set of deployments; the box ends on the newest installed AresOS, running and
        starting next, confirmed after a change; a STOP leads to Help."""
        import ways_back_ledger as ledger
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        texts = documents()
        box, outcome = self.forward_box(texts)
        for value in ('after **previous**, from plain Bazzite, or from any system GRUB started',
                      'This box runs **forward**. It selects the newest installed AresOS without a stick, login or network',
                      '```bash\n' + commands['forward'] + '\n' + commands['title'] + '\n```', pass_line('forward'),
                      'Any STOP → [A tools command stopped](EMERGENCY.md#a-tools-command-stopped)'):
            self.assertIn(value, box)
        positions = [outcome['change'].index(value) for value in (
                     '**… runs and now starts next; no restart is waiting**', 'check this boot', '**… starts next, after the restart**',
                     commands['reboot'], pass_line('reboot'), 'leave GRUB alone', '**Forward to … confirmed after the restart**')]
        self.assertEqual(positions, sorted(positions))
        # Reviews 4 and 5's dispatch, the two-step path and the tools' release left the box with update.
        for value in (commands['update'], commands['check'], 'update', 'newer still', 'release of your tools',
                      'Boot menu at the next start', 'start this box over', 'go by its line'):
            self.assertNotIn(value, box.replace('this update route', 'this route'))
        back = section(texts['INSTALL-PROCEDURES.md'], 'back-to-aresos-from-stock')
        for value in ('**forward** the newest AresOS, **previous** the older one',
                      'Neither installs a release, and neither needs a stick, login or network'):
            self.assertIn(value, back)
        for value in ('newer still', '**update**', commands['update']):
            self.assertNotIn(value, back)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("'Newest installed AresOS starts next '", "self.select('forward', state, shape, settled, target,",
                      "' runs and now starts next; no restart is waiting'", "'forward to '"):
            self.assertIn(value, source)

        traced = collections.Counter()
        for state in destination_space(ledger):
            if state.stage or state.trial:
                continue
            newest = max(row for row in state.rows if row != 'S')
            where = ('plain Bazzite' if state.running == 'S' else 'newest AresOS' if state.running == newest
                     else 'older AresOS') + (', first' if state.running == state.rows[0] else ', not first')
            with self.subTest(state=state):
                result = ledger.transition(state, ('forward', 'full'))
                if result.stop:
                    # The box's STOP line: the tools-stopped card, then Help. Only a change that waits
                    # for its restart stops forward here.
                    self.assertEqual((result.stop, state.outcome()), ('restart first', 'waiting'))
                    traced['STOP → Help'] += 1
                    continue
                after = result.state
                self.assertEqual((sorted(after.rows), after.stage), (sorted(state.rows), ''))
                if ledger.transition(state, ('update', 'full')).state.stage:
                    traced['update here would stage'] += 1
                if after.rows != state.rows:
                    # Restart only if the newly selected target is not the running system.
                    self.assertEqual((after.rows[0], after.journal.word), (newest, 'forward'))
                    titled = ledger.transition(after, ('title', 'full')).state
                    restart = titled.running != newest
                    end = ledger.transition(titled, ('restart', 'default')).state if restart else titled
                    checked = ledger.transition(end, ('check', 'full'))
                    self.assertFalse(checked.stop)
                    self.assertEqual(checked.confirmation, restart)
                    traced['changed from ' + where] += 1
                else:
                    # … already starts next; nothing changed: a restart only for "It does not run yet".
                    end = after if after.running == after.rows[0] else ledger.transition(after, ('restart', 'default')).state
                    self.assertFalse(ledger.transition(end, ('check', 'full')).stop)
                    traced['nothing changed, ' + ('It runs now' if end is after else 'It does not run yet')] += 1
                self.assertEqual((end.running, end.rows[0], end.stage), (newest, newest, ''))
            if state.running == 'S':
                self.assertFalse(ledger.transition(state, ('previous', 'full')).state.stage)
        self.assertEqual(traced, collections.Counter({
            'changed from plain Bazzite, first': 88, 'changed from plain Bazzite, not first': 58,
            'changed from older AresOS, first': 74, 'changed from older AresOS, not first': 56,
            'changed from newest AresOS, not first': 126, 'nothing changed, It runs now': 100,
            'nothing changed, It does not run yet': 181, 'STOP → Help': 68, 'update here would stage': 55}))

    def test_stage_box_names_forward_and_the_last_box_leads_back_to_it(self):
        """One word per meaning: where update may not stage it changes nothing and names forward. The stage
        box sends both lines to the last box: after it the newest installed AresOS runs and starts next,
        where update stages the release it could not stage before, or (its release installed already)
        has nothing to do. Traced from every resting state of the destination commands."""
        import ways_back_ledger as ledger
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        route = section(documents()['INSTALL.md'], UPDATE)
        stage = route.split('**Stage the new release:**', 1)[1].split('**Title and export:**', 1)[0]
        for value in ('**Update installs a new release only from a running AresOS that starts next**',
                      '**The release of these tools is installed already**', 'export and unplug',
                      'Use the last box, **Forward again, or back from plain Bazzite**',
                      'Come back to stage only if the announced release still needs installing.',
                      '**Interrupted update recorded:**', '**It runs now**', '(#run-at-check)'):
            self.assertIn(value, stage)
        self.assertNotIn(commands['forward'], stage)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("FORWARD_FIRST = ('Update installs a new release only from a running AresOS that starts next: run '",
                      "RELEASE_INSTALLED = ('The release of these tools is installed already, so update has nothing to install: run '"):
            self.assertIn(value, source)

        traced = collections.Counter()
        for state in destination_space(ledger):
            if not ledger.resting(state):
                continue
            update = ledger.transition(state, ('update', 'full'))
            if update.stop != 'at forward':
                traced['update ' + ('stages' if update.state.stage else 'has nothing to do')] += 1
                continue
            with self.subTest(state=state):
                # The last box: forward, title, a restart with no choice unless that AresOS runs and starts next.
                after = ledger.transition(state, ('forward', 'full')).state
                if after.running != after.rows[0]:
                    after = ledger.transition(ledger.transition(after, ('title', 'full')).state, ('restart', 'default')).state
                after = ledger.transition(after, ('check', 'full')).state
                again = ledger.transition(after, ('update', 'full'))
                self.assertFalse(again.stop)
                if state.bundle in state.rows:
                    self.assertEqual((after.running, after.rows[0], again.state.stage), (state.bundle, state.bundle, ''))
                    traced['installed already: the last box ends on it'] += 1
                else:
                    self.assertEqual(again.state.stage, state.bundle)
                    traced['may not stage here: after the last box update stages'] += 1
        self.assertEqual(traced, collections.Counter({'update stages': 55, 'update has nothing to do': 65,
                                                      'may not stage here: after the last box update stages': 143,
                                                      'installed already: the last box ends on it': 384}))

    def test_forward_again_after_a_failed_update_a_stock_return_and_previous_never_stages(self):
        """Review 5, finding 1, the connected sequence, now with forward: tools of release 28 installed, its
        update's finish lost (27, 13 and plain Bazzite stay); rollback to plain Bazzite and back with forward
        (confirmed as "Forward to …", so the record can no longer read it as an update); later previous to
        13. Forward again: 27 runs and starts next, confirmed, 28 is not staged. update on 13 would stage
        28 and its shutdown would remove 27: the box never runs it."""
        import ways_back_ledger as ledger
        box, _ = self.forward_box(documents())
        self.assertIn('This box runs **forward**', box)

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
        self.assertEqual(ledger.transition(state, ('update', 'full')).stop, 'at forward')  # update names forward on stock
        state = run(state, ('forward', 'full'))
        self.assertEqual(state.journal.word, 'forward')
        state = run(state, ('title', 'full'), ('restart', 'default'))
        self.assertTrue(ledger.transition(state, ('title', 'full')).confirmation)  # "Forward to … confirmed"
        state = run(state, ('check', 'full'), ('previous', 'full'), ('title', 'full'), ('restart', 'default'), ('check', 'full'))
        self.assertEqual((state.rows, state.running), (('13', '27', 'S'), '13'))
        # update here stages 28, and the shutdown keeps 28, 13 and plain Bazzite: 27 is gone.
        staged = ledger.transition(state, ('update', 'full')).state
        self.assertEqual((staged.stage, ledger.transition(staged, ('restart', 'default')).state.rows), ('28', ('28', '13', 'S')))
        # The box: forward, title, restart with no choice, check.
        forward = ledger.transition(state, ('forward', 'full'))
        self.assertFalse(forward.stop or forward.state.stage)
        state = run(forward.state, ('title', 'full'), ('restart', 'default'))
        titled = ledger.transition(state, ('title', 'full'))
        self.assertTrue(titled.confirmation)
        self.assertEqual((state.rows, state.running, state.stage), (('27', '13', 'S'), '27', ''))

    def test_a_return_that_changes_nothing_completes_without_a_confirmation(self):
        """Review 4, finding 3: when the system a command names already starts next, the tools write no
        journal (rule 4), so no "… confirmed after the restart" can follow. The guides tell the two apart:
        after a change, the confirmation; after nothing to do, PASS check with that system running and
        starting next. Traced in the reference ledger for forward (update's word for this until one word per
        meaning), previous, rollback and keep-stock."""
        import ways_back_ledger as ledger
        texts = documents()
        route = section(texts['INSTALL.md'], UPDATE)
        start = route.index('- [ ] **Forward again, or back from plain Bazzite**')
        box = route[start:route.index('**Record:**', start)]
        change = next(line for line in box.splitlines() if line.startswith('  - **Newest installed AresOS starts next**'))
        nothing = next(line for line in box.splitlines() if line.startswith('  - **… already starts next; nothing changed**'))
        self.assertIn('`PASS check` with **Forward to … confirmed after the restart** after a restart', change)
        for value in ('This command wrote no new confirmation', '**It runs now**', 'check this boot',
                      '**It does not run yet: it starts at the next restart**', 'restart as above',
                      '`PASS check` with the newest AresOS running and starting next'):
            self.assertIn(value, nothing)
        self.assertNotIn('confirmed after the restart', nothing)
        returned = section(texts['INSTALL.md'], 'return-to-the-older-aresos')
        for value in ('**Previous AresOS queued for the next start**', '**Return to … confirmed after the restart**',
                      '**… already starts next; nothing changed**', 'It may confirm an earlier selection'):
            self.assertIn(value, returned)
        procedures = texts['INSTALL-PROCEDURES.md']
        back = section(procedures, 'back-to-aresos-from-stock')
        self.assertIn('(INSTALL.md#return-to-the-older-aresos)', back)
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
            for word, target in (('forward', max(releases)), ('previous', min(releases)), ('rollback', 'S'), ('keep-stock', 'S')):
                result = ledger.transition(state, (word, 'full'))
                if result.stop:
                    continue  # a refusal with nothing changed
                self.assertFalse(result.state.stage)
                with self.subTest(state=state, word=word):
                    after = result.state
                    unchanged = after.rows == state.rows and (after.journal is None if state.outcome() == 'not-applied'
                                                              else after.journal == state.journal)
                    if not unchanged:
                        self.assertEqual(after.journal.word, word)
                    # Keep-stock still proves a second stock boot. Other routes restart only if needed.
                    restart = word == 'keep-stock' or after.running != after.rows[0]
                    if restart:
                        after = ledger.transition(after, ('restart', 'default')).state
                    titled = ledger.transition(after, ('title', 'full'))
                    self.assertFalse(ledger.transition(after, ('check', 'full')).stop)
                    self.assertEqual((after.running, after.rows[0]), (target, target))
                    if unchanged:
                        # Only an earlier change that is still open can confirm itself here.
                        self.assertTrue(open_change or not titled.confirmation)
                        traced[word + ': nothing changed' + ('' if titled.confirmation else ', no confirmation')] += 1
                    else:
                        self.assertEqual(titled.confirmation, restart)
                        traced[word + (': confirmed' if restart else ': same boot')] += 1
        for word in ('forward', 'previous', 'rollback', 'keep-stock'):
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
        # Back from stock: forward (or previous) in the update route's last box, behind its gate; no update.
        for value in ('**forward** the newest AresOS', '**previous** the older one', 'neither needs a stick, login or network',
                      '**Forward again, or back from plain Bazzite**', '(INSTALL.md#update-aresos-to-a-new-release)',
                      'STEP 5 COMPLETE', '(INSTALL.md#return-to-the-older-aresos)', '**A Bazzite update is waiting. Do not restart**',
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
        for value in ('newer or older AresOS', '**Saved stock rollback queued**',
                      '**… runs; plain Bazzite … starts next, after the restart**', 'every AresOS still installed',
                      '**Plain Bazzite runs here: use … keep-stock**', '**Rollback to … confirmed after the restart**',
                      '(#back-to-aresos-from-stock)', '**Expected exact stock/AresOS pair**'):
            self.assertIn(value, rollback)
        for value in ('**Your files in your home folder stay**', '**its own passwords, Wi-Fi and keyboard layout**',
                      '**Plain Bazzite** has no `ares` account', '**German**',
                      '**The AresOS from before your first update** (release 13) has no `ares` password and no administrator rights',
                      'A later update starts the new release with the settings of the system it runs on',
                      'packages 34 and 35', 'stays empty until you go forward again (**forward**)', 'Nothing is lost'):
            self.assertIn(value, notice)
        self.assertNotIn('with update', notice)
        layout = section(procedures, 'later-layout')
        self.assertIn('on an AresOS that does not start next it refuses and names forward or previous first', layout)
        self.assertNotIn('update or previous', layout)
        source = (ROOT/'os/owner-tools/owner.py').read_text()
        for value in ("'Saved stock is default'", "'Saved stock rollback queued'", "' runs and now starts next; no restart is waiting'",
                      "'Plain Bazzite runs here: use '", "'. Bazzite must not update while AresOS is installed: '",
                      "BACK_TO_ARESOS = 'run ' + typed('forward') + ' to go back to AresOS'",
                      "'This AresOS does not start next: make it the next start first ('",
                      "'A Bazzite update is waiting. Do not restart: the restart deletes {}. Get help.'", "'change to '", "'rollback to '",
                      "'The trial began on another system and its finish had started: run '",
                      "\"This system's half-written layout is restored to the settings before its trial\""):
            self.assertIn(value, source)

    def test_routine_box_for_new_tools_comes_first_with_his_rule_its_limit_and_the_stop_card(self):
        """Brief 22d: the routine box first, the window as it looks, his rule with the limit in plain words,
        the 8-character compare, the announced commit, the board note, the 10-minute rule and the STOP card;
        with the decisions after review 2 (R1 to R6, N2, N6 to N10)."""
        import test_owner_tools as common
        texts = documents()
        commands = json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        fingerprint = hashlib.sha256((ROOT/'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest()
        bootstrap = common.module('bootstrap')
        route = section(texts['INSTALL.md'], UPDATE)
        box = route.split("- [ ] **New tools from Claude's terminal**", 1)[1].split('- [ ] **Windows side**', 1)[0]
        gate = route.splitlines()[2]
        for value in ("the maintainer's board note for you with the full commit hash and the tools fingerprint",
                      '**announced commit**', 'never the newest one on GitHub by itself'):
            self.assertIn(value, gate)
        stale = 'The stick holds tools this laptop installed before (SHA256 …), not the installed ones'
        order = ("Only this box's install line and its export line run this way for now",
                 'every other owner command stays at the console (the boxes below) until a later release brings it here',
                 "as `ares` (no window yet)", 'only by a fast-forward pull',
                 "(never a reset, and never a checkout over other sessions' work)", "the commit's full hash added at the end",
                 'From here until the last PASS line no other Claude session runs an owner command',
                 '```bash\n' + commands['tools-folder'] + '\n```', "the commit's tools have this guide's fingerprint",
                 'Require `SHA256SUMS: OK`',
                 '**STOP tools folder** installed nothing and opened no window: Claude tells you', 'with no export',
                 'waits for your go', 'never from its working copy: `' + bootstrap.FROM_COMMIT + '`', 'entry **tools-routine**',
                 'entry **export-routine**', '```bash\n' + commands['tools-routine'] + '\n```',
                 'Its title bar says **Enter SSH Credentials**', 'it cannot be changed',
                 'Inside it says **' + bootstrap.label(fingerprint, bootstrap.ACTIONS['tools-routine']) + '**',
                 '**Password:**', '**OK** and **Cancel**', '**Your rule:**', 'you told Claude to go just now',
                 'starts with **AresOS owner tools**', '`' + fingerprint[:8] + '`',
                 'line 1 of `github.com/Ares-Empire/AresOS/blob/main/docs/OWNER-TOOLS.md`', 'on your phone (not on the laptop)',
                 'from your own bookmark of that address',
                 "(type it once into your phone's browser and save it as a bookmark; open it from there)",
                 'check that it says `main`',
                 'never use a link Claude sends you at that moment',
                 'press **Cancel**: nothing runs and nothing changes', '**What the window cannot do:**',
                 'it stops accidents and a Claude that acts without asking',
                 'It does not stop a Claude that has been tricked into showing you one thing and running another',
                 'can do anything as administrator, now and later, without asking again', 'use the stick boxes for new tools instead',
                 'One password runs all three', pass_line('install'), '**Tools updated from version**', pass_line('check'),
                 pass_line('title'), 'older titles are INVALID', 'no disk serials', 'to the board under topic `aresos`',
                 'after every later command that changes what starts next', 'within 10 minutes',
                 'stopping the password helper it opened, never the administrator command itself',
                 'sudo then ends with **sudo: no password was provided**, which shows that nothing ran',
                 'If you have already answered, Claude stops nothing and waits for the result',
                 '**A STOP**', 'Claude copies every STOP line to you word for word and asks for your go',
                 'only on your go it runs the export line below', 'tries nothing else',
                 '(EMERGENCY.md#a-routine-tools-command-stopped)',
                 "After a **STOP tools folder** (Claude's own line; no administrator command ran) there is no export and no window",
                 '**' + bootstrap.label(fingerprint, bootstrap.ACTIONS['export-routine']) + '**',
                 '```bash\n' + commands['export-routine'] + '\n```',
                 '**Without ARESTOOLS**', '`' + LOCAL_EXPORT + '`', 'a restart deletes it',
                 '`Tools stick absent; full records remain internal`', '**With ARESTOOLS**', '`' + STICK_EXPORT + '`',
                 'then unplug. The copy is on the stick.', 'The stick can still take records with older tools on it.',
                 'Claude rewrites it from Windows before it can bring the current tools.',
                 'Keep them out of the repository, pull requests and the board.',
                 'Record the announced commit, the fingerprint and the three PASS lines.', 'go on with the stage box',
                 'The title and export box after staging works with or without a stick.',
                 '[return to step 8](#8-everyday-boot-and-recovery)')
        position = 0
        for value in order:
            found = box.find(value, position)
            self.assertGreaterEqual(found, 0, value)
            position = found + len(value)
        # Decision 10 and the old ways are gone: no signal to sudo, no line from the working tree, no relative link.
        for value in ('process number', 'stops that sudo', 'the STOP line', 'copied from `os/owner-tools/commands.json`',
                      '[OWNER-TOOLS.md](OWNER-TOOLS.md)', 'changed nothing:', 'a refusal that names its reason'):
            self.assertNotIn(value, box)
        # The words he compares and reads come from the tools themselves.
        media = (ROOT/'os/owner-tools/media.py').read_text()
        for value in ("'Tools stick absent: records copied to '", "readers = 'only root can read it'",
                      "readers = 'uid ' + str(reader) + ' can read it'",
                      "'This copy is on this laptop, not off it; ' + readers + ', and a restart deletes it'",
                      "'For a copy off the laptop plug in the tools stick and run export again'", repr(STICK_EXPORT),
                      "'" + stale.replace('…', "' + found + '") + "'"):
            self.assertIn(value, media)
        owner_text = (ROOT/'os/owner-tools/owner.py').read_text()
        self.assertIn("'Keep the current administrator session open. Preserve diagnostics; do not reboot ", owner_text)
        card = section(texts['EMERGENCY.md'], 'a-routine-tools-command-stopped')
        # Review 4, S1: the card never sets the whole last line aside; its do-not-reboot half is his.
        self.assertNotIn('is for the console:', card)
        for value in ('**Action:**', 'Claude copies every STOP line to you word for word and asks for your go',
                      "only on your go it runs the routine box's export line", 'tries nothing else',
                      'no other line, no second try, no restart',
                      "After a **STOP tools folder** (Claude's own line; no administrator command ran) there is no export and no window",
                      "The tools' last line begins **Keep the current administrator session open**: that part is for the console",
                      '(on this route there is none to keep, and nothing is lost); its **do not reboot** holds here too',
                      'Claude reads `/run/ares-records` to help you and never copies it into the repository, a pull request or the board',
                      'it holds disk serials and firmware entries',
                      '**' + bootstrap.label(fingerprint, bootstrap.ACTIONS['export-routine']) + '**',
                      '**Cancel** is not a STOP: nothing ran', '**STOP tools folder** installed nothing',
                      'the installed tools still work', '`/run/ares-records`', '**SAFE TO REMOVE ARESTOOLS**',
                      '**STOP → go to [Help](INSTALL-REFERENCE.md#help)**', '(INSTALL.md#update-aresos-to-a-new-release)'):
            self.assertIn(value, card)
        self.assertNotIn('the STOP line', card)
        stick = section(texts['EMERGENCY.md'], 'a-tools-command-stopped')
        self.assertIn('**This copy is on this laptop, not off it**', stick)
        # R6: the stick falls behind after the routine box, in both places, with the tools' own line.
        for value in ("After new tools from Claude's terminal the stick still holds older tools", '`' + stale + '`',
                      'cannot bring the current tools until Claude writes it again'):
            self.assertIn(value, stick)
        emergency = texts['EMERGENCY.md']
        self.assertLess(emergency.index('## A tools command stopped'), emergency.index('## A routine tools command stopped'))

    def test_status_names_22c_and_22d_on_the_laptop_with_calm_test_open(self):
        import release28_walk

        status = documents()['INSTALL-STATUS.md']
        fingerprint = hashlib.sha256((ROOT/'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest()
        row = next(line for line in status.splitlines() if line.startswith('| Ways back after an update (package 22c) |'))
        # The rehearsal passed and its record step rebound the sources: the row links the run the bindings name.
        bindings = json.loads((ROOT/'os/manifest/ci/22c/source-bindings.json').read_text())
        # 22d carried 22c's ways back onto the laptop; version 3's fingerprint stays historical.
        for value in ('**BUILT AND REVIEWED; VM REHEARSAL PASSED; ON THE LAPTOP 2026-11-17 (IN VERSION 4); CALM TEST OPEN**',
                      'Ways back on the laptop in tools version 4 since 2026-11-17',
                      'Tools fingerprint `2084c786…`', 'version 3 itself never went on the laptop',
                      "package 22d's version 4 (next row) brought these ways back over version 2 on 2026-11-17",
                      '(../reviews/22c-ways-back-after-update/REPORT.md)', '**VM rehearsal passed**',
                      '(' + bindings['run'] + ')', 'every protected-disk audit was unchanged',
                      'tools-only update', '**On the laptop 2026-11-17:**',
                      '`PASS check` and `PASS title` followed version 4\'s install and the one-session console layout trial',
                      '**Calm test OPEN, with his OK:**', "the title's row map", 'stays OPEN',
                      # One word per meaning: forward returns, update only installs; review 7 found it SAFE.
                      'one word per destination', '`at forward` goes to the newest installed AresOS from every system',
                      '`at update` only installs a new release', 'reviewed SAFE (review 7)',
                      'previous, restart, forward, restart, then rollback, restart, forward, restart'):
            self.assertIn(value, row)
        for value in ('`at update` goes to', 'the newer AresOS from the boot menu, update', 'NOT REHEARSED', 'Not rehearsed yet',
                      'its review follows', 'the rehearsal passes', 'NOT ON THE LAPTOP',
                      '**Before this row may say "on the laptop":**', "the laptop's tools stay `851eb742…`"):
            self.assertNotIn(value, row)
        self.assertNotIn(fingerprint, row)
        row = next(line for line in status.splitlines() if line.startswith('| Owner tools without the stick (package 22d) |'))
        # 22d's rehearsal passed and its record step rebound the sources: the row links the run the bindings name.
        rebound = json.loads((ROOT/'os/manifest/ci/22d/source-bindings.json').read_text())
        for value in ('**BUILT AND REVIEWED; VM REHEARSAL PASSED; ON THE LAPTOP 2026-11-17**',
                      'on the laptop since 2026-11-17 over version 2 `851eb742…`',
                      'Tools fingerprint `' + release28_walk.TOOLS_V4 + '`',
                      'https://github.com/Ares-Empire/AresOS/blob/' + release28_walk.V4_COMMIT + '/docs/OWNER-TOOLS.md',
                      '**Enter SSH Credentials**',
                      'not a tricked Claude', 'the first installation stays on the stick', '`/run/ares-records`, on this laptop only',
                      'the routine box first', '(EMERGENCY.md#a-routine-tools-command-stopped)', '**VM rehearsal passed**',
                      '(' + rebound['run'] + ')', 'on `' + rebound['commit'][:8] + '`', '(../reviews/22d-tools-without-stick/runs/tools-local-' + rebound['run'].rsplit('/', 1)[1] + '/index.json)',
                      '`PASS install`, `PASS check` and `PASS title`', 'every protected-disk audit was unchanged',
                      'With his go on 2026-11-17', '`634e12378b68f77398f7c8b633fcea988a768acf`',
                      'routine line hash `0b11cfc5…`', 'OWNER-TOOLS.md line 1 on his phone and approved it',
                      '`PASS install` updated version 2 to 4',
                      '`Loaded console keys differ from system layout; get help`',
                      'Plymouth left every console busy for systemd-vconsole-setup',
                      'package 50 fixes it for release 28', 'the install was complete',
                      '`PASS export` copied records to `/run/ares-records`',
                      'one-session `loadkeys -C /dev/tty3 -- de` trial', 'keycode 21 from `+y` to `+z`',
                      '`PASS check` and `PASS title` showed R27 `5fad242fceac` running and starting next',
                      'R13 `9b19b7942bc1` and plain Bazzite `ed93d2158a1b`', 'pin yes, nothing staged',
                      'previous title INVALID as expected after install',
                      '`sudo -n true` was refused (no ticket kept)', '`yz-/!ü` typing matched on tty3 and in the terminal'):
            self.assertIn(value, row)
        for value in ('NOT REHEARSED', '**not rehearsed**', 'not yet reviewed', 'the VM rehearsal passes',
                      'NOT ON THE LAPTOP', 'The laptop has not run this route yet',
                      '**Before this row may say "on the laptop":**', "to install over the laptop's `851eb742…`"):
            self.assertNotIn(value, row)
        self.assertNotIn(fingerprint, row)
        self.assertEqual(status.splitlines().index(row) - 1,
                         next(i for i, line in enumerate(status.splitlines()) if line.startswith('| Ways back after an update (package 22c) |')))
        update = next(line for line in status.splitlines() if line.startswith('| Update route (packages 22 and 27) |'))
        self.assertIn("the laptop's tools are version 4 (`dcbc375f…`) since 2026-11-17", update)
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
