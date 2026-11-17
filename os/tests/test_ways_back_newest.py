"""43 step 2: D2's independent choice and I1–I4, including tools mutations.

All commands run through the model's intercepted host. No installed tools entry
or deployment command is executed. Reverts change Python methods only in memory.
"""
import unittest
from collections import deque
from dataclasses import replace
from unittest.mock import patch

import test_ways_back_model as model
from ways_back_ledger import Ledger, Journal, choose, starts, transition, steps, reduced
from ways_back_memo import Executions

owner = model.owner


def path(s, *events):
    for event in events:
        s = transition(s, event).state
    return s


def danger():
    return path(starts()[3], ('previous', 'full'), ('restart', 'default'), ('title', 'full'))


class ChoiceTest(unittest.TestCase):
    def rows(self):
        current, fresh = starts()[2:4]
        older = danger()
        invalid = replace(fresh, journal=Journal('forward', 'reorder', 'intent', '27', '13', ('S', '27', '13')))
        stock = Ledger('28', ('S',), 'S', settings=(('S', 'de', 'de'),))
        return [
            (0, invalid, ''),
            (1, stock, ''),
            (2, path(fresh, ('update', 'primitive'), ('power-off', 'default')), ''),
            (3, path(fresh, ('update', 'primitive')), 'update'),
            (4, path(fresh, ('update', 'intent')), 'update'),
            (5, path(older, ('update', 'intent')), ''),
            (6, path(fresh, ('update', 'full')), ''),
            (7, fresh, 'update'),
            (8, current, ''),
            (9, replace(current, running='S'), ''),
            (10, older, 'forward'),
        ]

    def test_every_table_row_is_predicted_before_the_tools_run(self):
        with model.driver() as d:
            for row, s, chosen in self.rows():
                with self.subTest(row=row):
                    expected = transition(s, ('newest', 'full'))
                    self.assertEqual(choose(s), row)
                    self.assertEqual(expected.chosen, chosen)
                    d.step(s, ('newest', 'full'), expected)
                    self.assertEqual(d.tools.chosen or '', chosen)

    def test_chosen_words_keep_their_own_transitions_and_cut_phases(self):
        with model.driver() as d:
            for row, s, chosen in self.rows():
                for phase in ('intent', 'primitive', 'record', 'full'):
                    if not chosen:
                        continue
                    with self.subTest(row=row, phase=phase):
                        expected = transition(s, ('newest', phase))
                        inner = transition(s, (chosen, phase))
                        self.assertEqual(expected, replace(inner, chosen=chosen))
                        d.step(s, ('newest', phase), expected)
                        if expected.cut:
                            self.assertTrue(d.checkpoints)

    def test_completed_staging_from_an_older_release_only_records_it(self):
        s = path(danger(), ('update', 'primitive'))
        self.assertEqual(choose(s), 3)
        with model.driver() as d:
            expected = transition(s, ('newest', 'full'))
            d.step(s, ('newest', 'full'), expected)
            self.assertFalse(d.host.changes)
            self.assertEqual(d.checkpoints[0][0], 'journal:recorded')
            self.assertIn('Saving the record', d.checkpoints[0][1])
            self.assertEqual((expected.state.stage, expected.state.running), ('28', '13'))

    def test_pending_returns_and_keep_stock_have_different_choices(self):
        s = starts()[3]
        cases = [('update', s), ('previous', s), ('rollback', s), ('forward', danger())]
        with model.driver() as d:
            for word, start in cases:
                pending = path(start, (word, 'full'))
                self.assertEqual(choose(pending), 6, word)
                expected = transition(pending, ('newest', 'full'))
                d.step(pending, ('newest', 'full'), expected)
                self.assertEqual(expected.state, pending)
                self.assertFalse(d.checkpoints or d.host.changes)
            kept = path(s, ('restart', 'S'), ('keep-stock', 'full'))
            self.assertEqual(choose(kept), 10)
            d.step(kept, ('newest', 'full'), transition(kept, ('newest', 'full')))
            self.assertEqual(d.tools.chosen, 'forward')

    def test_failed_staging_is_held_for_one_run_and_check_consumes_the_notice(self):
        with model.driver() as d:
            for start, next_row in ((starts()[3], 7), (danger(), 10)):
                failed = path(start, ('update', 'primitive'), ('power-off', 'default'))
                expected = transition(failed, ('newest', 'full'))
                d.step(failed, ('newest', 'full'), expected)
                self.assertEqual(expected.archives, ('not-applied',))
                self.assertEqual(choose(expected.state), next_row)
                self.assertFalse(d.host.changes)
                d.step(expected.state, ('newest', 'full'), transition(expected.state, ('newest', 'full')))
            checked = path(failed, ('check', 'full'))
            self.assertEqual(choose(checked), 10)
            failed = path(starts()[3], ('update', 'primitive'), ('power-off', 'default'))
            checked = model.RevertTest().path(d, failed, [('check', 'full')])
            self.assertEqual(choose(checked), 7)
            d.step(checked, ('newest', 'full'), transition(checked, ('newest', 'full')))
            self.assertEqual(d.tools.chosen, 'update')

    def test_failed_reorder_is_resolved_then_the_table_goes_on(self):
        s = path(danger(), ('forward', 'intent'), ('restart', 'default'))
        self.assertEqual(s.outcome(), 'not-applied')
        self.assertEqual(choose(s), 10)
        with model.driver() as d:
            expected = transition(s, ('newest', 'full'))
            d.step(s, ('newest', 'full'), expected)
            self.assertEqual(expected.archives, ('not-applied',))
            self.assertEqual(d.tools.chosen, 'forward')
            self.assertIn('was not applied', d.checkpoints[0][1])

    def test_survey_record_cut_happens_before_any_choice_or_announcement(self):
        s = path(starts()[3], ('rollback', 'primitive'), ('restart', '27'))
        with model.driver() as d:
            expected = transition(s, ('newest', 'record'))
            self.assertTrue(expected.cut)
            self.assertEqual(expected.chosen, '')
            d.step(s, ('newest', 'record'), expected)
            self.assertEqual(d.checkpoints, [('journal:recorded', '')])

    def test_all_forward_wordings_and_the_next_install_run(self):
        older = danger()
        stock = path(starts()[3], ('restart', 'S'), ('keep-stock', 'full'))
        running_newest = path(starts()[3], ('rollback', 'full'), ('restart', '27'))
        with model.driver() as d:
            for s in (older, stock, running_newest):
                self.assertEqual(choose(s), 10)
                selected = model.RevertTest().path(d, s, [('newest', 'full')])
                output = d.observed[-1]
                self.assertIn('No restart is needed first' if s is running_newest else 'After the restart', output)
                self.assertIn('Update:', output)
                self.assertFalse(selected.stage)
            self.assertEqual(choose(selected), 7)
            model.RevertTest().path(d, selected, [('newest', 'full')])

    def test_newest_preserves_breadth_first_order_and_adds_no_state(self):
        def prefix(newest):
            queue = deque(starts())
            seen = {reduced(s) for s in queue}
            ordered = [reduced(s) for s in queue]
            processed = []
            for _ in range(2000):
                s = queue.popleft()
                processed.append(reduced(s))
                for event, result in steps(s):
                    if not newest and event[0] == 'newest':
                        continue
                    key = reduced(result.state)
                    if key not in seen:
                        seen.add(key)
                        ordered.append(key)
                        queue.append(result.state)
            return processed, ordered
        self.assertEqual(prefix(False), prefix(True))

    def test_execution_reuse_matches_uncached_newest_with_each_etc_and_journal(self):
        with model.driver() as d:
            memo = Executions(d)
            samples = [s for row, s, chosen in self.rows() if row not in (0, 1)]
            for s in samples:
                for profile in ('de', 'us', 'us-intl'):
                    state = s.setting('S', profile, profile)
                    for event, expected in steps(state):
                        if event[0] == 'newest':
                            self.assertEqual(memo.step(state, event, expected), d.step(state, event, expected))
            self.assertGreater(memo.reused, 0)


class JudgmentRevertsTest(unittest.TestCase):
    def test_i1_catches_replacing_newest_with_the_inner_update_in_the_danger_state(self):
        s = danger()
        with model.driver() as d, patch.object(owner.Tools, 'newest', owner.Tools.update):
            with self.assertRaisesRegex(AssertionError, 'I1:'):
                d.step(s, ('newest', 'full'), transition(s, ('newest', 'full')))

    def test_i2_catches_inner_word_advice_in_both_own_lines_and_stops(self):
        real = owner.Tools.newest
        def bad_line(tools):
            return [*real(tools), owner.typed('update')]
        def bad_stop(tools):
            raise owner.Stop('Run ' + owner.typed('forward'))
        # Check both a result of newest alone and a line added to an inner
        # operation's result. The title's own lines remain exempt.
        for s in (starts()[2], danger()):
            for mutation in (bad_line, bad_stop):
                with self.subTest(rows=s.rows, mutation=mutation.__name__), model.driver() as d:
                    with patch.object(owner.Tools, 'newest', mutation), self.assertRaisesRegex(AssertionError, 'I2:'):
                        d.step(s, ('newest', 'full'), transition(s, ('newest', 'full')))

    def test_i3_catches_announcements_delayed_until_after_intent_or_mutation(self):
        real = owner.Tools.newest
        def delayed(tools):
            buffered = []
            with patch.object(tools, 'newest_say', buffered.append):
                lines = real(tools)
            for line in buffered:
                tools.newest_say(line)
            return lines
        for s in (starts()[3], danger(), path(starts()[3], ('update', 'primitive'))):
            for phase in ('intent', 'primitive', 'full'):
                with self.subTest(rows=s.rows, phase=phase), model.driver() as d:
                    with patch.object(owner.Tools, 'newest', delayed), self.assertRaisesRegex(AssertionError, 'I3:'):
                        d.step(s, ('newest', phase), transition(s, ('newest', phase)))

    def test_i3_also_checks_the_mutation_when_the_intent_has_its_announcement(self):
        # Remove the already printed announcement after journalling. The host
        # must observe output again at the primitive, not reuse the intent's copy.
        real = owner.Tools.intend
        with model.driver() as d:
            def erased(tools, *args, **kwargs):
                real(tools, *args, **kwargs)
                d.output.seek(0)
                d.output.truncate()
            with patch.object(owner.Tools, 'intend', erased), self.assertRaisesRegex(AssertionError, 'I3:.*(stage|set-default)'):
                s = starts()[3]
                d.step(s, ('newest', 'full'), transition(s, ('newest', 'full')))

    def test_i4_catches_an_announcement_before_a_predictable_refusal(self):
        real = owner.Tools.newest
        def early(tools):
            owner.say('Update: switching to the latest installed version')
            return real(tools)
        s = path(starts()[3], ('begin', 'us'))
        with model.driver() as d, patch.object(owner.Tools, 'newest', early):
            with self.assertRaisesRegex(AssertionError, 'I4: announcement followed by refusal'):
                d.step(s, ('newest', 'full'), transition(s, ('newest', 'full')))

    def test_i4_catches_spurious_and_contradicted_announcements(self):
        real = owner.Tools.newest
        def spurious(tools):
            owner.say('Update: switching to the latest installed version')
            return real(tools)
        def nothing(tools):
            return [*real(tools), 'Nothing changed']
        for s, mutation, message in ((starts()[2], spurious, 'without change or cut'),
                                      (danger(), nothing, 'Nothing after announcement')):
            with self.subTest(mutation=mutation.__name__), model.driver() as d:
                with patch.object(owner.Tools, 'newest', mutation), self.assertRaisesRegex(AssertionError, 'I4:.*' + message):
                    d.step(s, ('newest', 'full'), transition(s, ('newest', 'full')))

    def test_i4_catches_a_forward_announcement_even_when_the_chosen_word_is_update(self):
        s = starts()[3]
        with model.driver() as d, patch.object(owner.Tools, 'announce_update', owner.Tools.announce_forward):
            with self.assertRaisesRegex(AssertionError, 'I4: forward announced where newest runs and starts next'):
                d.step(s, ('newest', 'full'), transition(s, ('newest', 'full')))


if __name__ == '__main__':
    unittest.main()
