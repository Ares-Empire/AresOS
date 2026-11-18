"""Step 5 probes; run from the repo root with Python, optionally naming probe IDs.

Only disposable tracked-source exports are mutated. Exact patches, commands and
unabridged logs stay in .work/302/step5; receipts contain repo-relative paths.
OWNER_MUTATION_ROUND=part4 keeps rerun logs, exports and receipts separate.
Each test runs unchanged first, then with one mutation, then source is restored.
No pin, installed service or FilePolicy change is involved.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ROUND = os.environ.get('OWNER_MUTATION_ROUND', 'step5')
WORK = ROOT / '.work/302' / ROUND
EXPORTS = ROOT / 'control/test-work/302-exports'
S = 'control/aresos_control/storage.py'
R = 'control/owner_state_oracle/records.py'
D = 'control/owner_state_oracle/driver.py'
M = 'control/owner_state_oracle/model.py'
P = 'control/owner_state_oracle/perturb.py'
O = 'test_owner_state_oracle.'
B = 'test_restore_batches.RestoreBatches.'
J = 'test_review22_storage.Journal22.'
W = 'test_owner_state_sweep.'
LATCH = W + 'WriteLatchSweep302.test_latch_phases_cleanup_pairs_and_restart'
STATUS = W + 'WriteLatchSweep302.test_latch_cases_use_the_same_status_checker_in_every_phase'
TAIL = W + 'OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits'
START = W + 'OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm'
HEAD = O + 'AppliedHistory.test_decoder_applied_tail_matrix_and_missing_projection_row'
LOCK = O + 'StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute'
PHASES = J + 'test_first_fence_fsync_rollback_and_later_phase_failures'
CASES = []


def case(number, label, file, before, after, *tests):
    CASES.append(dict(id=f'm{number:02}', patch=label, file=file, before=before,
                      after=after, tests=list(tests)))


case(1, 'Keep latch after proven first-fence rollback', S,
     '                self.write_failed = False\n            raise\n',
     '                self.write_failed = True\n            raise\n',
     ('mail', 'test_owner_state_regressions.ReviewRegressions.test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13'),
     ('mail', LATCH))
case(2, 'Disable both request barrier gates', 'control/aresos_control/results.py',
     '        if self.write_barrier is not None:\n            raise self.write_barrier\n',
     '        return\n',
     ('mail', 'test_review_fixes_24.Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request'))
case(3, 'Clear latch inside every failed append, including marker/cleanup failures', S,
     '            self.write_failed = True\n            rolled_back = False\n',
     '            self.write_failed = False\n            rolled_back = False\n',
     ('base', PHASES),
     ('base', B + 'test_confirm_whose_marker_stays_after_a_failed_sync_keeps_the_lock_until_a_restart'))
case(4, 'Replay old storage cause on later latched request', S,
     "            raise Refused('journal_incomplete', RESTART_ADVICE)\n",
     "            raise self.storage_cause or Refused('journal_incomplete', RESTART_ADVICE)\n",
     ('base', PHASES), ('base', B + 'test_confirm_whose_last_marker_sync_fails_keeps_the_lock_until_a_restart'),
     ('mail', STATUS))
case(5, 'Omit restart advice from first storage refusal', 'control/aresos_control/results.py',
     "        if (not result['ok'] and store.write_failed and\n",
     "        if (False and not result['ok'] and store.write_failed and\n",
     ('base', PHASES), ('base', 'test_review23_results.ResponseSchemas23.test_first_storage_error_notes_and_restart_advice_survive_bounding'))
case(6, 'Replace first storage error code with journal_incomplete', 'control/aresos_control/results.py',
     "'error': {'code': self.error.code, 'message': str(self.error)}}",
     "'error': {'code': 'journal_incomplete', 'message': str(self.error)}}",
     ('base', PHASES), ('base', 'test_review23_results.ResponseSchemas23.test_first_storage_error_notes_and_restart_advice_survive_bounding'))
case(7, 'Infer latch from any call fault, including read/admission faults', R,
     "    if not call.get('write_attempted'):\n",
     "    if call.get('faults'):\n        return True\n    if not call.get('write_attempted'):\n",
     ('base', O + 'WriteLatch302.test_fault_count_read_only_and_admission_failures_are_not_latch_evidence'),
     ('base', O + 'WriteLatch302.test_journal_phases_and_actual_cleanup_determine_the_latch'))
case(8, 'Keep journal phase history after restart', D,
     '        self.restart_index = len(self.oracle.script)\n        self.journal_scopes = {}\n',
     '        self.restart_index = len(self.oracle.script)\n', ('mail', LATCH))
case(9, 'Bypass special staged-restore startup branch', S,
     "            if prepared and prepared.get('space', {}).get('restoring'):\n",
     "            if False and prepared and prepared.get('space', {}).get('restoring'):\n", ('mail', START))
START_BODY = "                self._replay(prepared)\n                self.locked = bool(self.get('restore_pending'))\n"
case(10, 'Skip staged replay and clear service lock', S, START_BODY,
     '                self.locked = False\n',
     ('base', B + 'test_startup_finishes_staged_final_confirm_without_another_confirmation'), ('mail', START))
case(11, 'Append startup commit marker without applying staged event', S, START_BODY,
     "                self._append({'commit': prepared['seq'], 'hash': prepared['record']['hash']})\n"
     "                self.committed = prepared['seq']\n"
     "                self.locked = bool(self.get('restore_pending'))\n",
     ('base', B + 'test_startup_finishes_staged_final_confirm_without_another_confirmation'), ('mail', START))
case(12, 'Treat intermediate startup batch as final: clear pending, replace generation, unlock', S, START_BODY,
     "                self._replay(prepared)\n"
     "                with self.db:\n"
     "                    self.db.execute(\"DELETE FROM kv WHERE k='restore_pending'\")\n"
     "                    self.db.execute(\"UPDATE kv SET v=? WHERE k='generation'\", (canonical(uuid.uuid4().hex),))\n"
     "                self.locked = False\n",
     ('base', B + 'test_startup_finishes_only_the_staged_intermediate_batch'))
case(13, 'Retain startup obligation for another start', D,
     '        self.startup_obligation = None\n', '        pass\n',
     ('base', O + 'StartupObligations.test_driver_checks_before_requests_consumes_once_and_second_restart_has_no_old_obligation'))
VISIBLE = '    if not record.head or not record.fences:\n'
case(14, 'Ignore applied tail and project marked rows only', R, VISIBLE,
     '    return record.events\n' + VISIBLE, ('base', HEAD), ('mail', TAIL))
case(15, 'Promote every prepared event without application proof', R, VISIBLE,
     '    return [*record.events, *record.prepared]\n' + VISIBLE, ('base', HEAD), ('mail', STATUS))
case(16, 'Ignore applied head hash', R,
     "    if record.head != (seq, fence.get('hash')) or seq <= max(record.committed, default=0):\n",
     '    if record.head[0] != seq or seq <= max(record.committed, default=0):\n', ('base', HEAD))
case(17, 'End producing call at marked sequence, leaving applied event to later reads', D,
     "        oracle.script[self.call_index]['end_seq'] = staged_sequence(self.snapshot())\n",
     "        oracle.script[self.call_index]['end_seq'] = max(self.snapshot().committed, default=0)\n", ('mail', TAIL))
case(18, 'Accept unscripted cancellation and acknowledgement', M,
     '    def scripted_transition(self, event, suffix, identity=None):\n',
     "    def scripted_transition(self, event, suffix, identity=None):\n"
     "        if suffix in {'_operation_cancel', '_notice_ack'}:\n            return True\n",
     ('base', O + 'AppliedHistory.test_applied_cancellation_and_acknowledgement_still_require_exact_script_identity'))
case(19, 'Supply applied rows as pre-command permission', D,
     'return dict(committed_before=copy.deepcopy(history_rows(record.events)), created_before=created,\n'
     "                    call_start_seq=getattr(self.oracle, 'active_start_seq', 0), before_seq=max(record.committed, default=0),\n",
     'return dict(committed_before=copy.deepcopy(history_rows(visible_history(record))), created_before=created,\n'
     "                    call_start_seq=getattr(self.oracle, 'active_start_seq', 0), before_seq=applied_sequence(record),\n",
     ('base', O + 'AppliedHistory.test_applied_context_cannot_authorize_a_remote_command_before_its_marker'))
case(20, 'Copy input lock instead of recomputing', P,
     '    changed.locked = decoded_lock(changed.rows, fences, changed.committed, changed.head) or service_lock(changed)\n',
     '    changed.locked = record.locked\n', ('base', LOCK))
case(21, 'Drop pending-restore decoded-lock term', R,
     "    if rows.get('restore_pending'):\n        return True\n",
     "    if False and rows.get('restore_pending'):\n        return True\n", ('base', LOCK))
case(22, 'Drop missing-head decoded-lock term', R,
     '    if head is None:\n        return True\n',
     '    if head is None:\n        return False\n', ('base', LOCK))
case(23, 'Drop head-hash decoded-lock term', R,
     '    return behind(sequence, committed) or head_hash != expected_hash\n',
     '    return behind(sequence, committed)\n', ('base', LOCK))
case(24, 'Drop behind-marker decoded-lock term', R,
     '    return behind(sequence, committed) or head_hash != expected_hash\n',
     '    return head_hash != expected_hash\n', ('base', LOCK))
case(25, 'Use marked boundary for all call attribution, moving applied event to later capture', R,
     "    return max((f['seq'] for f in record.fences), default=max(\n"
     "        (e['seq'] for e in [*record.events, *record.prepared]), default=0))\n",
     '    return max(record.committed, default=0)\n', ('mail', TAIL))
case(26, 'Drop empty-journal decoded-lock control', R,
     '    if not fences:\n        return False\n',
     '', ('base', LOCK))
case(27, 'Ignore live recheck latch refusal without a fresh physical fault', M,
     "                        bool(self.script[-1].get('faults', {}).get('trace')) or\n"
     "                        latch_refusal_first(getattr(self, 'transaction_record', record), self.script[-1]))\n",
     "                        bool(self.script[-1].get('faults', {}).get('trace')))\n",
     ('base', O + 'WriteLatch302.test_live_sent_copy_recheck_refused_by_latch_without_a_fresh_fault_is_unchecked'))


def run_export():
    """Child process: the approved managed-settings fixture, with ordered paths."""
    import unittest
    from unittest.mock import patch
    tree, kind, test = Path(sys.argv[2]).resolve(), sys.argv[3], sys.argv[4]
    paths = [tree / 'control', tree / 'control' / ('tests' if kind == 'base' else 'mail_tests'),
             tree / 'control' / ('mail_tests' if kind == 'base' else 'tests')]
    sys.path[:0] = list(map(str, paths))
    os.environ.update(PYTHONPATH=os.pathsep.join(map(str, paths)), PYTHONDONTWRITEBYTECODE='1',
                      TMPDIR=str(WORK / 'tmp'))
    settings = json.loads((tree / 'control/settings/managed-settings.draft.json').read_text())
    with patch('aresos_control.boundary.Boundary.read', lambda self, path: settings):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(test))
    raise SystemExit(not result.wasSuccessful())


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'tmp').mkdir(exist_ok=True)
    source_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    selected = [c for c in CASES if not sys.argv[1:] or c['id'] in sys.argv[1:]]
    receipt_file = Path(__file__).with_name('mutations.json' if ROUND == 'step5' else f'mutations-{ROUND}.json')
    receipts = json.loads(receipt_file.read_text()) if receipt_file.exists() else []
    for probe in selected:
        target = EXPORTS / (ROUND + '-' + probe['id'])
        assert not any(p.startswith('.') for p in target.resolve().parts)
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        tracked = subprocess.check_output(['git', 'ls-files', '-z', 'control', 'reviews/19b-owner-state'], cwd=ROOT).decode().split('\0')
        for name in filter(None, tracked):
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        (target / '.work').mkdir()
        path = target / probe['file']
        source = path.read_text()
        assert source.count(probe['before']) == 1, probe['id']
        mutant = source.replace(probe['before'], probe['after'])
        patch_path = WORK / (probe['id'] + '.patch')
        patch_path.write_text(''.join(difflib.unified_diff(source.splitlines(True), mutant.splitlines(True),
                             fromfile='a/' + probe['file'], tofile='b/' + probe['file'])))
        results = []
        try:
            for index, (kind, test) in enumerate(probe['tests'], 1):
                argv = ['python3', '-B', str(Path(__file__).relative_to(ROOT)), '--run-export',
                        str(target.relative_to(ROOT)), kind, test]
                command = ' '.join(argv)
                outputs = {}
                for variant in ('baseline', 'mutant'):
                    path.write_text(source if variant == 'baseline' else mutant)
                    result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1200)
                    log = WORK / f"{probe['id']}-{index}-{variant}.log"
                    log.write_text(result.stdout)
                    lines = result.stdout.replace(str(ROOT) + '/', '').splitlines()
                    # Logs retain every subtest; receipts keep one exact example
                    # of each failure kind and the unittest totals.
                    failures = []
                    for prefix in ('FAIL:', 'ERROR:', 'AssertionError:', 'Ran ', 'FAILED', 'OK'):
                        example = next((s for s in lines if s.startswith(prefix)), None)
                        if example is not None:
                            failures.append(example)
                    outputs[variant] = dict(exit=result.returncode, log=str(log.relative_to(ROOT)), summary=failures)
                    if variant == 'baseline' and result.returncode:
                        raise RuntimeError('Baseline failed: ' + str(log.relative_to(ROOT)))
                killed = (outputs['mutant']['exit'] != 0 and
                          any(s.startswith('AssertionError:') for s in outputs['mutant']['summary']) and
                          not any(s.startswith('ERROR:') for s in outputs['mutant']['summary']))
                if outputs['mutant']['exit'] and not killed:
                    raise RuntimeError('Invalid mutation failure: ' + outputs['mutant']['log'])
                results.append(dict(test=test, command=command, result='killed' if killed else 'survived', **outputs))
                print(probe['id'], index, results[-1]['result'], test, flush=True)
        finally:
            path.write_text(source)
            assert path.read_text() == source
        receipt = dict(id=probe['id'], patch=probe['patch'], source_head=source_head,
                       file=probe['file'], patch_file=str(patch_path.relative_to(ROOT)),
                       patch_sha256=hashlib.sha256(patch_path.read_bytes()).hexdigest(),
                       restored=True, result='killed' if any(t['result'] == 'killed' for t in results) else 'survived',
                       tests=results)
        receipts = [r for r in receipts if r['id'] != probe['id']] + [receipt]
        receipt_file.write_text(json.dumps(sorted(receipts, key=lambda r: r['id']), indent=2) + '\n')
    print('Receipts:', receipt_file.relative_to(ROOT), flush=True)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--run-export']:
        run_export()
    else:
        main()
