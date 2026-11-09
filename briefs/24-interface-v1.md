# 24: Interface v1: apps open from the hub on AresOS

Empire board brief 265. Part of P2, "Minecraft milestone" (`docs/design/OS-BASE.md` Appendix E). Mod package plus a new OS helper.

**Builder:** a Claude agent (Opus 5.5), owner request of 2026-11-09. **Review:** Codex gpt-6-astra (high), a fresh context.

## Why

On Windows the mod opens apps directly. On AresOS (Linux) the mod must ask an OS helper instead. The design is `docs/design/OS-BASE.md` Appendix B1 ("Mod and OS interface v1") and B2 ("Supervision and focus"): read both fully.

Today `LinuxAppCatalogue` returns an empty list and names the protocol `aresos-shell/1.0`. This package makes apps open from the hub on AresOS:

1. walking into an app's logo (or using its item) opens the app;
2. closing the app returns to the hub.

The mod's behaviour on Windows stays exactly as it is.

Package 23 (Minecraft starting in AresOS at login, built after package 21 merges) will start the helper and the desktop together. This package delivers the helper, its app registry and the mod side, testable on its own.

## Build

### A. The OS helper (`aresos-shell/1.0`)

1. **Transport:**
   - A user-level helper for `ares`, speaking newline-delimited JSON on a private Unix socket under `$XDG_RUNTIME_DIR/aresos/`.
   - Same-user peer check; launch nonce and desktop instance ID, as in B1.
   - Message size limits; malformed input rejected without crashing.
   - Every envelope carries the protocol version and a request/event ID.
2. **Messages:**
   - Implement `hello`, `list_apps`, `open_app`, `app_state`/`shell_focus` and `world_ready`/`heartbeat` as B1 specifies.
   - Leave `request_power`, `prepare_stop` and `save_complete` (the guardian) to package 25. Reject them as unknown operations for now, as B1 says for anything unknown.
   - Duplicate `open_app` request IDs return the same result; an uncertain launch is never retried blindly.
3. **Registry:**
   - The helper's apps come from image-shipped, reviewed JSON entries: stable ID, display name, argv or desktop entry, working directory, single/multi-window identity. The mod never sends a command.
   - First entries:
     - `terminal` (foot);
     - `notepad`: a text editor already in the base image (name the one you pick);
     - `browser`: `google-chrome`, available only when the binary exists, which it will after package 21.
   - Unknown IDs are visible but unavailable.
4. **Launch and return:**
   - Start each app in its own user scope, outside the game's lifetime group, e.g. `systemd-run --user --scope`.
   - Track its lifecycle and report `app_state`.
   - Return focus to the hub only when the foreground app's last relevant window has closed. labwc implements the wlr foreign-toplevel protocol; use it if you can do so robustly, and otherwise ship the best safe approximation and record the gap as a PLAN-GAP.
   - A launch with no matching window shows a failure in the game; it never hangs.
5. **Where it lives:**
   - Put it under `os/config` (e.g. `/usr/libexec/aresos-shell` and `/usr/share/aresos/apps/`), in Python 3 with the standard library only, since the image has `python3`.
   - Package 21 is changing `os/build.sh`, the package lock and session files in parallel. Keep your changes there minimal, and expect to rebase on 21.

### B. The mod (Linux side)

1. A `LinuxAppCatalogue` client for `aresos-shell/1.0`, using Java 25's Unix-domain socket channels. No new dependencies.
2. Behaviour:
   - `hello` with capabilities;
   - `list_apps` fills the app items and doors;
   - `open_app` on a click or walk-in, one launch per deliberate action;
   - `shell_focus` releases or captures the pointer and clears held input;
   - `world_ready`/`heartbeat` once the desktop world is loaded and input is usable.
3. **No fallback:** if the helper is missing or incompatible, the Linux mod shows a clear in-game message and **never** falls back to executing a command (B1). An explicit developer-only direct adapter may exist for standalone Linux development, but it is never enabled by default.
4. **Windows:** the Windows path (`WindowsAppCatalogue`, its launch and focus return) stays unchanged. Keep platform code behind the one small interface (AGENTS.md code style).
5. **Config:** the B1 schema-2 migration of `config/aresos/apps.json` is **not** required here unless the Linux path can't work without it. If it can't, record that as a PLAN-GAP rather than half-migrating the config.

### C. Verification

- **Helper:** Python unit tests for the protocol, envelopes, malformed and oversized input, duplicate request IDs, the registry, unknown and unavailable apps, peer and nonce checks, and the launch-scope commands (mocked). Add them under `os/tests`.
- **Mod:**
  - Java unit tests with a fake helper: handshake, incompatible version, helper absent or restarting, list, open, focus transitions, one launch per click.
  - The full `.\gradlew.bat build runClientGameTest` passes **twice** (AGENTS.md), with the Windows behaviour unchanged.
  - Run Gradle and the Minecraft client tests only when the laptop has room: at least 6 GB of free RAM. Never run them while a full WSL `os/tests` suite runs (check with `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu --exec pgrep -f "unittest discover -s os/tests"`), because packages 21 and 22 are being tested in parallel. Only one Minecraft client-test run at a time on the laptop. Stop every Gradle daemon at the end.
- **WSL:** run the helper's tests and the full `os/tests` suite in WSL from a clone of your **pushed** branch, plain and with `-B`, at most one full suite at a time. Known WSL-only failures, also on main: `test_greeter` (3 errors), `test_inherited_homebrew` (1 failure + 5 errors), `test_sysusers` (1 error).
- **Bound sources:** if you change a file that the package 16 walk binds, add its exact new hash to `os/manifest/ci/16/pending-rebind.json` with `checkout_sources.records`, as `reviews/15f-lenovo-firmware-entry/REPORT.md` describes.
- **Not verified here:** the real AresOS run (helper, labwc, real apps) is a hardware trial after packages 21–23 are released. Say so in the report.

## Out of scope

- Starting Minecraft at login, Prism, Java and the instance: package 23.
- The guardian (save and stop, power): package 25.
- Backups: package 26.
- The gameplay `minecraft` app: P5.
- Image content: package 21.
- Owner tools: package 22.

## Rules

- `AGENTS.md` applies, including its Gradle, Minecraft-folder and asset rules. Push `pkg/24-interface-v1` and open a PR. Never merge, never push to `main`. Never `--no-verify`: the privacy pre-push hook must pass.
- The repo is public: no personal data.
- Don't run anything as admin, and don't touch other worktrees.
- Commits end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Write `reviews/24-interface-v1/REPORT.md` in the AGENTS.md format, with JUDGMENT-CALLs marked.
