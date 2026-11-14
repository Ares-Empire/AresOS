Reviewed PR #46 at `c2b70be0`, covering the whole branch against `origin/main` (merge base `16a0c886`) with the record and replay commits since review 7, and the fix `c2b70be0..e0d446c3`. The verdict is for head `e0d446c3`.

Reviewer: a fresh Claude agent on Fable 5.2 (final review before the laptop; updates and rollback). Read-only; committed by the integrator.

**Nothing blocking in the tools or the owner's pages.** The head I was given had red checks; `20c168be` closes that, and I verified it. Two should-fix findings are deliberately not for this branch: fixing them here would change the rehearsed bundle or a bound test for no gain in safety on the laptop. Five nits follow.

## Findings

**1. Blocking at `c2b70be0`, closed by `20c168be`: the head's own checks were red.**
- Hosted run 43619559359 failed three assertions in two tests of `test_ways_back_probe` and skipped one. I got the same three locally before its result was in.
- Both causes come from the record step, and neither is in a file the laptop runs:
  - The bound-sources test read removed paths from the waiting list's top-level `removed`, which the rebind had moved into its history entry.
  - `host-walk.json` binds `test_owner_path.py`, which the record step changed afterwards.
- **What it pointed at beyond the two symptoms:** the tree had not decided whether 22c's host-walk receipt is frozen at the rehearsal or kept fresh.
  - Frozen: `os/tests/test_checkout_sources.py:78`, the old `skipIf`, and `rebind`'s own check.
  - Fresh: `RunnerTest`.
  - Regenerating the walk would have turned `test_checkout_sources` red; the builder's attempt confirmed it.
- **The fix takes "frozen" throughout, and holds:**
  - `host-walk.json` is byte-identical to `f84041bf` and equals table 0 of the bindings.
  - The gate test (`os/tests/test_ways_back_probe.py:471`) passes only if the waiting list names every changed file the walk binds, and still refuses a stale receipt.
  - The skip is now an assertion (line 509).
  - Removed paths are read as `test_checkout_sources` reads them (line 1321).
- **Run at `e0d446c3`:** `test_ways_back_probe` 57 OK with none skipped, `test_checkout_sources` 6, `test_owner_path` 47, `test_owner_step_limits` 4.
- **Consequence, correctly in the report:** no further 22c VM dispatch can run without a decision, and `rebind` refuses a second record anyway. A tools change from here belongs to a new package with its own receipt.

**2. Should-fix, for tools version 4, not this branch: a cleanly stopped update leaves its intent open.**
- **Where:** `os/owner-tools/owner.py:1776` raises the stop routine's message; lines 1277-1284 then stop every other command.
- **What he sees:** the stop routine says "stopped safely … Nothing changes at the next start; run update again later". In the same start, `check`, `title`, `reboot`, `forward`, `previous` and `rollback` then all STOP with "interrupted before its result was recorded; do not reboot; run … update to continue it".
- **Why it matters:** the two lines contradict each other, and `at reboot` is refused although a restart is exactly what resolves it. If the cause persists (no network), he has no working command in that start.
- **Why not now:** it is inherited from version 2, where it was worse. With this bundle `update` can never stage, because R27 is installed. Nothing is lost, and any restart resolves it as "was not applied".
- **Fix:** when the stop routine ends with no errors it has proved the list is as before, so archive the intent there, as `start_next` does at line 1610. Add a test that `check`, `title` and `reboot` pass in the same start.
- **Verified:** by a scenario over the tests' modelled machine, for a step that fails before and after staging.

**3. Should-fix, with the next package that touches these tests: nothing mechanical keeps a tool or guide file off the waiting list.**
- **Where:** `check_waiting` (`os/tests/test_checkout_sources.py:38`) accepts any bound path. "Only test files and the CI workflow wait" is prose in `pending-rebind.json`.
- **Also:** no test compares the committed run's `tools_version_3` with the payload's fingerprint.
- **Why it matters:** the chain is honest today because I checked it by hand (question 4). Until the laptop install, a later change to a bound guide or tool could wait there while the status row still says VM REHEARSAL PASSED.
- **Fix:** one test that fails while that row says so and a path under `os/owner-tools/`, `os/release/` or `docs/` waits, or the result's fingerprint differs from `SHA256SUMS`.

**4. Nit: the report's frame is stale.** `REPORT.md:5` still says "Stages 1b and 2 are not started". The brief's closing "try this" note is not in it. The judgment calls are spread over twelve sections, and call 8 (owner decision 1, `update` goes anywhere) is superseded by `forward`. A short closing section would give the owner an exact list before merge. The file is unbound, so no rerun is needed.

**5. Nit, tools version 4: the layout refusal names a step that cannot work after a restart.** "Layout trial is unfinished; prove it or revert first" (`owner.py:1571`, `:1905`) now also answers `forward`, `keep-stock` and `reboot` after a restart, where proof and revert refuse and only `layout abandon` works. `title` passes without mentioning the trial. The emergency card covers it. Fix: when the trial is from an earlier boot, name `layout abandon` from a fresh login.

**6. Nit, next guide change: two pages send him only to keep-stock after abandoning a trial on plain Bazzite.** `docs/EMERGENCY.md:57` and `docs/INSTALL-PROCEDURES.md:107`. After a boot-menu start that makes plain Bazzite the next start, which he may not want. Nothing is lost and `forward` undoes it. Fix: offer "Back to AresOS from stock" beside it, as the recovery-menu section does.

**7. Nit: `docs/INSTALL.md:273` says "(power, closed window) … in the same start".** After a power cut there is no same start; the next check says "was not applied", which the check box covers.

**8. Nit, tools version 4: the same system changes name across the update.** The provisional title calls the running release "newer AresOS …" in its expected-rows line, the card asks for "the AresOS that ran before the update", and afterwards the same system is "older AresOS …". The short digest ties them and the row is always `(ostree:1)`. Marking that row "runs now" would remove the step.

## The six questions

1. **No bootable AresOS, lost stock, wrong next step, silent failure: none found.**
   - Reorders create and delete nothing.
   - The only deletions are a staged row by the stop routine (only when it is the sole row before the running one) and the other AresOS at finalize, announced before staging.
   - `switch`, `verify` and `prepare` refuse beside an installed AresOS before any change.
   - A reorder reports success only after `sync` and two re-reads of the list, by the script and by the tools.
   - Scenario walks (cuts, boot-menu starts, plain Bazzite, pair and triple) all ended in a state where each installed system was one command away.
   - Exception: finding 2. Finding 5 is a wrong word, not a dead end.
2. **`update` only stages and `forward` only reorders: yes.**
   - `update` has no path to `start_next`.
   - `forward` is `select` over the one reorder, and with something staged it refuses and leaves the stage alone.
   - Every reorder passes checksum, serial, digest, reference and the journalled list to `start-next.sh`, which refuses before `set-default` with exit status 3.
   - I ran the real `Host.script` with harmless bodies: 3 only for the refusal, 1 for an assertion or a failed child.
3. **The three states stay distinct: yes.**
   - "starts next, after the restart" with "is not finished until the restart".
   - "runs and now starts next; no restart is waiting" with no confirmation.
   - "confirmed after the restart" only from a later boot.
   - "is in place and has not started yet" for a later boot on another system.
   - The archives keep the same distinctions, and the VM transcript shows each one.
4. **The evidence chain is honest: yes.**
   - Run 43597505549 is `success` on `f84041bf`; its result names fingerprint `2084c786…`, which is `sha256(SHA256SUMS)` at head; `sha256sum -c` passes.
   - All 260 bound rows equal `f84041bf`'s checkout bytes (the `.ps1` in its CRLF form).
   - Nothing under `os/owner-tools`, `os/release` or the three guides changed from review 7's head through the rehearsed head to `e0d446c3`.
   - Since the rehearsal only the status row, two tests, the model test, the waiting list, the bindings, the captures and the report changed.
   - The waiting list now holds two files: `test_owner_path.py` and `test_ways_back_probe.py`, both with matching bytes.
   - The 156 capture files hold no tokens, addresses, hashes or names.
5. **The owner's pages match the tools: yes, apart from nits 6 to 8.**
   - The stick block in both places equals `bootstrap.py`'s output and `commands.json`; the fingerprint is in all four places.
   - Every line the changed boxes quote is what the tools print.
   - I replayed the failed-update card for finalize done, not done, and the wrong row taken; "check first" makes each branch right.
6. **Missing against the briefs:**
   - The report items in nit 4.
   - A hosted run on the final head, not yet dispatched.
   - As the brief accepts, no VM has seen version 3 stage a release or finalize over three rows; that is the next release's gate.

## What I ran

- **Local tests,** one process at a time on `c2b70be0`: `test_ways_back` 52, `test_ways_back_reverts` 20, `test_ways_back_compatibility` 21, `test_owner_equality` 10, `test_owner_path` 47, `test_checkout_sources` 6, `test_owner_bootstrap` 8, `test_shell_assertions` 9, `test_default_stock`, and the capture replay 4, all OK.
- **Raw captures:** I fed all 48 committed raw captures to the payload's own `qualified_state`. All were accepted, covering all six orders and 13 of 18 order-and-running combinations, with row numbers equal to list places.
- **Replay against the transcript:** 77 commands; every printed line equals the VM's except the one the report explains (the layout trial is not replayed).
- **Hosted:** the full model job is green on `0df34c8f`, whose `owner.py` is identical to the head's.
- **Merge:** main merges cleanly and has changed no bound file or owner tool since the merge base.
- **Not run:** `test_owner_update`, the model, any VM, and no owner tool, `ostree`, `bootc` or `rpm-ostree` command of any kind on this laptop.
- **Not verified:** the laptop's own boot path and ostree's `bootconfig swap: yes` path, which the calm test will show.
- **Side effects:** no repository file was changed. `git merge-tree` left one unreferenced tree object in the object store, and the suite's own temporary folders under `os/tests` were removed at exit.

Merge still waits for checks-only run 29 on `e0d446c3` to pass with nothing skipped.

SAFE
