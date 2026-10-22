# 03h evidence: acceptance not met; 2/2 full runs used

- [Full attempt 1](attempt-1/README.md): release-container probe passed, but the
  VM graph audit raced a disappearing transient unit. This selected the brief's
  pre-decided static fallback.
- [Checks-only 1](checks-1/README.md): all 38 static/prototype regressions pass.
- [Full attempt 2](attempt-2/README.md): static audit correctly rejected the
  generated, unmasked Cockpit container entry point. Both runs booted labwc;
  neither completed normal policy, recovery/power/offline proof or VM 2.
- [Checks-only 2](checks-2/README.md): new Cockpit regression fixture error.
- [Final checks-only](checks-3/README.md): corrected fixture, all 39 tests pass.
  The exact Cockpit mask is added, but no full run of that final source exists.
- [Run ledger](ci-runs.json), [failed final-build manifests](../../../os/manifest/ci/03h/README.md),
  [report](../REPORT.md#03h-converge-pr-3-with-the-authorized-static-split),
  [separate activation-graph follow-up](../../../briefs/03-followup-activation-audit.md).

Original checks-only workflow ZIPs, credential-redacted full-run workflow ZIPs
and both original artifact ZIPs are retained. Both evidence ZIP hashes match GitHub metadata; all 46/39 entries
match the separately expanded downloads. No image/disk/credential/builder
configuration or binary journal is retained. No third full run was started.
