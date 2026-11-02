# 14x: Probe 11 timed out on a 17 kB/s Ubuntu mirror; raise the step and job limits, probe 12 and qualification 3

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14w still apply, with the change below.

## Diagnosis (integrator, from the run log)

In "Qualify tools, regressions, rewritten release identity and private access", `playwright install --with-deps chromium` spent **14 min 14 s fetching 14.8 MB at 17.4 kB/s** from the default Ubuntu mirror. Everything after it passed within seconds:
- 379 tests
- the native partitioned-loop test
- the Windows copy check
- the tools manifest check

Then the step hit its 15-minute limit. The pinned-tools step also took 11 of its 20 minutes. This is a slow mirror, not our code.

## Fix (workflow limits and apt retries only; no other change)

1. **Raise the limits:**
   - the native "Qualify tools…" step: 15 → **35** minutes
   - the probe job: 40 → **70**
   - the qualification (`owner-tools`) job: 130 → **160**, so slow setup can't eat the VM step's 106 minutes, which stay unchanged
   - the pinned-tools step stays at 20
2. **Apt retries:** before the Playwright install, write an apt config (`Acquire::Retries "3";`) so Playwright's own apt calls retry too.
3. **Bounds:** update the guard's probe and qualification bounds to the new job limits (about 72 and 160), and every test that pins them.

## Budget (owner's $3 cap, prevent on)

About $0.40 of the $3 has been used. One push (about 6) plus a probe of at most 72 plus a qualification of at most 160 is about 238 minutes, roughly $1.43, which fits. Settings for package `14` only:
- `minute_cap`: 700 (unchanged; 437 + 238 = 675)
- `dispatch_caps.probe`: **12**
- `owner-tools`: 3, with qualification 3 not yet used

## Then

1. Pinned local gitleaks, the replay and strict checks. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 12**. Only if it passes, **qualification 3 on the same head**.
4. The artifact rules from 14v apply.
5. Any stop: report it, no rerun.
6. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
