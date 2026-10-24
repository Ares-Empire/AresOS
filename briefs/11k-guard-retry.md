# 11k: Let the budget guard ride out GitHub's flaky job API, then finish A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11j" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c–11g, 11i and 11j still apply, plus the changes below.

## What stopped 11j

The idle-check fix and its regressions passed. The probe confirmed in the exact cached stock image that the daemon runs as `rpm-ostree` (rpm-ostree 2026.3, uupd 1.5.0). Then the unchanged guard (`rehearsal_guard.py full 196`) got HTTP 502 on job metadata three times, and nothing was dispatched. Stopping was correct: a guard that can't read the ledger must not authorize a full run.

## Integrator finding

This isn't the budget, and it isn't a GitHub outage: githubstatus showed "All Systems Operational".

- The plain `actions/runs/{id}/jobs` endpoint fails **intermittently** for some runs. At about 18:55 local time, probe run 40112294759 returned 502 twice, then 200 on the third try. The same run's `jobs?filter=latest` and `attempts/1/jobs` answered at once.
- The guard makes one such call per branch run, dozens in total, with no retry. A single intermittent 502 fails the whole guard.

## Integrator decision

1. **Bounded retry for read-only GitHub calls in the guard** (`api()` and the artifact ZIP download):
   - Retry only HTTP 5xx and connection failures. Find out how `gh api` reports the status, and parse that; don't guess.
   - Never retry 4xx, auth errors or JSON/parse errors. Those fail at once, as now.
   - At most 5 attempts per call, with growing waits (about 10, 20, 40 and 60 seconds).
   - Log each retry (path, status, attempt number) to stderr.
   - After the last attempt, fail closed exactly as now: no cached response, no skipped run, no partial ledger, no authorization.
2. **Regressions:**
   - A 502 followed by success must give the same ledger and minutes as a clean read.
   - Five 502s must fail closed with no authorization written.
   - A 403 or 404 must fail at once, without retrying.
   - A retry must never change the computed minutes or the full-run count.
3. **Probe rule unchanged.** The head has moved (the 11j report push plus this fix), so run a fresh probe on the new head, then the full on that same head. Nothing else in the walk-through changes. Confirm that in the REPORT before dispatching.
4. **Budget unchanged:** 750 minutes, 5 full runs, same ledger. 11j ended at 466/750 and 4/5. One probe (42), one complete full (182) and closing (14) come to 704. That's the whole plan: no second probe, no sixth full. If the guard can't fit it, stop and report.

## Then

1. Fresh probe on the new head.
2. One complete full run: **Part A** in both orders (installed keyboard, pause/cleanup/pin with exported decision values, and every later stage), then **Part B**.

All stop rules hold.

## Acceptance

11c's acceptance, plus an "11k" REPORT section with:
- the retry change and its regressions
- every retry seen this round (path, status, attempts)
- everything 11g's, 11i's and 11j's acceptance lists, including the installed keyboard result per order and the real pause/pin decision values

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
