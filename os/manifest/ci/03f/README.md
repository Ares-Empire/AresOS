# 03f build evidence: failed second full run

Root files are unchanged copies from the evidence artifact of
[39729374555](https://github.com/carlsenares/AresOS/actions/runs/39729374555),
source `cba88bb58c6bee08613fdac2ae0e7197b610a2e3`.
The image/disk builds, 817-unit build audit, signature/RPM/driver checks,
release isolation and all 32 regressions passed. The first VM's live inventory
then failed on a shell-quoted dependency name. These are build results from a
**failed VM run**, not evidence that 03f acceptance passed.

`toolchain.json`, exact package/installed-version records, APT policy/source
configuration, archive package metadata/SHA-256 values and executable/OVMF
hashes document the immutable tool and firmware inputs. `host-packages.txt`
and the archived host-platform record retain mutable host inputs.
`host-platform.txt` and `toolchain-package-metadata.txt` are preserved inside
the original artifact ZIP, including their original trailing whitespace/blank
lines, rather than copied into this directory. This runner was image
`20261012.334.1`, kernel `6.17.0-1022-azure`;
attempt 1 used image `20261018.339.1`, kernel `7.0.0-1017-azure`.

`updaters.json` is the **817-unit build inventory**. No live guest inventory,
raw bootc status export, canary rejection record or offline-poweroff result
was reached. The final quoted-vector correction is only validated by the
separate checks-only run on source `83b7c9d`; it has no new image digest.

The original, lossless [attempt-2 artifact ZIP](../../../../reviews/03-os-image/03f/attempt-2/evidence.zip)
retains all 39 evidence entries, including the diagnostic console/framebuffer
and QMP results. Each entry was SHA-256 compared to the expanded download.
The [attempt-1 archive](../../../../reviews/03-os-image/03f/attempt-1/evidence.zip),
all workflow-log ZIPs, run/job/artifact metadata and the
[run ledger](../../../../reviews/03-os-image/03f/ci-runs.json) are retained too.

No image, disk, password, credential file, binary guest journal or builder
configuration is committed. The [03f report](../../../../reviews/03-os-image/REPORT.md#03f-review-fixes)
records both failures, the green checks-only result, measurements and the
exhausted **2/2 full-run budget**. Both fresh VM passes still need verification.
