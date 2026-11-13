# 18d main merge, fixes round 2: a complete determinism script and guard, and round 1's regression

**Goal:** fix the one FIX finding of the package re-review (`reviews/18d-base-slim/PACKAGE-REVIEW-4.md`, on
`8bfe75ec`), record the Linux counts it asks for, and fix the Mail failure that round 1's fixed clock caused
(item 3). The security re-review (`SECURITY-REVIEW-3.md`) found no FIX. Round 1's brief,
`briefs/18d-main-merge-fixes.md`, still applies. Nothing else changes.

## What to fix

1. **The guard misses part of the script (finding 1).** `test_inherited_replays_have_identical_write_traces`
   (`control/mail_tests/test_review23_sweep.py`) makes only ambient `time.time()` and `uuid.uuid4()` raise. The
   scenarios also depend on `scripted_calendar()` (it scripts `time.time_ns()` and `time.localtime()` with no
   argument) and `scripted_ids()`. If the calendar script were lost, real nanosecond and calendar values would vary
   while their printed length stays the same, so three equal traces would not reveal it. The reviewer reproduced
   that: with the calendar script removed, three different `created_at` values of equal JSON length, and no guard
   failure. Fix it so losing any part of the script fails every time:
   - First find every ambient clock, calendar and random source these flows can read, in the service and the
     fixtures: at least `time.time`, `time.time_ns`, `time.localtime()` and `time.gmtime()` without an argument,
     `time.strftime` without a time tuple, `datetime.now/utcnow/today`, `uuid.uuid1/uuid4`, `random`, `secrets`,
     `os.urandom`, and `email.utils.make_msgid` or `formatdate` without fixed inputs. List what you found in the
     report, with file and line.
   - Make the guard reject every such ambient read during the replays (outside the scenario's own scripts), so a
     scenario that loses any script component raises instead of passing.
   - Add mutation checks: for each script component (the clock, the calendar, the IDs, and any source you script
     newly), run the guard with that one component disabled and show it fails, for every flow that reads that
     source. A source no flow reads needs no script; say so.
   - If a flow reads a source that is still unscripted and could vary run to run (for example a random Message-ID),
     script it the same way, keeping realistic value lengths, and keep every flow, point, mode, cleanup pair and
     assertion.
2. **Linux counts before and after (finding 2, known limit).** From the Linux logs, record per flow the discovered
   write points and the single, persistent and cleanup-pair case counts: before (Control Mail run `43153748879`,
   attempt 2, on `9bcacd84`, real clock) and after (run `43162099390` on `8bfe75ec`, and the final head). They must
   not drop; explain any difference by its cause.

3. **The regression round 1 caused.** Control Mail run `43162099390` (head `8bfe75ec`), attempt 1, job
   `containers (1)`: `test_review29_lifecycle.Lifecycle29.test_review29_rename_refused_result_offline_ack_expiry_then_trash_is_new_occurrence`
   failed at `control/mail_tests/test_review29_lifecycle.py:70`: `'Trash' not found in 'A change was interrupted
   before its completion was recorded. ...'`. It had not failed in any earlier Mail run. Round 1's build (stopped by
   the package lead so both items are designed together) diagnosed it and reproduced it locally: this test reuses the
   sweep's `Scenario`; with the float clock fixed, `scripted_calendar()` derives `time.time_ns()` from it, so
   successive notices get identical nanosecond timestamps, and ID order can put the generic interrupted-change
   warning ahead of the later Trash warning. Its uncommitted change is in the working tree
   (`git diff control/mail_tests/test_review23_sweep.py`: `time.time_ns` advances deterministically for flows other
   than `archive`). Check it, then keep, improve or replace it. Design it together with item 1: the guard must cover
   that script too, and the mutation checks must show that losing it fails.
   Then find every other test that reuses `Scenario` or these fixtures (search the test modules), and check each for
   behaviour that depends on time passing between steps: ordering by timestamp, "newest" selection, expiry, quiet
   periods, retention, occurrence identity. Run all of them locally, more than once where timing could matter, and
   say which you checked. A fixed clock must never make two events that the real system orders by time look
   simultaneous.

## Tests and runs

- Locally: `python3 control/generate.py --check`, the guard and its mutation checks, the focused sweep for the flows
  you changed, and every test module that reuses `Scenario` (item 3), as far as macOS allows (CI is the evidence for
  the real settings path).
- On GitHub, on the final head: Control base, Control Mail and Control boundary **twice each** (the pull-request run,
  then `gh run rerun <id>`; never a new push for the second pass). Both Mail attempts must pass every job. No oracle
  run.
- Any push restarts all three workflows and cancels older runs: commit locally (this brief and the review commit are
  local too) and push once, when everything is done and green locally.
- Budget: about six executions.

## Report

Add a section "Main merge fixes, round 2" to `reviews/18d-base-slim/REPORT.md`: the sources found, what the guard now
rejects, the mutation checks and their results, any newly scripted source, the lifecycle regression's cause and fix with the
list of `Scenario` users checked, and the before/after count table. Record
the final run IDs and attempts in the PR #25 description.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/18d-base-slim`. The draft PR #25 exists. Never merge anything, never push
  to `main`, never force-push.
- Don't edit the design or plan files, `README.md`, `STATE.md`, `HANDOFF.md`, anything under `os/`, `mod/`,
  `docs/INSTALL*`, `docs/EMERGENCY.md`, `reviews/19b-owner-state/`, `reviews/19-mail/`, or the review files the
  reviewers wrote (`reviews/18d-base-slim/*REVIEW*.md`, `SECURITY.md`). Production code changes only if a real defect
  needs one; say so plainly.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same harness as round 1, a focused completion of its guard.
