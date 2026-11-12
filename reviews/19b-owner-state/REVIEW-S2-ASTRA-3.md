Findings 1–2 are fixed. One new regression remains.

1. **Should-fix — unrelated incoming mail makes a complete filing scan fail oracle validation.**

   **Where:** [effects.py:54](/Users/pab/AresOS-19b-state/control/owner_state_oracle/effects.py:54), consumed by [model.py:659](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:659).

   **Reproduction, run in memory:** Seed an interrupted MOVE with healthy roles and an existing destination. After the scan’s LIST snapshot records Source UID 1, insert unrelated UID 2 immediately before SELECT. SEARCH correctly returns `1 2`; both bodies are fetched successfully. Production commits `state=partial`, a closed check, complete locations and an unacknowledged warning.

   The new validator compares SEARCH against the earlier LIST-time message inventory and rejects the legitimate arrival. It reports `unjustified-check-close` and `unsupported-resolution`, retaining spurious recovery. Replaying against the baseline oracle and its scan-completion rule accepts the same result without lifecycle errors.

   **Fix:** Validate SEARCH against independently recorded message inventory at that SEARCH, then require matching body evidence for every returned UID. LIST should establish the mailbox catalogue, not freeze its message contents. Add this arrival regression while retaining the empty-FETCH, wrong-UID and missing-literal negatives.

Verification: **35 selected tests passed**; one additional test was blocked during temporary-directory setup by read-only permissions. In-memory probes confirmed both original fixes, context/result-write failure handling, and successful retry after stale-reference refusal. No files were edited or containers run; the full filesystem fault sweep was not rerun.

CHANGES-NEEDED