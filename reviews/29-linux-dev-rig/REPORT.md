# 29: Build and test the mod on the AresOS laptop: report

Builder: Claude agent (Opus 5.5), on the owner's laptop running AresOS (release 27), as the user `ares`.
Branch `pkg/29-linux-dev-rig`. No system install, no change to `~/.bashrc` or PATH, nothing under `os/`,
no mod source changed.

## Done

**Java 25 in the home folder (outside the repo).**
- Eclipse Temurin **25.0.5+8 LTS**, the newest JDK 25 GA for Linux x64 in Adoptium's API on 2026-11-13
  (released 2026-10-21).
- URL: `https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.5%2B8/OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz`
  (141 341 188 bytes).
- SHA-256 `68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb`. `sha256sum -c` passed against both
  places where Adoptium publishes it: the `checksum` field of
  `api.adoptium.net/v3/assets/latest/25/hotspot?architecture=x64&image_type=jdk&os=linux&vendor=eclipse` and the
  release's own `….tar.gz.sha256.txt`.
- Unpacked to `~/.local/opt/jdk-25.0.5+8` (304 MB), stable link `~/.local/opt/jdk-25`. The tarball is deleted.
  `java -version`: `OpenJDK Runtime Environment Temurin-25.0.5+8 (build 25.0.5+8-LTS)`.

**`mod/dev/env.sh`** (sourced by the three scripts; they run from `mod/` whatever the caller's directory).
- `JAVA_HOME`: the caller's if it is a Java 25 JDK (`bin/java` and `bin/javac`, major version 25), otherwise
  `~/.local/opt/jdk-25`, otherwise one sentence and exit 1.
- Shared checks: the owner's Lunar game is any process whose `/proc/<pid>/exe` points under `~/.lunarclient/`
  (one `find -lname` over `/proc`, read only). Memory is `MemAvailable` from `/proc/meminfo` against 6 GiB.
  A refusal is one sentence and exit code **75** ("try later"). `--force` skips both checks.
- `aresos_lock`: takes `~/.cache/aresos-dev/client-test.lock` with `flock`, waiting and saying so.
- Gradle always runs as `./gradlew --no-daemon` inside its own systemd user scope
  (`systemd-run --user --scope`, unit `aresos-dev-<script>-<pid>.scope`). Every exit (success, failure, Ctrl+C,
  TERM, HUP) stops that scope, which ends everything in it: Gradle's single-use daemon, the game and the
  compositor. The scope runs in the background with `wait`, so a signal to the script alone acts at once.

**`mod/dev/build.sh`**: `./gradlew build` with extra arguments passed through, plus the same Lunar/memory refusal.

**`mod/dev/client-test.sh`**: `./gradlew runClientGameTest` (arguments pass through), with no window on the
owner's screen.
- The game runs inside **cage 0.3.1** with `WLR_BACKENDS=headless` and cage's **own Xwayland**. Minecraft 26.2
  asks GLFW for X11 whenever both X11 and Wayland are available (`GLX`), so the game is an X11 client of that
  Xwayland. The environment given to cage drops `DISPLAY`, `WAYLAND_DISPLAY` and `WAYLAND_SOCKET`; cage then sets
  both display variables to its own sockets. Simply unsetting `WAYLAND_DISPLAY` would not be enough, because
  libwayland then falls back to `wayland-0`, which is his. It also drops `ARESOS_LAUNCH_NONCE`,
  `ARESOS_DESKTOP_INSTANCE` and `ARESOS_SHELL_SOCKET`, so a test client can never reach a real app helper and
  open real apps.
- No input injection: the game only gets the Fabric test framework's synthetic input, and the headless
  compositor has no input devices.
- Sound goes to OpenAL Soft's null backend (`ALSOFT_DRIVERS=null`; the game logs `OpenAL initialized on device
  No Output`), so test music does not play on his speakers.
- GPU: it probes each mode with `glxinfo -B` inside a throwaway headless cage (about 0.2 s) and takes the first
  that renders on the expected device: **nvidia** (compositor on the NVIDIA render node, game with
  `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __VK_LAYER_NV_optimus=NVIDIA_only`, the
  supervisor's set), then **intel** (compositor on the Intel render node, Mesa GLX), then **software** (pixman,
  `LIBGL_ALWAYS_SOFTWARE=1`). `--gpu` forces one. If none works it stops with a sentence and never falls back to
  his screen. At the end it prints the device the game itself logged.
- Lock and refusal as above. After waiting for the lock it checks Lunar and memory again.
- The tests still rewrite tracked screenshots under `reviews/`. At the end it prints
  `git checkout -- ../reviews/`, and that renumbered screenshots stay untracked. `--keep-screenshots <dir>`
  copies every file the run wrote under `reviews/`, `mod/build/review/` and the test run's `screenshots/` into
  `<dir>`, keeping paths.
- Compositor output goes to `~/.cache/aresos-dev/client-test-compositor.log`. Gradle and the game keep the
  terminal.

**`mod/dev/run-hub.sh`**. Its header says it is a development aid that package 23's supervisor replaces.
- The contract comes from `ShellClient.fromEnvironment`, the helper's header and `main()`, and package 23's
  supervisor (`git show origin/pkg/23-minecraft-starts:os/config/usr/libexec/aresos-desktop`, read only). Helper
  and game share `ARESOS_DESKTOP_INSTANCE` and `ARESOS_LAUNCH_NONCE`. Both use the default socket
  `$XDG_RUNTIME_DIR/aresos/shell.sock`.
- It starts the helper the supervisor's way:
  - the session's environment without launch plumbing (`ARESOS_SHELL_SOCKET`, `ARESOS_SHELL_STATUS_FD`,
    `NOTIFY_SOCKET`, `LISTEN_*`, `WATCHDOG_*`);
  - the system PATH `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`;
  - a fresh instance `aresdesktop-dev-<12 hex>` and a nonce of 24 random bytes in URL-safe base64 (like
    `secrets.token_urlsafe(24)`), passed in the environment and never on a command line;
  - `setpriv --pdeathsig TERM`, so the helper gets SIGTERM if the script dies.

  Helper output goes to `~/.cache/aresos-dev/run-hub-helper.log`.
- `--helper <path>` (default `/usr/libexec/aresos-shell`) and `--registry <dir>` (passed to the helper's own
  `--registry`) were added at the coordinator's request. A helper path that is not a readable regular file (or
  not executable) is refused with one sentence and exit 2, and so is a registry that is not a readable
  directory.
- Then it runs `./gradlew runClient` (game folder `mod/run/`). The game gets the session's environment plus the
  same instance and nonce. It also gets the RTX 4060 offload variables when an NVIDIA GPU is present, as the
  supervisor does.
- When the game exits, or on Ctrl+C, the scope stops first. Then the helper gets SIGTERM (SIGKILL after 5 s) and
  its record is removed.
- Ownership: the helper it starts is recorded as `<pid> <start time> <instance> <nonce>` in
  `$XDG_RUNTIME_DIR/aresos/run-hub.helper` (mode 0600). A helper already serving the socket is reused only if
  that record names it (same PID and start time), and is then left running afterwards. Any other helper serving
  the socket stops the script with a sentence. A second `run-hub.sh` while one runs is refused
  (`~/.cache/aresos-dev/run-hub.lock`).
- It writes only to `mod/run/`, `~/.cache/aresos-dev/` and `$XDG_RUNTIME_DIR/aresos/`, plus Gradle's own
  `mod/build`, `mod/.gradle` and `~/.gradle`.

**Tests changed or skipped by operating system.** I read every failure; nothing else changed.
1. Six unit tests, category (b) (Windows-only path), are now
   `@EnabledOnOs(value = OS.WINDOWS, disabledReason = …)`. The reasons are in
   `mod/src/test/java/dev/aresos/catalogue/WindowsOnly.java`. On Windows they run unchanged.
   - **PowerShell.** These build Start Menu `.lnk` fixtures through `WScript.Shell` or run the PowerShell
     discovery script. On Linux they fail with `Cannot run program "powershell.exe"`:
     - `WindowsCatalogueTest.fixtureStartMenusAndUwpProduceStableUnpinnedAppsAndRealIcons`
     - `WindowsCatalogueTest.nativeShortcutIdentityIncludesArgvAndWorkingDirectory`
     - `WindowsCatalogueTest.nativeMissingIconSourceClearsPreviousExtraction`
     - `WindowsCatalogueIdentityTest.nativeCmdShortcutsWithDifferentRawQuotingRemainTwoApps`
   - **Windows path rules.** Notepad's known paths are resolved with the host's `Path.of(...)`. On Linux
     `C:\Windows\notepad.exe` is a relative path, so it never counts as Notepad:
     - `WindowsCatalogueIdentityTest.migratedDefaultNotepadReconcilesStoreAndShortcutWithoutChangingOwnerFields`
     - `WindowsNotepadAliasTest.knownWindowsPathsResolveVariablesCaseAndDotSegments`

   `WindowsAppCatalogue` only runs on Windows (`AresOs.onInitialize`), so this is not a Linux defect.
2. One client game test, category (a): `AresOsClientGameTest` (01c).
   - It compared the fake launcher's recorded command with the literal `notepad.exe`. On AresOS the default
     Notepad is a helper app with no command, because the helper launches it by ID
     (`AppsConfig.load(…, linux)`). The fake launcher therefore recorded `[]`, and the test failed with
     `Holding one click launched app more than once: [[]]` although one click had launched Notepad once.
   - Both places now expect `notepadCommand()`: the configured Notepad's command, checked to be unique among the
     configured apps, so a recorded launch still names Notepad and nothing else. In that world the three outcomes
     stay distinct: `[]`, test app B's `aresos-test-b`, or no launch.
   - On Windows `notepadCommand()` is `notepad.exe`, as before.

**Docs:** `mod/README.md` has a short "On Linux (AresOS)" section: the JDK (version, URL, checksum), the three
scripts, the lock, the refusals and what the headless run renders with.

## Verified

All on the laptop on 2026-11-13. Before each Gradle or client run, `free -g` showed 8–10 GB available and no
Lunar game was running (checked through `/proc/*/exe`).

**`mod/dev/build.sh`**
- Run 1 (first Gradle run; it downloaded Gradle 9.8.0, Loom and Minecraft 26.2): failed after 103 s on the six
  unit tests above.
- Run 2: **BUILD SUCCESSFUL in 30 s**. 62 unit tests: 56 passed, 6 skipped with their reason. `runGameTest`:
  `All 38 required tests passed :)`.
- Run 3 (final code): **BUILD SUCCESSFUL in 21 s** (unit tests up to date; `All 38 required tests passed :)`).
- Run 4, `dev/build.sh test --rerun` (also checks that arguments pass through): **BUILD SUCCESSFUL in 29 s**.
  56 passed, 6 skipped, 0 failed; 38 game tests passed.

**`mod/dev/client-test.sh`** (the full `runClientGameTest`, all 12 client test classes)

| Run | Scripts | Result | Time |
|---|---|---|---|
| 1 | first version | failed at `AresOsClientGameTest` (the Notepad literal above); the 9 classes before it passed | 5 min 10 s |
| 2 | after the test fix | **passed** | 6 min 45 s |
| 3 | final | **passed** | 7 min 2 s |
| 4 | final, straight after run 3 | **passed** | 6 min 47 s |

`env.sh` and `client-test.sh` changed after run 2 (signal handling, lock helper), so runs 3 and 4 are the two
consecutive passes with the final scripts.

- **The RTX 4060 renders the headless run.** Every run logged `Using graphics backend OpenGL, using drivers:
  3.3.0 NVIDIA 615.78.08` and `Using graphics device: NVIDIA GeForce RTX 4060 Laptop GPU/PCIe/SSE2 (NVIDIA
  Corporation)`. The compositor (wlroots GLES2) and its Xwayland were on the NVIDIA render node too.
- Each passing run logs the same 35 pass lines: 09c, 09d, 09b, 09, 08b (two), 24, 08, 07b, 07, 04d (nine worlds,
  three rejoins and the summary), 01c, 04, 04b (three), and 04c (save rename twice, typed seed,
  unsafe/authorization, selected home, placeholder, client checks).
- The Intel and software fallbacks were probed only, not run in full:
  - headless Intel gives `Mesa Intel(R) Iris(R) Xe Graphics (RPL-P)`;
  - software gives `llvmpipe (LLVM 22.1.8, 256 bits)`;
  - both are OpenGL 4.6 core, about 0.2 s per probe.

**No window on the owner's screen.** I took `grim` screenshots of the real display (both outputs, 3840×1080)
while the test game was running headless: run 1 at 14:58:37, run 3 at 15:19:30 and run 4 at 15:27:13. They show
only his terminal and no Minecraft window. They stay outside the repo, in my session's scratchpad, and are not
committed.

**Rendered frames, not black.** All 33 screenshots of run 2 are 854×480, with mean brightness 0.31–0.71 and
standard deviation 0.10–0.19. I looked at three myself and copied them to `screenshots/` here:
- `08-wall-logo-zone.png`: the 32×32 wool and concrete compass logo inside the lime-glass fixture frame, with
  sky, hotbar and hand.
- `04-hub-above.png`: the Nether hub from above (blackstone floor, lanterns, lava pool, anchor, glass cage). It
  also shows the chat line "AresOS apps can't open right now: the app helper is unavailable (this game was not
  started by the AresOS session (no launch nonce))". That is correct on AresOS without a helper, and it does not
  appear on Windows.
- `07-apps-page-2.png`: the Apps catalogue, page 2/2, with Fixture 26–40 and their generated icons.

**Cleanup on every exit.**
- After each run there was no cage, Xwayland, Gradle or game process of ours left, and no `aresos-dev*` unit.
  The Xwaylands still running belonged to the session's labwc and to another agent's headless labwc.
- With a stand-in command in the scope, each of these ended the script and its scope within about 50 ms, and the
  cleanup ran with the matching exit code:
  - TERM to the script: 143;
  - INT to its process group, as Ctrl+C sends it: 130;
  - HUP to the script: 129.
- A normal exit code (3) passed through unchanged.
- While another holder had the lock, `client-test.sh` printed `Waiting for another client test run on this
  laptop to finish (…/client-test.lock)...`, and TERM ended it at once.

**Refusals.**
- With a fake home whose `.lunarclient/jre/bin/java` was running, it printed `The owner's Minecraft (Lunar
  Client, PID …) is running; try again once it has closed, or pass --force.` and exited 75.
- With the floor raised to 100 GB, it printed `Only 9.1 GB of memory is available and a run needs 6 GB; try
  again later, or pass --force.` and exited 75.
- `--force` skips both.

**`run-hub.sh`**
- **Dry run** (`-m`) in the session: the helper started (`serving aresos-shell/1.0 on
  /run/user/1001/aresos/shell.sock (3 apps)`), Gradle ended, the helper stopped and the socket was gone.
- **Inside a headless cage**, so no window on his screen, up to the title screen:
  - game log: `INFO: AresOS app helper: CONNECTED (tracking windows)`;
  - helper log: `desktop connected (minor 0)`;
  - TERM to the script stopped the game, the helper and the scope within about 1 s and left
    `$XDG_RUNTIME_DIR/aresos/` empty.
- **On the real screen, once**, with the Lunar game not running:
  - game log: `AresOS app helper: CONNECTED (tracking windows)` and `Using graphics device: NVIDIA GeForce RTX
    4060 Laptop GPU`;
  - helper log: `desktop connected (minor 0)`;
  - then I closed it. **The Minecraft window (its loading screen) was on his screen for about 5 seconds
    (15:18:35–15:18:40).** The whole run lasted 14 s.
- **Refusals and options:**
  - A helper this script did not start, serving the socket: `Another AresOS app helper is already serving
    /run/user/1001/aresos/shell.sock and run-hub.sh did not start it; stop it first.`
  - A helper named by the record: `Reusing the app helper an earlier run-hub.sh started (PID …); it stays running
    afterwards.` It was still running afterwards.
  - `--helper /nonexistent`, `--helper /usr/libexec` and `--registry <a file>` were each refused with one
    sentence (exit 2).
  - `--helper ../os/config/usr/libexec/aresos-shell --registry ../os/config/usr/share/aresos/apps` started that
    helper with that registry (3 apps).

**No Gradle daemon left.** None remained after any run (checked with `ps`), and every run printed `Daemon will be
stopped at the end of the build`. Nothing is in `.work/`.

## Not verified

- Walking into a logo on the real screen and getting focus back. That needs a world with a zone and the owner's
  hands. `run-hub.sh` was only taken as far as the hello on the loading screen, as the brief asks.
- The Windows side of the test changes: the `@EnabledOnOs(WINDOWS)` tests and `notepadCommand()` returning
  `notepad.exe` were not run on Windows here. The bodies of the skipped tests are untouched.
- Full client test runs on Intel or software rendering (only the headless probes above).
- A real Ctrl+C typed into a terminal (simulated with SIGINT to the process group) and a closed terminal
  (simulated with HUP to the script).

## Linux findings (defects of the mod)

None. The suite found no Linux defect in the mod: the only failures were the Windows-only unit tests and the
Notepad literal in a test. Observations, not defects:
- Linux test screenshots show the helper-unavailable chat line (above), so they differ from the Windows ones.
- An older paragraph in `mod/README.md` is out of date since package 24's `ShellClient`: "On Linux,
  `aresos-shell/1.0` is a stub until the OS helper arrives … All Linux launches, including URLs, fail with an
  unavailable-helper diagnostic". I left it as it is, since it is outside this brief.
- Two Windows unit tests still run on Linux and pass, but partly vacuously, because no Windows path is absolute
  there: `WindowsNotepadAliasTest.otherPathsAndLaunchModifiersStaySeparate` and
  `…defaultNotepadAndStoreNeverAbsorbUnrelatedNotepadExecutable`. They are not skipped because they pass, but a
  Linux pass proves little about them.

## JUDGMENT-CALL

1. **Gradle without a lasting daemon.**
   - What: all three scripts run `./gradlew --no-daemon` in a systemd scope, instead of a daemon plus
     `./gradlew --stop` at the end.
   - Why: `--stop` stops every Gradle 9.8.0 daemon of this user, including other sessions' builds in other
     worktrees on this laptop.
   - Cost: each run starts a fresh single-use daemon (about 10–20 s), and there is no warm daemon between builds.
   - Changing it later: one line in `env.sh`.
2. **The same refusal in `build.sh` and `run-hub.sh`.**
   - What: the brief puts the Lunar/6 GB refusal on `client-test.sh`; I applied it to all three scripts, each
     with `--force`.
   - Why: a build also needs about 6 GB (CLAUDE.md) and should not run beside his game.
   - Alternative: refuse only in `client-test.sh`.
   - Changing it later: remove one line per script.
3. **Silent test runs.**
   - What: `client-test.sh` sends the test game's sound to OpenAL's null device. The brief did not ask for this.
   - Why: it keeps test music off his speakers, and the sound engine still runs.
   - Changing it later: one variable.
4. **cage, not labwc, as the headless compositor.**
   - Why: cage reads no configuration or autostart, exits with its child and returns its exit code. A labwc
     instance would need a private config dir so that the session's autostart never runs in it.
   - cage supports foreign-toplevel, so `run-hub.sh` also works inside it.
5. **run-hub game environment.**
   - What: as the brief says, the game keeps the session's environment (including his PATH) plus the launch
     identity and the offload variables. The helper gets the system PATH, like the supervisor's helper.
   - Difference: package 23's supervisor also sets the game's PATH to the system PATH.
   - Only one run-hub at a time (lock).
6. **6 GB** is read as 6 GiB of `MemAvailable`, the unit `free -g` shows.

## PLAN-GAP

- AGENTS.md rule 6 (`./gradlew --stop`) is unsafe on the shared laptop: it stops other sessions' daemons, busy
  ones included. The scripts avoid it; agents running Gradle directly do not.
- `git checkout -- ../reviews/` does not fully undo a client test run. Fabric numbers screenshots with one
  counter for the whole run, and many tracked names come from earlier, smaller runs. A full run therefore adds
  25 untracked, renumbered PNGs under `reviews/`, on Windows too. The script now says so. Deleting them is left
  to the builder, because a blanket `git clean` could also delete an unfinished report.
- The GPU probe needs `/usr/bin/glxinfo` (in the image today). Without it the script assumes NVIDIA works and
  still prints what the game reported.

## Open questions

- Should the old Linux paragraph of `mod/README.md` be rewritten (see the findings)? That belongs to whoever next
  touches the Linux launcher docs.

## Review fixes 1

Brief `briefs/29-review-fixes-1.md`, for `REVIEW.md` (gpt-6.1-sol on `8ee4aefa`: CHANGES-NEEDED, 3 blocking and 5
should-fix, all accepted). A Claude agent (Opus 5.5) wrote the fixes and was stopped by a usage limit before it
could run them. A fresh Claude agent (Opus 5.5) ran the checks below, fixed the three things they showed, and
wrote this section. What "Done" and "Verified" above say about `run-hub.sh`'s record file, helper reuse and
PID-based stop, about `timeout 30` around the GPU probes, about the lock wait and about Lunar detection no
longer holds; this section replaces it.

### What changed, per finding

The idea behind all of them: every process a script starts runs in a systemd user scope that the script created
and named, `aresos-dev-<name>-<pid>-<random>.scope`, and the script stops things only by stopping its own scopes.
`env.sh` holds that once (`ARESOS_SCOPES`, `aresos_scope_start`, `aresos_scoped`, `aresos_stop_scopes`). No
script remembers a PID to kill, and none reuses what an earlier run left.

1. **Helper cleanup could kill an unrelated process (blocking).** `run-hub.sh` starts its helper in a scope of
   its own (`aresos-dev-run-hub-helper-…`, `TimeoutStopSec=5`), and every exit stops that scope. The record
   file, `own_helper`, the reuse branch and the PID-based `kill` are gone. `setpriv --pdeathsig TERM` stays, as
   a safety net for a script killed with SIGKILL.
2. **GPU probes escaped cleanup (blocking).** Each probe runs through `aresos_scoped` in
   `aresos-dev-client-test-probe-<mode>-…`, with `RuntimeMaxSec=30` and `TimeoutStopSec=5`: systemd stops it
   after 30 s (TERM, then KILL 5 s later), and every exit of the script stops it too. Its output goes to
   `~/.cache/aresos-dev/client-test-probe.log`. No command substitution wraps it, so the script waits with
   `wait` and a signal acts at once.
3. **Signals during startup (blocking).** `aresos_scope_start` adds the unit's name to `ARESOS_SCOPES` before
   `systemd-run` starts. It holds any INT, TERM or HUP (the trap only records it) until the scope is active or
   the command has ended, and then acts on it. Every exit stops all registered scopes, with signals ignored
   meanwhile. Two more changes came from this pass's runs:
   - **A TERM that cage held back.** systemd's stop sends TERM once, to what is in the scope at that moment. A
     TERM right at the start of the main run reached cage while it was still starting. cage handles TERM in its
     event loop, so it first started its client (Gradle), which that TERM had missed. Gradle ran on and
     launched the game, which crashed for lack of a display; the script exited 12 s after the signal (the KILL
     would have come at 20 s). `aresos_stop_scopes` now queues the stop and sends TERM again, every half
     second, to whatever is still in the scopes, until they are gone. systemd still sends KILL after
     `TimeoutStopSec`.
   - **The lock wait.** The previous builder had replaced the background `flock` (and its PID) with a check
     every 0.5 s. In this pass a run checking like that waited 16 minutes, while two client tests of other
     worktrees that had started waiting later went first: a run that only checks loses to every run blocked in
     `flock`. `aresos_lock` now waits in one blocking `flock` on the lock's descriptor, in a scope of the script
     (`aresos-dev-lock-wait-…`, through `aresos_scoped`), so it keeps its place in line and a signal ends the
     wait at once.
4. **Readiness and reuse did not identify the socket's server.** Each run makes a private folder
   `$XDG_RUNTIME_DIR/aresos-dev/run-hub-<pid>/` (mode 0700; `mkdir` fails if it exists), starts the helper with
   `--socket` there, and gives the game `ARESOS_SHELL_SOCKET` with that path. The game starts only once the
   helper's scope is active and the socket in that folder is listening. No other helper uses that path, and
   only this run created the folder. It never uses `$XDG_RUNTIME_DIR/aresos/shell.sock`. At the start, a
   folder of a dead run is removed only when no `aresos-dev-*-<its pid>-*` unit exists; at exit, this run's
   folder is removed. The header says that, once package 23's own helper runs, both helpers watch the same
   windows while this script runs. Peer credentials are not checked and the script sends no hello of its own:
   only processes of the same user can create a socket in that folder, and the helper refuses a hello whose
   desktop instance or launch nonce does not match (`not_authorized`).
5. **Stale refusal checks.** `client-test.sh` checks Lunar and memory again after the lock and the probes,
   right before Gradle; `run-hub.sh` does it again once the helper is serving, right before Gradle. `--force`
   skips both.
6. **Lunar detection.** Only an executable matching `~/.lunarclient/*/bin/java` (also through the home folder's
   real path) counts, not any program under `~/.lunarclient`.
7. **Gradle daemon switches.** `--daemon`, `--stop` and `--status` among the forwarded arguments stop all three
   scripts with one sentence, exit 2 (`aresos_check_gradle_args`). **New in this pass:** `--foreground` as
   well. It starts a Gradle daemon (Gradle's help: "Starts the Gradle daemon in the foreground.") that other
   sessions' builds could connect to until the scope is stopped.
8. **`--keep-screenshots` reported success after a failure.** The folder is created and checked (a directory,
   writable) before the lock; otherwise exit 2. The copy's result is checked (`find … -exec cp … +` fails when
   a copy fails). A failure prints `FAILED to copy this run's screenshots to <dir> (see above); save them
   before undoing the rewritten ones.` and turns exit code 0 into 1.

Size: the four scripts went from 477 to 539 lines, mostly comments in `env.sh`. The brief hoped for no net
growth.

### What I ran and what it printed

All on the laptop on 2026-11-13. No Lunar game was running (its launcher was open, which no longer counts), and
`free -m` showed 6.3–10 GB available before each Gradle run. Three other builders (packages 32, 33 and 34) ran
`build.sh` and `client-test.sh` from their worktrees with the round-1 scripts meanwhile, so
`systemctl --user list-units 'aresos-dev-*'` sometimes listed their `aresos-dev-build-<pid>.scope` or
`aresos-dev-client-test-<pid>.scope` (the old names, without the random part). None of those were mine; below,
"no unit" means no unit of my run, and where the whole listing was empty I say so. Several times the lock was
taken within milliseconds of my run's exit by another worktree's waiting run (its scope is in the next
listing). No process of my run held it then: only the script and the processes in its scopes hold the lock's
descriptor, and all of them were gone.

- `bash -n` on the four files: no errors. The laptop has no `shellcheck`.
- **`mod/dev/build.sh`:** exit 0 after 25 s, `BUILD SUCCESSFUL in 24s`, `All 38 required tests passed :)` (the
  unit tests were up to date; no mod source changed). No unit of mine was left.
- **`mod/dev/client-test.sh`, full:**

  | Run | Scripts | Result |
  |---|---|---|
  | 1 | as handed over (`c1f3bf48`), `--keep-screenshots <dir>` | exit 0 after 6 min 52 s: `BUILD SUCCESSFUL in 6m 51s`, the same 35 pass lines as before, `Rendering headless on nvidia`, the game logged the RTX 4060, `Copied this run's screenshots to <dir>` (33 files, paths kept). No unit left, lock free. |
  | 2 | final (`0e3d7a93`), `--keep-screenshots <dir>` | waited for the lock behind another worktree's run (`Waiting for another client test run on this laptop to finish (…/client-test.lock)...`), then exit 0 after 6 min 46 s: `BUILD SUCCESSFUL in 6m 45s`, the same 35 pass lines, NVIDIA, 33 files copied. The listing at its exit was empty. |
  | 3 | final, `--keep-screenshots <dir>`, the folder made read-only once the game was up | waited for the lock, then `BUILD SUCCESSFUL in 6m 46s` with the same 35 pass lines; the copy failed (below) and the script exited 1. The listing at its exit was empty. |

- **Signals,** final scripts (`0e3d7a93`). Each case was a run of its own; a driver that held the script's PID
  sent the signal and then ran `systemctl --user list-units 'aresos-dev-*' --all --no-legend`, checked the
  lock, and listed the processes in the run's scopes (none in every case).

  | Signal | Exit | Script ended | Listing afterwards |
  |---|---|---|---|
  | TERM during the NVIDIA probe (2 ms after its scope appeared; the script had printed no probe result) | 143 | 0.57 s after it | empty |
  | TERM right at the start of the main run (the moment its start stamp appeared) | 143 | 1.13 s after it; Gradle printed nothing | empty |
  | TERM in the middle (40 s after the game was up, 3 tests passed) | 143 | 1.58 s after it | only package 32's next run |
  | HUP in the middle (same point) | 129 | 15.1 s after it | empty |

  What was in the run's scopes, sampled every 0.5 s after the mid-run signals: at the signal cage, Xwayland and
  three JVMs; 0.5 s later only Gradle's daemon and the game's JVM. After the TERM both were gone at 1.0 s.
  After the HUP the game's JVM took 14.6 s to end (it had just logged `Close the menu and finish moving or
  crafting items before switching AresOS mode`), inside the 20 s before systemd's KILL.

  Earlier runs of the same cases, none of which left a unit:
  - with the scripts as handed over: TERM during the probe 0.18 s; TERM at the start 12.0 s (the cage case under
    finding 3, which led to the stop fix);
  - with the stop fix, before the lock change: TERM during the probe 0.56 s (the probe log ended with `Error:
    unable to open display :1`: `glxinfo` started after cage had gone), TERM at the start 1.11 s, TERM in the
    middle 5.8 s and 1.6 s, HUP in the middle 17.4 s and 1.6 s.

- **`--keep-screenshots`, copy failure:** in run 3 the folder passed the check before the run, and my driver
  made it read-only (mode 555) once the game was up. At the end `cp` printed `cannot make directory
  '<dir>/reviews': Permission denied` (33 times, once per file). Then the script printed `FAILED to copy this
  run's screenshots to <dir> (see above); save them before undoing the rewritten ones.` and `Client tests ended
  with exit code 0 after 6 min 48 s (…)` (the tests' own result), and exited **1**.
- **`run-hub.sh` in a headless cage of my own.** My driver started `cage` with `WLR_BACKENDS=headless` on the
  NVIDIA render node, without the session's `DISPLAY` and `WAYLAND_DISPLAY`, in a scope of its own, and ran
  `run-hub.sh` as cage's client (cage gave it `WAYLAND_DISPLAY=wayland-2 DISPLAY=:2`). An inotify watch on
  `$XDG_RUNTIME_DIR/aresos/` (every event) and on the name `aresos` in `$XDG_RUNTIME_DIR` ran throughout.
  - While it ran: `aresos-dev-run-hub-helper-<pid>-…` and `aresos-dev-run-hub-game-<pid>-…` active; the private
    folder `drwx------ run-hub-<pid>` holding `srw------- shell.sock`, listening (`ss -xl`); the helper
    `python3 /usr/libexec/aresos-shell --socket /run/user/1001/aresos-dev/run-hub-<pid>/shell.sock`; all three
    JVMs of the game's scope with `ARESOS_SHELL_SOCKET` set to that socket, `DISPLAY=:2` and
    `WAYLAND_DISPLAY=wayland-2`.
  - **The hello:** helper log `serving aresos-shell/1.0 on /run/user/1001/aresos-dev/run-hub-<pid>/shell.sock (3
    apps)`, then `desktop connected (minor 0)`; the game printed `AresOS app helper: CONNECTED (tracking
    windows)`. A `grim` of my cage showed the game's first-start screen.
  - **The game ends:** I asked its window to close the way a close button does (a `WM_DELETE_WINDOW` client
    message on my cage's Xwayland; `xdotool windowquit` did nothing there, as cage handles no
    `_NET_CLOSE_WINDOW`, so that first try ended through my own cage's stop instead). The game logged
    `Stopping!`, Gradle `BUILD SUCCESSFUL in 17s`, and `run-hub.sh` printed `Stopped the app helper` and exited
    0, 1.5 s after the close.
  - **TERM** to `run-hub.sh` after the hello: exit 143 after 1.5 s, `Stopped the app helper`.
  - After each of the three runs: no unit of the run, `$XDG_RUNTIME_DIR/aresos-dev/` empty (the private folder
    gone), `$XDG_RUNTIME_DIR/aresos/` the same as before (the empty folder an earlier round-1 run made at
    15:18: same inode, mode, mtime and ctime), and 0 inotify events on it.
- **Refusals:**
  - `build.sh --daemon`, `--stop`, `--status`, `--foreground`; `client-test.sh -- tasks --daemon` and
    `client-test.sh -- --foreground`; `run-hub.sh --stop` and `run-hub.sh --foreground`: each printed
    `<script>: Gradle's <switch> is refused: these scripts run Gradle without a lasting daemon and leave other
    sessions' daemons alone.` and exited 2.
  - `--keep-screenshots` with a read-only folder, a folder under it, and `/etc/passwd`: `client-test.sh:
    --keep-screenshots: <path> is not a directory this run can write to.`, exit 2.
  - **Lunar,** tested with a fake home folder in `.work/lunar-test/home/` (ignored by git), never touching
    `~/.lunarclient`. Its `.lunarclient/jre/fake-zulu/bin/java` is a `jlink` runtime (`java.base` only) of the
    Temurin 25 JDK, running a class that sleeps; `.lunarclient/launcher/lunarclient` is a copy of
    `/usr/bin/sleep`. With `HOME` set to that folder:
    - with nothing running, and with the copy of `sleep` running there, `aresos_lunar_game_pids` printed
      nothing;
    - with that `java` running, it printed the process's PID, and `build.sh`, `client-test.sh` and
      `run-hub.sh` each printed `The owner's Minecraft (Lunar Client, PID 433519) is running; try again once it
      has closed, or pass --force.` and exited 75. (`run-hub.sh` ran with `--helper /usr/bin/false`, `DISPLAY`
      unset and a made-up `WAYLAND_DISPLAY`, so it could not have reached the screen had it not refused.)
    - With the real home folder and the Lunar launcher open, it printed nothing.
- **Stand-in checks of `env.sh`** (scratch scripts outside the repo that source it):
  - A scoped command that starts a child just after its TERM: the stop took 20.1 s with the handed-over
    `env.sh` (the child ran until the KILL) and 0.54 s now. No unit was left either way.
  - A scope with the probe's options (`TimeoutStopSec=20`, then `RuntimeMaxSec=3` and `TimeoutStopSec=5`)
    around a command that ignores TERM: `systemctl show` gave `TimeoutStopUSec=5s` (the later option wins),
    and systemd killed it after 8.4 s (3 s, then 5 s).
  - The lock, against a blocking `flock` that started waiting 0.3 s later: the old wait got the lock first in 0
    of 6 rounds, the new one in 6 of 6. TERM while waiting: exit 143 after 0.014 s, no unit left.

### Not verified

- A real Ctrl+C in a terminal and a really closed terminal: the runs above used TERM and HUP to the script.
  INT to the process group was only checked by the previous builder's stand-in (exit 130).
- A probe that really hangs: the 30 s limit was checked with the stand-in scope above, not with a wedged cage.
- `run-hub.sh` on the real screen was not run in this round, as the brief says, so neither was walking into a
  logo.
- Two helpers at once: package 23's own helper is not on the laptop yet.

## Review fixes 2

Brief `briefs/29-review-fixes-2.md`, addressing `REVIEW-2.md` on `5e53ca2f`.
Builder: Codex, gpt-6.1-sol. This section supersedes round 1's claims about
Gradle option spellings, unbounded startup and unchecked systemd query results.
No mod source or tests changed.

### Done

1. **Gradle options (`db29de28`).** The shared guard rejects `--daemon`,
   `--stop`, `--status`, `--foreground` and all four single-dash forms in all
   three scripts.
2. **Unknown systemd state (`ad135550`).** Cleanup retries stop requests and
   checks each query's status separately from its output. Only a successful
   inactive/failed result confirms absence. After 30 seconds without
   confirmation it prints one error naming the units, exits 1 and skips folder
   cleanup. Stale-folder checks in `run-hub.sh` retry failed listings for the
   same deadline and preserve the folder on failure. `systemctl` uses `PATH`
   so the checks can be exercised with a private wrapper.
3. **Startup deadline (`70ade912`).** Startup waits at most 15 seconds for
   activation. If its launcher is still running, it kills and reaps that live
   child before exiting, preventing a late command launch. Exit cleanup stops
   the unit by name; a deferred signal supplies the exit status (TERM: 143),
   otherwise the timeout exits 1. `systemd-run` also uses `PATH` for stand-ins.
4. **Scope ownership (`cbff956d`).** Each candidate name is checked before
   launch; existing names get another random suffix. A launcher that ends
   unsuccessfully before activation is reaped and unregistered, and the caller
   propagates its failure without stopping that name. An already active scope
   remains owned if its command subsequently fails, so its children still get
   cleaned up.

`mod/README.md` describes the deadlines, single-dash options and known limits.
Each fix has its own commit with a `Model: gpt-6.1-sol` trailer.

### Verified

All checks ran in this worktree on the owner's Linux laptop, without sudo or
`--force`. The real session's display variables were removed before launching
the full client checks; the client script created its own headless cage and
Xwayland. The `run-hub.sh` stale-folder stand-in used a private runtime folder
inside `.work/`, a nonexistent display name and `/usr/bin/false` as helper;
it never started a helper or game.

- `bash -n mod/dev/{env,build,client-test,run-hub}.sh`: exit 0, no output.
  `git diff --check`: exit 0, no output. `shellcheck` is not installed.
- One loop over the eight Gradle spellings, invoking each of `build.sh`,
  `client-test.sh` and `run-hub.sh` with `-- <spelling>`: all 24 exited 2 and
  printed `Gradle's <spelling> is refused: these scripts run Gradle without a
  lasting daemon and leave other sessions' daemons alone.`
- `python3 .work/review-fixes-2/query-checks.py` on the final scripts, using a
  private `PATH` wrapper that fails the first stop and selected state queries:
  - Persistent failed state queries: exit 1 after 29.40 s; stop retried; real
    scope inactive; stand-in lock free. Printed `FAILED: scopes not confirmed
    gone after 30 s: <unit>.` once.
  - Three transient failed state queries: exit 0 after 1.66 s; stop retried;
    real scope inactive; lock free.
  - Failed stale-folder listings: exit 1 after 29.32 s, one error naming
    `aresos-dev-*-777777777-*` and the retained folder. Its marker survived;
    no helper/game started and no run folder was deleted.
- `python3 .work/review-fixes-2/private-cleanup-check.py`: exit 1 after 30.50 s;
  one error naming the unconfirmed scope, this run's private folder retained,
  cleanup callback skipped, lock free.
- `python3 .work/review-fixes-2/startup-checks.py` on the final scripts, with
  a launcher that never activates: exit 1 after 14.74 s; with TERM sent after
  one second, exit 143 after 14.98 s. Each printed `Scope <unit> did not
  activate within 15 s; cancelled its launcher.` once. Launchers were reaped,
  no late command ran, scopes were inactive and both stand-in locks were free.
- `python3 .work/review-fixes-2/ownership-checks.py`: forced suffix 111 to name
  an existing real scope, then provided suffix 222. Printed `PASS collision:
  suffix 111 existed; suffix 222 used; existing scope still active afterwards;
  new scope gone; lock free.` The driver then stopped only its own fixture
  scope. Failed creation exited 42, or 143 with TERM pending; both printed
  `PASS failed creation`, made no stop/kill request and left the lock free.
- `mod/dev/build.sh`: exit 0, `All 38 required tests passed :)`,
  `BUILD SUCCESSFUL in 20s`, `17 actionable tasks: 3 executed, 14 up-to-date`.
- `python3 .work/review-fixes-2/old-standins.py`: the round-1 stand-ins also
  passed: a child launched during TERM was cleaned up in 0.59 s (exit 0);
  `RuntimeMaxSec=3` plus `TimeoutStopSec=5` killed a TERM-ignoring command in
  8.33 s (exit 137); TERM while waiting for a lock exited 143 in 0.02 s, with
  the lock free after the holder ended. An initial scratch harness had broken
  shell quoting and timed out after 30 s; these are the corrected harness's
  results. No process from the failed harness remained afterwards.
- `python3 .work/review-fixes-2/lock-order-check.py`: `PASS lock order` in
  all six rounds; the earlier scoped waiter acquired the lock before a later
  blocking `flock` each time.
- A created scope whose command starts a child and exits 42: printed `PASS
  failed command in created scope: exit 42; child stopped; lock free.`

- `python3 .work/review-fixes-2/full-checks.py` launches
  `mod/dev/client-test.sh --keep-screenshots <absolute .work path> build`
  twice, with `DISPLAY`, `WAYLAND_DISPLAY` and `WAYLAND_SOCKET` removed from
  its environment. Each invokes `./gradlew --no-daemon runClientGameTest build`,
  covering the full build and client tests twice as required by `AGENTS.md`.

  | Run | Result |
  |---|---|
  | 1 | Exit 0 after 426.15 s; `BUILD SUCCESSFUL in 7m 5s`; all 35 client pass lines, `All 38 required tests passed :)`; RTX 4060 headless; 33 PNG screenshots copied. |
  | 2 | Exit 0 after 424.22 s; `BUILD SUCCESSFUL in 7m 3s`; all 35 client pass lines, `All 38 required tests passed :)`; RTX 4060 headless; 33 PNG screenshots copied. |

`free -g` showed 10 GiB available before the standalone build and each combined
run. No run returned 75 or required a retry. Both full runs printed that their
single-use Gradle daemon would stop at the end of the build.

Afterwards, `systemctl --user list-units 'aresos-dev-*' --all --no-legend --plain`
printed nothing and a nonblocking `flock` confirmed the shared client-test lock
was free. No scope, game, compositor or Gradle daemon from these runs remained.
The final syntax and whitespace checks again exited 0 with no output.

Each run's 33 PNG screenshots and logs are preserved in the ignored
`.work/review-fixes-2/` (the `client-1-screenshots/` and
`client-2-screenshots/` folders). Restored the two tracked PNGs rewritten by the
tests and removed 25 generated untracked PNGs after saving the copies; no
screenshot changes are committed. **Files left in `.work/` over 500 MB: none.**

### Not verified

- A physical Ctrl+C or an actually closed terminal; these remain signal-only
  checks as in round 1. A truly wedged GPU probe remains represented by a
  stand-in.
- `run-hub.sh` on the owner's screen, walking into a logo, or two helpers
  watching windows at once. No real-session window was opened.
- A systemd manager that hangs calls, or a process racing to take a name
  between its successful absence check and creation. These are the brief's
  accepted limits, now documented in `mod/README.md`.

**JUDGMENT-CALL:** none beyond the limits explicitly accepted by the brief.

**PLAN-GAP:** none new. As recorded above, stopping all Gradle daemons with
`./gradlew --stop` would affect other builders. These scripts use single-use
Gradle daemons and clean up their own scopes instead.

**Open questions:** none.
