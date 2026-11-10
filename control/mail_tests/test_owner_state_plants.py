"""A validator must catch its own real production regression through comparison."""
from collections import Counter
import unittest
from unittest.mock import patch

from owner_state_oracle.model import Oracle
from owner_state_oracle.perturb import evaluate, STRUCTURAL
import owner_state_oracle.context as context
import owner_state_oracle.model as model
from owner_state_plants import PLANTS, FIELD_PLANTS, record


VALIDATORS = {
    'script_differences': ('wrong-sent-destination', 'R2.APPEND', lambda: patch.object(context, 'script_differences', return_value=[])),
    'stage_claims': ('missing-deleted-store', 'unjustified-stage', lambda: patch.object(Oracle, 'stage_claims', return_value=None)),
    'completion_errors': ('missing-sent-copy', 'false-completion', lambda: patch.object(Oracle, 'completion_errors', return_value=set())),
    'payload_claims': ('narrow-payload', 'unapproved-payload', lambda: patch.object(Oracle, 'payload_claims', return_value=None)),
    'filing_claims': ('false-rename-count', 'unapproved-filing-context', lambda: patch.object(Oracle, 'filing_claims', lambda self, key, row, event: row)),
    'transition': ('false-transition', 'unsupported-resolution', lambda: patch.object(Oracle, 'transition', lambda self, record, event, key, old, row: row)),
    'local.errors': ('false-local-flag', 'R2.LOCAL_FLAG', lambda: patch.object(model, 'local_errors', return_value=[])),
}


def require_plant(name, oracle, decoded, kind, validator):
    proofs = {}
    expected, differences = evaluate(oracle, decoded, proofs)
    own = {(view, fact) for view, fact in differences if fact.kind == kind and fact in proofs.get(validator, set())}
    assert own, ('Validator missed production plant', name, kind, sorted(differences))
    return expected, own


def run_plants_and_controls(test):
    recordings = {}
    for name, (flow, patches) in PLANTS.items():
        oracle, decoded, deltas = record(flow, patches)
        # Driver.compare, including every view, is unmodified. This assertion
        # cannot be satisfied by the alteration helper's own integrity checks.
        test.assertTrue(deltas, ('Production plant escaped Driver.compare', name))
        _, differences = evaluate(oracle, decoded)
        test.assertTrue(any(f.kind not in STRUCTURAL for _, f in differences), name)
        if name == 'missing-repair-parent-result':
            test.assertTrue(any(f.kind == 'missing-operation-result' for _, f in differences), name)
        recordings[name] = oracle, decoded
    test.assertEqual(set(FIELD_PLANTS.values()) - recordings.keys(), set())
    print(f'Owner real production field controls={len(FIELD_PLANTS)} caught through Driver.compare', flush=True)
    for validator, (name, kind, broken) in VALIDATORS.items():
        oracle, decoded = recordings[name]
        expected, own = require_plant(name, oracle, decoded, kind, validator)
        with broken():
            with test.assertRaisesRegex(AssertionError, 'Validator missed production plant'):
                require_plant(name, oracle, decoded, kind, validator)
        print(f'Owner validator={validator} production_plants=1 own_catches={len(own)} broken_rejected=1 expected_facts={len(expected)}', flush=True)


class ProductionPlants(unittest.TestCase):
    def test_real_production_plants_and_individual_broken_validators(self):
        run_plants_and_controls(self)
