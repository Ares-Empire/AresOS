# 19-review-fixes-6: drafts stay in Drafts, and `\Draft` marks a draft everywhere

**Goal:** close `reviews/19-mail/REVIEW-6.md` (review of head `614c0e0a`): an unmarked draft, one the owner's mail
program wrote, must not lose its draft protection by being moved or copied out of Drafts, and a draft his mail
program left in another folder is recognised by its IMAP `\Draft` flag. Approved by the lead on 2026-11-07. Briefs 19
and `19-review-fixes` to `-5` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule
decides.

Read `reviews/19-mail/REVIEW-6.md` first, then this brief, then `control/aresos_control/mail/adapter.py` (`authored`,
the `move`/`copy`/`flag` path and `safe_folder`).

## What to build

1. **Drafts stay in Drafts.** `mail_move` and `mail_copy` refuse to take any message (marked, flagged `\Draft` or
   neither) out of the SPECIAL-USE Drafts folder or its subfolders, before anything changes on the server. The
   refusal names the alternatives: send it with `mail_compose` `mode=draft`, or delete it with `mail_delete` (which
   asks the owner). Moving or copying into Drafts stays allowed. `mail_delete` to Trash keeps working for drafts.

2. **The IMAP `\Draft` flag marks a draft everywhere.** A message carrying `\Draft`, in any folder, is a draft
   exactly like a message with the `X-AresOS-Authored` marker or one in Drafts: it can't be attached, forwarded as an
   attachment, or nested at any depth inside an attachment, and its text reached inline, by quoting or by
   `mode=draft` is shown whole or refused as too large (rounds 1 and 5). Read the flag fresh from the server for the
   exact reference right before the decision, with the same stale-reference rules as other reads, and still never
   change flags while reading. `mail_flag` keeps refusing to add or remove `\Draft`; pin that with a test.

3. **Tests**, through the real adapter path against the container servers:
   - REVIEW-6's exact scenario as a regression: an unmarked owner draft in Drafts, then `mail_move` and `mail_copy`
     to an ordinary folder are refused, and the message stays where it was (checked on the server).
   - For a draft in Drafts: attaching its `source`, attaching a part of it, and forwarding it as an attachment are
     refused, each with the alternatives named.
   - A `\Draft`-flagged message without the marker in INBOX and in Archive: the same three attach paths are refused;
     an inline forward and a reply show its text in full; moving it between ordinary folders keeps the flag and the
     refusal.
   - Moving and copying an ordinary message into Drafts still works. Removing or adding `\Draft` with `mail_flag` is
     refused. Every earlier test keeps passing unchanged.

4. **Docs and report.**
   - Update the draft rules in the generated tool descriptions (`mail_move`, `mail_copy`, `mail_compose` and
     wherever drafts are explained), regenerate `docs/control/TOOLS.md` with `python3 control/generate.py`.
   - Add a short "Review fixes, round 6" section to `reviews/19-mail/REPORT.md`: REVIEW-6's finding, what changed,
     the tests that prove it by name.
   - In the round-5 section, record the "conflicting test instructions" item as **resolved** by the new rules
     (rounds 5 and 6 replace "shown in full inside an attachment" with "refused as an attachment"), not as an open
     PLAN-GAP.
   - Add a section **"For the owner: decisions before merge"** near the top of `REPORT.md`, in plain words for
     someone who doesn't read code: every JUDGMENT-CALL and every PLAN-GAP still open across all rounds, each as one
     or two sentences saying what he will notice when using mail, what was chosen and the alternative. Also list
     what still needs his own check with the real account (onboarding, how approvals look on the terminal and phone,
     how recipients' programs show a forwarded `.eml`). Put the same list in the PR body.
   - Run IDs as in rounds 4 and 5: in `REPORT.md`, the runs of the last commit that changes code or tests (both
     workflows, both passes) and the statement that any later commit changes only files under `reviews/`; in the PR
     body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and the deferred class of ordinary local files Claude
writes itself. Don't edit `reviews/19-mail/REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`,
`docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`,
`docs/control/FEATURES.md`, and `control/tests/`.

## Acceptance

- Each point has regression tests that would fail on `614c0e0a` (or are new behavior) and pass now; the report names
  them. No earlier test is weakened, skipped or deleted.
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
- Keep it to about 8 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a small rule change with server-side tests, on code it wrote.
