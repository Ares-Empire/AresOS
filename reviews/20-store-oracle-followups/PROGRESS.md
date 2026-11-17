# Empire brief 302 — progress

**Brief written; next: brief review.** Lead: `linux-tools`.
Source baseline: main `4737bb69`, after `git fetch origin` and
`git merge --ff-only origin/main` (from `67bf1909`). Only the brief and this file
are committed. No product code, workflow dispatch or running-service change.

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
