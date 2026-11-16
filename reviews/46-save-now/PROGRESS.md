# Package 46: progress

Builder: Claude agent (Opus). Brief: `briefs/46-save-now.md`. Branch `pkg/46-save-now`.

## Done

1. **Protocol and unit tests** (commit af029332).
   - `mod/src/main/java/dev/aresos/shell/LifecycleClient.java`: gate, `lifecycle_hello`, `save_world` /
     `world_saved`, joining, reconnect with backoff, quiet logging. The game side is the `LifecycleClient.Game`
     interface (one method, `save(Runnable starting)`).
   - `ShellClient.worldObject` is package-visible so `world_saved` carries exactly `world_ready`'s identity.
   - `mod/src/testShared/java/dev/aresos/shell/FakeSupervisor.java`: fake `desktop.sock` (records lines per connection,
     sends requests, can go away and come back).
   - `mod/src/test/java/dev/aresos/shell/LifecycleClientTest.java`: 11 tests, all passing
     (`mod/dev/build.sh test --tests 'dev.aresos.shell.LifecycleClientTest' -x runGameTest`).
2. **Game side, B1 row, client game test** (commit 6938089b).
   - `mod/src/client/java/dev/aresos/client/WorldSaves.java` (`LifecycleClient.Game` on the integrated server):
     tracks the server through `ServerLifecycleEvents` (`started` / `stopping` / `stopped`, public for the client
     test); `no_world` without a started server, `server_stopping` from the stop's start until it stopped (and for a save
     still queued when the stop begins), `not_desktop_world`, `error`; the save is `saveEverything(true, true, true)`
     (= `save-all flush`) on the server thread via `executeIfPossible`, timed for `ms`.
   - `DesktopWorld.saveName(server)`: the identity, now used by `ShellFocusClient.readyWorld` too.
   - `AresOsClient.onInitializeClient` registers `WorldSaves` and starts `LifecycleClient.fromEnvironment(System.getenv(), ...)`.
   - `docs/design/OS-BASE.md` B1 wire table: the `save_world` (lifecycle channel) row after `prepare_stop`.
   - `mod/src/gametest/java/dev/aresos/test/SaveNowClientGameTest.java`, last in the client list of
     `mod/src/gametest/resources/fabric.mod.json` (package 40's test comment updated: it is no longer last). Uses
     only the real `LifecycleClient` + `WorldSaves.INSTANCE` against a `FakeSupervisor`; the covered part copies
     `HomeScreenClientGameTest.covered`'s FakeHelper wiring. No screenshots.
3. **Measurement test written** (run in step 2, see 4) (commit after 6938089b, "46: save-time measurement").
   - `mod/src/gametest/java/dev/aresos/test/SaveTimesClientGameTest.java`, after `SaveNowClientGameTest` in the list;
     does nothing unless `-PmeasureSaves` (`mod/build.gradle` passes `aresos.measureSaves`). Creates a flat home with
     40 fake-helper programs (package 41's mix), closes and reopens it, saves right after joining, then twice a 60 s
     glide (package 41's route and speed, by teleport each tick) with a save after each. Log lines "46 save time ...".
4. **Step 2: measurement fixed and run; the saving indicator observed** (commit after c4951ef7).
   - `SaveTimesClientGameTest`: the 40 count what is his and present (a fresh apps file's own Notepad stays his but
     absent, so "mine" alone counted 41 and timed out); `waitForChunksRender(false)` (Fabric's plain call waits for the
     whole square of the render distance, the server sends a round area, so at render distance 8 it never ended).
   - `SaveNowClientGameTest` logs, without asserting, whether vanilla's "Saving world" corner text faded in during each
     save and how long it stayed ("46 saving indicator" lines); `HudTestAccess` reads its two values.

## State (for the next agent)

- Finished in step 2. The full report is under "Report" below; the lead commits it as `REPORT.md`. The client runs and
  their numbers are in the report's "Verified".

## What the code doesn't show

- Contract readings: the supervisor's reply to `lifecycle_hello` is unspecified, so the mod waits for nothing and
  ignores every line that is not a `save_world` request (the real supervisor answers every line it reads, see
  `os/config/usr/libexec/aresos-desktop` `on_peer`/`reply`). The request's `reason` is logged only; an unknown or
  missing reason still saves. An `id` comes back exactly as sent (number or text); a request without a usable `id` is
  ignored. Unknown ops (such as a later `prepare_stop`) get no answer: the hello's capabilities say what this mod does.
- `ms` is the save's own time on the server thread (around `saveEverything`), not the wait before it.
- `server_stopping` covers the whole stop (from `SERVER_STOPPING` to `SERVER_STOPPED`); after it, `no_world`. A request
  while the world is still loading (server not yet `SERVER_STARTED`) answers `no_world`.
- JUDGMENT-CALL candidate: `saveEverything` sets the server's "saving" flag, so vanilla's small "Saving world"
  autosave indicator can show in the corner while the save runs, as at every vanilla autosave. Avoiding it means not
  calling `saveEverything` (the brief names it), so it stays; say so in the report.
- Backoff: 0.5 s doubling to 10 s; it starts over only after a connection that lasted at least 10 s, so a supervisor
  that refuses the peer by closing at once is retried at most every 10 s. Logged only when the state changes.
- No override variable for the lifecycle socket (the contract names none); tests construct `LifecycleClient` with a
  path. `client-test.sh` and the 41 rig strip the launch nonce, so the mod's own lifecycle client never starts there.

## Report

Package 46, branch `pkg/46-save-now`: the mod saves the home world when the OS supervisor asks, over a lifecycle
channel of its own. Builder: Claude agents on Opus (step 1, then step 2). The supervisor's side is `linux-aresos`'s
package 25; nothing under `os/` changed.

### Done

- **The lifecycle channel** (`mod/src/main/java/dev/aresos/shell/LifecycleClient.java`).
  - Connects only when the launch environment has `ARESOS_DESKTOP_LIFECYCLE=1`, to `$XDG_RUNTIME_DIR/aresos/desktop.sock`,
    one JSON object per line. Without `XDG_RUNTIME_DIR` or the launch nonce and instance it logs one warning and stays
    off.
  - First line `lifecycle_hello` with `major` 1, `minor` 0, the helper hello's `instance` and `nonce`, and
    `capabilities: ["save_world"]`.
  - `save_world` gets `world_saved` with the `id` as sent, `ok`, `ms` and `world` (`world_ready`'s identity), or
    `ok:false` with `reason`.
  - Joining as the contract says: a request joins a save that has not started yet. One that arrives after a save began
    gets one follow-up save, which later requests join.
  - Reconnects when the socket goes away and comes back: backoff from 0.5 s doubling to 10 s, a fresh hello each time,
    a log line per change of state, nothing in the chat.
- **The game's side** (`mod/src/client/java/dev/aresos/client/WorldSaves.java`).
  - Runs `saveEverything(true, true, true)` (what `save-all flush` runs) on the integrated server's thread. It works
    while playing, with the Esc menu open and while a window covers the world: the server takes tasks while paused.
  - `ms` is the save's own time on the server thread.
  - Refusals:
    - `no_world`: no started server, also while a world is still loading.
    - `not_desktop_world`.
    - `server_stopping`: from the start of the server's stop until it stopped. A save still queued when the stop
      begins is refused and never runs.
    - `error`: the save saved nothing, or something threw before or during it.
- **Wiring.**
  - `DesktopWorld.saveName(server)` is the world identity; `ShellFocusClient.readyWorld` uses it too, so `world_saved`
    names the world exactly as `world_ready` does.
  - `AresOsClient` registers `WorldSaves` and starts the channel.
- **`docs/design/OS-BASE.md` B1:** a `save_world` (lifecycle channel) row: its gate, hello, request and answer. Marked
  as the mod's side built and the supervisor's side waiting for package 25.
- **Tests:**
  - `LifecycleClientTest`: 11 unit tests against `FakeSupervisor`, a fake `desktop.sock` in `mod/src/testShared`.
  - `SaveNowClientGameTest`: client game test, last but one in the client list, no screenshots.
  - `SaveTimesClientGameTest`: the measurement, last in the list. It measures only with
    `mod/dev/client-test.sh -PmeasureSaves`; otherwise it logs one line and does nothing.
  - Step 2 made the measurement work: the 40 apps are counted as the town counts them, and the test waits only for the
    chunks that arrived (see PLAN-GAP). Step 2 also added the saving-indicator observation (see JUDGMENT-CALL).

### Verified

- **`mod/dev/build.sh`** (full, at ba67fed2): BUILD SUCCESSFUL in 3 min 35 s.
  - 247 unit tests: 0 failures, 6 skipped (the Windows catalogue tests, skipped on Linux as before).
  - Server game tests: "All 104 required tests passed".
- **`mod/dev/client-test.sh`** (headless compositor, RTX 4060):

  | Run | Code | Result |
  |---|---|---|
  | 1 | 6938089b (step 1) | green, 10 min 36 s, 19 "checks passed" lines |
  | 2 | c4951ef7, with `-PmeasureSaves` | every client test passed (19 "checks passed"); the measurement test then timed out waiting for 40 apps (it counted 41, see PLAN-GAP) |
  | 2b | the count fixed, with `-PmeasureSaves` | every client test passed again; the measurement timed out in `waitForChunksRender` (see PLAN-GAP) |
  | 3 | ba67fed2's code, with `-PmeasureSaves` | **green**, exit 0, 12 min 34 s, 19 "checks passed" lines, measurement complete |
  | 4 | ba67fed2, plain | **green**, exit 0, 10 min 7 s, 19 "checks passed" lines |

  The final code passed the whole client suite twice (runs 3 and 4).
- **What `SaveNowClientGameTest` checks** (each run's line "46 save-now checks passed"):
  - The real `LifecycleClient` and `WorldSaves` against a fake supervisor save while playing, with the Esc menu open,
    and while covered (package 40's `shell_covered`).
  - Each time, a block placed just before the request is missing from a copy of its region file before
    `world_saved` and present after it.
  - The answer carries `world_ready`'s identity.
  - No screen opens, nothing pauses or unpauses, no chat line.
  - Refusals: `no_world` on the title screen and after closing, and `not_desktop_world`. `server_stopping` for a save
    still queued when the stop begins (it never runs afterwards) and for a request during the real stop.
  - Small test world, run 3: playing 81 ms, Esc menu 20 ms, covered 20 ms. Run 4: playing 82 ms, Esc menu 12 ms, covered 18 ms.
- **What the unit tests check:**
  - The gate: no variable, no connection.
  - The hello's exact fields.
  - Each answer and each refusal reason, including a game that throws or names no known reason (answered `error`,
    never saved).
  - Joining: requests before a save starts share it; requests after it began share one follow-up save.
  - Lines that are no request change nothing.
  - Reconnect with a fresh hello after the socket goes away and comes back.
  - No stale answer on a new connection; an oversized line ends the connection and the mod comes back; closing stops
    the reconnecting.

### Measured save times

Measured with `SaveTimesClientGameTest`, run 3. The setup:

- A flat home (the mod's real home creation) with a town of 40 test apps, in package 41's mix (6 Internet, 3 Games,
  3 Work & Media, 28 System & Tools).
- Render distance 8 and simulation distance 5, as the product sets them.
- Each `ms` is the mod's own answer through the real channel; one sample each.

| When | `ms` |
|---|---|
| **Right after joining the home again** | **103 ms** |
| **After a 60 s glide over new ground** (package 41's route and speed: 1.08 blocks a tick, north 15 s, south 30 s, north 15 s) | **116 ms** |
| After the same glide over that ground again | 458 ms |

- The log's "1849 chunks loaded" is the same each time: that is the 43 x 43 chunks the server holds around the player
  wherever he is.
- The glide did reach new ground: the world stored 2332 chunks, z from -32 to 31 against x from -21 to 21.
- Why the third save took four times longer is not known (one sample). A flush also waits for chunk writes still
  queued, for example of the chunks unloaded along the route.
- All three are far inside the contract's deadlines (about 60 s for a backup, about 10 s at shutdown).

### Not verified

- **Against the real supervisor:** package 25 isn't built. The real gate, socket path, peer check and deadlines are
  untested.
- **The mod's own channel in a dev run:** `client-test.sh` removes the AresOS launch variables, so `fromEnvironment`
  never opens the channel there. The tests construct `LifecycleClient` with a socket path, and the gate is unit-tested.
- **The owner's own home**, with his real apps and his disk busy with other work. The times come from a test home
  (40 fake apps, headless), one sample each.
- **The "Saving world" text in real play** (JUDGMENT-CALL). It is worked out from the game's code; the test only
  observes it with the test's own tick order.
- **`WorldSaves`'s `error` paths in the game:** a save that saves nothing, or a throw before or during it. They are
  compiled and the channel's side is unit-tested with a fake game, but they were never provoked in the game.
- **The hosted checks:** they start on push; the PR gives the run links.
- **Windows:** nothing changes there, because the gate is never set (unit test: no variable, no connection). There
  was no Windows run.

### JUDGMENT-CALL

**Vanilla's small "Saving world" text can show in the corner for a moment during a requested save.**

- **What happens.**
  - The save is vanilla's `saveEverything`, which the brief names. It is the same call as `/save-all flush`, the
    autosave every 5 minutes, and the save each time the game pauses.
  - It raises the server's "saving" flag. Twenty times a second the game checks that flag. While it is raised, a small
    white "Saving world" text in the bottom-right corner fades in a fifth of the way to full; afterwards it fades out a
    fifth per tick. It is drawn on top of everything, the Esc menu included.
- **What he would see in play.** This is worked out from the game's code with the measured times:

  | Save | Brightest | Clearly visible (over 10 %) | Then a faint trace |
  |---|---|---|---|
  | About 0.1 s (the 40-app home: 103 and 116 ms) | about 36 % (49 % if a third tick catches it) | about 0.35 s | about 1 s |
  | 458 ms (the slow one) | about 87 % | about 0.9 s | about 0.7 s |
  | About 20 ms (small world) | 20 % in about 2 of 5 saves, else nothing | about 0.2 s | about 0.7 s |

  - He sees the same text today at every autosave (every 5 minutes) and when he presses Esc.
  - While an app window covers the world, the text is hidden behind the window.
- **What the client test saw** ("46 saving indicator" lines, run 3).
  - Under the Esc menu and while covered (20 ms saves) it faded in to 22 %. One tick caught the flag, on top of the
    trace the pause's own save had left. It was then drawn for 18 more ticks, 14 of them under 10 %: about 0.2 s
    clearly and 0.7 s faint at play's 20 ticks a second.
  - While playing (81 ms) and for the save after the refused stop (41 ms) it did not show.
  - In the test the client and server tick in lockstep, so whether a tick catches the flag depends on their order, not
    on how long the save takes. In play it depends on the length, as in the table.
  - Run 4 showed the same: 22 % and 18 ticks (14 faint) under the Esc menu and while covered; nothing while playing
    (82 ms) or for save 7 (43 ms).
- **Chosen:** keep `saveEverything`, as the brief names it. The text behaves exactly like the autosave's text that he
  already sees every 5 minutes.
- **Alternatives:**
  - **A quiet save.** It would run the same steps without raising the flag: `PlayerList.saveAll()` and
    `saveAllChunks(true, true, true)`, plus the low-disk-space warning through a small invoker mixin, because that
    method is protected.
    - In Minecraft 26.2 nothing reads the flag except this text (checked in the game's code), so the data on disk
      would be the same.
    - Cost: about ten lines in `WorldSaves`, the mixin, and a client-test check that the text stays off.
    - Risk: a later Minecraft version that adds a step to `saveEverything` must be copied by hand, or a requested save
      silently misses it.
  - **Turning off vanilla's own "Autosave Indicator" option** by default in AresOS. That hides the text for every
    save, autosaves included. It is a different package's decision.
- **Recommendation:** keep it. Our save adds one more brief appearance of a text that the autosave already shows every
  5 minutes. If he wants no saving text at all, turning off the option hides all of them in one place, which the quiet
  save would not do.
- **Cost of changing later:** small and local either way. Only `WorldSaves` (and the options default) would change,
  with no protocol change.

### PLAN-GAP

- **"Nothing on screen" and `saveEverything`.** The brief asks for both, and they conflict slightly, because of the
  text above. See JUDGMENT-CALL.
- **Contract readings.** The contract doesn't settle these points; this is what the mod does. `linux-aresos` should
  confirm them for package 25.
  - The supervisor's reply to `lifecycle_hello` is unspecified. The mod waits for nothing and ignores every line that
    is not a `save_world` request. (The real supervisor answers every line it reads; see `on_peer` and `reply` in
    `os/config/usr/libexec/aresos-desktop`.)
  - The request's `reason` is only logged. An unknown or missing reason still saves.
  - `id` comes back exactly as sent, number or text. A request without a usable `id` is ignored.
  - Unknown ops, such as a later `prepare_stop`, get no answer; the hello's `capabilities` say what this mod does.
  - `ms` is the save's own time on the server thread, not the wait before it.
  - `server_stopping` covers the whole stop, from `SERVER_STOPPING` to `SERVER_STOPPED`; after it the answer is
    `no_world`. A request while the world is still loading (before `SERVER_STARTED`) is answered `no_world`.
  - The backoff starts over only after a connection that lasted at least 10 s. A supervisor that refuses the peer by
    closing at once is therefore retried at most every 10 s, and the log notes only changes of state.
  - There is no override variable for the lifecycle socket (the contract names none).
- **Test tooling.** Fabric's `waitForChunksRender()` waits for every chunk in the full square of the render distance,
  but the server sends a round area (`ChunkTrackingView`). Above render distance 6 the square's corners never come and
  the wait never ends. The suite's other tests run at 5. A later test at the product's distance should use
  `waitForChunksRender(false)`.
- **Counting "his" apps in a test.** A fresh apps file starts with Notepad as his. When the helper doesn't list
  Notepad, it stays his but absent, so counting "mine" alone gives one more than the town builds. Count what is his and
  present, as `TownKeeper.wanted` does.
- **Vanilla already saves on every pause.** That includes a window covering the world, through package 40's pause.
  It isn't flushed or forced, so it doesn't replace `save_world`. But a requested save soon after a pause has little
  left to write.

### Open questions

- **For the owner:** keep the "Saving world" text during requested saves, as now and as the autosave shows it? My
  advice is to keep it (JUDGMENT-CALL).
- **For `linux-aresos`:**
  - Do the contract readings above match package 25's supervisor? In particular: no hello reply is needed, `reason` is
    only logged, and unknown ops are not answered.
  - Is one save of up to about 0.5 s comfortable for the shutdown budget? Package 25 may want its own measurement on
    the real home once its side exists.
- **Open technically:** the third save's 458 ms (the same glide again, four times the first glide's time) is
  unexplained; there was one sample each.
