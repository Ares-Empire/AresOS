# 03f: OS image, review fixes

Follow-up on branch `pkg/03-os-image` (PR #3). Read `reviews/03-os-image/REVIEW.md` and the latest `REPORT.md` sections.

**Goal:** fix all three review findings, then a green CI run.

**In scope:**
1. **Narrow the contingency (blocking).**
   - `REPORTED_NOT_BLOCKING_FIRST_HARDWARE_BOOT_GATE` applies **only** to explicitly identified host-reader limitations: the kernel mount being unsupported **and** the userspace reader tooling unavailable.
   - Everything else is a blocking failure: `btrfs check` errors, extraction errors, journal verification failures, an expected boot that's absent from a readable journal, a wrong boot, and missing records.
   - Verify the journals before selecting the boot.
   - Regressions for each command-failure path, driving the real classification code, not just the outer exception.
2. **Updater audit covers activation (should-fix).**
   - Require suspicious units to be masked or on the reviewed allowlist regardless of unit-file state.
   - Also check activation: units pulled in by enabled timers, paths, sockets and targets, plus generated units, using live system and user manager state in the VM.
   - Regressions: a static updater triggered by an innocently named enabled timer, and an updater generated at boot. Both must fail.
3. **Pin the toolchain (should-fix).**
   - Pin Podman, Skopeo, QEMU and OVMF/firmware immutably, for example in a digest-pinned builder container, or as exact package versions from a dated snapshot.
   - If something can't be pinned on hosted runners, record exactly what and why, and keep recording versions.

**Budget:** at most 2 full CI runs.

**Acceptance:**
- A green run with both VM passes.
- An "03f" section in `REPORT.md`.
- The PR description updated, the PR still ready for review. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
