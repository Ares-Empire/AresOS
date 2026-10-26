# 14m: Probe 6 hit the snapshot download limit; harden it locally, retry on 1 November

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Briefs 14 to 14l still apply, with the change below.

## Integrator decision

Probe 6 failed in "Install pinned rehearsal tools on disposable runner": `snapshot.ubuntu.com` served packages at 4–5 seconds each and the step's 10-minute limit ran out. No test step ran. This is a slow server, not our code.

A retry in October would leave the other repos below the 60-minute margin the owner approved, so **no dispatch before 1 November**.

**Now, local only (commits, no push):**
1. Commit your local STOP report and budget updates.
2. Make that step tolerate a slow snapshot server without hiding a real failure:
   - Raise its `timeout-minutes` to **20**. The probe and qualification job timeouts stay the same, so the worst-case cost is unchanged.
   - Add apt download retries (`-o Acquire::Retries=3`) to the apt calls in that step and in `os/ci/install-tools.sh`.
   - Keep the snapshot pin and the package list exactly the same.
3. Run the local replay and the strict checks again. Keep the commits local; **don't push before 1 November**.

**On 1 November (I'll resume you):** restore the org reserve to **150**; set the package cap to cover the new bound. Probe 7 and qualification 2 are allowed then, with one push before dispatch, after fresh privacy, ledger and billing checks.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
