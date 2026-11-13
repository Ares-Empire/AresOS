# 19-review-fixes-15b: folder renames may move between parents, under the filing policy

**Goal:** an owner correction to round 15, point 2 (2026-11-08). The owner wants Claude to keep moving folders
between parents; refusing that is impractical for him. Remove round 15's same-parent restriction on
`mail_folder_rename` and take the security review's named alternative instead: extend the owner-reviewed filing
policy (rounds 10 and 11) to folder renames and moves. Everything else from round 15 stays as it is. Approved by the
lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-15` still apply where this brief doesn't change them; where
in doubt, their "If unsure" rule decides.

Read `reviews/19-mail/SECURITY-REVIEW-7.md` finding 2, `briefs/19-review-fixes-15.md` point 2, then
`control/aresos_control/mail/adapter.py` (`folder_rename`) and `control/aresos_control/mail/filing.py`.

## What to build

1. **Cross-parent renames work again, with a post-check and a warning.**
   - `mail_folder_rename` accepts a new name under a different parent again (as before round 15). Keep the existing
     checks before the action (special folders and their descendants can't be renamed, no folder may be renamed into
     Trash, Drafts or a protected role's subtree, fresh roles as in round 7).
   - Record a durable intent (the folder, its message count, the new name and the roles seen) before `RENAME`, the
     same way filing intents are recorded, so a crash in between leaves a visible unfinished entry.
   - After `RENAME`, `LIST` the new location and read the roles again. If the renamed folder or any of its ancestors
     now carries a protected role (Trash, Drafts, or an optional role whose rules forbid the change), nothing is
     renamed back and nothing is deleted. The result is `partial` (never `done`) with the plain-words warning ("The
     special folders changed while Claude was moving this folder. Nothing was deleted. It is now <folder>, inside
     <role>. Check it in your mail program."), and the same bounded notice goes through the existing filing-notice
     path: folder name (bounded and escaped), how many messages, repeated in later Mail results and `aresos log` until
     acknowledged, listed by `mail_filing_notices`, acknowledged with `mail_notice_ack`. Round 15's warning for a role
     the server assigns by name after the rename stays and uses this same path.
   - Update the `mail_folder_rename` description and regenerate the artifacts.

2. **Tests**, through the real adapter path with the scripted IMAP frontend:
   - The security review's race: `Source` (three messages) renamed to `Parent/Subfolder`, with `Parent` reassigned as
     `\Trash` between the final check and `RENAME`: the result is `partial` with the warning, a durable record exists,
     `mail_filing_notices` lists it, the warning repeats in a following Mail result and in `control_log`, the three
     messages are still there (checked on the server), and nothing was renamed back.
   - An ordinary cross-parent move (no role change) succeeds with `done` and no warning.
   - A rename within the same parent still works; round 15's rename tests change only where they expected the
     cross-parent refusal (name each such change in the report and keep the other assertions).

3. **Report.** In the round-15 section of `reviews/19-mail/REPORT.md`, replace the same-parent rule with this one and
   name the tests. In "For the owner: decisions before merge", fold folder moves into the existing filing bullet (no
   separate rename choice): moves of messages and folders both stay where they landed and warn if the special folders
   changed meanwhile. Update the PR body to match. Run IDs as before.

4. **Record the owner's answers (no code change).** The owner answered Mail's judgment calls on 2026-11-08, in the
   lead's session: "Agree on 8, names etc are enough. Agree on everything else too." In "For the owner: decisions
   before merge" of `REPORT.md` and in the PR body:
   - Mark every listed JUDGMENT-CALL and PLAN-GAP bullet as decided by the owner on 2026-11-08 and kept as built:
     draft revisions, draft protection, no draft attachment save, required and optional special folders, forwarded mail
     as `.eml`, saved `.eml` refused, strict refusals, size limits, Sent setup, folder deletion, repair after
     uncertainty, approval prompt (question first), filing notices (now including folder moves, point 1) and the
     control-character refusal.
   - Ordinary local files: settled. Attachments show path, name, size, hash and change time, not their text, and text
     Claude wrote may travel in attachments. The lead's stopping rule is therefore closed: findings that Claude-written
     text reaches an attachment are accepted behaviour, not a should-fix. Say so where the stopping rule is described.
   - Keep the "needs your own check with the real account" list as it is: those are the owner's checks after merge.

## Out of scope

Everything else in round 15 stays as sent; no fresh hunt. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`.

## Acceptance

- The race test would fail on round 15's head with the cross-parent refusal removed and no post-check, and passes
  now; the report names it. No other earlier test is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Leave the folder where it landed and tell the owner. Never rename back, never delete to recover.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Before each push, run locally:
  `python3 control/generate.py --check`,
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest
  test_operations test_record test_crashes test_approval_questions test_strict_json`, plus any new plain-Python tests.
  Aim for one push with code, tests and report together. For the second pass on the final head, rerun the same run
  with `gh run rerun <id>`; never push again just to get another run. Keep it to about 4 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a contained change on the filing path it built.
