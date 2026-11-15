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
