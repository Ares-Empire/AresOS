# 14zzb: Give the qualification VM step room for the whole tail; probe 31, qualification 20

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zza still apply, with the changes below.

## Integrator decision on the qualification 19 deadline STOP

Accepted as a step-budget limit, not a bug: the counts were exact (66/66) and no stage failed. The serial plan isn't needed, because no console-typing failure has been shown. **Raise the time limit instead.** These are free minutes: the budget is $0 with stop-usage on, and GitHub charges only the minutes actually used.

1. **Size the limit from real timings.**
   - From the retained qualification 17 and 19 logs, record how long each stage took, and how long the setup before the VM step and the work after it took.
   - Project the full run with the slower of the two for each stage. For the stages neither run finished (rollback-from-stock refusal, keep-stock, default-stock, the two Windows marker boots), use the slowest comparable boot stage.
2. **Set the limits:**
   - VM step `timeout-minutes`: 106 → **180**
   - the guard's qualification bound: 160 → **220**, and the job timeout to match if there is one
   - the probe bound stays at 72
   - If the projection with 25% margin exceeds 180, STOP and report rather than going higher.
3. **The minute cap stays at 2750.** 2144 + 72 + 220 = 2436 fits, and the organization has about 1567 included minutes left with the reserve at 150.
4. **Then, as in 14zz:** local checks, one push through the privacy hook, then **probe 31 and qualification 20 on that same head**, then STOP and report.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
