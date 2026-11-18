# Empire brief 302 — progress

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
