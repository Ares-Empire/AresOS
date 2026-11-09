"""Replay recorded contracts/regressions and all sweep modes with single-field lies."""
from collections import Counter
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from owner_state_oracle.perturb import check, freeze
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
            for flow, number, mode, cleanup, phase in (
                    ('send', None, 'single', None, 'live'),
                    ('repair', None, 'single', None, 'live'),
                    ('delete_permanent', 1, 'single', None, 'live'),
                    ('onboarding', 1, 'persistent', None, 'live'),
                    ('filing_move', 1, 'single', None, 'crash')):
                label[0] = f'sweep/{flow}/{number}/{mode}/{cleanup}/{phase}'
                _, cleanups = exercise(flow, number, mode, cleanup, Gaps(recording=True), phase)
            # Discover an actual cleanup pair; don't invent a fault boundary.
            from test_owner_state_sweep import OwnerScenario
            from storage_faults import OSWrites
            scenario = OwnerScenario('send')
            try:
                driver = Driver(scenario)
                fault = OSWrites(1)
                with driver.observe(fault), fault.wrap(scenario.fixture.engine.store):
                    result = scenario.call()
                driver.reply(result)
                cleanup = 1 if fault.cleanup_points else None
                self.assertIsNotNone(cleanup, 'Cleanup mode must really execute')
            finally:
                scenario.close()
            label[0] = 'sweep/send/cleanup-pair/crash'
            exercise('send', 1, 'single', cleanup, Gaps(recording=True), 'crash')
        counts = Counter()
        for scenario, oracle, record in recordings:
            checked = check(scenario, oracle, record)
            counts.update(checked)
            print(f'Owner perturbation scenario={scenario} total={sum(checked.values())} slipped=0', flush=True)
        self.assertTrue(all(counts[kind] for kind in ('boolean', 'state', 'row', 'sequence', 'effect', 'restore')))
        self.assertTrue(any(name.startswith('contracts/') for name, *_ in recordings))
        self.assertEqual({name.split('/')[1] for name, *_ in recordings if name.startswith('regression/')},
                         set(unittest.defaultTestLoader.getTestCaseNames(regressions.ReviewRegressions)))
        print(f'Owner perturbations scenarios={len(recordings)} kinds={dict(sorted(counts.items()))} total={sum(counts.values())} slipped=0', flush=True)
