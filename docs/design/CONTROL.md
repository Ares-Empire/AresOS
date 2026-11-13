# The control layer: design

**Status:** draft 32, 2026-11-13. Draft 16 with the owner's answers of 2026-11-07 built in (`PLAN.md` decisions 14 to
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
is wanted. Draft 32 (2026-11-13, no re-check yet) rewrites section 6 for what brief 20 built, for the owner's
change to decision 25 on 2026-11-11 (Claude works in his open tabs) and for the capability design of briefs 28
and 28b (reading, references, navigation, batched steps and a smaller tool list). Covers the shared base, Mail
and Chrome. The frontier
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
showed them; points marked *brief 20*, *brief 28* or *brief 28b* must be shown by that build's own tests before
anything relies on them.

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
   the browser session, tab, document and element, and to what the element showed when Claude last saw it
   (section 6).
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
   Chrome; `chrome_library` only lists them (section 6). Everything else about files is normal Claude Code
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

## 6. Chrome (decision 25: the light tool, in his own tabs too)

The owner chose the light tool (decision 25, board #107, his words: "B is good"). Claude works in his own, normal
Chrome through a small tool of our own: it reads pages as compact text, moves between tabs, clicks, types and scrolls,
and it asks before anything that clearly sends. Chrome stays completely normal, with no proxy and no certificate. On
2026-11-11 he widened the tool and set its direction:

- **His open tabs** (decision 25 as changed): "Claude can make group tabs but he can also work in my open tabs
  basically as if I was working in them … Claude sees everything once I need it or ask a question or smth, then
  that's automatically given. Eg 2 tabs open, one 'Car', the other 'Uni website' and I ask Claude to check my lectures
  he goes to uni website. Although the permission interpretation on this needs to be good." How that is read is under
  "Which tabs Claude works in".
- **Capability before more hardening:** "I don't just wanna rebuild Claude in Chrome. I wanna make a better tool for
  AresOS that's more efficient with readings, navigation, free tab navigation etc." What "more efficient" means is
  written as budgets and tested ("Efficiency, as a tested property").
- **The bar** (decision 24 as clarified): safe the way a good MCP or CLI is, not "nothing could ever go wrong". Every
  send, delete, payment and unsubscribe the tool recognises asks, with the exact content shown and bound. Claude
  can't answer or replay the question. The reader never reads a password field. Page content is marked untrusted. A
  hostile page that makes a step look ordinary is a known limit: it is written down under "Known limits" and fixed
  where the fix is reasonable or the harm is real. A page that sends something on its own after an ordinary click
  isn't held.

**Where it stands.** Brief 20 (PR #27) built the tool: the extension, the page reader, the page script that stops a
page's own submissions, the questions, the adapters and the qualification record. Its reports are in
`reviews/20-chrome/`. Briefs 28 and 28b build this section's capability design on top of it: 28 the reading, the
references, navigation, batched steps and the smaller tool list; 28b his open tabs. Points marked *checked* name the
check that showed them. Points marked *brief 20*, *brief 28* or *brief 28b* must be shown by that build's own tests
before anything relies on them. Until brief 28 merges, the tools carry brief 20's names and results
(`reviews/20-chrome/TOOL-DESCRIPTIONS.md`); "Actions" maps the old names to the new ones.

**History.** Briefs 17b to 17e and design drafts 9 to 25 built and checked a checkpoint outside Chrome that held
every send from a guarded site (an intercepting proxy, the site guard, attribution of each request, certificate
checks, the conditions under PLAN S2e). Decision 25 replaced all of it. Those reports stay as history
([17b](../../reviews/17b-chrome-holds/REPORT.md), PR #4; [17c](../../reviews/17c-chrome-pages/REPORT.md), PR #7;
[17d](../../reviews/17d-chrome-floor/REPORT.md), PR #8; [17e](../../reviews/17e-chrome-checkpoint/REPORT.md),
PR #10). What this section still uses from briefs 17 to 17c is marked *checked*, with the brief
([17](../../reviews/17-chrome-check/REPORT.md), PR #3: branded Chrome stable 157 on GitHub's Linux machines, fixture
sites and synthetic profiles).

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
  pinned toolbar button (**ON** on a tab Claude controls, **POP** where a popup of that tab is controlled, and with
  brief 28b **READ** on a tab of his that Claude looked at), and a **Stop** button in its popup that ends control
  at once (*checked* with a real click, 17c). Stopping never sends anything, drops every prepared operation and
  gives his tabs back.
- **The tool service may open outgoing connections.** Its unit allows `AF_UNIX AF_INET AF_INET6`: Mail's IMAP and
  SMTP need the network, and so does the daily fetch of Chrome's qualification record ("Tests"). It still listens
  only on its Unix sockets (section 2), and every other line of its sandbox stays. A test pins the unit's lines
  exactly (*brief 20*); brief 18c checks it in the image.

### What the extension can and can't do

- **No debugging port, nothing listening on the network.** The extension's control channel is the native messaging
  port Chrome opens to our host, and the host talks only to the tool service. The extension has no
  `externally_connectable` entry and takes no commands from pages, frames or other extensions; a page's messages are
  never commands.
- **A fixed set of commands.** The service sends named commands (list the tabs, read a page, say whether it has
  gone quiet, click an element, type, press a key, scroll, navigate, put a file into a file field, answer a dialog,
  run a prepared operation), and the extension runs only those. It never passes a DevTools method through from the
  service. The DevTools methods it uses are a fixed list in the extension (*brief 20*): dispatching input,
  navigating, answering a dialog, and installing the extension's own scripts in a tab Claude controls before the
  page's scripts run. Two of them can run script (`Runtime.evaluate`, `Runtime.callFunctionOn`); they run only those
  fixed scripts of the extension, never text from the service, from Claude or from a page. Methods that return field
  values (whole-page DOM snapshots, the DOM tree with attributes, the accessibility tree), read cookies or storage,
  or intercept network traffic are not on the list (*brief 20*: each refused). Reading happens in the extension's
  own content script (below), and a file reaches a file field through that script too. The extension has no
  `cookies` permission. Navigation is limited to web addresses (below), so a `javascript:` address can't be used to
  run script either.
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
    plain text doesn't make it readable;
  - a field whose name, id, label, placeholder or `autocomplete` holds a credential word (password, PIN, OTP, TAN,
    a verification, security or recovery code, a card security code, a secret, a token, a private key, a recovery
    phrase, in English and German; the list is part of the definitions). This rule wins everywhere, whatever the
    element or its type: a sign-in code in a plain text field, and a long field labelled "Password", are handled
    like a password (*brief 28*).

  The check runs again right before every value read, not once per page, so a field whose type changes after it was
  first seen is judged as it is at that moment, in every frame and shadow root.

  Such a field appears in the view as `password "Label" (not read)`. The binding (below) uses the same exclusion: it
  records such a field's presence and identity, never its value or whether it is empty. Claude never types a
  password: signing in is his, and a sign-in page is handed back to him.

  **Where the reader can't know a field's history, it leaves the value out** (*brief 28*). "Seen before" only
  helps in a document the reader has watched since before the page's scripts ran: Claude's own tabs, and a taken
  tab after its reload. In any other document a password he made visible earlier is by now an ordinary text
  field, and nothing in the page says what it was. That is the case in a taken tab before its reload, and in every
  tab of his that Claude looks at in place (*brief 28b*). A password field is always a single-line input, so the
  rule is as narrow as that. In such a document:
  - a single-line input that can hold typed text (text, phone, number, and any type the tool doesn't know) shows
    no value, only whether it is filled: `textbox "Label" (filled, not read)`;
  - a multi-line text field and an editable area are read, so Claude can proofread a draft he is writing in a tab
    of his and see what a form's long fields hold;
  - ticks, radio choices, chosen options, ranges, colours, dates and times, and email, address and search fields
    keep their values: none of them can have been a password field;
  - the name rule above wins over all of this, and so does masking: a field that is named like a credential, or
    masked right now, is never read.

  The same holds, inside a watched document, for a single-line field that already held text when the reader first
  met its shadow root, because a component can attach a root without the reader noticing at once. Claude doesn't
  type into a field whose value it can't read. A password or sign-in code reaching Claude is never an accepted
  limit (owner, 2026-11-11). What this rule costs and what it leaves are under "Known limits".
- **The service checks its peer.** `chrome.sock` accepts only his user (Chrome, and so the host, run as him) and one
  host per running Chrome, from the pinned profile ("Which tabs Claude works in", *brief 28b*). Under decision 24
  another program of his user could imitate or disturb the host, as it could any program of his (for example by
  registering a user-level host of the same name, which Chrome prefers: *checked*, 17); that is the accepted level of
  section 7, not a route the tool adds.

### Where Claude may go

- **Only web addresses.** `chrome_open` and `chrome_go` accept `https:` and `http:` addresses (`localhost`
  included) and `about:blank` for an empty tab, nothing else: no `javascript:`, `data:`, `blob:`, `file:`,
  `filesystem:`, `view-source:`, `chrome:`, `chrome-extension:`, `devtools:`, `intent:`, `mailto:`, `tel:` or other
  app schemes. Links on a page follow the same list: a link to another scheme is refused before the click, except a
  `javascript:` link, which is the page's own script and is classified like a button by its label (below).
- **Pages that could approve Claude's actions or change its limits are never read or acted on:** claude.ai with its
  Remote Control pages, the Anthropic console, Aresus, and Chrome's own settings, password and extension pages. The
  Anthropic sites are a fixed list in the tool. Chrome's own pages are out because they aren't web addresses. Aresus
  and any site he adds himself are in an owner-only setting on his laptop
  (`/etc/aresos/control/chrome-excluded-sites.json`, root-owned and changed with `sudo`): his never-list.
  **It ships empty, and nothing in this public repo names a host of his.** His own hosts, his dashboard first, are
  put into it during the live setup with him, before Claude's first session in his Chrome. No gate holds the tool
  back until then: an empty list is a valid setting, and a gate would need the host's name in the image or the
  repo. Until the host is in the list, his dashboard is an ordinary site to the tool, so that step comes first in
  the live setup. `chrome_sites` doesn't manage this list; it manages his read-only sites and his "don't ask
  again" entries. This keeps the approval his alone (section 7, requirement 3). The
  check runs before every read and every action, on the tab's top document and on the frame that holds the target,
  so it covers every way of getting there:
  - **his tabs:** `chrome_read` never reads such a page in place, and `chrome_take` refuses a tab showing one;
  - **redirects, history and popups:** a Claude tab or a popup that reaches such a page, by a redirect, back or
    forward, or a page opening it, is refused for reading and acting and handed back to him out of the group; the
    extension's session rules (`declarativeNetRequest`, limited to Claude's tabs) also refuse loading those sites as
    a page or a frame there;
  - **frames:** a frame from such a site inside another page is left out of the view, and acting on an element in it
    is refused.

### Which tabs Claude works in

Claude works in two kinds of tabs: its own, and his. Whose a tab is follows from who opened it, not from the group
it sits in. A tab is Claude's when Claude opened it, or when a tab under Claude's control did. Every other tab is
his, and it stays his while Claude has taken it.

**Claude's own tabs** are in a tab group labelled **Claude**. `chrome_open` puts a new tab there, in the same profile,
so his sign-ins work. A tab of his that Claude has taken gets a Claude group of its own, where it stands (below).
The service knows each group by Chrome's group id, not by its label. Every call names its tab:
there is no "current tab" and no switching step, so Claude moves between tabs freely. `chrome_show` brings a tab to
the front when he should look at it or sign in there.

**His open tabs (decision 25 as changed).** *brief 28b*

- **What Claude sees.** `chrome_tabs` lists every tab of every normal window of his Chrome profile in one result:
  the title, the address, the window, and whether the tab is Claude's, his, or his and taken. It also says which
  tab is in front, pinned, playing sound or asleep. Addresses are in the public form ("Reading a page"): the site
  and the path, never what follows `?` or `#`, because that can hold sign-in tokens. Titles are page text, so they
  are untrusted content (rule 4.8).
  - **Incognito windows are never listed, read or taken.** The extension's manifest says `"incognito":
    "not_allowed"`. Incognito is his way of saying "not for the record".
  - **Other Chrome profiles** aren't listed. Claude sees one profile, and it is pinned: the service remembers the
    first profile whose extension connected and refuses any other, also after a reconnect, until he switches it
    with an owner-only command. Brief 20 accepts whichever extension connects (read in its `bridge.py`), so without
    the pin a
    second profile could quietly take the first one's place. [`FEATURES.md`](../control/FEATURES.md) says so.
  - **Never readable:** the pages of "Where Claude may go" (the fixed list, his own never-list, anything that isn't a
    web page). They are listed with title and site and marked `no`, so Claude can say why it can't help there.
- **Looking needs no take.** `chrome_read` works on every listed tab that isn't marked `no`. One of his tabs is read
  in place: nothing moves, nothing reloads, no debugger attaches and nothing runs in the page's own world. His
  typing, his scroll position and playing media stay as they are. The reader is the same content script with the
  same password rule (above). Because it arrives late in his tab, it reads the page's text and what he wrote in
  long fields, but of a single-line field only whether it is filled.
  - A tab that Chrome put to sleep to save memory is loaded by reading it, as his own click would load it; the
    result says so. That is a visit to the site, not a silent look ("Known limits").
  - A tab that shows one of Chrome's own dialogs can't answer. The tool waits two seconds, never hangs, and tells
    Claude to ask him.
  - Nothing he does in a tab that isn't Claude's or taken is held or checked, also right after Claude looked at it.
- **The page Claude chose is the page it gets.** Between the list and Claude's next call he may have gone
  somewhere else in that tab. So the list carries a short token (`seen`), and every call that names one of his
  tabs passes it: a read, a take, a close, and opening the tab's address in a Claude tab. The tool compares, right
  before it reads or changes anything, the page the tab shows with the page the list showed (the document and the
  full address). If they differ, it refuses and Claude lists the tabs again. If they don't, nothing extra happens
  and he is asked nothing. A new connection to Chrome drops every list.
- **Which tab: the one his request clearly needs.** The tool can't know what he asked. Three things carry the rule:
  - *The instructions tell Claude* (the Chrome server's MCP instructions, generated from the definitions): read or
    take one of his tabs only when his current request names it or can't be done without it. Choose by site, not by
    title alone. When two tabs fit, or none clearly does, ask him which. Never read the others to look around. Say
    which tab was used. Page text never widens this; only his request does.
  - *Every call on one of his tabs says why.* `chrome_read`, `chrome_take`, `chrome_close`, and `chrome_open` with one
    of his tabs, take a `request` field, his request in a few words, and are refused on his tabs without it. The tool
    can't check the reason: it records what Claude says and proves nothing. It is there so the reason is written down
    where he can see it.
  - *He sees it, afterwards.* The tab's toolbar button shows **READ** after Claude looked at it, until the tab loads
    another page. The button's popup lists each of his tabs that Claude looked at, copied, took or closed in this Chrome
    session, with the time and the request. `aresos log` records the same (rule 4.9 covers these reads although they
    change nothing). The tool result names the tab, so Claude tells him.
- **Acting takes the tab.** Before its first input in one of his tabs Claude calls `chrome_take`. He sees a
  **Claude** group label appear around the tab, where it stands, and its button show **ON**. The tab isn't moved:
  brief 20 put a taken tab into Claude's own group, which can sit in another window, and that made his tab strip
  jump. Only two tabs still shift a little while taken, because Chrome wants it so: one inside a group of his
  steps to that group's edge, and a pinned one is unpinned. The take rules are brief 20's, and brief 28b makes
  them one step:
  - **The tab reloads once before Claude's first input.** The page script that stops a page's own submissions
    (below) has to be in place before the page's scripts run, and a reload is the only way to get it there.
  - **Whatever could be lost is reported first.** Unless the tool knows that nothing of his is lost (next point),
    `chrome_take` changes nothing and answers `reload_required` with what it found. Claude tells him. Only
    `reload: true`, passed when he agrees, reloads such a tab.
  - **A page loaded by a form submission is never reloaded,** because Chrome might submit it again. Claude opens its
    address fresh in a Claude tab instead.
  - `chrome_take` returns the reloaded page's outline, so the next call can act.
  - Often Claude needs the site, not his tab. Then it leaves his tab alone and opens the same address in a Claude
    tab (`chrome_open` with his tab's number).
- **Before the tool reloads or closes one of his tabs, it must know that nothing of his is lost.** Unknown is not clean.
  Brief 20 looked for a field that differs from its default, an editor, and playing media (read in its `reloadState`).
  That misses typing on the many pages that copy it into the field's default, work kept in a canvas, and a form on its
  way to the server. With brief 28b a tab is known clean only when all of this holds:
  - every frame answered, no dialog is open, and no load or form submission is under way;
  - nothing plays;
  - there is no editable area, no chosen file, no password field, and no field that differs from its default;
  - no text field holds text (a search box aside), unless he has never clicked or typed in the page since it
    loaded and it was opened fresh, not restored or reached by Back;
  - there is no canvas on a page he has used.

  In every other case the tab is left as it is and the result says what the tool found, with the labels of
  fields and never their values. The check runs in his tab without a debugger, as the last thing before the
  reload or the close. If Chrome itself asks "Leave site?", that question is his and the tool never answers it.
- **Giving it back.** `chrome_release`, the **Give back** button next to the tab in the popup, dragging the tab out
  of its Claude group, or **Stop** (which gives back everything) each end Claude's control of the tab, drop its prepared
  operations and put it back where it was: its window, its place, his own group, pinned if it was pinned. If his
  group was removed by Chrome because the taken tab was its only one, a group with the same name and colour is
  made for it.
- **Closing** (owner, 2026-11-13, board #201: "Yes, when I ask"). `chrome_close` closes Claude's own tabs. It
  closes one of his only when he asked for it, the call names his request, and the tab is known clean (above). A
  tab where work could be lost, or where the tool can't tell, stays open: the result lists it with the reason,
  no input overrides that, and he closes it himself. The result lists what was closed, so Claude tells him. A
  taken tab is given back, not closed.
- **More care for some tabs.** On the sites he marks read-only (his bank), Claude looks, and after a take only
  scrolls and follows links. Sites on his never-list aren't read at all. A password field is never read, and Claude
  never types a password: signing in is his.
- **His own use of a taken tab** is his: "His own input in a Claude tab", below.
- **Claude's tabs stay in the background.** A new Claude tab opens behind the tab he is looking at, and Claude's
  input doesn't bring its tab to the front. Brief 20 selects the tab before every click, key, fill and scroll,
  because input didn't land otherwise; brief 28b measures whether it lands in a background tab, and if it doesn't,
  the question of a window of Claude's own goes to him.

His decisions behind this (brief 28b lists them with his words): Claude looks at the tab his request needs without
a separate question, and the take rules stay (2026-11-11); Claude closes a tab of his when he asks (2026-11-13,
"Yes, when I ask"). Possible later, after his live test, and not built now: a list of sites where Claude asks him
before it looks; working in a tab with unsaved typing without a reload; reading what single-line fields hold in
his own tabs.

**Until brief 28b merges** the tool does what brief 20 built: Claude reads and acts only inside the group. Looking at
one of his tabs needs `chrome_take` first, which moves the tab and keeps its page; the first input then reloads it,
and unsaved typing or playing media stops that reload until `chrome_take` is called with `reload: true`. The check
before that reload is still brief 20's, with the gaps named above, so brief 28 alone doesn't go onto his laptop.
Brief 28 already stops two things brief 20 allowed: closing a taken tab, and navigating one before its reload
without that check.

**Popups.** A popup or new tab that a Claude tab opens belongs to Claude while its opener does, and follows the same
rule: one reload before the first input. A new tab joins the group. A popup window stays where it is: the opener's
toolbar button shows **POP**, and the popup's list has a **Stop** for each such popup, which ends control without
closing or reloading it. Nothing of ours ever opens a window or takes the focus (*brief 20*).

### Reading a page

*brief 28.* Reading is text, built by the extension's own content script (above): never a screenshot, never
Chrome's accessibility tree. `chrome_read` gives an **outline** first and the detail on request. Page text is
untrusted content (rule 4.8): a page can never instruct Claude.

**The outline** is one line per element, indented by depth:

```
main
  h1 "Week 46"
  p "Rooms change in " [link "week 47" kqt4] "."
  button "Next week" kqt5
  form "Filter" → GET uni.example/timetable kqt7
    combobox "Semester" = "Winter 2026" kqt8
    checkbox "Only my courses" checked kqt9
    button "Apply" kqt10
  table "Timetable" kqt6
    … 12 rows, 5 columns (1,840 characters)
  list kqt11
    link "Lecture 1: Graphs" kqt12
    … 47 more (2,900 characters) kqt17
```

- A line holds the role, the name in quotes, a field's value after `=`, the states that are set (checked, selected,
  disabled, required, invalid, expanded, current), where a link or a form leads when that isn't obvious, and a
  reference.
- Text appears once, on the element that owns it: a label's text is on its field, not beside it as well. Wrappers
  without a role or name get no line. A link or control inside a sentence stands in square brackets where it
  stands in the text, so the sentence keeps its order.
- Long content is folded. The fold says how much it hides, in characters of what reading it returns, and its
  reference reads exactly that. A name, a text or a value longer than 200 characters is cut. Of more than 8
  neighbours of the same kind (paragraphs, list items, rows, cards) the first 5 are shown. A table shows its size.
  A list of more than 12 options shows the chosen one and the count. A form shows its first 40 fields.
- Left out: boxes and coordinates (Claude acts by reference; the tool scrolls the element into view, inside the same
  hold as the input itself, and checks that the click lands on the element), elements behind an open dialog, hidden
  elements, and frames of the fixed list. Frames from other sites and shadow DOM, closed roots too, are part of the
  outline.
- A password field is the line `password "Label" (not read)`. A single-line field whose history the reader doesn't
  know is `textbox "Label" (filled, not read)` or `textbox "Label" (empty)`.
- A page can't forge a line. The role is one word from a fixed list: a page's own `role` string is used only when
  it is on that list, and otherwise the element's tag decides. Everything a page wrote (names, texts, values,
  option labels, table cells, titles, the path of a `find` hit) appears only inside quotes, with quotes, line
  breaks, control and direction-changing characters escaped (rule 4.1's escaping). That holds in the outline, in
  every detail read, in a change report and in the line a refusal shows. A refusal's own message never holds page
  text. A reference the service didn't issue doesn't work.

**Detail on request.** With `ref`, `chrome_read` returns that part of the page unfolded, in the shortest form that
fits its kind:

- a table as one line per row, the cells separated by `|`;
- a list as its items;
- a form as every field with its label, value, options, required mark and error text, its hidden fields by name,
  and where it sends;
- a text in full;
- a single link or control with everything known about it (its address in the public form, the title).

**All of it.** With `full`, `chrome_read` returns the page, or with `ref` one part of it, with nothing folded and
nothing cut, paged by the budget below. So reading a long page to its end is two or three calls, not one call per
fold.

**Finding.** With `find`, and `role` to narrow it, `chrome_read` returns the elements whose name, label, value or
text contains the words, folded parts and frames included: up to 20 per page, each as its outline line with a
reference and the path to it (`main › list "Week 46"`), and for a hit inside a long text 60 characters either side.
The match is literal and ignores case.

**Several tabs at once.** `tabs` takes up to five tabs and returns each one's outline, so comparing pages is one
call. A tab that can't be read gets its reason, and the others are still returned.

**Waiting.** With `until` (a text that must appear, or one that must be gone), the read waits up to 6 seconds and
says whether it happened. The tool waits without reading the page over and over: it asks the extension for one
small token that changes whenever the page's text, a field's content, a frame or the address changes, and reads
again only then. The same token tells when a page has gone quiet, and it is what a paging cursor is bound to.

**Size.** Every read has a budget, `max`, in characters: 6,000 unless Claude says otherwise, 3,000 per tab when
several are read, never more than 40,000. What doesn't fit is paged with a cursor bound to the page's state; a
cursor from an earlier state fails with "page changed, read again". A page of the answer ends at a line end; a
single line that is longer than the budget (a long text read in full) is continued inside the line, so paging
always advances. The tool measures the answer as it is sent, where a character outside ASCII takes six bytes, and
ends a page earlier when the whole wouldn't fit the base's bound of 48 KiB. The header names the tab, the address,
the title, the scroll position, and how many characters the whole answer has.

**Addresses: one public form.** *brief 28.* An address can carry a sign-in: a code after `?`, a token after `#`,
a user name and password in front of the site, or a reset link whose path is the key. So one function in the
service writes every address that leaves it, and it writes:

- the site, with `http://` in front when the page isn't `https`, and never a user name or password;
- the path, except what follows a sign-in word (`/reset/…`, `/verify/…`) and any part that looks like a random
  value (`…` stands in for both);
- `?…` or `#…` when there is a query or a fragment, never a name or value from them.

Every output uses this form and no other: the tab list, a page's address in a read, link and form targets, the
library's bookmarks and history, every tool result and error, the notices, the question and description of a
prepared operation, the operation's status and the log. The full address stays inside the service and the
extension, where navigation and the binding need it: an approved input is still compared with the full
destination. Claude uses an address it can't see by reference: it opens a link, a library entry or the address of
one of his tabs with `chrome_open`.

**References.** A reference is a short name the service issues: three letters and a number, such as `kqt5`. No
reference is ever issued for two things. The letters name one run of the service and change every time it starts.
The number comes from one counter for all tabs, only counts up, and isn't reset when Chrome restarts or when old
entries are dropped. So a reference from another tab, from before a restart of Chrome or of the service, or one
the service has dropped, never comes to mean another element: it is unknown, and refused. An element keeps its
reference for as long as it lives, across reads and results, so Claude can act on what it read earlier. For every
reference the service remembers the connection to Chrome, the tab, the frame and document, the reader that issued
the element's id, the element, and the line it last showed Claude. An action on a reference is refused with
`stale_reference` when:

- the reference is unknown, was issued for another tab, or was issued before Chrome or the service restarted;
- the document or the element is gone, or the page's reader was installed anew since;
- the element no longer means what Claude last saw. The service keeps a fingerprint per reference: the role, the
  name, the label and the title, where a link leads (the full address, also when the line doesn't show it), a
  list's options, whether the element is ticked, selected or expanded, and the whole value, also where the outline
  showed it cut. So Claude never overwrites something it hasn't seen and never follows a link that was swapped
  under the same name.

The refusal shows the element's line as it is now. When he switches or opens tabs, nothing is redirected.

Brief 20 also bound a reference to the whole view: after any change anywhere on the page every reference was
stale, and each action had to send back everything the element had shown, its place on the screen included
(*checked*, brief 20). The fingerprint keeps that comparison for the element itself, without its place. What goes
is the rest of the page: a free step now runs although something next to its element changed since Claude read it
("Known limits"). What stays is the check that a click lands on that element, the classification on fresh facts
right before the input, and for an asking step the binding of everything the question names.

**Text only first** (owner, 2026-11-13, board #202: "Text only first"). The first version reads pages as text and
takes no pictures. A picture costs more than a whole outline, shows whatever is on the screen (a password he made
visible included), and can't leave a value out. Pages the outline can't represent (a canvas text editor, a map)
need a site adapter or are listed as not supported yet in [`FEATURES.md`](../control/FEATURES.md).

A picture of a page region stays a possible later package. It would be taken only on request, of one element
Claude names by reference, never of a whole window. It would have to refuse a region that holds or overlaps a
password field, a field named like a credential, or any field whose value the reader itself wouldn't return, so
in his own tabs it could show no single-line field. And it would have to honour the fixed list and his
never-list frame by frame, because a picture of a tab shows every frame in it, and get its pixels without
bringing his tab to the front or attaching to it.

### Going to pages and acting

*brief 28.* One call does a whole step of work and returns what Claude needs to go on, so a second read is rarely
needed.

- **Going.** `chrome_open` opens a web address in a new Claude tab: an address Claude gives, the link or library entry
  behind a reference, or the address one of his tabs showed in the list. `chrome_go` moves a Claude tab: to an address,
  back, forward or reload. Both wait until the page has loaded and gone quiet, or until a text Claude names appears, for
  8 seconds unless Claude says otherwise and never more than 15. "Loaded" also covers a navigation that stays inside the
  same document (a fragment, or a step in a single-page site's history): there the address changes and no new document
  comes. With a text to wait for, the call returns once the navigation has arrived and the text is there, also on a page
  that never goes quiet. Both return the new page's outline with references. When the time runs out the result says
  `loaded: false`, with the outline as far as it is. The rules of "Where Claude may go" hold. Back or forward to a page
  that a form submission loaded is refused, because Chrome might submit it again (*brief 20*).
- **Acting.** `chrome_do` takes a tab and a list of up to 20 steps: click, fill, select, check, press, scroll,
  dialog, wait. Each step names its element by reference.
  - All references are checked before the first step runs. If one is stale, nothing has run.
  - Steps run in order. Each is classified right before its input, on what the element shows at that moment,
    exactly as a single action is ("What is free and what asks"). A free step is dispatched once. An asking step
    isn't dispatched: it is prepared.
  - Each step's element is checked again right before the step, on what the page shows then, its value included.
    It must still be what Claude last saw, unless this list's own earlier step on that same element changed it.
    Text that arrived in a field after Claude read it (a draft the page loaded, his own typing) is never
    overwritten: the step ends `stale` and the result shows the field as it is.
  - Before every further step, and after every wait, the tool looks at the tab. A submission the page started and
    the tool holds, an open dialog or a new page stops the list there.
  - The list stops after the first step that is prepared, fails, opens a dialog, loads a new page, makes the page
    start something the tool stops, or ends `unknown`. The result names the steps that didn't run. Nothing is
    retried and nothing runs twice.
  - So filling a form and sending it is one call and one question: the fills run, the click on the submit button is
    prepared, and its question shows the whole form as the page then holds it. `chrome_submit` runs it.
- **Every call ends before its caller gives up.** The caller's side waits 10 seconds for a read and 30 for a
  change (read in brief 20's `protocol.py`), and a caller that times out doesn't know what ran. So each tool
  has one deadline of its own, inside those: 8 seconds for a read, 18 for opening, going, taking and for a list of
  steps. In a list no step starts after second 12, and the steps that weren't started are reported as not run;
  Claude sends them again. About a dozen input steps fit in one call, because the tool waits out its hold of half
  a second after each input.
- **What a result carries.** What happened per step. Then, once the page has gone quiet (at most 1.5 seconds),
  **what changed**: the outline lines that are new, different or gone since before the call, in at most 2,000
  characters, with a count of the rest. When a new page loaded, its outline instead. A dialog that opened, a
  prepared operation with its question, a step the page started and the tool stopped, and a clipboard write are
  named too. Everything from the page is untrusted content. Any prepared operation still waiting is listed (rule
  4.10).
- **Uploads** stay a call of their own, `chrome_upload`, because the file's bytes come through the caller's side
  (rule 4.4). It always prepares an operation.

### What is free and what asks

Every input Claude dispatches is classified by what it would activate, whichever action carries it: a click, Enter
or Space on a focused control, any other key, filling, choosing or ticking.

**Free:** reading, finding text, scrolling, following links to web addresses, navigating to any web address (one he
gave, one from a page or one Claude wrote), typing and filling fields, choosing from lists, ticking boxes, opening and
closing Claude tabs, taking one of his tabs and giving it back. Searches are free everywhere: a search form sent as a
plain address (GET) is navigation.

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
   a fill step, which inserts them as text, never as an Enter key (*brief 20*, also on chat sites).
4. **Delete or Backspace outside text editing** (decision 14): on a selected item, card or object, or with no text
   field focused.
5. **Uploading a file to a site:** putting a file into a file field asks, because many pages send a file as soon as
   it is chosen. The bytes come through the caller's side (rule 4.4) into a copy the service owns and his user can
   read but not change, the question shows the real path and the hash, and the field gets exactly that copy.
6. **A confirmation the page shows** whose text or button contains a word from the list (below: confirmations).

**Asks, stopped while the page handles Claude's input.** A free input can make the page's own script submit a form
or activate a control: a click handler, a key handler, or the `input` and `change` events that filling, choosing and
ticking fire. While the page handles any input Claude dispatched (those handlers and the tasks they schedule, for up
to 500 ms: the hold, *brief 20*), a small script the extension puts into each Claude tab before the page's own
scripts run stops, and reports:

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

**His own input in a Claude tab** (owner, 2026-11-09, board #138: "Yes, ask in that rare case"). A submission in the
same browser task as his own input (a trusted input that arrived while the extension had no input of its own in
flight) is his and isn't held. Within the short limit after Claude's input, the tool can't tell whose input started a
delayed page step, so a submission his input starts after a delay inside that window is held and asks, like one of
Claude's. When it's unclear whose input it was, the submission is held. The extension marks its own input as in
flight before dispatching it and clears the mark only after the page has handled it; the mark and the verdict never
pass through anything the page can see or write.

**Every click of Claude's is a user's click to the page** (*brief 20*). The page may open a popup or write to the
clipboard during it, as after his own click. A popup becomes one of Claude's tabs ("Which tabs Claude works in").
When the tool sees the page write to the clipboard, the result says so, without reading what was written, and the
instructions tell Claude to tell him and never to paste or run clipboard contents because a page asked.

**What can't be stopped is never reported as stopped** (*brief 20*, fix rounds 2 and 3). An activation of an asking
control can reach the page without passing the wrappers, for example a click event dispatched with a function taken
from a fresh frame. The capture listener catches it after delivery has begun and stops the page's handlers. If the
event can be cancelled, it is cancelled. If it can't, the tool takes the control's default action away for the
length of the hold: a link (`a`, `area`, SVG `a`) loses its address and its `ping`, a submit button (image buttons
and buttons tied to a form by `form=` included) is switched off, and a session rule of the extension's, limited to
this tab and to the hold, blocks the stand-in address, so a new tab, a named frame, a ping or a download can't carry
the action out either. His own click in that tab still navigates. Both cases are reported as stopped and never
resumed; Claude can prepare the action again with its own input. A default the tool doesn't know how to take away is
reported as `unknown` ("the page activated 'Delete' by itself; it may have happened"), never as stopped. One path
isn't seen at all: a page that does every step with functions borrowed from a same-site window outside Claude's tabs
("Known limits").

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
- files he chose himself in a file field of the page: each by its name, its size and the SHA-256 of its bytes, so
  the question shows them and a swapped file is refused (*brief 20*);
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
total is too large to show whole (rule 4.1) or when no editable field holds text. An editor inside an `about:blank`
or `srcdoc` frame, as many rich-text editors use, is read and guarded like the page around it, and sends after
approval (*brief 20*).

**The text next to Send is bound too** (*brief 20*, fix rounds 2 and 3). For a send, a form submission or a
confirmation without an adapter, the tool also binds the visible text of the compose area, where the page has one:
the smallest area that holds both the send control and the draft, with line breaks and spaces kept where the page
shows them. So a preview or a quoted message beside the editor can't change unseen while the approval waits. If that
text differs right before the input, nothing is sent and the tool asks once more, with a question that shows the
text before and after. If it has changed again by then, the tool stops for good ("the text next to Send keeps
changing") and Claude asks him to send it himself. Live text outside the compose area (a clock, an autosave line)
never causes a second question. The adapters for his usual sites bind exactly what they name.

Other asking controls (delete, buy, subscribe and the like) bind the item they act on: the item an adapter names, or
else the smallest list item, row, article, form, dialog or region around the control, with its visible text up to a
bound, so the question can say what is deleted or bought and a re-sorted list can't swap it.

Where the page's script decides the destination and the tool can't see it (a control outside a form, without an
adapter), the question says so ("where the page sends this isn't visible to the tool"); it never names a destination
it didn't read.

**The question** is one plain sentence the tool writes, as the page shows it: the site and path (addresses in the
public form of "Reading a page"; `?…` marks a part that isn't shown), the signed-in account where an adapter reads
one, the label of the button or key, and what goes where; for example "Post a comment
on github.com/…/issues/12, as the page shows it: 'Thanks, fixed in #13' (button 'Comment')?". The content fields
follow: everything in the list above, files with path and hash, the number of hidden fields with their names and
values, and each password field by its label only.

**What the binding guarantees:** the input goes only if the page still shows what he approved, checked right before it
is dispatched. The comparison uses full addresses, also where the question shows the public form: a destination whose
query changed while the approval waited is refused. A page script that changes the page in the instant between that
check and the input, or that sends something else afterwards, isn't stopped (below).

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

### Chrome's own dialogs (alert, confirm, prompt)

*brief 20.* A dialog blocks its page, so it is handled before anything else in that tab.

- **Opened while Claude controls the tab:** Claude answers it with a `dialog` step. The page script is armed first,
  through the debugger, so what the page does after the answer is held like after any other input of Claude's. A
  confirmation of an asking kind is prepared instead (above).
- **Already open when Claude took the tab:** Chrome 157 gives no way to reach it. The tool waits five seconds at
  most, never hangs, and tells Claude to ask him to answer it himself; the tab is usable again once he has.
- **Opened through a function borrowed from another frame:** the tool can't hold what the page does after the
  answer. Answering it always asks, with the exact answer in the question and the words "its continuation isn't
  held", and "don't ask again" never covers it.

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

*brief 28*, and *brief 28b* for his tabs. Seventeen tools are offered to Claude, where brief 20 had 28.

| Action | Effect | What it does | Replaces (brief 20) |
|---|---|---|---|
| `chrome_tabs` | read | every tab of every normal window in one result: number, whose, title, address (public form), marks | `chrome_tabs` (5 to 10 tabs per call) |
| `chrome_read` | read | the outline of a tab, or of up to five tabs; one part by `ref`; `find`; `until`; paged by `max` and `cursor`. In one of his tabs it reads in place and needs `request` | `chrome_read`, `chrome_read_form`, `chrome_find`, `chrome_wait` |
| `chrome_open` | change | open a web address in a new Claude tab (an address, a link or a library entry by reference, or the address of one of his tabs), wait, return the outline | `chrome_open`, then wait and read |
| `chrome_go` | change | in a Claude tab: an address, back, forward or reload; wait, return the outline | `chrome_navigate`, then wait and read |
| `chrome_do` | change | up to 20 steps in one tab (click, fill, select, check, press, scroll, dialog, wait), each by reference. An asking step isn't dispatched and returns a prepared operation, and so does a submission the page starts while handling a step; an activation the page starts is stopped and reported, never resumed. Returns what changed | `chrome_click`, `chrome_fill`, `chrome_fill_form`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll`, `chrome_dialog` |
| `chrome_upload` | change | prepare putting a local file into a file field (it asks through `chrome_submit`) | the same |
| `chrome_show` | change | bring a tab and its window to the front, for him | new |
| `chrome_close` | change | close Claude tabs; one of his only when he asked (`request`) and the tab is known clean; never a taken tab | `chrome_close_tab` |
| `chrome_take`, `chrome_release` | change | take one of his tabs for acting (it reloads once; `reload: true`, when he agrees, where the tool can't rule out a loss; never a page of the fixed list); give it back to its place | `chrome_take_tab`, `chrome_release_tab` |
| `chrome_library` | read | his downloads (and where Chrome saved them), bookmarks or history, to find pages: titles, addresses in the public form, and a reference per entry to open it | `chrome_downloads`, `chrome_bookmarks`, `chrome_history` |
| `chrome_submit` | **send** | run one prepared operation, by id and hash, after the page-state check | the same |
| `chrome_submit_trusted` | send, free | as `chrome_submit`, only for a kind he set to "don't ask again" | the same |
| `chrome_drop` | change | drop a prepared operation; a stopped page step stays stopped and nothing happens on the page | the same |
| `chrome_operation_status` | read | an operation's stages (rule 4.3) | the same |
| `chrome_notices`, `chrome_notice_ack` | read, change | the warnings he should see (an input that may have run, a dropped operation), and marking one as seen | the same |
| `chrome_sites` | owner-only | his read-only sites and his "don't ask again" entries, to see and change | the same |

- **The asking tools don't change.** `chrome_submit`, `chrome_submit_trusted`, `chrome_drop`,
  `chrome_operation_status` and the notices keep their names, inputs, results and behaviour, and the managed ask rule
  stays on `chrome_submit` alone (section 7).
- **A list from `chrome_library` is a snapshot,** so paging through it is stable. A snapshot expires 5 minutes after
  the last page was asked for, or 30 minutes after it was made, whichever comes first; then the list starts again
  (*brief 20*).
- **What every server pays once:** the rules shared by all Chrome actions (untrusted page text, what to do on each
  error, the notice on an unqualified Chrome version, the clipboard rule, the rule for his tabs) are in the Chrome
  server's MCP instructions, and each description holds only what is specific to its action (brief 18d's pattern).

**Left out on purpose:**

- **Running script text, reading the console or the network.** Script text never runs (above). A project's own
  debugging uses its own browser from the terminal ("Project work in Chrome").
- **Screenshots, coordinates, hover and drag.** Text only first (owner, 2026-11-13); see "Reading a page". Hover
  and drag stay *later* in [`FEATURES.md`](../control/FEATURES.md).
- **A search that needs a model** ("find the login button" in free words). `find` is literal, free and testable.
- **A "current tab", loops or conditions in a step list, steps across several tabs.** Every call names one tab, and
  Claude decides between calls.
- **A richer result for `chrome_submit`.** It keeps brief 20's result (the stages, and what the page showed); Claude
  reads the tab afterwards when it needs more. Changing it would change the asking path.

### Efficiency, as a tested property

*brief 28.* "Better" is a number here. A test group runs fixed scripts against fixture pages, with no model and no
real site, counts the calls and the characters returned, and fails the build when a budget is exceeded. The baseline
is brief 20's tool list on the same fixtures, recorded once before it is replaced, and used as well as it allows
(its wait that returns a read, its form fill, its find). No test compares against Claude in Chrome.

| What | Brief 20 | Budget |
|---|---|---|
| Long page (120 paragraphs, 80 fields): the first read | 16,000 characters, page 1 of 14 (*checked*) | the whole outline in 1 call, at most 6,000 characters |
| The same page read to the end (`full`, then its cursors) | 221,477 characters, 14 calls (*checked*) | at most 75,000 characters, at most 3 calls |
| Its 80 fields with their values (the form by `ref`, after the first read) | inside the 14 pages | 1 further call, at most 6,000 characters |
| A table of 200 rows (by `ref`, after the first read) | recorded by brief 28 | 1 further call, at most 1.3 times the cells' own text |
| Finding one link among 300 | recorded by brief 28 | 1 call, at most 800 characters |
| Open a page and read a fact from it | open, then wait (which returns the read): 2 calls | 1 call |
| Fill 6 fields and send the form | read, `chrome_fill_form`, find the button, click: 4 calls and `chrome_submit` | 2 calls and `chrome_submit`, one question |
| Three result pages, one click each | a click and a wait per page: 6 calls | 3 calls |
| Compare three open tabs | a read per tab, each paged | 1 call |
| List 25 open tabs | 3 calls | 1 call, at most 3,500 characters |
| A free click that changes part of the page | a click, then a read or a find: 2 calls | 1 call, at most 2,500 characters |
| Read a fact from one of his tabs (*brief 28b*) | list, take, read; the tab moves | list, read; the tab untouched |
| What a session loads: descriptions and instructions | 28 tools; recorded on main after PR #27 | 17 tools, at most 10,000 characters, and not above the baseline |
| What a session loads: names and input schemas | 28 tools, about 10,600 characters (PR #27 at `8b7e799c`) | at most 6,000 characters |

- Every budget names the exact calls it allows (brief 28's table), and the test makes those calls and no others. A
  budget nobody can meet is changed in the brief, never in the test.
- Characters are counted on the whole result as Claude receives it. Brief 20's two *checked* numbers count the page
  text alone, which is a little less.
- Where the middle column has no number, brief 28 measures brief 20's tools on the fixture before it removes them,
  and the budget must also beat that number.
- Mail's 28 tools take 21,055 characters after brief 18d. A test pins Chrome's totals, so a later change can't grow
  them unnoticed.
- **Latency:** fewer calls don't prove a faster tool, because a step still reads the page's facts as brief 20 does.
  So brief 28 times brief 20's tools and the new ones in the same CI run, where the runner is the same: the first
  read of the long page, a free click with its report, and the 6-field form must each take at most 1.10 times
  brief 20's median plus 50 ms. PR #27 has no latency check at `8b7e799c`; one that its later part brings stays
  green.
- The efficiency group is a CI check only. It never turns anything off on the laptop: the qualification record
  ("Tests") counts the safety groups, not the budgets.

### Project work in Chrome (decision 23)

The same session does project work, so a project's check in Chrome uses the same tools, with the same rules: his
deployed site while he is signed in, or a server on the machine itself (`http://localhost`), since navigating to web
addresses is free. A project's own automated browser tests run as in normal Claude Code, for example with Playwright's
own Chromium from the terminal and an empty profile, without his sign-ins.

### Known limits

The list every tool keeps (`docs/REVIEW.md`, "Tools for Claude"): what it is, the harm, and why it is accepted. It
starts from brief 20's re-checks (`reviews/20-chrome/KNOWN-LIMITS.md`, *brief 20*). A limit is for low harm; a flaw
with real harm is fixed instead (owner, 2026-11-11). Each brief's report keeps the list true.

**A page acting on its own**

- **A page that sends on its own isn't held.** After an ordinary, free action (a click on a button without a telling
  label, typing, opening a chat), the page's own scripts, service workers or WebSockets can send what Claude entered
  or did: an autosave, an icon button that posts, typing indicators, read receipts, a send started after the
  500 ms hold. *Harm:* data leaves without a question. *Accepted:* the tool recognises actions before it acts; it
  doesn't intercept traffic (decision 25). The same holds for any browser tool.
- **A hostile page that borrows every step.** A page with a same-site window outside Claude's tabs can take every
  function it needs from that window (building the element, registering the handler, inserting it, dispatching the
  click) and so run a control labelled Delete during Claude's click without a question. The result reports Claude's
  click as dispatched, with what the page did unproven; it never says nothing happened. *Harm:* what that page could
  do anyway: it could call its own server without any click. *Accepted:* only a deliberately hostile page does
  this, and the three possible fixes each break a rule that matters more (they can't see the borrowed call, would
  expose password fields, or would attach to a tab that isn't Claude's).
- **Every click of Claude's counts as a user's click.** The page may then open a popup or write to the clipboard,
  as after his own click. Popups join Claude's tabs. A clipboard write is reported where the tool can see it
  (not through borrowed functions), never read. *Harm:* a page puts text on his clipboard. *Accepted:* withholding
  this would break ordinary clicks; the instructions tell Claude to tell him and never to paste or run clipboard
  contents because a page asked.
- **Between the check and the input** a page script can still change the page. *Harm:* the input lands on a page
  that differs from the question by an instant's change. *Accepted:* the check runs in the extension right before
  the input, which narrows this to an instant; it can't be closed from outside the page.
- **A page can notice the tool.** In a tab Claude controls, a script can detect that some functions are wrapped.
  *Harm:* a site may behave differently or refuse to work there. *Accepted:* it affects only Claude's tabs; nothing
  runs in the page's own world in his other tabs.

**What the tool recognises**

- **The word list is a rule of thumb.** A control that sends without saying so (an icon without a label, another
  word, another language) is free unless an adapter names it; a harmless control with a listed word ("Clear search")
  asks. *Harm:* a missed question, or one too many. *Accepted:* decision 25; the adapters name his usual sites'
  sends exactly, and the tool-user rounds count both kinds.
- **Data can leave through addresses.** Navigating and GET searches are free, so an address Claude writes can carry
  text to a site. *Harm:* as with `WebFetch` or any browser tool. *Accepted:* decision 25.
- **`done` doesn't prove what the site did.** The tool sees the input and the page, not the network. *Harm:* a site
  may have refused what was sent. *Accepted:* results say "as the page shows it", and nothing is ever sent again by
  itself.
- **Text next to Send that keeps changing.** A change adds one more question, showing before and after; a second
  change stops the send, and he sends it himself. Where the smallest area holding Send and the draft is the whole
  page, all its visible text is bound, so live text anywhere on such a page can end the same way. *Harm:* an extra
  question, or a send he does by hand. *Accepted:* it is the bounded price of binding previews; revisited after his
  live tests if his real sites hit it often.
- **His own delayed step in a Claude tab asks.** Within the 500 ms after Claude's input the tool can't tell whose
  input started a delayed page step. *Harm:* a question about his own action. *Accepted:* his decision (board
  #138).

**Dialogs**

- **A dialog already open when Claude took the tab** goes back to him. *Harm:* Claude waits for him. *Accepted:*
  Chrome gives no way to know who opened it or to hold what follows.
- **A dialog opened through a borrowed function** always asks, and what the page does after the answer isn't held.
  *Harm:* as "a page that sends on its own". *Accepted:* the question says so, and the answer runs once.

**Reading and his tabs** (*brief 28*, *brief 28b*)

- **A page that changes what it shows without changing its address.** A read, a take or a close of one of his
  tabs is bound to the document and address the list showed. A page that swaps its content in place (a chat that
  switches conversations) keeps both. *Harm:* Claude reads other content of the same site than the title in the
  list promised. *Accepted:* it is the same page of the same site that his request pointed at, the result shows
  the title as it now is, and nothing in Chrome tells the two states apart.
- **`request` records Claude's reason; it proves nothing.** The tool can't check that a tab is the one his request
  needs. A careless Claude, or one misled by a page's text, can read a tab of his that the request didn't need and
  write a plausible reason. The **READ** sign, the popup list and the log come after the read: they let him see
  it, they don't prevent it. *Harm:* that page's text reaches Claude. *Accepted:* choosing the tab is the agent's
  judgment, as with any tool that reads on his behalf (decision 24), and reading his open tabs is what he asked
  for. What the tool can enforce, it does: the page bound to the list, his never-list, incognito, the password
  rule, and a question before every send. The tool-user round measures how well the instructions hold.
- **Reading a tab that Chrome put to sleep is a visit.** The page is fetched and its scripts start, as when he
  clicks the tab. *Harm:* the site sees the visit, and a page may mark something as read. *Accepted:* visiting the
  page his request needs is what he asked for, and navigation is free (decision 25). The result says that the tab
  was woken. "Leaves no trace" is promised only for a tab that is already loaded, and a tab that wakes with
  restored fields isn't known clean for a later take or close.
- **In his own tabs Claude doesn't see what a single-line field holds.** Where the reader hasn't watched a page
  from its start, such a field shows only whether it is filled ("What the extension can and can't do"). *Harm:*
  Claude can't read back a name, a number or a search he typed in a tab of his; it reads his drafts in long
  fields, and it sees the rest after a take with its reload or in a copy of the page in its own tab. *Accepted:*
  a password he made visible is a single-line field that looks like any other, and a password is never a limit. A
  passive marker that proves each field's history could lift this later, after his live test. In Claude's own
  tabs the same hits one case: a filled single-line field inside a component whose shadow root the reader met
  late.
- **A secret he unmasked in a long field, under a label that says nothing.** In a document the reader didn't watch
  from its start, a multi-line field or an editable area is read unless its name says credential or it is masked
  at that moment. A settings page that masks a long secret by style (a key, a recovery phrase), labels it only
  "Value", and that he switched to visible before Claude looked, is read like the text it then is. *Harm:* that
  secret reaches Claude. *Accepted* (lead, 2026-11-13): reading his drafts is what he asked for, and it needs long
  fields to be readable; a password field is always a single-line input, and those stay unread; such a secret is
  plain text on his screen at that moment, like a key a page prints as text; the name list covers the labelled
  ones (secret, token, private key, recovery phrase, seed).
- **Claude doesn't see what follows `?` or `#` in an address.** *Harm:* it can't quote or rebuild such an address
  (a video's link, page 3 of a search); it opens the link by reference instead, or shows him the tab. *Accepted:*
  that part of an address is where sign-in codes travel, and the tool can't tell a code from a page number. If his
  live test shows this in the way, naming harmless parameters per site is the later step.
- **A question shows where a form goes without its query.** The site and the path are shown, and `?…` marks that
  there is more. *Harm:* he approves a destination whose last part he can't read. *Accepted:* what the form
  itself sends is shown in full, hidden fields included; the tool compares the whole destination right before the
  input and refuses a changed one; and showing the query would put sign-in tokens into Claude's context.
- **A secret in an address's path that doesn't look like one.** The public form hides what follows a sign-in word
  and anything that looks random. A short or wordy key elsewhere in a path is shown. *Harm:* such a link's key
  reaches Claude's context and the log. *Accepted:* the path is what tells one page from another, so it can't be
  hidden whole; sign-in links of this shape are rare, and most are used up when he opens them.
- **A reload on take loses what isn't work:** an open menu, a place in an endless list, a selection. *Harm:* he
  finds his tab reset. *Accepted:* the take rule (owner, 2026-11-11); looking needs no take, and Claude can work on
  a copy of the page in its own tab.
- **Work a page keeps where the tool can't look.** The check before a reload or a close looks at fields, editors,
  files, canvases, media and loading. A page he has used can still hold something in its script's memory alone,
  with no field showing it (an earlier step of a wizard). *Harm:* that state is lost when the tab is reloaded or
  closed. *Accepted:* the same happens when he closes the tab himself; pages that care ask "Leave site?", and the
  tool never answers that for him.
- **A group of his that held only the taken tab comes back as a new group.** Chrome removes a group when its
  last tab leaves, and the tool makes one with the same name and colour on release. *Harm:* a group he had saved
  or synced isn't linked to the new one. *Accepted:* the tab, its place and the group's look are restored; Chrome
  offers no way to keep an empty group.
- **A tab from one of his groups, or a pinned one, shifts while it is taken.** Chrome allows a tab one group and
  no group among pinned tabs. *Harm:* that tab steps to the edge of his group, or out of the pinned tabs, until
  it is given back. *Accepted:* every other taken tab stays exactly where it is, and a release puts these two
  back.
- **What he types into a taken tab can be lost when Claude navigates it.** *Harm:* his text in a tab that Claude
  is working in. *Accepted:* the tab is marked as Claude's for as long as it is taken, and giving it back is one
  click.
- **An unchanged element can come to mean something else.** A reference is checked on its own element: its name,
  its value, its options, where its link leads. The page around it isn't checked. A button that keeps its name
  while the row around it now shows another item still runs. *Harm:* Claude takes a free step with an older
  picture of what stands next to the control. *Accepted:* a step the tool recognises as a send, a delete or a
  payment still asks, and its question shows and binds the item, the form and the draft as they are then; the
  result of every step says what changed during the call, not what changed before it.
- **A reference's letters could repeat after the service lost its record of them.** The service never draws the
  letters of its last 100 runs again, from a record in its store. If the store was restored to an older state or
  couldn't be written, a new run draws at random, and one draw in about 9,000 repeats an old run's letters.
  *Harm:* a reference Claude kept from that old run could then name another element. *Accepted:* it needs a lost
  store, that draw, and Claude using a reference from before the restart instead of reading again.
- **The outline folds long content.** A control inside a folded part isn't in the first read. *Harm:* an extra
  call (`find`, or a read by `ref`). *Accepted:* it is the point of the budget; what asks is decided when Claude
  acts, on the element itself, never from the outline.
- **Marking page text untrusted doesn't make Claude immune.** A model can still misread or be misled by a page.
  *Harm and acceptance:* the normal MCP level (decision 24); everything a question shows is read and bound by the
  tool itself.

**Around the tool**

- **Fixtures aren't his real sites.** A real site's layout or bot check may need an adapter update or his own
  hand. *Accepted:* the staged check on his laptop after the first boot.
- **Crash tests cover the failures that were modelled.** *Accepted:* an unknown outcome is never repeated by itself.
- **Under decision 24,** a tricked Claude, or another program of his user, could disturb or imitate the native
  host or start Chrome in another way, as with any program of his (section 7).

### Tests

On GitHub's Linux machines with branded Chrome and fixture sites, each case proven by a fixture receiver's own log.
The whole set runs twice per build, and again on each new Chrome stable and beta (a daily job; beta is about four
weeks ahead, so a new major is normally qualified before his Chrome reaches it); a failure turns the affected adapter
or rule off until it is fixed, with the generic rules or a refusal in its place. Each new record reaches the laptop as
its own small update, not tied to an image build: the job publishes it with a GitHub artifact attestation, and the
service fetches it daily, accepting it only when the attestation verifies and it keeps every entry already held; the
job itself verifies the published record before appending to it. Each entry names the tool build it tested, and the
service counts only its own build's entries. The record keeps full versions and gates by major version (a passing
beta counts for its major): a patch of a qualified major runs normally, and a recorded failure turns off what failed.
On a major version with no entry at all for the installed build (rare: his Chrome reached a new major before any
record of it reached the laptop, for example after weeks offline), the tool runs in a conservative mode
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
   (a GET search form, links, typing, line breaks through a fill step, choosing, ticking) don't ask.
2. **Stopped page steps:** on honest fixtures, a `submit()` call and a submission through the `submit` event
   (`requestSubmit()`, a submit button, Enter), each started by a click handler, a key handler, and the `input` and
   `change` events of filling, choosing and ticking, are stopped and asked. After approval only that submission runs
   once: the receiver gets one submission, and the fixture counts no second click, key or input event from Claude. A
   script's `click()` and a dispatched click event on a labelled Delete link, started by any of those handlers and
   also one dispatched as not cancellable, are stopped before delivery and never resumed: no handler runs, the link's
   address isn't opened, and the result tells Claude what the page tried; Claude then acts on the link itself, which
   asks, and after approval it runs once. The fallback is a click dispatched with a function from a fresh frame, which
   bypasses the wrappers. A cancellable one is cancelled. A non-cancellable one has its default taken away for the
   hold: each kind of link and of submit button, and the routes through a new tab, a named frame, a ping and a
   download, with the receiver at zero. Both are reported as stopped and never resumed, and his own click in that
   tab during the hold still navigates. A default the tool can't take away is reported as `unknown`, never as
   stopped. Of all mixes of wrapped and borrowed steps, only the one where every step is borrowed runs unheld; the
   report lists it as a known limit. Nested handling: a handler that re-enters after
   its approved run gets no second pass from the mark or the allowance. Both resume paths keep their kind: a resumed
   `submit()` fires no `submit` event and runs no field checks (a form with a field that fails its checks still goes,
   as the page's `submit()` would have sent it); a resumed `requestSubmit()` runs the field checks and the page's
   `submit` handlers once. The loop case: a `submit` handler that cancels the event and calls `submit()` itself sends
   once, with one question; a handler that submits twice, or submits another form, gets a question for the extra one.
   His own input in a Claude tab (board #138), with the receiver's log as evidence: his Enter 130 ms after Claude's
   click, in a task with no input of the extension's in flight, submits at once without a question; his input during
   Claude's in-flight input is held and asks; Claude's own dispatched input never counts as his, also when the page
   forges any message, attribute or global it can reach; a submission his input starts after a delay inside the short
   limit is held and asks, also when his same input first submitted at once without a question (the exemption ends
  with that task); one he starts after the limit has passed isn't held.
3. **The binding:** after approval, a change to any recorded item (address, document, frame, element, label, the
   form's action or method, a visible or hidden field, compose text outside the form, the account an adapter reads,
   recipients, chat, a confirmation's text or opener) is refused and asks again; a closed tab or a Chrome restart
   refuses; one approval runs once; the deadline holds. Sends outside a form, without an adapter: Claude fills a
   compose area, an unrelated upload is approved, Send is prepared, and the text changes while the approval waits:
   refused (re-check 30). A message body in a plain editable `div` beside a named region holding the recipients and
   Send, with no dialog or form around them, is bound, and a change to it while the approval waits is refused
   (re-check 32). An existing draft Claude never typed is bound; a page with no editable text, or with more than can
   be shown whole, is refused. A read-only preview beside the editor that changes while the approval waits stops the
   send and asks once more, showing the text before and after; a second change stops for good ("send it yourself");
   a change of line breaks or indentation alone counts where the page shows them; live text outside the compose area
   never asks again. A file he chose himself that is swapped for another of the same name is refused.
4. **Confirmations:** a confirmation an adapter named is accepted only when it matches exactly (kind, frame and
   site, text, button); one that differs in any of these is treated as new. A new confirmation whose text or button
   carries a listed word asks on its own, also right after an approved action that didn't name it; one without a
   listed word is free, as the rule and `FEATURES.md` say.
5. **The question matches the page:** every item in the list, files with path and hash, hidden fields, password
   fields by label only, addresses in the public form, and "not visible to the tool" where the destination isn't.
6. **Where Claude may go:** every refused scheme in `chrome_open`, `chrome_go` and links; the fixed list
   reached by taking a tab, a redirect, a popup, back and forward, and an embedded frame, each refused before any
   read or action.
7. **Isolation:** no port listening (checked before and after the tool runs); pages, frames and other extensions
   can't command the extension; DevTools methods outside the fixed list refused; no cookie or storage reading.
   **Passwords:** a known password sits on fixtures in each excluded kind of field (`type="password"`, a field with
   `autocomplete="current-password"`, a field masked by `-webkit-text-security`, a password field switched to plain
   text by a "show password" button, a field whose type changes to password after the page loaded, and a password
   in the field's `value` attribute in the page source), each also inside an open shadow root, a closed shadow root
   and a frame from another site. With brief 28: a sign-in code in a plain field known only by its name, and the
   late cases, where the field was made plain before the reader arrived (by its type, by a removed `autocomplete`,
   by a removed mask), with a label that says nothing; there a single-line field shows only whether it is filled,
   and a long field is read unless its name says credential or it is masked. While the
   reader and the binding run over those forms, a test build records everything the extension receives from the
   browser (every DevTools response and every value its content script reads) and everything it sends to the host,
   the service, the log and the results; the password appears in none of them.
8. **Control and cancelling:** the Stop button ends control, drops prepared operations and sends nothing; dropping,
   the deadline passing, releasing or closing the tab and a Chrome restart each leave a prepared operation
   undispatched; tabs outside the group untouched; a reference stale once its element or document changed. Popups:
   a popup's own Stop ends control without closing or reloading it, and nothing of ours opens a window. Dialogs: one
   opened under Claude's control is answered with the hold armed; one already open at the take is handed to him
   within the bound; one opened through a borrowed function asks and says its continuation isn't held.
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
    one that autosaves typing, one that submits after the hold, and one that borrows every step from a window
    outside Claude's tabs are listed in the brief's report as not held, so "Known limits" stays true.

**Groups added by briefs 28 and 28b.** Groups 1 to 13 keep their cases and run through the new tools. The harness's
helper functions change, and never an assertion about a question, a binding, an approval or what the receiver got. Two
kinds of assertion do change, each listed in its brief's harness map: reading a text field in a taken tab before its
reload now gives `(filled, not read)` for a single-line field (brief 28), and a take reloads the tab itself instead of
the first input (brief 28b).

14. **Reading and references** (*brief 28*):
    - the outline's rules on fixtures, compared with stored expected outlines: text once, every fold with its exact
      count, frames and open and closed shadow roots in place, an open dialog hiding the rest;
    - paging: a text of 100,000 characters, a row wider than the budget and a long value each come back whole over
      their pages, every page advancing; text outside ASCII and five tabs at once stay inside the 48 KiB bound as
      sent; `full` returns a long page with nothing folded or cut;
    - a table, a list, a form, a long text and a single control read by `ref`; `find` across folded parts and
      frames, literal and without regard to case; five tabs in one call, one of them unreadable; `until` met and
      not met, also by a field's value and inside a frame; paging, and a cursor refused after the page changed,
      also when only a field's content changed;
    - references: the same element keeps its reference across reads; an action still works after an unrelated
      change on the page; a removed element, a renamed one, a field whose value changed, a link whose destination
      changed under the same name, a list whose options changed, a new document and an invented reference are each
      refused, with the element's present line where it still exists; a control that only moved or became enabled
      isn't;
    - references that can't collide: with two tabs that have both issued references, no string appears in both,
      and tab A's reference is refused with tab B's number; after a Chrome restart, and after a service restart,
      the same pages are read again until new references exist, and every old reference is still refused; a
      reference dropped from the table is refused and its string never comes back; after a release and a new take
      of the same page, a reference from before is refused;
    - addresses: a marker in the query, the fragment, the user name and a sign-in path of a page's own address, of
      link and form targets, of frames, redirects and library entries appears in no result, error, question,
      status, notice or log line; `chrome_open` by reference still reaches the full address; the binding still
      refuses a destination whose query changed;
    - hostile content: text and names shaped like outline lines, references, folds or instructions come back
      quoted and escaped inside the untrusted fields, in the outline, in tables, lists and forms read by `ref`, in
      a `find` hit's path, in a change report and in a stale reference's present line; a `role` attribute made of
      line breaks, outline lines and references shows as a role from the fixed list and nothing more; a refusal's
      message holds no page text; a page of 100,000 elements is cut with a plain notice;
    - passwords: group 7's fixtures and recording run over every new output (the outline, a form read by `ref`,
      `find` for the password itself, several tabs, `until`, the change report after a "show password" click, the
      results of `chrome_open`, `chrome_go` and `chrome_take`, a prepared operation's question); the password
      appears in none. In a document the reader didn't watch from its start, a single-line text field shows only
      whether it is filled, and the recording shows that the content script kept and sent none of those values; a
      draft in a multi-line field and in an editable area is read; a long field named like a credential, or
      masked at that moment, isn't.
15. **Going and acting in one call** (*brief 28*):
    - `chrome_open` and `chrome_go` return the outline after the load, say `loaded: false` on a timeout, and refuse
      what group 6 refuses; a navigation inside the same document counts as loaded without a new document, and a
      reload doesn't before the new document is there;
    - `chrome_do`: one stale reference means nothing ran; the list stops at the first asking step, a failure, a
      dialog, a new page, a stopped page step and an `unknown`, and the fixture counts no input from the steps
      after it;
    - nothing unseen is overwritten: a later step that fills a field into which the page loaded a draft, or the
      owner typed, after Claude's read is `stale` and the field keeps its text, also when only the cut part of a
      long value changed; a fill and then Enter on the same field passes;
    - the look between steps: a held submission that arrives after a step's reply or during a wait, a dialog and
      a new page each stop the list before the next step, with the held submission prepared;
    - an element far below the fold is brought on screen and the input lands; what the page does on that scroll
      is held like after any input; a list of options is chosen by value or by label, and a label two options
      share is refused; every outcome a step can have appears with its defined shape, and a list that fails after
      some inputs still returns them with their operation ids;
    - a form filled and sent in one call and `chrome_submit`: the receiver has nothing before approval, one
      submission after, none on a repeat, and the question shows every field as filled;
    - the change report names exactly the added, changed and removed lines on the fixture, within its bound;
    - a taken tab stays his: closing it is refused, and navigating it before its reload goes through the same
      check as a first input; a take, and opening one of his tabs' address, need the list's token and are refused
      when the tab has moved on (the opened address is the one the list showed);
    - Chrome, the host and the service each stopped in the middle of a list: no step runs twice;
    - time: through the real command and the real MCP proxy, a list that would wait longer than its deadline
      returns in time with the steps it didn't start counted, and a caller that goes away in the middle leaves
      every step that ran in the log and none running later;
    - two similar tabs, and he switches tabs while a list runs (PLAN task 14): every step lands in the named tab.
16. **Efficiency** (*brief 28*): the budgets of "Efficiency, as a tested property", against the recorded baseline.
17. **His open tabs** (*brief 28b*):
    - the list: every normal window, the marks, every address in the public form, an incognito window absent, a
      hostile title (instructions, forged marks, direction-changing characters) quoted and escaped;
    - looking in place: a fixture page that records every event, mutation, focus, scroll and request it can observe
      sees nothing from a read; the document, his typed text, his scroll position and playing media are unchanged;
      no debugger is attached; his own Enter in that tab right afterwards submits natively; a tab of the fixed list
      or his never-list is refused; an asleep tab is loaded and the result says so; a tab with an open dialog
      answers `owner_dialog` within the bound;
    - the page Claude chose: a read, a take, a close and opening a tab's address are refused without the list's
      token; after he navigates the listed tab (a new document, or a new address in the same document) each is
      refused before anything is read or changed, and nothing of the new page is in a result; unchanged, each
      works with no further step;
    - one profile: a second profile's extension is refused, also after the first one disconnects, until the owner
      command names it; then every token and reference from before is refused;
    - the reason: a read, a take or a close of one of his tabs without `request` is refused; with it, the popup and
      `aresos log` show the tab, the time and the request, and the button shows **READ**;
    - taking: a tab that isn't known clean gives `reload_required` with the reason and hasn't moved: a changed
      field, typing on a page that copies it into the field's default, an editor, a chosen file, a canvas he
      used, playing media, fields restored after Back, a frame that doesn't answer, a load or a submission under
      way; a fresh tab he never touched, and a used one with nothing but an empty or a search field, are taken;
      `reload: true` takes the others, except while a load, a submission or a dialog is in the way; a page loaded
      by a form submission is refused; `chrome_do` on one of his tabs that isn't taken is refused;
      `chrome_release`, **Give back**, dragging out and **Stop** each restore the window, the place, his group and
      the pin;
    - marked in place: a taken tab keeps its window and its place and shows a Claude group around it, also when
      another window is in front and when tabs are taken from two windows; the only tab of one of his groups
      returns into a group of the same name and colour; a tab from the middle of his group returns to its place
      in it;
    - closing: every tab that isn't known clean stays open and is listed with its reason, and no input closes
      it; a known clean one closes and is listed; a taken tab is refused;
    - passwords: in one of his tabs no single-line text field is read in place, so a field he switched to plain
      text before Claude's first read isn't either, whatever its label (in the page itself, in a frame, in an open
      and a closed shadow root; made plain by its type, its `autocomplete` or its mask); after a take with its
      reload a plain field is read again;
    - what he wrote: a draft in a multi-line field and in an editable area of his tab is read in place; a
      single-line field shows "filled" without its value; an editable area labelled "Password" isn't read;
    - the background: a new Claude tab doesn't come to the front, and a list of steps in a Claude tab leaves his
      front tab in front (or the brief's report says why it can't, and the question goes to him).
    A tool-user round (section 8) then checks the rule "the tab his request clearly needs" with a model: tabs named
    "Car" and "Uni website" and a look-alike are open, the request is "check my lectures", and the report says
    which tabs were read.

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
  (allow or deny). Such a hook returning allow, managed or his own, does approve a call that matches a managed ask
  rule: brief 18d measured it for the fake send tool at user and at managed level, in normal and in skip-permissions
  print mode (Claude Code 2.1.319), and a test pins it; brief 18c checks the interactive case. That joins the
  accepted residual below. His own `PermissionRequest` hooks must not match our asking tools, so that a broad
  auto-approve hook of his never answers for him ([`FEATURES.md`](../control/FEATURES.md)). So the switches
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
- A `PermissionRequest` hook can approve a managed ask (brief 18d, print mode; 18c checks the interactive case), so a
  hook that Claude or he writes could approve our asking tools without him answering. That is the same level as
  calling the service directly, and is accepted with it.

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
   asks in skip-permissions mode: *checked*), unless a `PermissionRequest` hook answers it, which brief 18d showed it
   can (the accepted residual, above); the input names one operation by id and hash, and the service
   refuses anything that differs from it at run time.
3. **Claude doesn't answer it in the session:** the prompt is his; the pages that could approve (claude.ai, Remote
   Control) can't be opened in a Claude tab (section 6). The exception is the same: a `PermissionRequest` hook that
   Claude wrote could answer it (brief 18d; the accepted residual, above).
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
   "Yes, and don't ask again", a `PreToolUse` hook returning "allow", and skip-permissions mode; a
   `PermissionRequest` hook returning allow, managed or his own, approving a managed ask (measured in brief 18d in
   normal and skip-permissions print mode, and pinned; the interactive case in 18c); the `question` verified; an
   approval bound to one operation; the app passwords unreadable by his user.
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
| 2. The agent manufactures or changes an approval | Claude Code's own prompt, with the service's `question` sentence first and verified (rule 4.1, section 7, decision 21); approval pages can't be opened in a Claude tab (section 6); managed ask rules that no allow rule, `PreToolUse` hook or mode turns off, with `PermissionRequest` hooks measured in brief 18d (print mode; interactive in 18c) and his own kept off our asking tools (section 7); rule 4.1 makes the approval show the service's description and refuses changes; "don't ask again" only through the owner's channel (section 6) |
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

**Open:** none for Chrome. His answers on his open tabs (2026-11-11), on closing them (2026-11-13, "Yes, when I
ask") and on screenshots (2026-11-13, "Text only first") are built into section 6 ("Which tabs Claude works in",
"Reading a page"); brief 28b lists them with what stays possible later.

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
  narrows that only in its strict setup, best-effort: section 7); and a `PermissionRequest` hook can approve our
  asking tools (brief 18d). The tools still ask for every send, delete and
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
