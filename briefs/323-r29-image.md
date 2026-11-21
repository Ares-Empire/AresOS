# 323: R29's image package: the layer library, JetBrains Mono, the Mesa and Intel checks, the one-layer labwc swap

Board brief 323. Lead: `linux-aresos`. It lands on main before R29's release package and before the indicator (B320, draft PR131), which needs the layer library. Agreed with `linux-laptop-home` on 2026-11-18 (STATE.md, package 23c's notes; `docs/design/LAPTOP-HOME.md` sections 4 and 9).

**Builder:** Codex `gpt-6.2-sol` `xhigh`, in two steps (below): a small, exactly specified image change, which is the workhorse's job. **Brief review:** one Codex `gpt-6.2-sol` `high` review, with no Claude review because the Claude week is tight (the brief-review rule). **Code review:** a fresh Codex `gpt-6.2-sol` `high` context. **Bar (decision 24):** "reasonably safe". Must-fix means real harm or a sure failure in the build, the image checks or the VM. Low-harm edge cases go to the report's Known limits.

## What changes

1. **The labwc swap in one layer.** Take `linux-tools`' commit `6d610587` from `pkg/18c-b-chrome` (PR76) unchanged with `git cherry-pick -x`. It applies cleanly to main. Its four files are `os/Containerfile`, `os/labwc/stage.py`, `os/tests/test_aresos_desktop.py` and `os/tests/test_labwc_stage.py`.
   - **What it does:** the `packages` stage now comes after the labwc build stage, so Fedora's labwc install and package 311's verified swap run in one `RUN`.
   - **Why:**
     - With the swap in a later layer, the committed image once kept Fedora's `/usr/bin/labwc` under 311's package record. That was control run 44888933298, where `rpm -V labwc` printed `..5......`. Both binaries have the same size, mode and time, so a metadata-only layer diff can miss the replacement.
     - Two other builds with the same layout were clean (44617007417, 44895737105). The image checks stop such an image, so the cost is a failed build, not a wrong labwc.
   - **If PR76 is already on main** when you start, skip this item and say so in PROGRESS.md.
2. **gtk4-layer-shell in the image.** Fedora 44's `gtk4-layer-shell` is pinned in `os/packages.lock.json` like every other added package (NEVRA and SHA-256). It also comes with its GObject typelib `Gtk4LayerShell-1.0`, which `load_gui()` in `os/config/usr/libexec/aresos-laptop-home` imports.
   - Step 1 adds it to `os/ci/check-resolve.sh`'s transaction preview and its `available` query. The lead then dispatches `check_build=resolve`, and step 2 takes its NEVRA and SHA-256 from that run's candidate lock.
   - Take only gtk4-layer-shell's entry, plus any pin the candidate renewed because Fedora no longer serves it. Name each renewed pin in PROGRESS.md.
   - If the pinned base already has gtk4-layer-shell, add no lock entry, say so, and keep the checks of item 4.
   - Install no other package. If it pulls in a dependency the base lacks, list it in PROGRESS.md and lock it the same way.
3. **JetBrains Mono.** Copy `reviews/44-laptop-home/prototypes/shared/fonts/JetBrainsMono-Variable.ttf` and `OFL-JetBrainsMono.txt` byte for byte to `os/config/usr/share/fonts/aresos/`, next to Space Grotesk (package 31). Their SHA-256 values are:
   - `48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda` for the font;
   - `b2fe5e8987594e9ffd1d2ca52a2f5d73eb8335243893c5d6254b5ad69269591d` for the licence.

   **If the base already has a JetBrains Mono** that fontconfig prefers for `JetBrains Mono`, report it. Make ours the one `fc-match` returns as `ares`, in the simplest way that keeps every other font choice unchanged.
4. **Image checks** in `os/ci/image-checks.sh`, next to package 53f's laptop home check. Each ends in a `pass` line, as its neighbours do:
   - **gtk4-layer-shell:**
     - `rpm -q` gives the locked NEVRA, and `rpm -V` is clean.
     - `/usr/lib64/libgtk4-layer-shell.so.0` exists.
     - As `ares`, with `LD_PRELOAD` set to that library and the environment otherwise like the 53f check's, the program's own `load_gui()` returns a `layer` that is not `None`. Print its version.
     - 53f's existing check, which runs without the preload, still passes unchanged.
   - **JetBrains Mono:** the two files have the pinned SHA-256 values. As `ares`, `fc-match --format '%{file}' 'JetBrains Mono'` gives `/usr/share/fonts/aresos/JetBrainsMono-Variable.ttf`, like the Space Grotesk check at about line 735.
   - **Mesa and Intel:** `/usr/share/glvnd/egl_vendor.d/50_mesa.json` and `/usr/share/vulkan/icd.d/intel_icd.x86_64.json` are regular files owned by a package (`rpm -qf`). Each parses as JSON, and the library its `library_path` names exists in the image. These are the files the supervisor will name in `__EGL_VENDOR_LIBRARY_FILENAMES` and `VK_DRIVER_FILES` (package 23c). This package only proves they are there.
5. **Tests.** Add or extend the static tests that pin `image-checks.sh` and `os/config` in the way the repo already does, including the two font hashes. Run the affected `os/tests` modules and say which you ran. Don't run the full suite: the laptop runs one at a time, and the lead runs it.

## Not in this package

- The supervisor's `LD_PRELOAD`, vendor pins and view token, which are package 23c's.
- `rc.xml`.
- `release_diff.py`'s reasons and R29's release profile, which belong to R29's release package.
- Any guide or owner text.
- Nothing under `os/owner-tools/`, `os/release/` or `docs/`.
- None of the files this package changes is bound in `os/manifest/ci/42/source-bindings.json`. If a test says otherwise, record it with `reviews/27-first-update-release/rebind.py pending "<note>"` and say so.

## Steps

- **Step 1:**
  - Items 1, 3, 4 and 5, and item 2's resolve list.
  - Branch `pkg/323-r29-image` (this brief is its first commit). Commit, push, and open a draft PR into main.
  - Keep `reviews/323-r29-image/PROGRESS.md`: what's done, what's left in order, and what the code doesn't show.
  - Then stop. The lead dispatches `check_build=resolve`.
- **Step 2 (a fresh run):**
  - Item 2's lock entry from that run's candidate lock, plus its test.
  - Push and stop. The lead dispatches `check_build=build`, whose image checks are this package's proof.
- **Last:** after the review is SAFE and the build is green, the lead commits the report from PROGRESS.md, deletes PROGRESS.md and merges. Then it tells `linux-desktop` that B320 can rebase, and tells `linux-tools` that the labwc fix is on main.

AGENTS.md's rules apply. In anything committed, write "the owner", never a name.
