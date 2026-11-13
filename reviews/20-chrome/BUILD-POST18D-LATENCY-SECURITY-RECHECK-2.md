# Scoped security re-check — ae0047d8

Reviewer: gpt-6-astra (xhigh), read-only.

Creation follows prepared replay, final reservation loading and recovery.
Admission checks physical space and history; early startup only detects an
existing index. Exact-code in-memory physical/history refusals preserve reserved
operation and holds. Successful creation leaves holds unchanged; existing-index
reads require no admission. Removing admission creates the forbidden index and
is detected. The actual-restart test was inspected, not independently rerun.
No edits or browser/profile/container access. Final acceptance remains pending.

SAFE
