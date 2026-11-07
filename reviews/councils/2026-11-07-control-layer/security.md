**2. Security and privacy**

Build the isolated, synthetic-account prototype now. Real-account access needs an enforcement boundary outside Claude and an independently authenticated confirmation channel.

**Checked:** reviewed the requested sources at `4690074` and the upstream documentation linked below. The current session starts labwc and a terminal, not Minecraft; Linux app launching remains a stub. See [session](../../../os/config/usr/bin/aresos-session:7), [autostart](../../../os/config/usr/share/aresos/labwc/autostart:1), and [LinuxAppLauncher](../../../mod/src/client/java/dev/aresos/client/launch/LinuxAppLauncher.java).

All scenarios, impacts and recommendations below are **assumed design analysis**, not observed exploits. Proposed checks were **not run**. No files were edited.

**Findings, most severe first**

1. **Critical — Confirmation is bypassable if Claude retains another route to the same authority.**

   **Checked:** the existing helper design explicitly says its same-user socket is not a security boundary against other programs of that user. Claude Code’s documentation likewise distinguishes permission prompts from OS-enforced restrictions. MCP’s `readOnlyHint` and `destructiveHint` are advisory metadata. Sources: [OS-BASE §B1](../../../docs/design/OS-BASE.md:236), [Claude Code security](https://code.claude.com/docs/en/security), [MCP annotations](https://modelcontextprotocol.io/specification/2025-06-18/schema#toolannotations).

   **Scenario:** an injected email persuades Claude to bypass `mail.send` by running a Python SMTP client, using webmail through Chrome, or modifying the approval service.

   **Impact:** the owner sees no confirmation even though the advertised tool behaves correctly.

   **Fix:** CLI and MCP must be thin clients of one policy broker. The broker classifies operations and checks authorization immediately before execution. Run the companion agent in an enforced sandbox without mail credentials, browser profiles, raw CDP, unrestricted network access, host session/accessibility buses, input injection, or writable broker code/configuration. Separate broker credentials and execution under a protected, unprivileged OS identity. Keep the recovery/coding assistant outside this companion session.

   **Check:** use a deliberately hostile client—not just an obedient model—to attempt direct SMTP, raw browser control, policy modification, credential reads and alternate desktop tools. Every bypass must fail at the OS or broker boundary. A malicious process with the signed-in desktop user’s unrestricted authority remains dangerous; root or broker compromise is outside this guarantee.

2. **Critical — “Prepare, then confirm” proves nothing if the agent can perform both steps.**

   **Checked:** the confirmation channel is undecided in [QUESTION.md](../../../reviews/councils/2026-11-07-control-layer/QUESTION.md). Existing [Mail-MCP](https://github.com/rafaelreverberi/Mail-MCP) advertises preview/token-based confirmation, but that interface alone does not establish an independent human decision.

   **Scenario:** Claude calls `prepare_send`, receives a token, then calls `confirm_send`; alternatively, the owner approves one attachment and Claude replaces its contents before execution.

   **Impact:** forged consent or a different action from the one reviewed.

   **Fix:** choose an approval credential held independently on the owner’s phone. The existing push service may notify; it must not itself constitute approval merely because a callback URL was visited. The phone must show broker-generated action details and authenticate approval of that exact immutable operation. Bind account, full recipients including Bcc, body, attachment bytes, deletion targets, expiry and a single-use nonce. Edits invalidate approval. Claude receives status, never approval credentials. A companion chat message, agent-controlled terminal, or browser automation session is insufficient.

   Persist execution state across crashes. **Checked:** SMTP timeout ambiguity can cause duplicate delivery; it cannot honestly promise exactly-once delivery. [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321.html#section-6.1). An uncertain result must stop for reconciliation rather than trigger an automatic resend.

   **Check:** forged callbacks, replay, expiry, concurrent execution, changed Bcc/attachments, cancellation, broker restart and a dropped final SMTP response. None may silently authorize or repeat an operation. Until the phone channel is qualified, real sends/deletes remain disabled.

3. **High — A debugging port exposes much more than the requested browser action.**

   **Checked:** Chrome 136’s restriction covers **both** `--remote-debugging-port` and `--remote-debugging-pipe` against the default data directory; a nonstandard `--user-data-dir` is required. Chrome for Testing is an exception. [Chrome announcement](https://developer.chrome.com/blog/remote-debugging-port).

   **Checked:** Chrome DevTools MCP explicitly warns that any application on the machine can connect to an exposed debugging port and control the browser. Current documentation also describes Chrome 144+ interactive attachment through `chrome://inspect/#remote-debugging`; that is connection consent, not approval of each subsequent action. [Connection documentation](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/advanced-usage.md).

   **Scenario:** an unrelated local process connects to port 9222 while the owner is signed into mail and operates that session.

   **Impact:** account actions and disclosure outside AresOS’s approval checks. Loopback binding does not authenticate local callers.

   **Fix — choice:** use a **separate automation profile plus pipe-only transport**. These are complementary decisions. The protected browser adapter owns the pipe; Claude gets narrow broker operations. Puppeteer supports this transport. [Puppeteer launch options](https://pptr.dev/api/puppeteer.launchoptions). Do not copy the everyday profile or enable sync/password-manager access.

   An extension bridge is worth evaluating later for selected everyday tabs. **Checked:** Claude in Chrome already shares browser login state and supplies site permissions; Playwright’s extension supports connection approval and a token that bypasses that dialog. Neither documented mechanism establishes AresOS’s exact-action approval contract. [Claude integration](https://code.claude.com/docs/en/chrome), [Playwright extension](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md).

   **Check:** verify no debugging listener, no access to the ordinary profile, no raw evaluate/CDP escape, and rejection of unauthorized peer access. Test shipping Chrome in a disposable home as well as the testing browser; Chrome for Testing alone cannot verify the default-profile restriction. A pipe does not cure unrestricted same-user access to the browser process or profile.

4. **High — “Read”, “fill” and “delete” need adapter-specific definitions.**

   **Checked:** IMAP `BODY.PEEK` avoids setting `\Seen`; `CLOSE` and `EXPUNGE` can permanently remove messages already marked deleted. AT-SPI exposes text replacement, not a guarantee about an application’s downstream behavior. [RFC 9051](https://datatracker.ietf.org/doc/html/rfc9051), [AT-SPI EditableText](https://docs.gtk.org/atspi2/method.EditableText.set_text_contents.html).

   **Scenario:** “fill this draft” triggers a web app’s autosave/upload before Send is clicked; closing an IMAP session expunges messages outside the approved deletion.

   **Impact:** premature disclosure or unintended deletion despite apparently safe tool names.

   **Fix:** classify actual effects, with unknown effects denied. Proposed initial policy:

   | Adapter | Free within an owner-approved read scope | Requires confirmation, or remains unavailable |
   |---|---|---|
   | Mail API / IMAP / SMTP | Search, bounded message reads, attachment retrieval into an inert private store; IMAP `EXAMINE` and `BODY.PEEK` | Send, reply, forward, receipts and server-side draft/attachment uploads. Trash, deletion flags, moves and permanent deletion. Gate other mailbox mutations initially; leave bulk expunge unavailable. |
   | Chrome | Bounded snapshots of explicitly selected content | Submission, uploads, sharing, purchases, account changes and deletion. Treat typing/filling as potentially transmitting. Generic JavaScript and raw CDP are unavailable. Navigation is a network action, not automatically a free read. |
   | AT-SPI / D-Bus | Scoped tree/property reads through reviewed interfaces | Text edits, actions, key injection and arbitrary methods. “Click button named Send” is not a sufficient semantic contract; unsupported workflows stay manual. |

   Local draft composition can remain free. Moving it into a remote service cannot.

   **Check:** inspect effects on the fixture server: unchanged IMAP flags and mailbox contents after reads; no remote image loads; no autosave before approval; no deletion beyond the exact target set. Include a page that sends data on each keystroke.

5. **High — Prompt injection can exfiltrate through a “read” route without calling Send.**

   **Checked:** Chrome DevTools MCP returns untrusted page content and leaves injection precautions to the client. [Security policy](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/SECURITY.md).

   **Scenario:** an email tells Claude to “verify this document” by opening a URL containing another email’s contents. Or it supplies a link to a local approval/admin endpoint.

   **Impact:** private content leaves through navigation, search parameters or an attachment fetch; the send gate never runs.

   **Fix:** treat mail, pages, filenames, accessibility labels and tool errors as untrusted data. Preserve provenance and escape control characters, but do not mistake formatting or injection detection for enforcement. Read tools must not accept arbitrary execution or unrestricted fetches. Scope access to owner-selected accounts/folders/tabs; mediate outbound requests, redirects and local-network destinations. Keep attachment parsing isolated and non-executing. Content must never widen permissions or authenticate approval.

   **Check:** fixtures containing forged owner instructions, encoded exfiltration URLs, redirects to loopback and malicious attachment names. Drive the forbidden calls directly and assert no external request or mutation occurs; model refusal is supplementary evidence.

6. **High — Autologin and a desktop keyring do not establish credential isolation.**

   **Checked:** greetd automatically starts the locked daily account; the session creates a D-Bus session. Existing configuration does not establish a control-layer secret-unlock policy. [greetd](../../../os/config/etc/greetd/config.toml:4), [account locking](../../../os/build.sh:40). The Secret Service specification permits implementations to make unlocked secrets available to other clients. [Secret Service unlocking](https://specifications.freedesktop.org/secret-service/latest/unlocking.html).

   **Scenario:** to make unattended startup work, an implementation stores an app password in `.mcp.json`, uses an unprotected fallback store, or lets Claude query an unlocked desktop keyring.

   **Impact:** the credential bypasses every action-level check and may survive in logs or backups.

   **Fix:** provision credentials directly into a broker-only encrypted store outside the repository. Require explicit owner unlock initially; unavailable/locked storage fails closed. Keep runtime credentials in the adapter, never tool output or Claude’s environment. Prefer provider-supported least-privilege OAuth scopes once the provider is known. Browser cookies remain inside the protected automation profile. Approval credentials remain separate from mail credentials.

   **Check:** cold boot, missing keyring, locked store, token expiry/revocation and another daily-account process attempting access. Scan process arguments, logs, crash artifacts and backups for synthetic secret canaries.

7. **High — “Reading is free” still discloses content to the model and can create public evidence.**

   **Checked:** local Claude Code sends data to its model service; training and retention depend on account settings. [Data usage](https://code.claude.com/docs/en/data-usage). The repository is public, and the privacy check is local; the workflow uploads evidence independently of that hook. [HANDOFF](../../../HANDOFF.md:5), [artifact upload](../../../.github/workflows/os-image.yml:254).

   **Scenario:** an inbox summary includes a password-reset link, then an owner troubleshooting session uploads the transcript or a browser trace as review evidence.

   **Impact:** sensitive correspondence reaches additional services or public artifacts without any mail send.

   **Fix:** define “free” as no repeated confirmation **within a previously approved data scope and model destination**. Default to bounded retrieval, no background whole-inbox ingestion, and no raw bodies, cookies, authorization headers or captured traffic in diagnostics. Keep production diagnostics private; public CI uses synthetic data only. Push notifications should contain minimal details.

   **Check:** synthetic canaries in bodies, headers, URLs and attachments must be absent from exported diagnostics and public artifact bundles. Verify the chosen Claude account’s data settings before real-mail access.

**General case:** **Assumed analysis:** this is the wider problem of granting an untrusted planner broad authority and then trying to recover safety through natural-language instructions; enforcement must sit where authority is exercised.

**Smallest useful version — proposed, unverified**

1. **Broker and isolation contract.** Add a separate `control/` area and a dedicated container-test workflow. Implement shared CLI/MCP policy, immutable proposals, independent test-signer approval, expiry/replay protection and restart behavior. Test with a hostile client and a fake adapter. No production `os/`, `mod/` or install-document changes; no GHCR credentials or package write access.

2. **Synthetic mail adapter.** Use established mail libraries behind the broker; evaluate existing MCP implementations for reusable parsing and protocol handling, not as presumed approval authorities. Run an actual IMAP/SMTP fixture server inside the test environment, with external delivery blocked. Deliver search/read, local reply drafts, approved synthetic send and exact-target trash tests. No real accounts or GHCR access. Provider API/OAuth qualification remains separate once the owner identifies the provider.

3. **Restricted Chrome adapter and VM qualification.** Reuse Puppeteer or Playwright for transport; add only the narrow AresOS policy surface. Test a separate profile, pipe transport, scoped snapshots and malicious fixture pages. Then exercise the same isolation and locked-secret behavior in an AresOS CI VM twice.

   **Checked constraint:** today’s [VM harness](../../../os/ci/vm.py) checks session/recovery/power policy, not these controls; its image workflow is currently tied to a release-and-publication path. A new nonpublishing qualification path is required. It would touch `os/ci/` and workflow files, coordinated with install work. Pulling the retained private release needs restored read authorization; reusing existing rehearsal paths needs `GHCR_READ_TOKEN`. Local test overlays need no package write permission. Publication needs restored package write access and owner authorization.

**Waits for the first boot**

- **Proposed:** actual owner provisioning, unlock/relock behavior, phone pairing and everyday signed-in browser use.
- **Proposed:** companion confirmation presentation, selected-tab behavior, portals and accessibility against the installed apps.
- **Checked/proposed distinction:** the current session is labwc with its own D-Bus launch. Mail policy, approvals and pipe transport do not require choosing KWin. Desktop integration and actual Flatpak/bus permissions need qualification on the chosen session. Flatpak documents filtered bus access and warns against granting the whole bus; do not solve integration failures by broadly opening it. [Flatpak permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html).
- Container/VM security work can proceed now; hardware use must not be presented as already verified.

**Questions only the owner can answer**

- Which mail provider, protocols and authentication are used? This determines the production adapter and available credential scopes.
- Is a separate automation browser profile acceptable initially? If everyday tabs are essential, extension evaluation becomes an earlier brief.
- Which phone push service is available, and is independent phone approval acceptable? Its authentication capabilities are currently unknown.
- Which folders, tabs and attachment types may be sent to Claude, under which account/data settings?
- Which apps beyond mail and Chrome matter first?

BUILD