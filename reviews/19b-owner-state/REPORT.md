# 19b — stage 1 only

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

**Read:** G22-evidence exposes a constraint for stage 3: an open check can preserve “not yet checked,” but cannot reconstruct an exact transient remote role fingerprint that was observed while its result write failed and then changed again. The later implementation must retain enough evidence under that failure model, or explicitly reconcile the guarantee with the owner; merely rerunning the latest LIST cannot recover the lost occurrence. Stage 1 records the failing assertion without claiming to solve it.

**Read:** stage-1 acceptance is the coverage/oracle/comparison/strict-gap harness, not the full brief's empty-ledger acceptance. Remaining gaps name stage 2 or 3. This is the user's explicit stopping point.

**Run — workflow budget:** 40 distinct workflow run IDs, 43 attempts including retries and cancelled runs. This exceeded the approximate 25-run target. Independent oracle review fixes, complete Linux baseline capture, calendar and UUID/nanosecond repeatability corrections, and required final repetitions account for the additional runs. Superseded, diagnostic and cancelled documentation-only runs are not passing verification. The report-only push `e32a3f02` restarted base/Mail because PR path filters use the cumulative diff; redundant runs [42649695450](https://github.com/Ares-Empire/AresOS/actions/runs/42649695450) and [42649695455](https://github.com/Ares-Empire/AresOS/actions/runs/42649695455) were cancelled. The closing report correction uses `[skip ci]` to avoid a reporting loop; its diff from tested source contains only the report/review documents.

## Open questions

None blocking stage 1. The next run should begin at stage 2 with this ledger and keep its unexpected-pass requirement.

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
