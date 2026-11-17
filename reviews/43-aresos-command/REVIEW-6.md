# 43 step 1: fix check of REVIEW-5 (Codex gpt-6-astra high, 2026-11-17)

Checks `1e468f19`.

Both REVIEW-5 findings are **fixed** in `1e468f19`.

1. **Predictable refusals after announcement — fixed.** The preflight runs before announcement, verification and intent. Its `--check` path exits before any unmask, reload, restore trap or staging command. Normal `update.sh` retains those checks and rejects configuration changes made after preflight. No new predictable refusal follows the announcement.

2. **Stale closing instruction — fixed.** The suffix uses `forward()`’s own validated survey, including its already-first path. It disappears when the tools’ release is installed and gives the correct restart advice otherwise. Row 9 remains correct.

**Breakage or newly opened issues:** none found in the touched code.

Verification used read-only, in-memory and stubbed-shell probes:

- Four survey-change cases and ten row 9/10 closing-line cases passed.
- Four bad configurations refused before mutation in both shell modes; staging also rejected a policy changed after successful preflight.
- Parent-code comparisons reproduced the stale suffix and announcement-order failures; removing the shell fix reached an intercepted mutation.
- Payload/source equality, bundle fingerprint and diff whitespace checks passed.

The added regressions target these failures. I did not rerun the filesystem-dependent modules; their successful local runs are the lead’s evidence. No files changed or installed owner tools ran.

SAFE