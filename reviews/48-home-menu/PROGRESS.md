# Package 48: progress

Builder: Claude (Opus), step agents. Branch `pkg/48-home-menu`, worktree `~/AresOS-48-home-menu`.

## Done

- Step 1: read the brief, the supervisor (part C), the code and tests it names, and Minecraft 26.2's own code (by
  `javap` on `~/.gradle/caches/fabric-loom/minecraftMaven/.../minecraft-clientonly-deobf-26.2.jar`; there is no
  sources jar, the names are Mojang's). Findings and the design below.
- Step 1, code (compiles; client tests not run yet):
  - `mod/src/main/java/dev/aresos/world/HomeRules.java` (the gate and the first start's decision) and its unit test
    `mod/src/test/java/dev/aresos/world/HomeRulesTest.java`.
  - `mod/src/client/java/dev/aresos/client/AresOsMenuScreen.java`: title, Back, Apps… (inactive outside Live, with a
    tooltip), Settings… (`OptionsScreen(this, options, true)`), New home… (**inactive placeholder until step 2 wires
    it**), the hint line. Not pausing.
  - `mixin/GuiMenuMixin.java` (registered in `aresos.client.mixins.json`): the AresOS menu instead of every game menu
    where `AresOsMenuScreen.replacesGameMenu`.
  - `AresOsClient`: `modeKey()` for the hint; `modeKeyInMenu` also answers in the AresOS menu.
  - `MinecraftFocusMixin`: `FOCUS_RETURN.recordPause` also records the AresOS menu (focus loss without the helper).
  - `HomeScreenClientGameTest`: its Esc check now expects `AresOsMenuScreen` in a session's desktop world.

- Step 2 (code written, compiles; client tests not yet run at the time of writing, see "Test runs" below):
  - `world/HomeSwap.java` (main): dated names, a fresh staging folder, the two renames with undo, restore, and
    `checkComplete` (the supervisor's `check_world` in Java). Unit test `HomeSwapTest`.
  - `client/HomePlan.java`: the create screen's choice (manifest, options, dimensions) and `create(client, dir, parent)`.
    `HomeButton` builds plans (`flatPlan`, `netherPlan`), `createWorld(client, parent, plan)` makes one as AresHub;
    `archive` names through `HomeSwap.datedName`. `HomeCreateScreen` takes an `Action` (title screen: create at once).
  - `client/HomeSwitch.java`: the switch (design below, as built). `client/HomeWorkingScreen.java`: the one-line screen.
  - `client/FirstStart.java`: B. `mixin/GuiScreenMixin.java` (`Gui.setScreen` HEAD) asks HomeSwitch, then FirstStart.
    `mixin/LevelLoadingCoverMixin.java`: loading screens show "Making your new home…" while a switch runs.
  - `AresOsMenuScreen`: New home… opens `HomeCreateScreen(this, confirmNewHome)`; the ConfirmScreen has the brief's
    text, "Make the new home" / Cancel (Cancel: back to the choice).
  - `ShellFocusClient.readyWorld`: null while `HomeSwitch.busy()`.
  - `AppsScreen` (D): `pressed` cleared in `init()` and on every left press (`mouseClicked` override, before super);
    a drag from the Apps screen opened through the menu ends in a new `InventoryScreen`.
  - Docs (E): `docs/design/HUB.md` (package 48 section after package 40's corrections; the two lines fixed),
    `mod/README.md` (title screen, the menu, New home, the first start, the tests).
  - Tests: `HomeMenuClientGameTest` (last in `fabric-client-gametest`), `ScreenLog` + test mixin `ScreenLogMixin`
    (records `Gui.screen` at its PUTFIELD), `aresos.homeMenuReviewDir` in `mod/build.gradle`.

- Step 3: two green full client runs at 0f0d2b04; the game's own switch path checked by hand in package 41's rig
  (`rig/real-switch.sh`, its log lines in `rig/real-switch-switch1.txt`); the report filled in; `origin/main` merged
  (package 46 not landed, so its two PLAN-GAPs stay); the PR opened.

## Left, in order

1. The fresh review. The lead commits the report below as REPORT.md and deletes this file when the package merges.
2. If package 46 (PR #92) lands before this one: the report's two PLAN-GAPs (`save_world` answers `no_world` while
   `HomeSwitch.busy()`, with a test; one home-screen gate, not two), then one more full client run.

## Test runs (step 2)

- `mod/dev/build.sh` after merging origin/main (5f18b483): green, 239 unit tests, all 104 server game tests.
- Trimmed client run (HomeScreen + HomeMenu): green, 57 s.
- Full client run 1 (committed list, at 5f18b483): **green**, 10 min 20 s. Switch flat -> Nether 50: 14,547 ms;
  no AresHub for 92 µs; failed switch back in 3,006 ms.
- Full client run 2: **hung** in `failedNewHome`, stopped by me (exit 1, 16 min 36 s). Thread dump: the client was
  in `HomeSwitch.closeStaging` (a scheduled task) -> `Minecraft.disconnect` -> `IntegratedServer.halt` ->
  `executeBlocking`, waiting for the server thread, which sat at the test framework's phase barrier
  (`ThreadingImpl.enterPhase` from `MinecraftServer.postRunTasks`) waiting for the client: a lock-step deadlock that
  only the client game test framework has. First fix, closing from the END_CLIENT_TICK handler instead of a task:
  the trimmed run hung the same way (thread dump: `HomeSwitch.tick` -> `closeWorld` -> `halt` -> `executeBlocking`,
  server at the barrier). So the framework only lets a test task close a world (it defers `disconnect` from a
  `runOnClient` task to its safe point, `MinecraftMixin.deferDisconnect`). Final fix: in the game the switch closes
  worlds from the tick (as the game does when a server says goodbye); in the tests
  `HomeSwitch.closeFromTestTasksForTests(true)` leaves each such close pending and the test's `waitForSwitch` runs it
  from `runOnClient` every tick (`runPendingCloseForTests`). The first close (the confirm button) already runs in a
  test task. Opens stay in tasks (the framework's `doWorldLoad` busy-wait keeps the lock-step going).
- Trimmed client run with the final fix: **green** (switch 16,219 ms, gap 156 µs, failed switch back in 3,084 ms).
- The three committed pictures (0086-0088) are step 3's full run 2's.

## Test runs (step 3, at 0f0d2b04, the committed list, no change under `mod/` since)

- Full client run 1: **green**, BUILD SUCCESSFUL in 10 min 18 s. Switch flat -> Nether 50: 15,420 ms; no AresHub for
  299 µs; failed switch back in 3,078 ms.
- Full client run 2: **green**, BUILD SUCCESSFUL in 10 min 19 s. Switch: 15,111 ms; no AresHub for 293 µs; failed
  switch back in 3,186 ms.
- The game's own path by hand (`rig/real-switch.sh switch1`, package 41's headless labwc rig with its restricted
  helper and virtual input, the development client as a session game, `mod/run/saves` empty): see the report's
  Verified. Pictures stayed in `.work/pkg48/switch1/` (not committed).
- Merging `origin/main` (8921d8ed) brought no change under `mod/` (package 44's design study and docs only).

## HomeSwitch as built (step 2)

- Phases: CLOSING_OLD -> MAKING (task) -> STAGING -> CLOSING_STAGING -> SWAPPING (task) -> OPENING -> idle; on failure
  FAILING -> RESTORING (task) -> RECOVERING -> idle with the chat line. A tick handler (END_CLIENT_TICK) waits for each
  world to close or open; it closes worlds itself (in tests through `runPendingCloseForTests`, see "Test runs") and
  schedules the opens with `client.schedule`; a step never assumes a close or open finished when its call returned,
  because the client game test framework defers `disconnect` and `doWorldLoad` called from a test task (its
  `MinecraftMixin.deferDisconnect`/`deferStartIntegratedServer`). Each waiting phase
  gives up after 2400 ticks (2 min) and restores.
- `screenComing` (while busy): TitleScreen or `setScreen(null)` with no level -> failure, the working screen instead;
  DisconnectedScreen -> failure; GenericMessageScreen / ProgressScreen -> the working screen; `null` with a level
  (the staging world's loading screen closing) -> the working screen, except while OPENING/RECOVERING. The
  LevelLoadingScreen is never replaced (its `tick()` closes it when the level is ready), only drawn over.
- A failure during FAILING/RESTORING/RECOVERING gives up (idle): the game's own screens show, the title screen is the
  floor. `start()` marks the first start decided, so such a title screen never makes a home.
- The fault for the client test: `HomeSwitch.failSecondRenameForTests(true)` (the second rename throws; swap undoes
  the first).

## Minecraft 26.2 facts the code relies on (not visible in our code)

- Every game menu comes from `Gui.setPauseScreen(boolean suppressMenu, boolean singleplayer)`; the only callers are
  `Minecraft.pauseGame(boolean)`, which `KeyboardHandler.keyPress` calls for Esc (F3+Esc passes `true`) and
  `Minecraft.pauseIfInactive` calls on focus loss. `new PauseScreen` appears nowhere else in the client jar. So one
  cancellable inject at the head of `Gui.setPauseScreen` catches Esc, F3+Esc, focus loss and any mod calling
  `pauseGame`.
- `Gui.setScreen(null)` with no level makes a `new TitleScreen()` itself; `Minecraft.disconnectFromWorld` and the
  disconnected screens set `new TitleScreen()`. So a `@ModifyVariable(at = HEAD, argsOnly = true)` on `Gui.setScreen`
  that treats `screen instanceof TitleScreen || (screen == null && minecraft.level == null)` as "the title screen
  is coming" catches every way to it.
- The first screen of a game start is set by `Gui.buildInitialScreens`' runnable when the resource load finishes
  (TitleScreen, or Quick Play's `--world` connect), while the loading overlay still fades out.
- `Minecraft.disconnect(Screen next, boolean)` shows "Saving world" (`GenericMessageScreen`) while the integrated
  server halts and saves, blocking the client thread but rendering frames, then sets `next`. Vanilla's Save and Quit
  is `level.disconnect(ClientLevel.DEFAULT_QUIT_MESSAGE)` then `disconnectWithSavingScreen()`.
- `WorldOpenFlows.createFreshLevel(name, settings, options, dims, parent)` is synchronous up to `doWorldLoad`, which
  itself disconnects any open world first (`disconnectWithProgressScreen`), starts the server, waits until it is
  ready and starts the connection. On an exception it sets `parent`; if `createWorldAccess` fails it shows a toast
  and `setScreen(null)` (the title screen).
- Fabric's `SERVER_STARTED` (where `NetherHome` provisions, saves everything and writes `aresos-home.provisioned`
  `complete`) fires before the server's tick loop sets `isReady`, and `doWorldLoad` connects only after `isReady`. So
  by the time a client player exists in a new home, it is provisioned (or provisioning failed and logged).
- `OptionsScreen(Screen last, Options, boolean inGame)`; the game menu uses `inGame = true`. Its Done returns to
  `last`.
- `BlockableEventLoop.execute` runs at once on the client thread; `schedule(Runnable)` queues for the next
  `runAllTasks` (start of the next frame).

## Part C: what the supervisor sees (read only; nothing under `os/` changes)

From `os/config/usr/libexec/aresos-desktop` and the mod's `ShellClient`/`ShellFocusClient`:

- **Heartbeats keep coming during a switch.** The mod's heartbeats come from the shell client's timer thread every
  5 s (`ShellClient.Settings.DEFAULT`), `ready` = whether `ShellFocusClient.readyWorld` last named a world. Leaving
  the world fires `ClientPlayConnectionEvents.DISCONNECT` -> `shell.world(null)`, so a `heartbeat` with
  `ready:false` goes out at once and every 5 s after. The supervisor's `on_helper_status` then sets
  `launch.ready = False`, resets `healthy_since` and moves IN_WORLD -> STARTING (`enter(STARTING)` shows no window
  and no cover). Confirmed.
- **No timer trips.** `heartbeats_stopped` (20 s, RECOVERY `unready`) is pending only while `launch.ready`; the
  start timeout (120 s, RECOVERY `slow_start`) only while `not launch.ever_ready`, and the first hub's `world_ready`
  set `ever_ready` for good. So a switch of any length stays in STARTING without a window. Confirmed.
- **The new world's `world_ready` brings it back.** `ready()` with `world == lock['world']` and `not launch.ready`
  runs `check_world` once, then IN_WORLD. Confirmed, provided the new AresHub is complete when that message comes.
- **`check_world` and a half-made AresHub.** `check_world` wants level.dat (or _old), `data/aresos/desktop.dat`,
  `data/aresos/nether_home.dat`, `aresos-home.provisioned` = `complete\n` and `aresos-home.properties`. It runs at
  `ready()` (above) and in `validate()` before every launch. Built the way the brief describes (archive, then create
  in place under `AresHub`), a game that dies while the new home is being made (seconds; longer for a Nether home's
  site search) leaves a half-made `AresHub` that the next start's `validate()` calls `world_damaged` ("Restore it
  from a backup"), although the old home is safe under its dated name. **PLAN-GAP, and the design below avoids it**:
  the new home is built under a staging name and moved into place only when complete.
- **The staging world must not report ready.** `ready()` for a world that is not the lock world still sets
  `launch.ready` and IN_WORLD. Harmless, but a guardian (package 25) asking `save_world` then would save the staging
  world. So `ShellFocusClient.readyWorld` answers null during the whole switch.
- **Package 46 (`save_world`, not merged yet):** during a switch the answer should be `no_world` (or the staging
  world's identity, which differs from `world_ready`'s). Whoever merges second makes 46's "is a world open" check
  also ask `HomeSwitch.busy()`. For `linux-aresos`: package 25 should compare `world_saved.world` with the lock
  world.
- **Game dies between the two renames** (old AresHub -> `AresHub-<date>`, staging -> `AresHub`): the next start finds
  no AresHub and says `world_missing` (hub_seen is true), as the brief expects. The window is two renames in one
  folder: microseconds. The text could mention the dated folder (`linux-aresos`'s call, below).
- **First start (B) mid-creation crash** (pre-existing in setup mode): a game that dies while the first flat home is
  made leaves a half-made `AresHub`; the next start says `world_damaged` with hub_seen false. Same as today's setup;
  noted for `linux-aresos`.

## Design (decided in step 1)

### A. The menu

- `AresOsMenuScreen` (client): title "AresOS"; buttons 200 wide "Back to the world", "Apps…", "Settings…",
  "New home…"; one gray hint line with the keys as bound (`AresOsClient` mode key and `options.keyInventory`,
  `getTranslatedKeyMessage()`). A `LinearLayout.vertical().spacing(4)` aligned like the game menu
  (`FrameLayout.alignInRectangle(layout, 0, 0, width, height, 0.5f, 0.25f)`), the screen's default in-world
  background (as AppsScreen). `isPauseScreen()` false. Esc closes it (default). Apps… is inactive in Build mode
  (AppsScreen closes itself outside Live: `AppsScreen.active` wants survival) with a tooltip: JUDGMENT-CALL.
- Gate: `HomeRules.menuReplacesGameMenu(HomeScreen.session(), AresOsClient.acceptsAppCommands(client))` (pure, main
  source set, unit tested). The app helper's state is not asked.
- `GuiMenuMixin`: inject at HEAD of `Gui.setPauseScreen`, cancellable: if the gate holds, set the AresOS menu (only if
  no screen is open, as vanilla) and cancel.
- `MinecraftFocusMixin`: unchanged rule (no menu on focus loss while `HomeScreen.active`). Without the helper, focus
  loss calls `pauseGame`, which now opens the AresOS menu; `FOCUS_RETURN.recordPause` also records the AresOS menu so
  it closes on return, as the game menu did.
- `AresOsClient.modeKeyInMenu`: also for the AresOS menu.
- Apps… opened from the menu: AppsScreen's Done returns to the menu (its parent). A drag (pick up to pin) needs the
  hotbar: from the menu it opens the inventory (`new InventoryScreen(player)`) instead of returning to the parent:
  JUDGMENT-CALL.

### A.5 The world switch (`HomeSwitch`, client, client thread only)

- `HomeCreateScreen` gets a create action (a `HomePlan`: manifest writer, `WorldOptions`, dimensions function), so
  the title screen keeps `HomeButton`'s create and the menu passes "confirm, then switch". Create -> a
  `ConfirmScreen` with the brief's text; No -> back to the create screen.
- Yes ->
  1. `GenericMessageScreen("Making your new home…")`; `level.disconnect(DEFAULT_QUIT_MESSAGE)`;
     `client.disconnect(working, false)` (saves and closes the old AresHub; "Saving world" shows meanwhile).
  2. Staging folder `AresHub-new-<date>` (never existing): create it, write the manifest, `NetherHome.createNewWorld`
     + `createFreshLevel(staging, same settings, options, dims, working)`. After it returns, no integrated server ->
     failure.
  3. Each client tick (END_CLIENT_TICK): when the staging player exists, `client.schedule` step 4 (the staging world
     is never drawn: the loading screen is still up). Server gone before that -> failure.
  4. Disconnect the staging world (saves). Check its files as `check_world` will (manifest, provisioned `complete`,
     level.dat, both data files). Then `HomeSwap.swap`: rename `AresHub` -> `AresHub-<date>` (HomeButton.archive's
     naming) and staging -> `AresHub`; if the second rename fails, the first is undone.
  5. `openWorld("AresHub", onCancel)`. Joined -> done; he arrives in Live (`NetherHome.arrive`).
- Failure anywhere: open the old home (moving it back first if it was moved) with a chat line queued for the next
  join: "Couldn't make the new home: <why>. Your home is as it was." A staging folder that failed stays (nothing is
  deleted).
- While busy: `ShellFocusClient.readyWorld` answers null; any title screen is replaced by the working screen and
  turns into the failure path (the `Gui.setScreen` hook).
- Test hook: a fault to inject at the second rename (the old home has been moved and must come back).

### B. The first start

- In the `Gui.setScreen` HEAD hook: when the title screen is coming and `HomeRules.firstStart(session,
  decidedBefore, hubFolderExists (NOFOLLOW_LINKS), switching)` says CREATE_FLAT: mark decided, return a
  `GenericMessageScreen("Making your home…")` instead, and `client.schedule(() -> HomeButton.createFlat(client, new
  TitleScreen()))`. Its error screen's OK sets that TitleScreen, which now passes (decided). So the title screen
  never shows; at most the working screen while the loading overlay fades.
- Decided once per game start: at the first title screen. `forTests` resets it.

## Notes for the report (collect here; the Report heading comes last)

- JUDGMENT-CALL candidates: F3+Esc (the game's "pause without a menu") opens the AresOS menu too; focus loss in a
  session's desktop world without the helper opens the AresOS menu (package 40's rule with the helper is unchanged)
  and closes it again on return like the game menu did; Apps… inactive in Build mode with a tooltip; a drag in the
  Apps screen opened from the menu ends in the inventory (the hotbar must be visible to pin); the confirm buttons'
  words ("Make the new home" / Cancel, to decide in step 2); "New home" takes two loads of the new world (staging,
  then the real open) and the "Saving world" screen shows twice.
- PLAN-GAP: building the new home in place under `AresHub` (the brief's order) leaves a half-made AresHub that
  `check_world` calls damaged if the game dies meanwhile; staging avoids it (part C).
- Measure for the report: how long "no AresHub on disk" lasts (two renames; log the nanoseconds in HomeSwitch), and
  how long the whole switch takes in the test.

## Code state

See `git log`. Step 1's commit: this file, plus whatever of A.1-A.4/A.6 is listed under Done.

## Report

(For the lead to commit as `reviews/48-home-menu/REPORT.md`; a Claude builder cannot create that file.)

### Done

- **A. The AresOS menu** (`AresOsMenuScreen`, `GuiMenuMixin`, `HomeRules.menuReplacesGameMenu`): in a game the session
  started and in a desktop world, with or without the app helper, the AresOS menu opens wherever the game would open
  its menu. How every way in is caught: Minecraft 26.2 makes every game menu in one place, `Gui.setPauseScreen`, whose
  only caller is `Minecraft.pauseGame`, which Esc and F3+Esc (`KeyboardHandler.keyPress`) and focus loss
  (`Minecraft.pauseIfInactive`) call; `new PauseScreen` appears nowhere else in the client jar. One cancellable inject
  there catches all of them and any mod calling `pauseGame`. Items as the brief lists, 200-wide game buttons in a
  centred column where the game menu stands, the in-world background, not pausing; G says "Close the menu before
  switching AresOS mode"; fits the 240-high GUI (checked and pictured).
- **A.5 New home…** (`HomeSwitch`, `HomeSwap`, `HomePlan`, `HomeWorkingScreen`, `GuiScreenMixin`,
  `LevelLoadingCoverMixin`): the home choice (`HomeCreateScreen` now takes a create action), one confirmation with the
  brief's text ("Make the new home" / Cancel; Cancel goes back to the choice as it was), then "Making your new home…"
  from the click to the new home. The staging design the lead approved: the old home is saved and closed; the new one
  is made in `AresHub-new-<date>` with the title screen's settings and manifest; once his player is in it (so it is
  provisioned) it is closed, checked as `check_world` checks a home (`HomeSwap.checkComplete`: folder, level.dat or
  level.dat_old with Data, desktop marker on, the saved home's fields, provisioned `complete\n`, the manifest); then
  AresHub -> `AresHub-<date>` (the title screen's naming, now `HomeSwap.datedName`) and staging -> AresHub, the first
  undone if the second fails; then AresHub opens and he arrives in Live. Any failure reopens the old home (moved back
  if moved) with "Couldn't make the new home: <why>. Your home is as it was."; a failed staging folder stays. The
  staging world is silent to the supervisor: `ShellFocusClient.readyWorld` answers null for the whole switch, so no
  `world_ready` and only `ready:false` heartbeats. No title screen is ever set: while a switch runs, a title screen
  or `setScreen(null)` without a world counts as a failure and becomes the working screen, the game's message and
  progress screens become the working screen, and its loading screens (left in place, they close themselves when the
  level is ready) draw the same line.
- **B. The first start** (`FirstStart`, `HomeRules.firstStart`, `GuiScreenMixin`): the first title screen of a game
  start, in a session, with no `AresHub` folder (NOFOLLOW_LINKS), becomes "Making your home…" and the flat home is
  made through `HomeButton.createFlat`'s path; its error screen's OK leads to the title screen with the AresOS button.
  Once per game start; a switch also marks it decided.
- **D.** `AppsScreen.pressed` is cleared in `init()` and on every left press before the rows see it.
- **E.** `docs/design/HUB.md` (a package 48 section after package 40's corrections; "Esc still opens the game menu"
  and the Live's-rules line fixed), `mod/README.md` (the title screen is no longer the way in for a session; the
  menu, New home, the first start, the tests).
- **Tests:** `HomeMenuClientGameTest` (new, last client test), `HomeScreenClientGameTest` (Esc expects the AresOS
  menu), `ScreenLog`/`ScreenLogMixin` (every screen `Gui.setScreen` stores), unit tests `HomeRulesTest`, `HomeSwapTest`.

### Verified

- `mod/dev/build.sh` (after merging `origin/main`, at 5f18b483): BUILD SUCCESSFUL, 239 unit tests passed, "All 104
  required tests passed" (server game tests).
- Trimmed local client run (HomeScreen + HomeMenu only, not committed): green, 57 s.
- Full client runs with the committed list, both at 0f0d2b04 (the final code: merging `origin/main` afterwards brought
  no change under `mod/`): **run 1 green, BUILD SUCCESSFUL in 10 min 18 s; run 2 green, BUILD SUCCESSFUL in 10 min
  19 s**, `HomeMenuClientGameTest` last in both ("48 home menu checks passed: ..."). An earlier full run, before the
  switch closed its worlds from the client tick, hung: closing a world from a scheduled task deadlocks with the client
  test framework's lock-step (the client waits in `IntegratedServer.halt` for the server thread, which waits at the
  framework's phase barrier for the client). The framework only lets a test task close a world, so in the tests
  (`HomeSwitch.closeFromTestTasksForTests`) the test's wait loop runs each pending close from `runOnClient`; in the
  game the switch closes them from the client tick, as the game does when a server says goodbye.
- **The game's own switch path, checked by hand** (the client tests can't run it): `reviews/48-home-menu/rig/real-switch.sh`
  starts the development client as a session game in package 41's headless rig (its own labwc, the worktree's
  `aresos-shell` with 40 test apps, virtual keyboard and pointer; never the owner's screen) with empty
  `mod/run/saves`. The first start made the flat home without a title screen ("First start: no AresHub yet, making
  the flat home", joined 3 s later, "The town is built: 40 logos"). Esc opened the AresOS menu; New home…, Flat,
  Create, "Make the new home" (pictures of each step): "Making your new home…" over the menu background, the old home
  saved and closed, the new one built in `AresHub-new-2026-11-16_17-46-11-074`, joined and left, then "in place as
  AresHub; the old one is AresHub-2026-11-16_17-46-12-645; no AresHub on disk for 324 µs", joined, "New home: ready
  3225 ms after he chose it". He stood in the new flat home in Live; Esc opened the menu there again; closing the
  window saved and quit at once. The saves held exactly `AresHub` and `AresHub-2026-11-16_17-46-12-645`, no
  `AresHub-new-*`, both with `aresos-home.provisioned` = `complete`, level.dat and the AresOS data files. The helper
  saw "desktop world ready", "no longer ready" at the switch, "ready" once more for the new AresHub: the staging world
  never reported ready. No hang. The log lines: `reviews/48-home-menu/rig/real-switch-switch1.txt`. A failed switch
  was not driven in the game (only in the client test).
- `HomeMenuClientGameTest` checks: Esc in a normal world in a session, and in a desktop world outside a session,
  opens `PauseScreen`; in a session's desktop world `AresOsMenuScreen`. The title screen with its AresOS button
  stays outside a session and with an AresHub folder present (whose contents are untouched). The first start makes
  the flat home, open, in Live, provisioned, and no `TitleScreen` is ever stored. In the flat home: the real Esc key
  opens the menu with exactly the four buttons, the title and the hint; the game is not paused and the server's game
  time moves 20 ticks in 20; G shows the line and changes nothing; Back, Esc, F3+Esc (`pauseGame(true)`); Apps… and
  Settings… open and their Done comes back; Apps… inactive in Build mode. Cancel (at the confirmation, then at the
  choice) leaves the same server and the same saves. Flat to Nether 50 with a gold block placed just before: the new
  AresHub is the Nether home with seed 50, passes `checkComplete`, he is in it in Live, exactly one new folder
  `AresHub-<date>` holds the flat home and (opened afterwards) the gold block, no `TitleScreen` stored. A failure
  injected at the second rename: back in the old Nether home (a new server), the chat line, only the staging folder
  added, no title screen stored. The test leaves the saves as it found them.
- **Measured** (trimmed run): the switch from "Make the new home" to standing in the new home took **18.95 s** for
  flat -> Nether seed 50 (two loads and the Nether site search); the moment without an AresHub on disk (two renames)
  lasted **427 µs**. The failed switch was back in the old home after 3.56 s. In the two full runs: **15.42 s and
  15.11 s** for the switch, **299 µs and 293 µs** without an AresHub, the failed switch back after **3.08 s and
  3.19 s**. In the game itself (the rig above), flat to flat: **3.2 s**, **324 µs**.
- Screenshots: `reviews/48-home-menu/screenshots/` (the menu at 1280x720, GUI scale 2; at the smallest GUI, 426x240;
  the working screen).

### Not verified

- In his real session: the supervisor's view of a switch (STARTING without a window, then IN_WORLD on the new
  `world_ready`) is read from the code only (part C, above); no fake-helper test drives `ShellFocusClient` through a
  switch. The first start under the real supervisor's setup mode (the test drives it with the session flag forced).
- How the double load feels on his laptop (the loading screens show the working line; nothing else of the second
  load shows).
- A failed switch in the game's own path (the rig drove only a successful one; the failure path ran in the client
  tests, where the test task closes the worlds).
- In the rig the new flat home's town came in two chat lines, "The town is built: 32 logos" and 5 s later "The town
  changed: 8 logos built", where the first start said "built: 40 logos" in one. All 40 logos stand in the end. Not
  looked into; a guess: the staging world generated the chunks around the start, which then load at once, while the
  farther logos' chunks are generated only after the open. Cosmetic, and the town's lines are package 36's.

### JUDGMENT-CALL

1. **F3+Esc** (the game's "pause without a menu") opens the AresOS menu too. Alternative: let it pause without a
   menu. Chosen because the brief wants every way to the game menu caught, and a pause with nothing on screen reads
   as a hang in a home screen. Cheap to change (one condition in `GuiMenuMixin`). Agreed by the lead.
2. **Focus loss without the helper** opens the AresOS menu (package 40's rule with the helper is unchanged: nothing
   opens) and it closes again when the focus comes back, as the game menu did. Agreed by the lead.
3. **Apps… is greyed out in Build mode** with a tooltip ("Apps open in Live mode. Back to the world, then G."),
   because the Apps screen closes itself outside Live. Agreed by the lead.
4. **A drag out of the Apps screen opened from the menu ends in the inventory** (the hotbar must be visible to pin);
   from the inventory's Apps… it returns to the inventory as before. Agreed by the lead.
5. **The confirmation's buttons:** "Make the new home" and Cancel; the brief's question unchanged (it still fits the
   staging design: the old home is kept under a dated name, nothing is deleted).
6. **New home loads the new world twice** (staging, then the real open) behind one "Making your new home…" screen;
   the game's loading screens show that line instead of their terrain progress. Approved by the lead.
7. **The working screens' look:** one white line over the game's own menu background (panorama, blur, menu
   texture), as the game's "Saving world"; no progress bar.

### PLAN-GAP

- Building the new home in place under `AresHub` (the brief's order) would leave a half-made AresHub that the
  supervisor's next start calls damaged if the game died meanwhile; built under a staging name it never is. Approved.
- **Package 46** (`save_world`, PR #92) was not on `origin/main` when this branch was finished, so `save_world` does
  not yet answer `no_world` during a switch. Whoever merges second: make 46's "is a world open" check also ask
  `HomeSwitch.busy()` (public, true from "Make the new home" until he is in a home again), with a test.
- **Package 46 also brings a gate:** `HomeScreen.home(client)` = `session() && AresOsClient.acceptsAppCommands(client)`,
  the same rule as this package's `AresOsMenuScreen.replacesGameMenu` (`HomeRules.menuReplacesGameMenu(session,
  desktop world)`), used there to hide the "Saving world" text. Whoever merges second keeps one of the two and has
  the other call it (not two copies of the rule). During a switch this package already replaces every "Saving world"
  screen with "Making your new home…" (`HomeSwitch.screenComing`), so 46's hiding and this replacement do not clash;
  the merge should keep the switch's replacement first.

### For linux-aresos (os/, not changed here)

- **Setup mode:** with this package a session game that reaches its first title screen without an AresHub makes the
  flat home itself and opens it (he arrives in Live mode); the title screen does not show. The window text "On the
  title screen click AresOS…" no longer matches; suggested: "Making your home… (the first start takes a moment)".
  If creation fails the title screen with the AresOS button shows as before, so the old text still fits that case.
- **`forget_hub`'s message** may now say that the next start makes a fresh flat home by itself.
- **During New home** the mod sends `ready:false` heartbeats (IN_WORLD -> STARTING, no window, no cover; no timer
  trips because `ever_ready` is set and `heartbeats_stopped` is pending only while ready), then `world_ready` for
  AresHub when he is in the new home (`check_world` passes: the new home is checked before it is moved into place).
  A switch takes 15 to 19 s for a Nether home (measured in the tests) and about 3 s for a flat one (measured in the
  game), the helper's "ready" coming back at its end.
- **`world_missing`** can now happen if the game dies in the ~0.3 ms between the two renames; the old home is then
  `AresHub-<date>` (the newest) and the new one `AresHub-new-<date>`. The text could say so.
- **Package 25:** check that `world_saved`'s `world` equals the locked world; `save_world` during a switch should get
  `no_world` (above).
- **First start dying mid-creation** (pre-existing, as in setup mode today): a game that dies while the first flat home
  is made leaves a half-made AresHub that the next start calls damaged (hub_seen false).
- A failed New home leaves `AresHub-new-<date>` folders in the saves; nothing cleans them up.

### Open questions

- None that block. Whether the owner wants a progress hint during a long Nether site search (the working line shows
  for the whole 15 to 20 s) is for his try-out.
