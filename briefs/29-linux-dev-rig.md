# 29: Build and test the mod on the AresOS laptop

Empire board brief 276. Dev tooling for `mod/`; no change to what the mod does.

**Builder:** a Claude agent (Opus 5.5). **Review:** a fresh reviewer that isn't the builder.

## Why

Until now the mod was built and tested on Windows. The laptop now runs AresOS, and the hub work (the flat home world, the logo plaza, chat commands) is built here. Three things are missing:

1. There is no JDK on AresOS, so Gradle can't run.
2. The client game tests open a real Minecraft window. On the owner's screen that steals his focus, and two runs at once break each other.
3. In the development client on Linux no app can open, because the mod only talks to the OS app helper, and nothing starts that helper for a development client. (Package 23's supervisor will do it at login; it isn't on the laptop yet.)

**Goal:** any session on this laptop can run `mod/dev/build.sh` and `mod/dev/client-test.sh` and get the same answers as on Windows, with no window on the owner's screen. The owner can run `mod/dev/run-hub.sh` in a terminal and get the development client in which walking into a logo really opens the app and closing it returns to the game.

## Build

### 1. Java 25, in the home folder only

- Eclipse Temurin JDK 25 (the newest 25 GA build for Linux x64) from Adoptium's official download, checked against the SHA-256 Adoptium publishes for exactly that file, unpacked under `~/.local/opt/` (e.g. `~/.local/opt/jdk-25.0.x+y`), with a stable link `~/.local/opt/jdk-25`.
- Nothing system-wide: no sudo, no rpm-ostree, no Flatpak, no Homebrew, no change to `~/.bashrc` or PATH. The scripts find the JDK themselves.
- This is outside the repo. Write the exact version, URL and checksum into the report and `mod/README.md`.

### 2. `mod/dev/env.sh` (sourced by the other scripts)

- Sets `JAVA_HOME` from the environment if already set, otherwise `~/.local/opt/jdk-25`; stops with one clear sentence if neither has a Java 25.
- Holds the shared checks (below) so the scripts don't copy them.

### 3. `mod/dev/build.sh`

- Runs `./gradlew build` (unit tests and server game tests), passing extra arguments through.

### 4. `mod/dev/client-test.sh`

Runs `./gradlew runClientGameTest` (extra arguments pass through) so that nothing appears on the owner's screen:

- inside its own headless Wayland compositor (the image has `cage` and `labwc`, both wlroots; `WLR_BACKENDS=headless`), with its own `WAYLAND_DISPLAY`. The game must not be able to reach the owner's real display: unset or override `DISPLAY` and the real `WAYLAND_DISPLAY` for the Gradle process. If Minecraft's GLFW needs X11, use the headless compositor's own Xwayland, never the session's.
- Prefer real GPU rendering (try the RTX 4060 with the offload variables `__NV_PRIME_RENDER_OFFLOAD=1` and `__GLX_VENDOR_LIBRARY_NAME=nvidia`, then Intel); fall back to software rendering only if neither works, and say in the report which one runs and how fast a full test run is.
- Only one run at a time on the laptop: take `flock` on `~/.cache/aresos-dev/client-test.lock` for the whole run (wait for it; print that it is waiting).
- Refuse to start (exit code and one sentence, `--force` overrides) when less than 6 GB of memory is available, or while the owner's Minecraft runs. His game is Lunar Client: a Java process whose executable lives under `~/.lunarclient/` (check `/proc/<pid>/exe`; `pgrep -f` from a Claude shell matches the shell itself). Only read `/proc`; never touch `~/.lunarclient` or `~/.minecraft`.
- On exit, in every case (success, failure, Ctrl+C): stop the compositor it started, and stop the Gradle daemon.
- The tests rewrite tracked screenshots under `reviews/`. Leave that as it is, and print the reminder `git checkout -- ../reviews/` at the end. Add `--keep-screenshots <dir>` that copies what the run wrote there first, so a builder can look at them.
- No input injection into the real session (no `ydotool`, no `wtype`).

Then make the whole client test suite pass here:

- Run it and read every failure. A failure is one of three things: (a) a test that assumes Windows or the owner's screen where the mod's behaviour is not Windows-only: fix the assumption in the test or its harness, without weakening what it proves; (b) a test of a Windows-only path (PowerShell discovery, Windows launch identity): let it skip on other systems with a stated reason, and list each such test in the report; (c) a real defect of the mod on Linux: do **not** fix it here unless it is a one-line change with an obvious cause; record it as a finding with the evidence.
- AGENTS.md rule 5 holds: never weaken, skip or delete a test to get green. (b) is the only allowed skip, and only by operating system.
- The Windows behaviour of the mod and of its tests must not change.

### 5. `mod/dev/run-hub.sh`

For the owner, on his real screen, from a terminal:

- Starts the installed app helper `/usr/libexec/aresos-shell` the way the session supervisor will, then the development client (`./gradlew runClient`) with the matching environment, so apps open and focus returns. Read how the mod expects socket, launch nonce and desktop instance ID (`mod/src/main/java/dev/aresos/shell/ShellClient.java`, `fromEnvironment`) and how the helper takes them (`os/config/usr/libexec/aresos-shell`, its header and argument parsing). Package 23's supervisor is the reference for the contract: read it with `git show origin/pkg/23-minecraft-starts:<path>` only. Do not copy it and do not touch that branch or its worktree.
- Minecraft renders on the RTX 4060 (the two offload variables above); everything else keeps the session's environment.
- When the game exits, the helper it started stops too. A helper that was already running is left alone and reused only if it is this script's own; otherwise stop with a sentence.
- It changes nothing outside `mod/run/`, `~/.cache/aresos-dev/` and `$XDG_RUNTIME_DIR/aresos/`.
- It is a development aid. Say so in its header, and that package 23 replaces it on the installed system.

### 6. Docs

- `mod/README.md`: a short "On Linux (AresOS)" section: the JDK, the three scripts, the lock, what the headless run renders with.
- Do **not** edit `CLAUDE.md`, `STATE.md`, `HANDOFF.md` or anything under `os/`. The orchestrator updates CLAUDE.md's client-test rule after the review.

## Acceptance

- `mod/dev/build.sh` passes.
- `mod/dev/client-test.sh` passes **twice in a row**, with no window on the owner's screen. Proof of the last point: a `grim` screenshot of the real display taken during the run (it shows no Minecraft window), kept outside the repo and described in the report, not committed (it shows his screen).
- The screenshots the tests wrote show real rendered frames, not black: look at three of them yourself and name them.
- `mod/dev/run-hub.sh` was started once far enough to see the helper accept the mod's `hello` in the game log, then closed. Only do this when the Lunar game isn't running, and say in the report that a window appeared on his screen for that long. If that can't be done without disturbing him, record it as not verified.
- `reviews/29-linux-dev-rig/REPORT.md` in the AGENTS.md format, including: the Java version and checksum, which GPU renders, the run times, every test changed or skipped by operating system and why, every Linux finding.

## Already decided

- Scripts are plain bash with `set -euo pipefail`, absolute paths for system tools, no new dependencies.
- The lock path and the 6 GB rule are fixed: other sessions on the laptop use them too.
- Mod sources may change only where a test-environment assumption forces it (4a) or for a one-line Linux defect (4c).

## If unsure

Take the option that can't disturb the owner's screen, his game or his files, and record it. If the headless route can't work at all on this laptop, stop and report what you tried; do not fall back to running the tests on his screen.

## Rules

- `AGENTS.md` applies. You work in the worktree `~/AresOS-29-linux-dev-rig` on branch `pkg/29-linux-dev-rig`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- The repo is public: no personal data, no screenshots of his screen, no Mojang assets.
- Other sessions work on this laptop at the same time (16 GB of memory). Keep one Gradle daemon, stop it when you are done, and never run two heavy steps at once.
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
