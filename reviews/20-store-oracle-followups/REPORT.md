# Report: brief 302, 20-store-oracle-followups

Final report for the whole package: draft PR [#111](https://github.com/Ares-Empire/AresOS/pull/111), branch
`pkg/302-store-oracle`, code head `a3b42851`, brief [20-store-oracle-followups](../../briefs/20-store-oracle-followups.md),
details and logs in [PROGRESS.md](PROGRESS.md). Sources: **P1–P7** = PROGRESS "Build part N"; **PF** = its "Fix after the
proof (Mail review25)"; **MJ** = [mutations.json](mutations.json); **M4** = [mutations-part4.json](mutations-part4.json); **NK** =
[new-key-classification.json](new-key-classification.json); **CC** = [CLASSIFICATION-CHECK.md](CLASSIFICATION-CHECK.md);
**GH** = `gh run view`/`gh api`, 2026-11-19. Where PROGRESS parts
disagree, the later part wins (part 4's "53 fresh lists" became 52 from part 5; part 3's m15/m17 survivors died in part 4).

## Done

**Item 1, the write latch and the request barrier:** `b64eb8f4` (P1); oracle follow-ups `13839137`, `1546da20` (P4).
- `_append` reports a rollback only once truncate and fsync both returned; only `Store.write`'s own first fence append
  then clears the latch, so the next explicit request needs no restart. Later-phase or cleanup failures keep it.
- A request-local barrier, set before pending collection and the deferred-notice flush and checked at `_admitted_request`'s
  start and in `ensure_writable`, gives the failed request (even a caught flush failure) zero app effects; its notice stays queued.
- Later calls refused by a surviving latch get `journal_incomplete`. The first failed request keeps its code, cause and
  notes, plus this advice once, after the first-error choice and before bounding: "A storage write did not finish.
  Fix the storage problem, then ask the owner to restart the AresOS tool service. Check the recorded request or
  operation after restart before trying another change." Tools never restart `aresos-toold.service`.
- Oracle: a raw journal trace (fence/marker write, sync, cleanup outcome) feeds one latch rule for status and
  request-state checks, never `Store.write_failed`, the returned error or a fault count; restart ends its history.
  G22-latch is an ordinary passing assertion. `13839137` applies the rule to a live Sent-copy recheck refused by the
  latch (M07/C01, the eight sample keys in NK); `1546da20` pins the outer call range and the status rows.

**Item 2, startup finishes a staged final confirm:** `6f12f561` (P2); base-only mock fixtures `d425882e`. No Store
change. `Driver.restarted` saves an immutable obligation from the full staged restore event, its plan and confirm
precondition. Right after binding, before any view, flush or confirm, a named `startup-replay` proof requires the
matching marker, a valid applied head and the exact effects; for a final batch also its generation, cleared
`restore_pending` and an unlocked service (an intermediate one keeps its lock and generation). Used once. RECHECK-1's two nits are in.

**Item 3, rows left at H:** `efa70045` (P2). The model is fixed; the store and the owner's replies don't change (board
#352). `records.visible_history` = marked events plus a validated applied tail (full staged event matching the last
hash-checked fence and the SQLite head, ahead of the last marker); `committed` stays exact. Rows, lifecycle, notices,
catalogues and the alteration recompute use it under the same identity/effect/transition gates. Call ranges use the
staged sequence, local reads the applied one, app-work permission the marked one. Documented in `control/README.md` and `FORMAT.md`.

## Capture, re-pin, proof

- **Capture 44352598226** on `e52ae87b` (P5): rejected; 60 jobs failed, 1 passed. Besides the strict old-pin failure,
  22 sweep jobs had 214 `Cannot operate on a closed database` errors (`Driver.restarted` queried the closed engine in
  `restart_index`/`restart_tail`); all 12 alteration shards failed corpus construction (`3 not greater than 3`, from
  hardcoded local offsets) with no `slipped=` line.
- **Harness fixes `6a818646`** (P6): a read-only fallback only for the closed handle; boundary discovery instead of
  numeric corpus offsets; `test_owner_state_capture.py` (3 tests) reproduces both. The lead authorized one replacement.
- **Capture 44375098965** (P7): 48 failures, each only the strict old-pin comparison (1 failure / 0 errors); ledger
  and all 12 alteration shards pass: 114 partitions, 2,096,041 candidates, `slipped=0`.
- **Re-pin `b2d50247`** (P7). Old pin, reproduced byte for byte from proof 43972005458's 53 lists: 2,576,083 keys /
  1,930 groups / 892,234 bytes, SHA-256 `8b27b1161505ac19eeaa41a6f1a69c95886de5da338249801963a96a083b74b1`. New pin from
  the capture's 52 lists (the passing G22-latch regression writes none): 2,420,003 keys / 1,860 groups / 860,653 bytes,
  SHA-256 `1b21f564533df6cdc1c99a5c4068d87538047f54a5243b6d0ed930d378ca2295`. Keys: 303,001 closed, 108,155 changed
  semantically, 8,159 alias-only, 146,921 new, 2,156,768 byte-identical. Most new keys (134,385) are in P7's "Items 1/3:
  recovery, filing, unchecked notices and counts"; all tables in P7 and [KNOWN-GAPS.md](../19b-owner-state/KNOWN-GAPS.md).
- **Expected shape** (P7): G22-latch/assertion closed by the passing healthy retry; the other 376 contract/G22/channel
  keys byte-identical; zero `startup-replay` failures; still zero `.restore-lock` keys. N7's 6,949 keys: 4,100 closed,
  928 changed, 365 alias-only, 1,556 identical, the false marked-versus-applied component gone. H's 63,379 keys became
  37,328. The 544 saved envelopes: 440 closed, 32 changed, 72 identical. All 544,801 `crash-locked` keys keep their
  semantics (528 alias-only). All 34 hosted flow-point counts unchanged.
- **Proof 44395635207** on `b2d50247`: 61/61 jobs green, its 52 fresh lists reproduce the new pin byte for byte, every
  alteration shard `slipped=0`. Source: the lead, who watched it; GH shows success, 61 of 61 jobs. PROGRESS records
  only the dispatch (P7) and that the proof stands (PF).
- **Mail fix `a3b42851`** (PF): Control Mail 44395716355 errored in `test_review_fixes_25` (`KeyError: 'data'`), as did
  44352678117, 44368668476, 44375244438. The test pinned the old latch: its read during the still-active fault now stops
  at the barrier (brief item 1.2). It now pins `storage_limit`, "Disk full" without restart advice, no `data`, the
  queued filing notice, then a new request without restart that reads the page (350 copies, one MOVE). The pin did
  not move: no product, oracle, workflow or selection file changed, and the oracle's runs don't select this module.

## Reviewer mutations

Part 3 at `5716bb2a` (MJ): 26 patches, 37 passing baselines, 35 assertion kills, 2 survivors. Part 4 at `1546da20`
(M4): 8 patches, 13 passing baselines, 13 kills. Final: all 27 patches killed on named assertions.

| Brief mutation | ID | Catching test | Result |
|---|---|---|---|
| Keep latch after rolled-back first fence | m01 | `test_owner_state_regressions.ReviewRegressions.test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13`; `test_owner_state_sweep.WriteLatchSweep302.test_latch_phases_cleanup_pairs_and_restart` | killed |
| Remove the request barrier | m02 | `test_review_fixes_24.Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request` | killed, all six variants (`1 != 0 : Failed flush must cause zero SMTP DATA`); PF rerun: 7 failures incl. review25 |
| Clear after any append failure | m03 | `test_review22_storage.Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`; `test_restore_batches.RestoreBatches.test_confirm_whose_marker_stays_after_a_failed_sync_keeps_the_lock_until_a_restart` | killed; its extra sweep run was invalid (`KeyError`), not counted |
| Raise old cause on later latched request | m04 | `Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`; `RestoreBatches.test_confirm_whose_last_marker_sync_fails_keeps_the_lock_until_a_restart`; `WriteLatchSweep302.test_latch_cases_use_the_same_status_checker_in_every_phase` | killed (P3 and P4) |
| Remove advice / first error → `journal_incomplete` | m05, m06 | `Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`; `test_review23_results.ResponseSchemas23.test_first_storage_error_notes_and_restart_advice_survive_bounding` | killed |
| Latch from any fault / kept after restart | m07, m08 | `test_owner_state_oracle.WriteLatch302.test_fault_count_read_only_and_admission_failures_are_not_latch_evidence`, `WriteLatch302.test_journal_phases_and_actual_cleanup_determine_the_latch`; m08: `WriteLatchSweep302.test_latch_phases_cleanup_pairs_and_restart` | killed (m07 in P3 and P4) |
| Bypass staged-restore startup branch | m09 | `test_owner_state_sweep.OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm` | killed at 26, 40, 73, both modes |
| Skip replay but unlock / marker without apply | m10, m11 | `RestoreBatches.test_startup_finishes_staged_final_confirm_without_another_confirmation`; the startup-proof test above | killed |
| Intermediate as final / obligation kept | m12, m13 | `RestoreBatches.test_startup_finishes_only_the_staged_intermediate_batch`; `test_owner_state_oracle.StartupObligations.test_driver_checks_before_requests_consumes_once_and_second_restart_has_no_old_obligation` | killed |
| Ignore the applied tail | m14 | `test_owner_state_oracle.AppliedHistory.test_decoder_applied_tail_matrix_and_missing_projection_row`; `OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits` | killed (P3 and P4) |
| Every prepared applied / ignore head hash | m15, m16 | the decoder matrix test above; m15 also `WriteLatchSweep302.test_latch_cases_use_the_same_status_checker_in_every_phase` | m16 killed; m15 survived that sweep in P3, killed in P4 (`Returned status rows must match applied history`) |
| Applied event to a later read / unscripted cancel or ack | m17, m25, m18 | `OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits` (m17, m25); `AppliedHistory.test_applied_cancellation_and_acknowledgement_still_require_exact_script_identity` (m18) | m17 survived in P3, killed in P4 (`Outer producing call must include its applied event`); m25, m18 killed |
| Applied context permits a remote command | m19 | `AppliedHistory.test_applied_context_cannot_authorize_a_remote_command_before_its_marker` (R2 controls pass) | killed |
| Copy the lock / drop a decoded-lock term | m20–m24, m26 | `StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | killed |
| (P4's new rule) ignore latch-refused live recheck | m27 | `WriteLatch302.test_live_sent_copy_recheck_refused_by_latch_without_a_fresh_fault_is_unchecked` | killed |

## Verified

- **Control CI on `a3b42851`, round 1** (attempt 1, GH), all six green: Repo privacy 44419011776, Control boundary
  44419011859, Control base 44419011760, Control Chrome qualification 44419011783, Control Mail 44419012014, Control
  Chrome 44419011791. **Round 2** (attempt 2 of the same runs): running; the lead records it.
- Last local runs (one worker, exports under `control/test-work/302-exports/`, logs in `.work/302/`). PF: Mail fixes
  22–25 and G22, 26 OK; base oracle/storage/restore/results/journal-closed, 169 OK; barrier removal FAILED (failures=7).
  P6: capture regressions 3 OK; base 174 OK; sweep units 16 OK; compact sample 1,444 keys identical to P4, seven clean
  traces byte-identical; restart flows' native matrix 686 phases, zero gaps; alteration shard 6/12, 183,894
  alterations, `slipped=0`. P4 after the main merge `947606b8`: base 187 OK, Mail 42 OK, `generate.py --check` OK.

## Not verified

Real recovery of the installed service (storage failure, then restarting `aresos-toold.service`); installed/root/channel
tests (CI ledger only); full Mail, sweep and alteration runs locally (hosted only); CI round 2; the reviews below. No game check applies.

## JUDGMENT-CALL

- **Board #352** (2026-11-18), owner: "Yes (recommended)": restart advice after an interrupted write; saved changes
  stay visible; after a fully undone first append the next explicit request works while the failed one still stops.
  Owner-visible: the advice and `journal_incomplete` on later latched calls; row replies at H are unchanged.
- **Board #353** (2026-11-18), owner: "One question (recommended)". That is Chrome's combined send/loss question (28b
  item 4c, [ALIGNMENT.md](../28-chrome-capability/ALIGNMENT.md)); nothing in this package builds on it.
- No other product decision. Reversible technical choices (P1, P2): rollback fact on the raised refusal, used only at
  the first fence; raw journal history on `Record` with an audited exclusion; applied history as a helper, not a new
  projection; the startup obligation on `Driver`; no journal or schema format change.

## PLAN-GAP

- Adjacent tests pinned the old latch: `test_journal_closed`, Mail `test_review_fixes_22` (P1) and `test_review_fixes_25`
  (PF; failing in Control Mail from 44352678117 on, seen only after the proof); updated, no product change. The hosted
  base container lacks the Mail helpers of the brief's local path; two mocks needed explicit inputs (`d425882e`, P2).
- Discovery finds 47 staged-final restore points in 26..73, not all; intermediate batches also fill a byte limit; `hold_facts` keeps marked
  rights until the marker; item 1's latch inputs must survive item 3's coherent re-encoding (P2).
- The sample missed a failed startup with a closed engine and the corpus kept local offsets although the brief asked
  for discovery (P5, P6; fixed in `6a818646`). The capture writes 52 lists, not 53 (P5, P7). The brief budgeted one
  capture; the lead approved the second.

## Known limits

- Native and hosted point counts differ (onboarding 2,570/2,610, send 875/879, restart 28/30 vs 32/34; P1, P6),
  unattributed; boundaries are discovered, never remapped.
- Accepted gaps stay pinned and visible (P7): N7's changed and identical residuals, the 32 changed and 72 identical saved
  envelopes, 16 new `qualification.mail_account_add` and 959 new history-proof keys; lifecycle/response gaps, not store fixes.
- **N8** in [KNOWN-GAPS.md](../19b-owner-state/KNOWN-GAPS.md) (CC's N1), notices left after a finished replay: 124,173 of the 146,921
  new keys, at 7,941 `crash-restart` case-phases in 24 flows. After a crash between staging and marking a call's last event,
  the restart finishes the event, but the store still shows "outcome unknown, inspect". A caution too many, not hidden
  harm; this package leaves start-up code untouched, item 3's staged ranges only removed the 12,517 wrong `lifecycle-proof` keys that hid it.
- **N9** in KNOWN-GAPS.md (CC's N3 and C3), reads refused while a notice stays queued: item 1.2's request barrier, set by
  every storage refusal in a request (`recorded_write`), refuses the read, and the reply has no page. 46,680 keys in 2,457
  case-phases (`filing_copy`, `filing_move`, `filing_rename`, `expiry`, `maintenance`; 7,140 of them new audit keys),
  1,056 of CC's N4 keys on top. While a latch survives and a notice is queued, every later request, reads included, is refused
  until the service restarts, with the restart advice and the passive pending section; before, such a read was
  answered with the error attached. Owner's decision: board #385, open.

## Open questions / left

One open owner question: board #385, whether N9's reach is wanted (Known limits). Left, in order: CI round 2 (the lead
records it); the fresh package/security cross-review; the independent classification check against the full historical
and fresh lists; then the lead's merge. After it, a `linux-tools` follow-up for N8 (CC, SHOULD-FIX 1): decide whether the
store drops the queued notice once the replay finishes its source (as it does for Chrome) or the model expects it, with
one re-pin. No file
over 500 MB under `.work/` (`.work/302/` holds about 534 MB of evidence, checked 2026-11-19).
