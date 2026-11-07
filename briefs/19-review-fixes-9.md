# 19-review-fixes-9: undo after a role race, per-root separators, export-only blob downloads

**Goal:** close the three blocking and two should-fix findings of the security re-review of head `5b0a0fb7`,
`reviews/19-mail/SECURITY-REVIEW-2.md` (read it first). It confirms that the original findings 3 and 5 are closed.
Approved by the lead on 2026-11-07. Briefs 19 and `19-review-fixes` to `-8` still apply where this brief doesn't
change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **Role race: check after the action, and undo** (re-review finding 1). Another LIST right before the `MOVE` only
   narrows the window. Keep the checks before the action, and add one after it:
   - After every `UID MOVE` and `UID COPY` done by `mail_move` or `mail_copy`, read the SPECIAL-USE roles again. If
     the target now holds a protected role (Trash, Drafts, or an optional role whose rules forbid the change), or any
     role changed during the action, undo it: for a move, `UID MOVE` the messages back to the exact source folder
     using the new UIDs from the server's `COPYUID` answer; for a copy, `UID EXPUNGE` exactly the copies just made.
     Then return `refused` with "special folders changed during the move; the messages were returned" (or "the
     copies were removed").
   - If the undo itself fails or can't be exact (no `COPYUID` in the answer, the source gone, a message no longer
     where it should be), the result is `partial` and names exactly where each message is now (folder and UID). It
     never ends `done`.
   - The undo needs `UIDPLUS`: on a server without it, `mail_move` and `mail_copy` refuse up front with a clear reason.
   - Write the intended move or copy (source, target, UIDs) to the audit log before acting and the outcome after, so
     a crash in between leaves a visible unfinished entry. Nothing is undone or retried automatically after a restart.
   - Tests, with a scripted IMAP frontend that reassigns a role at the chosen moment: the role is reassigned between
     the final check and the `MOVE`, and between the `COPY` and the post-check, for Trash, for Drafts and for an
     optional role (Archive); each ends `refused` with the messages back at their exact source (checked on the
     server) or the copies removed. A failing undo ends `partial` naming the messages' location. Ordinary moves and
     copies with stable roles still end `done`.

2. **Each protected root keeps its own separator** (re-review finding 2). Store, compare and apply the hierarchy
   separator of each protected root (Sent, Drafts, Trash, and the optional roles) as the server lists it for that
   folder, never INBOX's, including roots remembered from onboarding after the owner's setup step. Every "is this
   folder inside Drafts or Trash" decision uses that root's separator.
   - Test the re-review's exact case, with a scripted IMAP frontend or a Dovecot namespace configuration: INBOX uses
     `/`, Trash and Drafts use `.`; a `mail_move` into `Trash.Child` is refused as a free move (only `mail_delete`
     reaches it), and an unmarked, unflagged owner draft in `Drafts.Child` is a draft: `mail_attachment_save` of any
     part refuses, attaching or forwarding it as an attachment refuses, and moving it out refuses.

3. **Only export blobs can be downloaded** (re-review finding 3), at the base level. Every blob in the shared store
   records its origin. Blobs the service makes for its own use (composition parts, draft bodies, rebuilt mails, quoted
   parts, wire copies) can't be downloaded by any `file_save` of any app. Only blobs made for export to the owner (for
   example the result of `mail_attachment_save` for a non-draft mail, or an app's own explicit export) can, and
   attaching by blob hash keeps accepting only caller-imported blobs.
   - Take `testapp` out of the shipped `control/settings/managed-mcp.json`; it is a test fixture, so it stays only in
     test configurations. Keep the generated artifacts and the base suite consistent with that, and say in the report
     which base files changed and why.
   - Test the re-review's exact route: compose and save a long draft, compose it with `mode=draft`, take
     `generated_parts[0].sha256`, call `testapp`'s `file_save` (in a test configuration) for it as `notes.txt`:
     refused, no file written, nothing reaches the SMTP sink. Also: no internal blob kind can be downloaded; an
     ordinary `mail_attachment_save` still saves byte for byte.

4. **Should-fix findings.**
   - `mail_operation_status` always returns the recorded operation, its approval and its stages; live evidence
     problems (for example changed special folders) go in a separate `evidence_error` field instead of replacing the
     result. Test it with Trash's role removed after a send.
   - Subjects and display names are normalised before the approval is built, the same way serialization and the
     final check will read them back (at least surrounding whitespace), so the approved value equals what the final
     check decodes. `" invoice"` composes and sends as `invoice`, shown so in the approval. Test leading and trailing
     spaces and tabs, and a long folded subject.

5. **Report.** Link `reviews/19-mail/SECURITY-REVIEW-2.md` from `REPORT.md` next to the other review files. Add a
   short "Review fixes, round 9" section: each finding, what changed, the tests that prove it by name, the base files
   changed and why. Add to "For the owner: decisions before merge", in plain words, this stopping rule from the lead:
   Claude can always write a file itself and attach it, and the approval then shows only its name, size and change
   time; that is the open owner question about Claude-written files. So any further finding of the kind "text Claude
   wrote reaches an attachment by a new route" is settled by the owner's answer on how attachments are shown, not by
   another fix round; blocking findings of any other kind still count. Update the PR body to match. Run IDs as in
   rounds 6 to 8: in `REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both passes)
   and the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on the final
   head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`.
`control/tests/` (brief 18's tests) changes only where removing `testapp` from the shipped settings or the blob
origin rule forces it; name each such change in the report and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `5b0a0fb7` (or are new behavior) and pass now; the report names
  them. No earlier test is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse. Take the option that keeps a mail from being sent twice, sent without its approval or differently from what
the approval showed, or moved into Trash or out of Drafts without approval, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Commit in small steps and push this branch; draft PR #9 already exists, so don't open another.
  Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 10 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: protocol race handling and a base-level store change with server-side tests.
