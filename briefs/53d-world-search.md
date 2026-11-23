# 53d: Super opens a search over the world (the helper's and the mod's side)

Board #335, brief 306, step 5 of `docs/design/LAPTOP-HOME.md` section 9. Mod and helper package. The lead's handoff
for the whole build is `briefs/53-laptop-home-build.md`.

**Two steps, two builders:**
- **Step 1, the bar's look and its screen:** a Claude agent on **Fable 5.2**. How the bar looks is new design work
  (CLAUDE.md: design work runs on Fable). The owner sees its pictures before this package merges: the one owner look
  left in package 53.
- **Step 2, the rules:** a Claude agent on **Opus**. This is the helper's signal and event, and the mod opening the
  bar, built against tight rules.

Each step commits, pushes and keeps `reviews/53d-world-search/PROGRESS.md` true. At the end, step 2 replaces its
content with the report text in the AGENTS.md format, and the lead moves it to `REPORT.md`.

**Review:** a fresh Codex `gpt-6.2-sol` `high`. `linux-aresos` reads the `os/` diff before merge.

## Why

The owner reserved Super for a search over the world (boards #333 and #334). Pressed and released alone, from
anywhere, it opens a search bar on the screen that shows the world: the monitor when it is plugged in, otherwise the
laptop's own screen. Enter opens the best hit on that screen, and Escape closes the bar. It is the quickest way to an
app without first freeing the pointer in the game.

## Who builds what (agreed with `linux-aresos`, 2026-11-19)

- **23c, `linux-aresos`, builds:**
  - the supervisor's `aresos-desktop search` command, which sends SIGUSR1 to its own live helper child through its
    existing command path;
  - starting the helper with SIGUSR1 ignored, so a signal during Python's start-up cannot end it;
  - **the `rc.xml` keybind** (`Super_L` on release) and its labwc checks in a private rig;
  - the placement on the world's screen: the pointer moves to the world's output just before the launch, and the
    launch's first window is moved once if it maps elsewhere.
- **53d builds only:** the helper's handling of the signal and the new event, the mod's bar, and the `"screen":
  "world"` hint. It adds **no keybind**. Until 23c lands, nothing sends the signal.

## Read first

- `docs/design/LAPTOP-HOME.md`: section 6, "The reserved key, Super", section 9 step 5, and section 5 (1.2).
- `docs/design/HUB.md` 2.4 (the Apps screen's search) and 3.8 (1.1).
- The mod:
  - `mod/src/client/java/dev/aresos/client/AppsScreen.java` (how it opens over a container, its Enter, its search);
  - `ShellFocusClient.java` (`readyWorld`);
  - `mod/src/main/java/dev/aresos/config/AppSearch.java`;
  - `shell/ShellClient.java` (pending opens, resends after a reconnect);
  - `src/testShared/.../FakeHelper.java`.
- The helper, `os/config/usr/libexec/aresos-shell`:
  - `main()`, `build()` and `Server` (its selector loop);
  - the capabilities, `LATER_CAPABILITIES`, `emit` and `emit_to`;
  - window tracking: `Windows.covering`, and the world's activation request with its `uncover()`;
  - `return_to_desktop`, and why it must not be reused here.

## Step 1: the search bar (Fable)

1. **A screen of its own in the mod, `WorldSearchScreen`, drawn over the world.**
   - **Results:** it searches through `AppSearch` over names, short names, generic names and keywords, and shows My
     apps first, then all programs.
   - **The best hit** is the first result by this rule, which goes into `AppSearch` so the Apps screen can share it
     later: My apps before other programs; then a match at the start of the name or of a word, before a match inside
     a word; then by name. The best hit is framed.
   - **Enter** opens the best hit as its hotbar item would. With a blank query, Enter does nothing. With no hit,
     Enter does nothing and the bar says so in a line.
   - **Clicks and Escape:** a click on a result opens it, and Escape closes the bar.
   - **The pointer and pausing:** while the bar is open the pointer is free, as in the Apps screen.
     `isPauseScreen` is false.
   - **Opening from the bar** sends `open_app` with `"screen": "world"`, and the bar closes.
2. **Its look is design work.** Draw **two or three looks** for the bar, within AresOS's existing language for
   in-game screens: the Apps screen, the home menu, and the fonts and colours the mod already uses. Make one the
   default, and put the others behind a test-only switch.
   - **Pictures for the owner** come from client game tests with `FakeHelper` and generated test apps ("Test Web 1",
     generated icons), under `reviews/53d-world-search/screenshots/` (AGENTS.md). For each look: empty, typing with
     several hits, no hit, and a long list.
   - Add the client tests at the **end** of the client suite. Look at every picture yourself.
   - Write one paragraph per look in PROGRESS.md: what it is and why. Name the one you recommend.
3. **Until step 2, a test hook opens the screen.** Step 1 makes no helper change.

## Step 2: the rules (Opus)

1. **The helper: the signal.**
   - **The first statement of `main()`,** before `parse_args` and `build()`, installs the SIGUSR1 handler.
   - **The handler only records the signal and wakes the loop.** Use `signal.set_wakeup_fd` on a non-blocking pipe
     registered in `Server`'s selector. Activation, minimizing and events run only in the serving loop, never in the
     handler: a handler running between two bytecodes could cut into a half-sent Wayland request or a half-sent line
     to the mod.
   - **In the loop:**
     - signals within 300 ms are coalesced;
     - the helper acts only when all of these hold:
       - a desktop is connected on minor 2 and offered `shell_search`;
       - that connection has sent `world_ready`;
       - window tracking is on;
       - the world's window is known;
     - otherwise the signal is ignored.
   - **When it acts:**
     - it requests the world's activation through the same activation path the helper already uses, so its
       `uncover()` minimizes a maximized or fullscreen window that hides the world on its screen, using
       `covering(known_screen=True)`. Add no second minimize path. Smaller windows and windows on the other screen
       stay where they are;
     - it sends `shell_search` once the activation was requested, or at once if the world is already active;
     - **do not reuse `return_to_desktop`:** it sends `shell_focus` with `reason: app_closed` and marks the world in
       front before the compositor does.
2. **The wire contract (1.2, written into LAPTOP-HOME.md section 5):**
   - **`shell_search`** is an optional event for the desktop only, on minor 2 only, and offered only with window
     tracking. It is gated on minor 2 in the hello and in `emit_to` (`LATER_CAPABILITIES` checks only minor 1). It is
     never sent to a view.
   - **`open_app`'s `"screen": "world"`** is accepted only from a minor-2 desktop. From a view or an older desktop it
     is `malformed`, and any other value is `malformed`. The hint stays with the launch through pending checks,
     duplicate requests and a journal reload. No placement is built here.
   - **Example messages** go under `mod/src/test/resources/shell-1.2/`, and both test suites read them.
3. **The mod.**
   - **The capability:** `ShellClient` offers `shell_search` on minor 2.
   - **On the event,** handled on the client thread:
     - ignore it while `ShellFocusClient.readyWorld(client)` is null: a home switch, loading, or no desktop world;
     - ignore it while a screen with text being typed is open (chat, a sign, a book, an anvil, a command block),
       so his typing is never lost;
     - ignore it while the bar is already open;
     - otherwise, close an open container normally first (`closeContainer()`, as `AppsScreen` does), then open
       `WorldSearchScreen`.
   - **Escape** returns to the world, not to the screen that was open before.
   - **A resend:** the pending `open_app` keeps `"screen": "world"` across a reconnect.
4. **Tests.**
   - **Helper, in-process** (no helper subprocess on the real `WAYLAND_DISPLAY` or `XDG_RUNTIME_DIR`):
     - the handler is in place before `build()` runs: patch `build()` and assert `signal.getsignal(SIGUSR1)`;
     - the handler only sets the flag;
     - the event reaches only a minor-2 desktop that offered it, and never a view;
     - nothing happens with no desktop, with no `world_ready`, with no window tracking, or with the world's window
       unknown;
     - a maximized window on the world's screen is minimized, while a small window and a window on the other screen
       are not;
     - signals are coalesced;
     - the world already active;
     - `open_app` with `screen`: valid, bad, from a view, from 1.1, and kept through a duplicate and a journal
       reload.
   - **Mod unit tests:** `FakeHelper` negotiates minor 2 and advertises `shell_search`; the event, each ignore rule,
     the container close, the best-hit rule, and the hint kept on a resend.
   - **One client game test,** at the end of the suite: `shell_search` opens the bar; typing and Enter make
     `FakeHelper` record `open_app` with `"screen": "world"`; the bar closes; opening the bar again and pressing
     Escape returns to the world.
   - **For the laptop trial, in the report:** Super from inside the world with the pointer captured, from a small
     app, from a maximized app on the world's screen, from an app on the other screen, with the pointer on the laptop
     screen, and typing right after Super from a terminal.

## Acceptance

- **Mod:** `mod/dev/build.sh` passes, and `mod/dev/client-test.sh` passes **twice**. It takes the client-test lock, and
  it exits 75 under 6 GiB free; then wait and retry, never `--force`. Commit your own work before a suite run, then
  restore only the screenshot files the suite rewrote.
- **Helper:** the touched helper modules pass, each run by name (never the whole `os/tests`, never `test_owner_update`).
  After the last push, start one hosted run (`gh workflow run "OS image" --ref pkg/53d-world-search -f
  checks_only=true`) and put its ID in the report.
- **Push, then stop.** Never wait for or watch CI. Do not merge.

## Machine rules

- Headless only. Never the owner's session (`wayland-0`), his `.minecraft`, Lunar Client or `~/AresOS-try`.
- Never run `/usr/libexec/aresos-desktop` or a labwc with the repo's `rc.xml`: the keybind and its checks are 23c's.
- No screen capture: pictures come only from the client tests.
- The repo is public: generic names and generated pictures only.

## Out of scope

- 23c's side: the `search` command, the signal's sender, starting the helper with SIGUSR1 ignored, the `rc.xml`
  keybind, and the placement on the world's screen.
- The laptop home (53f).
