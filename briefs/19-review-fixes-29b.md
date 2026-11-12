# 19-review-fixes-29b: round 29 without restore (amends brief 29)

**Goal:** finish round 29. Your first run stopped correctly under brief 29 point 4: restoring an older backup rolls
back filing sources, check states and notices, because only SQLite holds them, and keeping them across a restore needs
19b's projection (`reviews/19-mail/REPORT.md`, "Review fixes, round 29", and `reviews/19-mail/round29-stop-probe.py`).
The lead agreed with the stop and took restore out of round 29 (2026-11-09). **Brief 29 still applies, amended as
follows; where the two differ, this brief wins.** Everything restore-related in brief 29 is out: the lifecycle's
"through … restore" and the generic test "an acknowledged occurrence doesn't come back after … restore".

## What to build

1. **Scope.** Brief 29's points 1, 2 and 3: findings 1 and 2 of security review 21 plus the catalogue rule. The
   lifecycle (check, occurrence, acknowledgement, resolution) must hold across **reads, pages, restarts, archive and
   expiry**. Occurrence records, fingerprints and per-occurrence acknowledgements go in the existing stores. No new
   committed projection, no oracle, nothing else from 19b. Brief 29's tests stand, without restore: the review's
   RENAME / refused result write / restart with IMAP down / acknowledge / 24 hours / IMAP returns sequence; the
   four-RENAME paging case; and the generic tests (unchanged evidence keeps one occurrence id across many reads and a
   restart; changed evidence after an acknowledgement starts a new occurrence; clean followed by recurrence starts a new
   occurrence; a clean check after a warning keeps the unacknowledged occurrence; an acknowledged occurrence doesn't
   come back after archive, expiry or restart).

2. **Restore is a known limit (lead decision, round 29).** Record it in `REPORT.md` as the lead's:
   - Restoring an older backup rolls back free changes (MOVE, COPY, RENAME, flags, folders), their checks, warnings
     and acknowledgements to the backup's state, as today.
   - Approved sends and deletes keep their protection from the independent journal: restore detection and no replay.
   - Brief 19b's projection closes this: its stage 3 says a restore re-derives open checks and unacknowledged
     occurrences.
   Don't change restore behaviour beyond point 3.

3. **Tell the owner at restore time.** Add one plain sentence to both the result of the restore confirmation
   (`control_restore_confirm`) and the description of the restore action, saying in substance: free changes made after
   the backup's time (moves, renames, folder changes) and their warnings are not in the backup, so check those folders
   yourself. Regenerate the artifacts (`python3 control/generate.py`). That is the only text change in this round; keep
   the result within its existing bounds and update any exact-text test only by adding the sentence.

4. **Catalogue table in `REPORT.md`** for round 29, one row each: `mail_filing_notices` (`mail/filing.py:notice_page`)
   as the one warning catalogue, with duplicate Sent warnings as entries in it; `Engine.notices`' first-three repeat
   on `control_pending`, `control_log` / `aresos log` and ordinary results; `control_pending`'s operation-summary
   paging (`Engine._pending`); `control_log`'s audit paging; `control_observations` (`results.py:observation_page`).
   Each one that pages warnings, or anything a warning points to, gets the stable ordering (creation, then id) and the
   cursor rule (bound to its ordering; a changed set restarts from the first page and says so, never `items=[]` with
   `total>0`), through the one shared helper, with its test named in the row. Where a catalogue pages nothing a warning
   points to, say so in its row.

5. **Report.** Keep the first run's stop note as the record of that run (retitle it as the first run, stopped) and the
   probe as evidence of the known limit. Below it: the lead's two round-29 decisions (the lifecycle from brief 29, and
   restore as a known limit), each finding, what changed, the catalogue table, files changed and why, tests by name.
   Run IDs as before: in `REPORT.md`, the runs of the last commit that changes code or tests (all workflows, both
   passes) and the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on
   the final head.

## Stop condition

If, without restore, a finding still can't be fixed without a new committed projection or the oracle, stop as before:
write in `REPORT.md` what and roughly how big, commit and push that note, and end the run with it.

## Out of scope, acceptance, "If unsure" and rules for this run

As in brief 29, unchanged: same paths untouched, no weakened or deleted tests, the Mail workflow (all jobs) and the
base workflow pass twice on the final head (second pass by `gh run rerun <id>`), the boundary workflow still passes,
generated artifacts in sync, local checks before every push, about 6 workflow runs, no `--no-verify`, never merge,
never force-push, never push to `main`, trailer `Codex-Model: gpt-6.1-sol (xhigh)`.

**Model:** `gpt-6.1-sol`, xhigh: the same lifecycle and paging work as brief 29, on code it wrote.
