# Package 323: R29's image package: report

**What it does:** R29's image gets:
- gtk4-layer-shell 1.3.0 (x86_64), the layer library for the laptop home and the indicator (B320);
- JetBrains Mono under `/usr/share/fonts/aresos/`;
- image checks for the layer library, the font, and Mesa's EGL and Intel's Vulkan driver files;
- 18c-b's one-layer labwc swap (`6d610587`), so a committed image always keeps package 311's labwc.

Nothing reaches the laptop until R29 is released.

**Builder:** Codex `gpt-6.2-sol` `xhigh` for step 1; the lead for the one-line resolve fix and for step 2 (copying the resolved lock, plus tests). **Brief review:** Codex `gpt-6.2-sol` `high`, NOT READY on one must-fix, fixed; the targeted recheck was READY. **Code review:** a fresh Codex `gpt-6.2-sol` `high` context, SAFE (`REVIEW-1.md`). Its one should-fix, the resolve preview's architecture, was applied in `616ba704`.

## Results

- **Check build 44919908251 on `616ba704`: green.** It passed:
  - `PASS labwc is the locked rebuild (labwc-0.9.6-1.fc44.aresos1.x86_64) … rpm -V labwc is clean`;
  - `PASS gtk4-layer-shell (gtk4-layer-shell-1.3.0-1.fc44.x86_64) verifies and the laptop home loads it as ares with the preload` (`LAPTOP_HOME_LAYER_SHELL 1.3.0`);
  - the JetBrains Mono and the Mesa and Intel checks;
  - `IMAGE_CHECKS_PASSED`;
  - the VM, including both `GUARDIAN_VM_PASSED` scenarios.
- **Check build 44917067389 on `0c9df244`:** red, but only in package 25's guardian VM check. Its lid time is rounded to the millisecond and read 67 µs before `save_asked`. That's main's race, fixed by `linux-laptop-home` in PR136. All of this package's image checks passed there too.
- **Resolve runs:**
  - 44911675124 requested the library by name and so pulled the i686 build with 23 multilib dependencies; fixed in `60588a1b`.
  - 44912634031's candidate adds exactly the x86_64 library. That run went red afterwards on a passing Maven Central outage in the mod build.

## What was done

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

## What the code does not show

- A successful build of the same pinned Bazzite base had neither a `gtk4-layer-shell` nor a JetBrains Mono RPM in `image/manifest/packages.txt`. The font is installed through the existing font directory and cache rebuild. The new image check will verify fontconfig precedence on the built image. [Build evidence](https://github.com/Ares-Empire/AresOS/actions/runs/44617007417/artifacts/14577053121)
- The layer shell assertion needs Step 2's reviewed NEVRA. The hosted image build will verify the GTK import, both font hashes and the selected font, the Mesa and Intel files and libraries, and `rpm -V labwc` in the finished image.
- Package 42's source bindings contain none of the changed paths. No file in `.work/` exceeds 500 MB.

## Known limits

- The image checks prove the files are there and load. The supervisor's `LD_PRELOAD`, its vendor pins, and the layer surface on a real screen are package 23c's work, and the indicator's (B320).
- `test_release27`'s and `test_release28`'s lock tests now model release 28's recorded lock. R29's release package adds R29's own profile, with gtk4-layer-shell's reason.
