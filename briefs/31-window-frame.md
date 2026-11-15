# 31: The Ares-Crown window frame

Empire board brief 279. Image package: it switches on the window frame the owner chose.

**Builder:** Codex (gpt-6.1-sol, xhigh): the look is designed and chosen; what is left is image plumbing and checks. **Review:** a fresh package review; then `linux-aresos` reads the `os/` diff before merge.

## Why

Every program's window on AresOS wears labwc's grey default frame. A Fable design agent built three complete themes (`docs/design/WINDOWS.md`, pictures in `reviews/window-design-v1/`), and the owner chose on 2026-11-13 (board #206): "None look crazy tbh but yes crown. But chrome shouldn't get the extra bar, other OS don't have that right? It looks weird".

**Goal:** after the next release, every window that takes the system's frame has the Ares-Crown bar (near-black, off-white Space Grotesk title, a gold dot on the active window, minimize / maximize / close at the right), Alt+Tab shows preview pictures, and programs that draw their own bar (Chrome, GNOME programs) show all three buttons in it. Chrome keeps its own bar with the tabs in it; nothing gives it a second one.

## Starting point

This branch is cut from a `main` that contains package 23, and carries the design commit from `design/windows-v1` (the three themes, `WINDOWS.md`, the pictures) and this brief. Package 23 changed `rc.xml`, `autostart`, `os/build.sh` and `os/ci/image-checks.sh`; read them as they are now. Package 30 (the helper lists his programs) is built at the same time in another worktree and also adds checks to `os/ci/image-checks.sh`: add yours in one block of their own. Read `docs/design/WINDOWS.md` fully first: it has the exact `rc.xml` lines, the font file and its checksum, and what was and wasn't tried.

## Build

1. **One theme ships.** Keep `os/config/usr/share/themes/Ares-Crown/labwc/` as designed. Delete the folders `Ares-Plain` and `Ares-Block` (they stay in git history and in `WINDOWS.md`'s pictures). Keep `reviews/window-design-v1/draw-buttons.py` working for Ares-Crown, or cut it down to that theme.
2. **`rc.xml`** (`os/config/usr/share/aresos/labwc/rc.xml`): replace only `<theme><name>Default</name></theme>` with the Ares-Crown block from `WINDOWS.md` ("Switching a theme on"), and add its `<windowSwitcher>` line. Touch nothing else in the file: the key bindings, the window rules and whatever package 23 put there stay byte for byte. `os/tests/test_everyday_account.py` reads this file and must pass unchanged.
3. **The font:** `SpaceGrotesk-Variable.ttf` (sha256 `acad6de1fc93436f5c0f1f4137751ef04f1aea3063e7036535970ffcfbd79f72`, 137 KB) and its licence `OFL-SpaceGrotesk.txt` into `os/config/usr/share/fonts/aresos/`, unchanged. Take both from `~/ares-empire/web/fonts/` (read-only; check the checksum). Add the font to the README's list of parts from others, with its copyright line (© 2020 The Space Grotesk Project Authors, SIL Open Font License 1.1).
4. **The three buttons for programs with their own bar.** A gschema override, not dconf: one file under `/usr/share/glib-2.0/schemas/` whose name sorts after anything the base may add later (for example `zz-aresos.gschema.override`), setting `button-layout='appmenu:minimize,maximize,close'` for `org.gnome.desktop.wm.preferences`. Scope it to this desktop if that works here (`[org.gnome.desktop.wm.preferences:AresOS]`; the session sets `XDG_CURRENT_DESKTOP=AresOS`); if the scoped form has no effect, use the unscoped one and say so. Run `glib-compile-schemas` in `os/build.sh`, in the same mode that installs the config, and fail the build if it fails. The image has no such step today.
5. **Chrome is left alone:** no Chrome preference, policy or window rule. It keeps its own bar.
6. **A broken theme must never cost him the desktop.** Show, in a headless labwc started the way `aresos-session` starts it, that with the theme folder missing (and separately, with the font missing) the session still starts, windows get a usable frame, and the recovery terminal's key binding (Super+Ctrl+Escape) is still bound and its command runs. If labwc does anything worse than fall back to its defaults, stop and report it.
7. **Checks** in `os/ci/image-checks.sh` (add only): the theme folder with its `themerc` and every button file `themerc` or labwc expects, the font and its licence, the theme name in `rc.xml`, the override file, and that the compiled schemas give the value (`gsettings get` with `XDG_CURRENT_DESKTOP=AresOS`, or reading the compiled file the way the image's tools allow).
8. **Docs:** in `docs/design/WINDOWS.md`, record the decision at the top (date, his words, Chrome keeps its own bar, what shipped), move the two other themes under "Not chosen" with their pictures, and turn "Left for the owner to choose" into what is still open (the size on the real panel; a dark look for other programs later). Do not edit `STATE.md`, `HANDOFF.md`, `CLAUDE.md`, the install docs or `os/ci/release_diff.py`.

## Verification

- **Headless, never on his screen:** a labwc of your own (`WLR_BACKENDS=headless`, own runtime folder and `WAYLAND_DISPLAY`), using this worktree's `rc.xml`, theme and font through a scratch data folder, and a scratch `XDG_DATA_DIRS` entry with the compiled override. Pictures with `grim` against that display at 1920x1080:
  - an active and an inactive window with the frame (`foot` and `kwrite` with sample text of your own);
  - Alt+Tab with preview pictures;
  - `gsettings get org.gnome.desktop.wm.preferences button-layout` as the user in that session, with `XDG_CURRENT_DESKTOP=AresOS`, printing the new value;
  - Chrome (a throwaway `--user-data-dir` in your scratch folder, never his profile) and one GTK4 header-bar program, each showing minimize, maximize and close in its own bar, and Chrome without a second bar;
  - the two fallback cases from step 6.
  Look at every picture yourself. Commit the ones that show nothing personal under `reviews/31-window-frame/`.
- **Tests:** the whole `os/tests` suite, plain and with `-B`; `os/tests/test_everyday_account.py` unchanged and passing.
- **Check build:** after pushing, `gh workflow run "OS image" --ref pkg/31-window-frame -f check_build=build`, and wait with one blocking `gh run watch`. Image checks and the VM pass must be green.
- **Report** (`reviews/31-window-frame/REPORT.md`, AGENTS.md format). Say plainly that `gschemas.compiled` changes in the image: the next release's image diff needs a rule for it, which the OS lead writes. List every `os/` file you touched at the top.
- **Not verified here:** the look on the laptop's real panel, and Discord and the Lunar Client launcher themselves (they draw their own windows). Write the short "try this" note for the owner.

## Already decided

- Ares-Crown, as designed. No restyling in this package; if something in the theme is plainly broken, fix that one thing and record it.
- A gschema override, compiled at build time. The font in its own folder with its licence beside it.
- Chrome keeps its own bar.

## If unsure

Leave the frame at labwc's default rather than ship something that can stop the session, and record why.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-31-window-frame`, branch `pkg/31-window-frame`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- The real session is `WAYLAND_DISPLAY=wayland-0` in `/run/user/1001`: never open a window there, never reconfigure the running labwc, never inject input. Stop every process you started; never stop a process by name alone (match your own PIDs).
- No sudo, no system installs, nothing written outside the worktree and your scratch folder. Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`.
- The repo is public: no personal data, no screenshots of his screen or his programs' content.
- Commit messages end with a trailer naming the model.
- Before a heavy step (the full `os/tests` suite, a headless compositor with programs in it) check that the owner's own game is not running (a Java process whose `/proc/<pid>/exe` is under `~/.lunarclient/`) and that `free -g` shows at least 4 GB available; otherwise wait with a blocking sleep of several minutes. Other builders share the laptop.
