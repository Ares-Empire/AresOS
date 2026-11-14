"""22c B11: remove each A rule in memory and require its guarding assertion to fail.

No production file is rewritten. The existing named tests are reused, and an
unexpected exception is NOT accepted as a successful revert proof. Version-2
compatibility mutations belong to B8; this module covers A9's unknown schema.
"""
import inspect
import pathlib
import textwrap
import unittest
from dataclasses import replace
from unittest.mock import patch

import test_ways_back as focused
import test_ways_back_model as model
import ways_back_ledger as ledger
from ways_back_ledger import starts, transition

owner = model.owner


def mutated(function, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    assert source.count(before) == 1, 'mutation no longer matches exactly once'
    namespace = {}
    exec(compile(source.replace(before, after), '<22c rule removed>', 'exec'), owner.__dict__, namespace)
    return namespace[function.__name__]


class RuleRevertsTest(unittest.TestCase):
    def detected_by(self, case, mention=None):
        result = unittest.TestResult()
        case.run(result)
        self.assertEqual(result.errors, [], 'an unrelated exception is not a revert proof')
        self.assertTrue(result.failures, case.id() + ' did not detect the removed rule')
        if mention is not None:
            for _, failure in result.failures:
                self.assertIn(mention, failure)

    def ledger_detects(self, d, s, event, message='accept/refuse|ledger differs'):
        expected = transition(s, event)
        with self.assertRaisesRegex(AssertionError, message):
            d.step(s, event, expected)

    def test_a1_third_installed_release_guard(self):
        change = mutated(owner.qualified_state, 'len(installed) <= 2', 'True')
        with patch.object(owner, 'qualified_state', change):
            self.detected_by(focused.ShapeTest('test_wrong_sets_keep_refusing'))

    def test_a2_running_member_need_not_be_first(self):
        change = mutated(owner.qualified_state, "rows = state['rpm']['deployments']",
                         "rows = state['rpm']['deployments']; require(rows[0] is booted, 'Running row is not first')")
        with model.driver() as d, patch.object(owner, 'qualified_state', change):
            self.ledger_detects(d, replace(starts()[2], running='S'), ('title', 'full'))

    def test_a3_reorder_requires_sync(self):
        real = pathlib.Path.read_text
        def no_sync(path, *args, **kwargs):
            source = real(path, *args, **kwargs)
            if path == model.ROOT / 'os/release/start-next.sh':
                self.assertEqual(source.count("subprocess.run(['sync'], check=True)"), 1)
                return source.replace("subprocess.run(['sync'], check=True)", 'pass')
            return source
        with patch.object(pathlib.Path, 'read_text', no_sync):
            self.detected_by(focused.ScriptTest('test_reads_immediately_before_one_set_default_syncs_and_checks_the_result'))

    def test_a4_previous_names_the_older_release(self):
        change = mutated(owner.Tools.previous, "older = min(shape['ares']", "older = max(shape['ares']")
        with model.driver() as d, patch.object(owner.Tools, 'previous', change):
            self.ledger_detects(d, starts()[2], ('previous', 'full'))

    def test_a5_applied_on_this_boot_is_not_confirmed(self):
        change = mutated(owner.Tools.outcome, "return 'applied' if same else 'done'", "return 'done'")
        with model.driver() as d:
            s = model.RevertTest().path(d, replace(starts()[2], running='S'), [('keep-stock', 'full')])
            with patch.object(owner.Tools, 'outcome', change):
                self.ledger_detects(d, s, ('title', 'full'))

    def test_a6_repair_note_blocks_settings_inheritance(self):
        change = mutated(owner.Tools.may_stage, 'not self.repair_note(booted)', 'True')
        with model.driver() as d:
            s = model.RevertTest().path(d, starts()[3], [
                ('begin', 'us'), ('proof', 'full'), ('finish', 'console'),
                ('restart', 'S'), ('abandon', 'full'), ('restart', '27')])
            with patch.object(owner.Tools, 'may_stage', change):
                self.ledger_detects(d, s, ('update', 'full'))

    def test_a7_abandon_elsewhere_keeps_a_bound_repair_note(self):
        change = mutated(owner.Tools.layout,
            'notes.append(note)', 'None')
        with model.driver() as d:
            s = model.RevertTest().path(d, starts()[2], [
                ('begin', 'us'), ('proof', 'full'), ('finish', 'console'), ('restart', 'S')])
            with patch.object(owner.Tools, 'layout', change):
                self.ledger_detects(d, s, ('abandon', 'full'))

    def test_a7_revert_preserves_the_interrupted_finish_authority(self):
        change = mutated(owner.Tools.layout, "if value.get('finishing') and value['proof']:", 'if False:')
        with model.driver() as d:
            s = model.RevertTest().path(d, starts()[2], [
                ('begin', 'us'), ('proof', 'full'), ('finish', 'console')])
            with patch.object(owner.Tools, 'layout', change):
                self.ledger_detects(d, s, ('revert', 'full'), 'finish authority lost')

    def test_a8_title_has_the_identity_based_menu(self):
        real = owner.Tools.standing
        with patch.object(owner.Tools, 'standing', lambda *a: real(*a)[:1]):
            self.detected_by(focused.ShapeTest('test_the_names_are_roles_with_a_short_digest_and_the_row_map_follows_the_boot_entries'))

    def test_a9_unknown_schema_refuses(self):
        change = mutated(owner.journalled, "value['schema'] == JOURNAL", 'True')
        with patch.object(owner, 'journalled', change):
            self.detected_by(focused.JournalTest('test_any_other_list_stops_and_an_unknown_schema_refuses'))

    def test_a10_keep_stock_checks_updaters(self):
        change = mutated(owner.Tools.recover, 'paused_state(self.host, self.pause)', 'None')
        with patch.object(owner.Tools, 'recover', change):
            self.detected_by(focused.ShapeTest('test_stock_updaters_warn_in_title_stop_keep_stock_and_never_block_the_way_off'))

    def test_a11_one_command_spelling(self):
        with patch.object(owner, 'typed', lambda *words: 'at ' + ' '.join(words)):
            self.detected_by(focused.ShapeTest('test_one_helper_spells_every_command_as_commands_json_does'))

    # One word per meaning (briefs/22c-forward-command.md): the two new invariants.
    def test_one_word_update_never_selects_an_installed_system(self):
        returned = replace(starts()[2], rows=('13', '27', 'S'), running='13')  # after previous and a restart
        # 1. The reorder put back where the tools' release is installed.
        installed = mutated(owner.Tools.update, 'raise Stop(RELEASE_INSTALLED)',
                            "return self.select('update', before, shape, settled, installed, 'Newest AresOS starts next ' + target)")
        # 2. The reorder put back where update may not stage (stock runs, or the running AresOS is not first).
        elsewhere = mutated(owner.Tools.update, '    self.may_stage(before, shape, settled)\n    stored_login(target)',
                            "    if booted is shape['stock'] or rows[0] is not booted:\n"
                            "        return self.select('update', before, shape, settled, newest(shape), 'Newest installed AresOS starts next')\n"
                            '    self.may_stage(before, shape, settled)\n    stored_login(target)')
        for change, state in ((installed, returned), (elsewhere, replace(starts()[3], rows=('S', '27', '13'), running='S'))):
            with self.subTest(state=state.rows + (state.bundle, state.running)), patch.object(owner.Tools, 'update', change):
                with model.driver() as d:
                    # The driver's own judgment of the fake's state, before any comparison with the ledger.
                    self.ledger_detects(d, state, ('update', 'full'), 'update selected an installed system')
                self.detected_by(focused.DestinationTest('test_update_never_selects_an_installed_system'))

    def test_one_word_forward_never_stages_or_changes_the_set_of_deployments(self):
        real = owner.Tools.forward
        def stages(tools):
            # The old update under the new word: it stages where the bundle's release is not installed.
            state, shape, settled = tools.survey()
            if tools.tools_release(shape) is None and state['rpm']['deployments'][0] is shape['booted'] is not shape['stock']:
                return tools.update()
            return real(tools)
        def removes(tools):
            lines = real(tools)
            tools.host.mutate('rpm-ostree', 'cleanup', '--pending')  # deletes every unpinned row before the running one
            return lines
        with model.driver() as d:
            with patch.object(owner.Tools, 'forward', stages):
                self.ledger_detects(d, starts()[3], ('forward', 'full'), 'forward staged or changed the set of deployments')
            with patch.object(owner.Tools, 'forward', removes):
                self.ledger_detects(d, replace(starts()[2], rows=('13', '27', 'S'), running='13'), ('forward', 'full'),
                                    'forward staged or changed the set of deployments')
        with patch.object(owner.Tools, 'forward', removes):
            self.detected_by(focused.DestinationTest('test_forward_selects_the_newest_installed_aresos_from_anywhere_and_never_stages'))

    def test_one_word_each_installed_system_is_one_command_away(self):
        """B2's destination invariant at its original strength: without forward's reorder from
        the older AresOS that runs and starts next, R27 is no command away with a bundle for R28."""
        def old_rule(tools):
            # update's old condition for a reorder, under the new word: not from a running AresOS that is first.
            state, shape, settled = tools.survey()
            if tools.tools_release(shape) is None and state['rpm']['deployments'][0] is shape['booted'] is not shape['stock']:
                raise owner.Stop('Forward selects only where update may not stage')
            return owner.Tools.select(tools, 'forward', state, shape, settled, owner.newest(shape), 'Newest installed AresOS starts next')
        state = replace(starts()[3], rows=('13', '27', 'S'), running='13')
        self.assertEqual(dict(model.destinations(state)), {'27': ('forward', 'full'), 'S': ('rollback', 'full')})
        with model.driver() as d, patch.object(owner.Tools, 'forward', old_rule):
            self.ledger_detects(d, state, ('forward', 'full'), 'accept/refuse')
        # The same narrowing in the reference rules themselves fails the invariant, not only the comparison.
        def narrowed(s, event):
            if event[0] == 'forward' and s.bundle not in s.rows and s.rows[0] == s.running != 'S':
                return ledger.Result(s, stop='update')
            return transition(s, event)
        ledger.invariants(state)
        with patch.object(ledger, 'transition', narrowed), self.assertRaisesRegex(AssertionError, 'destination refuses'):
            ledger.invariants(state)

    def test_review2_1_only_a_refusal_before_the_change_closes_the_intent(self):
        branch = 'if failure.code != REFUSED_BEFORE_CHANGE:'
        # Never closing: the refused intent stays open and matches neither list (the review's dead end).
        with patch.object(owner.Tools, 'start_next', mutated(owner.Tools.start_next, branch, 'if True:')):
            self.detected_by(focused.DestinationTest('test_outside_reorder_before_the_script_closes_the_intent_and_every_way_back_works'),
                             'the refused intent is still open')
        # Closing on every failure: a journal whose change may be on disk would be discarded.
        with patch.object(owner.Tools, 'start_next', mutated(owner.Tools.start_next, branch, 'if False:')):
            self.detected_by(focused.DestinationTest('test_a_script_failure_that_may_follow_the_change_keeps_the_intent_open'),
                             'refused-before-change')
        # The script's side: a refusal that exits like any other failure cannot be told apart.
        real = pathlib.Path.read_text
        def generic_exit(path, *args, **kwargs):
            source = real(path, *args, **kwargs)
            if path.name == 'start-next.sh':  # the tools render their bundle's copy
                self.assertEqual(source.count('sys.exit(3)'), 1)
                return source.replace('sys.exit(3)', 'sys.exit(1)')
            return source
        with patch.object(pathlib.Path, 'read_text', generic_exit):
            self.detected_by(focused.DestinationTest('test_outside_reorder_before_the_script_closes_the_intent_and_every_way_back_works'),
                             'the refused intent is still open')

    def test_review2_2_restoration_is_an_exclusive_phase(self):
        change = mutated(owner.Tools.layout, "require('restoring' not in value,", 'require(True,')
        with model.driver() as d:
            s = model.RevertTest().path(d, starts()[2], model.RevertTest.EXCLUSIVE)
            with patch.object(owner.Tools, 'layout', change):
                self.ledger_detects(d, s, ('finish', 'full'), 'accept/refuse')
        with patch.object(owner.Tools, 'layout', change):
            self.detected_by(focused.LayoutTest('test_restoration_is_exclusive_and_finish_from_the_original_login_names_abandon'),
                             'Stop not raised')

    def test_b3_cleanup_must_remove_unpinned_preceding_rows(self):
        real = model.Host.mutate
        def only_stage(host, *command, **kwargs):
            if command == ('rpm-ostree', 'cleanup', '--pending'):
                host.write_list([r for r in host.state['rpm']['deployments'] if not r.get('staged')])
                return
            return real(host, *command, **kwargs)
        with patch.object(model.Host, 'mutate', only_stage):
            self.detected_by(model.FakeRulesTest('test_list_write_drops_nonfirst_stage_and_cleanup_removes_unpinned_preceding_rows'))

    def test_b3_a_list_write_must_drop_a_nonfirst_stage(self):
        def keeps_stage(host, rows):
            host.state = model.status(rows)
            host.links = 1 - host.links
        with patch.object(model.Host, 'write_list', keeps_stage):
            self.detected_by(model.FakeRulesTest('test_list_write_drops_nonfirst_stage_and_cleanup_removes_unpinned_preceding_rows'))

    def test_b3_queued_flag_follows_order(self):
        real = model.status
        def never_queued(rows):
            result = real(rows)
            result['bootc']['status']['rollbackQueued'] = False
            return result
        with patch('ways_back_host.status', never_queued):
            self.detected_by(model.CaptureTest('test_every_probe_capture_matches_the_model_host'))


if __name__ == '__main__':
    unittest.main()
