"""Quick tests of evidence-critical parsing and the model's turn boundary."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from interactive_driver import Terminal, answer_option, selected_option
from interactive_model import Script


class Answers(unittest.TestCase):
    def test_choose_by_label_even_when_numbering_changes(self):
        screen = "  3. No\n❯ 1. Yes\n  2. Yes, and don't ask again for this tool\n"
        self.assertEqual(answer_option(screen, 'No'), ('3', 'No'))
        self.assertEqual(answer_option(screen, 'Yes'), ('1', 'Yes'))
        self.assertEqual(answer_option(screen, 'DAA')[0], '2')
        self.assertTrue(selected_option(screen, '1', 'Yes'))
        self.assertFalse(selected_option(screen, '3', 'No'))
        with self.assertRaises(AssertionError):
            answer_option('1. Yes, and do something else\n2. No', 'Yes')

    def test_unexpected_warning_is_not_permission(self):
        screen = '1. No, exit\n2. Yes, I accept\n'
        self.assertEqual(answer_option(screen, 'warning'), ('2', 'Yes, I accept'))
        with self.assertRaises(AssertionError):
            answer_option(screen, 'Yes')

    def test_numeric_submit_and_selection_only_both_complete(self):
        root = Path(__file__).resolve().parents[2] / '.work'
        root.mkdir(exist_ok=True)
        before = '❯ 1. Yes\n  3. No\n'
        for after, confirms in [('Interrupted · What should Claude do instead?', False),
                                ('  1. Yes\n❯ 3. No\n', True)]:
            with self.subTest(confirms=confirms), tempfile.TemporaryDirectory(dir=root) as folder:
                terminal = Terminal(None, folder, 'unused', '.', [], {})
                with patch.object(terminal, 'tmux') as command, patch.object(terminal, 'wait', side_effect=[before, after]):
                    terminal.choose(before, 'No')
                sent = [call.args[-1] for call in command.call_args_list]
                self.assertEqual(sent, ['3', '\r'] if confirms else ['3'])

    def test_dialog_must_stay_visible_for_the_input_guard_interval(self):
        root = Path(__file__).resolve().parents[2] / '.work'
        root.mkdir(exist_ok=True)
        clock = [0.0]

        def poll_pause(interval):
            clock[0] += interval

        def screen():
            return 'loading' if .3 <= clock[0] < .5 else '❯ 1. Yes\n3. No\n'

        with tempfile.TemporaryDirectory(dir=root) as folder:
            terminal = Terminal(None, folder, 'unused', '.', [], {})
            with patch.object(terminal, 'screen', side_effect=screen), \
                 patch('interactive_driver.time.monotonic', side_effect=lambda: clock[0]), \
                 patch('interactive_driver.time.sleep', side_effect=poll_pause):
                observed = terminal.wait('ready', lambda s: '1. Yes' in s, timeout=3, stable_for=1)
            self.assertIn('1. Yes', observed)
            self.assertGreaterEqual(clock[0], 1.5)


class Turns(unittest.TestCase):
    def test_stop_continuation_cannot_send_next_owner_step(self):
        script = Script([{'prompt': f'OWNER_{i}', 'send': 'send', 'approval': {'question': 'Q'}} for i in (1, 2)])
        messages = [{'role': 'user', 'content': 'OWNER_1'}]
        request = {'messages': messages}
        self.assertEqual(script.respond(request)[0]['id'], 'send-0')
        messages.append({'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'send-0',
                                                    'content': 'denied', 'is_error': True}]})
        self.assertEqual(script.respond(request)[0]['text'], 'INTERACTIVE_DONE_1')
        messages.append({'role': 'user', 'content': 'STOP_REMINDER'})
        self.assertEqual(script.respond(request)[0]['text'], 'INTERACTIVE_CONTINUATION_DONE_1')
        self.assertEqual(len(script.continuations), 1)
        messages.append({'role': 'user', 'content': 'OWNER_2'})
        self.assertEqual(script.respond(request)[0]['id'], 'send-1')

    def test_prepared_approval_is_copied_unchanged(self):
        approval = {'question': 'Q', 'operation_id': 'fixed', 'description': {'text': 'Exact'}}
        script = Script([{'prompt': 'OWNER_1', 'prepare': {'name': 'prepare', 'input': {'text': 'Written in full'}},
                          'send': 'send'}])
        request = {'messages': [{'role': 'user', 'content': 'OWNER_1'}]}
        self.assertEqual(script.respond(request)[0]['name'], 'prepare')
        request['messages'].append({'role': 'user', 'content': [{'type': 'tool_result',
            'tool_use_id': 'prepare-0', 'content': [{'type': 'text',
            'text': json.dumps({'ok': True, 'data': {'approval': approval}})}]}]})
        self.assertEqual(script.respond(request)[0]['input'], approval)
        self.assertEqual(len(script.issued), 2)


if __name__ == '__main__':
    unittest.main()
