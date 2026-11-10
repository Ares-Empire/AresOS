"""Replay recorded contracts/regressions and all sweep modes with single-field lies."""
from collections import Counter
import copy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from owner_state_oracle.perturb import check, freeze, state_vocabulary, mutations, evaluate, clone
import owner_state_cases
import test_owner_state_regressions as regressions
import test_review23_sweep as sweep_fixtures
from test_owner_state_sweep import exercise


class SystematicPerturbations(unittest.TestCase):
    def test_recorded_scenarios_have_no_silent_owner_state_change(self):
        recordings = []
        label = ['contracts']
        compare = Driver.compare
        reply = Driver.reply
        last_regression = {}
        def capture_reply(driver, result, *args, **kwargs):
            value = reply(driver, result, *args, **kwargs)
            if label[0].startswith('regression/'):
                last_regression[id(driver)] = (label[0], freeze(driver.oracle), copy.deepcopy(driver.snapshot()))
            return value
        def capture(driver, checker=None):
            # Freeze independently recorded inputs before evaluating the record.
            recordings.append((label[0] + '/' + str(len(recordings)), freeze(driver.oracle), copy.deepcopy(driver.snapshot())))
            return compare(driver, checker)
        with patch.object(Driver, 'compare', capture), patch.object(Driver, 'reply', capture_reply):
            owner_state_cases.run(Gaps(recording=True))
            for name in unittest.defaultTestLoader.getTestCaseNames(regressions.ReviewRegressions):
                label[0] = 'regression/' + name
                last_regression.clear()
                case = regressions.ReviewRegressions(name)
                case.setUp()
                fixture = SimpleNamespace(fixture=case, flow='named', action='mail_accounts', args={})
                driver = Driver(fixture)
                observed_drivers = [driver]
                construct = sweep_fixtures.Scenario.__init__
                def record_construct(scenario, *args, **kwargs):
                    construct(scenario, *args, **kwargs)
                    if name == 'test_review21_acknowledged_rename_expiry':
                        observed_drivers.append(Driver(scenario))
                request = Engine.request
                def observed(engine, envelope, *args, **kwargs):
                    current = next((item for item in observed_drivers if item.scenario.fixture.engine is engine), None)
                    if current is None:
                        return request(engine, envelope, *args, **kwargs)
                    current.scenario.action = envelope.get('action', envelope.get('method'))
                    current.scenario.args = envelope.get('arguments', {})
                    with current.observe():
                        result = request(engine, envelope, *args, **kwargs)
                    current.reply(result)
                    return result
                def diagnostic(test, gap, expected, actual):
                    registry = Gaps(recording=True)
                    checker = registry.checker(gap)
                    checker('assertion', expected, actual)
                    checker.finish()
                try:
                    with patch.object(Engine, 'request', observed), patch.object(sweep_fixtures.Scenario, '__init__', record_construct), patch.object(regressions.ReviewRegressions, 'known_gap', diagnostic):
                        getattr(case, name)()
                    self.assertTrue(last_regression, ('Named regression was not recorded', name))
                    recordings.extend(last_regression.values())
                finally:
                    case.doCleanups()
            from test_owner_state_sweep import OwnerScenario
            from storage_faults import OSWrites
            label[0] = 'discover-post-effect-boundaries'
            boundaries = {}
            for flow, command in (('send', 'DATA'), ('delete_permanent', 'EXPUNGE'),
                                  ('onboarding', 'DATA'), ('filing_move', 'MOVE')):
                scenario = OwnerScenario(flow)
                try:
                    driver, fault = Driver(scenario), OSWrites()
                    with driver.observe(fault), fault.wrap(scenario.fixture.engine.store):
                        result = scenario.call()
                    driver.reply(result)
                    accepted = next(e for e in driver.oracle.servers if e['command'] == command and e['accepted'])
                    boundaries[flow] = accepted['fault_point'] + 1
                    self.assertLessEqual(boundaries[flow], len(fault.points))
                finally:
                    scenario.close()
            for flow, number, mode, cleanup, phase in (
                    ('send', None, 'single', None, 'live'),
                    ('repair', None, 'single', None, 'live'),
                    ('delete_permanent', boundaries['delete_permanent'], 'single', None, 'live'),
                    ('onboarding', boundaries['onboarding'], 'persistent', None, 'live'),
                    ('filing_move', boundaries['filing_move'], 'single', None, 'crash')):
                label[0] = f'sweep/{flow}/{number}/{mode}/{cleanup}/{phase}'
                _, cleanups = exercise(flow, number, mode, cleanup, Gaps(recording=True), phase)
            # Discover an actual cleanup pair; don't invent a fault boundary.
            scenario = OwnerScenario('send')
            try:
                driver = Driver(scenario)
                fault = OSWrites(boundaries['send'])
                with driver.observe(fault), fault.wrap(scenario.fixture.engine.store):
                    result = scenario.call()
                driver.reply(result)
                cleanup = 1 if fault.cleanup_points else None
                self.assertIsNotNone(cleanup, 'Cleanup mode must really execute')
            finally:
                scenario.close()
            label[0] = 'sweep/send/cleanup-pair/crash'
            exercise('send', boundaries['send'], 'single', cleanup, Gaps(recording=True), 'crash')
        from test_owner_state_plants import run_plants_and_controls
        run_plants_and_controls(self)
        # Include both review reproductions with later acknowledgement, reads,
        # expiry/archive attempts in the same field-level alteration corpus.
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location('s2_regressions', Path(__file__).resolve().parents[1] / 'tests/test_owner_state_fixes_s2.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for kind in ('filing', 'rename'):
            for related, target, scan in ((False, True, True), (True, False, True), (True, True, True)):
                oracle, record, key = module.filing_case(kind, related, target, scan)
                recordings.append((f'check-regression/{kind}/{related}/{target}', freeze(oracle), record))
                if not related or not target:
                    for index, (action, replay, snapshot) in enumerate(module.filing_followups(copy.deepcopy(oracle), copy.deepcopy(record), key)):
                        recordings.append((f'check-regression/{kind}/{related}/{target}/{index}-{action}', freeze(replay), snapshot))
        from owner_state_plants import record as record_production
        flag_oracle, flag_record, flag_deltas = record_production('local_flag')
        self.assertFalse(flag_deltas, 'Healthy LOCAL_FLAG must be quiet before alterations')
        recordings.append(('local-flag/healthy', flag_oracle, flag_record))
        counts = Counter()
        statistics = Counter()
        states = state_vocabulary([record for _, _, record in recordings])
        shard = int(os.environ.get('OWNER_PERTURB_SHARD', '0'))
        shards = int(os.environ.get('OWNER_PERTURB_SHARDS', '1'))
        self.assertIn(shard, range(shards))
        recordings = [item for index, item in enumerate(recordings) if index % shards == shard]
        for scenario, oracle, record in recordings:
            checked = check(scenario, oracle, record, states, statistics=statistics)
            counts.update(checked)
            print(f'Owner perturbation scenario={scenario} total={sum(checked.values())} slipped=0', flush=True)
        self.assertTrue(all(counts[kind] for kind in ('boolean', 'state', 'row', 'sequence', 'effect', 'restore')))
        self.assertTrue(any(name.startswith('contracts/') for name, *_ in recordings))
        if shards == 1:
            self.assertEqual({name.split('/')[1] for name, *_ in recordings if name.startswith('regression/')},
                             set(unittest.defaultTestLoader.getTestCaseNames(regressions.ReviewRegressions)))
        print(f'Owner perturbations scenarios={len(recordings)} kinds={dict(sorted(counts.items()))} total={sum(counts.values())} slipped=0', flush=True)
        print(f'Owner validator alteration statistics={dict(sorted(statistics.items()))}', flush=True)
