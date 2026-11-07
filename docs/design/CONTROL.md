# The control layer: design

**Status:** draft 14, 2026-11-07. Covers the shared base, Mail and Chrome. The frontier review
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
after the phone tests (open: the owner decides). The eighth re-check
([8](../../reviews/control-design/2026-11-07-RECHECK-8.md)) found six blocking points in draft 10, and draft 11
answers them: uncertain reading held until the checkpoint is ready, clicks that may delete local data ask first, what
a recognised action is, three separate users with no shared files, every place the root is installed, and the exact
upstream TLS checks with what is lost. The ninth re-check ([9](../../reviews/control-design/2026-11-07-RECHECK-9.md))
closed three of them and found one new point; draft 12 records every input before it reaches Chrome, makes unlabelled
local-only deletion an owner question, checks upstream certificates with Chrome's own current data, and bounds a
destructive action approved in advance. The tenth re-check
([10](../../reviews/control-design/2026-11-07-RECHECK-10.md)) closed the input barrier and the advance approval; draft
13 states both options for unlabelled local-only deletion truthfully and makes Chrome's own security data a precise
contract (paths, what the trust rests on, a version gate, freshness from the data's own fields, recovery when it is
out of date). After the eleventh re-check ([11](../../reviews/control-design/2026-11-07-RECHECK-11.md)), draft 14
discloses option (b)'s exceptions, counts only evidence as freshness, ties recovery to verified tag coverage, and
turns three points settled more narrowly than the owner asked into owner questions (his folders, the scope of "don't
ask again", WhatsApp Web). Points marked *checked* name the check that showed them; points marked *brief 20* must be
shown by the Chrome build's own tests before anything relies on them.

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
| Coding sessions | Claude Code sessions for coding work, without the app tools (section 7). | user `coder` |
| Claude Code settings | `/etc/claude-code/managed-settings.json` and `managed-mcp.json`, owned by root (section 7). Exact values come once the tools exist (owner decision 3). | |

**Who can reach what:**

| From | `act.sock` | `admin.sock` | Passwords and sign-in data | Chrome's control channel |
|---|---|---|---|---|
| The owner's own terminal | as the assistant's user (`sudo -u`) | with `sudo` | no | only through the tools |
| Claude through its MCP tools (local MCP servers run outside the sandbox) | yes; send and delete ask first | no | no | only through the tools |
| Claude's terminal commands (sandboxed) | no | no | no | no |
| Claude's file tools (Read, Edit, Write; outside the sandbox) | no (they don't open sockets) | no | no: another user's files, plus deny rules | no |
| Coding sessions (user `coder`, section 7) | no; the MCP proxy refuses them | no | no | no |
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
around Claude, and section 7 lists every way Claude could start such a program and how each is closed.

**Three users, and what each can read.** The owner (his own user), the assistant (`assistant`) and coding sessions
(`coder`, as in brief 18b's isolation check) are separate users; coding sessions never run as the owner. Which of
the owner's folders the assistant may read, and which it may change, is **owner decides (open, section 10)**. Until he
answers, the assistant writes only into its own folders (rule 4.4), which the owner can read and the coding user
can't, and reads the folders he shares with it, read-only. Whatever he chooses, the rule stays: nothing the assistant
can write is readable by a coding session (section 7).

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
   opens a path in the owner's home. The MCP proxy, running as the assistant's user (section 2), opens the file and
   hands the bytes over; the service keeps them as an unchangeable copy by hash and sends exactly those. Claude Code's
   file-tool limits don't apply to MCP tools, so the proxy enforces its own:
   - **Reading** (attachments, uploads) only from the allowed folders: the assistant's own, and the owner's folders
     he shared with it read-only (for example `~/Documents`, `~/Downloads`, `~/Desktop`); never from places that
     hold credentials or configuration (`~/.ssh`,
     `~/.gnupg`, `~/.config`, `~/.local/share`, the browser profile, `~/.claude`, any dotfile), opened component by
     component under the allowed folder without following symlinks, regular files only, with a size limit. The
     prompt shows the real path.
   - **Saving** the other way: only into the assistant's own output folders (saved attachments, downloads, work
     files), which the owner can read and the coding user can't (section 7), with safe file names, never
     overwriting, never into configuration or start-up places. Whether the assistant may also change folders of
     his is **owner decides (open, section 10)**; if he picks some, writes there go through the tool service with
     these same limits, and the coding user can't read those folders.
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
- **"Don't ask again" for mail: owner decides (open, section 10).** If he takes it, an entry names the account and
  an exact set of recipients (To, Cc and Bcc together, for example only himself), set and revoked only through his
  own channels (section 6); a free send action then sends without asking only a composition whose recipients are
  exactly that set, and every other mail asks.
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
out, at most once. Chrome's blocking rules no longer protect anything, and fail-then-repeat and URL allowances are
gone. The extension and the page script stay, for everything except deciding what leaves.

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
  cookie encryption through a keyring of that user, not the plain store 17e used; his own downloads reaching him, and
  Claude's reaching only the assistant's folders (`chrome_downloads`); none of the browser user's files readable by
  the coding user. All *brief 20*.
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
forwards the earlier held messages on that connection with it, and its description lists them (*brief 20*). Earlier
messages never inherit a later message's freedom: a message that would go without asking waits behind earlier held
messages on its connection until those are decided.

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
  alone (a service credential tied to the machine), and deletes each text when its guard ends. Each text is recorded
  before the input that enters it reaches Chrome (the barrier, below).
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
can still arrive after it, and is not Claude's).

**Every input passes the barrier, not only the first.** Before the tool sends any acting input to Chrome (a click, a
key, a fill, a choice, an upload), the checkpoint durably records everything that input changes in its classification
(the guard, if it is the first; that the document is now one Claude acted in; any text Claude enters with it) and
acknowledges. Only then does the input go to Chrome. A crash before the acknowledgement means the input never reached
Chrome; a crash after it means the checkpoint already knows the input, so after restoring it classifies a page's
retry exactly as before. Because the checkpoint restores all of this before it reports ready, a restored page's first
send after a restart of Chrome or of the checkpoint is held before the extension has attached (*checked* for the
guards, 17e Q1; the rest, *brief 20*, with the checkpoint, the tool service and Chrome each killed between Claude's
call and the record, between the record and the input, and right after the input, and a page then retrying a GET
that carries the text).

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
   (the guard list, the record of consumed captures and Claude's entered text, encrypted) is in a folder only it can
   read. `checkpoint.sock` is open only to the tool service. Its listening port accepts connections only from the
   browser user (a firewall rule). The port is below 1024, which ordinary programs can't open, and the checkpoint is
   started with the right to open low ports and no other privilege, so no other program can listen there first and
   pose as it (17e: taking over the port was not tested). The checkpoint refuses to start if the port is taken or if
   ordinary users may open low ports.
   *Test:* the owner's, the assistant's and a coding user's programs can't connect to the port or the socket; a
   program of theirs can't open the port; the checkpoint refuses to start when the port is taken.
2. **Nothing it sees leaves the machine.** This means the checkpoint adds no way out of its own. It sends nothing
   anywhere except the browser's own traffic to the address Chrome asked for: no telemetry, no updates of its own, no
   remote logs, no exports, no web interface (mitmproxy's core only). Captured bytes stay in its memory: no core dumps
   of its process, its memory kept out of swap, no temporary files. On disk it keeps only its record: the guards, the
   consumed captures, and Claude's entered text encrypted at rest. Two flows are explicit and limited, and not what
   "nothing leaves" covers: descriptions in Claude's tool results, which reach Claude's model (it runs at Anthropic),
   and, if he takes that proposal, descriptions sent to his phone for approval, encrypted end to end (section 7).
   - **Affirmative attribution before anything reaches Claude.** A held operation is described to Claude only when it
     is attributed to a context Claude is authorised for: a Claude tab Claude acted in (by its current tag), or an
     operation a site adapter ties to Claude's action. Being on a guarded site is not enough. The owner's own tabs
     there, everything held only because attribution was uncertain, and Chrome's own service sends are shown to the
     owner only, never described to Claude.
   - **Safe fields only.** A description shows only fields the tool or a site adapter knows are safe to show: the
     text Claude entered, the values Claude chose in the form, and what an adapter decodes as content (a recipient,
     a message, a playlist name). Everything else is withheld behind a placeholder, its name included, because a
     field's name can itself carry data: "[field 3: 412 bytes, not shown]", and for content in no known format
     "[1,830 bytes in an unknown format, not shown]". The same applies to an address: its site is shown, and path
     segments and query fields the tool or an adapter can't show safely are replaced by placeholders the same way
     (`/reset/<token>` reads `/reset/[segment 2: 43 bytes, not shown]`). Cookies and
     authorisation headers are never shown. This holds in every description, to Claude and to the owner, and in the
     tool service's approval log; the hash still covers the real bytes, so the approval binds exactly what goes. A
     token that hides in a field the tool counts as safe is the residual (brief 20 lists the safe fields).
   *Test:* every outgoing connection of the checkpoint matches one Chrome asked for; it writes no file outside its
   state folder; core dumps are off; Claude's tools return nothing of an operation held in the owner's own tab on a
   guarded site, held for uncertain attribution, or sent by Chrome's services; marker tokens in cookies, headers,
   addresses, unknown fields and opaque bodies never appear in a description or the approval log.
3. **No bodies, cookies or secrets in logs.** Its logs and its record hold ids, lengths, hashes, states, the site and
   the method; never bodies, header values, cookies, passwords, query strings or socket messages. Claude's entered
   text is in the record only encrypted (above). Messages of the proxy core are filtered the same way (errors only,
   addresses cut to the site). The record of what was approved (the description the owner saw, as for mail, with
   sign-in data replaced) is the tool service's operation log, in its own private store; it is not a checkpoint log.
   *Test:* runs with marker strings in cookies, headers, bodies, query strings and socket messages; afterwards no log,
   journal entry, record, crash output or temporary file contains a marker in readable form. (17e did this for its
   own records and found and fixed one leak of a fixture value: *checked*, 17e Q11.)
4. **Upstream TLS: Chrome's own checks, with Chrome's own current data.** Before any byte of a request goes to a site,
   the checkpoint checks that site's connection itself, the way Chrome 157 would. Any failure ends it with an error
   page in Chrome; there is no fallback and no "accept anyway".
   - **Chrome's current security data.** The checkpoint reads the data Chrome's component updater keeps current, from
     Chrome's user-data directory (not a single profile's folder): the CRLSet in
     `CertificateRevocation/<version>/crl-set` (Chrome's revocation list), and in `PKIMetadata/<version>/` the Chrome
     Root Store (`crs.pb`, its roots and their limits), the CT configuration with the log list (`ct_config.pb`) and
     the pin list (`kp_pinslist.pb`) (re-check 10, Chromium 157 source).
   - **What this trust rests on.** These files carry no signatures of their own. Chrome checks each downloaded
     package's signature before unpacking it (re-check 10, Chromium 157 source), so the trust rests on Chrome's
     verified installation plus the protection of the folder: Chrome's user-data directory belongs to the browser user,
     the checkpoint's user may read it and not change it, and the assistant's and the coding user can't write it.
     Anything that can write that folder as the browser user can weaken these checks, just as it could weaken Chrome's
     own.
   - **Loading.** The checkpoint uses the version Chrome itself uses, by Chrome's own effective rules for choosing one
     (including compatibility and the floor Chrome has built in; "the highest complete version" is only where those
     rules agree, and brief 20 proves the two choose the same), loads it only when every file is present and parses
     against the schema the checkpoint was qualified with, switches over in one step for new connections, and
     otherwise keeps the last good data. The image ships a copy of each as the floor for a fresh installation. All
     *brief 20*.
   - **A version gate.** Chrome ships pinned in the AresOS image together with a checkpoint qualified for exactly that
     Chrome version, so the two change together. If the running Chrome's version differs from the one the checkpoint
     was qualified for, the owner gets a visible notice: "Chrome is newer than its checkpoint; checks a newer Chrome
     makes may be missing until AresOS is updated" (*brief 20* tests the notice).
   - **Freshness, only from evidence.** File times aren't used. Data is as fresh as the last evidence for exactly that
     version: the checkpoint saw it downloaded through itself, or saw the update server answer "no update" for it over
     a connection that passed every check (the checkpoint sees Chrome's component update checks pass through it).
     That time is kept in its record across restarts, tied to the version. Loading bytes that are already on disk
     (after a restart, the image's own copy, a restored folder) keeps their age; it is not evidence. Without evidence
     for the version held, its freshness is unknown, which counts as out of date. On top of that, a format's own
     fields apply where it has them: the CT log list's timestamp with Chrome's own limit (70 days, after which Chrome
     itself stops checking CT; the checkpoint pauses instead), the pin list's timestamp with Chrome's own age rule,
     and the CRLSet's expiry when it is set (it is optional). Each kind has an age limit, set in brief 20 from
     Chrome's own update intervals. *Brief 20:* a first start with only the image's copy (unknown, paused until
     Chrome's update), a restored folder or record whose evidence doesn't match the version on disk (unknown), and
     ordinary restarts (age kept).
   - **When data is out of date.** The checkpoint refuses new connections to sites and tells the owner ("Chrome's
     security lists are out of date; new connections are paused until Chrome updates them"), on his desktop and, if
     he takes the approval proposal, on his phone. Recovery has an exact contract:
     - It runs only while the extension is present and its tag coverage is verified (it is connected for this browser
       run, and its own probe requests from a page and a worker arrive tagged). Only then does a missing tag mean the
       request didn't come from a page or worker. When attribution is lost, recovery stops and new connections stay
       paused until the extension is back.
     - While it runs, only Chrome's own component updates get through: requests that carry no extension tag, go to
       Google's update hosts (a fixed list in the image), and have the update protocol's shape: an update check naming
       only Chrome's own component ids and versions, or the download of exactly the package that a previous update
       answer named. Everything else, page and worker imitations of these included, waits.
     - Every TLS check stays on for these connections, with the last good data; only the age limit is waived, and
       only for them.
     - A signed package authenticates what Chrome installs, not the request that fetched it; the request is judged by
       its shape and by the absence of a tag while tag coverage is verified, as above.
     - *Brief 20:* genuine updates recovering from stale data; matching requests from a page and a worker held while
       coverage is verified, and held again while the extension is gone (recovery stopped); recovery resuming when it
       is back.
     - The checkpoint loads the new data only when it is complete and valid (above); a package that fails Chrome's
       signature check isn't installed, and the checkpoint keeps waiting.
   - **Chain:** to a root in that root store, used with its limits (for example roots trusted only for certificates
     issued before a date). The checkpoint's own root is in no list but Chrome's (requirement 5).
   - **Name and dates:** the host name against the certificate's names (no fallback to the common name); every
     certificate in the chain within its dates and meant for its use; Chrome's minimum key sizes and signature
     algorithms.
   - **Protocol:** TLS 1.2 or 1.3 only.
   - **Certificate Transparency:** Chrome's complete CT policy as Chrome 157 applies it, pinned to that version: each
     log's state with its dates (for example usable, read-only, retired), how many signed timestamps are required by
     the certificate's lifetime and by how they are delivered (in the certificate, in the handshake, or in a stapled
     answer), the rule on distinct log operators, and each timestamp's signature checked against its log's key.
     Chrome's later rule changes are taken over with its version (*brief 20*: one test per rule).
   - **Pinned keys:** Chrome's pin list, from the same component.
   - **Revocation:** the CRLSet, applied as Chrome applies it. It carries most security-relevant revocations that
     certificate authorities publish, and certificates Chrome blocks itself because they were misissued or their key
     was compromised (re-check 9, Chrome 157's security FAQ). Stapled OCSP answers and the "must staple" mark are
     treated exactly as Chrome 157's verifier treats them, no stricter (re-check 9), so a site that works directly in
     Chrome works through the checkpoint. No online revocation lookups: Chrome doesn't make them either, and they
     would tell the issuer which sites he visits.
   - *Checked* (17e Q9): an invalid upstream certificate gave a failure and zero requests at the receiver; HSTS kept
     working; a Google address that Chrome pins worked through the local root, as Chrome documents. Everything else
     here is *brief 20*.

   **What is still lost, in plain words** (for the owner to accept before everyday use, section 10):
   - **Sites that ask the browser for a client certificate** don't work.
   - **No "continue anyway".** Chrome lets him click through a certificate warning, for example on his router's or
     printer's own page, whose certificate the device made itself. Through the checkpoint such a page doesn't open.
   - **Out-of-date lists pause browsing.** If Chrome can't update its lists for a long time, new connections pause
     until it can; Chrome on its own would go on (and with an old CT list it stops checking CT).
   - **Version differences.** The checkpoint copies Chrome 157's rules. Chrome and the checkpoint change together
     with the image, but if Chrome is ever newer than its checkpoint, checks the newer Chrome makes may be missing
     until AresOS is updated, and he is told so (the version gate above).
   *Test:* each with zero requests at the receiver: expired, wrong-name, self-signed, unknown-root, a root used past
   its limits, a certificate on the CRLSet, missing or invalid timestamps and each CT policy rule, a wrong pinned key,
   an old protocol; valid, missing, stale and invalid stapled answers, with and without "must staple", giving the same
   result as Chrome 157 directly; HSTS; out-of-date lists pausing new connections while Chrome's component update still
   gets through, and a page or worker imitating that update held; recovery from genuinely stale data, from a package
   that fails its signature check and from an interrupted update; loading only complete and valid versions in one
   step, the schema, Chrome's built-in floors and its choice of version, malformed and missing files; freshness
   across restarts, including an unchanged-update answer; the full CT policy (the 70-day limit, log operators and
   their history, retired logs, each delivery method, duplicate timestamps, the kinds of log); the version-gate
   notice; the checkpoint's root in no trust list but Chrome's.
5. **A key that rotates and can issue nothing while the checkpoint is stopped.**
   - **Every place the root goes, and nowhere else:** (a) Chrome's policy `CACertificates`, which the profile's
     network contexts read and re-read while Chrome runs (Chrome 157's policy definition: `dynamic_refresh: true`,
     `per_profile: true`; the profile service watches it: re-check 8); (b) the place Chrome's own network context reads
     trust, for its services (Safe Browsing, component updates), for the browser user only. The candidate for (b) is
     that user's own certificate database, which re-check 8 calls plausible but not yet shown to work for that context
     (*brief 20*). Chrome's own context has no way to update trust while running (re-check 8, Chromium 157 source), so
     it learns a new root only when Chrome starts.
   - **A fresh root per start.** A root-owned start step runs before the checkpoint. It first reconciles: from both
     places it removes every root this checkpoint installed earlier (left over from a crash or a power loss),
     identified by the fixed name its roots carry and the fingerprints in its record, and never touches any other
     trust entry. Then it makes a new
     root key and certificate (allowed only to sign site certificates, valid a few days at most), writes the
     certificate into both places, and hands the key to the checkpoint as a service credential: memory that isn't
     swapped, readable only by the checkpoint's user, gone when the service stops. It deletes its own copy; the key is
     never on disk.
   - **Only in memory.** The checkpoint keeps the key and the site certificates it makes only in memory.
   - **Stopped means nothing can issue.** When the checkpoint stops or crashes, the key is gone with it, and the stop
     step removes the root from both places (after a power loss, the next start's reconciliation does). Nothing can
     make a certificate Chrome trusts while the checkpoint is stopped: the old key no longer exists, and a new one
     exists only once a new run starts.
   - **Cached trust and open connections.** Chrome keeps open connections and earlier verification results, and its
     own context can't take a new root while running. So whenever the root changes (stop, crash, rotation, the
     pass-through switch in either direction), the launcher closes Chrome and starts it again only once the new root
     is in place, with its tabs restored. A running Chrome that still trusts an old root meanwhile reaches nothing: the
     new checkpoint signs with a root it doesn't know, which fails closed. Typing the owner hadn't sent in his own tabs
     can be lost; the extension says why Chrome restarted.
   - **Renewal.** Before a root expires, the checkpoint is restarted with a new one at a moment when nothing is held.
   *Test:* a new root at every start; no key material on disk, in swap or in a crash file; after a stop, a crash, a
   rotation and the pass-through switch, the old root is gone from both places, and the profile's contexts and Chrome's
   own context both refuse a certificate it signed and accept the new root's; after a kill that skips the stop step,
   the next start removes the leftover root.

### Chrome's own services through the checkpoint

17e found some of Chrome's own background connections failing the checkpoint's certificate (component updates,
Chrome's client services, the optimization guide, a Google static host), because the trust policy is per profile and
Chrome's own services use a separate network context that doesn't read it (*checked*, 17e Q9; re-check 7). The fix is
trust, never an exemption: no host is passed through unopened and none is let through by name, because either would
give a page an unchecked way out. The start step puts the root also where Chrome's own network context reads trust,
for the browser user only and never in the machine's trust store (requirement 5, place b). Brief 20 then shows,
through the checkpoint, with no guard on and again while guards are on, also while attribution is lost:

- Safe Browsing warning on its official test page, with a positive control: Safe Browsing on by policy and its lists
  loaded before the test (in 17e even the direct run showed no warning, so the control was missing);
- a fresh component download, not only "up to date" on a component already there;
- the extension's own updates, and sync;
- no certificate failures in Chrome's service connections;
- that recognising a service's protocol frees only that service: imitations of those requests made by a page, by a
  worker and through a send a page makes Chrome do are held, because a protocol's shape doesn't prove where a request
  came from or that its content is harmless (re-check 8).

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
| `chrome_click_destructive` | **delete** | click a control the page labels as destructive, or press Delete or Backspace outside a text field, only after approval; the approval says the click may delete data kept only in this browser; with a qualified adapter, an approval of one bounded advance operation (below) |
| `chrome_dialog` | change | accept, dismiss or answer a page's own dialog (alert, confirm, prompt) |
| `chrome_upload` | change | put a local file into a file field; the bytes come through the caller's side (rule 4.4), the extension gets no general file access (*checked*, 17) |
| `chrome_downloads` | read, change | list downloads; save one into an allowed folder (rule 4.4) |
| `chrome_bookmarks`, `chrome_history` | read | the owner's bookmarks and history, to find addresses |
| `chrome_wait` | read | wait for text, an element or the page to settle |
| `chrome_pending` | read | what is held that is attributed to Claude's work: pending sends and background holds (nothing of the owner's own tabs: requirement 2) |
| `chrome_submit` | **send** | let one pending send go: the captured operations the service described, by id and hash (below) |
| `chrome_submit_trusted` | send, free | as `chrome_submit`, only for an operation a site adapter recognises as a kind the owner set to "don't ask again" (below) |
| `chrome_open_site` | **send** | open an address that isn't free to open (below), with the full address in the input (an address Claude composed or was given, so nothing in it is hidden from Claude) |
| `chrome_drop` | change | drop held operations; nothing leaves |
| `chrome_end_guard` | **send** (asks) | end a site's guard where it didn't end by itself; the input shows what of Claude's may be left there and what the page stored; afterwards the owner's own sends there go unchecked |
| `chrome_end_call` | **send** (asks) | end every peer connection in Chrome (all calls) so that Claude can act; the approval says so and names the site Claude wants to act on and the calls the tool can see; the set is checked again right before cutting (calls, below) |
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
- **Reading through POST.** Many apps load data with POST (GraphQL queries, Notion, Google's apps). Such a request
  counts as reading only when a qualified site adapter recognises it as reading ("recognised", below). That a GraphQL
  request is written out as a `query` is a hint, not proof that the server changes nothing (re-check 8); stored
  queries, batches, mutations and Claude's text inline or in variables are never reading (*checked* on fixtures in the
  page, 17c: all were held). Without an adapter, such requests after Claude acted are held like any other POST, so
  working in those apps asks until their adapter exists. *Checked* on ten public sites without signing in (17c and
  17d, provisional: workers and live connections were switched off for safety, visits were short, and counts cover the
  main document; they are what the after-acting rule would hold, not prompts): GitHub, Wikipedia and a news site
  stayed usable with a few holds at most; Amazon and Google search held about a dozen each, mostly telemetry, which
  goes to the background list or is dropped as tracking; Notion and Google Docs read through POST and need an adapter;
  YouTube, Reddit and Stack Overflow showed the test machine a bot check and stay unmeasured. 17e's reading visits
  gave the same results through the checkpoint as direct (*checked*, 17e Q11). Signed-in use is measured in the
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
(all marked "as the page shows it"), and every held operation: site, address (with placeholders for what can't be
shown safely: requirement 2), method, the data decoded where possible, the capture id and the hash of its bytes.
Claude passes exactly that to `chrome_submit`, and the owner's prompt shows it. The checkpoint forwards each captured
operation at most once. *Checked*: held sends reached the fixture server zero times while held, exactly once after
release and never after drop, for posted forms, search forms, `fetch` and XHR posts, beacons, autosave, a form posting
to another site, link pings and a data-bearing image (17, 17b, 17c, holding in the page); and at the checkpoint, the
exact captured bytes once after approval with competitors still held (17e Q4, Q5).

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
list kept only in the browser) without any network send, so the checkpoint can't hold that (re-check 7).

- **Labelled destructive controls ask first,** on every site, before the click happens. Destructive means the
  control's accessible name or role says delete, remove, discard, clear, empty or trash, in English and German at
  least (löschen, entfernen, verwerfen, leeren, Papierkorb), matched as whole words; a site adapter may add more words
  and controls. Pressing Delete or Backspace counts the same, except in supported text editing: on text inside a
  text field or an editable area (`contenteditable`). When the selection or focus inside an editable area is an
  object (a card, an attachment, an image, an embedded item), Delete and Backspace are destructive too.
  `chrome_click` and `chrome_press` refuse such a control ("this control may delete; use
  `chrome_click_destructive`"), and `chrome_click_destructive` (effect delete, asks) clicks it only after approval.
  The approval names the control as the page labels it, the page and the site, and says plainly that the click may
  delete data kept only in this browser. It covers the click only: if the page then sends something, that send waits
  at the checkpoint and asks with its own approval, showing what is really sent.
- **A destructive action approved in advance,** only with a qualified site adapter. The approval comes before the
  click and names one bounded *advance operation*: the adapter contract's version, the account, the exact targets (by
  the site's own stable ids), the permitted effects ("delete these two drafts, kept in this browser and on the
  server"), a limit on how many requests or messages may follow and in what order, and an expiry. It is consumed once,
  durably, like a captured send, and recorded as consumed before the click reaches Chrome; the count of sends that
  follow is kept durably too. The sends that follow go without a second question only while each validates against
  that description, within its limit and before its expiry; anything else, and anything after it is used up, asks. A
  contract's recognition is never a reusable permission: each destructive operation is one approval.
- **An unlabelled control that deletes data kept only in the browser** (an icon without a name, a "Reset" that
  doesn't say what it resets; on an ordinary online site too, for example an unsent draft kept in the browser's
  storage): **owner decides (open, section 10)** between (a) such clicks stay free, and (b) on any site without an
  adapter, every click on something that isn't a link and every action other than plain text editing asks first; an
  adapter frees only interactions inside its qualified coverage. Under (b) links stay free, so two ways remain: a
  link's own click handler can clear a draft kept in the browser, and following a link leaves the page, losing a
  draft held only in its memory.
- *Tests (brief 20).* For both options: labelled controls and Delete or Backspace asking before the click; other
  ways to activate a control (Enter or Space on a focused control, a context-menu item, a double click, dragging an
  item onto a bin); a page's own confirmation after a destructive click (part of the same approved action) and a
  confirmation reached by another route (asks); plain text editing staying free, typing, Backspace and Delete on text
  in text fields and editable areas included; Delete and Backspace on a selected card, attachment or object inside
  an editable area asking. For (a): an unlabelled control on a fixture that keeps a draft in the browser's storage
  stays free, as he chose. For (b): on a site without an adapter, every click other than a link and plain text
  editing asks, on online and offline fixtures alike; on a site with an adapter, interactions inside its coverage go
  free and those outside it ask. For both: a fixture with a draft kept in the browser's storage and an
  ordinary-looking link whose click handler clears it, showing that the link goes free under either option (the
  disclosed exception).

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
when the page sent it by itself, listed as background for Claude if it comes from a Claude tab and on the owner's
details page if it comes from his own tabs (requirement 2); and put to the owner (next part) when his own input caused
it (*checked*, 17c: an owner's click in another tab that emptied Claude's queue was held, through local storage and
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
  caused it (*checked*, 17c). On a guarded site it is held. It can't be attributed to Claude's work, so it isn't
  described to Claude (requirement 2); Claude sees only that something unresolved is held on that site. It goes to
  the owner's approval surface (section 7), where he can answer it at the laptop or, under the proposal there, on his
  phone, never only to the laptop's details page. When he was using one of the site's tabs just before (input the
  tool didn't send), the extension's desktop notification shows it too: a guess about his notification, never an
  exemption. Each such send is one operation; the first answer from any surface decides it at once, and the same send
  reported through several attached sessions counts once (*brief 20*).

This is the owner deciding about his own click, not an approval of Claude's actions; those stay with the approval
surface (section 7).

**Which of the owner's own sends are put to him (settled with 17c).** Every send of his on a guarded site that isn't
plain reading, not only those that look like Claude's leftover (same address, Claude's text). 17c showed why that
narrower match isn't safe: a page's timer that empties Claude's queue leaves no traceable chain, and a shared worker's
send has no trace of whose click caused it, so a page can send Claude's queued deletion to another address than the
one that was held. What keeps the notifications few: site adapters for his usual sites that recognise reading (which
then goes without a question), guards that end when an adapter shows nothing is left, and his one click when Claude is
done on a site without one. Known tracking requests are dropped, not asked. The tool-user rounds count these
notifications on an ordinary day (section 8); the target is close to zero.

### "Don't ask again" (decision 7)

The owner can free a kind of action from asking, within these limits:

- **Only for kinds a site adapter recognises** (as defined under "Site adapters", below) and names, such as "Deezer:
  add to playlist" or "GitHub: star". Never for a send the tool doesn't recognise: one POST to `/graphql` looks like
  any other, so freeing "this address" would free everything sent there. A kind that sends a message to other people
  names one conversation whose identity the adapter validates in the captured bytes, never "any chat".
- **Mail, deleting and paying, and WhatsApp: owner decides (open, section 10).** His answer (#52) was general, and
  earlier drafts offered "don't ask again" more narrowly than he asked. Open: (1) mail sends, in the Mail tools and
  in Gmail, bound to an exact set of recipients (for example mails to himself); recommended: offer it. (2) Deleting
  and paying; recommended: always ask, which he can overrule. (3) WhatsApp Web, where the checkpoint can't check
  what is inside the encrypted messages, so "don't ask again" there would trust the page's own display;
  recommended: not at all. Until he answers, none of the three is offered.
- **Bound to its exact scope:** the site, the signed-in account, the target where the kind has one, the action, the
  permitted parameters and the adapter contract's version. Each release validates the complete captured operation
  against that scope again; anything else asks. An entry never covers another account or site.
- **Adapter updates never widen an entry.** A new adapter version applies to an existing entry only where its
  contract for that kind is the same or narrower; where it is wider, the entry is suspended (those sends ask) until
  the owner confirms it again.
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

**What "recognised" means.** An operation is recognised only when its complete captured form validates against a
qualified adapter contract for that site: the signed-in account; a stable identity of the target or conversation (an
id from the site's own data, not a name or a position on the page); the action; parameters within what the contract
permits; and this for every request or message the operation consists of. Unknown fields, a batch that mixes kinds,
and a protocol version the contract doesn't know make it unrecognised: it asks, or is refused where a question can't
describe it truthfully. A contract is qualified by receiver tests against fixtures and the owner's test accounts, and
it is versioned. Hints (timing, sizes, the page's own state, what the page script reports, a GraphQL operation written
as `query`) can make a description clearer; they never make an operation recognised. Everything that goes without a
question of its own needs recognition: reading through POST, the sends an adapter groups under one approved action, a
destructive action approved in advance, and "don't ask again".

His usual signed-in sites are the first adapter targets: WhatsApp Web, Gemini, Gmail and Deezer (more to come). What
each likely needs, to be confirmed when its adapter is built:

- **WhatsApp Web.** Messages go over a live connection whose content the page encrypts itself, so the checkpoint can
  hold each outgoing message but can't read it; its connection may also run in a worker, the kind of send that got
  past Chrome's own rules in 17d and needed the checkpoint. The description has to come from the adapter's reading
  of the page: the conversation, the text, the message shown as waiting. The site also sends things that reach other
  people without being messages: read receipts when a chat is opened, "typing…" while text is entered, presence.
  What the adapter can see of the encrypted bytes (timing, size, the page's own state) only describes; it can't
  recognise anything. So by default every send there after Claude acted asks, one question per message: the message
  and what Enter caused with it (the typing notice) grouped, and opening a chat (its read receipts) one question too,
  each described from the page and marked "as the page shows it", because the checkpoint can't check what is inside.
  "Don't ask again" there is the owner's open question above (recommended: not at all). "Claude fills in, he sends"
  is an option he can choose for this site. The hardest of the four.
- **Gemini.** Google's app talks through POST calls in Google's own format, reading included (loading a chat), like
  Google Docs in 17c. The adapter decodes the call names to tell reading from sending: asking a question (which sends
  Claude's text to Google), deleting a chat, sharing one. "Ask a question" is a candidate for "don't ask again".
- **Gmail.** Also POST calls, reading included. Opening a mail marks it read and saving a draft keeps it in his
  account (both changes, free once the adapter recognises them); sending is a mail send and asks; "don't ask again"
  for mail, bound to an exact set of recipients, is the owner's open question (section 10). The adapter decodes the
  recipients (Bcc included), subject and text so the approval reads like a mail (decision 11), and follows the "undo
  send" delay: the send leaves when the delay ends, and is held then. His main mail goes through the Mail tools
  (section 5).
- **Deezer.** Its web calls likely name each method in the address, so reading (search, lists, playing) and changing
  (add to a playlist, like, follow) can be told apart; reports of what was played are sends to his own account, which
  the adapter groups with the play action. "Add to playlist" is a candidate for "don't ask again".

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
  click (above); what happens with an unlabelled one is the owner's decision (section 10).
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
  on a control labelled delete, remove, discard, clear, empty or trash (or the German words) asks first; for a
  control without such a label he chooses between two options (section 10).
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
- **Certificate checks are Chrome's, with a few differences** (requirement 4): the checkpoint checks sites the way
  Chrome 157 does, with Chrome's own current lists; client certificates and "continue anyway" don't work, out-of-date
  lists pause browsing, and a Chrome newer than its checkpoint may make checks the checkpoint lacks (he is told). He
  decides whether to accept this before everyday use (section 10).
- **Uploads above the limit fail** rather than going around the checkpoint.

### Before it becomes his everyday browser (PLAN S2e)

Until all five hold, the fallback is the one in the plan: Claude fills in, the owner sends.

1. **Unrelated tabs stall about never.** How often his other tabs wait while Claude works on one site (uncertain
   attribution, the whole browser waiting while the extension is lost or before the checkpoint is ready, tab-less
   sends of a frame's site, Chrome's own services) is measured on his usual sites, in the tool-user rounds and after
   the first boot; the target is zero, and each stall is counted with its cause.
2. **Chrome's own protection works:** Safe Browsing with a positive control, and component updates with a fresh
   download, through the checkpoint and with no exemptions, also while guards are on (Chrome's own services, above);
   and he has accepted the TLS checks the checkpoint can't replicate (requirement 4, section 10).
3. **A way out of a fault.** An owner-only switch, `sudo aresos admin chrome checkpoint pass-through` (and a menu
   entry that runs it with his password), sets Chrome's policy to direct connections, lifts the firewall rule for the
   browser user, stops the checkpoint, which destroys its key, removes the root from every place it was installed and
   restarts Chrome (requirement 5). It works even when the checkpoint is broken. It
   needs no guard holding leftovers: where leftovers exist, they are shown first (on which site, what of Claude's may
   be left), and he ends those guards knowingly before the switch goes through. While it is on, Claude's Chrome tools
   are off ("checkpoint off: Chrome tools off until it is repaired"). Switching back starts the checkpoint with a new
   root and restarts Chrome, so that no connection opened without the checkpoint survives; Claude's tools return
   once the checkpoint reports ready.
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
  `chrome_end_call`. Because the barrier cuts every peer connection and can't tell which tab each belongs to, the
  approval is for all of them as one set: "end every call in Chrome so that Claude can act on this site", listing
  the calls the tool can see. Right before cutting, the tool checks the set again; if it changed while he was asked
  (a second call started), it asks again. Only his answer lets Claude act, never Claude's word that he agreed. The
  extension says why the calls ended.
- While a guard stays on (strict, above), new calls in Chrome don't connect; the extension says so and shows the guard
  he can end.
- Calls outside Chrome are not affected.

### Tests

The fixture sites, receivers and runners of briefs 17 to 17e, ported to the product (every hold proven by an
independent receiver's own log), and the everyday tasks in `PLAN.md` (Chrome tasks 8 to 14), on GitHub's Linux
machines with branded Chrome; the whole set runs twice on the recorded Chrome version (re-check 7). Synthetic fixtures
qualify the mechanism, not arbitrary real sites. Brief 20 must show, building on a pinned mitmproxy core:

1. **No way around it** (17e Q1 again, on the product): real connections from Chrome's user over IPv4, IPv6,
   localhost, link-local and a container's address, redirects, workers, QUIC and the checkpoint down, each before and
   after the image's firewall service reloads its rules; a Chrome started without the launcher can't browse; nobody
   else can listen on the checkpoint's port.
2. **Connections opened before a guard and the barrier** (17e Q2): pre-opened HTTP/2 and page, dedicated, shared and
   service-worker sockets; input only after the barrier is confirmed.
3. **Conservative attribution** (17e Q3): forged, stale and missing tags, opaque origins, foreign frames, hand-offs
   across origins, the extension removed; tab-less workers of a frame's site; Claude's entered text held in any tab;
   the page-made Chrome sends (push subscription, passkey, payment) refused on a guarded site; real web push: a
   message from an independent publisher shown delivered to a guarded site's worker (a positive control: the worker
   ran), and then zero arrivals at receivers of anything that worker sends without approval.
4. **Readiness, uncertain reading and the input barrier:** everything, GET and HEAD included, held at every start
   until the guards and Claude's entered text are restored; Chrome and Claude's tools only after the ready report;
   afterwards an uncertain GET or HEAD carrying Claude's entered text held, across restarts of the checkpoint, the
   service and the browser and loss of the extension; a damaged record never reports ready; every input recorded and
   acknowledged before it reaches Chrome, with the checkpoint, the tool service and Chrome each killed between
   Claude's call and the record, between the record and the input, and right after the input, and a page then
   retrying a GET that carries the text (held).
5. **Complete operations** (17e Q4) with the product's read, drain and size limits, including WebSocket ping and pong
   frames that carry data (17e gated them at its seam; brief 20 shows them held by a receiver test).
6. **One approval, one capture, and the context still the same** (17e Q5): competitors held; the account and document
   checked again up to forwarding, on fixtures with a real sign-out and sign-in (17d Q8) and through each usual-site
   adapter.
7. **Every crash point** (17e Q6): no arrival before forwarding, no replay, `unknown` after a cut-off forward; the
   tool service's operation log and the checkpoint's record agree after each crash.
8. **Cancellation and the 15-minute lifecycle:** an HTTP/2 stream reset seen and recorded as cancelled (open in 17e);
   abort, tab closing, expiry and the page script's cancel; a late approval refused; a hold waiting the full 15
   minutes for an approval, with HTTP/2 cancellation along the way, ending as `failed` with nothing sent; and an
   approval that arrives just before the 15 minutes end, forwarded at most once and correctly recorded.
9. **Other transports and calls:** WebTransport refused always and WebRTC while a guard is on, with a clear error
   where the page script can give one; a call through a relay over TCP and TLS working while no guard is on
   (positive control on a real call service), cut at the barrier; the acting refusal while a call runs, and acting
   only after the owner's answer to `chrome_end_call`, which covers every call as one set; a second call that starts
   while that question waits makes it ask again.
10. **The owner's five requirements** (above), each with its test: every trust location after stop, crash, rotation
    and pass-through, in the profile's contexts and Chrome's own, with only roots this checkpoint installed removed;
    the upstream TLS cases with Chrome's own current lists and their age limits; attribution before anything reaches
    Claude, safe-field descriptions with unknown fields and opaque content withheld; unattributed sends of the
    owner's tabs reaching his approval surface, also on the phone.
11. **Chrome's own services** (above), with no guard and under active guards, also with attribution lost: trust in
    Chrome's own network context with no exemptions; Safe Browsing with a working positive control; a fresh component
    download; the extension's update; sync; page-made imitations of their requests held; the list of features that
    send text.
12. **The strict guard:** adapter-based ending for the four usual sites; the one-click end; guards across checkpoint
    and Chrome restarts; storage and hand-offs keeping the guard (17e Q10).
13. **Clicks that may delete local data:** labelled controls in English and German refused by `chrome_click` and
    asking through `chrome_click_destructive` before the click; Delete and Backspace outside text fields; the other
    activation paths, confirmations and free text editing above, for whichever option the owner picks; an advance
    operation's follow-up sends released only while they validate, within its limit and before its expiry, used up
    once (a second deletion under the same approval asks), consumed durably before the destructive input reaches
    Chrome, its count of follow-up sends kept durably under competing sends and crashes; and without an adapter the
    follow-up sends asking.
14. **Bounded resources** (17e Q11): memory, capture count, total size, a full record, the memory ceiling; exhaustion
    never forwards.
15. **The pass-through switch** (condition 3): only through the owner's channel; leftovers shown first; Claude's
    Chrome tools off; the root removed everywhere; Chrome restarted when the checkpoint is back.
16. **Recognised actions and "don't ask again":** set only through the owner's channels; Claude can't write the list
    (hostile test); unknown fields, mixed batches and unknown protocol versions ask; a free operation batched with or
    preceded by unapproved ones doesn't take them along; an adapter update that widens a kind suspends the entry;
    revocation racing a release (the release either happened before the revocation was recorded or is refused);
    refused for unrecognised sends, and for mail, deleting, paying and WhatsApp Web as the owner decides (until then
    refused; a mail entry, if he allows it, matching only its exact recipient set); Claude Code's own "don't ask again"
    stays inert.
17. **The separate browser user on Fedora with KDE,** with the owner's profile and sign-ins moved once: display,
    sound, camera and microphone, notifications (the owner's own-send notifications reach his desktop), the file
    chooser, the keyring, downloads; the native host as that user; the launcher always used (desktop entry, links
    from other apps).
18. **The cost** for conditions 1 and 4: stalls of unrelated tabs (including the whole-browser holds while
    attribution is lost, and frames' tab-less workers) and decisions per action on the test sites, speed, memory,
    robot checks; then on his own sites after the first boot (condition 5).
19. **Upgrades:** 17e gates WebSocket control frames at a seam inside mitmproxy 12.2.1 that its public hooks don't
    offer; that seam and the fail-stop handling are checked again on every upgrade of the core.

The whole set runs twice on the recorded Chrome version, as 17d and 17e did, and again on every upgrade of Chrome or
of the proxy core. Hostile tests (section 7) add: reaching `chrome.sock`, `checkpoint.sock` or the checkpoint's port
from the sandbox, the assistant's user or a coding user; a user-level native messaging manifest; editing the profile,
Chrome's policies or the owner's allow list; acting in a tab outside the Claude group; opening extension pages.

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
- Coding sessions run as the coding user, `coder` (as in brief 18b's isolation check), never as the owner, and have
  no app tools. The managed files are machine-wide, so a coding session
  on the same machine gets the same `managed-mcp.json` and starts the app tool servers too. They refuse at once for
  any user but the assistant's (brief 18b, *checked*: "AresOS MCP proxy requires the configured assistant user"), and
  the service checks the caller's user again on every connection (briefs 18, 18b). So non-assistant users are refused
  outright, in both places: the socket permissions are the boundary, and the refusal makes the failure clear instead
  of leaving tools that fail later (a follow-up from the 18b review makes the guard check the effective user id as
  well as the real one: `PLAN.md`, "Follow-ups"). The checkpoint likewise accepts only the browser's user (section 6).
  Coding sessions that need other Claude Code settings (network to code hosts, writable work trees, their own
  credentials) run in their own container with their own settings files, keeping brief 18b's isolation, not a toolbox
  or distrobox default (re-check 6).
- **No shared files, no local connection.** What the assistant can write and what coding sessions can read never
  overlap: downloads, saved attachments, work files, session records (Claude Code's transcripts and memory) and
  temporary files (the launcher gives the assistant its own temporary folders) all live in the assistant's own
  folders, which the owner can read and the coding user can't. The owner's folders the assistant may read are
  read-only to it, so it can't plant anything there for a coding session to pick up. If he lets it change some of his
  folders (owner decides, open: section 10), the coding user loses read access to exactly those folders, so the rule
  holds. The assistant's user can't
  connect to the coding user's local services either (a firewall rule by user on the machine's own addresses), so a
  fetch to a local address can't carry text across. Otherwise a mail's text written into a file could be read by a
  coding session and sent with its network access, with no prompt (re-check 8). Anything that should cross goes
  through the approved-send channel (next point). The owner himself can copy a file across; Claude can't.
  *Test:* the assistant writes a content marker through every path it has (its file tools, a saved attachment, a
  Chrome download, its terminal's temporary files, its session records); a coding session and plain programs of the
  coding user search everything they can read and find none; the coding user runs real services on its own
  addresses (IPv4, IPv6 and a container's address), and the assistant's programs (outside and inside the sandbox,
  and its web fetch) try real connections to each, before and after the firewall's rules are reloaded, and none
  arrives; plus the follow-ups from the 18b review (the real and the effective user id, rogue user and project MCP
  configurations: `PLAN.md`, "Follow-ups").
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
5. **Offer "don't ask again"** where it is allowed (section 6; for mail, deleting, paying and WhatsApp the owner
   decides, open: section 10), written to the owner-only list.
6. **Decide once:** the first answer counts, a second or late answer is refused, an expired question sends nothing.

**Proposal: approvals get their own screen in his Aresus iPhone app,** with a local approval window on AresOS's own
screen at the laptop.

- **What he sees.** A mail is shown like a mail (from, to, Cc, Bcc, subject, the text, attachments by name and size); a
  Chrome action as the site, the action and what is sent (the decoded data; an adapter's or the page's wording marked
  as such); a deletion as each item. Buttons: Send and Don't send, plus "Don't ask again" where it is allowed
  (section 6).
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
- **One canonical description.** The service writes each question as one canonical description and signs it: the
  operation id and the log's generation, the account, every target, the complete set of what would go (for Chrome
  each captured operation's id and hash, for mail the composition's hash with its attachments' hashes), the time it
  expires, and for "Don't ask again" the exact scope the entry would get (section 6). A destructive action approved in
  advance (section 6) has no captures yet, so its question carries the bounded advance operation instead: the adapter
  contract's version, the account, the exact targets, the permitted effects, the limit on what may follow and the
  expiry; it is consumed once. Both the phone's signature and the window's answer cover the hash of exactly that
  description.
- **The device key.** Made in the phone's secure hardware, it never leaves the phone. It is usable only with the faces
  enrolled in Face ID at the time (Apple's `biometryCurrentSet`), with no passcode fallback, so someone who knows the
  passcode can't approve; changing Face ID makes the key unusable, and he enrols again. Every decision is signed over
  the description's hash, the answer and the question's one-time value. The tool service verifies it against the key
  he enrolled.
- **Enrolment.** Once, at the laptop, with an owner-only command (`sudo aresos admin approvals enrol`, his password).
  The code the phone scans on the laptop's screen carries the service's key and a one-time enrolment secret, so they
  never pass through the relay. The phone answers through the relay with its keys, bound to that secret; then the
  laptop and the phone both show a short code made from both keys, and he confirms they match. A relay that swapped a
  key fails here. Claude can't enrol: it needs his password and his phone.
- **Revocation.** `sudo aresos admin approvals` lists enrolled phones with their last use; `… revoke` removes one at
  once: from then on its answers are refused, also to questions already sent.
- **Answers refused:** one whose description hash doesn't match (altered), one whose one-time value was used before
  (replayed), one after the question expired, one to a question of an earlier log generation (after a restore, rule
  4.3), and one signed by a revoked key.
- **First answer wins, atomically.** The tool service records the first valid answer durably in the operation log
  before it acts; a later answer from the other surface is refused and shown as "already decided". After a crash the
  recorded answer stands; an operation with no recorded answer has none and expires.
- **Inert display.** The app and the window show descriptions as plain text: no remote images or other resources, no
  links that open by themselves, no executable markup; a formatted mail is shown as its text, with control and
  direction-changing characters escaped (rule 4.1). *Test:* the complete readable mail on the phone itself (a long
  text, Bcc, attachments, odd characters), and on the laptop's window.
- **Adversarial tests.** Each invalid answer has no effect at all (nothing sent, no entry written, the question
  still open until it expires): a relay that swaps the phone's or the service's key during enrolment (enrolment
  fails); answers that are altered, replayed, signed by a revoked phone, or sent for an expired question or one of an
  earlier log generation; Face ID changed after enrolment (the key no longer works); an attempt to answer with the
  phone's passcode instead of Face ID. Valid answers that compete (the phone and the laptop answering at the same
  moment, with the tool service killed in between) produce exactly one durable decision, also after the restart, and
  the operation runs at most once.
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

- **What the checkpoint's certificate checks still can't do** (section 6, requirement 4), needed before Chrome with
  the checkpoint becomes his everyday browser. The checkpoint checks sites' certificates the way Chrome 157 does, with
  Chrome's own current lists (its revocation list, root list, CT log list and pin list). What still differs: sites
  that ask the browser for a client certificate don't work; there is no "continue anyway", so a device page with a
  certificate it made itself (a router, a printer) doesn't open; if Chrome can't update its lists for a long time,
  new connections pause until it can. And Chrome and its checkpoint are updated together in the image, but if Chrome
  is ever newer than the checkpoint, checks the newer Chrome makes may be missing until AresOS is updated; he gets a
  visible notice when that happens. Recommended: accept.
- **Clicks that might delete data kept only in the browser, when the control doesn't say so** (section 6). Many
  sites keep some of his data only in the browser: offline apps, but also ordinary online sites, for example an
  unsent draft kept in the browser's storage. A click there can delete it without anything being sent, so the
  checkpoint can't hold it. Controls labelled delete, remove, discard, clear, empty or trash (and the German words),
  and Delete or Backspace outside plain text editing, already ask first. Open is a control that doesn't say what it
  does:
  - **(a) Such clicks stay free.** An unlabelled control (an icon without a name, a "Reset") can delete something
    kept only in this browser without asking, on any site where something is kept that way. Deleting something that
    also lives on a site's server is a send and asks; what this leaves open is data that exists only in the browser,
    such as a draft not yet sent.
  - **(b) Clicks ask on sites without an adapter.** On any site without an adapter, every click on something that
    isn't a link, and every action other than plain text editing, asks first; an adapter frees only what its
    qualified coverage includes. That covers every button and icon, but not links: a link's own click handler can
    still clear a draft kept in the browser, and following a link leaves the page, losing a draft held only in its
    memory. And most of Claude's work on sites without an adapter becomes a series of questions.
  Recommended: (a), because (b) makes Chrome hard to use on every site without an adapter, and what (a) leaves open
  is limited to data that was never sent anywhere.

- **Which of his folders the assistant may read, and which it may change** (sections 2, 4.4 and 7). Earlier drafts
  settled this more narrowly than he asked: the assistant only reads folders he shares and writes only its own
  folders, so he copies its results himself.
  - **(a) As now:** read-only access to the folders he picks; its own folders for everything it writes.
  - **(b) Folders it may change:** he picks folders the assistant may change, and the coding user can't read those
    folders. Writes go through the tool service with rule 4.4's limits (no dotfiles, no start-up places, no
    symlinks). Creating, renaming and moving within those folders are free; overwriting and deleting ask; moving to
    the Trash is a delete.
  Either way, coding sessions can't read what the assistant writes. Recommended: (b).
- **"Don't ask again": for which actions** (section 6). His answer (#52) was general; earlier drafts offered it only
  for site actions an adapter recognises. Open:
  - **Mail sends**, in the Mail tools and in Gmail, bound to an exact set of recipients (for example mails to
    himself). Recommended: offer it.
  - **Deleting and paying.** Recommended: always ask; he can overrule this.
  - **WhatsApp Web.** The checkpoint can't check what is inside the encrypted messages, so "don't ask again" there
    would trust the page's own display of what is sent. Offer it with that warning, or not at all. Recommended: not
    at all.
- **How Claude sends on WhatsApp Web** (section 6). (a) Claude asks per message, with the adapter's description of
  the conversation and text marked "as the page shows it", since the checkpoint can't read the encrypted message;
  (b) Claude fills in, and he presses send himself. Recommended: (a), the default; (b) stays available if he prefers
  it.

**Answered on 2026-11-07 and built into this draft:** data leaving in Chrome (decision 7: searches on his usual sites
are free, anything else that could carry Claude's text asks; section 6); the central session apart from coding work
(decision 8; section 7); Claude in Chrome kept for his own use and the machine-wide rules (decision 10; sections 6
and 7); the checkpoint with his hard requirements (decision 6; section 6); the strict guard (decision 12; section 6).

**For the owner, later:**

- Outgoing mail formatted (like Apple Mail) or plain by default, and the signature (a habit for CLAUDE.md, not a tool
  rule).
- Which of his folders the assistant may read (read-only, section 2), and which work folders Claude's file tools use
  (section 7). The assistant writes only into its own folders, which he can read and coding sessions can't.
- The feature list in [`FEATURES.md`](../control/FEATURES.md): anything missing, and what can wait.
- **What the checkpoint costs, with brief 20's numbers.** He agreed "if that's not a security risk". Before it becomes
  his everyday browser, the costs named in section 6 ("What changes for the owner") go back to him with brief 20's
  measurements, in particular calls stopping while a guard is on, how often a strict guard waits for his click, and
  how often the whole browser waits while attribution is lost.

**Settled by this design, for the re-check:**

- **Language and libraries.** Python 3 (already in the image), the standard library's `imaplib`, `smtplib` and
  `email` for Mail with explicitly verifying TLS contexts, the official MCP Python SDK pinned and shipped in the
  image. Chrome: the extension in JavaScript (required), the native host a small Python relay, and the page view and
  hold rules in the Python service, talking DevTools protocol through the extension; the page wrap is the
  extension's own script. The checkpoint is a Python add-on on a pinned mitmproxy core (17e used 12.2.1, with one
  version-specific seam for WebSocket control frames that is checked again on every upgrade). The code of briefs 17
  to 17e is the reference (check code, not product code); brief 20 ports what it settled.
