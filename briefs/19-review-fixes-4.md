# 19-review-fixes-4: attached mail rebuilt, an independent final check, byte-exact binaries

**Goal:** close `reviews/19-mail/REVIEW-4.md` (review of head `1aaa8ff`) by changing how attached mail is built,
not by patching detection again. Three rounds removed Bcc from copied header blocks and each review found a new
edge; this round makes a leak impossible by construction and adds a check that doesn't depend on the builder.
Forward as attachment stays: it is a *first* feature. Approved by the lead on 2026-11-07. Briefs 19 and
`19-review-fixes` to `-3` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule
decides.

Read `reviews/19-mail/REVIEW-4.md` first, then this brief, then `control/aresos_control/mail/codec.py`,
`guard.py` and the compose path in `adapter.py`.

## What to build

1. **Attached mail is rebuilt from an allowlist.** Every mail that goes out as an attachment (forward as attachment,
   an explicit `{reference, part: "source"}`, a `message/rfc822` or `message/global` part, a child of a
   `multipart/digest` without its own Content-Type, which is an implicit `message/rfc822`, and any nested message
   inside these) is built anew by the service. Never copy the original header block.
   - The message's top-level headers come only from this list: `From`, `Sender`, `Reply-To`, `To`, `Cc`, `Date`,
     `Subject`, `Message-ID`, `In-Reply-To`, `References`, `MIME-Version`. Each MIME part's headers come only from:
     `Content-Type`, `Content-Transfer-Encoding`, `Content-Disposition`, `Content-ID`, `Content-Description`,
     `Content-Language`. `Bcc`, `Resent-*`, the `X-AresOS-Authored` marker and anything else not listed can't
     survive.
   - Nested messages (explicit or implicit, at any depth) are rebuilt the same way, recursively. A structure you
     can't rebuild exactly (a broken encoding, a parse defect, too deep or too large) is refused with a clear reason,
     never passed through.
   - Dropping the marker must not drop its rule: decide authored provenance on the **original** before rebuilding,
     and text from a marked or Drafts source is still shown in full in the approval, or refused as too large
     (round 1).
   - The approval says the attached mail was rebuilt with only the listed headers and gives the hash of the bytes
     actually sent. Update the report's "exact attached mail bytes" JUDGMENT-CALL to match.
   - `mail_read` and `mail_attachment_save` keep returning the original bytes to the owner.

2. **An independent final check before DATA.** A separate module that imports nothing from `codec.py` (no shared
   detector or parser helper), run on the built MIME at compose and again on the exact bytes right before SMTP
   `DATA`. It:
   - decodes every part at every level: each transfer encoding (base64, quoted-printable, 7bit, 8bit, binary),
     multipart children, implicit digest children, nested `message/rfc822` and `message/global`, and the decoded
     bytes of every leaf, parsed again as a possible MIME entity and walked into, whatever the part claims to be,
     within a depth and size bound (beyond the bound: refuse);
   - refuses on any line, in any decoded content at any level, that matches a `Bcc:` or `Resent-Bcc:` header (case
     and whitespace before the colon don't matter) or the `X-AresOS-Authored` marker, unless that marked text is
     shown in full in this approval. A false positive, such as a text file that really contains a line starting with
     `Bcc:`, is refused with a clear reason that says so; that is accepted;
   - when it refuses before DATA, the operation ends `failed` with nothing sent, and a replay never submits.
   Header-block parsing everywhere (this check, `codec.is_mail` and the local-file refusal from round 2) stops only
   at a truly empty line. A line of spaces or tabs is not the end of the headers.

3. **Binary parts are byte-exact.** Keep each leaf's original decoded payload and never re-serialize it with CRLF
   line ends or any other change. The outgoing transfer encoding may differ (binary becomes base64 for SMTP), but
   the decoded bytes the recipient gets are identical. Fixtures: raw received messages with a PDF and a PNG whose
   bytes contain LF and bare CR, once with `Content-Transfer-Encoding: binary` and once with base64; forward each
   as an attachment and inline, and attach its parts explicitly; after sending, the received decoded bytes are
   asserted equal to the originals, byte for byte.

4. **Regressions through the real path.** REVIEW-4's three cases, each through compose, prepare and submission to
   the SMTP sink, checking the received mail fully decoded:
   - a Bcc-bearing saved Sent mail with `X_Custom: value` followed by a whitespace-only line, renamed `.txt`,
     through the real proxy import: refused;
   - a `multipart/digest` (also named `inner.txt`) whose child has no Content-Type and holds `Bcc`/`Resent-Bcc`
     (with and without `From`): rebuilt without them, or refused;
   - the binary-encoding PDF and PNG from point 3: byte-equal.
   Plus a test that feeds the final check a hand-built message that bypasses the builder (base64-encoded nested
   `Bcc`, an implicit digest child with `Bcc`, a marked part not shown in the approval) and checks that compose
   refuses and that send ends `failed` without `DATA`. All earlier rounds' review tests keep passing unchanged.

5. **Local attachments show when they last changed.** For the local-file PLAN-GAP, for now: the approval shows each
   caller-imported attachment's last change time next to its path, name, size and sha256. Take it on the caller
   side when the proxy reads the file, as the later of its modification time and its status-change time (`ctime`),
   because `touch` can backdate a modification time but not `ctime`. Show it in the owner's local time with the
   zone. Record this as a **JUDGMENT-CALL**: it is a hint, not proof of who wrote the file; whether files Claude
   wrote itself should show their text is an owner question the lead takes to him at merge. Test it through the
   real proxy path.

6. **Report.** Add a short "Review fixes, round 4" section to `reviews/19-mail/REPORT.md`: each REVIEW-4 finding,
   what changed, the tests that prove it (by name), the new and updated JUDGMENT-CALLs. Put the final run IDs in
   `REPORT.md` as well as in the PR body: in the report, the runs (both workflows, both passes) of the last commit
   that changes code or tests, and say that any later commit changes only `REPORT.md`; the PR body lists the runs
   on the final head. Keep claims marked **run**, **read** or **assumed**.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md`. The same paths
as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`,
`docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, and `control/tests/`.

## Acceptance

- Each point above has regression tests that would fail on `1aaa8ff` (or are new behavior) and pass now; the report
  names them. No earlier test is weakened, skipped or deleted.
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

**Model:** `gpt-6.1-sol`, xhigh: a structural change to code it wrote, with byte-level tests.
