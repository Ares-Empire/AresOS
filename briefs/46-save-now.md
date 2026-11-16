# 46: The mod saves the world when the supervisor asks

`linux-aresos`'s package 25 (the guardian: backups, clean shutdown and updates) needs the home screen's world saved on request, without Save and Quit and without the owner noticing. This package builds the mod's side. The supervisor's side is package 25's. The contract below is `linux-aresos`'s (the OS lead, 2026-11-16); build it as written.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`: a protocol against a fixed contract, with tests. **Review:** a fresh Codex context, `gpt-6-astra`, `high`. `linux-aresos` also reads the `docs/design/OS-BASE.md` change.

## Why a channel of its own

The mod has no channel to the supervisor today. The app helper's status pipe runs one way (helper to supervisor), and `desktop.sock` talks only to the Java wrapper and the owner's commands. OS-BASE B1 says the guardian's lifecycle messages go on a separate channel, so a dead app helper can't stop saving. So this is a direct mod-to-supervisor connection, not an `aresos-shell` message.

## The contract

- **Gate:** the mod connects only when its launch environment has `ARESOS_DESKTOP_LIFECYCLE=1`. The supervisor adds it in package 25. An older supervisor (release 28's) never sees the connection, so this package can merge at any time.
- **Connect** to `$XDG_RUNTIME_DIR/aresos/desktop.sock`, one JSON object per line. First line: `{"op":"lifecycle_hello","major":1,"minor":0,"instance":…,"nonce":…,"capabilities":["save_world"]}`, with the same instance and nonce as the helper hello (`ARESOS_DESKTOP_INSTANCE`, `ARESOS_LAUNCH_NONCE`). The supervisor checks the peer's `SO_PEERCRED` uid and that its PID is the JVM the wrapper reported (`jvm_started`); nothing on the mod's side needs to prove more.
- **Request:** `{"op":"save_world","id":n,"reason":"backup|shutdown|update|manual"}`.
- **What the mod does:** the equivalent of `save-all flush` on the integrated server's thread (`saveEverything` with flush, so the chunk IO is on disk before the answer). No pause, no leaving the world, nothing on screen. It must also work while the world is paused: covered (`shell_covered`, package 40) or with the Esc menu open. Test both.
- **Answer:** `{"op":"world_saved","id":n,"ok":true,"ms":…,"world":<the same identity as world_ready>}`, or `ok:false` with `reason` one of `no_world`, `not_desktop_world`, `server_stopping`, `error`.
- **Joining:** a request may join a save that has not yet started on the server thread. A request that arrives after a save began gets one follow-up save, which all later requests join. So at most one save runs and one waits, and "saved" always covers everything up to the request.
- **Timeout and failure:** the mod never aborts a running save; the supervisor owns the deadline (about 60 s for a backup, maybe 10 s or less at shutdown). No answer by the deadline counts as a failure on the supervisor's side.
- **Not in this package:** B1's `prepare_stop` (a clean close, the real JVM exit, the world lock released) stays package 25's second step after `save_world`. Don't build it.
- **Connection life:** reconnect if the supervisor's socket goes away and comes back, with a backoff, quietly (a log line, no chat), and only while the gate is set. Every reconnect starts with a fresh `lifecycle_hello`, so the supervisor checks the peer again (`linux-aresos`, 2026-11-16). A mod in a world that isn't a desktop world still answers `not_desktop_world`.

## Tests and measurement

- Unit tests against a fake lifecycle server, like `FakeHelper` (`mod/src/testShared/java/dev/aresos/shell/FakeHelper.java`): the gate (no variable, no connection), hello fields, each answer and reason, joining (requests before and after a save began), reconnect.
- A client game test: a save while covered and while the Esc menu is open, and a block placed just before the request is on disk after `world_saved` (read back from the region file or a reopened world).
- **Measure on the laptop** (through `mod/dev/client-test.sh` or package 41's rig in `reviews/41-home-memory/rig/`): the `ms` of a save in a flat home with a town of about 40 test apps, once right after joining and once after flying around to load many chunks. Use a world of your own in your worktree, never the owner's (`~/AresOS-try`, `~/.minecraft`).
- Add a row for `save_world` to OS-BASE B1's wire table (the lifecycle channel, its gate and its answer), marked as the mod's side built and the supervisor's side waiting for package 25.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-46-save-now`, branch `pkg/46-save-now`, from main. Merge `origin/main` into the branch before the hosted checks.
- Only `mod/` and `docs/design/OS-BASE.md` (the B1 row) change. Nothing under `os/`.
- Game runs only through `mod/dev/client-test.sh` or the package-41 rig (the lock, one game at a time, 6 GiB free). Never `./gradlew` yourself, never `--force`. Never the whole `os/tests` suite on the laptop.
- Headless only, never `WAYLAND_DISPLAY=wayland-0`. Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client. Stop only processes you started, by PID.
- The repo is public: no personal data.
- Report in `reviews/46-save-now/REPORT.md` with both measured times. Open a PR "Package 46: the mod saves the world when the supervisor asks". Never merge, never push to main, never `--no-verify`.
