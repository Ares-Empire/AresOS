# 19-review-fixes-8: Junk and Archive are optional roles

**Goal:** round 7 made every account need all five SPECIAL-USE roles (Sent, Drafts, Trash, Junk, Archive), each on
exactly one selectable folder, and refuses every change otherwise. If the owner's server doesn't mark Junk or
Archive, onboarding fails and his mail tools stop working. Only Sent, Drafts and Trash carry safety rules. Make Junk
and Archive optional without weakening anything round 7 protects. Approved by the lead on 2026-11-07. Briefs 19 and
`19-review-fixes` to `-7` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule
decides.

Read `briefs/19-review-fixes-7.md`, the "Review fixes, round 7" section of `reviews/19-mail/REPORT.md`, then
`control/aresos_control/mail/roles.py`, `onboarding.py` and the role checks in `adapter.py`.

## What to build

1. **Required roles:** Sent, Drafts and Trash must each be present on exactly one selectable folder, at onboarding,
   in the owner's `account_folders` step and in the fresh check before every change (round 7). Anything else refuses
   as today, naming the owner's setup step.

2. **Optional roles:** Junk and Archive may be missing. Onboarding and `account_folders` record each as present (with
   its folder) or absent.
   - When one is missing, only the actions that need it refuse, with a clear reason that names the missing role and
     says the owner can mark that folder in his mail server's settings and then run the setup step; everything else
     works.
   - A duplicated optional role (two folders), or one that changed since it was recorded (moved to another folder,
     appeared or disappeared), refuses the actions it affects: any change whose source or target is a folder that
     holds that role now or held it when recorded, until the owner runs the setup step. Other actions keep working.
   - Reads never refuse because of an optional role. Search and thread defaults leave out every folder that holds the
     Junk role now or held it when recorded, as they leave out Trash.
   - `mail_accounts` shows for each optional role whether it is present, absent or needs the owner's setup step, so
     Claude sees it before an action fails. Update the tool descriptions and regenerate `docs/control/TOOLS.md`.

3. **Unchanged:** round 7's Trash and Drafts protection (a folder that holds the role now or held it at onboarding),
   the draft rules of rounds 5 to 7, and everything else.

4. **Tests**, against the container servers:
   - An account whose server marks no Junk and no Archive onboards. Its moves between ordinary folders, `mail_delete`
     to Trash and for good, a send with the Sent copy and answered flag, and saving and sending a draft all work. A
     move "to junk" or "to archive" refuses with the clear reason.
   - Two folders marked `\Archive`: moves into or out of either refuse; moves between ordinary folders, deletes,
     sends and drafts still work. The same for a changed `\Archive` (moved to another folder after recording).
   - The existing Trash and Drafts protection tests pass unchanged; a missing or duplicated `\Trash`, `\Drafts` or
     `\Sent` still refuses as in round 7.
   - Earlier tests change only where the new rule forces it; name each change in the report and keep its assertions.

5. **Report.** Add a short "Review fixes, round 8" section to `reviews/19-mail/REPORT.md`: what changed and the tests
   that prove it, by name. Replace round 7's "conservative role refresh" JUDGMENT-CALL with the new rule, in plain
   words. Update "For the owner: decisions before merge" in `REPORT.md` and the PR body to match. Run IDs as in
   rounds 6 and 7: in `REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both
   passes) and the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on
   the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and `control/tests/`.

## Acceptance

- Each point has regression tests that would fail on `8e0c7bdd` (or are new behavior) and pass now; the report names
  them. No earlier test is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse the affected action, not the whole account. Take the option that keeps a mail from being sent twice, sent
without its approval or differently from what the approval showed, or deleted without being named, and say so in the
report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Commit in small steps and push this branch; draft PR #9 already exists, so don't open another.
  Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 8 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a contained rule change with server-side tests, on code it wrote.
