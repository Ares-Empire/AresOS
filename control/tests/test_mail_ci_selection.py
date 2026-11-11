"""The CI layout executes every module and every ledger bucket without loss."""
from pathlib import Path
import unittest
import ast

from ci.mail.tests import select_names, select_cases, flow_partition, OPTIONAL_CASES
from ci.base import select as base_select, OPTIONAL as BASE_OPTIONAL
from owner_state_oracle.gaps import owned, BUCKETS, SUITE_BUCKETS


class MailSelections(unittest.TestCase):
    def test_suite_sweep_and_alterations_partition_all_modules(self):
        modules = {p.stem for p in (Path(__file__).resolve().parents[1] / 'mail_tests').glob('test*.py')}
        suite = [select_names('suite', modules, shard, 4) for shard in range(4)]
        sweep = select_names('sweep', modules)
        alterations = select_names('perturb', modules)
        owner = select_names('owner', modules)
        executed = [name for part in suite + [sweep, alterations, owner] for name in part]
        self.assertEqual(set(executed), modules)
        self.assertEqual(len(executed), len(modules) + 1)
        self.assertEqual([m for m in modules if executed.count(m) == 2], ['test_owner_state_regressions'])
        self.assertEqual(set(sweep), {'test_review23_sweep', 'test_review24_io'})
        self.assertNotIn('test_owner_state_sweep', {n for part in suite for n in part})
        self.assertIn('test_owner_state_quiet', {n for part in suite for n in part})
        self.assertTrue(all(suite))
        self.assertEqual(select_names('all', modules), sorted(modules))

    def test_required_and_optional_cases_are_disjoint_and_complete(self):
        ids = OPTIONAL_CASES | {
            'test_owner_state_regressions.ReviewRegressions.test_review20_refused_reopen_then_archive',
            'test_owner_state_regressions.ReviewRegressions.test_review21_acknowledged_rename_expiry',
            'test_owner_state_regressions.ReviewRegressions.test_review21_paging_changed_warnings'}
        def suite(names):
            values = []
            for name in names:
                case = unittest.FunctionTestCase(lambda: None)
                case.id = lambda name=name: name
                values.append(case)
            return unittest.TestSuite(values)
        required = {c.id() for c in select_cases(suite(ids), 'suite')}
        optional = {c.id() for c in select_cases(suite(ids), 'owner')}
        self.assertEqual(optional, OPTIONAL_CASES)
        self.assertFalse(required & optional)
        self.assertEqual(required | optional, ids)
        base_ids = BASE_OPTIONAL | {'test_owner_state_oracle.OwnerOracle.test_expectation_imports_are_standard_library_only'}
        self.assertEqual({c.id() for c in base_select(suite(base_ids))}, base_ids - BASE_OPTIONAL)
        self.assertEqual({c.id() for c in base_select(suite(base_ids), True)}, BASE_OPTIONAL)

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
            self.assertEqual(sum(index % 4 == shard for shard in range(4)), 1)
        self.assertTrue(all(any(index % 4 == shard for index in range(len(assignments['FLOWS'])))
                            for shard in range(4)))
        for group, count in ((-1, 2), (2, 2), (0, 0)):
            with self.assertRaises(ValueError):
                flow_partition(flows, group, count)

    def test_measured_alteration_partition_owns_every_candidate_once(self):
        import json
        from ci.mail.tests import alteration_partition
        path = Path(__file__).resolve().parents[1] / 'mail_tests/owner_state_alteration_costs.json'
        costs = json.loads(path.read_text())
        names = [c['scenario'] for c in costs]
        assignments = alteration_partition(names, costs, 12)
        tasks = [task for shard in assignments for task in shard]
        self.assertEqual(len(tasks), len(set(tasks)))
        self.assertEqual(set(tasks), {(c['index'], p, c['parts']) for c in costs for p in range(c['parts'])})
        for c in costs:
            owned = [set(range(part, c['alterations'], parts))
                     for index, part, parts in tasks if index == c['index']]
            self.assertEqual(sum(map(len, owned)), c['alterations'])
            self.assertEqual(set().union(*owned), set(range(c['alterations'])))
        loads = [sum(costs[index]['seconds'] / parts for index, _, parts in shard) for shard in assignments]
        self.assertLess(max(loads), 1000)
        self.assertLess(max(loads) - min(loads), 10)
        with self.assertRaises(ValueError):
            alteration_partition(names[:-1], costs, 12)
