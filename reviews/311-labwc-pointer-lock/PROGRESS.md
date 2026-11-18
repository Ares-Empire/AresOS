# 311 progress: labwc that holds a pointer lock on layer-shell surfaces

**State: stopped on a PLAN-GAP.** The fix is proven, but the lock cannot be written, because the build
dependencies do not resolve on the pinned Bazzite base. The brief says to stop and report this. The branch does
not build an image until the lead decides (see PLAN-GAP 1). It must not be merged as it stands.

## Done

- `os/labwc/0001-allow-constraints-for-layer-surfaces.patch`: upstream `b7820667a2` adapted to 0.9.6. Same size as
  upstream (37 insertions, 8 deletions). The header names the commit and lists what was adapted.
- `os/labwc/stage.py`: `build`, `install` and `resolve`. Every refusal is one `LABWC_REFUSED` line.
- `os/Containerfile`: the `labwc` stage on the pinned base, and the swap in the final stage before `configure`.
- `os/ci/check-resolve.sh`: `check_build=resolve` prints a fresh resolution and a candidate lock (`labwc.txt`).
- `os/ci/image-checks.sh`: labwc's NEVRA, only one labwc, `rpm -V labwc` clean.
- `os/ci/check-image.sh`: the image's copy of the lock must equal the reviewed one.
- `os/tests/test_labwc_stage.py`: the lock's shape, every refusal, and the wiring.
- `os/tests/test_aresos_desktop.py`: the stage list and one fixture now include the new stage and lock.
- `reviews/311-labwc-pointer-lock/lock-probe/`: the headless behaviour probe.

## Left, in order

1. The lead decides PLAN-GAP 1.
2. Change the stage's `FROM` if that is the decision, and the matching line in `test_aresos_desktop.py`.
3. Run `stage.py resolve` in the chosen base with a bootstrap lock, and commit the candidate as
   `os/labwc/labwc.lock.json`. `resolve` looks for Fedora's signed copy on Koji for each package.
4. Run `podman build --target labwc`, then repeat acceptance items 1 to 4 on that RPM.
5. Build the final stage far enough to run `stage.py install` for real, including `rpm -V labwc`.
6. Run `test_labwc_stage` and `test_aresos_desktop` again: all 7 failing tests below need only the lock.
7. Run `rebind.py pending` again after the last change to a bound file.

## Acceptance

Items 1 to 4 ran in a plain `registry.fedoraproject.org/fedora:44` container
(`sha256:b02bb57e0e8ec2e057f0826436d2fc58765fa2b3b82d2abd322ece06e39c88f5`), as the brief says to do first. The
build dependencies there were Fedora's current ones, **not** a locked set, and the build was not on the pinned base.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Patched source builds to the NEVRA | PASS (fedora:44 only) | `labwc-0.9.6-1.fc44.aresos1.x86_64`, SHA-256 `4e35a3bd...f5c732` |
| 2 | Same file list and dependencies | PASS, with one explained difference | See below |
| 3 | Lock works on a layer surface, and the test can fail | PASS | Fedora's build fails, ours passes |
| 4 | A normal window's lock still works | PASS | Passes on both builds |
| 5 | New `os/tests` modules pass | **FAIL** | 41 of 47 pass, 6 errors: `labwc.lock.json` does not exist |
| 6 | Pending rebind list refreshed | PASS | `rebind.py pending`: 10 files before and after, only the note was added |
| - | The `labwc` stage and the final image | **NOT RUN** | No lock, so neither was ever built |

### Item 1

Rebuilt with the same spec edit `stage.py` makes (`%{autorelease}.aresos1` and one `Patch0` line). `rpm -qp` reports
`labwc-0.9.6-1.fc44.aresos1.x86_64`. The compiler flags (`%{OPTFLAGS}`) equal those of Fedora's build.

### Item 2

Compared with Fedora's `labwc-0.9.6-1.fc44.x86_64`, SHA-256 `9438b595...16f60b`, the same as `os/packages.lock.json`,
with Fedora's signature verified.

- **Files:** 64 in each. Identical except for the two `/usr/lib/.build-id/` entries (each a folder and a link). Those
  names are hashes of the compiled binaries, so a patched binary must differ.
- **Requires:** identical.
- **Provides:** differ only in the version of `labwc` and `labwc(x86-64)`, which is the release suffix.

### Items 3 and 4

Run: `podman run ... fedora:44 bash /probe/in-container.sh <rpm> /probe`. Each mode gets its own labwc with
`WLR_BACKENDS=headless` on a private `XDG_RUNTIME_DIR`. Full output: `evidence/probe-fedora-unpatched.txt` and
`evidence/probe-aresos1.txt`.

| Check | Fedora, layer | Ours, layer | Fedora, window | Ours, window |
|---|---|---|---|---|
| Lock activated | FAIL | PASS | PASS | PASS |
| Relative motion arrives in full | PASS | PASS | PASS | PASS |
| No absolute motion while locked | FAIL (20 events) | PASS (0) | PASS | PASS |
| Cursor stays still | FAIL (moved 200, 100) | PASS | PASS | PASS |
| Second lock activated | FAIL | PASS | PASS | PASS |
| Unlock moves the cursor to the hint | FAIL | PASS | PASS | PASS |
| Confinement activated | FAIL | PASS | PASS | PASS |
| Pointer stops at the region's edge | FAIL | PASS | PASS | PASS |
| **Exit code** | **1** | **0** | **0** | **0** |

The probe exits 2, not 1, when the compositor cannot be used, so a broken setup cannot pass as "fails on Fedora".

### Item 5

`python3 -m unittest discover -s os/tests -p 'test_labwc_stage.py'`: 47 tests, 6 errors. All 6 are in
`ReviewedLockTest`, which reads the missing lock.

Existing modules that read the changed files:

| Module | Result |
|---|---|
| `test_shell_assertions` | 9 tests, OK |
| `test_control_image` | 15 tests, OK |
| `test_checkout_sources` | 8 tests, OK |
| `test_aresos_desktop` | 189 tests. The full run predates its two test edits. Rerun of the two tests it failed: the stage list passes; `test_check_image_holds_a_release_image_to_the_reviewed_locks` still errors on the missing lock |

The full `test_aresos_desktop` module was not rerun after those edits.

## PLAN-GAP

### 1. The build dependencies do not resolve on the pinned base (blocking)

`wlroots0.19-devel` needs `pkgconfig(gbm)`, which only `mesa-libgbm-devel` provides. That package must match the
installed `mesa-libgbm`, and no source offers a match for the base's:

| Source | What it has | Why it does not work |
|---|---|---|
| Pinned base | Terra's `mesa-libgbm-1:26.2.4-1.fc44` (epoch 1) | The runtime that must be matched |
| Fedora's `fedora` and `updates` | `26.0.3-4` and `26.2.7-1` | Excluded on the base, wrong version, epoch 0 |
| Koji | `mesa-libgbm-devel-26.2.4-1.fc44` | Needs `mesa-libgbm(x86-64) = 26.2.4-1.fc44`; dnf5 refuses it against Terra's epoch 1. No signed copy under Fedora 44's key either |
| Terra | Only `1:26.2.7-1.fc44` today | Needs the same 26.2.7 runtime |

Commands and output: `evidence/base-mesa-gap.txt`.

Options for the lead (only A has been shown to work):

- **A (recommended): build the stage on a digest-pinned `fedora:44`.** Every dependency then comes from Fedora, signed
  and available on Koji, and the buildroot matches how Fedora built labwc. It departs from the brief's "same pinned
  base digest", which is why this builder did not choose it. Still to check: that the RPM runs on the base's
  libraries, since the buildroot's libraries may be newer than the base's.
- **B: replace Terra's mesa with Fedora's inside the throwaway stage.** Stays on the base, but changes both
  architectures of mesa there, and `stage.py` would have to allow replaced base packages. Not tried.
- **C: force Fedora's `mesa-libgbm-devel` 26.2.4 in with `rpm --nodeps`.** Same upstream headers, but it skips a
  dependency check and uses an unsigned file. Not tried.

### 2. R29's release-diff rule must cover more than the NEVRA (for `linux-aresos`, out of scope here)

`os/ci/release_diff.py` stops on a package outside `packages.lock.json`, so it will stop on
`labwc-0.9.6-1.fc44.aresos1.x86_64`. The rule must also accept the new `usr/share/aresos/manifest/labwc.lock.json`.

## JUDGMENT-CALL

None. Nothing here changes what the owner sees, and no owner-facing choice was made.

## What the code does not show

- The source package URL in the brief is Koji's unsigned copy. Its contents (`labwc.spec`, `labwc-0.9.6.tar.gz`) are
  byte-identical to Fedora's signed copy, whose signature was verified with the Fedora 44 key.
- Koji's top-level `x86_64/` copies are unsigned and have different hashes from the repository's. `stage.py resolve`
  therefore uses `data/signed/<key>/`, whose labwc copy has the same SHA-256 as `os/packages.lock.json`.
- The probe's lock request comes after the layer surface has focus, which is the path that fails on 0.9.6.
- Not tested: real hardware, Lan Mouse's `test-capture`, or labwc on the pinned base.
- The pinned base image (about 5.6 GB compressed) and `fedora:44` remain in rootless podman storage for the next step.
