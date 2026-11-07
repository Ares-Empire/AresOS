# 19-review-fixes-11: the owner's filing notice is always deliverable

**Goal:** close security re-review 4 (`reviews/19-mail/SECURITY-REVIEW-4.md`, head `410cb8e8`; read it first). The
round-10 undo findings are closed and no new destructive bypass was found. Left: the persistent filing notice repeats
the whole location report, so a large move makes the notice, `aresos log`, `control_pending` and every Mail result too
large to deliver; and notices skip the display escaping. Approved by the lead on 2026-11-07. Briefs 19 and
`19-review-fixes` to `-10` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule
decides.

## What to build

1. **A notice is short and fixed-size; locations are paged** (blocking).
   - A filing notice, as repeated in every following result and in `aresos log`, holds only: the plain-words sentence
     from round 10, the filing operation id, the number of affected messages, and the names of the folders involved
     (at most a small fixed number of names, each bounded in length and escaped, with "and N more" when there are
     more). It never contains per-message locations.
   - The immediate result of the `mail_move` or `mail_copy` that hit the race is bounded the same way: the warning, the
     filing id, the counts, and at most the first bounded page of locations with a cursor.
   - Exact per-message locations (folder, UIDVALIDITY, UID, and whatever round 10 records per message) come from a
     separate paged read: `mail_operation_status` with a cursor, or a new read action such as `mail_filing_locations`.
     Each page is bounded well below the result limit, the cursor is bound to the filing id, and every location is
     reachable by following the pages. Whichever you choose, document it in the tool descriptions and regenerate the
     artifacts.
   - The notices section of any result is bounded too: if many notices are unacknowledged, show the newest few in full
     and a count of the rest, with where to read them. No notice section, and no result, can exceed the response
     limit because of filing locations or the number of notices.
   - Tests, through the real adapter path: the re-review's 20-message case with long Message-IDs and its 4,000-message
     case. In both, the immediate result and the notice arrive within the limit, `aresos log`, `control_pending` and
     Mail reads keep working, and following the pages returns every location exactly once. Plus many unacknowledged
     notices at once.

2. **Notices are escaped like audit entries** (should-fix). Returned notices go through the same display escaping as
   the audit log (bidi and control characters escaped), while the exact internal references stay stored unescaped for
   the service's own use. Test with the re-review's encoded Message-ID containing a right-to-left override: escaped in
   `control_log` notices, `control_pending`, Mail results and the location pages.

3. **Report.** Link `reviews/19-mail/SECURITY-REVIEW-4.md` from `REPORT.md` next to the other review files. Add a short
   "Review fixes, round 11" section: each finding, what changed, the tests that prove it by name. Update the round-10
   owner bullet in "For the owner: decisions before merge" and the PR body if what the owner sees changes (a short
   warning; exact locations on request). Run IDs as before: in `REPORT.md`, the runs of the last commit that changes
   code or tests (both workflows, both passes) and the statement that any later commit changes only files under
   `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and brief 18b's boundary workflow (its intermittent vsock
failure is the lead's). Don't edit `reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same
paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`,
`docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, `control/tests/`, and the workflow files under
`.github/`. Brief 18's `engine.py` changes only as far as the bounded, escaped notices need; say why in the report.

## Acceptance

- Each point has regression tests that would fail on `410cb8e8` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted; an expectation that changes because notices no longer carry locations is named in
  the report and keeps its other assertions.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Keep the warning short and deliverable and put detail behind a paged read. Never drop a notice, never move or delete
mail to make a result smaller.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Every push to the PR starts the Mail,
  base and boundary workflows. Before each push, run locally everything that doesn't need containers (Docker isn't
  available on this Mac): `python3 control/generate.py --check`, a syntax check of every `control/**/*.py`, and the
  plain-Python test classes (`unittest.TestCase` subclasses that need no mail server, including your new ones where
  they can run that way). Batch your commits into as few pushes as you can, ideally one for the code and tests and one
  for the report. For the second pass on the final head, rerun the same run with `gh run rerun <id>`; never push again
  just to get another run. Keep it to about 6 workflow runs in all.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: bounded results and paging on code it wrote.
