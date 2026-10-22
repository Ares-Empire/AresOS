# 03g: Verify the 03f fixes in full VM runs

Follow-up on branch `pkg/03-os-image` (PR #3). Read the 03f section of `reviews/03-os-image/REPORT.md`.

**Situation:** the 03f review fixes are implemented. Both full runs failed on parser bugs in the new activation audit (systemctl `--` delimiter, shell-quoted escaped unit names). Both are fixed and pass 34 regressions plus the real hosted system-manager preflight, but haven't been booted in the guest.

**Goal:** a green full image workflow with **both VM passes** on the 03f code: the canaries are rejected by the live audit, normal policy passes, and recovery, power, offline journal and logind proof all pass.

**In scope:**
- Before each full run, run the checks-only preflight. Also exercise the parser against **real Fedora/Bazzite systemd output**, for example by running the audit's parsing on `systemctl show` output captured from the built image in a container step, before booting. That way the next parser surprise is caught in seconds, not after a 40-minute build.
- Fix only what the runs reveal. Never weaken or remove an assertion.

**Budget:** at most 2 full CI runs (checks-only runs don't count).

**Acceptance:** a green full run with both VM passes, recorded in a "03g" section of `REPORT.md`, and the PR description updated. Do not merge. If not green within budget, stop and report precisely.

**Model:** gpt-6.1-sol, xhigh.
