# 23 REPORT: Minecraft starts in AresOS

Built by a Claude agent (Opus 5.5). Brief: `briefs/23-minecraft-starts.md` (empire board brief 264).
Branch `pkg/23-minecraft-starts`, PR #36. Review: Codex gpt-6-astra (high), fresh context.

Nothing was pushed to a registry, signed or published. The release pin is unchanged.

## What the owner will see

- **First start after the update:** a small terminal says "AresOS: first start" with three steps, and Prism
  Launcher opens on its own sign-in page. He signs in with his Microsoft account in Prism. Prism downloads
  Minecraft 26.2 (a few minutes, once) and starts it on the title screen. He clicks **AresOS**, keeps seed 49 (or
  picks another) and clicks **Create**: the existing mod builds the hub exactly as on Windows. The terminal closes
  by itself once he is in the hub.
- **Every later start:** labwc comes up and Minecraft opens straight into the AresHub world, borderless and
  maximized, on the NVIDIA GPU. No terminal opens at login any more; the hub's Terminal app and Super+Ctrl+Escape
  still give one.
- **If Minecraft crashes:** it starts again after 5 s, then after 10 s. A third crash within five minutes, or a
  third in a row without 30 healthy minutes in between, stops the restarts: a terminal says what happened, where
  the logs are, and to type `retry`. That stop survives a reboot.
- **If he quits Minecraft himself:** nothing restarts; a terminal says "Minecraft was closed" and `retry` opens the
  hub again.
- **If Prism needs him to sign in again** (or the network is down): Prism shows its own dialog. If Prism ends
  without starting the game, a terminal says so and waits for `retry`.
- **If something is wrong with the world or the files:** a missing hub (one that existed before), a damaged hub, a
  changed desktop instance or an image file that doesn't match its pin each stop into a terminal that names the
  problem and the fix. AresOS never makes a replacement world and never changes the instance or the world.

## Done

### A. Prism and Java 25 in the image

- **Java 25:** Fedora's `java-25-openjdk-headless-1:25.0.4.1.1-1.1.fc44` and its three new dependencies
  (`java-25-openjdk-crypto-adapter`, `javapackages-filesystem`, `tzdata-java-2026f-1.fc44`) join
  `os/packages.lock.json` through the existing lock (resolved by run 42803572026; no other package in the lock
  moved). The game uses `/usr/lib/jvm/java-25-openjdk/bin/java`, a real file of that package.
- **Prism Launcher:** not in Fedora (checked: no `prismlauncher*` in `fedora`/`updates`; only a COPR side
  repository exists, which the brief rules out). The image takes Prism's official Linux bundle
  `PrismLauncher-Linux-Qt6-Portable-11.1.1.tar.gz` (Prism 11.1.1, 2026-09-28, the newest release) from its pinned
  GitHub URL, accepted only with its pinned SHA-256 and size (`e21949a8…e09e823`, equal to GitHub's own asset
  digest). `os/build.sh` unpacks it into `/usr/lib/prismlauncher` (Python's `data` filter: root-owned, no
  setuid/setgid, no group/world write; the archive records its files as UID 1001, which is `ares`), removes
  `portable.txt` and both `prismlauncher_updater` files, and links `/usr/bin/prismlauncher`. Prism's own log
  confirms the result: `Updates Enabled: No` (its updater turns on only when `bin/prismlauncher_updater` exists)
  and `Adjusted by: "Persistent data path"` (data in `~/.local/share/PrismLauncher`, not next to the binary). Every
  unpacked file's hash is recorded in `/usr/share/aresos/manifest/prism-files.sha256`. No desktop entry or MIME
  handler is installed (the bundle's would make Prism the handler for every `.zip`). Prism's UI stays available as
  `prismlauncher` for setup and re-login.

### B. The managed `AresDesktop` instance (`os/minecraft/desktop.lock.json`)

- **Pinned inputs** (`/usr/share/aresos/minecraft`, all from their pinned URLs and SHA-256, checked again at every
  desktop start):
  - Fabric Loader 0.19.5 and its six libraries (asm 9.10.1 ×5, sponge-mixin 0.17.4+mixin.0.8.7) from
    `maven.fabricmc.net`; each hash equals Maven's published `.sha256` and Fabric's own launcher profile for 26.2.
  - Fabric API 0.161.0+26.2 (Modrinth; byte-identical to Fabric's Maven copy), the newest for 26.2.
  - The AresOS mod jar, built from this repository's `mod/` (below), SHA-256 `8b04c511…65386743`.
  - `patches/net.fabricmc.fabric-loader.json`: a Prism component for Fabric Loader whose libraries are all
    `"MMC-hint": "local"`, so Prism loads the loader only from the image and never fetches it. It is generated
    from the lock (`loader_patch`) and a test keeps the shipped file equal to it. Like Fabric's own launcher profile
    for 26.2, it needs no intermediary mappings (26.x is not obfuscated).
- **The mod jar is reproducible and pinned:** `mod/build.gradle` turns off archive timestamps and fixes the entry
  order (no other mod change). `os/ci/build-mod.sh` builds the jar from the committed `mod/` in a digest-pinned
  `eclipse-temurin:25.0.5_8-jdk-noble` container and requires the pinned hash. `check_build=resolve` builds it twice
  from clean copies and requires equal bytes (run 42803572026: both `8b04c511…`). `check_build=build` builds it
  before the image and copies it into the build context (`os/minecraft/aresos.jar`, ignored by Git); `build.sh`
  checks it again.
- **Provisioning** (`provision()` in `/usr/libexec/aresos-desktop`, at every start, as `ares`):
  - Creates `~/.local/share/aresos/worlds` and, only if no instance exists yet,
    `~/.local/share/PrismLauncher/instances/AresDesktop`. It is assembled in a hidden staging folder and renamed
    into place, so it appears whole or not at all. An existing instance, complete or not, is never touched; nor is
    an existing `prismlauncher.cfg`.
  - The instance: `instance.cfg` (wrapper command `/usr/libexec/aresos-desktop-java`, Java 25 pinned, heap
    512 MiB to 3 GiB (B5), console never shown, maximized window, Prism's own GPU switch off),
    `mmc-pack.json` (Minecraft 26.2, Fabric Loader 0.19.5), `minecraft/options.txt` (render 8 and simulation 5
    chunks (B5), no exclusive fullscreen, no first-launch accessibility screen).
  - `patches`, `libraries` and `minecraft/mods` are links into `/usr/share/aresos/minecraft`, so they are read-only
    and an AresOS update or rollback changes them with the image. `minecraft/saves` links to
    `~/.local/share/aresos/worlds`: the world lives there and is linked into this instance only (section 5).
  - A first-start `prismlauncher.cfg` (only if none exists) keeps Prism's first-run wizard to its sign-in page
    (English, system theme, our Java, no automatic Java download or switching).
  - **A pin mismatch stops into recovery:** a changed image input (`verify_inputs`), or an instance whose links,
    wrapper command, Java path, Minecraft or Fabric Loader version or components differ (`check_instance`), opens
    recovery with the exact difference. Prism's own rewrites (`lastLaunchTime`, the LWJGL component it adds) are
    not drift. `aresos-desktop reset-instance` moves a drifted instance aside (dated, nothing deleted, and the old
    copy loses only its link to the worlds); the next start makes a fresh one with the same world.
- **No Sodium or Iris.** Minecraft itself is never in the image; Prism downloads it after he signs in. Nothing reads
  or edits Prism's account file.

### C. The world

- First start: the hub is created by the mod's existing code, the way Windows does it today: the title screen's
  **AresOS** button, then `HomeCreateScreen` (seed 49 prefilled, placeholder hub), then `NetherHome` writes the
  manifest, `DesktopWorld` marks the save and the hub is built on the first server start (packages 04/04c). Because
  `minecraft/saves` is the worlds folder, the save lands in `~/.local/share/aresos/worlds/AresHub`. No mod code
  changed for this (JUDGMENT-CALL 1).
- Later starts: `--world AresHub` (Prism's quick play), checked first by `check_world`: `level.dat` (or
  `level.dat_old`) and the desktop marker `data/aresos/desktop.dat` must be readable gzip, and an interrupted hub
  build (`aresos-home.provisioned` not `complete`) counts as damaged.
- Missing (after the hub has been seen once, recorded in the state file), damaged or interrupted: RECOVERY,
  latched. Never a replacement: `aresos-desktop forget-hub` (only while `AresHub` is absent) is the explicit way
  back to first-start creation.

### D. The supervisor (`/usr/libexec/aresos-desktop`, Python standard library)

- **Start:** labwc's autostart now runs the polkit agent and `/usr/libexec/aresos-desktop session` (no terminal).
  `session` is a small keeper that runs `aresos-desktop supervise` and restarts it after a failure, up to 5 times in
  10 minutes, then shows a terminal with the reason.
- **States (B2):** SETUP (no hub yet: Prism's sign-in, then the title screen), STARTING, IN_WORLD, AUTH_REQUIRED,
  RECOVERY. SETUP, AUTH_REQUIRED and RECOVERY open a foot terminal (`app_id aresos.desktop`) with the message and a
  `retry` command. It is set up like the recovery terminal (system PATH, never his `~/.bashrc`) and closes when the
  hub is reached or a new launch starts.
- **Launch:** `systemd-run --user --scope --quiet --collect --slice=aresos.slice
  --unit=aresos-desktop-<launch>.scope --property=MemoryHigh=5G -- /usr/bin/prismlauncher --launch AresDesktop
  --world AresHub` (no `--world` in SETUP). B5: the game, Prism and its children get their own group with the 5 GiB
  soft target; apps stay in the helper's `app.slice` scopes; no hard limit yet. Prism gets the session's
  environment with the system PATH and no launch secrets.
- **The real JVM:** Prism runs `aresos-desktop-java <java> <args>` (its wrapper command) instead of Java. The
  wrapper
  - takes the desktop lock (`$XDG_RUNTIME_DIR/aresos/desktop.lock`); Java inherits it, so it is held from loading to
    the JVM's final exit (B2), and a second desktop cannot start;
  - asks the supervisor for the launch over its socket (peer UID and PID checked; only the `AresDesktop` instance
    and the pinned Java are accepted; refused while recovery is latched or a desktop already runs);
  - starts Java as its child with the launch nonce, desktop instance and GPU variables, reports the JVM's PID (the
    supervisor checks it is the wrapper's child, records its start time and watches it with a pidfd) and its exact
    exit status (also in `desktop-exit.json`, in case the supervisor restarted meanwhile);
  - makes Java die with it (PR_SET_PDEATHSIG) and forwards termination signals. Prism's stdin (its launch script),
    stdout and stderr pass straight through.
  A restarted supervisor adopts a JVM that still runs (PID and start time) and never starts a second one.
- **Package 24's helper (brief item 6, first branch):** the supervisor starts `/usr/libexec/aresos-shell` for every
  launch with `ARESOS_DESKTOP_INSTANCE` (one per session) and a fresh `ARESOS_LAUNCH_NONCE`, and the wrapper gives the
  game the same two (B1). A helper that exits is restarted with the same nonce after 2 s (at most 5 times a minute).
  Readiness reaches the supervisor on a new one-way **status pipe** (`ARESOS_SHELL_STATUS_FD`): the helper writes
  `desktop_connected`, `world_ready` and `heartbeat` lines for the authenticated desktop only, drops a line rather
  than block, and never passes the descriptor to apps. This answers package 24's open question about where
  readiness lives.
- **Restart policy (B2):**
  - An unexpected exit (non-zero) restarts after 5 s, then 10 s; three failures within five minutes or three
    consecutive failures (ready-then-crash cycles four minutes apart included) latch RECOVERY.
  - The consecutive count, the failure times, the latch and whether the hub has been seen persist in
    `~/.local/state/aresos/desktop.json` (atomic writes); an unreadable file stops into recovery instead of losing a
    latch.
  - Reset only by 30 continuous healthy minutes in the world (heartbeats at most 20 s apart; leaving the world or a
    gap restarts the period) or the owner's `retry`.
  - Never restarted automatically: exit 0 (he quit), a kill by SIGKILL (memory pressure or force; latched, not
    counted), auth states (Prism ending before the game), setup, and the 120-s prepared-start timeout, which shows
    recovery but never kills the game (if the hub appears later, the terminal closes).
- **Logs:** `~/.local/state/aresos/desktop.log` (rotated at 512 KiB). Recovery texts point there and to Minecraft's
  `latest.log` and `crash-reports/`.

### E. The GPU

The wrapper gives only the game `__NV_PRIME_RENDER_OFFLOAD=1`, `__GLX_VENDOR_LIBRARY_NAME=nvidia` and
`__VK_LAYER_NV_optimus=NVIDIA_only`, and only when `/proc/driver/nvidia/gpus` lists a GPU. These are the variables
switcheroo-control and Prism's own discrete-GPU switch use: NVIDIA's PRIME render offload renders this one process
on the RTX 4060 for GLX (Xwayland), EGL and Vulkan, while Intel keeps driving the session and every other app
(OS-BASE section 2: per-game offload, never session-wide). Variables that Prism's bundle set for Prism itself, any
other GPU variables and `LD_PRELOAD`/`LD_LIBRARY_PATH` are removed from the game's environment, and its PATH is the
system PATH. OpenGL, no shaders (Minecraft's default renderer; no Sodium or Iris). JUDGMENT-CALL 5 covers a machine
without the NVIDIA driver.

### F. Session files

- `labwc/autostart`: the polkit agent, then the supervisor (no terminal).
- `rc.xml`: a window rule makes the hub window (`app_id aresos-desktop`, set by package 24's mixin) borderless and
  maximized. Super+Ctrl+Escape is unchanged.
- `/usr/share/aresos/desktop-view.bashrc`: the message terminal's rcfile.
- `/usr/bin/aresos-desktop` links to the supervisor for his commands (`status`, `retry`, `forget-hub`,
  `reset-instance`).
- `os/README.md` describes the desktop and the mod-jar step.

### G. Verification code

- `os/tests/test_aresos_desktop.py` (71 tests):
  - pinned inputs and the shipped loader patch;
  - provisioning: exact layout, idempotent byte for byte, an existing instance and Prism config never overwritten,
    a failed provisioning leaves nothing, drift reported but not repaired, Prism's own rewrites tolerated;
  - world checks;
  - the exact `systemd-run`/Prism command and the environments (Prism without secrets; the game with nonce, system
    PATH and NVIDIA only with the driver; the wrapper's scrubbing);
  - the restart policy;
  - the supervisor's states with a fake runner: first start, hub creation, crash backoff and latch, the latch
    surviving a restart and refusing the wrapper, retry, ready-then-crash cycles, the 30-minute reset and
    heartbeat gaps, quit, kill, unknown exits, the exit file, slow start without a kill, AUTH_REQUIRED, early Prism
    failure, refusals, a held lock, adoption, the helper's restart budget, every message's instruction;
  - on Linux, the real wrapper (environment, stdin, exit status, refusal, no supervisor, the lock held until the
    JVM ends, the game dying with a killed wrapper, signal forwarding) and the real event loop with stand-ins for
    Prism, the helper and Java (crash, restart, latch and `retry` over the real socket; AUTH_REQUIRED; malformed and
    foreign requests; an internal error answered without stopping the supervisor).
- `os/tests/test_aresos_shell.py`: three tests for the status pipe (only authenticated desktop events; never blocks;
  a closed pipe switches it off; apps never inherit it).
- `os/tests/test_everyday_account.py`: two assertions pinned the old autostart line (`aresos-terminal &`); they now
  pin the new one, which is the decision the brief changes. Nothing was deleted or skipped.
- `os/ci/check-resolve.sh`: a package 23 inventory (Java in the base and in Fedora, Prism not in Fedora, the pinned
  bundle's hash, layout, `--version`, `--help` and a headless start as an unprivileged user); `check-build.sh
  resolve` builds the mod jar twice.
- `os/ci/image-checks.sh` (inside the built image): Java 25 is the locked package and runs as `ares`; Prism is the
  pinned version, its files match the recorded hashes, are root-owned and not group/world-writable, with no
  updater, portable marker or setuid file, and its own log says updates off and data in his home; every
  provisioning input matches its pin; the autostart and window rule; provisioning as `ares` from the real inputs is
  idempotent and reports a changed instance; no system unit starts the desktop; the supervisor, wrapper, view and
  Prism join the absolute-startup-command check. `check-image.sh` also compares the image's `desktop.lock.json`
  with the repository's.
- `os/ci/overlay/checks.py` (VM): the first terminal is now the desktop's message window; the shortcut check
  requires a recovery terminal next to it (both recovery-style), and a new `desktop_session` check requires the
  keeper, supervisor, helper and Prism to run as `ares` and nothing of the desktop as root, state SETUP, the helper
  holding the session's instance and the launch's nonce, Prism without the nonce, Prism in
  `aresos.slice/aresos-desktop-<launch>.scope` with `memory.high` 5 GiB, the instance's four links, and Prism's log
  (updates off, launching `AresDesktop`). `shadow-names.txt` adds `prismlauncher`, `java`, `systemd-run`,
  `systemctl`, `aresos-desktop`, `aresos-desktop-java`, `aresos-shell` and `cat`.
- Bound sources: no file bound by the package 16 walk changed (`os-image.yml` and `vm.py` are untouched), so
  `os/manifest/ci/16/pending-rebind.json` is unchanged (`test_checkout_sources` passes).

## Verified

CI runs on this branch (`https://github.com/Ares-Empire/AresOS/actions/runs/<id>`):

| Run | What | Result |
|---|---|---|
| 42803572026 | `check_build=resolve` on `a2e6c997` | Success. Java 25 resolves to four new packages and nothing else moves; no Prism in Fedora; the Prism bundle matches its pin, `--version` prints `PrismLauncher 11.1.1`, a headless start logs `Updates Enabled: No` and `Persistent data path`; the mod jar built twice from clean copies: both `8b04c511…65386743` (`MOD_JAR_REPRODUCIBLE`). Evidence: `runs/resolve-42803572026/`. |
| 42807403559 | `check_build=build` on `92f03f2e` | Failed at the new Prism version check: Prism prints its version and then an empty line, and the check took the last line. Everything before it passed (image built, mod jar pinned, Java 25, Prism files, ownership, hashes). Fixed in `36f6dcc4` (exact line match). |
| **42809824712** | **`check_build=build` on `36f6dcc4`, with the VM boot** | **Success.** `MOD_JAR_PINNED 8b04c511…`; 39 in-image PASS lines and `IMAGE_CHECKS_PASSED`, including Java 25 (`java-25-openjdk-headless-1:25.0.4.1.1-1.1.fc44`, `openjdk version "25.0.4.1"` as `ares`), `Prism Launcher PrismLauncher 11.1.1 from its pinned bundle`, the pinned inputs, the autostart, provisioning as `ares` and no system unit; `all 30 absolute startup commands exist`; `polkit: 21 rule files, 401 actions, 0 change with wheel, 73 denied to ares, 132 reviewed passwordless, 0 cached defaults`, `POLKIT_CHECK_PASSED`; `Image manifest locks equal the reviewed locks` (now including `desktop.lock.json`); `CHECK_BUILD_PASSED`. VM pass: guest policy, power events, the recovery shortcut, tty3 login and `PASS: offline logind power-key path`; `UEFI VM checks passed`; `CHECK_BUILD_VM_PASSED`. The new `desktop_session` check, in the real labwc session: keeper, supervisor, helper and `/usr/bin/prismlauncher --launch AresDesktop` all UID 1001, state `SETUP`, the helper with the session's instance and the launch's nonce, Prism in `/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-desktop-<launch>.scope` with `memory.high` 5368709120, the four instance links, Prism's log `Version 11.1.1`, `Updates Enabled: No`, `Persistent data path`, `Application root path "/usr/lib/prismlauncher"`, `ID of instance to launch "AresDesktop"`; both terminals (the desktop's message window and the recovery terminal) recovery-style; none of the 25 shadowing programs in `~/.local/bin` ran. Evidence: `runs/build-42809824712/`. |
| 42809903934 | `checks_only=true` on `36f6dcc4` (full suite natively) | `Ran 927 tests`, `FAILED (failures=7, errors=111, skipped=27)`: all 118 in package 22's `test_owner_update`, exactly as on main (run 42815704308 on `6978dc3c`: `Ran 853 tests`, the same 118; PLAN-GAP 5). Every package 23 test passed natively. The step stops at that unittest command, so its compile and syntax sweeps did not run there (they ran locally: `py_compile` and `bash -n` on every changed file). Summary: `runs/checks-42809903934/summary.txt`. |

Laptop (Windows, `mod\gradlew.bat build runClientGameTest`; the mod changed only in `build.gradle`; no Lunar Client,
no other Minecraft or Gradle running, no WSL suite during them):

- **Run 1** (6.4 GB free): `BUILD SUCCESSFUL in 7m 41s`. Unit tests: 62 `PASSED`, none failed or skipped. Server
  game tests: `All 38 required tests passed :)`. Client game tests: all passed (`01c`, `04`, `04b`, `04c`, `04d`,
  `07`, `07b`, `08`, `08b`, `09`, `09b`, `09c`, `09d`, `24`).
- **Run 2** (6.3 GB with run 1's daemon): `BUILD SUCCESSFUL in 7m 14s`, the same 38 server game tests and all client
  game tests passed again (unit tests up to date from run 1).
- After each run: `git checkout -- reviews/` and `git clean -f -- reviews/` (the client tests rewrite other
  packages' screenshots; package 23 adds none). Then `gradlew --stop`: `1 Daemon stopped`.
- The laptop's jar (`a86c2cf3…`, Temurin 25.0.4) differs from the pinned CI build (Temurin 25.0.5 container), as
  expected (JUDGMENT-CALL 14).

WSL (Ubuntu 24.04, Python 3.12, fresh `git clone --depth 1 -b pkg/23-minecraft-starts` into `/tmp` at `36f6dcc4`,
no other suite running, 5.0 GB free):

- Full suite, plain and `-B`: both `Ran 927 tests`, `FAILED (failures=1, errors=12)`. Every failure is in the known
  WSL-only set that also fails on main: `test_greeter` 3 errors, `test_inherited_homebrew` 1 failure + 7 errors,
  `test_sysusers` 2 errors. Everything else passes, including `test_aresos_desktop` (71), `test_aresos_shell` (67),
  `test_everyday_account`, `test_shell_assertions` and `test_checkout_sources`.
- Focused from the worktree during the work: `test_aresos_desktop` 71 OK (several times, also after the last
  supervisor change), `test_aresos_shell` 67 OK, `test_shell_assertions` 8 OK, `test_checkout_sources` 4 OK.

Other:

- Every Fabric jar's SHA-256 was computed from a fresh download and equals Maven's published `.sha256`; asm and
  sponge-mixin also equal Fabric's launcher profile for 26.2; Fabric API is byte-identical on Modrinth and Maven.
- Prism's behaviour was read in its 11.1.1 source: command-line options, `updaterEnabled()`, the data path and
  portable markers, the setup wizard's pages, `--launch` quitting when the game ends, the wrapper invocation
  (`LauncherPartLaunch::executeTask`: wrapper, then Java and its arguments, launch script on stdin), local
  libraries (`MMC-hint: local`, looked up in `instance/libraries/<artifact>-<version>.jar`) and custom patches.
- `.work/` holds only run evidence (under 1 MB); nothing over 500 MB is left.

## Not verified (needs the laptop, the owner or a later package)

- **The real boot into the hub on the laptop** (the P3 trial, after a release with the owner's OK). Everything
  below is part of it.
- Prism's real hand-off to the wrapper with a real Minecraft. The wrapper is tested with Prism's exact argument
  shape and stdin from Prism 11.1.1's source, and the VM shows Prism starting for `AresDesktop`, but no JVM was
  launched: CI has no Microsoft account and must not download Minecraft without one.
- The owner's sign-in in Prism's wizard (device code or browser through `xdg-open` and Chrome), Prism's re-login
  dialogs, and how long the first Minecraft download takes.
- The mod's `world_ready` and heartbeats reaching the supervisor through the real helper in a real session (both
  sides are tested separately; the VM has no game).
- NVIDIA PRIME offload actually rendering Minecraft on the RTX 4060 (check F3 or the game log's renderer line);
  whether GLFW picks Xwayland or Wayland; the borderless maximized window rule; pointer capture and
  Super+Ctrl+Escape while the game has focus.
- Memory: the 3 GiB heap and the 5 GiB soft target under real use (B5 asks for measurement).
- Restart behaviour with a real crash, and the 30-minute reset with real heartbeats.

## JUDGMENT-CALL

Owner-facing ones first (1 to 6); 7 to 14 are technical.

1. **First start: he creates the hub with the mod's AresOS button, as on Windows.** (Owner-facing.)
   - Chosen: on first start Minecraft opens on its title screen (no `--world`) and the SETUP terminal tells him to
     click AresOS and Create. The mod's existing create screen offers seed 49 with the placeholder hub, the quick
     picks 50 and 26, or his own seed. No mod code changed.
   - Rejected: the mod creating AresHub by itself with seed 49 (STATE.md: he explores seeds and nothing is locked
     until he says so; it would pick for him), or the mod opening its create screen automatically on AresOS (a mod
     change with its own client test, for one click less).
   - Cost of changing later: a small mod change (open `HomeCreateScreen` when the session asks) plus a client test.
2. **No terminal at login.** (Owner-facing.) The session used to open foot at login; now the supervisor opens a
   terminal only when there is something to read or do (first start, sign-in, recovery). In the hub, the Terminal
   app and Super+Ctrl+Escape give a terminal. Rejected: keeping the login terminal behind the hub (one more window
   to Alt+Tab past, and it would sit in front until Minecraft is up). Reversal: one autostart line.
3. **Quitting Minecraft yourself does not restart it.** (Owner-facing.) Exit code 0 is his own Quit: a terminal
   says "Minecraft was closed" and `retry` opens the hub again; nothing is counted as a failure. Rejected:
   restarting it at once (the hub would come back every time he tries to leave it, and before package 25 there is
   no shut-down button in the hub). Reversal: a few lines in `finish_jvm`.
4. **A slow start never kills the game.** (Owner-facing.) If the hub is not ready 120 s after the JVM started
   (B2's prepared-start timeout), a recovery terminal says so, but Minecraft keeps running, and the terminal closes
   by itself if the hub appears. Rejected: killing and restarting it (a world being generated or loaded must not
   be killed; B2 forbids destructive automatic repair). The first start (SETUP) has no timeout: download, sign-in
   and world creation take as long as they take.
5. **Without the NVIDIA driver the hub still starts, on the default GPU.** (Owner-facing in a failure.) The
   offload variables are set only when `/proc/driver/nvidia/gpus` lists a GPU; otherwise the game runs on Intel and
   the log says so. Rejected: refusing to start (no hub at all after a driver problem; recovery would be harder,
   not easier). OS-BASE's "Intel-only Minecraft does not pass" is a qualification rule for the P3 trial, which
   should check the renderer.
6. **The desktop instance is strictly managed.** (Owner-facing if he tinkers in Prism.) Its mods, libraries and
   loader patch are read-only links into the image, so no extra mod can be added to the hub (the gameplay instance,
   P5, is for his mods), and AresOS updates change them with the image. A changed wrapper command, Java path,
   Minecraft or Fabric version or link stops into recovery with the exact difference; `aresos-desktop
   reset-instance` moves the instance aside (dated, nothing deleted) and the next start makes a fresh one with the
   same world. Rejected: copying the jars into the instance (stale after an update, and "never overwrite" would
   then mean recovery after every update) or repairing drift automatically (the brief: never overwrite).
7. **Prism comes from its official Linux bundle, without its updater.** Prism is not in Fedora; the only Fedora
   route is a COPR side repository, which the brief rules out. Of the official Linux downloads I took the extracted
   "Qt6 Portable" bundle (the AppImage needs FUSE or extraction, and portable mode would keep his data next to the
   binary). Removing `portable.txt` and `bin/prismlauncher_updater` is exactly how Prism decides (its source,
   `Application.cpp`): updates off and data in `~/.local/share/PrismLauncher`; its own startup log confirms both.
   It brings its own Qt 6.10 and libraries (about 200 MB under `/usr/lib/prismlauncher`). No desktop entry or MIME
   registration (the bundle's would claim every `.zip`).
8. **Java is the headless JRE** (`java-25-openjdk-headless`): Minecraft and Prism's launcher part need no AWT, and
   it adds three small packages instead of the full JRE's GUI stack. Changing it later: one package in the lock.
9. **Fabric Loader stays 0.19.5** although 0.20.1 (2026-10-19) exists: the mod builds and its client tests run on
   0.19.5. Moving the image to 0.20.x belongs with a mod change that also moves `gradle.properties`. Fabric API
   0.161.0+26.2 is already the newest for 26.2.
10. **Kills and unknown exits.** A JVM killed by SIGKILL (the kernel's OOM killer, or a forced kill) latches
    recovery without counting as a crash (B5: no automatic restart under pressure). An exit nobody reported (the
    wrapper was killed too, as with Prism's Kill button or systemd-oomd stopping the whole scope) counts as a crash:
    the safe side for a crash loop.
11. **One nonce per launch, one instance ID per session.** Every game launch gets a fresh `ARESOS_LAUNCH_NONCE`, so
    the helper is restarted with it before each launch (the game is not running then; the helper reconciles its app
    journal on restart, package 24). The instance ID stays for the session so the helper keeps its journal.
12. **The latch survives reboots, not only supervisor restarts.** It lives in `~/.local/state/aresos`. B2 says
    "survives restarts"; a crash loop that a reboot silently cleared would come back at every boot.
13. **The supervisor's keeper** restarts a failed supervisor up to 5 times in 10 minutes, then shows a terminal. The
    game survives a supervisor restart; the new supervisor adopts it by PID and start time.
14. **The mod jar pin is the CI container's build.** `build-mod.sh` builds in `eclipse-temurin:25.0.5_8` pinned by
    digest. A jar built on the laptop (Temurin 25.0.4) has other bytes (`a86c2cf3…`), so only the container build
    matches the pin; any change to `mod/` needs the pin renewed (`check_build=resolve` prints it).

## PLAN-GAP

1. **Every later image build must build the mod jar first.** The image now needs `os/minecraft/aresos.jar`;
   `check_build` runs `os/ci/build-mod.sh`, but the release job in `.github/workflows/os-image.yml` (bound by the
   package 16 walk, untouched here) and package 27's release path do not. Without the jar, `build.sh` stops with
   "run os/ci/build-mod.sh before building the image". The release package that includes 23 adds that one step
   before its `podman build`.
2. **Pins expire.** Fedora `updates` drops superseded builds: `java-25-openjdk-headless` (25.0.5 already waits in
   updates-testing) and especially `tzdata-java` (time-zone updates) will vanish, as `xdg-desktop-portal-wlr` did
   for package 21. Renew with `check_build=resolve` and record it. Prism's, Fabric's and Modrinth's files are
   versioned and stay.
3. **Minecraft or Fabric upgrades need a migration.** An existing instance keeps `net.minecraft 26.2` in its
   `mmc-pack.json` (Prism's file; provisioning never rewrites it). An image that pins 26.3 stops into recovery
   ("Minecraft is 26.2, this AresOS pins 26.3") until `reset-instance`. The package that moves the mod to 26.3
   should add a reviewed migration, or accept that one reset.
4. **Readiness depends on the app helper.** If the helper is down for good (five failures in a minute), the hub can
   still run but the supervisor never hears `world_ready`, so the 120 s window appears. That matches B2 (readiness
   needs the mod's report), but the message cannot tell the two causes apart.
5. **Main's hosted regression job fails since package 22 (not caused here).** `checks_only` on main `6978dc3c`
   (run 42815704308): `Ran 853 tests`, `FAILED (failures=7, errors=111, skipped=27)`, all in `test_owner_update`
   (for example `owner.Stop: Wrong or ambiguous target disk serial` where a test expects its own refusal). This
   branch gives exactly the same 118 failures and adds 74 passing tests (run 42809903934, `Ran 927 tests`). The
   same suite passes in WSL, where package 22 ran it; it was never run on the hosted runner. Package 22's area.
6. **Not in this package:** B2's APP_FOCUSED, STOPPING and DESKTOP_STOPPED_FOR_GAME (guardian 25, gameplay P5), a
   clean save at shutdown or logout (25: until then the session's end stops the game without a save request), and
   backups (26).

## Open questions

- None blocking. The owner-facing judgment calls (1 to 6) go to the owner before merge; the main one is whether the
  first start should create the hub by itself with seed 49 instead of waiting for his click on AresOS (1).
