# Part S — state review fixes

**Status: verification in progress; not acceptance evidence yet.** Draft PR [#34](https://github.com/Ares-Empire/AresOS/pull/34) targets `pkg/20-chrome`. Source head `cc1718fd`; runtime hash `298045eb35f2348a6d9f3982e7f1d1745846cf1b09600bec375b72fc82711ab5`.

## Done (read)

The existing committed-journal reader is the single Chrome authority for operation status, pending work, permissions and qualification. It writes no record, cache or projection file. `Store.chrome_state` shares that reader with the adapter and qualification service. Restore reconciles configuration, qualification, checks, operation outcomes, acknowledgements and tombstones in bounded batches while `restore_pending` stays set; only the last generation commit unlocks it.

Finished checks retire through bounded `control_expire` commits once their occurrences are acknowledged. Their immutable journal records keep deduplication, clean-interval and acknowledgement identities; an individual retired identity is read from that same journal if it returns. Nothing replays input. Lost queues commit stale non-resumable results independently of the queue; returning stale entries are acknowledged without another preparation. Uncertain activation occurrences still need their own acknowledgement.

| Item | Fix | Regression / removal mutation |
|---|---|---|
| S1 / D-1 | Reconcile Chrome rows before restore unlocks; qualification and owner permission reads use committed history. | `test_s1_restore_reconciles_revocation_readonly_and_qualification_offline`; `test_s1_readable_policy_rollback_cannot_hide_committed_qualification`; mutations **S1 restore**, **S1 qualification**. |
| S2 / D-2 | Every Chrome operation and pending read uses the committed journal plus live identity checks, including readable SQLite ahead of or behind it. | `test_s2_readable_rollback_pending_uses_committed_reservation`; `test_s2_failed_completion_marker_never_reports_uncommitted_done`; mutations **S2 status**, **S2 pending**. |
| S3 / D-3 | Restore preserves committed terminal outcomes and acknowledgements. Operation acknowledgements, like occurrence acknowledgements, are monotonic. | `test_s3_cancel_and_expiry_ack_survive_rollback_restore_archive_restart`; mutation **S3 terminal**. |
| S4 / D-4 | Retire completed checks and acknowledged occurrences, keeping historical receipts. Retirement also works under owner archive admission above the history quota. | `test_s4_more_than_512_completed_checks_leave_room_for_chrome_and_mail` (520 public reads, then new Mail intent admission); `test_s4_retirement_keeps_warning_ack_and_dedup_identity_in_history`; `test_s4_archive_retires_checks_even_above_the_shared_history_quota`; mutations **S4 retirement**, **S4 receipts**, **S4 archive admission**. |
| S5 / D-5 | A live open check is disclosed as a check, never materialized as an interruption occurrence. Startup defers Chrome interruption materialization until local replay; a recovered terminal result removes only uncommitted recovery proposals. | `test_s5_clean_stopped_submission_has_no_interruption_warning`; actual process-cut test below; mutations **S5 live check**, **S5 startup**. |
| S6 / D-6 | Read reconciles committed open checks against live session and queued steps. Lost steps become stale, non-resumable results; uncertain activations remain separately acknowledgeable. | `test_s6_lost_queue_resolves_native_check_and_preserves_uncertain_occurrence`; `test_s6_a_stale_step_cannot_be_prepared_if_the_same_queue_entry_returns`; mutations **S6 lost queue**, **S6 stale queue returns**. |
| S7 / D-7 | `chrome_drop` has cancellation semantics at request admission, recovery classification, index admission and cancellation-budget consumption. | `test_s7_drop_spends_cancel_reservation_at_history_and_physical_boundaries`; mutation **S7 admission**. |
| S8 / D-8 | Index-bound disclosure returns a bounded explicit unavailable warning, leaving public owner archive admission reachable, including after restart. | `test_s8_archive_remains_publicly_reachable_above_index_bound_and_after_restart`; mutation **S8 public archive**. |
| S9 / D-9 | Storage fallback keeps known Mail warning totals and routes, accounts for displacement in the compact page, and removes stale Chrome counts before adding current ones. | `test_s9_mail_only_and_mixed_fallback_keep_all_remaining_counts`; `test_s9_replacing_a_cached_chrome_page_does_not_double_count_its_hidden_rows`; mutation **S9 Mail continuation**. |
| S10 / D-10 | Shared ordering uses nanoseconds, including Chrome's synthesized fallback times. | `test_s10_mixed_notice_pages_use_nanosecond_chronology`; mutation **S10 chronology**. |
| S11 / D-11 | Scenario/receiver oracle decodes only committed journal records. Every public view is independently checked during active injection, after space returns without restart, and after restart. Actual process exits cover durable cuts separately. | `test_every_chrome_durable_writer_single_persistent_cleanup_pairs_restart_space_restored`; `test_chrome_storage_single_persistent_cleanup_pairs_crash_restart_space_restored`; `test_s11_actual_process_cuts_before_and_after_input_keep_every_committed_view`; oracle self-tests for R1, R2, R3 and round 27; mutation **S11 oracle**. |
| S12 / PKG-6, C-6, D-12 | Read dialogs, activation followups, stage details, error observations, operation status, evidence and historical Chrome audit summaries put page text inside `untrusted_content`; ordinary audit summaries are service-authored. | `test_s12_every_page_text_copy_is_inside_untrusted_content`; mutations **S12 dialog**, **S12 stages**. |

All `test_s*` names above are in `control/chrome_tests/test_state_fixes.py` except process cuts (`test_state_crashes.py`) and oracle self-tests (`test_state_oracle.py`). `test_state_mutations.py` runs nineteen focused removal mutations in disposable copies inside this worktree; no mutation changes the active checkout or an assertion.

## Scope and integration (read)

State changes are in `engine.py`, `storage.py`, `recovery.py`, `retention.py`, `chrome/committed.py`, qualification's stored-record read, and the adapter's notice/pending, owner-list, check/recovery, evidence and read-result functions. There is no new projection and no new acknowledgement format. 19b can absorb the current keys, source check fingerprints, occurrence IDs, acknowledgements and tombstones directly; it replaces this reader with its shared committed read path. Immutable history is never rewritten.

Small changes required in Part P areas: `Chrome.trusted()` reads its stored owner entry through the same committed reader; no classification or authorization semantics were added there. Two fixture consumer files, `control/chrome/ci/matrices.mjs` and `control/chrome/ci/sites/matrices.mjs`, read native dialogs from **`untrusted_content.dialog`** after S12. No receiver assertion was relaxed. The payload, binding, question and dispatch implementation otherwise stays with Part P. Status stages keep their names, with each value wrapped in `untrusted_content`; evidence puts its stages inside `untrusted_content` too.

The old committed-read test expected a mixed storage-fallback continuation to count only Chrome's hidden row. Its assertion now requires all four hidden rows and the shared `control_notices` route (the three displaced cached Mail warnings plus the remaining Chrome warning). This corrects the reviewed loss; it removes no test coverage.

## Verified (run)

Local execution is restricted to plain Python and Node tests; no browser process, browser profile, system installation or Gradle daemon was used. Focused review regressions on the final source: `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -p 'test_state_*.py' -v` printed **24 tests, OK**, including **19 STATE MUTATION KILLED** lines and **9 actual process cuts**. The nine cuts use `os._exit(73)` before/after the independent record append, SQLite prepare, SQLite apply and journal commit, plus immediately before dispatch; raw committed status is inspected before startup can recover anything.

The oracle's semantic warning triggers come from the scenario script and receiver observations; local commit facts and opaque occurrence IDs come from its own hash-chain decoder. A warning row cannot justify its own expected warning. The receiver independently records whether input was authorized and had a committed submitting context; duplicate operation arrivals fail. Public Chrome notices, all pending pages, all log pages, passive envelopes and individual statuses are checked separately. An actual read failure must disclose unavailable state; that is counted separately from a successful equality comparison. Even refused public calls must preserve current Chrome disclosures when the committed record remains readable.

Writer flows: readonly, allow, revoke, trusted, qualification, delivery, observation, activation, stopped submission preparation, acknowledgement, release, upload copy, drop, retirement, lost queue, approved stopped submission and restore. Single ENOSPC, persistent exhaustion and primary/cleanup pairs use the existing raw OS/SQLite VFS injector. Injection remains active for the first view comparison; the next comparison restores space without restarting; process cuts are separate evidence.

Final full workflow results and exact log-line evidence: **pending**. Final source workflows started manually: Chrome `42797577799`; base `42797584820`; Mail `42797589663`. The repeat is started after the active run is established; Mail's workflow cancels an active run on another dispatch, so its repeat waits for completion.

Earlier diagnostics are not final acceptance: base `42794569981` and `42796262618` passed on preceding heads; local 148-case Node VM suite passed. Superseded Chrome runs and interrupted local sweeps are not counted as passes. The new oracle/process cuts exposed the startup false-interruption defect, which was fixed before final source verification.

The draft PR's automatic qualification workflow tests GitHub's combined merge ref against the moving Part P base. Runs `42796238861` and `42797097033` fail the new Part P Node case **P27 Stop lifts navigation blocks before deferred native restoration**, with `Cannot read properties of undefined (reading 'callback')` in `background.test.mjs`. It is outside Part S's files; this is retained for the package lead, separate from branch-only verification.

## Not verified

The twice-complete final-source workflows are still in progress. No synthetic pass establishes real accounts, live sites, an installed image or the owner's desktop. Part P owns its panel cases; group 12 remains the existing 18d gap. This report does not close that gap or the owner-Enter panel boundary.

## JUDGMENT-CALL

None beyond the brief's decisions. Finished-check retirement keeps immutable history and acknowledgement identities; stale work cannot resume. Unavailable disclosures preserve access to recovery without granting any input authority.

## PLAN-GAP

No new design change. Integration must retain the S12 dialog result location and the committed owner-entry read when combining the adapter changes. The contemporaneous combined-ref P27 failure belongs to the ongoing Part P build.

## Open questions / run and disk ledger

No owner preference is needed. Five earlier Chrome workflow IDs were cancelled or superseded; the sixth is the first final-source attempt. The cap remains about fifteen. A closing run ledger and `.work/` files above 500 MB will be recorded after verification.
