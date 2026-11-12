"""Production plants must add differences relative to the same healthy flow."""
import unittest
from unittest.mock import patch

from owner_state_oracle.model import Oracle
from owner_state_oracle.perturb import evaluate, STRUCTURAL, coherent_change, check
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


def new_views(baseline, planted):
    return {key for key, value in planted.items() if baseline.get(key) != value}


def semantic(oracle, decoded):
    return {(view, fact) for view, fact in evaluate(oracle, decoded)[1] if fact.kind not in STRUCTURAL}


def run_plants_and_controls(test):
    baselines, recordings = {}, {}
    for name, (flow, patches) in PLANTS.items():
        if flow not in baselines:
            baselines[flow] = record(flow)
        base_oracle, base_decoded, base_deltas = baselines[flow]
        oracle, decoded, deltas = record(flow, patches)
        # Both runs use the unmodified Driver.compare. Existing gaps cannot
        # satisfy either assertion, including gaps on the very same view.
        test.assertTrue(new_views(base_deltas, deltas), ('Production plant escaped Driver.compare', name))
        new = semantic(oracle, decoded) - semantic(base_oracle, base_decoded)
        test.assertTrue(new, ('No new semantic fact from production plant', name))
        if name == 'missing-repair-parent-result':
            test.assertTrue(any(f.kind == 'missing-operation-result' for _, f in new), name)
        recordings[name] = oracle, decoded, deltas
    test.assertEqual(set(FIELD_PLANTS.values()) - recordings.keys(), set())
    print(f'Owner real production field controls={len(FIELD_PLANTS)} caught through Driver.compare relative to baseline', flush=True)
    for validator, (name, kind, broken) in VALIDATORS.items():
        flow, patches = PLANTS[name]
        oracle, decoded, deltas = recordings[name]
        base_oracle, base_decoded, base_deltas = baselines[flow]
        intact = new_views(base_deltas, deltas)
        proofs = {}
        _, differences = evaluate(oracle, decoded, proofs)
        own = {f for _, f in differences - evaluate(base_oracle, base_decoded)[1]
               if f.kind == kind and f in proofs.get(validator, set())}
        test.assertTrue(own, ('Validator missed production plant', validator, name))
        with broken():
            # Baseline and plant both run through Driver.compare with exactly
            # one validator disabled. Provenance alone is never a control.
            broken_base = record(flow)
            broken_plant = record(flow, patches)
            remaining = new_views(broken_base[2], broken_plant[2])
            remaining_proofs = {}
            evaluate(broken_plant[0], broken_plant[1], remaining_proofs)
            redundant = sorted(v for v, facts in remaining_proofs.items() if v != validator and facts)
        if validator in {'local.errors', 'transition'}:
            test.assertFalse(remaining, ('The plant must slip when its only validator is removed', validator))
        else:
            test.assertTrue(remaining, ('Update documented validator redundancy', validator))
        print(f'Owner validator={validator} plant={name} intact_new_views={len(intact)} '
              f'disabled_new_views={len(remaining)} own_catches={len(own)} redundant_with={",".join(redundant) or "none"}', flush=True)


class ProductionPlants(unittest.TestCase):
    def test_real_production_plants_and_individual_broken_validators(self):
        run_plants_and_controls(self)

    def test_baseline_alone_cannot_satisfy_a_plant_assertion(self):
        for flow in sorted({flow for flow, _ in PLANTS.values()}):
            oracle, decoded, deltas = record(flow)
            second, second_record, second_deltas = record(flow)
            self.assertFalse(new_views(deltas, second_deltas), flow)
            self.assertFalse(semantic(second, second_record) - semantic(oracle, decoded), flow)

    def test_terminal_and_filing_result_removal_are_caught_only_by_the_named_validator(self):
        for flow, validator, prefix in (('send', 'stage_claims', 'op:'), ('filing_move', 'filing_claims', 'mail:filing:'),
                                        ('filing_copy', 'filing_claims', 'mail:filing:'), ('filing_rename', 'filing_claims', 'mail:rename:')):
            with self.subTest(flow=flow):
                oracle, decoded, _ = record(flow)
                event = next(e for e in reversed(decoded.events) if any(k.startswith(prefix) for k in e['set']))
                key = next(k for k in event['set'] if k.startswith(prefix))
                changes = [('row', (), None)]
                if validator == 'filing_claims':
                    changes.append(('state', ('state',), 'started'))
                for kind, path, replacement in changes:
                    with self.subTest(kind=kind):
                        replay, changed = coherent_change(oracle, decoded, key, path=path, replacement=replacement,
                                                          kind=kind, since=event['seq'])
                        candidate = [(f'coherent/{event["seq"]}/{key}/{"/".join(path)}', kind, (replay, changed))]
                        check(flow, oracle, decoded, candidates=candidate)
                        with VALIDATORS[validator][2]():
                            with self.assertRaisesRegex(AssertionError, 'Silent owner-state perturbation'):
                                check(flow, oracle, decoded, candidates=candidate)
                        print(f'Owner alteration control={flow} terminal-{kind} caught_only_by={validator}', flush=True)
