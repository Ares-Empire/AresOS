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
| `test_owner_step_limits`, `test_checkout_sources` | see C below |

### Expected red until a later step

- `test_ways_back_probe` (22c's frozen receipt names version 3; step 6) and `os/ci/owner_vm.py`'s `(2, 3)`.
- `test_owner_update` was not run here, by the rule.

### JUDGMENT-CALL (for the owner, at the "try this" stage)

- The words of the two labels (`install these tools, then check and title`; `export the records`), the routine box,
  the routine STOP card and the new STOP lines (`STOP after install: check or title refused`, the `STOP tools folder`
  lines). Changing a label or a STOP line later costs a new generated line, its tests and the guide's quotes, but no
  tools version (they are outside the payload).
- The board note is posted after the tools-only box too, not only after a change of what starts next (decision 8):
  on the routine route he no longer sees the title himself, and the failed-update card works from his last title.

### Left, in order

Steps 3 to 7 as in the brief: review of steps 1 and 2 (Fable), then review 8's findings 2 and 5, their review, the
harness mode `tools-local` with the rehearsal, the record step.
