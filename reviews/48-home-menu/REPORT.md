# Package 48: report

Builder: Claude agents (Opus 5.5), in three steps. Brief: `briefs/48-home-menu.md`. Branch `pkg/48-home-menu`, PR #94.


(For the lead to commit as `reviews/48-home-menu/REPORT.md`; a Claude builder cannot create that file.)

## Done

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

## Verified

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

## Not verified

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

## JUDGMENT-CALL

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

## PLAN-GAP

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

## For linux-aresos (os/, not changed here)

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

## Open questions

- None that block. Whether the owner wants a progress hint during a long Nether site search (the working line shows
  for the whole 15 to 20 s) is for his try-out.
