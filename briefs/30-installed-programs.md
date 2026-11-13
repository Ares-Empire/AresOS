# 30: The hub lists his installed programs

Empire board brief 277 (board #163, the owner's "his own programs in the hub"). One package for both sides: the OS app helper (`aresos-shell`) and the mod.

**Builder:** a Claude agent (Fable 5.2): it changes what the helper starts, so mistakes cost more than usual. **Review:** a package review and a security review at the tools bar (`docs/REVIEW.md`, "Tools for Claude"), both fresh; then `linux-aresos` reads the `os/` diff before merge.

## Why

On AresOS the hub knows three apps: Chrome, Terminal and Notepad, from a reviewed list in the image. The owner's programs (Lunar Client, Firefox, Steam, later Discord, anything he installs) are missing. He wants to walk into their logos, right-click them in the hotbar and type `/lunar`, `/dc`, `/chrome`.

**Goal:** every program installed on the laptop that a normal start menu would show appears in the game's app list with its real name and icon, opens through the helper like the three built-in apps, and returns to the hub when its last window closes. A program installed while AresOS runs appears without logging out. Lunar Client and Steam start on the RTX 4060.

Not in this package: which apps get a logo in the world or a place in the inventory by default, and the `/name` commands. Those follow `docs/design/HUB.md` in later packages; this one delivers the list they build on.

## A. The helper (interface `aresos-shell/1.1`)

Read `os/config/usr/libexec/aresos-shell` fully first, and `docs/design/OS-BASE.md` Appendix B1 and B2.

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
- `Terminal=true` (btop and the like): the program runs inside the AresOS terminal: `foot` with an app ID of its own for that program, so its window is tracked like any other.
- Scope, unchanged: its own user scope under `app.slice` through `systemd-run --user --scope`, outside the game's and the helper's cgroups, with the session's environment minus the private variables. Package 23 puts Minecraft in a scope of its own with a memory limit and a supervisor that reacts to that scope dying; a program opened from the hub must never be inside it. Add a test that asserts the unit and slice of a discovered program's launch command.
- **Graphics card:** an entry with `PrefersNonDefaultGPU=true` or `X-KDE-RunOnDiscreteGpu=true`, or with `Game` among its `Categories`, starts with `__NV_PRIME_RENDER_OFFLOAD=1` and `__GLX_VENDOR_LIBRARY_NAME=nvidia` added, and only when the NVIDIA driver is loaded (decide by a file check such as `/proc/driver/nvidia/version`, injected for tests). Registry entries get the same through a new optional key `"gpu": "discrete"`. Nothing else may add environment variables to a launch.
- The helper stays unprivileged: no sudo, no polkit, no setuid helper, nothing outside his user. It never writes outside `$XDG_RUNTIME_DIR/aresos/` and its cache folder (A6).

### A5. Windows and the way back

The owner's rule: closing the program's window puts him back in the hub. Today a window belongs to an app through the registry's `window.app_ids`, and two apps claiming one identity make both unavailable.

- A discovered program's identities are, in this order: `StartupWMClass`, the desktop file ID without `.desktop`, the Flatpak app ID if it is a Flatpak entry, the executable's base name. Between discovered programs a clash never makes anything unavailable: the earlier program keeps the identity and the later one loses that single identity. A registry entry's identities always win.
- A discovered program has no declared single/multi behaviour. Treat an early clean exit as a hand-over, not a failure, and never report `no_window` as a failure for it while its scope still runs: say what you chose and why in the report.
- Lunar Client is the hard case and the owner's first program: the launcher's window is `lunarclient`, and the game it starts is a Java window with another identity, in the same scope. While that scope is alive the hub must not take the focus back because the launcher's window closed, and when the game and the launcher are both gone he must land in the hub. Design the rule (for example: windows no app claims, appearing while exactly one launched program's scope is alive, belong to that launch), keep it inside the existing transition logic (`windows_changed`), and prove it with tests that replay the window events in every split order, as the existing ones do.
- Nothing here may change how the three registry apps behave. The existing helper tests must pass unchanged, apart from fixtures that gain the new optional keys.

### A6. Icons

The game needs one picture per program, as a file it can read without trusting the program's own files.

- Resolve `Icon`: an absolute path as written; otherwise by name through the icon folders (`~/.local/share/icons`, the two Flatpak exports' `share/icons`, `/usr/local/share/icons`, `/usr/share/icons`, `/usr/share/pixmaps`), themes `hicolor` then `breeze`, preferring the largest raster size up to 256 px, then scalable. No path from an icon name may leave those folders (no `/`, no `..`).
- Convert every icon to a normalised PNG (RGBA, 128×128, aspect kept, transparent padding) in `$XDG_CACHE_HOME/aresos/icons/` (default `~/.cache/aresos/icons/`, mode 0700), named by a hash of the source path, size and modification time, written atomically. The conversion runs in a short-lived child process with a timeout and an input size limit, so a broken or hostile image can only lose its own icon. Find the converter the image really has (it has no `rsvg-convert`; ImageMagick's `magick` is there, and so are the libraries labwc itself uses for SVG): check on this laptop which route renders both PNG and SVG icons correctly, pick one, and name it in the report. If the image lacks what is needed, that is a PLAN-GAP, not a reason to install something.
- Icons never slow the helper down: the app list answers at once, a missing picture is simply absent, and the list's revision changes when pictures arrive.

### A7. The interface

- Minor version 1 (`aresos-shell/1.1`), negotiated in `hello` as today (`min(minor)`).
- `list_apps` entries gain optional fields, sent only to a client that negotiated 1.1: `icon` (absolute path of the normalised PNG, or absent), `categories` (the entry's categories, each `[A-Za-z0-9-]{1,32}`, at most 16), `generic_name`, `keywords` (at most 16, each at most 32 characters), `desktop_id`, `exec_name` (the base name of the program that runs; for a Flatpak entry the Flatpak app ID), `source` (`image`, `system`, `flatpak` or `user`), `terminal` (boolean). No command, no arguments and no environment are ever sent to the game.
- The list changes while the helper runs. Detect it without inotify (standard library only): rescan when asked and at most every few seconds, cheaply (folder and file times first). Tell a connected 1.1 client with an `apps_changed` event carrying the new revision; the client then asks again. `list_apps` must stay within the 64 KiB message limit: page it or raise the limit for this reply only, and say which.
- Compatibility, both ways, each with a test:
  - an older mod (1.0, the jar pinned in an image) with this helper: gets exactly what it gets today, the registry apps with `{id, name, available, reason}` and nothing else. Discovered programs are listed and opened only for a client that negotiated 1.1 (the older mod would put every one of them into his inventory);
  - this mod with the older helper (release 27's, 1.0): three apps, no pictures, today's behaviour, no error message.
- Update `docs/design/OS-BASE.md` Appendix B1 for 1.1 (the `list_apps` row and one paragraph on discovered programs), and the header comment of the helper.

### A8. What must stay green

- `os/tests` (the helper's tests and the whole suite), `os/image-checks.sh` and the VM checks. After pushing, run one check build on the PR's branch: `gh workflow run "OS image" --ref pkg/30-installed-programs -f check_build=build`, and wait for it with one blocking `gh run watch`, not by polling. GitHub's runners are free for this repo.
- If you change a file that the package 16 walk binds, add its new hash to `os/manifest/ci/16/pending-rebind.json` as `reviews/15f-lenovo-firmware-entry/REPORT.md` describes.
- Files you may touch under `os/`: `config/usr/libexec/aresos-shell`, `config/usr/share/aresos/apps/*.json`, `tests/test_aresos_shell.py` and new test files and fixtures beside it, `manifest/ci/16/pending-rebind.json`, and `image-checks.sh` only to add a check. Nothing else under `os/`; package 23 (PR #36) is changing the session and the supervisor this week. List every `os/` file you touched at the top of the report.

## B. The mod

Read `mod/src/main/java/dev/aresos/shell/ShellClient.java`, `catalogue/LinuxAppCatalogue.java`, `config/AppsConfig.java`, `config/AppDefinition.java`, `icon/*.java`, `item/AppInventory.java` and `client/AppsScreen.java` first.

1. `ShellClient` speaks 1.1: parses the new optional fields (unknown ones are ignored), handles `apps_changed` by asking again, and still works with a 1.0 helper.
2. The fields reach the app list: the picture path becomes the app's icon source, so the item shows the program's own pixel icon and `/aresos logo` can build its logo. Categories, generic name, keywords, desktop ID, executable name and source are kept on the app in memory for the packages that follow (`/name`, the plaza). They come fresh from the helper at every start and are not written into `apps.json`; his own name, look and pin for an app stay in `apps.json` as today.
3. A program without a picture gets a plain vanilla item look chosen by its main category (a short table in one place; `minecraft:paper` when nothing fits).
4. When the list or a picture changes while the game runs, the item icons follow: regenerate the icon pack and reload it, once per change and not more than once every few seconds. No reload when nothing changed.
5. **The inventory must not flood.** Today every known app is put into the inventory. Keep that for the three registry apps and for anything already pinned or already in his inventory. A discovered program is listed in the **Apps…** screen only, and taking it from there puts its item in his hand as today. Give the Apps… screen a search field (type to filter by name; Enter takes the only match), because the list is now long, and sort it by name.
6. A program that disappears (uninstalled) stays in `apps.json` and in his inventory but shows as unavailable when used, with the helper's reason; nothing is deleted.
7. Windows behaviour is unchanged. Platform code stays behind the existing interfaces.

## C. Verification

- **Helper:** unit tests for every rule in A1 to A7, with fixtures taken from real entries of this laptop (`/usr/share/applications`, the Flatpak exports, Lunar's entry with the home path replaced by a placeholder). Hostile fixtures: oversized file, binary junk, `Exec` with shell characters, `Icon=../../x`, an icon that is not an image, 500 entries, two entries with one identity, an entry that hides a system one.
- **Mod:** Java unit tests with the fake helper for 1.0 and 1.1, `apps_changed`, a list of 150 programs, the Apps… search. `mod/dev/build.sh` passes; `mod/dev/client-test.sh` passes **twice** (see `mod/README.md`, "On Linux"; it holds the laptop's client-test lock and refuses while the owner's game runs).
- **End to end, headless:** start a headless labwc, this worktree's helper inside it, and open two neutral programs through the real socket (a small script or test that speaks the protocol is enough; the game is not needed): `kcalc` and `btop` (the terminal case). Show that each got its own scope under `app.slice`, that its window was matched, and that ending it produced the return event. Never open a window in the owner's session, and never start Chrome with his profile, Lunar Client or Steam; he tries those himself with `mod/dev/run-hub.sh --helper … --registry …` once this is reviewed.
- **Not verified here:** Lunar Client and Steam for real, and the offload variables' effect on a real game. Say so, and write the three-line "try this" note for the owner at the end of the report.

## Already decided

- One package, built in this order: helper listing and launch, helper windows, icons, interface, mod.
- Standard library only in the helper. No new dependency in the mod.
- No shell, no command or environment from the game, the helper unprivileged: these are not up for trade.
- The safety bar is the tools bar: safe the way a normal app launcher is. A desktop entry in his own folders can already run anything as him on any Linux desktop; listing it adds no new power. A hostile entry that looks like another program is a known limit, not a finding to fix.

## If unsure

Leave a program out of the list rather than start something in a way the entry didn't ask for. Record every such case.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-30-installed-programs`, branch `pkg/30-installed-programs`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- The repo is public: no personal data in fixtures (replace the home path), no third-party icons committed (draw two tiny test images yourself).
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft`, `~/.lunarclient`, or PR #36's branch. No sudo, no system installs.
- 16 GB of memory is shared with other sessions: one Gradle daemon, stopped when done; never two heavy steps at once.
- Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
- `reviews/30-installed-programs/REPORT.md` in the AGENTS.md format, with JUDGMENT-CALLs and PLAN-GAPs marked.
