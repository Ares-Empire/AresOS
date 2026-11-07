# 19-review-fixes-3: third and last round of review fixes

**Goal:** close the two findings in `reviews/19-mail/REVIEW-3.md` (fix review of head `5180db3`) so that no
outgoing mail can carry a `Bcc`/`Resent-Bcc` header or undisclosed service-built (Claude-authored) text in any
attachment, however it is encoded or nested. This is the last fix round, so close the class, not only the two
reproductions. Nothing else changes. Briefs 19, `19-review-fixes` and `19-review-fixes-2` still apply; where in doubt,
their "If unsure" rule decides.

Read `reviews/19-mail/REVIEW-3.md` first, then this brief, then `control/aresos_control/mail/codec.py`
(`is_mail`, `approval_texts`, `without_bcc`) and the compose path in `adapter.py`.

## What to fix

1. **REVIEW-3 finding 1 (blocking): mail detection follows the real header syntax.** `codec.is_mail` accepts only
   `[A-Za-z0-9-]+` header names and gives up at the first line it doesn't recognise, so one header such as
   `X_Custom:` makes a saved mail look like an ordinary file.
   - Accept any RFC 5322 field name (printable ASCII 33–126 except `:`), with or without space before the colon.
   - Don't stop at a line that isn't a header: scan the whole leading block up to the first empty line (and an
     mbox `From ` line at the top), and decide by whether that block holds a `From:` line and one identifying header
     (`Date`, `Subject`, `Message-ID`, `Received`, `MIME-Version`, `Bcc`, `Resent-Bcc`, or the service's
     `X-AresOS-Authored` marker). A wrong guess must refuse a file, never let a mail through.
   - Tests: export a marked draft and a Bcc-bearing Sent copy, add headers with punctuation (`X_Custom:`, `X.Y:`,
     `X!:`), a malformed line in the header block, and an mbox `From ` line; rename to `.txt`; each import is
     refused through the real proxy path. An ordinary text file and a PDF still attach.

2. **REVIEW-3 finding 2 (blocking): encoded and nested messages are decoded before they are checked.**
   `without_bcc` and `approval_texts` trust the parser's tree and only decode leaf parts, so a `message/rfc822` or
   `message/global` part sent with base64 or quoted-printable keeps its `Bcc`, `Resent-Bcc` and authored text.
   - Before sanitizing and before the provenance/disclosure check, decode the transfer encoding of every
     `message/*` part and of every part whose decoded bytes are a mail (by the detector above), parse it as a mail
     and recurse, at any depth. Re-emit the sanitized message so the bytes that go out are the bytes approved. Where
     a part can't be decoded and re-emitted exactly (an unknown or broken transfer encoding, a multipart declared
     with base64 or quoted-printable, a parse defect inside a nested header block), refuse the composition with a
     clear reason instead of sending it unchecked.
   - **Final guard, independent of the sanitizer:** after the outgoing MIME of a composition is built, and again
     right before SMTP submission on the exact bytes to be sent, walk it the way a recipient's mail program would:
     decode every transfer encoding at every level, treat every part whose decoded bytes are a mail as a mail and
     walk into it. Refuse (compose) or stop without submitting (send, recorded as `failed`, nothing left) if any
     `Bcc` or `Resent-Bcc` header appears anywhere, or if any part carries the `X-AresOS-Authored` marker whose text
     is not shown in full in the approval. The guard must not reuse the sanitizer's code path for deciding what to
     check.
   - Tests: a Bcc-bearing message attached as `message/rfc822` and as `message/global` with base64 and with
     quoted-printable, nested two levels deep, in new, reply, reply-all, both forward styles and draft modes; a
     marked draft inside such an encoded part. Each is either sanitized and disclosed (and the received mail, fully
     decoded at every level, has no Bcc address and no undisclosed marked text) or refused. One test feeds the final
     guard a hand-built MIME message with a base64-encoded nested `Bcc` that bypasses the sanitizer, and checks that
     compose refuses and that send stops without an SMTP `DATA`.

Then update `reviews/19-mail/REPORT.md`: add a short "Review fixes, round 3" section naming each finding, what
changed, the final guard, and the tests that prove it (by name); and the final head's run IDs. Keep claims marked
**run**, **read** or **assumed**.

## Out of scope

Everything outside these two findings and the final guard, including a fresh hunt for other issues and the
deliberately deferred class of ordinary local files Claude writes itself (the PLAN-GAP already in the report).
Don't edit `reviews/19-mail/REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and `control/tests/`.

## Acceptance

- Each finding and the final guard have regression tests that would fail on `5180db3` and pass now; the report
  names them.
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
- Keep it to about 6 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same careful protocol work, on code it wrote.
