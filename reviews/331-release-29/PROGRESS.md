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

1. Lead recheck of the source guard and step 2's labwc exception at the draft PR head.
2. Step 3's next slice adds candidate equality and the R29 update, recovery and boot walk
   from the confirmed R28 guest.
3. Step 4 adds the guest probes, Control and Chrome checks and the local host receipt.
4. Step 5 wires the hosted gates, runner allowlists and receipt with closed caps. The lead
   dispatches hosted checks and the read-only historical baseline preflight.
5. Step 6 takes the named main cut and the reviewed handoffs for 18c-b, B330, B329
   and B321 as applicable. The lead settles package 43 under the brief.
6. Steps 7–12 handle resolve and dry run, publish approval, release record,
   candidate tools and guides, qualifying rehearsal and the final pin.

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
download or installer asset stops the preflight until the inputs are requalified. R29
candidate equality, the update and recovery walk, and its new guest checks remain for
steps 3 and 4. Hosted workflow and ledger changes remain for step 5. Ledger use is zero
dispatches and uploads, with both R29 publish caps at zero. There are no files over
500 MB in `.work/`.
