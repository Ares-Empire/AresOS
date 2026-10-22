# 03i evidence: full workflow and both fresh VM passes green

Source **`a4eaca14b2b7c8aaef8dd4b815b2abe73fce47e5`**; the existing Cockpit
mask, strict audit, tests and workflow required no code change.

- [Checks-only first](checks-1/README.md): 39 regressions, syntax and real hosted
  manager query pass; image job skipped.
- [Full attempt 1](attempt-1/README.md): image build/audit, release isolation,
  disk construction and both fresh KVM/UEFI guests pass, including actual
  offline journal/logind proof in each guest.
- [Run ledger](ci-runs.json): **1/2** authorized full attempts used; no rerun.
- [Raw manifests and per-pass results](../../../os/manifest/ci/03i/README.md).
- [03i report](../REPORT.md#03i-verify-the-static-audit-with-the-cockpit-mask).

The evidence ZIP is the original GitHub download. Its hash matches GitHub
metadata and all 103 expanded entries match. The checks-only workflow ZIP is
also original. The full workflow ZIP redacts two VM-only password hashes;
its remaining entry text is preserved. No image, disk, credential file, builder
configuration or binary journal is retained. Six screenshots were inspected.
The deferred activation graph and hardware/release gates remain unqualified.
