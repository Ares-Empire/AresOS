# Package 46: progress

Builder: Claude agent (Opus). Brief: `briefs/46-save-now.md`. Branch `pkg/46-save-now`.

## Done

1. **Protocol and unit tests** (commit "46: the lifecycle channel's protocol and unit tests").
   - `mod/src/main/java/dev/aresos/shell/LifecycleClient.java`: gate, `lifecycle_hello`, `save_world` /
     `world_saved`, joining, reconnect with backoff, quiet logging. The game side is the `LifecycleClient.Game`
     interface (one method, `save(Runnable starting)`).
   - `ShellClient.worldObject` is now package-visible so `world_saved` carries exactly `world_ready`'s identity.
   - `mod/src/testShared/java/dev/aresos/shell/FakeSupervisor.java`: fake `desktop.sock` (records lines per connection,
     sends requests, can go away and come back).
   - `mod/src/test/java/dev/aresos/shell/LifecycleClientTest.java`: 11 tests, all passing
     (`mod/dev/build.sh test --tests 'dev.aresos.shell.LifecycleClientTest' -x runGameTest`).

## Left, in order

2. Game side: `DesktopWorld.saveName(server)` shared with `ShellFocusClient.readyWorld`; a client class implementing
   `LifecycleClient.Game` on the integrated server (`executeIfPossible`, refuse `no_world` / `not_desktop_world` /
   `server_stopping` / `error`, `saveEverything(true, true, true)` timed); started from `AresOsClient.onInitializeClient`
   via `LifecycleClient.fromEnvironment(System.getenv(), ...)`.
3. B1 row in `docs/design/OS-BASE.md` (wire table, next to `prepare_stop`).
4. Client game test (end of the entrypoint list in `mod/src/gametest/resources/fabric.mod.json`): save unpaused, covered
   (FakeHelper `shell_covered`, as `HomeScreenClientGameTest.covered`) and with the Esc menu open; a block placed while
   paused (after vanilla's pause-save) is absent from a copy of the region file before `world_saved` and present
   after; `not_desktop_world`; `no_world` after closing; `server_stopping` with a save queued behind a held server
   thread while the world closes.
5. Measurements (gated client test, `-PmeasureSaves`): flat home with a 40-app town, save right after rejoining and
   after a 60 s glide (package 41's route); both `ms` into the report.
6. Full `build.sh` and `client-test.sh` twice, report under "Report" below, PR.

## What the code doesn't show

- Contract reading so far: the supervisor's reply to `lifecycle_hello` is unspecified, so the mod waits for nothing
  and ignores every line that is not a `save_world` request (the real supervisor answers every line it reads). The
  request's `reason` is logged only; an unknown or missing reason still saves. An `id` comes back exactly as sent
  (number or text); a request without a usable `id` is ignored. Unknown ops (such as a later `prepare_stop`) get no
  answer: the hello's capabilities say what this mod does.
- `ms` is the save's own time on the server thread (around `saveEverything`), not the wait before it.
