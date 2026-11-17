# Step 3, round 2: fixes for REVIEW-6 (2026-11-17)

Head: `5c9d5f015a29354301b661802579f5e1871c69e9`. Changes are left uncommitted for the lead.
Read REVIEW-4.md, FIXES-4.md, REVIEW-6.md, the package brief and the design. No owner-tools code,
PROGRESS.md or package 27 rebind tables changed. No push, workflow dispatch, VM, privilege escalation,
system deployment command or real game-data operation was performed.

## Done / regressions

1. **Real instance layout.** `os/ci/release28_walk.py:92` requires instance-root `patches` and `libraries`,
   `minecraft/mods` and `minecraft/saves`. The probe verifies each is a symlink with exactly the provisioner's
   target text (`:391`); the daily-user reader verifies it independently (`:424`). The fixture imports the real
   `os/config/usr/libexec/aresos-desktop` and calls its `Paths` and `expected_links()` rather than copying the
   layout (`os/tests/test_owner_walk.py:547`). The host receipt now binds that newly read source
   (`reviews/42-release-28/walk-host.py:26`).
   `HomeProbeTest.test_real_provisioner_links_are_required_at_their_actual_locations` runs the submitted
   probe against that fixture, asserts the actual layout, and removes each required link in turn.
   `test_changed_link_text_stops_even_when_the_new_target_is_accessible` rejects a misdirected link.
   These tests are in `os/tests/test_release28_rehearsal.py:507`.

2. **R27 rollback.** The daily-user reader always checks link text and all home-backed data, but only R28
   checks the image-backed targets (`os/ci/release28_walk.py:429`). The previous-27 call explicitly supplies
   `image_targets=False` (`os/ci/release28_walk.py:711`); the initial and final R28 calls retain the default requirement.
   `Release28Session.boot()` physically moves the entire model image share out of its mounted location on
   R27 and restores it on R28, without changing any home links or data (`os/tests/test_owner_walk.py:561`).
   `HomeProbeTest.test_rollback_preserves_link_text_and_worlds_without_r28_image_targets` proves an unchanged
   home passes with all three image targets absent on R27. `test_image_targets_are_required_again_after_forward`
   removes each restored target and requires a STOP (`os/tests/test_release28_rehearsal.py:531`).
   The complete local walk also asserts the targets are absent on both R27 boots and present on both R28 boots
   (`:629`). Requiring image targets on rollback would fail these success cases.

3. **Saved worlds.** The VM's first R28 home probe plants `Release28Rehearsal/level.dat` (gzip NBT-like bytes)
   and `region/r.0.0.mca` (8 KiB header plus synthetic payload) through `minecraft/saves`; files and created
   directories are explicitly owned by UID/GID 1001 (`os/ci/release28_walk.py:98`, `:395`). An existing world
   with that name stops the probe instead of being overwritten. The resolved saves directory is snapshotted,
   including SHA-256, UID/GID, permissions, entry type and symlink text (`:363`, `:415`). The same snapshot
   runs as ares, opening files and checking directory/file access, and must equal root's snapshot (`:436`,
   `:530`). Both rollback and forward compare the saved-world snapshot without Prism's mutable-file exemptions
   (`:537`); timestamps remain outside the snapshot, as in the existing instance checks.
   `HomeProbeTest.test_saved_world_contains_owned_level_and_region_data_through_saves` checks the seeded files.
   `test_world_deletion_corruption_and_denial_stop_on_either_boot` deletes, corrupts, denies access, changes owner,
   and changes readable permissions for each file on each return boot (`os/tests/test_release28_rehearsal.py:555`).
   The complete route also injects deletion, region corruption and directory access denial, each requiring STOP
   (`os/tests/test_owner_walk.py:703`, `:1275`).

## Verification

Before running the owner module, and before receipt generation and modules which exercise its local model,
the worktree-local preflight runs exactly:

```text
pgrep -a -u ares -x ksshaskpass
pgrep -af 'AresOS owner tools'
```

Both printed nothing; the script printed `Owner-tools preflight: no matches`. Running the commands from a
script avoids matching the sandbox's own wrapper command text. No owner module started on a busy result.

Receipt regeneration, after the final bound source edits:

```text
PYTHONDONTWRITEBYTECODE=1 python3 reviews/42-release-28/walk-host.py
PASS package 42 host walk (release-28): 268 sources; no VM started
```

Tests run separately, one module at a time, from the worktree root:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'
```

| Module | Result printed |
| --- | --- |
| test_release28_rehearsal | Ran 44 tests in 36.651s; OK |
| test_owner_walk | Ran 34 tests in 359.402s; OK |
| test_tools_local_wiring | Ran 42 tests in 63.802s; OK |
| test_release28 | Ran 75 tests in 23.731s; OK |
| test_ways_back_probe | Ran 57 tests in 154.833s; FAILED (failures=2) |

The two ways-back failures are the `reorder-probe` and `ways-back` subcases of
`RunnerTest.test_the_probe_reads_package_22cs_host_walk_and_refuses_a_stale_one`, both at the unchanged
`os/ci/owner_vm.py:2322` assertion, `Host walk is stale`. A read-only reconstruction of that test's effective
receipt (active source tables, overlaid with `os/manifest/ci/16/pending-rebind.json`) identifies exactly one
stale path: `os/tests/test_owner_walk.py`, changed in this round. The lead must refresh that pending hash after
merging and rerun the module. No pending list or historical receipt was changed, and no test was bypassed.

The tools-local wiring module also emitted Git's default-branch hints and its temporary origin's
`remote HEAD refers to nonexistent ref, unable to checkout` warning; the module completed OK.

An earlier development invocation of test_release28_rehearsal also printed `Ran 44 tests in 38.601s; OK`,
before adding the provisioner source to the receipt's bound files.

A separate read-only receipt check printed `PASS receipt: 268 source hashes match; Control False; 8 boots`.
The regenerated receipt retains 176 checks, 822 commands and 542 typed blocks. `git diff --check` passed
with no output. `git diff --exit-code -- os/owner-tools/ reviews/42-release-28/PROGRESS.md
os/manifest/ci/16/pending-rebind.json reviews/27-first-update-release/rebind.py` passed with no output.
The closing `find .work -type f -size +500000000c` printed nothing: no files over 500 MB remain there.

## Not verified / design

No VM or actual Minecraft session ran. The remaining permitted VM rehearsal must prove the real boot round trip,
daily-user permissions and image payload restoration. The synthetic save is a persistence fixture, not proof
Minecraft can load a world or the representative apps configuration. The real laptop's home and game data were
never used. No mod/client or hosted suite ran. Control qualification remains the previously documented step 2
work; this round does not alter it.

No new owner-facing design choice or brief change; no unresolved finding from this round.
