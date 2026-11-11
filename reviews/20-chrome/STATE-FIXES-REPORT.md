# Part S — state review fixes

## Combined-head rule (lead, 2026-11-10; integrate-3)

Part S is merged into `pkg/20-chrome` by the lead's `3b37bd57`. The catalogue JUDGMENT-CALL below is
**accepted by the lead with an absolute cap**, and is now a decided rule, not an owner question: a snapshot
expires five minutes after its last valid page request or thirty minutes after creation, whichever comes first.
Invalid cursors never renew it; at most two snapshots remain retained. An expired cursor explicitly says
“start the list again without a cursor”. The combined-head tests exercise all three catalogues at both
deadlines, an active walk, a full immutable 26-minute walk, pruning and restart.

The cap changes only Chrome's `control/chrome/extension/background.js`. The shared
`control/aresos_control/paging.py`, `results.py` and `mail/` are untouched by this integration change;
Mail's behaviour is unchanged and the 18d/19b merge order is unaffected. `background.js` belongs to Part P:
Part S's one-line renewal was merged into Part P's equivalent renewal, and the merge kept Part P's version.
Combined verification and the exact-head CI evidence route are in [REPORT.md](REPORT.md); earlier results below
remain Part S's own source evidence.

The first combined CI run also found six legacy `dialog` reads in Part P's newer `ci/review-matrices.mjs`.
They now use S12's `untrusted_content.dialog`, as `ci/matrices.mjs` and `ci/sites/matrices.mjs` already did.
This is a fixture-consumer correction only, with a browser-free contract regression/removal mutation; no service
result shape, page behavior, receiver assertion or approval assertion changed.

The combined Mail PR run exposed a base test's timing-sensitive injection: a 50 ms whole-upload timeout could
fire before its final frame. The minimal `control/tests/test_review22_protocol.py` change injects timeout only
after that frame is sent, preserving the unknown result, committed bytes and import-journal assertions. Ten
focused repetitions and all three socket timeout cases pass. This is a test-fixture change; shared production
paging, results, engine, storage and Mail code are unchanged by the integration run. See the combined report for
the failed run and the required exact-head repeats.

A later combined browser run exposed a Part P publication race: a read could finish during native-dialog
frame lookup and return text before frame/guard provenance was known. `background.js` now waits on a private,
bounded readiness promise across read/result paths and re-enters modal reading after a final-frame race.
This preserves the decided borrowed-dialog question instead of exposing incomplete metadata. Ordering/deadline
regressions and removal mutations cover the fix; the combined report retains the failed raw object and final
verification. No shared production paging, results, state or Mail file changes for this fix.

The next combined pair found a popup admitted before its document committed, leaving no reader in the surviving
page. The Chrome-only recovery installs the passive ISOLATED reader/guard on the exact native document when the
browser reports a missing receiver. Document-ID-addressed reads/injection prevent navigation from mixing privacy
identities; an existing password-history refusal is preserved. First-act reload and all dirty/media/POST checks
remain. Both full-fixture workflow deadlines now accommodate the sequential exhaustive browser/Python stages
(240-minute container, 250-minute job). The combined report records the failed pair, strict regressions and run
allowance discrepancy. Shared production paging, results, state and Mail files remain unchanged by this fix.

**Status: Part S complete; final-source suites green twice.** Draft PR [#34](https://github.com/Ares-Empire/AresOS/pull/34) targets `pkg/20-chrome`. Runtime and fixture source `e5f3d8c5`; runtime hash `7d84b3d1223caff2b40d9feb68ffba285fc6819eac89eca711494a692e576edc`.

## Done (read)

The existing committed-journal reader is the single Chrome authority for operation status, pending work, permissions and qualification. It writes no record, cache or projection file. `Store.chrome_state` shares that reader with the adapter and qualification service. Restore reconciles bounded configuration, checks, operation outcomes, acknowledgements and tombstones while `restore_pending` stays set; only the last generation commit unlocks it. Qualification reads use the complete committed history directly, including histories larger than a restore batch, so restore does not duplicate it into disposable SQLite.

Finished checks retire through bounded `control_expire` commits once their occurrences are acknowledged. Their immutable journal records keep deduplication, clean-interval and acknowledgement identities; an individual retired identity is read from that same journal if it returns. Nothing replays input. Explicit notice and pending checks reconcile queues even when page reading is gated or the tab has been released. Lost queues commit stale non-resumable results; returning stale entries are acknowledged without another preparation. An unavailable live queue leaves its committed check open and readable. Uncertain activation occurrences still need their own acknowledgement.

| Item | Fix | Regression / removal mutation |
|---|---|---|
| S1 / D-1 | Reconcile Chrome rows before restore unlocks; qualification and owner permission reads use committed history. | `test_s1_restore_reconciles_revocation_readonly_and_qualification_offline`; `test_s1_readable_policy_rollback_cannot_hide_committed_qualification`; `test_s1_large_qualification_history_restores_without_a_large_rewrite`; mutations **S1 restore**, **S1 qualification**, **S1 large qualification**. |
| S2 / D-2 | Every Chrome operation and pending read uses the committed journal plus live identity checks, including readable SQLite ahead of or behind it. | `test_s2_readable_rollback_pending_uses_committed_reservation`; `test_s2_failed_completion_marker_never_reports_uncommitted_done`; mutations **S2 status**, **S2 pending**. |
| S3 / D-3 | Restore preserves committed terminal outcomes and acknowledgements. Operation acknowledgements, like occurrence acknowledgements, are monotonic. | `test_s3_cancel_and_expiry_ack_survive_rollback_restore_archive_restart`; mutation **S3 terminal**. |
| S4 / D-4 | Retire completed checks and acknowledged occurrences, keeping historical receipts. Retirement also works under owner archive admission above the history quota. | `test_s4_more_than_512_completed_checks_leave_room_for_chrome_and_mail` (520 public reads, then new Mail intent admission); `test_s4_retirement_keeps_warning_ack_and_dedup_identity_in_history`; `test_s4_archive_retires_checks_even_above_the_shared_history_quota`; mutations **S4 retirement**, **S4 receipts**, **S4 archive admission**. |
| S5 / D-5 | A live open check is disclosed as a check, never materialized as an interruption occurrence. Startup defers Chrome interruption materialization until local replay; a recovered terminal result removes only uncommitted recovery proposals. | `test_s5_clean_stopped_submission_has_no_interruption_warning`; actual process-cut test below; mutations **S5 live check**, **S5 startup**. |
| S6 / D-6 | Read reconciles committed open checks against live session and queued steps. Lost steps become stale, non-resumable results; uncertain activations remain separately acknowledgeable. | `test_s6_lost_queue_resolves_native_check_and_preserves_uncertain_occurrence`; `test_s6_a_stale_step_cannot_be_prepared_if_the_same_queue_entry_returns`; `test_s6_notices_and_pending_resolve_lost_queues_without_page_reads`; `test_s6_unavailable_queue_keeps_its_committed_open_check_readable`; mutations **S6 lost queue**, **S6 stale queue returns**, **S6 read-gated queue loss**, **S6 unavailable queue**. |
| S7 / D-7 | `chrome_drop` has cancellation semantics at request admission, recovery classification, index admission and cancellation-budget consumption. | `test_s7_drop_spends_cancel_reservation_at_history_and_physical_boundaries`; mutation **S7 admission**. |
| S8 / D-8 | Index-bound disclosure returns a bounded explicit unavailable warning, leaving public owner archive admission reachable, including after restart. | `test_s8_archive_remains_publicly_reachable_above_index_bound_and_after_restart`; `test_s8_index_bound_keeps_readable_mail_warnings_and_their_continuation`; mutations **S8 public archive**, **S8 Mail preservation**. |
| S9 / D-9 | Storage fallback keeps known Mail warning totals and routes, accounts for displacement in the compact page, and removes stale Chrome counts before adding current ones. | `test_s9_mail_only_and_mixed_fallback_keep_all_remaining_counts`; `test_s9_replacing_a_cached_chrome_page_does_not_double_count_its_hidden_rows`; mutation **S9 Mail continuation**. |
| S10 / D-10 | Shared ordering uses nanoseconds, including Chrome's synthesized fallback times. | `test_s10_mixed_notice_pages_use_nanosecond_chronology`; mutation **S10 chronology**. |
| S11 / D-11 | Scenario/receiver oracle decodes only committed journal records. Every public view is independently checked during active injection, after space returns without restart, and after restart. Actual process exits cover durable cuts separately. | `test_every_chrome_durable_writer_single_persistent_cleanup_pairs_restart_space_restored`; `test_chrome_storage_single_persistent_cleanup_pairs_crash_restart_space_restored`; `test_s11_actual_process_cuts_before_and_after_input_keep_every_committed_view`; oracle self-tests for R1, R2, R3 and round 27; `test_s11_persistent_write_exhaustion_retains_exact_committed_disclosure`; mutations **S11 oracle**, **S11 journal read close**. |
| S12 / PKG-6, C-6, D-12 | Read dialogs, activation followups, stage details, error observations, operation status, evidence and historical Chrome audit summaries put page text inside `untrusted_content`; ordinary audit summaries are service-authored. | `test_s12_every_page_text_copy_is_inside_untrusted_content`; mutations **S12 dialog**, **S12 stages**. |

All `test_s*` names above are in `control/chrome_tests/test_state_fixes.py` except process cuts (`test_state_crashes.py`), persistent exhaustion (`test_state_exhaustion.py`) and oracle self-tests (`test_state_oracle.py`). `test_state_mutations.py` runs twenty-four focused removal mutations in disposable copies inside this worktree; no mutation changes the active checkout or an assertion.

## Scope and integration (read)

State changes are in `engine.py`, `storage.py`, `recovery.py`, `retention.py`, `chrome/committed.py`, qualification's stored-record read, and the adapter's notice/pending, owner-list, check/recovery, evidence and read-result functions. There is no new projection and no new acknowledgement format. 19b can absorb the current keys, source check fingerprints, occurrence IDs, acknowledgements and tombstones directly; it replaces this reader with its shared committed read path. Immutable history is never rewritten.

Small changes required in Part P areas: `Chrome.trusted()` reads its stored owner entry through the same committed reader; no classification or authorization semantics were added there. Two fixture consumer files, `control/chrome/ci/matrices.mjs` and `control/chrome/ci/sites/matrices.mjs`, read native dialogs from **`untrusted_content.dialog`** after S12. No receiver assertion was relaxed. The payload, binding, question and dispatch implementation otherwise stays with Part P. Status stages keep their names, with each value wrapped in `untrusted_content`; evidence puts its stages inside `untrusted_content` too.

The other necessary Part P file change is two deadline values in `.github/workflows/control-chrome.yml`: the container limit is 165 minutes and the job limit 175. Run `42803086121` hit the former 105-minute limit in both modes (exit 124), after all 200 Python tests passed in 3480.039 seconds externally and 2596.640 seconds under policy. Its browser word matrix was incomplete, so it is not acceptance. The state sweeps now run independent flows in two spawned Python processes with separate stores and fault injectors. Every result is required; worker assertions fail the parent and are never retried. Fault points, view comparisons, cleanup pairs and receiver assertions are unchanged. `test_state_sweeps.py` checks process isolation and assertion propagation; removing `future.result()` makes its failure-propagation test fail (retained mutation evidence). The extended deadline allows the full browser inventory to finish despite runner timing variance.

The final necessary Part P edit is one assignment in `control/chrome/extension/background.js`: a valid catalogue cursor renews its snapshot's last-use time. Run `42819687759` passed external installation but policy mode failed its complete-catalogue case when a long history walk exceeded five absolute minutes. The snapshot remains immutable, expires after five idle minutes, and keeps the existing two-snapshot, 10,000-item and 8 MiB bounds. The test was preserved. New browser-free Node regressions are in Part S's `state-catalogues.test.mjs`; removing the renewal makes active paging fail.

The old committed-read test expected a mixed storage-fallback continuation to count only Chrome's hidden row. Its assertion now requires all four hidden rows and the shared `control_notices` route (the three displaced cached Mail warnings plus the remaining Chrome warning). This corrects the reviewed loss; it removes no test coverage.

## Verified (run)

Local execution used plain Python and Node only. No browser process, browser profile, system installation or Gradle daemon was used on the Mac. On final source `e5f3d8c5`, `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -v` passed **202 tests twice**, in **739.349s** and **782.549s**. Retained [first](records/state-fixes/local-final-python-1.txt) and [repeat](records/state-fixes/local-final-python-2.txt) outputs have writer totals on line 82, nine actual process cuts on 174, 24 killed state removal mutations on 198–221, dispatch totals on 235 and results on 255/257. Exact per-item test, mutation and run lines are indexed in [state-test-index.json](records/state-fixes/state-test-index.json).

Writer totals per pass: **1,860 single, 1,860 persistent, 7,111 cleanup pairs**. Dispatch totals: **446 single, 446 persistent, 2,116 cleanup pairs**. Each scenario compares every public view with injection active, after space returns without restart, and after restart. The separate process tests use `os._exit(73)` before/after independent append, SQL prepare, SQL apply and commit, plus before dispatch; raw committed status is inspected before startup recovery. Independent worker results are mandatory. Removing worker assertion propagation is killed by its [focused regression](records/state-fixes/worker-removal-mutation.txt).

The scenario/receiver oracle has its own committed hash-chain decoder and imports neither production state code nor SQLite. Warning triggers come from the scenario and receiver history; a warning row cannot justify itself. Receiver arrivals require authorization and a committed submitting context; duplicate arrivals fail. Chrome notices, all pending/log pages, passive envelopes, live validity and individual statuses are checked separately. Refused responses still preserve the exact warning set; write exhaustion cannot be replaced by a generic unavailable disclosure. Policy refusals of a command's own data are counted separately while its envelope is checked.

`node --test control/chrome_tests/*.test.mjs` passed **151 tests twice**, retained as [first](records/state-fixes/local-final-node-1.txt) and [repeat](records/state-fixes/local-final-node-2.txt), result lines 152/154/155. New clock-controlled catalogue tests walk all 80 captured rows for downloads, history and bookmarks over more than five minutes, prove the source is queried once, preserve idle expiry, reject wrong-scope/out-of-range cursor renewal, and retain the two-snapshot bound. The [renewal removal mutation](records/state-fixes/catalogue-removal-mutation.txt) fails. `python3 control/generate.py --check` printed `Generated artifacts match definitions`.

Final-source Chrome passed twice: [`42846669867`](https://github.com/Ares-Empire/AresOS/actions/runs/42846669867) and [`42888182810`](https://github.com/Ares-Empire/AresOS/actions/runs/42888182810), both external and policy installation. Each mode ran all 202 Python tests, 151 Node tests and 61 named browser cases. All four retained browser passes satisfy the independent [receiver audit](records/state-fixes/receiver-audit.json): **135 approval sequences each at 0 before approval, 1 after, 1 after repeat; 20 independent free-dialog sequences each; unchanged native popup document/windows after Stop; one POST popup request**. Group 12 is deliberately false, as required until 18d. Per-S test/mutation output lines and actual run sources are in [state-test-index.json](records/state-fixes/state-test-index.json); Node result lines are in [node-test-index.json](records/state-fixes/node-test-index.json). Artifact manifests retain SHA-256, exact source, install mode and attempt: [first](records/state-fixes/42846669867-artifacts.json), [repeat](records/state-fixes/42888182810-artifacts.json).

The first Chrome run's external runner lost communication with GitHub before it could upload logs or an artifact. Its [failure annotation](records/state-fixes/runner-loss-42846669867.json) is retained; no test result is inferred from that attempt. Only the failed job was rerun on the same commit. First acceptance uses policy attempt 1 and external attempt 2; the repeat ran both modes afresh. No test assertion was changed or bypassed.

Final-source base passed twice: [`42846676171`](https://github.com/Ares-Empire/AresOS/actions/runs/42846676171), [`42870880216`](https://github.com/Ares-Empire/AresOS/actions/runs/42870880216), **142 tests each**. Mail passed twice: [`42846682893`](https://github.com/Ares-Empire/AresOS/actions/runs/42846682893), [`42870886492`](https://github.com/Ares-Empire/AresOS/actions/runs/42870886492), **142 base tests, 309 Mail tests and all four fault-sweep shards each**. Exact retained output excerpts, original artifact line numbers and hashes are in [shared-final-summaries.json](records/state-fixes/shared-final-summaries.json). All final workflows tested head `1418fcde`, whose runtime, tests and workflow files equal source `e5f3d8c5`; the difference is report/evidence only. Earlier shared passes on runtime `0cd2ea49…` remain historical in [shared-summaries.json](records/state-fixes/shared-summaries.json).

Chrome `42803086121` timed out at 105 minutes; both 200-test Python suites passed, but browser matrices were incomplete ([record](records/state-fixes/timeout-42803086121.json)). Its replacement `42819687759` passed all 202 Python tests in both modes and the external browser job. Policy mode failed one of 61 named cases, **FEATURE tools forms options find wait fill_form scroll and full catalogues**, on absolute snapshot expiry. The [failed-job record](records/state-fixes/failure-42819687759-policy/record.json), browser log, matrix and Python output are retained separately. This failure caused the catalogue fix; neither workflow is full acceptance evidence.

Older local 200-case and 202-case passes, interrupted/superseded runs, and automatic qualification tests of GitHub's combined Part P merge ref remain diagnostic history. They do not establish final branch-only acceptance. The combined-ref workflow previously exposed a Part P P27 callback failure; later combined refs passed, as recorded separately from these state-branch results.

## Not verified

Synthetic tests do not establish real accounts, live sites, an installed image or the owner's desktop. Part P owns its panel cases; group 12 remains the existing 18d gap. This report does not close that gap or the owner-Enter panel boundary. Final Part S local and Linux-container suites are green twice.

## JUDGMENT-CALL

**Decided by the lead, 2026-11-10, with integrate-3's absolute cap.** Catalogue lifetime is five minutes of
inactivity, bounded by thirty minutes from creation. A valid page request keeps the captured immutable list
available until the earlier deadline. Rejected alternatives were five absolute minutes (the observed slow-walk
failure), reducing the fixture (would hide that failure), no expiry (would retain idle snapshots), and unlimited
active renewal (would keep a stale walk alive forever). The existing two-snapshot and size bounds remain.
These reads authorize no input. Changing the rule later changes only Chrome's deadlines and its clock-controlled
regression expectations. This decision does not go to the owner.

## PLAN-GAP

Specification was fetched from `origin/main` before reading it with `git show`; continuation/integration briefs absent there were read on this branch. `20-integrate-3.md` now takes precedence. The long-catalogue lifetime case surfaced in CI and is settled by the lead's capped-lifetime rule above. Integration retains S12's dialog location, the committed stored-entry read, and Part P's valid-cursor timestamp renewal. No committed identity or acknowledgement migration is introduced. The historical combined-ref P27 failure belongs to Part P's earlier build.

## Open questions / run and disk ledger

No implementation question remains. The catalogue-lifetime decision is accepted by the lead and needs no owner
decision. Part S's original draft PR was into `pkg/20-chrome`; the lead subsequently merged it. This integration
works only on `pkg/20-chrome`, keeps PR #27 draft and never merges or pushes to `main`.

The lead's 2026-11-10 16:10 direction raised the state branch allowance to about 25 Chrome runs and required blocking shell waits instead of per-turn CI polling. Closing [ledger](records/state-fixes/run-ledger.json): **16 GitHub run IDs, 17 executions including the failed-runner retry**, within that allowance. This includes twelve cancelled/superseded diagnostics, the 105-minute timeout, the catalogue-expiry failure, the final first run with its infrastructure retry, and the full repeat. The earlier cancelled/superseded runs were started by this build. No other build's workflow was cancelled. After the lead's direction, each run/batch was awaited with one blocking `gh run watch --exit-status --interval 60` shell call; failed-job logs were examined after completion. Successful records were retained and indexed programmatically for this report.

Closing [disk inventory](records/state-fixes/work-inventory.json): no `.work/` file over 500 MiB and no retained large download, ISO, extracted image or browser profile. No Gradle daemon was started. No local test process started by this build remains.

Identity lookups absent from the current set scan the committed journal; 19b should replace that slow path with its shared lookup while retaining these identities. Long-history performance beyond the retained stress cases is not measured here.
