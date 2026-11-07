# The control layer: design

**Status:** draft 9, 2026-11-07. Covers the shared base, Mail and Chrome. The frontier review
([`REVIEW`](../../reviews/control-design/2026-11-07-REVIEW.md), 8 blocking) and five re-checks
([1](../../reviews/control-design/2026-11-07-RECHECK.md), [2](../../reviews/control-design/2026-11-07-RECHECK-2.md),
[3](../../reviews/control-design/2026-11-07-RECHECK-3.md), [4](../../reviews/control-design/2026-11-07-RECHECK-4.md),
[5](../../reviews/control-design/2026-11-07-RECHECK-5.md)) ended at "ready for brief 18" on draft 6. Draft 7 adds
brief 17b's Chrome results (section 6: fail, then repeat; the policy install; the owner's own stop control; service
workers). Draft 8 adds brief 17c's (section 6: holding inside the page as the normal path, what the hold protects
against and what it doesn't, workers, live messages, the restart, the owner's own sends, the site guard settled); the
reviewer's sixth re-check ([6](../../reviews/control-design/2026-11-07-RECHECK-6.md)) found four blocking points
there, and draft 9 answers them: Chrome's own blocking rules as a floor under every hold, a site guard that ends by
itself only on evidence, workers covered by that floor whoever starts them, and no repeat without the complete bytes.
Points marked *17d* are checked by brief 17d before the Chrome build; points marked *brief 20* must be shown by the
Chrome build's own tests before anything relies on them.

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
`/run/aresos-tools` hidden from the sandbox's file view. The docs call the seccomp filter optional; native Claude
Code 2.1.319 has it built in (sockets refused even without the separate helper: brief 18b, *checked*). The launcher
still refuses to start Claude Code when the separate helper is missing, so a later version that drops the built-in
filter fails closed, and the hostile tests run with and without it. Before each start it also checks the native
program against a hash pinned at build time and runs a canary (a test socket the built-in filter must refuse), so
the protection doesn't depend on the separate helper alone (brief 18b, *checked*).

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
     command; then the generation moves on, ids of an earlier generation can no longer submit or be approved (their
     status, history and evidence stay readable), and every operation the separate record knows but the restored
     log doesn't is listed as `unknown` with its description, for the owner to check. Repairs that never submit
     again (a missing Sent copy) run as new operations that point to the old one. Mail adds evidence on the server: the Message-ID is derived from the operation id, and before
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

Built on briefs 17, 17b and 17c: branded Chrome stable 157 on GitHub's Linux machines, synthetic profiles and fixture
sites, ten public sites visited without signing in and with every send blocked
([17 report](../../reviews/17-chrome-check/REPORT.md), PR #3; [17b report](../../reviews/17b-chrome-holds/REPORT.md),
PR #4; [17c report](../../reviews/17c-chrome-pages/REPORT.md), PR #7). What the checks showed is marked *checked*; what
brief 17d checks before the build is marked *17d*; what the Chrome build still has to show is marked *brief 20*.

### How the tool reaches Chrome

- **Our own small extension** (Manifest V3, using `chrome.debugger`), installed and updated by the image through
  Chrome's `ExtensionInstallForcelist` policy with a local update manifest: the owner can't disable or remove it, and
  a new version arrives through the manifest (*checked*). It has no `management` permission (with it, an extension
  can disable itself, which released a held request: *checked*), and developer mode is off by policy so nobody
  reloads it by hand. Chrome starts its **native messaging host**, registered system-wide under
  `/etc/opt/chrome/native-messaging-hosts/`, with the `NativeMessagingUserLevelHosts` policy off: otherwise a
  user-level registration of the same name wins (*checked*). The system manifest and the host program are root-owned
  in the image. The host only relays between the extension and the service's `chrome.sock`. *Checked:* attaches to
  a tab that was opened and signed in before the tool started, with no debugging port and Chrome's sandbox on.
  Claude in Chrome's extension (`fcoeoabgfenejglbffodgkkbkcdhcgfn`) is blocked by `ExtensionInstallBlocklist`
  (*checked*).
- **Rejected:** Chrome's own consent attach (`chrome://inspect`) opens a debugging listener on port 9222 that stays
  on after a restart (*checked*), against the owner's no-debugging-port rule. Playwright's bridge extension works,
  but any local program that finds its endpoint can drive the page (*checked*); our own extension keeps that channel
  inside the service.
- **The owner always sees and can stop it.** Chrome hides its "started debugging this browser" bar for a
  policy-installed extension (*checked*), so the extension shows its own: the Claude tab group's colour, a badge on
  its toolbar button while Claude is working (the button pinned by policy), and in its popup a **Stop** button that
  fails everything held, then ends control. Stopping never sends anything (*checked* with the real popup and a real
  click: badge and group turned to stopped, seven kinds of held sends never arrived). The popup's messages carry no
  frame or document id in this Chrome version, so Stop accepts the extension's id, the exact popup address and a
  current popup context; Stop can only end control, never release anything.
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

While a tab is in the group, everything it sends waits for approval, also when the owner clicks there himself (his
own sends are confirmed by him in Chrome; below). To use a tab freely again, the owner drags it out of the group;
Claude's control of it ends, anything held is dropped, and the site stays guarded while Claude's work there is
unresolved.

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
| `chrome_end_guard` | **send** (asks) | end a site's guard where it didn't end by itself; the input shows what of Claude's may be left there and what the page stored; afterwards the owner's own sends there go unchecked |
| `chrome_operation_status` | read | an operation's stages (rule 4.3) |
| `chrome_sites` | owner-only | the owner's lists of known and trusted sites |

Every acting result says what happened (new page, dialog, download), the elements that changed, and anything held.
While a tab has a pending send, it accepts only reading, `chrome_submit…` and `chrome_drop`; background holds
(below) don't block it.

### What leaves a Claude tab, and how it is held

**What the hold is for, and what it isn't.** The hold stops a page's own code from sending Claude's work before the
owner approves it: a click that deletes, typed text that autosaves, a queue that a timer empties, a message on a live
connection. That is the everyday risk, and against it the tool must be complete. It doesn't make a hostile page safe
to type into: a page whose own scripts set out to carry off what Claude enters there can put it into plain reading
traffic, or keep a live connection's original send function away from the wrap (*checked*, 17c: a fixture page that
kept the browser's own `WebSocket.send` delivered a message the tool never saw; Chrome's network stage doesn't see
live messages, so no catch-all exists for them). Against a hostile page the protections are where Claude may act at
all (new sites ask first, below and section 10), and noticing afterwards: the tool compares Chrome's own record of
each WebSocket's sent messages (connection, content, order) with what it let go (released holds and messages free as
reading), and any message it didn't let go stops all input on that site and is reported to the owner (*brief 20*).
That is a diagnosis after the fact, not prevention, and WebRTC data channels and WebTransport have no such record in
Chrome. A hostile page that sends over ordinary HTTP past the wrap meets Chrome's own blocking rules (the floor,
below; *checked* at the request stage: zero arrivals before approval).

The rule: **nothing Claude caused or entered leaves a Claude tab without approval, and when the tool can't tell, the
request is held, never let go.** The one exception is plain reading (below), which stays free so that pages load; a
hostile script on a site the owner uses could abuse it, and that is the owner's decision in section 10. The service
judges every send the tab and everything it started (frames, popups, workers) makes, before it leaves the browser:
inside the page where the wrap is in place, at Chrome's request stage for everything else, with Chrome's own blocking
rules underneath (next part). It sorts each by cause and content, never by timing alone:

- **Caused by Claude: held as a pending send.** The tool follows each request's initiator, including the chain of
  timers, promises and callbacks behind it, back to its origin. A request that leads back to a click, key or other
  input Claude made is Claude's, however late it comes: a deletion scheduled twelve seconds after a click, an "undo
  send" delay, a retry of a dropped send. Requests caused by one action form one pending send, so a form that sends
  three requests asks once. *Checked* (17c, fixtures): chains through a timer, a promise, a mutation observer and
  `postMessage` were traced back to Claude's click; a send through a worker stayed unknown and was held; none of
  Claude's was counted as the page's own. A page's timer that empties a queue Claude's click filled leaves no chain
  at all, which is why the next rule exists. Tracing is supporting evidence only: no request is ever freed because
  its chain looks like the page's or the owner's.
- **After Claude acted on a page: held, whoever caused it.** Once Claude has done more than read, scroll and follow
  plain links in a document (clicked a control, typed, chosen, ticked, uploaded), every request from that document
  and its site's other guarded contexts that isn't plain reading is held, whatever started it: the page may carry
  Claude's input or effect in any form, also through its own state (a queue filled by Claude's click and sent by a
  timer the page set when it loaded). This holds for the owner's own clicks there too, because his click can flush
  work Claude queued (below: the owner's own sends). Any request anywhere that carries Claude's typed text (as typed
  or URL-, form-, JSON- or base64-encoded) is held too.
- **Plain reading goes:** GET or HEAD without a body and without Claude's text: pages, images, scripts, styles,
  fonts, the data a page loads to show something. Reading has to stay free, or no page would load. Which pages Claude
  may open at all is the next rule.
- **The page's own activity goes** only in a document Claude hasn't acted on: requests the page makes by itself
  (when it loads, on its own timers, after the owner's own clicks) that carry none of Claude's text.
- **Reading through POST.** Many apps load data with POST (GraphQL queries, Notion, Google's apps). A GraphQL request
  counts as reading only when its operation is written out in the request (not a stored or batched one), is a
  query, and its variables carry none of Claude's text; everything else about it is judged like any other request
  (*checked* on fixtures: a stored query, a batch, a mutation and Claude's text inline or in variables were all held).
  Other apps need a site adapter to tell reading from sending. Without one, their requests after Claude acted are
  held, so working in those apps asks until their adapter exists. *Checked* on ten public sites without signing in
  (17c, provisional: workers and live connections were switched off for safety, visits were short, and counts cover
  the main document; they are what the after-acting rule would hold, not prompts): GitHub, Wikipedia and a news site stayed
  usable with a few holds at most; Amazon and Google search held about a dozen each, mostly telemetry, which goes to
  the background list or is dropped as tracking; Notion and Google Docs read through POST and need an adapter;
  YouTube, Reddit and Stack Overflow showed the test machine a bot check and stay unmeasured. Signed-in use is
  measured in the tool-user rounds, on the owner's usual sites.
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
site, link pings and a data-bearing image.

**How a send is held, in practice (17b, 17c, 17d).** Three layers:

- **Inside the page: the normal path.** The extension's page script, which Chrome puts into every document and frame
  before the site's own scripts (also `about:blank` and `srcdoc` frames a script creates), and the tool's script in
  every dedicated worker before its first line, wrap the page's send functions: `fetch`, `XMLHttpRequest.send`,
  `navigator.sendBeacon`, form submission (the submit event, `submit()`, `requestSubmit()`), `WebSocket.send`,
  `RTCDataChannel.send` and WebTransport writers. A send that must be held creates no request: the page simply waits
  (a form stays on screen, a `fetch` stays pending, a message stays queued). After approval the wrapper performs
  exactly that call once; after a drop the page gets an ordinary failure (`AbortError` for `fetch`; the XHR's error
  event is *brief 20*, the check's prototype fired none). *Checked* for all seven kinds in the page itself, and for
  `fetch` in same-site and other-site frames, `about:blank` and `srcdoc` (the other kinds in frames: *brief 20*):
  zero arrivals while held, exactly one after release, none after drop; none when control ended while calls were held
  (page reload, debugger detach, the Stop button, extension reload, update and blocking by policy, the native host
  killed, Chrome closed and killed). Duplicate decisions, an expired `AbortSignal`, a form changed after the hold
  and a held call of an earlier document were refused. A call waiting in the page isn't paused inside Chrome, so
  control breaking has nothing to let go.
- **Chrome's own blocking rules: the floor.** A request paused at Chrome's request stage is let go when the
  extension is reloaded, updated, disabled or detached, and a blocking rule added after it was paused doesn't stop it
  (*checked*, 17b); even failing it at once leaves the instant between Chrome pausing it and the tool's answer
  (re-check 6). So the hard barrier is Chrome's own blocking rules (`declarativeNetRequest`), which Chrome applies
  before a request starts, with no pause and without the extension's code running: for every guarded site (rules
  Chrome keeps across restarts and extension updates, matched by the site that makes the request) and every Claude
  tab Claude has acted in (also frames of other sites in it), every request that isn't plain reading
  (any method but GET and HEAD) and every new live connection (WebSocket, WebTransport) is blocked. New live
  connections are let through only from a tab whose documents and dedicated workers the tool has reached; a worker
  without a tab (shared, service) gets none. *17d:* the rules act before the request stage, apply to a restored tab's
  first request at browser start and to every worker's requests (also a worker Chrome updates or starts by itself,
  with no page attached), and what the tool can see of a request they blocked.
- **Fail, then repeat, for what the wrap misses.** A page can get around the wrap (a saved original function, one
  taken from a fresh frame, a worker started from a blob). What it sends that way meets the floor and fails; the
  tool records what Chrome reports of it, and that is what the owner's prompt shows. After approval the service
  grants one allowance for exactly that request (method, full address, body and the headers the page set) and
  Claude repeats the action; the first matching request goes out once. A repeat that differs in anything, including
  a changing token, is refused, and no field is ever ignored automatically (*checked* at the request stage: hostile
  fixture pages had zero arrivals before approval, and a public demo form, aborted). The page shows a failed send
  first, and some sites lose a draft or token on it; sites whose requests change on every attempt need a site
  adapter or `chrome_submit_input`.
- **How an approved send passes the floor.** Through a one-time allowance: a rule for exactly that address and
  method from that tab or site, added right before the release and removed at its first match, when control ends and
  whenever the extension starts. The gate at the request stage then compares the matching request's body and the
  headers the page set with the approval and fails any difference. What remains is the instant around an approved
  release: ending control between Chrome pausing the matching request and the gate's answer can let a request to the
  approved address and method go unchecked (*17d* measures that window and shows the allowance gone after a reload,
  update, disable or crash of the extension). The approval also binds the signed-in account the description shows:
  if the page's account or session for that site changed while it waited, the release is refused (*brief 20*, with
  changed headers and competing identical requests).
- **Complete bytes, or no repeat.** The wrapper keeps the complete body as it was when held, files included (a file
  Claude put into a field is known by its sha256 from `chrome_upload`). A body whose complete bytes the tool can't
  hold or see (a stream; a request the floor blocked whose body Chrome doesn't report in full, as with the file parts
  of a form or a large body: *17d*) is refused, unless a site adapter describes the operation. Missing bytes never
  count as a match. A live message has no request stage: the wrapper sends its own copy of the message as held.
  Messages on one live connection keep their order: releasing one takes the earlier held messages on that connection
  with it, and its description lists them (*brief 20*).
- **Qualified contexts only.** The in-page path is used where the wrap is shown to be in place from the start: the
  kinds of document, frame and worker above. Where it isn't (a page loaded before the tool attached), only the floor
  holds and live messages already open can't be held at all, so input there is refused until a reload (below).
- **Plain GETs stay free, so one gap stays:** a GET that carries Claude's typed text and that the wrap misses is
  failed at the request stage, which leaves the same instant between pause and answer; and a worker the tool hasn't
  reached isn't checked for Claude's text at all. GETs can't be blocked wholesale, or no page would load. Both are
  named here; the wrap catches the honest cases (a search form, a page's own `fetch`).

Outcomes follow rule 4.3: the site's answer is recorded but doesn't prove the business step worked (`done` means the
site accepted the request); the page gave up waiting (its own timeout or `AbortSignal`) or the tab closed before
release is `failed`; the connection broke after release is `unknown`. Pages give up on their own timeouts
(*checked*); a page that gave up shows its own error, and Claude acts again for a new hold. Under fail-then-repeat
the owner's approval waits on the captured request, not on the page.

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
(an offline outbox that retries after a restart). So a site is *guarded*: its other tabs and workers are attached,
and what they send that isn't plain reading is held like in a Claude tab: listed as background when the page sent it
by itself, and put to the owner (next paragraph) when his own input caused it (*checked*, 17c: an owner's click in
another tab that emptied Claude's queue was held, through local storage and through a worker shared by both tabs).

- **When it starts:** with Claude's first action on the site (more than reading, scrolling and plain links).
- **When it ends by itself:** only on evidence that nothing of Claude's can be left there. All of these: every
  document Claude acted in there is gone (its tab closed; a released tab, or a page kept in Chrome's back-forward
  cache, still counts); every send Claude caused there was released (none failed, dropped, expired or still held);
  and from Claude's first action on, nothing in Claude's tab wrote to the browser's storage (web storage, IndexedDB,
  Cache Storage, cookies set by a script, the origin's private file system), passed data to another context (a
  broadcast channel, a shared or service worker, another window), or registered a worker or a background sync. An
  honest page that keeps Claude's work for later has to put it in one of those places (re-check 6: an offline app
  that records a deletion in IndexedDB and sends it later from another tab). The tool watches these through
  Chrome's own storage events where Chrome has them and the page script otherwise (*17d*: which of them Chrome
  reports; *brief 20*). Closing a tab fires the page's own leaving events, where many apps send what they still
  hold; those sends are held and, dropped with the page, keep the guard on.
- **Otherwise:** until a site adapter shows that what Claude left there is resolved, or the owner ends it: on the
  details page, or when Claude asks with `chrome_end_guard` (Claude Code's prompt shows what the page stored and
  where). A dropped or expired request is not such evidence, since the page may keep it queued (*checked*, 17b: a
  site's background sync sent a rejected request again five minutes later).
- **Across restarts:** the guard list and its floor rules are kept by Chrome (*checked* for the list). Restored pages
  start before the tool has attached (*checked*: a restored page's first request came before the tool was ready), so
  the page script holds their sends from the first document (*checked*) and the floor blocks what isn't plain
  reading (*17d*: for a restored tab's first request, other sites a restored page sends to, and workers without a
  tab). The floor rules of a guarded site are never lifted while the guard lasts, not even while the tool is
  attached, so a crash while attached leaves them in place. A restored service worker was held once the tool
  attached (*checked*); that is not proof for a worker Chrome starts by itself, which is why the floor covers
  workers.
- **Where a context can't be guarded,** the tool refuses to act on that site while it exists.

**The owner's own sends on a guarded site.** A request caused by the owner's own input (input the tool didn't
dispatch) on a guarded site, in the Claude group or outside it, is held too, because it may carry Claude's queued
work. The owner decides it himself, on a surface outside every page:

- **Where it appears:** a desktop notification from the extension (`chrome.notifications`) with "Send" and "Don't
  send", and a details window that is the extension's own page (address, method, data, and anything of Claude's still
  unresolved on the site, plus a way to end the guard). Never inside the page: no overlay, no frame embedded in the
  page, no page dialog, because a content script shares the page's document and Claude can read and click anything
  there.
- **Who can answer:** the extension accepts a decision only from the notification's own buttons
  (`onButtonClicked`) or from its own details page, checked by what Chrome reports about the sender: the extension's
  own id, the exact details-page address in the extension's origin, and the top-level document (not a frame).
  Messages from a page or a content script (even the extension's own) never release a request or end a guard. The
  tests show both sides: the owner's genuine answer works, every forged one is refused (*checked*, 17c: the real
  notification's Send and Don't send through the desktop's action menu, and the details page, each gave exactly one
  and zero arrivals; a page, the extension's content script, another extension page and the details page embedded
  in a frame were refused; taking an extension page and opening Chrome's pages were refused).
- **Why Claude can't:** Claude acts only through the debugger in page tabs of the Claude group; `chrome_take_tab` and
  `chrome_open` refuse extension pages and Chrome's own pages; desktop notifications and extension windows aren't
  pages it can reach; and its sandboxed terminal can't create input. The hostile tests try each: taking the details
  window, reading and clicking in every tab, answering a page dialog, forging messages from a page or content
  script, and creating input from the sandbox. Every attempt must leave the request held and the guard on.
- **Sends whose cause can't be seen:** a send from a worker that serves several tabs carries no trace of whose click
  caused it (*checked*). On a guarded site it is held as background for Claude and, when the owner was using one of
  the site's tabs just before (input the tool didn't send), also put to him: a guess about his notification, never
  an exemption. Outside that window it stays visible as unresolved on the details page and in the site's guard. Both
  places show one operation; the first answer decides it at once, and the same worker send reported through several
  attached sessions counts once (*brief 20*).

This is the owner deciding about his own click, not an approval of Claude's actions; those stay with Claude Code's
prompt.

**Which of the owner's own sends are put to him (settled with 17c).** Every send of his on a guarded site that isn't
plain reading, not only those that look like Claude's leftover (same address, Claude's text; proposed in draft 7
after `mac-capacity` raised the cost). 17c showed why that narrower match isn't safe: a page's timer that empties
Claude's queue leaves no traceable chain, and a shared worker's send has no trace of whose click caused it, so a page
can send Claude's queued deletion to another address than the one that was held. What keeps the notifications few is
that guards end by themselves where the evidence above shows nothing of Claude's can be left (draft 7 kept every
site Claude acted on guarded). Where a page stored something, the guard stays until the owner ends it: one click on
the details page, which says what of Claude's is unresolved and what to check (the site's outbox or drafts), or one
prompt when Claude asks. Known tracking requests are dropped, not asked. The tool-user rounds count these notifications on an ordinary day (section 8); the target is close to zero.

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
  held like a request (*checked*, 17c: all three, zero, one and zero arrivals; WebTransport for datagrams only, its
  streams still to show in *brief 20*). **Which messages count:** after Claude acted on a page, every message on
  it, like every request: on a chat fixture one ordinary click sent presence, subscription and typing messages and
  Enter sent the text, so matching Claude's text alone would have held one message in four (*checked*). Messages
  without Claude's text are background holds; a site adapter can free the ones it shows to be reading (a
  subscription). How many everyday sites keep such connections open while signed in couldn't be measured without
  signing in (17c blocked them on public sites for safety); a 2021 crawl found WebSockets on 6.3% of sites (Web
  Conference 2021, "WebSocket Adoption and the Landscape of the Real-Time Web"). The tool-user rounds measure it on
  the owner's usual sites.
- **Where the message hold can't be in place** (a tab taken from the owner whose connection was opened before the
  tool attached, until the page reloads; a page where the wrap provably fails), the tool can't see what a key or
  click sends. There, typing, Enter and clicks other than plain links are refused, unless a site adapter establishes
  the account, the conversation or target and the text: then `chrome_submit_input` does them as one asking step with
  that description, after re-checking it right before acting. Usually reloading the page brings the message hold
  back (*checked*, 17c: Chrome's inventory found a connection opened before the tool attached, a message on it
  went unheld, and after a reload the same send was held). *Checked:* holding the key press gave zero arrivals until
  approval and exactly one after.
- **Service workers:** the tool attaches to the site's service worker itself, which holds what the page sends through
  the worker, what the worker sends on its own, and background sync (*checked*). Telling the tab to bypass its worker
  also works but breaks features that only the worker provides (*checked*), so it isn't used. A worker can serve the
  owner's own tabs too, so its site is guarded as in "Other tabs of the same site". Failing a request doesn't cancel
  what the site queued: background sync retried a rejected request five minutes later (*checked*), so exact repeats
  of a dropped request are refused at once, and that list is kept across restarts with the site guard.
- **Workers that start while Claude works or a site is guarded.** A dedicated worker is reached before its first line
  (*checked*, 17c). A new shared worker and a newly installed or replaced service worker were not: the tool couldn't
  reach them in time, and their first send arrived (*checked*). Chrome also updates and starts a site's service
  worker by itself: on navigation, on push and sync events, or when the page asks for an update (Chrome's service
  worker lifecycle documentation). So nothing relies on reaching a worker early: the floor blocks every request that
  isn't plain reading and every new live connection from a worker without a tab, whoever started it and whether or
  not a page is attached (*17d*). Workers the tool does reach (dedicated ones, and running ones once attached:
  *checked*) hold as in a page. The page script also refuses to start new shared workers and service worker
  registrations while Claude works on the site (*checked* on the public sites), so honest pages keep to paths the
  tool can hold; pages do without offline use and push notifications there while it lasts.
- **A site that changes something with a plain GET** (against the web's rules, rare on reputable sites) can't be told
  from reading without knowing the site; and **a site that hides what it sends** (encrypts typed text before sending
  it) defeats the typed-text match, though its other requests after Claude typed are still held. Both are why new
  sites ask first and why site adapters exist.

### Fail closed

A held send must never go out because control broke. Held calls wait in the page and requests that aren't plain
reading are blocked by Chrome's own rules before they start; neither is paused inside Chrome, so a reload, update,
disable or detach has nothing to release (*checked* for calls held in the page through nine ways control can end,
17c; *17d* for the floor). The one thing paused is a request the floor lets through for checking (an approved send's
matching request, a GET checked for Claude's text): the instant named above. Checked separately: when the host or the
service's socket went away, or the extension's worker crashed, held requests were failed, not sent; Chrome closing
sent nothing; DevTools opened beside the tool didn't end control. A held request whose page or tab goes away, or
whose time runs out, is dropped, never sent. Live-connection detection after a re-attach uses Chrome's own event
stream plus a per-page inventory of open connections (*checked* on fixtures); where that inventory can't be complete,
the page counts as one where the message hold isn't in place.

### Tests

The fixture sites and runner from brief 17, extended with the cases of briefs 17b and 17c (every hold case proven by
the fixture server's own log, the counterexample of a page that keeps a live send away from the wrap included) and
the everyday tasks in `PLAN.md` (Chrome tasks 8 to 14), on GitHub's Linux machines with branded Chrome. Every point
marked *17d* is settled by brief 17d before the build starts, and every point marked *brief 20* is a test there
before anything relies on it. Hostile tests (section 7) add: reaching
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
  - Plugins and mods: none installed (`strictKnownMarketplaces: []`, `disableSideloadFlags`; an empty
    `enabledPlugins` is not a deny-all, so nothing is installed in the first place, and the launcher refuses to start
    when any plugin is installed: brief 18b). Claude Code's own built-in parts remain and are audited in the image
    test; cached plugins, LSP servers and monitors run by Claude Code itself are not yet qualified (brief 18b) and are
    part of the model-driven hostile test.
  - Settings below the managed file: the launcher starts Claude Code with no other settings sources
    (`--setting-sources ''`), so user and project settings can't add hooks, a status line, a helper or a permission
    grant (brief 18b, *checked*: with them allowed, planted markers ran; with the launcher's start, none did).
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
- **The sandbox:** forced on (`enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`); for the assistant
  session the whole work tree is read-only to the terminal, because Linux's sandbox can't exclude places like
  `**/.envrc` inside a writable folder (brief 18b); writing files goes through the file tools and their deny rules;
  no Unix sockets
  (`allowAllUnixSockets: false` plus the seccomp filter, section 2); the browser profile, `/run/aresos-tools`, the
  keyring and Claude Code's sign-in files hidden from its file view; no session D-Bus.
- **The network:** in skip-permissions mode the sandbox lets the terminal reach any host unless the list is locked, so
  the list is locked (`allowManagedDomainsOnly`), and it contains only what the owner allows (section 10). `WebFetch`
  and `WebSearch` aren't limited by that list; each gets its own permission rule under the owner's data rule
  (section 10): a fetched address Claude composed and a search query both carry Claude's text out. Until the owner answers, both ask on every call. How much network
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
   native messaging manifest, opening claude.ai in a Claude tab to approve its own prompt, creating keyboard or mouse
   input (through the display server or `/dev/uinput`) to answer the extension's notice, restarting to escape. The
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
   what "works really well" means. For Chrome they also count the notifications the owner would get for his own
   sends on an ordinary day; the target is close to zero.
5. **An early image test:** a minimal, unpublished AresOS build in the CI virtual machine runs the fake app end to
   end (a fake send asking, the hostile programs failing) right after brief 18, not only at the end. It also settles
   what CI had to loosen: GitHub's runner needed its user-namespace limit relaxed for the sandbox (brief 18b), so the
   image needs its own namespace policy. `laptop-aresos` agrees the `os/ci/` change first.
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
  could encode what Claude types there into plain reading traffic, or send it on a live connection it keeps away from
  the wrap (section 6, *checked* on a fixture); refusing input or limiting where such pages load from would close
  that, at a large cost to owner decision 2, and is not recommended. The tool notices an unheld WebSocket message
  afterwards and stops input on that site. The same rule
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
- **Claude in Chrome on AresOS** (asked 2026-11-07, board #58). The central session can't load it either way
  (`managed-mcp.json` lists only the control layer's servers; a hostile test checks that). Blocking it by Chrome
  policy (section 6) adds a little safety but takes the side panel from the owner's own use. Recommended: keep it for
  him. Until he answers, the image blocks it as section 6 says; if he keeps it, only that policy entry goes, and the
  `managed-mcp.json` exclusion and its hostile test stay.
- **Machine-wide rules** (board #59): the managed settings apply to every Claude Code session on the machine and
  change only with the admin password. That is what makes them hold; coding sessions get their own rules only if
  they run apart (above).

**For the owner, later:**

- Outgoing mail formatted (like Apple Mail) or plain by default, and the signature (a habit for CLAUDE.md, not a tool
  rule).
- Which folders Claude may read and write outside the app tools (section 7).
- The feature list in [`FEATURES.md`](../control/FEATURES.md): anything missing, and what can wait.

**Settled by this design, for the re-check:**

- **Language and libraries.** Python 3 (already in the image), the standard library's `imaplib`, `smtplib` and
  `email` for Mail with explicitly verifying TLS contexts, the official MCP Python SDK pinned and shipped in the
  image. Chrome: the extension in JavaScript (required), the native host a small Python relay, and the page view and
  hold rules in the Python service, talking DevTools protocol through the extension; the page wrap is the
  extension's own script. The Node code of briefs 17, 17b and 17c is the reference (check code, not product code);
  brief 20 ports what it settled.
