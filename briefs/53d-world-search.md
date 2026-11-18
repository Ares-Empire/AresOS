# 53d: Super opens a search over the world

Board #335, brief 306, step 5 of `docs/design/LAPTOP-HOME.md` section 9. Mod, helper and `rc.xml` package. The lead's
handoff for the whole build is `briefs/53-laptop-home-build.md`.

**Two steps, two builders:**
- **Step 1, the bar's look and its screen:** a Claude agent on **Fable 5.2**. How the bar looks is new design work
  (CLAUDE.md: design work runs on Fable). The owner sees its pictures before this package merges, and that is the
  one owner look left in package 53.
- **Step 2, the rules:** a Claude agent on **Opus**. This is the helper's event, the mod opening the bar, and the
  keybind, built against tight rules.

Each step commits, pushes and keeps `reviews/53d-world-search/PROGRESS.md` true. At the end step 2 replaces its
content with the report text in the AGENTS.md format, and the lead moves it to `REPORT.md`.

**Review:** a fresh Codex `gpt-6.2-sol` `high`. `linux-aresos` reads the `os/` diff before merge.

## Why

The owner reserved Super for a search over the world (boards #333 and #334). Pressed and released alone, from
anywhere, it opens a search bar on the screen that shows the world: the monitor when it is plugged in, otherwise the
laptop's own screen. Enter opens the best hit on that screen, Escape closes the bar. This is the quickest way to an
app without first freeing the pointer in the game.

## Read first

- `docs/design/LAPTOP-HOME.md`: section 6, "The reserved key, Super", and section 9, step 5 with its tests.
- `docs/design/HUB.md` 2.4 (the Apps screen's search) and 3.8 (the 1.1 interface), and LAPTOP-HOME.md section 5
  (1.2).
- The mod:
  - `mod/src/client/java/dev/aresos/client/AppsScreen.java` and `ShellFocusClient.java`;
  - `mod/src/main/java/dev/aresos/config/AppSearch.java` and `shell/ShellClient.java`;
  - `src/testShared/.../FakeHelper.java`.
- The helper, `os/config/usr/libexec/aresos-shell`: `return_to_desktop`, `Windows.covering` and how activating a
  covered world minimizes what covers it (package 40), `emit`, the capabilities, and `shell_covered` as the model
  for a desktop-only event.
- `os/config/usr/share/aresos/labwc/rc.xml`.

## Agreed with `linux-aresos` (2026-11-19)

- **The command:** `aresos-desktop search` is 23c's. It goes through the supervisor's existing command path. The
  supervisor sends **SIGUSR1 to its own live helper child**, never to a PID read from a file. It does nothing
  (exit 0) when no helper or world is up, or the state is not IN_WORLD.
- **The helper** installs its SIGUSR1 handler before it reports ready, so an early signal cannot kill it.
- **The `rc.xml` keybind is 53d's**, with notice to `linux-aresos` and `linux-desktop` before it merges.
  `linux-desktop` knows that Super alone is reserved.
- **Opening on the world's screen** needs 23c's placement. 23c's direction (`linux-aresos`, 00:35): move the
  pointer to the centre of the world's output just before the launch, since labwc places a new window on the
  pointer's output. If the launch's first window still maps elsewhere, move that window once. A labwc rule cannot
  do it, because rules match app IDs, not launches. 53d only carries the hint: the mod sends `"screen": "world"`
  with `open_app`, the helper accepts and records it per launch, and the report carries a PLAN-GAP for 23c.

## Step 1: the search bar (Fable)

1. **A screen of its own in the mod**, `WorldSearchScreen`, drawn over the world. It finds as the Apps screen's
   search does: through `AppSearch`, over names, short names, generic names and keywords, ranked the same way.
   - The best hit is framed. Enter opens it as its hotbar item would.
   - A click on a result opens that result. Escape closes the bar.
   - While the bar is open the pointer is free, as in the Apps screen.
   - With no hit, Enter does nothing, and the bar says so in a line.
   - Opening from the bar sends `open_app` with `"screen": "world"`.
2. **Its look is design work.** Draw **two or three looks** for the bar, within AresOS's existing language for
   in-game screens: the Apps screen, the home menu, and the fonts and colours the mod already uses. Make one of them
   the default, and put the others behind a test-only switch.
   - **Pictures for the owner** come from client game tests with `FakeHelper` and generated test apps ("Test Web 1",
     generated icons), under `reviews/53d-world-search/pictures/`. For each look: empty, typing with several hits,
     no hit, and a long list.
   - Add the client tests at the **end** of the client suite. Look at every picture yourself.
   - Write one paragraph per look in PROGRESS.md: what it is and why. Name the one you recommend.
3. **Until step 2, a test hook opens the screen.** Step 1 adds no keybind and no helper change.

## Step 2: the rules (Opus)

1. **The helper (1.2).**
   - **The capability:** a new event `shell_search`, offered as a capability the way `shell_covered` is. It is sent
     only to a connected desktop that offered it, never to a view.
   - **On SIGUSR1,** when such a desktop is connected:
     - activate the world's window as `return_to_desktop` does;
     - minimize a maximized or fullscreen window that hides the world on its screen, by package 40's rule, and leave
       smaller windows and windows on the other screen where they are;
     - send `shell_search`.
   - **Otherwise** it ignores the signal.
   - **Repeats:** coalesce signals within 300 ms.
   - **`open_app`** accepts an optional `"screen": "world"` and records it with the launch. An unknown value is
     `malformed`. No placement is built here.
   - Add example messages under `mod/src/test/resources/shell-1.2/` and one line in LAPTOP-HOME.md section 5.
2. **The mod.**
   - `ShellClient` offers `shell_search`.
   - On the event, the client thread opens `WorldSearchScreen` in place of any open screen, unless the game is
     loading or a home switch is running (the lifecycle's STARTING); then it ignores the event.
   - Escape returns to the world, not to the screen that was open before.
3. **`rc.xml`:** `<keybind key="Super_L" onRelease="yes">` running `/usr/libexec/aresos-desktop search`. Check that
   labwc 0.9.6 fires it only when Super is pressed and released alone. Super combined with another key must not
   fire it. The existing `W-C-Escape` must keep working.
4. **Tests:**
   - **Helper modules, by name:**
     - the signal reaches only a desktop that offered `shell_search`, never a view;
     - no connected world means nothing happens;
     - a maximized window on the world's screen is minimized, while a small window and a window on the other
       screen are not;
     - signals are coalesced;
     - a signal before ready does not end the helper;
     - `open_app` with `screen`, both valid and bad.
   - **Mod unit tests with `FakeHelper` sending `shell_search`.**
   - **One client game test,** at the end of the suite: `shell_search` opens the bar; typing and Enter make
     `FakeHelper` record `open_app` with `"screen": "world"`; Escape returns to the world.
   - What only the laptop trial can check goes to the report: Super from a small app, from a maximized app on the
     world's screen, from an app on the other screen, and with the pointer on the laptop screen.

## Acceptance

- **Mod:** `mod/dev/build.sh` passes, and `mod/dev/client-test.sh` passes **twice**. It takes the client-test lock,
  and it exits 75 under 6 GiB free; then wait and retry, never `--force`. Commit your own work before a suite run,
  then restore only the screenshot files the suite rewrote.
- **Helper:** the touched helper modules pass, each run by name (never the whole `os/tests`, never
  `test_owner_update`). After the last push, start one hosted run (`gh workflow run "OS image" --ref
  pkg/53d-world-search -f checks_only=true`) and put its ID in the report.
- **Push, then stop.** Never wait for or watch CI. Do not merge.

## Machine rules

- Headless only. Never the owner's session (`wayland-0`), his `.minecraft`, Lunar Client or `~/AresOS-try`.
- No screen capture: pictures come only from the client tests.
- The repo is public: generic names and generated pictures only.

## Out of scope

- The supervisor's `search` command and the placement on the world's screen (23c, `linux-aresos`).
- The laptop home (53f).
- Any other keybind.
