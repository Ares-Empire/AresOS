# 03d: Prove the power-key path from the guest's on-disk journal

Follow-up on branch `pkg/03-os-image` (draft PR #3). Read the 03c section of `reviews/03-os-image/REPORT.md`.

**Situation:** every check passes except one. A clean, guest-initiated poweroff after an ACPI power-button press is observed (QMP `POWERDOWN` → `SHUTDOWN guest=true`, `poweroff.target`, clean teardown), but the logind "Power key pressed" record is never captured by the live journal follower.

**Goal:** settle, with evidence, whether the button event goes through systemd-logind.

**In scope:**
- After the VM has powered off, read the guest's **persistent journal offline from its disk** on the runner (for example by attaching the disposable overlay disk and running `journalctl -D <guest journal dir>` or `--root`, read-only). Use the previous-boot records of `systemd-logind` for the power-key event and the orderly shutdown. Make sure the journal is persistent in the test overlay, and in the release image if needed.
- If needed, raise systemd-logind's log level **in the CI-only overlay only**, so the event is recorded.
- Assert from that offline journal: logind handled the power key, and the shutdown that followed was orderly. Keep all other 03c checks and the second fresh VM pass.

**Budget:** at most 2 full CI runs.

**If still not provable:** stop. Record exactly what the offline journal shows, and leave the assertion in place. Claude will then decide whether this becomes a documented first-hardware-boot check. Never weaken or remove the assertion yourself.

**Acceptance:** a green run, or a precise negative result with the offline journal evidence, recorded in a "03d" section of `REPORT.md`. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
