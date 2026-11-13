# 34 My apps: builder handoff

Working notes for the next builder. Deleted in the last commit before the PR is ready.

## State

- **Done:** reading only (AGENTS.md, the brief, HUB.md 2.4, 2.5, 3.5, 3.7, 3.8, and the code the brief lists). No code is changed yet.
- **Not started:** every step below.

## Steps, in order

1. **A: the mod speaks `aresos-shell/1.1`.** `ShellClient` (minor 1, paging, revision restarts, optional fields, `apps_changed`), `FakeHelper` for 1.0 and 1.1, the example messages under `mod/src/test/resources/shell-1.1/`, unit tests. Then A3 (what the system said, kept on the app and saved), A4 (icon path feeds the pixel icon; regenerate and reload the pack, throttled), A5 (vanilla look by group, one table).
2. **B1: the apps file.** New schema (3) with `mine` per app and `baseline` for the file, atomic write with a backup as the schema-2 move did; unit tests for the move, the backup and a broken file.
3. **B2: the rules and the inventory.** Day one, the baseline, new programs after it, only complete lists; add and remove including the saved Build inventory and a pending mode switch; Q on an app item; the three commands; pinning makes it his. Server game tests.
4. **B3: the Apps screen** (search box, My apps, All programs, left and right click, Enter, Escape, 200 programs) and the client game tests with screenshots under `reviews/34-my-apps/screenshots/`.
5. `mod/README.md`, `reviews/34-my-apps/REPORT.md`, `mod/dev/build.sh` once and `mod/dev/client-test.sh` twice, `git fetch origin` (merge `origin/main` if #44 merged, main's `mod/dev/` wins), delete this file, push, `gh pr create`.

## Decisions taken so far (none is in code yet)

- **The envelope.** HUB.md 3.8 does not say which `protocol` string a 1.1 client writes. Chosen: the mod's `hello` carries `aresos-shell/1.1` (its own version) with `"major": 1, "minor": 1`; every later message carries the negotiated minor (`1.0` with a 1.0 helper, `1.1` with a 1.1 helper). This mirrors the helper, which answers with its own minor until `hello` and the negotiated one after. The installed 1.0 helper accepts it: it compares only the major (`ENVELOPE` in `os/config/usr/libexec/aresos-shell`). The mod already accepts any `aresos-shell/1.x` envelope. Record this in the report under "what 3.8 left open".
- **The mod offers `app_details`, `apps_changed` and `list_paging` in `hello`'s `capabilities`** and requires none. This matters: the helper's `emit` sends an event only if the client offered a capability of that name, so without `apps_changed` in the offer no event would ever come.
- **Optional entry fields and `next` are read only when the negotiated minor is 1.** With a 1.0 helper the reply is one page and unknown fields are ignored, exactly as today.
- **The baseline is written only by a complete list that carries origins (negotiated 1.1).** Reason: the laptop runs the 1.0 helper today (three apps). If that list wrote the baseline, the 1.1 helper's first list would count as "after the baseline" and the 11 Flatpaks Bazzite ships (`flatpak-system`) would join My apps by themselves, against the day-one rule (only `user` and `flatpak-user`). So on Windows and with a 1.0 helper no baseline is written and nothing joins by itself. This is a PLAN-GAP to record (the brief's B2 does not say it).
- **A starter** is an app whose ID is `browser`, `terminal` or `notepad` (one fixed set, needed at the schema move, where no helper answers), or whose `source` is `image` on a 1.1 list.
- **"Newly appears"** means: its ID is not in the apps file before this list. A program that left the system and comes back keeps the `mine` it had.

## Things the code does not show

- `FakeHelper` is package-private in `mod/src/test/java/dev/aresos/shell/`. The gametest source set gets `src/test/resources` (see `build.gradle`) but not `src/test/java`, so the client game tests cannot use it as it is. The existing client tests drive the app list with `AppsTestAccess.aresos$setApps` and a replaced launcher instead of a socket. The brief wants the client tests "with the fake helper", so the helper has to become reachable from the gametest source set without copying it (for example by adding its file to that source set in `build.gradle`).
- Existing tests assert `aresos-shell/1.0` on every message the fake helper receives and `minor` 0 in `hello` (`ShellClientTest.handshakeSends...`); they change with step A.
- `AresOs.java` and `AresOsClient.java` are shared with packages 32 and 33: registration lines only. New logic goes in its own classes.
- The Lunar Client launcher (an AppImage, Electron) may run all day; the dev scripts refuse only for the game itself (a process whose executable lives under `~/.lunarclient/`).
- Worktrees for packages 30 and 35 exist next to this one. They are not this package's business.
