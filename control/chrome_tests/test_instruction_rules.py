"""Steps 0a and 1d: every instruction kept while text moves, and the switched catalogue pinned.

The baseline is frozen from package 28 at cd2ce599: main's Chrome instructions,
each sentence of them mapped to where it is stated now (`rules`), and main's
sizes. Step 1d adds brief 28a item 7's list of rules (`item7_rules`) with their
homes, and the final sizes of the nineteen tools (`final_sizes`).
main-ask-rules.json is the verbatim generated file on main at 7417c19a, so
shallow CI needs no Git history.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.definitions import COMMON_INSTRUCTIONS, instructions_for, tools_for
from aresos_control.boundary_policy import asking_rules

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / 'fixtures/28a-instructions'
BASELINE = json.loads((FIXTURES / 'baseline.json').read_text())


DOCUMENT = ROOT / 'reviews/28a-chrome-act/TOOL-DESCRIPTIONS.md'


def document():
    """reviews/28a-chrome-act/TOOL-DESCRIPTIONS.md: the descriptions and the instructions exactly as generated."""
    tools = tools_for('chrome')
    instructions = instructions_for('chrome')
    final = BASELINE['final_sizes']
    out = ['# Chrome tool descriptions and instructions (package 28a, step 1d)', '',
           'Exactly as `instructions_for(\'chrome\')` and `tools_for(\'chrome\')` give them, which are the generated',
           '`control/generated/chrome-instructions.txt` and `chrome-tools.json`. Written by `document()` in',
           '`control/chrome_tests/test_instruction_rules.py`, which fails when this file and the catalogue differ.', '',
           '| | Main at this package\'s start | Step 1d |', '|---|---:|---:|']
    for key, label in (('tools', 'Tools offered'), ('descriptions', 'Descriptions'), ('instructions', 'Server instructions'),
                       ('descriptions_and_instructions', 'Descriptions plus instructions'),
                       ('names_and_input_schemas', 'Names plus input schemas (compact JSON)')):
        out.append('| %s | %s | %s |' % (label, format(BASELINE['sizes'][key], ','), format(final[key], ',')))
    out += ['', '## Server instructions (%s characters)' % format(len(instructions), ','), '', '```text', instructions, '```', '']
    for tool in tools:
        out += ['## `chrome_%s` (%s characters)' % (tool['name'], format(len(tool['description']), ',')), '',
                '```text', tool['description'], '```', '']
    return '\n'.join(out)


class InstructionRules(unittest.TestCase):
    def test_tool_descriptions_document_is_exactly_as_generated(self):
        self.assertEqual(DOCUMENT.read_text(), document())

    def test_map_accounts_for_the_complete_old_chrome_text(self):
        rules = BASELINE['rules']
        self.assertEqual([rule['number'] for rule in rules], list(range(1, 24)))
        self.assertEqual(' '.join(rule['before'] for rule in rules),
                         ' '.join(BASELINE['chrome_text'].split()))
        self.assertEqual(len(COMMON_INSTRUCTIONS) + 2 + len(BASELINE['chrome_text']),
                         BASELINE['sizes']['instructions'])

    def homes(self):
        return {'instructions': instructions_for('chrome'),
                **{'chrome_' + tool['name']: tool['description'] for tool in tools_for('chrome')}}

    def test_every_old_rule_is_stated_in_its_new_home(self):
        # Every original sentence must be mapped, not merely a selected subset.
        self.assertEqual(len(BASELINE['rules']), 23)
        self.assertEqual(' '.join(rule['before'] for rule in BASELINE['rules']),
                         ' '.join(BASELINE['chrome_text'].split()))
        homes = self.homes()
        for rule in BASELINE['rules']:
            self.assertTrue(rule['after'], rule['number'])
            for destination in rule['after']:
                with self.subTest(rule=rule['number'], home=destination['home']):
                    self.assertIn(destination['text'], homes[destination['home']])

    def test_every_rule_of_item_7_is_stated_in_its_home(self):
        # Brief 28a, item 7's list of the rules every action shares, and the single-tool ones it names.
        self.assertEqual(len(BASELINE['item7_rules']), 21)
        homes = self.homes()
        for rule in BASELINE['item7_rules']:
            self.assertTrue(rule['after'], rule['rule'])
            for destination in rule['after']:
                with self.subTest(rule=rule['rule'], home=destination['home']):
                    self.assertIn(destination['text'], homes[destination['home']])

    def test_single_tool_rules_live_in_their_descriptions(self):
        instructions = instructions_for('chrome')
        for rule in [*BASELINE['rules'], *BASELINE['item7_rules']]:
            for destination in rule['after']:
                if destination['home'] != 'instructions':
                    with self.subTest(rule=rule.get('number', rule.get('rule'))):
                        self.assertNotIn(destination['text'], instructions)

    def test_no_instruction_or_description_names_a_tool_the_list_doesnt_offer(self):
        # Brief 20's replaced tools are gone from the public list; nothing Claude reads names one.
        offered = {'chrome_' + tool['name'] for tool in tools_for('chrome')}
        for home, text in self.homes().items():
            for name in re.findall(r'chrome_[a-z_]+', text):
                with self.subTest(home=home, name=name):
                    self.assertIn(name, offered)

    def test_common_instructions_are_byte_identical(self):
        self.assertEqual(hashlib.sha256(COMMON_INSTRUCTIONS.encode()).hexdigest(), BASELINE['common_sha256'])
        self.assertTrue(instructions_for('chrome').startswith(COMMON_INSTRUCTIONS + '\n\n'))

    def test_the_switched_catalogue_is_pinned(self):
        # Step 1d: the nineteen tools, their names, inputs, results and hints, apart from the descriptions
        # the size pins below count. A change fails here until the pin moves on purpose.
        from aresos_control.chrome.loss import ERROR
        final = BASELINE['final_sizes']
        tools = tools_for('chrome')
        self.assertEqual([tool['name'] for tool in tools], final['names'])
        for tool in tools:
            self.assertEqual(tool['outputSchema']['properties']['error'], ERROR, tool['name'])
        structure = [{key: value for key, value in tool.items() if key != 'description'} for tool in tools]
        encoded = json.dumps(structure, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), final['catalogue_structure_sha256'])

    def test_the_sizes_stay_within_mains_and_are_pinned(self):
        # Brief 28a, item 7: not above main's catalogue at this package's start, measured as brief 18d measured
        # Mail's (efficiency-summary.py's sizes), and pinned exactly; brief 28b starts from these totals.
        spec = importlib.util.spec_from_file_location('efficiency_summary', ROOT / 'control/chrome/ci/efficiency-summary.py')
        summary = importlib.util.module_from_spec(spec); spec.loader.exec_module(summary)
        main, final, now = BASELINE['sizes'], BASELINE['final_sizes'], summary.sizes()
        self.assertEqual(main, {'tools': 30, 'descriptions': 5085, 'instructions': 4093,
                                'descriptions_and_instructions': 9178, 'names_and_input_schemas': 11080})
        self.assertEqual(now['tools'], 19)
        self.assertLessEqual(now['descriptions_and_instructions'], main['descriptions_and_instructions'])
        self.assertLessEqual(now['names_and_input_schemas'], main['names_and_input_schemas'])
        self.assertEqual(now, {key: final[key] for key in now})

    def test_the_instructions_fit_2800_characters(self):
        # Brief 28a, item 7: rules that span tools only, at most 2,800 characters with the shared 1,762;
        # brief 28b moves this pin to 3,800. test_questions keeps every app within Claude Code's 4,096.
        from aresos_control.chrome.definitions import SHARED, CLIPBOARD_NOTICE
        instructions = instructions_for('chrome')
        self.assertLessEqual(len(instructions), 2800)
        self.assertEqual(instructions, COMMON_INSTRUCTIONS + '\n\n' + SHARED + ' ' + CLIPBOARD_NOTICE)
        self.assertLessEqual(len(instructions) - len(COMMON_INSTRUCTIONS), 1148)
        self.assertEqual(len(instructions), BASELINE['final_sizes']['instructions'])

    def test_generated_ask_rules_are_main_bytes(self):
        from generate import generated
        main = (FIXTURES / 'main-ask-rules.json').read_bytes()
        self.assertEqual((ROOT / 'control/settings/ask-rules.json').read_bytes(), main)
        artifacts = generated()
        self.assertEqual(artifacts['control/settings/ask-rules.json'].encode(), main)
        expected = [rule for rule in json.loads(main)['permissions']['ask']
                    if rule.startswith('mcp__chrome__')]
        self.assertEqual(expected, ['mcp__chrome__read_typed_fields', 'mcp__chrome__submit'])
        self.assertEqual([rule for rule in asking_rules() if rule.startswith('mcp__chrome__')], expected)
        managed = json.loads(artifacts['control/settings/managed-settings.draft.json'])
        self.assertEqual([rule for rule in managed['permissions']['ask']
                          if rule.startswith('mcp__chrome__')], expected)
