BLOCKED

Brief review of `briefs/25-guardian.md` (commit `751e132b`) by a fresh Claude agent on Opus, condensed by the lead
(`linux-laptop-home`, 2026-11-19).

## Blocking

- **B1. A builder's test can end his session.** `Loop` and `Supervisor` default `environ` to `os.environ`
  (`aresos-desktop:1047, 2124`), `session_environment()` (`:798`) passes everything except `PRIVATE_ENVIRONMENT`,
  and `labwc --exit` signals `$LABWC_PID`. Fix: logout ends labwc with SIGTERM through the labwc pidfd 3.2 watches
  (never `labwc --exit`; `LABWC_PID` only from the supervisor's own environ). Machine rules: every supervisor a
  test, rig or manual try starts runs under `env -i` with `HOME`, a temporary `XDG_RUNTIME_DIR`, `PATH` and a
  stand-in `LABWC_PID` it started; never the shell's `DISPLAY`, `WAYLAND_DISPLAY`, `DBUS_SESSION_BUS_ADDRESS` or
  `LABWC_PID`.
- **B2. The real-game rig would make the mod dial his live supervisor's socket**
  (`reviews/49b-arena-rerun/rig/start.sh:31-34`, `inner.sh:13-17, 40-43`). Fix: only the game's command line in
  `inner.sh` gets the gate, `XDG_RUNTIME_DIR` = the test supervisor's temporary runtime folder, the instance and
  nonce the adoption runtime file names, and an absolute `WAYLAND_DISPLAY` if needed; assert
  `/proc/<game>/environ` has that `XDG_RUNTIME_DIR` before sending `save`.
- **B3. A stop right after adoption is called clean with no save.** `adopt()` leaves `ever_ready` False and the
  mod's reconnect backoff reaches 10 s. Fix: an adopted launch takes "a world was ready" from an open stop record
  and otherwise counts as world-ready; it waits up to 10 s for the hello and is unsaved or called off without one.
- **B4. An op arriving during a stop is unspecified, so the guard's ordering can be lost.** Fix: an op during a
  stop joins it; `stop --reason shutdown` makes it uncancellable as a signal does; every caller gets its reply
  when the stop ends; `save` during a stop gets the stop's save result; nothing starts a second stop or save.

## Split

Step 5 is overloaded. Make section 4 (48's leftovers) its own step and plan the real-game check as step 6 from
the start.

## For the code review (the ones that matter go into the brief)

- What "closes its record" means for called-off and for overrun stops: an adopted game that got SIGTERM and ends
  with 143 must not count as a crash and be restarted in the middle of a teardown.
- `server_stopping` followed by `no_world`, and `no_world` during New home, never mean clean.
- `save_failed` and `stuck`: latched, or passing on purpose (`ready()` at `:1448` re-enters IN_WORLD on the next
  heartbeat).
- The R28 compatibility test runs against R28's frozen key list.
- `request()` (`:2392`) times out after 10 s, but `save` needs 60 s and more, and `stop` needs
  `STOP_BUDGET + 10`.
- `stop` exits 0 with no socket (`main()` returns 1 today).
- `--reason shutdown` only from the guard, or only while systemd is stopping.
- 4.1's rename only when no launch is alive and `jvm_lock_held()` is false.
- 4.2's date pattern allows `HomeSwap.datedName`'s `-N` suffix.
- A supervisor started after labwc ended exits at once.
- In the VM the shortcut step leaves the supervisor latched `killed`, and the supervisor logs to `desktop.log`,
  not the journal.
