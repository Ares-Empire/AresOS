# Scoped package review — 1c6cfff2

Reviewer: gpt-6.1-sol (high), read-only.

FIX: invalid evidence passes the prepared gate: client median 10000 ms/p95 1 ms;
a required stage with only samples:20; and a 1–2 ms total containing a 525 ms wait.
Validate complete finite nonnegative ordered metrics and total/wait consistency,
with regressions for each. Four existing gate tests pass. Paired noise and the
both-percentile decision policy otherwise fit the stated scope. Targets, reference
and wiring remain pending. No edits or browser/profile/container/GitHub changes.

CHANGES-NEEDED
