# Empire brief 302 — progress

## Build part 2 (steps 3 and 4)

Status: **Build part 2 done; next: step 5**.

### Done (commits per step)

- `git fetch origin` succeeded at the start. The fetched main tip `dddc8d58`
  differs from part 1 only in `STATE.md`. No file changed here overlaps, so
  no merge was needed. Branch `pkg/302-store-oracle`, existing draft PR #111.
- Step 3: `6f12f561` (pushed). A canonical immutable before-start restore
  obligation is saved from the full matching event, restore plan and scripted
  confirm precondition. `Driver.started` sends `startup-replay` to the shared
  checker immediately after binding, before views, flushes or another confirm.
  It requires the matching marker, valid applied head, exact event and SQLite
  effects, generation, pending flag and service lock. Intermediate batches finish
  only their saved work and retain generation/lock. Failed starts cannot claim
  readiness; healthy subsequent starts finish the saved event. Obligations end
  after checking, and later restarts cannot inherit an old confirm. Captured
  failed envelopes remain immutable. No production Store change.
- Base-container fixture follow-up: `d425882e` (pushed), after the CI finding
  described below; it changes only two mock tests, not Driver or the real VFS.
- Step 4: `efa70045` (pushed). `records.visible_history` keeps `events` and
  `committed` exact and extends local rows only with an ordinary validated tail
  matching the last fence and applied SQLite head. The event remains prepared.
  Lifecycle, current notices/catalogues, paging, qualification and audit use the
  same history and the same identity/effect/transition proof gates. Archive
  discovery still starts from marked hash-qualified manifests. Restore batches
  retain their separate rule; Chrome's committed projection is unchanged.
- Call ranges use staged sequence; local read evidence uses applied sequence;
  pre-command snapshots/permission and unfinished space plans use marked history.
  An applied event stays with its producing call through its failed envelope and
  restart. Visibility neither authorizes another app command nor releases a
  recovery hold before its marker. This required changing part 1's driver range
  and trace inputs, but not its Store/barrier/advice implementation.
- Alterations mutate applied rows, event versions and coherent row/event/fence
  claims while preserving markers/startup inputs. The corpus appends applied
  cancellation/account tails and staged final/intermediate restores; its four
  new cost entries are measured locally. Rejected prepared candidates still get
  independent fence checks. Identity errors reach semantic comparison before
  malformed encodings interrupt replay; generation/input hash are immutable.
  Fence hashes are checked even when restore lost their working events. These
  redundant encoding checks cannot count as semantic catches of coherent lies.
- Took RECHECK-1's two nits: recompute receives the opposite input lock, and
  the full decoded-lock table covers pending, absent head, hash, behind/equal/ahead
  and empty records. Recompute handles absent heads and preserves a bad head
  hash unless a matching original fence was actually re-encoded.

### Tests and mutation

All execution uses tracked-source exports under
`control/test-work/302-exports/` with no dot-prefixed ancestor. Logs, patches,
scripts and recordings are under `.work/302/`. The runner applies the prior
package's managed-settings `Boundary.read` stand-in, exports absolute PYTHONPATH,
disables bytecode, sets TMPDIR to `.work/302/tmp`, and orders base `tests` before
`mail_tests`; Mail runs separately. No FilePolicy change.

- Step 3 export `step302a`: `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/step302a base test_owner_state_oracle test_restore_batches test_review22_storage`:
  **148 tests OK**, 46.613 s (`step3-base-final.log`: 131 oracle, 9 restore,
  8 storage). Driver-only final recheck: **131 OK**, 1.136 s
  (`step3-oracle-final.log`). Restore 1k/10k retained/peak bytes:
  13,785/217,066 and 13,785/217,069.
- Step 3 runner `mail test_owner_state_sweep.OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm test_owner_state_sweep.OwnerStateSweep.test_discovered_staged_restore_interval_and_cleanup_pairs_replay_at_startup`:
  **2 tests OK**, 97.370 s (`step3-sweep-final.log`). The six named 26/40/73
  cases cover both modes. Discovery examines all 76 clean points: 47 staged-final
  points, endpoints 26/73; 100 single/persistent cases including 25/74/75 controls,
  plus 137 cleanup pairs. All startup proofs empty; no restore-lock gaps.
- Skipped-startup mutation: disposable `skip302a`, only the special startup
  branch condition bypassed (`skipped-startup.patch`). Same named pre-confirm
  test: **1 test FAILED (failures=1)**, 2.569 s
  (`step3-skipped-startup-final.log`). All six cases fail the assertion
  `startup-replay must finish before any automatic confirm`, with missing
  marker/head/effects/generation/lock proof. It is not an import, fixture or pin
  failure. The baseline immediately above passes. Its first attempt passed
  unexpectedly because the new checker had not called `finish()`; added that
  call and a direct raw-proof assertion, then reran both baseline and mutant.
- Step 4 export `step302c`, before the last coherent-input regression: runner `base test_owner_state_oracle test_owner_state_fixes_s2 test_review22_storage test_restore_batches test_mail_ci_selection`:
  **190 tests OK**, 47.453 s (`step4-base-final2.log`: oracle 140, S2 26,
  storage 9, restore 9, CI selection 6). Store coverage includes cancellation,
  acknowledgement and account-like rows at marker failures, single/persistent
  write faults and failed rollback, refused retry without byte changes, visible
  applied rows, staged-only controls, same rows after restart and zero receiver
  arrivals. Decoder/model negatives include head/hash/fence/staging/restore,
  missing rows, unmarked archive manifests, exact cancellation/ack identity,
  coherent identity deletion/generation/input hash/outcome/effect claims, and
  applied context unable to authorize a command before its marker.
- After the final coherent-input fix, runner `base test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection`: **173 tests OK**, 1.597 s (`step4-oracle-final3.log`: oracle 141, S2 26, CI selection 6). Includes completed/failed marker controls: coherent re-encoding preserves the raw journal history and marker set, and both status/request-state checks retain the original physical latch expectation.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/final-mail.py control/test-work/302-exports/step302c mail`: **42 tests OK**, 433.488 s (`step4-mail-sweep-final.log`): ordinary owner contracts, quiet, regressions, S2 effects and plants (26), plus all sweep unit tests (16), excluding only the full matrix. Final latch coverage: 154 view runs / 275 checked phases, 3,598 other recorded gap keys, and 77 phase/retry/restart variants including 41 cleanup pairs. No status/restore-lock disagreements in those latch assertions. The other gaps are recordings, not a full-pin pass.
- With `mail_tests` removed from both sys.path and exported PYTHONPATH, and an assertion that `storage_faults` cannot be imported, `.work/302/base-only.py` runs `base test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection`: **173 tests OK**, 1.636 s (`step4-base-only-verified.log`). The startup SQL mock explicitly uses an empty fault scope; the pre-command mock supplies only `ACTIVE=None`. Every assertion remains. Real Mail/VFS tests remain unchanged.
- The new applied-tail sweep discovers marker writes at cancel 68, onboarding
  61, repair 364, status 154, archive 231 and send 873, then exercises each write
  and sync in both modes and live/crash phases: **48 cases + 76 cleanup phase
  runs**. Checks include every view/page/count/envelope, 56 live applied records
  with correct producing-call identity, and 62 restarts with immutable saved
  envelopes and no repeated remote action. Staged-but-unapplied controls remain
  in the latch sweep. Startup coverage still has zero proof/lock gaps.
- `OWNER_PERTURB_SHARD=6 OWNER_PERTURB_SHARDS=12 PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/step302c mail test_owner_state_perturb.SystematicPerturbations.test_recorded_scenarios_have_no_silent_owner_state_change`: **1 test OK**, 720.004 s (`step4-alteration-shard6-verified.log`): **12 recordings, 183,894 alterations, 21,052 coherent changes, slipped=0**. All seven required alteration kinds occur; the previously failing large onboarding contract passes all 23,070 candidates in its selected part. Includes the applied-tail cancellation recording and all intact/disabled validator controls.
- Focused four-record corpus: `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/new-alterations.py control/test-work/302-exports/step302c mail ignored`:
  **12,284 alterations, slipped=0** (`step4-new-alterations-final4.log`):
  cancel 2,211, onboarding 1,234, staged final 1,264, staged intermediate 7,575.
  Both row-only and coherent claims are checked (202 coherent candidates in the
  two applied-tail recordings). New costs record measured seconds/counts for this focused vocabulary, not
  invented hosted timing. The full shard uses the whole-corpus vocabulary and
  therefore has different candidate counts (cancel 2,631 there). Existing cost weights retain their hosted provenance.

Earlier non-green logs are retained. The initial decoder assertion still expected
an applied unmarked generation to be invisible; changed it to require visibility
while keeping marked/prepared sets separate and adding unapplied controls.
A direct Store application fault raises the raw OSError, unlike Engine's bounded
reply; the store test now checks its mapped original refusal. The new corpus found
silent generation/identity-deletion/lost-fence alterations; the independent and
semantic checks above fix them without weakening an assertion or allowed set.
Its intermediate fixture originally reused one composition and correctly got one
idempotent preparation; distinct synthetic subjects now make 35 operations. An
interim sample exposed eight premature hold releases; fixed by retaining marked
space-plan authority. The first shard attempt was interrupted by its exact PID
(exit 130) before rerunning the final source; it is not evidence of a pass.
The next full shard exposed a phantom latch after coherent hash re-encoding
(`step4-alteration-shard6-final.log`, 1 test failed after 346.524 s). A coherent
writer now preserves the original physical transaction record as independent
input to the existing latch rule, for status and request-state checks. It changes
no raw trace, marker or startup input, and does not weaken the live hash/phase
checks. The focused regression and the final full rerun cover this distinction.

### Compact sample delta against part 1

`PYTHONDONTWRITEBYTECODE=1 python3 .work/302/sample.py control/test-work/302-exports/step302c mail .work/302/after-item3-final`:
**104 runs, 187 checked phases, 1,528 keys** (`step4-sample-final.log`). The 52
additional phases are the new immediate startup checks, all empty. Against
part 1's final `after-item1/sample.json` (2,345 keys): **825 closed, 147 changed,
8 new, 1,373 identical** (`step4-sample-delta-final.json`). Twelve changed keys
are alias-only. Against the original 2,498-key baseline: 978 closed, 151 changed,
8 new, 1,369 identical. All seven complete clean trace files are byte-identical.

| Flow | Closed | Changed | New |
|---|---:|---:|---:|
| archive | 31 | 0 | 0 |
| cancel | 118 | 26 | 0 |
| onboarding | 132 | 18 | 0 |
| repair | 263 | 28 | 0 |
| restore | 54 | 27 | 0 |
| send | 175 | 20 | 8 |
| status | 52 | 28 | 0 |

- Applied rows now agree at H: cancel 69 is `failed` in both store and model;
  onboarding 61/62 includes the saved account. The staged/unapplied controls do
  not become visible. The historical 1439 case still is not the local first
  account boundary, and remains explicitly exercised.
- Restore's 54 closures and 27 changes are after-start lifecycle/row-reason
  corrections from assigning the replayed batch to its original staged confirm.
  The old marked end range excluded that event. No store, restore-lock formula,
  restore-row projection or captured pre-crash record was changed to force it.
- The eight new keys are `control_pending.notice-count` and `mail catalogue.total`
  at send marker 873/874: model 0, store 1, in live/exhausted phases. They expose
  count disagreements after correcting the applied row, not startup/lock gaps.
  No new recovery-hold keys remain. Their whole-pin classification belongs to
  step 6; this sample does not promise N7's historical total or erase other gaps.
- No key ends in `.restore-lock` or `/startup-replay`. The standalone startup
  proof adds coverage rather than an accepted baseline gap. No pin change.

### Push checks

Latest observed push (`d425882e`):

| Workflow | Run | Observed |
|---|---:|---|
| Control boundary | 44339324452 | pending |
| Control Chrome | 44339324376 | queued |
| Control Chrome qualification | 44339324396 | pending |
| Control base | 44339324334 | pending |
| Repo privacy | 44339324446 | pending |
| Control Mail | 44339324269 | queued |

Step 3 (`6f12f561`): Repo privacy **44327232557 passed** and Control boundary
**44327232070 passed**. Control base **44327233131 failed**: 407 tests, one
`ModuleNotFoundError: storage_faults` in the new base-only startup mock. The
local two-path runner had included Mail helpers, masking that missing dependency.
Reading the failed log also led to checking the new applied-context mock without
Mail imports; it had the same dependency. `d425882e` gives only those mocks their
explicit empty inputs. The isolated 173-test recheck above passes. The hosted
retry is pending, not claimed green (`step3-base-ci-failure.log`).

At the same observation, `efa70045` Base/Mail/boundary/privacy/qualification
runs were cancelled and Chrome was queued. Step 3 Mail/qualification were
cancelled and Chrome was queued. Raw observations: `step3-push-checks.json`,
`step4-push-checks.json`, `part2-push-checks-final.json`. No workflow was
dispatched, rerun or awaited past this work; the closing documentation push
changes no executable source.

### Left, in order

1. Step 5: every reviewer mutation on the final build, with passing baselines and exact
   patches/failures in disposable executable exports. The skipped-startup probe
   above is completed; it does not waive the full final-build matrix gate.
2. Step 6: integrate current main, settle drift, re-pin once, full capture,
   pin classification and proof, and required Control CI green twice.
3. The assigned package/security and independent classification reviews.

### What the code doesn't show

Local exports and synthetic fixtures prove no installed/root/channel behaviour,
real owner account/service restart, full sweep/alteration matrix, hosted point
portability or whole-pin classification. Required pushed workflows are reported
only as observed above; no dispatch, rerun or wait past this work. No production
Store/Engine, OS, boot, mount or live-service change, and no mod test is needed.

### JUDGMENT-CALLs

No new product choice; board #352 already approved keeping applied rows visible
and the restart advice. Reversible oracle choices: derive applied history via a
helper rather than another mutable Record projection; keep the canonical startup
obligation on Driver, separate from decoded state; keep permission and space plans
marked while local rows are applied. No schema/journal format or Record exclusion
was added. Changing these later costs test/oracle work, not data migration.

### PLAN-GAPs

- Intermediate restore batches fill their byte limit as well as their row limit:
  the 70-change store fixture's first batch has 30 operations. The test asserts
  the saved batch exactly, retained generation/lock and no invented remaining work.
  Discovery finds 47 staged-final points within 26..73, rather than treating every
  syscall in that interval as identical staged bytes.
- The new alteration corpus exposed validation blind spots in rejected prepared
  claims, coherent missing identity and old fences without working events. These
  needed shared proof checks; copying rows into the final projection or counting
  a format exception as a semantic catch was not sufficient.
- Local visible rows do not finish a space plan. The brief did not name
  `hold_facts`; it must retain marked rights until the marker to avoid introducing
  eight false hold discrepancies. No live reservation or Store code was changed.
- Item 1's raw marker hashes also need independence from item 3's coherent
  fence re-encoding. Otherwise a healthy completed physical write appears latched
  merely because an alteration re-encoded its claim. The original immutable
  transaction record now supplies those inputs; no cached latch flag or returned
  error is used.
- The brief's local base path includes Mail helpers, while the hosted base
  container omits them. That hid two new mock fixtures' imports of the Mail VFS
  module. Explicit empty mock inputs and a no-Mail-path recheck close the gap;
  production fault injection is unchanged.
- Part 1's hosted/local onboarding difference (2,610 versus 2,570 points) remains
  unresolved and explicitly deferred to same-runtime capture/classification.
  All seven local clean traces match part 1 exactly; no point was silently skipped.

Closing scratch scan: no files over 500 MB under `.work/` or `control/test-work/`.
No Gradle daemon was started. No installed/root/channel test, workflow dispatch,
OS owner module, boot tool, mount or live-service action was run.

---

## Build part 1 (steps 1 and 2)

Status: **Build part 1 done; next: step 3**.

### Done

- Step 1: baseline at `4a6acc2e`. `git fetch origin` returned exit 0;
  `HEAD` and `origin/main` both resolve to `4a6acc2e`, so no merge was needed.
  The branch is `pkg/302-store-oracle`. Baseline commit: `2de6da86` (pushed).
- Step 2: `b64eb8f4` (pushed): `_append` reports actual rollback completion; only
  `Store.write`'s first fence can clear the persistent latch. Fresh observations
  hold the request barrier before dispatch and at later writable checks, through
  reply finishing. Failed writes/flushes retain the first cause and queued notice.
  Surviving latches refuse later writes with `journal_incomplete`; restart advice
  is appended once after first-error selection and survives bounded replies.
- The independent oracle records raw fence/marker write, sync and cleanup
  completion, plus the position of a storage check whose decoded inputs were
  already latched. Frozen `JournalAttempt` tuples survive unchanged bytes and
  captured envelopes; restart ends running history. One shared rule supplies
  status and request-state expectations. No store latch flag, returned error or
  fault count supplies the expected latch. Reads need an actual write/check
  attempt to permit a latch refusal. G22 is now an ordinary passing assertion;
  its pin stays untouched until step 6. README/FORMAT document item 1 only.

### The baseline and the sample

Executable tracked-file exports are under ignored
`control/test-work/302-exports/` (no dot-prefixed ancestor). Logs, scripts and
recordings are in `.work/302/`. Tests use the documented managed-settings
`Boundary.read` stand-in, bytecode disabled, absolute `PYTHONPATH` exported for
subprocesses, and `TMPDIR` resolved to `.work/302/tmp`. Base imports put
`control/tests` before `control/mail_tests`; Mail uses the reverse order. The
export needs an empty `.work/` for existing decoder fixtures. FilePolicy is
unchanged. These local exports are test fixtures, not an installed service.

Commands from the worktree root:

- `git archive HEAD control reviews/19b-owner-state | tar -x -C control/test-work/302-exports/baseline`
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/baseline base test_owner_state_oracle test_review22_storage test_restore_batches`:
  **134 tests OK** (124 + 6 + 4), 42.374 s, `baseline-base-rerun.log`.
  Restore verification printed `(13785, 217066)` / `(13785, 217069)` retained/peak bytes.
  The first attempt ran 134 with 5 fixture errors (export lacked `.work/`);
  `baseline-base.log` retains that failure. No test was changed to fix it.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/baseline mail sweep-units`:
  **11 tests OK**, 9.847 s, `baseline-sweep.log`; excludes only the full matrix.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/sample.py control/test-work/302-exports/baseline mail .work/302/baseline`:
  **104 sampled runs, 135 checked phases, 2,498 recorded keys**,
  `baseline-sample-rerun.log`, `baseline/sample.json`, and seven clean traces.
  No key ends in `.restore-lock`. This is a recording, not a strict pin proof.
  The first sample attempt failed because its diagnostic row reads were inside
  injected faults; those diagnostics now use `outside_faults`, without changing
  the sweep's observations or faults.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/baseline-values.py`:
  `Expected baseline row and lock assertions: OK` (`baseline-values-final.log`).
  Direct pre/post-start probes assert the staged final generation without a
  second confirm. Points 26/40/73/74/75 finish unlocked; 25 stays locked.
  Startup can append a recovery event after sequence 6 (head 7), so the probe
  checks completion and the exact staged generation, not an assumed head of 6.
  Earlier probe logs retain its overstrict head/count assertions and corrections.

Clean points and resolved sample boundaries:

| Flow | Clean points | Sample points (write/sync for the selected marker) |
|---|---:|---|
| restore | 76 | 25, 26, 40, 73, 74, 75; cleanup pair 75:76 |
| cancel | 70 | 1, 2, 10, 24, 30, 67, 68, 69; cleanup pair 2:3 |
| onboarding | 2,570 | first account marker 61/62; historical 1439 also exercised |
| repair | 366 | last marker 364/365 |
| status | 156 | last marker 154/155 |
| archive | 373 | last marker 231/232 (later points are export/cleanup) |
| send | 875 | last marker 873/874 |

Every listed non-pair point ran in single/persistent mode and live/crash phases;
cleanup pairs ran in single mode and both phases. Cancel 69/single/live has
head 6, marker 5, prepared event 6: the store shows `failed`, the model
`reserved`, both unlocked. Onboarding 61 in either mode and 62/single shows
one more account than the model (raw fixture totals 2/1; the new-account
catalogue is 1/0). At 62/persistent the marker survives failed cleanup, so both
count 2. Historical 1439 is now in a later transaction, with head/marker 24 and
prepared 25; it does not reproduce the historical account key. Nothing was
silently skipped. Local onboarding still has 2,570 rather than hosted 2,610
points; attribution remains for the later capture on the same runtime.

### Item 1 tests and the barrier mutation

Final executable export: `control/test-work/302-exports/build302/`, whose path
has the same length as the baseline export. Commands use `run.py`'s stand-in and
import ordering described above. Every full matrix is excluded.

- `python3 .work/302/run.py control/test-work/302-exports/build302 base test_owner_state_oracle test_review22_storage test_restore_batches test_review23_results test_journal_closed`:
  **148 tests OK**, 45.782 s (`final-base.log`). The source at that run included
  the store/barrier/advice changes; later oracle-only refinements were rechecked
  with **127 tests OK**, 1.037 s, using the same runner with
  `base test_owner_state_oracle` (`oracle-verified.log`). Restore peaks remain
  217,066 / 217,069 bytes.
- `python3 .work/302/run.py control/test-work/302-exports/build302 mail test_review_fixes_22 test_review_fixes_23 test_review_fixes_24 test_owner_state_regressions.ReviewRegressions.test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13`:
  **18 tests OK**, 11.699 s (`final-mail.log`). Includes G22 and the named
  failed-pre-dispatch-flush regression. Its final strengthened test records the
  caught pre-command refusal and asserts it outside Engine's exception handler.
- `python3 .work/302/run.py control/test-work/302-exports/build302 mail test_review24_io test_review_fixes_24.Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request`:
  **3 tests OK**, 3.307 s (`raw-and-barrier-verified.log`): two raw-I/O tests and
  the final named barrier regression (six variants: before dispatch / after
  admission, each zero / short / fence-sync). Each failed request causes zero
  DATA; the next explicit request succeeds without restart, exactly one DATA
  and one APPEND in total. Separate coverage blocks reads and cancellation in
  the failed request and permits their healthy retry.
- `python3 .work/302/run.py control/test-work/302-exports/build302 mail sweep-units`:
  **13 tests OK**, 93.305 s (`sweep-verified.log`). New tests execute **154 view
  runs** (plus clean/discovery helpers), **198 unique checked phase identifiers**,
  **3,994 other recorded gap keys**, and separately **77 phase/retry/restart
  variants including 41 cleanup pairs**. Zero status and restore-lock gaps in
  these cases. Covers both modes, live/exhausted/restarted phases, first fence,
  index, staging, application, H and final confirm. Successful later confirm
  ends the interrupted-confirm flag after safe first-fence rollback.
- Store tests cover zero/short writes, fence fsync, truncate and rollback-sync
  failure, index/staging/application and marker write/sync, ENOSPC/EDQUOT/EIO and
  SQLite FULL/IOERR. They retain failed-write assertions, require healthy explicit
  retry after proven rollback, preserve notes/advice/first error, refuse later
  writes without changing bytes, and verify restart recovery. Both final-confirm
  marker rollback outcomes retain the lock and staged generation; the second
  confirm is `journal_incomplete` with no new write/generation, and restart
  finishes the same generation without another owner confirmation.
- Oracle table: 18 phase/completion/cleanup combinations, read-only/admission
  controls, marker/fence identity, immutable entries, restart bounds, and both
  first-error orderings. Raw read-handle SQLite close faults demonstrably return
  no Python exception; they cannot displace the first propagated refusal.

**Barrier removal mutation:** disposable `mutate02` export; exact patch in
`.work/302/barrier-removal-final.patch`. Changed only the body of
`Observations.require_writable` to `return`, disabling both request gates while
retaining narrow latch clearing and the original final error envelope.

`python3 .work/302/run.py control/test-work/302-exports/mutate02 mail test_review_fixes_24.Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request`:
**1 test, FAILED (failures=6)**, 3.032 s (`barrier-mutation-final.log`). Every
variant fails `1 != 0 : Failed flush must cause zero SMTP DATA`, not an import,
fixture or pin error. The same named baseline passed immediately beforehand in
the 3-test run above. An earlier narrower mutation also failed the three
pre-dispatch zero-DATA assertions (`barrier-mutant.log`); final evidence removes
both gates and catches all six variants.

**Compact sample after item 1:**
`python3 .work/302/sample.py control/test-work/302-exports/build302 mail .work/302/after-item1`:
104 runs / 135 checked phases, **2,345 keys** (`sample-verified.log`,
`after-item1/sample.json`). Compared with baseline: **153 closed, 8 changed,
0 new, 2,337 identical** (`sample-delta-final.json`). All seven full clean traces
are byte-identical, not just equal point counts. Still zero `.restore-lock` keys.

- The 153 closed keys are statuses: cancel 75, onboarding 6, repair 24, status 24,
  send 24. They concern later latch refusals and the new independent expectations.
- Four changed archive status deltas remove `journal_incomplete` from the expected
  set for a read that attempted no write; the existing `stale_reference` defect
  remains. Four cancel 1/2 envelope deltas retain the exact same missing reserved
  row/count mismatch, now repeated on four log pages instead of two. A direct
  before/after audit probe is saved as `audit-delta-{baseline,item1}.log`; live
  checks can now write after safe first-fence rollback, extending the audit log.
- H's row discrepancy remains a control: cancel 69 still shows model `reserved`
  versus store `failed`. Item 2's startup proof and item 3's row correction have
  not been built. No pin change or full-pin classification is claimed.

Earlier non-green logs are retained, not represented as passes: the first oracle
run exposed a hand-built Driver fixture without new trace state and an overly
broad restore-lock status exception; the initial bounds test incorrectly assumed
an already-shortened message needed fragment storage; the first retry sweep
mistook a later read-only close failure for failed journal cleanup. Expanded
samples then found first-error ordering and ignored SQLite-close issues. Those
causes were fixed and tested; no assertion, FilePolicy rule or allowed set was
weakened to hide a pin failure. `git diff --check` passes.

Push checks so far: baseline commit's Repo privacy run **44319148928 passed**.
Control workflows are path-filtered for that documentation-only push.

Draft PR: [#111](https://github.com/Ares-Empire/AresOS/pull/111), against `main`.
After the normal implementation push, the closing read-only Actions query showed:

| Workflow | Run | Observed result |
|---|---:|---|
| Control base | 44324138098 | queued |
| Control boundary | 44324138060 | queued |
| Control Chrome | 44324138069 | queued |
| Control Chrome qualification | 44324138105 | queued |
| Repo privacy | 44324138082 | queued |

Control Mail had not yet appeared in that query; no result is claimed for it.
Raw snapshots are `push-checks-{implementation,closing}.json`. These are
observations, not CI passes. No workflow was dispatched, rerun or awaited past
this work. The closing documentation commit records these results and the
implementation hash; it changes no product or tests.

### Left, in order

1. Step 3: item 2, independent startup obligation and pre-confirm proof.
2. Step 4: item 3, applied history, lifecycle ordering and alterations.
3. Step 5: all remaining mutations.
4. Step 6: merge current main, re-pin once, full capture and proof.
5. Final package/security reviews and independent classification review.

### What the code doesn't show

Local checks use synthetic fixtures and the managed-settings stand-in. They
prove no installed-channel/root behaviour, hosted point portability, whole-pin
classification, full sweep or alteration matrix. No workflow was dispatched.
No OS, boot, mounted-disk, owner-module or mod tests belong to this run.

### JUDGMENT-CALLs

The owner approved the brief's restart advice and continued visibility of saved
rows on board #352. No new product judgment call. Technical choices are reversible:
the rollback fact is an attribute of the raised refusal, consumed only at the
first fence; immutable raw history is stored on Record with an audited exclusion,
and storage-check order on the script. No on-disk format changes.

### PLAN-GAPs

- Existing decoder tests require an export-local `.work/`; added that fixture
  directory. No policy change. Startup's post-replay head can advance beyond
  the final confirm due to normal recovery, so the baseline assertion checks
  the staged generation and matching event instead of head equality.
- Historical onboarding 1439 does not represent the local first account marker;
  exercised it and 61/62 separately. The 40-point hosted difference remains
  unresolved, as the brief anticipated; no pin or point list was rewritten.
- Adjacent `test_journal_closed` and Mail `test_review_fixes_22` also pinned the
  old latch behaviour beyond the named modules. Updated only those expectations
  to the new contract and ran both modules, adding a healthy explicit status retry.
- The brief requires first-error preservation but does not spell out the ignored
  raw SQLite read-close case. Recorded storage-check order, scoped raw faults to
  each request and added an executable raw-I/O control rather than treating every
  fault site as a propagated storage error. Intermediate sample regressions are
  recorded above, with zero new keys after the correction.

Closing scratch scan: no files over 500 MB under `.work/` or `control/test-work/`.
No Gradle daemon was started. No installed/root/channel test, workflow dispatch,
OS owner module, boot tool, mount or live-service action was run.

---

**READY (BRIEF-RECHECK-1); owner answered board #352 "Yes (recommended)"; merged by the lead; next: the build (Codex gpt-6.1-sol xhigh, in the brief's steps)**. Lead: `linux-tools`.
Source baseline: main `4737bb69`, after `git fetch origin` and
`git merge --ff-only origin/main` (from `67bf1909`). Only the brief and this file
are committed. No product code, workflow dispatch or running-service change.

## Revision 1 — 2026-11-18

- **1. The write latch / Decision and exact change / Tests and oracle change:**
  kept the narrow durability predicate, including actual truncate-and-fsync
  success before indexing or SQLite. Added a request-local barrier before
  dispatch and at subsequent writable checks, including caught deferred-flush
  failures. Added the named zero-effects/next-explicit-request regression.
  **Build order and gates / Reviewer mutations** now require its baseline and
  barrier-removal mutation; all earlier mutations remain.
- **What must not change; overlapping work:** named package 43's canonical
  `['cli', 'control', 'log', ...]` channel-test dependency, which `linux-tools`
  lands with 43's Control change. Kept the historical `aresos log` oracle label
  and the re-pin's independence from 43. Updated #98, #97 and #58 (`beb42ec8`)
  to merged, and #72 to `f282553ba631`, retaining its whole-request `call_time`.
  Fetched main was `87d86471`; no merge was made in this brief revision.
- **Build order and gates:** executable exports go under ignored
  `control/test-work/302-exports/`, without dot-prefixed ancestors; logs remain
  under `.work/`. FilePolicy stays unchanged.
- **Question for the owner:** says “the failed save was completely undone,”
  includes the saved-cancellation example and freeing storage/fixing the disk
  followed by restarting the tool service, which resends nothing. “Yes” remains
  recommended because the barrier stops the failed request even after latch
  clearing. Items 2 and 3, the re-pin plan/expected shape and the “What must not
  change” rules are unchanged. No disagreement with `BRIEF-REVIEW-1`.

Checks for this revision (scratch: `.work/revision-302/`; bytecode disabled,
`TMPDIR` resolved inside its `tmp/`; the unit runner also has `PYTHONPATH`
resolved to `control`, `control/tests`, `control/mail_tests` in that order):

- `python3 .work/review-302/probe.py latch`: reproduced `latch-exact.log`:
  baseline zero DATA; narrow latch clear alone one DATA in the failed request.
  `python3 .work/revision-302/barrier-probe.py latch` against this worktree:
  adding the request barrier gave `storage_limit`, zero effects, unchanged
  journal, reserved operation and queued notice; the new healthy request gave
  `ok`, one DATA and one APPEND. Removing the barrier gave one DATA again.
  These are runtime scratch patches, not an implementation of the brief.
- `python3 .work/review-302/cli-probe.py`: removing the shortcut gave exit 2
  and zero proxy calls for `log`; `control log` gave exit 0 and one proxy call.
- `python3 .work/302/unit.py . base tests.test_owner_state_oracle tests.test_review22_storage tests.test_restore_batches`:
  **134 tests OK**, 41.669 s (`units.log`); restore peak bytes 217,066 / 217,069.
- Exported tracked Control and the existing pin with `git archive HEAD` into
  `control/test-work/302-revision-export/`, an ignored path without dot ancestors.
  With `REVIEW302_TREE` pointing there, `python3 .work/review-302/run.py mail test_owner_state_sweep.OwnerStateSweep.test_export_repeated_fault_uses_same_caller_path_and_exact_delta`:
  **1 test OK**, 0.522 s (`export.log`).
- Checked the cited production/test/oracle code, the current #72 engine diff
  and merged-commit ancestry. `git diff --check` passed. Full workflows, new
  implementation tests and the full mutation matrix remain the builder's work;
  none was dispatched or claimed here. No installed-channel, OS or mod tests.
- A structural comparison confirmed items 2/3, the complete re-pin section and
  the “What must not change” rules are unchanged; all 13 earlier mutation rows
  remain, with one barrier mutation added. No files over 500 MB remain under
  `.work/` or `control/test-work/`.

## Original brief evidence

Local evidence, 2026-11-17. Scratch output: `.work/302/current/`.
The unit runner uses the repo's managed-settings stand-in, as the prior package
documents. `TMPDIR` was set to `.work/302/current/tmp` and bytecode was disabled.

- `python3 .work/302/unit.py . base tests.test_owner_state_oracle tests.test_review22_storage tests.test_restore_batches`:
  134 tests, one subprocess import error because `PYTHONPATH` was not exported.
  The 10 storage/restore tests passed. The 1k/10k restore test printed peak bytes
  217,066 / 217,069. `base.log` holds the failure, not a green claim.
- With `PYTHONPATH` containing absolute paths to `control`, `control/tests` and
  `control/mail_tests`, `python3 .work/302/unit.py . base tests.test_owner_state_oracle`:
  **124 tests OK**, 1.093 s (`oracle.log`).
- `python3 .work/302/current/checks.py units`: all 11 unit tests of
  `test_owner_state_sweep` (excluding the full matrix), **OK**, 7.565 s.
- `python3 reviews/20-restore-lock-followups/repro.py` and
  `python3 .work/302/latch.py .`: second requests repeat `storage_limit` after
  faults end; restart clears the latch. The confirm remains locked before restart.
  First-append, fence-only, staged and applied cases were exercised.
- `python3 .work/302/current/checks.py startup`: a targeted test mutation bypasses
  only the staged-restore selection during initialization. At 26, 40 and 73 the
  real store unlocks; the mutant and decoder stay locked with no lock-view gap.
  The final run is `startup-final.log`. Earlier probes were too broad: skipping
  replay alone still cleared the lock and was detected; hiding pending events
  from reservation loading also broke replay at 74. Neither is the final probe.
- `python3 .work/302/current/checks.py h`: cancel at 69 gave head 6 / marker 5,
  store `failed`, model `reserved`, unlocked, write latch set (`h.log`).
- `python3 .work/302/sample.py . .work/302/current/sample.json restore/single/26/0/crash restore/single/73/0/crash restore/persistent/75/0/live restore/single/75/76/crash cancel/single/69/0/live cancel/persistent/68/0/live cancel/single/69/0/crash onboarding/persistent/1439/0/live`:
  8 sampled runs, 205 recorded keys. This is a recording of existing gaps,
  not a green full-sweep result. `python3 .work/302/points.py . restore cancel`
  recorded clean traces: restore 76 points, cancel 70. No sampled key ends in
  `.restore-lock`.
- The historical onboarding 1439 key was absent locally. `python3
  .work/302/current/checks.py onboarding-points` found 2,570 clean points (the
  published proof recorded 2,610). It identified the first account marker at
  61/62. `python3 .work/302/sample.py . .work/302/current/onboarding-h.json
  onboarding/persistent/61/0/live onboarding/single/62/0/live` recorded 64 keys.
  Both show the model counting zero catalogue rows while the store shows one.
  The local/hosted point-count difference has not been attributed to a cause;
  the builder must compare baseline and fixes on the same runtime.
- Both requested three-dot branch diff stats and their shared-file hunks were
  inspected. #98 and #97 were inspected with `git show`. Overlaps are in the brief.
- The current pin's SHA-256 matches `KNOWN-GAPS.md`. N7's historical full-matrix
  counts are attributed to its classification/recheck, not to this small sample.

Not run: full oracle workflow, full alteration matrix, installed-channel tests,
OS or mod tests. No boot tools, mounts, sudo or process-name kills. No file over
500 MB was found under `.work/` during the closing check.
