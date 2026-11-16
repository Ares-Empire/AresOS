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

- Client run 2 (`-PmeasureSaves`, at c4951ef7): suite green, the measurement failed at the 40-app count. Run 2b: suite
  green, the measurement failed at `waitForChunksRender`. Run 3 (`-PmeasureSaves`, the step-2 code): **green**, exit 0
  in 12 min 34 s, 19 "checks passed" lines. Times: right after joining 103 ms, after a 60 s glide over new ground
  116 ms, after the same glide again 458 ms (each one sample; 1849 = the 43 x 43 chunks the server holds around the
  player; the world stored 2332 chunks, z -32 to 31, x -21 to 21, so the glide reached new ground). Test world:
  playing 81 ms, Esc menu 20 ms, covered 20 ms. Indicator: under the Esc menu and covered it faded in to 22 % and was
  drawn 18 more ticks (14 under 10 %); while playing (81 ms) and for save 7 (41 ms) it did not show.
- Left: `mod/dev/build.sh` once, a plain `mod/dev/client-test.sh` once more, merge `origin/main`, the report, the PR.

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
