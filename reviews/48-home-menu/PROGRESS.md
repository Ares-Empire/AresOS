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

## Left, in order

1. Run the client tests (trimmed list locally to iterate, never committed), fix, screenshots into
   `reviews/48-home-menu/screenshots/`.
2. Two green full client runs (committed list) and the full `mod/dev/build.sh`.
3. Merge `origin/main` (package 46's `save_world`: if merged by then, make it answer `no_world` while
   `HomeSwitch.busy()`, with a test; otherwise PLAN-GAP in the report).
4. The report (heading "Report" below), then the ready PR.

## HomeSwitch as built (step 2)

- Phases: CLOSING_OLD -> MAKING (task) -> STAGING -> CLOSING_STAGING -> SWAPPING (task) -> OPENING -> idle; on failure
  FAILING -> RESTORING (task) -> RECOVERING -> idle with the chat line. A tick handler (END_CLIENT_TICK) waits for each
  world to close or open and schedules the next step with `client.schedule`; a step never assumes a close or open
  finished when its call returned, because the client game test framework defers `disconnect` and `doWorldLoad`
  called from a test task (its `MinecraftMixin.deferDisconnect`/`deferStartIntegratedServer`). Each waiting phase
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
