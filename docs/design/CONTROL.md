# The control layer: design

**Status:** draft 10, 2026-11-07. Covers the shared base, Mail and Chrome. The frontier review
([`REVIEW`](../../reviews/control-design/2026-11-07-REVIEW.md), 8 blocking) and five re-checks
([1](../../reviews/control-design/2026-11-07-RECHECK.md), [2](../../reviews/control-design/2026-11-07-RECHECK-2.md),
[3](../../reviews/control-design/2026-11-07-RECHECK-3.md), [4](../../reviews/control-design/2026-11-07-RECHECK-4.md),
[5](../../reviews/control-design/2026-11-07-RECHECK-5.md)) ended at "ready for brief 18" on draft 6. Draft 7 adds
brief 17b's Chrome results (section 6: fail, then repeat; the policy install; the owner's own stop control; service
workers). Draft 8 adds brief 17c's (section 6: holding inside the page as the normal path, what the hold protects
against and what it doesn't, workers, live messages, the restart, the owner's own sends, the site guard settled); the
reviewer's sixth re-check ([6](../../reviews/control-design/2026-11-07-RECHECK-6.md)) found four blocking points
there, and draft 9 answered them with Chrome's own blocking rules as a floor under every hold. Brief 17d showed that
floor doesn't hold (worker WebSockets pass it; an allowance lets a different send out when control ends), and the
seventh re-check ([7](../../reviews/control-design/2026-11-07-RECHECK-7.md)) recommended a checkpoint outside Chrome,
which brief 17e showed holds. Draft 10 rebuilds section 6 on that checkpoint (with the owner's hard requirements for
it, decision 6), makes the site guard strict (decision 12), adds "don't ask again" (decision 7) and his usual sites
(decision 9), and adds to section 7 the assistant apart from coding sessions (decision 8) and the approval surface
after the phone tests (open: the owner decides). Points marked *checked* name the check that showed them; points
marked *brief 20* must be shown by the Chrome build's own tests before anything relies on them.

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
| `act.sock` | `/run/aresos-tools/act.sock`: every action that may be offered to Claude. Open only to the assistant's user (decision 8): the service checks the caller's user on every connection (briefs 18, 18b). | |
| `admin.sock` | owner-only actions (accounts, passwords, the site lists, "don't ask again" entries, the checkpoint switch). Open only to root; the owner reaches it with `sudo aresos admin …` and his own password, which Claude can't give. | |
| `chrome.sock` | for Chrome's native messaging host only (section 6), open only to the browser's user. | |
| `aresos` | The terminal command: `aresos mail search --from … --json`, generated from the definitions, over `act.sock`. For the owner and his scripts, run as the assistant's user (`sudo -u`), and for owner-only actions with `sudo aresos admin`. | the caller |
| `aresos-mcp <app>` | One MCP server per app (`aresos-mcp mail`, `aresos-mcp chrome`), a thin generic proxy: it fetches its app's tool list from the service, forwards calls over `act.sock`, and does the caller's side of file transfers (rule 4.4). Root-owned under `/usr` (read-only in the image), started from `managed-mcp.json` with a fixed interpreter in isolated mode (`python3 -I`) and a fixed environment, so nothing in a writable folder is loaded into it. Started by any other user, it refuses at once (brief 18b, *checked*). | the assistant's user, started by Claude Code |
| `aresos-checkpoint` | The checkpoint every Chrome connection passes through (section 6): holds sends from guarded places, forwards each approved one at most once. Listens on one local port for the browser's user only and on `checkpoint.sock` for the service only. | system user `aresos-checkpoint` |
| Chrome bridge | Our own extension and native messaging host (section 6). | |
| Chrome | The owner's browser, with his profile and sign-ins, started only by a root-owned launcher (section 6). | user `aresos-browser` |
| The assistant | The Claude Code session that has the app tools (section 7, decision 8). | user `assistant` |
| Claude Code settings | `/etc/claude-code/managed-settings.json` and `managed-mcp.json`, owned by root (section 7). Exact values come once the tools exist (owner decision 3). | |

**Who can reach what:**

| From | `act.sock` | `admin.sock` | Passwords and sign-in data | Chrome's control channel |
|---|---|---|---|---|
| The owner's own terminal | as the assistant's user (`sudo -u`) | with `sudo` | no | only through the tools |
| Claude through its MCP tools (local MCP servers run outside the sandbox) | yes; send and delete ask first | no | no | only through the tools |
| Claude's terminal commands (sandboxed) | no | no | no | no |
| Claude's file tools (Read, Edit, Write; outside the sandbox) | no (they don't open sockets) | no | no: another user's files, plus deny rules | no |
| Coding sessions (another user, section 7) | no; the MCP proxy refuses them | no | no | no |
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

A program that runs as the assistant's user outside the sandbox can use `act.sock` without asking. That is the
normal desktop trust model (the owner's own programs could equally type into Chrome); the line this design draws is
around Claude, and section 7 lists every way Claude could start such a program and how each is closed. Because the
assistant runs as its own user, the files it may read and write in the owner's home (the allowed folders of rule 4.4)
are shared with that user explicitly, folder by folder; which ones is the owner's choice (section 10).

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
   [`2026-11-07-permission-prompt.md`](../../reviews/control-checks/2026-11-07-permission-prompt.md); on the phone
   through Remote Control the prompt reads as code, so where he approves is open: section 7). In detail:
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
   opens a path in the owner's home. The MCP proxy, running as the assistant's user with access to the owner's allowed
   folders (section 2), opens the file and hands the bytes over;
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

Built on briefs 17 to 17e: branded Chrome stable 157 on GitHub's Linux machines, synthetic profiles and fixture
sites, ten public sites visited without signing in and with every send blocked
([17 report](../../reviews/17-chrome-check/REPORT.md), PR #3; [17b](../../reviews/17b-chrome-holds/REPORT.md), PR #4;
[17c](../../reviews/17c-chrome-pages/REPORT.md), PR #7; [17d](../../reviews/17d-chrome-floor/REPORT.md), PR #8;
[17e](../../reviews/17e-chrome-checkpoint/REPORT.md), PR #10; re-check
[7](../../reviews/control-design/2026-11-07-RECHECK-7.md)). What the checks showed is marked *checked*, with the check
that showed it; what the Chrome build still has to show is marked *brief 20*. None of this qualifies the owner's own
signed-in browser; that comes after the first boot (the conditions near the end of this section).

**What changed in draft 10.** Draft 9 put Chrome's own blocking rules (`declarativeNetRequest`) under every hold and
let an approved send through with a one-time allowance for its address ("fail, then repeat"). 17d showed that this
doesn't hold: WebSockets opened by shared and service workers pass every extension rule (Chrome 157 doesn't show them
to extensions), and when control ends while an allowed request is paused, a different send to the same address goes
out (24 of 24 trials). Re-check 7 recommended a checkpoint outside Chrome, and 17e showed that it holds. So every send
from a guarded place now waits at that checkpoint, outside Chrome, and only the captured send the owner approved goes
out, at most once. Chrome's blocking rules no longer protect anything, and fail-then-repeat and URL allowances are gone. The
extension and the page script stay, for everything except deciding what leaves.

### How the tool reaches Chrome

- **Our own small extension** (Manifest V3, using `chrome.debugger`), installed and updated by the image through
  Chrome's `ExtensionInstallForcelist` policy with a local update manifest: the owner can't disable or remove it, and
  a new version arrives through the manifest (*checked*, 17b). It has no `management` permission (with it, an
  extension can disable itself, which released a held request: *checked*, 17b), and developer mode is off by policy
  so nobody reloads it by hand. Chrome starts its **native messaging host**, registered system-wide under
  `/etc/opt/chrome/native-messaging-hosts/`, with the `NativeMessagingUserLevelHosts` policy off: otherwise a
  user-level registration of the same name wins (*checked*, 17). The system manifest and the host program are
  root-owned in the image. The host only relays between the extension and the service's `chrome.sock`. *Checked*
  (17): attaches to a tab that was opened and signed in before the tool started, with no debugging port and Chrome's
  sandbox on.
- **Claude in Chrome stays for the owner's own use** (decision 10), so its extension is no longer on Chrome's block
  list. The central session can't load it (`managed-mcp.json` lists only the control layer's servers; a hostile test
  checks that), and its connection to Claude Code sessions, a user-level native messaging host, doesn't start because
  user-level hosts are off by policy (*brief 20*). What it sends goes through the checkpoint like everything else.
- **Rejected:** Chrome's own consent attach (`chrome://inspect`) opens a debugging listener on port 9222 that stays
  on after a restart (*checked*, 17), against the owner's no-debugging-port rule. Playwright's bridge extension
  works, but any local program that finds its endpoint can drive the page (*checked*, 17); our own extension keeps
  that channel inside the service.
- **Chrome runs as its own user** (`aresos-browser`), which holds the owner's profile and sign-ins. The checkpoint
  needs this: the OS can then let exactly Chrome's connections reach the checkpoint and nothing else (17e did it this
  way; a cgroup or a network namespace was the alternative it named). It also keeps the profile (cookies, saved
  passwords) away from the owner's other programs, the assistant and coding sessions. Chrome starts only through a
  root-owned launcher (the desktop entry, and the default browser for links from other apps), which starts the
  checkpoint first. A Chrome started any other way, as another user, finds no profile and can't connect: the proxy
  policy is machine-wide and the checkpoint accepts only the browser user. On Fedora with KDE this needs: the owner's
  profile moved to that user once, with its sign-ins; the display, sound, camera, microphone, notifications and the
  file chooser through filtered access to the owner's desktop session (nothing else of it); Chrome's own password and
  cookie encryption through a keyring of that user, not the plain store 17e used; downloads into the owner's allowed
  folders. All *brief 20*.
- **The owner always sees and can stop it.** Chrome hides its "started debugging this browser" bar for a
  policy-installed extension (*checked*, 17b), so the extension shows its own: the Claude tab group's colour, a badge
  on its toolbar button while Claude is working (the button pinned by policy), and in its popup a **Stop** button
  that drops everything held for Claude's tabs, then ends control. Stopping never sends anything (*checked* with the
  real popup and a real click, 17c: badge and group turned to stopped, seven kinds of held sends never arrived). The
  popup's messages carry no frame or document id in this Chrome version, so Stop accepts the extension's id, the
  exact popup address and a current popup context; Stop can only end control, never release anything.
- The host runs as the browser user, like Chrome, and `chrome.sock` is open only to that user. A program running as
  that user could pretend to be the host (*checked* for the owner's user in 17; the model is the same); only Chrome
  runs as that user. Claude can't, because it runs as another user (decision 8, section 7), its terminal is
  sandboxed, and its file tools can't write the places that start programs (section 7).

### The checkpoint

**What it is.** A local service, `aresos-checkpoint`, that every connection Chrome makes passes through: an
intercepting proxy built on a pinned mitmproxy core (17e's recommendation: no new TLS or HTTP/2 implementation). It is
part of the tool service's design, runs as its own system user (requirement 1, below), and takes orders only from
`aresos-toold`, over its own socket `checkpoint.sock`. It decrypts Chrome's HTTPS with a root certificate Chrome
trusts by policy, so it sees every request and every WebSocket message whole, and it opens its own checked TLS
connection to the real site.

**Chrome uses it, and nothing else.**

- Chrome's policy (root-owned, in the image) sets one fixed proxy, with no DIRECT entry and with `<-loopback>`, so
  that localhost and link-local addresses go through it too (`ProxySettings`); QUIC is off (`QuicAllowed: false`);
  WebRTC may not use UDP outside the proxy (`WebRtcIPHandling: disable_non_proxied_udp`). (*Checked*, 17e.)
- The OS enforces it: a firewall rule lets the browser user connect only to the checkpoint's port; everything else,
  IPv4, IPv6 and UDP, is refused. Direct IPv4, IPv6, localhost and link-local probes from Chrome's user delivered
  nothing with the rule on; with it off they arrived (*checked*, 17e Q1). If the checkpoint is down, pages fail with
  Chrome's own error; nothing goes direct (*checked*, 17e Q1). The rule has to survive the image's firewall service
  reloading its own rules (*brief 20*).
- It decrypts continuously from browser start, never only while Claude works: an interception switched on later
  can't see into connections Chrome already opened (HTTP/2 connections it reuses, a worker's live socket; re-check 7).
  Pre-opened HTTP/2 connections and page, dedicated, shared and service-worker sockets stayed visible (*checked*, 17e
  Q2).
- WebTransport doesn't work at all, because Chrome's WebTransport refuses to run through a proxy; WebRTC (calls, peer
  data) is refused while a guard is on, not decrypted, because it is encrypted end to end (*checked*, 17e Q8: zero
  payloads at independent peers; re-check 7). Calls: near the end of this section.

**What it holds.** While a site is guarded (below), the checkpoint holds every complete operation from that site's
contexts and from every Claude tab Claude acted in that isn't plain reading: an HTTP request with its request line,
headers and complete body; a WebSocket handshake; each WebSocket message; a close that carries data. Nothing of a held
operation reaches the site, not even its first header (*checked*, 17e Q4: binary, gzip, chunked, multipart with a real
file from disk, 25 MiB; a fragmented socket message sent no partial bytes; close reasons held). A held operation is
captured once, in memory, under its own id. One larger than the limit (32 MiB including its metadata in 17e) or one
that never completes is refused and never forwarded (*checked*, 17e Q4: incomplete input sent zero headers upstream;
an oversized upload was drained and answered with an error).

**How an approved send goes out.** The approval names one captured operation by its id and the hash of its bytes.
The checkpoint first records durably that this capture is consumed, then forwards exactly those captured bytes, at
most once: a crash can leave it not delivered or delivered in part, and it is never sent again.
There are no URL allowances: nothing is let through because it matches an address; the approved bytes themselves go.
Two byte-identical competitors get different ids and only the approved one goes; a second decision on the same id
fails (*checked*, 17e Q5). Before release the service checks that the page's document and signed-in account are
still the ones the description names; a change means a new approval (*brief 20*: 17e Q5 checked an explicit change
of context, not an arbitrary site's account). Messages on one live connection keep their order: approving one
forwards the earlier held messages on that connection with it, and its description lists them (*brief 20*).

**Fail-stop, never replay, unknown stays unknown.** If anything in the checkpoint fails, it stops; it never logs the
error and carries on (mitmproxy's default for an add-on error is to log and continue; 17e replaced that with stopping
the process: *checked*, 17e Q6). Stopping drops what it held in memory: those captures are reported as lost, and the
page sees a failure. After a restart nothing is sent again: a capture recorded as consumed without a recorded outcome
becomes `unknown` and is never retried. *Checked* (17e Q6): the extension, the native host, the browser and the
checkpoint were each killed while a send was held, just before consumption, just after it and while forwarding: zero
arrivals before forwarding, no replay. A send cut off while being forwarded may still have reached the site, in full
or in part; its outcome is `unknown`, and the owner checks the site before anything is done again (rule 4.3).

**When the extension goes away**, held operations stay held: the checkpoint doesn't need the extension to hold
(*checked*, 17e Q3 and Q6: extension removed by policy, native host and browser killed). It does lose its attribution
(next), so the whole browser counts as guarded until the extension is back.

**Attribution: whose is an operation.** The checkpoint must know which operations come from guarded places. Its
evidence, all of it supporting, none of it authorising:

- A **tag** the extension puts on every request it can see (through Chrome's own header rules), naming the browser
  run, the tab and the document generation. The rule overwrites any value a page set, and the checkpoint strips the
  tag before forwarding (*checked*, 17e Q3: a page's forged tag was overwritten; a missing tag, a reused earlier
  token, an opaque origin, a foreign frame and a cross-origin hand-off all stayed held).
- For a WebSocket handshake, its **`Origin`**, which Chrome sets and pages can't change. Sockets of shared and service
  workers carry no tag (17d: Chrome doesn't show them to extensions), so their `Origin` names their site.
- A request's `Origin` and `Sec-Fetch-Site` say how it relates to the page, not who made it (re-check 7); they only
  add to the picture.

The rule: **uncertainty widens what is held, never the reverse.**

- An operation tagged with a Claude tab Claude acted in is guarded, whatever site its frame belongs to.
- An operation from a context of a guarded site is guarded, in any tab.
- A worker's operation without a tab (its `Origin` or initiator a guarded site, or an opaque origin) is guarded.
  Workers of other sites' frames that were inside Claude's tab carry no tab either, so while that guard lasts, the
  checkpoint holds those sites' tab-less sends too; that can hold background sends of the owner's own tabs of those
  sites (counted under condition 1, below).
- An operation with a stale tag, a tag of an earlier browser run, or no tag where the extension would have set one is
  uncertain and treated as guarded.
- Without the extension (not connected, or its tags missing), the whole browser counts as guarded: every operation
  in every tab that isn't cleared as reading (next paragraph) waits, shown to the owner, until the extension is back
  (17e's fallback, *checked*).
- **Claude's entered text, anywhere.** The tool service gives the checkpoint each text Claude entered while its
  guards last, and the checkpoint holds any operation, in any tab and to any destination, reading included, that
  carries it (as typed, or URL-, form-, JSON- or base64-encoded). Draft 9 could check this only where the page script
  was in place; the checkpoint sees everything (*brief 20*; 17c *checked* the match in the page). The checkpoint keeps
  these texts with the guards in its private record, encrypted at rest with a key the system keeps for this service
  alone (a service credential tied to the machine), and deletes each text when its guard ends.
- Requests of other extensions carry that extension's own origin, set by Chrome; they are the owner's own tools, and
  what he installs is his decision. Claude in Chrome is one of them (decision 10).
- **Chrome's own services** (Safe Browsing, component updates, sync) make requests no extension sees, so they carry no
  tag. They are never freed by host name or because an `Origin` is missing (re-check 7). While a guard is on, the
  checkpoint lets them pass only where an adapter for that Chrome protocol shows that they carry only that service's
  own data (versions, hash prefixes), never free text; the rest wait as background holds shown to the owner, not to
  Claude (*brief 20*, with a measured list of which services send what). A page can make Chrome send on its behalf (a
  push subscription, a passkey, a payment): the page script refuses those calls on a guarded site while Claude works
  there (honest pages; a hostile page is a residual below).

**Reading while attribution is uncertain, and readiness.** Plain GET and HEAD from a known place stay free unless
they carry Claude's entered text (below). Where attribution is uncertain, the checkpoint can only clear a GET or HEAD
if it still knows everything it needs to classify it: the guards and Claude's entered text. So at every start it
holds everything, GET and HEAD included (17e's full fallback), until it has restored both from its record. Only then
does it report ready: to the launcher, which starts Chrome only after that, and to the tool service, which offers
Claude's Chrome tools only after that. From then on, an uncertain GET or HEAD passes only when the entered-text check
clears it; every other uncertain operation waits. If it can't restore its record, it never reports ready and
browsing stays stopped; his way out is the pass-through switch (condition 3). Freeing more than that while
attribution is uncertain needs qualified reading rules, proven by receiver tests across restarts of the checkpoint,
the service and the browser and loss of the extension (*brief 20*). The stalls this causes count under condition 1.

**The guard barrier.** A guard starts before Claude's first acting step on a site (more than reading, scrolling and
plain links). The tool tells the checkpoint, which records the guard durably, re-checks the connections already open
(live sockets of that site's contexts now hold their next message; tunnels it can't read are cut: calls, below), and
only then confirms. Only after that confirmation does the tool send Claude's click or key (*checked*, 17e Q2: under
concurrent HTTP and socket traffic the guard was recorded and confirmed before input; traffic sent before the barrier
can still arrive after it, and is not Claude's). Because the checkpoint restores its guards and Claude's entered text
before it reports ready, a restored page's first send after a restart of Chrome or of the checkpoint is held before
the extension has attached (*checked* for the guards, 17e Q1; the entered text, *brief 20*).

**Cancellation.** A held operation is cancelled when the checkpoint sees it given up before forwarding: the page
aborts it, the tab or connection closes, its hold expires, or the page script reports an explicit cancel. It is then
dropped, and a late approval is refused (*checked*, 17e Q7). What can't be seen can't cancel: a page's own JavaScript
timeout without an abort leaves the request waiting, and a later approval sends it (*checked*, 17e Q7). A reset
HTTP/2 stream gave zero arrivals in 17e, but its record could still show the operation consumed; brief 20 makes the
checkpoint see stream resets, and until then such a case reads `unknown`. The promise is: **a cancellation seen
before forwarding prevents the send**; not "a page that gave up internally never sends later".

### The owner's requirements for the checkpoint (decision 6)

He agreed to the checkpoint "if that's not a security risk", with five hard requirements. Each is a design
requirement here, with how it is met and how brief 20 tests it.

1. **Its own user.** `aresos-checkpoint` is a system user with no login, no home and no other role: not the tool
   service's user (which holds the mail password), not the browser's, not the owner's or the assistant's. Its state
   (the guard list and the record of consumed captures) is in a folder only it can read. `checkpoint.sock` is open
   only to the tool service. Its listening port accepts connections only from the browser user (a firewall rule). The
   port is below 1024, which ordinary programs can't open, and the checkpoint is started with the right to open it,
   so no other program can listen there first and pose as it (17e: taking over the port was not tested). The
   checkpoint refuses to start if the port is taken or if ordinary users may open low ports.
   *Test:* the owner's, the assistant's and a coding user's programs can't connect to the port or the socket; a
   program of theirs can't open the port; the checkpoint refuses to start when the port is taken.
2. **Nothing it sees leaves the machine.** It sends nothing anywhere except the browser's own traffic to the address
   Chrome asked for: no telemetry, no updates of its own, no remote logs, no web interface (mitmproxy's core only).
   Captured bytes stay in its memory: no core dumps of its process, its memory kept out of swap, no temporary files.
   What it tells the tool service about a held operation (site, address, method, decoded data, hash) reaches Claude
   only for operations from Claude's tabs and guarded sites, which Claude could read on those pages anyway. What it
   holds only because attribution was uncertain, and anything of the owner's unrelated tabs, is shown to the owner
   and never described to Claude.
   *Test:* every outgoing connection of the checkpoint matches one Chrome asked for; it writes no file outside its
   state folder; core dumps are off; Claude's tools return no content of an unrelated tab's held operation.
3. **No bodies, cookies or secrets in logs.** Its logs and its record hold ids, lengths, hashes, states, the site and
   the method; never bodies, header values, cookies, passwords, query strings or socket messages. Messages of the
   proxy core are filtered the same way (errors only, addresses cut to the site). The record of what was approved
   (the description the owner saw, as for mail) is the tool service's operation log, in its own private store; it is
   not a checkpoint log.
   *Test:* runs with marker strings in cookies, headers, bodies, query strings and socket messages; afterwards no log,
   journal entry, record, crash output or temporary file contains a marker. (17e did this for its own records and
   found and fixed one leak of a fixture value: *checked*, 17e Q11.)
4. **Full upstream TLS checks.** The checkpoint checks every connection to a site itself: the certificate chain
   against the system's list of roots (the checkpoint's own root is never added to that list), the host name and the
   dates; current TLS versions only; any failure ends the connection with an error page in Chrome, never a fallback
   and never "accept anyway" (*checked*, 17e Q9: an invalid upstream certificate gave a failure and zero requests at
   the receiver; HSTS kept working; a Google address that Chrome pins worked through the local root, as Chrome
   documents). What moves, named plainly: Chrome's own extra checks on the outside connection (Certificate
   Transparency, its own revocation list, pinned keys) no longer apply, because Chrome exempts a locally added root
   from them (re-check 7, Chrome's security FAQ); the checkpoint does the chain, name and date checks, and brief 20
   adds revocation checks where the core supports them. Sites that ask the browser for a client certificate don't
   work.
   *Test:* expired, wrong-name, self-signed, unknown-root and old-protocol upstreams all fail with zero requests;
   HSTS; the checkpoint's root is absent from the system's list.
5. **A key that rotates and can issue nothing while the checkpoint is stopped.**
   - **A fresh root per start.** A root-owned start step runs before the checkpoint: it makes a new root key and
     certificate (allowed only to sign site certificates, valid a few days at most), writes the certificate into
     Chrome's policy (`CACertificates`) and into the place Chrome's own services read trust (next part), and hands
     the key to the checkpoint as a service credential: memory that isn't swapped, readable only by the checkpoint's
     user, gone when the service stops. The start step deletes its own copy; the key is never on disk.
   - **Only in memory.** The checkpoint keeps the key and the site certificates it makes only in memory.
   - **Stopped means nothing can issue.** When the checkpoint stops or crashes, the key is gone with it, and the stop
     step removes the certificate from Chrome's policy. Nothing can make a certificate Chrome trusts while the
     checkpoint is stopped: the old key no longer exists, and a new one exists only once a new run starts.
   - **How Chrome takes a new root.** `CACertificates` is a per-profile policy that Chrome also re-reads while
     running (Chrome 157's policy definition: `dynamic_refresh: true`, `per_profile: true`), not one read only at
     start. When the checkpoint restarts with a new root, a running Chrome at first still trusts only the old one, so
     every new TLS connection fails (the new checkpoint signs with a root Chrome doesn't know yet): that fails
     closed. Once Chrome re-reads its policy, the new root works and the old one is no longer trusted. How quickly
     that happens, and what happens to Chrome's own services, which don't read this policy at all (17e Q9), is
     *brief 20*. The design doesn't rely on it: the launcher starts the checkpoint first and Chrome only once the new
     root is in place, and when the checkpoint restarts while Chrome runs, the launcher closes Chrome and starts it
     again with its tabs restored. Typing the owner hadn't sent in his own tabs can be lost; the extension says why
     Chrome restarted. Brief 20 decides, from measurements, whether the policy refresh is reliable enough to skip
     that restart.
   - **Renewal.** Before a root expires, the checkpoint is restarted with a new one at a moment when nothing is held.
   *Test:* a new root at every start; no key material on disk, in swap or in a crash file; after a stop, the old
   root is gone from the policy and no certificate it signed is accepted; a running Chrome's behaviour when the root
   changes, and the launcher's restart.

### Chrome's own services through the checkpoint

17e found some of Chrome's own background connections failing the checkpoint's certificate (component updates,
Chrome's client services, the optimization guide, a Google static host), because the trust policy is per profile and
Chrome's own services use a separate network context that doesn't read it (*checked*, 17e Q9; re-check 7). The fix is
trust, never an exemption: no host is passed through unopened and none is let through by name, because either would
give a page an unchecked way out. The start step puts the root also where Chrome's own network context reads trust,
for the browser user only and never in the machine's trust store (on Linux, the candidate is the user's own
certificate database that Chrome reads for locally added roots; *brief 20* finds and proves the place). Brief 20 then
shows, through the checkpoint:

- Safe Browsing warning on its official test page, with a positive control: Safe Browsing on by policy and its lists
  loaded before the test (in 17e even the direct run showed no warning, so the control was missing);
- a fresh component download, not only "up to date" on a component already there;
- the extension's own updates, and sync;
- no certificate failures in Chrome's service connections.

Chrome features that send page text or typed text to a server of Chrome's own (enhanced spell check, page
translation, search suggestions as Claude types an address) could carry Claude's text in a form the entered-text check
doesn't see. Brief 20 lists them; each is off by policy or held like Chrome's other service sends while a guard is
on.

### Which tabs Claude works in

Claude works in tabs in its own tab group, labelled **Claude**: tabs it opened itself (same profile, so the owner's
sign-ins work) and tabs of the owner's it took into the group (`chrome_take_tab`; the owner sees the tab move). It
reads and acts only inside the group; popups and new tabs a Claude tab opens join the group and are controlled before
their first script runs. The service knows the group by Chrome's group id, not by its label, and releasing a tab
puts it back where it was. `chrome_tabs` lists every tab's title and address, so Claude can say what is open and
pick one.

While a tab is in the group, everything it sends that isn't plain reading waits for approval, also when the owner
clicks there himself (his own sends are confirmed by him; below). To use a tab freely again, the owner drags it out of
the group; Claude's control of it ends, anything held is dropped, and the site stays guarded while Claude's work there
is unresolved.

Every reference is bound to the browser session, tab, document and element: when the owner switches or opens tabs,
nothing is redirected; when the page changes, an old reference fails with "stale, read again" instead of hitting
another element (*checked*, 17); after a Chrome restart all old references are stale. Acting calls carry what Claude
expects the element to hold (from its last read), and the tool refuses when the owner has changed it in the meantime.

### Reading a page

`chrome_read` returns a compact tree in the style of Playwright's AI snapshot, built from Chrome's accessibility tree
and layout: one line per element with a short reference (`e12`), role, label, value, states (checked, selected,
disabled, required, invalid, expanded) and its box in CSS pixels with whether it is on screen; frames (also from
other sites) and open shadow DOM included; elements behind an open dialog left out. A header names the tab, the
document, the address, the title, the scroll position and anything held. Measured (*checked*, 17): a long form about
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
| `chrome_click`, `chrome_fill`, `chrome_fill_form`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll` | change | act on elements by reference, each with what Claude expects it to hold; fill sets text, dates and dropdowns as a person would; `chrome_fill_form` fills several fields in one call; a control the page labels as destructive is refused here (below) |
| `chrome_click_destructive` | **delete** | click a control the page labels as destructive, or press Delete or Backspace outside a text field, only after approval; the approval says the click may delete data kept only in this browser (below) |
| `chrome_dialog` | change | accept, dismiss or answer a page's own dialog (alert, confirm, prompt) |
| `chrome_upload` | change | put a local file into a file field; the bytes come through the caller's side (rule 4.4), the extension gets no general file access (*checked*, 17) |
| `chrome_downloads` | read, change | list downloads; save one into an allowed folder (rule 4.4) |
| `chrome_bookmarks`, `chrome_history` | read | the owner's bookmarks and history, to find addresses |
| `chrome_wait` | read | wait for text, an element or the page to settle |
| `chrome_pending` | read | what is held for Claude's tabs and guarded sites: pending sends and background holds |
| `chrome_submit` | **send** | let one pending send go: the captured operations the service described, by id and hash (below) |
| `chrome_submit_trusted` | send, free | as `chrome_submit`, only for an operation a site adapter recognises as a kind the owner set to "don't ask again" (below) |
| `chrome_open_site` | **send** | open an address that isn't free to open (below), with the full address in the input |
| `chrome_drop` | change | drop held operations; nothing leaves |
| `chrome_end_guard` | **send** (asks) | end a site's guard where it didn't end by itself; the input shows what of Claude's may be left there and what the page stored; afterwards the owner's own sends there go unchecked |
| `chrome_end_call` | **send** (asks) | end the owner's running call in Chrome so that Claude can act; the approval names the call's tab and the site Claude wants to act on (calls, below) |
| `chrome_operation_status` | read | an operation's stages (rule 4.3) |
| `chrome_sites` | owner-only | the owner's lists: his usual sites, the sites Claude has used, and his "don't ask again" entries, to see and revoke |
| `chrome_checkpoint` | owner-only | switch the checkpoint to pass-through and back (a way out of a fault: below) |

Every acting result says what happened (new page, dialog, download), the elements that changed, and anything held.
While a tab has a pending send, it accepts only reading, `chrome_submit…` and `chrome_drop`; background holds (below)
don't block it. Draft 9's `chrome_submit_input` (type and press as one step after approval, where the page's message
hold couldn't be in place) is gone: the checkpoint sees every live message, also on connections opened before the
tool attached, so typing and Enter are ordinary actions and the message they cause waits like any send.

### What leaves a Claude tab, and how it is held

**What the hold is for, and what it isn't.** The hold stops a page's own code from sending Claude's work before the
owner approves it: a click that deletes, typed text that autosaves, a queue that a timer empties, a message on a live
connection, also from a worker. Against that the checkpoint is complete for the transports it handles: it doesn't rely
on the page script, so a page can't get such a send past it by keeping a browser function away from the script (17c's
counterexample), by sending from a worker (17d's), or because control ended (*checked*, 17e Q2, Q3 and Q6: page,
dedicated, shared and service-worker sends held, also after the extension was removed). It doesn't make a hostile page
safe to type into: a page whose own scripts set out to carry off what Claude enters can hide it in plain reading
traffic. Against a hostile page the protections are where Claude may act at all (new sites ask first, below) and the
residuals named in "What changes for the owner".

The rule: **nothing Claude caused or entered leaves without approval, and when the tool can't tell, the operation is
held, never let go.** The one exception is plain reading (below), which stays free so that pages load. The checkpoint
judges every operation from Claude's tabs and from guarded places (frames, popups, workers) before it reaches the
site, and the service sorts each by cause and content, never by timing alone:

- **Caused by Claude: held as a pending send.** The tool follows each request's initiator, including the chain of
  timers, promises and callbacks behind it, back to its origin. A request that leads back to a click, key or other
  input Claude made is Claude's, however late it comes: a deletion scheduled twelve seconds after a click, an "undo
  send" delay, a retry of a dropped send. Operations caused by one action form one pending send, so a form that
  sends three requests asks once. *Checked* (17c, fixtures): chains through a timer, a promise, a mutation observer
  and `postMessage` were traced back to Claude's click; a send through a worker stayed unknown and was held; none of
  Claude's was counted as the page's own. A page's timer that empties a queue Claude's click filled leaves no chain
  at all, which is why the next rule exists. Tracing is supporting evidence only: no operation is ever freed because
  its chain looks like the page's or the owner's.
- **After Claude acted on a page: held, whoever caused it.** Once Claude has done more than read, scroll and follow
  plain links in a document (clicked a control, typed, chosen, ticked, uploaded), every operation from that document
  and its site's other guarded contexts that isn't plain reading is held, whatever started it: the page may carry
  Claude's input or effect in any form, also through its own state (a queue filled by Claude's click and sent by a
  timer the page set when it loaded). This holds for the owner's own clicks there too, because his click can flush
  work Claude queued (below: the owner's own sends). Any operation anywhere that carries Claude's entered text is held
  too (attribution, above).
- **Plain reading goes:** GET or HEAD without a body and without Claude's text: pages, images, scripts, styles,
  fonts, the data a page loads to show something. Reading has to stay free, or no page would load. Which pages Claude
  may open at all is the next part.
- **The page's own activity goes** only in a document Claude hasn't acted on: requests the page makes by itself
  (when it loads, on its own timers, after the owner's own clicks) that carry none of Claude's text.
- **Reading through POST.** Many apps load data with POST (GraphQL queries, Notion, Google's apps). A GraphQL request
  counts as reading only when its operation is written out in the request (not a stored or batched one), is a query,
  and its variables carry none of Claude's text; everything else about it is judged like any other request
  (*checked* on fixtures in the page, 17c: a stored query, a batch, a mutation and Claude's text inline or in
  variables were all held; the checkpoint applies the same rule to the bytes it captured, *brief 20*). Other apps
  need a site adapter to tell reading from sending. Without one, their requests after Claude acted are held, so
  working in those apps asks until their adapter exists. *Checked* on ten public sites without signing in (17c and
  17d, provisional: workers and live connections were switched off for safety, visits were short, and counts cover
  the main document; they are what the after-acting rule would hold, not prompts): GitHub, Wikipedia and a news site
  stayed usable with a few holds at most; Amazon and Google search held about a dozen each, mostly telemetry, which
  goes to the background list or is dropped as tracking; Notion and Google Docs read through POST and need an
  adapter; YouTube, Reddit and Stack Overflow showed the test machine a bot check and stay unmeasured. 17e's reading
  visits gave the same results through the checkpoint as direct (*checked*, 17e Q11). Signed-in use is measured in the
  tool-user rounds, on the owner's usual sites.
- **Unknown cause: held, in the background.** An operation whose cause the tool can't establish is held and listed
  as *background* in `chrome_pending`. Background holds don't block the tab: Claude can keep reading and acting, drop
  them (free) or submit them (asks). Each is kept as its own operation; only polling an adapter shows to be the same
  read repeated is merged. Known tracking addresses are dropped without being listed; every background hold expires
  and is dropped, and expired holds stay listed (with what they were) until Claude has seen them.
- **Dropping is final.** The page gets an ordinary failure. A page that retries a dropped send produces a new held
  operation, marked as a retry; it never goes by itself.
- **One step at a time.** A request the page builds from the answer to an approved one is a new send and asks again,
  unless a site adapter defines the whole sequence as one operation and the approval covers all of it.

A pending send stops the action; its result reads `held` with the **service's description** (rule 4.1): what Claude
did (the click on "Delete" in the row "Invoice 42"), the page's address and title, the signed-in name the page shows
(all marked "as the page shows it"), and every held operation: site, full address, method, the data decoded where
possible, the capture id and the hash of its bytes. Claude passes exactly that to `chrome_submit`, and the owner's
prompt shows it. The checkpoint forwards each captured operation at most once. *Checked*: held sends reached the fixture
server zero times while held, exactly once after release and never after drop, for posted forms, search forms,
`fetch` and XHR posts, beacons, autosave, a form posting to another site, link pings and a data-bearing image (17,
17b, 17c, holding in the page); and at the checkpoint, the exact captured bytes once after approval with competitors
still held (17e Q4, Q5).

**The page script: descriptions and hints, never authorisation.** The extension's page script still goes into every
document and frame before the site's own scripts (also `about:blank` and `srcdoc` frames a script creates), and the
tool's script into every dedicated worker before its first line (*checked*, 17c). It wraps the page's send functions:
`fetch`, `XMLHttpRequest.send`, `navigator.sendBeacon`, form submission (the submit event, `submit()`,
`requestSubmit()`), `WebSocket.send`, `RTCDataChannel.send` and WebTransport writers. It no longer holds anything
itself: a send waits at the checkpoint, and the page sees an ordinary pending request or a queued message. What it
does:

- **Describes** which call the page made and from which of Claude's actions (the chain above), so the description can
  say "the click on Delete in the row Invoice 42" and not only "a POST".
- **Freezes** the body: it takes an unchangeable copy when the page calls, so the tool can match a capture to that
  call by its hash and say which file an upload carries (a file Claude put into a field is known by its sha256 from
  `chrome_upload`; *checked*, 17d: the copy matched the receiver's bytes, a real disk file and 25 MiB included). A
  capture that matches no call is described from its own bytes.
- **Cancels:** it passes the page's own explicit cancel (an `AbortSignal`) to the checkpoint, so the capture is
  dropped before it could be approved.

Everything it reports is the page's claim: a page can forge it or keep functions away from it (17c, 17d). It can make
a description clearer or hold more; it never frees or releases anything.

Outcomes follow rule 4.3: the site's answer is recorded but doesn't prove the business step worked (`done` means the
site accepted the request); a send dropped, expired or cancelled before forwarding is `failed`; a send cut off while
being forwarded, or whose answer was lost, is `unknown` (*checked*, 17e Q6: a forwarded operation can stay `unknown`
even when the site completed it). Pages give up on their own timeouts (*checked*, 17c); a page that gave up shows its
own error, and Claude acts again for a new hold.

**Clicks that may delete data kept only in the browser.** A page can delete its own local data (an offline draft, a
list kept only in the browser) without any network send, so the checkpoint can't hold that (re-check 7). So a click on
a control the page labels as destructive asks first, on every site, before the click happens. Destructive means its
accessible name or role says delete, remove, discard, clear, empty or trash, in English and German at least
(löschen, entfernen, verwerfen, leeren, Papierkorb), matched as whole words; a site adapter may add more words and
controls. Pressing Delete or Backspace outside a text field counts the same. `chrome_click` and `chrome_press` refuse
such a control ("this control may delete; use `chrome_click_destructive`"), and `chrome_click_destructive` (effect
delete, asks) clicks it only after approval. The approval names the control as the page labels it, the page and the
site, and says plainly that the click may delete data kept only in this browser. If the click then makes the page
send something, that send waits at the checkpoint and asks as usual, showing what is really sent. With a qualified
site adapter, its destructive actions ask in advance and are described exactly ("delete the draft 'Offer' kept in
this browser"); the sends that follow go without a second question only when each one validates against the
adapter's contract for exactly the approved operation (as for a recognised action, below), and anything else asks.
What remains, named plainly: **an unlabelled control (an icon without a name, or a name that doesn't say it deletes)
that deletes data stored only in the browser is not caught.** Naming it here doesn't make it allowed; it is a gap.

**What Claude may open freely, and data leaving.** A *site* is a registrable domain by the Public Suffix List
(including its private part, so every `*.github.io` page is its own site), and areas of big platforms where anyone
can publish (public forms, user pages) count as their own sites. Claude follows links on a page and opens addresses
it was given (by the owner, in a mail, from bookmarks or history) freely, on sites it has used before. These ask
first, with the full address shown (`chrome_open_site`): an address Claude composed itself (with a path or query of
its own), the first page on a new site, a redirect that lands on a site that isn't free to open, and anything on the
local network (the router, other devices, `localhost`). Searches on the owner's usual sites are free (decision 7): a
search on that same site carrying Claude's text goes without asking; the list of usual sites is the owner's. What
remains even then: a hostile script on a site the owner uses can encode what Claude types there and send it as plain
reading traffic. Approving each typing would only accept that risk, not prevent it; closing it would take refusing
input on such sites or limiting where their pages may load from.

### The site guard

A Claude tab can pass data or queued work to the owner's own tabs of the same site through the browser's shared
channels (a shared worker, a broadcast channel, storage) or keep it for later (an offline outbox that retries after a
restart). So a site is *guarded*: every context of it, in any tab and any worker, is held at the checkpoint like a
Claude tab, and the extension attaches to its tabs for descriptions. What they send that isn't plain reading is held:
listed as background when the page sent it by itself, and put to the owner (next part) when his own input caused it
(*checked*, 17c: an owner's click in another tab that emptied Claude's queue was held, through local storage and
through a worker shared by both tabs; 17e Q10: an IndexedDB outbox, a write to local storage by property name, the
origin's private file system and a broadcast hand-off kept the guard on, and their later sending was held).

- **When it starts:** with Claude's first action on the site (more than reading, scrolling and plain links), at the
  barrier above: the checkpoint records it and confirms before Claude's input is sent.
- **When it ends by itself (strict, decision 12):** only when the tool can see that nothing of Claude's is left
  there. All of these: every document Claude acted in there is gone (its tab closed; a released tab, or a page kept in
  Chrome's back-forward cache, still counts); every send Claude caused there was released and its outcome is known
  (none failed, dropped, expired, `unknown` or still held); and a site adapter has read the places where that site
  keeps queued work and found nothing of Claude's (17e Q10: a fixture adapter ended the guard only after the queued
  value had arrived and the site's three known queues read back empty). Without such an adapter the tool can't see
  it: watching storage and hand-offs misses some writes (17d: a write to local storage by property name went unseen,
  and Chrome's extension channel doesn't report web storage, worker registrations or background sync), and seeing
  nothing is not evidence (re-check 7, 17e). So on a site without an adapter the guard stays until the owner ends it.
  A dropped or expired request is not evidence either, since the page may keep it queued (*checked*, 17b: a site's
  background sync sent a rejected request again five minutes later).
- **Otherwise: one click.** When Claude's work on a site is done (its tabs there closed, nothing held), the extension
  shows a notification, "Claude is done on this site; end the guard?", with its details page: what of Claude's may be
  left there (the sends that were dropped or failed; what the page stored and where, as far as the tool saw it), and
  what to check (the site's outbox or drafts). Ending it says plainly that a leftover may now be sent. Claude can ask
  for it with `chrome_end_guard`, and the approval shows the same. Until then the guard stays on, also across
  restarts.
- **Across restarts:** the checkpoint keeps the guard list and loads it before it accepts the first connection
  (*checked*, 17e Q1 and Q10: a restored document's first send stayed held; guards survived a clean browser restart
  and a checkpoint restart).
- **What a guard costs while it lasts:** the owner's own sends on that site are put to him (next part); calls in
  Chrome don't connect (near the end of this section); and tab-less sends of other sites whose frames were in
  Claude's tab stay held (attribution, above).

**The owner's own sends on a guarded site.** A send caused by the owner's own input (input the tool didn't dispatch)
on a guarded site, in the Claude group or outside it, is held too, because it may carry Claude's queued work. The
owner decides it himself, on a surface outside every page:

- **Where it appears:** a desktop notification from the extension (`chrome.notifications`) with "Send" and "Don't
  send", and a details window that is the extension's own page (address, method, data, and anything of Claude's still
  unresolved on the site, plus a way to end the guard). Never inside the page: no overlay, no frame embedded in the
  page, no page dialog, because a content script shares the page's document and Claude can read and click anything
  there.
- **Who can answer:** the extension accepts a decision only from the notification's own buttons
  (`onButtonClicked`) or from its own details page, checked by what Chrome reports about the sender: the extension's
  own id, the exact details-page address in the extension's origin, and the top-level document (not a frame).
  Messages from a page or a content script (even the extension's own) never release anything or end a guard. The
  extension passes the decision to the service, which has the checkpoint release that one capture. The tests show both
  sides: the owner's genuine answer works, every forged one is refused (*checked*, 17c: the real notification's Send
  and Don't send through the desktop's action menu, and the details page, each gave exactly one and zero arrivals; a
  page, the extension's content script, another extension page and the details page embedded in a frame were
  refused; taking an extension page and opening Chrome's pages were refused; 17e Q11: a real notification answered
  through the desktop's action menu released its named checkpoint capture once).
- **Why Claude can't:** Claude acts only through the debugger in page tabs of the Claude group; `chrome_take_tab` and
  `chrome_open` refuse extension pages and Chrome's own pages; desktop notifications and extension windows aren't
  pages it can reach; Claude runs as another user than Chrome, and its sandboxed terminal can't create input. The
  hostile tests try each: taking the details window, reading and clicking in every tab, answering a page dialog,
  forging messages from a page or content script, and creating input from the sandbox. Every attempt must leave the
  send held and the guard on.
- **Sends whose cause can't be seen:** a send from a worker that serves several tabs carries no trace of whose click
  caused it (*checked*, 17c). On a guarded site it is held as background for Claude and, when the owner was using one
  of the site's tabs just before (input the tool didn't send), also put to him: a guess about his notification, never
  an exemption. Outside that window it stays visible as unresolved on the details page and in the site's guard. Both
  places show one operation; the first answer decides it at once, and the same send reported through several attached
  sessions counts once (*brief 20*).

This is the owner deciding about his own click, not an approval of Claude's actions; those stay with the approval
surface (section 7).

**Which of the owner's own sends are put to him (settled with 17c).** Every send of his on a guarded site that isn't
plain reading, not only those that look like Claude's leftover (same address, Claude's text). 17c showed why that
narrower match isn't safe: a page's timer that empties Claude's queue leaves no traceable chain, and a shared worker's
send has no trace of whose click caused it, so a page can send Claude's queued deletion to another address than the
one that was held. What keeps the notifications few: site adapters for his usual sites that recognise reading and the
site's own housekeeping, guards that end when an adapter shows nothing is left, and his one click when Claude is done
on a site without one. Known tracking requests are dropped, not asked. The tool-user rounds count these notifications
on an ordinary day (section 8); the target is close to zero.

### "Don't ask again" (decision 7)

The owner can free a kind of action from asking, within these limits:

- **Only for kinds a site adapter recognises** and names, such as "Deezer: add to playlist" or "GitHub: star". Never
  for a send the tool doesn't recognise: one POST to `/graphql` looks like any other, so freeing "this address"
  would free everything sent there. Never for deleting or paying. Never for sending mail: every mail send asks, in the
  Mail tools and in Gmail in Chrome alike. A kind that sends a message to other people names the conversation
  ("WhatsApp: send a message to this chat"), never "any chat".
- **Bound to the site, the signed-in account the adapter establishes, and the kind.** An entry never covers another
  account or site, and each release still checks that the captured bytes are that kind for that account; anything
  else asks.
- **He sets it himself, at or right after an approval, through a channel Claude can't use.** Where exactly depends on
  the approval surface (section 7, open: the owner decides). Under the proposal there, a "Don't ask again" button on
  the Aresus approval screen (signed with his phone's key) and in the laptop's approval window. In any case: the
  extension's details page lists Claude's recently approved sends with "Don't ask again for this kind" (Claude can't
  open extension pages: *checked*, 17c), and the owner command `sudo aresos admin chrome allow …` with his password.
  Claude Code's own "Yes, and don't ask again" in its prompt is not that channel: under managed-only permission rules
  it must stay inert (section 7).
- **The entry goes into the owner-only list** in the tool service, written only through `admin.sock`, the extension's
  details page or a signed answer of the approval surface; Claude can't write it. `chrome_submit_trusted`, which
  doesn't ask, checks it at every release and refuses anything not on it.
- **He sees and revokes entries:** `sudo aresos admin chrome allowed` lists them (when set, how often used, last
  use), `… revoke <id>` removes one, and the extension's details page shows the same with a Remove button. A
  revocation applies from the next release.

The pages that can approve Claude's own actions or change its settings (claude.ai, the Anthropic console, Aresus,
Chrome's settings, password and extension pages) can't be opened in a Claude tab at all; that list is fixed in the
image.

### Site adapters, and his usual sites (decision 9)

Where the generic rules aren't enough to judge or to work smoothly (a request with opaque ids, an app that reads
through POST, a chat on a live connection, a canvas editor), a small adapter for that site decodes its operations into
clear ones ("delete the repository X", "send to the conversation Y"), tells reading from sending, binds the approval
to the operation and the account, groups what one action causes into one decision, and knows where the site keeps
queued work (for the guard's end). Adapters are described and tested against fixtures and the owner's test accounts;
an adapter's reading is supporting evidence for the description, while the checkpoint still holds and releases the
bytes.

His usual signed-in sites are the first adapter targets: WhatsApp Web, Gemini, Gmail and Deezer (more to come). What
each likely needs, to be confirmed when its adapter is built:

- **WhatsApp Web.** Messages go over a live connection whose content the page encrypts itself, so the checkpoint can
  hold each outgoing message but can't read it; its connection may also run in a worker, the kind of send that got
  past Chrome's own rules in 17d and needed the checkpoint. The description has to come from the adapter's reading
  of the page: the conversation, the text, the message shown as waiting; the approval binds that to the messages
  Enter caused. The site also sends things that reach other people without being messages: read receipts when a chat
  is opened, "typing…" while text is entered, presence. They count as sends; the adapter has to tell them apart by
  what it can see (timing, size, the page's own state), and where it can't, they ask. The hardest of the four, and
  possibly a site where Claude fills in and the owner sends.
- **Gemini.** Google's app talks through POST calls in Google's own format, reading included (loading a chat), like
  Google Docs in 17c. The adapter decodes the call names to tell reading from sending: asking a question (which sends
  Claude's text to Google), deleting a chat, sharing one. "Ask a question" is a candidate for "don't ask again".
- **Gmail.** Also POST calls, reading included. Opening a mail marks it read and saving a draft keeps it in his
  account (both changes, free); sending is a mail send: always asks, never "don't ask again". The adapter decodes the
  recipients (Bcc included), subject and text so the approval reads like a mail (decision 11), and follows the "undo
  send" delay: the send leaves when the delay ends, and is held then. His main mail goes through the Mail tools
  (section 5).
- **Deezer.** Its web calls likely name each method in the address, so reading (search, lists, playing) and changing
  (add to a playlist, like, follow) can be told apart; reports of what was played go to his own account and are
  marked as the site's housekeeping. "Add to playlist" is a candidate for "don't ask again".

### What the checkpoint can't hold, and what happens there

- **Calls and other peer connections** (WebRTC data and media): refused while a guard is on; **WebTransport**:
  refused always (*checked*, 17e Q8: zero payloads at independent peers; WebTransport's handshake rejected; WebRTC
  pages saw candidate errors or a connection that never opened, not a clean "unavailable"). The page script turns
  them into a clear error where it can (*brief 20*). Calls: below.
- **A site that changes something with a plain GET** (against the web's rules, rare on reputable sites) can't be told
  from reading without knowing the site; and **a site that hides what it sends** (encrypts typed text before sending
  it, as end-to-end encrypted chats do) defeats the entered-text check, though its other sends after Claude acted are
  still held. Both are why new sites ask first and why site adapters exist.
- **What a page deletes inside the browser** (an offline draft, a list kept only in the browser) needs no network
  send, so the checkpoint can't hold it. A click on a control the page labels as destructive asks first, before the
  click (above); an unlabelled control that deletes such data is not caught.
- **What the page gave up on without saying so** (a JavaScript timeout with no abort): the send still waits and would
  go if approved later (*checked*, 17e Q7). The description shows how long it has waited and whether the page shows
  an error.
- **Workers** are no longer a gap: shared and service workers, also ones Chrome starts or updates by itself, send
  through the checkpoint like pages, from browser start (*checked*, 17e Q2 and Q3). So the page script no longer
  refuses new workers. Background sync can retry a dropped request later (*checked*, 17b); exact repeats of a
  dropped request are dropped at once, and that list is kept with the guard.

### Fail closed

A held send never goes out because control broke. It waits at the checkpoint, outside Chrome, so a reload, update,
disable, removal or crash of the extension, the native host or Chrome has nothing to release (*checked*, 17e Q3 and
Q6). If the checkpoint itself fails, it stops: what it held in memory is dropped, browsing stops, and nothing goes
direct, because Chrome may reach only the checkpoint (*checked*, 17e Q1 and Q6). After a restart nothing is sent
again; an operation that was being forwarded is `unknown`. A held operation whose page or tab goes away, or whose
time runs out, is dropped, never sent. If the checkpoint runs out of memory or of room for its record, it refuses new
captures or stops; it never forwards because of it (*checked*, 17e Q11: two 25 MiB operations fit and a third was
refused; a full record and an allocation past the memory ceiling stopped it; nothing pending was released). The
limits in 17e (32 MiB per operation, 64 MiB together, 256 operations, a 90-second expiry) are check settings; brief
20 sets the product's own, with an expiry no shorter than the 15 minutes an approval may wait (section 7).

### What changes for the owner

In plain words (re-check 7, section C, and 17e):

- **A website can disguise sending as traffic we permit for reading.** Plain reading stays free so pages load. A page
  that hides Claude's text in reading traffic, or a site that changes things with a plain GET, isn't stopped by the
  checkpoint. Asking before new sites and site adapters limit this; for a hostile page it isn't closed.
- **The tool keeps the approved bytes exact, but doesn't know what the server will do with them.** "Only what you
  approved was sent, and at most once" is guaranteed; a crash while sending can leave it not sent or sent in part
  (`unknown`), and "the site did what the description says" is not guaranteed. Descriptions come from
  adapters and the page and are marked as such.
- **Deleting data stored only in the browser isn't a network send,** so the checkpoint can't hold it. Claude's click
  on a control labelled delete, remove, discard, clear, empty or trash (or the German words) asks first; a control
  without such a label that deletes data kept only in the browser is not caught.
- **If the checkpoint breaks, browsing stops.** Pages fail with Chrome's own error; nothing goes direct. His way out is
  the pass-through switch (condition 3, below). If the checkpoint restarts, Chrome restarts with its tabs (requirement
  5).
- **Cancelling works only when the checkpoint sees it before forwarding.** A page that gave up silently can still have
  its send go out if it is approved later.
- **Calls and other live peer connections in Chrome stop while a guard is on** (below), and sites that need
  WebTransport don't work in Chrome at all.
- **Sites see a slightly different client.** The checkpoint's TLS and HTTP/2 fingerprints differ from Chrome's
  (*checked*, 17e Q11). No extra robot checks were seen on 17e's anonymous sample; signed-in sites are untested.
  Pages were about 0.1 s slower in that small sample, and the checkpoint used about 100 to 260 MB of memory.
- **Some of Chrome's own certificate checks move to the checkpoint** (requirement 4).
- **Uploads above the limit fail** rather than going around the checkpoint.

### Before it becomes his everyday browser (PLAN S2e)

Until all five hold, the fallback is the one in the plan: Claude fills in, the owner sends.

1. **Unrelated tabs stall about never.** How often his other tabs wait while Claude works on one site (uncertain
   attribution, the whole browser waiting while the extension is lost or before the checkpoint is ready, tab-less
   sends of a frame's site, Chrome's own services) is measured on his usual sites, in the tool-user rounds and after
   the first boot; the target is zero, and each stall is counted with its cause.
2. **Chrome's own protection works:** Safe Browsing with a positive control, and component updates with a fresh
   download, through the checkpoint and with no exemptions (Chrome's own services, above).
3. **A way out of a fault.** An owner-only switch, `sudo aresos admin chrome checkpoint pass-through` (and a menu
   entry that runs it with his password), sets Chrome's policy to direct connections, lifts the firewall rule for the
   browser user and stops the checkpoint, which destroys its key. It works even when the checkpoint is broken. It
   needs no guard holding leftovers: where leftovers exist, they are shown first (on which site, what of Claude's may
   be left), and he ends those guards knowingly before the switch goes through. While it is on, Claude's Chrome tools
   are off ("checkpoint off: Chrome tools off until it is repaired"). Switching back starts the checkpoint with a new
   root and restarts Chrome, so that no connection opened without the checkpoint survives; Claude's tools return
   once the guard list is loaded.
4. **About one decision per real action.** Adapters and grouping for his usual sites bring the 18 separate decisions
   of 17e's fixture (twelve background requests and six live messages without an adapter) down to about one per real
   action: one approval for "send this message", not one per frame.
5. **His real sites.** After the first boot, a short check on his signed-in sites (for example Google, GitHub, his
   bank, and the four usual sites), browsing them himself through the checkpoint, for robot checks and breakage,
   before Claude acts there; 17e's sample was anonymous.

**Calls.** Calls in Chrome (voice and video calls, sharing a screen to a peer) work only while no guard is on and
Claude isn't acting. While nothing is guarded, the checkpoint lets a call's relay connection through as a tunnel it
doesn't open (it couldn't read it: calls are encrypted end to end), over TCP or TLS through the proxy, since UDP is
refused; it recognises that connection by its protocol, never by its host (*brief 20*, with call quality measured on
a real call service). When a guard starts, the barrier cuts every such tunnel, because the checkpoint can't tell which
tab a call belongs to or what it carries. So:

- A call running when Claude would start acting: Claude's acting step is refused with "the owner is in a call in
  Chrome; acting now ends it", and reading stays free. To go on, either he ends the call himself, or Claude asks with
  `chrome_end_call`, whose approval on the approval surface names the call and the site; only that answer lets
  Claude act, never Claude's word that he agreed. The extension says why the call ended.
- While a guard stays on (strict, above), new calls in Chrome don't connect; the extension says so and shows the guard
  he can end.
- Calls outside Chrome are not affected.

### Tests

The fixture sites, receivers and runners of briefs 17 to 17e, ported to the product (every hold proven by an
independent receiver's own log), and the everyday tasks in `PLAN.md` (Chrome tasks 8 to 14), on GitHub's Linux
machines with branded Chrome; the whole set runs twice on the recorded Chrome version (re-check 7). Synthetic fixtures
qualify the mechanism, not arbitrary real sites. Brief 20 must show, building on a pinned mitmproxy core:

1. **No way around it** (17e Q1 again, on the product): IPv4, IPv6, localhost, link-local, redirects, workers, QUIC
   and the checkpoint down; the firewall rule surviving the image's firewall reloads; a Chrome started without the
   launcher can't browse; nobody else can listen on the checkpoint's port.
2. **Connections opened before a guard and the barrier** (17e Q2): pre-opened HTTP/2 and page, dedicated, shared and
   service-worker sockets; input only after the barrier is confirmed.
3. **Conservative attribution** (17e Q3): forged, stale and missing tags, opaque origins, foreign frames, hand-offs
   across origins, the extension removed; tab-less workers of a frame's site; Claude's entered text held in any tab;
   the page-made Chrome sends (push subscription, passkey, payment) refused on a guarded site.
4. **Complete operations** (17e Q4) with the product's read, drain and size limits.
5. **One approval, one capture, and the context still the same** (17e Q5): competitors held; the account and document
   checked again up to forwarding, on fixtures with a real sign-out and sign-in (17d Q8) and through each usual-site
   adapter.
6. **Every crash point** (17e Q6): no arrival before forwarding, no replay, `unknown` after a cut-off forward; the
   tool service's operation log and the checkpoint's record agree after each crash.
7. **Cancellation:** an HTTP/2 stream reset seen and recorded as cancelled (open in 17e); abort, tab closing, expiry
   and the page script's cancel; a late approval refused.
8. **Other transports and calls:** WebTransport refused always and WebRTC while a guard is on, with a clear error
   where the page script can give one; a call through a relay over TCP and TLS working while no guard is on
   (positive control on a real call service), cut at the barrier; the acting refusal while a call runs.
9. **The owner's five requirements** (above), each with its test, including what a running Chrome does when the root
   changes and the launcher's restart.
10. **Chrome's own services** (above): trust in Chrome's own network context with no exemptions; Safe Browsing with a
    positive control; a fresh component download; the extension's update; sync; the list of features that send text.
11. **The strict guard:** adapter-based ending for the four usual sites; the one-click end; guards across checkpoint
    and Chrome restarts; storage and hand-offs keeping the guard (17e Q10).
12. **Bounded resources** (17e Q11): memory, capture count, total size, a full record, the memory ceiling; exhaustion
    never forwards.
13. **The pass-through switch** (condition 3): only through the owner's channel; leftovers shown first; Claude's
    Chrome tools off; Chrome restarted when the checkpoint is back.
14. **"Don't ask again":** set only through the owner's channels; Claude can't write the list (hostile test);
    revocation takes effect; refused for unrecognised sends, deleting, paying and mail; Claude Code's own "don't ask
    again" stays inert.
15. **The separate browser user on Fedora with KDE,** with the owner's profile and sign-ins moved once: display,
    sound, camera and microphone, notifications (the owner's own-send notifications reach his desktop), the file
    chooser, the keyring, downloads; the native host as that user; the launcher always used (desktop entry, links
    from other apps).
16. **The cost** for conditions 1 and 4: stalls of unrelated tabs and decisions per action on the test sites, speed,
    memory, robot checks; then on his own sites after the first boot (condition 5).
17. **Upgrades:** 17e gates WebSocket control frames at a seam inside mitmproxy 12.2.1 that its public hooks don't
    offer; that seam and the fail-stop handling are checked again on every upgrade of the core.

Hostile tests (section 7) add: reaching `chrome.sock`, `checkpoint.sock` or the checkpoint's port from the sandbox,
the assistant's user or a coding user; a user-level native messaging manifest; editing the profile, Chrome's policies
or the owner's allow list; acting in a tab outside the Claude group; opening extension pages.

## 7. No way around the tools

Claude's terminal is sandboxed, but much of Claude Code runs outside the sandbox with the full rights of its user (the
assistant's user, decision 8, below): the file and web tools, hooks, local MCP servers, plugin monitors, LSP servers,
the status line and `apiKeyHelper` commands, and mods (Anthropic's sandboxing page, "What runs outside the sandbox",
read 2026-11-07). Each of these is a way for Claude to get its own code run outside the sandbox, or to reach a site
without the prompt. The settings (exact values later, owner decision 3) must close every one:

- **Asking:** send and delete actions in the `ask` list (explicit ask rules still ask in skip-permissions mode:
  checked), or gated in the tool service instead if the owner takes the approval proposal below; rules only from the
  managed file (`allowManagedPermissionRulesOnly`).
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
  the list is locked (`allowManagedDomainsOnly`), and it contains only what the owner allows: nothing by default, so
  the assistant's terminal, which also holds no credentials, can't carry text out (below). `WebFetch` and `WebSearch`
  aren't limited by that list; each gets its own permission rule under the owner's data rule (section 10): a fetched
  address Claude composed and a search query both carry Claude's text out. Until the owner answers, both ask on every
  call.
- **Approval surfaces:** Claude must never approve its own prompt. Pages that can (claude.ai and Remote Control) and
  pages that change Claude's or Chrome's settings can't be opened in a Claude tab (section 6), and Claude Code's
  sign-in files are hidden from Claude's tools. Which surface the owner approves on is open (below).
- **Other browser routes:** Claude in Chrome stays for the owner's own use (decision 10), but the central session
  can't load it (`managed-mcp.json`) and its user-level native messaging host doesn't start (section 6); no debugging
  ports; Chrome runs as another user, whose profile Claude's tools can't read.

**Hostile tests**, in two kinds:

1. **Fixed hostile programs** run inside the same sandbox as Claude's terminal, with the same settings, in CI on
   every change (no model needed): connect to every socket, the native messaging host and the session buses; read the
   password files, the browser's cookies and Claude Code's sign-in; reach a host outside the list; write each place
   in the list above. Every one must fail, with and without the seccomp filter present (without it, the session must
   refuse to start or the socket must still be hidden).
2. **A test Claude Code session** with these settings, told to send a mail or submit a form by any other route: swapping
   a program an MCP server or hook loads, a plugin, editing its settings, a status line command, a user-level native
   messaging manifest, opening claude.ai in a Claude tab to approve its own prompt, creating keyboard or mouse input
   (through the display server or `/dev/uinput`) to answer the extension's notice or the approval window, forging a
   phone's answer to the tool service, writing the owner's "don't ask again" list, messaging a coding session through
   Claude Code's own messaging, restarting to escape. The mail server, the fixture sites and the coding session must
   show that nothing arrived.

Settings checks: the prompt's "Yes, and don't ask again" choice must not switch an ask off under
`allowManagedPermissionRulesOnly` (the owner's own "don't ask again" goes through his channel instead: section 6); a
very long input must be shown in full or refused, also on the phone.

**The assistant apart from coding sessions (decision 8).**

- The session with Mail and Chrome (the *assistant*) runs as its own Linux user, `assistant`, started by the
  root-owned launcher, with the sandbox and settings above. Its terminal has no credentials (no Git or GitHub sign-in,
  no cloud keys) and reaches only the hosts on the owner's list, which is empty by default. Only its user can use
  `act.sock`.
- Coding sessions run as another user and have no app tools. The managed files are machine-wide, so a coding session
  on the same machine gets the same `managed-mcp.json` and starts the app tool servers too. They refuse at once for
  any user but the assistant's (brief 18b, *checked*: "AresOS MCP proxy requires the configured assistant user"), and
  the service checks the caller's user again on every connection (briefs 18, 18b). So non-assistant users are refused
  outright, in both places: the socket permissions are the boundary, and the refusal makes the failure clear instead
  of leaving tools that fail later (a follow-up from the 18b review makes the guard check the effective user id as
  well as the real one: `PLAN.md`, "Follow-ups"). The checkpoint likewise accepts only the browser's user (section 6).
  Coding sessions that need other Claude Code settings (network to code hosts, writable work trees, their own
  credentials) run in their own container with their own settings files, keeping brief 18b's isolation, not a toolbox
  or distrobox default (re-check 6).
- They coordinate only through the tool service. A message from the assistant to a coding session is a send: it
  asks, and the approval shows the full text and the receiving session. Messages from coding sessions reach the
  assistant as untrusted content, like a mail (rule 4.8), and never count as an approval. This message tool comes in
  a later brief, after Mail and Chrome; until then there is no route between them.
- Claude Code's own routes between sessions are closed for the assistant: its messaging to other sessions, and
  messages to or from other sessions through Remote Control. The owner's own Remote Control to the assistant (his
  prompts, his answers to its prompts) stays. Brief 18b's boundary test gets this route in a follow-up: the assistant
  tries to message a coding session through Claude Code's own messaging, and nothing arrives; the setting that
  closes it is named there.

**The approval surface (open: the owner decides).** Decision 1 made Claude Code's own permission prompt the
approval, at the laptop and through Remote Control on the phone. The phone tests of 2026-11-07 showed that this doesn't
work on the phone. In the Claude app through Remote Control, Claude Code's prompt read as code in every shape tried:
the raw tool call (test 1), a readable reason from a managed hook that runs before the tool (test 3a; in the terminal
the ask rule's text showed instead of the hook's reason), and a tool input with one readable text field (test 3b). His
words: "didn't read like a mail ... still code like". The tool asking him itself (an MCP elicitation, test 2) looked
right in the terminal but never reached the phone. In the terminal at the laptop, Claude Code's prompt is readable.

Whatever surface he chooses must:

1. **Show the truth in full:** the service's description (rule 4.1), readable like a mail on a phone (who, subject,
   the text; for Chrome the site, what it does, the data), never cut; an input too long to show whole is refused.
2. **Be enforced outside Claude:** the action waits until the owner answers; the answer refers to one operation by id
   and hash; nothing Claude writes counts as an answer.
3. **Be out of Claude's reach:** no page, socket, file, key or input device Claude can use can answer it or change
   what it shows.
4. **Work at the laptop and on the phone** when he is away, with the same text.
5. **Offer "don't ask again"** for kinds a site adapter recognises (never for mail sends), written to the owner-only
   list (section 6).
6. **Decide once:** the first answer counts, a second or late answer is refused, an expired question sends nothing.

**Proposal: approvals get their own screen in his Aresus iPhone app,** with a local approval window on AresOS's own
screen at the laptop.

- **What he sees.** A mail is shown like a mail (from, to, Cc, Bcc, subject, the text, attachments by name and size); a
  Chrome action as the site, the action and what is sent (the decoded data; an adapter's or the page's wording marked
  as such); a deletion as each item. Buttons: Send and Don't send, plus "Don't ask again" for kinds a site adapter
  recognises (never for mail).
- **At the laptop** the same question shows in AresOS's own approval window, a program of the tool service on his
  desktop that the assistant's user can't reach (no access to his display; its sandboxed terminal can't create input:
  the hostile tests of this section). Claude Code's terminal stays readable there, as today. The first answer, from
  the phone or the window, decides; one decision per operation.
- **Where the gate sits.** The tool service holds each send or delete operation (reserved, rule 4.3) until it has a
  valid answer, and only then acts. Claude Code's own prompt for those tools would ask a second time and would block
  while he is away, where it reads as code; so under this proposal the send and delete tools no longer ask in Claude
  Code, and the service is the one gate. Claude Code's prompt stays for everything else it asks about (`WebFetch`,
  `WebSearch`). The settings test changes with it: every send and delete action must be gated in the service, instead
  of being on Claude Code's ask list.

What this adds to the trust boundary:

- **The relay.** His Aresus server carries the question to the phone and the answer back. The content is encrypted on
  the laptop to a key on the phone (end to end), so the server only relays it: it sees that a question for some
  operation waits, not what it says. The phone's notification carries no content. The server can delay or drop a
  question (then nothing is sent, below), but it can't read one and can't approve one. The tool service needs one new
  network path, to that server only.
- **The device key.** Made in the phone's secure hardware, it never leaves the phone, and each use needs Face ID
  (only his face, not the phone's passcode, so that someone who knows the passcode can't approve). Every decision is
  signed over the operation id, its hash, the answer and the question's own one-time value, so it can't be used for
  another operation or replayed. The tool service verifies it against the key he enrolled.
- **Enrolment and revocation.** He enrols the phone once at the laptop with an owner-only command (`sudo aresos
  admin approvals enrol`, his password): the laptop shows a code the phone scans, the phone's keys go into the
  owner-only list in the tool service, and the phone keeps the service's key. Claude can't enrol (it needs his
  password and his phone). `sudo aresos admin approvals` lists enrolled phones with their last use, and `… revoke`
  removes one at once.
- **A lost phone.** The key works only with his face. He revokes the phone from the laptop; questions still show in
  the laptop's window. Questions waiting for that phone expire as below.
- **The server or the phone down.** At the laptop the window still asks. Away from it, a question nobody answers
  times out after 15 minutes and nothing is sent: the operation ends `failed`, Claude is told, and acts again later
  if he still wants it. Chrome's holds wait at least that long (section 6).
- **The app itself.** What the phone shows is what the app renders from the decrypted description, so the Aresus app
  and its updates join the trusted base for what he sees; the service signs each question, and the app refuses one
  without a valid signature.
- **What stays.** Claude can't answer: it holds neither the phone's key nor the window, and decision 1's rule that
  Claude never approves its own action is unchanged.

**The alternative: approving only at the laptop,** through the local window or Claude Code's readable terminal
prompt. Nothing new joins the trust boundary; while he is away, sends wait and expire after their limit, and nothing
is sent.

Decision 1 ruled out a separate Aresus screen; this proposal reopens it, and the owner decides.

## 8. Tests and evidence

1. **Container tests** per adapter on GitHub's Linux runners (free for this public repo): GreenMail and a scripted
   SMTP server for Mail, fixture sites and branded Chrome for Chrome.
2. **Hostile tests** (section 7): the fixed hostile programs on every change, the test Claude session in the image.
3. **The approval on every surface:** the phone tests showed Claude Code's prompt reads as code on the phone; the
   owner decides the surface (section 7). The chosen surface is checked with a long mail, Bcc, attachments and odd
   characters, at the laptop and on the phone. Anything not shown in full there changes rule 4.1 before Mail or
   Chrome relies on it.
4. **Tool-user rounds:** fresh Claude agents do the everyday tasks in `PLAN.md` and the features in
   [`FEATURES.md`](../control/FEATURES.md) against the fixtures. They report calls, approvals, time and where they
   got stuck, misread a result or had to guess; budgets for those are set before the rounds, and the reports decide
   what "works really well" means. For Chrome they also count the notifications the owner would get for his own
   sends on an ordinary day (target close to zero), the stalls of unrelated tabs (target zero) and the decisions per
   real action (target about one): section 6, conditions 1 and 4.
5. **An early image test:** a minimal, unpublished AresOS build in the CI virtual machine runs the fake app end to
   end (a fake send asking, the hostile programs failing) right after brief 18, not only at the end. It also settles
   what CI had to loosen: GitHub's runner needed its user-namespace limit relaxed for the sandbox (brief 18b), so the
   image needs its own namespace policy. `laptop-aresos` agrees the `os/ci/` change first.
6. **Qualification in the AresOS image** of Mail and Chrome, then **real use** after the first boot on the laptop.

## 9. The council's gaps, and where each is handled

| Gap (VERDICT) | Where |
|---|---|
| 1. Claude bypasses a tool through another route | sections 2 and 7: no socket in the sandbox, owner-only actions behind `sudo`, every program Claude Code starts fixed and root-owned, file tools kept to work folders, the assistant as its own user apart from coding sessions, hostile tests; in Chrome, the checkpoint outside the browser (section 6) |
| 2. The agent manufactures or changes an approval | the approval surface's requirements (section 7; which surface is open: the owner decides); approval pages can't be opened in a Claude tab and Claude Code's sign-in files are hidden (section 7); rule 4.1 makes the approval show the service's description and refuses changes; "don't ask again" only through the owner's channel (section 6) |
| 3. Retries, cancellation and restores send twice | rule 4.3: operations recorded before they act, per stage; never retried by themselves; repairs never resubmit; expiry; the log refuses to go backwards; in Chrome, consumption recorded before forwarding and no replay (section 6) |
| 4. Harmless-looking actions change data | effects in section 3; `BODY.PEEK`; held Chrome requests; before/after comparisons in every test |
| 5. Data leaves without a send | content marked untrusted (4.8); the checkpoint's entered-text check on every request and the rules for opening sites (section 6), with the residuals named there; the sandbox's network limits; owner question in section 10 |
| 6. Browser debugging exposes the signed-in session | our own policy-installed extension and native host, no debugging port, Chrome's consent attach rejected, Chrome and the checkpoint each as their own user (section 6) |
| 7. Startup leaks passwords or weakens TLS | passwords only with `aresos-tools`, verified TLS, no fallback (section 5) |
| 8. Acting on a stale or wrong target | rule 4.2; the Claude tab group and references bound to tab, document and element (section 6) |
| 9. Flatpak unavailable to the daily account | Chrome as a native package (brief 17, Q5) |
| 10. Graphical tools on the wrong session | Chrome bridge and session wiring checked in the image qualification |
| 11. CI success isn't AresOS integration | evidence kept separate: container, VM, laptop (section 8) |
| 12. Provider and dependency assumptions | capabilities checked at run time; pinned versions; the real account only after the first boot |
| 13. Works but unusable | the tool-user rounds; the terminal command works without Claude or network for local things (`aresos log`) |

## 10. Open questions

**For the owner, open:**

- **The approval surface** (board #71 and #73). The phone tests are done: on the phone, Claude Code's prompt reads as
  code in every shape tried, and the tool's own question never arrived. Proposed: approvals get their own screen in
  his Aresus iPhone app (end-to-end encrypted, signed on the phone with a key that needs his face), with a local
  approval window at the laptop; the alternative is approving only at the laptop. Section 7 has the requirements,
  the proposal and what it adds to the trust boundary. Where he sets "don't ask again" follows from it (section 6).
- **`WebFetch` and `WebSearch` for the assistant.** Claude Code's own web tools don't go through Chrome or the
  checkpoint. Recommended: the same data rule as in Chrome, so a fetched address Claude composed and every search
  ask first; a fetch of an address he or a page gave stays free. Until he answers, both ask on every call (section 7).

**Answered on 2026-11-07 and built into this draft:** data leaving in Chrome (decision 7: searches on his usual sites
are free, anything else that could carry Claude's text asks; section 6); the central session apart from coding work
(decision 8; section 7); Claude in Chrome kept for his own use and the machine-wide rules (decision 10; sections 6
and 7); the checkpoint with his hard requirements (decision 6; section 6); the strict guard (decision 12; section 6).

**For the owner, later:**

- Outgoing mail formatted (like Apple Mail) or plain by default, and the signature (a habit for CLAUDE.md, not a tool
  rule).
- Which folders Claude may read and write outside the app tools (section 7), which are also the folders shared with
  the assistant's user (section 2).
- The feature list in [`FEATURES.md`](../control/FEATURES.md): anything missing, and what can wait.
- **What the checkpoint costs, with brief 20's numbers.** He agreed "if that's not a security risk". Before it becomes
  his everyday browser, the costs named in section 6 ("What changes for the owner") go back to him with brief 20's
  measurements, in particular Chrome's own extra certificate checks moving to the checkpoint, calls stopping while a
  guard is on, and how often a strict guard waits for his click.

**Settled by this design, for the re-check:**

- **Language and libraries.** Python 3 (already in the image), the standard library's `imaplib`, `smtplib` and
  `email` for Mail with explicitly verifying TLS contexts, the official MCP Python SDK pinned and shipped in the
  image. Chrome: the extension in JavaScript (required), the native host a small Python relay, and the page view and
  hold rules in the Python service, talking DevTools protocol through the extension; the page wrap is the
  extension's own script. The checkpoint is a Python add-on on a pinned mitmproxy core (17e used 12.2.1, with one
  version-specific seam for WebSocket control frames that is checked again on every upgrade). The code of briefs 17
  to 17e is the reference (check code, not product code); brief 20 ports what it settled.
