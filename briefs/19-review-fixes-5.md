# 19-review-fixes-5: drafts are never attachments, the marker stays on drafts

**Goal:** close `reviews/19-mail/REVIEW-5.md` (review of head `4316545`) by refusing instead of disclosing: text
Claude saved as a draft never travels inside an attachment, so there is nothing to disclose there. Forward as
attachment stays for received and sent mail. Approved by the lead on 2026-11-07. Briefs 19 and `19-review-fixes`
to `-4` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule decides.

Read `reviews/19-mail/REVIEW-5.md` first, then this brief, then `control/aresos_control/mail/adapter.py` (the
`authored` check, `mime`, around lines 400 and 431), `codec.py` and `guard.py`.

## What to build

1. **Drafts are never attachments.** A draft, meaning a message carrying the `X-AresOS-Authored` marker or one in
   the SPECIAL-USE Drafts folder, can't be attached or forwarded as an attachment, at any depth: not by
   `mode=forward` with `forward_as=attachment`, not as an explicit `{reference, part}` (its source or any part of
   it), and not as a nested message inside another attached mail. Decide it on the original before any rebuild.
   The refusal names the two alternatives, both of which show the full text in the approval: send the draft itself
   (`mode=draft`), or forward it inline. Draft text still reached by inline forward, reply quoting or `mode=draft`
   keeps round 1's rule: the whole text payload shown in full, or refused as too large, never cut. Take that text
   as it is; never re-parse it as a mail to decide what to show.

2. **The marker is on drafts only.** Today `mime` puts `X-AresOS-Authored: 1` on every outgoing message
   (`adapter.py` around line 400) and on authored attachments (around line 431), so recipients and every Sent copy
   carry it. From now on only `mail_draft_save` writes the marker. Outgoing mail and the Sent copy carry no
   `X-AresOS` header anywhere. Sending a draft builds a new message without the marker. Forwarding the owner's own
   sent mail as an attachment works again, since its text was approved when it was sent.
   - Test, in every compose mode (new plain, new formatted, reply, reply-all, forward inline, forward as attachment,
     draft): the bytes received at the SMTP sink and the Sent copy, fully decoded at every level, contain no
     `X-AresOS` header anywhere; a saved draft still carries the marker after `mail_move` and `mail_copy`.
   - Where an earlier test asserted the marker on sent mail, change only that expectation, and say in the report
     which test and why. No other earlier test changes.

3. **The final check refuses any marker outside the main body** (REVIEW-5 finding 2). In `guard.py`, an
   `X-AresOS-Authored` line found anywhere outside the composition's own main body text, in any header block or
   decoded content, at any depth, whatever the container or child type claims to be, refuses the composition, and
   before `DATA` ends the operation `failed` with nothing sent and no submission on replay. With point 2, legitimate
   outgoing mail has no marker at all, so this needs no "unless disclosed" exception for attachments. Keep the check
   independent of `codec.py`.
   - Tests: builder-bypassing messages with the marker on a multipart container holding an `application/octet-stream`
     child, on a `message/rfc822` container with an opaque child, and inside a base64 leaf; each is refused at
     compose, and at send ends `failed` without `DATA`.

4. **Text parts are scanned line by line, never re-parsed as a mail** (REVIEW-5 finding 3). A `text/*` leaf is
   decoded and every line is scanned for `Bcc:`/`Resent-Bcc:` header lines and the marker, but its content is never
   treated as a nested MIME entity, in `guard.py` or in `codec.py`. Declared containers (`multipart/*`,
   `message/*`, implicit digest children) and transfer encodings keep their strict checks. A non-text leaf is
   walked into as a nested entity only when its decoded bytes start with a complete, well-formed header block
   ending at a truly empty line; otherwise it is opaque and line-scanned.
   - Tests: plain and formatted new mail, and a reply, whose text starts with `FYI: the documents are attached.` or
     `Status: all green` followed by prose lines, compose, prepare and arrive at the SMTP sink unchanged. A text
     attachment that really contains a `Bcc:` line is still refused with the clear reason from round 4.

5. **Finding 1's round trip and a draft sent as itself.**
   - REVIEW-5 finding 1 becomes a refusal test: `compose → mail_draft_save` with a body that starts with `From: …`,
     a long `Subject: …`, an empty line and `Small body`; attaching its source, a part of it, or forwarding it as an
     attachment is refused with the message from point 1, also after moving it out of Drafts.
   - A draft whose body starts with header-like lines, sent as itself (`mode=draft`), shows its whole body in the
     approval, header-like lines included; the 23,100-character version is refused as too large, never cut.

6. **New JUDGMENT-CALL in `REPORT.md`, in plain words:** a mail forwarded as an attachment reaches recipients as an
   `.eml` file (`application/octet-stream`), not as an attached mail their mail program shows inline. Say what the
   common mail programs (Apple Mail, Outlook, Thunderbird, Gmail on the web, iOS Mail) do with such a file if you can
   find out from their documentation, each marked **read** (with the source) or **assumed**. Name no mail provider
   the owner may use; this is about recipients' programs.

Then add a short "Review fixes, round 5" section to `reviews/19-mail/REPORT.md`: each REVIEW-5 finding and point
above, what changed, the tests that prove it (by name), the changed earlier expectation from point 2, and the new
JUDGMENT-CALL. Put the run IDs in `REPORT.md` as in round 4 (the last commit that changes code or tests, both
workflows, both passes; any later commit changes only `REPORT.md`) and the final head's runs in the PR body. Keep
claims marked **run**, **read** or **assumed**.

## Out of scope

Everything else, including a fresh hunt for other issues and the deferred class of ordinary local files Claude
writes itself. Don't edit `reviews/19-mail/REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`,
`docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`,
`docs/control/FEATURES.md`, and `control/tests/`.

## Acceptance

- Each point has regression tests that would fail on `4316545` (or are new behavior) and pass now; the report names
  them. No earlier test is weakened, skipped or deleted, apart from the marker expectation point 2 changes.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse. Take the option that keeps a mail from being sent twice, sent without its approval or differently from what
the approval showed, or deleted without being named, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Commit in small steps and push this branch; draft PR #9 already exists, so don't open another.
  Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 10 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a structural simplification of code it wrote, with byte-level tests.
