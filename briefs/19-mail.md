# 19: Mail tools

**Goal:** the owner's mail as clean tools on brief 18's base: every feature marked *first* in the Mail part of
`docs/control/FEATURES.md`, following design sections 3 to 5, proven in containers against real mail servers. After
this package a fresh Claude can do the seven everyday mail tasks in `docs/control/PLAN.md` with these tools alone:
no guessing, nothing marked read by accident, and every send or delete put to the owner exactly as it will happen.
That is what "works really well" means here; the tool-user rounds after this package measure it.

## Background (read first)

The design, plan and feature list are on the council branch; read them with `git show`:

- `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`: **section 5 is this package's
  specification**; sections 3 and 4 are the rules every action follows (one definition per action, truthful asking
  input, operations recorded before they act, files on the caller's side, untrusted content); section 8 the tests.
- `…:docs/control/FEATURES.md` (Mail part: what is *first*, *later*, *owner*, *never*) and `…:docs/control/PLAN.md`
  (everyday tasks 1 to 7).
- `…:reviews/control-design/2026-11-07-*.md`: the design review and its re-checks; the Mail findings (deleting through
  a free move, partial outcomes, truthful descriptions, `CLOSE`, TLS) are why section 5 reads as it does.
- This branch starts from brief 18's final head: read `reviews/18-control-base/REPORT.md` ("Adding a Mail or Chrome
  adapter", the judgment calls and follow-ups) and `control/README.md` before writing code. Use its `Adapter`
  interface, `Engine`, file transfer, generated artifacts and test support; change the base only where Mail needs it,
  and say why in the report.

In short: `mail_compose` builds the whole mail inside the service and returns its id and hash; `mail_send` names that
composition and repeats everything the owner must see, with Claude's own text in full and long quoted parts by
reference, so the owner's Claude Code prompt shows the truth and the service sends exactly what was approved.
Deleting asks and names each message; moving to Trash is a delete, never a free move. Every send and delete is an
operation in brief 18's log, with per-recipient and per-stage outcomes, and is never retried by itself.

## What to build

All under `control/`, Python 3 standard library (`imaplib`, `smtplib`, `email`, `ssl`, `html.parser`) plus what brief
18 already pins. No other runtime dependency without a reason in the report.

1. **The Mail adapter and its definitions:** every action in the table of design section 5, with schemas and
   descriptions written for Claude (what it does, when to use it, what it returns, its effect, what to do on each
   error), generated into the MCP tool list, the `aresos` command, `docs/control/TOOLS.md` and the ask list
   (`control/settings/ask-rules.json`), following brief 18's naming. Add the `mail` server to the draft
   `control/settings/managed-mcp.json`.
2. **References and state binding** (rule 4.2): a message reference carries account, folder, UIDVALIDITY and UID, and
   is checked before every action; a stale reference fails with "stale, search again", never hits another message.
   Don't depend on `CONDSTORE` or `QRESYNC` (the owner's server may lack them): use them when present, and otherwise
   re-read what the action depends on right before acting. Delete items carry `{reference, from, subject, date}` and
   each is re-checked against the server before anything is deleted.
3. **Reading never changes flags:** every fetch uses `BODY.PEEK`; a test checks flags before and after every read
   action. Incoming HTML becomes readable text with links kept; remote content is never fetched. Long mails and
   folders are paged with cursors bound to the folder's state. Mail content is untrusted (rule 4.8) and is marked so
   in results.
4. **Compose and send** as section 5 says: replies, reply-all and forwards (inline and as attachment) with Reply-To,
   the owner's aliases removed, In-Reply-To and References, a reply to the owner's own sent mail going to its original
   recipients, no Bcc header in what others receive. Attachments from allowed local folders (brief 18's caller-side
   transfer, by sha256) or from parts of other mails. Plain or formatted: Claude writes formatted text in a small
   Markdown subset (bold, italic, lists, links, quotes) and the service produces the HTML and the plain-text part; no
   raw HTML from Claude. The signature and the plain-or-formatted default come from the account's configuration
   (default: plain, no signature); the owner sets them later.
5. **Sending:** SMTP submission over TLS; the Message-ID derived from the operation id and looked for in Sent before
   submitting (brief 18's evidence hook); each recipient's answer recorded (some refused is `partial`); then the Sent
   copy (only where the configuration says the client saves it) and the answered flag as their own stages; a lost
   final answer is `unknown`; `mail_operation_repair` repairs a stage and never submits again.
6. **Deleting and folders:** to the Trash with `MOVE`; for good with `UID EXPUNGE` on exactly the named messages,
   refused without `UIDPLUS`; never IMAP `CLOSE` on a mailbox that may hold messages marked deleted (use `UNSELECT`);
   messages already marked deleted by someone else survive. `mail_move` to Trash is refused. `mail_folder_delete`
   only on an empty folder without subfolders, and only where onboarding showed that the server refuses deleting a
   folder that holds mail; refused elsewhere with a clear reason.
7. **Encoding:** MIME with a plain part (and HTML when formatted), quoted-printable or base64, encoded-word headers and
   attachment names, CRLF; hashes over decoded bytes; a non-ASCII local part refused clearly when the server has no
   `SMTPUTF8`; non-ASCII domains converted.
8. **Transport security and passwords:** explicitly verifying TLS contexts with hostname checks for IMAP and SMTP, no
   plaintext fallback, the password sent only after the check. Accounts are added by the owner with an owner-only
   command over `admin.sock` (`sudo aresos admin mail account add …`): the password is read from his terminal, stored
   in a file only `aresos-tools` can read, and never passes through Claude or the act socket. Onboarding records the
   capabilities, the special folders (by `SPECIAL-USE`, never by English names), whether the server saves sent mail to
   Sent itself, and whether it refuses deleting a non-empty folder (tested on a throwaway folder it creates).
9. **`mail_contacts`** from the owner's mail history (who he wrote to and heard from), **`mail_unsubscribe`** through
   the mail's own `List-Unsubscribe` header (one-click HTTPS POST per RFC 8058, or the `mailto:` it names), asking.

## Tests (containers on GitHub's Linux runners, no model, no real account)

- A pinned GreenMail container with synthetic accounts and outside delivery blocked, plus a small scripted SMTP server
  for failures GreenMail can't produce (a refused recipient, a dropped final answer, a failure at each later stage).
  Where GreenMail lacks something the owner's server has (`SPECIAL-USE`, `MOVE`, `UIDPLUS`, a server that refuses
  deleting a non-empty folder), add a second pinned real IMAP server (for example Dovecot) and say which tests run on
  which. Test both "the client saves to Sent" and "the server saves to Sent".
- Every fixture and every check listed under **Tests** in design section 5, each by name in the report.
- Crash at every step of a send and a delete (brief 18's kill points) never sends or deletes twice; a restore keeps
  brief 18's lock until the owner confirms.
- The asking input of `mail_send` and `mail_delete` for a long mail with Bcc, attachments and odd characters stays
  within brief 18's 16 KiB limit, or is refused as too large, never cut; control and direction-changing characters
  show escaped.
- The generated artifacts are in sync; brief 18's whole suite still passes.

`.github/workflows/control-mail.yml` runs them on pushes to this branch (path filter) and on its pull request; brief
18's base workflow keeps running too.

## Out of scope

- Chrome (brief 20), and the Mail rows marked *later*, *owner* or *never* in `FEATURES.md` (CardDAV, answering
  calendar invitations, send later, new-mail notices, server filters, PDF export, read receipts).
- Anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, and the design and
  plan files (proposals go in the report).
- A real mail account, the provider's name or any real address. Running Claude Code or any model in CI. Anything on
  this Mac outside this worktree.

## Acceptance

- Every *first* row of the Mail part of `FEATURES.md` has its tool and at least one test; the report maps row → tool →
  test. Anything not built is a **PLAN-GAP** with the reason.
- Every check in design section 5 passes, by name.
- The workflow passes twice on the final head.
- No secrets, real addresses, account names or provider names.

## Report (`reviews/19-mail/REPORT.md`)

What was built; the feature → tool → test mapping; the section 5 checks with test names; which server each test ran
on; the tool descriptions as Claude will read them (the generated reference, with anything you are unsure reads well
pointed out); deviations as **PLAN-GAP**s; **JUDGMENT-CALL**s (anything that changes how mail feels for the owner);
what isn't done and why. Mark claims **run** (workflow run ID and log line), **read** (source and version) or
**assumed**.

## Already decided

Design sections 3 to 5, brief 18's base and its owner-facing limits (15-minute approval, 16 KiB asking input, 25 MiB
files), and the owner's decisions in `PLAN.md`. Nothing is retried by itself; nothing resumes by itself after a
restart; deleting is never free.

## If unsure

Take the option that keeps a mail from being sent twice, sent without its approval, or deleted without being named,
and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`. It starts from brief 18's branch; when brief 18 reaches `main`,
  the lead merges `main` in (never rebase). Commit in small steps, push this branch, open a draft PR against `main`
  with `gh pr create --draft`, and say in it that it builds on PR #6. Never merge, never push to `main`, never
  force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 20 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a careful protocol build with many tests on brief 18's base, which it built well.
