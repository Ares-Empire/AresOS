# AresOS control layer: the plan

Updated 2026-11-07. Led by the Claude session `mac-aresos-control`. The owner's picture is
[`OWNER-SCOPE.md`](../../reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md); it wins over the council's
VERDICT wherever they differ. This file is the plan and where it stands; keep it true.

## What we are building

A central Claude Code session, part of AresOS, runs the owner's apps through clean tools. Each app gets one tool set,
offered both as a terminal command (CLI) and as an MCP server, built from one definition. Every app with all of its
features. Screenshots and mouse moves are a last resort, never the main path.

The first two apps are Mail and Chrome. Those two are made to work really well before any other app starts.

- **Mail:** read, search, threads, write, reply, forward, send, attachments (download and attach), folders, flags,
  move, delete.
- **Chrome:** in the owner's own signed-in tabs. Claude sees the page as structure (fields with their labels and
  values, buttons, links, text, and where each one is on the page), navigates, fills and clicks without screenshots.
  A separate browser profile is only a test fixture.

## Decisions (owner, 2026-11-07)

1. **Approval is Claude Code's own permission prompt.** At the laptop he answers it in the session; when away,
   through Claude Code remote control on his phone (he approves pushes there). No separate approval screen in Aresus.
2. **What asks:** sending, deleting and submitting. Reading, searching, scrolling, following links and typing into
   fields are free. In Chrome, anything that submits data to a site asks, except on sites in a list the owner keeps.
3. **The exact permission settings are written once the tools exist** and we know more. The tools must be shaped so
   that settings can name each kind of action.
4. **Mail and Chrome first**, made to work really well; other apps after that.
5. **Questions for the owner go out as a push** (board ask plus a phone push), not only in a transcript.

## How sending stays under the owner's control

Three places, each with one job:

| Place | Its job | Why there |
|---|---|---|
| **The tools** | Know what each action really does, and give each kind its own tool: reading (`mail_search`, `chrome_read`), changing (`mail_move`), sending (`mail_send`, `chrome_submit`), deleting (`mail_delete`). In Chrome, a click or key press that would send data to the site is held and becomes a separate `chrome_submit` step. | Only the tool can see that a click sends something. |
| **Claude Code's settings** (a system-wide file in the image that only the admin account can change) | Decide which tools ask first and which are free. | Claude Code enforces them: Claude can't answer its own prompt and can't edit that file. Checked 2026-11-07: an "ask" rule still asks in skip-permissions mode, and the prompt shows the whole input ([check](../../reviews/control-checks/2026-11-07-permission-prompt.md)). |
| **CLAUDE.md** | Habits: how the owner writes mails, where things get filed. | These are requests to Claude. They are never what keeps sending under control. |

**Rules for every tool, so the prompt tells the truth:**

- An action that asks carries everything needed to judge it in its own input: the account, all recipients including
  Bcc, subject, the full text, attachment paths with their hashes; for Chrome the site, the address, the method and
  the data being sent. The tool refuses when the input doesn't match what would really happen (for example a file
  that changed after its hash was taken).
- Results are honest: sent, not sent, or "unknown, don't retry" (for example when the mail server's answer was lost).
  A tool never repeats a send by itself.
- Reading never changes anything: mail stays unread, nothing is saved on a site.
- Each result names exactly what it refers to (account, folder, message; tab, page, field), so Claude never acts on
  the wrong thing after the owner switched tabs or a folder changed.

**No way around the tools** (set up once in the image; the exact values come with the settings):

- Passwords and sign-in data belong to a separate system user. Only the tool service uses them; Claude's account
  can't read them.
- Claude's own terminal commands run in Claude Code's sandbox, which can't reach the tool service, the mail server or
  Chrome's control channel. Only the MCP tools can.
- The rules on asking, the allowed MCP servers and hooks, and the sandbox live in the system-wide file. Other ways to
  control the browser (Claude in Chrome, debugging ports) are off.
- Each of these gets a hostile test: a test Claude session tries every other route and must fail.

## Order of work

0. **Checks before building (now).**
   - **S1, Claude Code's prompt:** done 2026-11-07 ([check](../../reviews/control-checks/2026-11-07-permission-prompt.md)).
   - **S2, Chrome (brief 17):** can a tool attach to an already-open tab in normal Chrome with a normal profile
     (no debugging port), read the page as structure with positions, fill and click, and hold a submit before it
     leaves the browser? What can't be held (for example chat messages sent over a WebSocket)? Runs on GitHub's Linux
     machines. Chrome is the harder app, so its open questions are settled before the design is fixed.
1. **Design** (`docs/design/CONTROL.md`): the tool contract, the service and its system user, CLI and MCP from one
   definition, the full Mail and Chrome tool lists with inputs and results, and the tests. Written by Claude, because
   it is what Claude will read; reviewed by fresh Codex (frontier model) before anything is built.
2. **Core (brief 18):** the shared base, one test app, and the hostile tests, in containers.
3. **Mail and Chrome (briefs 19 and 20)**, side by side on the core. Mail is the easier one: a known protocol and a
   test mail server.
4. **Tool-user rounds** after each first version (see below); fixes become follow-up briefs.
5. **Security review** of the whole stack (fresh Codex, frontier), then **qualification in the real AresOS image** in
   the CI virtual machine. `laptop-aresos` is told before anything under `os/` changes.
6. **After the first boot on the laptop:** the real mail account, the owner's own Chrome, the system-wide settings,
   and the first weeks of real use.

Codex (ChatGPT Pro) ends 2026-11-21, so steps 1 to 5 are planned to be done by then.

## Who does what

| Who | Does | Reports to |
|---|---|---|
| `mac-aresos-control` (Claude, lead) | the plan, the design, the tool lists (what Claude will read), briefs, checking results, merges after the owner's "merge", the owner's questions | the owner |
| Codex workhorse (`gpt-6.1-sol`, xhigh) | checks (S2) and builds: one run per package in its own worktree, tested on GitHub's Linux machines | its package lead; for S2 the lead |
| Codex workhorse, fresh (`gpt-6.1-sol`, high, read-only) | package reviews | its package lead |
| Codex frontier, fresh (`gpt-6-astra`, xhigh) | the design review and the final security review: the base for every later app, and the security boundary | the lead |
| Claude package leads (background agents, one per running package) | run build, CI, review and fix rounds; report only when a package is ready for merge (summary and review result), on a JUDGMENT-CALL, or when blocked | the lead |
| Claude tool users (fresh agents that know nothing about the code) | do the everyday tasks below with the tools against a test mailbox and test sites; report where they got stuck, misread a result or needed too many calls | the lead: this is the check that the tools do what we need |
| `mac-capacity` | checks every few hours that the work matches OWNER-SCOPE | the owner |
| `laptop-aresos` | the install work, `os/`, `mod/` and the install docs | the owner |

Why this split: Codex has the capacity for building and reviewing until 2026-11-21, and every review is a fresh
context. Claude judges the tools from the user's side because Claude is the one who will use them. Package leads
keep build logs and review rounds out of the lead's context, so the lead keeps the overview and the owner gets short
answers. Briefs live on their package branch and reach `main` with the package; nothing is pushed to `main` without
the owner's "merge".

## Everyday tasks the tools must handle

The tool users run these against the test mailbox and test sites. A version is good when a fresh Claude finishes them
without screenshots, without guessing, and without asking the owner anything except the approvals. The owner can add
tasks at any time.

**Mail**

1. List the mails that need an answer this week, without marking anything as read.
2. Find a mail by sender and topic, show its thread, and download the attached PDF.
3. Reply to a thread with a short text and one file attached: recipients, subject and quoted text right.
4. Forward an invoice mail to a given address.
5. Move a month's invoices into a folder; flag one mail.
6. Delete a fixed set of newsletters to the Trash; the approval shows exactly which.
7. Write a new mail with two attachments to two people, one of them in Bcc.

**Chrome** (test sites)

8. In an open, signed-in tab: say what the page shows and which fields are still empty.
9. Fill a multi-page form (text, dropdowns, checkboxes, a date, a file upload) and stop before sending it.
10. Send that form: one asking step that shows the site, the address and the data.
11. Search a site and open the third result.
12. A page that saves while you type: typing there counts as sending and is held, unless the site is on the free
    list.
13. A chat page that sends messages over a WebSocket: handled as S2 finds possible.
14. Two similar tabs, and the owner switches tabs while Claude works: Claude stays on its own tab and doesn't touch
    the other.

## Open

- The exact system-wide settings: once the tools exist (decision 3).
- Language and libraries: decided in the design, after S2.
- How the CI virtual machine gets the AresOS image for step 5 (the private image needs read access the owner
  restores, or a fresh unpublished build in the job): decided in the design.
- The mail provider and account details stay out of this public repo.

## Where it stands

- **2026-11-07:** owner decisions above. S1 done. S2 (brief 17) running (Codex `gpt-6.1-sol`, branch
  `pkg/17-chrome-check`). Design draft for the shared base and Mail: [`docs/design/CONTROL.md`](../design/CONTROL.md);
  its Chrome part waits for S2, then the whole design goes to the frontier review.
