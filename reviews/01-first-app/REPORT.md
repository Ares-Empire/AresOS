# 01 — First app item and Live mode

Branch: `pkg/01-first-app`. PR: https://github.com/carlsenares/AresOS/pull/1.

The original 01 report below is historical. The [01b follow-up](#01b-follow-up)
supersedes its ten-second focus window and protection in every survival world.

## Done

- **Project:** `mod/` starts from the official Fabric example mod's `26.2`
  branch, commit `1ce1c77a77ddbf7587e0d171ea369051668a67a6`. Pins Minecraft
  26.2, Java 25, Loader 0.19.5, API 0.161.0+26.2, Loom 1.19.2, and Gradle
  9.8.0. Includes both wrapper scripts, the wrapper jar and distribution checksum,
  the template license, split client/common sources, and development instructions
  in `mod/README.md`. No game textures, fonts, sounds, or logos are included.
- **Config:** `AppDefinition` / `AppsConfig` create `config/aresos/apps.json` in
  the game directory with the specified Notepad default. The format is a JSON
  array. Commands remain argument lists; saves use a temporary file and atomic
  replacement where supported. Invalid JSON/entries/duplicate ids get a unique,
  byte-for-byte `.broken-<uuid>` backup before defaults are written. I/O failures
  log the problem and use in-memory defaults without deleting the original.
- **Items and joining:** `AppItems` registers `aresos:app` and the persistent,
  network-synchronized `aresos:app_id` component. Stacks have size one, the
  app's name and the configured vanilla `item_model`. Pinning checks the whole
  inventory, including offhand, and fills only free hotbar slots. Full hotbars
  are left alone. `/aresos give <app>` is registered for integrated servers and
  works without cheats.
- **Launching:** `AppItem` invokes the client handler only. Its continuous-use
  state suppresses vanilla's held-click repeats until release, with no use
  animation or movement penalty. `AppLauncher` has Windows and Linux
  implementations selected by OS. `ProcessBuilder` runs off the game thread,
  without a shell or waiting for exit; streams do not hold up the game. Unknown
  ids and failures produce action-bar errors.
- **Focus:** `MinecraftFocusMixin` intercepts only vanilla's `pauseIfInactive`
  path. `FocusReturn` records the resulting pause screen by identity and clears
  it on focus return. Esc-opened menus, replacement screens, unrelated focus
  loss, and quick returns before a menu exists are preserved.
- **Live/Build:** `LiveMode` rejects damage and death for survival players,
  keeps hunger/saturation at 20 each server tick, and teleports players below
  the world's minimum Y to their personal respawn or the vanilla fallback.
  Respawn-anchor charges are not consumed and fall distance is cleared. The
  AresOS Controls category contains the default G binding. Its C2S payload
  toggles survival/creative only for the singleplayer host; dedicated-server
  requests and integrated-server guests are rejected.
- **Tests:** 11 unit tests; 7 AresOS server game tests; one client suite using an
  injected fake launcher, with test-only accessors and three saved screenshots.
  Production jars contain neither fake launchers nor test accessors.

## Verified

Environment: Windows 11, Temurin `25.0.4.1+1-LTS`. On 2026-10-21 the Modrinth
[26.2 Fabric API version list](https://api.modrinth.com/v2/project/fabric-api/version?game_versions=%5B%2226.2%22%5D)
returned `0.161.0+26.2` as the newest release. Fabric's
[loader metadata](https://meta.fabricmc.net/v2/versions/loader/26.2) marked
`0.19.5` stable; the newer 0.20 versions were not stable.

Final command, run inside `mod/`:

```powershell
.\gradlew.bat build runClientGameTest
```

Exit code **0**. Full stdout/stderr: [verification.txt](verification.txt).
Selected exact output:

```text
All 8 required tests passed :)
AppsConfigTest > firstStartWritesDefaults() PASSED
AppsConfigTest > emptyListIsAnIntentionalConfig() PASSED
AppsConfigTest > invalidFieldsAndDuplicateIdsRecoverWithoutDiscardingOriginal() PASSED
AppsConfigTest > failedReadDoesNotReplaceOwnersPath() PASSED
AppsConfigTest > brokenFileIsBackedUpByteForByteBeforeDefaults() PASSED
AppsConfigTest > roundTripPreservesArgumentsUnicodeAndPinnedChoice() PASSED
AppsConfigTest > repeatedFailuresKeepEveryBackup() PASSED
FocusReturnTest > onlyClosesTheCapturedFocusLossScreen() PASSED
FocusReturnTest > returnBeforeMenuExistsDoesNotCloseAnything() PASSED
FocusReturnTest > unrelatedFocusLossAndFailedOrExpiredLaunchDoNotCloseMenus() PASSED
FocusReturnTest > preservesEscMenuAndReplacementScreen() PASSED
Client checks passed: pinned Notepad, one launch per click, host-only G toggle without cheats, focus return, action-bar errors, give command, and three screenshots
Stopping!
BUILD SUCCESSFUL in 40s
18 actionable tasks: 6 executed, 12 up-to-date
```

- Eight server tests means **seven AresOS tests plus Fabric's sanity test**.
  Damage checks run against every registered damage type and explicit fall and
  mob-attack damage. The lava player is confirmed inside lava while its embedded
  network connection ticks normal player physics. The fixture acknowledges
  client loading and asserts vanilla join immunity is absent. Food checks apply
  sprint/jump statistics and exhaustion for 120 ticks, including normal food
  processing; they do not call the protection helper themselves. Void recovery
  runs through the registered server tick callback and verifies personal spawn
  and cleared fall distance. Pinning covers occupied slots, repeated placement,
  existing inventory/offhand copies, full hotbars, and unpinned apps. Dedicated
  mode requests and invalid item looks are also checked.
- The client suite creates a survival world with cheats explicitly disabled.
  It checks Notepad's id, name, model and stack size; holds right-click for 16
  ticks and gets exactly one fake call with `[notepad.exe]`; then checks a second
  click. Actual G input changes both client and server modes both ways. A guest
  is rejected. The actual vanilla focus-loss method is exercised with simulated
  window focus, including preservation of an Esc menu and unrelated pause.
  Unknown ids, an injected failed future, and the actual client-issued give
  command are checked. **No test starts a real app.**
- Screenshots generated by that suite and visually inspected:
  [Notepad hotbar](screenshots/0000_hotbar-notepad.png),
  [Build](screenshots/0001_build-mode.png),
  [Live](screenshots/0002_live-mode.png). The book icon renders; the survival
  bars disappear in Build and return full in Live.
- `jar tf mod/build/libs/aresos-0.1.0.jar`: inspected the packaged classes and
  assets; only production classes and the AresOS language JSON are present.
  `git diff e37c140 --check`: exit 0, no output after whitespace cleanup.
- After the final run, a process query restricted to this worktree's Java dev
  clients printed **`Remaining dev clients: 0`**. The game and integrated server
  shut down normally. The owner's Minecraft/Lunar folders were not accessed.

Earlier verification and fixes, recorded so an initial green result is not
mistaken for the final evidence:

- `genSources` initially failed: `Plugin net.fabricmc:fabric-loom:1.19.2
  requires at least Gradle 9.8.0. This build uses Gradle 9.7.1.` Updated the
  wrapper; the next run printed `BUILD SUCCESSFUL in 1m 39s`.
- `compileJava`, `build`, and `build compileGametestJava` initially reported
  compile errors for renamed 26.2 APIs (payload registry, food/teleport/profile,
  client HUD message, and block-position center). Fixed against generated
  sources. The first successful `build` printed `BUILD SUCCESSFUL in 24s`, with
  11 unit tests and then-seven server tests.
- The first `runClientGameTest` exposed the command restriction's null-server
  placeholder during join: `Couldn't place player in world` and
  `java.lang.NullPointerException`. Changed registration to the integrated
  environment. The harness remained on the disconnected loading screen, so its
  exact worktree-owned client process was stopped; that invocation exited 1.
  An immediate retry could not open the still-held output file and did not
  launch Gradle. The next `runClientGameTest` passed: `BUILD SUCCESSFUL in 29s`.
- Adding an explicit lava-presence assertion caused a combined
  `build runClientGameTest` to fail: `Lava test player was not in lava on tick
  60`, `1 required tests failed :(`, `BUILD FAILED in 14s`. The embedded
  connection needed normal player ticking, and its handshake needed to remove
  vanilla join immunity. Fixed the fixture and kept the stronger assertion.
  The next combined run passed in 41s. The final run above also passed, after
  adding explicit client completion output and the five-minute task timeout.

The final client log contains an anisotropic-filtering option error and offline
dev-session Realms/profile-key authentication errors (401); the suite still
completed. The `Could not launch app notepad` warning with `Test failure` is the
deliberately injected failure-path check, not a real attempted process launch.

## Not verified

- Real Notepad creation, Windows foreground behavior, and closing Notepad with
  X to return physically to Minecraft. Tests deliberately substitute the
  launcher. To check: inside `mod/`, run `.\gradlew.bat runClient`, create/open
  a survival world, right-click Notepad once, close it, and confirm the world is
  immediately usable. Repeat with a manually opened Esc menu and confirm it
  remains open. Close the dev client afterward.
- Linux process startup on a Linux machine. Its implementation compiles, but
  the shared default `notepad.exe` needs a Linux command in the config.
- A second physical LAN client, cross-dimension void recovery, and a charged
  respawn anchor in an actual Nether world. Host authorization is exercised
  programmatically; the void test uses a forced personal Overworld spawn.
- An independent package review is still the next workflow step; this report
  is implementation evidence, not that review.

## JUDGMENT-CALL

1. **Associate only the first focus loss within ten seconds of launching.**
   Chose a bounded window and exact screen identity. Rejected remaining armed
   indefinitely because a later unrelated Alt-Tab could be treated as an app
   return, and rejected native OS window tracking for this simple cross-platform
   package. A process that takes more than ten seconds to take focus may leave
   the vanilla pause menu open. Changing the interval costs one constant and
   associated tests; stronger attribution would require more launcher/window
   integration. Owner should review this timing choice before merge.
2. **Live protection applies to every survival player while this mod is loaded.**
   This follows the brief's survival-based definition, including guests and
   other development worlds; only mode switching is host-restricted. Rejected
   adding a per-world opt-in or host-only protection because neither is in this
   package. Changing policy later is localized to `LiveMode.isLive` and its
   tests. Owner should be aware before using the mod with ordinary survival
   worlds.

## PLAN-GAP

- The official 26.2 template currently carries Loom 1.18-SNAPSHOT / Gradle
  9.7.1, while this brief asks for Loom 1.19.x. The stable 1.19.2 plugin requires
  Gradle 9.8.0; upgraded the wrapper rather than downgrading the requested Loom.
- The brief does not define behavior for a syntactically valid but missing
  vanilla item look. It now warns and uses the book model without discarding
  the app configuration. Changing that fallback is one method.
- The brief leaves exhausted hotbars and config reload unspecified. Pinning
  retries on the next join, and config edits take effect after restarting the
  client. These choices avoid new screens, overflow inventory rules or watchers.

## Open questions

- Owner acceptance of the ten-second focus window and survival-world coverage.
- Human confirmation of the real Windows Notepad/focus round trip above.
- No implementation blockers remain. The branch is pushed and PR #1 is open
  against `main`; it has not been merged.

## 01b follow-up

### Done

- **Findings 1/2:** `AppInput` handles actual mouse/keyboard use presses and
  releases, independently of vanilla item-use state. `MinecraftAppInputMixin`
  consumes app use before block/entity interactions and held-button repeats.
  `AppItem` no longer launches or starts continuous item use.
- **Finding 3:** every launch gets a generation token; failures cancel only
  their own focus tracking. The window is one constant, **30 seconds**.
- **World rules:** `DesktopWorld` stores `enabled` in the save's
  `data/aresos/desktop.dat`, covering every dimension. Missing means normal.
  Host-only `/aresos desktop on|off` works without cheats. Protection, food,
  void rescue, pins, G, and `/aresos give` require the marker. Normal G shows
  "Not an AresOS world". Enabling applies immediately; disabling keeps existing
  items/game mode. Returning to Live retries safe pinning. Updated `mod/README.md`.
- Added four normal-world server tests, token/expiry unit tests, and client
  regressions for click edges, targets, overlapping launches, marker commands
  and persistence. Separate server-test environments isolate the save-wide flag.

### Verified

Windows 11, Temurin `25.0.4.1+1-LTS`. Final code: `dad777d`, `5413b29`.
Commands below ran inside `mod/` unless stated otherwise.

- `.\gradlew.bat compileJava compileClientJava compileGametestJava test`: exit
  **0**, **13 unit tests passed**, including cancellation and the exact 30-second
  boundary. [Output](01b-unit-verification.txt): `BUILD SUCCESSFUL in 5s` /
  `7 actionable tasks: 6 executed, 1 up-to-date`.
- `.\gradlew.bat build runClientGameTest`: final exit **0**.
  [Full output](01b-verification.txt), with these exact completion lines:

  ```text
  All 12 required tests passed :)
  01b client checks passed: normal-world defaults, marker on/off and reopen, host-only commands without cheats, held-click slot switch, between-tick clicks, door/chest/villager interception with vanilla controls, overlapping launch focus return, Build/Live, errors, give command, and four screenshots
  Stopping!
  BUILD SUCCESSFUL in 54s
  18 actionable tasks: 9 executed, 9 up-to-date
  ```

  Server: **11 AresOS tests + Fabric's sanity test**. All existing desktop tests
  pass when marked; normal-world tests allow actual fall damage/death, drain
  hunger, take void damage without rescue, and place no pins on join or retry.
  Client: held slot 1 -> 2 -> 1 launches once; two release/repress pairs inside
  one client-thread operation each launch again. Door/chest/villager clicks
  launch once without changing the door or opening any client/server container.
  Empty-hand controls then open all three targets. A fails after B captures its
  pause screen, and B's return still works. Tests never start real programs.
  The client uses cheats-off survival, rejects G/give before marking and a
  guest's desktop-off command, checks Build/Live, and reopens the save with pins
  when on and without pins when off. Existing apps still launch in normal worlds.
- Four final screenshots rendered and visually inspected:
  [normal](screenshots/0000_01b-normal-world.png),
  [marked hotbar](screenshots/0001_01b-hotbar-notepad.png),
  [Build](screenshots/0002_01b-build-mode.png),
  [Live](screenshots/0003_01b-live-mode.png). Normal has no apps; marked shows
  the book; survival bars disappear in Build and return full in Live.
- Repo-root `jar tf mod/build/libs/aresos-0.1.0.jar`: exit **0**, production
  classes/language JSON only; no test code, environments, or copied game assets.
  `git diff --check`: exit **0**, no whitespace errors.
- `.\gradlew.bat --stop`: exit **0**, `Stopping Daemon(s)` / `1 Daemon stopped`.
  Process query: `Remaining worktree Java processes: 0`. No other Gradle version
  was started; the dev client closed normally.

Earlier runs: initial compile failed with no
`displayClientMessage(MutableComponent,boolean)` on `ServerPlayer`
(`BUILD FAILED in 7s`); corrected to `sendSystemMessage(Component, boolean)`.
The first combined run passed (`BUILD SUCCESSFUL in 50s`,
`18 actionable tasks: 7 executed, 11 up-to-date`). Final screenshot capture waits
for the earlier normal-world message to expire and clears old chat. No tests
were weakened. Known offline-dev authentication/anisotropic-option messages
remain in the log; both launcher warnings are deliberate fake failures.

### Not verified

Physical Notepad/native Windows focus and close-X behavior, Linux launching,
a second LAN machine, and actual cross-dimension/Nether-anchor rescue still need
human checks. Use `runClient` and `/aresos desktop on` in its isolated world;
close the client afterward. Keyboard rebinding compiles and its mixin loads;
click regressions use default right mouse. Independent 01b review is pending.

### JUDGMENT-CALL

- Chose server SavedData for one save-wide marker (following
  [Fabric's mechanism](https://docs.fabricmc.net/develop/serialization/saved-data)).
  Rejected global config/per-dimension flags to prevent unrelated saves or
  dimensions inheriting inconsistent rules. A later file/codec change needs
  a small migration; changing the boolean uses the command.
- Enabling applies immediately; disabling preserves items and game mode.
  Rejected item deletion/forced survival because those change player state
  beyond restoring vanilla rules. Give is host-only like desktop administration.
  Policy changes are localized to `setEnabled` and command guards.

The owner's 30-second and marked-world-only decisions supersede both original
01 judgment calls; neither remains an unresolved owner question.

### PLAN-GAP

No blockers. Existing unmarked dev worlds need `/aresos desktop on` once.

### Open questions

Only the human checks and follow-up review above. PR #1 remains open; no merge.

## 01c follow-up

**Done:** `dc51c5c` preserves use press/release edges but queues their count.
`startUseItem` resolves the held app after vanilla hotbar selection and consumes
app clicks before target interaction, including held-button repeats. Each use
attempt consumes its edge even on an empty slot; unused edges expire at tick end.
Client tests inject real number-key or scroll callbacks followed by use
press/release in one client-thread operation, covering empty -> app, A -> B
(exactly B's command), and app -> empty for both selection methods. App B and
its configuration accessor exist only in tests; the fixture restores config/items.
The earlier two between-tick release/repress pairs still require exactly two
additional launches, now checked after vanilla dispatch.

**Verified:** Windows 11 / Java `25.0.4.1+1-LTS`. Inside `mod/`, final
`.\gradlew.bat build runClientGameTest --console=plain` exited **0**;
[full output](01c-verification.txt):

```text
All 12 required tests passed :)
BUILD SUCCESSFUL in 1m
18 actionable tasks: 5 executed, 13 up-to-date
```

All 01/01b client checks and all six new selection cases passed with a fake
launcher. All 13 unit tests actually ran and printed `PASSED` in the
[first combined run](01c-first-verification.txt); the final unit task was
up-to-date. Server tests ran again in the final run (11 AresOS + Fabric sanity).
Inspected all five screenshots, including [selected app B](screenshots/0004_01c-selected-app-b.png).
Preserved the four screenshot modifications present before this run byte-for-byte.
Repo-root `jar tf mod/build/libs/aresos-0.1.0.jar` exited 0: production classes
and language JSON only, with no test accessors/configuration. `git diff --check`
exited 0 with no output. `.\gradlew.bat --stop` exited 0 and printed
`Stopping Daemon(s)` / `1 Daemon stopped`; the process query printed
`Remaining worktree Java processes: 0`. No other Gradle version was started.

Earlier checks: before the production fix, `.\gradlew.bat runClientGameTest
--console=plain` exited 1: `Number key 2 -> 0: wrong launches: []` /
`BUILD FAILED in 39s`, reproducing the review finding. The first combined run
exited 1 (`BUILD FAILED in 51s`) after unit/server success because my scroll
fixture expected two slots from one callback: `Scroll 2 -> 0: scroll did not
select target`. Corrected the fixture to use single-step selection, including
8 -> 0 wraparound; retained its target-slot assertion. Existing offline-dev
authentication/anisotropic-option messages and deliberate fake-launch failures
remain in the logs.

**Not verified:** physical input timing and real Notepad/native focus behavior;
all launch commands were intercepted by the fake launcher.

**JUDGMENT-CALL:** none beyond the brief's vanilla input ordering.
**PLAN-GAP:** none. **Open questions:** only the existing human checks and review.
