# 331 Release 29 progress

## Done · step 1 · 2026-11-21

Added the R29 profile, exact RPM delta, file and unit reasons, and main-source stop in
`os/ci/release_diff.py`. The gate checks the R28 record's source trees and the checked-out
build inputs against the branch's merge base with main. R29 adds `os/labwc/` to the source
list and permits the reviewed jar-pin-only change on the release branch. The historical R27
and R28 profiles keep their own rules.

| Current main change | Image and evidence |
| --- | --- |
| B323 · `6fe289e4` | The x86_64 package lock adds `gtk4-layer-shell-1.3.0-1.fc44.x86_64`. The diff checks the RPM's non-ghost payload against its file records and requires clean RPM verification. The shared library and its GObject typelib are used by the indicator and laptop home. The JetBrains Mono font and licence ship under `/usr/share/fonts/aresos`. Both fontconfig cache formats are rebuilt. The image checks exercise the typelib with its preload and check font selection. The Mesa EGL and Intel Vulkan checks cover existing graphics RPM files and their libraries. |
| 311 and B323 · `67e1e60c`, `6fe289e4` | The package layer installs Fedora's `labwc-0.9.6-1.fc44.x86_64`, then replaces it in the same layer with `labwc-0.9.6-1.fc44.aresos1.x86_64`. The download lock still pins Fedora's RPM as input. The final `packages.txt` records the rebuilt NEVRA, and `labwc.lock.json` records the build inputs. Keeping the swap in one layer preserves the replacement binary when size, mode and mtime coincide. Step 1 stopped pending the payload comparison, which step 2 now provides. |
| B320 · `06883a3d` | Six labwc key rows route brightness up and down, volume up and down, speaker mute and microphone mute through executable `aresos-level`. Volume up also unmutes. Brightness down stops at 1% of the backlight's maximum. Executable `aresos-indicator` and `aresos-settings` use the look JSON and 17 sprites. Jersey 10 and its licence ship with the font cache refresh. |
| 25 and PR136 · `61a66d78`, `5e8f90f9` | The supervisor, Java wrapper, cover and shell coordinate planned-stop saves. The desktop message window adds `restart`. The borderless `aresos.black` window stays on top during a save. The guardian unit, login-scope ordering drop-in and exact graphical-target enable link each have a reason. The guardian asks the game to save and waits within a deadline. The offline updater audit gains the guardian's exact enabled row and commands. Its unit-specific drop-in scan leaves existing rows intact. PR136 adds half a second of slack to the hosted lid timestamp check. The cut still needs both guardian VM receipts. |
| 56, 53c, 53d, 53f and PR134 · `da441546`, `e01cd6a1`, `c576818b`, `3048b221`, `182005e6` | The rebuilt mod jar includes the mouse and hotbar changes, faster flight and world-search support. The installed desktop lock and mod record bind the jar's pin and build revision. The shell helper handles focus and desktop views, invalidates stale home cursors and caps view launch checks. The image carries the native GTK 4 and Cairo laptop-home executable. Laptop-home and Super search launch wiring awaits 23c. B316's portal source is present on main and its image integration belongs to B321. |
| T475, Chrome and Control | T475 records the laptop on R28 with R27 as rollback, corrected stock pinned, R13 retired and owner tools v5 `df89ac33…`. Chrome, Control Part A and its `aresos` CLI already ship in R28. The two images must match the validated Control install and vendor inventory, with only the source revision changing in `control.json`. The existing Control UID and GID are 250. The dispatcher from package 43 remains subject to its cut decision. |

The full bound source delta from the recorded R28 commit to this branch's main base covers
`mod/`, `os/Containerfile`, `os/build.sh`, 34 paths under `os/config/`, six paths under
`os/labwc/` and `os/packages.lock.json`. The named generated paths cover the RPM database,
dnf5 history and repository markers, ldconfig caches and the fontconfig rebuild. The
classifier also checks completeness for unchanged required links, typed Prism inventory,
the pinned Prism list, deterministic compiled schemas and the locked Java alternatives chains.

## Verified locally

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_release29.py` | `Ran 12 tests in 5.400s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release28.py` | `Ran 94 tests in 31.710s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release27.py` | `Ran 41 tests in 6.836s`, `OK` |
| `git diff --check` | Exit 0 with no output |

The R29 tests used fixture images and stand-ins for image commands. The fixture diff
classified every change except the labwc payload and wrote a stopped result. Regressions
cover missing files and RPM records, incorrect metadata, missing alternatives links and
groups, a missing unit audit, unmasking, source omissions and a changed merge resolution.

## Done · step 1 review fixes · 2026-11-22

REVIEW-1 (`1767cf17`) requested two fixes. R29 now compares canonical updater-audit JSON and
requires exact fields, types and row order. The fixture runs `os/tests/audit.py` against
disposable roots with stand-in unit listings. Near misses cover duplicate, extra and missing
fields, type changes, and reordered commands and rows.

The source guard now includes Git-ignored files under the local OS build inputs. The regression
plants an ignored `os/config/var/log/dnf5.log` in a fixture checkout and verifies that the diff
stops before mounting. An ignored log under `mod/` passes the source guard because the build
reads `mod/` from the committed source.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_release29.py` | `Ran 14 tests in 9.883s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release28.py` | `Ran 94 tests in 38.838s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release27.py` | `Ran 41 tests in 7.642s`, `OK` |

## Done · step 2 · 2026-11-22

Addressed both REVIEW-2 should-fixes. The source guard scans Git-ignored paths throughout the
`os/` context for `COPY .` and applies the root-relative exclusions in the checked-in
`os/.containerignore`. Its own stop message lists paths to move or remove before rebuilding.
The regression covers `os/.env`, an ignored config log and a nested `ci/` under `os/tests/`.
Ignored files in the excluded `os/ci/` and `os/manifest/ci/` directories and outside `os/` pass
this scan. The current ignore rules are literal paths. If a later cut adds globs or negation,
the guard conservatively reports all Git-ignored candidates until it can check those patterns.

### Labwc exception for lead review

- R28 must have exactly `labwc-0.9.6-1.fc44.x86_64`. R29 must have exactly the `result.nevra`
  validated by the cut's labwc stage, currently `labwc-0.9.6-1.fc44.aresos1.x86_64`. The complete
  download lock gains exactly `gtk4-layer-shell-1.3.0-1.fc44.x86_64` and keeps each existing
  RPM's pin. The effective installed delta adds that GTK RPM and the pinned rebuild and
  removes Fedora labwc. The shared removal check still requires the same RPM name and architecture.
- Both images must independently pass `rpm -V` for their exact labwc NEVRA. Each expected path
  needs one non-ghost RPM record and an installed entry matching that record. Fedora's exact
  64-path inventory is the 60 fixed paths plus two build-ID symlinks and their two prefix
  directories. The rebuilt RPM must carry those same fixed paths and its own two links.
  Each binary supplies one 20-byte GNU build ID. Its RPM link must use that ID in its name
  and target exactly `../../../../usr/bin/labwc` or `../../../../usr/bin/labnag` as appropriate.
  Each link must be absent from the opposite image. Prefix directories can be added or
  removed only for those links. Two distinct candidate links can share one prefix directory,
  in which case the candidate has 63 paths. A common directory must compare equal.
- The fixed payload must be byte-identical with the same metadata and RPM records except for
  `/usr/bin/labwc` and `/usr/bin/labnag`, which must remain root-owned 0755 regular files.
  The RPM checks reject extended attributes and file capabilities. Each rebuilt binary must
  match both of its SHA-256 pins from the cut lock. The normalizer uses the image's `objcopy`
  and removes exactly `.note.gnu.build-id`, `.gnu_debuglink` and `.gnu_debugdata` from its
  temporary copy. The loaded-image check hashes through the end of the last segment and
  zeroes only `e_shoff` and the GNU build-ID descriptor. The normalized check covers the
  retained sections and the loaded check covers mapped padding and program headers. Bytes
  omitted by both 311 algorithms remain outside those hashes.
- The cut binds the entire `os/labwc/` tree to main. The result records the Git blobs and modes
  of the lock, stage and loaded-image helper. The checker reads and compiles the committed
  sources and requires the installed lock to match the committed bytes. `result.json` records
  the two RPM verification results, both inventories, build IDs, raw executable SHA-256 values
  and the measured pins. B321 can use the same comparison with its reviewed stage, lock pins
  and evidence for its final `aresos2` cut.

The positive fixture reaches `IMAGE_DIFF_PASSED`. Near misses cover missing payload on both
sides, ghost and digest records, changed documentation even with matching RPM metadata,
unexpected xattrs, stale or misdirected links, each incorrect hash pin and loaded padding
that leaves the normalized hash unchanged. Other stops cover a changed download hash, the
wrong replacement release, name or architecture, and absent or changed build sources.

### Verified locally · step 2

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_release29.py` after the source guard | `Ran 14 tests in 9.426s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release29.py` with the labwc comparison | `Ran 25 tests in 27.218s`, `OK`. Passing fixtures printed `IMAGE_DIFF_PASSED` for 60, 60, 57 and 62 changes. |
| `python3 -m unittest discover -s os/tests -p test_release28.py` | `Ran 94 tests in 36.779s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release27.py` | `Ran 41 tests in 6.905s`, `OK` |
| `git diff --check` | Exit 0 with no output |

The Fedora mirror copy matched R28's locked RPM SHA-256
`9438b595a52653540f6d95c83453284c0d99b3f9f6c4df13320b21253916f60b`. A read-only
`rpm -qp --nosignature --qf` query using the classifier's file format returned `64 exact
non-ghost RPM records` in the comparison. `rpm2cpio` and `cpio -idm --quiet
--no-absolute-filenames` extracted only the two executables under `.work/`. Their ELF notes
matched the Fedora links ending in `6e/61cec6435d39a5126a1ec7b1bd109152327f8b` for labwc
and `ec/bdf3ff0423bb879b79912f84b3e5f06f8786fd` for labnag. The download and extracts were
removed. [Fedora release RPM](https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/Packages/l/labwc-0.9.6-1.fc44.x86_64.rpm)

## Sources and runs

- Approved starting head `1b2b27c790bcd402926dff3a659ee071f3ad5dfa`. Main base
  `a9863055b2987127cd1cd684182deed9ece24ce0`. Step 1 code and test head
  `b17b4daca5eca6f7f0a82f4c2e9047fd7070fb66`.
- Source-guard fix `2b7d25e1`. Step 2 code and test head `4632153bec7bb69af0ad342703ba840a48a9c3d4`.
  The labwc path inventory and normalization contract come from package 311 at
  `67e1e60c746aea6159daeab8a3256fbf582dd5ff` and the Fedora RPM pinned in R28.
- R28 from `os/manifest/releases/28.json`, source
  `7d5fbbf2c7f7c5b4d41dd707a9407e6401a4d062`, signed digest
  `sha256:aa97b2d506a4b48e24869902d78adb7700482a068d9bb5dc371e886a76e5f15d`, base
  `sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`.
  [Recorded R28 publish run 44590446680](https://github.com/Ares-Empire/AresOS/actions/runs/44590446680)
- R29 hosted run and run SHA pending. Ledger use is zero dispatches and zero uploads.
  R29's effective `dispatch_caps.publish-29` and `publish_cap` are both zero.
  The hosted ledger wiring belongs to step 5.

## Left in order

1. Review pre-cut step 6b on the draft PR head.
2. Settle B321 under the four cut conditions in the brief, take the named main
   cut and classify any remaining image differences. Apply the brief's decision
   on package 43 at the cut.
3. Resolve the cut, verify the reproducible jar and refresh its pin. Run the
   hosted checks and dry run, and repeat the historical baseline preflight
   using the final bound inputs before private upload.
4. After lead approval, publish privately and record the signed release.
   Prepare the candidate tools and guides, qualify the signed digest in the
   rehearsal and complete the final review and pin.
5. In R30, address REVIEW-13 finding 2 by requiring full branch refs in the
   historical R13, R27 and R28 job conditions and excluding `release_27`
   from R13 selection. Today `os/ci/publish.sh` refuses same-named tags
   before registry operations.

## Limits

The release comparison has run with fixtures and the Fedora path list has been checked
against the pinned RPM. Hosted verification of the complete comparison, including its
normalization command on the final R29 image, remains open. The release jar pin, guardian VM
save and timeout receipts, and R29 rehearsal also remain open. The pointer-lock hardware
check follows the owner's update. There are no downloads over 500 MB in `.work/`.

## Paused 2026-11-21 evening (the lead)

- **Why:** mac-capacity asked all leads to slow Codex down until Monday. R29's cut waits for Deskflow (c) anyway, about 28 Nov.
- **Step 2:** stopped partway, with nothing committed. The partial diff is kept outside the repo at `~/AresOS-331-step2-partial.patch` (764 lines); a fresh step 2 turn may read it or start over.
- **Late-package notes (2026-11-21):**
  - B329 (PR143): the lead's os/ read is clean. Its image-difference list is in its PROGRESS.md under "For linux-aresos". R29's guest walk expects the AresOS theme.
  - For R29's Known limits: after Alt+Tab then Escape, the world keeps its pointer lock but gets no keys until you switch away and back. Main's rc.xml does the same; the frame isn't the cause (linux-desktop).

## Step 2 reviewed 2026-11-22 (the lead)

- **REVIEW-3** (fresh Codex `gpt-6.2-sol` high, at `144fd9ae`): SAFE. It ran on Sol rather than the brief's Astra, under mac-capacity's Codex pace rule.
- **Carried into the next slices:**
  1. Extend the build-context guard to non-ignored untracked files and tracked edits outside `IMAGE_SOURCES_29` that `COPY .` would bring in. The image diff would still catch any resulting image change; this closes the gap earlier. Do it in the next slice that touches the guard.
  2. Give labwc and labnag distinct fixture payloads, add a swap regression, and add direct regressions for an extra RPM path, a duplicate record and a valid but stale installed lock. Do it with step 3 or 4 as a small first item.
  3. Refresh the `aresos2` fixture bindings at the cut, in B321's late-package slice.
- **Next:** step 3, the walk, on Codex when the pace allows (Monday).
- **Merged on main since step 1's baseline (2026-11-21/22):**
  - 18c-b (PR76, `d37ea134`): its release handoff is in `reviews/18c-b-chrome-image/PROGRESS.md`, "For linux-aresos's release brief". Keep C6's first-use half on R29's first boot, before the synthetic list. The CI overlay now sets a static hostname (`e9379346`) to stop Chrome's lock flake.
  - B329, the frame (PR143, `b720da42`).
  - B330, the Prism handler (PR140, `a7fb7cfe`).
  - 327 and 328a, mod/ only (`4dd5288b`, `92cf365a`): the jar pin renews at the cut.
  - The late-package slice merges main and classifies these.

## Done · step 3 historical baseline · 2026-11-22

- `release29_walk.py` and the `owner_vm.py` route for `release-29` reuse the offline
  stock install and correction, the R13 switch with tools v1, the R27 update with tools v2,
  and the tools-local folder and password-window legs for v4 and v5. The R28 helper stages
  the exact signed R28 image and confirms its first boot through `check` and `title`. The
  final snapshot requires R28 running, the same R27 deployment retained, the corrected
  stock deployment pinned and R13 removed. Both bootc slots and the deployment identities
  must agree. The guest reads every installed v5 payload file and checks that the tools
  journal is settled and the deployment transaction and outcome journal are idle. Both
  protected-disk and firmware paths run their existing audits.
- The route checks immutable record hashes for R13, R27 and R28 and the recorded image
  source objects. R13's image inputs match its reviewed squash. The R27 and R28 image inputs
  match their recorded source tree rows. The tools trees, both release-record copies and
  fingerprints come from v1 `17fe261c`, v2 `41b06513`, v4 `634e1237` and v5
  `6ae4da41`. The reconstructed v5 stand-in must equal the published tools tree and
  release blob and match the guide's two fingerprint lines. Its full fingerprint is
  `df89ac336e13db84934505551ba28163cbd60fa5b3b9fb0ec97b9585945896c6`.
- `registry_auth.py baseline <cosign>` checks the exact package 331 branch ref and mode
  and uses the job token to inspect the three private digests. It verifies each record's
  exact Cosign identity and issuer, records the signature hashes and removes the temporary
  auth before the guest starts. `owner_vm.py` checks the same-run registry proof and
  pinned ISO download before starting the route. The offline installer checks the served
  Web UI bundle and source map before installation. The passing baseline receipt records
  those hashes, the confirmed deployment shape and the baseline input hashes. Run
  `release29_walk.py check-receipt <receipt>` against the current checkout. A changed
  baseline input requires a fresh preflight. The active release pointer and candidate
  payload can advance independently of these historical pins.
- Refreshed 12 pending source rows with zero removals. Package 42's receipt and source
  binding tables remain historical.

### Verified locally

These modules ran one at a time from the repo root, with `TMPDIR` inside the worktree.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_owner_walk.py` | `Ran 40 tests in 634.537s`, `OK`, and `PASS historical R29 baseline through confirmed R28 with tools v5` |
| `python3 -m unittest discover -s os/tests -p test_release29_rehearsal.py` | `Ran 7 tests in 0.834s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release28_rehearsal.py` | `Ran 44 tests in 35.970s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_rehearsal_auth.py` | `Ran 9 tests in 0.079s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_installer_webui.py` | `Ran 9 tests in 0.003s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_owner_media.py` | `Ran 6 tests in 0.203s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_checkout_sources.py` | `Ran 10 tests in 0.937s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_ci_api_permissions.py` | `Ran 4 tests in 3.396s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_tools_local_wiring.py` | `Ran 42 tests in 51.372s`, `OK`. The disposable Git fixture printed its default-branch and empty-remote-HEAD notices. |
| `git diff --check` and `git diff --cached --check` | Exit 0 with no output |

The first R28 regression run printed `Ran 44 tests in 35.862s` and `FAILED (failures=1)` because the shared
host-receipt lookup changed the historical branch decision trace. The package 331
lookup moved to its own route and the same module passed. The local failure cases
include wrong branch refs and signatures, changed installer bytes and stale receipts,
lost stock pin, retained R13, changed R27 identity, an active transaction or outcome,
and mismatched installed tools.

### Lead dispatch and receipt

After steps 4 and 5, run `checks_only=true` with the same-head full model, then dispatch
the read-only baseline on the reviewed branch head. The baseline job runs its own native
authorization and uses a job token with package read access. Fetch the recorded image sources and the historical
R13 probe source if the runner checkout lacks those Git objects. Run the registry check
and the existing exact ISO inspection before entering the disposable VM route. Save
`evidence/release-29-baseline.json` from the successful hosted run and retain its
registry, installer and two-disk evidence for review. The publish gate must obtain the
receipt from that successful run and validate the current inputs before private upload.
Record its run ID, attempt and commit. Keep both publish caps at zero during baseline
work.

### Limits

This slice started at `a48c7e91`. The baseline implementation and fixtures are at
`503282d9870c18922b994e7c9db9bce6469bf117`. Verification used local fixtures for the
registry, ISO and guest route. Real job-token access, Cosign, ISO availability, boot and disk audits still need
the hosted preflight. The checkout uses the R28-qualified ISO pin `bd043223…`. A changed
download or installer asset stops the preflight until the inputs are requalified. The
historical preflight ends at confirmed R28. See slice B below for the candidate route.
Hosted workflow and ledger changes remain for step 5. Ledger use is zero
dispatches and uploads, with both R29 publish caps at zero. There are no files over
500 MB in `.work/`.

## Done · step 3 slice A REVIEW-4 fixes · 2026-11-22

Started from review head `c364ea88a721ce9be88bef99ed5d0bf7c5662f0a`. The package 331
owner guest skips the legacy registry auth lookup after preflight removes its temporary
auth. The physical guest login supplies the read-only job token. The regression constructs
the real firmware marker guest with QEMU mocked and verifies that the guest starts without
an auth share. Refreshed the two affected pending source hashes.

The baseline receipt now hashes `os/ci/install-tools.sh`, `os/ci/toolchain.json` and
`os/ci/firmware_contract.py`. It will also hash `os/manifest/ci/331/host-walk.json` when
step 4 adds it. The hosted route and baseline hash check share that path. Adding the host
receipt or changing any of those inputs requires a fresh baseline preflight.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_release29_rehearsal.py` | `Ran 9 tests in 0.945s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_two_disk_vm.py` | `Ran 29 tests in 0.170s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_checkout_sources.py` | `Ran 10 tests in 1.203s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_rehearsal_auth.py` | `Ran 9 tests in 0.094s`, `OK` |
| `git diff --check` and `git diff --cached --check` | Exit 0 with no output |

The modules ran one at a time from the repo root with `TMPDIR` inside the worktree.
The step 4 host-walk receipt and hosted registry and VM proof remain pending. Ledger
use is zero dispatches and uploads, with both R29 publish caps at zero. There are no
files over 500 MB in `.work/`.

## Done · step 3 slice B · 2026-11-22

Started at `a813c78adbb1db122b09035d110fb4e52a630d9a`. The implementation and
fixtures are at `57206d9b6a460ff4a1706c310add74155461483c`.

- The `release-29` driver with `RELEASE29_PHASE=qualify` checks candidate equality before VM setup. The
  stand-in extends the pinned R28/v5 origin, and the generator produces both release
  and history copies, the bundle manifests, commands and the guide fingerprint. The
  cut must supply a committed R29 record and a matching tools tree, active release
  blob and owner-tools guide. Only a local preparation check of exact v5 bytes can
  defer comparison. The baseline-only route still writes the historical receipt.
- Starting on confirmed R28, the routine runs the folder and password-window lines
  from the stand-in commit. The model checks the guide and dialog fingerprint, the
  three PASS lines, the install receipt and the missing cached sudo ticket. The same
  bundle is a no-op, and a different bundle at the same version and the v5 downgrade
  both STOP. Each replay preserves the installed tools and journal.
- The console stages the exact digest, titles and exports with the stick absent,
  then reboots. The VM's audited one-time BootNext represents F12 → Bazzite. The
  staging and boot snapshots require exact identities, the pinned corrected stock,
  and agreement between the bootc slots and deployment rows. R27 alone retires.
  Update, previous to R28 and forward to R29 each require their own confirmation
  and fresh title. A refused update rechecks the original shape. If R28 boots after
  staging, the card allows one retry after the save gate only when the update is in
  place and the title proves that R28 was a non-default start. A not-applied result
  sends the route to Help and leaves the previous selection alone.
- The model checks the save gate immediately before the initial update restart,
  forward restart and failed-update recovery restart out of R28. It exercises the
  submitted status/close-message reader, home snapshot and Terminal launch scripts
  under the existing fixture interfaces. It compares the planted schema-4 apps and
  both synthetic save files through all boots with the existing Prism allowance and
  image targets required on both releases. Terminal opens before the successful
  check on each of the four boots. The first R29 check also proves the no-foot STOP.
- The route carries forward the stock rewind, exact ISO and served Web UI checks,
  offline stock boot and disk and firmware audits. A failed shutdown retains its
  redacted transcript, and the harness still audits if guest cleanup fails. A live
  login stall retains its transcript for the lead. Requalify a changed ISO or
  installer asset before rerunning.

### Verified locally · slice B

The tests ran one module at a time from the repo root with `TMPDIR` inside the worktree.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_owner_walk.py` | `Ran 40 tests in 615.645s`, `OK`, and `PASS historical R29 baseline through confirmed R28 with tools v5` |
| `python3 -m unittest discover -s os/tests -p test_release29_rehearsal.py` | `Ran 15 tests in 8.858s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_two_disk_vm.py` | `Ran 30 tests in 0.172s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_checkout_sources.py` | `Ran 10 tests in 0.999s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release28_rehearsal.py` | `Ran 44 tests in 34.292s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_tools_local_wiring.py` | `Ran 42 tests in 57.636s`, `OK`. The disposable Git fixture printed its default-branch and empty-remote-HEAD notices. |
| `git diff --check` and `git diff --cached --check` | Exit 0 with no output |

The first R29 run printed `Ran 15 tests in 2.874s` and `FAILED (errors=17)` because the
fixture unpacked three fields from the historical model's four-field factory. The
fixture now takes the factory's snapshot function. Two R28 runs each reported
`FAILED (failures=1)` in the job-gate scan. The first exposed the shared CLI argument
change, which moved to a package 331 environment selector. The second isolated a
pre-existing REVIEW-4 regression at `a813c78a`. The static scan could not see the
legacy registry check through the constructor's conditional expression. The explicit
package 331 branch preserves guest login without a legacy auth share and makes the
historical registry check visible to that scan again. Rebinding refreshed three existing hashes
in the 12 pending rows, with zero removals.

### Next and lead dispatches

1. Review this deployment walk. Step 4 builds the remaining session, home and game
   probes, the eleven Control checks and Chrome first-use and rollback checks. Bind
   the checker and settings in `os/manifest/ci/331/host-walk.json`. Carry the labwc
   fixture follow-ups from REVIEW-3 into that slice.
2. Step 5 adds authorization, budgets and receipt wiring for the separate read-only
   baseline and qualifying routes, with both publish caps closed. The lead dispatches
   same-head `checks_only=true` and the full model, then the read-only baseline. Retain
   its run ID, attempt and SHA and recheck the baseline receipt before private upload.
3. The lead settles the late-package cut and dispatches resolve and dry run on the
   reviewed cut. After permission and review the lead dispatches the one private
   publish, closes the caps and hands over the signed record. Step 10 prepares the
   real tools and guides. After same-head checks the lead dispatches the qualifying
   rehearsal, then reviews the receipts before the final pin.

### Limits

The local candidate uses a synthetic record and v5's executable bytes with an
explicit fixture version. Step 10 chooses the next free version and incorporates
package 43's reviewed tools and route if it rides. Local model evidence covers route
ordering, stop conditions and fixture persistence. The actual Alt+F4 close, message
and world save on R28 still require a manual check. Terminal with the world open and
the physical F12 menu also need live evidence. The signed R29 image, registry access,
hosted VM and physical disk proofs remain pending. Step 4 still owns the session probes,
end-of-walk game scope and Control checks. Both publish caps remain zero and ledger
use is zero dispatches and uploads. `.work/` contains no files over 500 MB.

## Done · step 3 REVIEW-5 fixes · 2026-11-22

Started at `696aa59f`.

- The R29 deployment receipt records the first unattended boot digest after the
  update restart and one-time Bazzite selection. Only a first boot into R29 can
  qualify. If R28 starts, the documented recovery still allows one retry after
  the save gate. Even if the retry reaches R29 and the rest of the walk completes,
  the receipt remains `not-qualifying` and the run stops with a failure. The model
  covers a successful recovery, a second R28 start and a clean first boot.
- The Windows marker attempts the offline protected-disk and firmware audit in
  nested cleanup after closing the guest. The fixture verifies that order after
  a shutdown timeout, a marker assertion failure and a close error.
- On both R28 and R29, the daily user exclusively creates a disposable file
  beside the planted `level.dat`, reads its bytes back and removes it. The
  model verifies the write on each normal boot and rejects read-only saves on
  either release. Package 331 opts in to the write probe.
- Refreshed the two affected pending source hashes. The historical baseline
  receipt binds the changed harness inputs, so a fresh preflight is required.

### Verified locally

The modules ran one at a time from the repo root with `TMPDIR` in `.work/`.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_release29_rehearsal.py` | `Ran 17 tests in 9.955s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_two_disk_vm.py` | `Ran 31 tests in 0.181s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release28_rehearsal.py` | `Ran 44 tests in 33.597s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_checkout_sources.py` | `Ran 10 tests in 1.200s`, `OK` |
| `git diff --check` and `git diff --cached --check` | Exit 0 with no output |

The lead's review of this fix round comes before step 4. Real VM boots, firmware
and disk comparisons, and the owner's live save and close are still pending.
Both R29 publish caps are zero, with zero dispatches and uploads used. There
are no files over 500 MB in `.work/`.

## Done · step 4 · 2026-11-22

Started at `028cc315` on draft PR144. Merged `origin/main` at
`d37ea134f036a770f5d60ab76d3c6f06ec7a0e3e` in `a5dbff3f`. Resolved the
pending-rebind conflict by keeping both sides' notes and recomputing the files
with `rebind.py pending`. After the probe changes it reported 14 pending rows
and zero removals. The active package 42 binding tables stay historical.

- **Carried item 2** · `cd393cfd`. The labwc and labnag fixtures now have
  distinct normalized and loaded-image payloads. The swap regression keeps
  each expected build ID and refreshes the RPM records so it reaches the
  per-executable hash check. Extra paths, duplicate records and a well-formed
  stale installed lock each have a direct refusal case. The step 1 and 2 fixture
  comparison uses the reviewed pre-merge head until the late rules are added.
- **Guest and Control probes** · `9d6455e1`. The four confirming boots check
  the running labwc theme, fontconfig, runtime privilege, polkit and the PATH
  read inside the reopened Terminal. R28 expects Ares-Crown and Space Grotesk.
  R29 expects B329's AresOS theme and also checks Jersey 10 and JetBrains Mono.
  The exact Terminal app starts from the supervisor's Wayland environment in
  the daily user's home on tty1. Each try records the PID and log. Only the
  missing-monitor message permits another try, with five attempts available.
  The first R29 confirmation still exercises the no-foot STOP. The home and
  save checks continue on all four boots. The last R29 boot measures the paused
  JVM in its game scope with `memory.high=2684354560`.
- The bound 18c-b stdin checker receives the five service checks on R28 and all
  eleven checks on R29. The harness saves its output before querying the login
  graph. The service account and private state use UID/GID 250. A masked
  non-root unit can appear as an ordering reference and is still traversed.
  Required masked units and any dependency on Control stop the walk.
- Starting R28 stages the synthetic format-1 list in a separate root-owned file
  under `/var/lib`, checks that the live path is absent and records an independent
  root `sha256sum` of the staged bytes. On the first R29 boot the C1 check requires
  the exact format-0 placeholder and root:aresos-tools 0640. C6 waits for the
  policy-installed native host in a disposable normal Chrome profile, observes
  settings refusal for tabs, read, open and take_tab, and checks zero requests
  against a loopback server with a positive counter check. Root then feeds the
  staged bytes to `tee`, and tabs succeeds. Both R29 boots compare the checker
  line `CONTROL_CHROME_SITES_SHA256` and the live metadata to the pre-update hash
  and package contract. After `previous`, R28 runs the five service checks and
  independently reads the live hash as root. Only synthetic values enter evidence.

### Handoff to the late-package profile slice

| Main merge | Exact deltas to classify at the cut |
| --- | --- |
| 18c-b · `d37ea134` | Inventory the new Control tree and locked vendor results against R28's install. Bind `chrome_build`, `chrome_extension`, `gh`, the expanded `links` and installed file records in `control.json`. Validate the signed per-build bundle `extension.crx`, `native-host.json`, `policy.json` and `update.xml` under `/usr/share/aresos/chrome/` with matching IDs. Cover the managed policy and native-host links under `/etc/opt/chrome/` and their image copies, `/usr/libexec/aresos-control/chrome/{host,native_host.py}` and the qualification and build records, the Chrome polkit action and tmpfiles rule. The live sites file is guest state. Bind `os/gh.lock.json` and `os/keys/github-cli-rpm.pub` to the source. Classify `/usr/bin/gh`, its licence and installed `gh.lock.json`. The signature-checked RPM has 240 paths and contributes only the binary outside the installed RPM set. Keep `-B` in the Python child calls and the help check as nobody. The check-build overlay's static hostname and its Control fixture pieces belong to the harness. [18c-b handoff](../18c-b-chrome-image/PROGRESS.md#for-linux-aresoss-release-brief) |
| B329 · `b720da42` | Add 37 AresOS labwc theme files, 36 look pack frame cells and the changed `look.json`. Compare the exact theme, switcher, Shift+Alt+Tab, title-bar scrolling and root press rows of `rc.xml`. Keep the Crown pin. The guest now expects AresOS on R29. If B321 rides, check the merged bindings together. [B329 handoff](../329-window-frame/PROGRESS.md#for-linux-aresos) |
| B330 · `a7fb7cfe` | Add the hidden `org.prismlauncher.PrismLauncher.desktop` entry and change `aresos-mimeapps.list` to register the callback. Keep existing cache generation. Live Microsoft sign-in is still open. [B330 report](../330-prism-handler/REPORT.md#expected-r29-image-changes) |
| 327 and 328a · `4dd5288b`, `92cf365a` | The mod tree now includes the home try-out and Terminal look changes plus the pointer capture work. Renew the jar pin from two clean hosted builds of the final source. |

### Verified locally

Ran these modules one at a time from the repository root, with `TMPDIR` in
`.work/`.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_release29.py` | `Ran 29 tests in 30.729s`, `OK`. The positive fixture diffs printed `IMAGE_DIFF_PASSED` for 60, 60, 57 and 62 paths. |
| `python3 -m unittest discover -s os/tests -p test_release28.py` | `Ran 94 tests in 58.132s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release27.py` | `Ran 41 tests in 6.646s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_two_disk_vm.py` | `Ran 31 tests in 0.173s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release28_rehearsal.py` | `Ran 44 tests in 34.708s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_checkout_sources.py` | `Ran 10 tests in 0.962s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_owner_walk.py` | `Ran 40 tests in 623.113s`, `OK`, and `PASS historical R29 baseline through confirmed R28 with tools v5` |
| `python3 -m unittest discover -s os/tests -p test_release29_rehearsal.py` | `Ran 22 tests in 26.362s`, `OK`, and the C1, C6 first-use and C6 reboot PASS markers |
| `python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/owner-tools/*.py reviews/331-release-29/walk-host.py` | Exit 0 with no output |
| `python3 reviews/331-release-29/walk-host.py` | `PASS package 331 synthetic baseline and candidate host walk with 314 sources` |
| `git diff --check` and `git diff --cached --check` | Exit 0 with no output |

The post-merge image fixture first reached the main-source stop because its Git
queries still read the merged head. It now tests the pre-late-package profile
against its reviewed source. The historical R27 scans also exposed the step 3
mode-list change and a package lookup hidden behind a local alias. The reviewed
route exception names R29 and the legacy lookup is again visible to the scan.
The first rehearsal fixture runs exposed missing VT and process details. In the
PID replacement case the fake now changes the PID after the submitted code has
observed the launch.

The local receipt binds the checker, probe sources and settings. Its 314 source
hashes match both the raw checkout bytes and the checkout replay. The diagnostics
retain 36 passing observations and 12 refusals, including missing display, wrong cwd and wrong VT, PID replacement,
monitor exhaustion, a rewritten, missing or reset sites list, a missing Control
check, a page hit during the closed gate and login dependency refusals. Mapped
fixture paths are recorded as guest paths. [Host receipt](../../os/manifest/ci/331/host-walk.json) ·
[Probe diagnostics](diagnostics/step4-probes.json)

### Limits and next

The Chrome profile, root reads, session checks and JVM are exercised locally
through submitted guest code with stand-in services and fixture state. The
fixture uses a real signed synthetic CRX with OpenSSL verification and a real
loopback counter. Hosted evidence must exercise the shipped browser and signed
candidate, the real service, desktop and scope, and the disk and firmware audits.
The owner's live save and close, Terminal with the world open and physical menu
checks are still open. C8 and 28b's combined profile proof retain their separate
live gates. The hosted baseline must be fresh because the harness and its receipt
are bound inputs.

Step 5 owns hosted selectors, permissions and the ledger and rehearsal receipts.
Step 6 owns the late image rules and final cut. B321's final contract, the
`aresos2` fixture binding and the build-context guard follow-up from REVIEW-3
remain for their applicable slices. Both effective R29 publish caps are zero.
Dispatches and uploads used by this slice are zero. There are no files over
500 MB in `.work/`.

## Done · step 5 first slice · 2026-11-22

Started at `e6ee98fe` on draft PR144. The REVIEW-7 fixes are at
`a08cf01b95bd9d66d87ca4c6b52f2d9a11439277`. The workflow and ledger changes
are at `851804260011aee0ab87510687f0a2b87e055500`.

- The login graph queries and traverses `Wants=` edges. The guest fixture adds
  `Wants=aresos-toold.service` to `greetd.service` and the walk stops.
  The existing hard-requirement checks still apply to their own edge types.
- The host receipt generator and validator share the complete expected source
  list, including `release29_walk.py`, the checker, probes, settings inputs
  and inherited rows. The test removes each of the 314 rows in turn and
  requires a refusal. Refreshed the existing local receipt's source hashes
  and the pending rebind record. The pending record has 19 changed files and
  zero removals.
- The exact `refs/heads/pkg/331-release-29` ref selects three jobs for
  `dry_run_29=true`, `release_29=true` and `rehearsal=release-29`.
  Colliding inputs and a same-named tag select no R29 route. The existing
  checks and resolve jobs call the guard on the same branch. Only the R29
  publish job receives package write and OIDC permissions. The dry run and
  rehearsal have read access.
- The package 331 guard counts dispatches from the first one, including
  failures and cancellations before any job starts. A collision with
  `release_29=true` keeps the publish title so the attempt spends that
  dispatch. Closing both publish caps preserves the historical dispatch and
  upload in the ledger. Fixtures give checks and rehearsal their own
  allowances while both publish caps are zero and prove that another
  release dispatch is refused. Both publish caps must open for a first
  publish and a prior upload attempt prevents another.

### Verified locally

Ran the following from the repository root, one module at a time, with
`TMPDIR` in `.work/`. The test command was
`python3 -m unittest discover -s os/tests -p <module>.py`.

| Module | Final result |
| --- | --- |
| `test_release29_workflow` | `Ran 8 tests in 0.062s`, `OK` |
| `test_build_tools` | `Ran 4 tests in 0.114s`, `OK` |
| `test_release29_rehearsal` | `Ran 22 tests in 30.459s`, `OK`. Printed `CONTROL_CHROME_FILES_PASS`, `CONTROL_CHROME_SITES_FIRST_USE_PASS` and `CONTROL_CHROME_SITES_REBOOT_PASS`. |
| `test_release28` | `Ran 94 tests in 55.099s`, `OK` |
| `test_release27` | `Ran 41 tests in 7.018s`, `OK` |
| `test_release28_rehearsal` | `Ran 44 tests in 34.817s`, `OK` |
| `test_rehearsal_budget` | `Ran 6 tests in 0.077s`, `OK` |
| `test_owner_staged_release` | `Ran 7 tests in 0.056s`, `OK` |
| `test_ci_api_permissions` | `Ran 4 tests in 4.256s`, `OK` |
| `test_ci_step_environment` | `Ran 4 tests in 21.504s`, `OK` |
| `test_checkout_sources` | `Ran 10 tests in 1.097s`, `OK` |
| `test_ways_back_model` with `-k test_hosted_checks_explore_the_slice_and_a_parallel_job_the_full_model_when_selected` | `Ran 1 test in 0.038s`, `OK` |

`python3 -m py_compile` on the changed CI and walk Python modules and the
new workflow test, plus `git diff --check` and `git diff --cached --check`,
exited 0 with no output. The source replay and raw byte comparison reported
`Validated 314 host receipt source rows`. The first test run exposed two
older assertions that pinned the pre-R29 mode table and title expression.
The final assertions check the extended table and R28's rendered title.
The permission audit caught the model guard's transitive package-read
requirement. The source replay passed after the final hashes were refreshed.

### Limits and next

The three new R29 jobs stop after their dispatch guard pending the next slice.
That slice owns registry targets, runner allowlists, hosted receipts and the
budget values. The lead then runs the same-head hosted checks and read-only
historical baseline preflight. Real signed-image VM evidence and the owner's
live checks remain open.

Hosted dispatches and uploads used by this slice are zero. No hosted run ID or
SHA was issued. `dispatch_caps.publish-29`, `publish_cap` and the qualifying
`dispatch_caps.release-29` are all zero. There are no files over 500 MB in
`.work/`.

## Done · step 5 slice A REVIEW-8 fixes · 2026-11-22

Started at `d9862df5` on `pkg/331-release-29`.

- The read-only `release-29-authorize` job checks the full branch ref
  case-sensitively and requires both publish caps. The separate `release-29`
  stub needs its success and has only `contents: read`. That downstream job
  is where the future publish steps and their package write and OIDC
  permissions belong. Fixtures reject a case-variant branch even with both
  caps open and keep the stub gated on failures, skips and cancellations.
- `checks-29-authorize` reserves 95 minutes once for the 60-minute regressions
  job and the 35-minute model job. Both jobs require its success on package
  331. A fixture with 60 minutes available refuses the dispatch. The
  historical R28 checks guard still reserves 60 minutes.
- Rejected package 331 input combinations use the default `OS image` title.
  The ledger counts that title and other unrecognized titles under
  `dispatch_counts.rejected`, while charging any measured job time. A
  collision with `release_29=true` still counts as a publish dispatch.
- The package 331 walk opts into `Wants=` queries and validation on both
  R28 and both R29 Control-checked boots. The historical R28 rehearsal keeps
  its original edge set. The guest fixtures exercise both routes.
- Refreshed the affected host receipt hashes and pending source bindings.
  The pending record has 18 changed files and zero removals.

### Verified locally

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the
repository root, one module at a time, with `TMPDIR` in `.work/tmp`.

| Module | Final result |
| --- | --- |
| `test_release29_workflow` | `Ran 12 tests in 0.082s`, `OK` |
| `test_release29_rehearsal` | `Ran 23 tests in 32.175s`, `OK`. Printed `CONTROL_CHROME_FILES_PASS`, `CONTROL_CHROME_SITES_FIRST_USE_PASS` and `CONTROL_CHROME_SITES_REBOOT_PASS`. |
| `test_release28_rehearsal` | `Ran 44 tests in 31.683s`, `OK` |
| `test_release28` | `Ran 94 tests in 58.714s`, `OK` |
| `test_release27` | `Ran 41 tests in 7.109s`, `OK` |
| `test_rehearsal_budget` | `Ran 6 tests in 0.076s`, `OK` |
| `test_owner_staged_release` | `Ran 7 tests in 0.056s`, `OK` |
| `test_checkout_sources` | `Ran 10 tests in 1.052s`, `OK` |
| `test_ci_api_permissions` | `Ran 4 tests in 4.055s`, `OK` |
| `test_ci_step_environment` | `Ran 4 tests in 19.888s`, `OK` |
| `test_ways_back_model` with `-k test_hosted_checks_explore_the_slice_and_a_parallel_job_the_full_model_when_selected` | `Ran 1 test in 0.039s`, `OK` |

The first workflow fixture run found a missing step name in the synthetic
timed job. The first budget test run found an assertion that still expected the
R29 clause in the R28 guard. The final runs include the corrected fixture
and the restored R28-only assertion.

The source comparison validated all 314 host receipt rows. Python compilation
of the edited modules, YAML parsing and `bash -n` on 94 workflow shell steps
with expressions replaced by fixture values passed. `git diff --check`
passed.

### Limits and next

REVIEW-8 known limit 5 stays with the next budget slice. A cancelled job row
without usable timestamps still stops the R29 ledger because the committed
settings supply no fallback bound. A cancelled dispatch with no job rows
still counts. The next slice owns the bound and hosted wiring.

All nine package 331 caps are zero. This round used zero hosted dispatches
and uploads. All evidence above is local. There are no files over 500 MB
in `.work/`.

## Done · step 5 second slice · 2026-11-22

Started at `5da3b3da96f75b370b2622b773ec2955dc59ce73` on draft PR144.
Implementation and fixture head `13b169d0611e23a8ab4516d694adb001e027e860`.

- The read-only `release-29-baseline` selector has its own dispatch count.
  It requires successful regressions and the full model on the exact head.
  The hosted runner checks its native capabilities, fetches missing pinned Git
  objects and verifies R13, R27 and R28 with the scoped job token and each
  immutable record's exact digest, Cosign identity and issuer. It removes the
  temporary auth before booting the disposable disks. The pinned ISO check and
  served Web UI bundle and source map checks gate the walk through confirmed
  R28 and tools v5. The separate qualifying dispatch also verifies the
  successful R29 publish job, recorded source trees and exact signed candidate
  before running the candidate route.
- The baseline artifact `release-29-baseline-receipt` retains
  `release-29-baseline.json` with the commit, run ID, attempt, registry proof,
  inputs, installer hashes and final audit facts. A passing qualification
  retains `release-29-qualifying-receipt` with the same-run registries, candidate
  equality and deployment result and `331-bound-sources.json`. Bounded
  diagnostics use `release-29-baseline-evidence` and `release-29-evidence`.
  Checks authorization has its own `331-checks-authorization` artifact.
- The R29 build modes use the immutable R28 target even when the active
  release pointer changes. The R29 publish entry checks the exact hosted
  branch, job, mode and ledger before its prospective shipment stop.
  The workflow publish stub is read-only and still needs authorization.
  The dry-run stub stays in place for step 7.
- REVIEW-8 limit 5 is covered by committed bounds. The ledger retains failed
  and cancelled dispatches. An unusable job interval falls back to the
  job's committed ceiling, with 360 minutes for an unrecognized hosted job.
  The checks reservation includes all 100 minutes across authorization and
  both workers. The ledger records the actual spend and preserves prior
  publish dispatches and uploads when both publish caps close.
- All ten effective caps remain zero in `os/ci/rehearsal-331-caps.json`.
  The separate file lets the lead change allowances without changing the
  hashed walk and policy inputs. The guard and its bounds remain bound.
  Refreshed the 314 host receipt rows and 23 pending rows with zero removals.

### Reviewed budget to open in later steps

| Mode | Initial dispatch allowance after review | Reservation per dispatch |
| --- | --- | --- |
| Same-head checks with full model | Separately reviewed, propose one now | 100 minutes, including 5 for authorization |
| Historical baseline preflight | Separately reviewed, propose one now | 345 minutes |
| Resolve | Separately reviewed on the cut | 120 minutes |
| Dry run | Two | 180 minutes |
| Private publish | One, with both publish caps open | 185 minutes, including 5 for authorization |
| Qualifying rehearsal | Up to three | 345 minutes |

The 345-minute ceiling covers each VM job from setup through evidence upload.
Measure the longer qualifying route before setting a separate VM-step limit.
Retry allowances require separate review. The first pair requires a 445-minute
cumulative cap with an empty ledger. Account for any previously charged minutes
before setting it.

### Lead dispatches in order

After reviewing this slice, commit the allowance for `checks: 1`,
`release-29-baseline: 1` and the reviewed minute cap. Keep the other caps closed.
Run both commands on that same pushed head. Wait for the checks and full model
to pass before dispatching the baseline.

```bash
gh workflow run "OS image" --ref pkg/331-release-29 -f checks_only=true -f full_model=true
gh workflow run "OS image" --ref pkg/331-release-29 -f rehearsal=release-29-baseline
```

Watch each run with `gh run watch <run-id> --exit-status --interval 60`. Record
both run IDs, attempts and head SHAs. Preserve the passing baseline artifact and
its bounded diagnostics for review. Before private upload, verify the passing
run identity and use `python3 os/ci/release29_walk.py check-receipt <receipt>`
against the intended checkout. A change to a bound baseline input requires a
fresh reviewed preflight. Steps 6 and 7 settle the cut, late-package rules,
resolve and dry run.

### Verified locally

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the
repository root, one module at a time, with `TMPDIR` in `.work/tmp`.

| Module | Result |
| --- | --- |
| `test_release29_workflow` | `Ran 15 tests in 0.122s`, `OK` |
| `test_build_tools` | `Ran 6 tests in 0.128s`, `OK` |
| `test_release29_rehearsal` | `Ran 26 tests in 30.902s`, `OK`. Printed the three Control Chrome PASS markers from fixtures. |
| `test_ci_api_permissions` | `Ran 4 tests in 4.138s`, `OK` |
| `test_ci_step_environment` | `Ran 4 tests in 20.909s`, `OK` |
| `test_owner_capabilities` | `Ran 6 tests in 0.180s`, `OK` |
| `test_owner_devices_native` | `Ran 14 tests in 2.203s`, `OK` |
| `test_owner_counter_flush` | `Ran 7 tests in 0.045s`, `OK` |
| `test_rehearsal_budget` | `Ran 6 tests in 0.083s`, `OK` |
| `test_owner_staged_release` | `Ran 7 tests in 0.058s`, `OK` |
| `test_rehearsal_auth` | `Ran 9 tests in 0.108s`, `OK` |
| `test_checkout_sources` | `Ran 10 tests in 1.063s`, `OK` |
| `test_release28_rehearsal` | `Ran 44 tests in 34.952s`, `OK` |
| `test_release28` | `Ran 94 tests in 56.248s`, `OK` |
| `test_release27` | `Ran 41 tests in 7.015s`, `OK` |
| `test_tools_local_wiring` | `Ran 42 tests in 57.257s`, `OK`. The disposable Git fixture printed the default-branch and empty-remote-HEAD notices. |
| `test_ways_back_model` with `-k test_hosted_checks_explore_the_slice_and_a_parallel_job_the_full_model_when_selected` | `Ran 1 test in 0.044s`, `OK` |

The first workflow fixture caught the new baseline selector reaching the
legacy rehearsal on another branch. The legacy selector now excludes it.
The environment audit originally expected a single device-proof caller and
now checks both callers. The historical decision scan flagged two R29
predicates it could not evaluate. The registry predicate now puts the
literal package check first, and the driver compares the receipt with a
separately constructed dispatch identity. The final runs passed.

YAML parsing and `bash -n` passed for all 102 workflow shell steps with
expressions rendered as fixture values. `bash -n os/ci/publish.sh`,
`python3 -m py_compile` on the edited Python files and `git diff --check`
passed. Source replay and raw-byte checks validated all 314 host receipt
rows. There are no files over 500 MB in `.work/`.

### Limits

This slice used zero hosted dispatches and zero uploads, so it has no hosted
run ID, attempt or SHA. Live job-token access, Cosign and ISO availability,
the served installer assets, disposable VM boot and protected disk audits
remain for the hosted baseline. Qualification still needs the real R29
record and exact candidate payload after publishing. The owner's live
world close and save, Terminal with the world open and physical boot menu
remain manual checks. All effective caps are zero at handoff.

## Done · step 5 slice B REVIEW-10 fixes · 2026-11-22

Started at `3a7bd3a665250f2740bb9d5618fbdb24d99268b4` on `pkg/331-release-29`.

- After authorization, the qualifying job validates the publish URL in the
  checked-in R29 record and passes its exact run ID and the job token to the
  pinned artifact download action. It uses the `os-image-evidence` name and
  root `release.json` path used by prior publishes. The verifier compares the
  artifact's digest and full record against the candidate before the native
  checks, signature checks and VM walk. Fixtures accept the matching record
  and refuse a missing artifact, a wrong run ID and a different digest with
  the same signing identity.
- Both R29 walk mode names now reach the exact package 331 guard through
  `owner_media.require_runner()`, including the capability, device and kernel
  counter entry points. Fixtures accept the exact dispatch context for both
  modes and refuse a package 14 context before reaching any native probe.
- Refreshed five hashes in the 314-row host receipt and the affected pending
  bindings. The pending list has 23 files and zero removals.

### Verified locally

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the
repository root, one module at a time, with `TMPDIR` in `.work/tmp`.

| Module | Result |
| --- | --- |
| `test_release29_workflow.py` | `Ran 15 tests in 0.132s`, `OK` |
| `test_release29_rehearsal.py` | `Ran 26 tests in 30.959s`, `OK`, with the three Control Chrome PASS markers from fixtures |
| `test_owner_media.py` | `Ran 6 tests in 0.213s`, `OK` |
| `test_owner_capabilities.py` | `Ran 6 tests in 0.180s`, `OK` |
| `test_owner_devices_native.py` | `Ran 14 tests in 1.807s`, `OK` |
| `test_owner_counter_flush.py` | `Ran 7 tests in 0.048s`, `OK`, with `COUNTER_KERNEL_PROOF guest-required guest-before-hidden-input` from the fixture |
| `test_ci_api_permissions.py` | `Ran 4 tests in 4.030s`, `OK` |
| `test_ci_step_environment.py` | `Ran 4 tests in 20.748s`, `OK` |
| `test_checkout_sources.py` | `Ran 10 tests in 1.046s`, `OK` |
| `test_release27.py` | `Ran 41 tests in 6.739s`, `OK` |
| `test_release28_rehearsal.py` | `Ran 44 tests in 36.171s`, `OK` |

YAML parsing and `bash -n` passed for all 103 workflow shell steps with
expressions rendered as fixture values. Six local cases exercised the actual
run-ID step, including refusal of an absent ID, an attempt URL, another
repository and a preexisting download directory. Source replay and raw-byte
checks validated all 314 host receipt rows. `git diff --check` passed. There
are no files over 500 MB in `.work/`.

### Limits and next

All ten caps are zero, and the publish stub stays read-only behind
authorization. Ledger use for this round is zero dispatches and uploads.
After recheck, the lead still owns the same-head checks and baseline preflight
in the order above. Later qualification needs the real publish run's retained
artifact and the exact candidate payload. Hosted artifact access and VM boot
remain unverified.

## Hosted checks fix for a fresh evidence directory · 2026-11-22

All three rejected reset cases in hosted checks run 45065464450 raised
`FileNotFoundError` while saving shutdown diagnostics. The shutdown console
writer now creates its parent directory and reports filesystem errors as a
warning. Shutdown event validation and the final write-counter audit still
determine the shutdown result.
[Hosted checks run](https://github.com/Ares-Empire/AresOS/actions/runs/45065464450)

The shared JSON writer used by `release29_probes.py` and `owner_vm.py` now
creates its parent directory. The separate baseline receipt in
`release29_walk.py` does the same. Required receipts still fail if they
cannot be saved. Refreshed four hashes in the 314-row host receipt and
updated the pending source bindings, which now contain 24 files and zero
removals.

The reset test now discovers on its own. Each rejected event starts with a
fresh temporary evidence path and checks both the rejection reason and the
saved console file. A file collision fixture checks that an evidence write
error preserves both accepted and rejected reset results. The JSON writer
and baseline fixtures also use missing parent directories.

### Verified locally

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the
repository root, one module at a time. Moved the existing `evidence/` folder
aside for the runs and restored it afterward. Before the fix, the isolated
reset module reproduced the three `FileNotFoundError` cases and raised an
`IsADirectoryError` in the new collision fixture.

| Module | Result |
| --- | --- |
| `test_owner_reset.py` | `Ran 5 tests in 0.013s`, `OK` |
| `test_two_disk_vm.py` | `Ran 32 tests in 0.173s`, `OK` |
| `test_release29_rehearsal.py` | `Ran 26 tests in 31.115s`, `OK`, with the three Control Chrome PASS markers from fixtures |
| `test_owner_walk.py` | `Ran 40 tests in 623.299s`, `OK`, with `PASS historical R29 baseline through confirmed R28 with tools v5` |
| `test_checkout_sources.py` | `Ran 10 tests in 1.050s`, `OK` |
| `test_stock_image.py` | `Ran 29 tests in 0.122s`, `OK`, with three stock-rewind free-space messages from fixtures |

Source replay and raw-byte checks verified all 314 host receipt rows.
`git diff --check` passed. There are no files over 500 MB in `.work/`.
Verification covered local fixtures. The hosted rerun and live VM remain
unverified.

## Hosted proof after step 5 (the lead, 2026-11-22/23)

- **Checks 1:** run 45065464450 at `f4a33f85` FAILED. `test_owner_reset` raised FileNotFoundError writing `evidence/two-disk/…-shutdown-console.txt` on a fresh runner. It was fixed in `492fdf82` (evidence folders are created before writing).
- **Checks 2:** run 45070065335 at `1ac63562` PASSED: the regressions (2642 tests) and the full ways-back model.
- **Historical baseline preflight:** run 45073317069 at `1ac63562`, attempt 1, PASSED in about 2 h. Its artifacts are `release-29-baseline-receipt` and `release-29-baseline-evidence` (about 22 MB). The receipt must be checked with `release29_walk.py check-receipt` before the private upload, and redone if a bound baseline input changes.
- **Ledger:** checks 2 of 2 and release-29-baseline 1 of 1 are spent, within the minute cap of 545. The publish caps stay 0.
- **Next:** late-package slices for what is already on main (18c-b, B329, B330, the mod changes 327, 328a and 328), then the cut once B321 meets its conditions.

## Step 6 · late packages through 328 · 2026-11-23

Started at `c01a5660` on draft PR144. Merged `origin/main` at
`17211fb1203a53d64653e49429a7fdecee39a69b` in `a78a6574`. The previous
merge `a5dbff3f` already contained 18c-b, B329, B330, 327 and 328a. The new
main commits carried no pending-rebind edits, so the clean merge preserved
all earlier notes. Recomputed the pending file list with `rebind.py pending`.
Package 334's design and review files also arrived in this merge.

### Image profile

- **18c-b · `d37ea134`.** Replays each side's `control-tree` install
  map and wheel lock from that image's committed inputs. The two images
  have the same wheel and vendor records, and the classifier checks every
  recorded file, directory, and link in both installs. The reviewed
  runtime delta is `aresos_control/chrome/exclusions.py` for the new
  first-boot gate, computed `chrome/build-id.json`, the two native relay
  files, the polkit action and the tmpfiles rule. The shared `control.json`
  binds the source revision, Chrome build, bundle and gh fields, and
  the two additional links. The bundle check holds the directory to four
  files, verifies the CRX signature and committed payload, and compares
  policy, update XML and native-host metadata with the rendered
  templates and signed extension ID. The image has two root policy and
  host links under `/etc/opt/chrome`. The guest checker compares them with
  the deployed copies under `/usr/etc`. The sites list is created in
  guest state on first boot. [Control proof 44936830501](https://github.com/Ares-Empire/AresOS/actions/runs/44936830501)
- **18c-b gh.** Binds `os/gh.lock.json` and its signing-key file and mode
  to the source. The build verifies the signature, RPM SHA-256 and all
  240 RPM payload paths. The profile requires the binary, the licence and
  the installed byte-for-byte lock. It refuses another RPM payload file
  or an installed gh RPM, including when present on both sides. Both R29
  confirming boots require the pinned gh version in the Control result.
  C6 still observes the closed first-use gate before the synthetic list
  is installed. [18c-b handoff](../18c-b-chrome-image/PROGRESS.md#for-linux-aresoss-release-brief)
- **B329 · `b720da42`.** Checks the 37 new files in
  `/usr/share/themes/AresOS/labwc/`, the 36 native look pack frame cells,
  their directories and the expanded look manifest. Compares both
  complete inventories with the image-check pins. The B329 XML delta
  replaces the theme and switcher rows and adds `A-S-Tab` and three
  mouse rows. The mouse rows retain `<default />` first, disable both
  TitleBar scroll directions and clear the Left, Right and Middle Root
  presses. The diff compares exact XML bytes and keeps the Crown pin.
  The guest uses AresOS on both R29 boots and Ares-Crown on both R28 boots.
  [B329 handoff](../329-window-frame/PROGRESS.md#for-linux-aresos) ·
  [Hosted build 44942183654](https://github.com/Ares-Empire/AresOS/actions/runs/44942183654)
- **B330 · `a7fb7cfe`.** Checks the hidden
  `org.prismlauncher.PrismLauncher.desktop` entry and the Prism scheme
  default in `aresos-mimeapps.list` against the source files. The
  classifier has no MIME cache exception for B330. The two R29 guest
  boots query the scheme as the daily account with the AresOS session
  environment. Live Microsoft sign-in is open. [B330 report](../330-prism-handler/REPORT.md) ·
  [Hosted build 44938296580](https://github.com/Ares-Empire/AresOS/actions/runs/44938296580)
- **Mod · `4dd5288b`, `92cf365a`, `17211fb1`.** 327 adds home
  onboarding, Live protection, menu access, New home and Terminal artwork.
  328a keeps the pointer in the active world and prevents clicks reaching
  apps beneath it. 328 adds click-to-look and edge-turn prototypes. The
  image carries these through the existing jar and its records. The
  desktop lock still has its previous jar pin. Renew only that pin when
  two clean hosted builds reproduce the final cut's jar. B332, B334 and
  the intervening brief and status commits have no mounted image delta.
  The 18c-b static CI hostname and B329's frame harness are test inputs.

The context guard now checks ordinary untracked files, Git-ignored files
and tracked edits anywhere under the local `os/` context, including
staged edits. It honors literal root exclusions from `os/.containerignore`.
Fixtures cover copied files with names containing spaces, exclusions,
nested look-alike paths and an ignored file outside `os/`. The classifier
also exercises reordered XML, missing and wrong-mode frame files, an
unhidden Prism entry, a wrong default and a cache change, a forged CRX
signature, a wrong Chrome link, vendor drift, preplanted guest state, and
changed gh bytes and extra RPM payload.

### Summary for the owner

- Chrome shows the AresOS extension's A button and a managed-browser notice.
  Chrome tools stay off until the owner writes the never-list.
- Windows use the new pixel frame. Shift+Alt+Tab cycles backward, and
  scrolling on the title bar no longer shades or unshades a window.
- The browser can send Prism's Microsoft sign-in callback to Prism Launcher.

### Historical baseline and next cut

Downloaded the receipt artifact from run 45073317069 and compared its 73
input hashes against Git blobs at `1ac63562` and at merge `a78a6574`.
All 73 matched at both commits. The merge by itself changed zero
baseline-bound inputs. This slice changes `os/ci/release29_probes.py`,
`os/ci/release29_walk.py` and the local receipt
`os/manifest/ci/331/host-walk.json`, which the hosted baseline also binds.
**The lead must rerun the historical baseline preflight before the private
upload.** [Run 45073317069](https://github.com/Ares-Empire/AresOS/actions/runs/45073317069)

The final cut, Deskflow decision, reproducible jar evidence, hosted checks
and dry run remain open. Live OAuth and the owner's world and hardware
checks remain open. The existing Alt+Tab then Escape issue persists in
both frame configurations. Switching away and back restores keys to the
world. This slice used zero dispatches and zero uploads.


### Verified locally

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the
repository root, one module at a time, with `TMPDIR` in `.work/tmp` and
`PYTHONDONTWRITEBYTECODE=1`. The final results total 712 tests over
31 modules, including the separately listed filters.

| Module | Result |
| --- | --- |
| `test_release29.py` | `Ran 35 tests in 59.128s`, `OK` |
| `test_release28.py` | `Ran 94 tests in 63.927s`, `OK` |
| `test_release27.py` | `Ran 41 tests in 7.029s`, `OK` |
| `test_owner_walk.py` | `Ran 40 tests in 622.476s`, `OK` |
| `test_release29_rehearsal.py` | `Ran 26 tests in 32.418s`, `OK` |
| `test_release29_workflow.py` | `Ran 15 tests in 0.131s`, `OK` |
| `test_checkout_sources.py` | `Ran 10 tests in 1.064s`, `OK` |
| `test_release28_rehearsal.py` | `Ran 44 tests in 34.731s`, `OK` |
| `test_two_disk_vm.py` | `Ran 32 tests in 0.177s`, `OK` |
| `test_rehearsal_auth.py` | `Ran 9 tests in 0.093s`, `OK` |
| `test_installer_webui.py` | `Ran 9 tests in 0.004s`, `OK` |
| `test_owner_media.py` | `Ran 6 tests in 0.195s`, `OK` |
| `test_ci_api_permissions.py` | `Ran 4 tests in 4.101s`, `OK` |
| `test_tools_local_wiring.py` | `Ran 42 tests in 57.467s`, `OK` |
| `test_build_tools.py` | `Ran 6 tests in 0.139s`, `OK` |
| `test_rehearsal_budget.py` | `Ran 6 tests in 0.084s`, `OK` |
| `test_owner_staged_release.py` | `Ran 7 tests in 0.059s`, `OK` |
| `test_ci_step_environment.py` | `Ran 4 tests in 20.641s`, `OK` |
| `test_owner_capabilities.py` | `Ran 6 tests in 0.177s`, `OK` |
| `test_owner_devices_native.py` | `Ran 14 tests in 1.779s`, `OK` |
| `test_owner_counter_flush.py` | `Ran 7 tests in 0.051s`, `OK` |
| `test_owner_reset.py` | `Ran 5 tests in 0.013s`, `OK` |
| `test_stock_image.py` | `Ran 29 tests in 0.118s`, `OK` |
| `test_aresos_labwc_rc.py` | `Ran 2 tests in 0.005s`, `OK` |
| `test_aresos_labwc_theme.py` | `Ran 3 tests in 0.093s`, `OK` |
| `test_aresos_look_pack.py` | `Ran 1 test in 0.098s`, `OK` |
| `test_aresos_shell_discovery.py` | `Ran 37 tests in 0.114s`, `OK` |
| `test_everyday_account.py` | `Ran 36 tests in 0.113s`, `OK` |
| `test_control_vm.py` | `Ran 103 tests in 2.705s`, `OK` |
| `test_control_image.py` with `-k InstallMapTest -k ChromeImageTest -k ChromePrivateScanTest -k GhImageTest` | `Ran 38 tests in 2.555s`, `OK` |
| `test_ways_back_model.py` with `-k test_hosted_checks_explore_the_slice_and_a_parallel_job_the_full_model_when_selected` | `Ran 1 test in 0.042s`, `OK` |

The first merged-profile run found that its R28 fixture omitted the
existing polkit action directories and that its stale labwc test was
reading the patched fixture hash. Corrected the fixture to include the
base policy on both sides and read the unpatched lock from Git. The final
fixture run printed `IMAGE_DIFF_PASSED` for 160, 160, 157 and 162 changed
paths. The historical walk printed `PASS historical R29 baseline through
confirmed R28 with tools v5`. The R29 rehearsal printed the three
Chrome first-use and reboot PASS markers.

`python3 reviews/331-release-29/walk-host.py` printed
`PASS package 331 synthetic baseline and candidate host walk with 319 sources`.
All 319 rows matched the raw checkout SHA-256 and Git checkout replay.
The diagnostics retain 38 passing observations and 15 refusals. The
pending table has 24 changed rows and zero removals. The branch's source
guard passed on the exact main merge base after 54 generated Python
cache files were moved aside to `.work/331-context-cache/`.

`python3 -B os/ci/release29_walk.py check-receipt .work/331-baseline/release-29-baseline.json`
exited 1 with `STOP: rerun the historical R29 baseline preflight on the current inputs`.
The incoming B334 design note has a whitespace-only line. The post-merge
slice passed `git diff --check a78a6574`. The cap file matches
`1ac63562` byte for byte. There are no files over 500 MB in `.work/`.

## Late-package slice reviewed 2026-11-23 (the lead)

- **REVIEW-12** (fresh Codex `gpt-6.2-sol` high, at `0f8b6870`): SAFE. 18c-b, B329, B330 and the mod changes of 327, 328a and 328 are classified.
- **Waiting for the cut:** B321 (Deskflow (c)) under item 6's four conditions, and any later merges such as B334a (bench) and further mod changes. Then the cut slice, the resolve, the dry run, the rerun of the baseline preflight (3 of its 73 inputs changed in this slice), and the publish gate.
- **Chrome 28 and 28a (linux-tools, PR72 and PR116):** they may ride R29 if both are on main by end of Wednesday 25 Nov (the lead, 2026-11-23; the owner wants the Chrome tools improved before R29). They are control/ code only, and CONTROL_CHROME_BUILD changes; the gate stays closed. linux-tools hands over the image differences, any new Control checks, any release gate in their own handoffs, and an owner-summary line. If they miss Wednesday, they wait for R30.
- **B334a, the bench (PR168, `7e161ebc`), merged 2026-11-23:** it changes os-image.yml, check-build.sh, .containerignore and pending-rebind.json. B331's next main merge resolves the os-image.yml conflicts and keeps both sides' pending notes. Bench refuses ledger-managed refs (taken from rehearsal-packages.json). A stray bench run on pkg/331-release-29 would be counted as rejected and charged; deleting one is the lead's decision.
- **B321's os/ read 1 (2026-11-23):** FINDINGS, in `B321-LEAD-READ-1.md` (a Codex Sol read for the lead, at `9b01df80`). linux-desktop fixes items 1, 2, 4 and 5 and makes the resolve prove a stable `updates` source. For B331's cut slice (item 3): the Deskflow and libportal inventory, the desktop-entry exception, the merged rc.xml pin, source bindings for `os/input-portal/`, `os/manifest/input-portal.sha256` and `os/deskflow-rpm.sh`, the host-receipt rows for `os/ci/toolchain.json` and rc.xml, and a fresh baseline preflight. B321 stays off main until stable.
- **28a renames Chrome tools (linux-tools, 2026-11-23):** `take_tab` becomes `take`, and the tabs and read replies change shape. If 28a rides R29, the late-package slice updates C6's first-use refusal set in `release29_probes.py`, `release29_walk.py` and their tests from linux-tools' old-to-new map. The Control check names and PASS lines stay the same.
- **28a's tool map, main to 28a (linux-tools, 2026-11-23; the chrome_ prefix dropped):**
  - take_tab becomes take (it takes the `seen` token from tabs); release_tab becomes release; close_tab becomes close; navigate becomes go;
  - downloads, bookmarks and history become library with `kind`;
  - click, fill, fill_form, select, check, press, scroll, dialog and wait become do (steps; wait becomes `until`);
  - find and read_form become read (`find`, `ref`, `full`); show is new;
  - unchanged: tabs, read, open, drop, operation_status, notices, notice_ack, upload, submit, submit_trusted, read_typed_fields and prepare_read_typed_fields.
  - Replies: tabs gives `seen`, `total` and a rendered list (no `data.items`); read gives the outline (no `untrusted_content.tree`).
  - C6's first-use refusal set is tabs, read, open and take, with the exact `chrome_settings_unavailable` and zero page-server arrivals; the PASS names are unchanged. The lead's read of 28a's os/ part: clean (chrome_actions.py, sessions.py, test_control_vm.py).
- **B321's os/ read 2 (2026-11-23): CLEAN at `52c99893`** (`B321-LEAD-READ-2.md`). B321 merges after dispatch 16, which runs the stable re-resolve and gives the corrected portal binary (`29e4b8ff`) its hosted relogin proof. Any later os/ change comes back to the lead.
- **Chrome profile lock and the guest hostname (linux-tools, 2026-11-23):** a guest without a static hostname gets renamed by NetworkManager after boot. Chrome's profile lock then names the old host, and every later Chrome start fails ("profile in use … on another computer"). The CI overlay fix (`8f3053a1`, NetworkManager `hostname-mode=none`) doesn't reach R29's rehearsal, which installs the real images. **For the cut slice:** the baseline leg sets a static hostname in the guest (as the owner's laptop has /etc/hostname) before any Chrome start, with a probe that the name is unchanged across reboots. This keeps the Chrome checks on both R29 boots and after `previous`/`forward` from flaking.
  - linux-tools confirms that 18c-b's checks read no hostname (C7 matches journal lines by unit and process; the C11 records name no host). Set the name at runtime in the guest (`hostnamectl set-hostname`, or a real file written outside any build RUN step) before Chrome first runs in that boot.
- **Chrome 28 and 28a merged on main (2026-11-23):** 28 is `11d22cd4` (PR72), 28a is `db7ad4bf` (PR116). linux-tools' handoff for the late-package slice:
  - **Control's installed code:** under `/usr/libexec/aresos-control/aresos_control/chrome/`, 28's view modules (view, nodes, references, address) and 28a's tool list and adapter (open, go, read, do, take, release, close, show, library and upload; submit and submit_trusted unchanged). The generated catalogue and MCP instructions change with them. `control/settings/ask-rules.json` is byte-identical.
  - **Extension bundle:** under `/usr/share/aresos/chrome/`, new extension code (reader.js, background.js). So CONTROL_CHROME_BUILD, control.json's `chrome_build` and `chrome_extension`, and the per-build extension ID change.
  - **Ledger:** the release's `record_build.py add` row is for the new CONTROL_CHROME_BUILD.
  - **Not shipped:** os/ changes are CI only (the overlay's NetworkManager drop-in, os/ci/control, os/tests).
  - **Checks:** no new Control check or guest probe, and the PASS names are unchanged. C6's first-use refusal set is tabs, read, open and take. C8 is stricter, but the rehearsal doesn't run it.
  - **Gates:** neither package gates the release beyond the owner's live sitting (C8 before his never-list). 28b isn't in R29.
  - **Owner-summary line:** "Chrome: Claude's Chrome tools get faster and leaner. Pages come as a compact outline with short references, and one call can do several steps and report only what changed. They stay off until you write your never-list in a short sitting with Claude."
  - **Known CI flakes:** C11's GitHub rate limit (control pass only; retry in R30), and board T527 (prism_failed once in control-ordinary).

## Done · step 6b · 2026-11-26

- Merged main through `9b07a957` and kept R29's guarded workflow modes
  alongside B334a's bench. The bench reads the shared release ledger and
  refuses managed refs before tools or image work. Kept both parents' pending
  notes and recomputed the file hashes. Cherry-picked the
  [T527 investigation](T527-PRISM-CHECK.md) from `4d3d375d`.
- Bound Chrome 28 (`11d22cd4`) and 28a (`db7ad4bf`) in the R29 image
  comparison. It requires the exact installed Python modules, regenerated
  catalogue, MCP instructions and CLI help, the reviewed
  `CONTROL_CHROME_BUILD`, and the CRX payload and manifests with one
  per-build extension ID. The install-map and bundle checks verify the
  image bytes and metadata. The comparison also checks
  `control/settings/ask-rules.json` against the pre-28 source byte for byte.
- B334a and B334b add no installed image paths. The source tests account for
  the separate bench layer, the release context exclusions and the release
  build's cleanup of its staging directory. The context guard accepts the
  exact new bench test exclusion and still catches neighbouring paths.
- C6 now checks `tabs`, `read`, `open` and `take`. The deployment receipt
  records all four `chrome_settings_unavailable` replies and zero page
  requests. The three Chrome PASS names stay the same.
- The guest sets `aresos-rehearsal` at the first authenticated installed
  stock boot, before enabling the network or opening Chrome. Each later
  boot reads `/etc/hostname` and checks its static and transient names,
  including the first R29 boot, the return to R28 and the forward boot.
  A mismatch stops the walk before any hostname repair.
- On unexpected desktop recovery, the walk retains bounded `explain`,
  `desktop.log`, current-boot daily-user journal and Prism log output
  before stopping. The recovery decision remains with the lead. The
  Control check saves the first `prism_failed` explanation in its ordinary
  evidence and keeps its existing verdict.

**Owner summary.** Chrome: Claude's Chrome tools get faster and leaner. Pages come as a compact outline with short references, and one call can do several steps and report only what changed. They stay off until you write your never-list in a short sitting with Claude.

### Historical baseline

Compared the 73 input hashes from run 45073317069 at `1ac63562` with the
recorded Git checkout and this slice. Six bound paths changed.

- `.github/workflows/os-image.yml`
- `os/ci/owner_vm.py`
- `os/ci/release28_walk.py`
- `os/ci/release29_probes.py`
- `os/ci/release29_walk.py`
- `os/manifest/ci/331/host-walk.json`

The lead needs a fresh historical baseline preflight on the final cut before
private upload. [Run 45073317069](https://github.com/Ares-Empire/AresOS/actions/runs/45073317069)

### Verified locally

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the
repository root, one affected module at a time, with temporary files under
`.work/331-step6b/tmp` and bytecode writes disabled. The latest runs total
667 passing tests across 30 modules.

| Module | Result |
| --- | --- |
| `test_bench_dispatch.py` | `Ran 7 tests in 0.246s`, `OK` |
| `test_bench_evidence.py` | `Ran 7 tests in 0.036s`, `OK` |
| `test_bench_release_layers.py` | `Ran 3 tests in 0.169s`, `OK` |
| `test_bench_script.py` | `Ran 3 tests in 0.027s`, `OK` |
| `test_build_tools.py` | `Ran 6 tests in 0.160s`, `OK` |
| `test_checkout_sources.py` | `Ran 10 tests in 1.115s`, `OK` |
| `test_ci_api_permissions.py` | `Ran 4 tests in 5.038s`, `OK` |
| `test_ci_step_environment.py` | `Ran 4 tests in 25.666s`, `OK` |
| `test_control_image.py` with `-k InstallMapTest -k ChromeImageTest -k ChromePrivateScanTest -k GhImageTest` | `Ran 38 tests in 2.689s`, `OK` |
| `test_control_vm.py` | `Ran 110 tests in 3.206s`, `OK` |
| `test_installer_webui.py` | `Ran 9 tests in 0.005s`, `OK` |
| `test_owner_capabilities.py` | `Ran 6 tests in 0.183s`, `OK` |
| `test_owner_counter_flush.py` | `Ran 7 tests in 0.053s`, `OK` |
| `test_owner_devices_native.py` | `Ran 14 tests in 2.125s`, `OK` |
| `test_owner_media.py` | `Ran 6 tests in 0.384s`, `OK` |
| `test_owner_reset.py` | `Ran 5 tests in 0.015s`, `OK` |
| `test_owner_staged_release.py` | `Ran 7 tests in 0.067s`, `OK` |
| `test_owner_walk.py` | `Ran 40 tests in 638.806s`, `OK` |
| `test_rehearsal_auth.py` | `Ran 9 tests in 0.189s`, `OK` |
| `test_rehearsal_budget.py` | `Ran 6 tests in 0.128s`, `OK` |
| `test_release27.py` | `Ran 41 tests in 6.891s`, `OK` |
| `test_release28.py` | `Ran 94 tests in 65.896s`, `OK` |
| `test_release28_rehearsal.py` | `Ran 44 tests in 36.492s`, `OK` |
| `test_release29.py` | `Ran 39 tests in 65.784s`, `OK` |
| `test_release29_rehearsal.py` | `Ran 29 tests in 41.428s`, `OK` |
| `test_release29_workflow.py` | `Ran 15 tests in 0.136s`, `OK` |
| `test_stock_image.py` | `Ran 29 tests in 0.165s`, `OK` |
| `test_tools_local_wiring.py` | `Ran 42 tests in 58.741s`, `OK` |
| `test_two_disk_vm.py` | `Ran 32 tests in 0.193s`, `OK` |
| `test_ways_back_model.py` with `-k test_hosted_checks_explore_the_slice_and_a_parallel_job_the_full_model_when_selected` | `Ran 1 test in 0.043s`, `OK` |

The first image-profile run after the merge exposed the unrecognised B334a
ignore pattern. The first combined run exposed a misplaced assertion in the
new bench fixture. The final image-profile run passed and printed
`IMAGE_DIFF_PASSED` for 182, 182, 179 and 184 paths. The historical model
printed `PASS historical R29 baseline through confirmed R28 with tools v5`.
The R29 rehearsal model printed `CONTROL_CHROME_FILES_PASS`,
`CONTROL_CHROME_SITES_FIRST_USE_PASS` and `CONTROL_CHROME_SITES_REBOOT_PASS`.

`python3 reviews/331-release-29/walk-host.py` printed
`PASS package 331 synthetic baseline and candidate host walk with 319 sources`.
The source rows match the raw checkout and Git checkout replay. The
[fixture diagnostics](diagnostics/step4-probes.json) retain 47 passing
observations and 20 refusals. Recomputing pending bindings found 24 changed
rows and zero removals. The R29 source guard passed against main at
`9b07a957`. The rehearsal cap and dispatch ledger compare byte for byte
with the pre-slice branch.

`python3 -B os/ci/release29_walk.py check-receipt .work/331-baseline/release-29-baseline.json`
exited 1 with `STOP: rerun the historical R29 baseline preflight on the current inputs`.

### Limits

The local tests use fixtures. The signed image comparison, hostname
persistence through real VM boots, and Prism failure capture in a hosted
guest still need hosted proof. B321 and the remaining cut changes are
scheduled at the cut. This slice used zero dispatches and zero uploads.
There are no files over 500 MB in `.work/`.

## Done · step 6b fix · 2026-11-26

For REVIEW-13 finding 1, the R29 walk checks desktop health immediately
before rebooting into `previous` and on the forward boot just before the
game-scope probe. That probe deliberately kills its JVM and already checks
the resulting recovery.
At either new checkpoint, unexpected recovery saves bounded `explain`,
`desktop.log`, the current-boot daily-user journal and the Prism log before
stopping without a retry. The fixtures check the order and cover both
`prism_failed` and `jvm_failed`.

The refreshed local host receipt binds the walk and test changes. The two
historical baseline inputs changed again since `f93fe4de` are
`os/ci/release29_walk.py` and `os/manifest/ci/331/host-walk.json`. The same
six paths still differ from run 45073317069. Running
`python3 -B os/ci/release29_walk.py check-receipt .work/331-baseline/release-29-baseline.json`
exited 1 with `STOP: rerun the historical R29 baseline preflight on the current inputs`.

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the repo
root, one module at a time, with temporary files under `.work/331-step6b-fix/tmp`.

| Module | Result |
| --- | --- |
| `test_release29.py` | `Ran 39 tests in 69.620s`, `OK` |
| `test_release29_rehearsal.py` | `Ran 29 tests in 42.565s`, `OK` after correcting the test's evidence lookup |
| `test_release29_workflow.py` | `Ran 15 tests in 0.134s`, `OK` |
| `test_owner_walk.py` | `Ran 40 tests in 619.480s`, `OK` |

`python3 reviews/331-release-29/walk-host.py` printed
`PASS package 331 synthetic baseline and candidate host walk with 319 sources`.
All 319 hashes matched the raw files and Git checkout replay. The two new
status records appear in the [fixture diagnostics](diagnostics/step4-probes.json).
Real-boot proof remains with the hosted rehearsal. There are no files over
500 MB in `.work/`.

## Live ISO requalified 2026-11-26

The R29 baseline preflight at `5fd70c8c` stopped in **Inspect the exact
pinned live ISO** with `Official checksum changed: STOP`. Bazzite replaced
`bazzite-nvidia-open-stable-live-amd64.iso` on 2026-11-25 at 16:56 GMT.
[Run 45882047120](https://github.com/Ares-Empire/AresOS/actions/runs/45882047120)

The first download with `curl --continue-at -` matched Bazzite's
`Content-Length` of **9102135296 bytes** and SHA-256
`062c93ac13838557e9e8cdff01940aa4a65186049ae6f0179cf5111411fa1396`.
The legacy publisher checksum also matched its existing pin.
[Live publisher checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso-CHECKSUM)
[Legacy publisher checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-amd64.iso-CHECKSUM)

`7z x -so -tIso` extracted `LiveOS/squashfs.img` from the verified ISO.
`unsquashfs -p 1 -strict-errors -cat` read
`var/lib/containers/storage/overlay-images/images.json` from that
SquashFS 4.0 image in user space. The following is the output of
`stock_image.embedded_rows`. `stock_image.check_embedded` accepted it
against the refreshed pin.

```json
[
  {
    "names": ["ghcr.io/ublue-os/bazzite-nvidia-open:stable"],
    "digest": "sha256:98a6a6a31670cbfa005866c6d6de2e768409dd7cb9db25f324b20cc55294fb89"
  }
]
```

The stock image fixture now uses fields from the observed index.

**Lead correction (2026-11-26):** this step first also added the live
ISO's checksum to `docs/INSTALL-REFERENCE.md` and loosened
`test_owner_equality.py` to allow it, following the lead's prompt, which
pointed at R28's older requalification (3ae3716a). Since R28 (6ae4da41)
the live ISO is rehearsal-only and must stay out of the owner's guide,
reference and card, which
`test_rehearsal_iso_is_absent_from_the_owner_route_and_the_install_hold_precedes_the_erase`
enforces. The lead restored both files to their `5fd70c8c` bytes, set
their pending and host-receipt hashes back, and reran
`rebind.py pending` (unchanged), `test_owner_equality.py` and
`test_stock_image.py` (both `OK`). All 319 host-receipt hashes match
the checkout. A requalification changes only
`os/manifest/installer-isos.json`, its stock fixture and the bindings.

### Baseline inputs

Two of the 73 input hashes changed from `5fd70c8c`.

- `os/manifest/installer-isos.json`
- `os/manifest/ci/331/host-walk.json`

`python3 reviews/27-first-update-release/rebind.py pending` reported
`pending: 25 bound files differ from the active bindings, 0 removed`.
`python3 reviews/331-release-29/walk-host.py` printed
`PASS package 331 synthetic baseline and candidate host walk with 319 sources`.
All 319 hashes matched the raw checkout and Git checkout replay. The earlier
baseline receipt was refused with
`STOP: rerun the historical R29 baseline preflight on the current inputs`.

### Local verification

Ran `python3 -m unittest discover -s os/tests -p <module>.py` from the repo
root, one module at a time. Temporary files were under `.work/` and
Python bytecode writes were disabled.
All 278 tests across 11 modules passed.

| Module | Result |
| --- | --- |
| `test_stock_image.py` | `Ran 29 tests in 0.136s`, `OK` |
| `test_installer_download.py` | `Ran 12 tests in 0.320s`, `OK` |
| `test_installer_webui.py` | `Ran 9 tests in 0.005s`, `OK` |
| `test_two_disk_vm.py` | `Ran 32 tests in 0.183s`, `OK` |
| `test_checkout_sources.py` | `Ran 10 tests in 1.058s`, `OK` |
| `test_owner_equality.py` | `Ran 12 tests in 104.123s`, `OK` |
| `test_owner_path.py` | `Ran 51 tests in 1.752s`, `OK` |
| `test_release29.py` | `Ran 39 tests in 66.675s`, `OK` |
| `test_release29_rehearsal.py` | `Ran 29 tests in 41.674s`, `OK` |
| `test_release29_workflow.py` | `Ran 15 tests in 0.133s`, `OK` |
| `test_owner_walk.py` | `Ran 40 tests in 623.625s`, `OK` |

The served Web UI and historical install and boot still need hosted proof.
This step used zero workflow dispatches. The ISO, the SquashFS and every
other temporary file from this step were removed. There are no files over
500 MB in `.work/`.

## Hosted proof after the ISO requalification (the lead, 2026-11-26)

- **Checks 5:** run 45887122194 at `2dd94cd4` PASSED: the regressions and the full ways-back model.
- **Historical baseline preflight:** run 45891398742 at `2dd94cd4`, attempt 1, PASSED in about 98 minutes with the requalified live ISO (`062c93ac…`, 9102135296 bytes). `python3 os/ci/release29_walk.py check-receipt` on its `release-29-baseline-receipt` printed `PASS recorded historical R29 baseline matches the current inputs`. The receipt artifact expires 2026-12-26 and the evidence artifact (about 22 MB) on 2026-11-29.
- **Ledger:** checks 5 of 5 and release-29-baseline 3 of 3 are spent, within the minute cap of 990. The publish caps stay 0.
- **Next:** this proves everything R29 can test before B321. The cut slice merges main (B333 `4038b149`, B343 `70364fa9` and B321 once Deskflow is stable), which changes bound baseline inputs, so the cut needs one more checks run and one more baseline preflight before the private upload. If Fedora is late, the fallback cut does the same without B321.
