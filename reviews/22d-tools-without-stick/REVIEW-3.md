Reviewed PR #66 step 4, `4cdd7b28..aff05fa1`.

Reviewer: a fresh Claude agent on Opus 5.5, read-only. I changed no repository file, pushed nothing and dispatched nothing. I ran no owner tool, sudo, ostree, bootc or rpm-ostree command. Committed by the integrator from my final message.

**In short:** both fixes are right, both tests fail when their fix is taken out, the pins agree, and the hosted run on `aff05fa1` is green, full model included. I found three nits and nothing above that. While I worked, the branch gained `5f9bde61` (review 2) and `9e72719b` (the brief's "Decisions after review 2"). Neither touches a file this step changed.

## Findings

**1. Nit: an archive write that fails halfway gives a message that doesn't match the state. Safe either way.**
- **Where:** `os/owner-tools/owner.py:1895-1904` (the archive in `stop_update`), with `archive` at `:1275-1280`.
- **What happens** (simulated on the fakes):
  - **The intent's file cannot be deleted** (or the folder sync inside `save` fails). The closed record is written, but the intent stays open.
    - The STOP says "stopping it did not finish: records: …". The other commands STOP with "interrupted … run update to continue it", which agrees with the open intent.
    - The next `update` closes the same intent a second time, as `retried`, and stages. So two closed records describe one intent. Harmless.
  - **The intent was deleted but the final folder sync fails.** The STOP still says "stopping it did not finish … Do not reboot; export records and get help". Yet in that start every command works. This is finding 2 in reverse.
- **Why it is only a nit:**
  - Both cases need an I/O error on the records folder just after a successful write.
  - The list had already been proved as before. If a power cut brings the intent back, the next start closes it as `not-applied`.
- **Fix:** none needed. If the wording is ever revisited, a records-only failure could say "stopped safely, but its record could not be closed; get help" without "Do not reboot".

**2. Nit: in the trial's own boot, once the original console is closed, the first wording names steps that refuse.**
- **Where:** `owner.py:71` (`LAYOUT_TRIAL`), used by `no_layout_trial` at `:1603-1615`.
- **What he sees:** in the same boot, after the administrator console that ran `begin` is logged out, the message says "prove it or revert first". But revert refuses ("Revert from the original open administrator session", `:2245`), and finish refuses too (`:2276`). Only `layout abandon` from a fresh login works.
- **Why only a nit:** this was already there before step 4 and is outside finding 5's wording. `begin` tells him to keep the console open, `check` names abandon, and the emergency card covers it.
- **Fix, optional:** add "; if the console that began it is closed, from a fresh physical administrator login run sudo /var/lib/ares/at layout abandon".
  - Normally a wording change costs a new fingerprint. The brief's new section already changes the payload for N3 and N4, so this could ride along for free.

**3. Nit: no test drives the third caller with a trial record from an earlier boot.**
- **Where:** in `os/tests/test_owner_update.py`, the tools-update cells at `:1190`, `:1393`/`:1405` and `:973` write `dict(phase='pin')` or `{}`. Those records have no administrator boot, so `system_ready` only ever shows the first wording.
- **What is covered:** the needle test (`:1479`) proves `system_ready` calls `checker.no_layout_trial()`. The helper itself is tested through `may_change` and `reboot` in `test_ways_back`.
- **Fix:** one cell (in `test_owner_sources` or `ToolsUpdateTest`) with `administrator.boot` set to another boot id, expecting `LAYOUT_TRIAL_RESTARTED` and nothing changed.

A small note, not a finding: `PROGRESS.md` says the errors test passes with the fixes taken out. Its two `record failed` cases fail without finding 2's fix, because they inject a failure into the archive call the fix adds. That is fine, and the file is deleted at the end anyway.

## The questions

**1. Finding 2: the intent is closed only after every part passed.**
- **Only after a full proof.** `if not errors` comes after all four parts: stopping the step, the diagnostics row, `reconcile_update`, `restore_masks`.
  - If the end of the step is not proved (`gone` False), `reconcile_update` does not run and an error is recorded, so nothing is closed.
  - `reconcile_update` returns without raising only in two cases:
    - nothing is staged (both views), there is no rollback queued, and the kept rows equal `before`;
    - this update's own staged row was removed and the list re-read equals `before`.
  - Rows are compared as whole dicts, so a changed pin also fails. Each mask this run removed must read `masked` through systemctl.
  - The only journal is the intent itself. The owner lock rules out another writer.
  - `step is None` means `Popen` raised, so no process exists that could stage after the check.
- **Kills and cuts never close it.** A kill or power cut (`PowerCut` is a BaseException) never reaches the routine. A STOP after a successful step ("Staged update identity mismatch", a failed status read, a failed record) is raised outside the routine. In all of these the intent stays open.
- **The archive runs inside `Deferred`,** so a closed window or Ctrl+C cannot cut it short.
- **The archive failing halfway:** see finding 1. Nothing unsafe either way.
- **After a clean stop, in the same start:** `test_ways_back` covers `check`, `title`, `reboot` and `update` before and after staging. My scratch run over the same fixtures added:
  - `forward`: "already starts next";
  - `previous`: queued;
  - `rollback`: queued;
  - restart then `check`: no notes, no intent, the one `stopped-not-applied` record and nothing else;
  - `update` afterwards stages.
- **What the archive changes for him:** the only difference from version 3 is the record left behind. `intend` had already closed any earlier record, as it did before, so nothing is lost.
- **The model:** it does not need a new event. A clean stop ends in a state the model already explores (same rows, no journal). Its cuts bypass the routine, which is why the slice counts did not change.

**2. Finding 5: the boot id is a reliable test.**
- **Where it comes from:** `administrator.boot` is written by `session()` at `layout begin` from `/proc/sys/kernel/random/boot_id`. Proof, revert and finish refuse on the same comparison ("Trial crossed a reboot").
  - So whenever the new wording appears, they really do refuse.
  - Whenever the first wording appears for a readable record, they pass their boot check.
- **"Record from this boot but the login not":** this cannot happen. The login is read in the same call that writes the boot id, and a login cannot survive a restart.
  - The nearby case that does exist is a closed console within the same boot: finding 2.
- **Versions 2 and 3** write the same field (checked at `41b06513` and `58738e5e`), so the tools update judges their trials correctly.
- **When the boot cannot be read** (not JSON, missing, not a string), the first wording stays and the command still refuses.
  - That is safe: in that state proof, revert and abandon would all fail on the same record, so no wording would help. Only "get help" would.
  - The record is root-only and written atomically, so I accept this.
- **The named command works:**
  - `layout abandon` takes a tty3 or tty4 `ares-recovery` login. After a restart that login counts as fresh by the boot difference.
  - It runs on the same AresOS and on plain Bazzite (tested on `S`), and after it the refused word passes.
  - `layout-abandon` is in `commands.json`.
- **The third caller needed it, and has it.** `system_ready` had the same text and the same dead end.
  - It runs before the tools journal and on resume in copy and publish, where the old tools are current and their abandon works.
  - It also runs at retire, where the new tools are current, and `main` lets `layout` run after `settle_tools`.
  - Leaving out "nothing changed" is right, because a journalled copy may already be there.

**3. The tests:**
- **Taking out each fix fails its test.** In scratch copies, each fix removed on its own:
  - Without finding 2's fix: the clean-stop test fails at both points, and so do the errors test's `record failed` cases.
  - Without finding 5's fix: the trial test fails ("…prove it or revert first" != "…began before the last restart…").
- **The `test_owner_update` edits** are right as I read them (they only run hosted):
  - `CLOSED` is exactly the two points that reach the routine. `observe` and `record` stay open.
  - `test_the_same_command_redoes…`: for `after`, the switch is counted twice. That holds because the intent is closed and `update` stages again.
  - Moving `test_other_commands_never_continue…` to `observe` keeps its point.
  - Patching `finalizer_masks` to `[]` stops the routine reading the runner's real `/etc` (on AresOS those masks exist).
  - `stopped_cleanly` and `stopped_with_errors` match the code.
  - The `system_ready` needle appears exactly once.
- **Hosted run 43677461596 on `aff05fa1`:** success (`gh run watch --exit-status` 0), including "Full ways-back model when its sources changed" (14m38s).

**4. The INSTALL.md sentence is true and plain.** `docs/INSTALL.md:330` now reads: "If the update STOPs with **was stopped safely**, nothing changed and every command works: run update again later, or get Help. If it is cut off before its PASS without that line (the command killed), the next command in the same start STOPs with **interrupted …; do not reboot** …".
- Both halves match the code.
- Dropping "(power, closed window)" is correct: a closed window lands in the stop routine, and a power cut leaves no "same start".
- A stop with errors keeps its own line ("Do not reboot; export records and get help"), and running `update` again after one is guarded, so the sentence needs no third case.
- This is the only "same start" sentence in the guides. Apart from fingerprint swaps, no other guide line changed.

**5. The pins:**
- **The fingerprint.** `sha256(SHA256SUMS)` is `e68fd5fd56fad619…cb75b`.
  - `sha256sum -c --strict` passes.
  - `owner.py`, `media.py`, `history.json` and `update.sh` are byte-equal to their payload copies.
  - It appears in `OWNER-TOOLS.md` (line 1 `Owner tools version 4: e68fd5fd`, line 2 full), `commands.json` (4), `INSTALL.md` (12), `EMERGENCY.md`, `INSTALL-STATUS.md` and the pending list.
  - `673803dc` is gone from `docs/` and `os/`.
- **`commands.json`:** `bootstrap.lines(fp)` and `bootstrap.command(fp)` equal `tools-folder`, `tools-routine`, `export-routine` and `install`.
- **The pending list:** all 23 rows match `aff05fa1`'s bytes. Every bound file the step changed is listed. The unlisted ones (`ways_back_ledger.py`, `OWNER-TOOLS.md`, `INSTALL-STATUS.md`) are not bound.
- **Coming next:** the brief's new section changes the payload again (N3, N4), so these pins move once more in a later step.

## What I ran

- **Tests,** Python 3.14, one module at a time, on a `git archive` copy of `aff05fa1` or in the worktree:
  - `test_ways_back`: 56 OK; the 4 new tests OK.
  - `test_ways_back_reverts`: 20 OK.
  - `test_ways_back_model` with `ARESOS_MODEL_SCOPE=slice`: 26 OK.
  - `test_owner_sources`: 12 OK.
  - `test_owner_bootstrap`: 12 OK.
  - `test_owner_equality`: 11 OK.
  - `test_owner_path`: 48. One test needs git history; it ran OK in the worktree.
  - `test_checkout_sources`: 6 OK.
  - `test_owner_step_limits`: 4 OK.
- **Not run:** `test_owner_update`, not even its classes through a library import.
- **Scratch scripts (fakes only), since deleted:**
  - each fix taken out on its own, then the four tests;
  - `forward`, `previous`, `rollback` and a restart after a clean stop;
  - the archive failing at `unlink` and at the folder sync.
- **Hosted:** `gh run list`, then `gh run watch 43677461596 --interval 60`.
- **Side effects:** the worktree is clean (its tests' temporary folders went at exit), and my scratch copies are removed.

SAFE
