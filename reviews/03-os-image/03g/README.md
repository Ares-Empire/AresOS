# 03g evidence: acceptance not met

Both counted full runs stopped before disk construction; neither VM ran.
The final code is `06da4b82fe968fa8e87c27afbdcb2559808bbb09`.
No implementation changed after its green base preflight and failed full run.

- [Checks-only 1](checks-1/README.md): 34 regressions and Ubuntu manager query passed.
- [Full attempt 1](attempt-1/README.md): release built; invalid `/opt` mount target.
- [Checks-only 2](checks-2/README.md): real pinned Fedora base system/user inventory passed.
- [Full attempt 2](attempt-2/README.md): release built; `user@1000.service` failed in its container.
- [Run ledger](ci-runs.json), [original artifact integrity comparisons](archive-verification.txt).
- [Current report](../REPORT.md#03g-verify-03f-in-full-vm-runs).

All original workflow-log ZIPs are retained. The three evidence ZIPs are exact
GitHub downloads whose hashes match their artifact metadata and whose entries
match the separate expanded `gh run download` results. Neither full run produced
a disk, VM screenshot, canary rejection, recovery result or offline journal.
No image, disk, credential or builder configuration is retained here.
