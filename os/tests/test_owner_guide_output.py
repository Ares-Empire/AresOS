"""Compare the owner guides' quoted console results with the shipped tools."""
import ast
import itertools
import json
import re
import subprocess
import unittest

from test_owner_path import ROOT, documents, section

TOOLS = ROOT / 'os/owner-tools'
GUIDES = ('INSTALL.md', 'EMERGENCY.md', 'INSTALL-PROCEDURES.md', 'INSTALL-REFERENCE.md', 'INSTALL-STATUS.md')
QUOTED = re.compile(r'\*\*([^*`\n]+)\*\*|`([^`\n]+)`')
CUE = re.compile(
    r'\b(?:require|expect|look for|shows?|prints?|says?|STOPs? (?:containing|with)|ends with|received)\s*[:\s]*$',
    re.IGNORECASE,
)
# Other programs produce these results. Their own tests check the bootstrap and Windows helper.
OTHER_OUTPUT = ('SHA256SUMS: OK', 'PASS tools manifest SHA256 ', 'PASS ARESTOOLS ready;',
                'PASS: ', 'PASS → ', 'sudo: no password was provided', 'updated successfully',
                'AresOS owner tools ')
# Bold text also marks screen labels, physical gates and route names.
LABELS = {
    'Terminal', 'Login:', 'login:', 'Password:', '#', 'Continue boot', 'STEP 5 COMPLETE',
    'PASS', 'Windows', 'Bazzite', 'German', 'installer German', 'End of Stage',
    'With ARESTOOLS', 'Without ARESTOOLS', 'With ARESTOOLS:', 'Without ARESTOOLS:',
    'BIOS-Modus: UEFI', 'Sicherer Startzustand: Aus', 'Vollständig entschlüsselt', '0,0%',
    'Ruhezustand / Schnellstart', 'both Micron and Crucial', 'nvidia-smi',
    'Secure Boot changed', 'Windows recovery prompt', 'Missing internal boot entry while its SSD is attached',
    'OK', 'Cancel', 'AresOS owner tools', 'read:packages-only', 'Use entire disk', 'Crucial only',
    'Überprüfung abbrechen', '<name> wiederherstellen', 'erfolgreich geschrieben',
    '<ISO name> erfolgreich geschrieben',
    'Das Laufwerk wurde erfolgreich wiederhergestellt! → Fertig', 'Enter SSH Credentials',
    'STOP tools folder', 'Tools stick lifecycle', 'layout abandon', 'and you already recorded that PASS', 'daily_wheel: true',
    'Minecraft was closed. Nothing is wrong.',
}


def word(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ''


def output_templates(source, values):
    """Read string expressions that feed the CLI, using … for runtime fields."""
    tree = ast.parse(source)
    values = values.copy()
    candidates = set()

    def strings(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if ast.unparse(node) == 'label[0].upper() + label[1:]':
                return [label[:1].upper() + label[1:] for label in values.get('label', ['…'])]
            return [a + b for a, b in itertools.product(strings(node.left), strings(node.right))]
        if isinstance(node, ast.IfExp):
            return strings(node.body) + strings(node.orelse)
        if isinstance(node, (ast.List, ast.Tuple)):
            return [line for item in node.elts for line in strings(item)]
        if isinstance(node, ast.Call) and word(node.func) in ('name', 'label', 'change'):
            return values.get('label' if word(node.func) == 'name' else word(node.func), ['…'])
        if isinstance(node, ast.Call) and word(node.func) == 'typed':
            return ['sudo /var/lib/ares/at ' + ' '.join(strings(arg)[0] for arg in node.args)]
        if isinstance(node, ast.Call) and word(node.func) == 'format':
            return [template.format(*('…' for _ in node.args)) for template in strings(node.func.value)
                    if template != '…']
        if isinstance(node, ast.Call) and word(node.func) == 'str':
            return strings(node.args[0])
        return values.get(word(node), ['…'])

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(word(target) == 'layout_next' for target in node.targets):
            values['layout_next'] = strings(node.value)

    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            candidates.update(strings(node.value))
        elif isinstance(node, ast.Assign) and any(word(target) == 'lines' for target in node.targets):
            candidates.update(strings(node.value))
        elif isinstance(node, ast.Call):
            func = word(node.func)
            if func in {'require', 'select'}:
                candidates.update(strings(node.args[-1]))
            if func in {'note', 'append', 'say', 'print', 'input', 'getpass', 'Stop'} and node.args:
                candidates.update(strings(node.args[0]))
    return candidates - {'', '…'}


def quoted_results(page, text):
    """Find quoted output after a cue, in a result bullet, or in a PASS marker."""
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith('```'):
            fenced = not fenced
        if fenced:
            continue
        previous = 0
        result = False
        for match in QUOTED.finditer(line):
            quote = next(group for group in match.groups() if group is not None)
            before = line[previous:match.start()]
            bullet = (re.fullmatch(r'\s*-\s*', line[:match.start()]) and not quote.endswith(':')
                      and page in ('INSTALL.md', 'EMERGENCY.md') and re.match(
                          r'(?:Update to |Newest installed AresOS |Previous AresOS |… already )', quote))
            if CUE.search(before) or bullet:
                result = True
            elif not re.fullmatch(r'[(),; /]*(?:(?:and|or|with|then)\s*)?', before):
                result = False
            previous = match.end()
            if quote.startswith('PASS ') or result:
                if quote not in LABELS and not quote.startswith(OTHER_OUTPUT + ('sudo ', 'Ctrl', 'Alt', 'Fn+', 'F12')):
                    yield number, quote


def matches_output(quote, candidates):
    pattern = re.compile('.*'.join(map(re.escape, re.split(r'…|\.{3}', quote))))
    return any(pattern.search(line) for line in candidates)


def check_selection_route(text, command, confirmation):
    checks = re.findall(r'(?:Update to|Return to|Forward to) … confirmed after the restart', text)
    if checks != [confirmation] or '#run-at-check)' not in text or 'repeat the check box' in text:
        raise AssertionError(f'{command} needs its own boot check and {confirmation}')


class OwnerGuideOutputTest(unittest.TestCase):
    def test_quoted_results_match_printed_strings(self):
        from test_owner_tools import owner, module

        source = (TOOLS / 'owner.py').read_text()
        media = module('media')
        # Bind the output's generated words to the code that supplies them.
        fixtures = [dict(checksum=hex(index)[2:] * 64, serial=0, osname='fixture',
                         **{'container-image-reference-digest': 'sha256:' + str(index) * 64})
                    for index in range(4)]
        stock, older, newer, staged = fixtures
        shape = dict(stock=stock, ares=[older, newer], staged=staged,
                     known={row['container-image-reference-digest']: (index,) for index, row in enumerate(fixtures)})
        labels = [owner.role(shape, row) + ' …' for row in fixtures]
        labels.append(owner.role(dict(shape, ares=[newer]), newer) + ' …')
        changes = [owner.Tools.change(dict(word=word, reference='…'), capital=True)
                   for word in ('update', 'previous', 'forward', 'rollback', 'keep-stock')]
        values = dict(change=changes, label=labels, profile=['de', 'us', 'us-intl'], LOCAL=[str(media.LOCAL)])
        for name in ('FORWARD_FIRST', 'RELEASE_INSTALLED', 'LOGIN_REFUSAL', 'BAZZITE_WAITING'):
            values[name] = [getattr(owner, name)]
        candidates = output_templates(source, values) | output_templates((TOOLS / 'media.py').read_text(), values)
        candidates |= {'STOP: ' + line for line in candidates}
        for filename in ('owner.py', 'media.py'):
            # A failed bootstrap can leave version 2 installed. The guide names its older output.
            archived = subprocess.check_output(
                ['git', 'show', f'41b06513:os/owner-tools/payload/{filename}'], cwd=ROOT, text=True)
            candidates |= output_templates(archived, {})
        commands = json.loads((TOOLS / 'commands.json').read_text())
        self.assertIn("print('PASS ' + ' '.join(sys.argv[1:]))", source)
        known = next(node.value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Assign)
                     and any(word(target) == 'known' for target in node.targets) and isinstance(node.value, ast.Set))
        candidates |= {'PASS ' + verb for verb in ast.literal_eval(known) - {'layout'}}
        candidates |= {'PASS ' + command.split('sudo /var/lib/ares/at ', 1)[1]
                       for key, command in commands.items() if key.startswith('layout-')}
        missing = [(page, number, quote) for page, guide in documents().items() if page in GUIDES
                   for number, quote in quoted_results(page, guide) if not matches_output(quote, candidates)]
        self.assertFalse(missing, '\n' + '\n'.join(f'{page}:{number}: {quote}' for page, number, quote in missing))
        invented = 'Forward to … verified after the restart'
        self.assertEqual(list(quoted_results('INSTALL.md', f'Require **{invented}**.')), [(1, invented)])
        self.assertFalse(matches_output(invented, candidates))

    def test_previous_and_forward_require_their_own_confirmation(self):
        guide = documents()['INSTALL.md']
        previous = section(guide, 'return-to-the-older-aresos')
        forward = section(guide, 'update-aresos-to-a-new-release').split('- [ ] **Forward again', 1)[1]
        for text, command, confirmation in (
            (previous, 'previous', 'Return to … confirmed after the restart'),
            (forward, 'forward', 'Forward to … confirmed after the restart'),
        ):
            with self.subTest(command=command):
                check_selection_route(text, command, confirmation)
                wrong = text.replace(confirmation, 'Update to … confirmed after the restart')
                with self.assertRaises(AssertionError):
                    check_selection_route(wrong, command, confirmation)
                with self.assertRaises(AssertionError):
                    check_selection_route(text.replace('#run-at-check)', '#update-aresos-to-a-new-release)')
                                          + '\nThen repeat the check box.', command, confirmation)
