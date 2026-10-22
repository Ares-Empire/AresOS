# 06e: Qualify the 06d fixes in a real VM run

Follow-up on branch `pkg/06-image-release` (PR #10). Read the 06d section of `reviews/06-image-release/REPORT.md` and `briefs/06d-review-fixes.md`.

**Where 06d left off:** all six review fixes are implemented, and 82 regressions pass in checks-only runs. No full VM run passed:
- Full run 1 failed at the stock greeter check because the observer assumed SDDM. The pinned stock image uses **Plasma Login Manager** (`plasma-login-greeter` as `plasmalogin`). The saved frame shows the greeter rendered.
- Full run 2 was cancelled before guest testing.

The corrected observer (`5cbcfea`) is regression-tested only.

**Task:** get one green full run of the 06d guest sequence. It covers:
- the stock greeter, rendered and captured
- the transaction identity inspection before each reboot
- the switch and the full policy, including the rewritten negative checks
- tty3 login, sudo, then logout with the getty prompt confirmed
- partition equality
- rollback, with a **rendered stock greeter screenshot** you have inspected
- the second stock default boot

Reuse the signed image (`switch_from_run=39818554327`). The runtime payload must stay unchanged.

**Before every full dispatch:** check every assumption a new or changed check makes (process names, accounts, units, VTs, paths) against the retained package inventory and earlier evidence from this exact image, then record the check in the report. 06d lost both runs to an assumption that its own inventory contradicted.

**Pre-decided handling:**
- A harness flaw gets fixed with a regression and a checks-only run before the next full run.
- A product failure, including any rewritten negative check that now fires on the real image, means stop and report. Don't weaken the check.
- GRUB recovery promotion stays **untested** and listed as an open release gate. Don't spend runs on it.

**Constraints:** no mod changes, and no Gradle, mod build or Minecraft client test (the owner is using the laptop to play, and memory is short). No physical installation, no owner token, no visibility change.

**Budget:** at most **2 full runs** (switch-only reuse), plus checks-only runs as needed. About 1,285 of 2,000 monthly minutes are used.

**Acceptance:**
- A green full run with the inspected rendered rollback greeter screenshot.
- A "06e" section in `REPORT.md` listing the 06d "not verified" items that are now verified.
- Push the branch and keep PR #10 open. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
