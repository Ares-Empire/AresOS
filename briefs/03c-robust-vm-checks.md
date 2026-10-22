# 03c: Verify recovery and power through robust channels

Follow-up on branch `pkg/03-os-image` (draft PR #3). Read `reviews/03-os-image/REPORT.md`, including the 03b section.

**Situation:** the image builds and boots into labwc every time. Over many runs, the only failures came from the test harness driving a serial or TTY console and synchronizing on prompts (PAM flushing, terminal queries, framing). That is test-channel fragility, not an image defect.

**Goal:** verify the **same properties** through channels that don't depend on prompt text or timing, so CI goes green:
1. **Clean poweroff on the power key:** inject an ACPI power-button press via QMP (`system_powerdown`). Assert the guest reaches poweroff cleanly: a QEMU shutdown event with guest-initiated poweroff, and journal or console evidence of the poweroff target. Lid and suspend requests must do nothing (assert sleep targets masked and logind settings in the live guest).
2. **Authenticated recovery login works:** prove password authentication for the provisioned recovery admin through a deterministic mechanism. Examples: a test-only check service that runs `su`/PAM non-interactively with the test password and writes PASS/FAIL to a virtio-serial port, or SSH with password auth enabled only in a test overlay. Also assert a getty is running on tty3. Test-only overlays must never be part of the release image.
3. Keep every check that already passes (session, updater masks, no wheel for `ares`, no inherited display manager), and export raw `bootc status` and the runtime updater inventory.

**Budget:** at most 3 full CI runs. If a property still can't be verified reliably in CI, stop and document exactly what remains for the first hardware boot. Never fake a pass, and never weaken an assertion.

**Acceptance:** a green run linked in a "03c" section of `REPORT.md`, PR #3 marked ready for review with an updated description. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
