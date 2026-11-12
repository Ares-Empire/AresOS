Findings 2–4 are fixed. Finding 1’s unrelated-LIST reproduction is fixed, but its scan-completeness requirement remains incomplete.

- **Blocking — incomplete scans can authorize check closure.** [driver.py:324](/Users/pab/AresOS-19b-state/control/owner_state_oracle/driver.py:324), consumed by [model.py:608](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:608).

  **Reproduction:** Start an interrupted filing with one message and an existing destination. During its correlated recovery scan, let SELECT and metadata FETCH succeed, then return `('OK', [])` for the message’s `BODY.PEEK[]` FETCH. Production `locations()` correctly returns `scan_complete=False`, but the new recorder emits `SCAN_RESULT accepted=True` because it checks command status without validating the returned body. Follow this with a false `done/check_open=False` commit. My in-memory probe produced **zero proof failures and no retained recovery obligation**.

  **Fix:** Record and independently validate the actual FETCH results, including the matching UID and body literal, before declaring the scan complete. Require that evidence for closure and add this false-completion regression.

Validation: 24 fix-round tests and eight `StageTwoPartA` tests passed. RENAME and incorrect-count probes confirmed their fixes. The compact ledger contains only stage-3 entries. No files edited or containers run.

CHANGES-NEEDED