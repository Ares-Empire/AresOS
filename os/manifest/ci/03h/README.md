# 03h raw manifests: final full attempt failed

[Run 39749001395](https://github.com/carlsenares/AresOS/actions/runs/39749001395),
source **`c5473259e537ef38621a34899e8d330e9a360e36`**, passed release/package/driver
checks, the 817-unit build audit, release isolation and disk construction.
VM 1's static audit then correctly rejected generated `cockpit-container.service`.
No VM 2, recovery, power/input or offline journal/logind proof was reached.

These digests/manifests identify that **failed qualification build**, not the
later `9b29c02` source with its new Cockpit mask. Only checks-only CI has passed
for that final source. **03h acceptance is not met; 2/2 full runs are used.**

[Provenance](provenance.json), [release digest](image-digest.txt),
[test-layer digest](vm-image-digest.txt), [metrics](metrics.json),
signature, locked packages, protected driver set and exact pinned tool/firmware
versions/hashes remain unchanged raw evidence. `host-platform.txt` and
`toolchain-package-metadata.txt` contain original trailing whitespace and are
retained only in the [lossless artifact ZIP](../../../../reviews/03-os-image/03h/attempt-2/evidence.zip).
The ZIP also contains VM 1's error, passive console/QMP and failed framebuffer.
No successful backend/runtime/canary export or poweroff result is fabricated.

[All 03h evidence](../../../../reviews/03-os-image/03h/README.md),
[current report](../../../../reviews/03-os-image/REPORT.md#03h-converge-pr-3-with-the-authorized-static-split).
