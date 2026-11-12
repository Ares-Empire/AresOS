# 19-review-fixes-29: the warning lifecycle (check, occurrence, acknowledgement, resolution) in Mail

**Goal:** close security review 21 (`reviews/19-mail/SECURITY-REVIEW-21.md`, head `0ba7870e`; read it first), judged
against the lead's refined disk bar (round 25). Round 28's own fixes held (refused reopening skips the read, archive
keeps late duplicates, a clean send archives, MOVE/COPY recovery reports observable drift), and there is no bypass.
Both blocking findings come from one gap: the warning lifecycle isn't defined, so acknowledgement, check state and
ordering get mixed up. Package 19b's brief defines it (`git show origin/main:briefs/19b-owner-state.md`, section
"Warning lifecycle"). **This round builds that section only into Mail**: not 19b's committed projection, not its oracle,
not R1–R3 in general. Approved by the lead on 2026-11-09. Briefs 19 and `19-review-fixes` to `-28` still apply where
this brief doesn't change them; where in doubt, their "If unsure" rule decides.

## The lifecycle (lead decision, round 29; record it in `REPORT.md` as the lead's)

Four separate things, each committed:

- **Check:** open, clean or warning (round 27).
- **Warning occurrence:** an id, the operation, the check kind and an **evidence fingerprint** (for duplicates the set
  of matching Sent copies; for filing the destination and its role; for scans the locations found). Reading the same
  evidence again matches the existing occurrence and keeps its id, timestamp, order and acknowledgement, across reads,
  pages and restarts. A new occurrence starts only when the fingerprint changes, or when the warning comes back after a
  committed clean result. A later clean check never erases an unacknowledged occurrence.
- **Acknowledgement:** per occurrence, through the existing acknowledgement action. It never closes a check.
- **Action resolution:** the operation's own end (done, failed, expired, cancelled, settled), independent of its
  warnings.

An occurrence leaves the owner-visible set only when acknowledged. It neither disappears early nor comes back after
acknowledgement, through rollback, archive, expiry, restore or restart.

## What to build

1. **An open check stays discoverable and is never expired or archived, whatever is acknowledged** (review finding 1;
   `recovery.py` around line 31, `retention.py` around line 96).
   - Recovery and the pending view find open checks by their check state, not by `started`, so a source that is
     `partial` with `check_open=True` stays listed (as "not yet checked" until its evidence can be read).
   - Retention, expiry and archive skip any source with an open check or an unacknowledged occurrence.
   - Test the review's sequence: RENAME succeeds, its result write is refused, restart with IMAP down, acknowledge the
     recovery warning, 24 hours pass, IMAP returns. The check is still listed, its evidence read runs, and the Trash
     drift warning appears as a new occurrence.

2. **Stable occurrences, and pagination that can't silently drop a warning** (review finding 2; `mail/filing.py`
   around line 202).
   - A recheck with an unchanged fingerprint changes nothing: no new timestamp, no reset acknowledgement, no reorder.
   - Pages are ordered by occurrence creation (then id). The cursor binds to the ordering it was issued for. If the set
     changed underneath it, the next page says so and restarts from the first page; it never returns `items=[]` with
     `total>0`.
   - Test the review's case: four interrupted RENAME checks with Drafts unresolved and the Trash drift on the oldest.
     Paging reaches all four, and acknowledging three keeps them acknowledged after rechecks.
   - Generic tests: unchanged evidence read many times keeps one occurrence id; changed evidence after an
     acknowledgement starts a new occurrence; clean followed by recurrence starts a new occurrence; a clean check after
     a warning keeps the unacknowledged occurrence; an acknowledged occurrence doesn't come back after archive, expiry,
     restore or restart.

3. **Every catalogue that pages warnings** (`mail_filing_notices`, `control_pending`, duplicate warnings, `aresos log`,
   and any other the code has) uses the same stable ordering and cursor rule, through one shared helper. List them in
   `REPORT.md` with their tests.

4. **Stop condition.** If this needs 19b's larger pieces (a new committed projection of owner state, the rebuilt
   oracle), stop: write in `REPORT.md` what and roughly how big, commit and push that note, and end the run with it as
   your final message. Don't build it. Adding occurrence records, fingerprints and per-occurrence acknowledgement to the
   existing stores is in scope and doesn't trigger the stop.

5. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-21.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 29" section: the lead's lifecycle decision, each finding, what changed, the catalogue list (point
   3), the files changed and why, the tests by name. Run IDs as before: in `REPORT.md`, the runs of the last commit that
   changes code or tests (all workflows, both passes) and the statement that any later commit changes only files under
   `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including 19b's projection, oracle and R1–R3, and a fresh hunt for other issues. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, `briefs/19b-owner-state.md` (on main), and the workflow files
under `.github/` other than `control-mail.yml` (sweep sharding only, `timeout-minutes: 45` kept). Brief 18's tests
under `control/tests/` change only by additions or where the lifecycle forces it; name each change and keep its
assertions.

## Acceptance

- Each point has regression tests that would fail on `0ba7870e` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow (all its jobs) and the base workflow both pass twice on the final head; the boundary workflow still
  passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Keep checks, occurrences, acknowledgements and resolutions separate; an open check or an unacknowledged occurrence is
never expired or archived; unchanged evidence never changes an occurrence; a changed set restarts paging, never drops it.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Before each push, run locally:
  `python3 control/generate.py --check`,
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and the base tests you ran in round 28, plus your new plain-Python tests. Reason carefully through real-server tests
  whose fixtures you touch before pushing. Aim for one push with the code and tests and one with the report. Don't
  start extra manual workflow runs. For the second pass on the final head, rerun the same pull-request run with
  `gh run rerun <id>`; never push again just to get another run. Keep it to about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per point).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a warning-lifecycle model and stable paging across Mail and the base, on code it wrote.
