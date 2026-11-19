# 311d: pin labwc's code even though the RPM isn't byte-reproducible

**Goal:** each build of labwc proves it contains exactly the reviewed code, although build IDs and debug data differ between builds. Briefs 311, 311b and 311c stay in force.

**Why:** three builds from the same locked inputs gave three different RPM hashes. Only `BUILDTIME`, `BUILDHOST`, header sizes and digests, three ELF sections in `labwc` and `labnag`, and the two `/usr/lib/.build-id/` paths differed. `linux-aresos` decided on 2026-11-19: accept this for R29, and pin the binaries with the varying sections removed. A fully reproducible build is an optional follow-up.

## In scope

1. **One normalizing function** in `os/labwc/stage.py`: copy a binary to a temporary file, remove exactly `.note.gnu.build-id`, `.gnu_debuglink` and `.gnu_debugdata` with `objcopy --remove-section`, and return the SHA-256 of what is left. The original binary is never changed.
2. **The pins:** `os/labwc/labwc.lock.json` records the normalized SHA-256 of `/usr/bin/labwc` and of `/usr/bin/labnag`. Check the real installed paths in the RPM's file list.
3. **The stage refuses:** after building the RPM, the `labwc` stage computes both normalized hashes from the RPM's own payload, prints them, and stops with one clear `LABWC_REFUSED` line if either differs from the lock.
4. **`check_build=resolve`** explains how the pins are renewed when the patch or the locked build environment changes, and never renews them silently during a build.
5. **Tests** in `os/tests/test_labwc_stage.py`:
   - the three sections are the only ones removed, so nothing else can hide there;
   - a binary that differs in any other section gives a different hash;
   - a binary that differs only in those three sections gives the same hash;
   - the stage's refusal fires on a wrong pin.

## Out of scope

R29's release-diff rule, which `linux-aresos` writes. Making the build fully reproducible. Everything in `reviews/311-labwc-pointer-lock/KNOWN-LIMITS.md`.

## Acceptance

1. **The pins hold across builds:** at least two separate `podman build --no-cache --target labwc` runs from the real files produce different RPM hashes and the same two normalized hashes. Record both builds' values in `PROGRESS.md`. If the normalized hashes differ between builds, stop and report which bytes differ, and do not loosen the check.
2. A wrong pin stops the build with the new line. Record the command and output.
3. `test_labwc_stage` and `test_aresos_desktop` pass.
4. `rebind.py pending` is run again if a bound file changed.
5. `PROGRESS.md`'s final section gives `linux-aresos` what R29's rule needs: the NEVRA, the file list, the two normalized hashes, and the exact sections removed.

Brief 311's limits all hold: no hosted workflows, no merge, no push to `main`, nothing on the running laptop.

**Model:** Claude Opus 5.5: a small, exact change.
