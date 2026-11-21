# Package 323 progress

## Done

- PR 76 was open at the start. Cherry-picked `6d610587` as `726bda0a` with its patch unchanged. Fedora's labwc install and the verified package 311 swap now share one `RUN` in the `packages` stage. Both patch IDs are `6ec194e65799ba7b4c5b4180fa7ec2fb7900ff79`.
- `check-resolve.sh` records `gtk4-layer-shell` in the base inventory, includes it in the transaction preview and available query, and requests it for the candidate lock.
- Copied JetBrains Mono and its OFL licence from package 44 into `os/config/usr/share/fonts/aresos/`. The image checks both hashes and the everyday account's fontconfig match.
- The image checks compare the installed layer shell to the package lock, verify its RPM, and load it through laptop home's `load_gui()` under preload. The existing 53f check still runs without preload. The Mesa EGL and Intel Vulkan checks verify package ownership, JSON and the presence of their referenced libraries. Sonames resolve through x86-64 cache entries.
- Added `tests.test_r29_image` for the resolve wiring, font pins, layer shell check and driver manifests. The cherry-pick also updates the desktop and labwc tests for the new stage layout.

## Verified

The unittest commands ran one at a time from `os/` under bubblewrap with private `/run` and `/tmp`, a worktree-local `HOME` and `TMPDIR`, and no inherited session environment. The desktop module skipped its real systemd user-scope test because the sandbox has no user bus.

| Command | Result |
| --- | --- |
| `python3 -m unittest tests.test_r29_image` | `Ran 8 tests in 0.005s`, `OK` |
| `python3 -m unittest tests.test_labwc_stage` | `Ran 126 tests in 11.479s`, `OK` |
| `python3 -m unittest tests.test_aresos_desktop` | `Ran 189 tests in 203.317s`, `OK (skipped=1)` |
| `bash -n os/ci/check-resolve.sh` and `bash -n os/ci/image-checks.sh` | Each exited 0 |
| `cmp` and `sha256sum` for the copied font and licence | Both copies match byte for byte and both hashes match the brief |
| Compare the existing 53f check with `6bf34255` | Byte-for-byte match |

## Step 2 (the lead, 2026-11-21)

- The first resolve (44911675124, `fb99517e`) requested `gtk4-layer-shell` by name. dnf then also downloaded the i686 build and 23 multilib dependencies, such as i686 GTK 4 and GStreamer, and it would have moved x86_64 GStreamer. `60588a1b` requests `gtk4-layer-shell.x86_64` only.
- The second resolve (44912634031, `60588a1b`) produced a candidate that differs from the lock by exactly `gtk4-layer-shell-1.3.0-1.fc44.x86_64`. Nothing was renewed, and labwc and wlroots are unchanged.
  - The run went red later, in the mod jar build: Gradle found no `org.cadixdev` POMs on Maven Central for a moment, and they were served again minutes later. The candidate's download had already exited 0.
  - The candidate is kept in `runs/resolve-44912634031/`. `os/packages.lock.json` equals it, in its order, written in the lock's one-row-per-line layout.
- `tests.test_r29_image` pins that: the lock equals the candidate, and the only layer-shell row is the x86_64 one.
- Three release tests read the working tree's lock as if it were R28's, and broke on a package R28 never had. They now read R28's lock through the blob its record names (`test_release27.released`):
  - `test_release27` PackageDiffTest, which was written against R28's lock and so holds package 23's Java;
  - `test_release28` PackageDiff28Test;
  - `test_release28` MainSmokeTest, which also serves that lock to `release_diff` in place of the working tree's.
- Tests run from the repository root as CI runs them (`unittest discover -s os/tests -p <module>`):
  - OK: `test_r29_image`, `test_release27`, `test_release28`, and 17 other modules that read the lock, Containerfile, image checks, fonts or resolve.
  - `test_owner_update` fails its 170 laptop-environment subtests, as on main.
  - `test_ways_back_model` was stopped by the lead's 15-minute timeout. This package changes none of its sources.

## Left in order

1. (Done, above.)
2. (Done, above.)
3. The lead dispatches `check_build=build` after the Step 2 push and obtains the fresh code review. With a green build and a SAFE review, the lead commits the report from this note, removes this note, merges, and tells `linux-desktop` and `linux-tools` as specified in the brief.

## What the code does not show

- A successful build of the same pinned Bazzite base had neither a `gtk4-layer-shell` nor a JetBrains Mono RPM in `image/manifest/packages.txt`. The font is installed through the existing font directory and cache rebuild. The new image check will verify fontconfig precedence on the built image. [Build evidence](https://github.com/Ares-Empire/AresOS/actions/runs/44617007417/artifacts/14577053121)
- The layer shell assertion needs Step 2's reviewed NEVRA. The hosted image build will verify the GTK import, both font hashes and the selected font, the Mesa and Intel files and libraries, and `rpm -V labwc` in the finished image.
- Package 42's source bindings contain none of the changed paths. No file in `.work/` exceeds 500 MB.
