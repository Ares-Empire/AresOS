**Member 1 — System.** Build a small host service shared by a CLI and an MCP interface. Keep mail, browser control and desktop window management separate.

**Checked** below means source inspection, not runtime verification. **Assumed/proposed** identifies scenarios, recommendations and future tests. I reviewed `46900744c9b8da1de86b00f42927e17e41da09b1`; no files were edited and no runtime tests were run.

1. **Blocking before live writes: CLI and MCP must share one action authority and operation history.**

   **Checked:** The council requires confirmation for sending/deleting. MCP’s stdio transport launches a server subprocess; it does not provide shared application state across separate clients. SMTP also has an acknowledged failure case where the server accepts a message but the client times out before receiving success. [MCP transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [RFC 5321 §4.5.3.2.6](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.6).

   **Assumed scenario → impact:** Claude sends mail through MCP, loses the response, then retries through the CLI. Separate implementations can send twice or apply different approval rules.

   **Proposed fix:** Both frontends call one service. It owns adapter connections, operation IDs, approval state and a small persistent operation journal. A timed-out external write can return `outcome_unknown`; restarting the service must not replay it automatically. Confirmation belongs below both frontends. Keep live writes disabled until the Security member’s enforcement design is implemented: a same-user socket alone does not prevent Claude’s shell from bypassing the service.

   **Proposed check:** Submit the same operation through both interfaces, interrupt the connection after the test mail server accepts it, then restart everything. Assert one submission, consistent status and no automatic resend. Test denial through both interfaces.

2. **Blocking for desktop integration: the current session and the user service manager cannot be assumed to share a D-Bus environment.**

   **Checked:** [`aresos-session`](../../../os/config/usr/bin/aresos-session:7) starts labwc inside `dbus-run-session`, which creates a new bus. The existing [user-service audit](../../../os/tests/audit.py:59) instead addresses `/run/user/1001/bus`. The labwc autostart currently launches only the terminal. AT-SPI has a separate accessibility bus discovered through `org.a11y.Bus` on the session bus. [D-Bus documentation](https://dbus.freedesktop.org/doc/dbus-run-session.1.html), [AT-SPI architecture](https://raw.githubusercontent.com/GNOME/at-spi2-core/main/bus/README.md).

   **Assumed scenario → impact:** An MCP server started from a graphical terminal sees an app; the same adapter started as a user service sees another bus or stale display environment and reports no apps. A container test passes while the installed session fails.

   **Proposed fix:** Run the service as daily user `ares`, on the host, attached explicitly to the graphical session. Establish one session-bus arrangement for apps, the service and service activation; prefer the existing PAM/systemd user bus when qualified. Start an explicit AresOS session target after the compositor establishes its environment, and stop it when that session ends. Do not assume merely installing a user unit starts it correctly.

   Current labwc documents automatic activation-environment updates, so the gap is not simply “missing environment export”; the exact pinned build and bus arrangement need verification. [labwc session management](https://labwc.github.io/labwc.1.html#session-management).

   **Proposed check:** In the VM, compare bus identities from the terminal, service and test app; discover AT-SPI separately; read and change a synthetic widget. Repeat after compositor restart. A dead session must invalidate desktop handles rather than reconnect silently to a different session.

3. **Blocking for a Flatpak-based rollout: the image deliberately prevents today’s daily user from running Flatpak.**

   **Checked:** [`os/build.sh`](../../../os/build.sh:93) makes `flatpak` inaccessible to `ares`; [user policy](../../../os/policy/masked-user-units.txt:13) masks Flatpak helpers, and [`guest.sh`](../../../os/tests/guest.sh:24) asserts that restriction. Flatpak also filters session D-Bus access and restricts host filesystem visibility. [Flatpak permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html).

   **Assumed scenario → impact:** A brief installs Chrome as a Flatpak and expects `flatpak run` plus a host extension bridge to work. Launch fails before automation starts; enabling broad sandbox access to fix it would introduce an unreviewed policy change.

   **Proposed fix:** Keep the control service and adapters native on the host. For development, use a pinned bundle in disposable containers/VMs. For deployment, put managed code, dependencies and user-service definitions in the image; keep account configuration, credentials and private state per user. This follows the maintenance contract in [OS-BASE §9/A1](../../../docs/design/OS-BASE.md:150), rather than installing changing dependencies at every MCP startup.

   Treat Flatpak application launching as a separate integration change that preserves the prohibition on unmanaged updates. Qualify the exact browser package and bridge permissions; do not grant unrestricted session-bus or host access as a shortcut. Mail through its service API needs no mail-client sandbox access.

   **Proposed check:** Run the chosen package as `ares` in the image VM, including browser attachment and a synthetic attachment/file operation. Re-run updater-denial checks. Also prove that rolling back code does not leave incompatible per-user state.

4. **Should fix before writing acceptance criteria: the existing CI job is not a general control-layer VM test.**

   **Checked:** [`vm.py`](../../../os/ci/vm.py:105) checks session, policy, recovery and power behavior. It does not exercise mail, Chrome or accessibility. The image job is [restricted to `pkg/13-keyboard-layout` and `release_13`](../../../.github/workflows/os-image.yml:115), builds the keyboard release, and subsequently publishes it. Linux catalogue and launch support remain [explicit stubs](../../../mod/src/client/java/dev/aresos/client/launch/LinuxAppLauncher.java:8).

   **Assumed scenario → impact:** A new branch gets passing container tests and existing boot checks, then reports “tested in AresOS.” Neither the installed service nor the owner’s browser path has actually run.

   **Proposed fix:** Add a dedicated container workflow and a separate, explicitly nonpublishing VM integration mode. Reuse the VM harness, but launch test clients as `ares` in the actual graphical session. Preserve the existing recovery/power checks. Report container, image-VM and hardware evidence separately.

   **Proposed dependency split:**

   | Test or action | Registry dependency |
   |---|---|
   | Contract tests, container mail server, browser against local fixture pages | Neither missing setting |
   | VM using the existing private release | Working package read authorization; use the restored token where required, or verified repository `GITHUB_TOKEN` access |
   | Existing historical-image comparison/release path | `GHCR_READ_TOKEN` as currently wired |
   | Publishing a new image | Restored package write access and owner authorization |

   **Checked qualification:** [HANDOFF](../../../HANDOFF.md:5) reports the missing settings; I did not independently query their current GitHub state. Existing workflows also contain job-token read paths, so the named secret is not intrinsically required for every possible VM job.

   **Proposed check:** Run the new VM suite twice from fresh overlays, with publication disabled and without write permission. No successful container run substitutes for this gate.

5. **Should fix in the adapter contract: “inspect and fill” is not a sufficient common model for mail and browsers.**

   **Checked:** The provider/protocol is explicitly unknown. IMAP distinguishes fetching a body from `BODY.PEEK`, which avoids implicitly setting `\Seen`. Existing browser tools use page/snapshot-specific element references. [IMAP specification](https://datatracker.ietf.org/doc/html/rfc9051#section-6.4.5), [Playwright snapshots](https://github.com/microsoft/playwright.dev/blob/main/mcp/snapshots.mdx).

   **Assumed scenario → impact:** An inbox summary marks messages read; a delayed form action targets a page that has navigated; or a successful local IMAP test is presented as support for a provider that requires a different API.

   **Proposed fix:** Share the operation envelope, not a universal screen model. Each adapter exposes capabilities and typed domain operations. Include target identity, revision/session identity, effect classification, deadline and explicit outcomes such as `unsupported`, `stale_target`, `auth_required` and `outcome_unknown`. Mail identities must include account/mailbox identity and protocol validity information; browser handles must be bound to the selected profile, tab and document.

   Keep mail authentication/provider code replaceable. An IMAP/SMTP implementation can be a useful laboratory adapter before the owner answers, but cannot establish real-account compatibility.

   **Proposed check:** Assert unchanged mailbox flags after reads; invalidate handles after mailbox recreation or browser navigation; test missing credentials and unsupported capabilities. Validate effects at the test server, not just command exit codes.

6. **Should fix scope: existing browser control and compositor-dependent desktop features are different projects.**

   **Checked:** Claude Code already documents Chrome integration, including Linux native-messaging configuration, but requires Anthropic sign-in. Playwright MCP provides structured snapshots and an extension route to existing tabs. Chrome DevTools MCP documents attachment to running Chrome. Existing mail and AT-SPI MCP implementations also exist; their existence does not establish AresOS compatibility. [Claude Chrome integration](https://code.claude.com/docs/en/chrome), [Playwright browser connections](https://playwright.dev/mcp/configuration/browser-extension), [Chrome DevTools configuration](https://developer.chrome.com/docs/devtools/agents/get-started/configuration), [email-mcp](https://github.com/codefuturist/email-mcp), [linux-desktop-mcp](https://github.com/lotnikov/linux-desktop-mcp).

   **Assumed scenario → impact:** A new browser engine duplicates upstream work, while tests operate a separate empty browser instead of the tab the owner requested. Alternatively, mail work waits unnecessarily for the companion’s window-positioning design.

   **Proposed fix:** Wrap a pinned existing browser implementation—Playwright is my initial candidate—and qualify the narrow operations needed. Distinguish “launch a controlled test browser” from “attach to the owner-selected existing browser.” Do not expose the upstream server’s entire tool catalogue automatically. Claude in Chrome is an existing user-facing option to assess, not an account-free CI dependency.

   **Checked compositor distinction:** labwc exposes window enumeration and some management through foreign-toplevel integration; KWin exposes geometry through its scripting API. Neither supplies mail or browser DOM semantics. [labwc integration](https://labwc.github.io/integration.html), [KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/).

   **Proposed check:** Demonstrate that the adapter acts on the selected synthetic tab while leaving another tab untouched. Run API/browser contract tests without compositor geometry support. Defer KWin integration: current image policy masks Plasma units and explicitly rejects a running KWin, so switching requires a coordinated session/policy change.

**General case:** **Assumed conclusion:** this is a common integration problem where a working automation library is mistaken for a qualified desktop service with correct identity, lifecycle and installation behavior.

**Smallest useful version — proposed, each testable without the laptop:**

1. **Shared service, CLI and MCP contract.** New `control/` area plus container CI. One session-owned host service, a private runtime socket, a scriptable CLI with JSON output, and a thin stdio MCP bridge using the same operations. Include capability/health reporting and a synthetic adapter. Test concurrency, disconnects, stale handles, restart and identical denials. Keep it independent of Minecraft and the power/save supervisor.

2. **Mail reading and draft preparation.** Adopt suitable existing protocol code after inspection. Exercise search, read and attachments against a container mail server, with synthetic addresses and messages. Prepare drafts without delivering them; test write mechanics only against the fixture server behind the common authorization interface. Provider-specific authentication waits for the owner’s answer. No production credentials or captured traffic enter CI.

3. **Browser adapter and AresOS session qualification.** Wrap the selected upstream browser engine; test local fixture pages, tab identity, navigation and restart in containers. Add the nonpublishing VM mode and actual session service wiring. This is the first coordinated touch to `os/config/`, `os/ci/`, package/manifest inputs and the OS workflow; image builds require owner authorization. Registry access can block the VM gate without blocking container development. `mod/` and install instructions need no changes for these briefs.

**Assumed installation choice:** release-managed executable/runtime in the image, per-user configuration and private state, bounded service restart, lazy adapter startup, and no dependency on Claude or Minecraft staying alive. The MCP bridge may restart without restarting the service.

**Assumed portability choice:** leave macOS possible through separate lifecycle, credential-store, accessibility and window-management backends. Keep Linux D-Bus objects out of the common contract. Build no macOS implementation now.

**Waits for the first boot — proposed:**

- Actual browser packaging, extension connection and manually configured account authentication on the owner’s installation.
- NVIDIA/Wayland behavior, display scaling, focus and resource use alongside Minecraft.
- Companion positioning, rooms and compositor selection based on actual use.
- The owner’s confirmation experience. Container tests can prove protocol behavior, but cannot establish whether prompts are understandable or tolerable.

**Questions only the owner can answer:**

- Which mail provider, supported protocol and authentication method must work? This determines the production mail adapter.
- Must Chrome control the existing daily profile immediately, or is a separate automation profile useful initially?
- Which apps come after mail and Chrome? This determines whether AT-SPI or compositor work deserves priority.
- Which confirmation channel should authorize sends/deletes? Real writes remain disabled until its enforcement is qualified.
- When may the image/session integration be built and qualified alongside the ongoing install work?

BUILD