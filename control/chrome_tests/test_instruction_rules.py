"""Step 0a: preserve the old catalogue and every instruction while moving text.

The baseline is frozen from package 28 at cd2ce599. main-ask-rules.json is the
verbatim generated file on main at 7417c19a, so shallow CI needs no Git history.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.definitions import COMMON_INSTRUCTIONS, instructions_for, tools_for
from aresos_control.boundary_policy import asking_rules

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / 'fixtures/28a-instructions'
BASELINE = json.loads((FIXTURES / 'baseline.json').read_text())


class InstructionRules(unittest.TestCase):
    def test_map_accounts_for_the_complete_old_chrome_text(self):
        rules = BASELINE['rules']
        self.assertEqual([rule['number'] for rule in rules], list(range(1, 24)))
        self.assertEqual(' '.join(rule['before'] for rule in rules),
                         ' '.join(BASELINE['chrome_text'].split()))
        self.assertEqual(len(COMMON_INSTRUCTIONS) + 2 + len(BASELINE['chrome_text']),
                         BASELINE['sizes']['instructions'])

    def test_every_old_rule_is_stated_in_its_new_home(self):
        # Every original sentence must be mapped, not merely a selected subset.
        self.assertEqual(len(BASELINE['rules']), 23)
        self.assertEqual(' '.join(rule['before'] for rule in BASELINE['rules']),
                         ' '.join(BASELINE['chrome_text'].split()))
        homes = {'instructions': instructions_for('chrome'),
                 **{'chrome_' + tool['name']: tool['description'] for tool in tools_for('chrome')}}
        for rule in BASELINE['rules']:
            self.assertTrue(rule['after'], rule['number'])
            for destination in rule['after']:
                with self.subTest(rule=rule['number'], home=destination['home']):
                    self.assertIn(destination['text'], homes[destination['home']])

    def test_single_tool_rules_live_in_their_descriptions(self):
        instructions = instructions_for('chrome')
        for rule in BASELINE['rules']:
            for destination in rule['after']:
                if destination['home'] in {'chrome_tabs', 'chrome_click', 'chrome_prepare_read_typed_fields'}:
                    with self.subTest(rule=rule['number']):
                        self.assertNotIn(destination['text'], instructions)

    def test_common_instructions_are_byte_identical(self):
        self.assertEqual(hashlib.sha256(COMMON_INSTRUCTIONS.encode()).hexdigest(), BASELINE['common_sha256'])
        self.assertTrue(instructions_for('chrome').startswith(COMMON_INSTRUCTIONS + '\n\n'))

    def test_catalogue_changes_only_descriptions(self):
        structure = [{key: value for key, value in tool.items() if key != 'description'}
                     for tool in tools_for('chrome')]
        encoded = json.dumps(structure, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(len(structure), BASELINE['sizes']['tools'])
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), BASELINE['catalogue_structure_sha256'])

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
