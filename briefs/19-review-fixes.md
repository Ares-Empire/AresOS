# 19-review-fixes: fixes from the package review

**Goal:** close the four blocking findings and the one should-fix finding in `reviews/19-mail/REVIEW.md` (review
of head `bc38016`), so no mail can be sent with text the owner did not see, no Bcc leaks, no password reaches a
result or log, and folder deletion is never enabled on a server that was not shown to refuse deleting a folder that
holds mail. Nothing else changes.

Read `reviews/19-mail/REVIEW.md` first, then this brief, then the code it names. Brief 19 (`briefs/19-mail.md`) and
its design still apply; where in doubt, its "If unsure" rule decides.

## What to fix

1. **Finding 1 (blocking): text Claude could have written must be shown in full.** Today `mail_compose` with
   `mode=draft` and no `text` turns the draft's body into a `draft_body`/`draft_html` part shown only by hash. Claude
   can write any text into a draft with the free `mail_draft_save`, so the approval hides Claude's own words and
   escapes the 16 KiB limit. The same hole exists through `reply` and `forward`: Claude saves a draft, optionally
   moves or copies it to another folder, then quotes or forwards it, and the body travels as a by-reference
   `quoted_mail` or forwarded part.
   - In `mode=draft`, show the draft's whole body in the approval like Claude's own text: the plain text in full,
     and, when the draft has an HTML part whose readable text differs from the plain text, that readable text (links
     kept) in full as well. Too large for the asking input is refused with a clear reason, never cut or moved to a
     reference.
   - A part may go by reference only when it comes from a message the service did not build from Claude's input.
     A message created by `mail_draft_save` (in any folder, after any move or copy) is Claude's input: quoting or
     forwarding it shows its text in full under the same limit, or is refused. Mark service-built drafts in a way
     that survives `mail_move`/`mail_copy` and can't be removed by Claude's free tools; if you can't make that
     reliable, show in full (or refuse) for any source in the SPECIAL-USE Drafts folder and any message carrying the
     marker. Say in the report which you chose and what it means for the owner's own drafts.
   - Tests: compose → `mail_draft_save` → compose `mode=draft` without `text` → prepare send shows the full body
     (and the 21,000-character case is refused as too large, never shortened); the same draft moved to another
     folder, then `reply` and `forward` (inline and as attachment) show it in full or are refused.

2. **Finding 2 (blocking): forwarding never leaks Bcc.** Forwarding as an attachment today sends the original
   source unchanged, so forwarding a Sent copy that holds a `Bcc:` header discloses it.
   - Before hashing and approving a forwarded message, remove `Bcc` and `Resent-Bcc` headers from it, including
     from nested `message/rfc822` parts. The approval says the forwarded mail is the original with Bcc removed, with
     the hash of the bytes actually sent. Check the inline forward and the reply/reply-all/quote paths for the same
     leak (Bcc must never appear in To, Cc, a quoted header block or a forwarded header block).
   - Update the report's "exact forward bytes" JUDGMENT-CALL to match.
   - Tests: send a mail with Bcc so the client-saved Sent copy holds the Bcc header (the client-saves-Sent
     configuration), then forward that Sent copy as an attachment and inline; the received mail and every part of it
     contain no Bcc address. Also a nested forwarded message with a Bcc header.

3. **Finding 3 (blocking): no password or raw server text in results, logs or stored operations.** `Engine.submit`
   stores `str(exc)` of any adapter exception in the operation's public `reason`; IMAP and SMTP errors can carry raw
   server text, which may echo the password.
   - Every error that reaches an operation's `reason` or stages, the durable log, the independent append-only record,
     `aresos log`, the act socket or an MCP result carries only a controlled category and a safe message written by
     the service. Raw server text never goes there. As a second guard, scrub the account's password (and its base64
     forms used in `AUTH PLAIN`/`LOGIN`) from any text before it is stored or returned.
   - This touches brief 18's `engine.py`; keep the change minimal, keep the base suite green, and say why in the
     report.
   - Tests: an IMAP server and an SMTP server (scripted fixtures are fine) that echo the password in their failure
     text, during login, after a successful preflight and in the middle of a send and a delete. Check the call's
     result, `mail_operation_status`, the SQLite log, the independent record and the service log for the password
     and its base64 forms.

4. **Finding 4 (blocking): folder deletion is enabled only on proof.** Onboarding today treats any non-OK reply to
   `DELETE` on the non-empty probe folder as "the server refuses deleting a folder that holds mail".
   - Record `safe_folder_delete=true` only when all of these hold: the `DELETE` of the non-empty folder got `NO`
     without a response code that marks it transient, permission-related or otherwise unrelated (for example
     `INUSE`, `UNAVAILABLE`, `NOPERM`, `LIMIT`, `SERVERBUG`, `CONTACTADMIN`, `ALREADYEXISTS`, `NONEXISTENT`); the
     folder and the probe message still exist afterwards, checked by exact reference; the probe message is then
     removed with the exact `UID EXPUNGE` cleanup, which succeeded; and `DELETE` of the now-empty folder succeeded.
     Anything else leaves folder deletion disabled, and the account's `mail_accounts` result says why.
   - Check the outcome of every cleanup step; a failed cleanup leaves folder deletion disabled and is reported to
     the owner, never ignored.
   - Tests: a scripted IMAP frontend that answers the non-empty `DELETE` with a transient `NO [INUSE]` on an
     otherwise unsafe server leaves deletion disabled; a refusal after which the probe message is gone leaves it
     disabled; a failed cleanup leaves it disabled; the existing positive guard test still qualifies.

5. **Finding 5 (should-fix): `mail_operation_repair` describes what it does.** Its description promises "or
   qualified Sent evidence", but repair requires recorded `accepted:250`. Make the description say exactly that an
   operation without a recorded final DATA acceptance can't be repaired and needs the owner to inspect it, then
   regenerate the artifacts (`python3 control/generate.py`).

Then update `reviews/19-mail/REPORT.md`: a short "Review fixes" section naming each finding, what changed, and the
test that proves it (by name); update the run IDs so they are the workflow runs on the final head; keep claims
marked **run**, **read** or **assumed**.

## Out of scope

Everything outside these five findings, including a fresh hunt for other issues and the report's other
JUDGMENT-CALLs and PLAN-GAPs (the lead takes those to the owner). Don't edit `reviews/19-mail/REVIEW.md`. The same
paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`,
`docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, and `control/tests/` (brief 18's tests stay as
they are).

## Acceptance

- Findings 1 to 4 each have a regression test that would fail on `bc38016` and passes now; the report names it.
  Finding 5 is covered by the generated-artifact check.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Take the option that keeps a mail from being sent twice, sent without its approval or differently from what the
approval showed, or deleted without being named, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Commit in small steps and push this branch; the draft PR #9 already exists, so don't open
  another. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 8 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same careful protocol work as brief 19, on code it wrote.
