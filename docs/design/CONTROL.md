# The control layer: design

**Status:** draft, 2026-11-07. Covers the shared base, Mail and Chrome. Chrome rests on brief 17's check; the points
marked *17b* are checked next. A fresh Codex review (frontier model) checks this design before brief 18 is written.

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

Built on brief 17's check: branded Chrome stable 157 on GitHub's Linux machines, synthetic profile and fixture sites
([report](../../reviews/17-chrome-check/REPORT.md), PR #3). What the check showed is marked *checked*; what brief 17b
still has to show is marked *17b*.

### How the tool reaches Chrome

- **Our own small extension** (Manifest V3, using `chrome.debugger`), installed by the image through Chrome's managed
  policy, so it can't be removed or swapped from the profile. Chrome starts its **native messaging host**, registered
  system-wide under `/etc/opt/chrome/native-messaging-hosts/`; the host only relays between the extension and the
  service's `chrome.sock`. *Checked:* attaches to a tab that was opened and signed in before the tool started, with
  no debugging port and Chrome's sandbox on. `--load-extension` no longer works in branded Chrome; the policy install
  route is *17b*.
- **Rejected:** Chrome's own consent attach (`chrome://inspect`) opens a debugging listener on port 9222 that stays
  on after a restart (*checked*), against the owner's no-debugging-port rule. Playwright's bridge extension works,
  but any local program that finds its endpoint can drive the page (*checked*); our own extension keeps that channel
  inside the service.
- While Claude controls a tab, Chrome shows its "started debugging this browser" bar. Pressing Cancel there ends
  Claude's control at once (what that does to a held send: see "Fail closed").
- The host runs as the owner's user, like Chrome. A program running as the owner outside the sandbox could pretend
  to be it (*checked*); that is the desktop trust model of section 2. Claude can't, because its terminal is
  sandboxed and its file tools can't write the places that start programs (section 7).

### Which tabs Claude works in

Claude works in tabs in a tab group named **Claude**: tabs it opened itself (same profile, so the owner's sign-ins
work) and tabs of the owner's it took into the group (`chrome_take_tab`; the owner sees the tab move). It reads and
acts only inside the group. `chrome_tabs` lists every tab's title and address, so Claude can say what is open and
pick one. Every reference is bound to tab, document and element: when the owner switches or opens tabs, nothing is
redirected; when the page changes, an old reference fails with "stale, read again" instead of hitting another
element (*checked*).

### Reading a page

`chrome_read` returns a compact tree in the style of Playwright's AI snapshot, built from Chrome's accessibility tree
and layout: one line per element with a short reference (`e12`), role, label, value, states (checked, selected,
disabled, required, invalid, expanded) and its box in CSS pixels with whether it is on screen; frames (also from
other sites) and open shadow DOM included; elements behind an open dialog left out. A header names the tab, the
document, the address, the title, the scroll position and anything held. Measured (*checked*): a long form about
1,300 tokens, a long article about 15,000; views are paged at about 16,000 characters with a cursor bound to the
document, and `chrome_find` searches a long page for text. Page text is untrusted content (rule 4.8).

### Actions

| Action | Effect | What it does |
|---|---|---|
| `chrome_tabs` | read | all tabs: title, address, whether in the Claude group |
| `chrome_take_tab`, `chrome_release_tab` | change | move one of the owner's tabs into or out of the Claude group |
| `chrome_open` | change | open an address in a new tab in the Claude group |
| `chrome_read`, `chrome_find` | read | the page view; text search on the page |
| `chrome_navigate` | change | in a Claude tab: an address, back, forward, reload |
| `chrome_click`, `chrome_fill`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll` | change | act on an element by reference; fill sets text, dates and dropdowns as a person would |
| `chrome_upload` | change | put a local file (path and sha256) into a file field; the tool hands over the bytes, the extension gets no general file access (*checked*) |
| `chrome_wait` | read | wait for text, an element or the page to settle |
| `chrome_pending` | read | what is held in a tab |
| `chrome_submit` | **send** | let one held send go, with its whole content in the input |
| `chrome_submit_input` | **send** | on a page the tool can't hold (below): type and press as one step, after approval |
| `chrome_submit_trusted` | send, free | as `chrome_submit`, refused unless the site is on the owner's trusted list |
| `chrome_drop` | change | drop a held send; nothing leaves |
| `chrome_sites` | owner-only | the owner's lists of known and trusted sites |

Every acting result says what happened (new page, dialog, download), the elements that changed, and anything held.
While a tab has something held, it accepts only reading, `chrome_submit…` and `chrome_drop`.

### What counts as sending, and how it is held

The service holds every request the tab makes at Chrome's request stage, before it leaves the browser, and decides
whether it is a send:

1. **During an action**, until the page settles (no new requests for half a second, at most ten seconds): any
   method other than GET, HEAD or OPTIONS; a form submission (a search form on a known site counts as reading if the
   owner takes the known-sites rule); a beacon, ping or report; opening a WebSocket; or a request that carries text
   Claude typed into the page, except as part of such a search.
2. **At any time** while the tab is controlled: a request that carries text Claude typed into the page and that the
   owner hasn't approved, whenever it leaves (autosave after a pause, an "undo send" delay). Typed text is matched
   as typed and in the usual encodings (URL, form, JSON, base64).
3. **A page opening on a site that isn't known**, by any cause: an address Claude typed, a link, a redirect, a script.
   (The known-sites rule is an open owner question; section 10.)
4. Everything else goes: pages, images, scripts, data a page loads to show something, and background traffic that
   carries none of Claude's text.

A send stops the action; its result reads `held`, with a hold id, the site, the full address, the method, the data
(decoded where possible, raw bytes' hash always), and what caused it (for example the click on "Send" in a form,
with the form's visible fields). Claude passes exactly that to `chrome_submit`, and the owner's prompt shows it. The
service refuses when anything differs from the held request, and releases it once. *Checked:* held sends reached the
fixture server zero times while held, exactly once after release and never after drop, for posted forms, search
forms, `fetch` and XHR posts, beacons, autosave, a form posting to another site, link pings and a data-bearing image.

Outcomes: the site answered (`done`, with its status), the page gave up waiting or the tab closed (`failed`, nothing
was sent), or the connection broke after release (`unknown`). How long a held send survives while the owner answers
on the phone, and what common pages do meanwhile, is *17b*.

### What can't be held, and what happens there

- **Live connections** (WebSocket, WebTransport, WebRTC): Chrome's request hold doesn't see their messages
  (*checked* for WebSocket). On a page with such a connection open, the tool can't know what a key or click sends.
  There, typing, Enter and clicks other than plain links go through `chrome_submit_input`: one asking step that shows
  the site, the field, the text and the key, done only after approval. *Checked:* holding the key press gave zero
  arrivals until approval and exactly one after.
- **Service workers:** requests a site's service worker sends were not held (*checked*), and requests a page sends
  through its service worker may be invisible to the tab's hold. *17b:* hold at the worker itself, and let the
  controlled tab bypass its service worker. Until that passes, a page under a service worker counts as a live-
  connection page.
- **A site that hides what it sends** (encrypts typed text, sends it later in another form, or changes something with
  a plain GET) can get past rules 1 and 2. That is acceptable only on sites the owner chose to use with Claude; rule 3
  is what keeps Claude off other sites without asking.

### Fail closed

A held send must never go out because control broke. *Checked:* when the controller disconnected, Chrome let the
held request go, on all three routes. Required: the extension keeps holding and drops what it held when the service
or the host goes away; a held send outlives neither its page nor a time limit (then it is dropped, never sent); and
for the ways control ends that the extension doesn't choose (Cancel on the bar, DevTools opened, the extension
updated or crashed, Chrome closed), *17b* tests a backstop that blocks the held request first. If no backstop holds,
the fallback is "fail, then repeat": the request is stopped and failed at once, and after approval the action is done
again and only the matching request goes out. The Chrome part isn't finished until one of the two passes.

### Tests

The fixture sites and runner from brief 17, extended with brief 17b's cases and the everyday tasks in `PLAN.md`
(Chrome tasks 8 to 14), on GitHub's Linux machines with branded Chrome. Hostile tests (section 7) add: reaching
`chrome.sock` or the host from the sandbox, a user-level native messaging manifest, editing the profile or Chrome's
policies, and acting in a tab outside the Claude group.

## 7. No way around the tools

The settings are written after the tools exist (owner decision 3), but the design needs these things from them:

- Send and delete actions in the **ask** list; read and change actions free.
- Rules only from the system-wide file (`allowManagedPermissionRulesOnly`), MCP servers only from it
  (`allowManagedMcpServersOnly`), hooks only from it (`allowManagedHooksOnly`).
- The **sandbox** forced on for Claude's terminal commands (`enabled`, `failIfUnavailable`,
  `allowUnsandboxedCommands: false`), with `read.sock` as the only allowed tool socket, no access to the browser
  profile, the session's D-Bus or the keyring, and the network the owner allows.
- **Claude's file tools** (Read, Edit, Write) run outside the sandbox, as the owner's user. A file that the owner's
  session later runs would carry Claude's code out of the sandbox: shell startup files, autostart entries, systemd
  user units, desktop files, a user-level native messaging manifest, git hooks, Claude Code's own configuration.
  Writes must stay inside named work folders. Two ways: deny rules on each such place (a list that can miss one), or
  running without skip-permissions so that every write outside the work folders asks (stronger, more prompts). Chosen
  in the settings step; the hostile tests write each of these places.
- **Deny rules** for Claude's file tools on the browser profile, Chrome's policies and the tool service's files.
- Other browser routes off: Claude in Chrome (blocked by Chrome policy), debugging ports.

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
| 5. Data leaves without a send | content marked untrusted (4.8); Chrome's typed-text and known-sites rules (section 6); the sandbox's network limits; owner question in section 10 |
| 6. Browser debugging exposes the signed-in session | our own policy-installed extension and native host, no debugging port, Chrome's consent attach rejected (section 6) |
| 7. Startup leaks passwords or weakens TLS | passwords only with `aresos-tools`, verified TLS, no fallback (section 5) |
| 8. Acting on a stale or wrong target | rule 4.2; the Claude tab group and references bound to tab, document and element (section 6) |
| 9. Flatpak unavailable to the daily account | Chrome as a native package (brief 17, Q5) |
| 10. Graphical tools on the wrong session | Chrome bridge and session wiring checked in the image qualification |
| 11. CI success isn't AresOS integration | evidence kept separate: container, VM, laptop (section 8) |
| 12. Provider and dependency assumptions | capabilities checked at run time; pinned versions; the real account only after the first boot |
| 13. Works but unusable | the tool-user rounds; the terminal command works without Claude or network for local things (`aresos log`) |

## 10. Open questions

For the design review:

- **Data leaving through links and typing (asked of the owner 2026-11-07).** Following links and typing are free
  (owner decision 2), but a misled Claude could open an address that carries private text in it, or type that text
  into a site whose own code sends it in a way the tool can't recognise. Recommendation: **known sites.** Claude
  opens, reads, types and searches freely on sites already used with it; the first page on a new site is held and
  asks once, showing the full address, and an approved site becomes known. Sends still ask everywhere except trusted
  sites. Searches (GET forms) on known sites count as reading, since opening an address with a query there is free
  anyway. The other way is keeping links and typing free everywhere and relying on Claude's judgement and the
  untrusted-content rule. The same question applies to Claude Code's `WebFetch` and the sandbox's network
  allowance, in the settings step.
- **The sandbox and the rest of Claude's work.** Claude's terminal on AresOS is sandboxed for everything, not just
  for these tools: which network and folders it may reach decides how useful it is for other work. Needs a proposal
  for the settings step.
- **Language and libraries.** Proposed: Python 3 (already in the image), the standard library's `imaplib`,
  `smtplib` and `email` for Mail, the official MCP Python SDK pinned and shipped in the image. Chrome: the extension
  in JavaScript (required), the native host a small Python relay, and the page view and hold rules in the Python
  service, talking DevTools protocol through the extension (brief 17's Node code is the reference to port).

For the owner, later:

- Outgoing mail as plain text, or formatted (HTML) like Apple Mail.
- A signature, and anything else about how his mails should look (a habit for CLAUDE.md, not a tool rule).
