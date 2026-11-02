# 14zm: A local wall-clock overrun on the busy laptop is a host limitation; continue the $10 round

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zl still apply, with the change below.

**Integrator decision:** the timing test that took 30.010 s, then 31.897 s against its 30-second bound did so on this laptop, which is under heavy memory pressure: Claude Code keeps reaping background jobs for low memory. A small overrun of a wall-clock bound on a loaded host is a **host limitation**. It is handled like the existing eight host-limited tests:
- **Don't change the test or its bound.** It stays mandatory in the **native CI suite**, and the probe's native step must pass it there.
- Record it in the REPORT as a host-timing limitation, with both measured times.
- If it also exceeds its bound in native CI, that's a real STOP.
- Don't add any skip, marker or environment switch for it.

Then continue exactly as 14zl says:
1. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget ($10, prevent true).
3. **Probe 20**. Only if it passes, **qualification 9 on the same head**.
4. Any CI stop: report it with the exported diagnostics, no rerun.
5. Closing steps as in 14zl. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
