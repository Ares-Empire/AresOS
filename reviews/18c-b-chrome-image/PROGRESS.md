# 18c-b progress

Brief: `briefs/18c-b-chrome-image.md` (draft PR #73, branch `briefs/18c-b-chrome-image`; not on `main` yet).
Branch `pkg/18c-b-chrome`, one builder at a time. Each step is a fresh agent; this file is the handoff.

## Where it stands

**Step 1a is built** (2026-11-15, Claude Fable 5.2, as the brief recommends for the signing key and the packer).
Next: step 1b (`record_build.py`), then step 2 (the install proof in the container).

## Done

**1a. Packer, templates, pins** (item 1; `control/` only, nothing under `os/` or `docs/design/`)

- `control/chrome/packaging/pack.py`: `python3 pack.py EXTENSION_FOLDER OUTPUT_FOLDER` writes `extension.crx`,
  `update.xml`, `policy.json`, `native-host.json` (each 0644) and prints the public record as one JSON line
  (`id`, `version`, `public_key_sha256`, `crx_sha256`, `payload`). As a module: `pack.pack(folder)` returns
  `(files, record)`, `pack.write(folder, output)` returns the record; `pack.payload(folder)`,
  `pack.version(folder)` and `pack.render(id, version)` need only the standard library (for `check-image.sh`).
- Templates: `policy.json` is `ExtensionSettings` alone with the four keys; `update.xml` has the placeholder
  `EXTENSION_VERSION`; `native-host.json` is unchanged (it already had one origin and the fixed launcher).
- `control/chrome/ci/install/test_pack.py` (10 tests) and `pack-crosscheck.test.mjs` (the node cross-check).
- `control/chrome_tests/test_extension_stores_nothing.py`: the storage pin.
- `exclusions.py`: `SETTING` is `/var/lib/aresos-control/chrome-excluded-sites.json`, and the refusal has the
  brief's exact text. `prepare.mjs` lines 32 to 34 and `test_exclusions.py` line 13 follow the path. Nothing
  else in the service changed.
- `control/chrome/packaging/aresos-control-chrome.tmpfiles`: the two agreed lines with a comment.
- `control/chrome_tests/test_excluded_sites_placeholder.py`: the tmpfiles lines, the placeholder refused, the
  empty list accepted, the unit unable to write the folder, and the sweep over the 31 Chrome tools.
- `control/chrome/packaging/README.md`: the paragraphs item 1 names.

`python3 control/chrome/build.py` prints `2acd63cbc4ae0ec273e82f700a4a8afdfa7288f191706a848c9091b64636c6ec` at
`0fc242e7` (the brief expected it to change: `packaging/` and `exclusions.py` are hashed).

## Left, in order

1. **1b** `record_build.py`, its tests under `control/chrome/ci/records/`, the records workflow, the one recorded
   run. The README already names the tool.
2. **2** the install proof in the container. First thing: run `test_pack.py` and `pack-crosscheck.test.mjs` there.
   They have run nowhere on GitHub yet, and the node test has never run at all.
3. **3a, 3b, 4 (4b), 5, 6** as the brief's "Steps" lists them. 3a waits for PR #58 on `main`, the lead's go and
   the owner's answer to question 5.

## What the code doesn't show

- **Signing uses Python's `cryptography`**, imported inside `_sign_with_fresh_key` only. The container of
  `control/chrome/ci/Dockerfile` (Debian bookworm) has `python3` without it: step 2's workflow installs the
  distribution package `python3-cryptography` (no pip). The calls used exist since `cryptography` 3.1.
- **Run `pack.py` without `-S`**: `-S` hides site-packages and with it `cryptography`. 18c's `os/build.sh` runs
  `build.py` with `-I -B`, which is fine for `pack.py` too.
- **`pack.py` never overwrites.** It refuses an output folder that already holds one of the four files. Bundles
  A, B and C each go into a folder of their own and are copied from there.
- **The image check needs a reader of its own** for `extension.crx` (the installed tree has no `pack.py`, and a
  packer shouldn't be checked with itself). `test_pack.py` has one (`fields`, `read_crx`) and the key-scan forms
  (`forms`: raw, hex, base64 and base64url at three alignments) for whoever writes the modulus scan in step 3a.
- **`os/tests` in step 3a** ("no installed file contains `EXTENSION_ID`, `UPDATE_URL` or `CRX_URL`") should also
  name `EXTENSION_VERSION`. `pack.render` already refuses to return a file with any of the four left in it.
- **How the key test works:** it wraps `rsa.generate_private_key` to see the keys the packer makes, then looks
  for p, q, d and the CRT numbers in everything returned, written or left behind. No key is a fixture anywhere.
- **The sweep's prepared operations** are written through the engine's own `reserve`, with the adapter's
  `prepare` replaced (it reads the page, which the gate never allows). The record has the engine's shape that way.
- In today's code the swept tools make **no** bridge call at all; the test allows `ack_steps` and `queued_steps`
  as the brief says and fails on any other, `configure` included.

## Local tests (laptop, 2026-11-15, Python 3.14.8, `cryptography` 50.0.0)

- `python3 -m unittest discover -s control/chrome/ci/install -p 'test_*.py'`: `Ran 10 tests`, `OK`.
- `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_extension_stores_nothing
  test_excluded_sites_placeholder test_exclusions test_build test_unit`: `Ran 16 tests`, `OK`.
- `… -m unittest test_owner_confirm.Policy` (it reads the README): `Ran 7 tests`, `OK`.
- `test_excluded_sites_placeholder` on the code before the change: `FAILED (failures=29)`, as required.
- A packer changed to leave its key as a file in the temporary folder fails
  `test_no_private_key_in_what_is_returned_written_or_left_behind` (tried once, not committed).
- **Not run:** `pack-crosscheck.test.mjs` and every other `*.mjs` (no node on the laptop); the container; the
  full Chrome and Control suites (GitHub runs them). `test_committed`, `test_fault_surface`, `test_sites` and
  `control/tests`' `test_policy_sources`, `test_slim_policy`, `test_unit` were started locally and had not
  finished when this was written: take their result from the GitHub runs below.

## CI runs

See the end of this file.

## JUDGMENT-CALL

1. **`cryptography` in the process, not OpenSSL through pipes.** The key lives only in the crypto library's
   memory, is never serialized and is freed after one signature. The pipe route would carry the key's PEM
   through a pipe and into Python bytes that can't be wiped. Cost: the container needs a distribution package
   (above). Changing it later touches one function and changes the build hash.
2. **The policy form** is `ExtensionSettings` alone, as the brief and the lead's answer 7 say. Whether the
   pinned Chrome installs from it is step 2's first case; the fallback in the brief stays open until then.
3. **The placeholder gate and its message** are the brief's, word for word.
4. **The named tools are called too.** The brief only names them. The test also requires each to answer `ok`
   and to reach no page, and requires the two tables to cover the tool list and `chrome_sites`' commands
   exactly, so the list can't go stale in either direction. Stricter than asked; easy to loosen.
5. **The storage pin is a little wider** than the four names: it also catches `navigator.storage`,
   `chrome['storage']` and a `storage` permission in the manifest.
6. **`pack.py`'s refusals beyond the brief:** an output folder that already holds a bundle file; a manifest
   version that isn't one to four numbers (it goes into `update.xml` as it stands); a file name that isn't
   UTF-8. The command also sets the core-file limit to zero, so a crash can't write the key to disk.
7. **The zip** is deflated as `install.mjs`'s is (what CI's Chrome has unpacked since package 17), with the
   time fixed at 1980-01-01 and mode 0644.

## PLAN-GAP

- **Branch name.** The brief's "Rules" say `pkg/18c-b-chrome-image`; the lead's handoff gave
  `pkg/18c-b-chrome`, which is what exists.
- **No runner for `control/chrome/ci/install/` until step 2.** The brief places the tests there so no existing
  suite picks them up, so on GitHub they first run in step 2's workflow.
- **The README names `record_build.py`** one step before it exists (item 1 asks for the sentence now).
- **Other texts still name the old `/etc` path:** `docs/control/TOOLS-HANDOFF.md`, `STATE.md`,
  `briefs/18c-image-test.md`, `reviews/20-chrome/` (history). All outside this package's paths; the lead's.
- **CI's list in the container** now goes to `/var/lib/aresos-control/`, which `prepare.mjs` makes as root
  (0755 by default). `Boundary.read` needs that; only the `control-chrome.yml` run shows it.

## The brief against the code

Nothing in item 1 turned out wrong. Checked: `exclusions.py` lines 8 and 23, `prepare.mjs` lines 32 to 34,
`test_exclusions.py` line 13 and `background.js` lines 869 to 875 are where the brief says; the extension uses
no browser storage; `python-shard.py` picks up every `control/chrome_tests/test_*.py`, so the two new test
files run in `control-chrome.yml` without a workflow change.
