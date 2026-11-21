# 311: labwc that holds a pointer lock on layer-shell surfaces

**Goal:** the owner can share this laptop's keyboard and mouse with his Mac. This package removes the first blocker: AresOS's labwc 0.9.6 never applies a pointer lock to a layer-shell surface, so capture snaps back as soon as the mouse moves. He sees nothing new from this package alone. Packages after it add the portal backend and Deskflow.

**Why this way:** upstream fixed it in labwc 0.20.3 (commit `b7820667a2`, "allow constraints for wlr_layer_surface_v1", upstream issue #3745). `linux-aresos`, who owns `os/` and the releases, chose a rebuild of Fedora's own source package with that one patch: same file list, same build flags, smallest change to the session he uses every day.

## In scope

1. **The patch:** `os/labwc/0001-allow-constraints-for-layer-surfaces.patch`. Upstream `b7820667a2` adapted to 0.9.6. It conflicts in five places in `src/input/cursor.c`, because 0.9.6 reaches the server through `seat->server` or a `server` argument where upstream has a global `server`. The header names the upstream commit and says what was adapted. Keep upstream's logic, and change only what 0.9.6's structure requires.
2. **The lock:** `os/labwc/labwc.lock.json` holds:
   - the source package's URL and SHA-256: `https://kojipkgs.fedoraproject.org/packages/labwc/0.9.6/1.fc44/src/labwc-0.9.6-1.fc44.src.rpm`;
   - the patch's SHA-256;
   - the expected result NEVRA, `labwc-0.9.6-1.fc44.aresos1.x86_64`;
   - every build dependency by exact NEVRA and SHA-256.
3. **The build stage** in `os/Containerfile`, on the same pinned base digest as the other stages, in the style of the `mod` stage:
   - verifies the source package and the patch against the lock;
   - installs exactly the locked build dependencies and fails with one clear line on any drift, never quietly taking newer ones;
   - adds the patch and the release suffix to Fedora's spec with the smallest possible edit, so `rpm -q` shows `0.9.6-1.fc44.aresos1`;
   - outputs the RPM and nothing else.
4. **The final stage:** installs that RPM from a local file, removes Fedora's labwc, and fails if both are present or the installed NEVRA differs from the lock.
5. **Signatures:** the RPM is unsigned and `os/build.sh` installs local packages with `localpkg_gpgcheck=True`. Add one exception for exactly this NEVRA, never a general one. Check every other place that expects Fedora signatures (image checks, the audit, the release tools).
6. **`check_build=resolve`** prints a fresh resolution of the build dependencies, as it does for `packages.lock.json`.
7. **Image checks** in `os/ci/image-checks.sh`: labwc's NEVRA, and `rpm -V labwc` clean.
8. **Tests** in `os/tests/` for the lock's shape and for the refusals: wrong source hash, wrong patch hash, drifted dependency, both packages present. Each new refusal gets a test that shows it fires.

## Out of scope

- R29's release-diff rule for labwc. `linux-aresos` writes it on R29's branch.
- The portal backend, Deskflow, portal routing, the Lan Mouse unit.
- Any other labwc change or a move to labwc 0.20.x.
- Anything on the running laptop: no `rpm-ostree`, `bootc`, `sudo`, `systemctl` changes or package installs on the host. Never restart, replace or signal the owner's labwc session.
- Hosted runs. **Do not dispatch any GitHub workflow:** the R28 cut is Thursday 2026-11-19 12:00. The lead dispatches the check build after the cut.
- Merging, or pushing to `main`.

## Acceptance

Do these locally, in a rootless podman container, and record the commands and results in `reviews/311-labwc-pointer-lock/PROGRESS.md`:

1. The source package, patched, builds to `labwc-0.9.6-1.fc44.aresos1.x86_64`.
2. `rpm -qlp` of our RPM and of Fedora's `labwc-0.9.6-1.fc44.x86_64` list the same files. Compare dependencies (`rpm -qp --requires --provides`) too, and explain any difference.
3. **The fix is shown to work, and the test proves it can fail.** In a container or on a private headless Wayland socket, run labwc with `WLR_BACKENDS=headless`, and have a client take a pointer lock on a layer-shell surface and receive relative motion while the cursor stays still. The same test must fail on Fedora's unpatched build. `~/.local/opt/lan-mouse/lan-mouse test-capture` or a small test client are both acceptable. If this cannot be shown headless, say exactly why under `PLAN-GAP`, and name what the real laptop test must prove.
4. A normal window's pointer lock still works in the same test (the code path the patch changes).
5. The new `os/tests` modules pass. Run modules with `python3 -m unittest discover -s os/tests -p '<module>.py'`. Do not run `test_inherited_homebrew` or `test_sysusers`: they call `sudo -n` on the host.
6. If `os/` files bound by earlier rehearsals changed, refresh the pending list with the repo's rebind tool (`rebind.py pending`) and do not edit that file by hand.

## Already decided

- Rebuild Fedora's source package, not an upstream build (`linux-aresos`, 2026-11-18).
- Release suffix `.aresos1`.
- The brief stays on this branch until the R28 cut.
- The stage's output is the RPM only.

## If unsure

- **Build dependencies can vanish:** `os/build.sh` fetches pinned packages from Fedora's `updates` repository, which keeps only recent versions. Prefer fetching the locked build dependencies by exact URL from `kojipkgs.fedoraproject.org`, checked by SHA-256, so a later rebuild gets the same bytes. If that doesn't work, stop and report it as a `PLAN-GAP`.
- **Pulling the base image:** the pinned base is large. Do the patch, RPM and behaviour proof in a plain `fedora:44` container first. Pull the base only if resolving the locked dependencies needs it. Keep at least 4 GiB of memory free for the owner's session.
- Anything that would change what the owner sees, or the session's behaviour beyond the fix: stop and write a `JUDGMENT-CALL`.

**Model:** Claude Opus 5.5: this is a tight brief with a known fix, and a fresh reviewer follows.
