# 30: The hub lists his installed programs

Empire board brief 277 (board #163, the owner's "his own programs in the hub"). The OS app helper's side (`aresos-shell`). The mod's side is package 34 ("My apps"), built first; both follow one description, `docs/design/HUB.md` section 3.8.

**Builder:** a Claude agent (Fable 5.2): it changes what the helper starts, so mistakes cost more than usual. **Review:** a package review and a security review at the tools bar (`docs/REVIEW.md`, "Tools for Claude"), both fresh; then `linux-aresos` reads the `os/` diff before merge.

## Why

On AresOS the hub knows three apps: Chrome, Terminal and Notepad, from a reviewed list in the image. The owner's programs (Lunar Client, Firefox, Steam, later Discord, anything he installs) are missing. He wants to walk into their logos, right-click them in the hotbar and type `/lunar`, `/dc`, `/chrome`.

**Goal:** every program installed on the laptop that a normal start menu would show appears in the game's app list with its real name and icon, opens through the helper like the three built-in apps, and returns to the hub when its last window closes. A program installed while AresOS runs appears without logging out. Lunar Client and Steam start on the RTX 4060.

Not in this package: anything in the mod. Which programs are his, their items, logos and `/name` commands are the hub packages 32 to 37 (`docs/design/HUB.md`); this one delivers the list they build on.

## A. The helper (interface `aresos-shell/1.1`)

Read `os/config/usr/libexec/aresos-shell` fully first, `docs/design/OS-BASE.md` Appendix B1 and B2, and `docs/design/HUB.md` sections 3.7 and 3.8. Section 3.8 is the interface; where this brief and 3.8 differ, 3.8 wins and you say so in the report.

### A1. Where programs come from

- The reviewed registry (`/usr/share/aresos/apps/*.json`) stays and wins: its IDs (`browser`, `terminal`, `notepad`) are saved in his pins and logos and never change.
- New: desktop entries, read from these folders in this order (a desktop file ID found earlier hides the same ID later, as the Desktop Entry spec says; `Hidden=true` in an earlier folder removes it everywhere):
  1. `$XDG_DATA_HOME/applications` (default `~/.local/share/applications`)
  2. `~/.local/share/flatpak/exports/share/applications`
  3. `/var/lib/flatpak/exports/share/applications`
  4. `/usr/local/share/applications`
  5. `/usr/share/applications`
- A registry entry may name the desktop file IDs it stands for (new optional key `"replaces": ["google-chrome.desktop", "com.google.Chrome.desktop"]`), so Chrome, the terminal and KWrite are not listed twice. Add the right values to the three shipped entries.

### A2. Which entries are listed

Listed: `Type=Application` with a usable `Exec`. Not listed: `Hidden=true`, `NoDisplay=true`, entries whose `OnlyShowIn`/`NotShowIn` exclude this desktop (`XDG_CURRENT_DESKTOP` is `AresOS`), entries whose `TryExec` isn't an executable file, and `DBusActivatable=true` entries without `Exec`. An entry that can't be parsed is skipped with one log line; it never stops the others. Desktop entry actions (`[Desktop Action …]`) are ignored.

Desktop entries are untrusted text. Read at most 1 MiB per file, only the `[Desktop Entry]` group, UTF-8 with replacement; follow no include mechanism; cap the number of listed programs (today's `MAX_APPS`) and say in the log when the cap cuts.

### A3. IDs and names

- A discovered program's ID is derived from its desktop file ID, lower-cased, with every character outside `[a-z0-9_-]` turned into `-`, without the `.desktop` ending, at most 64 characters (`org.mozilla.firefox.desktop` → `org-mozilla-firefox`, `lunarclient.desktop` → `lunarclient`). The same program must get the same ID on every start: pins and logos are saved by ID. Two entries that map to one ID: the earlier folder keeps it, the later one is not listed (log line). A discovered ID never takes a registry ID.
- The name is the entry's plain `Name` (no localisation in this package), trimmed to 64 printable characters.

### A4. Starting a discovered program

- `Exec` is parsed by the spec as today (`desktop_exec`): field codes dropped, quoting honoured, no shell, ever. Flatpak's file-forwarding markers (`@@u %u @@`, `@@ %f @@`) are dropped together with the field code they wrap. The first word is resolved to a full path once (`/usr/local/bin:/usr/bin`, or absolute as written) and must be an executable regular file.
- `Path` (absolute) is the working directory, otherwise his home.
- `Terminal=true` (btop and the like): the program runs inside the AresOS terminal: `foot` with an app ID of its own for that program, so its window is tracked like any other. Keep the terminal's command in one place in the helper: the owner decided (board #191) that Konsole becomes the everyday terminal later, and that switch should be one line.
- Scope, unchanged: its own user scope under `app.slice` through `systemd-run --user --scope`, outside the game's and the helper's cgroups, with the session's environment minus the private variables. Package 23 puts Minecraft in a scope of its own with a memory limit and a supervisor that reacts to that scope dying; a program opened from the hub must never be inside it. Add a test that asserts the unit and slice of a discovered program's launch command.
- **Graphics card:** an entry with `PrefersNonDefaultGPU=true` or `X-KDE-RunOnDiscreteGpu=true`, or with `Game` among its `Categories`, starts on the RTX 4060. Registry entries get the same through a new optional key `"gpu": "discrete"`. Mirror package 23 exactly (`os/config/usr/libexec/aresos-desktop`: the constant `NVIDIA_OFFLOAD` and `nvidia_present()`):
  - the same three variables: `__NV_PRIME_RENDER_OFFLOAD=1`, `__GLX_VENDOR_LIBRARY_NAME=nvidia`, `__VK_LAYER_NV_optimus=NVIDIA_only` (the third makes Vulkan pick the NVIDIA card, which Steam's games need);
  - the same test for the driver (it lists at least one GPU under `/proc/driver/nvidia/gpus`), injected for tests; without the driver nothing is added;
  - before applying the rule, every launch drops inherited card variables (package 23's `GPU_KEYS` in `aresos-desktop-java`: the three above plus `__NV_PRIME_RENDER_OFFLOAD_PROVIDER`, `__EGL_VENDOR_LIBRARY_FILENAMES`, `DRI_PRIME`), so a program never inherits the game's card choice;
  - a test that fails when the helper's and the supervisor's sets differ.
  Nothing else may add environment variables to a launch.
- The helper stays unprivileged: no sudo, no polkit, no setuid helper, nothing outside his user. It never writes outside `$XDG_RUNTIME_DIR/aresos/` and its cache folder (A6).

### A5. Windows and the way back

The owner's rule: closing the program's window puts him back in the hub. Today a window belongs to an app through the registry's `window.app_ids`, and two apps claiming one identity make both unavailable.

- A discovered program's identities are, in this order: `StartupWMClass`, the desktop file ID without `.desktop`, the Flatpak app ID if it is a Flatpak entry, the executable's base name. Between discovered programs a clash never makes anything unavailable: the earlier program keeps the identity and the later one loses that single identity. A registry entry's identities always win.
- A discovered program has no declared single/multi behaviour. Treat an early clean exit as a hand-over, not a failure, and never report `no_window` as a failure for it while its scope still runs: say what you chose and why in the report.
- "Gone" means no window left, whether or not a process is still running. Discord, Steam and Lunar Client keep running without a window after "close", and this session has no tray: closing the last window must put him back in the hub, and choosing the program again must bring its window back (the hand-over rule above covers that second start). One test for exactly this.
- Lunar Client is the hard case and the owner's first program: the launcher's window is `lunarclient`, and the game it starts is a Java window with another identity, in the same scope. While that scope is alive the hub must not take the focus back because the launcher's window closed, and when the game and the launcher are both gone he must land in the hub. Design the rule (for example: windows no app claims, appearing while exactly one launched program's scope is alive, belong to that launch), keep it inside the existing transition logic (`windows_changed`), and prove it with tests that replay the window events in every split order, as the existing ones do.
- Nothing here may change how the three registry apps behave. The existing helper tests must pass unchanged, apart from fixtures that gain the new optional keys.

### A6. Icons

The game needs one picture per program, as a file it can read without trusting the program's own files.

- Resolve `Icon`: an absolute path as written; otherwise by name through the icon folders (`~/.local/share/icons`, the two Flatpak exports' `share/icons`, `/usr/local/share/icons`, `/usr/share/icons`, `/usr/share/pixmaps`), themes `hicolor` then `breeze`, preferring the largest raster size up to 256 px, then scalable. No path from an icon name may leave those folders (no `/`, no `..`).
- Convert every icon to a normalised PNG (RGBA, 128×128, aspect kept, transparent padding) in `$XDG_CACHE_HOME/aresos/icons/` (default `~/.cache/aresos/icons/`, mode 0700), named by a hash of the source path, size and modification time, written atomically. The conversion runs in a short-lived child process with a timeout and an input size limit, so a broken or hostile image can only lose its own icon.
- The converter is ImageMagick, which the image has (`/usr/bin/magick` 7.1.2; its `SVG` coder is librsvg, checked on release 27; there is no `rsvg-convert`). Rules for using it on untrusted files:
  - sniff the file type yourself from its first bytes and accept only PNG and SVG; anything else is skipped and the program keeps its fallback look;
  - name the coder explicitly (`png:<absolute path>`, `svg:<absolute path>`) and never let ImageMagick guess from the name or the content; its own SVG renderer (`MSVG`) must never run on these files, so make sure the librsvg coder is the one that answers `svg:` and fail closed otherwise;
  - resource limits on every run (`-limit` memory, map, disk and time, plus a pixel cap), and no network;
  - if it is cheap, run the converter under `bwrap` (in the image) with no network and only the icon readable; say in the report whether you did.
  If the image turns out to lack something this needs, that is a PLAN-GAP, not a reason to install it.
- Add a check to `os/ci/image-checks.sh` that the converter and its librsvg `SVG` coder exist: a base update could drop them.
- Icons never slow the helper down: the app list answers at once, a missing picture is simply absent, and the list's revision changes when pictures arrive.

### A7. The interface

Implement the helper's side of `docs/design/HUB.md` section 3.8 exactly: minor version 1 and the three new capabilities, paging with `cursor` and `next` inside the 64 KiB limit, the optional entry fields (`source` in its five kinds, `icon`, `categories`, `generic_name`, `keywords`, `desktop_id`, `exec_name`, `terminal`), a starter that stands for desktop entries listed once with that entry's picture and details, the `apps_changed` event, and exactly today's answer for a 1.0 client.

- The mod package (34) committed example messages under `mod/src/test/resources/shell-1.1/`. They are the contract: your tests read those files and check that the helper produces and accepts that shape. If one of them is wrong or can't be met, stop and report it; do not change it.
- The list changes while the helper runs. Detect it without inotify (standard library only): rescan when asked and at most every few seconds, cheaply (folder and file times first).
- Compatibility, both ways, each with a test: the older mod (1.0, the jar pinned in an image) with this helper gets the starters only, as today; the newer mod with release 27's helper is package 34's test.
- No command, no arguments and no environment are ever sent to the game.
- Update `docs/design/OS-BASE.md` Appendix B1 for 1.1 (take HUB.md 3.8 over, and one paragraph on discovered programs), and the header comment of the helper.

### A8. What must stay green

- `os/tests` (the helper's tests and the whole suite), `os/ci/image-checks.sh` and the VM checks. After pushing, run one check build on the PR's branch: `gh workflow run "OS image" --ref pkg/30-installed-programs -f check_build=build`, and wait for it with one blocking `gh run watch`, not by polling. GitHub's runners are free for this repo.
- Files you may touch under `os/`: `config/usr/libexec/aresos-shell`, `config/usr/share/aresos/apps/*.json`, `tests/test_aresos_shell.py` and new test files and fixtures beside it, and `ci/image-checks.sh` only to add checks. Nothing else under `os/`. None of these is bound by a rehearsal today (the active bindings are `os/manifest/ci/27/source-bindings.json`); if a test tells you a bound file changed, stop and report it, the OS lead decides. List every `os/` file you touched at the top of the report.
- **Starting point:** package 23 (PR #36) changes `aresos-shell`, `test_aresos_shell.py` and `image-checks.sh` too. This package is cut from a `main` that contains package 23 and package 34, and you read the helper as it is then; check "scope, unchanged" in A4 against that version.

## B. Verification

- **Helper:** unit tests for every rule in A1 to A7, with fixtures taken from real entries of this laptop (`/usr/share/applications`, the Flatpak exports, Lunar's entry with the home path replaced by a placeholder). Hostile fixtures: oversized file, binary junk, `Exec` with shell characters, `Icon=../../x`, an icon that is not an image, 500 entries, two entries with one identity, an entry that hides a system one.
- **End to end, headless:** start a headless labwc, this worktree's helper inside it, and open two neutral programs through the real socket (a small script or test that speaks the protocol is enough; the game is not needed): `kcalc` and `btop` (the terminal case). Show that each got its own scope under `app.slice`, that its window was matched, and that ending it produced the return event. Never open a window in the owner's session, and never start Chrome with his profile, Lunar Client or Steam; he tries those himself with `mod/dev/run-hub.sh --helper … --registry …` once this is reviewed.
- **Not verified here:** Lunar Client and Steam for real, and the offload variables' effect on a real game. Say so, and write the three-line "try this" note for the owner at the end of the report.

## Already decided

- Built in this order: listing and launch, windows, icons, interface.
- Standard library only in the helper. No change under `mod/` except reading its example messages from tests.
- No shell, no command or environment from the game, the helper unprivileged: these are not up for trade.
- The safety bar is the tools bar: safe the way a normal app launcher is. A desktop entry in his own folders can already run anything as him on any Linux desktop; listing it adds no new power. A hostile entry that looks like another program is a known limit, not a finding to fix.

## If unsure

Leave a program out of the list rather than start something in a way the entry didn't ask for. Record every such case.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-30-installed-programs`, branch `pkg/30-installed-programs`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- The repo is public: no personal data in fixtures (replace the home path), no third-party icons committed (draw two tiny test images yourself).
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft`, `~/.lunarclient`, or PR #36's branch. No sudo, no system installs.
- 16 GB of memory is shared with other sessions: never two heavy steps at once.
- Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
- `reviews/30-installed-programs/REPORT.md` in the AGENTS.md format, with JUDGMENT-CALLs and PLAN-GAPs marked.
