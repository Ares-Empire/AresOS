"""The CI layout executes every module and every ledger bucket without loss."""
from pathlib import Path
import unittest
import ast

from ci.mail.tests import select_names, flow_partition, inherited_names
from owner_state_oracle.gaps import owned, BUCKETS, SUITE_BUCKETS


class MailSelections(unittest.TestCase):
    def test_suite_sweep_and_alterations_partition_all_modules(self):
        modules = {p.stem for p in (Path(__file__).resolve().parents[1] / 'mail_tests').glob('test*.py')}
        suite = [select_names('suite', modules, shard, 4) for shard in range(4)]
        sweep = select_names('sweep', modules)
        alterations = select_names('perturb', modules)
        executed = [name for part in suite + [sweep, alterations] for name in part]
        self.assertEqual(set(executed), modules)
        self.assertEqual(len(executed), len(modules))
        self.assertTrue(all(suite))
        self.assertEqual(select_names('all', modules), sorted(modules))

    def test_twelve_sweep_jobs_own_each_bucket_exactly_once(self):
        for bucket in range(BUCKETS):
            group = {'owner': str(bucket)}
            self.assertEqual([s for s in range(12) if owned(group, s, 12, 0, 1)], [bucket])
        self.assertTrue(all(owned({'owner': 'shared'}, s, 12, 0, 1) for s in range(12)))

    def test_bad_selection_or_shard_fails(self):
        for args in (('unknown', [], 0, 1), ('suite', [], -1, 4), ('suite', [], 4, 4), ('suite', [], 0, 0)):
            with self.assertRaises(ValueError):
                select_names(*args)

    def test_flow_groups_preserve_every_ledger_group_and_inherited_flow(self):
        source = Path(__file__).resolve().parents[1] / 'mail_tests/test_owner_state_sweep.py'
        assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(source.read_text()).body
                       if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {'FLOWS', 'EXTRA'}}
        flows = assignments['FLOWS'] + assignments['EXTRA']
        groups = [flow_partition(flows, group, 3, isolated=('onboarding',)) for group in range(3)]
        self.assertEqual(set().union(*map(set, groups)), set(flows))
        self.assertEqual(sum(map(len, groups)), len(flows))
        self.assertEqual(groups[2], ('onboarding',))
        for flow in flows:
            for bucket in range(SUITE_BUCKETS.get(flow, BUCKETS)):
                self.assertEqual(sum(flow in groups[group] and owned({'owner': str(bucket), 'suite': flow}, shard, count, 0, 1)
                    for group in range(3) for count in [24 if group == 2 else 12] for shard in range(count)), 1)
        for index, flow in enumerate(assignments['FLOWS']):
            self.assertEqual(sum(index % count == shard and 'test_review23_sweep' in inherited_names(
                ['test_review23_sweep', 'test_review24_io'], 'sweep', group)
                for group in range(3) for count in [24 if group == 2 else 12] for shard in range(count)), 1)
        self.assertTrue(all(any(index % 12 == shard for index in range(len(assignments['FLOWS'])))
                            for shard in range(12)))
        for group, count in ((-1, 2), (2, 2), (0, 0)):
            with self.assertRaises(ValueError):
                flow_partition(flows, group, count)
