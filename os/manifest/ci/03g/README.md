# 03g build evidence: failed final full run

These are unchanged build manifests from
[39739567070](https://github.com/carlsenares/AresOS/actions/runs/39739567070),
source `06da4b82fe968fa8e87c27afbdcb2559808bbb09`. The release build passed
34 regressions, signature/RPM/driver/tool checks, the 817-unit build audit and
container lint (10 passed / 1 skipped / 4 inherited warnings).

The release-container preflight then failed to start `user@1000.service` before
the audit ran. **No overlay, disk or VM was built.** No guest backend export,
live inventory, canary rejection, recovery or offline poweroff result exists.
The release digest identifies a failed qualification run, not an accepted image.

Exact tool/firmware versions, archive metadata, hashes and mutable host inputs
remain recorded. The raw `host-platform.txt` and
`toolchain-package-metadata.txt` have original trailing whitespace/blank lines
and are retained only in the [original evidence ZIP](../../../../reviews/03-os-image/03g/attempt-2/evidence.zip).
That ZIP also retains the empty console and single-line container-ID output.

[All 03g evidence](../../../../reviews/03-os-image/03g/README.md) includes both
failed full runs and both preceding successful checks-only runs. The
[base parser transcript](../../../../reviews/03-os-image/03g/checks-2/README.md)
proves real Fedora system/user output parsing, not the configured release's
container startup or either required VM pass. See the
[report](../../../../reviews/03-os-image/REPORT.md#03g-verify-03f-in-full-vm-runs)
for the **2/2 budget stop** and unresolved diagnostic gap.
