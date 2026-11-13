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

## Review fixes 1: progress

Work in progress (brief `briefs/29-review-fixes-1.md`). Done (code committed): all seven fixes, as planned below.
Verified so far: `bash -n`; a stand-in harness (exit codes 0/3, TERM 143, HUP 129, INT to the process group 130,
TERM at 19 points during scope start: no unit left); refusals of `--daemon/--stop/--status` (exit 2, all three
scripts) and of unwritable `--keep-screenshots` destinations (exit 2); Lunar detection with a jlinked runtime in a
fake HOME under `.work/lunar-test/` (Java: exit 75 in all three; non-Java program: not counted).
Left: `build.sh`, one full `client-test.sh`, the four signal cases, the copy-failure exit code, `run-hub.sh` in a
headless cage of my own, README, the final report section. The plan:
- `env.sh`: `aresos_say` writes to a copy of stderr saved at load time (today a signal while a scoped run's
  call is redirected sends the cleanup messages into that redirect, e.g. the compositor log).
- `env.sh`: a list `ARESOS_SCOPES` of this script's units, named `aresos-dev-<name>-<pid>-<random>.scope`.
  `aresos_scope_start <name> [systemd-run options] -- <command>` registers the unit, starts
  `systemd-run --user --scope --collect` in the background with signals deferred (the traps set a pending
  code instead of exiting), waits until the unit is active or the job has ended (`jobs -rp`, never a PID kill),
  then acts on a pending signal. `aresos_scoped` = start + `wait` + stop. Every exit stops all registered
  units (`systemctl --user stop`, TERM then KILL after `TimeoutStopSec`).
- `aresos_lock` polls `flock -n` every 0.5 s instead of a background `flock` with a PID to kill.
- GPU probes: `aresos_scoped probe-<mode> --property=RuntimeMaxSec=30 --property=TimeoutStopSec=5`, output to
  `~/.cache/aresos-dev/client-test-probe.log`, no command substitution around them.
- Check again (Lunar, memory) right before Gradle in `client-test.sh` and `run-hub.sh`.
- Lunar: only `/proc/*/exe` matching `~/.lunarclient/*/bin/java`. Positive test: a jlinked runtime in a fake
  HOME under `.work/` running a sleeping Java program.
- `--daemon`, `--stop`, `--status` refused in all three scripts (one shared function in `env.sh`).
- `--keep-screenshots`: mkdir and writability check before the run; copy result checked, failure turns exit 0
  into 1.
- `run-hub.sh`: private `$XDG_RUNTIME_DIR/aresos-dev/run-hub-<pid>/` (0700), helper with `--socket` there in its
  own scope (`setpriv --pdeathsig TERM` kept as a SIGKILL safety net), no record file/reuse/PID kill; leftover
  folders removed only when no `aresos-dev-*-<pid>-*` unit exists; the folder is removed at exit.
