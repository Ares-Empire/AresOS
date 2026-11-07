**3. Skeptic**

**Recommendation — assumed judgment:** adopt existing browser and mail engines; build only the small AresOS layer needed to constrain operations, expose them consistently and verify them. A general desktop automation framework is unnecessary for the first version.

**Evidence:** checked against repository commit `4690074` and the upstream sources linked below. “Checked” means inspected documentation or source, not executed successfully on AresOS. Scenarios and recommendations are assumptions. No files were edited; proposed tests were not run.

**Findings, most severe first**

1. **Existing automation servers do not automatically satisfy “sending or deleting asks first.”**

   **Checked:** Playwright explicitly says its MCP server is not a security boundary. Classic Mail MCP’s destructive-operation confirmation is a caller-supplied string; its send tools instruct the caller to obtain authorization. Those mechanisms alone do not establish that the owner approved anything. [Playwright security](https://github.com/microsoft/playwright-mcp#security), [Classic Mail tool contract](https://github.com/kapitelh/classic-mail-mcp/blob/main/docs/tools.md)

   **Scenario — assumed:** AresOS carefully gates `mail.send`, but Claude can still click Send in webmail through a general browser tool. Alternatively, it supplies a connector’s confirmation argument itself.

   **Impact:** adopting connectors wholesale would break the central promise while appearing to implement it.

   **Fix — proposed:** adopt their engines, but expose only qualified operations. Start with mail reading and locally prepared replies, with the owner sending manually. Browser navigation, filling, pressing Enter and JavaScript execution must not be classified as harmless merely because their names omit “send”; a form can submit or autosave from those actions. A wrapper is not an enforceable boundary if Claude can reach the same credentials or unrestricted backend through its shell.

   **Check — proposed:** use a fake webmail application and mailbox server. Attempt the same send through every exposed route, including browser actions and direct backend access; verify the server receives nothing without owner authorization. This is a prerequisite to enabling real-account mutations.

2. **A custom Chrome control engine would duplicate substantial existing functionality; profile handoff is the actual gap.**

   **Checked alternatives:**

   | Existing option | What it already provides | Proposed use |
   |---|---|---|
   | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md) | Structured snapshots, field filling, tab control and script execution; the package also has a [CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md). | First backend to qualify for the Chrome-only requirement. |
   | [Playwright MCP](https://github.com/microsoft/playwright-mcp) | Accessibility snapshots without screenshots, browser actions and an extension path to existing tabs. | Alternative if the first backend fails a concrete required workflow; do not maintain both initially. |
   | [Claude Code with Claude in Chrome](https://code.claude.com/docs/en/chrome) | Existing browser integration, shared login state, DOM inspection and form automation. It requires a direct Anthropic plan and interactive `/login`; API-key and `setup-token` authentication do not enable it. | Lowest-code owner trial, subject to the required confirmation behavior and account setup. |

   **Checked:** Chrome 136’s restriction applies to **both** remote-debugging port and pipe switches against the default data directory. However, current Chrome documentation also describes Chrome 144+ consent-based attachment through `--autoConnect`. Therefore, “we must write an extension to reach the real profile” is not established. [Debugging-switch changes](https://developer.chrome.com/blog/remote-debugging-port), [Current connection options](https://developer.chrome.com/docs/devtools/agents/get-started/configuration)

   **Scenario — assumed:** a demo fills a form in a newly launched browser, but the owner asks Claude to continue in their already-open university tab.

   **Impact:** successful automation produces the wrong product experience; copying cookies or asking the owner to log in repeatedly adds maintenance and friction.

   **Fix — proposed:** qualify an upstream connection path before building a bridge. Explicitly distinguish a disposable automation profile from takeover of an existing owner session.

   **Check — proposed:** create two disposable profiles with different synthetic logins. Verify the selected profile and tab, reconnect behavior and preservation of unsent form contents. Test structural operations with screenshot tools disabled.

3. **Mail implementation should wait for provider information only where necessary; writing a mail stack now would be wasted work.**

   **Checked:** [Himalaya v2.2.1](https://github.com/pimalaya/himalaya/blob/v2.2.1/README.md) already supplies a JSON CLI covering IMAP/SMTP, JMAP, Gmail and Microsoft Graph, subject to compiled features. Its authentication integration still needs configuration and, for OAuth, an external token broker.

   **Checked:** [Classic Mail MCP](https://github.com/kapitelh/classic-mail-mcp) is another candidate: read-only by default, mail search/read and attachment access, with optional mutations. It requires password or app-password mailbox authentication; its Google OAuth authenticates clients **to the MCP server**, not to Gmail. The project labels itself a public preview.

   **Scenario — assumed:** a password-based IMAP adapter passes all container tests, then the owner identifies an account requiring provider OAuth or another protocol.

   **Impact:** the first adapter may be unusable, and the owner inherits authentication plumbing that an existing client could have supplied.

   **Fix — proposed:** qualify a released mail engine behind a small operation interface. Prefer an existing provider API when the account supports it; use IMAP/SMTP where appropriate. Do not build MIME handling, mailbox synchronization or multiple authentication flows speculatively.

   **Check — proposed:** test search, message reading without changing unread state, Unicode, attachments and pagination against a container-local mail server. Separately test token expiry and authentication failure using synthetic endpoints. These checks establish adapter behavior, not compatibility with the unknown real provider.

4. **The existing VM gate does not yet prove this control layer works in the real session.**

   **Checked:** the session runs labwc inside `dbus-run-session`, but its autostart currently opens a terminal. The Linux app launcher is explicitly unavailable. The VM checks session/recovery/power policy, not mail or Chrome automation. Furthermore, the image job is restricted to the historical keyboard-release branch and includes publication. [Session script](../../../os/config/usr/bin/aresos-session:7), [Autostart](../../../os/config/usr/share/aresos/labwc/autostart:1), [Linux launcher](../../../mod/src/client/java/dev/aresos/client/launch/LinuxAppLauncher.java:8), [VM harness](../../../os/ci/vm.py), [Workflow](../../../.github/workflows/os-image.yml:115)

   **Scenario — assumed:** headless Chrome works in an Ubuntu container, so a brief reports “AresOS integration passed.” On AresOS, the process instead has the wrong session environment, cannot find its browser, or cannot connect across the selected packaging boundary.

   **Impact:** failures move to installation week, when the owner expected working tools.

   **Fix — proposed:** separate protocol tests from real-image session qualification. Add a test-only VM path rather than repurposing the historical release job. Run the adapter as the daily user inside the actual session.

   **Check — proposed:** two fresh VM passes covering startup, browser connection, synthetic mail access, process restart and recovery-terminal availability. Container success and VM success must be reported separately.

5. **AT-SPI, wtype and ydotool are useful fallbacks, not interchangeable app APIs.**

   **Checked:** [linux-desktop-mcp](https://github.com/lotnikov/linux-desktop-mcp) already exposes AT-SPI tree inspection, element actions and value setting. It documents Wayland support for reading/direct value setting, but an X11-only clipboard fallback and uneven application coverage. [wtype’s source](https://github.com/atx/wtype/blob/master/main.c) requires the compositor’s virtual-keyboard protocol. [ydotool](https://github.com/ReimuNotMoe/ydotool) injects input through `/dev/uinput`, requiring access normally restricted to privileged processes.

   **Scenario — assumed:** an application exposes only an empty accessibility frame. A fallback types a reply, but focus has moved to another window.

   **Impact:** silent wrong-window input and a growing collection of app-specific exceptions; broad input-device access adds another deployment obligation.

   **Fix — proposed:** postpone generic desktop control until the owner names a required application that lacks a service or remote-control API. Then qualify that application’s actual package and toolkit. Mail APIs and browser DOM control do not require choosing labwc versus KWin; window geometry, activation and synthetic-input fallbacks do. Flatpak also filters D-Bus access, so installed-package behavior needs testing rather than blanket permission expansion. [Flatpak permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html#d-bus-access)

   **Check — proposed:** test the selected app in the AresOS VM, including missing accessibility data and focus changes. Unsupported operations must fail visibly instead of silently switching to keystrokes.

6. **Generators and unpinned upstream installs would leave one owner maintaining more than the apparent “thin wrapper.”**

   **Checked:** CLI-Anything already offers generated harnesses and a catalogue. Its LibreOffice example uses document generation plus headless rendering; its Zoom harness uses the REST API. Thus “closed apps cannot benefit” is too broad, but its source-driven generation process is not a universal live-window interface. [CLI-Anything](https://github.com/HKUDS/CLI-Anything)

   **Checked version trap:** Himalaya’s development README advertises `himalaya mcp`, while the latest published release found, v2.2.1, has no MCP command in its command enum. A brief copied from current development documentation could therefore fail against the released binary. [Development documentation](https://github.com/pimalaya/himalaya#MCP-server), [Released command definitions](https://github.com/pimalaya/himalaya/blob/v2.2.1/src/cli.rs)

   **Scenario — assumed:** a generated document CLI modifies an on-disk file while the owner has unsaved edits open; or an `@latest` dependency changes behavior after qualification.

   **Impact:** conflicting state, broken workflows and recurring repair beyond the initial build.

   **Fix — proposed:** reuse existing harnesses only for a named workflow, distinguishing file processing from live-app control. Pin one browser backend, one mail engine and their dependencies. Keep updates within AresOS’s existing maintenance process. The recurring work will be authentication changes, browser/runtime compatibility and selected site workflows; adding a second implementation multiplies that work.

   **Check — proposed:** test the exact released artifacts from a clean environment, then exercise upgrade and rollback. For document adapters, explicitly test unsaved GUI state rather than accepting a valid exported file as proof of live-app control.

**General case**

**Assumed judgment:** this is an instance of confusing an automation transport with a supported owner workflow—upstream tools cover much of the transport, while AresOS still owns authorization, correct session selection and repeatable qualification.

**Smallest useful version**

1. **Brief 1: qualify one upstream Chrome backend.**  
   **Proposed:** use Chrome DevTools MCP with a disposable Chrome for Testing profile and a local fixture website. Exercise snapshots, extraction, form fields, tab identity and restart through deterministic MCP calls; no paid model session or real login is necessary. Keep this in a new `control/` area and a separate container-test workflow. No GHCR read token or package write access is needed.

2. **Brief 2: mail reading and local reply preparation.**  
   **Proposed:** qualify a released mail engine, provisionally Himalaya’s CLI, and add only the small MCP surface actually missing. Use [GreenMail](https://greenmail-mail-test.github.io/greenmail/), which supplies containerized IMAP/SMTP testing. Verify mailbox state independently; keep send/delete unavailable to the agent. The owner’s provider answer determines the production backend and authentication work. This also needs neither missing GitHub setting.

3. **Brief 3: qualify the same tools inside the frozen AresOS image.**  
   **Proposed:** add a test-only overlay and VM entry point, coordinating changes under `os/ci/` with installation work. Verify the real daily-user session twice. This requires restored private-image read access—through `GHCR_READ_TOKEN` or explicitly granted job-token access—but no package write permission if nothing is published. The missing settings are recorded in [HANDOFF.md](../../../HANDOFF.md:12). Image rebuilds remain owner-authorized. None of these briefs needs a mod or install-guide change.

**Waits for the first boot**

- **Assumed:** owner evaluation of actual browser-profile takeover, login recovery, confirmation friction and idle resource use. Synthetic tests cannot settle whether these feel acceptable.
- **Checked dependency:** hub-to-app companion behavior also needs the currently unimplemented Linux helper and later Minecraft integration; first boot alone does not supply them.
- **Assumed:** final desktop fallback selection depends on the chosen compositor and actual apps. Mail and browser protocol work can proceed beforehand.
- **Assumed:** real-account mutations wait for the provider decision and a qualified approval boundary, regardless of whether first boot has happened.

**Questions only the owner can answer**

- Which mail provider, supported protocol and authentication method must work? No address or credentials belong in the public answer.
- Must Claude continue in existing signed-in tabs, or is a separate automation profile acceptable?
- Which two or three concrete tasks—and which apps beyond mail and Chrome—would justify ongoing maintenance?
- Is manual sending from a prepared reply acceptable initially, and which independent confirmation channel should eventually authorize mutations?
- Will the always-on Claude session use interactive Anthropic login, or another authentication mode? This changes whether Claude in Chrome is an option.

BUILD