# 22 REPORT: Update the laptop to a new AresOS release

Built by a Claude agent (Opus 5.5). Brief: `briefs/22-update-route.md`. Reviews go in `REVIEW*.md` next to this file.

Current tools manifest fingerprint: `712a571005f1c2a9d743fba77a1b1bb8ecffbec499078d42015820b223a23cf4`.

## Done

- **Release history** (`os/owner-tools/history.json`, new payload file):
  - `tools_version` (now 2) and the ordered, append-only list of AresOS releases the tools know. Each record holds the reference, the signature identity and its own `daily_wheel` rule. R13 is `false`.
  - Its last record must equal `release.json` (reference and identity), so the target always arrives through the fingerprinted bundle. Nobody types a digest.
  - Strict parsing: exact fields, a real boolean (never "either"), the `ghcr.io/ares-empire/aresos` reference and an Ares-Empire workflow identity, unique digests, no stock digest, no duplicate JSON keys.
  - The release package appends 21's record with `daily_wheel: true` when it pins 21 in `release.json`.
- **`at update`** (`owner.py` `update`/`before_update`, `os/release/update.sh`):
  - Runs on a running AresOS that `check` accepts. Before any change it requires: no layout trial, `idle` (no transaction, no rpm-ostree/bootc/ostree client), an accepted deployment shape, no staged deployment, no queued rollback, a known running release older than the target, the target not deployed yet, no layered or unlocked AresOS deployment, and BLS entries that match the deployments.
  - Then it checks the saved registry login can read the target manifest (`stored_login`; the secret is never recorded). A missing, expired or unreadable login refuses with "Registry login missing, expired or unreachable: run sudo /var/lib/ares/at login, then run this command again; nothing was changed".
  - Then the unchanged `verify` script (cosign, identity, digest) and `bootc switch --retain` to the target, with a recheck that the running release has not changed.
  - Afterwards it requires the exact staged target, the same booted deployment and retained deployments equal to before, and refreshes the title.
- **`at previous`** (`os/release/previous.sh`): only in the three-deployment shape with the booted release newer than the other one. It checks bootc's rollback slot is that exact release (image, digest, checksum, unpinned), runs `bootc rollback`, requires the queued state with unchanged identities and flags, and refreshes the title. It refuses the reverse (going "forward" after a return) and anything pending.
- **Shapes** (`qualified_state`, now with an optional `history`; without it the rules are exactly the old ones):
  - Accepted besides the old shapes: an update staged over a running release (stock pinned last, at most one older AresOS between), the three-deployment state after the reboot (new booted, old rollback, stock pinned last), and the queued return to the previous release.
  - Refused: stock booted beside two releases, stock not last, unknown or duplicate releases, a pinned or re-originated AresOS, two staged rows, a staged release that is not the target, a queued staged state, a wrong rollback slot, four deployments without a stage.
  - `preflight_recovery` (rollback, keep-stock, layout) accepts any known release in the AresOS/stock pair, so newer tools keep the stock recovery working before the update. It still requires the exact pair.
- **Per-release account rule** (`check`): the booted release's own record decides; `wheel` membership must equal `daily_wheel` exactly. Stock still runs `stock-session`; an unknown booted image STOPs.
- **`at login` on AresOS**: the stock path is unchanged. On a running AresOS it requires the full update preflight, so a login only serves an update to a newer target.
- **Tools updating themselves** (`install` then `update_tools`):
  - The same bootstrap block runs `at install` from its verified private copy. An existing, completed installation with other tools becomes an update; the first-install route is unchanged for no installation, an unfinished one, or a rerun of the original bundle.
  - Before any write it checks the stick, the installation files, the recorded disk identity and the entry point. The new `tools_version` must be higher than the installed one (the 15f tools count as version 1 and are accepted only by their exact fingerprint `3ef85c4a…`), and the installed history must be a prefix of the new one. The new tools must accept today's deployment state (idle, shape, no layout trial, no unfinished prepare).
  - Journalled in `/var/lib/ares/tools-update-intent.json` (copy, swap, records, complete) and resumable after an interruption at any step, only with the same bundle and stick. The old tools move to `/var/lib/ares/retired-tools/<fingerprint>`; nothing is deleted. A receipt `<time>-tools-update.json` goes into the records once. A repeat says "Tools already installed; nothing changed".
  - Older or same-version tools, a rewritten or shortened history, or an unknown history-less bundle STOP with nothing written. The 15f tools themselves cannot downgrade an updated installation: their unchanged install route refuses the new files before writing (tested on that same route in the current code).
- **`install` refactor**: the stick check and the partial-copy cleanup and sealing moved into helpers (`tools_stick`, `discard_partial_copy`, `seal_copy`) shared with the update; behaviour unchanged (the existing install, resume and placement tests pass).
- **Commands**: `update` and `previous` in `owner.py`'s dispatcher and `commands.json`. Payload regenerated with `bundle.py --refresh`; the fingerprint above is in `docs/INSTALL.md` (step 4 copy check and bootstrap line 8, and the same two places in the update route), `commands.json` and `docs/INSTALL-STATUS.md`.
- **Guide**:
  - `docs/INSTALL.md` step 8, "Update AresOS to a new release": its own gate (STEP 5 COMPLETE and a checked running AresOS), then eight boxes: Windows side (rename the old stick bundle, `Copy-AresOwnerTools`, fingerprint), the 13-line bootstrap, `at update` (with the login refresh on a login STOP), `at title` and `at export`, `at reboot` and F12 to Bazzite, `at check`/`title`/`records`, the one-time `ares` password (`sudo passwd ares`, lowercase a–x and top-row digits, never recorded) and `at previous`. PASS/STOP and returns in each.
  - `docs/EMERGENCY.md`: new "Failed or bad update" (Windows then Help if it does not start; `at previous` if it starts but misbehaves; never a guessed GRUB title or a repeated update), and the update case in the hang card.
  - `docs/INSTALL-PROCEDURES.md` and `docs/INSTALL-REFERENCE.md`: the three-deployment limits of the recovery menu, rollback, keep-stock and layout trials; update-route returns from the console and hang references.
  - `docs/INSTALL-STATUS.md`: steps 4–7 as they happened (from `STATE.md`, no private values), step 7's brightness (#139) and power-button (#140) items OPEN, the hardware, keyboard, Windows-record, shortcut and reader rows brought up to date, and a package 22 row (built, not used, nothing released).
- **Tests**:
  - New `os/tests/test_owner_update.py` (26 tests at first, 34 after the review fixes): the bootc list model checked against every retained package 13 stage; accepted and refused shapes; history validation; `update` success (first and later update) and every refusal with zero changes (staged, queued rollback, queued previous, nothing newer, booted stock, target deployed, unknown running release, layered, unlocked, missing login, expired login, unsigned, wrong identity, active client, transaction, layout trial); a stale title blocks the reboot; `check`, `title` and `reboot` on every update shape; the per-release wheel rule both ways; `previous` success and refusals; `login` on AresOS; tools update, rerun, newer-over-history, downgrade, same version, rewritten and shortened history, unknown legacy, refused state, interruption after every copy, rename and record write, mismatched resume, and the unchanged install route refusing an updated installation.
  - `test_owner_path`: the route walker models the update gate (no `login`, `switch` or `update` line without the step 5 proof, the update command only inside the gated route, the gate's STOP outside it), plus the update route's order, PASS, STOP and returns, the failed-update card and gate mutations; the Stage C test now pins steps 5–7 and the open items.
  - `test_owner_equality`: both bootstrap copies must equal the tested block (mutating either copy, or dropping one, refuses); this report is the current fingerprint report; `update` and `previous` are listed as not yet typed by a rehearsal.
  - `test_owner_entry`: the two new handlers are patched like the others.
- **Bound sources**: `os/manifest/ci/16/pending-rebind.json` lists the 14 bound files that now differ from the package 16 walk, with exact checkout hashes from `checkout_sources.records` (new in the list: `bundle.py`, `test_owner_entry.py`). The walk tables are unchanged. It also lists `unwalked_commands` (`update`, `previous`).

## Verified

- **WSL full suites** (Ubuntu, Python 3.12.3) on a fresh `git clone --depth 1 -b pkg/22-update-route` of the pushed head `7e15d8ab`:
  - `python3 -m unittest discover -s os/tests`: `Ran 715 tests`, `FAILED (failures=1, errors=9)`.
  - `python3 -B -m unittest discover -s os/tests`: `Ran 715 tests`, `FAILED (failures=1, errors=9)`.
  - In both runs the failures are exactly the known WSL-only set, also on main: `test_greeter` (3 errors), `test_inherited_homebrew` (1 failure + 5 errors), `test_sysusers` (1 error). Everything else passes, including `test_checkout_sources`, `test_owner_equality`, `test_owner_step_limits`, `test_owner_path`, `test_owner_update`, `test_owner_entry` and `test_owner_walk`.
- **Focused WSL runs** during the work (a mirror of the worktree in WSL `/tmp`): `test_owner_update` 26 OK, `test_owner_path` 39 OK, `test_owner_equality` 9 OK, `test_checkout_sources` 4 OK, `test_owner_step_limits` 4 OK, `test_owner_entry` 3 OK, `test_owner_walk` 9 OK, `test_owner_devices` 6 OK, `test_owner_diagnostics` 10 OK, `test_owner_export` 3 OK, `test_owner_tools` 13 OK, `test_owner_commands` 6 OK, `test_owner_setup_resume` 9 OK, `test_owner_finalize` 9 OK, `test_owner_retained` 5 OK, `test_owner_hidden` 10 OK, `test_owner_bootstrap` 6 OK. After the last edit of this report, `test_owner_equality` and `test_owner_path` were rerun on the final head (see the PR).
- **Windows PASS lines**: `pwsh -NoProfile -File os/tests/owner-pass.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/22-ps` (fixtures only, ordinary terminal, no storage queries) printed `PASS 6 documented Windows PASS results equal captured entry stdout; no hardware queries.`; the update route adds two of the six. The scratch folder was removed.
- **Bundle**: `python os/owner-tools/bundle.py --refresh` printed `PASS bundle manifest SHA256 712a571005f1c2a9d743fba77a1b1bb8ecffbec499078d42015820b223a23cf4`; the same fingerprint is in `commands.json`, both bootstrap copies and both copy checks in `docs/INSTALL.md`, INSTALL-STATUS and this report.
- **Bound sources**: `checkout_sources.records` (Windows Python 3.13) recomputed the 14 pending files; its `.work/` scratch was removed. No `.work/` is left in the worktree.
- **Push**: the local privacy pre-push hook passed.

## Not verified

- No real update ran anywhere: no newer signed release exists. Staging, finalization and `bootc rollback` lists are modelled from the retained package 13 fixtures and the retained OSTree and bootc sources (`ostree-src_libostree_ostree-sysroot-deploy.c`, `bootc-crates_lib_src_deploy.rs`, `bootc-crates_lib_src_cli.rs`), not run. The release package's VM rehearsal must run update, reboot, check and previous before the first real update.
- The saved login format (`/etc/ostree/auth.json` as `{"auths": {"ghcr.io": {"auth": base64}}}`, written by `podman login --authfile`) is the documented containers-auth format but was not read on the laptop. If it differed, `at update` would refuse pointing to `at login`, and the loop would end at Help with nothing changed.
- `passwd`'s success line ("… updated successfully") and `sudo -v` for `ares` need the release where `ares` is in wheel (package 21).
- The Windows `Rename-Item` line was not run against a real stick; `Copy-AresOwnerTools` itself is unchanged.
- Phone readability of the new route: only the local route tests.

## JUDGMENT-CALL

1. **Later updates drop the AresOS two releases back.** *Owner: accepted (board #154, 2026-11-09).* From the three-deployment state, OSTree's finalization keeps the new, booted and pinned deployments and removes the older unpinned AresOS (the retained `ostree_sysroot_simple_write_deployment` call with `NO_CLEAN`). I accept that shape, and `at update` prints which release goes, so every later release can update. Rejected: refusing it (blocks every update after the first), or a separate retire command (more code and a new mutation). The brief's "No other deployment may be lost" holds for the first update only. Changing it later: remove the four-deployment staged shape and the message (a few lines and tests).
2. **Release records live in the tools' `history.json`**, not in `release.json` (out of scope here). The release package appends each release with its `daily_wheel`; tests force the last record to equal `release.json`. Alternative: a field in each `release.json`, which would still need R13's rule somewhere.
3. **`at previous` is its own command**; `at rollback` stays "back to stock" from the pair. Rejected: making `rollback` depend on the deployment count (same word, two outcomes, read on a phone).
4. **After an update the stock recovery tools stop applying.** *Owner: accepted (board #154, 2026-11-09); follow-up 22c extends them before the second update.* Rollback, keep-stock (and so the recovery menu) and layout trials keep requiring the AresOS/stock pair and refuse with three deployments. The way back is `at previous` or F12, Windows, Help; the stock deployment stays pinned and bootable. Extending them means new mutation paths (for example `ostree admin set-default`) that need a VM rehearsal. Documented in the guide, card and procedures.
5. **Tools update through `at install`**: no serial prompts (the recorded disk identity is rechecked), newer tools only, the old tools kept privately in `retired-tools/` rather than deleted, a journalled two-rename swap. Alternative: a new bootstrap verb, which would change the pinned 13-line block.
6. **The old stick bundle is renamed on Windows** (`ares-tools-replaced-<date>`), not deleted, because `Copy-AresOwnerTools` refuses an existing folder. Rejected: changing the reviewed Windows module.
7. **The updater check is `idle` only** (the brief's "reuse idle"); the stock pause check (`paused_state`) is not run on AresOS, whose image masks its updaters.
8. **The update gate asks for STEP 5 COMPLETE** (the owner has it) plus a checked running AresOS, so the route walker keeps one proof for every authentication.
9. **`bootc switch --retain`**, exactly as the first switch. In the retained bootc source `--retain` only affects an ostree refspec origin, so container deployments behave the same either way.
10. **The login pre-check** reads the saved credential to test it against the target manifest before cosign, so an expired token gets the login pointer and a signature failure never does.

## PLAN-GAP

- The brief's three-deployment rule does not cover the second and later updates (JUDGMENT-CALL 1) or the stock recovery after an update (JUDGMENT-CALL 4).
- `test_owner_equality` requires every command to be typed by the package 16 walk, which cannot type `update` or `previous` before a newer release exists. `pending-rebind.json` now lists them in `unwalked_commands`; the test refuses a listed command once a rehearsal types it, so the release package's rehearsal must walk them and empty the list.
- The release package must: append 21 to `history.json` (`daily_wheel: true`), pin it in `release.json`, regenerate the payload and fingerprint (step 4, the update route, `commands.json`, INSTALL-STATUS, the current report), and rehearse update, reboot, check and previous in a VM.
- INSTALL-STATUS's tools-stick lifecycle row is unchanged: `STATE.md` has no step 5–7 stick facts.

## Open questions

- None. The owner accepted JUDGMENT-CALLs 1 and 4 (board #154, 2026-11-09).

## Review fixes (review 1, CHANGES-NEEDED at `ab5850ec`)

Brief `briefs/22-review-fixes.md`; review `REVIEW.md` (gpt-6-astra, high). JUDGMENT-CALLs 1 and 4 are unchanged, as the owner decided.

1. **Blocker, false update confirmation.**
   - `update` and `previous` now write `records/outcome-pending.json`: the kind, this boot's id, the deployment list before, the staged or queued list, the list the restart must produce (update: new, running, stock; previous: the queued order) and the deployment that must boot.
   - Every command that reads the deployment state compares it: `check`, `title`, `records` (through `title`), `reboot`, `update`, `previous`, `login` on AresOS, `rollback`, `keep-stock`, `layout begin`/`abandon` and the tools update. In the same boot the exact staged or queued list must still be there. After a restart only the recorded release, booted, in the recorded order, with nothing staged or queued, passes; `title` then saves `<time>-outcome-confirmed.json`, removes the pending record and prints "Update to … confirmed after the restart" (or "Return to …").
   - Anything else STOPs before any change: "The update to … did not finish at the restart (another deployment runs / it is still pending); do not repeat it; export records and get help: EMERGENCY Failed or bad update". An older booted release, a still-staged update and a still-queued return all STOP. The one way on: if the restart left exactly the pre-change list, the same command may run once more (after Help); the old record is kept as `-outcome-retried`.
   - `media.py`: export lets `outcome-pending.json` change between exports, like `title.json`.
   - Guide and card: the check box requires the confirmation line; a "did not finish at the restart" STOP goes to the failed-update card, and only Help decides on a repeat.
   - Tests: confirmation only after the recorded new start; failed finalization (the old list is back after the restart) STOPs `check`, `title`, `records`, `reboot`, `rollback`, `layout begin` and `previous` with nothing changed, then the retried update is confirmed after the next start; a still-staged update after the restart; a list changed before the restart; an unsuccessful `previous` (still queued, or the queue lost), its retry and its confirmation.
2. **Blocker, concurrent owner commands.**
   - `main()` holds an exclusive `flock` on `/run/ares-owner.lock` (created 0600, never through a link, ordinary file only) for the whole command, the bootstrap's `install` included. A second command STOPs at once: "Another owner command is running; let it finish, then run this one again".
   - `update` reruns its whole preflight (layout trial, `idle`, shape, outcome, nothing staged or queued, BLS) immediately before staging and requires the deployment list unchanged since its first check.
   - Tests: the real lock (a second holder refused, released after close, a link refused); the real dispatcher runs `at update` while `at layout begin us`, started during verification, is refused with no trial record, and the update then completes; a layout trial, a transaction, an outside stage, a queued rollback or a changed list appearing during verification refuse before staging.
   - The in-process `main()` tests (`test_owner_entry`, `test_owner_diagnostics`) point the lock at a temporary file, because an unprivileged test cannot write `/run`.
3. **Should-fix, resumed tools update.** The system preflight (no layout trial, prepare complete, `idle`, and the new tools accept the deployment state, outcome included) now runs on every resume, before the copy, the swap or the receipt. Test: interrupted in the copy phase, between the two swap renames, and after the swap, then a transaction, a layout trial or an unknown staged image appears: the resume STOPs with `/var/lib/ares` unchanged, and after that change is undone it completes.
4. **Should-fix, legacy rule.** The 15f tools migrate as R13 with `daily_wheel: false`; `extends` compares the rule exactly, without a wildcard. Tests: a legacy bundle reads as exactly the reviewed R13 record, and a bundle that rewrites R13 as administrator is refused (unit test and tools update).

New tools fingerprint `712a571005f1c2a9d743fba77a1b1bb8ecffbec499078d42015820b223a23cf4` (step 4 and the update route in `docs/INSTALL.md`, `commands.json`, INSTALL-STATUS, this report). `pending-rebind.json` now lists 17 files (new: `media.py`, `payload/media.py`, `test_owner_diagnostics.py`), with exact hashes from `checkout_sources.records`.

Verified for the fixes:
- WSL full suites on a fresh clone of the pushed head `384abe37` (code identical to the final head; only this report changed after), each started only with at least 4 GB free and no other suite running: plain `Ran 723 tests`, `FAILED (failures=1, errors=9)`; `-B` `Ran 723 tests`, `FAILED (failures=1, errors=9)`. Both are exactly the known WSL-only set: `test_greeter` (3 errors), `test_inherited_homebrew` (1 failure + 5 errors), `test_sysusers` (1 error).
- Focused WSL suites before the push: `test_owner_update` 34 OK, `test_owner_path` 39 OK, `test_owner_equality` 9 OK, `test_checkout_sources` 4 OK, `test_owner_step_limits` 4 OK, `test_owner_entry` 3 OK, `test_owner_diagnostics` 10 OK, `test_owner_export` 3 OK, `test_owner_devices` 6 OK, `test_owner_hidden` 10 OK, `test_owner_setup_resume` 9 OK, `test_owner_walk` 9 OK, `test_owner_tools` 13 OK, `test_owner_finalize` 9 OK, `test_owner_retained` 5 OK, `test_owner_commands` 6 OK.
- Windows: `owner-pass.Tests.ps1` (fixtures only) printed `PASS 6 documented Windows PASS results equal captured entry stdout; no hardware queries.` with the new fingerprint; its scratch folder was removed.
- The earlier full-suite results in "Verified" above belong to `7e15d8ab`, before these fixes.
