# Scoped security review — 1c6cfff2

Reviewer: gpt-6-astra (xhigh), read-only.

Two FIXes. Subtracting marginal percentiles hides a valid warm regression:
reference work 40 ms/sample; current 200 ms for 18 samples and40 ms for2, with
waits525/750 ms respectively. Actual work median/p95 is200/200, but subtracting
client/wait percentiles yields200/40 and passes with runner factor1. Subtract
matched samples before calculating percentiles. Also reject malformed metric
blocks: reversed median/p95 and required stages missing durations currently pass.
Four existing tests pass. This is CI-only; runtime/index scope is unchanged.
Targets are pending and the gate unwired. No edits or browser/profile/container
access.

CHANGES-NEEDED
