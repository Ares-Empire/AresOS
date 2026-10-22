# 03i raw evidence: qualified static audit with the Cockpit mask

[Green full run 39756953602](https://github.com/carlsenares/AresOS/actions/runs/39756953602),
source **`a4eaca14b2b7c8aaef8dd4b815b2abe73fce47e5`**. Both fresh KVM/UEFI
guests passed canary rejection, normal policy, recovery, input/power and actual
offline journal/logind proof. The existing Cockpit mask needed no correction.

[Provenance](provenance.json), [release digest](image-digest.txt),
[release OCI manifest](image-oci-manifest.json), [test-layer digest](vm-image-digest.txt),
[test-layer OCI manifest](vm-image-oci-manifest.json), [metrics](metrics.json),
[build updater inventory](updaters.json), [kernel/NVIDIA packages](kernel-nvidia.txt),
base/signature, complete package inventory and pinned toolchain files are raw
copies of the artifact. The image was not published.

| Evidence | VM pass 1 | VM pass 2 |
|---|---|---|
| Raw bootc status | [backend](vm-pass-1/backend.json) | [backend](vm-pass-2/backend.json) |
| Runtime inventory | [1,088 units](vm-pass-1/runtime-updaters.json) | [1,088 units](vm-pass-2/runtime-updaters.json) |
| Static/generated canary rejection | [proof](vm-pass-1/updater-regressions.json) | [proof](vm-pass-2/updater-regressions.json) |
| Normal policy | [result](vm-pass-1/policy-result.json) | [result](vm-pass-2/policy-result.json) |
| Input/sleep checks | [events](vm-pass-1/power-events.json) | [events](vm-pass-2/power-events.json) |
| tty3 getty and PAM authentication | [result](vm-pass-1/recovery-result.json) | [result](vm-pass-2/recovery-result.json) |
| Clean guest poweroff | [result](vm-pass-1/poweroff.json) | [result](vm-pass-2/poweroff.json) |
| Offline journal result | [passed](vm-pass-1/offline-poweroff-check.json) | [passed](vm-pass-2/offline-poweroff-check.json) |
| Structured logind/manager records | [proof](vm-pass-1/offline-poweroff.json) | [proof](vm-pass-2/offline-poweroff.json) |
| Read-only reader and cleanup commands | [commands](vm-pass-1/offline-commands.json) | [commands](vm-pass-2/offline-commands.json) |
| Persistent journal file hashes | [hashes](vm-pass-1/offline-journal-files.json) | [hashes](vm-pass-2/offline-journal-files.json) |

Both backends identify bootc/OSTree storage and test-image digest
`sha256:cfe1029721b3680f9782870c2ea63ca8b72a2b0000aebc0725522203eba7fbda`.
The separate release digest is
`sha256:05c27647e0b7e69d90208d99b5ff3873df71b7fa78a744f4fd50bb61349230d7`.
Boot IDs are `b854391a357041369180be760f446df2` and
`2c3026bde47b4cc9b1a33718c1fa546a`. Each journal has the ordered pre-button
marker, structured short power-key event, `SHUTDOWN=power-off` and successful
logind stop. Both used working userspace extraction after a failed kernel mount;
neither used the hardware-gate contingency.

The [original evidence ZIP](../../../../reviews/03-os-image/03i/attempt-1/evidence.zip)
also retains full offline boot text/JSON, logind JSON, journal verification,
passive console/QMP logs, acceleration records and original framebuffers.
`host-platform.txt` and `toolchain-package-metadata.txt` contain original trailing
whitespace and remain in that lossless ZIP rather than expanded here. Both raw
`poweroff.txt` console excerpts also remain there, preserving their carriage
returns and terminal control sequences. Duplicated base64 export wrappers and
large full-journal exports also remain in the ZIP.
No binary journal, image/disk or credential file is retained.

[All 03i evidence](../../../../reviews/03-os-image/03i/README.md),
[current report](../../../../reviews/03-os-image/REPORT.md#03i-verify-the-static-audit-with-the-cockpit-mask).
