# Review 1 — package and security

Reviewer: fresh Codex context, independent of the builder. Model: GPT-6. Date: 2026-11-19. Reviewed PR #111, code head `a3b42851`, plus report commit `e8c707bf`.

Read: AGENTS.md; the complete brief and READY recheck; REPORT.md; PROGRESS.md parts 1–7 and the Mail review25 follow-up; both mutation receipts; docs/REVIEW.md; DESIGN.md and the relevant CONTROL.md safety/recovery sections; the control diff and affected code. Board #352 governs this review.

Ran with bytecode disabled, TMPDIR and all scratch under `.work/xreview-1/`, one worker:

- **201 base tests passed**, including oracle, storage, restore, results, journal, S2 and CI selection.
- **56 Mail tests:** 53 passed; three methods encountered seven export-fixture errors.
- **All 16 sweep unit tests:** 15 passed; one export-fixture error. Startup coverage included **47 discovered points, 100 single/persistent cases and 137 cleanup pairs**.
- **13 CLI/idle tests:** four passed; nine socket-binding EPERM errors.
- The **eight export-fixture errors and nine EPERM errors reproduced on the merge base**, with identical affected tests. These are environment limitations, not findings.
- **27 mutation patches:** 20 distinct passing baselines and **38 intended assertion kills**. The additional combined review24/review25 barrier baseline passed; its mutant failed all seven assertions.
- **12,284 focused recovery alterations passed, `slipped=0`**. Generated-artifact checking passed.

Exact patches, logs and receipts (`.work/xreview-1/mutations/receipts.json`, the reviewer's scratch, not committed) remain in scratch. Hosted proof 44395635207 and the six first-round CI successes are accepted as supplied; nothing was dispatched or rerun. CI round 2 remains the lead’s gate.

| Mutation | Test catching it in my run | Result |
|---|---|---|
| m01: retain latch after complete first-fence rollback | `ReviewRegressions.test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13`; `WriteLatchSweep302.test_latch_phases_cleanup_pairs_and_restart` | Both killed |
| m02: remove request barrier | `Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request` | Six failures: actual DATA became 1 instead of 0 |
| m03: clear latch after any append failure | `Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`; `RestoreBatches.test_confirm_whose_marker_stays_after_a_failed_sync_keeps_the_lock_until_a_restart` | Both killed |
| m04: return old cause on later latched request | Store phase test above; `RestoreBatches.test_confirm_whose_last_marker_sync_fails_keeps_the_lock_until_a_restart`; `WriteLatchSweep302.test_latch_cases_use_the_same_status_checker_in_every_phase` | All killed |
| m05/m06: omit advice / replace first error | Store phase test; `ResponseSchemas23.test_first_storage_error_notes_and_restart_advice_survive_bounding` | Both patches killed by both tests |
| m07/m08: infer latch from any fault / retain history after restart | `WriteLatch302.test_fault_count_read_only_and_admission_failures_are_not_latch_evidence`; `test_journal_phases_and_actual_cleanup_determine_the_latch`; latch retry/restart sweep | Both killed |
| m09: bypass staged-restore startup branch | `OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm` | Killed before automatic confirm |
| m10/m11: unlock without replay / mark without applying | `RestoreBatches.test_startup_finishes_staged_final_confirm_without_another_confirmation`; startup proof above | Both patches killed by both tests |
| m12/m13: intermediate treated as final / obligation retained | `RestoreBatches.test_startup_finishes_only_the_staged_intermediate_batch`; `StartupObligations.test_driver_checks_before_requests_consumes_once_and_second_restart_has_no_old_obligation` | Both killed |
| m14: ignore applied tail | `AppliedHistory.test_decoder_applied_tail_matrix_and_missing_projection_row`; `OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits` | Both killed |
| m15/m16: promote every prepared event / ignore head hash | Decoder matrix above; m15 also the latch status sweep | Both killed |
| m17/m25/m18: misattribute producing call / accept unscripted cancel or ack | Applied-tail producing-call sweep; `AppliedHistory.test_applied_cancellation_and_acknowledgement_still_require_exact_script_identity` | All killed |
| m19: permit remote command using applied context | `AppliedHistory.test_applied_context_cannot_authorize_a_remote_command_before_its_marker` | Killed; existing R2 controls passed |
| m20–m24/m26: copy lock or remove decoded-lock terms | `StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | All six killed |
| m27: ignore latch-refused live recheck | `WriteLatch302.test_live_sent_copy_recheck_refused_by_latch_without_a_fresh_fault_is_unchecked` | Killed |

These results match the builder’s final receipts. In particular, m15’s former sweep survivor now fails the returned-row assertion, and m17 fails **“Outer producing call must include its applied event.”** I did not count the builder’s invalid m03 auxiliary sweep as evidence.

No BLOCKER, SHOULD-FIX or NIT findings.

The [latch exception](../../control/aresos_control/storage.py#L733) requires actual truncate-and-fsync completion before indexing or SQLite staging. The [request gate](../../control/aresos_control/engine.py#L776) and later writable checks stop caught failures from reaching effects. The tests demonstrate zero effects in the failed request, then exactly one send on a healthy explicit request. Later-phase failures retain the latch, original first errors and restart advice.

The [startup obligation](../../control/owner_state_oracle/driver.py#L139) checks replay before views or another confirm can repair it. Marker, applied head, effects, generation and lock are independently checked. [Applied history](../../control/owner_state_oracle/records.py#L239) preserves saved rows while [pre-command snapshots](../../control/owner_state_oracle/driver.py#L163) retain marked authority.

The [Mail review25 change](../../control/mail_tests/test_review_fixes_25.py#L52) pins refusal before dispatch, retains the queued warning, and preserves the old location-page, 350-copy and exactly-one-MOVE assertions on the healthy next request. It does not weaken their protection.

Format 3 and strict exact-delta checking remain unchanged. The pin is byte-identical between `b2d50247` and `a3b42851`, SHA-256 `1b21f564533df6cdc1c99a5c4068d87538047f54a5243b6d0ed930d378ca2295`. No post-proof change affects proof-list inputs: review25 is outside the owner/alteration selections. I did not redo the separate key classification.

The read-only comparison with main confirms no intervening changes under `control/`, `.github/workflows/` or `reviews/19b-owner-state/`; this package needs no control integration change from main.

The branch and pre-existing review file are untouched. All mutated scratch sources were restored. No file over 500 MB remains under `.work/`.

SAFE