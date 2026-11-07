# The control layer: design

**Status:** draft, 2026-11-07. Covers the shared base and Mail. The Chrome part (section 6) is filled in after brief
17's check. A fresh Codex review (frontier model) checks this design before brief 18 is written.

The plan, the owner's decisions and who does what: [`docs/control/PLAN.md`](../control/PLAN.md). The owner's
picture: [`OWNER-SCOPE.md`](../../reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md). The council's 13 gaps
([`VERDICT.md`](../../reviews/councils/2026-11-07-control-layer/VERDICT.md)) are the checklist; section 9 maps each
one to where it is handled.

## 1. In one paragraph

A tool service runs under its own system user, holds the passwords, and does the work for every app. Each action is
defined once, with what it does to the world (its *effect*), and from that one definition come the MCP tools Claude
calls, the `aresos` terminal command, and the list of actions that must ask the owner. Claude Code asks the owner
before any action whose effect is sending or deleting; its own terminal commands run in Claude Code's sandbox and can
only reach the read-only side of the service. Every action that changes something is logged, and every result says
exactly what it refers to and what really happened.

## 2. The pieces

| Piece | What it is | Runs as |
|---|---|---|
| `aresos-toold` | The tool service: app adapters (Mail, Chrome, later more), passwords, the action log. Listens on two Unix sockets and nothing else (no TCP). | system user `aresos-tools` |
| `read.sock` | `/run/aresos-tools/read.sock`: accepts only actions whose effect is *read*. | |
| `act.sock` | `/run/aresos-tools/act.sock`: accepts every action. | |
| `aresos` | The terminal command: `aresos mail search --from … --json`. Generated from the definitions. Uses `read.sock` for reading, `act.sock` for everything else. | the caller |
| `aresos-mcp <app>` | One MCP server per app (`aresos-mcp mail`, `aresos-mcp chrome`), a thin generic proxy: it fetches its app's tool list from the service and forwards calls over `act.sock`. Claude Code starts it over stdio. | `ares` (daily user), started by Claude Code |
| Chrome bridge | How the service reaches the owner's own Chrome. Decided by brief 17 (section 6). | |
| Claude Code settings | The system-wide file (`/etc/claude-code/managed-settings.json` and `managed-mcp.json`), owned by root. Exact values come once the tools exist (owner decision 3). | |

**Who can reach what:**

| From | `read.sock` | `act.sock` | Passwords and sign-in data | Chrome's control channel |
|---|---|---|---|---|
| The owner's own terminal | yes | yes | no | only through the tools |
| Claude through its MCP tools (Claude Code itself, outside the sandbox) | yes | yes, and send/delete ask first | no | only through the tools |
| Claude's terminal commands (sandboxed) | yes (allowed in the sandbox) | no | no | no |
| Claude's file tools (Read, Edit, Write) | no sockets | no sockets | no: other user's files, plus deny rules for the browser profile | no |
| `aresos-toold` | | | yes | yes |

Why two sockets: Claude Code's prompt guards MCP tool calls, not terminal commands. The sandbox keeps Claude's
terminal commands away from `act.sock`, so the only way for Claude to change, send or delete is an MCP call, and
those ask where the settings say so. Reading through the terminal stays possible, so Claude can pipe results into
other commands.

A program that runs as the owner outside the sandbox can use `act.sock` without asking. That is the normal desktop
trust model (such a program could also type into Chrome); the line this design draws is around Claude.

## 3. One definition per action

Each action is defined once in the service:

- **Name:** `<app>_<verb>`, for example `mail_search`. MCP name `mcp__<app>__<verb>` (`mcp__mail__search`); terminal
  `aresos <app> <verb>`.
- **Effect**, one of:
  - **read:** changes nothing anywhere. Reading a mail leaves it unread; reading a page saves nothing.
  - **change:** changes the owner's own data, can be undone, and reaches no one else: move, flag, mark as read,
    save a draft, save an attachment to disk, create a folder, type into a field that the site doesn't send.
  - **send:** data leaves to someone else: send a mail, submit a form, anything a site receives because of an
    action.
  - **delete:** removes something, to the Trash or for good.
- **Input and result schemas**, and a **description written for Claude**: what it does, when to use it, what it
  returns, its effect, and what to do on each error.
- **owner-only** (optional): actions that are never offered to Claude, such as account setup or the list of trusted
  sites. They exist only in the terminal command, over `act.sock`, and the MCP proxy never forwards them.

Generated from the definitions: the MCP tool lists, the terminal command with its `--help`, a reference page
(`docs/control/TOOLS.md`), and the list of send and delete actions for the settings. A test fails if any send or
delete action is missing from the settings' ask list, so the two can't drift apart.

Default settings (exact values later, owner decision 3): send and delete ask; read and change are free. One action
has one effect: when an action could do two things (for example compose a reply and save it as a draft), it becomes
two actions.

## 4. Rules every action follows

1. **The asking input tells the whole truth.** A send or delete action carries everything the owner needs to decide
   in its own input, because the prompt shows exactly that input (checked:
   [`2026-11-07-permission-prompt.md`](../../reviews/control-checks/2026-11-07-permission-prompt.md)). The service
   refuses when the input doesn't match what would happen: an attachment whose hash changed, a message reference
   whose sender, subject or date don't match, a held Chrome request whose site, address or data differ.
2. **Exact references.** Every result names what it refers to, and later actions use those references. A mail
   message is `account / folder / UIDVALIDITY / UID` plus its Message-ID; when the folder's UIDVALIDITY changed, the
   reference fails with "stale, search again" instead of pointing at another mail. Chrome references are bound to
   tab, document and element (section 6).
3. **Honest outcomes.** `done`, `refused` (with the reason), `failed` (nothing happened), or `unknown` (it may have
   happened). An `unknown` is never retried automatically; the result says how to check (for a mail: whether it
   reached the Sent folder or the recipient's reply arrives).
4. **Once only.** Every send and delete carries a `request_id`. The action log refuses a second run of the same
   `request_id`, also after a restart.
5. **Reading changes nothing.** Mail is fetched with `BODY.PEEK`; flags are compared before and after in the tests.
6. **Readable, bounded results.** Compact structured results with the important fields first. Long content is paged
   (`cursor`), and every result has a size cap, so a huge mail or page never floods Claude's context.
7. **Errors say what to do next.** Not "IMAP error 3", but "the folder was recreated; search again".
8. **Content is data, never instructions.** Text from mails and pages comes back in fields marked as untrusted
   content, and the tool descriptions tell Claude that. Whatever a mail says, any send or delete still asks.
9. **Everything that changes something is logged.** Time, action, input summary, outcome. `aresos log` shows the
   owner what Claude did today.

## 5. Mail

**Accounts:** one account to begin with, the owner's (IMAP over TLS, SMTP submission over TLS, password). Several
accounts work the same way through configuration. The provider's details are kept privately, outside this repo; the
adapter checks the server's capabilities and refuses features the server lacks instead of guessing.

**Actions:**

| Action | Effect | Input | Result |
|---|---|---|---|
| `mail_accounts` | read | | accounts, with their special folders (Inbox, Sent, Drafts, Trash, Junk, Archive) |
| `mail_folders` | read | account | folders with total and unread counts |
| `mail_search` | read | account, folders (default: all but Trash and Junk), from, to, subject, text, since, before, unread, flagged, answered, has attachment, limit, cursor | message summaries: reference, date, from, to, subject, flags, size, attachment names, a short preview |
| `mail_read` | read | reference, which part, offset | headers, the text (HTML turned into readable text with links kept), attachments (part, file name, type, size, sha256), the thread reference |
| `mail_thread` | read | reference | the conversation in order, across Inbox and Sent, built from Message-ID, In-Reply-To and References |
| `mail_attachment_save` | change | reference, part, folder (default `~/Downloads`) | saved path and sha256. Saving never opens or runs the file. |
| `mail_compose` | read | new mail, or `reply` / `reply_all` / `forward` to a reference, plus text and attachments | the complete mail exactly as it would go out: from, to, cc, bcc, subject, the quoted text, attachments with sha256, In-Reply-To. Nothing is stored or sent. |
| `mail_draft_save` | change | a complete mail | the draft's reference in Drafts |
| `mail_send` | **send** | a complete mail (account, from, to, cc, bcc, subject, text, attachments with path or source part and sha256, the replied-to reference), `request_id` | the outcome; on success the Message-ID, the copy saved in Sent, and the replied-to mail marked as answered |
| `mail_move` | change | references, target folder | the new references |
| `mail_flag` | change | references, flags to add or remove (read, flagged, answered) | the new flags |
| `mail_folder_create`, `mail_folder_rename` | change | account, name | the folder |
| `mail_delete` | **delete** | items, each `{reference, from, subject, date}`; to the Trash or for good; `request_id` | the outcome per item |
| `mail_folder_delete` | **delete** | account, folder, its message count | the outcome |

How each one works:

- **Reply and forward** go through `mail_compose`, which returns the whole mail; Claude passes that to `mail_send`.
  So the owner's prompt always shows the final recipients, subject, text and attachments, never a short reference.
- **Sending:** SMTP submission; when the server accepts, the service appends a copy to Sent (the provider doesn't do
  that itself) and marks the replied-to mail as answered. A lost server answer gives `unknown` and no retry.
- **Deleting for good** uses `UID EXPUNGE` on exactly the named messages, and is refused on a server without
  `UIDPLUS` (a plain `EXPUNGE` could remove other messages). To the Trash uses `MOVE`.
- **Text:** HTML mails are turned into readable text with links kept; character sets and encoded headers are
  decoded; German umlauts survive both ways. Outgoing mail is plain UTF-8 text with the usual quoting. HTML
  formatting for outgoing mail is an open question (section 10).
- **Transport security:** TLS with a verified certificate on both IMAP and SMTP, no plaintext fallback, and the
  password is only sent after the certificate check.
- **Passwords:** set once by the owner with an owner-only command (`aresos mail account add`), stored in a file only
  `aresos-tools` can read. A missing or unreadable password stops with a clear error; there is no other source.

**Tests (container, no real account):** a pinned GreenMail container with synthetic accounts and outside delivery
blocked. Fixtures: threads across Inbox and Sent, HTML and plain mails, attachments (PDF, image, a file named like a
program), Unicode in names and subjects, a large folder for paging, and a folder recreated with a new UIDVALIDITY.
Checks: flags unchanged after every read action; a send arrives exactly once, with the right recipients including
Bcc, the attachments byte for byte, the Sent copy and the answered flag; a dropped final SMTP answer gives `unknown`
and no second send; a stale reference fails; a changed attachment is refused; a certificate mismatch fails before the
password is sent.

## 6. Chrome

To be written after brief 17. The plan so far, so that names can be fixed:

- Claude works in the owner's own Chrome and own tabs. The tools keep to the tab they were given, even when the
  owner switches tabs.
- Reading (`chrome_tabs`, `chrome_read`) returns the page as structure: elements with references, roles,
  labels, values, states and positions, plus the visible text, paged when large.
- Acting (`chrome_navigate`, `chrome_click`, `chrome_fill`, `chrome_select`, `chrome_press`, `chrome_scroll`,
  `chrome_upload`) is free, except that anything a site would receive because of the action is held.
- A held request becomes `chrome_submit` (**send**, asks) with the site, address, method and data in its input, or
  `chrome_submit_trusted` (**send**, free) which the service refuses unless the site is on the owner's trusted list.
  `chrome_drop` lets it go nowhere.
- Brief 17 answers: the attach route, the page-view format, the rule that tells a real send from background
  traffic, and what can't be held (for example chat messages over a WebSocket).

## 7. No way around the tools

The settings are written after the tools exist (owner decision 3), but the design needs these things from them:

- Send and delete actions in the **ask** list; read and change actions free.
- Rules only from the system-wide file (`allowManagedPermissionRulesOnly`), MCP servers only from it
  (`allowManagedMcpServersOnly`), hooks only from it (`allowManagedHooksOnly`).
- The **sandbox** forced on for Claude's terminal commands (`enabled`, `failIfUnavailable`,
  `allowUnsandboxedCommands: false`), with `read.sock` as the only allowed tool socket, no access to the browser
  profile, the session's D-Bus or the keyring, and the network the owner allows.
- **Deny rules** for Claude's file tools on the browser profile and the tool service's files.
- Other browser routes off: Claude in Chrome, debugging ports.

**Hostile tests** (container first, then the AresOS image): a test Claude Code session, with these settings, is
told to send a mail or submit a form by every other route: a script talking SMTP, a script on `act.sock`, starting
`aresos-mcp` from the terminal, reading the password file, reading the browser's cookies, the keyring over D-Bus,
the Chrome control channel, editing its own settings, adding an MCP server. Every one must fail, and the mail
server and fixture sites must show nothing arrived.

Settings checks that belong to this list: the prompt's "Yes, and don't ask again" choice must not switch an ask off
under `allowManagedPermissionRulesOnly`, and a very long mail must still be shown in full (or refused) in the prompt.

## 8. Tests and evidence

1. **Container tests** per adapter on GitHub's Linux runners (free for this public repo): GreenMail for Mail, a
   fixture site and Chrome for Chrome.
2. **Hostile tests** (section 7).
3. **Tool-user rounds:** fresh Claude agents do the everyday tasks in `PLAN.md` against the fixtures and report where
   they got stuck, misread a result or needed too many calls. Those reports decide what "works really well" means.
4. **Qualification in the AresOS image** in the CI virtual machine, after `laptop-aresos` agrees the `os/ci/` change.
5. **Real use** after the first boot on the laptop.

## 9. The council's gaps, and where each is handled

| Gap (VERDICT) | Where |
|---|---|
| 1. Claude bypasses a tool through another route | sections 2 and 7: two sockets, sandbox, managed settings, hostile tests |
| 2. The agent manufactures or changes an approval | the approval is Claude Code's own prompt, which Claude can't answer; rule 4.1 makes the prompt show the exact action and refuses mismatches |
| 3. Retries, cancellation and restores send twice | rules 4.3 and 4.4: `unknown` is never retried; `request_id` once only; the log survives restarts. Restoring a backup must not revive old request ids: the log is never restored backwards (to check in brief 18). |
| 4. Harmless-looking actions change data | effects in section 3; `BODY.PEEK`; held Chrome requests; before/after comparisons in every test |
| 5. Data leaves without a send | content marked untrusted (4.8); the sandbox's network limits; open question on navigation in section 10 |
| 6. Browser debugging exposes the signed-in session | no debugging port on the owner's profile; route from brief 17 |
| 7. Startup leaks passwords or weakens TLS | passwords only with `aresos-tools`, verified TLS, no fallback (section 5) |
| 8. Acting on a stale or wrong target | rule 4.2; Chrome tab binding (section 6) |
| 9. Flatpak unavailable to the daily account | Chrome as a native package (brief 17, Q5) |
| 10. Graphical tools on the wrong session | Chrome bridge and session wiring checked in the image qualification |
| 11. CI success isn't AresOS integration | evidence kept separate: container, VM, laptop (section 8) |
| 12. Provider and dependency assumptions | capabilities checked at run time; pinned versions; the real account only after the first boot |
| 13. Works but unusable | the tool-user rounds; the terminal command works without Claude or network for local things (`aresos log`) |

## 10. Open questions

For the design review:

- **Data leaving through navigation.** Navigating is free (owner decision 2), but a misled Claude could open an
  address that carries private data in it (`https://example.invalid/?q=<mail text>`). Options: hold navigation to a
  typed address with a long query on a site the owner has never visited; or accept the risk and rely on the content
  rules. Needs a recommendation, and then the owner's call.
- **The sandbox and the rest of Claude's work.** Claude's terminal on AresOS is sandboxed for everything, not just
  for these tools: which network and folders it may reach decides how useful it is for other work. Needs a proposal
  for the settings step.
- **Language and libraries.** Proposed: Python 3 (already in the image), the standard library's `imaplib`,
  `smtplib` and `email` for Mail, the official MCP Python SDK pinned and shipped in the image. The Chrome side
  follows brief 17.

For the owner, later:

- Outgoing mail as plain text, or formatted (HTML) like Apple Mail.
- A signature, and anything else about how his mails should look (a habit for CLAUDE.md, not a tool rule).
