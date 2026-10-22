# 03f evidence index

**Acceptance not met: 2/2 permitted full runs failed.** Final parser code
`83b7c9d` passes all 34 regressions and the real hosted system-manager query;
that checks-only result does not qualify either fresh guest pass.

- [Full attempt 1](attempt-1/README.md): missing `--` for `-.mount`, 31
  regressions and image/disk builds passed, first VM audit failed.
- [Full attempt 2](attempt-2/README.md): quoted escaped dependency name, 32
  regressions and image/disk builds passed, first VM audit failed.
- [Checks-only 39734679057](checks-39734679057/run.json): final parser code,
  new regression fixture selected the wrong runuser argument separator.
- [Checks-only 39734786025](checks-39734786025/run.json): corrected fixture,
  **34 tests OK**, syntax checks passed, **437 unit files / 596 unit names**
  read from the actual hosted system manager. Image job skipped.

Each folder retains original GitHub run/job metadata and workflow log ZIPs;
the full attempts also retain original artifacts and raw failure responses.
Both artifacts have 39 entries, all hash-matched to the expanded downloads.
[ci-runs.json](ci-runs.json) marks exactly two entries as full attempts.
[Build manifests](../../../os/manifest/ci/03f/README.md) come from the failed
second full run. [Report](../REPORT.md#03f-review-fixes) records limits and
remaining acceptance work. No third full run or rerun was started.
