# 18d main merge, fixes round 1: the intermittent Mail sweep

**Goal:** a required check failed once on the combined head `9bcacd84` and passed on its rerun. `AGENTS.md`: a test
that passes once and fails once is a failure; fix its cause, never the assertion. Find and fix the cause, so Control
base, Control Mail and Control boundary pass twice on the final head. Nothing else changes.

## The failure

Control Mail run `43153748879`, attempt 1, job `sweep (2)`:
`test_review23_sweep.FaultSweep23.test_review23_enospc_at_every_discovered_durable_write`, flow `send_duplicate`,
point 844 (`journal.write`), single-fault mode. `self.assertEqual(trace[:number], points[:number])`
(`control/mail_tests/test_review23_sweep.py:705`) failed: the faulted run's write trace first differs from the clean
run's at index 721 (`sqlite.main.fsync` where the clean run had `sqlite.main.write`), before the fault is injected.
Persistent mode at the same point passed; attempt 2 passed all jobs.

What is known (package lead and the integration build, `reviews/18d-base-slim/REPORT.md`, PR #25):

- 18d doesn't change this flow's writes. Mail's head `ad777f5e` discovers 919 write points for `send_duplicate`
  (run `43147996259`, `sweep (2)`); this head discovers 912. The only difference is 7 fewer `file.close` events (the
  slimmer boundary check closes fewer descriptors). Every write, fsync, create and unlink count is equal.
- The faulted run diverged from the clean run by itself, before its fault: one fewer SQLite page written in a
  transaction.
- Likely cause, not proven: values whose length changes from run to run. Storage writes float timestamps into JSON
  (for example `"time": time.time()` in `storage.py`, `expires`, `attempt_ended_at`, `sent_append_*_at`), and
  Python prints a float in as few digits as round-trip needs, so the length varies; random IDs could do the same if
  their length varies. A row a few bytes longer can need one more page. 19b fixed the same class of mismatch for the
  archive flow only (`8915955b`: `Scenario('archive')` gets fixed IDs and a fixed clock, and
  `test_archive_replays_have_identical_write_traces` shows equal traces). The other inherited flows, `send_duplicate`
  included, still use real time and IDs (`test_review23_sweep.py:29`).
- The integration build's 160 local samples did not reproduce it: the event is rare, so absence locally proves
  little.

## What to do

1. **Show the mechanism, or rule it out, deterministically.** For example: run `send_duplicate`'s clean flow under two
   fixed clocks whose values print with different lengths (such as `1794225600.0` and `1794225600.1234567`), or with
   IDs of different lengths, and compare the write traces; and check each stored value that comes from the clock or a
   random source. A test that shows "these inputs change the page trace" is the evidence; a rerun that passes is not.
2. **Fix the cause.** If it is the clock and IDs: give every inherited sweep flow (`test_review23_sweep.py`) the same
   deterministic clock and IDs that the archive flow has, advancing time deterministically where a flow needs time to
   pass, so the clean run and every faulted run write the same bytes. Keep every flow, point, fault mode, cleanup pair
   and assertion. Then add a required check that, for every inherited flow, repeated clean runs give identical write
   traces (as the archive check does), so any remaining nondeterminism fails every time, not one run in many.
   If the cause is something else, fix that instead. If it is a real defect in production code, fix it there,
   minimal and tested, and say so plainly.
3. **If no cause can be shown,** don't guess and don't loosen the assertion: stop, and report what you tried and what
   you found.
4. **The optional owner oracle stays as it is.** Don't touch `reviews/19b-owner-state/KNOWN-GAPS.json` or the oracle;
   its pin migration is the PLAN-GAP already recorded for the lead.

## Tests and runs

- Locally: `python3 control/generate.py --check`, the new determinism tests, and the focused sweep for the flows you
  changed, as far as macOS allows (the managed settings check refuses the `/etc` symlink there; CI is the evidence).
- On GitHub, on the final head: Control base, Control Mail and Control boundary **twice each**: the pull-request run,
  then `gh run rerun <id>` (never a new push for the second pass). Both Mail attempts must pass every job. No oracle
  run.
- Any push to the PR restarts all three workflows and cancels older runs, so commit in small steps locally (this
  brief and the review commit `14a2ff43` are local too) and push once, when everything is done and green locally.
- Budget: about six executions. If a run fails, fix the cause, never the assertion, and say how many you used.

## Report

Add a section "Main merge fixes, round 1" to `reviews/18d-base-slim/REPORT.md`: the mechanism and its evidence (or
what ruled it out), the fix, the tests, and the counts of flows, points and cases before and after (they must not
drop). Record the final run IDs and attempts in the PR #25 description, as before.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/18d-base-slim`. The draft PR #25 exists. Never merge anything, never push
  to `main`, never force-push.
- Don't edit the design or plan files, `README.md`, `STATE.md`, `HANDOFF.md`, anything under `os/`, `mod/`,
  `docs/INSTALL*`, `docs/EMERGENCY.md`, anything under `reviews/19b-owner-state/` or `reviews/19-mail/`, or the
  review files the reviewers wrote (`reviews/18d-base-slim/*REVIEW*.md`, `SECURITY.md`).
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a focused determinism diagnosis in a test harness it already knows from the
integration build; nothing here needs Astra's extra depth.
