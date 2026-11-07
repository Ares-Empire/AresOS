**4. Daily use**

**Assumed recommendation:** build a small “find, explain, prepare” assistant first. Week-one value is finding the right mail, explaining the selected browser page, and preparing something the owner can review. Companion animation can follow.

**Checked:** reviewed the listed sources at `4690074`. This was source/documentation review; no runtime tests were run and no files were edited. Scenarios, frequency estimates, fixes and proposed checks below are **assumed**, not observed owner behaviour.

**Findings, most severe first**

1. **Confirmation must happen before the meaningful change, without interrupting every preparation step.**

   **Checked:** the [council question](../../../reviews/councils/2026-11-07-control-layer/QUESTION.md) requires confirmation for sending/deleting but leaves its presentation open. Some browser editing publishes immediately: Google Docs saves changes as the user types. [Google documentation](https://support.google.com/docs/answer/49114?hl=en&co=GENIE.Platform%3DDesktop)

   **Assumed — scenario:** “Prepare this paragraph for our shared document” changes the live document before the owner reviews it. Conversely, preparing three replies becomes intolerable if every search, read and wording change asks permission. **Impact:** either unexpected publication or habitual approval without reading. **Fix:** prepare content locally; present one review of the actual outward action, including account, recipients, complete content and attachments. A deletion approval should cover a fixed, inspectable selection, distinguishing Trash from permanent deletion. Changed content invalidates approval. Prefer review beside the work; phone confirmation should be optional for unattended tasks. **Check:** use an autosaving local page and a synthetic mailbox; verify zero publication before approval, zero sends after rejection, and no per-message prompts during a read-only summary. Initially keep final send/delete manual until the confirmation channel is settled.

2. **“Take over here” needs an explicit target and an immediate way to return control.**

   **Checked:** [README](../../../README.md:79) envisages simultaneous windows and the companion working inside an app. Existing tools can reuse browser state: Playwright’s extension supports selecting an existing tab; Claude Code’s Chrome integration shares login state but ordinarily opens task tabs. Neither description establishes AresOS’s intended handoff behaviour. [Playwright extension](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md), [Claude Code documentation](https://code.claude.com/docs/en/chrome)

   **Assumed — scenario:** the owner requests help with a half-filled form, then changes tabs or corrects a field while Claude is thinking. The assistant resumes against the wrong page or overwrites that correction. **Impact:** lost work, possibly under the wrong account; a separate empty browser also defeats the request. **Fix:** show the chosen profile, tab and task; retain that identity rather than following whichever tab is now active. Provide Stop/take-back-control. Recheck affected fields before writing and pause on conflicting edits. Leave the page open with a precise account of completed and remaining work. **Check:** two profiles, two similarly named tabs, owner edits during a delay, navigation and disconnect. Assert that unrelated tabs and manual corrections survive, and cancellation prevents subsequent actions.

3. **A morning mail summary must preserve the owner’s unread queue.**

   **Checked:** IMAP body retrieval can implicitly set `\Seen`; `BODY.PEEK` avoids that change. “Read-only” therefore needs behavioural testing, not merely the absence of a delete tool. [RFC 9051](https://www.rfc-editor.org/rfc/rfc9051.html#section-6.4.4)

   **Assumed — scenario:** “What needs a reply?” reads twenty messages and clears their unread status. Later, the owner trusts the inbox’s unread filter and misses something omitted from the summary. **Impact:** the assistant silently damages an existing task-management habit. **Fix:** preserve flags during search and summarisation; identify each source message and the search’s account/time scope. Make “mark these read” a separate requested action. Return reply drafts with their source thread and intended recipients visible. **Check:** seed unread/read messages, similar subjects, multiple folders and paginated results in the container mail server; compare flags before/after and verify every summary reference resolves to the intended message.

4. **The first useful entry point cannot depend on the companion or Minecraft being ready.**

   **Checked:** [labwc autostart](../../../os/config/usr/share/aresos/labwc/autostart) currently opens a terminal. [LinuxAppCatalogue](../../../mod/src/main/java/dev/aresos/catalogue/LinuxAppCatalogue.java) returns no apps, and [LinuxAppLauncher](../../../mod/src/client/java/dev/aresos/client/launch/LinuxAppLauncher.java) reports the helper unavailable. The recovery-capable help command is an idea in [README](../../../README.md:99).

   **Assumed — scenario:** the owner boots the initial OS, wants help connecting an app, and has neither the promised chat bar nor a working Minecraft app launch. During a network failure, starting cloud-backed help cannot itself explain the problem. **Impact:** working adapters remain inaccessible at exactly the moment they are needed. **Fix:** provide one documented terminal entry that reaches the existing assistant session, shows connected capabilities and task status, and supports cancellation. Its local diagnostic/help output must work without Claude or network access. Later, the companion becomes another entry to the same tasks. **Check:** invoke it from the daily session and recovery TTY with Minecraft absent, Claude absent and networking disabled; require useful local output and an explicit explanation of unavailable capabilities.

**Concrete use and frequency — assumed planning hypotheses**

| Moment | Useful request | Likely frequency to validate |
|---|---|---|
| Starting work | “Which messages need my attention? Show the originals.” | Once per working day, if mail is central |
| Working in Chrome | “Explain this page” or “compare these selected tabs.” | Several times per working day |
| Replying or completing administration | “Prepare a reply” or “prepare these form values for review.” | Several times weekly; possibly daily |
| Setup or something breaking | “Why can’t this app connect?” | Several times during setup, occasional afterward |

**Assumed:** companion takeover should shorten these same tasks; it is not an additional reason to automate. Simple app opening should remain convenient through existing desktop controls. Validate usefulness by whether the owner voluntarily repeats these workflows, including time spent correcting and confirming them.

**General case:** **Assumed:** this is a wider shared-control problem—automation is useful only when the owner can identify its target, understand its changes and resume manual work without reconstruction.

**Smallest useful version — assumed briefs, in order**

1. **One usable entry and task lifecycle.** A small CLI/MCP surface with task identity, status, cancellation, readable results and offline diagnostic help. Exercise it using fake adapters and a fake Claude process, including interruption and restart. Keep initial code in a separate control-layer directory with its own container-test workflow.

2. **Read the owner-selected Chrome tab and prepare an answer.** Evaluate existing integrations before writing browser plumbing. Playwright MCP already supplies structured accessibility snapshots without requiring screenshots; its extension can attach to existing tabs. [Upstream documentation](https://github.com/microsoft/playwright-mcp) Start with selected-page reading, source-linked answers and locally prepared form content. Test against synthetic authenticated pages in a headed browser on a standard Linux runner, including the handoff cases above. Arbitrary form submission is outside this first brief.

3. **One-account mail search, thread reading and local reply preparation.** Choose the real integration after the owner identifies provider/protocol/authentication. Existing mail MCP implementations advertise these operations and read-only modes; evaluate rather than assume their compatibility. [Example upstream project](https://github.com/honest-magic/mail-mcp) Test against an actual mail server inside the container, with synthetic messages and credentials. Until the provider is known, this proves the workflow contract only—not real-account readiness.

**Checked CI limits:** [vm.py](../../../os/ci/vm.py) tests session, policy, recovery and power behaviour, not these app workflows. The current [image workflow](../../../.github/workflows/os-image.yml:115) has package-specific release gating and proceeds to publication. [HANDOFF](../../../HANDOFF.md:5) records the missing registry settings.

**Assumed integration plan:** container tests need neither missing setting. Add a separately approved, nonpublishing VM test path for the frozen private image; its pull needs restored `GHCR_READ_TOKEN` or verified equivalent read access. Package Write access is needed for publication, which these tests need not perform. VM work touches `os/ci/` and the workflow; eventual installed commands require coordinated `os/` packaging changes and owner-approved image work. These first briefs need no `mod/` or install-guide changes.

**Waits for the first boot**

- **Assumed:** owner-supervised real-account onboarding and authentication renewal; synthetic tests cannot establish compatibility with the unknown mail account or actual browser packaging.
- **Assumed:** keyboard reachability, fullscreen interruption, focus behaviour and acceptable latency/resource use during the owner’s real workload.
- **Checked dependency; assumed sequencing:** [README](../../../README.md:103) leaves labwc versus KWin open. Mail, browser tab operations and terminal help need not wait for that decision. Companion positioning and movement between actual windows do; hub-to-app choreography additionally needs the unfinished Linux shell integration.

**Questions only the owner can answer**

- Which mail provider, protocol and authentication method must work? This determines brief 3’s adapter; credentials should remain private.
- Which two repetitive browser/mail tasks actually consume time, and how often? Which other app comes next?
- Is terminal access with read/prepare/manual-send useful for week one, or is in-app confirmation essential?
- Should confirmations normally appear on the laptop or through the existing phone push service? Is one approval for a visibly enumerated deletion batch acceptable?

BUILD