# 19b — owner state

**Current status — stage 2 fixes round 1 complete (2026-11-10):**
The oracle, alteration-test, RENAME and fixture fixes are complete. Control base,
Mail (all 64 jobs) and boundary each passed twice on `08644540`; both complete
53-list strict merges reproduce the compact pin with zero R2 gaps. The final
section below supersedes the earlier fold evidence. Stage 3 has not been started.

## Done

**Read:** `AGENTS.md`, both 19b briefs (the Mail note wins), the repository design/workflow/review documents, Mail rounds 16–22 security reviews and rounds 26b/27 inventories. This branch starts from the Mail branch and its note; draft PR [#26](https://github.com/Ares-Empire/AresOS/pull/26) targets `pkg/19-mail`. No merge.

**Read — implementation:** [COVERAGE.md](COVERAGE.md) was committed alone in `c9faec45`, before any code. M01–M14 preserve every round-26b row; C01–C05 preserve inventory C. The executable map links each to sweep, lifecycle, refusal, quiet-use and regression cases.

**Read — implementation:** `control/owner_state_oracle/` is shared test code. `records.py` independently decodes committed events, independent fences/commit markers and hash-valid recursive archives from the documented Mail disk format; it ignores working `kv` rows and the production index. SQLite/hot-journal recovery operates on a byte copy inside the worktree. Prepared and unprepared transactions remain distinct. [FORMAT.md](../../control/owner_state_oracle/FORMAT.md) documents the format and evidence rules.

**Read — implementation:** the expectation core uses the Python standard library only. An AST import test enforces that boundary. Its inputs are ordered scripted calls/arguments/test clock/faults/delivered-or-lost replies, real fixture command logs and independently decoded commits. The driver may import production modules to exercise/read them; expectations do not. Pre-command snapshots bind exact current attempts, accounts, messages, recipients, folders, roles/delimiters, flags, wire hashes and POST bodies. Independent event replay audits local testapp deletions, settings and role-review effects against prior context and scripted arguments; separate receiver configuration is recorded before its effect. Historical/previous/current protected roots must remain intact. SMTP, IMAP, HTTPS and testapp receiver evidence are recorded outside fault injection; AUTH credentials are excluded.

**Read — implementation:** `test_owner_state_sweep.py` covers all 22 inherited flows and ten additional flows, every discovered single/persistent write fault, primary/cleanup pairs, restored space without restart, and a separate immediate-crash/restart branch. Comparisons run before status can recreate lost evidence. Pending, each app catalogue, audit/log and passive envelopes are checked separately, with exact identities/counts/reasons/metadata and every page. The installed channel test covers socket, CLI, real MCP process and hooks. The original transport/schema validator still runs; its exact schema failures become separate strict gap assertions, while unrelated exceptions remain hard failures. Existing tests remain enabled; the CI selection includes the new sweep.

**Read — implementation:** check state, warning fingerprint/occurrence, acknowledgement and action resolution are separate in the oracle. Repeated identical evidence preserves identity/ack; changed evidence or independently proved committed clean then recurrence creates a new occurrence; clean never removes an unacknowledged warning. Focused cases cover archive, expiry, restore, restart, legacy records and normal quiet send/move/copy/rename/deletes. Mutation tests deliberately break R1, R2, R3 and round 27, including review-19/lost-duplicates evidence.

**Read — implementation:** reviews 20/21/22 have named regressions and independent cases. The three review-22 assertions lead [KNOWN-GAPS.md](KNOWN-GAPS.md). The ledger contains 675,562 assertion-specific failures in 1,501 exact delta groups (44,856 stage 2; 630,706 stage 3). Exact failures are pinned in `KNOWN-GAPS.json` by case/mode/fault/cleanup/phase/view/page, matrix row and closing stage. Grouped storage only deduplicates identical deltas; every case is explicit. Unexpected pass, changed delta, unlisted failure, omitted view or unexecuted suite entry fails.

**Read — public changes:** the required paging description now says `page_changed` restarts the first page; generated tool JSON and `docs/control/TOOLS.md` match. `control-base.yml` and `control-mail.yml` accept PRs to `pkg/19-mail`; there are no other workflow-definition changes. No production storage, warning selection, approval, tool behavior, restore sentence or projection was changed. The new tests expose work for stages 2/3.

## Verified

**Run — final strict source:** `0caf753626c24e58141a52c5e9ed7d26ed6a5ddc`. Every workflow below passed twice. The closing report/review commit changes documentation only; no test source, production source or gap data changed after these runs.

| Workflow | Final repetitions | Exact output / artifact evidence |
| --- | --- | --- |
| Control base | [42644340866 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42644340866/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42644340866/attempts/2), both success | `results.txt:326/321`: `Ran 192 tests in 185.630s` / `Ran 192 tests in 192.117s`; lines 328/323 `OK`; lines 335/330 `Control base suite PASS`. |
| Control Mail 1 | [42644340882](https://github.com/Ares-Empire/AresOS/actions/runs/42644340882), all five jobs success | Suite `mail.txt:361`: `Ran 316 tests in 1202.465s`, `OK`, `Control Mail suite PASS`; shared `base.txt:316`: `Ran 192 tests in 240.071s`, `OK`; fixture isolation PASS. |
| Control Mail 2 | [42644366804](https://github.com/Ares-Empire/AresOS/actions/runs/42644366804), all five jobs success | Suite `mail.txt:361`: `Ran 316 tests in 985.401s`, `OK`, `Control Mail suite PASS`; shared `base.txt:313`: `Ran 192 tests in 229.961s`, `OK`; fixture isolation PASS. |
| Control boundary | [42644365833](https://github.com/Ares-Empire/AresOS/actions/runs/42644365833), [42644371566](https://github.com/Ares-Empire/AresOS/actions/runs/42644371566), both success | `identity.txt:1` records this source SHA. `present-console.txt:808/808` and `absent-console.txt:715/715`: `SETTINGS_OK mcp_exclusive marketplace_lock sideload_flags`. Both hostile-program modes and separate-user/policy steps succeeded. |

Each Mail sweep artifact has four inherited tests plus three independent workers with four test methods each. All four runners print `OK`; all three workers exit 0 and enforce their complete strict ledger scope. The table gives exact `mail.txt` lines within `control-mail-sweep-N-RUN-1` artifacts. No discovery mode or accepted exception replaces those assertions.

| Sweep shard | First repetition: duration and proof | Second repetition: duration and proof |
| --- | --- | --- |
| 0 | 28m 48s; `OK` lines 259/417/536/651; worker exits 418/537/652; strict counts 53630/58560/59237 | 21m 48s; `OK` lines 259/417/536/651; worker exits 418/537/652; strict counts 53630/58560/59237 |
| 1 | 19m 24s; `OK` lines 250/372/475/586; worker exits 373/476/587; strict counts 51994/57962/52822 | 28m 13s; `OK` lines 250/372/475/586; worker exits 373/476/587; strict counts 51994/57962/52822 |
| 2 | 26m 17s; `OK` lines 20/122/237/360; worker exits 123/238/361; strict counts 60320/54579/54176 | 24m 40s; `OK` lines 20/122/237/360; worker exits 123/238/361; strict counts 60320/54579/54176 |
| 3 | 22m 18s; `OK` lines 20/162/303/394; worker exits 163/304/395; strict counts 57187/60527/54706 | 24m 53s; `OK` lines 20/162/303/394; worker exits 163/304/395; strict counts 57187/60527/54706 |

Every one of the ten Mail jobs completed under 45 minutes; maximum 28m 48s, measured from workflow job startedAt/completedAt.

The commands are the unchanged workflow commands: Fedora `bash control/ci/test.sh`, isolated `bash control/ci/mail/run.sh suite` and `sweep` (shards 0–3), and the boundary Docker harness plus `bash control/boundary/isolation.sh`. No real account or model call is used.

**Run — development failures, retained for audit:** base [42585513451](https://github.com/Ares-Empire/AresOS/actions/runs/42585513451) exposed a harness comparison of opaque cursors with different app scopes; each view now follows and validates its own token. Mail [42586664730](https://github.com/Ares-Empire/AresOS/actions/runs/42586664730) failed when the new driver read SQLite generation directly under persistent exhaustion (`OperationalError`); it now records the unavailable-generation assertion delta. Mail [42594791368](https://github.com/Ares-Empire/AresOS/actions/runs/42594791368) passed its 316-test suite and shards 2/3, but shards 0/1 hit the 45-minute timeout. The gap index and primary-fault partition in `5cb3ac64` reduced uneven work, but run [42600725397](https://github.com/Ares-Empire/AresOS/actions/runs/42600725397) still timed out all four shards: one finished the owner oracle before the inherited tests hit the cap, while others were still in full onboarding. `fd9af47d` runs two isolated owner-sweep processes alongside the inherited tests, retaining all assertions and checking every child exit. Both scheduling changes received sol high SAFE reviews. The first process-split capture at `fd9af47d` was superseded when a focused review found and then verified fixes for local-mutation oracle blind spots; its suite passed. Its completed sweep jobs failed in 28–30 minutes on testapp status schema violations under exhaustion, proving child failures reach the job result. The next correction preserves those validator failures as exact stage-3 gap assertions rather than aborting comparison or changing production. Superseded runs are not final evidence. Earlier superseded Mail runs were cancelled when source changed. None of those runs is claimed as final strict green.

**Run — local (diagnostic, outside workflow evidence):** 49 independent oracle self-tests passed (`Ran 49 tests`, `OK`). The focused contract/named-regression diagnostic plus partition/repeatability/constructor checks passed ten tests (`OK`) using a local shim for Linux-only installed boundary files; this is not installed-policy verification. `python3 control/generate.py --check` printed `Generated artifacts match definitions`; `git diff --check` passed. GitHub's isolated Linux containers supply the authoritative installed-policy/server tests. No model or real account is used.

Local commands (the `.work/run-owner-tests.py` policy shim is diagnostic only):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control .work/venv/bin/python -m unittest discover -s control/tests -p test_owner_state_oracle.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests .work/venv/bin/python .work/run-owner-tests.py \
  test_owner_state_sweep.OwnerStateSweep.test_shards_cover_every_fault_and_keep_its_cleanup_and_crash_cases \
  test_owner_state_sweep.OwnerStateSweep.test_repeated_fault_is_independent_of_ambient_identity_order \
  test_owner_state_sweep.OwnerStateSweep.test_constructor_failure_restores_request_and_clock \
  test_owner_state_contracts test_owner_state_regressions
python3 control/generate.py --check
git diff --check
```


**Read — review:** [STAGE-1-REVIEW.md](STAGE-1-REVIEW.md) records the required fresh sol high review and its final scope. The reviewer approved the initial strict source/ledger at `10accdf1`, then the calendar-only correction at `51041df1`, as SAFE. The initial 675,775 keys matched harvested data exactly; the reviewer independently validated the maintenance-only correction to 675,562, tags, ownership and completeness, and ran 45 self-tests. The final reproducible pin at `ec2fe843` also received SAFE: all eight Linux captures, all 32 flows per worker, exact 675,562-key/1,513-group pin, 115 unchanged non-sweep entries, strict restoration and 47 self-tests were independently checked. This is not approval of production gap closure.

**Run — calendar correction:** no-argument C localtime ignored the earlier time.time shim, making the pinned audit data depend on the real date. A complete local maintenance replay first matched all 2,914 Linux failures across 62 boundaries exactly; recollection with the effective-clock calendar produced 2,701 (234 removed, 21 added, no changed shared values). Only maintenance entries changed. The corrected strict local replay passed all 2,701 entries; final full Linux repetitions verify the complete ledger. Host-date/retention-advance/explicit-time conversion, exception cleanup and constructor cleanup tests were added. Installed CLI audit checks now filter today's records and bound both midnight and catalogue restarts.

**Run — repeatability failure and correction:** [42623480745](https://github.com/Ares-Empire/AresOS/actions/runs/42623480745) at `51041df1` passed the 316-test Mail suite, 188-test shared base and all inherited sweep tests, but every owner worker failed strict comparisons. Completed artifacts show changes only in repair, settlement, filing move/copy and onboarding. The fresh reviewer independently identified real recovery-order changes from sorting random UUID keys and occurrence-alias permutations. The correction uses unique, nonmonotonic, per-flow seeded UUIDv4 inputs, continuous across restarts, plus effective-clock nanosecond timestamps. It changes test inputs, not equality assertions. Both parent/repair ID orders and ambient-ID independence are tested.

**Run — Linux recollection:** local Mac clean traces exposed missing descriptor-close positions in the earlier dictionary policy shim. A real descriptor walk rooted inside the worktree reproduced those positions, but four copy/export/archive flows still differed by platform. Abandoned local captures were discarded. The complete ledger was therefore recollected in Linux [42628677586](https://github.com/Ares-Empire/AresOS/actions/runs/42628677586), source `198b9ef1`; each capture worker deliberately failed after emitting every exact assertion. This is diagnostic evidence, never green verification. Base [42628677620](https://github.com/Ares-Empire/AresOS/actions/runs/42628677620) passed 190 tests (`results.txt:319`, line 321 `OK`, line 328 `Control base suite PASS`). All eight capture workers ran all 32 flows and failed only at the intentional final capture assertion. Every inherited sweep passed. The complete key set is unchanged; 9,894 deltas changed and groups fell to 1,513. All sweep entries were replaced by that Linux capture; 115 non-sweep entries remain from the earlier Linux source and passed strictly in the new suite/base. The pin `ec2fe843` received SAFE; its later strict pair exposed the oracle-only tie described below.


**Run — notice-order failure/correction:** strict runs [42634913901](https://github.com/Ares-Empire/AresOS/actions/runs/42634913901) and [42634933153](https://github.com/Ares-Empire/AresOS/actions/runs/42634933153) passed their 316-test suites and 190-test shared bases, but repair/settlement comparisons depended on Python hash order. Independent fresh-process seeds 1/4 reproduced different expected page slots with identical injected fault traces. Recovery and unchecked notices shared the oracle's old source/time sorting key. The corrected comparator independently derives every documented synthetic/public notice ID, uses saved creation timestamps when present, and groups/sorts by creation time and public ID. Normal CI does not pin a hash seed. New tests cover opposite input orders, fresh hash-seed processes, all synthetic ID forms and saved-time lookup.

**Run — corrected pin:** full local repair captures agree under both hash seeds across all 377 discovered boundaries and every mode/pair/crash: 35,830 identical assertion entries. Settlement, filing move/copy/rename and focused contracts were recollected with the real descriptor walk; their discovered boundary counts match Linux. Four disjoint onboarding replays exactly match all 145,018 prior Linux entries. The pin retains every assertion key and the stage counts, with 8,486 corrected deltas and 1,501 groups. The remaining entries are retained from Linux; the full strict repetitions above are authoritative for the replacement and retained data.

**Run / read — runtime correction:** the first `ec2fe843` run's shard 0 also hit 45 minutes: inherited tests passed in 1,959.637s; worker 0 completed its failing comparisons in 2,616.418s and worker 1 had not finished at the cap. The runner now uses three isolated owner workers per shard. Stable SHA-256 of flow/primary-point spreads periodic write/cleanup patterns; all modes, pairs and crash phases stay with their primary, and clean cases still run on every worker. Unique ownership/completeness and real child-failure propagation are tested for three workers. No cases or inherited assertions were removed. This changes Python scheduling, not workflow definitions.

**Read — final source review:** the fresh sol high reviewer marked `0caf753626c24e58141a52c5e9ed7d26ed6a5ddc` SAFE. They verified the exact replacement captures, all 406,761 retained entries, unchanged onboarding data, row/stage tags, round-trip, strict entrypoints and three-worker hash ownership. They ran 49 self-tests, isolated ownership and diff checks. Production gap closure remains outside this approval.

## Not verified / intentionally not built

Stages 2 and 3 are outside this run. The known-gap list intentionally remains nonempty. New pre-mutation context fields, the durable projection and SQLite-read fallback, one production read path, removal of volatile fallbacks, and restore of free-change warning/ack history are not implemented. No claim that production now satisfies R1–R3 or the whole package acceptance is made. No tests were removed or replaced, so no removed-test mapping is needed.

No real account/provider, owner machine integration or Minecraft/Gradle tests were run; this brief excludes those. The whole-package astra security review belongs after stage 3. No Gradle daemon was started.

**Read — storage:** production persistence bytes per operation are unchanged because this stage changes no persistence. A projection has not been built. The requested send/move/delete/free-change/25 MiB before-and-after measurements and archive-out demonstration belong to stages 2/3; they were not measured here and no figures are inferred.

## JUDGMENT-CALL

**Read:** no new product behavior or owner decision. Test-only choices are reversible: fixed synthetic clock and per-flow pseudo-random UUID stream, byte-copy crash/decoder snapshots, explicit opaque-ID aliases by committed creation order, and grouped exact-delta storage to keep the ledger reviewable and comparisons fast. They preserve every failure and page rather than accepting wildcard failures.

## PLAN-GAP

**Read — superseded by lead D3 in fixes round 1:** G22-evidence exposes a constraint for stage 3: an open check can preserve “not yet checked,” but cannot reconstruct an exact transient remote role fingerprint that was observed while its result write failed and then changed again. The later implementation must retain enough evidence under that failure model, or explicitly reconcile the guarantee with the owner; merely rerunning the latest LIST cannot recover the lost occurrence. Stage 1 records the failing assertion without claiming to solve it.

**Read:** stage-1 acceptance is the coverage/oracle/comparison/strict-gap harness, not the full brief's empty-ledger acceptance. Remaining gaps name stage 2 or 3. This is the user's explicit stopping point.

**Run — workflow budget:** 40 distinct workflow run IDs, 43 attempts including retries and cancelled runs. This exceeded the approximate 25-run target. Independent oracle review fixes, complete Linux baseline capture, calendar and UUID/nanosecond repeatability corrections, and required final repetitions account for the additional runs. Superseded, diagnostic and cancelled documentation-only runs are not passing verification. The report-only push `e32a3f02` restarted base/Mail because PR path filters use the cumulative diff; redundant runs [42649695450](https://github.com/Ares-Empire/AresOS/actions/runs/42649695450) and [42649695455](https://github.com/Ares-Empire/AresOS/actions/runs/42649695455) were cancelled. The closing report correction uses `[skip ci]` to avoid a reporting loop; its diff from tested source contains only the report/review documents.

## Open questions

The lead’s fresh review of this stage-1 fix round is pending. Stage 2 is outside this run and was not started. The next authorized stage must retain the ledger’s unexpected-pass requirement.

## Workspace cleanup

**Run:** a recursive `.work/` inventory found no file over 500 MB. Removed 572,520,370 bytes of duplicate captured ledgers and superseded boundary copies; retained raw Linux evidence and the committed pin. Abandoned local captures were discarded. No large disk image was downloaded, and no Gradle daemon was started.

## Stage 1, fixes round 1

**Run — L1 before expectation changes:** converted the original format-2 full list to format 3. `LEDGER-CONVERSION.json` records source/result SHA-256 and sizes; independent rehashing matched every digest and all 675,562 assertion keys (44,856 stage 2; 630,706 stage 3). The committed summary is 804,042 bytes in 1,623 ownership groups. Each digest pins the key, row, stage and exact calls/missing/extra/page delta. The full list remains only under `.work/` and in CI artifacts. `KNOWN-GAPS.md` documents regenerate/diff commands. `gaps.verify` checks absent/unlisted/changed groups and every owned group; twelve buckets map wholly to the four-shard, three-worker CI split, with shared clean groups checked by all workers.

**Run — L1 local checks:** oracle suite: `Ran 50 tests`, `OK`; generator: `Generated artifacts match definitions`; `git diff --check`: no output. Compact-ledger mutations reject a changed delta, removed/added key, unexpected pass and moved group, and unchanged input passes. The expectation-import AST check still includes `gaps.py`.


**Read — findings 1–9 (test-only implementation):**

| Finding | Change | Breaking-mutation self-test (`StageOneFixMutations`) |
| --- | --- | --- |
| 1 | Replay acknowledgement, check closure and removal against scripted actions and independent evidence; retain obligations and emit lifecycle-proof differences for unjustified transitions. Installed-channel tests now record their actions. | `test_spontaneous_ack_cannot_erase_warning`, `test_scripted_ack_cannot_close_unfinished_check`, `test_archive_cannot_remove_unresolved_reservation` |
| 2 | Compare script/approval against both context and attempted command, including exact account/UID/folder/recipients/flags/repair stage. | `test_matching_context_and_command_cannot_change_script_uid` plus existing exact-field, POST and repair-order mutations |
| 3 | Remove response-error-driven expectations. Check permitted read status from injected faults, transaction/restore state and failed raw reads, including empty catalogues. | `test_empty_healthy_catalogue_cannot_refuse_itself` |
| 4 | Derive background-storage warning and first cause from scripted maintenance fault history; preserve it across failed writes and restart. Decode its public warning independently. | `test_background_first_cause_present_lost_and_restart` |
| 5 | Freeze each recorded reply's expected passive envelope at response time, including original actions, errors and continuation replies, before later evidence reads. | `test_every_action_error_and_continuation_envelope_keeps_live_warning` |
| 6 | Derive completed qualification from probe logs/result commit and subsequent scripted owner settings; compare readiness, bounded Sent policy/caveat and negative DELETE qualification on result/account reads and restart. | `test_completed_qualification_comes_from_probe_evidence`; focused `qualification-probes-restart` |
| 7 | Compare expected recovery/unchecked public handles separately from their owner facts on every page and read. | `test_recovery_handle_is_checked_on_pages_reads_and_ack` |
| 8 | Compare audit sequence/time/action/outcome/operation identity, explanation and structured evidence with the documented untrusted wrapper and bounded historical filing projection. Installed CLI uses the same independent projection. | `test_audit_checks_identity_explanation_evidence_and_marking` |
| 9 | Keep semantic occurrence identity independent of an unknown public handle; bind after successful persistence and retain acknowledgement semantics. | `test_unbound_semantic_occurrence_binds_after_persistence_and_acks` |

**Read — D3 recorded for stage 3:** reserve evidence-record capacity before the remote check using `space.py`. A failing disk leaves the check open and retains the specific occurrence or a committed generic warning that evidence was seen but could not be recorded, with an actionable “check Trash”. `retained_role` and `test_D3_generic_warning_requires_committed_evidence_and_open_check` encode exactly that alternative; an uncommitted or merely “not yet checked” warning does not satisfy it. Production implementation remains deferred.

**Run — local before Linux capture:** 62 oracle self-tests passed (`Ran 62 tests`, `OK`). The focused matrix contracts and six named review regressions passed (`Ran 7 tests`, `OK`) after pinning the new local contract deltas; partition/repeatability/constructor cleanup passed (`Ran 3 tests`, `OK`). A diagnostic traversal ran all 32 flows clean and at primary point 1 in single, persistent and immediate-crash modes; all completed. The descriptor-walk policy fixture is rooted inside this worktree; it is diagnostic, not installed-policy evidence. Generator printed `Generated artifacts match definitions`; diff check printed nothing. Docker CLI exists but its daemon is unavailable, so authoritative installed/container verification is on GitHub Linux. No system software was installed or started.

**Read — scope:** no production modules or approval/tool behavior changed. No tests were removed or weakened; synthetic lifecycle fixtures now include the scripted actions/complete records their transitions require. The compact ledger's local contract update changes 110 focused failures to 367 because the additional envelope, status, lifecycle, handle, qualification and audit checks expose more exact differences. Final Linux counts and workflow evidence follow below.


**Run / read — qualification recorder correction before pinning:** a local raw-probe inspection showed APPEND arrival identities used the recorder's default account after its transport scope ended. The recorder now passes the selected account explicitly. The qualification expectation distinguishes successful exact cleanup from generic refusal with cleanup, lost probe, exact cleanup failure, empty-folder cleanup failure and unverifiable survival. Raw nonempty semantics plus exact survival/EXPUNGE and independently decoded probe result commits supply the proof. `test_qualification_distinguishes_each_negative_probe_reason` checks the successful case and every negative reason; `test_coherent_wrong_append_flags_are_not_authorized` checks that a wrong APPEND flag cannot be justified by a matching context. The corrected source passes 64 oracle self-tests and seven focused contract/regression tests; its local focused pin has 364 failures. The first Linux capture at `9f9d8cc6` is superseded for oracle/ledger evidence; its base (205 tests) and boundary passed, but it is not final-head acceptance evidence.


**Run — final source local checks:** 65 oracle self-tests pass (`Ran 65 tests`, `OK`), including coherent wrong APPEND flags, send message identities and all negative qualification reasons. Scripted repairs follow the independently recorded original approval rather than borrowing attempted command arguments. The seven focused contract/regression tests pass with the corrected 364-entry focused pin. No production path changed. Complete local expiry/maintenance captures under fresh hash seeds 1 and 4 match all 17,811 exact deltas across single/persistent faults, cleanup pairs and immediate restart; this is repeatability evidence, not installed Linux qualification.


**Run — compact pin from completed Linux capture:** Mail [42657094358](https://github.com/Ares-Empire/AresOS/actions/runs/42657094358), attempt 1, source `0b6cfec6`, completed every inherited sweep and all 32 flows in every one of twelve owner workers. Each owner's only failure was its final comparison to the old digest groups. Worker logs contain 96 flow-completion records per shard; all 17 full-list artifacts were merged (12 workers, three named regressions, focused contracts and installed channels). Ownership checks found exactly twelve owners; duplicate shared clean entries agree exactly. Base [42657093657](https://github.com/Ares-Empire/AresOS/actions/runs/42657093657), attempt 1: `results.txt:336` printed `Ran 207 tests in 166.142s`, line 345 `Control base suite PASS`. Mail suite `mail.txt:361`: `Ran 316 tests in 984.640s`, line 365 `Control Mail suite PASS`. The four shard logs end at their intentional old-pin mismatch; elapsed sweep times were 1886.714, 1832.656, 1492.191 and 1464.563 seconds, all below 45 minutes. This capture is not strict green verification.

**Run — new counts:** `LEDGER-CAPTURE.json` pins capture hashes and the resulting compact ledger hash. The 858,685-byte ledger has 1,697 groups and 1,648,920 exact keys: 44,857 stage 2, 1,604,063 stage 3. Against the original 675,562-key full list, there are 1,012,928 additions, 39,570 removals and 544,176 changed retained deltas/tags. The added envelope/status/audit/lifecycle/handle/qualification checks explain the expansion; corrected background warnings and late binding remove or change earlier incorrect deltas. The stage-2 increase is the added `qualification-probes-restart/R2.context-before-command` focused assertion; no production context changed. `KNOWN-GAPS.md` contains the per-suite stage counts and regenerate/diff commands. Full-entry validation still checks nonempty deltas, valid rows/stages and unique page positions before hashing; conversion of the old full list remains byte-identical to `LEDGER-CONVERSION.json`. There is no committed full-list replacement.

**Run — final source local checks before strict push:** 66 oracle self-tests pass (`Ran 66 tests`, `OK`), including the compact-packer validation mutations; seven focused contract/regression tests pass. Generator prints `Generated artifacts match definitions`; `git diff --check` is silent. Strict Linux repetitions on this pin follow below. No stage review was run; the lead owns the fresh review.


**Run — repeatability failure and correction:** first strict Mail [42662867171](https://github.com/Ares-Empire/AresOS/actions/runs/42662867171), attempt 1, source `92f587de`, passed the 316-test suite and inherited sweeps, but every owner worker rejected changed export audit deltas. Exact comparison of both complete Linux captures found only random caller `TemporaryDirectory` components in the newly checked full audit `folder` and saved `path` fields. Keys, counts, rows, stages, calls and pages did not change. Base [42662867363](https://github.com/Ares-Empire/AresOS/actions/runs/42662867363) (209 tests) and boundary [42662849614](https://github.com/Ares-Empire/AresOS/actions/runs/42662849614) passed twice at that source; those superseded runs are not final-source acceptance evidence.

**Read / run — fixture input correction:** the owner scenario now gives caller directories injective names from flow/mode/primary/cleanup/live-or-crash, with the original `tmp` plus eight-character width. This preserves serialized record lengths and component counts. `flock` isolates identical shared clean and repeatability cases until fixture cleanup. Production temporary files and inherited-sweep inputs are unchanged. The actual audit comparison and gap checker still compare full literal paths; no fields are removed or normalized during comparison. A wrong-folder mutation still fails. The added real export repeatability test checks both raw fault traces and exact gap entries across two fresh scenarios.

**Run — complete replay proof:** `caller_capture.py` replays only the declared caller-directory input in the old full captures; it rejects inconsistent targets within one script. `CALLER-REPLAY.json` records that all 17 artifacts from the two independent Linux runs agree exactly after this input replay, including every row/stage/call/missing/extra/page. Only 2,380 assertions carry the changed path input. The compact pin retains 1,648,920 keys, stage counts 44,857 / 1,604,063 and 1,697 groups / 858,685 bytes. No assertion key, count or check was removed. Regenerate the historical replay under `.work/` with:

```sh
PYTHONPATH=control python3 -m owner_state_oracle.caller_capture .work/19b-fixes/capture/*/owner-gaps-*.json.gz --output-dir .work/19b-fixes/stable-capture
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-fixes/stable-capture/*/owner-gaps-*.json.gz --output .work/19b-fixes/replayed-compact.json
diff -u reviews/19b-owner-state/KNOWN-GAPS.json .work/19b-fixes/replayed-compact.json
```

**Run — local after fixture correction:** 68 oracle self-tests (`Ran 68 tests`, `OK`), seven focused contract/regression tests plus real export repeatability (`Ran 8 tests`, `OK`); generator `Generated artifacts match definitions`; diff check silent. The AST import check includes the conversion and fixture-input helpers as well as `gaps.py`, and all their imports remain standard-library/test-helper only. Final Linux strict repetitions on the deterministic caller input follow below.


**Run — final strict repetitions:** all three workflows passed twice on source `25dfdd63714bf80ef55ec4b106eac359f344a82b` with the same compact ledger. The closing commit changes review documents only; no test code, production code or ledger data changed after these runs.

| Workflow | Run / attempts | Exact evidence |
| --- | --- | --- |
| Control base | [42669403736 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42669403736/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42669403736/attempts/2), both success | Attempt 1 `results.txt:340`: `Ran 211 tests in 230.664s`; line 349 `Control base suite PASS`; Attempt 2 `results.txt:340`: `Ran 211 tests in 164.283s`; line 349 `Control base suite PASS` |
| Control mail | [42669403515 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42669403515/attempts/1), [attempt 3](https://github.com/Ares-Empire/AresOS/actions/runs/42669403515/attempts/3), both success | Attempt 1 `mail.txt:361`: `Ran 316 tests in 818.286s`; line 365 `Control Mail suite PASS`; shared `base.txt:332`: 211 tests, `OK`; isolated fixtures PASS; Attempt 3 `mail.txt:361`: `Ran 316 tests in 803.435s`; line 365 `Control Mail suite PASS`; shared `base.txt:332`: 211 tests, `OK`; isolated fixtures PASS |
| Control boundary | [42669647155 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42669647155/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42669647155/attempts/2), both success | Attempt 1: `present-console.txt:808`, `absent-console.txt:715`; identity line 1 matches source; Attempt 2: `present-console.txt:808`, `absent-console.txt:715`; identity line 1 matches source |

| Mail sweep shard | First strict pass | Second strict pass |
| --- | --- | --- |
| 0 | 31m 38s; `OK` lines 259/418/538/654; strict counts 127957/143732/142578; all three workers exit 0 | 24m 17s; `OK` lines 259/418/538/654; strict counts 127957/143732/142578; all three workers exit 0 |
| 1 | 23m 02s; `OK` lines 250/373/477/589; strict counts 127011/141020/131414; all three workers exit 0 | 30m 21s; `OK` lines 250/373/477/589; strict counts 127011/141020/131414; all three workers exit 0 |
| 2 | 24m 40s; `OK` lines 20/123/239/363; strict counts 148684/132511/133555; all three workers exit 0 | 29m 12s; `OK` lines 20/123/239/363; strict counts 148684/132511/133555; all three workers exit 0 |
| 3 | 27m 52s; `OK` lines 20/163/305/397; strict counts 139583/148063/133037; all three workers exit 0 | 23m 23s; `OK` lines 20/163/305/397; strict counts 139583/148063/133037; all three workers exit 0 |

**Run — Mail startup:** attempt 2 of run 42669403515 failed before creating any jobs (`total_count=0`); no test ran. The CLI reported a likely workflow-file issue, without further diagnostics. Rerunning the unchanged workflow at the same source started all five jobs on attempt 3. Final Mail repetitions are attempts 1 and 3, not the jobless attempt 2.

**Run — runtime and completeness:** every one of the ten Mail jobs finished below 45 minutes; maximum 31m 38s, from job startedAt/completedAt. Each shard retained four inherited tests, three independent owner workers, all 32 flows and every storage mode, cleanup pair, immediate crash and restored-space case. Every owned compact group and shared clean group matched exactly. No captures or expected exceptions substitute for these strict passes.

**Run — workflow count:** this fix round added 12 distinct workflow IDs / 18 attempts. Whole stage-1 branch total: 52 IDs / 61 attempts, including superseded and cancelled diagnostics. D1 relaxed the approximate 25-run target. The initial Mail capture was cancelled when the qualification recorder was corrected; strict Mail 42662867171 then exposed caller-path drift, fixed by deterministic fixture inputs; completed capture `42657094358` deliberately failed only at the old pin. Neither is final green evidence.

**Read — closing scope:** L1 and all nine review findings are implemented and tested. No production code or public tool/approval behavior changed in this fix round. No tests were removed, skipped or weakened; the old full-entry page validation moved into the compact packer. D3 is recorded as the exact stage-3 oracle contract, with production work deferred. Stage 2 was not started, no stage review was run, and PR #26 remains a draft against `pkg/19-mail`. The lead owns the fresh review.


**Run — closing workspace:** `.work/` inventory after final artifact download found no file over 500 MB (`[]`). No system software was installed, no owner Minecraft/client data was accessed, and no Gradle daemon was started. The closing push uses `[skip ci]` because its diff from the twice-tested source contains only REPORT.md and KNOWN-GAPS.md; the test code, production code and compact ledger are byte-for-byte unchanged.

## Stage 1, fixes round 2

**Read — scope:** implements `briefs/19b-s1-fixes-2.md` and all four findings of `REVIEW-S1-2.md`. Changes are confined to the independent oracle, its driver/fixtures, tests and review evidence. Production, public tools and approval inputs are unchanged. Stage 2 has not started.

**Read — finding 1 / obligation rule:** `Oracle.lifecycle` replays the validated reservation-to-expiry/cancellation transition into a separate operation-notice obligation. `notice=False`, later flag changes, archive removal and older restored rows cannot discharge it. Only the matching scripted acknowledgement with a committed transition does. `StageOneRoundTwo.test_expiry_notice_false_cannot_erase_obligation`, `test_archive_cannot_remove_unacknowledged_expiry_including_first_read`, `test_only_matching_committed_ack_ends_expiry_obligation` and `test_expiry_obligation_survives_restore_and_restart` cover both reported mutations and the positive acknowledgement path. Recovery, open checks and warning occurrences retain their separate lifetimes; terminal operation claims, intent/export removals, incomplete-account removal and metadata changes receive independent proof checks too.

**Read — finding 2:** the scripted delete mode selects the Trash role; the independent pre-command role map supplies its unique destination. A context/MOVE pair targeting `Other` fails both script comparisons. Flag commands must belong to the complete nonempty add/remove plan from the script; a separate completeness check detects an omitted branch even if every attempted command is internally coherent. `test_coherent_wrong_delete_destination_violates_script`, `test_empty_removal_cannot_replace_requested_flag_addition` and `test_complete_flag_plan_requires_both_nonempty_branches` cover wrong and permitted commands. Interrupted batches retain the existing fault/refused-reply exception to completion, never permission for an extra command.

**Read — finding 3:** response capture no longer tests whether the response contains `pending`. Public calls, including the special `mail_account_add` request method, queue their own original response even when the entire envelope is missing. `compare_envelope` asserts the envelope's presence even for an empty catalogue. Only four explicitly named Scenario-generated results (`expiry`, `maintenance`, `restart_index`, `restart_tail`) are excluded. `test_missing_original_onboarding_error_envelope_is_compared` removes the original onboarding error envelope with a live warning; `test_missing_envelope_fails_even_when_quiet_and_synthetic_results_are_named` covers the quiet and synthetic cases. Later healthy reads cannot replace the frozen original comparison.

**Read — finding 4:** probe results are correlated with the onboarding call, exact probe folder/UID, delivered command replies, command-before-commit sequence and fault positions. An earlier handled fault cannot explain a later false result. A successful delivered EXPUNGE/empty DELETE with no later fault derives success even if production commits `failed`, and also creates a lifecycle-proof discrepancy. Qualification retains its original result through later expiry/archive/restart and changes only for the exact scripted account-setting commit. `test_coherent_false_cleanup_state_and_public_reason_are_rejected`, `test_empty_probe_false_failure_and_wrong_commit_order_are_rejected` and `test_probe_failure_needs_a_later_fault_or_failed_reply` cover coherent false state/disclosure, ordering, real refusal and fault placement. The preexisting negative-reason test now supplies an actual rejected command when testing failed cleanup; changing a stored state alone is the new breaking mutation.

**Read — field audit conventions:** the table below covers all production-origin reads in the five expectation modules. Fields read together at the listed sites share a row; nested paths are explicit. Script arguments, raw fixture/server observations and fault traces are independent inputs, not production claims. Decoder bookkeeping (`events`, `rows`, `committed`, `prepared`, `fences`, `working_sequences`, `locked`, `generation`) is expanded below rather than treated as an authority by name. Fixture history before `Driver.seed_sequence` is the scenario's starting state; new outcome/stage validation begins at that boundary. Existing acknowledgement, expiry, check-close and removal checks still replay history. Opaque IDs bind identities; they never decide whether an obligation exists. Comparison-only reads transform the actual public value and cannot select the expected obligation.

| Field(s) read | Where read | Independent validation / comparison-only use | Self-test (in `test_owner_state_oracle.py` unless specified) |
| --- | --- | --- | --- |
| Journal `format`, `seq`, `previous`, `hash`; commit `commit`, `hash`; unterminated line | `records.decode` | Documented formats, canonical SHA-256 chain, consecutive sequence, exact matching commit; torn final line only is ignored | `test_decoder_distinguishes_prepared_and_committed_without_kv`, `test_decoder_rejects_corruption_but_ignores_torn_tail`, `test_decoder_rejects_unsupported_format` |
| Working event `seq`, `record`, `time`; compact operation `id`, `generation`, `input_hash`, `state` | `records.decode.valid_event`, including archived events | Event/fence equality, timestamp equality and full operation/compact-fence equality; prepared rows never count as committed results | `test_decoder_validates_event_time_and_full_operation_against_fence`, `test_unprepared_fence_is_distinct_from_a_replayable_prepared_event` |
| `archive:*` presence, manifest `path`, `sha256`; archive `event`, nested manifests | `records.decode` | Discover only from committed events, verify literal bytes against committed hash, recursively verify each event's fence/commit; never discover via directory listing | `test_decoder_follows_hash_valid_archived_manifests_recursively` |
| Presence/absence of historical events; SQLite head `seq`, `hash`; `working_sequences` | `records.decode`; `compare.source_order`, audit selection | Missing history at a current head fails unless explicit restore history explains it; older head is restore evidence. Every current-day working audit event must appear on the public pages | `test_decoder_missing_history_cannot_be_justified_by_current_head`, `test_working_check_closed_without_committed_result_cannot_change_expectations`, `test_audit_checks_identity_explanation_evidence_and_marking` |
| `generation`, `restore_pending`; decoded `locked`, unmatched/prepared fences | `records.decode`; `model.lifecycle`, `expected`, `request_state`, `permitted_status`, `holds`; `compare.notice_head` | Head/fence/commit mismatch is independent lock evidence. A changed generation/pending marker needs the scripted committed restore (initial generation excepted). Invalid markers produce lifecycle differences; cannot justify themselves | `test_forged_restore_archive_and_notice_metadata_are_detected`, `test_cached_refusal_mutation_uses_script_and_committed_transaction_state`; focused `restore-before/after-*` contracts |
| `archived:ID` presence and `seq` | `model.lifecycle`, `expected` | Require matching archive action/sequence and operation tombstone in that same commit. Tombstones cannot discharge live notice/check/work obligations | `test_archive_cannot_remove_unresolved_reservation`, `test_archive_cannot_remove_unacknowledged_expiry_including_first_read`, `test_forged_restore_archive_and_notice_metadata_are_detected` |
| Source/operation/notice row presence or deletion | `model.lifecycle`, `expected`, `holds`, `bind_occurrences`; `context.bind`; `local.errors` | Replay committed history; preserve unresolved work/open checks/unacknowledged occurrences through removal/restore. Only a scripted supported completion or matching committed acknowledgement resolves it. Missing pre-command rows fail R2 | `test_open_account_and_filing_obligations_survive_row_removal`, `test_mutated_committed_context_and_unproved_resolution_do_not_end_work`, `test_r2_command_before_context_is_caught`, `test_missing_search_and_lost_working_row_do_not_erase_registered_duplicate_expectation` |
| Operation `id`, `app`, `action`, `payload`, `approval`, `expires`, `repair_of` | `model.lifecycle`, `expected`, `completion_errors`, `holds`, `public_handle`; `context.bind/decode/permitted/script_differences` | Key/ID agreement; immutable preparation context across updates; script/approval/command comparisons validate selected app/action, recipients and targets. IDs are opaque bindings, not evidence of completion | `test_mutated_committed_context_and_unproved_resolution_do_not_end_work`, `test_exact_context_cannot_be_supplied_by_another_attempt_or_changed_fields`, `test_repair_context_binding_handles_both_opaque_id_orders` |
| Operation `state`, `reason` | `model.lifecycle`, `expected`, `resolution_proof`, `completion_errors`, `holds`; `context.bind`; `local.errors` | Finite states; post-seed terminal transitions require correlated effects/refusals/faults or explicit local effect/repair evidence. Reserved expiry requires the scripted clock; cancellation requires its exact call/commit. Public state/reason is then compared exactly (documented restored-reason family only) | `test_bad_completion_without_server_acceptance_is_caught`, `test_mutated_committed_context_and_unproved_resolution_do_not_end_work`, expiry/ack tests above |
| Operation `notice`, `ack` | `model.lifecycle`, `expected` | Expiry/cancellation obligation is independent of `notice`; a matching scripted committed ack ends it. A flag flip is a discrepancy and does not change the obligation | `test_expiry_notice_false_cannot_erase_obligation`, `test_only_matching_committed_ack_ends_expiry_obligation`, `test_spontaneous_ack_cannot_erase_warning` |
| `sent_copy_check.state`, `.clean`; `warning_checks.*.warning`, `.fingerprint` | `model.expected`, `warning`, `lifecycle`, `clean_proof`, `result_proof` | Result commit must follow the correlated raw SENT/LIST/scan evidence in that call. Clean epochs require independent clean evidence. Ack never closes a check; missing result retains the open obligation | `test_scripted_ack_cannot_close_unfinished_check`, `test_false_production_clean_cannot_resurrect_acknowledged_same_evidence`, `test_special_rename_role_cannot_supply_clean_proof`, `test_round27_check_closed_without_committed_result_is_caught` |
| Filing/rename `state`, `check_open` | `model.lifecycle`, `expected`, `warning`; `context.bind`; `compare.retained_role` | Initial started context opens recovery; closing requires correlated LIST/scan plus a later result commit. Observed raw role drift warns even when a new row claims done/closed | `test_raw_trash_list_warns_even_if_production_claims_done_and_closed`, `test_scripted_ack_cannot_close_unfinished_check`, `test_open_account_and_filing_obligations_survive_row_removal` |
| Notice `id`, `ack`, `source_key`, `check_kind`, `evidence_fingerprint` | `model.lifecycle`, `bind_occurrences`; `compare.notice_facts`, `notice_identity`, `retained_role` | Exact script/commit validates acknowledgement. Raw evidence selects semantic source/kind/fingerprint, disk only binds the public handle. Changing/deleting a row cannot remove detected facts. Existing-format notices lacking fingerprints can bind an opaque handle, but public semantics and stable identity still compare to raw evidence | `test_occurrence_binding_matches_evidence_not_last_unused_notice`, `test_unbound_semantic_occurrence_binds_after_persistence_and_acks`, `test_recovery_handle_is_checked_on_pages_reads_and_ack`, `test_forged_restore_archive_and_notice_metadata_are_detected` |
| Notice `created_at`; first source event `time`, `seq` | `model.lifecycle`; `compare.source_order`, `ordered_pending`, `ordered_notices` | Timestamp must fall inside the recorded creating call/commit; later notice metadata is immutable. Stable ordering uses validated creation time and public ID, never set iteration. Legacy synthetic fixtures without timestamps use source order | `test_forged_restore_archive_and_notice_metadata_are_detected`, `test_notice_order_uses_distinct_public_ids_even_when_source_time_ties`, `test_synthetic_notice_id_formats_and_saved_creation_order` |
| Filing/rename `id`, `account`, `verb`, `source`, `target`, `sources`, `roles_before`, `message_count` | `context.bind/decode`, `model.warning`, `expected`, `locations` | Bind only the current call/created identity. Independently compare scripted folder/reference/account and raw command/role map. Folder/count/role disclosure derives from that bound context and raw evidence and is checked separately from handle binding | `test_matching_context_and_command_cannot_change_script_uid`, `test_coherent_wrong_delete_destination_violates_script`, `test_public_notice_must_expose_exact_context_not_only_opaque_id_and_role` |
| Filing `records[*].source`, `.sha256`, `.destination`; decoded location/context rows | `model.locations`, warning folder summaries | Scripted source identities are checked by R2; raw fixture bytes/UIDs select actual matching locations and COPYUID selects the last-known destination. Missing source context is an R2 failure; every disclosed location/fragment compares independently with raw mailbox contents | `test_public_notice_must_expose_exact_context_not_only_opaque_id_and_role`; focused `scan-incomplete`, review-22 evidence and filing contracts |
| `context.command`, `.account`, `.roles`, `.delimiters`, `.identities`, `.source`, `.destination`, `.flags`, `.append_flags`, `.recipients`, `.sha256`, `.body`, `.arguments`, `.operation_id` | `context.bind`, `decode`, `required`, `differences`, `script_differences`; `model.require_context` | Three separate comparisons: script authority, committed-before context, raw command. Exact identities/recipients/folders/flags/POST body/hash/role roots and repair stage; matching context/command alone is insufficient. Flag plan completeness checks both requested branches | `test_coherent_wrong_delete_destination_violates_script`, `test_empty_removal_cannot_replace_requested_flag_addition`, `test_complete_flag_plan_requires_both_nonempty_branches`, `test_post_context_binds_exact_url_body_source_and_current_operation`, `test_coherent_wrong_append_flags_are_not_authorized` |
| `payload.mode`, `.items[*].reference`, `.folder`, `.method`, `.reference`, `.target`, `.body`, `.account`, `.to/.cc/.bcc`; `payload.composition.mail.{account,from,to,cc,bcc,answered_reference}` | `context.decode/permitted/script_differences`; `model.expected`, `completion_errors`, `stage_claims` | Script/approval supplies authority; raw commands/receipts supply effects. Delete mode independently chooses Trash/permanent commands; message ID derives from scripted operation ID; exact recipient envelope must be accepted once | `test_trash_delete_context_does_not_authorize_expunge_before_crash`, `test_coherent_wrong_delete_destination_violates_script`, `test_coherent_wrong_send_message_identity_is_not_authorized`, `test_bad_completion_without_server_acceptance_is_caught` |
| `stages.wire_sha256`, `.sent_wire_sha256` | `context.decode` | Commitment supplies a claimed local wire hash only; the pre-command comparison requires equality with the independently hashed actual transmitted bytes. It grants no resolution/notice permission | `test_exact_context_cannot_be_supplied_by_another_attempt_or_changed_fields`, `test_coherent_wrong_send_message_identity_is_not_authorized` |
| `stages.message_id`, `.smtp_data`, `rcpt:*`, `recipient:*`, `.sent_copy`, `.answered_flag`, `.folder_probe`, `.folder`, `target:*`, `.https_post` | `model.stage_claims`, `completion_errors`, `probe_outcome`; repair validation | Changed positive claims need exact correlated delivered DATA/RCPT/RECEIVE/APPEND/STORE/DELETE/EXPUNGE/POST or read-only Sent/local-stage evidence before the commit. Probe failure claims also need an actual refusal/lost reply or a later injected fault | `test_stage_outcome_needs_correlated_delivered_command`, `test_coherent_false_cleanup_state_and_public_reason_are_rejected`, `test_probe_failure_needs_a_later_fault_or_failed_reply`; clean-flow and repair/settlement contracts |
| Other stage detail (`attempting`, hashes, warnings, absent/not-attempted/failed local detail), `repair_of`, `payload.stage` | `context.decode/script_differences`; full operation-status comparison in driver | Nonpositive stage detail cannot resolve a warning/check by itself. Repair authority is exact scripted parent/stage; successful completion still requires independent effects. Full public stage/approval/state equality is an additional comparison, not a source of qualification expectations | `test_repair_context_binding_handles_both_opaque_id_orders`, `test_coherent_false_cleanup_state_and_public_reason_are_rejected`, focused repair/settlement and operation-status sweep assertions |
| Account `id`, `onboarded`, `ready` and row presence | `model.lifecycle`, `expected`, `qualification` | Incomplete account recovery cannot be removed. A post-seed completion flag needs that account's scripted onboarding commit and delivered self-probe DATA; qualification is independently derived and retained even if the account row later changes/disappears | `test_open_account_and_filing_obligations_survive_row_removal`, `test_completed_qualification_comes_from_probe_evidence` |
| Account `special`, `roots`, `optional`, `delimiter`, `protected_special`; nested root `folder`, `delimiter` | `context.special_roles/special_delimiters/decode`; `model.expected`; `local.protected_roots/errors` | Roles are checked against raw LIST and script; folder-review hash must match exact role fields. Old/current protected Trash/Drafts roots are unioned independently, unrelated roots unchanged. Duplicate/unresolved roles cannot authorize a target | `test_role_review_keeps_historical_and_old_and_current_protected_roots`, `test_local_settings_and_role_review_require_exact_current_arguments`, `test_coherent_wrong_delete_destination_violates_script` |
| Account `sent_policy`, `safe_folder_delete`, `folder_delete_reason`, `ready`; account-setting `format`, `signature` | `model.qualification`, `qualification_facts`; `local.errors` | Expected readiness/policy/reason derives from correlated bounded probe logs and validated results, not account flags. A later policy change needs the exact account's scripted committed settings. Actual public reason is normalized only to documented semantic families | `test_completed_qualification_comes_from_probe_evidence`, `test_qualification_distinguishes_each_negative_probe_reason`, `test_coherent_false_cleanup_state_and_public_reason_are_rejected`, `test_local_settings_and_role_review_require_exact_current_arguments` |
| Probe operation `action`, `payload.folder/empty/items`, `state`; account-completion event `action`, `outcome`, `seq` | `model.qualification`, `probe_qualification`, `probe_outcome` | Exact onboarding correlation/account/probe identities and result order; delivered raw replies and later fault positions validate each committed outcome. Missing result with a command is a proof discrepancy, not evidence for a false reason | `test_empty_probe_false_failure_and_wrong_commit_order_are_rejected`, `test_probe_failure_needs_a_later_fault_or_failed_reply`, `test_coherent_false_cleanup_state_and_public_reason_are_rejected` |
| Test-app rows `items`, `epoch`; item `id`, `revision`, `sender`, `subject`, `date`; operation `payload.items`, `approval`, `state` | `local.errors`; `model.completion_errors`, `resolution_proof` | Scripted exact references and named metadata must match initial items; only approved targets may disappear; survivors and all unrelated data must match exactly. Final completion requires every approved removal and its actual committed local effect | `test_local_delete_requires_prior_context_even_before_terminal_outcome`, `test_local_delete_rejects_extra_target_wrong_reference_and_changed_survivor`, `test_local_delete_allows_batches_and_prepared_effects_with_prior_context` |
| Generic intent `id`, `app`, `action`, `state`, `context`; creation sequence/time | `context.bind`; `local.errors`; `model.lifecycle`, `intent_result_proof`, `public_handle` | Current script/call interval and committed-before ordering bind it. Completion needs delivered correlated commands or that call's actual local settings/role/export effect; acknowledgement is separate and exact. Removing the row alone cannot resolve it | `test_exact_context_cannot_be_supplied_by_another_attempt_or_changed_fields`, `test_local_settings_and_role_review_require_exact_current_arguments`, `test_open_account_and_filing_obligations_survive_row_removal`; legacy-intent contracts |
| Export row `app`, `sha256`, `size`; row presence/removal; `saved` request `export_id`, `app`, `outcome` | `model.holds`, `lifecycle`, `intent_result_proof`, `export_result_proof`; driver publication comparison | Fixture source bytes independently supply hash/length. Release needs the matching scripted saved request/committed result, or a correlated injected refusal. Actual caller bytes and reported publication hash compare separately; a missing result retains recovery and hold | `test_export_repeated_fault_uses_same_caller_path_and_exact_delta` (Mail); export/publication/rollback sweep cases |
| Event `action`, `outcome`, `operation_id`, `summary`, `untrusted_content`, `seq`, `time`; historical filing `id/state/sources/records/locations/references` | `compare.audit_fact`, audit paging | Decoder supplies committed facts; script/effect checks above validate fields used for obligations. Audit transformation is the documented public untrusted projection and compares every explanation/reference, including literal paths; no audit value authorizes a resolution | `test_audit_checks_identity_explanation_evidence_and_marking`, `test_caller_capture_conversion_keeps_wrong_targets_distinguishable` |
| Reply `ok`, `error.code`; `data` absence; `pending` presence | `compare.compare_status/pages/compare_envelope`; `model.qualification_facts`; driver capture | Read status is allowed only by independent current faults/admission/transaction/restore/transport evidence, even when empty. Original envelope presence is required from scripted request type. Error scope can widen expected pending membership; it never removes a warning or narrows the independently derived obligation set | `test_empty_healthy_catalogue_cannot_refuse_itself`, `test_missing_original_onboarding_error_envelope_is_compared`, `test_missing_envelope_fails_even_when_quiet_and_synthetic_results_are_named` |
| Public pending `items[*].operation_id/state/reason`, `total`, `cursor`, `restore_required` | `compare.pending_facts`, `compare_envelope`, `notice_head`, `compare_views` | Actual-only transformation; equality with independently replayed pending obligations, counts, head/continuation and restore evidence; cursor must advance and traversal is bounded | `test_wrong_passive_page_is_not_masked_by_healthy_pending_view`, `test_pages_drain_and_cannot_loop`, expiry mutation tests |
| Public notices `operation_id`, `app`, `state`; content `intent_key`, `operation_id`, `check`, `recovery_warning`, `check_open`, `filing_id`, `message_count`, `reason`, `folders`, `folders_more`, `folders_more_text`, `unresolved_roles`, `scan_complete` | `compare.notice_facts`, `retained_role` | Actual-only semantic transformation; full equality with independent source/occurrence, count/role, context and public handles. Flags in the reply cannot close expected checks. D3's alternative requires the exact committed generic evidence warning while its check stays open | `test_public_notice_must_expose_exact_context_not_only_opaque_id_and_role`, `test_recovery_handle_is_checked_on_pages_reads_and_ack`, `test_D3_generic_warning_requires_committed_evidence_and_open_check` |
| Page `items`, `notices`, `total`, `cursor`, `page_changed`, `notices_more.count/action`; qualification `data.accounts/account`, onboarding `data.notice` | `compare.pages/notice_head/compare_views`; `model.qualification_facts`; driver | Actual-only: exact heads/pages/complete union, counts, duplicate checks and advertised continuation. Restarts are bounded and cannot hide a missing final item. Qualification/caveat equality uses the independent retained result | `test_pages_drain_and_cannot_loop`, `test_extras_and_each_view_fail_independently`, `test_completed_qualification_comes_from_probe_evidence`, focused review-21 paging contracts |

**Read — audit-driven fixture changes:** the archive fixture advances the controlled clock to age real commits, instead of editing committed event timestamps away from their independent fences. The inherited fixture retains its existing path when no clock hook is provided. Request start sequences come from the decoder outside faults; they never read the production journal iterator under injected failures. Raw commands also record their fault-boundary position so only later faults can justify a lost result. These are test-input/observation changes, not storage or production changes.

**Run — local:** 90 oracle self-tests pass. The focused diagnostic runs all seven contracts/named regressions plus real export repeatability and last-response proof tests (nine tests); it records new gaps under `.work/` without treating the superseded ledger as green. First-boundary single/persistent faults, live/restored space and crash/restart execute for all 32 flows. Generator and diff checks pass. Strict Linux capture and final repetition evidence are recorded below when complete.

**Read — audit completion:** onboarding command authority also fixes the scripted account and the independently created disposable probe folder/UID; an internally coherent context for another account or an unrelated folder fails (`test_onboarding_context_cannot_authorize_another_account_or_unrelated_folder`). Final lifecycle/clean/completion checks run after the last status/location response; the real-driver `test_last_status_committed_lie_is_in_same_comparisons_proof` commits a false stage during that last read and requires its proof failure in the same comparison. Capture attempts made before these finishing checks were cancelled and are not verification evidence.

**Read — probe fault interval:** independent snapshots record the earliest fault-boundary position by which each commit was observed. A fault after that observation cannot explain the earlier probe result (`test_fault_after_observed_probe_commit_cannot_justify_false_failure`). This closes the unrelated-later-fault variant as well as the reported no-fault false-state case.

**Read — app/action scope:** `test_false_app_flag_cannot_hide_a_scripted_mail_reservation` and `test_coherent_wrong_app_and_action_cannot_hide_scripted_reservation` validate app scope and initial operation action against the script, including the coherent pair mutation. Account keys also validate their stored identity. This final validation-only commit was held locally while the Linux capture finished. The capture source below precedes those guards; final strict runs execute them against the complete pin. No captured assertion is discarded to accommodate them.

**Run — complete Linux capture:** Mail [42687523943](https://github.com/Ares-Empire/AresOS/actions/runs/42687523943), attempt 1, source `72d3ac77375594f867f0127a7939388c63121159`; base [42687524469](https://github.com/Ares-Empire/AresOS/actions/runs/42687524469), attempt 1. Every shard log has 96 flow-completion records (all 32 flows in each of three workers), no runtime errors, an inherited four-test `OK` and exactly three final old-pin failures. Each worker ran six tests; only its final compact comparison failed. The suite ran 316 tests (`mail.txt:373`, 990.162s); only the final contract pin failed (`:361`, `:376`). All four suite lists match the final-code local focused diagnostic exactly, including full deltas. Base `results.txt:360` printed `Ran 231 tests in 201.546s`, `:369` printed `Control base suite PASS`; embedded suite base `base.txt:352` printed 231 tests in 227.496s and `:361` PASS. Mail job durations were 1625/1814/1927/1738 seconds for shards 1/2/3/0, and 1258 seconds for the suite, all below 45 minutes. This is capture evidence, not strict green acceptance.

**Run — compact pin:** `LEDGER-CAPTURE-R2.json` records all 17 artifact hashes, the capture source and compact hash. Merge validation requires all twelve owners, exact shared-key agreement, each nonshared key's correct owner and every dedicated suite. The new ledger has **1,629,889 exact keys**, **44,857 stage 2 / 1,585,032 stage 3**, in **1,716 groups / 868,337 bytes**. Against round 1: **48,348 additions, 67,379 removals, 1,320,217 changed retained deltas**. No full list is committed.

**Read / run — why counts changed:** required expiry/recovery/check/qualification obligations and final-response proofs add coverage. Retaining independently justified recovery through removal/restore also fixes prior false `unexpected extra` warnings: for example `delete_trash/persistent/237/0/crash-restart/aresos log.notice-count` previously expected 0 while production correctly disclosed 1. The recovery obligation now requires that notice, so the incorrect gap disappears; losing it would fail. Similar corrections affect export, onboarding and local-change recoveries. Archive is the sole flow whose discovered boundary count changes, 356 to 353: its fixture now advances the clock rather than rewriting timestamps, while still archiving real history and executing VACUUM. All other flows retain their discovered point counts. Exact envelope-presence facts also bind a new deterministic `response` alias before subsequent comparisons, changing many literal deltas; no fields are removed or normalized. These are oracle/fixture corrections, not production gap closures. Every assertion still executes and every remaining delta is hashed in full. The focused contract capture adds eight keys, removes none and changes 278 retained deltas.

**Run — local on the new pin:** 90 oracle self-tests (`Ran 90 tests`, `OK`), nine strict focused/real-driver tests (`Ran 9 tests`, `OK`), generator `Generated artifacts match definitions`, silent `git diff --check`. The final two app/action tests are included. The full Linux strict repetitions follow below.


**Run — final strict repetitions:** Control base, Control Mail and Control boundary each passed attempts **1 and 2** on `24706dafee41ec8473d71a54aa4c09e434b4e802`, with the same compact ledger and the final app/action guards. No final-source strict test failed. The closing commit adds review evidence only; code, tests and ledger bytes remain identical to this twice-tested source.

| Workflow | Runs / attempts | Exact evidence |
| --- | --- | --- |
| Control base | [42693447617 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42693447617/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42693447617/attempts/2), success | Both `results.txt:362`: 233 tests; 157.894s / 177.755s. Both `:371`: `Control base suite PASS` |
| Control Mail | [42693447616 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42693447616/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42693447616/attempts/2), all five jobs success each time | Both suite `mail.txt:361`: 316 tests; 829.970s / 1000.417s. Both `:365`: `Control Mail suite PASS`. Embedded `base.txt:354`: 233 tests; 189.046s / 230.125s; `:363` PASS. Both `isolation.txt:1` PASS |
| Control boundary | [42693452764 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42693452764/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42693452764/attempts/2), success | Both `present-console.txt:808`, `absent-console.txt:715`: `SETTINGS_OK mcp_exclusive marketplace_lock sideload_flags`; both `identity.txt:1` identify the tested source and correct attempt |

**Run — Mail completeness and runtime:** every sweep job has 96 flow-completion records: all 32 flows in each of its three isolated workers. Every worker ran six tests and exited 0; every inherited four-test sweep printed `OK`. Single faults, persistent exhaustion, cleanup pairs, immediate crash/restart and restored-space cases all execute. Every owned group and the shared clean groups match exactly in both repetitions. The four `OK` line numbers below are the inherited suite and three workers, in that shard's `mail.txt`; line numbers and pinned worker counts agree in both attempts.

| Mail shard | Attempt 1 job duration | Attempt 2 job duration | `OK` lines (both) | Pinned keys, workers 0 / 1 / 2 (both) |
| --- | --- | --- | --- | --- |
| 0 | 36m 11s | 34m 15s | 259/419/540/657 | 126908/140981/140661 |
| 1 | 32m 35s | 21m 49s | 250/374/479/592 | 126014/138504/129970 |
| 2 | 26m 12s | 26m 53s | 20/124/241/366 | 146750/132221/131040 |
| 3 | 30m 46s | 22m 52s | 20/164/307/400 | 137098/146190/133769 |

The two suite jobs took 17m 47s / 21m 11s. All **ten Mail jobs** finished below 45 minutes; maximum **36m 11s**. Durations use job startedAt/completedAt, including setup and artifact upload, not just a selected test timer.

**Run — independent full-pin proof:** each strict repetition's complete 17 actual lists was merged and repacked independently after download. Both reproduce **1,629,889 keys / 1,716 groups / 868,337 bytes** and SHA-256 `c6d26c983ca808bca1597cdcb48d4dbe2b41a7a3b2ad932a66667d7c726b9f98` byte-for-byte. `LEDGER-STRICT-R2.json` pins the tested source, both repetitions and all 34 artifact hashes. This directly verifies the final guards against the entire ledger, including the validation-only commit held after the earlier capture. No capture or permitted old-pin mismatch substitutes for these strict passes.

**Run — exact local commands on the new pin:**

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control .work/venv/bin/python -m unittest discover -s control/tests -p test_owner_state_oracle.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests .work/venv/bin/python .work/run-owner-tests.py test_owner_state_contracts test_owner_state_regressions test_owner_state_sweep.OwnerStateSweep.test_export_repeated_fault_uses_same_caller_path_and_exact_delta test_owner_state_sweep.OwnerStateSweep.test_last_status_committed_lie_is_in_same_comparisons_proof
python3 control/generate.py --check
git diff --check
```

Outputs: `Ran 90 tests in 0.240s`, `OK`; `Ran 9 tests in 4.491s`, `OK`; `Generated artifacts match definitions`; silent diff check. The local wrapper reads the repository's managed-policy templates in place of Linux-only installed paths; it is not installed-policy evidence. The Linux base and boundary runs above provide that verification. The first system-Python attempt lacked `jsonschema`; subsequent local checks used the existing worktree venv. No system software was installed.

**Run — workflow count:** this round used **11 distinct workflow IDs / 14 attempts**. The whole stage-1 branch is **63 IDs / 75 attempts**, from the Actions API. The three preliminary Mail runs (`42685627664`, `42685838753`, `42686319069`) were cancelled while finishing the audit; their successful base companions are superseded diagnostics. The complete old-pin capture (`42687523943`) is also not green acceptance. D1's relaxed run target applies. Final acceptance is exactly the three workflows and two attempts listed above.

**Read — closing scope / not verified:** all four review findings, the field audit and the obligation rule are implemented in test code and verified here. No production code, tool descriptions, public actions, approval bindings or acknowledgement permissions changed. No test was removed, skipped or weakened; failed-cleanup fixtures now provide an actual refused command and separately test the coherent false-state mutation. Stage 2 and stage 3 remain unbuilt, with their exact production gaps retained in the ledger. No real account, model or human-playing verification is claimed. No own stage review was run; the lead owns the fresh fix check. PR #26 remains a draft against `pkg/19-mail`; no merge was performed.

**JUDGMENT-CALL — read:** no new owner-visible product decision. Fixture clock ageing, explicit initial-state inputs and stricter decoder/proof checks are reversible test choices described in the audit; keeping the timestamp-rewrite fixture would contradict its independent fence and was rejected.

**PLAN-GAP — read:** no new design change in this round. D3's production evidence reservation and durable generic-warning fallback remain deferred to stage 3, as instructed.

**Open questions — read:** none for this fix round.

**Run — closing workspace:** the `.work/` regular-file inventory over 500 MiB printed `[]`. No large image or ISO was downloaded. No Gradle daemon was started. The closing push uses `[skip ci]` because only REPORT.md, KNOWN-GAPS.md and the strict evidence manifest differ from the twice-tested source; test code, production code and the compact ledger are unchanged.

## Stage 1, fixes round 3

**Done:** `model.py` and `resolutions.py` retain independently established
obligations behind one corroborated resolution allowlist; `records.py` bounds
restore/history authority; `driver.py` freezes script, fixture and pre-command
inputs. `compare.py` checks every public surface against those obligations.
`perturb.py`, the recorded-corpus test, focused contracts and direct self-tests
cover structure S and all five findings. The compact ledger, coverage contract,
field audit and capture/strict manifests are updated below.

**Read — scope:** this round implements structure S and all five findings of
`REVIEW-S1-3.md` in the oracle, comparison, tests and compact ledger. Production
code and the stage-2/3 work remain outside this round. The resolution contract
and executable table are documented in `control/owner_state_oracle/FORMAT.md`.

**Read — independent obligation derivation:** scripted approvals select every
required target, recipient, flag operation and destination. Server commands,
replies, raw pre-command byte hashes, role observations and the injected fault
trace establish effects and uncertainty. The decoder establishes which commits
occurred and their order. `Oracle.obligations` keeps source/kind/establishment
sequence separately from the current projection. `retain_obligations` requires
a corroborated allowlisted resolution before a kind can disappear, including
rollback to an older row that is still present. Occurrences, acknowledgements,
clean epochs, operation notices and qualification evidence remain separate.
The pre-fault fixture history is a frozen starting-state input; changes to it
are compared, rather than accepted as a new fixture. Pre-command decoded
observations also compare historical presence and content against the replay;
they cannot authorize a smaller effect plan.

**Read — resolution table:** `resolutions.RESOLUTIONS` is the single executable
allowlist. Each entry specifies both its independent proofs and the obligation
kinds it may discharge. The table in FORMAT.md lists acknowledgement,
submission, completion, failure, uncertainty, clean-check result, check result,
cancellation, expiry, settlement, restore, archive, onboarding completion,
intent completion and export publication. Missing kinds or missing proofs fail
closed. Restore and archive discharge no live obligation. Acknowledging an
occurrence cannot close its check, and completion cannot acknowledge warnings.
`test_resolution_table_fails_closed_for_every_missing_proof` removes every
required proof from every entry, and tests an unknown resolution kind.

| Review finding | Change | Direct test (in `control/tests/test_owner_state_oracle.py`) |
| --- | --- | --- |
| 1: initial payload narrows completion | `approved` reads the scripted approval; initial payload fields are compared and completion requires all approved effects, with exact identities and recipients | `test_initial_payload_and_completion_require_every_approved_target`: two approved targets, one payload target and one EXPUNGE |
| 2: unsupported transitions erase work | A total operation state machine gates transitions through the resolution allowlist; retained obligation kinds protect pending work, recovery and holds | `test_unallowlisted_state_edges_retain_reservation_and_recovery`: fault-free `reserved → refused` with `notice=False`, and `unknown → reserved`; `test_rollback_to_existing_reserved_row_does_not_erase_unknown_recovery` |
| 3: restore disables missing-history checks | Every restore explains only its bounded preceding interval; later missing sequences remain errors in decoder and model | `test_restore_cannot_explain_a_later_missing_sequence`; `test_decoder_restore_at_one_rejects_missing_later_intent` uses real SQLite and hash-valid independent commits `{1,2,3}`, a restore at 1, and missing intent sequence 2 |
| 4: incomplete account disappears | Account recovery is a retained obligation until allowlisted onboarding completion; row deletion and restore cannot release it | `test_incomplete_account_survives_rollback_restore_and_explicit_removal`; positive `test_onboarding_resolution_releases_only_corroborated_completion` |
| 5: filing hash justifies its own disclosure | Locations use exact source hashes captured before the originating command, rather than `records[*].sha256`; recorded hashes/destinations are compared | `test_false_filing_hash_cannot_justify_false_locations`: false hash still yields independently correct locations and a lifecycle difference |

**Read — updated complete field audit:** this table supersedes the round-2
validation column; its earlier tests remain in place. All public fields below
are actual values being compared, never independent authority.

| Production value / presence read | Reader | Independent derivation or comparison; tests |
| --- | --- | --- |
| Independent fence `format/seq/previous/hash`, commit markers, full event `record/time`, compact operation `id/generation/input_hash/state` | `records.decode/consistency_errors` | Hash-chain/commit equality, full/compact equality, exact sequence coverage and event order; decoder corruption, format, field and later-missing-intent tests |
| Working head, prepared/committed/unprepared sequences, generation, restore marker and `locked` | Decoder; `lifecycle`; `request_state/permitted_status`; comparison | Head and independent fences derive the lock; restore intervals end before their marker and require scripted confirmation; no marker explains a later omission. Record consistency and perturbation boolean/sequence/restore mutations |
| Event row presence, null tombstones, archived history and archive manifests/path/hash | Decoder; lifecycle replay; retained obligations | Qualified archive bytes and recursive events; every pre-command decoded observation is compared to its historical replay. Removal needs allowlisted intent/export/ack resolution; archive cannot discharge live work. Removal, archive, restore and systematic row-drop tests |
| Frozen initial fixture events and subsequent event order | `Driver` seed; lifecycle | Starting history is explicit input, frozen before the faulted call; modified seed events fail. Post-seed events need script/server/fault evidence. Systematic historical-version and sequence mutations |
| Operation `id/app/action`, approval, initial and later payload fields, expiry, repair parent | `approved/payload_claims/transition`; context/local validators | Opaque identity binds the script; full effects come from the scripted approval. Payload account, items, mode, folder, reference, target, method, recipients, sender, attachments and repair stage are compared. Initial target-omission, wrong app/action, UID/destination/flags and repair-binding tests |
| Operation `state/reason`, `notice/ack`, expiry/cancellation removal | Total transition gate; operation notices; retained obligations | Table-authorized state edges only. Faults/replies justify failure; script clock or cancellation creates a notice obligation independent of `notice`; exact committed acknowledgement releases it. Round-2 expiry tests and round-3 transition/rollback tests |
| Operation stage fields (`message_id`, wire hashes, SMTP/recipient result, Sent/answered stage, target hashes, DELETE probe/folder, POST status) | `stage_claims/completion_errors/probe_outcome` | Exact raw command identities, bytes, recipients, delivered replies, faults after the command and before observed commit, and full scripted effect plan. False stage/probe/cleanup and incomplete completion tests |
| Sent `sent_copy_check.state/clean/count`; warning checks `warning/fingerprint/occurrence_id`; check presence | `expected/lifecycle/warning/result_proof/clean_proof` | Raw Sent evidence selects warnings; a correlated `mail_sent_copy_check_open` establishes enrollment even with a false checked flag; only a correlated committed result closes a check; only a clean raw result advances an epoch. Positive opener, acknowledgement/clean/recurrence and systematic flag/state tests |
| Filing/rename `id/app/account/source/sources/target/verb`, records' sources/hashes/destinations, message count, roles/delimiters | `filing_claims/locations`; context validators | Scripted arguments select sources/target/account/verb; exact pre-command identities/byte hashes and COPYUID replies determine locations and known destinations; LIST determines role risk. Production values are compared. Coherent wrong-destination, false-hash and perturbation effect tests |
| Filing/rename `state/check_open`, warnings and removed rows | Lifecycle; open-check/occurrence registries | Raw role/location evidence plus a matching result commit discharge a check, independently of occurrence acknowledgement. Unsupported reopen/start/state changes fail. Incomplete scans, legacy checks, acknowledgement and systematic state/boolean/removal tests |
| Notice `id/source_key/check_kind/evidence_fingerprint/created_at/ack`, content and row presence | Lifecycle; semantic occurrence binding; comparison ordering | Independently detected evidence selects the occurrence; row supplies an opaque handle only. Binding, identity, immutable context, time bounds and scripted acknowledgement are checked; deletion never deletes the occurrence. Spontaneous ack, changing metadata, late binding and perturbation tests |
| Incomplete account `id/onboarded/ready`, presence or removal | Lifecycle; account obligation kind | Scripted account identity, onboarding commit and delivered probe corroboration; completion cannot be reversed or suppressed by a flag. Incomplete-account restore/deletion and positive-completion tests |
| Qualification `ready/sent_policy/safe_folder_delete/folder_delete_reason` and probe operation outcome | `qualification/probe_qualification/probe_outcome` | Readiness, Sent caveat and DELETE qualification come from raw correlated probes, replies and fault/commit intervals; committed state is compared before deriving the result. Settings changes require scripted committed settings. All qualification reason mutations remain |
| Generic intent `id/app/action/state/context`, presence/removal | Lifecycle; context/local validators; intent resolution gate | Current script/command identity and exact context; legacy/current handle binds once across history and rollback. Completion needs an ordered effect/reply, acknowledgement needs its exact scripted identity. Positive handle tests, historical removal comparison and systematic ID/row tests cover identity and absence |
| Account settings and protected-role fields (`format/signature/sent_policy/ready`, roots/delimiters, historical/current role union) | `local.errors/protected_roots` | Prior decoded context, exact script arguments and independent same-call LIST evidence; unchanged survivors compare exactly. Local settings/role-review and perturbation tests |
| Test-app item IDs, epoch/revision and item fields; receiver configuration | `local.errors`; command/context and completion checks | Prior submitting operation and exact scripted target set; only approved items may disappear, all approved targets must be gone for completion, and survivors stay unchanged. Receiver commands compare raw arguments. Existing local-delete/configuration tests |
| Export source hash/size/path/app, export row presence, publication/release and holds | Driver; export/intent gates; `holds` | Fixture bytes supply hash/size; matching scripted saved identity, committed publication or correlated refusal releases recovery/hold; caller bytes and reported publication compare separately. Export repeatability/rollback and systematic hold tests |
| Audit `seq/time/action/outcome/operation_id/summary/untrusted_content`, historical filing references | `compare.audit_fact` | Full documented public projection of decoded commits is compared; every field used to resolve obligations is separately validated above. Untrusted marking and literal caller paths remain exact. Existing audit/path mutations |
| Reply `ok/error.code`, missing `data` or `pending`, original action/error/continuation envelope presence | Response driver; status/envelope/page comparison | Scripted request selects required envelope; faults/admission/transaction/restore/transport evidence select permitted status even for an empty view. No returned refusal authorizes itself. Existing missing-envelope/healthy-refusal tests |
| Public pending IDs/state/reason, notice IDs/app/state/context/count/roles/recovery/check flags; pages/totals/cursors/restart/continuation and qualification disclosures | `compare` actual-only transforms and validated projection | Equality with retained independent facts on every surface/head/page; grouping uses the validated projection, including scripted acknowledgements and corrected app scope. Bound traversal/duplicates/counts/handles are compared separately. Existing per-view/page/handle/context tests and focused contracts |

**Read — systematic test:** `test_owner_state_perturb` records the full focused
contract set, all six named review-20/21/22 regressions, and sweep samples in
every mode. `perturb.mutations` enumerates every boolean/state/effect field and
every row/version/sequence, with both projection-only changes and coherent
history/projection changes. Restore markers are inserted before each sequence.
`perturb.check` compares the complete owner set, holds and qualification, and
requires a *new* difference for a changed set; a pre-existing production gap is
not sufficient. The deliberate broken-oracle test proves the assertion fires
and names its scenario and field. Executed counts and Linux evidence follow
when verification is complete.

**Read — additional class closures found by the systematic test:** an unsupported
Sent-check reopen, a finished filing changed to `started`, omission of an
observed historical intent, and a warning flag selecting a clean epoch now have
independent validation or derivation. Clean epochs use the latest correlated
raw result and a matching result commit (including the documented Sent-copy
stage), once per read/result pair. They are independent of warning/clean flags;
acknowledgement and unrelated commits cannot certify a clean result. The
approval comparator additionally covers body, subject, format, signature, reply
chain, generated parts, composition identity/hash, expiry and the recorded
approval/input hash. Unsubscribe compares both its outer source/target and its
inner mail composition. No production flag supplies its own justification.

**Read — fixture precision:** legacy/interrupted rows inserted after construction
are explicit `fixture_input` script arguments captured before their write. They
are compared to the corresponding commit; an arbitrary production event called
`fixture` is not an input. The existing positive recovery-handle test now states
its acknowledgement commit interval, and the positive archive test supplies its
script and qualified manifest. Their assertions are unchanged. These stricter
fixtures preserve the existing test purposes; no test was skipped or weakened.

**Read — local environment:** local commands use the existing worktree venv and
`.work/run-owner-tests.py`, whose only environment accommodation reads this
repo's managed-policy templates instead of Linux installed paths. Diagnostic
focused comparisons record the new full deltas under `.work/`; their old-pin
mismatch is not strict green verification. Installed-policy and container
verification comes from the Linux workflows below. No system software or
Gradle daemon was started.

**Run — initial local source checks:** 101 oracle self-tests passed (`Ran 101
tests in 0.251s`, `OK`). The focused/regression/real-driver/perturbation pass ran
10 tests in 124.444s and printed `OK`. Generator printed `Generated artifacts
match definitions`; `git diff --check` was silent. The first-boundary diagnostic
also executed all 32 flows in single/persistent modes and live/crash phases,
printing each flow and `Diagnostic assertions 927`; it is diagnostic coverage,
not a replacement for the full Linux sweep or strict ledger checks.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control .work/venv/bin/python -m unittest discover -s control/tests -p test_owner_state_oracle.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests .work/venv/bin/python .work/19b-round3/focused_capture.py test_owner_state_contracts test_owner_state_regressions test_owner_state_sweep.OwnerStateSweep.test_export_repeated_fault_uses_same_caller_path_and_exact_delta test_owner_state_sweep.OwnerStateSweep.test_last_status_committed_lie_is_in_same_comparisons_proof test_owner_state_perturb.SystematicPerturbations
python3 control/generate.py --check
git diff --check
```

**Run — initial systematic result (expanded below):** **66 recorded scenarios, 70,953 perturbations,
`slipped=0`**. The corpus contains all 52 focused contract states, seven recorded
states from all six named review regressions, and seven sweep snapshots (clean
send and repair, single fault, persistent exhaustion plus restored space,
crash/restart, and an actually reached cleanup pair). Frozen scripts/logs do not
acquire later scenario calls while the corpus is collected. Each check starts
with its own oracle copy; existing baseline defects cannot mask a new silent
change. The test reports the scenario and field on failure.

| Perturbation kind | Executed |
| --- | ---: |
| Every boolean, including decoded lock | 5,126 |
| Every state to all other states | 40,320 |
| Targets, recipients, flags, hashes, destinations and identities | 21,271 |
| Row / historical-version removal | 1,704 |
| Dropped committed sequence | 1,266 |
| Restore marker before each sequence | 1,266 |
| Total | 70,953 |

**Read — finishing repair audit:** a repair reservation gets its parent and full
stage arguments from the correlated scripted repair call, including its hold
and submission transition. Frozen corpus copies bind that authority by call
identity, not Python object identity. The direct positive/negative test is
`test_scripted_repair_keeps_its_parent_stage_and_settlement_hold`. Account and
missing-history gaps now name M12/C05/M14 and M06/M09/M14 respectively; all
assertion keys and deltas remain exact.


**Read — completed structural audit:** initial obligations are now established
before the first call can remove their rows. The additional real contract is
`contract/initial-account-first-reply-restore`; its incomplete account stays
expected even though production restores away the row before any public reply.
Restore confirmation needs the independently decoded precondition recorded
before the call, not just a matching request name. Failure needs a fresh
submission without an accepted or lost effect; a new storage fault cannot settle
earlier unknown work. Stage metadata is compared to its committed stage, and
intent/export scope is bound to the script and immutable thereafter.

**Read — complete perturbation scope:** state substitutions include event
outcomes and per-stage results, using one vocabulary containing every observed
state/outcome plus the documented states. Event metadata, prepared rows and
compact fences are included. The exact expected set also includes full location
references and permitted request status. Sweep samples inject faults immediately
after accepted DATA, EXPUNGE or MOVE, and discover a real post-effect cleanup
pair. These are deterministic trace boundaries, rather than a search over random
inputs. The final counts below supersede the initial 70,953-mutation run.

**Run — superseded diagnostic:** base [42714514139](https://github.com/Ares-Empire/AresOS/actions/runs/42714514139), source
`54092e340f1c0a7683edcb1eda1dbef77cfc9d6d`, passed 244 tests in 201.509s
(`results.txt:373`, PASS at `:382`). Mail [42714514243](https://github.com/Ares-Empire/AresOS/actions/runs/42714514243) was
cancelled while finishing the structural audit. Its suite ran 317 tests; only
the superseded compact pin failed (`mail.txt:429`, `:441`, `:443`), and its
initial 70,953 perturbations passed (`:140`). Two sweep shards completed only
old-pin failures; the other two were cancelled. This incomplete run is not
acceptance or a source for the final ledger. Fresh complete capture and strict
repetitions follow.

**Read — expiry/cancellation detail:** an `operation-notice` fact now preserves
the independently validated expiry/cancellation reason separately from the
operation's current recovery state. Pending-page comparisons check both facts
without counting another operation row. `test_expiry_notice_survives_a_different_current_recovery_state`
rejects replacing the expiry disclosure with a generic restored-evidence reason.
The full field audit's operation-notice row includes this separate fact; only
the exact committed acknowledgement discharges it.

**Run — intermediate local acceptance:** **106 oracle self-tests passed** (`Ran 106 tests
in 0.262s`, `OK`), and the full focused/regression/driver/expanded-perturbation
pass printed **`Ran 10 tests in 416.292s`, `OK`**. Generator again printed
`Generated artifacts match definitions`; diff check was silent. That
corpus contains **67 recorded scenarios**: all **53 focused contract states**,
seven states from the six named regressions, and seven sweep snapshots with
faults after accepted effects. Every mode is represented, including persistent
exhaustion and restored space, immediate crash/restart and an actually reached
cleanup pair. Full locations and permitted request statuses are in the checked
owner set. Every perturbation either introduced a new difference or preserved
that exact set; pre-existing defects did not count as a new difference.

| Intermediate expanded perturbation kind | Executed |
| --- | ---: |
| Boolean flags | 6,548 |
| States, event outcomes and stage results | 193,050 |
| Effects, identities, recipients, flags, hashes, destinations and app scope | 26,052 |
| Removed rows / versions | 1,786 |
| Dropped committed sequences | 1,325 |
| Restore markers before sequences | 1,325 |
| **Total, none slipped** | **230,086** |

The direct finishing tests also cover a current storage fault attempting to
resolve earlier unknown work, stage-event metadata disagreeing with its full
stage, restore without an independently observed precondition, and coherent
wrong intent/export scope. Together with the five finding-specific tests above,
they exercise the executable table's fail-closed semantics. No production code
or public action changed.

**Read — positive-path proof audit:** ordinary generic intents use either the
legacy suffix or the current `recovery-`-prefixed suffix. The oracle accepts
either initially and binds it across history and rollback. The actual Sent
check opener is `mail_sent_copy_check_open`; a correlated opener establishes
an unchecked obligation even when its recorded state falsely says checked.
`test_legacy_and_modern_intent_ids_bind_once` and
`test_valid_sent_check_reopen_is_corroborated_before_its_read` exercise both
positive and breaking forms. Quiet send, move, copy, rename and delete
contracts now additionally assert zero lifecycle, clean-result and completion
proof errors, preventing oracle false positives from entering the new pin.
The systematic test also changes every individual `id` field.

**Run — second superseded diagnostic:** source
`8221ca06cf6a1eba71dff390e29ef946b9861c50`, base
[42724117647](https://github.com/Ares-Empire/AresOS/actions/runs/42724117647)
passed 249 tests in 169.677s (`results.txt:378`, PASS at `:387`). Mail
[42724117581](https://github.com/Ares-Empire/AresOS/actions/runs/42724117581)
was cancelled during the positive-path proof audit above. All five jobs were
cancelled; none is acceptance or a source for the new ledger.

**Run — finished-source local acceptance:** **108 oracle self-tests** printed
`Ran 108 tests in 0.272s`, `OK`. The focused contracts, six named regressions,
two real-driver checks and full systematic matrix printed
`Ran 10 tests in 436.248s`, `OK`. The final corpus is **67 recorded scenarios**:
53 focused states, seven regression states and seven sweep snapshots in every
mode. **236,560 perturbations ran; none slipped.** This supersedes the earlier
local counts. Generator printed `Generated artifacts match definitions`, and
`git diff --check` was silent.

| Finished-source perturbation kind | Executed |
| --- | ---: |
| Boolean flags | 6,548 |
| States, outcomes and stage results | 193,050 |
| Effects, identities, recipients, flags, hashes, destinations and app scope | 32,526 |
| Removed rows / historical versions | 1,786 |
| Dropped committed sequences | 1,325 |
| Restore markers before sequences | 1,325 |
| **Total, none slipped** | **236,560** |


**Run — complete Linux capture:** Mail [42728213029](https://github.com/Ares-Empire/AresOS/actions/runs/42728213029), base [42728213032](https://github.com/Ares-Empire/AresOS/actions/runs/42728213032), attempt 1, source `745e9d11f97f591d37e8ffb98253ba9ccc8117b1`. Base printed `Ran 251 tests in 202.889s` (`results.txt:380`), `OK` (`:382`) and `Control base suite PASS` (`:389`). Embedded base printed 251 tests in 194.399s (`base.txt:372`, PASS `:381`). Mail printed all **236,560 perturbations, zero slipped** (`mail.txt:141`), then 317 tests in 1853.102s (`:442`); only final old contract-pin verification failed (`:430`). No runtime error occurred.

All four shard logs contain 96 flow-completion lines: every one of 32 flows in each of three workers. Each child ran six tests and failed only its final comparison with the superseded pin; each inherited four-test sweep printed `OK`. Worker exit lines are shard 0 `:431/:563/:691`, shard 1 `:386/:502/:626`, shard 2 `:136/:264/:400`, shard 3 `:176/:330/:434`. Mail job durations were suite **2093s**, shards 0/1/2/3 **2251/2149/2176/1820s**, all below 45 minutes. This complete diagnostic capture is not strict green verification.

**Run — updated compact pin:** `LEDGER-CAPTURE-R3.json` records all 17 actual-list hashes. Merge validation requires all twelve owners, correct nonshared ownership, exact agreement on shared keys and every dedicated suite. The pin contains **1,810,440 exact keys**, **44,857 stage 2 / 1,765,583 stage 3**, **2,115 groups / 976,806 bytes**, SHA-256 `a5cd7a55288aeb958e4f8420c1ca68e62f62c7c883197fb0fc239ec045809759`. Compared with round 2: **194,530 additions, 13,979 removals, 108,328 changed retained deltas**. One-space JSON indentation saves whitespace while retaining all samples/digests and format-3 strictness; no full list is committed. KNOWN-GAPS.md records the exact regeneration command and per-suite closing-stage counts. Missing work/account/hold/history and full-effect checks add coverage; corrected clean epochs and notice grouping remove incorrect differences. Production remains unchanged.


**Run — final strict repetitions:** Control base, Control Mail and Control
boundary each passed twice with code, tests and ledger from
`e8d269ad1aa848b0de74392edfb14d817dd0c0ca`. Base and Mail use two distinct run
IDs, each attempt 1: the manual dispatch and the automatic PR update. Boundary
uses attempts 1 and 2 of one run. No final-source strict test failed.

| Workflow | Passing runs / attempts | Exact output evidence |
| --- | --- | --- |
| Control base | [42733231891](https://github.com/Ares-Empire/AresOS/actions/runs/42733231891), [42733232348](https://github.com/Ares-Empire/AresOS/actions/runs/42733232348), both attempt 1 | Both `results.txt:380`: 251 tests, 227.581s / 228.550s; `:382` OK; `:389` PASS |
| Control Mail | [42733235634](https://github.com/Ares-Empire/AresOS/actions/runs/42733235634), [42733232393](https://github.com/Ares-Empire/AresOS/actions/runs/42733232393), both attempt 1 | Both suite `mail.txt:141`: 67 scenarios, 236,560 perturbations, slipped=0; `:430`: 317 tests, 2333.948s / 1444.010s; `:434` PASS. Embedded `base.txt:372`: 251 tests, 231.042s / 164.742s; `:381` PASS |
| Control boundary | [42733240406 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42733240406/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42733240406/attempts/2) | Attempt 1 downloaded workflow log `boundary-actions.txt:1701/:2416`: SETTINGS_OK in both modes; `:2436`: exact tested HEAD and attempt. Attempt 2 artifacts `present-console.txt:808`, `absent-console.txt:715`: SETTINGS_OK; `identity.txt:1`: exact HEAD and attempt. Separate-user/policy steps passed in both |

Boundary attempt 1's artifact was unavailable after its rerun; its complete
official workflow log was downloaded instead and is the explicitly identified
evidence above. Attempt 2's artifact was downloaded. `LEDGER-STRICT-R3.json`
records hashes for these boundary evidence files as well as the gap lists.

Every strict shard has all 96 flow-completion records (32 flows × three workers),
three six-test `OK` results, zero worker exits, and the inherited four-test `OK`.
The following line positions are identical in the two repetitions; all are in
the corresponding shard's `mail.txt`.

| Shard | Inherited test result | Six-test results | Worker exits (all 0) | Final PASS |
| --- | --- | --- | --- | --- |
| 0 | `:257` | `:417/:538/:655` | `:420/:541/:658` | `:660` |
| 1 | `:248` | `:372/:477/:590` | `:375/:480/:593` | `:595` |
| 2 | `:18` | `:122/:239/:364` | `:125/:242/:367` | `:369` |
| 3 | `:18` | `:162/:305/:398` | `:165/:308/:401` | `:403` |

| Mail job | Manual run seconds | Automatic run seconds |
| --- | ---: | ---: |
| Suite | 2,614 | 1,650 |
| Shard 0 | 1,645 | 1,792 |
| Shard 1 | 1,334 | 1,593 |
| Shard 2 | 2,026 | 2,195 |
| Shard 3 | 2,041 | 1,309 |

Every Mail job was below 45 minutes; the maximum was **43m34s**. Base jobs took
260s / 264s; boundary jobs took 210s / 201s.

**Read — exact automatic-checkout identity:** GitHub's automatic PR checkout is
merge commit `1fa89d5a308ba1af1892528a8870f8fa25dc2906`. Its Git tree and the
branch head's tree are both `88384027eb242f7b4dcee45a3edf8b7e751b78d0`,
verified through the commit API. The automatic base workflow log identifies it
at `:157`; the five automatic Mail job checkout lines are
`:156/:911/:1955/:2743/:3722`. Thus both repetitions test identical repository
contents. The strict manifest records these identities and lines.

**Run — complete strict pin proof:** each repetition's 17 complete actual lists
was independently merged, ownership-checked and repacked after download.
Both reproduce **1,810,440 keys / 2,115 groups / 976,806 bytes** and SHA-256
`a5cd7a55288aeb958e4f8420c1ca68e62f62c7c883197fb0fc239ec045809759`
byte-for-byte. `LEDGER-STRICT-R3.json` records all 34 actual-list hashes, both
run/attempt sets and the tested source. No diagnostic old-pin mismatch counts
as acceptance.

**Run — pinned local check:** the final pin also passed 108 self-tests
(`Ran 108 tests in 0.233s`, `OK`) and nine focused/regression/real-driver tests
(`Ran 9 tests in 4.724s`, `OK`). Generator printed
`Generated artifacts match definitions`; diff check was silent.

**Run — workflow count:** this round added **11 distinct workflow IDs / 12
attempts**: six diagnostic IDs, four strict base/Mail IDs and one boundary ID
with two attempts. Stage 1 now totals **74 IDs / 87 attempts**, versus 63 / 75
before this round. This includes cancelled, superseded and diagnostic runs;
only the strict passes above are acceptance.

**Not verified:** stage-2/3 production gap closure and real-account behavior
remain outside this run. No production source changed. The package lead owns
the fresh fix check; no stage review was run by this implementation run.

**JUDGMENT-CALL:** no product behavior decision. The oracle keeps the explicit
legacy/current intent handle forms and binds either once; requiring only the
current prefix would incorrectly reject old fixtures. Changing this later is
local test-oracle work. Ledger indentation is a reversible representation choice
with no assertion or digest-input change.

**PLAN-GAP:** D3 still needs evidence-record capacity reservation and a committed
specific or generic observed-evidence warning in stage 3. This round retains
that exact requirement and closing-stage assignment; no ordinary unchecked
notice is accepted as its substitute. No additional plan gap was assumed.

**Open questions:** none for this round. Stage 2 has not started; nothing was
merged.

**Run — closing workspace:** the regular-file inventory over 500 MiB in `.work/`
printed `[]`. No large image/download or Gradle daemon was started. The closing
commit changes only REPORT.md, KNOWN-GAPS.md and the strict evidence manifest;
code, tests and compact-ledger bytes are identical to the twice-tested source.
The closing push uses `[skip ci]` and the normal privacy pre-push check.

## Stage 2, part A

**Read — scope:** fixes REVIEW-S1-4 before any stage-2 production change.
Only test/oracle code, the compact ledger and this report change in this part.
The existing draft PR remains #26 against `pkg/19-mail`.

**Read — evidence gates:** filing check resolution and clean epochs now share
`read_evidence`. A successful, delivered LIST must belong to the enrolled check,
match its account and follow its mutation in the transcript. Admission LIST
cannot close a later check. Recovery LIST records the enrolled source keys.
The negative test covers absent, lost and negative post-command results, and
retains recovery for the review's MOVE-without-COPYUID case; the delivered
post-command result is a positive control. Unsubscribe completion now requires
one exact approved request, its operation/call identity, delivered HTTP success,
and the read/command/commit interval. An earlier operation's HTTP 200 cannot
justify this operation's HTTP 500. The HTTPS recorder now records positional
request bodies as well as keyword bodies; it compares the actual wire request.

**Read — field audit update (supplements the complete round-3 table):**

| Production-written field / structure | Independent check and alteration coverage |
| --- | --- |
| Filing result `state`, `check_open`, clean/warning flags | Successful delivered account-qualified evidence, correlated enrollment and strict post-mutation ordering; negative and positive result tests |
| Unsubscribe payload/reference/target/method/body, result/state | Full scripted approval, this call's exact POST and successful response before this operation's completion; two-operation 200/500 regression |
| Every scalar of `rows`, event `set`, metadata, `fences`, `prepared` | Required field paths are enumerated from each decoded scenario and compared with the actual mutation paths; no row-field allowlist or scalar exclusions |
| Every recipient, flag, target, location list entry; scalar and list `append_flags` | Each scalar position is changed independently, and every list also has its own removal/insertion perturbation; coverage self-test rejects an omitted new field |
| Reservation/submission `reason`, unchanged-state operation `reason` | Scripted phase selects fixed reservation/submission explanation; unchanged-state updates retain the prior explanation. The complete field test exposed and closed this additional silent narrowing |
| `events[*].record` | Explicit duplicate-field exclusion: its independently decoded fence is perturbed separately and byte equality is checked by `consistency_errors` on every comparison |
| Decoder bookkeeping | Explicit justified exclusions in `RECORD_EXCLUSIONS`: independently validated commit-marker set, physical SQLite membership, derived fence difference/generation/restore intervals, validated head and recorder startup boundary. Their decoder/archive integrity tests remain in place; `locked` is perturbed directly |

**Read — comparison proof:** `compare_proofs` is used by the real sweep driver
and the alteration test. Completion, clean-result, lifecycle and malformed-record
differences must reach its checker. Baseline errors are subtracted. A helper
exception that is not forwarded is not detection. The field audit itself fails
if a present decoded field is not perturbed. Thirteen planted committed faults
cover boolean flag, state, removed row, dropped sequence, target, recipient,
flag-list entry, append_flags, hash, destination, restore marker, account and
role. Each is checked through `Gaps.checker`; for each, a deliberately broken
oracle trusts the corrupted field to erase recovery and is rejected by the
alteration test. This also checks the future free-context representation in an
explicitly scripted recorded fixture, before production writes those fields.
The scenario corpus can be divided by index into disjoint shards; every shard
records the same inputs and runs the planted negative controls.

**Run — initial focused checks:** 113 oracle self-tests passed. The focused
contracts and all six named review regressions passed both diagnostic and strict
seven-test runs; the strict run printed `Ran 7 tests in 23.000s`, `OK`.
The worktree-only policy fixture exercises the real descriptor walk against
this repo's managed settings, without writing installed system policy.

**Run — ledger refresh:** `LEDGER-S2-A.json` records the 16 local full-list
artifacts replacing the four affected sweep flows (all twelve ownership
buckets), focused contracts and named regressions. Unaffected prefixes retain
their twice-verified Linux entries from `LEDGER-STRICT-R3.json`, repetition 1.
The format-3 pin is **976,806 bytes / 2,115 groups / 1,810,601 exact keys**:
**44,857 stage 2 / 1,765,744 stage 3**, SHA-256
`341e4b3c31d1deb30deff1394514b003f4bdd88bf24fb3b5155c06bd54ca0a42`.
There are 161 added keys, no removed keys and 1,253 changed retained deltas.
The additions expose unsupported filing closure; the changed deltas also
reflect exact HTTPS body capture. These are oracle corrections, not production
gap closure. The full lists remain under `.work/` only.

**Not verified:** part A does not claim new complete Linux workflow acceptance
or close production R2/R1/R3 gaps. Its local strict affected-flow and full
perturbation results follow below. Stage 3 remains outside this run. The lead
owns all three stage reviews; no implementation-run review is performed.

**JUDGMENT-CALL:** none affecting product behavior. Test process sharding and
explicit decoder-field exclusions are test infrastructure choices; changing
them does not change public actions or approval binding.

**PLAN-GAP:** none added. D3's evidence reservation and durable generic warning
remain assigned to stage 3. **Open questions:** none.

**Run — part A completion:** the four disjoint local perturbation passes printed `OK`: **68 recorded scenarios / 307869 alterations / zero slipped**. Counts: boolean=6607, effect=103562, restore=1329, row=1794, sequence=1329, state=193248. Every pass also caught all 13 planted faults through the comparison and rejected all 13 broken-oracle controls. All twelve strict affected-flow workers exited 0; each ran every single, persistent, cleanup-pair and crash case it owns across filing MOVE/COPY/RENAME and HTTPS unsubscribe. The final oracle self-tests, strict contracts/regressions, generator and diff checks passed. Logs are `.work/19b-s2/part-a-{self-final,strict-focused-final,perturb-0,perturb-1,perturb-2,perturb-3}.txt` and `capture-a/{shard}-{worker}.txt`.

**Run count:** part A adds **zero workflow IDs / attempts**; its checkpoint push uses `[skip ci]`. Linux acceptance is reserved for stage 2’s finished source and second pass. The checkpoint contains no production or workflow change.

## Stage 2: action context (R2)

**Read — production `2eb79db6`:** the shared `action_context` module commits a
complete context before entering an effect. It requires a submitting operation
or a started filing/free intent; a finished or missing source cannot authorize
another effect. Generic free attempts get separate identities and full caller
arguments. Context includes account, exact message identities, source,
destination, role roots/delimiters, recipients and command details (flags,
append_flags, wire hash or POST body). A failed commit prevents the command.
SQLite's immutable events retain every previous context; no remote work is
replayed. The independent journal remains compact, with its existing fences and
commit markers. The durable owner projection belongs to stage 3.

**Read — Mail:** preparation records retain the role baseline. DATA, draft/Sent/
probe APPEND, MOVE/COPY, STORE, exact EXPUNGE, folder CREATE/DELETE/RENAME and
HTTPS POST all pass the shared commit boundary. Probe folder and Message-ID
identities precede their commands. A repair commits on its own operation row,
with the original message/stage identity. The adapter's APPEND wrapper commits
before the actual append entry point, so the existing remote fixtures observe
the correct order too. Context is additive on stage/outcome writes, preventing
an earlier in-memory operation object from discarding the latest context.

**Read — base/test app:** Engine supplies scoped action authority to submission
and repair. Receiver configuration, delivery and local-stage effects, exact
local deletion, and free local flagging commit their context first. Context,
format markers and preparation roles are excluded from public operation
responses. Approval inputs, questions, bindings, untrusted marking, repair quiet
periods and acknowledgement permissions are unchanged. No generated tool file
changes; the generator still checks against the same definitions.

**Read — compatibility:** unfinished older operations and free changes disclose
that their context is “not yet checked”; finished older operations add nothing.
Supplemental legacy rows stream into the existing bounded catalogue. A first
implementation exceeded the 1 MiB paging-memory assertion at 10,000 operations;
streaming fixed it without changing that assertion. The frozen legacy fixture
was written by pre-stage-2 production `fda0d164`, with its actual SQLite SQL dump
and independently committed journal. The new code opens it, preserves old
warnings, keeps finished old work quiet and accepts a new completed send.

**Read — test infrastructure:** the independent oracle now also checks receiver
local-stage mutations and exact pre-commit context for local deletion. Its
positive local-delete fixtures explicitly supply the stronger context while
retaining all existing negative assertions and prepared-effect cases. Frozen
oracle recordings drop the production recorder callback and its queued engine
responses; it is plumbing, never an expectation input. The field/path audit and
planted controls remain active. No test is removed, skipped or replaced.

**Run — local focused verification:** `test_action_context` printed `Ran 7 tests
in 5.548s`, `OK`, including per-kind successful order and refused-commit cases,
separate free attempts, a finished-source rejection, local flag ordering, and
actual pre-stage-2 store compatibility. The oracle/selection self-tests printed
`Ran 118 tests in 0.579s`, `OK`. The supported local base subset printed `Ran 35
tests in 7.106s`, `OK`; its unchanged 10,000-operation paging assertion measured
96,059 bytes. `test_record` printed `Ran 3 tests in 3.412s`, `OK`: tiny and
maximum-body-plus-25-MiB test-app sends each add 6,121 permanent-journal bytes
across nine context/state/stage records; the three-recipient sample adds 9,040
bytes across thirteen records. Counts are now measured rather than hardcoded to
the pre-context number of writes. The original no-private-body/attachment/path
assertions remain intact. Generator, Python compilation, shell syntax and diff
checks passed.

**Run — local environment limit:** the earlier broad local base/crash attempts
failed in child processes at `boundary_not_installed`: the worktree policy
substitute is not installed system policy and is not inherited across exec.
The first attempt printed 47 tests with 129 failing subtests / 22 errors,
including the subsequently fixed paging-memory assertion. The second printed
47 tests with 128 failing subtests / 22 errors, all in installed-policy child
paths. Those runs are not green evidence. The unchanged complete base/crash/
installed-channel tests must pass in both final Linux repetitions below.
Nothing was installed or changed on the host to emulate Linux.

**Read — CI `00f24ebb`, refined at `82902fd8`:** only `control-mail.yml` changes. Four jobs partition
suite modules, four partition every recorded alteration scenario, and two
ordinary flow groups each have twelve isolated sweep jobs. Onboarding has 24
dedicated jobs/buckets. Format 3 explicitly records this per-suite exception;
ordinary flows retain their twelve buckets. Every bucket stays whole. The
inherited whole-flow fault cases have exactly one owner in the first ordinary
group's twelve workers (corrected in `253191a3`); its clean/control tests run
there too. The independent owner clean/control cases still run in every
assigned worker, including onboarding.
Selection tests prove the complete module/flow/bucket unions and uniqueness;
shared clean oracle cases still run identically in twelve workers. Artifacts
are uploaded by every job and the cap remains 45 minutes. Actual durations and
the two passing repetitions follow below; layout alone is not timing evidence.

**Run — storage:** `STORAGE-S2.json` records synthetic ordinary Mail operations
before (`fda0d164`) and after R2. Every sample completed `done`, with one Sent
copy and ordinary folder roles. Measurements include composing/preparing but
exclude the already imported caller attachment. “Events” is the byte sum of
canonical full committed events; “DB” is physical SQLite page growth, and
“journal” includes permanent fences and commit markers. The disposable index
needed no additional pages in these small samples. There is no stage-3
projection yet (zero bytes), so these are incremental R2 figures.

| Operation | Journal before → after, bytes | Full event bytes before → after | DB page bytes before → after |
| --- | ---: | ---: | ---: |
| Mail send | 9,506 → 10,918 | 36,663 → 57,570 | 57,344 → 73,728 |
| MOVE | 2,064 → 2,410 | 7,279 → 10,688 | 12,288 → 16,384 |
| Permanent delete | 3,942 → 5,524 | 11,202 → 22,317 | 24,576 → 32,768 |
| Free folder CREATE | 688 → 1,032 | 1,229 → 2,585 | 0 → 8,192 |
| Mail send with 25 MiB attachment | 9,508 → 10,920 | 42,977 → 66,980 | 57,344 → 81,920 |

The two-byte journal difference between the ordinary/attachment samples is
sequence-width allocation after import; the aligned test-app invariant above
checks exact equality independently of body/attachment size. Raw attachment
and MIME bytes remain in their existing blob/wire stores; context stores
identities and hashes. Archive and acknowledged-warning compatibility is
covered by the unchanged complete suites in the final Linux repetitions.

**Not verified / remaining scope:** no real account or provider is used.
R1/R3, the durable projection/fallback, warning lifecycle redesign, restore's
free-change projection and D3 remain stage 3. `warnings.py`, `paging.py` and
the public restore descriptions are unchanged. The full package is not claimed
complete; this run stops after stage 2. The lead owns the stage, storage-fault
and oracle-independence reviews; no own stage review was run.

**JUDGMENT-CALL:** no approval or product-action decision. Context is an additive
SQLite/event field, with a small format marker distinguishing new reservations
from older ones lacking preparation context. The existing compact permanent
journal is preserved; choosing its stage-3 projection format is deferred.
CI flow isolation and process partitioning are reversible infrastructure
choices, proved not to omit cases. **PLAN-GAP:** none added; D3 remains open.
**Open questions:** none.


**Read — final R2 follow-up `9662bf7a`:** context uses every root from the latest
successful existing role check, including unrelated ambiguous optional roots.
These read inputs are committed before the effect; no owner warning depends on
the cache. Local settings retain their stored preparation map. The independent
server recorder decodes quoted modified UTF-7 names, so quoted/Unicode optional
roots with different delimiters compare exactly. The new legal-action regression
and existing focused/regression cases printed `Ran 15 tests in 17.473s`, `OK`;
119 oracle/selection self-tests printed `Ran 119 tests in 0.524s`, `OK`. This
follow-up adds no remote read or changes any approval/action. Empty optional
maps retain the same encoding used by the full local capture.

**Run — full local capture and strict comparison:** all twelve workers completed
all 32 flows, all discovered fault sites and every single/persistent/cleanup/
crash/restart case, then printed six-test `OK` results and exited 0. For example,
worker 0 printed `Ran 6 tests in 3768.659s`, `OK`. Onboarding discovers 3,017
boundaries and took 1,300.774–2,051.408s per worker while the twelve local workers
shared the host. That measured tail motivated its dedicated 24-bucket CI split.
The full raw lists were then checked with the strict compact-ledger verifier,
including ownership, shared-key equality, exact rows/stages/deltas and all owned
groups; all 17 capture lists matched. The installed-channel two-key prefix
retains its prior strict Linux evidence until the final repetitions.

**Run — stage-2 gap closure:** the new format-3 pin contains **2,200,009 exact
stage-3 keys and zero stage-2 keys**, in **1,952 groups / 898,329 bytes**, SHA-256
`36335d9f705794079937fdac48633273c3f4f986d7ee5ea45ad8726b32107055`.
All 44,857 part-A stage-2 assertions have passed; no R2 assertion was moved to
stage 3. Remaining/new stage-3 failures are collected at the additional context
transaction boundaries and retain their complete exact deltas. `LEDGER-S2.json`
records all actual-list hashes, counts and the deterministic 24-bucket onboarding
exception. Each of the twelve local capture workers owns two complete onboarding
buckets, while each Linux onboarding job owns one. The selection/ownership tests
check both topologies, every flow and all shared clean cases. No full list is
committed. The final Linux strict proof and run count follow below.

**Run — final local alteration matrix:** 68 scenarios, **362059 alterations, zero slipped**, across four disjoint passing shards. Kinds: boolean=6714, effect=148321, restore=1412, row=1877, sequence=1412, state=202323. All 13 planted field kinds reached the comparison and all 13 broken-oracle controls failed as intended in each shard. Elapsed times were 180.760s / 267.601s / 292.477s / 116.567s. The final five Mail storage measurements were also repeated byte-for-byte after the optional-role fix; the updated storage manifest pins the final output.

**Run — first Linux diagnostic wave (`8e455241`):** base runs `42754922711`
and `42754965833` exposed 21 failures in two tests that still targeted the old
write sequence. R2 adds pre-effect context commits. The crash matrix now
explicitly covers all twelve send, eight delete and four repair writes, retaining
the original no-replay/restore assertions at every durability fence. The
incomplete-result test injects at the recipient result commit after the new
context commit. With a worktree-only policy substitute inherited by child
processes, the expanded local crash/journal suite printed `Ran 16 tests in
19.053s`, `OK`; no host policy was installed. The 119 oracle/selection self-tests
also pass.

The first Mail diagnostic run `42754922775` revealed two infrastructure issues:
whole-flow inherited fault tests were spread over more workers than their 22
flows, and Linux SQLite/export syscall traces differ from the local capture.
The inherited suite now uses the first twelve workers only, covering every flow
once with nonempty buckets; the independent owner sweep keeps all 48 jobs and
all shared cases. Selection tests assert that union and nonemptiness. The
Linux full actual lists are retained for the exact Linux pin; no R2 difference
is admitted. The redundant second Mail diagnostic `42754968875` was cancelled
once these failures were known; it is counted, never passing evidence. Neither
failed base run is acceptance evidence. The storage stop below prevents final strict repetitions.


## Stage 2 closing stop: storage decision required

**Read — governing rule:** `briefs/19b-owner-state.md:229–230` says: “Stop and
report the figures if storage per operation in the permanent journal or
projection grows by more than about 1 KB; the lead takes that to the owner.”
The stage-2 start brief does not waive this limit. The stop was applied late:
the figures were already recorded when the first Linux wave began. Those
runs and the subsequent local test corrections do not authorize crossing the
storage threshold.

**Run — measured blocker:** `STORAGE-S2.json` contains the repeatable before/after
figures on the actual R2 source. The permanent-journal increments are:

| Operation | Additional permanent-journal bytes |
| --- | ---: |
| Mail send | **1,412** |
| MOVE | 346 |
| Permanent delete | **1,582** |
| Free folder CREATE | 344 |
| Mail send with 25 MiB attachment | **1,412** |

The projection is not built (zero bytes, stage 3). Full SQLite event/DB growth
is listed above separately. The send and delete journal increments trigger
the required stop. No history was rewritten and no storage assertion was
weakened. **JUDGMENT-CALL / open question:** the lead must take this measured
cost to the owner before implementation/acceptance continues; this run grants
no exception and introduces no substitute journal format.

**Verified locally:** 119 oracle/selection self-tests; 16 expanded crash/journal
tests with worktree-only inherited policy fixtures; eight direct R2 tests and
seven focused/regression tests; all 68 recorded scenarios / 362,059 alterations
with zero slipped; all twelve complete local fault-capture workers followed by
strict offline comparison to the local compact pin. The five storage figures
repeat byte-for-byte on the final production source. Generator and diff checks
pass. Exact earlier output and source caveats are retained above.

**Not verified:** stage 2 is not Linux-green. The local compact pin is provisional
for Linux because export syscall boundary numbering differs. A complete Linux
capture, exact repin and two strict final-source repetitions are still needed.
The first-wave base failures were corrected in `253191a3` and verified locally,
but that correction has not passed Linux. The CI selection correction is also
awaiting Linux. All Mail jobs still need two complete passing timing sets;
completed diagnostic jobs alone do not satisfy that requirement. No final
`LEDGER-STRICT-S2.json` is fabricated.

**Run — workflow accounting:** stage 2 used **six distinct workflow IDs / six
attempts**, all at `8e455241`, with no part-A CI:

| Workflow | Runs (all attempt 1) | Result |
| --- | --- | --- |
| Control base | `42754922711`, `42754965833` | Failed: 262 tests, 21 failures in old write-sequence expectations |
| Control Mail | `42754922775`, `42754968875` | Diagnostic failures; both cancelled, first at the storage stop, second when duplicate failures were known |
| Control boundary | `42754972134`, `42754976711` | Both passed; superseded diagnostic source, not final acceptance |

Whole branch accounting is **80 workflow IDs / 93 attempts**, adding these six
to stage 1's 74 IDs / 87 attempts. Raw downloaded output and partial full actual
lists stay under `.work/19b-s2/ci/`; no full list enters Git. The closing push
uses `[skip ci]` to publish the stopped state without starting another wave.
PR #26 remains a draft against `pkg/19-mail`; never merged. No Gradle daemon
was started. The closing large-file inventory is recorded below.

**Run — closing `.work/` inventory:** no regular file exceeds 500 MiB.

## Stage 2 fold round

**Read — authorization:** `briefs/19b-s2-fold.md` authorizes this one fold round
and continuation only if both send and permanent delete grow by under 1 KB.
The earlier storage stop is historical. No immutable history is rewritten.
The frozen pre-stage-2 store and all public approvals/questions remain unchanged.

**Read — implementation:** the shared mutation boundary reads its own committed,
unfinished row and reuses context only on exact equality, with current write
admission still checked. A changed live context gets a separate commit. The
submitting transaction carries the first deletion/test-app effect; stage writes
carry SMTP DATA, HTTPS POST, EXPUNGE, the next batch target and test-app local
stages. Sent APPEND's existing attempt-start write carries context, including
on a repair's own identity. Filing's existing pre-command writes carry MOVE/COPY;
RENAME's intent carries identities read before its command. Generic CREATE/first
flag STORE use the starting intent. Onboarding CREATE combines its new free
intent with the existing probe-configuration write. No remote command moves
before its commit, and no remote read or replay is added.

**Run — storage gate:** the unchanged `.work/19b-s2/storage-figures.py` harness was
rerun against extracted tracked `control/` snapshots of `fda0d164` and `d87bc02d`,
and the fold source. Both historical snapshots reproduce `STORAGE-S2.json`
exactly. All five final samples finish `done`. Figures include composition or
preparation, exclude caller import, and use the same ordinary roles and one
Sent copy. “Records” counts transaction fences; each completed fence also has
one commit-marker line, whose bytes are included. Physical journal line counts
are twice the displayed record counts.

| Operation | Before stage 2 `fda0d164`: bytes / records | Part B `d87bc02d`: bytes / records | Fold: bytes / records | Growth over before |
| --- | ---: | ---: | ---: | ---: |
| Mail send | 9,506 / 14 | 10,918 / 16 | 9,506 / 14 | **0** |
| MOVE | 2,064 / 6 | 2,410 / 7 | 2,064 / 6 | 0 |
| Permanent delete | 3,942 / 5 | 5,524 / 7 | 3,942 / 5 | **0** |
| Free folder CREATE | 688 / 2 | 1,032 / 3 | 688 / 2 | 0 |
| Mail send, 25 MiB attachment | 9,508 / 14 | 10,920 / 16 | 9,508 / 14 | 0 |

The gate passes at the stricter decimal **1,000-byte** interpretation. All extra
context transactions in these five samples are removed. `STORAGE-S2.json`
retains all three sets of event/SQLite/index/projection figures and log hashes.
The journal format is unchanged. The stage-3 projection remains absent (zero).

**Read — retained records:** send's fourteen transactions are composition,
reservation, submitting, six message/wire/SMTP/recipient stages, Sent APPEND
start/end, two local-stage results and final outcome. MOVE's six are generic
start, initial filing intent, pre-command started fence, post-command evidence,
filing completion and generic completion. Delete's five are reservation,
submitting, marked, target result and outcome. CREATE's two are its start and
completion. Each already existed before stage 2 and retains its original
state/evidence/lifecycle role; this round does not remove those boundaries.

| Separate context still required outside the five samples | Reason |
| --- | --- |
| Draft APPEND | Generated Message-ID and wire hash follow the generic start; no intervening existing write precedes APPEND |
| Onboarding probe APPEND | Probe MIME/Message-ID follows CREATE completion; its own identity and completion are required |
| Free test-app CONFIGURE / LOCAL_FLAG | No existing write precedes the receiver setting or local-item effect |
| Changed live roles/source/identity, or another flag variant | Earlier context differs; without an intervening existing write a replacement context commit must precede dispatch |

**Read — verification scope:** the direct R2 suite includes real SIGKILL workers
and ENOSPC at every logical write's entry and four durability fences, covering
folded and separate paths. Its independent command comparison uses the same
`differences` checker as the sweep and decodes the record before server entry.
After process death, recovery must leave receiver deliveries/stages/settings
unchanged. A failed new context blocks its own command; a refused onboarding
result may be followed by a separately committed probe on another identity.
The original failed-result/no-next-recipient assertion is unchanged; its
injection now targets the folded recipient-result write. The existing complete
backup/restore crash matrices cover every remaining test-app write.

**Not verified yet:** Linux full capture, strict pin and both final Control
workflow repetitions are pending below. Stage 3 has not started. The lead owns
all three stage reviews; this run performs no own stage review.

**Run — measured source:** production fold commits `1af497f8` and `fc7b6efa`.
The final source repeats all five storage measurements byte-for-byte. LOCAL_FLAG
also uses its existing item write to close the free intent, eliminating an empty
completion transaction; its direct test requires exactly two writes and no open
intent afterward. This does not affect the five storage samples.

**Read / run — oracle correction:** injected pre-write failures can leave one
onboarding probe submitting while another, independently committed probe starts.
The old binder treated the two open operations as ambiguous. Internal operation
binding now uses actual server command identity and the approved payload,
independently of the context being tested. The negative self-test still catches
a wrong destination or identity, and refuses a missing committed source. The
new write-fence test initially assumed every failed result stopped all later
onboarding probes; it now correctly requires that a failed *new context* blocks
its own identity, while every later command independently proves its context.
No existing assertion was weakened, and no new R2 gap is admitted.

**Run — local fold checks:**

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.work/19b-s2/child-policy:control:control/mail_tests .work/venv/bin/python .work/19b-s2/local.py test_action_context
Ran 10 tests in 207.269s
OK
```

The twenty mutation flows discover **129 logical writes**; each runs entry
ENOSPC, ENOSPC at journal-appended / SQLite-prepared / SQLite-committed /
journal-committed, and SIGKILL at those four fences: **1,161 fault/crash cases**.
The command-boundary and frozen-old-store assertions also pass. The child-policy
fixture is confined to this worktree; no host policy is installed.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.work/19b-s2/child-policy:control:control/tests .work/venv/bin/python .work/19b-s2/local.py test_crashes test_journal_closed test_record test_owner_state_oracle test_mail_ci_selection
Ran 139 tests in 25.086s
OK
Record growth: tiny send=4078 bytes; maximum body + 25 MiB send=4078 bytes; 6 context/state/stage records
Record growth: typical three-recipient send=5560 bytes across 8 context/state/stage records
```

The final-source focused run of `test_action_context.ActionContexts`,
`test_owner_state_contracts` and `test_owner_state_regressions` printed
`Ran 16 tests in 9.553s`, `OK`. `control/generate.py --check` printed
`Generated artifacts match definitions`; `git diff --check` printed nothing.
Logs are `.work/19b-fold/{write-fences-complete,pre-push-base,pre-push-focused}.txt`.
The earlier experimental runs with the overly broad onboarding assertion or
ambiguous binding failed; their output remains in `.work/19b-fold/` and is not
green evidence. The final checks above resolve those test-infrastructure errors.

**Run — Linux capture source:** `99a9d9711865472b1df57a36aff481e7788665e9`,
pushed normally without bypass flags. Capture Mail `42758730136`, base
`42758730461`, boundary `42758810824` were started once. Their results and exact
pin follow after the jobs complete; an old-ledger comparison failure is capture
evidence only, never strict acceptance.

**Run — incomplete diagnostic superseded:** the Mail run `42758730136` was
cancelled before the complete capture finished. Source `99a9d971` would have
copied RENAME's internal context into its public audit payload. The fix attaches
context to the stored row while keeping the previous public audit dictionary.
A new regression inspects every public log page and requires both internal fields
to be absent; direct R2/contracts/regressions print `Ran 17 tests in 5.950s`, `OK`. The 36 RENAME
entry/fence failure/crash cases print `Ran 1 test in 4.581s`, `OK`. All five
storage samples repeat byte-for-byte. No incomplete capture list is used in the
pin. Base `42758730461` passed 263 tests in 217.510s (`results.txt:392`, `OK`
`:394`, PASS `:401`); boundary `42758810824` passed. These are superseded
source diagnostics, not final acceptance. The replacement below is the one
complete Linux capture on the corrected fold.

**Read — fold field-audit addition:** `context.internal_command` reads committed
`id`, `repair_of`, payload folder and message references only to join an
internal probe to the actual logged command when several probes remain open.
It does not derive or resolve an obligation. `differences` still compares the
selected context and command independently against the scripted account,
recipient set and previously logged probe CREATE/APPEND identities. A missing
source, corrupted context identity or wrong destination still fails
`test_internal_probe_binding_uses_command_identity_with_multiple_open_probes`.
The complete decoded-field perturbation audit remains active. The Adapter
protocol now supplies `submission_context(operation)`; returning `None` retains
the separate commit at dispatch when an earlier context cannot be prepared.

**Run — complete corrected Linux capture and strict offline re-pin:** Mail
[42760159138](https://github.com/Ares-Empire/AresOS/actions/runs/42760159138),
base [42760159041](https://github.com/Ares-Empire/AresOS/actions/runs/42760159041),
attempt 1, source `a1859a6969911e3d38866807e0812e6088d4fa7c`.
All 48 sweep/onboarding owners completed all assigned flows and six-test child
runs. Every input is fresh Linux evidence, including the independent base
channel. The merge verifies **53 full actual lists**, correct ownership,
identical shared-key deltas and exact complete row/stage/calls/facts/pages
hashes. The new compact pin is **1,849,228 exact keys, all stage 3; zero stage 2;
1,936 groups; 890,087 bytes**, SHA-256
`ff3de0ad2c95e7892ad09f46878ee9ba77e5aad7d6490ac369c3bc66297ad988`.
Every one of the 53 inputs then passed the strict compact verifier. No R2
assertion was reclassified, and no full list is committed.
`LEDGER-CAPTURE-S2-FOLD.json` records every input/log hash, ownership, suite
counts and all 56 job durations. Maximum capture job duration was **1,127s
(18m47s)**, below both the 45-minute cap and the 35-minute aim.

**Run — diagnostic failures retained and fixed:** this capture is not a green
workflow. Besides old-pin comparisons, it found one real-HTTPS fixture failure
(`test_unsubscribe.py:78`) and eight inherited direct-archive prefix mismatches
(`test_review23_sweep.py:651/:655`). The HTTPS transcript lacked the URL,
pre-command committed rows and caller sequence interval required by part A's
strong completion proof. `a70e02ab` records those independent inputs, keeping
the original completion assertion. Its real local HTTPS receiver test, with
only IMAP substituted, printed `Ran 1 test in 0.622s`, `OK`; the 204, redirect,
no-cookie/no-GET and exact-body assertions remain.

`8915955b` fixes the inherited archive fixture's random IDs and changing event
timestamps. Only direct `Scenario('archive')` gets fixed IDs/clock; it advances
time to age real commits. The independent `OwnerScenario` already had its own
deterministic clock/IDs and retains exactly the captured execution. Three
complete archive replays now have equal write traces. The focused inherited
shard runs every original prefix assertion and fault/cleanup case, printing
**301 single / 301 persistent / 1,532 archive cleanup-pair cases**, plus the
restore cases, `Ran 2 tests in 84.319s`, `OK`. No assertion or fault mode was
removed. Final local self/selection checks print `Ran 120 tests in 0.230s`,
`OK`; focused R2/contracts/regressions print `Ran 17 tests in 7.650s`, `OK`.
These fixture corrections do not supply or alter any of the 53 captured owner
lists; the two final full strict repetitions below must validate both fixes
and the complete pin.

**Read — ledger change:** the fold removes context transactions and their raw
failure sites. The final Linux pin has a net 350,781 fewer stage-3 assertion
keys and 16 fewer groups than part B's local pin; Linux export/SQLite syscall
numbering and exact changed deltas remain explicit. The digest includes every
remaining exact failure; nothing is normalized away or accepted as an R2 gap.
D3, G22 and all R1/R3/lifecycle work remain assigned to stage 3.


## Stage 2 fold: final strict verification

**Run — tested source:** `be8ea4ca20064d403702e81e323a9a2bd731f6dd`, with the corrected
standalone HTTPS recorder, deterministic inherited archive fixture and complete
Linux pin. No production or ledger changes occur between the two repetitions.
`LEDGER-STRICT-S2-FOLD.json` pins the source, all **106 actual-list hashes**,
all 112 Mail job durations, exact output lines and both independent full merges.
The closing documentation-only commit leaves this code, tests and pin unchanged.

| Workflow | First strict run | Second strict run | Evidence |
| --- | --- | --- | --- |
| Control base | [42764959121 / attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42764959121/attempts/1) | [same run / attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42764959121/attempts/2) | attempt 1: results.txt:393/395/402 — Ran 263 tests in 174.962s, OK, PASS; attempt 2: results.txt:392/394/401 — Ran 263 tests in 244.012s, OK, PASS |
| Control Mail | [42764959165 / attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42764959165/attempts/1) | [same run / attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42764959165/attempts/2) | All 56 jobs green in each attempt; every owner worker runs six tests and every job log ends in Control Mail suite PASS. Suite counts and exact log lines are pinned in the strict manifest. |
| Control boundary | [42764999307 / attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42764999307/attempts/1) | [same run / attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42764999307/attempts/2) | attempt 1: present-console.txt:808/absent-console.txt:715 SETTINGS_OK; identity.txt:1 names the exact tested HEAD; attempt 2: present-console.txt:808/absent-console.txt:715 SETTINGS_OK; identity.txt:1 names the exact tested HEAD |

**Run — Mail timing and complete selection:** each attempt contains four suite
jobs, four alteration jobs, 24 ordinary sweep jobs and 24 onboarding jobs. No
case, fault mode or assertion is dropped, and the timeout remains 45 minutes.
The four disjoint suite jobs run **327 tests** in each repetition; the separate
sweep/alteration jobs retain all their additional tests and cases.

| Attempt | Suite maximum | Alteration maximum | Ordinary sweep maximum | Onboarding maximum | All-job maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 17m41s | 12m20s | 16m18s | 8m11s | 17m41s |
| 2 | 13m45s | 15m20s | 13m43s | 8m48s | 15m20s |

Every Mail job is below the 35-minute aim as well as the 45-minute hard cap.
Both alteration passes run **68 recorded scenarios / 348,416 perturbations /
zero slipped**, with all 13 planted field faults caught through the comparison
and all 13 broken-oracle controls rejected in every shard. The private RENAME
audit duplication was removed rather than excluded from the field audit.

**Run — independent complete-pin proof:** each repetition independently merges
all 53 fresh actual lists (all 48 owners, four focused/named lists and the fresh
base-channel list). Both produce exactly **1,849,228 stage-3 keys, zero stage-2
keys, 1,936 groups, 890,087 bytes**, SHA-256
`ff3de0ad2c95e7892ad09f46878ee9ba77e5aad7d6490ac369c3bc66297ad988`.
Correct ownership, multiplicity and shared-key equality are required; every
packed group also passes its original strict checker. All 44,857 part-A R2
assertions remain closed; no R2 failure is accepted or moved to stage 3.

**Run — workflow accounting:** this fold uses **8 distinct workflow IDs /
11 attempts**: the three superseded initial diagnostics (one incomplete Mail
capture cancelled), the corrected complete Mail/base capture, and the three
strict workflows with two attempts each. Stage 2 totals **14 IDs / 17
attempts**; the whole branch totals **88 IDs / 104 attempts**, from the Actions
API. The Mail rerun request returned HTTP 502, but the API confirmed attempt 2
had been created; it was not requested again. No duplicate attempt is hidden.
D1's relaxed run target applies. Captures and diagnostic failures are never
counted as strict green acceptance.

**Read — closing scope / not verified:** the R2 fold and stage-2 verification are
complete. Real accounts, real providers and owner use are not exercised; the
CI uses synthetic isolated servers. R1/R3, the durable projection/fallback,
warning lifecycle redesign, restore's free-change projection and D3 remain
stage 3. No own stage review was run; the package lead owns the three fresh
reviews. PR #26 remains a draft against `pkg/19-mail`; it was not merged.

**JUDGMENT-CALL:** no product or approval decision. Exact committed context is
reused only while the live command agrees; otherwise a separate pre-command
commit remains. The existing immutable journal format and history are retained.
**PLAN-GAP:** none added by this fold; D3 remains deferred as briefed.
**Open questions:** none for the requested run. Stage 3 was not started.

**Run — closing housekeeping:** normal pushes retained the privacy gate and no
bypass flag was used. Gitleaks scans of this run's commits found no leaks; the
final scan output is `.work/19b-fold/privacy-final.txt`. The closing `.work/`
inventory (`large-files-final.json`, regular files over 500,000,000 bytes) is
empty: **no file exceeds 500 MB**. No Gradle daemon was started. Full gap lists,
raw logs and generated fixture material remain uncommitted under `.work/`.

## Stage 2, fixes round 1

**Read — scope:** `19b-s2-fixes.md` and all three reviews control this round.
Commits first strengthened the alteration harness (`bfbe580c`), then fixed the
oracle (`60d47295`), then restored body-independent RENAME (`78162dcf`), then
corrected the sweep fixtures (`81f39107`). Subsequent verification fixes remain
within those items. No stage-3 implementation, immutable-history rewrite,
approval/input/question/binding change, or self-review was performed.

| Brief item | Change (read) | Regression / plant (run locally unless marked below) |
| --- | --- | --- |
| 1 / B5 / S5 | Nested key deletion; independent server-snapshot field audit; coherent event/projection/fence/later-snapshot alterations; integrity-only differences excluded for coherent lies; production plants through unmodified Driver.compare; seven individual validator controls | P1 escaped the reviewed oracle (`teeth-before.txt`, `FAILED`); the new controls reject that oracle. Every one of the 13 field kinds maps to a real production plant. Final alteration totals follow the Linux evidence below. |
| 2a / B1 | Send completion requires the independently selected Sent and answered stages, even when production omits the stage row entirely | `missing-sent-copy` (P1); `stage_claims` also requires each planned stage |
| 2b / B2 | Script plus independent roles select Sent/Drafts; answered STORE must be exact Answered on the approved original; Sent bytes equal DATA or its approved Bcc-header variant | P2, P6, P7; `wrong-append-flags`, `wrong-sent-bytes` |
| 2c / B3 | Per-target Deleted STORE must precede EXPUNGE; marked stages require that exact STORE | P4; fixture test preserves UID 1 before marking and preserves unnamed UID 7 after exact EXPUNGE |
| 2d / B4 / ASTRA 3 | Every reference × flag branch and exact folder effect is required before intent completion. Accepted effects are counted per intent and per scripted attempt regardless of terminal state | Both omitted-branch variants; real failed-result APPEND retry under persistent exhaustion, reached cleanup pair, restart and restored space; two independently scripted draft saves have different intent identities |
| 2e / SOL 1 / ASTRA 2 | Actual check correlation replaces all-row LIST enrollment; rename destination must exist; filing recovery needs a complete independently recorded scan | Unrelated LIST and absent-destination cases, plus acknowledgement, repeated reads, post-expiry read, archive attempt and restart; added to the alteration corpus |
| 2f / SOL 2 | Each receiver recipient is independently checked against approval and prior context before completion | Wrong and extra-recipient command-boundary cases |
| 2g / S2 / SOL 4 | Rename count comes from source-folder identities in the RENAME server event; committed/public counts are compared to it | P5; coherent `message_count` variants |
| 2h / S1 | Outcome state/reason derives from replies, required local effects and fault/commit order; a false reason is replaced in the retained projection | P3; runtime fixture-label reason test; subsequent same-state rows preserve the validated reason |
| 2i / S3 | Versioned missing context cannot use legacy synthesis; unversioned context synthesis requires an explicitly legacy source | `missing-context`, `dropped-context-commit`; version-one STORE test; frozen pre-stage-two store compatibility remains enabled |
| 2j / S4 | Only seed and scripted fixture_input intervals receive fixture authority | Runtime `fixture` event reports a lifecycle error and cannot supply a reason |
| 2k / ASTRA 4 | LOCAL_FLAG validates exact reference, revision, requested value and prior context, then corroborates atomic item/intent completion; full owner sweep includes local_flag | Missing-context case fails; valid atomic completion passes; real wrong-value plant; all fault modes are selected by the normal sweep |
| 2l | AST import checks resolve relative imports to the audited package; absolute imports must be standard-library modules; direct, attribute and getattr-style dynamic imports are rejected | Bare same-name modules, parent production import, driver import, builtins.__import__, getattr and imported aliases are negative controls |
| 3 / SOL 3 / ASTRA 1 | RENAME reuses the existing safe_folder UID/UIDVALIDITY enumeration. No extra SELECT, FETCH, full-body parse or wire-size admission is added | Oversized, depth-45 and 1,100-part folders rename successfully with zero FETCHes; existing all-write failure/crash fences remain enabled |
| 4 | Normal APPEND adds one Sent copy; separate send_duplicate flow retains delayed-copy warnings. EXPUNGE honors Deleted and STORE honors both add/remove branches | Quiet send and deliberate race assertions; existing quiet move/copy/rename/Trash/permanent-delete contracts all pass |

**Run — local source checks:** the completed local pass and exact commands are
recorded below. Earlier development runs, including failures, remain under
`.work/19b-s2-fixes/` and are not substituted for that pass. The diagnostic
traversal ran all **34 flows** clean and at point 1 in
single/persistent/live/crash modes, ending `R2 gaps {}`
(`diagnostic-current.txt`). These Mac runs use the existing worktree-local
managed-policy fixture and child-process shim; installed Linux policy and
server verification is supplied by the workflows below. Generator printed
`Generated artifacts match definitions`; diff check was silent.

**Read — alteration performance:** identical completion questions in a single
replay are memoized using the operation inputs, record-event identity, current
server/script lengths and local item state. Each replay starts with an empty
cache; payload claims still run on each invocation. Script intervals are indexed by commit sequence within each replay. Coherent mutations copy the affected row and writable envelopes while sharing other immutable inputs; the input-immutability test checks this. Every alteration still
reaches the shared comparison. Mail alterations are split over 12 disjoint
scenario shards; the timeout remains 45 minutes and all scenarios/fields remain
selected. Early diagnostic alteration runs were stopped and replaced while
fixing newly exposed malformed-field/result-row cases; they are not green
acceptance evidence.

The updated resolution requirements below refine the existing executable
allowlist; all other resolution kinds in FORMAT.md remain unchanged.

| Resolution | Independent corroboration (read) | What remains visible without it |
| --- | --- | --- |
| completion / send | Approved full envelope, delivered accepted DATA, unique-role Sent APPEND or correlated Sent match, approved Answered STORE, all before completion | Pending work and recovery |
| completion / permanent delete | Every approved reference's accepted/delivered Deleted STORE followed by exact UID EXPUNGE | Pending work and recovery |
| intent_completion / remote free change | Every scripted effect in the plan accepted and delivered once before the result commit | Intent recovery, including interrupted batches |
| intent_completion / LOCAL_FLAG | Prior exact context, scripted reference/revision/value, matching committed item change and atomic intent removal | Intent recovery / local-effect proof difference |
| check_result / filing | Post-mutation LIST for this check; independent roles and exact target; complete source-specific recovery scan | Open check and recovery |
| check_result / rename | Post-mutation LIST for this check, exact destination present and resolved roles | Open check and recovery |
| acknowledgement | Exact scripted occurrence and its own committed acknowledgement | Unacknowledged occurrence; acknowledgement never settles unfinished work |

| Production-written input added/refined in the field audit | Where read | Independent validation | Tests / alterations |
| --- | --- | --- | --- |
| Every committed_before row field, including state/id/action/account/repair_of, context.operation_id/command, roles, recipients, hashes and identities | context.bind/decode/differences; model.stage_claims, filing_claims, warning | Decoded commit prefix and sequence; script/approval, raw commands and independent role/byte evidence; bindings cannot justify command authority | Every snapshot scalar/key; coherent propagation into all later copies; P1–P7 and versioned missing-context plant |
| created_before row keys and sequences | context.bind; model.lifecycle | First independently decoded non-null commit, strictly within this attempt where a new intent is required, never after command before_seq | Snapshot field audit; `unverified-source-creation`; frozen/current source binding tests |
| LIST check_sources | read_evidence/result_proof | Recorder scope for the actual source-specific check; matching account and post-mutation order; destination existence and scan completion | Ordinary mail_accounts LIST cannot enroll a check; every list entry altered |
| commit_observations row contents and sequence membership | model.lifecycle | Independent decoded commit prefix; observations cannot replace the script or raw server facts | Every scalar/key altered; coherent later-copy propagation |
| states/reasons, absent stage keys, missing result rows, context_version/context | lifecycle, outcome, stage_claims, completion_errors | Script/approved effect plan, RCPT/DATA/local-stage replies, faults, commit order and explicit legacy interval | P1/P3/P4; nested-key deletion; runtime fixture label; missing result/context commits |
| message_count and rename identity list | filing_claims and notice-context | Number of independent source-folder identities at RENAME; UID/UIDVALIDITY identify the namespace without MIME reads | P5 and coherent count changes; zero-FETCH rename tests |
| testapp item flagged/revision, missing intent and atomic removal | local.errors and intent_result_proof | Scripted exact reference and requested value; prior committed context; exact item revision change | Valid/missing/wrong-value local flag cases and full local_flag sweep |
| APPEND destination/flags/bytes and mutation multiplicity | script_differences, effects, context_errors, completion_errors | Script role/flag/effect plan and raw DATA/Bcc bytes; count per scripted attempt and intent, independent of terminal state | P2/P6/P7, wrong flags/bytes and duplicate-result-write retry |

**Run — storage (same STORAGE-S2 harness):** `storage-final.txt` and
`STORAGE-S2.json.after_fixes_round_1` reproduce after_fold byte-for-byte for all
five operations, including SQLite event/file figures. No permanent-journal
record was added. The projection remains unbuilt (zero bytes, stage 3).

| Sample | Before stage 2 bytes / records | Part B bytes / records | Fold bytes / records | Fixes round 1 bytes / records | Journal growth over before |
| --- | ---: | ---: | ---: | ---: | ---: |
| Send | 9,506 / 14 | 10,918 / 16 | 9,506 / 14 | 9,506 / 14 | 0 |
| Move | 2,064 / 6 | 2,410 / 7 | 2,064 / 6 | 2,064 / 6 | 0 |
| Permanent delete | 3,942 / 5 | 5,524 / 7 | 3,942 / 5 | 3,942 / 5 | 0 |
| Free CREATE | 688 / 2 | 1,032 / 3 | 688 / 2 | 688 / 2 | 0 |
| 25 MiB send | 9,508 / 14 | 10,920 / 16 | 9,508 / 14 | 9,508 / 14 | 0 |

**Read — warnings.py / paging.py:** no changes to either file in this fix round.
**Not verified:** human mail accounts and provider behavior are outside the
synthetic-account scope. Stage-3 gaps remain explicitly deferred. The package
lead runs the fresh reviews; this run does not review itself.
**JUDGMENT-CALL:** none changing owner-facing behavior; RENAME restores the
pre-stage-two behavior. **PLAN-GAP:** none requiring a new owner decision.
**Open questions:** none for this round.


**Run / read — additional cases exposed by the strengthened test:** missing
submission reasons now compare against the canonical reason even when the key
is absent. An existing fixture-consistency difference cannot authorize a newly
changed copy: initial fixture values come from the explicit script/seed input,
while later production resolutions still need their normal proof. A malformed
probe reference or deadline reports a semantic difference instead of aborting
all expectations. Removed onboarding result rows retain the independently
observed account-setup obligation and qualification disclosure. Direct tests
cover each case. Script clock samples and the independently selected test TTL
validate new reservation deadlines, including a coherent numeric deadline lie.
Expectation modules do not import the clock recorder.

**Read — coherent versions:** every historical row version is exercised, without
coalescing equal field names across versions. A lie propagates through matching
later copies of that value; a subsequent different legitimate result remains
intact. Removed versions rebuild the affected projection/snapshots and creation
sequence from the altered commit prefix. Matching compact fences, their hash
chain and working head are re-encoded in memory. The real immutable history is
untouched. A direct positive transformation test checks these copy/version
relationships and proves comparison leaves its inputs unchanged.

**Run — healthy-path additions:** the Bcc Sent variant matches the exact DATA
wire, and a relative RENAME resolves its parent using the independently listed
delimiter. All six effect/fixture tests print `OK` in `effects-final.txt`; the
final oversized-message case advertises one byte above the normal wire limit,
without allocating a large body or changing that limit (`rename-final.txt`).

**Run / read — complete enrollment and result claims:** dropping an operation's
terminal row is a real Store.write plant through Driver.compare; dropped filing
results also report their own semantic difference. A first filing result cannot
start in a resolved state. Deleting Sent-check enrollment cannot consume an
earlier successful search: resolution requires an explicit checked state and
its correlated result proof. The direct deletion regression preserves the
unchecked obligation. Missing onboarding-completion errors identify the actual
account completion commit, so an unrelated context/result write cannot mask the
missing row. These cases were found by the stronger per-version corpus; failed
development logs are retained and are not acceptance evidence.

**Read / run — validator attribution and retained identity:** alteration figures
record the exact validator that emitted each semantic proof; they do not infer
ownership from a shared fact-kind name. The plant controls now require that
actual provenance as well. A negative attribution test prevents a filing check's
unsupported resolution from being credited to the operation transition gate.
The strengthened corpus also checks missing cancellation/expiry/acknowledgement
results, early operation identity/action validation, immutable enrolled filing
context, atomic source/result rows, and required current warning context.
Synthetic check regressions freeze their seed separately. Coherent mutations
copy only the affected path; the nested copy/version test proves both the source
record and independent server inputs remain unchanged.

**Read / run — final malformed-record guards:** identity/app/action omissions are
checked before dependent resolution helpers inspect later records. A complete
source-specific filing check cannot be persisted as still unchecked without a
semantic difference. The existing expiry test's positive fixture now includes
its original mail_send action; all expiry, acknowledgement and archive
assertions remain unchanged. Frozen legacy field absences remain distinct from
new runtime omissions.

**Read / run — complete compact copies:** the coherent writer now includes the
approval-derived compact description and repair context, references the prior
committed row when a result write omits it, and propagates matching copies in
fences whose working event is absent. A direct transformation test covers each
case and unchanged source inputs. Hash rebuilding starts at the first changed
fence. This changes only synthetic copies under test. The LOCAL_FLAG healthy
record is also in the systematic corpus, in addition to its production plant,
negative controls and complete normal fault sweep.

**Read / run — event copies:** coherent state and stage mutations update their
duplicated event outcomes and stage-result metadata too. Stage/event and
filing-state/event copy disagreements are explicitly integrity-only; they do not
count toward catching coherent variants. The transformation test checks these
copies directly. The final coherent-only diagnostic and full-field passes are
reported separately; final Linux runs exercise the complete finished source.

**Read / run — final-result and repair proofs:** a filing can persist intermediate
progress after its LIST; only the last source write in an unfaulted scripted
attempt, or an explicit recovery-result commit, must reflect the completed
check. The expected completion still needs the correlated destination/scan/role
proof. Successful repair completion requires its matching parent stage update
in the same commit. A real Store.write plant omits that parent, and must produce
its own missing-result proof through Driver.compare. A direct negative/positive
atomic-parent test covers missing rows, missing stages and the matching update.

**Run — completed local pass (same source):** source `ad9d6d59` passed 144
oracle/CI-selection tests, the 26-test focused suite (461.195s), and all four
complete alteration shards. The latter cover **94 recordings / 2,003,694
alterations / 257,524 coherent variants / zero slipped**. Exactly 14,904
alterations change the expected owner set. The separate coherent-only diagnostic
also passes all 94 recordings. [LOCAL-S2-FIXES.json](LOCAL-S2-FIXES.json) records
source identities, exact log hashes, counts and test summaries. Local owner-state
runs record candidate gaps before re-pinning; they do not pass the superseded
strict ledger. Installed-policy/server acceptance comes from strict Linux below.

| Validator | Alterations its own proof catches | Of those, owner set changes | Disabling only this validator |
| --- | ---: | ---: | --- |
| script_differences | 5,380 | 647 | Plant assertion fails (required) |
| stage_claims | 50,082 | 1,415 | Plant assertion fails (required) |
| completion_errors | 2,395 | 1,329 | Plant assertion fails (required) |
| payload_claims | 59,821 | 24 | Plant assertion fails (required) |
| filing_claims | 1,054 | 90 | Plant assertion fails (required) |
| transition | 12,134 | 3,588 | Plant assertion fails (required) |
| local.errors | 1,544 | 1,170 | Plant assertion fails (required) |

Each alteration shard also passes all 13 production field-kind controls and all
seven single-validator controls through the shared comparison. These counts
credit actual emitted proof provenance, exclude integrity-only catches for
coherent variants, and count alterations rather than duplicate proof facts.

**Run — local commands:**

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests .work/venv/bin/python -m unittest test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/19b-s2/child-policy .work/venv/bin/python .work/19b-s2/local.py test_owner_state_contracts test_owner_state_regressions test_action_context test_owner_state_plants test_owner_state_s2_effects
# Each shard 0..3, with OWNER_PERTURB_SHARDS=4:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests OWNER_PERTURB_SHARD=0 OWNER_PERTURB_SHARDS=4 .work/venv/bin/python .work/19b-s2/local.py test_owner_state_perturb
python3 control/generate.py --check
git diff --check
```

The unit and focused commands print `OK`; each alteration shard prints `OK`
and `slipped=0`. Generator prints `Generated artifacts match definitions`;
diff check prints nothing. The original oracle-review probe scripts were read
and left untouched; P1–P7 were adapted into the production plants in this tree.

**Run / read — standalone mailto recorder correction:** the Linux capture's
suite 0 exposed `test_header_mailto_exact_address_body_and_approval`: its direct
Oracle invocation lacked pre-command commit prefixes and any Sent APPEND event.
The stricter completion validator correctly rejected those incomplete inputs
(`No matching accepted SMTP DATA`, `Approved local stage missing: sent_copy`).
`46f9c123` records those prefixes and the actual APPEND with independently
listed roles, flags and bytes; the SMTP receiver also records raw DATA bytes.
All original assertions remain, and an accepted APPEND assertion was added.
The test passes locally with real TLS SMTP plus memory IMAP (`Ran 1 test in
0.545s`, `OK`, `mailto-recorder-local.txt`), using the ignored local policy/path
fixture. Both strict Linux rounds pass the full real-server test setup.
Only `smtp_fixture.py` and `test_unsubscribe.py` change after capture source
`ad9d6d59`; production, expectations, Driver and all 53 owner-state gap-list
inputs remain identical. The capture is diagnostic evidence, not green
acceptance, and is not rerun to replace that recorded failure.

**Run — one complete Linux capture and strict re-pin:** Mail
[42811270001 / 1](https://github.com/Ares-Empire/AresOS/actions/runs/42811270001)
and fresh base
[42811270027 / 1](https://github.com/Ares-Empire/AresOS/actions/runs/42811270027)
use source `ad9d6d5903bc7519d271d46dbaffed2091675fb1`. Base prints
`Ran 287 tests in 215.976s`, `OK`, `Control base suite PASS`. All 64 Mail logs
were checked: 14 jobs passed, 48 owner workers completed their six tests and
failed at the superseded strict pin, suite 3 failed its superseded contract pin,
and suite 0 exposed the standalone recorder issue described above. There are no
runtime errors or inherited-sweep failures. This is the single diagnostic Linux
capture; it is not presented as a green workflow.

All **53 fresh actual lists** (48 sweep/onboarding workers, contract, three G22
cases and fresh base channel) have complete owned suites, correct unique/shared
ownership and identical shared values. Their union contains **2,057,880 exact
stage-3 keys / zero stage-2 keys**, **2,024 groups / 928,878 bytes**, format 3,
SHA-256 `abaf79487708e750813a25f337633f05bf1b20857cc6cc1aa9f9fd3c1c573277`.
After packing, every input is independently passed through the strict checker
against the new pin. No partial/local/old list is substituted. The additional
flows and stronger retained-obligation checks explain why this exact stage-3
pin differs from the fold; no R2 assertion is reassigned to stage 3.
[LEDGER-CAPTURE-S2-FIXES.json](LEDGER-CAPTURE-S2-FIXES.json) records every actual
list's hash, counts, owned suites/buckets, complete job timings and exact log
evidence. Full actual lists remain under `.work/` and in CI artifacts.

All twelve Linux alteration jobs pass **94 recordings / 2,003,694 alterations /
257,524 coherent variants / 14,904 owner-set changes / zero slipped**. Every
per-validator count in the local table above is reproduced exactly, including
13 production field-kind controls and seven single-validator controls in each
shard. The capture's maximum Mail duration is **2,192s (36m32s)**, close to the
35-minute aim and below the unchanged 45-minute cap.

**Run — capture validation commands:**

```sh
python3 .work/19b-s2-fixes/ci/validate.py 42811270001 1 capture
PYTHONPATH=control:control/mail_tests .work/venv/bin/python .work/19b-s2-fixes/ci/harvest.py 42811270001 1 repin
python3 .work/19b-s2-fixes/ci/publish-capture.py
```

The first prints `Validated all 64 Mail job logs: capture` with the two explicit
failure categories; the harvest prints the counts, size, digest and zero R2
above, after all 53 strict checks pass. The ignored helpers do not change test
selection or expectations. KNOWN-GAPS.md gives a standalone reproduction from
the recorded artifacts.

**Run — finished-source strict pair:** the pin and all code/tests are fixed at
`08644540c415d5f4bbbcb7efe8b1cb105dc161df`. Every workflow below passed attempts
**1 and 2** on that source. The first proof was saved before requesting the
second repetition; no code, test, selection or pin changed between them.

| Workflow | Run | Attempt 1 | Attempt 2 |
| --- | --- | --- | --- |
| Control base | [42818236541](https://github.com/Ares-Empire/AresOS/actions/runs/42818236541) | 287 tests in 200.436s; `OK`; `Control base suite PASS` | 287 tests in 211.440s; `OK`; `Control base suite PASS` |
| Control Mail | [42818236590](https://github.com/Ares-Empire/AresOS/actions/runs/42818236590) | All 64 jobs PASS; maximum **1,710s / 28m30s** | All 64 jobs PASS; maximum **1,679s / 27m59s** |
| Control boundary | [42818278484](https://github.com/Ares-Empire/AresOS/actions/runs/42818278484) | PASS; exact HEAD; `SETTINGS_OK` with and without seccomp | PASS; exact HEAD; `SETTINGS_OK` with and without seccomp |

All **128 Mail jobs** are below both the 35-minute aim and unchanged 45-minute
cap. Each repetition runs the four 78/79/103/75-test suites, all 48 complete
six-test owner workers, and all twelve alteration shards. Each alteration pass
prints **94 recordings / 2,003,694 alterations / 257,524 coherent / 14,904 owner-set
changes / zero slipped**. Every own-validator catch count exactly matches the
table above. All thirteen real production field-kind controls and all seven
single-validator controls pass in every shard. The corrected standalone mailto
test prints `ok` in both real-server runs.

Both complete fresh **53-list** merges strictly validate ownership and shared
values, then reproduce all **2,057,880** exact stage-3 entries and the
**928,878-byte** compact pin byte-for-byte. Both have **zero R2 gaps**. No full
list is borrowed from the capture or the other repetition.
[LEDGER-STRICT-S2-FIXES.json](LEDGER-STRICT-S2-FIXES.json) records all **106** fresh
actual-list hashes, exact output lines/log hashes, every job duration, source,
pin hash and run accounting. This is acceptance evidence; the earlier failed
capture remains separately classified.

**Run — workflow commands:** the pin push automatically started base and Mail;
boundary was dispatched explicitly. GitHub ran the existing Fedora base,
isolated-server Mail `suite`/`perturb`/`sweep`, and boundary workflows without
relaxing their checks or timeouts. The second repetition reran each entire
workflow:

```sh
gh workflow run control-boundary.yml --ref pkg/19b-owner-state
gh run rerun 42818236541
gh run rerun 42818278484
gh run rerun 42818236590
# Each attempt 1 and 2, after downloading its complete artifacts:
python3 .work/19b-s2-fixes/ci/validate.py 42818236590 2 strict
PYTHONPATH=control:control/mail_tests .work/venv/bin/python .work/19b-s2-fixes/ci/harvest.py 42818236590 2 strict
python3 .work/19b-s2-fixes/ci/proof.py 42818236590 42818236541 42818278484 2
```

Validation prints `Validated all 64 Mail job logs: strict ; all strict green`.
Harvest prints the identical pin counts/digest and zero R2; proof prints source,
attempt, maximum duration, pin keys and alteration total. All exit zero. The
Mail rerun request returned HTTP 502, but the immediate API read showed attempt
2 already queued on the correct source; the request was not repeated and no
extra attempt was created.

**Run / read — storage reproduction:** the unchanged measurement harness is
`.work/19b-s2/storage-figures.py`, using the worktree-local managed-policy fixture
and synthetic remote commands. It measures preparation plus execution, excluding
the caller import. Reproduce the recorded measurement with:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests .work/venv/bin/python .work/19b-s2/storage-figures.py .work/19b-s2-fixes/storage-final.json
```

The recorded output prints `measuring send`, `move`, `delete`, `free_change`,
`send_25mib`, then the JSON figures in the storage table above: all five outcomes
`done`, all journal growth zero. `STORAGE-S2.json` retains the exact measurements.

**Run — workflow count:** API snapshots before and after this fix round show
**5 new workflow IDs / 8 attempts / 197 jobs**: one complete Mail capture plus
fresh base (2 attempts), followed by the three finished-source workflows twice
(6 attempts). The Mail capture's 50 failed jobs are the explicitly reported
old-pin/recorder diagnostics; every one of the 132 finished-source strict jobs
passes. Branch totals increase from **88 IDs / 104 attempts** to **93 IDs / 112
attempts**. The strict manifest includes the five new IDs and their final
attempt counts. No own stage review was run.

**Run / read — closing scope and housekeeping:** the closing commit changes
only REPORT.md, COVERAGE.md, KNOWN-GAPS.md and the new strict proof manifest.
Code, tests, workflow definitions and KNOWN-GAPS.json remain identical to tested
source `08644540`. Normal pushes use no `--no-verify` bypass. The manual Gitleaks
commit-range scan prints `no leaks found`; its final log is
`.work/19b-s2-fixes/privacy-final.txt`. The final `.work/` inventory of regular
files over 500,000,000 bytes is **empty** (`large-files-final.json`). No Gradle
daemon was started; both local CI watchers exited after completion. Full actual
lists, raw logs and synthetic fixture files stay uncommitted under `.work/`.
PR #26 remains a draft against `pkg/19-mail`; it is not merged. Stage 3 was not
started. Real accounts/provider behavior remain not verified as scoped above;
the lead owns the fresh stage reviews. No additional judgment call, plan gap or
open question is introduced by this closing verification.
