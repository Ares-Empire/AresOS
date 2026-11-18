# Empire brief 302 — progress

## Build part 1 (steps 1 and 2)

Status: **Build in progress; baseline established; next: step 2**.

### Done

- Step 1: baseline at `4a6acc2e`. `git fetch origin` returned exit 0;
  `HEAD` and `origin/main` both resolve to `4a6acc2e`, so no merge was needed.
  The branch is `pkg/302-store-oracle`. Baseline commit: this commit.
- Step 2: implementation and focused verification in progress.

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

Pending step 2.

### Left, in order

1. Step 2: finish item 1 and its local oracle checks.
2. Step 3: item 2, independent startup obligation and pre-confirm proof.
3. Step 4: item 3, applied history, lifecycle ordering and alterations.
4. Step 5: all remaining mutations and fresh reviews.
5. Step 6: merge current main, re-pin once, full capture and proof.
6. Final package/security reviews and independent classification review.

### What the code doesn't show

Local checks use synthetic fixtures and the managed-settings stand-in. They
prove no installed-channel/root behaviour, hosted point portability, whole-pin
classification, full sweep or alteration matrix. No workflow was dispatched.
No OS, boot, mounted-disk, owner-module or mod tests belong to this run.

### JUDGMENT-CALLs

The owner approved the brief's restart advice and continued visibility of saved
rows on board #352. No new product decision so far.

### PLAN-GAPs

- Existing decoder tests require an export-local `.work/`; added that fixture
  directory. No policy change. Startup's post-replay head can advance beyond
  the final confirm due to normal recovery, so the baseline assertion checks
  the staged generation and matching event instead of head equality.
- Historical onboarding 1439 does not represent the local first account marker;
  exercised it and 61/62 separately. The 40-point hosted difference remains
  unresolved, as the brief anticipated; no pin or point list was rewritten.

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
