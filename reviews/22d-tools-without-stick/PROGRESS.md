# 22d progress

Kept by each step's builder: done, left in order, what the code doesn't show. The last step deletes this file.

## Step 1 (the tools), 2026-11-15, Claude agent on Fable 5.2: done

Brief row 1: decisions 6 and 7 in `os/owner-tools/owner.py` and `media.py`, tools version 4, their tests.
No PLAN-GAP: the brief, the note and the code agree where behaviour is concerned.

### What changed

- **The route** (`owner.bundle_source`, `main`): the start block that ran decides. The stick block leaves its mount
  `m` beside the private copy, the folder block has none; `main` reads that and hands `install` the word `stick` or
  `folder`. Anything named `m` counts as the stick block, so doubt gets the stricter rules.
- **Stick block:** every rule as before (terminal, the labelled stick, one mount, the same bundle), same messages.
- **Folder block:** no terminal test, no stick. An attached stick is not looked at (no `lsblk` label query runs).
- **The first installation** refuses on the folder route before any prompt, with or without a terminal:
  `The first installation runs only from the tools USB at the recovery console; nothing changed`.
- **The journal** keeps schema `tools-update1` and all eight fields and gains `source` (`stick` or `folder`). The
  stick's volume UUID stays where it was, in `tools_volume_uuid`; for the folder that field is `null`. Nothing else new
  is written under `/var/lib/ares` before publication. `settle_tools` is unchanged and does not read `source`, so a
  later version can add a third source without making version 4's recovery refuse.
- **Resume:** an update begun from the folder resumes from either block. One begun from a stick resumes only from
  that stick; from the folder it stops with
  `Interrupted tools update began from the tools USB; finish it from that stick at the recovery console`.
  A journal without `source` (written by older tools) counts as begun from the stick.
- **The receipt** (`*-tools-update.json`) gains `source` (where the update began), `finished_from` (the block of the
  run that wrote the receipt) and `caller` (`login_uid` from `/proc/self/loginuid`, `terminal` true or false).
- **`export` without a stick** writes a checked copy to `/run/ares-records`: root-owned, folder 0700 and files 0600,
  each copy read back by SHA-256, then one grant for the calling login uid
  (`setfacl --recursive --modify user:<uid>:rX`). With no login uid, or root's, the copy stays root-only. An earlier
  export's folder is replaced whole. Its three lines:
  - `Tools stick absent: records copied to /run/ares-records with SHA256 readback`
  - `This copy is on this laptop, not off it; uid 1001 can read it, and a restart deletes it`
  - `For a copy off the laptop plug in the tools stick and run export again`

  They never contain `SAFE TO REMOVE` or `ARESTOOLS`: only a stick export says those words.
- **`export` to a stick** accepts the installed bundle and every bundle this laptop installed before, each verified
  in `retired-tools/<manifest>`. For such a stick it adds one line before `SAFE TO REMOVE ARESTOOLS`:
  `The stick holds tools this laptop installed before (SHA256 …), not the installed ones`. Any other bundle is
  refused as before (`Tools manifest differs; do not copy records`).
- **Tools version 4** in `history.json`; the payload is refreshed. Its fingerprint at this commit is
  `673803dcfb0154d79f386491aa407f173edb903d67ee6f108e729151f9ced228`. It changes with every later change to a
  payload file, so step 2 pins the one it finds.

### What the code doesn't show

- **`at install` through the installed entry** (review 1's nit) follows the folder rules, because nothing named `m`
  lies beside an installed toolset. With the same bundle it answers `Tools already installed; nothing changed`
  without a terminal or stick (before: it asked for both). It finishes an update that began from the folder and was
  cut after publication. A first-installed bundle run again that way gets the first-installation refusal above.
- **A bug the new tests caught:** `update_tools` already had a local variable named `source` (the old tools being
  retired). It is now `leaving`; the parameter keeps the name.
- **`install` and `update_tools` default to `stick`** for callers that name no source (tests, `os/ci`). So the
  existing stick fixtures run unchanged and prove the stick route is as it was. Only `main` decides in production.
- **The grant's real effect is not proven by a test.** The tests assert the exact `setfacl` call through a stand-in
  host. I tried the same flags by hand on a scratch folder on tmpfs: folder `user:1000:r-x`, file `user:1000:r--`,
  nothing for others. Step 6's VM walk should assert that `ares` can read `/run/ares-records/*.json` and that
  another account cannot. `setfacl` is in the image (`acl`, `os/manifest/ci/packages.txt:39`). If it fails or is
  missing, export stops after the copy was made and the copy stays root-only.
- **The receipt's `finished_from`** is not in the brief. It is there because a folder update finished from the stick
  would otherwise read as "folder, with a terminal".
- **`media.export`'s third argument** is now the list of accepted fingerprints (installed first), and it takes the
  reader's uid. Both live in the same bundle, so no older caller exists.

### Tests added, and what ran here

Run from the repository root, one module at a time, Python 3.14 on the laptop.

| Module | What | Result here |
|---|---|---|
| `os/tests/test_owner_sources.py` (new, 12 tests) | The block decides the route through the real `main`; the caller; the folder route without terminal with the fixture's stick attached and never queried; the stick route's refusals; the first installation refused on the folder route with and without a terminal; resume from each block at every one of the 30 events of an update, for all four pairs; another stick, another bundle and an unknown source; a journal without `source`; version 2 and 3 bundles exactly as at `41b06513` and `58738e5e`; version 4 over each of them from both blocks in both layouts (the laptop's `tools-<fingerprint>` with a completed journal, and `tools`); versions 2's and 3's own `settle_tools` over version 4's journal at every cut before publication (21 or 22 per case, 8 cases), then version 4 resumes; `Tools.export`'s accepted list | `Ran 12 tests in 91.981s`, `OK` |
| `os/tests/test_owner_export.py` (3 new, 6 in all) | A stick with a retired bundle accepted, a foreign one refused, also when found mounted; the copy under `/run`, its three lines, modes, the one grant, replacement, the refusals; the same through the real entry in a fresh process | Natively 3 pass, 3 fail. Two of the three failed before this step (the fixtures patch `Path.stat`, and Python 3.14's `lstat` no longer goes through it); the third is the new test on the same fixture. With `Path.lstat` set to Python 3.12's behaviour in a scratch runner: `Ran 6 tests`, `OK` |
| `os/tests/test_ways_back_compatibility.py` (version pins only) | Version 2 to 4 on the stick route over all 13 historical shapes; version 2 settles every cut | `Ran 21 tests in 49.192s`, `OK` |
| `os/tests/test_owner_devices.py`, `test_owner_setup_resume.py` (untouched, they call `install`) | The first installation from the stick | 6 `OK`; 9 run with the same 6 errors as at `9d11c069` (`case_sensitive`, Python 3.14) |
| `os/tests/test_owner_bootstrap.py` (untouched) | | 7 pass, 1 fails as expected (below) |
| `os/tests/test_owner_update.py` | The refusal table now runs every row for both sources (`FOLDER_REFUSING` holds the one message that differs); the fixture takes `source` and `run(other)`; version pins follow the payload | **Not run here**, by the rule. Its fixture is exercised by the two modules above that import it. The table itself first runs in the hosted checks. A stubbed local run of the table was refused by the session's permission check, so I did not do it |

### Expected red until step 2 (pins, `commands.json`, guides)

The payload's fingerprint changed and step 2 owns the pins. From reading the tests, not from running them:

- `test_owner_bootstrap.test_documented_command_is_generated_from_complete_system_manifest` (seen red here)
- `test_owner_equality` (the blocks in `commands.json` and the guides against the payload)
- `test_owner_path`, `test_owner_walk` and any guide test that quotes line 8 or `2084c786…`
  (`docs/INSTALL.md`, `docs/INSTALL-STATUS.md`)

### Expected red until a later step (the integrator's call)

- `test_checkout_sources`: ten files that 22c's walk binds now differ (checked against
  `os/manifest/ci/22c/source-bindings.json`): `owner.py`, `media.py`, `history.json`, the five payload files that
  follow them, and two test files (`test_owner_export.py`, `test_owner_update.py`). The waiting list's own rule
  admits only test files, and tool files wait for 22d's receipt (step 6). I did not run `rebind.py pending` and
  did not run this module.
- `test_ways_back_probe` (22c's frozen receipt names `tools_version_3` as this checkout's payload) and
  `os/ci/owner_vm.py:2146` (`(2, 3)`): step 6's harness and receipt.
- `test_ways_back_model` selects the full model for this branch (`owner.py` changed), as for any tools change.

### JUDGMENT-CALL (for the owner, at the "try this" stage)

The words of the new lines he or Claude will read: the three `export` lines, the line for a stick with older tools,
the first-installation refusal and the stick-only resume refusal (all quoted above). Chosen to say what happened and
what to do next in one line each. Changing them later costs a new tools version and the guides that quote them.

## Step 2 (lines, labels, pins, guides), 2026-11-15, Claude agent on Opus 5.5: done

Brief row 2 (decisions 2, 3, 4, 5, 8, 9, 10 and the guide parts of 6) and the integrator's items A to C.
No PLAN-GAP.

### What changed

- **`bootstrap.py`** generates, besides the stick block (unchanged but for v4's fingerprint):
  - `tools_folder` (`commands.json` `tools-folder`): Claude's line as `ares`, no window, `/usr/bin/bash -c '…' tools-folder`
    with the announced commit's full hash appended as its only input. Under `set -euo pipefail`, `PATH=/usr/bin:/bin`:
    a 40-hex hash, `cd /var/home/ares/AresOS`, `git fetch origin +refs/heads/main:refs/remotes/origin/main`, the commit
    an ancestor of `origin/main`, `git diff --quiet <commit> -- os/owner-tools` (the dirty or stale refusal: the root
    line Claude copies from that checkout's `commands.json` is then the commit's), `rm -rf` and `mkdir` of
    `/var/home/ares/ares-tools`, `git archive <commit>:os/owner-tools/payload | tar -x`, then
    `echo "<fingerprint>  SHA256SUMS" | sha256sum -c --strict`. Each refusal prints one `STOP tools folder: …` line
    and comes before the folder changes; any other failure prints `STOP tools folder: refused, nothing was installed`.
  - `tools_routine` (`tools-routine`): `SUDO_ASKPASS=/usr/bin/ksshaskpass /usr/bin/sudo -k -A -p '<label>' bash -c
    '<script>'`, the script being the folder block byte for byte (12 lines), then
    `trap "echo STOP after install: check or title refused" ERR`, `/var/lib/ares/at check`, `/var/lib/ares/at title`.
    One window per go; the first STOP ends it.
  - `export_routine` (`export-routine`): the same prefix around `/var/lib/ares/at export`.
  - `label(fingerprint, action)`: `AresOS owner tools <8 hex>: <action>`, letters, digits, spaces and commas only
    around its one colon (sudo expands `%` in a prompt; a quote would change the line's quoting).
- **`commands.json`** holds the three lines after `install`. They wait under `unwalked_commands` in
  `os/manifest/ci/16/pending-rebind.json` until 22d's rehearsal types them (step 6).
- **`docs/OWNER-TOOLS.md`**: line 1 `Owner tools version 4: 673803dc`, line 2 the full fingerprint, a blank line, then
  two sentences. On GitHub lines 1 and 2 render as one paragraph; the 8 characters still follow the colon.
- **The guides.** `docs/INSTALL.md`'s update route: the gate defines the announced commit (the maintainer's board note
  with full hash and fingerprint; Claude installs only that). A new first box, **New tools from Claude's terminal**:
  Claude's folder line, then the one routine line; the window as it looks (title bar **Enter SSH Credentials**, the
  label inside, Password, OK, Cancel); his rule (go just now, the label, the 8 characters against line 1 of
  OWNER-TOOLS.md on GitHub on his phone); the limit in plain words (stops accidents and a Claude acting unasked, not a
  tricked Claude; after one password such a program can do anything as administrator, later too; the stick boxes are
  his alternative); the three PASS lines; the board note with the title's lines under topic `aresos`; the 10-minute
  rule; the STOP rule with the routine export line and the export answers of version 4 and of older tools. The
  Windows, tools and tools-only boxes follow as the stick route, second. `docs/EMERGENCY.md`: a card **A routine tools
  command stopped** after **A tools command stopped**, whose export sentence gains the `/run/ares-records` wording.
  `docs/INSTALL-STATUS.md`: a 22d row (built, not rehearsed, not on the laptop); the 22c row keeps `2084c786…` short
  and says version 3 never goes on the laptop (board #265). v4's fingerprint is pinned in step 4's and step 8's blocks
  and PASS lines.
- **Tests:** `test_owner_bootstrap` (the brief's shape word for word; the 16 ksshaskpass patterns against every label;
  the tools-only script run with stand-ins: install, check, title, and each first STOP; Claude's folder line against
  real git repositories: fetch, not on main, unknown, short or missing hash, dirty and stale checkout, an untracked
  file kept out, a wrong pinned fingerprint, an unreachable origin). `test_owner_equality` pins every `bash -c` block of
  `INSTALL.md`, whatever its prefix (F17), each generated line once and byte-equal, and OWNER-TOOLS.md against the
  payload, the blocks' literal and the labels; OWNER-TOOLS.md is an owner page (fingerprint and inline checks) and
  replaces the 22c report as the current fingerprint document. `test_owner_path` pins the routine box, the card and
  the 22d row. `test_owner_entry` and `test_ways_back` skip the generated lines (they start no dispatcher of their
  own) and expect `install(…, 'folder')` through the installed entry.

### The ksshaskpass patterns

From KDE's mirror, `src/main.cpp` at tag `v6.7.5` (the R27 image's `ksshaskpass-6.7.5-1.fc44`), read with `curl`
on 2026-11-15 (SHA-256 of the file `e088570c…`): `parsePrompt` tries exactly 16 patterns (15 entry prompts and the
unknown-host question) and logs `Unable to parse phrase` otherwise, as step 0 saw. The test lists all 16 in that order,
proves each takes the prompt it was written for, and checks every generated label (and the label at each first hex
digit) against them with Python's `re.search`, which matches QRegularExpression's unanchored search for these patterns.

### Integrator's items

- **A.** `regressions` `timeout-minutes` 25 → 40 in `os-image.yml`; 22c's ledger charges an unaccountable checks job
  40 (the larger of its two jobs' bounds) with a note in its budget text; `test_ways_back_model` pins both. Nothing
  else pinned 25 (`test_release27` and `test_ways_back_probe` pin other jobs).
- **B.** Cause: step 1's route decision. The three tests started `install` with no `m` beside the payload, so it ran
  as the folder block, whose first installation refuses before the STOPs they test. The code is right (decision 7);
  the tests now create `m` as the stick block does. The module uses only stand-ins (FixtureHost, patched `Host`,
  `geteuid`, `HOME`, `LOCK`, records under the test folder); it ran here. `test_owner_entry` had the same cause
  (expected `install(payload, host)`).
- **C.** `rebind.py pending` ran once after the last change to a bound file; the list's `status` and `decision` now say
  that tool, guide and workflow files wait for 22d's rehearsal.

### Tests run here (Python 3.14, one module at a time)

| Module | Result |
|---|---|
| `test_owner_bootstrap` | `Ran 12 tests`, `OK` |
| `test_owner_equality` | `Ran 11 tests`, `OK` |
| `test_owner_path` | `Ran 48 tests`, `OK` |
| `test_owner_walk` | `Ran 27 tests`, `OK` |
| `test_owner_entry` | `Ran 3 tests`, `OK` |
| `test_owner_diagnostics` | natively 9 pass, 1 error (`Unsafe private setup directory`, the Python 3.14 `lstat` fixture issue step 1 names); with `Path.lstat` routed through `Path.stat` as in 3.12: `Ran 10 tests`, `OK` |
| `test_grub_bls`, `test_system_keyboard`, `test_stock_prepare` (read `INSTALL.md`) | `OK` each |
| `test_ways_back_model -k test_hosted_checks_explore`, `test_ways_back -k test_one_helper_spells`, `test_ways_back_reverts -k test_a11` | `OK` each |
| `test_owner_step_limits`, `test_checkout_sources` | red until `rebind.py pending` recorded `commands.json` and the rest; after it `OK` each (4 and 6 tests) |
| `test_ways_back_probe` (not changed; reads the ledger and `commands.json`) | `Ran 57 tests`, 2 failures, both `Host walk is stale` (22c's frozen receipt, below) |

### Expected red until a later step

- `test_ways_back_probe.test_the_probe_reads_package_22cs_host_walk_and_refuses_a_stale_one` (both modes: 22c's frozen
  host-walk receipt names version 3's payload; step 6's harness and receipt) and `os/ci/owner_vm.py`'s `(2, 3)`.
- `test_owner_update` was not run here, by the rule.

### JUDGMENT-CALL (for the owner, at the "try this" stage)

- The words of the two labels (`install these tools, then check and title`; `export the records`), the routine box,
  the routine STOP card and the new STOP lines (`STOP after install: check or title refused`, the `STOP tools folder`
  lines). Changing a label or a STOP line later costs a new generated line, its tests and the guide's quotes, but no
  tools version (they are outside the payload).
- The board note is posted after the tools-only box too, not only after a change of what starts next (decision 8):
  on the routine route he no longer sees the title himself, and the failed-update card works from his last title.

### Left after step 2

Steps 3 to 7 as in the brief.

## Step 4 (review 8's findings 2 and 5), 2026-11-15, Claude agent on Opus 5.5: done

Brief row 4 (decision 11). Built on `4cdd7b28` while step 3's review of steps 1 and 2 ran on that head; nothing of
steps 1 and 2 changed. No PLAN-GAP.

### What changed

- **Finding 2, a cleanly stopped update closes its intent** (`Tools.stop_update`). When every part of the stop routine
  passed, `reconcile_update` has proved the list is as before (nothing staged, or this update's staged row removed and
  the others unchanged). The routine then archives the intent as `<stamp>-outcome-stopped-not-applied.json` (the
  intent plus `stopped` and `staged_release_removed`), as `start_next` does for its certain refusal. Its line is
  unchanged ("… was stopped safely: … Nothing changes at the next start; run update again later, or get help"), and
  now holds in the same start: `check`, `title`, `reboot`, `forward`, `previous`, `rollback` and `update` work. With
  any error (a surviving process, an unproved end, a failed status read, a foreign staged row, a failed mask, or the
  archive itself failing, reported as `records: …`) the intent stays open and every other command STOPs with
  "interrupted before its result was recorded; do not reboot; run … update to continue it", as before. A kill or a
  power cut in the step never reaches the routine, so it leaves the intent open too.
- **Finding 5, a trial from an earlier boot names abandon** (`Tools.no_layout_trial`, constants `LAYOUT_TRIAL` and
  `LAYOUT_TRIAL_RESTARTED`). One helper replaces the three copies of the refusal: `may_change` (the reorders, staging,
  `layout begin`), `reboot`, and the tools update's readiness check (`system_ready`, which had the same wording and the
  same problem). In the trial's own boot the wording is unchanged:
  `Layout trial is unfinished; prove it or revert first`. When the trial's administrator login was in another boot:
  `Layout trial is unfinished and began before the last restart: from a fresh physical administrator login run sudo /var/lib/ares/at layout abandon, then run this command again`.
  It keeps the old prefix (every test and the model that matched `Layout trial is unfinished` still do) and does not
  say "nothing changed" (in the tools update the refusal can come with a journalled copy in place). A record whose
  boot cannot be read (not JSON, no `administrator.boot`, not a string) keeps the first wording; it refuses all the
  same. `title` still passes without mentioning the trial (finding 5's side remark; not changed).
- **The guide.** `INSTALL.md`'s update box said a cut-off update ("(power, closed window)") makes the next command in
  the same start STOP. A closed window ends in the stop routine, which now closes the intent, and a power cut leaves
  no same start (finding 7). It now reads: "If the update STOPs with **was stopped safely**, nothing changed and every
  command works: run update again later, or get Help. If it is cut off before its PASS without that line (the command
  killed), the next command in the same start STOPs with **interrupted before its result was recorded; do not
  reboot**: …". No guide quoted the layout refusal, so none changed for finding 5.
- **Fingerprint:** payload refreshed (`bundle.py --refresh`); tools version 4 is now
  `e68fd5fd56fad61987bdad9d9c1106e40e449548f82dcc27fa351a75074cb75b` in `commands.json` (equal to `bootstrap.lines`),
  `OWNER-TOOLS.md`, `INSTALL.md` (stick blocks, folder line, routine and export labels, PASS lines), `EMERGENCY.md` and
  `INSTALL-STATUS.md`. `rebind.py pending "22d step 4: review 8 findings 2 and 5"` ran after the last bound change.

### Tests

- `test_ways_back.py` (4 new): a clean stop for a step that fails before staging and one that fails after it (the
  routine removed the staged row): the line, the list as before, the closed record, then `check`, `title`, `reboot`
  and `update` in the same start; a stop with errors (a surviving step, a failed mask after the removal, an archive
  that fails), before and after staging: the intent stays open and `check`, `title`, `reboot`, `forward`, `previous` and `rollback` STOP as
  before with nothing changed; a trial on the older AresOS refused by `forward`, `rollback`, `reboot` and `begin` with
  the same-boot wording, then after a restart by the same words and on plain Bazzite by `forward`, `keep-stock` and
  `reboot` with the new one, `proof` refusing (`Trial crossed a reboot`), and `abandon` from the fresh login clearing
  it; unreadable trial records keep the first wording. With both fixes reverted in a scratch copy the clean-stop test (both
  points) and the trial test fail; the errors test and the unreadable-record test pin unchanged behaviour and pass
  either way.
- `ways_back_ledger.py`: the model predicts both wordings by the trial's boot (`trial_refusal`). The slice's counts
  are unchanged; only executions grow a little, because the refusal now reads the trial record.
- `test_owner_update.py` (hosted only): the `system_ready` needle is now `checker.no_layout_trial()`. `IntentTest`:
  update's step failing before or after staging ends in a clean stop, so the intent is closed there (`CLOSED`),
  `check`, `title` and `records` pass, the next start archives nothing more, and the same command stages afresh; the
  "other commands never continue an intent" test uses the `observe` point (staged, then the status read failed), where
  the intent stays open. The fixture patches `finalizer_masks` to `[]` so the routine never reads the runner's `/etc`.
  `UpdateStopTest`: `stopped_cleanly` expects no open intent and one closed record (and `settled` None); the five
  stops with an error assert the intent stays open (`stopped_with_errors`). **Not run here**, by the rule. The changed
  `IntentTest` scenarios were replayed with the module imported as a library (scratch script, not committed): OK.
- `test_owner_path.py`: pins the new guide sentence, the tool's `' and was stopped safely: '`, and that
  `(power, closed window)` is gone.

### What ran here (Python 3.14, one module at a time)

| Module | Result |
|---|---|
| `test_ways_back` (4 new tests) | `Ran 56 tests`, `OK` |
| `test_ways_back_model`, `ARESOS_MODEL_SCOPE=slice` (ledger changed) | `Ran 26 tests in 188.961s`, `OK`; slice `173130 states, 3185862 edges` (the pinned `SLICE_COUNTS`, unchanged), 245754 executions, 2940108 reuses. The full model runs hosted; its pinned counts (967215, 26519328) should not change either, since only the predicted refusal words changed, not a state or an edge |
| `test_ways_back_reverts`, `test_ways_back_compatibility`, `test_owner_sources` (ledger; the tools update's readiness check) | `OK` each (20, 21, 12 tests) |
| `test_owner_bootstrap`, `test_owner_equality`, `test_owner_path`, `test_owner_entry`, `test_owner_walk` (pins, guide) | `OK` each (12, 11, 48, 3, 27 tests) |
| `test_grub_bls`, `test_system_keyboard`, `test_stock_prepare`, `test_owner_session` (read the guides) | `OK` each (6, 7, 7, 16 tests) |
| `test_checkout_sources`, `test_owner_step_limits` (after `rebind.py pending`: 23 bound files wait) | `OK` each (6, 4 tests) |
| `test_ways_back_probe` | `Ran 57 tests`, the same 2 failures as at step 2 (`Host walk is stale`, below) |
| `test_owner_update` | not run here, by the rule; its changed `IntentTest` update scenarios replayed through the library: OK |

### Expected red until a later step

Unchanged from step 2: `test_ways_back_probe`'s two `Host walk is stale` failures (22c's frozen host-walk receipt;
step 6) and `os/ci/owner_vm.py`'s `(2, 3)`. `test_ways_back_model` selects the full model for this branch (hosted).

### JUDGMENT-CALL (for the owner, at the "try this" stage)

- The new refusal's words (above). Changing them later costs a tools version.
- The `INSTALL.md` sentence about a stopped update (above).

### Left, in order

Step 5 (review of step 4) is done: `REVIEW-3.md`, SAFE. Then the fix step below, step 6, step 7.

## Fix step after reviews 2 and 3, 2026-11-15, Claude agent on Opus 5.5: done

The brief's section "Decisions after review 2 (integrator, 2026-11-15)", including "From review 3". No PLAN-GAP.
Line numbers are at this step's commits.

### Each item

- **R1 (decision 10 replaced).** `docs/INSTALL.md:276`: after 10 minutes Claude closes the window by stopping the
  password helper it opened, never the administrator command; sudo then ends with **sudo: no password was provided**,
  which shows nothing ran; if he has already answered, Claude stops nothing and waits. No guide holds the walk stage
  (it is only in the brief, whose section already replaces it); `test_owner_path.py:1721` refuses the old words
  (`process number`, `stops that sudo`). The harness part is step 6's (below).
- **R2, R5, N9.** `INSTALL.md:278` and the card `docs/EMERGENCY.md:66-67`: Claude copies every STOP line word for word,
  asks for his go, and only on his go runs the export line; after a **STOP tools folder** no export and no window; the
  card says Claude reads `/run/ares-records` to help and never copies it into the repository, a pull request or the
  board (disk serials, firmware entries), and that the tools' **Keep the current administrator session open** is for
  the console (on this route nothing is lost). The box says the same about the copy (`INSTALL.md:284`).
- **R3.** `bootstrap.FROM_COMMIT` (`os/owner-tools/bootstrap.py:44`) is
  `git -C /var/home/ares/AresOS show <commit>:os/owner-tools/commands.json`; the box (`INSTALL.md:249`) says Claude
  takes the line from there, entry **tools-routine** (export: **export-routine**), never from its working copy. The
  checkout check stays. Pinned in `test_owner_path.py` (the box's order list); `test_owner_bootstrap.py:341` runs the
  command against a dirty checkout and gets the commit's `commands.json`. The entry names are bold, not code: the
  inline owner-command check reads any code span named like a `commands.json` entry as a command.
- **N2.** The folder line checks the commit's own `SHA256SUMS` against the pinned fingerprint before it empties the
  folder (`bootstrap.py:153-154`): `STOP tools folder: <commit> holds other tools than <8 hex>`. Every refusal with
  its own reason now comes before `rm -rf`; only a failing `git archive` or `tar` after it leaves the folder emptied
  (still "nothing was installed"). `test_owner_bootstrap.py:349`: a wrong pin refuses with that line and leaves the
  folder exactly as it was (the other refusals already asserted that). The box says "installed nothing and opened no
  window (a refusal that names its reason left the tools folder as it was)" (`INSTALL.md:247`).
- **N7, N8.** `INSTALL.md:230`: a fast-forward pull only, never a reset or a checkout over other sessions' work; from
  then until the last PASS line no other Claude session runs an owner command.
- **R4, N6.** `INSTALL.md:272`: line 1 of `github.com/Ares-Empire/AresOS/blob/main/docs/OWNER-TOOLS.md`, opened from
  his own bookmark, `main` in it, never a link Claude sends at that moment. `docs/OWNER-TOOLS.md` has a blank line
  between line 1 and the full fingerprint; `test_owner_equality.py:190-210` holds the page's new shape and the address.
  The brief's decision 5 text ("line 2 the full fingerprint") was left as it is: its section after review 2 replaces it.
- **R6.** One sentence in the routine box (`INSTALL.md:284`) and one in **A tools command stopped**
  (`EMERGENCY.md:61`), each quoting `The stick holds tools this laptop installed before (SHA256 …), not the installed
  ones`, which `test_owner_path.py` holds equal to `media.py`'s string around its fingerprint.
- **N1, N5.** `bootstrap.routine` (`bootstrap.py:106-116`): `SUDO_ASKPASS=/usr/bin/ksshaskpass SSH_ASKPASS_PROMPT=
  /usr/bin/sudo -k -A -p '<label>' /usr/bin/bash -c '<script>'`. The empty assignment, not `env -u`: it keeps the
  decision 2 shape, and ksshaskpass 6.7.5 treats empty as unset (`src/main.cpp:283-289`, the same file as step 2's,
  SHA-256 `e088570c…`: only `confirm` and `none` change the window). `test_owner_bootstrap.py:194` runs each routine
  line through bash against a stand-in for `/usr/bin/sudo` with the caller's `SSH_ASKPASS_PROMPT` unset, `confirm`
  and `none` and a foreign `SUDO_ASKPASS`: the stand-in always gets an empty prompt variable, the fixed helper and
  `-k -A -p <label> /usr/bin/bash -c <script>`. The labels did not change; the 16-pattern test still passes.
- **N3.** `owner.caller()` (`owner.py:217`): `sys.stdin is not None and sys.stdin.isatty()`;
  `test_owner_sources.py:174` with `sys.stdin` None.
- **N4.** `media.export_local` (`media.py:104-118`): a missing or failing `setfacl` (any exception from the grant)
  leaves the complete copy root's and export passes with
  `This copy is on this laptop, not off it; only root can read it, since uid 1001 could not be let in (<reason>), and a restart deletes it`.
  The reason is the host's message without its `; do not reboot`. `test_owner_export.py:202`: the real `Host` with
  setfacl missing (`Required tool missing: setfacl`), failing (`Operation failed: setfacl`) and not executable; no
  line says reboot, modes stay 0700/0600.
- **Review 3, nit 2.** `owner.LAYOUT_TRIAL` (`owner.py:73`):
  `Layout trial is unfinished; prove it or revert first; if the console that began it is closed, from a fresh physical administrator login run sudo /var/lib/ares/at layout abandon`.
  `test_ways_back.py:1176` and `test_owner_update.py:1393` (hosted only) expect it; the model matches by substring and
  its slice is unchanged.
- **Review 3, nit 3.** `test_owner_sources.py:255` (`LayoutTrialTest`): the tools update from both blocks with a
  trial record from an earlier boot refuses with `LAYOUT_TRIAL_RESTARTED`, one from this boot with `LAYOUT_TRIAL`;
  the tools' home byte for byte as before and no mutation.
- **N10.** `INSTALL.md:228`: only this box's install line and its export line run this way for now; every other owner
  command stays at the console until a later release brings it here. In 22d the generated routine lines are exactly
  `tools-routine` and `export-routine`.
- **The label's comment** (review 2, question 5) also names the rich-text reason for its character rule.
- **Fingerprint:** payload refreshed (`bundle.py --refresh`); tools version 4 is now
  `dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be` in `commands.json` (equal to `bootstrap.command`
  and `bootstrap.lines`), `OWNER-TOOLS.md`, `INSTALL.md`, `EMERGENCY.md` and `INSTALL-STATUS.md`; `e68fd5fd` is gone
  from `docs/` and `os/`. `rebind.py pending "22d fixes after reviews 2 and 3"` ran last.

### What step 6 must assert from these items

- **R1, the unanswered window.** The stand-in caller starts the routine line in the background and, after the
  harness's (shortened) wait, stops only the `ksshaskpass` process whose parent is that sudo (it runs as uid 1001);
  it never signals the sudo. Assert: that helper is gone (and the dialog with it, by screenshot); sudo's stderr holds
  `sudo: no password was provided`; sudo exits 1; nothing changed (no new `/run/ares-bootstrap.*`, the tools' home,
  records and journal byte for byte, every protected-disk audit unchanged); the only signalled PID is the helper's.
- **R1, the answered window** (recommended): once the helper is gone the caller signals nothing and the line's result
  (PASS install, check, title) arrives.
- **R3:** the stand-in caller takes `tools-routine` and `export-routine` with `bootstrap.FROM_COMMIT` for the
  announced commit, not from the working tree.
- **N2:** a stage that feeds version 3's commit through Claude's folder line now sees
  `STOP tools folder: <commit> holds other tools than dcbc375f` with the folder unchanged. The "v3 refuses" stage must
  put v3's bundle into the folder another way to reach the root line's own STOP.
- **N3** (recommended): one routine line run with stdin closed (`<&-`): PASS, and the receipt's
  `caller.terminal` false, no traceback.
- **N4:** with the image's `setfacl` the export line names uid 1001; `ares` reads `/run/ares-records`, another account
  cannot (already in the brief).
- **N5:** the dialog asserts (helper argument equals the label) hold with the caller's `SSH_ASKPASS_PROMPT=confirm`,
  if the harness sets one; the window keeps its password field.
- Unchanged from the brief: the stand-in origin whose `main` holds the commit; the 70-character label wrapped, not cut.

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_owner_bootstrap` (1 new) | `Ran 13 tests`, `OK` |
| `test_owner_equality` | `Ran 11 tests`, `OK` |
| `test_owner_path` | `Ran 48 tests`, `OK` |
| `test_owner_sources` (1 new) | `Ran 13 tests`, `OK` |
| `test_owner_export` | natively 3 pass, the same 3 fail as at the step's start (Python 3.14 fixture); with `Path.lstat` routed through `Path.stat` in a scratch runner 4 pass, and the 2 fresh-process tests fail there exactly as on a copy of `80cb99a9` (the child gets no patch). The changed test passes either way |
| `test_ways_back` | `Ran 56 tests`, `OK` |
| `test_ways_back_model` | `Ran 26 tests`, `OK` (slice) |
| `test_ways_back_reverts`, `test_ways_back_compatibility`, `test_owner_walk`, `test_owner_entry` | `OK` each (20, 21, 27, 3) |
| `test_grub_bls`, `test_system_keyboard`, `test_stock_prepare`, `test_owner_session` | `OK` each (6, 7, 7, 16) |
| `test_checkout_sources`, `test_owner_step_limits` | after `rebind.py pending` (23 bound files wait): `OK` each (6, 4) |
| `test_owner_update` | not run, by the rule (one refusal text changed) |

### JUDGMENT-CALL (new wording he will read)

- In the payload (a change costs a tools version): the failed-grant export line above; the same-boot layout refusal
  (review 3's words).
- Outside the payload: `STOP tools folder: <commit> holds other tools than <8 hex>`; the guide sentences for R1, R2,
  R4, R5, R6, N7, N8 and N10.
- R6 says "until Claude writes it again (for now from Windows, the box below)" instead of naming package 22e: 22e is
  not built, and the owner's guide names no packages there.

### Left, in order

Step 6 (harness `tools-local`, its ledger entry, the receipt, the walk with the assertions above, hosted checks, the
VM run), step 7. `INSTALL-STATUS.md`'s 22d row still says "not yet reviewed": the record step updates it.

## Step 6, part a (harness, the walk), 2026-11-15, Claude agent on Opus 5.5: done (part b continues below)

The brief's row 6 up to a VM dispatch the integrator can run. Commits `d91fc456` (guide fixes), `c4474d49` (wiring),
and the stand-in origin commit after it. Nothing dispatched.

### Done

- **1. Review 4's guide fixes** (`d91fc456`, no payload change): S1 on the routine STOP card (`EMERGENCY.md:67`, the
  last line's **do not reboot** holds here too); N-a (the bookmark: type the address once into the phone's browser and
  save it); N-b (the box says only "installed nothing and opened no window"; `tools_folder`'s docstring "emptied or
  partly filled"). `test_owner_path` holds the new words and refuses the old ones (`'is for the console:'` on the
  card, `'a refusal that names its reason'` in the box) and checks the tools' line still says `do not reboot`.
  `rebind.py pending` ran.
- **2. The mode `tools-local`** (`c4474d49`):
  - Ledger `22d` in `os/ci/rehearsal-packages.json`: checks 20, `tools-local` 4, `vm_dispatch_cap` 4, minutes 1200,
    job bounds 22c's (345 job / 315 VM step; checks 40), publish 0, start `first-dispatch`.
  - Workflow: option `tools-local`; `REHEARSAL_PACKAGE` maps the branch to `22d`; every condition naming 22c's
    branch names 22d's too (`(22c || 22d)` groups, the two shell `test` lines, the cleanup `!=`); the rehearsal job's
    gate gains `(inputs.rehearsal == 'tools-local') == (github.ref_name == 'pkg/22d-tools-without-stick')`.
  - Step scripts admit 22d's branch, package and mode: `owner_media.require_runner`, `registry_auth` (dispatch and
    signature), `owner_capabilities`, `owner_devices`, `installer_webui`, `two_disk_vm`. `rehearsal_guard` gets
    `OWN_RUN_PACKAGES = ('22c', '22d')` (native step in the run itself, the model gate, the VM dispatch cap, the
    authorization file). `checkout_sources.active_tables` prefers 22d's bindings once recorded.
  - `owner_vm.main`: `tools-local` is package 22d's only; reads `os/manifest/ci/22d/host-walk.json`; saves
    `22d-bound-sources` over 22c's tables (`bound_sources(..., '22d', '22c')`); creates the stick from the laptop's
    tools as 22c does; hands the walk to `tools_local.rehearsal` with version 2 from history.
  - Tests: new `os/tests/test_tools_local_wiring.py` (ledger = brief, the mode runs only the rehearsal job and only
    on 22d's branch, checks-only runs regressions and model there, every step script's gates pass with 22d's
    environment (this caught `owner_devices.py:360`), the steps' arguments and bounds, 22d decides like 22c's
    `ways-back` except four reviewed decisions, the guard writes `22d-dispatch-authorization.json` and refuses
    another branch, runner and registry accept only 22d's triple, the driver keeps routes to packages). The pinned
    workflow strings in `test_rehearsal_budget`, `test_owner_guard`, `test_rehearsal_auth`, `test_owner_capabilities`,
    `test_release27` and `test_ways_back_probe` follow; 22c's wiring test now also refuses `tools-local` on its
    branch and its modes on 22d's.
  - `reviews/22d-tools-without-stick/walk-host.py` (22d's own receipt, inherits 22c's bound set plus
    `tools_local.py`, the wiring test and itself). **Not run yet:** it calls `test_owner_walk.walk(route='tools-local')`,
    which does not exist yet. 22c's receipt is untouched.
- **3, started: `os/ci/tools_local.py`**: the walk's plan in its docstring; `standin_origin(destination, head)` builds
  the guest's stand-in for GitHub (below), tested in `test_tools_local_wiring.StandInOriginTest`;
  `rehearsal()` refuses with `STOP: the tools-local walk is not built yet` (tested), so nothing can be dispatched by
  accident (and `owner_vm.main` already stops earlier on the missing 22d receipt).

### What the code doesn't show

- **The stand-in origin is not the real commit (integrator: please confirm).** The real commits' trees are 910 MB
  (17,535 files); the lines read only `os/owner-tools` (0.43 MB). `standin_origin` makes a bare repository whose
  `main` is two commits: version 3's `os/owner-tools` (tag `version-3`), then this head's; each `os/owner-tools`
  tree has the real commit's tree hash (git names trees by content; asserted), and nothing else is in them. So the
  on-main check, the checkout check, the N2 fingerprint check, `git archive` and `FROM_COMMIT` read the real bytes,
  but the hash Claude "announces" in the VM is the stand-in's. The walk should record both hashes and the tree hash.
- **Budget:** with 345 per VM reservation and about 36 per checks run, 1200 minutes allow three VM dispatches beside
  a few checks runs; the cap of 4 is reachable only if the minutes are raised (22c needed that, run 43581458429).
  The four checks-only runs already on the branch (43669481694 cancelled, 43673689888, 43677461596, 43680654211)
  count against the 20 and the minutes (`start: first-dispatch`).
- `test_ways_back_probe` takes about 140 s here; `test_tools_local_wiring` 2 s.

### Left, in order (the next agent continues here)

1. **The walk in `tools_local.rehearsal`** (replace the refusal), using 22c's pieces: `owner_vm.laptop_update(...,
   bundle=(version_2, TOOLS_V2))`, `td.start_installed(..., 'release-27')`, `confirmed_update`, `Console.passwd`
   and `Console(guest, 'tty4').ares_sudo` (as `ways_back_rehearsal` begins, `owner_vm.py:2125-2150`); `finish`,
   `td.marker` at the end; `owner_vm.records()`/`diagnostic_reader` for the tools' records and journal.
   Suggested shape, from what step 6's notes require:
   - **Guest setup** (root serial shell, `guest.command`): write the bundle (about 200 KB; base64 in chunks) and, as
     `ares`, `git clone --bare` it to `GUEST_ORIGIN` with `main` reset to `version-3`, then `git clone` it to
     `/var/home/ares/AresOS` (so `origin` is the stand-in). Before the install stages move the stand-in's `main` to
     the head commit and bring the checkout there with `git pull --ff-only` (the guide's rule N7).
   - **The stand-in caller:** a script written as `ares` (e.g. `/run/aresos-caller-<stage>.sh`) that takes the
     entry with `git -C /var/home/ares/AresOS show <commit>:os/owner-tools/commands.json` (R3; for v3 refuses use
     this checkout's `bootstrap.tools_folder(TOOLS_V3)` and `bootstrap.tools_routine(TOOLS_V3)` instead, N-e), records
     that `/dev/tty` cannot be opened (no controlling terminal), runs the line in the background, writes sudo's PID,
     stderr, stdout and exit status to files. Typed once in foot (as `terminal_path` does: switch to tty1, wait for
     foot, `ACTIVE_DESKTOP`, then `type_text(guest, 'setsid -f /run/aresos-caller-<stage>.sh\n', 'de')`), so it runs
     in his session with `WAYLAND_DISPLAY` and the session bus, without a terminal.
   - **The dialog driver:** from the root serial shell wait for a `ksshaskpass` process whose parent is that sudo;
     assert its `argv[1]` equals `bootstrap.label(fp, action)`, its uid 1001; list keyring processes
     (`kwalletd5`, `kwalletd6`, `ksecretd`, `gnome-keyring-daemon`) before and after: none new; `guest.screenshot`
     (the label is 70 characters: the picture must show it wrapped, not cut); then type the password
     (`type_text(guest, ares_password + '\n', 'de')`) or `guest.keys(['esc'])`.
   - **R1:** `kill -TERM <helper pid>` as `ares` (not root; record the only signalled PID); wait for sudo's exit:
     status 1, stderr holds `sudo: no password was provided`; nothing changed (no new `/run/ares-bootstrap.*`, the
     tools' home, records and journal byte for byte).
   - **Cut:** find the tools update's copy→publication window in `owner.update_tools` (`owner.py:2560-2720`,
     `published = HOME / ('tools-' + fingerprint)`) and freeze/reset there as 22c's `CUT_WATCH` does for rollback
     (`owner_vm.py:1810-1880`); after the restart the old tools' `check` passes.
   - **Install:** PASS install, check, title from one window; the receipt (`tools-update` record) names
     `source: folder`, `caller.uid 1001`, `caller.terminal false`; `runuser -u ares -- sudo -n true` refused.
   - **Tamper:** one byte in `/var/home/ares/ares-tools`; STOP before bundle code.
   - **Stick with a next version:** build a v4+1 bundle on the runner (this payload with a changed version number,
     `bundle.py`'s refresh into a work folder; check how `test_owner_update` builds its next-version fixture),
     `media.replace('tools-5', source=...)`, `media.attach`, the guide's stick block at tty3 (`walk.run(console,
     'install', ...)` with `commands['install']` from `bootstrap.command(<its fingerprint>)`).
   - **Exports:** the routine `export-routine` line (window, password): `ares` reads `/run/ares-records/*.json`,
     another account (e.g. `runuser -u nobody`) cannot; then the stick holding version 2
     (`media.replace(..., source=version_2)`) at tty3: accepted with the retired-bundle line.
   - **End:** restart, `check`, `title`, `td.marker(audit, 'final-unattended-windows')` and the detached one; the result
     saved as `tools-local-rehearsal-result`.
2. **The local walk:** `test_owner_walk.walk(route='tools-local')` with `TOOLS_LOCAL_STAGES`, answering every new
   capture (as `route == 'ways-back'` does at `test_owner_walk.py:451-475`); tests for it in
   `test_tools_local_wiring` (stages, the dialog asserts, R1's single signalled PID, the receipt fields).
3. `python3 reviews/22d-tools-without-stick/walk-host.py` (writes `os/manifest/ci/22d/host-walk.json`), a receipt test
   (fresh until 22d's record step), `rebind.py pending`, then the touched modules one at a time.
4. The integrator: a checks-only run on the head, then the VM dispatch
   (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick -f rehearsal=tools-local`).

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_owner_path` | `Ran 48 tests`, `OK` |
| `test_owner_equality`, `test_owner_bootstrap` | `OK` each |
| `test_tools_local_wiring` (new) | `Ran 13 tests`, `OK` |
| `test_ways_back_probe` | `Ran 57 tests`, `OK` |
| `test_release27` | `Ran 41 tests`, `OK` |
| `test_rehearsal_budget`, `test_owner_guard`, `test_rehearsal_auth` | `OK` each (4, 12, 9) |
| `test_owner_capabilities`, `test_owner_devices`, `test_organization_budget`, `test_ci_api_permissions` | `OK` each (6, 6, 19, 4) |
| `test_checkout_sources`, `test_owner_step_limits` | after `rebind.py pending` (35 bound files wait): `OK` each (6, 4) |
| `test_owner_update` | not run, by the rule |

## Step 6, part b (the walk itself), 2026-11-15, Claude agent on Opus 5.5

Part a's "Left, in order" items 1 to 3, with the integrator's decisions on part a's two PLAN-GAPs. Nothing
dispatched; no owner tool, sudo, ostree, bootc, rpm-ostree, ksshaskpass or generated line ran here.

### The integrator's decisions (2026-11-15)

- **Stand-in origin:** accepted as built. The walk records, for each announced commit, the stand-in's hash, the
  real commit's and the tree hash, and asserts the trees equal on the runner (stand-in repository and this
  checkout) and in the guest (`git rev-parse HEAD:os/owner-tools` in his checkout after the clone and after the
  fast-forward pull). The result's `announced` holds the rows.
- **Budget:** 22d's `minute_cap` 1200 → 2400 (ledger text says why and when; `test_tools_local_wiring` holds
  2400 and the sentence; the brief's budget line notes the raise). 20 checks-only runs and 4 VM dispatches stay.

### Done

- **`tools_local.rehearsal(vm, audit, media, password, hashed, ares_password, version_2)`** (`os/ci/tools_local.py`).
  `vm` is the running `owner_vm` module (`sys.modules[__name__]` in `owner_vm.main`, which runs as `__main__`;
  a second import of `owner_vm` would split its globals). Boots: package 27's route (`laptop_update` with v2),
  `release-27`, `cut-27`, `final-27`.
  - Guest setup: the stand-in bundle in 48 kB base64 commands, checked by SHA-256; as ares (`runuser -u ares --
    env HOME=/var/home/ares`) a bare clone at `/var/home/ares/aresos-origin.git` with `main` at v3's stand-in, then
    his checkout `/var/home/ares/AresOS`; later origin's `main` moves to the head's stand-in and the checkout
    follows by `git pull --ff-only` (N7).
  - The caller (`CALLER`): written by root to `/run/aresos-caller-<stage>.py`, started from foot by typing
    `bash /run/aresos-caller-<stage>.sh` (the launcher runs `setsid -f` with stdin `/dev/null`, so the typed text
    is letters, `/`, `-`, `.` only). It records uid, login uid, `/dev/tty` refused (ENXIO), stdin not a tty,
    `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR`; reads each line from `git show <commit>:os/owner-tools/commands.json`
    (R3; v3's lines are this checkout's `bootstrap.tools_folder/tools_routine(TOOLS_V3)`, N-e); runs the folder
    line, then the routine line with stdout/stderr to files; with `unanswered` it SIGTERMs only the
    `/usr/bin/ksshaskpass` child of the sudo it started and records every signalled PID; `no-ticket` runs
    `sudo -n true`. The harness compares the SHA-256 of each line it ran with the expected line.
  - The dialog driver (`DIALOG`, root): waits for exactly one ksshaskpass whose parent is that sudo; asserts
    `argv == [/usr/bin/ksshaskpass, label]`, parent = sudo, uid 1001, and no keyring process (`kwalletd5/6`,
    `ksecretd`, `gnome-keyring-daemon`) beyond the start's baseline (taken per boot); screenshot `<stage>-window`;
    then the password typed (`type_text`, `de`), Escape, or nothing (R1). After the caller ends the keyring list
    is compared again.
  - `STATE` (root): a digest of `/var/lib/ares` without records, the entry, the toolsets, the tools journal's
    phase/manifest/source, the records' names, `/run/ares-bootstrap.*`, a digest of the tools folder.
  - Stages, as the brief: v3 refuses (the STOP names `Tools update runs only from the physical recovery
    console`; tools, entry and journal unchanged) → Cancel (Escape; exit 1, `sudo: no password was provided`;
    tools, entry, journal, records and bootstrap copies unchanged) → R1 (30 s instead of 10 minutes; signalled
    = [the helper]; helper gone; exit 1 with the line; nothing changed) → Cut (`TOOLS_CUT` watches the journal for
    phase `publish` with this head's manifest, SIGSTOPs the `owner.py install` process, asserts the entry is still
    the old tools and `tools-<head>` exists; QMP reset) → `cut-27`: the old tools' `check` passes, the journal still
    names the head (source folder) → Install (resumes; exactly `PASS install`, `PASS check`, `PASS title`; the
    receipt: manifest, v2 → 4, `source`/`finished_from` folder, `caller == {login_uid: 1001, terminal: false}`;
    `sudo -n true` refused in the same session) → Tamper (one byte of `ares-tools/owner.py`; `STOP bootstrap:
    verification or install refused`, no PASS, tools unchanged) → the stick with `next_version` (this payload,
    tools version 5, manifests regenerated) at tty3 through the stick block (`source: stick`, 4 → 5) → export to
    the folder (window; `PASS export`; ares reads every `/run/ares-records/*.json`, `nobody` none) → export to a
    stick holding v2 (the retired-bundle line, quoted from `media.py`) → restart → `final-27`: check, title,
    logout; both final markers. Result: `tools-local-rehearsal-result`.
  - No closed-stdin stage (N-d).
- **The local walk:** `test_owner_walk.walk(route='tools-local')`, stages `TOOLS_LOCAL_STAGES`. Its `ToolsLocal`
  model reads each caller's parameters back from the program the harness sends, takes the label from the line
  that caller would run, and decides each outcome from what the walk saw (the password typed, Escape pressed,
  or a caller that closes the window); the install happens only after the cut. Passes (176 checks).
- **Tests** (`os/tests/test_tools_local_wiring.py`): the walk's stages and markers; every label and screenshot;
  R1's single signalled PID and the receipt fields; both hashes and the tree per announced commit; a harness that
  types the password into the Cancel window fails the walk; the real `CALLER` run here under `setsid` against a
  stand-in sudo and helper (argv[0] set with `exec -a`, `sleep` underneath: nothing privileged runs) signals only
  the helper, never a sibling named `ksshaskpass-not`, and reports no terminal; `next_version` changes only
  `history.json`; 22d's receipt is fresh. Part a's "not built yet" test is gone with the refusal.
- `os/manifest/ci/22d/host-walk.json` written by `walk-host.py` (263 sources); `rebind.py pending` ran (36 files).

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_tools_local_wiring` | `Ran 21 tests`, `OK` |
| `test_owner_walk` | `Ran 27 tests in 101.854s`, `OK` |
| `test_release27` | `Ran 41 tests`, `OK` |
| `test_ways_back_probe` | `Ran 57 tests in 145.681s`, `OK` |
| `test_rehearsal_budget`, `test_organization_budget`, `test_owner_guard` | `OK` each (4, 19, 12) |
| `test_checkout_sources`, `test_owner_step_limits` | after `rebind.py pending`: `OK` each (6, 4) |
| `test_owner_update` | not run, by the rule |

### What only the VM can show (watch these in the first run)

- Whether labwc gives the ksshaskpass window the focus, so the typed password reaches it (the harness has no
  focus read; a miss shows as `no password was provided` at v3 or a wait to the deadline).
- Whether the cut lands in the window between the journal's `publish` and the entry's switch (a few hashes of
  0.4 MB); a miss says "repeat it".
- That v2's `check` passes over v4's open journal and leaves it for v4 to resume (step 1's tests say so).

### Left, in order (the next agent continues here)

1. The integrator: a checks-only run on the head (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick
   -f checks_only=true`), then the VM dispatch (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick
   -f rehearsal=tools-local`).
2. After a pass: `rebind.py rebind` for 22d, step 7 (record step, final review).

## Step 6, part c (release 27's facts from its source commit), 2026-11-15, Claude agent on Opus 5.5: done

VM run 43690565301 (tools-local, on `cb2a1eec`) stopped in the rehearsal job's step "Qualify tools, regressions,
rewritten release identity and private access" at `os/ci/verify_release.py:65`: `Release 27 runtime payload changed:
os/Containerfile`. 22d branches from a main that holds the next release's image changes (packages 23, 30, 30b, 31,
unreleased), while the VM runs the pinned, signature-checked release 27 image. Against release 27's source
`b216f28f` this checkout's `os/Containerfile`, `os/build.sh`, `os/packages.lock.json` and `os/config` differ; the
other six recorded trees are equal. Nothing dispatched; no owner tool, sudo, ostree, bootc or rpm-ostree ran.

### The integrator's decision (2026-11-15)

For 22d's tools-local rehearsal release 27's facts are bound to release 27's own source commit, not to HEAD.
22c's and 27's branches behave exactly as before.

### Done

- **`verify_release.py`:** in release 27's block, after every identity check (run, job, signature, image diff,
  job-token read, the rows' shape and path list), the triple `GITHUB_REF_NAME=pkg/22d-tools-without-stick`,
  `REHEARSAL_PACKAGE=22d`, `REHEARSAL_MODE=tools-local` (the same triple `registry_auth.require_dispatch` and
  `owner_media.require_runner` admit) selects the new check. If the source commit is not in the clone
  (`git cat-file -e <source>^{commit}`), it runs `git fetch --no-tags origin <source>`. Each recorded tree must be
  a 40-hex ID and `git rev-parse --verify --quiet <source>:<path>` must equal it (a missing path fails too). The
  paths whose HEAD tree differs are listed in the line it prints: `the image under test is release 27 built from
  <source> (every recorded tree is there); this checkout's image sources differ in <paths> because they hold
  unreleased changes`. Every other environment, including 22d's branch without its package or mode (the
  regressions step runs the suite with `env -u REHEARSAL_PACKAGE`), takes the old HEAD loop, unchanged byte for byte.
  The top check `release['base'] == os/manifest/base.json`'s reference stays in every mode.
- **Checked against this clone's real git** (gh faked, no network; `b216f28f` is local, so no fetch): 22d's triple
  prints `differ in os/Containerfile, os/build.sh, os/packages.lock.json, os/config` and exits 0; without
  `REHEARSAL_PACKAGE` it still stops with `payload changed: os/Containerfile`.
- **Tests:**
  - `test_release27.run_verify_release` is the one fake for both modules: gh's answers, HEAD's trees, the
    source commit's trees and whether that commit is in the clone. It sets only the mode variables a test names,
    because the hosted rehearsal step runs the suite with 22d's branch and mode in its environment.
    `VerifyRelease27Test` uses it unchanged in what it asserts.
  - `test_tools_local_wiring.VerifyReleaseTest`: trees found at the source pass and name the four moved paths
    (and "no path" for an unchanged checkout); a source commit missing from the clone is fetched first; a
    different or missing tree at the source (`os/config`, `os/manifest/base.json`, `os/tests/audit.py`) refuses;
    every identity check still refuses in the mode; 22c's and 27's triples, 22d's branch with another package,
    mode or branch, without `REHEARSAL_PACKAGE`, and no variables all print the old line, run no git beyond
    rev-parse, and refuse a moved HEAD tree.
  - `WalkTest.test_the_walk_reads_no_image_source_of_release_27_from_this_checkout`: an audit hook records what
    the local tools-local walk opens and which git commands it runs; no file under release 27's payload paths
    (all but `os/manifest/base.json`) and no git word naming them. Checked by hand that it fails when
    `confirmed_update` reads `os/config/.../rc.xml` or runs `git show HEAD:os/build.sh`.
- `walk-host.py` ran (`verify_release.py` and the wiring test are bound; 263 sources); `rebind.py pending` ran
  (38 files).

### The checkout's readers of image facts, and what each got

Found by tracing the local walk (every checkout file opened and git command run), then reading by hand the steps
the walk replaces in the VM (`td.install`/`live_inventory`, `td.start_installed`/`sw.start_guest`,
`kb.deployment_snapshot`, `kb.capture_stock_greeter`, `td.marker`, `td.Audit.check`, `restore_windows_order`,
`pin_serial_console`) and `owner_vm.main`. **No reader of release 27's runtime payload from the checkout exists in
this route, so nothing in `owner_vm.py` or `tools_local.py` changed;** the walk test above keeps it so.

| Reader | What it reads | What I did |
|---|---|---|
| `verify_release.py` tree loop | the ten recorded trees at HEAD | changed (above) |
| `verify_release.py` top | `os/manifest/base.json` reference = `release['base']` | kept in every mode: release 27's base itself; if main moves the base, the run stops before any VM |
| `two_disk_vm.live_inventory` (stock install, VM only) | base.json's digest for the live ISO's stock image | not changed: stock Bazzite, not release 27; bound by the base check above (tree equal at `b216f28f` and HEAD) |
| `registry_auth.REFERENCE`, `live_inventory`, `owner_vm.laptop_update` | `os/manifest/release.json` | not changed: release 27's own record, the facts verify_release checks |
| `laptop_update` | `os/manifest/releases/13.json`, `os/owner-tools/history.json` | not changed: release 13's reference and the tools' release list, not image sources |
| `prepare_and_switch` at `corrected-stock` | `os/tests/inherited-homebrew.sh` | not changed: runs on stock Bazzite; differs from `b216f28f` only by package 27's own harness fix (`cd /`, rehearsal run 7), with which 22c passed |
| `owner_scripts` at `release-13` | `os/tests/guest.sh`, `inherited-homebrew.sh` | already from the pinned commit `RELEASE_13_SCRIPTS` |
| `owner_scripts`/`release_rules`/`polkit_sweep` at `release-27` | HEAD's `guest.sh`, `polkit-review.json`, `sudo -l`'s `timestamp_timeout=0`, `HUB_TERMINAL` | not in this route: only package 27's update and 22c's walks call them; `confirmed_update` runs only `check` and `title` |
| `td.LIVE`, `installer_webui`, `installer_inspect` | `os/manifest/installer-isos.json` | not changed: the live ISO, equal at `b216f28f` and HEAD |
| `live_inventory` | `os/release/verify.sh` | read, not run: 22d uses the native signature proof |
| `stock_inventory`, `stock_recipe_probe` | `os/tests/audit.py`, `os/release/pause-stock-updates.sh` | not in this route (probe and `two_disk_vm.main` only) |
| `two_disk_vm` live probe | `os/config/usr/libexec/aresos-keyboard` | package 13 only |
| Guest programs and host data | `owner_console/hidden/key_counter/login/read_diagnostics.py`, `offline_webui.py`, `keyboard_proof.py`, `tty_password.py`, the QEMU keymaps | not changed: harness, not image facts; since `b216f28f` only packages 27, 22c and 22d changed them, none of 23/30/30b/31 |
| The integrator's examples | sudoers and `timestamp_timeout`, the askpass, labwc's `rc.xml`, package lists | no checkout reader: `RULES` reads the guest's own `sudo -l` (not in this route); the askpass is `bootstrap.ASKPASS` of the tools under test, and the walk asserts the guest's live helper; nothing in `os/ci` reads `rc.xml`; `os/packages.lock.json` is read only by `release_diff`/`image_diff` and `test_release27` (the next release's build checks in the regressions step) |
| Harness constants for release 27's session | `ACTIVE_DESKTOP`, foot on tty1 (`Walk.caller`, `terminal_path`), `DAILY_PATH` | not changed: constants written for release 27 (22c's run passed with them); they read nothing of HEAD's image (package 23 changed the autostart there) |

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_tools_local_wiring` | before `walk-host.py`: only the receipt test failed (`verify_release.py`'s new bytes); after: `Ran 27 tests`, `OK` |
| `test_release27` | `Ran 41 tests`, `OK`; its `VerifyRelease` tests also `OK` with 22d's triple set in the environment |
| `test_release_squash_binding`, `test_ci_api_permissions` | `OK` each (7, 4) |
| `test_checkout_sources`, `test_owner_step_limits` | after `rebind.py pending`: `OK` each (6, 4) |
| `test_owner_equality`, `test_owner_path` | `OK` each (11, 48) |
| `test_ways_back_probe` | `Ran 57 tests in 148.578s`, `OK` |
| `test_owner_update` | not run, by the rule |

### What the code doesn't show

- `test_release27.py` is in the ways-back model's import closure (`model_scope.closure()`), so this head changes
  the model's sources: the guard's model gate wants a checks-only run on this head whose model job passed. The
  planned checks-only run gives it.
- On the runner `b216f28f` should be in the clone (checkout `fetch-depth: 0` fetches `origin/pkg/27-first-update-release`);
  if that branch is ever deleted, the fetch by SHA runs (GitHub serves it from PR #35's ref).
- In the VM run, the step's log should show the new line naming `os/Containerfile, os/build.sh,
  os/packages.lock.json, os/config`.

### Left, in order (the next agent continues here)

1. The integrator: a checks-only run on the new head, then the VM dispatch
   (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick -f rehearsal=tools-local`).
2. After a pass: `rebind.py rebind` for 22d, step 7 (record step, final review).

## Step 6, part d (the window before the password; the launcher retried), 2026-11-15, Claude agent on Opus 5.5: done

A read-only preflight before the next VM run found two faults in the walk; the integrator accepted both fixes
(2026-11-15). Commit `ca6abde5`. Nothing dispatched; no owner tool, sudo, ostree, bootc, rpm-ostree or ksshaskpass ran.

### Done

- **HIGH: the password and Escape were typed before the window existed.** `DIALOG` reported the window as soon as a
  `/usr/bin/ksshaskpass` process existed under the caller's sudo (at fork); on a cold KF6/Qt start the keys would go
  to foot (the password, or part of it, plus Enter as a shell command, into `~/.bash_history` and onto the screen).
  - `SETTLE` (part of `DIALOG`): once the helper is found, `settle(pid)` waits until it is at least 3 s past its first
    sighting and its utime+stime (`/proc/<pid>/stat` split after the last `)`, fields 11 and 12 of the rest) has not
    moved for 2 s; it gives up after 20 s (R1's caller closes the window 30 s after its own first sighting; a test
    holds `most + 10 <= R1_SECONDS`). A zombie or unreadable stat counts as gone. After the wait `DIALOG` reads the
    processes again (same helper, same sudo; the keyring list then); a helper gone before it settled reports
    `the window closed before it settled`, which `Walk.window` turns into a STOP. The answer carries `settled`, `gone`
    and `settle_seconds`; each `dialogs` row of the result records `settled` and `settle_seconds`.
  - **After a give-up the walk goes on** (the integrator's "give up after about 20 s, must stay under R1"): the picture
    check below still stands between it and the password.
  - **The picture check:** `Walk.launch` takes `<stage>-before` just before typing the launcher; `Walk.window` takes
    `<stage>-window` after DIALOG and compares the middle half of the screen each way (`centre_change`: pixels where
    any channel differs). At least 1% of it must differ (`CENTRE_CHANGED`), or `STOP: no window on the screen at
    <stage> (...); nothing was typed`. The result is saved as `<stage>-window-centre` and in the dialog row
    (`before`, `centre_changed`). labwc places new windows in the middle (its default policy; release 27's `rc.xml`
    sets none) and maximizes foot.
  - **My addition: Ctrl+L before the before-picture.** Without it, "differs" would pass whenever foot's own lines in
    the centre changed (the launcher line, the next prompt, a scroll), so the check would not show a dialog. Ctrl+L
    (bash's readline `clear-screen`; neither labwc's nor foot's bindings take it) puts foot's prompt at the top, so
    the centre of foot's maximized window stays empty unless a window opens there. A glyph in the centre is under
    the 1% (tested); the dialog covers about a third of it.
- **MODERATE-LOW: the launcher line could be lost after a real VT switch** (tl-v3 from tty4, tl-install and tl-export
  from tty3), with no retry. `Walk.launch` now sends Ctrl+U (drops a partial line, also keys left by Ctrl+Alt+F1 on
  an already active tty1) and Ctrl+L, waits 0.5 s, takes the before-picture and types the launcher. `LAUNCHED` waits
  up to 20 s for `<out>/log` and prints `found` true/false, exiting 0 either way (no `failed_command`). On a miss:
  screenshot `<stage>-launch-miss`, the same launch again (picture `<stage>-before-retry`, which the window is then
  compared with), check `<stage>-launched-retry`; a second miss is `STOP: the caller did not start at <stage>: its
  launcher, typed twice in foot, never ran`. `launcher(out)` starts with `set -C`, so the `> <out>/log` of a second
  start refuses (`cannot overwrite existing file`, exit 1) and a late first line cannot start a second caller.
- **The local walk** (`test_owner_walk.ToolsLocal`): a caller starts only once its launcher reached foot (`lost`
  drops a stage's first lines; the window capture answers `no window` until then); `-launched` captures are answered
  from that; every screenshot is a picture (foot's typed lines at the top; on `<stage>-window` the stage's dialog in
  the middle unless `hidden`); the dialog answer carries `settled`.

### Tests (`os/tests/test_tools_local_wiring.py`)

- `SettleTest` (fake `/proc` stat lines, fake clock): the CPU time read after the last `)` (a name with spaces and
  `)`), zombie/dead/missing/short lines are gone; an idle helper settles at 3 s; one still drawing settles 2 s after
  its CPU time last moved (7 s); one that never settles is given up at 20 s (and 20 + 10 <= R1's 30); one that
  vanishes is gone (at 1 s, and at once).
- `DialogProgramTest`: the real `DIALOG` program here against a stand-in sudo and helper (`exec -a`, `sleep`
  underneath): reports the window only after 3 s, `settled`, the helper's argv, parent and uid; a helper killed at
  2 s is `the window closed before it settled`.
- `WindowPictureTest`: only the centre counts (foot's top lines do not; one glyph is under the threshold; a centred
  dialog is far over it, with its box); pictures of different sizes STOP.
- `LauncherTest`: `launcher()` begins `#!/bin/bash`, `set -C`; run twice with bash here, the caller runs once and the
  second start fails with `cannot overwrite existing file`.
- `LaunchOrderTest` (`Walk.caller` with a stand-in guest): the exact order switch → foot ready → session → 1 s →
  Ctrl+U → Ctrl+L → 0.5 s → `<stage>-before` → launcher typed → `<stage>-launched`; a first miss adds
  `<stage>-launch-miss` and the same sequence with `-before-retry` / `-launched-retry`; a second miss STOPs naming
  the stage after typing exactly twice.
- `WalkTest`: every dialog settled, its before-picture is `<stage>-before` and comes before its window picture, its
  centre changed by at least the threshold; a walk whose tl-install launcher is lost once passes with the launcher
  typed twice there (once everywhere else) and the miss picture between the two before-pictures; a walk whose tl-v3
  window stays off the screen STOPs (`no window on the screen at tl-v3`) with nothing typed after the window was seen.

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_tools_local_wiring` | before `walk-host.py`: only the receipt test failed (`tools_local.py`'s new bytes); after: `Ran 41 tests in 55.230s`, `OK` |
| `test_owner_walk` | `Ran 27 tests in 104.522s`, `OK` |
| `test_checkout_sources` | after `rebind.py pending` (38 files wait): `Ran 6 tests`, `OK` |
| `test_owner_step_limits` | `Ran 4 tests`, `OK` |
| `test_owner_update` | not run, by the rule |

`walk-host.py`: `PASS package 22d host walk (tools-local): 263 sources`.

### What only the VM can show (watch these in the next run)

- Each dialog row's `settle_seconds` and `settled` (a give-up at 20 s means the helper kept using CPU, e.g. a
  blinking cursor; the picture check then decided), and `centre_changed` with the `<stage>-before` and
  `<stage>-window` pictures side by side.
- Whether any `<stage>-launch-miss` picture exists (a lost first line) and what it shows.
- That Ctrl+L cleared foot (the before-pictures show the prompt at the top).

### Left, in order (the next agent continues here)

1. The integrator: a checks-only run on the new head (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick
   -f checks_only=true`), then the VM dispatch (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick
   -f rehearsal=tools-local`).
2. After a pass: `rebind.py rebind` for 22d, step 7 (record step, final review).

## Step 6, part e (two stick removals in one boot; the VM dispatch cap), 2026-11-15, Claude agent on Opus 5.5: done

VM run 43714310216 (tools-local, dispatch 3 of 4, on `fca1d2a1`) stopped at the guest command
`export-version-2-unplug-confirmed-xhci-health` with `AssertionError: STOP: repeated tools-stick disconnect`
(`counts['expected_disconnect'] <= 1` in `owner_xhci.classify`). Nothing dispatched here; no owner tool, sudo,
ostree, bootc, rpm-ostree or ksshaskpass ran.

### Where it stopped: in 22d's own walk, near its end (not in package 27's route)

The run passed package 27's route and almost all of 22d's walk. Recorded stages: `tl-v3`, `tl-cancel`,
`tl-unanswered`, `tl-cut`, `tl-install`, `tl-tamper`, `tl-stick-next`, `tl-export`; the stick holding version 2 was
taken with its retired-bundle line (`export-version-2-stick-owner-result`: passed). It stopped at that stick's
removal, the last step of boot 12 (`cut-27`), before `tl-export-stick`, the restart and `final-27`.

### The cause (harness, not a flake)

The xHCI health context is made once per boot (`owner_vm.Guest.__init__`): `since_usec=0` (package 14's choice: the
whole boot, so early failures cannot hide) and `expected_disconnect=None`. `Media.detach` set
`expected_disconnect` to the stick's port and nothing ever reset it, and `classify` excused one disconnect of that
port per boot. Every route before 22d removes the stick at most once per boot (`tools-stock` boot 7, `update-tools`
boot 10, 22c's `tools-3`); 22d's walk is the first to remove it twice in one boot: `tools-next` and
`export-version-2`, both in `cut-27` (`tools_local.py:687-721`). 22d changed no media or xHCI code
(`git diff 58738e5e..fca1d2a1`: only `require_runner` admits 22d).

From the run's counts-only results (`checked` = kernel lines since boot; the lines' text never leaves the guest):

| Check | boot | expected | unrequested | checked |
|---|---|---|---|---|
| `tools-stock-requested-unplug` → `-unplug-confirmed` | 7 | 0 → 1 | 0 | 816 → 819 |
| `update-tools-requested-unplug` → `-unplug-confirmed` | 10 | 0 → 1 | 0 | 814 → 817 |
| `tools-next-requested-unplug` → `-unplug-confirmed` | 12 | 0 → 1 | 0 | 817 → 820 |
| `export-version-2-before-hotplug` (the next stick, same boot) | 12 | **1** | 0 | 820 |
| `export-version-2-requested-unplug` | 12 | 1 | 0 | 837 |
| `export-version-2-unplug-confirmed` | 12 | 2: STOP | | |

Each unplug logged exactly one disconnect line of port `2-2` (each `-tools-usb-port` capture resolved `2-2`); the
second removal's check counted the first removal's line too. Replayed here: HEAD's `owner_media`/`owner_xhci` through
the real `Media.attach`/`detach` twice in one boot against a modelled kernel journal stop with the run's traceback
(`<module>` line 50, `kernel_health` line 32, `classify` line 21, `repeated tools-stick disconnect`) at the second
`unplug-confirmed`.

### The fix: each requested removal excuses one line of its own

- `owner_media.Media.detach`: the `-tools-usb-port` program (run while the stick still exists, just before the
  `requested-unplug` checkpoint and QMP `device_del`) also prints `requested_usec`, the guest's `CLOCK_MONOTONIC`;
  the context's new `removals` list gains `[port, requested_usec]`.
- `owner_xhci.classify(rows, since, boot, removals)`: a disconnect line of a requested port belongs to the latest
  request for that port at or before its `__MONOTONIC_TIMESTAMP`; each request excuses one (`STOP: repeated
  tools-stick disconnect` otherwise); a disconnect of the port before its first request, or of any other port, is
  unrequested (STOP while the stick is attached or needed, as before). `since_usec` stays 0: the whole boot is still
  read, nothing is excused by moving a window. journald stamps a kernel line on `CLOCK_MONOTONIC` when it receives it
  (checked on this laptop, systemd 259: `__MONOTONIC_TIMESTAMP` is 0.06 to 0.3 s after `_SOURCE_MONOTONIC_TIMESTAMP`,
  on the clock `time.clock_gettime(CLOCK_MONOTONIC)` reads), so a removal's line comes after its request, and the
  previous removal's line was already read by its `unplug-confirmed` check before the next stick was attached.
- `preamble` refuses a malformed `removals` (not `[str port, int >= 0]`, out of order) and the old key; each health
  result also carries `tools_removals_requested`. `owner_vm.Guest` starts each boot with `removals=[]`.
- The explanation is a comment above `classify`, not a docstring: that source goes to the guest over the serial
  line with every checkpoint and guarded observer (`classify` grows 155 bytes).
- With one removal per boot (every earlier route) the result is the same, except that a tools-port disconnect logged
  before the request is no longer excused once the request is made (the `before-unplug` check already stopped on it).

### The VM dispatch cap (integrator's decision, 2026-11-15)

Ledger `22d`: `vm_dispatch_cap` 4 → 6, `tools-local` 4 → 6, with the dated reason in the budget text (the runners are
free for this public repository, the caps stop runaway loops, three runs stopped on harness issues: 43690565301 before
the VM, 43699785728 at the stand-in origin, 43714310216 here); the brief's budget line notes it. Minutes 2400 and
checks 20 stay. At run 3's dispatch the ledger stood at 595 consumed minutes, 10 checks runs and 3 VM dispatches.

### Tests

- `test_owner_ps2`: `context()` takes `removals`; `test_each_requested_removal_excuses_one_disconnect_of_its_port_after_it`
  (run 3's two lines pass; a line before the first request, another port, two lines for one request, a line between
  the requests, no requests); `test_context_refuses_malformed_or_unordered_removals`; `StickRemovalsInOneBootTest`
  runs the real `Media.attach`/`detach` twice in one boot (the real `-tools-usb-port` program over a stand-in sysfs
  folder, the real checkpoint programs over a modelled journal, `Media.verify` and saving stubbed): counts (0,0) →
  (1,0) → (1,0) at the second `before-hotplug` → (2,0), never a stop; one unplug logging two lines still STOPs.
- `test_tools_local_wiring.LedgerTest`: the caps 6/6, the dated sentence; `test_six_vm_dispatches_and_no_seventh`
  (the guard's budget with six tools-local runs passes, a seventh stops).

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_owner_ps2` | `Ran 18 tests`, `OK` (14 before) |
| `test_tools_local_wiring` | before `walk-host.py`: only the receipt test failed (`owner_media.py`'s new bytes); after: `Ran 42 tests`, `OK` |
| `test_owner_walk` | `Ran 27 tests in 105.176s`, `OK` |
| `test_checkout_sources` | after `rebind.py pending` (40 files wait): `Ran 6 tests`, `OK` |
| `test_owner_step_limits`, `test_rehearsal_budget`, `test_organization_budget`, `test_owner_guard`, `test_owner_media` | `OK` each (4, 4, 19, 12, 6) |
| `test_owner_reset` | with `PYTHONPATH=os/ci` (it imports `owner_vm` directly; without it the import fails, also on HEAD): `Ran 4 tests`, `OK` |
| `test_ways_back_probe` | `Ran 57 tests in 147.734s`, `OK` |
| `test_owner_update` | not run, by the rule |

`walk-host.py`: `PASS package 22d host walk (tools-local): 263 sources`. `rebind.py pending` ran (40 files).

### What only the VM can show (watch these in the next run)

- `export-version-2-tools-usb-port` carries `requested_usec`; `export-version-2-unplug-confirmed-xhci-health` should
  show `expected_disconnect: 2`, `usb_disconnect: 0`, `tools_removals_requested: 2`.
- The walk's remaining stages: `tl-export-stick`, the restart, `final-27` (check, title, logout), both final markers,
  `tools-local-rehearsal-result`.

### Left, in order (the next agent continues here)

1. The integrator: a checks-only run on the new head (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick
   -f checks_only=true`), then VM dispatch 4 of 6 (`gh workflow run "OS image" --ref pkg/22d-tools-without-stick
   -f rehearsal=tools-local`).
2. After a pass: `rebind.py rebind` for 22d, step 7 (record step, final review).

## Step 7, record step, 2026-11-15, Claude agent on Opus 5.5: done (the final review follows)

VM run 4, [43737933979](https://github.com/Ares-Empire/AresOS/actions/runs/43737933979) (`tools-local`, on `89bc0658`),
passed. Its evidence was downloaded once by the integrator; this step read it from there. Nothing dispatched; no owner
tool, sudo, ostree, bootc, rpm-ostree or ksshaskpass ran.

### Done

1. **The rebind.** `rebind.py` read from source first; then, run once:
   `python3 reviews/27-first-update-release/rebind.py rebind 22d <evidence>/two-disk/22d-bound-sources.json 43737933979`
   printed **recorded 6 tables, 263 unique sources for package 22d; 40 waiting files and 0 removed paths moved to the
   history; pending list empty**. `os/manifest/ci/22d/source-bindings.json` (run 43737933979, commit `89bc0658`) are now
   the active tables; the history's new entry waited for 22c's bindings.
2. **The receipt freezes.** `test_tools_local_wiring.ReceiptTest` is now
   `test_the_receipt_is_fresh_until_the_record_step_and_frozen_after`, as 22c's `HostWalkReceiptTest`: once 22d's
   bindings exist it asserts that the receipt's sources equal their table 0; before that it runs the freshness check as
   it was. `os/manifest/ci/22d/host-walk.json` is unchanged and is never regenerated from now on.
3. **The status row.** `docs/INSTALL-STATUS.md`'s 22d row: **BUILT AND REVIEWED; VM REHEARSAL PASSED; NOT ON THE
   LAPTOP**, the checks-only run 43729592775, run 4's link and head, what it walked, the three earlier runs, a link to
   the captures, "The laptop has not run this route yet", and the final review before "on the laptop". The bound
   `test_owner_path.py` pinned "NOT REHEARSED" and "**not rehearsed**", so its pin changed with the row (as 22c's record
   step did): the new status, the run and head the 22d bindings name, the captures link, the three PASS lines, the
   audits, "not run this route yet", and the old words refused. It fails on the old row (checked by hand).
4. **22c's gate test after 22d's rebind** (the lesson from 22c's record step). After the rebind
   `test_ways_back_probe.RunnerTest.test_the_probe_reads_package_22cs_host_walk_and_refuses_a_stale_one` failed in both
   modes (`Host walk is stale`). It hands `owner_vm.main('22c', …)` 22c's frozen receipt with each row that waits on the
   list replaced by the list's bytes; the rebind moved the 40 files that waited into 22d's bindings and emptied the
   list, so the rows changed since 22c's run were named nowhere it looked. It now takes those rows from the active
   bindings (`checkout_sources.merge(active_tables(ROOT))`: 22d's since this step; while 22c's were active they equal
   the receipt), then from the list. So it stays fresh only if the chain names every changed file the walk binds:
   with `test_owner_path.py` taken off the list by hand it fails again (`Host walk is stale`; list restored).
5. **The waiting list.** `rebind.py pending "22d record step: …"` (after the last bound change): **pending: 3 bound files
   differ from the active bindings, 0 removed** (`os/tests/test_owner_path.py`, `os/tests/test_tools_local_wiring.py`,
   `os/tests/test_ways_back_probe.py`). Its `status` names them, as 22c's did.
6. **The captures**, `reviews/22d-tools-without-stick/runs/tools-local-43737933979/` (98 files, 940 kB): the result
   file; every stage's decoded `tl-*` JSON and both pictures (`-before`, `-window`) for v3, Cancel, unanswered, cut,
   install, tamper and export, plus the cut's watcher, the install's records and receipt fields, the export's access
   check, the stick-next and export-stick stage rows; the xHCI health at the first removal's `unplug-confirmed`, the
   second stick's `before-hotplug`, `requested-unplug` and `unplug-confirmed` (expected 1, 1, 1, 2; `usb_disconnect` 0;
   `tools_removals_requested` 1, 1, 1, 2), and that removal's port file; the PASS pictures of the stick install of
   version 5, its check, the export to the version 2 stick and the final check and title; both final Windows marker
   texts; `22d-bound-sources.json`; `22d-dispatch-authorization.json`; `index.json` (each file's SHA-256, what was
   left out and replaced, the patterns searched, and the 15 protected-disk audits, each equal to the baseline).
   - **Left out (privacy):** the tools' full results with their trace (`tl-install-receipt.json`, the stick install's and
     check's, the version 2 stick export's, the final check's and title's): each holds the VM disks' partition and
     filesystem UUIDs, and the repository holds no GUIDs, also not a throwaway VM's (22c's rule). In their place
     `tl-install-receipt-fields.json` is the receipt without its trace, and the PASS pictures show the lines. The two
     Windows marker pictures show the VM's Windows-stand-in ESP GUID, so they are left out; in the two marker texts that
     GUID became `VM-WINDOWS-ESP` (the only change to any copied file).
   - **Searched for** before writing: 22c's forbidden patterns (tokens, credential headers, password hashes, the
     harness password's shape, private keys), emails, GUIDs, `serial`, and the names `patrik`, `carlsen`, `lenovo`,
     `micron`, `crucial`. What remains: "password" only in sudo's messages, "serial" only in the tools' "stock serial"
     line and in bound test file names. Every kept picture was looked at: the desktop with foot and the window, and
     console text (PASS lines, ostree checksums, image digests).
   - The copy was made by a scratch script outside the repository (not committed).

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_checkout_sources` | right after the rebind `Ran 6 tests`, `OK`; after the last change `Ran 6 tests`, `OK` |
| `test_owner_step_limits` | `Ran 4 tests`, `OK` |
| `test_owner_path` | first 4 failures: a link to the 22d `REPORT.md`, which does not exist yet (the link check refuses it); the row links the captures instead; then `Ran 48 tests`, `OK` |
| `test_tools_local_wiring` (the receipt test's module) | `Ran 42 tests in 54.688s`, `OK` |
| `test_owner_bootstrap` | `Ran 13 tests`, `OK` |
| `test_owner_equality` | `Ran 11 tests in 72.987s`, `OK` |
| `test_owner_sources` | `Ran 13 tests in 73.906s`, `OK` |
| `test_ways_back` | `Ran 56 tests in 30.278s`, `OK` |
| `test_ways_back_probe` (reads the waiting list and the bindings; 22c's lesson) | after the rebind 2 failures (item 4); after its fix `Ran 57 tests in 148.418s`, `OK` |
| `test_owner_update` | not run, by the rule (hosted: green in 43729592775) |

### Not done, for the integrator

- **Review 8's finding 3** (brief decision 11 puts it in the record step): a test that fails while a status row says VM
  REHEARSAL PASSED and a tool or guide file waits, or while the result's fingerprint differs from `SHA256SUMS`. It is a
  new test in a bound file, which this step's rules did not allow. Today the chain holds by hand: only three test files
  wait, and run 4's `tools` equals the payload's fingerprint `dcbc375f…`.
- **`unwalked_commands`** in the waiting list still names `tools-folder`, `tools-routine` and `export-routine`, and its
  `unwalked_rule` says they wait "until 22d's rehearsal types them". Run 4 ran all three (the caller runs them; it types
  only a launcher). `test_owner_equality` counts only typed blocks, so taking them off the list would fail it. Either
  that test learns the tools-local walk's lines, or the rule's sentence says how 22d's lines were walked.
- `test_checkout_sources.test_current_receipts_agree_and_package14_stays_historical` picks the first of
  `('22c', '27', '16')` with bindings, so it still checks 22c's receipt, not 22d's (it passes). Adding `'22d'` (and
  `'22d': '22c'` in its map) is a bound change; not made here.
- The row links the captures, not the report: `REPORT.md` does not exist until the integrator commits it. A report link
  then needs the row and its pin again.

## Step 7b (review 8's finding 3; the walked routine lines), 2026-11-15, Claude agent on Opus 5.5: done

Tests and their data only; the tools payload is unchanged (`sha256sum os/owner-tools/payload/SHA256SUMS` was
`dcbc375f…597be` before and after). Nothing dispatched; no owner tool or sudo ran.

### Done

1. **Review 8's finding 3** (package 22c), in `os/tests/test_checkout_sources.py`:
   `test_a_row_that_says_vm_rehearsal_passed_holds_only_what_the_rehearsal_ran`. For every row of
   `docs/INSTALL-STATUS.md` whose status says **VM REHEARSAL PASSED; NOT ON THE LAPTOP** (today 22c's and 22d's):
   - nothing waits on the list (files or removed paths) but test files (`os/tests/`) and the CI workflow
     (`.github/workflows/`);
   - the row names exactly one `[rehearsal run <id>]`, that run's committed result
     (`reviews/*/runs/*-<id>/*-rehearsal-result.json`) passed, and the row's `Tools fingerprint` is the one the result
     names (22c: `tools_version_3`, 22d: `tools`, in `REHEARSED_TOOLS`);
   - for the newest rehearsal's row (the package whose bindings are active, found by matching
     `checkout.active_tables`, so no package order is copied): the run and commit are the active bindings', and the
     result's fingerprint equals `sha256(SHA256SUMS)`. Run 4's `tools` is `dcbc375f…`, as the payload's.
   22c's row is held the same way except for the payload: its version 3 never goes on the laptop (the row says so) and
   22d's later rehearsal took over, so 22c's row is held to its own run 43597505549 (`2084c786…`), 22d's to the payload.
   Each failure names the row and what changed, and ends: "Rehearse again (a VM run of the route, then its record
   step), or move the row on: it may say "VM REHEARSAL PASSED; NOT ON THE LAPTOP" only while the laptop would get
   exactly what that rehearsal ran."
   - **Which files may wait.** The finding's fix names `os/owner-tools/`, `os/release/` and `docs/`; the rule the list
     states is "only test files and the CI workflow", and the step's brief says that is the rule to enforce. So the
     test allows only those two and refuses everything else bound (tools, release scripts, guides, the harness in
     `os/ci/`, the host walks, the image manifest). Stricter than the finding: a harness-only change for a later
     package also trips while a row still says rehearsed, and then the row moves or the integrator widens `MAY_WAIT` as
     a recorded decision.
     **Integrator's decision (2026-11-15, after step 7b):** narrowed to the finding's three folders as
     `MUST_NOT_WAIT = ('os/owner-tools/', 'os/release/', 'docs/')`: what the laptop gets. A waiting harness file
     changes how a rehearsal runs, not what the laptop gets, and waits for the next rehearsal as package 27b allows;
     otherwise release 28's harness steps would trip on 22d's row. The negative control now also proves a waiting
     `os/ci/` file passes.
   - **A negative control in the suite:** `test_a_rehearsed_row_refuses_waiting_tools_or_guides_and_other_tools`
     runs the same check on a small made-up table (so it stays valid when the real rows move): a waiting tool, guide,
     release script or harness file, other tools than the run's, a row naming other tools or another run, a run that
     did not pass, a result without the field and a row without its package all fail; with the rows moved to "ON THE
     LAPTOP" the same waiting files and other tools pass.
   - **Proved on the real files** (a scratch script outside the repository, deleted after): the real test passed as
     committed; with `os/owner-tools/owner.py` added to a scratch copy of the list it failed with "…rows for packages
     22c and 22d say VM REHEARSAL PASSED; NOT ON THE LAPTOP, but these bound files changed since the last VM rehearsal
     (…/runs/43737933979) and wait on os/manifest/ci/16/pending-rebind.json: os/owner-tools/owner.py. While such a row
     stands only test files and the CI workflow may wait. Rehearse again …"; with one changed byte in a scratch copy
     of `SHA256SUMS` it failed with "…row for package 22d says … but the tools changed since: run 43737933979
     rehearsed tools fingerprint dcbc375f…, and os/owner-tools/payload/SHA256SUMS now hashes to 4135bd67…. Rehearse
     again …"; with the scratch gone it passed again.
   - The list's `decision` gains this rule in a sentence.
2. **`unwalked_commands`: the test learned the caller's lines** (the smaller honest fix of the two; rewording the rule
   would have kept three walked commands on a list of unwalked ones). `test_owner_equality`'s
   `test_every_owner_command_equals_the_command_physically_typed_by_ci` now also walks 22d's route
   (`walk.walk(route='tools-local')`) and counts as walked every `commands.json` entry the harness has the caller run
   (`local.callers[stage]['entries']`, read from the program the harness sends, as the walk's model does). So
   `tools-folder`, `tools-routine` and `export-routine` count as walked and left the list (`unwalked_commands: []`);
   the test refuses a listed command once it is typed or run. The run's captured caller results agree:
   `line_sha256` in `tl-cancel/-unanswered/-install-caller-result.json` (folder `c1b579be…`, routine `0b11cfc5…`)
   and `tl-export-caller-result.json` (`7e1ffa76…`) are the SHA-256 of today's three entries. The list's
   `unwalked_rule` and the function's docstring say how 22d's lines were walked. The module takes about 13 s longer.
   Proved by a scratch script (deleted after): with `tools-routine` put back on the list the test fails (the routine
   line "unexpectedly found" among the walked lines).
3. **The waiting list.** `rebind.py pending "22d step 7b: review 8 finding 3 test; unwalked routine lines"`, run
   once after the last bound change: **pending: 5 bound files differ from the active bindings, 0 removed**
   (`os/tests/test_checkout_sources.py`, `test_owner_equality.py`, `test_owner_path.py`, `test_tools_local_wiring.py`,
   `test_ways_back_probe.py`); all under `os/tests/`, so the new test passes on them. The list's `status` names the two
   new ones.

### Tests run here (Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`)

| Module | Result |
|---|---|
| `test_owner_equality` | `Ran 11 tests in 85.879s`, `OK` |
| `test_checkout_sources` | `Ran 8 tests`, `OK` (after the waiting list) |
| `test_owner_path` | `Ran 48 tests`, `OK` |
| `test_tools_local_wiring` | `Ran 42 tests in 54.738s`, `OK` |
| `test_ways_back_probe` (reads the list and the bindings) | `Ran 57 tests in 147.563s`, `OK` |
| `test_owner_sources` | `Ran 13 tests in 71.531s`, `OK` |
| `test_owner_update` | not run, by the rule |

### What happens after merge (for the integrator)

- While 22c's or 22d's row says **VM REHEARSAL PASSED; NOT ON THE LAPTOP**, any change to a bound tool, guide, release
  script or harness file fails `test_checkout_sources` once it waits (and a payload change fails it at once, waiting
  or not). Release 28's work changes `docs/` and `os/owner-tools/`: before that, both rows move on (22d's to "on the
  laptop" after his install; 22c's too, since version 4 carries its ways back, or to words saying version 3 was
  superseded), each with its pin in `test_owner_path.py`. Or a new rehearsal records its bindings and its own row.
- A new rehearsal's row needs an entry in `REHEARSED_TOOLS` (the result's field naming its tools); the test says so.

## Report (for the integrator to commit as REPORT.md)

# Package 22d: the owner tools without the stick, from Claude's terminal

Brief: `briefs/22d-tools-without-stick.md` (empire brief 291). PR #66, branch `pkg/22d-tools-without-stick`. Builders:
Claude agents (step 1 on Fable 5.2, the other steps on Opus 5.5). Reviews 1 and 2 on Fable, 3 and 4 on Opus; the final
review before the laptop (review 5, Fable) found it SAFE, and step 8 closed its findings (main merged in, this text).

## Done

**What 22d gives the owner.** New owner tools no longer need the USB stick, Windows or the black console. Claude runs
two lines in its own terminal. The first (as `ares`, no window) fetches GitHub's main, checks that the commit announced
on the board is on it and holds exactly the tools with the published fingerprint, and puts those tools in a folder. The
second opens a small password window on the laptop's screen. When he types his password there, the tools install,
then check and title run, all from that one password. Before typing, he compares the 8 characters in the window with
line 1 of `docs/OWNER-TOOLS.md`, opened on his phone from his own bookmark. Records can be exported the same way; without
a stick they go to `/run/ares-records`, on this laptop only. The stick and the console stay as the emergency route,
and the very first installation stays on the stick. Installing from the stick keeps every rule; beside it two things
are new: `export` to the stick also takes a stick holding tools this laptop installed before (with a line saying so),
and an update begun from the folder may be finished from a stick. The window stops accidents and a Claude acting
unasked, not a tricked Claude; the guide says so in plain words.

- **The tools** (`os/owner-tools/owner.py`, `media.py`, tools version 4): the start block that ran decides the route
  (stick: every old rule; folder: no console, no stick); the journal keeps its schema and adds `source`; a folder-begun
  update resumes from either route, a stick-begun one only from that stick; the receipt names the source and the caller
  (login uid, terminal or not); export without a stick copies to `/run/ares-records` (root's, readable by his uid), and
  a stick holding tools this laptop installed before is accepted with a line saying so. Review 8's findings 2 and 5: a
  cleanly stopped update closes its record, and a layout trial from before a restart names `layout abandon`.
- **The lines** (`bootstrap.py`, `commands.json`): Claude's folder line, the tools-only routine line and the routine
  export line, generated, pinned and tested; the routine line is taken from the announced commit itself.
- **The guides:** `docs/OWNER-TOOLS.md` (new), the routine box first in `docs/INSTALL.md`'s update route, a routine STOP
  card in `docs/EMERGENCY.md`, the 22d row in `docs/INSTALL-STATUS.md`.
- **The rehearsal** (`os/ci/tools_local.py`, mode `tools-local`, ledger `22d`): the owner's route in a VM, with a
  stand-in caller in his desktop session and no terminal, a dialog driver that checks the window before typing.

## Verified

**The VM runs** (mode `tools-local`, from the laptop's state: R27 by tools version 2, R13 and the pinned stock):

| Run | Head | What happened | Fix |
|---|---|---|---|
| [43690565301](https://github.com/Ares-Empire/AresOS/actions/runs/43690565301) | `cb2a1eec` | Stopped before the VM: release 27's check compared its image sources with this checkout, which holds unreleased image changes from main | Step 6c: in this mode release 27's facts are read from its own source commit `b216f28f`; the switch job gets the mode as step env (`7889ba5e`) |
| [43699785728](https://github.com/Ares-Empire/AresOS/actions/runs/43699785728) | | Stopped at the stand-in origin's setup: the bundle carried `main` but no `HEAD`, so the clone had nothing to check out | `1b733a4f`: the stand-in names `main` as `HEAD`; the checkout clones `--branch main`. Then step 6d (a read-only preflight): the password or Escape could reach foot before the window existed; now the driver waits until the window has settled and a picture shows it, and the launcher is retried once |
| [43714310216](https://github.com/Ares-Empire/AresOS/actions/runs/43714310216) | `fca1d2a1` | Passed almost all of the walk; stopped at the second stick removal in one boot (`repeated tools-stick disconnect`): the USB health check excused one removal per boot | Step 6e: each requested removal excuses one disconnect of its own port after it; VM dispatch cap 4 to 6 (integrator) |
| [43737933979](https://github.com/Ares-Empire/AresOS/actions/runs/43737933979) | `89bc0658` | **Passed** | |

Run 4, stage by stage (captures in `reviews/22d-tools-without-stick/runs/tools-local-43737933979/`):
- **Version 3 refuses:** its window (label `2084c786`, wrapped onto two lines), password typed, then `STOP: Tools update
  runs only from the physical recovery console` and `STOP bootstrap: verification or install refused`; nothing changed.
- **Cancel:** Escape in the window; `sudo: no password was provided`, exit 1; nothing changed.
- **Unanswered:** the caller closed the window after 30 s (standing in for the 10 minutes) by stopping only the password
  helper; the same line and exit; nothing changed.
- **Cut:** password typed, the install frozen between the copy and the switch, hard reset; after the restart the old
  tools' `check` passed and the record still named the new tools.
- **Install:** the next window resumed it: `PASS install` (version 2 to 4), `PASS check`, `PASS title`; the receipt
  names `source: folder`, login uid 1001, no terminal; `sudo -n true` refused afterwards (no password kept).
- **Tamper:** one changed byte in the tools folder: `STOP bootstrap: verification or install refused` before any tools
  code ran; nothing changed.
- **Stick with a next version:** a test bundle, version 5 (`4125f556…`, never published), installed from the stick at
  the console by version 4's own stick route.
- **Export:** without a stick through the window: `PASS export`, 42 files under `/run/ares-records`, `ares` reads them,
  another account cannot; to a stick holding version 2: accepted with `The stick holds tools this laptop installed
  before (SHA256 851eb742…), not the installed ones`.
- **End:** restart, check and title passed; both Windows starts (unattended and detached) reached the Windows marker.
- In every window: title bar **Enter SSH Credentials**, the helper's argument equal to the label, the window settled
  (3.0 to 4.6 s) and visible (25 to 28 % of the screen's centre changed), no keyring process started; the caller had
  no terminal. Every protected-disk audit equalled the baseline over 15 starts.
- The announced commits were a stand-in GitHub inside the VM whose `os/owner-tools` tree equals the real commit's
  (`89bc0658` ↔ stand-in `7e018ac5`, tree `73fb5929`; version 3's `58738e5e` ↔ `49de19e8`, tree `b322a88e`).

**Hosted checks:** checks-only run [43729592775](https://github.com/Ares-Empire/AresOS/actions/runs/43729592775) on
`89bc0658`: green, 1613 tests, full model, nothing skipped. Budget at run 4's dispatch: 776 of 2400 minutes, 11 of 20
checks runs, 4 of 6 VM dispatches. Step 8 merged main into the branch: that head (and the commit announced on the
board) needs its own green checks-only run with the full model; run 43755153393 tested `7ef03022`, before the merge.

**Locally** (Python 3.14, one module at a time, slice model): every step's modules, listed in each step's section of
`PROGRESS.md`; after the record step `test_checkout_sources`, `test_tools_local_wiring`, `test_owner_path`,
`test_owner_step_limits`, `test_owner_bootstrap`, `test_owner_equality`, `test_owner_sources`, `test_ways_back` and
`test_ways_back_probe`; after step 7b `test_checkout_sources`, `test_owner_equality`, `test_owner_path`,
`test_tools_local_wiring`, `test_ways_back_probe` and `test_owner_sources`; after step 8 (the merge) those six
and `test_owner_bootstrap`, and main's `test_ways_back_model` and `test_aresos_desktop` (they read the workflow and
the ledger) and `test_journal_ready` (it reads `os/ci/vm.py`). `test_owner_update` runs hosted only.

**The fingerprint:** tools version 4 is `dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be` (SHA-256 of
the payload's `SHA256SUMS`). It is pinned, and tests hold equal: `docs/OWNER-TOOLS.md` (line 1 `Owner tools version 4:
dcbc375f`, then the full value), `os/owner-tools/commands.json` (= `bootstrap.command` and `bootstrap.lines`), the stick
blocks, Claude's folder line, both window labels and the PASS lines in `docs/INSTALL.md`, `docs/EMERGENCY.md` and the
22d row of `docs/INSTALL-STATUS.md`. Run 4's result names the same value. The record step rebound 263 sources to
`os/manifest/ci/22d/source-bindings.json`; six bound files changed since wait on the list: five test files (three by
the record step, two by step 7b) and `os/ci/vm.py`, which main's package 23b changed (merged in by step 8). A test now
holds this chain (package 22c's review 8, finding 3): while a status row says **VM REHEARSAL PASSED; NOT ON THE
LAPTOP**, nothing under `os/owner-tools/`, `os/release/` or `docs/` may wait (what the laptop gets; a harness, workflow
or test file may wait for the next rehearsal), each such row names the tools its run rehearsed, and the newest
rehearsal's tools (run 4's) equal the payload's. 22d's three lines (folder, routine,
export) count as walked: the run's caller ran them, and they left the list of unwalked commands.

## Not verified

- **The laptop.** Nothing of 22d has run there; the owner's session comes after merge ("Try this" below).
- In the VM: the real 10 minutes (30 s there), the real GitHub (a stand-in origin with the same tools tree), a run with
  stdin closed (not walked), and a keyring only as processes (none started).
- **No uninterrupted install from version 2 to 4.** In run 4 the copy ran before the cut and the rest after it, so
  every phase ran on a real system, but never in one run. The uninterrupted folder install runs on fakes
  (`test_owner_sources`), and in the VM only by the stick route (version 4 to 5). Enough, but not the same run.
- **Claude's Bash tool as the caller.** In the VM a program read the line and ran it; on the laptop Claude does that by
  the recipe in "Try this", whose hashes are the lines run 4's caller ran.

## JUDGMENT-CALL (for the owner: the words only)

He decides wording; everything else is settled. Changing any of the ten wordings before the laptop session means a new
VM rehearsal (one of the two VM runs left, then its record step), because all ten live in the tools, `commands.json` or
the guides, which may not change while 22d's row says the VM rehearsal passed. The reviewer advises keeping all ten
for this install; wishes ride with the next tools version, which release 28 needs anyway. (The owner answered on board
#307, 2026-11-15: "Keep as written"; all ten stand, so no new rehearsal.) After the laptop session,
changing a line inside the tools costs a new tools version; changing a line outside them costs new generated lines,
their tests and the guide's quotes, but no tools version.

Inside the tools (what the tools print):
1. Export without the stick, three lines: `Tools stick absent: records copied to /run/ares-records with SHA256
   readback`; `This copy is on this laptop, not off it; uid 1001 can read it, and a restart deletes it`; `For a copy
   off the laptop plug in the tools stick and run export again`. If his account cannot be let in: `This copy is on
   this laptop, not off it; only root can read it, since uid 1001 could not be let in (<reason>), and a restart deletes
   it`.
2. Export to a stick with older tools: `The stick holds tools this laptop installed before (SHA256 …), not the installed
   ones`.
3. First installation tried without the stick: `The first installation runs only from the tools USB at the recovery
   console; nothing changed`.
4. A stick-begun update finished without the stick: `Interrupted tools update began from the tools USB; finish it from
   that stick at the recovery console`.
5. An unfinished layout trial: in the same start `Layout trial is unfinished; prove it or revert first; if the console
   that began it is closed, from a fresh physical administrator login run sudo /var/lib/ares/at layout abandon`; after a
   restart `Layout trial is unfinished and began before the last restart: from a fresh physical administrator login run
   sudo /var/lib/ares/at layout abandon, then run this command again`.

Outside the tools (the window and Claude's lines):
6. The window's two labels: `AresOS owner tools dcbc375f: install these tools, then check and title` and `AresOS owner
   tools dcbc375f: export the records`.
7. The new STOP lines: `STOP after install: check or title refused`, and Claude's folder line's `STOP tools folder: …`
   (`give the full commit hash`, `<commit> is not on origin/main`, `this checkout differs from <commit> in
   os/owner-tools`, `<commit> holds other tools than dcbc375f`, `refused, nothing was installed`).

In the guides:
8. The routine box in `INSTALL.md` and the card **A routine tools command stopped** in `EMERGENCY.md`, including: after
   10 minutes without an answer Claude closes the window and nothing runs; after a STOP Claude copies every STOP line
   word for word and runs the export only on his go; his phone bookmark of `OWNER-TOOLS.md` on `main`, never a link
   Claude sends then; the console's "Keep the current administrator session open" does not apply on this route; after
   a routine install the stick holds older tools until Claude writes it again ("for now from Windows", not a package
   name); Claude updates its copy only by a fast-forward pull, and no other Claude session runs an owner command
   meanwhile; only the install and export lines run this way for now.
9. The sentence about a stopped update: "If the update STOPs with **was stopped safely**, nothing changed and every
   command works: run update again later, or get Help."
10. After every install from Claude's terminal (not only after a change of what starts next), Claude posts the title's
    lines (which system runs and starts next, the boot menu's rows, no serials) to the board, since he no longer sees
    the title himself.

## PLAN-GAP

None open. The brief's walk ran as written, with the integrator's recorded changes (decision 10 replaced by R1, the
stand-in origin, release 27's facts from its own commit, the dispatch caps).

## Open questions (for the integrator)

- `test_checkout_sources` still checks 22c's receipt as the current one (see the record step's "Not done").
- After merge, any bound tool, release script or guide change (`os/owner-tools/`, `os/release/`, `docs/`) fails
  `test_checkout_sources` while 22c's or 22d's row says **VM REHEARSAL PASSED; NOT ON THE LAPTOP**; a harness, workflow
  or test file may wait. Before release 28's work changes `docs/` and `os/owner-tools/`, both rows move on (22c's too:
  version 4 carries its ways back), or a new rehearsal records its own row (step 7b's "What happens after merge"; its
  first sentence there still names harness files, from before the integrator's decision).
- The test refuses a waiting tool, release script or guide (`os/owner-tools/`, `os/release/`, `docs/`: what the laptop
  gets) while a row says rehearsed, as review 8 proposed (the integrator's decision after step 7b; the builder's first
  version also refused harness files, which would have stopped release 28's harness steps).

Open items for later (from the final review, REVIEW-5; none blocks the laptop session):
- **N1, the next version of the lines** (`os/owner-tools/bootstrap.py:44`, `:150-157`): `FROM_COMMIT` runs `git` by
  PATH and neither line clears `GIT_*` or passes `--no-replace-objects`, so a `GIT_DIR` in the caller's environment or
  a replace ref could make `git show <commit>:…commands.json` return another file. Each needs a program already writing
  as him; the laptop has neither today ("Try this" step 2 checks). Fix: `/usr/bin/git --no-replace-objects` and
  `unset "${!GIT_@}"`. Not now: the change is under `os/owner-tools/`, which may not wait while the row says rehearsed.
- **N2, the next image** (beside `SUDO_ASKPASS`, F18): nothing in `os/config` or the image checks pins sudo's
  `env_reset` (on by sudo's default). The line leans on it little.
- **N6, the next guide change** (`docs/INSTALL.md:276`, the routine box): it names neither a wrong password nor a power
  cut. The guides are pinned while 22d's row says rehearsed; until then "Try this" step 8 carries both.

## Try this (the laptop session, after merge)

Claude runs every line below in its own terminal as `ares` (its Bash tool, not through a second shell, a
here-document or `eval`). Shell variables do not survive between the Bash tool's calls, so each code block is one
call. `<commit>` stands for the announced commit's full 40-character hash. Nothing in steps 1 to 4 needs a password or
changes the system.

**Before the session (the integrator)**

1. Merge PR #66 into `main`. Before the board note, on the merge commit `<commit>` that is on `origin/main`:
   - a checks-only run is green with the full model (run 43755153393 tested `7ef03022`, before step 8's merge);
   - `git rev-parse <commit>:os/owner-tools` prints `73fb5929cddd36db91662bad7d83e5453b965ca6` (the tree run 4
     walked);
   - `git rev-parse <commit>:docs/INSTALL.md <commit>:docs/EMERGENCY.md <commit>:docs/OWNER-TOOLS.md` prints
     `115e4974255f093e0e7947eb68e47ebaa65020d2`, `7e68584fca121f2d5a9b0a88a35b9f2844c0f780` and
     `53c075c804ab0c2449ac5f11fd2d786e0e900cff`.

   Then post on the board: `<commit>` in full and the fingerprint
   `dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be`.

**Prechecks (Claude, read-only)**

2. Tell every other running session: from step 4 until the last PASS line, run no `rpm-ostree`, `bootc` or `ostree`
   command (also no read-only one) and no `os/tests` owner module; the tools STOP on any such client of any user.
   Then each of these must hold; if one does not, stop and tell him (nothing has run):
   - `pgrep -u ares -x labwc` and `pgrep -u ares -x foot` each print a PID. If `foot` prints none, he opens an AresOS
     terminal window first, and keeps it open until the three PASS lines. Without it he gets `PASS install`, then a
     STOP from `check` and `STOP after install: check or title refused`: the tools are installed and nothing is lost,
     but his session ends on the STOP card.
   - `pgrep -a -x 'rpm-ostree|bootc|ostree'` prints nothing (`rpm-ostreed`, the daemon, does not count).
   - `lsblk -o NAME,SIZE,MOUNTPOINTS`: every mount point is on the AresOS SSD (the disk that holds `/boot/efi`); no
     partition of the Windows SSD has one. Otherwise the tools STOP with **Protected disk is mounted** (a file manager
     on the desktop can mount it; the console never does).
   - `env | grep '^GIT_'` prints only `GIT_EDITOR=…`; `git -C /var/home/ares/AresOS for-each-ref refs/replace` and
     `git -C /var/home/ares/AresOS config --get-regexp '^url\.'` print nothing; `git -C /var/home/ares/AresOS remote
     get-url origin` prints `https://github.com/Ares-Empire/AresOS.git`.
3. `git -C /var/home/ares/AresOS pull --ff-only`. Then `git -C /var/home/ares/AresOS merge-base --is-ancestor <commit>
   HEAD` must succeed (exit 0).

**The folder line (Claude, as `ares`; no window)**

4. One call:

   ```bash
   c=<commit>
   line=$(/usr/bin/git -C /var/home/ares/AresOS show "$c":os/owner-tools/commands.json | /usr/bin/python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)[sys.argv[1]])' tools-folder)
   if [ "$(printf %s "$line" | sha256sum)" = "c1b579be56abe84e24c3be1be6a93edc7ccb39cee607988b493cfe55bc4bdd82  -" ]
   then /usr/bin/bash -c "$line $c" < /dev/null
   else echo "NOT RUN: the folder line differs from the one run 4 ran"; exit 1
   fi
   ```

   Expect `SHA256SUMS: OK` as its last line, and no window. A `STOP tools folder: …` line ends the session there:
   nothing was installed, no window opens and no export follows. `NOT RUN` means the commit holds another line than
   the rehearsed one: stop and tell the integrator.

**His go**

5. Claude prints the routine line's SHA-256 (one call):

   ```bash
   c=<commit>
   line=$(/usr/bin/git -C /var/home/ares/AresOS show "$c":os/owner-tools/commands.json | /usr/bin/python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)[sys.argv[1]])' tools-routine)
   printf %s "$line" | sha256sum
   ```

   It must print `0b11cfc562841f58393bdb11f7962556418f851241885ce21d11594a4e13c079  -`: the line run 4's caller ran
   (`line_sha256` in `tl-install-caller-result.json`). Otherwise stop and tell the integrator. Then Claude tells him:
   tools version 4, `dcbc375f`, a password window comes next; and waits for his go.
6. On his go, one **background** call, and Claude notes the time it started:

   ```bash
   c=<commit>
   line=$(/usr/bin/git -C /var/home/ares/AresOS show "$c":os/owner-tools/commands.json | /usr/bin/python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)[sys.argv[1]])' tools-routine)
   if [ "$(printf %s "$line" | sha256sum)" = "0b11cfc562841f58393bdb11f7962556418f851241885ce21d11594a4e13c079  -" ]
   then exec /usr/bin/bash -c "$line" < /dev/null
   else echo "NOT RUN: the routine line differs from the one run 4 ran"; exit 1
   fi
   ```

   The line is one argument to `/usr/bin/bash -c`, exactly as the VM's caller ran it (`os/ci/tools_local.py`,
   `CALLER`). If Claude Code asks its own permission for this command first, that is Claude's prompt, not the window.
7. He sees a small window titled **Enter SSH Credentials**, inside **AresOS owner tools dcbc375f: install these tools,
   then check and title**, a Password field, OK and Cancel. On his phone, from his own bookmark, he opens
   `github.com/Ares-Empire/AresOS/blob/main/docs/OWNER-TOOLS.md`, checks it says `main`, and compares line 1
   (`Owner tools version 4: dcbc375f`) with the 8 characters in the window. Same: he types his password and presses OK.
   Different, or anything odd: Cancel (nothing runs).

**While the window is open**

8. What he may see, and what Claude does:
   - **No answer within 10 minutes** of step 6: Claude runs `pgrep -a -u ares -x ksshaskpass`. It lists the helper with
     the label as its argument (`AresOS owner tools dcbc375f: install these tools, then check and title`). If exactly
     that one process is still there, `kill <its PID>`, that one PID and nothing else (never `pkill`, never sudo or
     bash). sudo then ends with `sudo: no password was provided`, exit 1: nothing ran; Claude asks him again. If it
     lists none, he has answered: wait for the result. If it lists more than one, or one with another argument, kill
     nothing and tell him.
   - **No window to be seen** (behind the hub or a full-screen game): he says so, and Claude closes it as above; nothing
     runs.
   - **Cancel:** the window closes; `sudo: no password was provided`, exit 1; nothing changed.
   - **A wrong password:** `Sorry, try again.` and the window comes back with the same label, up to three times. After
     the third, sudo gives up and nothing ran.
   - **A power cut or restart during the install:** after the start the tools work (the old ones before the switch, the
     new ones after). On his go Claude runs step 4 and then step 6 again, and the install resumes; run 4 did exactly
     this (cut, then install).
   - **Any STOP** (Cancel is not one): Claude copies every STOP line to him word for word, asks for his go, and only
     then runs the export (step 10); it tries nothing else.

**The result**

9. What he should see (Claude reads it to him): `PASS install` with `Tools updated from version 2 to 4` and
   `manifest SHA256 dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be`, then `PASS check`, then
   `PASS title` with these lines (run 4 printed the same; the 12 characters are release 27's, release 13's and the
   pinned stock's image digests):
   - `newer AresOS 5fad242fceac runs and starts next`
   - `Boot menu at the next start: (ostree:0) newer AresOS 5fad242fceac, starts next; (ostree:1) older AresOS
     9b19b7942bc1; (ostree:2) plain Bazzite ed93d2158a1b`
   - `pin yes; transaction idle` and `staged False; rollback queued False`
   - `Previous title INVALID; use this record until the next reorder`

   Claude posts the title's lines (which system runs and starts next, the boot menu's rows, no serials) to the board
   under topic `aresos`. Optional, the integrator's call: `/usr/bin/sudo -n true` must then be refused (no ticket
   kept), as the VM's last step.
10. Optional, or after a STOP on his go: the export, the same way as steps 5 to 8 with entry `export-routine`, hash
    `7e1ffa764c263ef78025cee21c9d7ef2b6959e370765da40ae55046dc45a23d4` and the label **AresOS owner tools dcbc375f:
    export the records**. Expect `Tools stick absent: records copied to /run/ares-records with SHA256 readback`, then
    `This copy is on this laptop, not off it; uid 1001 can read it, and a restart deletes it`.
