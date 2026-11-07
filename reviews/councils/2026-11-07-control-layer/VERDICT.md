**BUILD.** Start a small assistant that reads selected browser pages and mail, prepares replies locally, and leaves sending and deletion to the owner, using existing automation engines. Real-account access follows provider, privacy and isolation checks; automated writes need a separately proven approval mechanism.

I read the question and all eight member reports against repository commit `4690074`, and checked disputed claims against source code and upstream documentation. This is a planning verdict: no runtime tests were run and no files were changed.

The first briefs should be built in this order:

1. **Selected-page reading, with one usable command.**

   **Goal:** From a terminal or Claude’s MCP connection, select a browser tab, extract its content, prepare text locally, inspect task status and stop further work.

   **Adopt versus build:** Adopt one pinned Playwright backend. Its existing extension supports selecting an already-open tab, and its Chromium launch code supports a private pipe connection. Build only the narrow AresOS operations, target tracking and shared CLI/MCP task service. Start with a separate disposable profile; test the extension handoff using synthetic profiles too. Do not expose the upstream server’s unrestricted tool catalogue. This choice follows the required “help with this tab” workflow, rather than a preference for one browser project. [Playwright extension](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md), [Chromium launch source](https://raw.githubusercontent.com/microsoft/playwright/main/packages/playwright-core/src/server/chromium/chromium.ts)

   **Tests without the laptop:** Standard Linux runner, local fixture website and a headed browser on a virtual display. Test two profiles, similarly named tabs, navigation, owner edits during a delay, disconnects and cancellation. Verify that reading causes no fixture mutation. Help and status must work without Claude or internet access. Deterministic tool calls provide the evidence; no paid model account is required.

   **Files and areas:** New `control/` code, fixtures, dependency locks, documentation and `.github/workflows/control.yml`, plus its brief and review report. No `os/`, `mod/` or install-guide changes.

   **Registry access:** Neither `GHCR_READ_TOKEN` nor package write access.

2. **Mail search and local replies, including the manual-send handoff.**

   **Goal:** Find relevant messages without changing their unread status, show their sources, and prepare a reply that the owner can finish in a mail client.

   **Adopt versus build:** Qualify Himalaya’s released JSON CLI as the initial mail engine; reuse its protocol and message parsing. Build the restricted adapter and local draft presentation. The inspected v2.2.1 source has no MCP command, so do not plan around an unreleased `himalaya mcp`. The owner’s provider answer determines whether the production adapter uses its API, JMAP or IMAP; the laboratory adapter does not settle that choice. [Released capabilities](https://github.com/pimalaya/himalaya/blob/v2.2.1/README.md), [Released commands](https://github.com/pimalaya/himalaya/blob/v2.2.1/src/cli.rs)

   **Tests without the laptop:** Use a pinned [GreenMail container](https://greenmail-mail-test.github.io/greenmail/) with synthetic accounts and external delivery blocked. Check pagination, Unicode, attachments, unchanged mailbox flags and correct message identities. Carry a prepared reply through a disposable mail client to a simulated owner send, checking recipients, attachments and reply ancestry. The test driver may simulate the owner; the assistant must remain unable to send.

   **Files and areas:** `control/` mail adapter, fixtures, handoff documentation and container workflow. No production OS or mod changes.

   **Registry access:** Neither missing setting.

3. **Enforced read-only access and private credentials.**

   **Goal:** Make the restrictions hold even when a hostile program calls the tools directly or an email persuades Claude to try another route.

   **Adopt versus build:** Adopt Linux isolation and established credential-storage facilities. Build the small policy service shared by CLI and MCP. Credentials and execution belong to a protected, unprivileged service identity; the companion gets only scoped operations. An `ares` session bridge handles graphical connections. Recovery/coding assistance remains a separate session with separate authority.

   Keep production send/delete operations unavailable. This brief should not become a phone-approval project or a general automation framework.

   **Tests without the laptop:** Run hostile clients with the companion’s exact container permissions. Attempt credential reads, direct SMTP, unrestricted browser control, policy modification, arbitrary network requests and access to desktop input services. Test locked storage, expired credentials, invalid TLS certificates, malicious attachments, redirects and secret canaries in diagnostics. Verify the browser sandbox explicitly.

   **Files and areas:** `control/` policy, process-launch configuration, credential integration, diagnostic export and security fixtures. No production `os/` changes yet.

   **Registry access:** Neither missing setting.

4. **Qualification inside the actual AresOS image.**

   **Goal:** Prove the same tools work in AresOS’s graphical session and recovery terminal, with the intended permissions and browser package.

   **Adopt versus build:** Reuse the existing VM harness and frozen signed release. Add a separately invoked, nonpublishing test path and disposable test overlay. Qualify a pinned native browser bundle first: the present image explicitly prevents `ares` from executing Flatpak. Managed binaries and dependencies should eventually ship through image maintenance; private account state stays outside Git. [Current executable restrictions](../../../os/build.sh:93)

   **Tests without the laptop:** Two complete passes from fresh VM overlays. Check graphical-session connection, browser sandbox and transport, synthetic mail, credential isolation, offline help, service/compositor restart and recovery access. Preserve existing power and updater checks. Test rollback with retained control-layer state.

   **Files and areas:** New control-layer VM workflow and overlay, `os/ci/`, and relevant `os/tests/` checks. Coordinate any production wiring under `os/config/`, `os/Containerfile`, `os/build.sh`, package locks and manifests with the installation work. No `mod/` or install-guide changes are needed for this qualification.

   **Registry access:** Working private-image **read** authorization is required. The named `GHCR_READ_TOKEN` is not universally required: existing package 13/14/16 paths use `GITHUB_TOKEN`, with package access granted separately. Their branch restrictions mean a new control-layer path still needs implementation. Package **write** access is unnecessary for nonpublishing qualification; publication requires restored write access and owner approval. Current access has not been independently verified. [Workflow](../../../.github/workflows/os-image.yml:395), [Authentication implementation](../../../os/ci/registry_auth.py:53)

All briefs go through branches, PRs and the local privacy check. Each merge requires the owner’s instruction; image rebuilds and publication retain their separate owner gate. Keep Linux session and credential details outside the common operation contract so a later macOS implementation remains possible, without building it now.

What waits for the first boot:

- **Actual hardware experience:** NVIDIA/Wayland behaviour, keyboard reachability, focus, display scaling, memory, heat and latency alongside Minecraft. Containers and VMs cannot establish these.
- **Owner onboarding:** Real credentials, authentication renewal, unlock behaviour and actual signed-in browser use. Provider information and synthetic authentication tests can happen earlier.
- **Whether the workflow saves effort:** Try finding mail, explaining a page and finishing a prepared reply. Count corrections and handoffs, then decide whether automated writes are worth maintaining.
- **Companion positioning, the wheel and rooms:** These depend on desktop behaviour and window geometry. Mail and browser content operations do not require choosing KWin. labwc already offers window enumeration and some management; KWin offers additional scripting facilities. [labwc integration](https://labwc.github.io/integration.html), [KWin API](https://develop.kde.org/docs/plasma/kwin/api/)
- **Hub-to-app choreography:** It also needs the unfinished Linux app helper; booting the laptop does not implement it. [Linux launcher](../../../mod/src/client/java/dev/aresos/client/launch/LinuxAppLauncher.java:8)

Automated sending and deletion wait for an independent approval channel and the write-specific checks below, **regardless of whether first boot has happened**. Generic accessibility control waits for a named useful application that lacks a suitable API.

Questions only the owner can answer:

| Question | Recommended default | What changes otherwise |
|---|---|---|
| Which mail provider, authentication method and mail client must work? | Keep development synthetic until identified; prefer the provider’s supported API and narrow permissions. Do not put addresses or credentials in the public answer. | Determines the production adapter, login flow and reply handoff. |
| Must assistance continue in existing signed-in tabs immediately? | Use a separate profile initially, while qualifying existing-tab handoff early with fixtures. | Existing-tab isolation and connection testing become prerequisites for the first live browser release. |
| Is read/prepare/manual-send useful initially? | Yes; review beside the work and send manually. | Automated writes require an additional approval brief before they can ship. A phone is one candidate, not a mandatory dependency. |
| Which content may reach Claude, and through which account/login mode? | Explicitly selected folders, messages and tabs; no background whole-inbox ingestion or automatic attachment processing. Use an existing approved account. | Broader access expands the privacy scope. Claude in Chrome is an optional trial only if its authentication requirements fit: its documentation requires interactive `/login`, not an API key or `setup-token`. [Authentication requirements](https://code.claude.com/docs/en/chrome) |
| Which two recurring tasks matter most, and which app follows mail and Chrome? | Start with “find mail needing attention and prepare a reply” and “explain this selected page.” | Reorder adapters around the named tasks; add accessibility work only for a demonstrated need. |
| When may integration affect the installation work? | Develop containers now; coordinate the VM overlay separately and defer production image changes until the installation work has a stable handoff. | Earlier integration needs an explicitly coordinated image change and its full regression checks. |

The merged gaps, ranked by severity, are:

1. **Critical before live access — Claude can bypass a tool’s restrictions through another route.**  
   **Scenario:** An injected email induces a shell command that sends mail directly, or browser automation clicks Send in webmail.  
   **Fix:** Separate the constrained companion from recovery/coding assistance; protect credentials, browser control and policy configuration outside its authority. Both CLI and MCP use one policy service. The repository already acknowledges that a same-user socket is not this security boundary.  
   **Check:** Hostile clients must fail to use direct SMTP, raw browser control, credential files, desktop input or writable policy. [Existing boundary statement](../../../docs/design/OS-BASE.md:249)

2. **Critical before automated writes — The agent can manufacture approval or change what was approved.**  
   **Scenario:** Claude supplies its own confirmation token, or an attachment changes after the owner approves it.  
   **Fix:** An independently authenticated owner action must approve the exact account, recipients including Bcc, content, attachment bytes or fixed deletion set. Approval expires, works once and becomes invalid after changes. Connection consent and a push-notification callback are insufficient.  
   **Check:** Reject forged approvals, altered content, expired requests, replay and concurrent execution. A trusted local interface is acceptable only if the agent cannot operate or impersonate it.

3. **High before automated writes — Retry, cancellation and restoration can cause duplicate or misreported actions.**  
   **Scenario:** SMTP accepts a message but its reply is lost; Claude retries through the CLI. Alternatively, restoring a backup revives an old approval.  
   **Fix:** Share durable operation history; report uncertain outcomes honestly and reconcile before resending. Restoration must invalidate previous approvals. Stop prevents subsequent actions but cannot undo an accepted send.  
   **Check:** Drop the final response, restart both interfaces, cancel after acceptance and restore a pre-send backup. Require no automatic second submission and truthful status. SMTP and MCP explicitly leave these ambiguity/cancellation cases possible. [SMTP](https://www.rfc-editor.org/rfc/rfc5321.html#section-6.1), [MCP cancellation](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)

4. **High — Apparently harmless operations can change or publish data.**  
   **Scenario:** Reading clears unread flags; filling a field triggers autosave; mailbox cleanup permanently removes unrelated messages.  
   **Fix:** Classify actual effects per adapter. Preserve mail flags, compose locally, and treat uploads, server drafts, typing, moves and deletion flags as mutations. Unknown effects remain unavailable; bulk expunge stays disabled.  
   **Check:** Compare fixture-server state before and after every allowed operation, including a page that transmits each keystroke. IMAP provides `BODY.PEEK` specifically to avoid implicitly marking messages read. [IMAP specification](https://www.rfc-editor.org/rfc/rfc9051.html#section-6.4.5)

5. **High — Private information can escape without a Send operation.**  
   **Scenario:** A malicious message asks Claude to open a URL containing another message’s contents; a diagnostic export publishes reset links or cookies.  
   **Fix:** Scope reads and the model destination beforehand; mediate outbound requests and redirects, protect local endpoints, isolate attachment processing and export only sanitised diagnostics. Treat retrieved instructions as untrusted content. Public CI uses synthetic data exclusively. Disable unnecessary telemetry explicitly: Chrome DevTools MCP’s usage collection and trace-URL lookup illustrate why CI defaults are insufficient.  
   **Check:** Exercise forbidden requests directly, including encoded URLs and redirects; scan exported artifacts for synthetic secrets with `CI` unset. [Upstream telemetry settings](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/configuration.md)

6. **High — Browser debugging can expose the entire signed-in session.**  
   **Scenario:** Another local process connects to an open debugging port and controls webmail.  
   **Fix:** Use a separate profile and private pipe for managed automation, with no debugging listener or agent-accessible raw control. Chrome 136 restricts both port and pipe switches against the default profile; Chrome 144’s consent-based attachment is a different route, not approval for each action. Keep the browser’s own sandbox enabled.  
   **Check:** Inspect actual launch arguments, listeners, profile access and sandbox state; test shipping Chrome as well as Chrome for Testing. Playwright’s inspected source adds `--no-sandbox` unless explicitly enabled. [Chrome restrictions](https://developer.chrome.com/blog/remote-debugging-port), [Existing-session attachment](https://developer.chrome.com/docs/devtools/agents/get-started/configuration), [Playwright launch source](https://raw.githubusercontent.com/microsoft/playwright/main/packages/playwright-core/src/server/chromium/chromium.ts)

7. **High — Unattended startup can expose credentials or weaken transport security.**  
   **Scenario:** A locked credential store leads to a plaintext password fallback, or a fixture configuration accepts an invalid production certificate.  
   **Fix:** Require owner unlock initially; missing or locked storage fails closed. Keep secrets out of the companion environment, command arguments and logs. Use narrow provider permissions and verified TLS without plaintext fallback.  
   **Check:** Cold boot, locked storage, revocation, certificate mismatch and downgrade attempts must fail before credentials are disclosed. Scan logs and process arguments for canaries. [Mail TLS requirements](https://www.rfc-editor.org/rfc/rfc8314.html#section-5)

8. **High — Automation can act on a stale or wrong target.**  
   **Scenario:** The owner edits a form while Claude thinks, or a mailbox is recreated and an old message identifier now points elsewhere.  
   **Fix:** Bind browser operations to profile, tab and document identity; bind mail operations to account, mailbox and validity information. Recheck affected state, pause on conflicts and expose local Stop/status.  
   **Check:** Switch tabs, navigate, edit concurrently, recreate the mailbox and disconnect. Unrelated content and manual corrections must survive.

9. **Deployment blocker — Flatpak is currently unavailable to the daily account.**  
   **Scenario:** A brief assumes `flatpak run` will launch Chrome; AresOS denies execution.  
   **Fix:** Qualify a native package first. Any later Flatpak enablement is a deliberate policy change that must preserve controlled updates and narrow permissions.  
   **Check:** Launch the exact browser as its intended runtime identity in the VM and rerun updater-denial checks. [Build restriction](../../../os/build.sh:93), [Guest assertion](../../../os/tests/guest.sh:24)

10. **Deployment blocker — Graphical tools and user services may connect to different sessions.**  
    **Scenario:** A tool works from a terminal but finds no applications when started as a service.  
    **Fix:** Explicitly connect the graphical bridge to the active session and stop/invalidate it when that session ends. Resolve the current separate D-Bus arrangements before adding desktop accessibility.  
    **Check:** Compare terminal, service and fixture-app connections, then restart the compositor. Old handles must become invalid. [Session launch](../../../os/config/usr/bin/aresos-session:7), [Service audit](../../../os/tests/audit.py:59)

11. **Deployment blocker — Existing CI success does not demonstrate control-layer integration.**  
    **Scenario:** Container tests pass and the report claims AresOS support, although the VM never launches these tools; reusing the image job also introduces publication.  
    **Fix:** Add the explicit nonpublishing VM path, with read-only registry permissions and separate container/VM/hardware evidence.  
    **Check:** Two fresh VM passes exercising the new operations, with publication absent and package writes unavailable. The current harness checks session, recovery and power behaviour; the image job is tied to the historical release branch. [VM harness](../../../os/ci/vm.py:105), [Image workflow](../../../.github/workflows/os-image.yml:115)

12. **Should fix before promising compatibility — Provider and dependency assumptions can invalidate the implementation.**  
    **Scenario:** Password-based IMAP works in CI but the real account requires another authentication flow; development documentation advertises a command absent from the pinned release.  
    **Fix:** Obtain provider information, qualify exact released artifacts and maintain one browser backend and one mail engine. Keep upgrades controlled and test retained-state rollback.  
    **Check:** Clean-install the pinned versions, exercise authentication expiry and unsupported capabilities, and verify upgrade/rollback. A successful fixture test is not evidence of real-provider support.

13. **Should fix before the owner trial — A working backend can still be unusable.**  
    **Scenario:** Minecraft is unavailable, cloud help cannot start offline, or a draft leaves the owner reconstructing recipients, attachments and the original conversation.  
    **Fix:** Provide the terminal entry immediately, with local diagnostics and cancellation. Complete and document the manual-send handoff. Keep reply source and account visible.  
    **Check:** Run without Minecraft, Claude and networking; then finish a fixture reply through the intended client and inspect the received message. Record the steps required from the owner.

The remaining disagreements are product choices, not unresolved factual disputes. Workflow-first development wins over a general framework, while retaining one small shared policy service; Playwright is the first browser choice because it directly addresses selected-tab handoff. A phone is optional, qualified read-only access can precede write approval, and the `ares` graphical bridge must remain separate from protected credentials.

Two corrections matter: provider permissions can separate reading from sending, so real reading does not inherently require a transaction-approval device; and CLI-Anything is not limited categorically to open-source applications—its catalogue includes a Zoom REST adapter. Neither fact establishes AresOS compatibility or justifies generic desktop automation now. [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes), [CLI-Anything catalogue](https://github.com/HKUDS/CLI-Anything)

GAPS-FOUND (13)