# 18d main merge, fixes round 3: one scripted chronology for the Mail sweep fixtures

**Goal:** fix the two FIX findings of the package review of round 2 (`reviews/18d-base-slim/PACKAGE-REVIEW-5.md`, on
`88151b1c`) and record what its known limit asks for. The security review of round 2 (`SECURITY-REVIEW-4.md`) found
no FIX. The briefs of rounds 1 and 2 (`briefs/18d-main-merge-fixes.md`, `-2.md`) still apply. Test fixtures only;
nothing else changes.

## Why a round 3

Rounds 1 and 2 made the inherited sweep scenarios deterministic by scripting each time and random source on its own.
The reviewer found two places where that is still not one consistent time:

1. **File timestamps are ambient (finding 1).** Blob expiry reads the files' modification times
   (`control/aresos_control/blobs.py:142`), which the kernel sets from the real clock; the scripts don't control
   them, and the guard doesn't notice. The reviewer's probe changed only `st_mtime`: one case wrote nothing, the
   other unlinked two files and synced the directory, and no `AmbientRead` was raised. The export flows reach this
   through retention checks.
2. **Two clocks that disagree (finding 2).** Round 2 freezes `time.time()` and advances `time.time_ns()`. Recovery
   notices take their time from the float clock (`control/aresos_control/recovery.py:94`), checked warnings from
   nanoseconds, so a later recovery warning can sort before an earlier checked warning: the reviewer produced
   `...769` then a later `...768`, and the newest-first page showed the earlier warning first. The real system never
   produces that order. The new ordering test compares only nanosecond reads, so it misses it.

## What to build

1. **One scripted chronology per scenario.** Replace the separate clock scripts with one deterministic time source
   that every time read in these fixtures goes through: `time.time`, `time.time_ns`, implicit calendar reads
   (`localtime`, `gmtime`, `strftime`, `email.utils.formatdate`, `datetime.now`), and the file timestamps the service
   reads (blob modification times, and any other `st_mtime`/`st_ctime`/`getmtime` it compares with the clock; find
   them all). Requirements:
   - Every read advances the chronology by a fixed small step, so events the real system orders by time keep that
     order, and the float and nanosecond views always agree (one derived from the other).
   - The clean run and every faulted run read the same sequence, so their write traces stay equal before the fault.
   - Flows that need time to pass (expiry, maintenance, archive ageing, quiet periods) move it forward explicitly, as
     today, and restoring a temporary clock jump never moves time backwards for later reads.
   - File timestamps the service compares come from the chronology (for example, set on the files the fixtures and
     service create, or read through one scripted seam), and the real expiry writes (unlinks, directory syncs) stay.
   Keep the IDs, MIME boundaries and temporary names scripted as round 2 did.
2. **The guard covers it.** An unscripted time read of any kind, including a file timestamp that didn't come from the
   chronology, fails the guarded replay. Extend the mutation checks so that disabling each component (the chronology
   for each kind of read, the file timestamps, IDs, MIME boundaries, temporary names) fails for every flow that
   consumes it, fault and recovery paths included.
3. **Test the real ordering, not the reads.** Replace or extend the ordering test with one that drives production
   warning creation and the actual notice page: checked warnings before and after a later recovery source, and across
   an expiry clock jump and its restoration. The newest-first page must show them in real time order.
4. **Keep everything else.** Every flow, discovered point, single and persistent mode, cleanup pair and assertion stays;
   the Linux counts must not drop. No production code changes. If a production defect turns up, stop and report it.

## Known limit to record (finding 3)

From the final head's two Mail attempts, record per-flow discovered points and single, persistent and cleanup-pair
counts against the before-and-round-1 baseline (6,642 points; 6,302 single, 6,302 persistent and 15,915 cleanup-pair
cases), and the duration of every required Mail job against its 35-minute limit.

## Tests and runs

- Locally: `python3 control/generate.py --check`, the guard, its mutation checks, the new ordering test, the full
  fault sweep and every module that reuses `Scenario`, as far as macOS allows (CI is the evidence for the real settings
  path). Run the ordering and lifecycle tests several times.
- On GitHub, on the final head: Control base, Control Mail and Control boundary **twice each** (the pull-request run,
  then `gh run rerun <id>`; never a new push for the second pass). Both Mail attempts must pass every job. No oracle
  run.
- Any push restarts all three workflows and cancels older runs: commit locally (this brief and the review commit are
  local too) and push once, when everything is done and green locally.
- Budget: about six executions.

## Report

Add a section "Main merge fixes, round 3" to `reviews/18d-base-slim/REPORT.md`: the chronology's design, every time
source it covers (file and line), what the guard rejects, the mutation results, the ordering test, the count table
and the job durations. Record the final run IDs and attempts in the PR #25 description.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/18d-base-slim`. The draft PR #25 exists. Never merge anything, never push
  to `main`, never force-push.
- Don't edit the design or plan files, `README.md`, `STATE.md`, `HANDOFF.md`, anything under `os/`, `mod/`,
  `docs/INSTALL*`, `docs/EMERGENCY.md`, `reviews/19b-owner-state/`, `reviews/19-mail/`, the review files the
  reviewers wrote (`reviews/18d-base-slim/*REVIEW*.md`, `SECURITY.md`), or production code under
  `control/aresos_control/`.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same harness as rounds 1 and 2, now with one design that replaces the separate
scripts.
