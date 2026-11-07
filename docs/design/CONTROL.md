# The control layer: design

**Status:** draft 4, 2026-11-07. Covers the shared base, Mail and Chrome. Revised after the frontier review
([`2026-11-07-REVIEW.md`](../../reviews/control-design/2026-11-07-REVIEW.md), 8 blocking findings) and its re-check
and re-checks ([`RECHECK`](../../reviews/control-design/2026-11-07-RECHECK.md),
[`RECHECK-2`](../../reviews/control-design/2026-11-07-RECHECK-2.md)); the same reviewer checks draft 4 before brief
18 starts. Chrome rests on brief 17's check; points marked *17b* and
*17c* are checked next.

The plan, the owner's decisions and who does what: [`docs/control/PLAN.md`](../control/PLAN.md). The owner's
picture: [`OWNER-SCOPE.md`](../../reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md). The council's 13 gaps
([`VERDICT.md`](../../reviews/councils/2026-11-07-control-layer/VERDICT.md)) are the checklist; section 9 maps each
one to where it is handled.

## 1. In one paragraph

A tool service runs under its own system user, holds the passwords, and does the work for every app. Each action is
defined once, with what it does to the world (its *effect*), and from that one definition come the MCP tools Claude
calls, the `aresos` terminal command, and the list of actions that must ask the owner. Claude Code asks the owner
before any action whose effect is sending or deleting; Claude's own terminal commands run in Claude Code's sandbox and
can't reach the service at all, so Claude acts on apps only through the MCP tools. Every send and delete is recorded
as an operation before it acts, and every result says exactly what it refers to and what really happened.

## 2. The pieces

| Piece | What it is | Runs as |
|---|---|---|
| `aresos-toold` | The tool service: app adapters (Mail, Chrome, later more), passwords, the operation log. Listens on three Unix sockets and nothing else (no TCP). | system user `aresos-tools` |
| `act.sock` | `/run/aresos-tools/act.sock`: every action that may be offered to Claude. Open to the owner's user. | |
| `admin.sock` | owner-only actions (accounts, passwords, the site lists). Open only to root; the owner reaches it with `sudo aresos admin …` and his own password, which Claude can't give. | |
| `chrome.sock` | for Chrome's native messaging host only (section 6). | |
| `aresos` | The terminal command: `aresos mail search --from … --json`, generated from the definitions, over `act.sock`. For the owner and his scripts. | the caller |
| `aresos-mcp <app>` | One MCP server per app (`aresos-mcp mail`, `aresos-mcp chrome`), a thin generic proxy: it fetches its app's tool list from the service, forwards calls over `act.sock`, and does the caller's side of file transfers (rule 4.4). Root-owned under `/usr` (read-only in the image), started from `managed-mcp.json` with a fixed interpreter in isolated mode (`python3 -I`) and a fixed environment, so nothing in a writable folder is loaded into it. | the owner's user, started by Claude Code |
| Chrome bridge | Our own extension and native messaging host (section 6). | |
| Claude Code settings | `/etc/claude-code/managed-settings.json` and `managed-mcp.json`, owned by root (section 7). Exact values come once the tools exist (owner decision 3). | |

**Who can reach what:**

| From | `act.sock` | `admin.sock` | Passwords and sign-in data | Chrome's control channel |
|---|---|---|---|---|
| The owner's own terminal | yes | with `sudo` | no | only through the tools |
| Claude through its MCP tools (local MCP servers run outside the sandbox) | yes; send and delete ask first | no | no | only through the tools |
| Claude's terminal commands (sandboxed) | no | no | no | no |
| Claude's file tools (Read, Edit, Write; outside the sandbox) | no (they don't open sockets) | no | no: another user's files, plus deny rules | no |
| `aresos-toold` | | | yes | yes |

**Why Claude's terminal reaches no socket.** On Linux, Claude Code's sandbox can't let one Unix socket through and
block another: `allowUnixSockets` is ignored there, and the only switch, `allowAllUnixSockets`, opens every socket
(Anthropic's settings reference, read 2026-11-07). So the sandbox allows none, and Claude reads apps through the MCP
tools too. Two layers keep it so: the seccomp filter that blocks Unix sockets (`allowAllUnixSockets: false`), and
`/run/aresos-tools` hidden from the sandbox's file view. The seccomp filter is an optional dependency and the
sandbox starts without it, so the image ships it, the image qualification checks it, and the hostile tests run with
and without it.

A program that runs as the owner outside the sandbox can use `act.sock` without asking. That is the normal desktop
trust model (such a program could also type into Chrome); the line this design draws is around Claude, and section 7
lists every way Claude could start such a program and how each is closed.

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
  - **delete:** removes something, to the Trash or for good. Moving to the Trash is deleting.
- **Input and result schemas**, and a **description written for Claude**: what it does, when to use it, what it
  returns, its effect, and what to do on each error.
- **owner-only** (optional): actions that are never offered to Claude, such as account setup or the list of trusted
  sites. They exist only in the terminal command, over `admin.sock` with `sudo`; `act.sock` refuses them.

Generated from the definitions: the MCP tool lists, the terminal command with its `--help`, a reference page
(`docs/control/TOOLS.md`), and the list of send and delete actions for the settings. A test fails if any send or
delete action is missing from the settings' ask list, so the two can't drift apart.

Default settings (exact values later, owner decision 3): send and delete ask; read and change are free. One action
has one effect: when an action could do two things (for example compose a reply and save it as a draft), it becomes
two actions.

## 4. Rules every action follows

1. **The asking input tells the whole truth.** A send or delete action carries in its own input what the owner
   needs to decide, because the prompt shows exactly that input (checked in the terminal:
   [`2026-11-07-permission-prompt.md`](../../reviews/control-checks/2026-11-07-permission-prompt.md); the phone
   through Remote Control is checked with the owner on the fake app in brief 18). In detail:
   - **The operation, as the service describes it**, not as Claude does: the action, the account, every recipient or
     target, and what is affected (for a deletion each item's sender, subject and date; for a site the page's own
     title, signed-in name and the item's label as the page shows them, marked as such).
   - **Everything Claude wrote, in full.** Parts the service builds itself from existing data (a quoted thread, a
     forwarded attachment) appear by reference with their size and hash; Claude can't change them.
   - The service **binds the approval to the state it describes** and refuses when anything differs at run time: an
     attachment whose bytes changed, a message whose sender, subject or date don't match, a folder whose contents
     changed, a held request whose bytes differ, a page whose address, title or conversation changed.
   - Control and direction-changing characters are shown escaped, and an input too large to be shown whole in the
     prompt is refused, never cut.
2. **Exact references.** Every result names what it refers to, and later actions use those references. A mail
   message is `account / folder / UIDVALIDITY / UID` plus its Message-ID; when the folder's UIDVALIDITY changed, the
   reference fails with "stale, search again" instead of pointing at another mail. Chrome references are bound to
   the browser session, tab, document, view and element (section 6).
3. **Operations are recorded before they act.** Every send and delete is an *operation* in the service's durable log:
   - It is **reserved** with its id and the hash of its exact input before any irreversible step. The same id again
     returns the existing operation and its status; it never runs twice, also after a restart.
   - **Each stage is recorded** as it happens: for a mail, the submission per recipient, the Sent copy, the answered
     flag; for a site, release, the site's answer.
   - **Outcomes:** `done`; `partial` (with what happened per stage and recipient); `refused` (with the reason);
     `failed` (nothing left the machine); `unknown` (it may have happened: a lost server answer, a crash after the
     submission). Nothing is ever retried by itself. `<app>_operation_status` shows an operation; repairs (save the
     missing Sent copy, set the missing flag) are their own actions and never submit again.
   - **States and cancelling:** `reserved` → `submitting` → `done`, `partial`, `failed` or `unknown`. An operation
     can be cancelled or expire only while `reserved` (then it is `failed`: nothing left); once `submitting` has been
     recorded it runs to an outcome. An approval waiting longer than its limit expires.
   - **Restarts and restores:** nothing resumes by itself after a restart; an operation found `submitting` becomes
     `unknown`. Operation ids are issued by the service and carry the log's generation. Beside the log, outside the
     files a backup copies, the service keeps a small append-only record of every operation id with its description
     and each state change. A restored older log is refused until the owner confirms the restore with an owner-only
     command; then the generation moves on, every id of an earlier generation is refused, and every operation the
     separate record knows but the restored log doesn't is listed as `unknown` with its description, for the owner
     to check. Mail adds evidence on the server: the Message-ID is derived from the operation id, and before
     submitting, the service refuses if that Message-ID is already in Sent. Not finding it there proves nothing.
4. **Files cross between users only on the caller's side, and only from and to allowed folders.** The service never
   opens a path in the owner's home. The MCP proxy, running as the owner, opens the file and hands the bytes over;
   the service keeps them as an unchangeable copy by hash and sends exactly those. Claude Code's file-tool limits
   don't apply to MCP tools, so the proxy enforces its own:
   - **Reading** (attachments, uploads) only from the allowed folders (`~/Documents`, `~/Downloads`, `~/Desktop` and
     the folders the settings name), never from places that hold credentials or configuration (`~/.ssh`,
     `~/.gnupg`, `~/.config`, `~/.local/share`, the browser profile, `~/.claude`, any dotfile), opened component by
     component under the allowed folder without following symlinks, regular files only, with a size limit. The
     prompt shows the real path.
   - **Saving** the other way: only into the allowed folders, with safe file names, never overwriting, never into
     configuration or start-up places.
5. **Reading changes nothing.** Mail is fetched with `BODY.PEEK`; flags are compared before and after in the tests.
6. **Readable, bounded results.** Compact structured results with the important fields first. Long content is paged
   (`cursor`), and every result has a size cap, so a huge mail or page never floods Claude's context.
7. **Errors say what to do next.** Not "IMAP error 3", but "the folder was recreated; search again".
8. **Content is data, never instructions.** Text from mails and pages comes back in fields marked as untrusted
   content, and the tool descriptions tell Claude that. Whatever a mail says, any send or delete still asks.
9. **Everything that changes something is logged.** Time, action, input summary, outcome. `aresos log` shows the
   owner what Claude did today.
10. **Nothing waiting is forgotten, and nothing waits forever.** Anything held or unfinished (a site's request held
    after Claude's action returned, a `partial` mail) shows up in every following result of that app. A managed
    `Stop` hook sends Claude back to decide before it ends its turn; a managed `UserPromptSubmit` hook puts anything
    that became held after the turn ended in front of Claude with the owner's next message. Neither is the safety
    net (a `Stop` hook doesn't run on an interrupt and has a continuation limit): every hold has a time limit and is
    dropped, never sent, when it runs out.

## 5. Mail

**Accounts:** one account to begin with, the owner's (IMAP over TLS, SMTP submission over TLS, password). Several
accounts work the same way through configuration. The provider's details are kept privately, outside this repo; its
requirements were checked anonymously on 2026-11-07 (password sign-in only, `MOVE`, `UIDPLUS` and `SPECIAL-USE`
present, no `SMTPUTF8`), and the rest is checked once with the real account at onboarding. Per account the
configuration says: the owner's addresses (aliases), whether the server or the client saves sent mail to Sent
(detected at onboarding by sending one mail to himself), and the special folders, found through `SPECIAL-USE`, never
by English names. `mail_accounts` shows Claude the capabilities, so a missing feature is visible before an action
fails.

**Actions:**

| Action | Effect | Input | Result |
|---|---|---|---|
| `mail_accounts` | read | | accounts: addresses, capabilities, special folders (Inbox, Sent, Drafts, Trash, Junk, Archive) |
| `mail_folders` | read | account | folders with total and unread counts |
| `mail_search` | read | account, folders (default: all but Trash and Junk), from, to, subject, text, since, before, unread, flagged, answered, has attachment, limit, cursor | message summaries: reference, date, from, to, subject, flags, size, attachment names, a short preview |
| `mail_read` | read | reference, which part (or `source`), offset | headers, the text (HTML turned into readable text with links kept), attachments (part, file name, type, size, sha256), the thread reference |
| `mail_thread` | read | reference | the conversation in order, across all folders but Trash and Junk |
| `mail_attachment_save` | change | reference, part (or the whole mail as `.eml`), folder (an allowed folder, default `~/Downloads`) | saved path and sha256; never overwrites, never opens or runs the file |
| `mail_contacts` | read | text | addresses the owner has written to or received from, with names |
| `mail_compose` | change | new mail, or `reply` / `reply_all` / `forward` to a reference, or an existing draft to send or change; text (plain or formatted); attachments (local files or parts of other mails) | a *composition* kept by the service: its id, hash and the whole mail as it would go out (from, to, cc, bcc, subject, text, quoted part by reference, attachments with sha256, threading headers). Nothing is sent. |
| `mail_draft_save` | change | a composition, optionally replacing an existing draft | the draft's reference in Drafts |
| `mail_send` | **send** | the composition's id and hash, account, from, to, cc, bcc, subject, Claude's own text in full, the quoted and forwarded parts by reference, attachments by name, size and sha256, `request_id` | the operation's outcome per recipient and stage (rule 4.3): Message-ID, Sent copy, answered flag |
| `mail_move`, `mail_copy` | change | references, target folder (never Trash: that is `mail_delete`) | the new references |
| `mail_flag` | change | references, flags and keywords to add or remove (read, flagged, answered, the owner's own keywords) | the new flags |
| `mail_folder_create`, `mail_folder_rename` | change | account, name | the folder |
| `mail_delete` | **delete** | items, each `{reference, from, subject, date}`; to the Trash or for good; `request_id` | the outcome per item |
| `mail_folder_delete` | **delete** | account, folder (must be empty and without subfolders; only where the server refuses deleting a folder that holds mail) | the outcome |
| `mail_operation_status`, `mail_operation_repair` | read, change | operation id; for repair which stage (Sent copy, flag) | the operation's stages; a repair never submits again |
| `mail_unsubscribe` | **send** | reference, and the unsubscribe address or mail the message's own header names, `request_id` | the outcome |

How each one works:

- **Compose, then send.** `mail_compose` builds the whole mail in the service; `mail_send` names it by id and hash
  and repeats everything the owner must see, with Claude's own text in full. The service sends exactly the stored
  composition and refuses if the input doesn't match it. A long quoted thread therefore never has to pass through
  Claude, and still can't be altered.
- **Replies** use Reply-To where set, never address the owner's own addresses (reply-all removes them), and build
  In-Reply-To and References from the original. A reply to the owner's own sent mail goes to that mail's original
  To and Cc, as Apple Mail does. Bcc recipients never appear in the headers that others receive.
- **Threads** are built from Message-ID, In-Reply-To and References. A mail without a Message-ID gets an internal id
  (account, folder, UIDVALIDITY, UID) that is never put into outgoing headers; a reply to it has no In-Reply-To.
  Mails sharing one Message-ID are all kept, ordered by date and marked as duplicates.
- **Formatted mail:** the owner's mails can be plain or formatted (HTML with a plain-text part); which is the default,
  and the signature, are the owner's habits (section 10). Incoming HTML is turned into readable text with links kept.
- **Sending:** SMTP submission over TLS. The server's answer per recipient is recorded: some accepted and some refused
  is `partial`, never `done`. Then the Sent copy (only where the client must save it) and the answered flag, each
  recorded as its own stage; a failed stage is repaired with `mail_operation_repair`, never by sending again. A lost
  server answer is `unknown`.
- **Encoding:** MIME with a plain-text part (and an HTML part when formatted), quoted-printable or base64,
  encoded-word headers, encoded attachment names, CRLF line ends. Hashes are over the decoded bytes. A non-ASCII
  address part is refused clearly, because the server has no `SMTPUTF8`; non-ASCII domains are converted.
- **Deleting for good** uses `UID EXPUNGE` on exactly the named messages, and is refused on a server without
  `UIDPLUS`. The service never calls IMAP `CLOSE` on a mailbox it may write to (that can remove other messages marked
  deleted); it uses `UNSELECT`. To the Trash uses `MOVE`.
- **Deleting a folder** works only on an empty folder without subfolders; its mails are deleted first with
  `mail_delete` (exact messages, asking). IMAP's `DELETE` removes whatever is in the folder at that moment and has no
  "only if empty", so `mail_folder_delete` is offered only on a server shown at onboarding to refuse deleting a
  folder that holds mail. On any other server it is refused, `FEATURES.md` says so, and the owner deletes the empty
  folder in his mail program.
- **Transport security:** both connections use an explicitly verifying TLS context (Python's `IMAP4_SSL` doesn't
  verify by default), with hostname checking and no plaintext fallback. The password is sent only after the check.
- **Passwords:** set once by the owner with an owner-only command (`aresos mail account add`), stored in a file only
  `aresos-tools` can read. A missing or unreadable password stops with a clear error; there is no other source.

**Tests (container, no real account):** a pinned GreenMail container with synthetic accounts and outside delivery
blocked, plus a small scripted SMTP server for failures GreenMail can't produce. Fixtures: threads across folders
(one part archived), missing and duplicate Message-IDs, a mailing list with Reply-To, a reply to the owner's own sent
mail, aliases, HTML and plain mails, nested forwarded mails, attachments (PDF, image, a file named like a program,
non-ASCII names), non-UTF-8 mails, a large folder for paging, and a folder recreated with a new UIDVALIDITY. Checks:
flags unchanged after every read action; a send arrives exactly once, with the right recipients and no Bcc header,
the attachments byte for byte, the Sent copy and the answered flag; one refused recipient gives `partial`; a failure
at each stage after submission is repaired without a second submission; a dropped final SMTP answer gives `unknown`;
a crash at each step of the operation log never sends twice; a stale reference fails; a changed attachment or
composition is refused; moving to Trash through `mail_move` is refused; deleting a folder that received a new mail
during approval is refused; messages already marked deleted survive; a certificate mismatch fails before the
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

Claude works in tabs in its own tab group, labelled **Claude**: tabs it opened itself (same profile, so the owner's
sign-ins work) and tabs of the owner's it took into the group (`chrome_take_tab`; the owner sees the tab move). It
reads and acts only inside the group; popups and new tabs a Claude tab opens join the group and are controlled before
their first script runs. The service knows the group by Chrome's group id, not by its label, and releasing a tab
puts it back where it was. `chrome_tabs` lists every tab's title and address, so Claude can say what is open and
pick one.

While a tab is in the group, everything it sends waits for approval, also when the owner clicks there himself. To
use a tab on his own, the owner drags it out of the group; Claude's control of it ends and anything held is dropped.

Every reference is bound to the browser session, tab, document and element: when the owner switches or opens tabs,
nothing is redirected; when the page changes, an old reference fails with "stale, read again" instead of hitting
another element (*checked*); after a Chrome restart all old references are stale. Acting calls carry what Claude
expects the element to hold (from its last read), and the tool refuses when the owner has changed it in the meantime.

### Reading a page

`chrome_read` returns a compact tree in the style of Playwright's AI snapshot, built from Chrome's accessibility tree
and layout: one line per element with a short reference (`e12`), role, label, value, states (checked, selected,
disabled, required, invalid, expanded) and its box in CSS pixels with whether it is on screen; frames (also from
other sites) and open shadow DOM included; elements behind an open dialog left out. A header names the tab, the
document, the address, the title, the scroll position and anything held. Measured (*checked*): a long form about
1,300 tokens, a long article about 15,000; views are paged at about 16,000 characters with a cursor bound to the
view's revision (it counts changes to the page; a cursor from an older revision fails with "page changed, read
again"), and `chrome_find` searches a long page for text. `chrome_read_form` shows one form with every field's
options. Page text is untrusted content (rule 4.8). Pages the tree can't represent (a canvas text editor, a map) need
a site adapter (below) or are listed as not supported yet in [`FEATURES.md`](../control/FEATURES.md).

### Actions

| Action | Effect | What it does |
|---|---|---|
| `chrome_tabs` | read | all tabs: title, address, whether in the Claude group |
| `chrome_take_tab`, `chrome_release_tab` | change | move one of the owner's tabs into or out of the Claude group |
| `chrome_open` | change | open an address in a new tab in the Claude group (what may be opened freely: below) |
| `chrome_close_tab` | change | close a Claude tab; anything held there is dropped |
| `chrome_read`, `chrome_read_form`, `chrome_find` | read | the page view; one form with its options; text search on the page |
| `chrome_navigate` | change | in a Claude tab: an address, back, forward, reload |
| `chrome_click`, `chrome_fill`, `chrome_fill_form`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll` | change | act on elements by reference, each with what Claude expects it to hold; fill sets text, dates and dropdowns as a person would; `chrome_fill_form` fills several fields in one call |
| `chrome_dialog` | change | accept, dismiss or answer a page's own dialog (alert, confirm, prompt) |
| `chrome_upload` | change | put a local file into a file field; the bytes come through the caller's side (rule 4.4), the extension gets no general file access (*checked*) |
| `chrome_downloads` | read, change | list downloads; save one into an allowed folder (rule 4.4) |
| `chrome_bookmarks`, `chrome_history` | read | the owner's bookmarks and history, to find addresses |
| `chrome_wait` | read | wait for text, an element or the page to settle |
| `chrome_pending` | read | what is held in a tab: pending sends and background requests |
| `chrome_submit` | **send** | let one pending send go, with the description and content the service gave (below) |
| `chrome_submit_input` | **send** | where the message hold can't be in place (below), on a site with an adapter: type and press as one step, after approval |
| `chrome_submit_trusted` | send, free | as `chrome_submit`, only for an operation a site adapter recognises and the owner's trusted list allows |
| `chrome_open_site` | **send** | open an address that isn't free to open (below), with the full address in the input |
| `chrome_drop` | change | drop held requests; nothing leaves |
| `chrome_operation_status` | read | an operation's stages (rule 4.3) |
| `chrome_sites` | owner-only | the owner's lists of known and trusted sites |

Every acting result says what happened (new page, dialog, download), the elements that changed, and anything held.
While a tab has a pending send, it accepts only reading, `chrome_submit…` and `chrome_drop`; background holds
(below) don't block it.

### What leaves a Claude tab, and how it is held

The rule: **nothing Claude caused or entered leaves a Claude tab without approval, and when the tool can't tell, the
request is held, never let go.** The one exception is plain reading (below), which stays free so that pages load; a
hostile script on a site the owner uses could abuse it, and that is the owner's decision in section 10. The service
holds every request the tab and everything it started (frames, popups, workers) makes, at Chrome's request stage,
before it leaves the browser, and sorts it by cause and content, never by timing alone:

- **Caused by Claude: held as a pending send.** The tool follows each request's initiator, including the chain of
  timers, promises and callbacks behind it, back to its origin. A request that leads back to a click, key or other
  input Claude made is Claude's, however late it comes: a deletion scheduled twelve seconds after a click, an "undo
  send" delay, a retry of a dropped send. Requests caused by one action form one pending send, so a form that sends
  three requests asks once.
- **After Claude acted on a page: held, whoever caused it.** Once Claude has done more than read, scroll and follow
  plain links in a document (clicked a control, typed, chosen, ticked, uploaded), every request from that document
  and its site's other guarded contexts that isn't plain reading is held, whatever started it: the page may carry
  Claude's input or effect in any form, also through its own state (a queue filled by Claude's click and sent by a
  timer the page set when it loaded). Only requests caused by the owner's own input (input the tool didn't
  dispatch) pass. Any request anywhere that carries Claude's typed text (as typed or URL-, form-, JSON- or
  base64-encoded) is held too.
- **Plain reading goes:** GET or HEAD without a body and without Claude's text: pages, images, scripts, styles,
  fonts, the data a page loads to show something. Reading has to stay free, or no page would load. Which pages Claude
  may open at all is the next rule.
- **The page's own activity goes** only in a document Claude hasn't acted on: requests the page makes by itself
  (when it loads, on its own timers, after the owner's own clicks) that carry none of Claude's text.
- **Reading through POST.** Many apps load data with POST (GraphQL queries, Notion, Google's apps). A GraphQL request
  counts as reading only when its operation is written out in the request (not a stored or batched one), is a
  query, and its variables carry none of Claude's text; everything else about it is judged like any other request.
  Other apps need a site adapter to tell reading from sending. Without one, their requests after Claude acted are
  held, so working in those apps asks until their adapter exists. 17c measures how often that happens on everyday
  sites.
- **Unknown cause: held, in the background.** A request whose cause the tool can't establish is held and listed as
  *background* in `chrome_pending`. Background holds don't block the tab: Claude can keep reading and acting, drop
  them (free) or submit them (asks). Each is kept as its own request; only polling an adapter shows to be the same
  read repeated is merged. Known tracking addresses are dropped without being listed; every background hold expires
  and is dropped, and expired holds stay listed (with what they were) until Claude has seen them.
- **Dropping is final.** A page that retries a dropped send produces a new held request, marked as a retry; it never
  goes by itself.
- **One step at a time.** A request the page builds from the answer to an approved one is a new send and asks again,
  unless a site adapter defines the whole sequence as one operation and the approval covers all of it.

A pending send stops the action; its result reads `held` with the **service's description** (rule 4.1): what Claude
did (the click on "Delete" in the row "Invoice 42"), the page's address and title, the signed-in name the page shows
(all marked "as the page shows it"), and every held request: site, full address, method, the data decoded where
possible and the raw bytes' hash. Claude passes exactly that to `chrome_submit`, and the owner's prompt shows it.
Before release the service checks that the page, the element and the bytes are still the same, and releases each
request once. *Checked:* held sends reached the fixture server zero times while held, exactly once after release and
never after drop, for posted forms, search forms, `fetch` and XHR posts, beacons, autosave, a form posting to another
site, link pings and a data-bearing image. *17c:* tracing causes through timers, promises and workers, with no
request of Claude's ever counted as the page's own.

Outcomes follow rule 4.3: the site's answer is recorded but doesn't prove the business step worked (`done` means the
site accepted the request); the page gave up waiting or the tab closed before release is `failed`; the connection
broke after release is `unknown`. How long a held send survives while the owner answers on the phone, and what common
pages do meanwhile, is *17b*.

**What Claude may open freely, and data leaving.** A *site* is a registrable domain by the Public Suffix List
(including its private part, so every `*.github.io` page is its own site), and areas of big platforms where anyone
can publish (public forms, user pages) count as their own sites. Claude follows links on a page and opens addresses
it was given (by the owner, in a mail, from bookmarks or history) freely, on sites it has used before. These ask
first, with the full address shown (`chrome_open_site`): an address Claude composed itself (with a path or query of
its own), the first page on a new site, a redirect that lands on a site that isn't free to open, and anything on the
local network (the router, other devices, `localhost`). Whether a search on a site the owner uses is free or asks
is the owner's call (section 10). What remains even then: a hostile script on a site the owner uses can encode what
Claude types there and send it as plain reading traffic. Approving each typing would only accept that risk, not
prevent it; closing it would take refusing input on such sites or limiting where their pages may load from.

**Other tabs of the same site, and later.** A Claude tab can pass data or queued work to the owner's own tabs of the
same site through the browser's shared channels (a shared worker, a broadcast channel, storage) or keep it for later
(an offline outbox that retries after a restart). So once Claude has acted on a site, that site is *guarded*: its
other tabs and workers are attached, and what they send that isn't plain reading or caused by the owner's own input
is held like in a Claude tab, listed as background. The guard stays on across browser restarts (the extension keeps
the list) until every operation Claude started there is resolved and a set time has passed; the owner can end it
with an owner-only command. Where a context can't be guarded, the tool refuses to act on that site while it
exists.

**The trusted list** frees sends only through a site adapter: an entry names a site and operations its adapter
recognises (for example "post a message in a chat", "add to the basket"). Without an adapter nothing is free, because
methods and button labels don't say what a request does. Deleting and paying are never free. Pages that can approve
Claude's own actions or change its settings (claude.ai, the Anthropic console, Aresus, Chrome's settings, password
and extension pages) can't be opened in a Claude tab at all; that list is fixed in the image.

**Site adapters.** Where the generic rules aren't enough to judge or to work smoothly (a request with opaque ids, an
app that reads through POST, a chat on a live connection, a canvas editor), a small adapter for that site decodes its
requests into clear operations ("delete the repository X", "send to the conversation Y"), tells reading from
sending, and binds the approval to the operation. Adapters are written for the owner's usual sites first, after the
tool-user rounds show where they are needed.

### What can't be held, and what happens there

- **Live connections** (WebSocket, WebTransport, WebRTC): Chrome's request hold doesn't see their messages
  (*checked* for WebSocket). Many everyday signed-in sites keep one open only for live updates (GitHub, Gmail, Slack,
  Notion), so asking on every action there would make Chrome tedious. The hold therefore moves to the message: a
  small script the tool puts into every page, frame and worker before the site's own scripts run wraps the send
  functions (`WebSocket.send`, `RTCDataChannel.send`, WebTransport writers), and a message that counts as a send is
  held like a request. *Checked:* this held a WebSocket send on a page it was in from the start; it missed a page that
  was already loaded before the tool attached, and a socket opened in a worker. *17c:* workers caught before they
  start, which messages count as sends (those carrying Claude's typed text only, or every message during an action:
  measured on chat-like fixtures and public pages), and how many everyday sites keep such connections open.
- **Where the message hold can't be in place** (a tab taken from the owner whose connection was opened before the
  tool attached, until the page reloads; a page where the wrap provably fails), the tool can't see what a key or
  click sends. There, typing, Enter and clicks other than plain links are refused, unless a site adapter establishes
  the account, the conversation or target and the text: then `chrome_submit_input` does them as one asking step with
  that description, after re-checking it right before acting. Usually reloading the page brings the message hold
  back. *Checked:* holding the key press gave zero arrivals until approval and exactly one after.
- **Service workers:** requests a site's service worker sends were not held (*checked*), and requests a page sends
  through its service worker may be invisible to the tab's hold. *17b:* hold at the worker itself, and let the
  controlled tab bypass its service worker. Until that passes, a page under a service worker is treated like a page
  without the message hold.
- **A site that changes something with a plain GET** (against the web's rules, rare on reputable sites) can't be told
  from reading without knowing the site; and **a site that hides what it sends** (encrypts typed text before sending
  it) defeats the typed-text match, though its other requests after Claude typed are still held. Both are why new
  sites ask first and why site adapters exist.

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

Claude's terminal is sandboxed, but much of Claude Code runs outside the sandbox with the owner's full rights: the
file and web tools, hooks, local MCP servers, plugin monitors, LSP servers, the status line and `apiKeyHelper`
commands, and mods (Anthropic's sandboxing page, "What runs outside the sandbox", read 2026-11-07). Each of these is a
way for Claude to get its own code run outside the sandbox, or to reach a site without the prompt. The settings
(exact values later, owner decision 3) must close every one:

- **Asking:** send and delete actions in the `ask` list (explicit ask rules still ask in skip-permissions mode:
  checked); rules only from the managed file (`allowManagedPermissionRulesOnly`).
- **Programs Claude Code starts:**
  - MCP servers: exactly the set in `managed-mcp.json` (that also shuts out plugin servers and `--mcp-config`), and
    Claude in Chrome not among them. Each server is a root-owned program with a fixed interpreter, isolated mode and
    a fixed environment (section 2), so a writable file can't be loaded into it.
  - Hooks: only managed ones (`allowManagedHooksOnly`), each a root-owned program with the same fixed interpreter,
    isolated mode and environment as the MCP proxy.
  - Claude Code itself: the central session is the command-line Claude Code, started by a root-owned launcher with
    a fixed environment (nothing like `NODE_OPTIONS` that loads code into it), with no IDE, desktop-app, SDK or
    browser integration. SDK hooks and in-process MCP servers, which the managed switches still allow, therefore
    have no way in.
  - Plugins and mods: none (`strictKnownMarketplaces: []`, `disableSideloadFlags`, every plugin off in
    `enabledPlugins`); a check in brief 18 confirms that this also keeps out plugin LSP servers, monitors and mods,
    or finds the switch that does.
  - The status line and `apiKeyHelper`: none. The managed file sets neither, Claude's file tools refuse Claude
    Code's settings files and the sandbox can't write them (both checked by hostile tests), and brief 18b finds
    whether a managed key can force them off; if one is ever needed, it gets the same fixed, root-owned treatment as
    the MCP proxy.
- **Claude's file tools:** `blockWritesOutsideWorkingDirectories` (holds in every mode, also skip-permissions), with
  the working folders named in the settings. Inside them, deny rules for every place whose contents another program
  later runs as the owner: `.git/hooks`, `.git/config`, `.envrc`, `.claude/`, `.mcp.json`, editor task files. Reads:
  deny rules for the browser profile, Chrome's policies, Claude Code's own sign-in files, and the tool service's
  files (also another user's), or `blockReadsOutsideWorkingDirectories`, chosen with the owner (section 10).
  What remains is the owner himself running code Claude wrote in a work folder: that is ordinary development and is
  named here so it isn't mistaken for a closed route.
- **The sandbox:** forced on (`enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`); no Unix sockets
  (`allowAllUnixSockets: false` plus the seccomp filter, section 2); the browser profile, `/run/aresos-tools`, the
  keyring and Claude Code's sign-in files hidden from its file view; no session D-Bus.
- **The network:** in skip-permissions mode the sandbox lets the terminal reach any host unless the list is locked, so
  the list is locked (`allowManagedDomainsOnly`), and it contains only what the owner allows (section 10). `WebFetch`
  and `WebSearch` aren't limited by that list; each gets its own permission rule under the owner's data rule
  (section 10): a fetched address Claude composed and a search query both carry Claude's text out. How much network
  and which credentials the central session's terminal has at all is an owner question (section 10).
- **Approval surfaces:** Claude must never approve its own prompt. Pages that can (claude.ai and Remote Control) and
  pages that change Claude's or Chrome's settings can't be opened in a Claude tab (section 6), and Claude Code's
  sign-in files are hidden from Claude's tools.
- **Other browser routes:** Claude in Chrome blocked by Chrome policy; no debugging ports.

**Hostile tests**, in two kinds:

1. **Fixed hostile programs** run inside the same sandbox as Claude's terminal, with the same settings, in CI on
   every change (no model needed): connect to every socket, the native messaging host and the session buses; read the
   password files, the browser's cookies and Claude Code's sign-in; reach a host outside the list; write each place
   in the list above. Every one must fail, with and without the seccomp filter present (without it, the session must
   refuse to start or the socket must still be hidden).
2. **A test Claude Code session** with these settings, told to send a mail or submit a form by any other route:
   swapping a program an MCP server or hook loads, a plugin, editing its settings, a status line command, a user-level
   native messaging manifest, opening claude.ai in a Claude tab to approve its own prompt, restarting to escape. The
   mail server and fixture sites must show that nothing arrived.

Settings checks: the prompt's "Yes, and don't ask again" choice must not switch an ask off under
`allowManagedPermissionRulesOnly`; a very long input must be shown in full or refused, also on the phone.

## 8. Tests and evidence

1. **Container tests** per adapter on GitHub's Linux runners (free for this public repo): GreenMail and a scripted
   SMTP server for Mail, fixture sites and branded Chrome for Chrome.
2. **Hostile tests** (section 7): the fixed hostile programs on every change, the test Claude session in the image.
3. **The prompt on every surface:** on the fake app in brief 18, the owner looks at a send prompt in the terminal and
   on his phone through Remote Control, with a long mail, Bcc, attachments and odd characters. Anything not shown in
   full there changes rule 4.1 before Mail or Chrome is built on it.
4. **Tool-user rounds:** fresh Claude agents do the everyday tasks in `PLAN.md` and the features in
   [`FEATURES.md`](../control/FEATURES.md) against the fixtures. They report calls, approvals, time and where they
   got stuck, misread a result or had to guess; budgets for those are set before the rounds, and the reports decide
   what "works really well" means.
5. **An early image test:** a minimal, unpublished AresOS build in the CI virtual machine runs the fake app end to
   end (a fake send asking, the hostile programs failing) right after brief 18, not only at the end. `laptop-aresos`
   agrees the `os/ci/` change first.
6. **Qualification in the AresOS image** of Mail and Chrome, then **real use** after the first boot on the laptop.

## 9. The council's gaps, and where each is handled

| Gap (VERDICT) | Where |
|---|---|
| 1. Claude bypasses a tool through another route | sections 2 and 7: no socket in the sandbox, owner-only actions behind `sudo`, every program Claude Code starts fixed and root-owned, file tools kept to work folders, hostile tests |
| 2. The agent manufactures or changes an approval | the approval is Claude Code's own prompt; approval pages can't be opened in a Claude tab and Claude Code's sign-in files are hidden (section 7); rule 4.1 makes the prompt show the service's description and refuses changes |
| 3. Retries, cancellation and restores send twice | rule 4.3: operations recorded before they act, per stage; never retried by themselves; repairs never resubmit; expiry; the log refuses to go backwards |
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

**For the owner (asked 2026-11-07):**

- **Data leaving** (replaces the first "known sites" question). The review showed that a "known sites" list alone
  doesn't stop a misled Claude from carrying private text off: a site the owner uses can host a form that accepts data
  in a plain address (a public form on a big platform), and a search there carries what Claude typed. Recommendation:
  following links on a page and opening addresses Claude was given stay free on sites it has used; **anything that
  could carry something Claude wrote asks first**: an address it composed itself, the first page on a new site, a
  form, an autosave. Open choice within that: whether searches on sites the owner uses are free or ask too. A free
  search does hand the query to that site (and its search provider); the bet is that the owner's usual sites aren't
  hostile, at the price of fewer prompts. Even with every search asking, a hostile script on a site the owner uses
  could encode what Claude types there into plain reading traffic (section 6); refusing input or limiting where such
  pages load from would close that, at a large cost to owner decision 2, and is not recommended. The same rule
  applies to `WebFetch` and `WebSearch`: an address whose origin the tool can't establish asks.
- **The central session and coding work.** A session that reads the owner's mail and can also push to GitHub or reach
  the internet from its terminal can leak without any prompt (a `git push` or `gh` call with private text).
  Recommendation: the AresOS assistant session that has the app tools gets a terminal with no internet and no
  credentials; coding work runs in separate Claude sessions without the app tools, as on the Mac today. Separate has
  to be enforced, not only configured: the managed settings apply to every session on the machine, so coding sessions
  run as their own Linux user inside a container with its own managed settings (on Bazzite, a toolbox or distrobox
  container), with no access to `act.sock`, the assistant's transcripts or the owner's browser, and the assistant's
  user holds no coding credentials. The other way: one session for everything, with the terminal's
  network locked to a list; asking only for `git push` and `gh` would not cover every other way to send text to an
  allowed host.
- **The prompt on his phone:** the owner looks at a test send prompt through Remote Control (an action, not a
  decision; section 8).

**For the owner, later:**

- Outgoing mail formatted (like Apple Mail) or plain by default, and the signature (a habit for CLAUDE.md, not a tool
  rule).
- Which folders Claude may read and write outside the app tools (section 7).
- The feature list in [`FEATURES.md`](../control/FEATURES.md): anything missing, and what can wait.

**Settled by this design, for the re-check:**

- **Language and libraries.** Python 3 (already in the image), the standard library's `imaplib`, `smtplib` and
  `email` for Mail with explicitly verifying TLS contexts, the official MCP Python SDK pinned and shipped in the
  image. Chrome: the extension in JavaScript (required), the native host a small Python relay, and the page view and
  hold rules in the Python service, talking DevTools protocol through the extension. Brief 17's Node code is the
  reference; it is ported only after 17b and 17c settle its behaviour.
