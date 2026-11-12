# 19-review-fixes-2: second round of review fixes

**Goal:** close the three findings in `reviews/19-mail/REVIEW-2.md` (fix review of head `300cd06`). Nothing else
changes. `briefs/19-review-fixes.md` and brief 19 still apply; where in doubt, their "If unsure" rule decides.

Read `reviews/19-mail/REVIEW-2.md` first, then this brief, then the code it names.

## What to fix

1. **REVIEW-2 finding 2 (blocking): every mail attached to an outgoing composition loses its Bcc.** Today only
   `mode=forward` with `forward_as=attachment` removes `Bcc`/`Resent-Bcc`; an explicit
   `attachments=[{"reference": …, "part": "source"}]` (or a `message/rfc822` part, or a part that contains nested
   messages) attaches the original bytes with the Bcc header.
   - Apply the same recursive `Bcc`/`Resent-Bcc` removal (`codec.without_bcc`) to every mail-source attachment of a
     composition, in every mode, before hashing and approval; the approval names the transformation and the hash
     of the bytes actually sent. Do it only on the compose path: `mail_attachment_save` and `mail_read` keep giving
     the owner the original bytes.
   - Test: send a mail with Bcc (client saves Sent), then compose a new mail and a reply that attach that Sent
     copy's `source` and a nested `message/rfc822` part explicitly; the received mail and every part of it contain
     no Bcc address, and `mail_attachment_save` of the same source still returns the original bytes.

2. **REVIEW-2 finding 1 (blocking): a mail saved to disk can't come back as an attachment.** Claude can save a
   service-built draft as `.eml` with `mail_attachment_save` and attach that file through the caller-side import,
   so its text travels by hash only. The same round trip re-attaches a Sent copy with its Bcc header.
   - Refuse a caller-imported local attachment when its content is an RFC 822 mail message, decided from the
     bytes (a leading header block with `From:` and at least one of `Date:`, `Subject:`, `Message-ID:`,
     `Received:`, `MIME-Version:` before the first empty line, with tolerance for a BOM and leading whitespace), and
     also when its name ends in `.eml` or `.msg`, whatever the content. The error tells Claude to forward or attach
     the mail itself by reference (`mode=forward`, or `{reference, part: "source"}`), which goes through the
     authored-text and Bcc rules.
   - Record this as a **JUDGMENT-CALL** in the report: the owner can't attach a saved `.eml` file from his folders;
     he forwards the mail itself instead.
   - Record as a **PLAN-GAP** for the lead (don't build anything for it): any other local file Claude writes with
     its own file tools (a `.txt`, `.md`, `.csv`, a PDF) is attached by name, size, path and sha256 as design
     section 5 says, so text Claude wrote can still travel in an attachment the owner doesn't read in the prompt.
     Closing that needs a design decision (for example showing text-like attachments in full, or showing each local
     file's modification time in the approval).
   - Test: save a marked draft and a Bcc-bearing Sent copy as `.eml` with `mail_attachment_save`, then try to attach
     each through the real proxy import path; both are refused, also when renamed to `.txt` and when given a
     leading BOM or blank line. An ordinary PDF and an ordinary text file still attach.

3. **REVIEW-2 finding 3 (should-fix): the password scrubber never rewrites typed evidence.** `Engine.stage` scrubs
   stage names and outcomes with `transport.scrub`, so a password equal to (or contained in) `accepted:250`, a hash
   or an id corrupts the evidence repair depends on.
   - Keep typed evidence exact: stage keys, outcome codes (`accepted:250`, `refused:550`, `done`, …), hashes, ids,
     Message-IDs and recipient addresses are never scrubbed. Make stage outcomes come from a controlled vocabulary
     the service writes, so no server text can reach them. Scrub only free-text diagnostic fields, and keep finding
     3's guarantee that the password and its `AUTH` encodings never reach a result, the act socket, the SQLite log,
     the independent record or a log.
   - Test: an account whose password is `accepted:250`, and one whose password is a substring of a stored composition
     hash; a send succeeds, its stages read `accepted:250` exactly, a failed Sent stage is repaired, and the
     password-echo tests from round 1 still pass.

Then update `reviews/19-mail/REPORT.md`: add a short "Review fixes, round 2" section naming each finding, what
changed and the test that proves it; the new JUDGMENT-CALL and PLAN-GAP above; and the final head's run IDs. Keep
claims marked **run**, **read** or **assumed**.

## Out of scope

Everything outside these three findings, including a fresh hunt for other issues. Don't edit
`reviews/19-mail/REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and `control/tests/`.

## Acceptance

- Each finding has a regression test that would fail on `300cd06` and passes now; the report names it.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Take the option that keeps a mail from being sent twice, sent without its approval or differently from what the
approval showed, or deleted without being named, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Commit in small steps and push this branch; draft PR #9 already exists, so don't open another.
  Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 6 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same careful protocol work, on code it wrote.
