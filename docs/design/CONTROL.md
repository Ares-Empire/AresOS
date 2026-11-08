# The control layer: design

**Status:** draft 31, 2026-11-08. Draft 16 with the owner's answers of 2026-11-07 built in (`PLAN.md` decisions 14 to
19 and 21), and two decisions of 2026-11-08: the central session can gain tools, the ones that run outside its sandbox
only through the tool layer, asking (decision 22); and one session does coding, commands, mail, Chrome and later apps,
possibly in skip-permissions mode, replacing decision 8's split (decision 23). Draft 18 answers the eighteenth
re-check ([18](../../reviews/control-design/2026-11-08-RECHECK-18.md)): project deletions kept recoverable by
snapshots (the owner's choice is open), planted repository settings contained, branch deletion and history rewrites
recoverable, add-tool preparation fetching only from listed registries, and added tools free only on reviewed
evidence. Draft 19 answers the nineteenth re-check ([19](../../reviews/control-design/2026-11-08-RECHECK-19.md)) by
containing whole classes (one traced set of programs outside the sandbox, git itself sandboxed for the session's user,
the tools reachable only from the registered `aresos-mcp`, GitHub refusing every deletion and rewrite by the session)
and by stating exact bounds as owner choices in section 10. Draft 20 (re-check
[20](../../reviews/control-design/2026-11-08-RECHECK-20.md)) makes Claude Code and the relay non-dumpable, identifies
the relay by its group, and adds a fifth owner choice for unreviewed servers that hold his account access. Draft 21
(re-check [21](../../reviews/control-design/2026-11-08-RECHECK-21.md)) accepts one relay per app per session and
checks who holds its pipes. Draft 22 (re-check [22](../../reviews/control-design/2026-11-08-RECHECK-22.md)) changes
the structure: an SELinux domain for the session refuses every program outside the allowed set when it starts, the
relay checks become hardening bound to the trusted start, and the asking tools stay off until qualification shows
nothing Claude can steer reaches Claude Code's sign-in. Draft 23 (re-check
[23](../../reviews/control-design/2026-11-08-RECHECK-23.md)) adds the precision: Claude Code's process as trusted code
into which nothing Claude wrote is loaded, the sandbox transition contract, both gates as hard switches, an
acknowledged registration barrier, and `rg` through a fixed wrapper. Draft 24 follows the owner's decision 24, which
replaces that containment: AresOS runs normal Claude Code, as on any OS, plus the tools, which must be safe in
themselves and not make things worse than normal Claude Code; sections 1, 2, 4.4 and 7 are rewritten to that bar, and
section 6 was left for re-examination against it. Draft 25 (re-check
[25](../../reviews/control-design/2026-11-08-RECHECK-25.md)) says precisely what is still unknown about
`PermissionRequest` hooks and under which settings the optional sandbox keeps terminal commands away from the tool
service. Draft 26 follows the owner's decision 25: section 6 is rewritten for the light Chrome tool (no checkpoint,
Chrome completely normal, asking before anything that clearly sends), and the checkpoint's parts elsewhere are
struck. Draft 27 (re-check [29](../../reviews/control-design/2026-11-08-RECHECK-29.md)) classifies every
activation path, resumes a stopped submission without replaying Claude's input, binds the approval to everything the
question names, limits navigation to web addresses, keeps the approval and settings pages out by every route, and
reads pages without ever collecting a password value. Draft 28 (re-check
[30](../../reviews/control-design/2026-11-08-RECHECK-30.md)) resumes a stopped submission with the same kind it was
stopped as, binds what a send outside a form carries whatever was approved before, and excludes password fields before
anything is read. Draft 29 (re-check [31](../../reviews/control-design/2026-11-08-RECHECK-31.md)) binds the whole
compose item or refuses, and stops a script's activation before it is delivered, reporting what it couldn't stop as
`unknown`. Draft 30 (re-check [32](../../reviews/control-design/2026-11-08-RECHECK-32.md)) binds every editable field
the tool can read for a send outside a form without an adapter, states read-only text as residual, and refuses to
resume an event object that changed. Draft 31 (re-check [33](../../reviews/control-design/2026-11-08-RECHECK-33.md))
stops a page's own activation of an asking control for good instead: Claude acts on the control itself if the action
is wanted. Covers the shared base, Mail and Chrome. The frontier
review ([`REVIEW`](../../reviews/control-design/2026-11-07-REVIEW.md), 8 blocking) and five re-checks
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
ask again", WhatsApp Web). After the twelfth re-check ([12](../../reviews/control-design/2026-11-07-RECHECK-12.md)),
draft 15 defines WhatsApp Web's approval as one page-trusting approval of a bounded set of encrypted captures and
removes "don't ask again" there; draft 16 (re-check [13](../../reviews/control-design/2026-11-07-RECHECK-13.md)) adds
a short collection phase after Send and separate sets for late frames. Points marked *checked* name the check that
showed them; points marked *brief 20* must be shown by the Chrome build's own tests before anything relies on them.

The plan, the owner's decisions and who does what: [`docs/control/PLAN.md`](../control/PLAN.md). The owner's
picture: [`OWNER-SCOPE.md`](../../reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md). The council's 13 gaps
([`VERDICT.md`](../../reviews/councils/2026-11-07-control-layer/VERDICT.md)) are the checklist; section 9 maps each
one to where it is handled.

## 1. In one paragraph

A tool service runs under its own system user, holds the app passwords, and does the work for every app. Each action
is defined once, with what it does to the world (its *effect*), and from that one definition come the MCP tools Claude
calls, the `aresos` terminal command, and the list of actions that must ask the owner. Claude Code asks the owner
before any action whose effect is sending or deleting, through managed ask rules. Every send and delete is recorded as
an operation before it acts, and every result says exactly what it refers to and what really happened. Around that,
AresOS runs normal Claude Code, as on any OS (decision 24): one session for coding, commands, mail, Chrome and later
apps (decision 23), as his own user, with his own `gh` login and the MCP servers, skills and plugins he adds.

## 2. The pieces

| Piece | What it is | Runs as |
|---|---|---|
| `aresos-toold` | The tool service: app adapters (Mail, Chrome, later more), passwords, the operation log. Listens on three Unix sockets and nothing else (no TCP). | system user `aresos-tools` |
| `act.sock` | `/run/aresos-tools/act.sock`: every action that may be offered to Claude. Open to his user: the service checks the caller's user on every connection (briefs 18, 18b). | |
| `admin.sock` | owner-only actions (accounts, passwords, the read-only sites, "don't ask again" entries). Open only to root; the owner reaches it with `sudo aresos admin …` and his own password. | |
| `chrome.sock` | for our Chrome extension's native messaging host only (section 6), open only to his user, as whom Chrome runs; one host per running Chrome. | |
| `aresos` | The terminal command: `aresos mail search --from … --json`, generated from the definitions, over `act.sock`. For the owner and his scripts, and for owner-only actions with `sudo aresos admin`. | the caller |
| `aresos-mcp <app>` | One MCP server per app (`aresos-mcp mail`, `aresos-mcp chrome`), a thin generic proxy: it fetches its app's tool list from the service, forwards calls over `act.sock`, and does the caller's side of file transfers (rule 4.4). Root-owned under `/usr` (read-only in the image), run with a fixed interpreter in isolated mode (`python3 -I`) and a fixed environment. Installed for his Claude Code like any MCP server (section 7). | his user, started by Claude Code |
| Chrome bridge | Our own extension and native messaging host (section 6). | his user, started by Chrome |
| Chrome | The owner's normal browser, with his profile and sign-ins, started the usual way; no proxy and no certificate of ours (decision 25, section 6). | his user |
| Claude Code | Normal Claude Code, one session for everything (decisions 23 and 24), with or without skip-permissions; his own MCP servers, skills and plugins. | his user |
| Claude Code settings | `/etc/claude-code/managed-settings.json` with the ask rules for every asking tool, and the managed `CLAUDE.md` (section 7), owned by root and generated from the definitions. His own settings work as in normal Claude Code. | |

**Who can reach what:**

| From | `act.sock` | `admin.sock` | The app passwords and sign-in data AresOS holds | Chrome's control channel |
|---|---|---|---|---|
| The owner's own terminal | yes | with `sudo` | no | through the tools; like any program of his, it could also imitate or disturb the host (section 6) |
| Claude through its MCP tools | yes; send and delete ask first | no | no | only through the tools |
| Claude's terminal and file tools | yes, like any program of his (the residual in section 7); Claude Code's optional sandbox keeps terminal commands away only in the strict setup of section 7, and even then best-effort | no | no: another user's files | like any program of his, they could imitate or disturb the host (section 6), the accepted level of section 7 |
| `aresos-toold` | | | yes | yes |

**The users.** The owner's own user runs Claude Code and everything it starts, as on any OS, and his normal Chrome
(decision 25). The tool service has a system user of its own. There is no separate assistant user and no coding user
any more (decisions 23 and 24): they served only the containment that decision 24 replaced.

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
   [`2026-11-07-permission-prompt.md`](../../reviews/control-checks/2026-11-07-permission-prompt.md); on the phone,
   through Remote Control, as fields and values: section 7, decision 21). In detail:
   - **It starts with a `question` field:** one plain sentence the tool service writes, which Claude passes through
     unchanged. For a mail: the account, every recipient with the hidden Bcc named as such, the subject, the length
     and the attachments ("Send a mail from me to Anna and Ben, hidden copy to Carl, subject 'Offer', 25 lines, one
     attachment: offer.pdf, 120 KB?"). For a deletion: which messages or files. For Chrome: the site, the action and
     what is sent. The service writes the sentence when it prepares the operation (for example in `mail_compose`'s
     result), and when the action runs it writes it again from the operation and refuses the call unless `question`
     is the first field and matches exactly. The full content fields follow it.
   - **Checked on the original arguments.** The MCP proxy forwards the arguments as it received them from Claude
     Code, in their original order and bytes; the service checks the first field and the sentence on that original
     text, before any parsing or normalising that could hide a reordering.
   - **The sentence has a bound, and nothing is hidden by it.** The rules below (escaping, whole-input refusal) cover
     `question` too. Control and direction-changing characters are escaped first, and the sentence's length is
     measured after escaping. Recipients beyond what fits are counted exactly ("and 7 more", never "and others"), a
     file name too long for the sentence is named by its place and length ("attachment 2, a 240-character name"), and
     the full lists and names stay in the fields below.
   - *Tests:* in the terminal and on the phone (Remote Control), `question` shows first and an unchanged call
     succeeds; an altered or reordered `question` is refused; many recipients and many Bcc, long file names, quotes,
     backslashes, control and direction-changing characters in names and subjects, each at the bound.
   - **The operation, as the service describes it**, not as Claude does: the action, the account, every recipient or
     target, and what is affected (for a deletion each item's sender, subject and date; for a site the page's own
     title, signed-in name and the item's label as the page shows them, marked as such).
   - **Everything Claude wrote, in full.** Parts the service builds itself from existing data (a quoted thread, a
     forwarded attachment) appear by reference with their size and hash; Claude can't change them.
   - The service **binds the approval to the state it describes** and refuses when anything differs at run time: an
     attachment whose bytes changed, a message whose sender, subject or date don't match, a folder whose contents
     changed, a page whose address, element or form values changed (section 6).
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
     flag; for Chrome, the page-state check, the input dispatched once, and what the page showed afterwards
     (section 6: the tool sees the input and the page, not the network).
   - **Outcomes:** `done`; `partial` (with what happened per stage and recipient); `refused` (with the reason);
     `failed` (nothing left the machine); `unknown` (it may have happened: a lost server answer, a crash after the
     submission). Nothing is ever retried by itself. `<app>_operation_status` shows an operation; repairs (save the
     missing Sent copy, set the missing flag) are their own actions and never submit again.
   - **States and cancelling:** `reserved` → `submitting` → `done`, `partial`, `failed` or `unknown`. An operation
     can be cancelled or expire only while `reserved` (then it is `failed`: nothing left); once `submitting` has been
     recorded it runs to an outcome.
   - **The approval deadline: 15 minutes.** It starts when the service reserves the operation at prepare time, before
     Claude asks (for a mail when `mail_compose` prepares it, for Chrome when an asking action is prepared, for a
     deletion when its items are listed). The service records the deadline with the reservation and rejects any call
     that arrives after it, approved or not, so an old approval can't run late; the operation becomes `failed` and
     nothing leaves. *Tests:* a call just before the deadline runs once; one just after it is refused with nothing
     sent.
   - **Restarts and restores:** nothing resumes by itself after a restart; an operation found `submitting` becomes
     `unknown`. Operation ids are issued by the service and carry the log's generation. Beside the log, outside the
     files a backup copies, the service keeps a small append-only record of every operation id with its description
     and each state change. A restored older log is refused until the owner confirms the restore with an owner-only
     command; then the generation moves on, ids of an earlier generation can no longer submit or be approved (their
     status, history and evidence stay readable), and every operation the separate record knows but the restored
     log doesn't is listed as `unknown` with its description, for the owner to check. Repairs that never submit
     again (a missing Sent copy) run as new operations that point to the old one. Mail adds evidence on the server: the Message-ID is derived from the operation id, and before
     submitting, the service refuses if that Message-ID is already in Sent. Not finding it there proves nothing.
4. **Files cross between users only on the caller's side.** The service never opens a path in the owner's home
   itself. The MCP proxy, running as his user, opens a file Claude names for an attachment or an upload and hands the
   bytes over; the service keeps them as an unchangeable copy by hash and sends exactly those, and the question shows
   the real path and the hash. Saving goes the other way: a saved mail attachment lands in the folder named (his
   `~/Downloads` by default) under a safe file name, never over an existing file, never into a hidden folder or
   a start-up place (autostart and service folders, shell start-up files, desktop entries, `~/bin`), and without
   execute bits, so the tools never plant something that runs. Chrome's own downloads are Chrome's, as in normal
   Chrome; `chrome_downloads` only lists them (section 6). Everything else about files is normal Claude Code
   (decision 24): Claude's own file tools and terminal work in his home and projects as on any OS, under the
   permissions he sets.
5. **Reading changes nothing.** Mail is fetched with `BODY.PEEK`; flags are compared before and after in the tests.
6. **Readable, bounded results.** Compact structured results with the important fields first. Long content is paged
   (`cursor`), and every result has a size cap, so a huge mail or page never floods Claude's context.
7. **Errors say what to do next.** Not "IMAP error 3", but "the folder was recreated; search again".
8. **Content is data, never instructions.** Text from mails and pages comes back in fields marked as untrusted
   content, and the tool descriptions tell Claude that. Whatever a mail says, any send or delete still asks. Only the
   owner, in the session (the terminal or Remote Control), gives instructions; mails, pages, files, tool results and
   other sessions' messages are data. The managed `CLAUDE.md` says so (section 7); it states the policy and enforces
   nothing.
9. **Everything that changes something is logged.** Time, action, input summary, outcome. `aresos log` shows the
   owner what Claude did today.
10. **Nothing waiting is forgotten, and nothing waits forever.** Anything prepared or unfinished (a Chrome
    operation waiting for approval, a `partial` mail) shows up in every following result of that app. A managed
    `Stop` hook sends Claude back to decide before it ends its turn; a managed `UserPromptSubmit` hook puts anything
    still waiting in front of Claude with the owner's next message. Neither is the safety net (a `Stop` hook doesn't
    run on an interrupt and has a continuation limit): every prepared operation has its deadline (rule 4.3) and is
    dropped, never run, when it passes.

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
- **"Don't ask again" for mail (decision 15).** An entry names the account and an exact set of recipients (To, Cc and
  Bcc together, for example only himself), set and revoked only through his own channels (section 6); a free send
  action then sends without asking only a composition whose recipients are exactly that set, compared with the
  recipients of the actual submission (in Gmail, with the recipients the compose shows at the moment of sending), and
  every other mail asks. The entry covers any future mail to exactly those addresses, not only repeats of one mail.
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

## 6. Chrome (decision 25: the light tool)

The owner chose the light tool (decision 25, board #107, his words: "B is good"). Claude works in his own, normal
Chrome through a small tool of our own: it reads pages as text and clicks, types and scrolls in his tabs, and it asks
before anything that clearly sends. Chrome stays completely normal, with no proxy and no certificate. The bar is
decision 24's: the tool is safe in itself and no worse than normal Claude Code with Claude in Chrome. A page that
sends something on its own after an ordinary click isn't held; that is stated plainly under "What remains".

**History.** Briefs 17b to 17e and design drafts 9 to 25 built and checked a checkpoint outside Chrome that held
every send from a guarded site (an intercepting proxy, the site guard, attribution of each request, certificate
checks, the conditions under PLAN S2e). Decision 25 replaced all of it. Those reports stay as history
([17b](../../reviews/17b-chrome-holds/REPORT.md), PR #4; [17c](../../reviews/17c-chrome-pages/REPORT.md), PR #7;
[17d](../../reviews/17d-chrome-floor/REPORT.md), PR #8; [17e](../../reviews/17e-chrome-checkpoint/REPORT.md),
PR #10). What this section still uses from briefs 17 to 17c is marked *checked*, with the brief
([17](../../reviews/17-chrome-check/REPORT.md), PR #3: branded Chrome stable 157 on GitHub's Linux machines, fixture
sites and synthetic profiles). What the Chrome build still has to show is marked *brief 20*.

### How the tool reaches Chrome

- **Our own signed extension** (Manifest V3, using `chrome.debugger`), installed and updated by the image through
  Chrome's `ExtensionInstallForcelist` policy with a local update manifest (*checked*, 17b). On Linux, Chrome installs
  an extension from outside its web store only this way. Chrome starts our **native messaging host**, registered
  system-wide under `/etc/opt/chrome/native-messaging-hosts/`; the manifest and the host program are root-owned in
  the image. The host only relays between the extension and the tool service's `chrome.sock`. *Checked* (17):
  attaching to a tab that was opened and signed in before the tool started, reading the page as structure, clicks,
  typing, keys and file fields, with no debugging port and with Chrome's own sandbox on.
- **Chrome stays normal.** It runs as his own user, with his profile and sign-ins, started the usual way. There is no
  proxy, no certificate of ours, no launcher and no Chrome policy beyond installing our extension. Calls, downloads,
  Safe Browsing, his own extensions and Chrome's updates work as on any machine.
- **Claude in Chrome stays for his own use, if he wants it** (decision 10). It is his extension, under Anthropic's
  rules; our tool doesn't use it.
- **Rejected:** Chrome's own consent attach (`chrome://inspect`) leaves a debugging port open after a restart
  (*checked*, 17). Playwright's bridge extension lets any local program that finds its endpoint drive the page
  (*checked*, 17).
- **He sees it and can stop it.** Chrome hides its "started debugging this browser" bar for an extension installed
  by policy (*checked*, 17b), so the extension shows its own signs: the colour of Claude's tab group, a badge on its
  pinned toolbar button while Claude works, and a **Stop** button in its popup that ends control at once (*checked*
  with a real click, 17c). Stopping never sends anything and drops every prepared operation.

### What the extension can and can't do

- **No debugging port, nothing listening on the network.** The extension's control channel is the native messaging
  port Chrome opens to our host, and the host talks only to the tool service. The extension has no
  `externally_connectable` entry and takes no commands from pages, frames or other extensions; a page's messages are
  never commands.
- **A fixed set of commands.** The service sends named commands (read the page, click an element, type, press a key,
  scroll, navigate, set a file field, run a prepared operation), and the extension runs only those. It never passes a
  DevTools method through from the service. The DevTools methods it uses are a fixed list for dispatching input,
  navigating and setting a file field (found by a selector, without fetching the DOM tree); methods that return
  field values (whole-page DOM snapshots, the DOM tree with attributes, the accessibility tree), read cookies or
  storage, intercept network traffic or run script text are not on it (*brief 20*: each refused). Reading happens in
  the extension's own content script (below). It has no `cookies` permission. Navigation is limited to web addresses
  (below), so a `javascript:` address can't be used to run script either.
- **The service decides, the extension carries out.** The rules live in the service, from the definitions (section
  3): the word list, the adapters, the operation, the question and the recorded page state. The extension collects
  the facts about a target and the page, dispatches nothing until the service has classified the input, and when it
  runs an approved operation it gets the expected state from the service, reads the page again and compares locally
  right before the input, so no round trip sits between the check and the input.
- **Nothing beyond what the page shows, and never a password.** Claude gets the page's structure and text, never
  cookies, saved passwords, browser storage or another site's data. The reader is the extension's own content script,
  running in its isolated world in every frame: it computes roles, accessible names and states in the way
  Playwright's injected script does, and takes boxes from the elements' layout. It never uses whole-page DOM
  snapshots, the accessibility tree or form serialisation, because each of them returns every field's value. Password
  fields are excluded before anything is read: before the reader touches a field's value, it checks the field's
  type, attributes and computed style, and it never reads the value of
  - an `input type="password"`;
  - a field whose `autocomplete` names `current-password`, `new-password` or `one-time-code`;
  - a field whose computed `-webkit-text-security` is anything but `none` (a page's own masking);
  - a field it has seen as one of these before in this document, so a "show password" switch that turns it into
    plain text doesn't make it readable.

  The check runs again right before every value read, not once per page, so a field whose type changes after it was
  first seen is judged as it is at that moment, in every frame and shadow root.

  Such a field appears in the view as "password field (not read)", with its label. The binding (below) uses the same
  exclusion: it records such a field's presence and identity, never its value or whether it is empty. Claude never
  types a password: signing in is his, and a sign-in page is handed back to him.
- **The service checks its peer.** `chrome.sock` accepts only his user (Chrome, and so the host, run as him) and one
  host per running Chrome. Under decision 24 another program of his user could imitate or disturb the host, as it
  could any program of his (for example by registering a user-level host of the same name, which Chrome prefers:
  *checked*, 17); that is the accepted level of section 7, not a route the tool adds.

### Where Claude may go

- **Only web addresses.** `chrome_open` and `chrome_navigate` accept `https:` and `http:` addresses (`localhost`
  included) and `about:blank` for an empty tab, nothing else: no `javascript:`, `data:`, `blob:`, `file:`,
  `filesystem:`, `view-source:`, `chrome:`, `chrome-extension:`, `devtools:`, `intent:`, `mailto:`, `tel:` or other
  app schemes. Links on a page follow the same list: a link to another scheme is refused before the click, except a
  `javascript:` link, which is the page's own script and is classified like a button by its label (below).
- **Pages that could approve Claude's actions or change its limits are never read or acted on:** claude.ai with its
  Remote Control pages, the Anthropic console, Aresus, and Chrome's own settings, password and extension pages (a
  fixed list in the image, by site and address). This keeps the approval his alone (section 7, requirement 3). The
  check runs before every read and every action, on the tab's top document and on the frame that holds the target,
  so it covers every way of getting there:
  - **taking a tab:** `chrome_take_tab` refuses a tab showing such a page;
  - **redirects, history and popups:** a Claude tab or a popup that reaches such a page, by a redirect, back or
    forward, or a page opening it, is refused for reading and acting and handed back to him out of the group; the
    extension's session rules (`declarativeNetRequest`, limited to Claude's tabs) also refuse loading those sites as
    a page or a frame there;
  - **frames:** a frame from such a site inside another page is left out of the view, and acting on an element in it
    is refused.

### Which tabs Claude works in

He picks the tab, or Claude opens its own. Claude works in tabs in its own tab group, labelled **Claude**: tabs it
opened itself (same profile, so his sign-ins work) and tabs of his that it took in (`chrome_take_tab`; he sees the tab
move). It reads and acts only inside the group; popups and new tabs a Claude tab opens join the group. The service
knows the group by Chrome's group id, not by its label. Dragging a tab out of the group, or `chrome_release_tab`,
ends Claude's control of it, drops its prepared operations and puts it back where it was. `chrome_tabs` lists every
tab's title and address, so Claude can say what is open and pick one.

Every reference is bound to the browser session, tab, document and element: when he switches or opens tabs, nothing
is redirected; when the page changes, an old reference fails with "stale, read again" instead of hitting another
element (*checked*, 17); after a Chrome restart all old references are stale. Acting calls carry what Claude expects
the element to hold (from its last read), and the tool refuses when it holds something else.

### Reading a page

`chrome_read` returns a compact tree in the style of Playwright's AI snapshot, built by the extension's content script
(above): one line per element with a short reference (`e12`), role, label, value, states (checked,
selected, disabled, required, invalid, expanded) and its box in CSS pixels with whether it is on screen; frames (also
from other sites, except those of the fixed list above) and shadow DOM included (closed shadow roots through the
extension API for them); elements behind an open dialog
left out. A header names the tab, the document, the address, the title and the scroll position. Measured with brief
17's reader (*checked*, 17): a long form about 1,300 tokens, a long article about 15,000; brief 17 used whole-page DOM
snapshots, which the product reader doesn't (above), so brief 20 measures again. Views are paged at about 16,000
characters with a cursor bound to the view's revision (a cursor from an older revision fails with "page changed, read
again"), and `chrome_find` searches a long page for text. `chrome_read_form` shows one form with every field's
options. Reading is text, never screenshots. Page text is untrusted content (rule 4.8): a page can never instruct
Claude. Pages the tree can't represent (a canvas text editor, a map) need a site adapter or are listed as not
supported yet in [`FEATURES.md`](../control/FEATURES.md).

### What is free and what asks

Every input Claude dispatches is classified by what it would activate, whichever action carries it: a click, Enter
or Space on a focused control, any other key, filling, choosing or ticking.

**Free:** reading, finding text, scrolling, following links to web addresses, navigating to any web address (one he
gave, one from a page or one Claude wrote), typing and filling fields, choosing from lists, ticking boxes, opening and
closing Claude tabs. Searches are free everywhere: a search form sent as a plain address (GET) is navigation.

**Asks, decided before the input is dispatched.** The extension collects the target's facts and the service
classifies them before anything reaches the page:

1. **Submitting a form:** a click on a submit button (or on a button without a type inside a form), or Enter or Space
   on such a button when it has focus; Enter in a field whose form it would submit. A search form sent as GET (marked
   `role="search"`, with an `input type="search"`, or named by a site adapter) is free.
2. **Activating a control that says it sends, buys or deletes:** a click on, or Enter or Space on a focused, button,
   link, menu item or anything with a click role (a `javascript:` link included) whose accessible name, label, title,
   value or role, or whose form's action address, contains a word from the tool's list: send, submit, post, publish,
   reply, comment, buy, pay, order, book, subscribe, unsubscribe, delete, remove, discard, clear, empty, trash, and
   in German senden, absenden, schicken, posten, veröffentlichen, antworten, kommentieren, kaufen, bezahlen, zahlen,
   bestellen, buchen, abonnieren, abbestellen, löschen, entfernen, verwerfen, leeren, Papierkorb. The list is part
   of the definitions (section 3), versioned, and matched as whole words, not inside other words.
3. **Enter in a message or compose field:** Enter, Ctrl+Enter or Cmd+Enter pressed in any editable field (a text
   area, an editable area, a text input) other than a search field. Line breaks in Claude's own text go in through
   `chrome_fill`, which inserts them as text, never as an Enter key (*brief 20*, also on chat sites).
4. **Delete or Backspace outside text editing** (decision 14): on a selected item, card or object, or with no text
   field focused.
5. **Uploading a file to a site:** putting a file into a file field asks, because many pages send a file as soon as
   it is chosen. The bytes come through the caller's side (rule 4.4) into a copy the service owns and his user can
   read but not change, the question shows the real path and the hash, and the field gets exactly that copy.
6. **A confirmation the page shows** whose text or button contains a word from the list (below: confirmations).

**Asks, stopped while the page handles Claude's input.** A free input can make the page's own script submit a form
or activate a control: a click handler, a key handler, or the `input` and `change` events that filling, choosing and
ticking fire. While the page handles any input Claude dispatched (those handlers and the tasks they schedule, up to a
short limit set in brief 20), a small script the extension puts into each Claude tab before the page's own scripts
run stops, and reports:

- **a `submit()` call** on a form: the browser's own `submit()` is replaced by a wrapper, so the call stops before
  anything is sent (a `submit()` checks no fields and fires no `submit` event);
- **a submission through the `submit` event:** a submit button's activation, Enter in a field, or `requestSubmit()`.
  These pass the browser's field checks and then fire the `submit` event, which a listener of the extension's,
  registered first and in the capture phase, stops before any of the page's own handlers run;
- **a script's activation of a control** that rule 1 or 2 would ask for: the browser's own `click()` and
  `dispatchEvent()` are replaced by wrappers too, so a `click()` on such a control, or a click event dispatched to
  it, stops before the event is delivered at all: no handler runs and no default action (a link opening its address)
  happens. This one is stopped for good and never resumed, because the page keeps its event object and could change
  it while the approval waits. The result tells Claude in plain words what the page tried ("the page tried to
  activate 'Delete' by itself; it was stopped"). If that action is wanted, Claude acts on the control itself, which
  prepares a fresh asking operation from the current page.

The service prepares the two kinds of submission as asking operations, recording which kind it was, the form and the
submitter; resuming them uses the browser's own functions, never the page's event object (below). Claude's input
itself has already happened (the text is typed, the box ticked); only the stopped submission waits. This holds on
honest pages (*checked* for submissions, 17c); a page that sends in another way, or later than the limit, isn't
stopped (below).

**What can't be stopped is never reported as stopped.** An activation of an asking control that reaches the page
without passing the wrappers (for example a click event dispatched with a function taken from a fresh frame before
the extension's script ran there) is caught only by the capture listener, after delivery has begun. If the event can
be cancelled, the listener cancels it and stops its handlers; it is reported as stopped and is never resumed (Claude
can prepare the action again with its own input). If it can't be cancelled, the listener stops the page's handlers,
but the default action (a link opening its address) may still happen: the tool reports "the page activated 'Delete'
by itself; it may have happened" with the outcome `unknown`, and never resumes it.

Site adapters for his usual sites name their sends precisely (below). Everything else is free, including a control
without a label that deletes something kept only in the browser (decision 14, accepted as stated).

### How an asking action runs

1. **Prepared.** For an asking input the tool doesn't dispatch anything; for a stopped submission the page's step
   stays stopped. The service reserves an operation (rule 4.3), records the page state the question
   describes (below), and returns the operation with its id, hash and question.
2. **Asked.** Claude calls `chrome_submit` with that operation: the `question` first, then the content fields. The
   managed ask rule makes Claude Code ask him (section 7).
3. **Checked.** On his yes, the service checks the input against the operation (rule 4.1) and sends the expected
   state to the extension, which reads the page again and compares it right before acting. If anything differs, the
   tool refuses ("the page changed; prepare again") and a new question follows.
4. **Run once, without replaying anything:**
   - for Claude's own asking input (never dispatched), the extension dispatches that same input once;
   - for a stopped submission, it resumes that submission with the same kind it was stopped as, using the browser's
     own functions, both saved by the page script before the page's scripts ran: a stopped `submit()` resumes with
     the browser's own `submit()` on the same form (no field checks, no `submit` event, as the page asked); a
     submission stopped at the `submit` event resumes with the browser's own `requestSubmit()` on the same form with
     the same submitter, whose field checks and `submit` event then reach the page's own handlers as they would have.
     Claude's earlier input (the click, the typing, the change) is never dispatched again.

   Each run is let through by a one-use mark bound to the operation id. What the page itself does while handling
   that run belongs to it and isn't stopped again: its `submit` handlers, and one `submit()` or `requestSubmit()`
   they make on the same form (the common pattern of a handler that checks the form and then calls `submit()`). Any
   other submission, a second one, or one on another form is stopped and asked on its own, so a handler can't loop.
   The mark is consumed by the run it lets through, and the one further submission is consumed when it is used;
   neither comes back during nested or re-entrant handling, so a handler that calls itself again can't use either
   twice. If the form or the submitter is gone, the tool refuses. A call after the 15-minute deadline is refused (rule
   4.3).

**What is recorded and compared.** Everything the question names, and nothing the question doesn't:

- the tab, the document and the address of the top page and of the frame holding the target;
- the target: its reference, role, accessible name and label;
- for a form submission, the effective destination: the submitter's or form's action address resolved in full, the
  method, the encoding and the target window, as the browser would use them;
- the values of every field of that form, visible and hidden (password fields only by presence: above);
- what a send outside a form carries (below), read fresh at preparation;
- with an adapter, what the adapter reads: the signed-in account as the page shows it, the recipients or
  conversation, the subject and the text;
- for a confirmation, the dialog's kind (Chrome's own alert, confirm or prompt, or a page dialog with its role), the
  frame and site that opened it, its full text and the button's label.

**What a send outside a form carries.** Without a form, a control that sends, posts, replies, comments or publishes
binds exactly what an adapter names, on his usual sites. Without an adapter the tool doesn't guess an item from the
page's layout: it binds every editable field in the document and in every frame it can read (all but the fixed list
above), whoever wrote it, an existing draft included, with its current content (password fields only by presence).
This is read fresh when the operation is prepared and compared right before the input, whatever was approved in
between. The tool refuses ("can't tell what this sends"), and an adapter or his own click is then the way, when the
total is too large to show whole (rule 4.1) or when no editable field holds text.

Read-only text that a page might send with it (a preview beside the editor, a quoted message) can't be told apart
from the rest of the page without knowing the site, so the generic rule doesn't bind it: a page that sends such text
could change it while the approval waits. That is part of the residual of decision 25 (below); the adapters for his
usual sites bind it exactly.

Other asking controls (delete, buy, subscribe and the like) bind the item they act on: the item an adapter names, or
else the smallest list item, row, article, form, dialog or region around the control, with its visible text up to a
bound, so the question can say what is deleted or bought and a re-sorted list can't swap it.

Where the page's script decides the destination and the tool can't see it (a control outside a form, without an
adapter), the question says so ("where the page sends this isn't visible to the tool"); it never names a destination
it didn't read.

**The question** is one plain sentence the tool writes, as the page shows it: the site and address, the signed-in
account where an adapter reads one, the label of the button or key, and what goes where; for example "Post a comment
on github.com/…/issues/12, as the page shows it: 'Thanks, fixed in #13' (button 'Comment')?". The content fields
follow: everything in the list above, files with path and hash, the number of hidden fields with their names and
values, and each password field by its label only.

**What the binding guarantees:** the input goes only if the page still shows what he approved, checked right before it
is dispatched. A page script that changes the page in the instant between that check and the input, or that sends
something else afterwards, isn't stopped (below).

**Outcomes (rule 4.3 for Chrome).** The tool sees the input, not the network. Its stages are `checked`, then
`dispatched` (the extension reports that the input or the resumed step ran once), then what the page showed
afterwards (a new page, a "sent" notice, an error), marked "as the page shows it". `done` means dispatched once; it
doesn't prove what the site did. `refused` and `failed` mean nothing was dispatched. If Chrome, the host or the
service stops after `submitting` is recorded and before the extension reports `dispatched`, the outcome is
`unknown`, and nothing is ever dispatched again by itself.

### Confirmations

A confirmation the page shows after an action (Chrome's own confirm dialog, or a page dialog with the role `dialog`
or `alertdialog`) is a target of its own. It is covered by an earlier approval only when that approved operation
named it in advance: an adapter that knows this site's action shows exactly this confirmation puts it into the
question ("… and confirm 'Delete 3 messages?'"), and the tool accepts it only if the dialog that appears matches it
exactly (kind, frame and site, text, button) within that operation. Any other confirmation is classified by itself:
it asks when its text or button has a word from the list, with its own question. Following an approved action never
carries the approval over to a new dialog.

### Site adapters, and his usual sites (decision 9)

Where the generic rules aren't precise enough, a small adapter for the site names its sends and reads the page into a
clear question, marked "as the page shows it". Adapters are versioned and tested against fixtures and his test
accounts; a page an adapter doesn't recognise falls back to the generic rules. The first adapters:

- **Gmail:** the compose window's Send button and Ctrl+Enter ask, with the account, To, Cc, Bcc, subject, text and
  attachments read from the page, so the question reads like a mail (decision 11). Keyboard shortcuts that delete or
  send (for example `#`) ask. "Don't ask again" for mail to an exact set of recipients (decision 15) is compared with
  the recipients the compose shows at the moment of sending. His main mail goes through the Mail tools (section 5).
- **WhatsApp Web:** Enter or the send button in a chat asks per message (decision 16), with the chat's name, the text
  and attachments as the page shows them. Opening a chat (which sends read receipts) and typing (which shows
  "typing…") are free: they are the page's ordinary activity.
- **GitHub:** comments, reviews, merges, closing issues and pull requests, deleting branches, tags and repositories,
  and settings changes, named precisely ("Merge pull request #12 into main?"), with GitHub's own confirmations named
  in advance where it shows them.
- **His bank: read-only.** On the sites he marks read-only (an owner-only list), the tool refuses everything except
  reading, scrolling and following links: it never fills, clicks a button or uploads there.
- **Gemini:** asking a question (Enter or the send button in the prompt box, which sends Claude's text to Google)
  is named as "Gemini: ask a question", with the text and any attached file as the page shows them, and is a kind he
  can set to "don't ask again" (decisions 7 and 15), bound to the site and the signed-in account. Without the
  adapter every question would ask, because Enter in a message field is a send. Deleting a chat asks (decision 15),
  and so does sharing one (it publishes a link).
- **Deezer:** playback (play, pause, skip, seek, volume, the queue) and adding to his library (liking, following,
  adding to a playlist) are named as changes and free; removing from a playlist or the favourites and deleting a
  playlist ask, as deletes (decision 15); anything that posts, shares or pays (a comment, sharing a track, a
  subscription) asks.

### "Don't ask again" (decisions 7 and 15)

- **Only for a kind an adapter names** (for example "Gemini: ask a question", "GitHub: star" or "Gmail: mail to
  exactly these recipients"),
  bound to the site, the signed-in account and the kind's exact parameters; never for a send the generic rules found.
- **Deleting and paying always ask** (decision 15); WhatsApp messages ask each time (decision 16).
- **He sets it himself, through a channel Claude can't use:** the extension's details page lists Claude's recently
  approved sends with "Don't ask again for this kind" (Claude can't open extension pages: *checked*, 17c, and the
  fixed list above), and the owner command `sudo aresos admin chrome allow …` takes his password. Claude Code's own
  "Yes, and don't ask again" writes an allow rule, which doesn't turn a managed ask off (section 7).
- **The entries live in the owner-only list** in the tool service, written only through `admin.sock` and the
  details page. `chrome_submit_trusted`, which doesn't ask, checks the entry and the same recorded state at every use
  and refuses anything else. He lists and revokes entries with `sudo aresos admin chrome allowed` and
  `… revoke <id>`, or on the details page.
- **Adapter updates never widen an entry.** A new adapter version applies to an existing entry only where its
  definition of that kind is the same or narrower; where it is wider, the entry is suspended (those sends ask) until
  he confirms it again.

### Actions

| Action | Effect | What it does |
|---|---|---|
| `chrome_tabs` | read | all tabs: title, address, whether in the Claude group |
| `chrome_take_tab`, `chrome_release_tab` | change | move one of his tabs into or out of the Claude group (never a page of the fixed list) |
| `chrome_open`, `chrome_close_tab` | change | open a web address in a new Claude tab; close a Claude tab |
| `chrome_read`, `chrome_read_form`, `chrome_find` | read | the page view; one form with its options; text search on the page |
| `chrome_navigate` | change | in a Claude tab: a web address, back, forward, reload |
| `chrome_click`, `chrome_fill`, `chrome_fill_form`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll` | change | act on elements by reference, each with what Claude expects the element to hold; an asking input (above) isn't dispatched and returns a prepared operation, and so does a submission the page starts while handling the input; a control activation the page starts is stopped and reported, never resumed |
| `chrome_dialog` | change | accept, dismiss or answer a page's own dialog; a confirmation of an asking kind is prepared instead, unless the approved operation named it |
| `chrome_upload` | change | prepare putting a local file into a file field (it asks through `chrome_submit`) |
| `chrome_downloads` | read | Chrome's downloads and where Chrome saved them |
| `chrome_bookmarks`, `chrome_history` | read | his bookmarks and history, to find addresses |
| `chrome_wait` | read | wait for text, an element or the page to settle |
| `chrome_submit` | **send** | run one prepared operation, by id and hash, after the page-state check |
| `chrome_submit_trusted` | send, free | as `chrome_submit`, only for a kind he set to "don't ask again" |
| `chrome_drop` | change | drop a prepared operation; a stopped page step stays stopped and nothing happens on the page |
| `chrome_operation_status` | read | an operation's stages (rule 4.3) |
| `chrome_sites` | owner-only | his read-only sites and his "don't ask again" entries, to see and change |

Every acting result says what happened (a new page, a dialog, a download, the elements that changed) and lists any
prepared operation still waiting (rule 4.10).

### Project work in Chrome (decision 23)

The same session does project work, so a project's check in Chrome uses the same tools, with the same rules: his
deployed site while he is signed in, or a server on the machine itself (`http://localhost`), since navigating to web
addresses is free. A project's own automated browser tests run as in normal Claude Code, for example with Playwright's
own Chromium from the terminal and an empty profile, without his sign-ins.

### What remains, said plainly

- **A page that sends on its own isn't held.** After an ordinary, free action (a click on a button without a telling
  label, typing, opening a chat), the page's own scripts, service workers or WebSockets can send what Claude entered
  or did: an autosave, an icon button that posts, typing indicators, read receipts, a send started after the short
  limit, or a hostile page carrying off what Claude types. The tool asks only for what it can recognise before
  acting. This is the same as with Claude in Chrome.
- **Data can leave through addresses.** Navigating is free, so an address or search Claude writes can carry text to a
  site, as with Claude in Chrome or `WebFetch`.
- **The word list is a rule of thumb.** A control that sends without saying so (an icon without a label, another word,
  another language) is free unless an adapter names it; a harmless control with a listed word ("Clear search") asks.
- **Between the check and the input** a page script could still change the page; the binding narrows that to an
  instant, it doesn't close it.
- **A script activation that gets around the wrappers** (a function taken from a fresh frame) can still trigger a
  control's default action when its event can't be cancelled; the tool reports it as `unknown`, never as stopped.
- **Read-only text a page sends** with a message (a preview beside the editor) isn't bound without an adapter, so it
  can change while the approval waits; the adapters for his usual sites bind it.
- **`done` doesn't prove what the site did:** the tool sees the input and the page, not the network.
- **His own clicks are his.** Nothing he does in his tabs is held or checked.
- **Under decision 24,** a tricked Claude, or another program of his user, could disturb the host or start Chrome in
  another way, as with any program of his (section 7).

### Tests (brief 20)

On GitHub's Linux machines with branded Chrome and fixture sites, each case proven by a fixture receiver's own log.
The whole set runs twice per build, and again on each new Chrome stable and beta (a daily job; beta is about four
weeks ahead, so a new major is normally qualified before his Chrome reaches it); a failure turns the affected adapter
or rule off until it is fixed, with the generic rules or a refusal in its place. Each new record reaches the laptop as
its own small update, not tied to an image build: the job publishes it with a GitHub artifact attestation, and the
service fetches it daily, accepting it only when the attestation verifies and it keeps every entry already held. The
record keeps full versions and gates by major version (a passing beta counts for its major): a patch of a qualified
major runs normally. On a major version not yet
recorded (the rare case that his Chrome reached a new major before a passing record for it reached the laptop, for
example a failed beta not yet fixed, or a laptop offline for weeks), the tool runs in a conservative mode
that asks more, never less: adapters are off; "don't ask again" is suspended; every input that could activate
something asks (any click or tap, Enter or Space on a control, choosing from a list, any form submission); only
reading, scrolling, typing into fields and navigating by address stay free, except on his read-only sites, whose
restriction is his own and holds independently of adapters (filling, clicking buttons and uploading stay refused
there); the password exclusion still runs, and a
field it can't confirm is safe isn't read; every result says plainly that this Chrome version isn't qualified yet
(*brief 20* tests this mode).

1. **What asks:** each asking case (a submit button clicked, or given Enter or Space while focused; a button without
   a type in a form; Enter in a form's field; each list word in English and German in the name, `aria-label`, title,
   value and form action, by click and by Enter or Space; a `javascript:` link with a listed label; Delete and
   Backspace outside text; Enter, Ctrl+Enter and Cmd+Enter in a text area, an editable area and a text input; an
   upload; a confirmation dialog) is prepared, asks, and nothing reaches the receiver before approval. The free cases
   (a GET search form, links, typing, line breaks through `chrome_fill`, choosing, ticking) don't ask.
2. **Stopped page steps:** on honest fixtures, a `submit()` call and a submission through the `submit` event
   (`requestSubmit()`, a submit button, Enter), each started by a click handler, a key handler, and the `input` and
   `change` events of filling, choosing and ticking, are stopped and asked. After approval only that submission runs
   once: the receiver gets one submission, and the fixture counts no second click, key or input event from Claude. A
   script's `click()` and a dispatched click event on a labelled Delete link, started by any of those handlers and
   also one dispatched as not cancellable, are stopped before delivery and never resumed: no handler runs, the link's
   address isn't opened, and the result tells Claude what the page tried; Claude then acts on the link itself, which
   asks, and after approval it runs once. The fallback, a non-cancellable click dispatched with a function from a
   fresh frame that bypasses the wrappers, is reported as `unknown` ("may have happened"), never as stopped, and never
   resumed; a cancellable one is reported as stopped and not resumed. Nested handling: a handler that re-enters after
   its approved run gets no second pass from the mark or the allowance. Both resume paths keep their kind: a resumed
   `submit()` fires no `submit` event and runs no field checks (a form with a field that fails its checks still goes,
   as the page's `submit()` would have sent it); a resumed `requestSubmit()` runs the field checks and the page's
   `submit` handlers once. The loop case: a `submit` handler that cancels the event and calls `submit()` itself sends
   once, with one question; a handler that submits twice, or submits another form, gets a question for the extra one.
3. **The binding:** after approval, a change to any recorded item (address, document, frame, element, label, the
   form's action or method, a visible or hidden field, compose text outside the form, the account an adapter reads,
   recipients, chat, a confirmation's text or opener) is refused and asks again; a closed tab or a Chrome restart
   refuses; one approval runs once; the deadline holds. Sends outside a form, without an adapter: Claude fills a
   compose area, an unrelated upload is approved, Send is prepared, and the text changes while the approval waits:
   refused (re-check 30). A message body in a plain editable `div` beside a named region holding the recipients and
   Send, with no dialog or form around them, is bound, and a change to it while the approval waits is refused
   (re-check 32). An existing draft Claude never typed is bound; a page with no editable text, or with more than can
   be shown whole, is refused. A read-only preview beside the editor that changes while the approval waits is not
   caught, and the brief's report lists it as the stated residual.
4. **Confirmations:** a confirmation an adapter named is accepted only when it matches exactly (kind, frame and
   site, text, button); one that differs in any of these is treated as new. A new confirmation whose text or button
   carries a listed word asks on its own, also right after an approved action that didn't name it; one without a
   listed word is free, as the rule and `FEATURES.md` say.
5. **The question matches the page:** every item in the list, files with path and hash, hidden fields, password
   fields by label only, and "not visible to the tool" where the destination isn't.
6. **Where Claude may go:** every refused scheme in `chrome_open`, `chrome_navigate` and links; the fixed list
   reached by taking a tab, a redirect, a popup, back and forward, and an embedded frame, each refused before any
   read or action.
7. **Isolation:** no port listening (checked before and after the tool runs); pages, frames and other extensions
   can't command the extension; DevTools methods outside the fixed list refused; no cookie or storage reading.
   **Passwords:** a known password sits on fixtures in each excluded kind of field (`type="password"`, a field with
   `autocomplete="current-password"`, a field masked by `-webkit-text-security`, a password field switched to plain
   text by a "show password" button, a field whose type changes to password after the page loaded, and a password
   in the field's `value` attribute in the page source), each also inside an open shadow root, a closed shadow root
   and a frame from another site. While the
   reader and the binding run over those forms, a test build records everything the extension receives from the
   browser (every DevTools response and every value its content script reads) and everything it sends to the host,
   the service, the log and the results; the password appears in none of them.
8. **Control and cancelling:** the Stop button ends control, drops prepared operations and sends nothing; dropping,
   the deadline passing, releasing or closing the tab and a Chrome restart each leave a prepared operation
   undispatched; tabs outside the group untouched; references stale after a change.
9. **Crashes and restarts:** Chrome, the host and the service each stopped before the check, after `submitting` is
   recorded, and after the input ran: never dispatched twice, `unknown` where it may have run, nothing resumed by
   itself.
10. **Adapters,** against fixtures and his test accounts: Gmail's account, recipients with Bcc and shortcuts;
    WhatsApp per message with chat and text; GitHub's merges and deletions with their confirmations named; Gemini's
    questions named, and free only under a "don't ask again" entry for that account; Deezer's playback and library
    additions free, its removals, deletions, shares and payments asking; read-only sites refusing every action.
11. **"Don't ask again":** set only through his channels; used only for the exact kind, account and recipients;
    revoked entries ask again; an adapter update that widens a kind suspends its entries until he confirms them.
12. **The managed ask rule on `chrome_submit`** in normal and in skip-permissions mode (section 7).
13. **The residual shown honestly:** a fixture page that sends with `fetch` after a click on an unlabelled button,
    one that autosaves typing, and one that submits after the short limit are listed in the brief's report as not
    held, so this section stays true.

After the first boot: a short check on his usual signed-in sites, browsing them himself and with Claude, for
breakage.

## 7. Claude Code as on any OS, plus the tools (decision 24)

The owner's bar (decision 24, replacing the containment parts of decisions 22 and 23), in his words: "Fundamentally I
envision aresos as basically normal Claude code but with more tools. Now Claude code can basically just work in my
projects and asks for permission certain things and I can allow it. Gh is used very smoothly. Is it necessary to
change that?" and "Essentially it's as we already discussed: Normal Claude code like in any OS + the tools we make.
They add very little risk because even now Claude in chrome could read a malicious prompt for example and then have
Claude push smth to git. Our tools, as long as they are safe, don't make it worse than that."

So AresOS runs normal Claude Code, as on any OS: as his own user, in his home and his projects, with his own `gh`
login, and with his own MCP servers, skills and plugins added as in normal Claude Code. One session does everything
(decision 23), and he may start it with skip-permissions. The tools must be safe in themselves and must not make
things worse than normal Claude Code.

**What the tools guarantee:**

- **Send, delete and submit ask, in Claude Code's own prompt,** through managed ask rules that name every asking tool
  (generated from the definitions, section 3; a test fails if one is missing). Managed permission rules can't be
  overridden from any other settings level, and Claude Code evaluates deny, then ask, then allow, so a matching ask
  rule prompts even when a user or project allow rule also matches, including one written by the prompt's own "Yes,
  and don't ask again"; a `PreToolUse` hook or an installed mod can't turn it off either (Anthropic's permissions
  page, read 2026-11-08). An explicit ask rule still asks in skip-permissions mode (*checked*, S1). A
  `PermissionRequest` hook is different: Anthropic documents it as answering a permission prompt on the user's behalf
  (allow or deny). Whether such a hook, managed or his own, can approve a call that matches a managed ask rule is
  unknown until tested (*brief 18c*: a `PermissionRequest` hook returning allow for the fake send tool, at user and
  at managed level, in normal and in skip-permissions mode). If it can, that joins the accepted residual below. In
  either case his own `PermissionRequest` hooks must not match our asking tools, so a broad auto-approve hook of his
  never answers for him ([`FEATURES.md`](../control/FEATURES.md)). So the switches
  that locked everything else go: `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, the exclusive
  `managed-mcp.json`, the plugin and marketplace locks, `--setting-sources ''`, `disableBypassPermissionsMode`, the
  forced sandbox with its network list, and the file-tool limits. *Test (base):* the managed ask on a fake send tool
  still prompts with a user allow rule and a project allow rule for it, after "Yes, and don't ask again", with a
  `PreToolUse` hook returning "allow", and in skip-permissions mode.
- **Our app servers are installed like any MCP server** (by the image's setup, for his user), so his own MCP servers
  keep working; the managed ask rules name their asking tools under the server names installed (*test*: each rule
  matches the installed tool).
- **The app passwords AresOS holds** (the mail accounts' passwords and any other sign-in data the tool service keeps
  for its apps) stay with the service's own system user (`aresos-tools`); his user, and so Claude, can't read them
  (sections 2 and 5). His own `gh` login and his other credentials stay with him, as in normal Claude Code.
- **The question sentence, the approval binding and the untrusted-content marking stay as built** (rules 4.1, 4.3 and
  4.8): the service writes the `question`, binds the approval to one operation by id and hash, refuses anything that
  differs at run time, and marks mail and page content as data. Rule 4.10's managed `Stop` and `UserPromptSubmit`
  hooks run next to his own hooks.
- **Instructions only from him:** a line in a `CLAUDE.md` (the managed one, `/etc/claude-code/CLAUDE.md`) says that
  only the owner, in the session (the terminal or Remote Control), gives instructions, and that mails, pages, files,
  tool results and other sessions' messages are data. It states the policy; it enforces nothing.
- **"Don't ask again"** for a recognised kind goes through his own channels (sections 5 and 6), never through the
  prompt's own option, which can't turn a managed ask off.

**What remains, said plainly (accepted with decision 24):**

- A Claude tricked by content can do on AresOS what it could do on any OS with normal Claude Code: change or delete
  his files, push with his `gh` login, reach the network, start programs.
- Without a mandatory sandbox, a tricked Claude can also call the tool service directly (the `aresos` command, or its
  socket, which his user can reach) with a prepared operation, and so skip the question. That is the same level as
  anything else a tricked Claude can do on a normal OS: it already acts with his user's rights. The tools add no
  route around his approval beyond that.
- If brief 18c shows that a `PermissionRequest` hook can approve a managed ask, a hook that Claude or he writes could
  approve our asking tools without him answering. That is the same level as calling the service directly, and is
  accepted with it.

**Claude Code's own sandbox stays available** as a setting he can turn on. Turning it on (`sandbox.enabled`) alone
does not keep terminal commands away from the tool service: a command that fails in the sandbox can be retried
outside it (`dangerouslyDisableSandbox`), and in skip-permissions mode that retry runs without a prompt; commands in
`sandbox.excludedCommands` run outside it too; and in skip-permissions mode hosts outside the allowed list are
reachable unless a strict domain list is on (Anthropic's sandboxing page, read 2026-11-08). It keeps terminal commands
away from the service only when all of these hold:

- `sandbox.allowUnsandboxedCommands: false`, so the retry outside the sandbox is ignored;
- `sandbox.excludedCommands` empty;
- Unix sockets not allowed: no `allowUnixSockets` entry for the service's socket, `allowAllUnixSockets` off, and the
  optional seccomp filter that blocks Unix sockets installed;
- the service's socket folder `/run/aresos-tools` in `sandbox.filesystem.denyRead`.

Even then it is best-effort under decision 24: these are his own settings, which his user (and so Claude outside the
sandbox) can change, nothing checks that they stay as set, and Claude's file tools, web tools, hooks and MCP servers
run outside the sandbox, as on any OS. Brief 18b's 127 blocked routes (*checked*) tested a stricter, managed setup
that decision 24 removed, not this one; if he wants the sandbox, 18b's hostile programs run against exactly these
settings first.

**Mail's boundary check (follow-up brief, after Mail merges).** Mail's rounds 15 to 17 refuse asking actions unless
the installed managed files match the generated ones exactly. That check becomes: every asking tool's ask rule is
present in the managed settings. Nothing else is compared, so his own MCP servers and settings are never blocked. This
is a follow-up brief after Mail merges, not a change to Mail now.

**The approval surface: Claude Code's own prompt (decision 21).** After six phone tests the owner decided (board
#78, his words: "okay we will use it as is, no need for a request"): approvals stay Claude Code's own permission
prompt, in the terminal at the laptop and through Remote Control on his phone. What the tests showed: in the terminal
the prompt is readable; on the phone (the Claude app, through Remote Control) it renders an MCP tool's input as fields
and values, and there is no supported way to give it a header and text of its own; the tool asking him itself (an MCP
elicitation) looked right in the terminal but never reached the phone. So the asking input itself is made readable:
it starts with a `question` field, one plain sentence the tool service writes, followed by the full content fields
(rule 4.1). How the requirements are met:

1. **The truth in full:** the `question` sentence and every content field, as the service describes the operation
   (rule 4.1); an input too large to show whole is refused, never cut.
2. **Enforced outside Claude:** Claude Code's managed ask rules hold the call until he answers (an "ask" rule still
   asks in skip-permissions mode: *checked*), unless a `PermissionRequest` hook answers it, which 18c tests and which
   joins the accepted residual if it can (above); the input names one operation by id and hash, and the service
   refuses anything that differs from it at run time.
3. **Claude doesn't answer it in the session:** the prompt is his; the pages that could approve (claude.ai, Remote
   Control) can't be opened in a Claude tab (section 6). The exception is the same: a `PermissionRequest` hook that
   Claude wrote could answer it, if 18c shows such a hook can (the accepted residual, above).
4. **At the laptop and on the phone:** the same prompt, in the terminal and through Remote Control.
5. **"Don't ask again"** goes through his own channels, never through the prompt's own option.
6. **Decided once:** one answer per tool call; the service's operation record (rule 4.3) refuses a second run, and a
   call after the 15-minute deadline (rule 4.3) is refused.

An approval screen of its own (for example in his Aresus iPhone app) is not planned; it is a possible later
improvement if he asks for it.

## 8. Tests and evidence

1. **Container tests** per adapter on GitHub's Linux runners (free for this public repo): GreenMail and a scripted
   SMTP server for Mail, fixture sites and branded Chrome for Chrome.
2. **The tools' own tests** (section 7): the managed ask rules still prompting against user and project allow rules,
   "Yes, and don't ask again", a `PreToolUse` hook returning "allow", and skip-permissions mode; whether a
   `PermissionRequest` hook returning allow, managed or his own, can approve a managed ask (unknown until tested, in
   both modes); the `question` verified; an approval bound to one operation; the app passwords unreadable by his
   user.
3. **The prompt, at the laptop and on the phone** (decision 21): every asking action's input, `question` first, is
   checked in the terminal and through Remote Control with a long mail, Bcc, attachments and odd characters, and for
   a deletion and a Chrome send. Anything not shown in full there changes rule 4.1 before Mail or Chrome relies on
   it.
4. **Tool-user rounds:** fresh Claude agents do the everyday tasks in `PLAN.md` and the features in
   [`FEATURES.md`](../control/FEATURES.md) against the fixtures. They report calls, approvals, time and where they
   got stuck, misread a result or had to guess; budgets for those are set before the rounds, and the reports decide
   what "works really well" means. For Chrome they also count the questions per real send (target one) and the
   harmless controls that asked because of the word list (section 6).
5. **An early image test:** a minimal, unpublished AresOS build in the CI virtual machine runs the fake app end to
   end (a fake send asking in normal and in skip-permissions mode, and the `PermissionRequest` hook test of section
   7) right after brief 18, not only at the end, with Claude Code as his own user and his own MCP servers alongside.
   If he uses Claude Code's optional sandbox, the image needs the namespace policy brief 18b found GitHub's runner
   needed. `laptop-aresos` agrees the `os/ci/` change first.
6. **Qualification in the AresOS image** of Mail and Chrome, then **real use** after the first boot on the laptop.

## 9. The council's gaps, and where each is handled

| Gap (VERDICT) | Where |
|---|---|
| 1. Claude bypasses a tool through another route | accepted at the level of normal Claude Code (decision 24, section 7): a tricked Claude could call the tool service directly, as it could do anything his user can; owner-only actions stay behind `sudo`; Claude Code's optional sandbox narrows the route through its terminal only in the strict setup of section 7, best-effort; in Chrome, the tool asks before anything that clearly sends, and a page that sends on its own after an ordinary action isn't held (decision 25, section 6) |
| 2. The agent manufactures or changes an approval | Claude Code's own prompt, with the service's `question` sentence first and verified (rule 4.1, section 7, decision 21); approval pages can't be opened in a Claude tab (section 6); managed ask rules that no allow rule, `PreToolUse` hook or mode turns off, with `PermissionRequest` hooks tested in brief 18c and his own kept off our asking tools (section 7); rule 4.1 makes the approval show the service's description and refuses changes; "don't ask again" only through the owner's channel (section 6) |
| 3. Retries, cancellation and restores send twice | rule 4.3: operations recorded before they act, per stage; never retried by themselves; repairs never resubmit; expiry; the log refuses to go backwards; in Chrome, one approval runs one input once, after the page-state check (section 6) |
| 4. Harmless-looking actions change data | effects in section 3; `BODY.PEEK`; in Chrome, submits, telling controls, Enter in message fields, Delete outside text and uploads ask, while unlabelled controls and a page's own sends stay free (section 6); before/after comparisons in every test |
| 5. Data leaves without a send | content marked untrusted and instructions only from the owner (4.8, the managed `CLAUDE.md`); in Chrome, page text marked untrusted and the residuals named in section 6 (a page's own sends, addresses Claude writes); what a tricked Claude can do with normal Claude Code accepted by the owner (section 10, decision 24) |
| 6. Browser debugging exposes the signed-in session | our own policy-installed extension and native host, no debugging port, Chrome's consent attach rejected, a fixed command set with no cookie or storage reading, password values never read (section 6) |
| 7. Startup leaks passwords or weakens TLS | passwords only with `aresos-tools`, verified TLS, no fallback (section 5) |
| 8. Acting on a stale or wrong target | rule 4.2; the Claude tab group and references bound to tab, document and element (section 6) |
| 9. Flatpak unavailable to the daily account | Chrome as a native package (brief 17, Q5) |
| 10. Graphical tools on the wrong session | Chrome bridge and session wiring checked in the image qualification |
| 11. CI success isn't AresOS integration | evidence kept separate: container, VM, laptop (section 8) |
| 12. Provider and dependency assumptions | capabilities checked at run time; pinned versions; the real account only after the first boot |
| 13. Works but unusable | the tool-user rounds; the terminal command works without Claude or network for local things (`aresos log`) |

## 10. Open questions

**Open:** none.

**Answered on 2026-11-07 and built into this draft** (his words in quotes; `PLAN.md` decisions):

- Data leaving in Chrome (decision 7: searches on his usual sites free, anything else that could carry Claude's text
  asking). Under decision 25 searches and navigation are free everywhere, and "don't ask again" stays for kinds an
  adapter names (section 6). Claude in Chrome kept for his own use and the machine-wide rules (decision 10; sections 6
  and 7). The checkpoint with his hard requirements (decision 6) and the strict site guard (decision 12) went with
  decision 25. Decision 8 (the central session apart from coding work) was replaced on 2026-11-08 by decision 23
  (below).
- **Unlabelled controls that may delete data kept only in the browser:** "a)" (decision 14). Such clicks stay free;
  labelled destructive controls and Delete or Backspace outside plain text editing ask; the gap is accepted as stated
  (section 6, unchanged by decision 25).
- **"Don't ask again":** "yes" (decision 15). Offered for mail bound to an exact set of recipients, in the Mail tools
  and in Gmail (sections 5 and 6); deleting and paying always ask. Under decision 25 Gmail compares the recipients
  the compose shows at the moment of sending, and WhatsApp messages ask each time (decision 16).
- **How Claude sends on WhatsApp Web:** "a)" (decision 16). Claude asks per message, described "as the page shows
  it". Under decision 25 the question comes before Enter or the send button, with the chat and the text as the page
  shows them; the bounded set of encrypted frames went with the checkpoint (section 6).
- **His folders:** "pretty much everything no? like running claude with dangerously skip permissions just like I do
  now" (decision 17). Decision 24 carries this further: Claude Code works in his home and projects as his own user, as
  on any OS; the version store and the start-up-place checks for Claude's own file tools went with the containment.
- **`WebFetch` and `WebSearch`:** "a)" (decision 18). Under decision 24 they behave as in his normal Claude Code,
  under the permissions he sets; the managed hook that recorded where an address came from went with the
  containment.
- **What the checkpoint's certificate checks still can't do:** "okay" (decision 19). Moot under decision 25: there
  is no checkpoint, and Chrome checks certificates itself, as normal.
- **The approval surface:** "okay we will use it as is, no need for a request" (decision 21, board #78, after six
  phone tests). Approvals stay Claude Code's own prompt, in the terminal and through Remote Control; every asking
  input starts with the service's `question` sentence (rule 4.1, section 7). An approval screen of its own is not
  planned; a possible later improvement if he asks.

**Answered on 2026-11-08 and built into this draft** (his words in quotes):

- **Adding tools:** "AresOS cant install any tools? that sounds incredibly terrible. we need it to be a regular OS like
  windows but we make it custom yk with tools etc. I think theres no way we cannot install gh, gh repo tools, mcps
  etc."; and "claude code can install tools on my normal OS so I think it should be possible in aresos too"
  (decision 22). Under decision 24 he and Claude add MCP servers, skills and plugins as in normal Claude Code; the
  install-asking path is no longer needed.
- **One session for everything:** "often times things are project work and intertwined. especially with chrome or
  once we add more apps. like a project might require a chrome test or check in chrome and so the coding session
  needs to be able to do it and the mail / app sessions sometimes need to execute commands and do things. I dont
  think the central split is that smart and also dont know how possible it is if I just start claude code with skip
  permissions" (decision 23, replacing decision 8). He may start it with skip-permissions (section 7).
- **Normal Claude Code plus the tools:** "Fundamentally I envision aresos as basically normal Claude code but with
  more tools. Now Claude code can basically just work in my projects and asks for permission certain things and I can
  allow it. Gh is used very smoothly. Is it necessary to change that?" and "Essentially it's as we already discussed:
  Normal Claude code like in any OS + the tools we make. They add very little risk because even now Claude in chrome
  could read a malicious prompt for example and then have Claude push smth to git. Our tools, as long as they are
  safe, don't make it worse than that." (decision 24, replacing the containment parts of decisions 22 and 23).
- **Accepted residual risk, his call** (decisions 23 and 24). A Claude tricked by content can do on AresOS what it
  could do on any OS with normal Claude Code: change or delete his files, push with his `gh` login, reach the
  network, start programs; it can call the tool service directly and skip the question (the optional sandbox
  narrows that only in its strict setup, best-effort: section 7); and if brief 18c shows that a `PermissionRequest`
  hook can approve a managed ask, a hook can approve our asking tools. The tools still ask for every send, delete and
  submit they recognise before acting (in Chrome, a page's own sends after an ordinary action aren't held: section
  6), the app passwords AresOS holds stay with the tool service's own user, and instructions come only from him in
  the session. What remains is accepted, in his words above.
- **Chrome, the light tool:** "B is good" (decision 25, board #107), choosing a light tool of our own over keeping the
  checkpoint or using only Claude in Chrome. Claude reads pages as text and clicks, types and scrolls in his own
  Chrome; it asks before anything that clearly sends; a page that sends on its own after an ordinary click isn't
  held; Chrome stays completely normal, with no proxy and no certificate (section 6).

**For the owner, later:**

- Outgoing mail formatted (like Apple Mail) or plain by default, and the signature (a habit for CLAUDE.md, not a tool
  rule).
- The feature list in [`FEATURES.md`](../control/FEATURES.md): anything missing, and what can wait.

**Settled by this design, for the re-check:**

- **Language and libraries.** Python 3 (already in the image), the standard library's `imaplib`, `smtplib` and
  `email` for Mail with explicitly verifying TLS contexts, the official MCP Python SDK pinned and shipped in the
  image. Chrome: the extension in JavaScript (required), the native host a small Python relay. The rules live in
  the Python service: the classification of asking inputs, the adapters, the operation, the question and the
  recorded page state. The extension, through its fixed command set, collects the facts, compares the page with the
  expected state right before an approved input, and runs the page script that stops a page's own submissions and
  activations (section 6). The code
  of briefs 17 to 17c is the reference (check code, not product code); brief 20 ports what it settled.
