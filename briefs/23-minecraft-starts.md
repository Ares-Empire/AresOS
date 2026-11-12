# 23: Minecraft starts in AresOS

Empire board brief 264. Part of P2, "Minecraft milestone" (`docs/design/OS-BASE.md` Appendix E). Image package; it starts after package 21 has merged and builds on it.

**Builder:** a Claude agent (Opus 5.5), owner request of 2026-11-09. **Review:** Codex gpt-6-astra (high), a fresh context.

## Why

AresOS boots into labwc with a terminal. The point of AresOS is that it boots into the owner's Nether hub in Minecraft. The design is `docs/design/OS-BASE.md`:

- section 5 ("Starting the desktop and playing Minecraft");
- Appendix B2 ("Supervision and focus");
- B5 ("Memory, GPU and restart pressure");
- the GPU rows in section 2.

Read them fully. Package 24 (interface v1: the helper that opens apps from the hub) is built in parallel. This package starts the desktop and passes the helper what it needs.

## Build

1. **Prism and Java, in the image:**
   - Native Prism Launcher and **Java 25**, both pinned exactly.
   - Use Fedora packages through the existing lock if they exist there. Otherwise use Prism's official Linux release, pinned by sha256 and installed under `/usr`.
   - Same discipline as package 21's Chrome: no side repos or updaters left active.
   - Prism's UI stays available for setup and re-login.
2. **The managed `AresDesktop` instance:**
   - Created in `ares`'s home at first desktop start from **image-shipped, hash-pinned inputs**: Fabric Loader, Fabric API, and the AresOS mod jar built from this repo's `mod/` in CI and pinned into the image.
   - Use the versions in `AGENTS.md` unless newer ones are checked and pinned. No Sodium or Iris yet (they come after qualification).
   - Minecraft itself is downloaded by Prism after the owner signs in. Never redistribute it, never ship Mojang assets, never edit account files or bypass authentication.
   - Provisioning is idempotent and **never overwrites** an existing instance or world. A pin mismatch stops into recovery.
   - Heap and working set follow B5: desktop heap 3 GiB to start.
3. **The world:**
   - The marked `AresHub` desktop save lives under `~/.local/share/aresos/worlds/` and is linked into the desktop instance only (section 5).
   - Create it on first start with the mod's **existing** desktop-world and Nether-home code (packages 04/04c: `DesktopWorld`, `NetherHome`, `HomeSites`). Read how Windows creates and marks it today, and reuse that.
   - A missing or corrupt world, or a failed sign-in, opens recovery, never a replacement world.
4. **The session:**
   - labwc's autostart starts an AresOS desktop **supervisor** instead of only foot.
   - States, as B2 names them: SETUP (first run, with Prism's UI for the owner's own Microsoft sign-in), STARTING, IN_WORLD, AUTH_REQUIRED, RECOVERY.
   - Launch with `prismlauncher --launch AresDesktop --world AresHub` (or Prism's exact current flags).
   - Track the real Java process, not Prism's PID.
   - Restart policy exactly as B2: stop after three failures in five minutes or three consecutive failures; a latched recovery that survives restarts; reset only after 30 healthy minutes or an explicit Retry.
   - RECOVERY shows a foot terminal with a clear message.
   - Super+Ctrl+Escape (recovery terminal) keeps working at all times.
5. **The GPU:** NVIDIA renders Minecraft (PRIME render offload environment) while Intel drives the session, as section 2 proposes. OpenGL, no shaders. Record the environment you set and why.
6. **Package 24's helper:** if `/usr/libexec/aresos-shell` exists, start it with the session and pass the launch nonce and desktop instance ID to both it and the game, as B1 requires. If package 24 hasn't merged yet, define that contract in one place, so 24 plugs in without changing this package's states.

## Verification

- **Unit tests** (`os/tests`):
  - the supervisor's states and restart policy, including persistence across restart, the latch and the reset;
  - provisioning: idempotent, never overwrites, refuses pin mismatches;
  - the launch command and environment.
- **CI:**
  - Build the mod jar in CI and check its pinned hash.
  - Build the image with package 21's throwaway CI path. Never push, sign or publish.
  - In the built image, check: Prism and Java 25 present and pinned, the provisioning inputs' hashes, the autostart, and that nothing runs as root.
- **Mod:** if you change the mod, the full `.\gradlew.bat build runClientGameTest` passes **twice**. Only one Minecraft client-test run at a time on the laptop, and only with at least 6 GB of free RAM. Stop Gradle daemons at the end.
- **WSL:** run the full `os/tests` suite from a clone of your pushed branch, plain and with `-B`, at most one full suite at a time. Known WSL-only failures, also on main: `test_greeter` 3, `test_inherited_homebrew` 6, `test_sysusers` 1.
- **Bound sources:** exact hashes in `os/manifest/ci/16/pending-rebind.json` for any bound file you change (`checkout_sources.records`).
- **Not verified here:** the real boot into the hub on the laptop (the P3 trial, after release with the owner's OK). Say so.

## Out of scope

- Opening apps from the hub (package 24).
- The guardian, clean save and shutdown (25).
- Backups (26).
- The gameplay `minecraft` app (P5).
- Shaders, the boot splash, sleep.
- Owner tools (22).
- Publishing.

## Rules

- `AGENTS.md` applies. Push `pkg/23-minecraft-starts` and open a PR. Never merge, never push to `main`. Never `--no-verify`.
- The repo is public: no personal data, no Mojang assets.
- Don't touch the owner's real `.minecraft` or Lunar Client. No admin, no disks. Don't touch other worktrees.
- Commits end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Write `reviews/23-minecraft-starts/REPORT.md` in the AGENTS.md format, with JUDGMENT-CALLs marked.
