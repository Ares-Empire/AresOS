# 23: review fixes, round 1

Follow-up to `briefs/23-minecraft-starts.md`. Review: `reviews/23-minecraft-starts/REVIEW-1.md` (gpt-6-astra high, CHANGES-NEEDED: 3 blocking, 8 should-fix). Builder: the same Claude agent (Opus). Next review: a fresh Codex context.

## Owner answers (2026-11-10)

All 14 JUDGMENT-CALLs were accepted. Board #168: "Create it myself": first start opens the title screen and he creates the hub with the AresOS button. Board #169: "Yes to all" for calls 2–6 and the 8 technical calls.

The reviewer agrees with every call except **10**. Finding 1 below changes call 10. Record the new behavior as an updated JUDGMENT-CALL 10 in the report; the integrator takes it to the owner.

## Fix

Fix every finding at its cause, each with a test that fails before the fix. The numbers follow REVIEW-1.

1. **Blocking: memory kills must never restart the game (B5).**
   - When systemd-oomd or the kernel kills the whole scope, the wrapper dies too and no exit is reported. Today that counts as a crash and restarts after 5 s.
   - Read the scope's real result (for example its unit `Result`, or the cgroup's `memory.events` `oom_kill`/`oom_group_kill` counts).
   - Latch recovery for any whole-scope death that can't be explained as the owner's quit or a plain crash. Leave recovery only by `retry`, plus B5's cleared-pressure condition if the design asks for it.
   - Test: kill the whole scope, not only Java.
2. **Blocking: a damaged hub must not pass or be declared ready.**
   - `check_world()` checks gzip readability only. Validate the real saved data: the AresOS marker and its `enabled` value, `data/aresos/nether_home.dat`, and completed provisioning.
   - Refuse unattended opening and show recovery when any is missing or malformed. Never rewrite the save.
   - Alternatively, or as well, make the mod send `world_ready` only when the home is valid. Choose what is correct and smallest.
   - Fixtures: real-format NBT (a small reader or writer is fine), covering missing home data, a disabled marker, malformed NBT and interrupted provisioning. Today's "valid world" fixtures hold plain strings; replace them.
   - A mod change needs `build runClientGameTest` (one Gradle run at a time, ≥ 6 GB free) and a renewed jar pin through `check_build=resolve` (call 14).
3. **Blocking: every image build must build and check the mod jar.**
   - Make building the pinned jar and checking its hash a prerequisite inside the shared build path that every image build runs. `os/build.sh` is the likely place: it is not bound, and package 27 doesn't touch it.
   - **Don't edit `.github/workflows/os-image.yml`.** It is bound, and package 27 is rewriting its release job right now.
   - If the release job doesn't go through the shared path, stop and report instead (the integrator then sequences it after 27 merges).
   - Show that a clean checkout's release build preparation produces and checks the jar, without publishing (a test, plus the next `check_build` run).
4. **The game's memory limit must hold for the real JVM.**
   - Prism forwards `--launch` to an already-running Prism, and Java then inherits that Prism's cgroup. A launch from Prism's own UI isn't scoped either.
   - Enforce the scope at the wrapper/JVM boundary (for example the wrapper starts Java in its own scope with `MemoryHigh`), or refuse a launch outside it.
   - Test with Prism already running outside the desktop scope, and check the Java PID's cgroup and limit.
5. **Account for a game that ends while the supervisor is down.**
   - Before a new launch, reconcile each unfinished launch exactly once: normal exit, crash, SIGKILL, or no exit record.
   - Bind exit records to the launch ID and process identity, not only the PID.
6. **One validation gate for every new JVM**, including launches from Prism's UI.
   - Recheck the image pins and the managed instance directory.
   - Refuse a damaged or unexpectedly missing world, instead of falling back to setup.
7. **No endless STARTING.**
   - Add an explicit launch-failure report, and a bounded wait between authorization and the JVM's PID.
   - Recover when the wrapper dies or the handoff is lost.
   - Test spawn failure and connection loss between authorization and `jvm_started`.
8. **Pin the game's full component set.**
   - Lock Prism's component metadata and the executable dependencies, including the LWJGL version and natives (versions and hashes), in `os/minecraft/desktop.lock.json`.
   - Validation must refuse any other LWJGL version. Minecraft itself still downloads through Prism with his account; never redistribute Mojang files.
9. **Keep recovery usable under memory pressure (B5).**
   - Protect the compositor, the supervisor and the recovery terminal: for example `MemoryMin`/`MemoryLow` with ancestor-aware placement, and oomd preferences that pick the game group first.
   - Check the effective hierarchy in the VM.
   - Add a pressure test in the disposable VM if it fits the budget below. Otherwise record exactly what is and isn't proven.
10. **Lost readiness must show.**
    - After heartbeat loss or helper exhaustion, clear "ready" and show the helper failure. Don't kill or repair the game.
    - Keep a bounded readiness check after adopting a JVM.
11. **A restarted desktop waits below the foreground app (B2).**
    - Coordinate with package 24's window tracking, or use labwc's focus controls, so an editor or browser in front stays in front when Minecraft restarts.
    - Test a restart while another app has focus. If the VM can't show it, say so.

## Rules and budget

- `AGENTS.md` applies. Push `pkg/23-minecraft-starts`; never merge, never push to `main`, never `--no-verify`.
- **Memory:** two agents share the laptop.
  - Before any WSL suite: ≥ 5 GB free and `pgrep -f "python3.*unittest"` empty.
  - Before Gradle: ≥ 6 GB free.
  - Use `pkg23-` names. Restart work stopped for low memory once memory is free (owner, board #160).
- **CI budget:** at most two `check_build=build` runs (with VM), one `check_build=resolve` if the jar pin changes, and one `checks_only`. Report before dispatching more.
  - Main's hosted `checks_only` fails in `test_owner_update` until PR #37 merges. Compare with main, as you did.
- Update `REPORT.md` with a "Review fixes 1" section first: each finding, the fix, its test, and what remains unproven. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
