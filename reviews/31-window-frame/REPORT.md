# Package 31: Ares-Crown window frame

## Every OS file touched

Relative to the supplied worktree commit `03624a37`: `M` modified, `A` added, `D` deleted.
`K` lists the design's 37 Crown files kept byte for byte (new in the PR against main).
There are no other OS changes. The deleted alternatives are still in the design commit and its pictures.

```text
M	os/build.sh
M	os/ci/image-checks.sh
M	os/config/usr/share/aresos/labwc/rc.xml
A	os/config/usr/share/fonts/aresos/OFL-SpaceGrotesk.txt
A	os/config/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf
A	os/config/usr/share/glib-2.0/schemas/zz-aresos.gschema.override
D	os/config/usr/share/themes/Ares-Block/labwc/close-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/close-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/close_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/close_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk_toggled-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk_toggled-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk_toggled_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/desk_toggled_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/iconify-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/iconify-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/iconify_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/iconify_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max_toggled-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max_toggled-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max_toggled_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/max_toggled_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/menu-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/menu-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/menu_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/menu_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade_toggled-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade_toggled-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade_toggled_hover-active.svg
D	os/config/usr/share/themes/Ares-Block/labwc/shade_toggled_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Block/labwc/themerc
D	os/config/usr/share/themes/Ares-Plain/labwc/close-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/close-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/close_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/close_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk_toggled-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk_toggled-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk_toggled_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/desk_toggled_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/iconify-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/iconify-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/iconify_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/iconify_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max_toggled-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max_toggled-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max_toggled_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/max_toggled_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/menu-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/menu-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/menu_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/menu_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade_toggled-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade_toggled-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade_toggled_hover-active.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/shade_toggled_hover-inactive.svg
D	os/config/usr/share/themes/Ares-Plain/labwc/themerc
A	os/tests/test_window_frame.py
K	os/config/usr/share/themes/Ares-Crown/labwc/close-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/close-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/close_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/close_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk_toggled-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk_toggled-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk_toggled_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/desk_toggled_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/iconify-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/iconify-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/iconify_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/iconify_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max_toggled-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max_toggled-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max_toggled_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/max_toggled_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/menu-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/menu-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/menu_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/menu_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade_toggled-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade_toggled-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade_toggled_hover-active.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/shade_toggled_hover-inactive.svg
K	os/config/usr/share/themes/Ares-Crown/labwc/themerc
```

## Done

- Kept Ares-Crown exactly as designed; removed the 37 files in each of Ares-Plain and Ares-Block.
  Cut the button generator down to Crown; all 36 generated SVGs reproduce the shipped bytes.
- Replaced only the theme element in `rc.xml` and added thumbnail Alt+Tab. Everything outside those two
  elements is byte-identical to the supplied configuration, including package 23's rules and recovery binding.
- Bundled the unchanged Space Grotesk font and licence from the authorized read-only source. The font is
  136,676 bytes and has SHA-256 `acad6de1fc93436f5c0f1f4137751ef04f1aea3063e7036535970ffcfbd79f72`.
  `.gitattributes` preserves the licence's upstream CRLF bytes; README records its copyright and SIL OFL 1.1.
- Added `zz-aresos.gschema.override`, scoped to `org.gnome.desktop.wm.preferences:AresOS`. It works here;
  no unscoped fallback was needed. `build.sh configure`, after the Containerfile copies config, runs
  `glib-compile-schemas --strict`; compilation errors fail the image build. No dconf setting is written.
- Added one independent package-31 block to image checks: themerc, every glyph/focus/hover state (36 SVGs),
  font checksum, licence, selected theme, layout, thumbnail switcher, override and its compiled AresOS value as `ares`.
  Added a regression test that compiles the actual override and checks AresOS, GNOME and an unset desktop.
- Chrome keeps its own bar. No preference, policy or window rule was added. The desktop-scoped default also
  gives GTK header-bar programs all three buttons without changing their own frames.
- Updated `WINDOWS.md` with the owner's dated decision, the shipped configuration, the unchosen alternatives,
  and the remaining real-panel size/dark-app questions. Added reproducible, isolated screenshot helpers here.

**Release handoff:** `gschemas.compiled` changes in the image. The next release's image diff needs a rule for it,
which the OS lead writes. `os/ci/release_diff.py` was not edited. STATE, HANDOFF, CLAUDE and install docs were not edited.

## Verified

### Local checks

- `python3 -m unittest discover -s os/tests -p test_window_frame.py -v`: **1 test, OK**. The compiled override
  gives `'appmenu:minimize,maximize,close'` only for AresOS, and `'appmenu:close'` for GNOME and an unset desktop.
- `python3 -m unittest discover -s os/tests -p test_everyday_account.py -v`: **34 tests, OK** (0.157 s).
  That test file is unchanged.
- `bash -n os/build.sh os/ci/image-checks.sh`: exit 0, no output.
- `python3 -m py_compile reviews/31-window-frame/*.py`: exit 0, no output.
- Python comparisons against the supplied files printed
  `UNCHANGED_BINDINGS_AND_RULES; EVERYDAY_TEST_UNCHANGED; 36_CROWN_BUTTONS_REPRODUCED`.
  Comparing both committed font files with their upstream bytes printed `FONT_AND_LICENCE_BYTES_UNCHANGED_IN_GIT`.
- `git diff --check`: exit 0, no output. The screenshot harness's two internal entry points also refused the real runtime before issuing any display command (`OWNER_DISPLAY_REFUSAL_PASSED`).
- `python3 -m unittest discover -s os/tests -v`: **1,096 tests in 828.365 s; FAILED
  (failures=101, errors=23, skipped=1)**. This is not a green local suite. Existing failures include unavailable
  passwordless sudo for Homebrew fixtures, Python 3.14 `Path.glob` monkeypatch incompatibilities (`case_sensitive`),
  and owner-update fixtures expecting the Ubuntu runner's missing `rpm-ostree` rather than this AresOS installation.
  The suite's `sudo -n` attempts were refused; no admin action succeeded. Tests were not modified or skipped to pass.
- The `-B` run of the full suite was **stopped by the orchestrator** part-way (2026-11-13 21:35) and is not counted. The OS lead's rule, which reached this package after its brief was written: the full `os/tests` suite is never run natively on the laptop, because `test_owner_update` starts the real owner tools' entry on the owner's running system and leaves stand-in processes behind. The plain run above did that once; its numbers are exactly the known native baseline (failures in `test_owner_update`, in tests written against Python 3.12's pathlib, and in tests that need root; nothing from this package). One stand-in it left (`sleep 3600`) was ended by its PID. The full count comes from the hosted runs below.
- Mod regression results and hosted check results will be recorded after completion.

### Headless windows and recovery

`python3 reviews/31-window-frame/capture.py` completed all three cases with exit 0 and printed
`CAPTURE_PASSED=normal`, `CAPTURE_PASSED=no-theme`, `CAPTURE_PASSED=no-font`.
The normal case was then rerun with interpolated pointer drags to show both windows' sample text completely;
`python3 reviews/31-window-frame/capture.py normal` exited 0. Every final picture was opened and inspected.

The harness uses the worktree's real `aresos-session`, keyboard helper, rc.xml, recovery terminal and bashrc,
with executable permissions applied as in `build.sh`. A private bwrap PID/network namespace, private D-Bus,
home/config/cache/fontconfig/runtime directories and `WLR_BACKENDS=headless`, `WLR_RENDERER=pixman` keep it off the
owner's session. `/run/user/1001` is hidden in the namespace; no owner profile or display is used. Only autostart
is replaced, to launch test programs instead of the real desktop. All children die with the held namespace process.
`wlr-randr` sets `HEADLESS-1` to 1920x1080; `grim` captures that output on its private Wayland display.

Before each case the harness printed `free -g` (at least 4 GB available) and checked `/proc/*/exe` for the owner's
Lunar Java; no such game was running. The full suites received the same preflight checks. No force override was used.

Inside each session, as user `ares`, `XDG_CURRENT_DESKTOP=AresOS gsettings get
org.gnome.desktop.wm.preferences button-layout` printed `'appmenu:minimize,maximize,close'` from the scratch compiled
schemas, using the memory backend to query the default without saved dconf values. `fc-match` printed
`Space Grotesk,Space Grotesk Light` in normal/no-theme cases and `Adwaita Mono` in no-font.

| Picture (all 1920x1080) | Inspected result |
|---|---|
| [01-frame.png](01-frame.png) | Active foot: gold dot, bright Space Grotesk title, all three buttons; inactive KWrite: ring and dim title. Both show only sample text. |
| [02-alt-tab.png](02-alt-tab.png) | Actual window thumbnails, gold chosen entry and preview outline. |
| [03-chrome.png](03-chrome.png) | Fresh throwaway profile, local sample page; minimize/maximize/close inside Chrome's own tab bar, no second bar. |
| [04-gtk-header.png](04-gtk-header.png) | GTK4 sample's own header bar has all three buttons; no compositor title bar. |
| [05-no-theme-recovery.png](05-no-theme-recovery.png) | Theme folder absent: usable grey fallback frame; unchanged Super+Ctrl+Escape launched the real recovery command; typed `echo recovered` printed `recovered`. |
| [06-no-font-recovery.png](06-no-font-recovery.png) | Font absent: Crown stays usable with readable fallback title; same real shortcut/command and shell proof. |

Labwc stayed up and usable in both fallback cases; it did not cost the session. Benign isolated-session log messages
include unavailable portal/FUSE/PipeWire services and disconnects while the test namespace shuts down; neither fallback
crashed. The first harness attempts exposed fixture permissions/device mounts and Wayland object-ID ordering errors;
these were corrected only in the test harness. No production setting was changed to obtain the pictures.

Installed versions tested: labwc 0.9.6, foot 1.27.0, KWrite 26.08.1, Chrome 157.0.8103.50,
GLib 2.88.4, GTK4 4.22.5; Python 3.14.8.

### Hosted verification

After pushing, dispatch the brief's `OS image` check build with `check_build=build` and wait with one blocking
`gh run watch --exit-status`. The result, URL and exact tested commit will be recorded here. Also dispatch the existing
`checks_only=true` workflow to run the unchanged regression suite on its supported disposable Ubuntu runner.

## Not verified

- Size, legibility and the real Minecraft background on the laptop's own panel: intentionally never opened there.
- Discord and the Lunar Client launcher themselves; they draw their own windows. Neither was started or inspected.
- Flatpak sandbox variants of header-bar applications; the GTK4 sample here is native.
- The complete local OS suite cannot currently be called green under the laptop restrictions; see the exact results above.

**Try this after the reviewed release:** open Terminal and Notepad together; check the gold dot follows focus and titles
are readable. Hold Alt+Tab and check the previews. Open Chrome and a GTK header-bar app: each should have three buttons
at the right, and Chrome should have only its own tab bar. Try minimize/maximize/restore/close and Super+Ctrl+Escape.
Then try Discord and the Lunar launcher and report any awkward size or missing buttons. No manual setting is needed.

## JUDGMENT-CALL

None. Theme, dimensions, font, thumbnail switching and Chrome's own bar were already decided. Desktop scoping was
verified and retained as the brief's preferred reversible option; changing it later is a one-section override edit.

## PLAN-GAP

- The local full-suite acceptance assumes a disposable Ubuntu host with passwordless sudo and older Python, while this
  run requires unprivileged AresOS with Python 3.14 and installed OS commands. Preserve the tests and run their existing
  hosted regression workflow; a local no-admin test harness is a separate package. No test was weakened here.

## Open questions

Only the two design follow-ups: title size on the real panel and whether other programs should prefer dark mode later.
The OS lead must add the compiled-schema image-diff rule before the next release.

## Cleanup

All screenshot-session processes were stopped by their held namespace PIDs, never by process name. Final build-process
cleanup and the inventory of `.work/` files over 500 MB will be recorded before closing.

## After the hosted runs (orchestrator, 2026-11-13)

- The check build with VM on `fe6db50f` passed (run 43501555136).
- The hosted regressions on `fe6db50f` failed in one test, `test_checkout_sources`: "Checkout source binding mismatch: .gitattributes". The builder had added a line to the root `.gitattributes` to keep the font licence's CRLF line ends, and that file is bound by the rehearsal records. The line is taken out again and the licence is stored with LF line ends like every other text file; its words are unchanged, and nothing checks its bytes (the image check reads its copyright line and its title). The font file itself is untouched and still matches its checksum. "FONT_AND_LICENCE_BYTES_UNCHANGED_IN_GIT" above therefore holds for the font only.
- `main` is merged in; the hosted regressions and the check build are run again on the new head, and their results are in the pull request.
