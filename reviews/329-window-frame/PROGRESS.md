# 329: progress

Step 1 of 2, 2026-11-21. Branch `pkg/329-window-frame` started at `f91aad16`, the merge base with `origin/main` at the start of this step.

## Done

- `1d676c9a` adds the 36 frame cells and role colours to the Look A pack. `make_pack.py` uses the study's art and its Jersey 10 pin. `make_labwc_theme.py` reads the pack and writes the committed `themerc` and 36 nearest-neighbour PNGs.
- `abf1fde2` selects `AresOS`, sets all five Jersey 10 fonts, configures Alt+Tab and Shift+Alt+Tab, and clears the two title-bar scrolls. The fixtures pin the historical release-diff rows and the unit test checks the five settings in the live XML.
- `ed203ac1` updates the pack's file list and digest and checks the new theme and XML in the image. The existing Crown pin still matches the Crown files.
- `6cf4ac64` documents the shipped frame, corrected Jersey 10 scale and A-first build order.

### Verified

The six modules below were run one at a time with `python3 -m unittest discover -s os/tests -p <file>`, with bytecode writes disabled and temporary test files under `.work/`.

| Module | Tests | Result |
|---|---:|---|
| `test_aresos_look_pack.py` | 1 | OK |
| `test_aresos_labwc_theme.py` | 3 | OK |
| `test_aresos_labwc_rc.py` | 2 | OK |
| `test_everyday_account.py` | 34 | OK |
| `test_aresos_desktop.py` | 189 | OK, 1 skipped |
| `test_shell_assertions.py` | 9 | OK |

The total was 238 tests, with 237 passing and one skipped. `test_everyday_account.py` printed Python 3.14's `load_module()` deprecation warning. `test_aresos_desktop.py` printed the stand-in's “lost the supervisor” messages and skipped the case that needs a reachable user systemd manager. `bash -n os/ci/image-checks.sh` and `git diff --check` passed. The package 320 and 329 Python image checks passed when run against `os/config/usr/share` in the checkout. `release_diff.crown_pin()` found the one Crown pin and `crown_digest()` matched it. The pack's former indicator PNGs, the indicator program, Crown assets, `release_diff.py` and `test_release28.py` match the base.

The full image build runs in GitHub Actions. The compositor and on-panel checks remain open. There are no `__pycache__` directories under `os/config` and no files over 500 MB in `.work/`.

## Left, in order

1. Refresh `origin/main` at the start of step 2. If B321 has landed with green recovery assertions, use its XML as the baseline and preserve both recovery chords and their action order. Use the exact XML in B321's progress log under “For step 3”.
2. Extend `wl-harness window` and add `frame` to the isolated 320 harness. Install the actual branch and merge-base theme and font in their respective private runs. Use the labwc build pinned by the branch's lock. Record the merge base and confirm the compositor starts without theme errors.
3. Run the frame checks in brief order and save the captures and review sheets in `evidence/`. Check all 36 images at 1:1 via the normal and toggle layouts. Stop and report if the bar differs from 40 px. Include the drag, snap, resize, shade, focus and pointer-lock comparisons against the baseline, as well as the B and C fallback and the built-in root menu rows.
4. Rerun 320's nine harness checks and run the full hosted OS regression suite with `checks_only=true`. Write `KNOWN-LIMITS.md` and `REPORT.md`, including the relevant open checks from COMPONENTS.md 4.2 and section 8.
5. Verify the public and private hashes again before pushing. Dispatch `os-image.yml` with `check_build=build` on step 2's final head and verify that head is green. Record the run in the draft PR for the fresh review and R29 handoff.

## What the code doesn't show

- The install path contains the prebuilt theme. The generator's `--output` is the `labwc` directory itself. To reproduce in scratch, run `python3 -B os/look/make_pack.py --output <pack>` and `python3 -B os/look/make_labwc_theme.py --pack <pack> --output <theme-dir>`. The pinned bytes are the checked-in files. The regeneration tests compare PNG modes, sizes and pixels so they also work across Pillow and zlib versions.
- The `a9863055` `rc.xml` used for the historical fixture was byte-identical to the branch's `f91aad16` starting XML. The headless comparison uses the actual merge base at step 2, including Crown's Space Grotesk geometry if Crown is still selected there.
- The live look falls back to A in all three settings. The B and C sync package owns live reconfigure. The overview owns Super+Tab and the cover filters. Step 2 still needs labwc evidence for the menu row sizes, title antialiasing and ellipsis, and the world's frame, stacking and pointer lock.

## For linux-aresos

| File | Commit | Review |
|---|---|---|
| `os/config/usr/share/aresos/labwc/rc.xml` | `abf1fde2` | Selects `AresOS`, configures the switcher and adds Shift+Alt+Tab and the two title-bar scroll overrides. |
| `os/ci/image-checks.sh` | `ed203ac1` | Pins the expanded pack and new theme, checks the frame settings and keeps the Crown pin for R28. |

The R29 release profile belongs to `linux-aresos`. The image adds 37 theme files and 36 pack cells and changes `look.json`. The `rc_xml_settings` delta replaces `theme` and `windowSwitcher`, adds `A-S-Tab`, and adds two `mouse` rows. Keep Crown's files and Space Grotesk for R28's checks and the startup cover, respectively. The R29 guest walk should expect the `AresOS` theme.

## The public and private check

Before the first push, checked the SHA-256 of 86 committed file versions across all five outgoing commits, including this log. Zero matches. All 72 PNG paths were verified against the public Look A study, as native 24 × 20 cells or their exact 48 × 40 enlargements. The lead-provided hashes stayed in ignored scratch and were compared in memory.
