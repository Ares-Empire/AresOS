# 14zh: Wire the idle proof into every prompt wait; probe 17 and qualification 7

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zg still apply, with the change below.

## Diagnosis (integrator, from the 14zg report)

Qualification 6 passed `title` after the first network. The next `prompt(completed)` wait found the cursor on an empty line (x0, y49). The row above held the root prompt followed by a kernel message, `sched: DL replenish lagged too much`.

There were **0 resync records**: since 14zb and 14ze, an Enter needs a fresh physical idle proof, but this completed-wait path never asks the idle observer for one. So 14j's bounded resync was never offered. This is a harness wiring gap. The policy itself is unchanged.

## Fix (harness only)

1. In **every** prompt-readiness wait (completed, after-hidden, after-hotplug, after-network, after-boot), do this when the cursor line has no prompt:
   - Ask the (14ze/14zg sudo-relay-aware) physical idle observer for idle authority.
   - Press Enter only if the observer says ready. At most 2 resyncs per wait, as 14j says.
   - Record each attempt: stage, the observer's answer, and the cursor line before and after.
   - If the observer refuses, STOP with the exported foreground chain.
2. Never press Enter without that proof. Don't change the prompt predicate, the console log level or the Enter limit.
3. Give every wait a unique receipt name, so no stage overwrites another's.
4. **Local tests** with VCSA and `/proc` fixtures:
   - the exact qualification 6 screen plus an idle sudo-relay shell: one Enter, then pass
   - the same screen with a busy foreground: STOP, no Enter
   - three cluttered screens: STOP after 2 Enters
   - every wait kind takes the same path
5. **Prevent the next round's surprise:** walk the remaining stages (export, the Windows round trip, corrected stock, login, verify, switch, the AresOS boot, layout begin/proof/revert/finish, rollback, keep-stock) in the stand-in walk with cluttered-screen and sudo-relay fixtures at every wait.

## Budget (owner's $6 cap; about $3.19 billed)

One more round: one push (about 6), plus a probe of at most 72, plus a qualification of at most 160. That's about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: **1100** (810 + 238 = 1048)
- `dispatch_caps.probe`: **17**
- `owner-tools`: **7**

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 17**. Only if it passes, **qualification 7 on the same head**.
4. Any CI stop: report it with the exported diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
