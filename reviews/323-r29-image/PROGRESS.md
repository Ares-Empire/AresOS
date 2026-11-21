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

## Left in order

1. The lead dispatches `check_build=resolve` on `pkg/323-r29-image` and shares the evidence with the Step 2 builder.
2. Compare `candidate-packages.lock.json` to the current lock. Accept only `gtk4-layer-shell`, its newly needed dependencies, and pins Fedora stopped serving. Stop for the lead if labwc, wlroots, or any package 311 labwc build pin renews. Otherwise replace the lock wholesale in the candidate's order, add its test, and record each added or renewed entry here. If the base inventory already lists `gtk4-layer-shell`, use that recorded NEVRA in the image check and omit the package request and lock entry.
3. The lead dispatches `check_build=build` after the Step 2 push and obtains the fresh code review. With a green build and a SAFE review, the lead commits the report from this note, removes this note, merges, and tells `linux-desktop` and `linux-tools` as specified in the brief.

## What the code does not show

- A successful build of the same pinned Bazzite base had neither a `gtk4-layer-shell` nor a JetBrains Mono RPM in `image/manifest/packages.txt`. The font is installed through the existing font directory and cache rebuild. The new image check will verify fontconfig precedence on the built image. [Build evidence](https://github.com/Ares-Empire/AresOS/actions/runs/44617007417/artifacts/14577053121)
- The layer shell assertion needs Step 2's reviewed NEVRA. The hosted image build will verify the GTK import, both font hashes and the selected font, the Mesa and Intel files and libraries, and `rpm -V labwc` in the finished image.
- Package 42's source bindings contain none of the changed paths. No file in `.work/` exceeds 500 MB.
