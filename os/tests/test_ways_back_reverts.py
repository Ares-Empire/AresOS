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
from ways_back_ledger import starts, transition

owner = model.owner


def mutated(function, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    assert source.count(before) == 1, 'mutation no longer matches exactly once'
    namespace = {}
    exec(compile(source.replace(before, after), '<22c rule removed>', 'exec'), owner.__dict__, namespace)
    return namespace[function.__name__]


class RuleRevertsTest(unittest.TestCase):
    def detected_by(self, case):
        result = unittest.TestResult()
        case.run(result)
        self.assertEqual(result.errors, [], 'an unrelated exception is not a revert proof')
        self.assertTrue(result.failures, case.id() + ' did not detect the removed rule')

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
            "notes.append(dict(deployment_identity=value['deployment_identity'], old=value['old'], new=value['new']))", 'None')
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
