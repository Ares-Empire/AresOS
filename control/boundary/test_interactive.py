"""Quick tests of evidence-critical parsing and the model's turn boundary."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from interactive_driver import Terminal, answer_option, selected_option
from interactive_model import Script
from interactive_suite import SCOPES, SEND, check_case_evidence, check_send_turn, step


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
        unnumbered = '  ❯ No, exit\n    Yes, I accept\n'
        self.assertEqual(answer_option(unnumbered, 'warning'), (None, 'Yes, I accept'))
        self.assertTrue(selected_option(unnumbered, None, 'No, exit'))
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
    def test_daa_rejects_send_2_arrival_and_swapped_results(self):
        scripts = [step(i) for i in (1, 2, 3)]
        requests = [{'messages': [{'role': 'assistant', 'content': [
            {'type': 'tool_use', 'id': 'send-' + str(i), 'name': SEND, 'input': script['approval']}
            for i, script in enumerate(scripts[:2])]}]}]
        success = {'type': 'tool_result', 'tool_use_id': 'send-0',
                   'content': [{'type': 'text', 'text': 'FIXTURE_SEND_RAN'}]}
        refusal = {'type': 'tool_result', 'tool_use_id': 'send-1', 'is_error': True,
                   'content': "The user doesn't want to proceed with this tool use. The tool use was rejected"}
        good = {'send-0': success, 'send-1': refusal}
        swapped = {'send-0': dict(refusal, tool_use_id='send-0'),
                   'send-1': dict(success, tool_use_id='send-1')}
        # All three bad recordings have the old passing cumulative count and
        # result count. Check arrivals and result meaning independently too.
        for counts, results in [([0, 1], swapped), ([0, 1], good), ([1, 1], swapped)]:
            self.assertEqual(counts[-1], 1)
            self.assertEqual(len(results), 2)
            for index in (0, 1):
                with self.subTest(counts=counts, results=results, send=index + 1), self.assertRaises(AssertionError):
                    check_send_turn(scripts[index], index, requests, results,
                                    0 if index == 0 else counts[0], counts[index], index == 0)
        check_send_turn(scripts[0], 0, requests, good, 0, 1, True)
        check_send_turn(scripts[1], 1, requests, good, 1, 1, False)
        restarted = [{'messages': [{'role': 'assistant', 'content': [
            {'type': 'tool_use', 'id': 'send-0', 'name': SEND, 'input': scripts[2]['approval']}]}]}]
        third = {'send-0': dict(refusal, tool_use_id='send-0')}
        check_send_turn(scripts[2], 0, restarted, third, 1, 1, False)
        with self.assertRaises(AssertionError):
            check_send_turn(scripts[2], 0, restarted, third, 1, 2, False)

    def test_send_result_id_and_operation_are_bound_to_the_tool_use(self):
        script = step(1)
        use = {'type': 'tool_use', 'id': 'send-0', 'name': SEND, 'input': script['approval']}
        requests = [{'messages': [{'role': 'assistant', 'content': [use]}]}]
        result = {'type': 'tool_result', 'tool_use_id': 'another-send',
                  'content': [{'type': 'text', 'text': 'FIXTURE_SEND_RAN'}]}
        with self.assertRaises(AssertionError):
            check_send_turn(script, 0, requests, {'send-0': result}, 0, 1, True)
        result['tool_use_id'] = 'send-0'
        use['input'] = step(2)['approval']
        with self.assertRaises(AssertionError):
            check_send_turn(script, 0, requests, {'send-0': result}, 0, 1, True)
        use['input'] = script['approval']
        result.update(is_error=True, content='MCP transport failed')
        with self.assertRaises(AssertionError):
            check_send_turn(script, 0, requests, {'send-0': result}, 0, 0, False)

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


class Evidence(unittest.TestCase):
    def test_daa_requires_written_grant_and_retention_after_process_start(self):
        root = Path(__file__).resolve().parents[2] / '.work'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            case = Path(folder) / 'normal-daa'
            grant = {'permissions': {'allow': [SEND]}}
            settings = {str(SCOPES['local']): grant}
            row = {'case': 'normal-daa', 'send_arrivals': 1, 'hook_calls': 0,
                   'prompt_shown': [True, True], 'daa_offered': [True, True], 'owner_answers': 2,
                   'new_session': {'prompt_shown': [True], 'owner_answers': 1}}

            def save(session, name, value):
                path = case / session / (name + '.json')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))

            for session, numbers in [('session-1', [1, 2]), ('session-3', [3])]:
                uses, results, turns, actions = [], {}, [], []
                for index, number in enumerate(numbers):
                    identifier = 'send-' + str(index)
                    script = step(number)
                    uses.append({'type': 'tool_use', 'id': identifier, 'name': SEND, 'input': script['approval']})
                    result = {'type': 'tool_result', 'tool_use_id': identifier}
                    result.update({'content': [{'type': 'text', 'text': 'FIXTURE_SEND_RAN'}]} if number == 1 else
                                  {'is_error': True, 'content': "The user doesn't want to proceed with this tool use. The tool use was rejected"})
                    results[identifier] = result
                    turns.append({'prompt': script['prompt'], 'tool_use_id': identifier,
                                  'operation_id': script['approval']['operation_id'],
                                  'arrivals_before': int(number > 1), 'arrivals_after': 1})
                    option = "Yes, and don't ask again for this tool" if number == 1 else 'No'
                    screen = str(number) + '.txt'
                    save(session, 'settings-after-turn-' + str(index + 1), settings)
                    (case / session / screen).write_text(
                        'question: Send this fixture message?\noperation_id: ' + script['approval']['operation_id'] +
                        '\ndescription: Synthetic fixed payload\n1. ' + option + '\n')
                    actions.append({'screen': screen, 'key': '1', 'option': option})
                for name, value in [('requests', [{'messages': [{'role': 'assistant', 'content': uses}]}]),
                                    ('results', results), ('turns', turns), ('error', None),
                                    ('settings-before', settings), ('settings-after-start', settings)]:
                    save(session, name, value)
                (case / session / 'actions.jsonl').write_text(''.join(json.dumps(a) + '\n' for a in actions))
            check_case_evidence(case, row, {})
            # A correct prelaunch file does not prove the new CLI kept it.
            for session, name in [('session-1', 'settings-after-turn-1'),
                                  ('session-1', 'settings-after-turn-2'),
                                  ('session-3', 'settings-before'),
                                  ('session-3', 'settings-after-start'),
                                  ('session-3', 'settings-after-turn-1')]:
                with self.subTest(session=session, snapshot=name):
                    save(session, name, {str(SCOPES['local']): {}})
                    with self.assertRaises(AssertionError):
                        check_case_evidence(case, row, {})
                    save(session, name, settings)
            row['daa_offered'][0] = False
            with self.assertRaises(AssertionError):
                check_case_evidence(case, row, {})


class RealToolResultTest(unittest.TestCase):
    """Package 18c, B2: in the VM the real proxy's result arrives as one string, not as text blocks."""

    def test_the_approval_is_copied_from_a_string_result(self):
        from interactive_model import Script
        approval = {'question': 'Send this fixture message?', 'operation_id': 'op-1', 'description': {}}
        step = {'prompt': 'P1', 'prepare': {'name': 'prepare', 'input': {}}, 'send': 'send'}
        script = Script([step])
        first = script.respond({'messages': [{'role': 'user', 'content': 'P1'}]})
        self.assertEqual(first[0]['id'], 'prepare-0')
        result = {'type': 'tool_result', 'tool_use_id': 'prepare-0',
                  'content': json.dumps({'ok': True, 'data': {'approval': approval}})}
        second = script.respond({'messages': [{'role': 'user', 'content': 'P1'},
                                              {'role': 'user', 'content': [result]}]})
        self.assertEqual((second[0]['name'], second[0]['input']), ('send', approval))


if __name__ == '__main__':
    unittest.main()
