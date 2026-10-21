# 04d: Make the arrival-site search deterministic

Follow-up on branch `pkg/04-nether-home` (PR #4). The delta review said SAFE, but **Claude's integration rerun failed**:
`java.lang.AssertionError: Site search was not deterministic` (full log: `reviews/04-nether-home/integration-gate-04bc-failure.txt`, head `e365d9d`). Codex's own run passed, so the result depends on timing or load state.

**Goal:** for a given seed, the safe-arrival search (04c, non-49 seeds) always returns the same spot, and that spot is safe in the fully generated world.

**In scope:**
- Find the real cause (for example reading partially generated or unloaded chunks, iteration order over a hash-based collection, time or tick dependence, or the state of a previous test world). Explain it in the report.
- Fix it at the source: score only fully generated terrain (force-generate or synchronously load what's needed) and use a stable order. Don't loosen the assertion.
- Strengthen the test: run the search for at least three seeds, several times each, in **fresh** worlds and once after a rejoin, and assert identical results that are safe in the generated world.
- Prove it: the new test fails or flakes on the old code (show how you triggered it), and passes **5 consecutive full `build runClientGameTest` runs** on the fix.

**Out of scope:** everything else.

**Acceptance:** 5 consecutive green full runs recorded in a "04d" section of `REPORT.md`. Stop your Gradle daemons.

**If unsure:** deterministic and safe beats fast.

**Model:** gpt-6.1-sol, xhigh.
