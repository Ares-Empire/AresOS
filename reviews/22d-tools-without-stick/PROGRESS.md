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

### Left, in order

Step 2 (Opus): `bootstrap.py` lines and labels, `commands.json`, the pins, `docs/OWNER-TOOLS.md`, the guides,
`test_owner_equality`. Then steps 3 to 7 as in the brief.
