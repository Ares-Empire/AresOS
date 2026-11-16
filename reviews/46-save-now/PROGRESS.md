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
3. **Measurement test written and compiling, not yet run** (commit after 6938089b, "46: save-time measurement").
   - `mod/src/gametest/java/dev/aresos/test/SaveTimesClientGameTest.java`, after `SaveNowClientGameTest` in the list;
     does nothing unless `-PmeasureSaves` (`mod/build.gradle` passes `aresos.measureSaves`). Creates a flat home with
     40 fake-helper programs (package 41's mix), closes and reopens it, saves right after joining, then twice a 60 s
     glide (package 41's route and speed, by teleport each tick) with a save after each. Log lines "46 save time ...".

## State (for the next agent)

- Client run 1 (`mod/dev/client-test.sh`, full suite, measurement not asked): **green**, exit 0 after 10 min 36 s on
  the RTX 4060, 19 "checks passed" lines in `mod/build/run/clientGameTest/logs/latest.log`, the last
  "46 save-now checks passed: ...". Its own save times in the small test world: playing 85 ms, Esc menu 22 ms,
  covered 18 ms. That run was at 6938089b; since then `WorldSaves` also answers `error` when something throws on the
  server thread before the save (not yet run in the game; covered by compile only).
- The run left untracked screenshots with new numbers in other packages' folders (the suite's numbering drifted long
  before this package; ours take none): `git clean` them as well as `git checkout -- reviews/` after a run, keeping
  `reviews/46-save-now/`.

## Left, in order

1. (Note for any change to `SaveNowClientGameTest`: the server thread waits for the test between ticks, so a save
   asked between test steps runs only at the next tick; `context.waitFor` ticks, `supervisor.answer` doesn't.)
2. Measurements: `mod/dev/client-test.sh -PmeasureSaves` (whole suite plus about 5 minutes; the task's timeout is
   20 minutes). Take the two times from `mod/build/run/clientGameTest/logs/latest.log` ("46 save time" lines).
3. Full `mod/dev/build.sh` once and `mod/dev/client-test.sh` twice green (AGENTS.md). Merge `origin/main` before the
   hosted checks.
4. Report under "Report" below (Done / Verified / Not verified / JUDGMENT-CALL / PLAN-GAP / Open questions, both
   times), then the PR "Package 46: the mod saves the world when the supervisor asks" (ready, not draft).

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
