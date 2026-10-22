# 03e: One final run for the offline journal reader

Follow-up on branch `pkg/03-os-image` (draft PR #3). Read the 03d section of `reviews/03-os-image/REPORT.md`.

**Budget: exactly one full CI run.** No code changes beyond what's needed to make the existing offline reader work: the committed `:r` Podman device fix, the read-only Btrfs extraction fallback, and runner `dmesg` capture on mount failure.

**Claude's integrator decision, made in advance:**
- **If the offline journal is read:** assert as 03d specified (marker → logind short-power-key record → logind poweroff → orderly stop). Green means done, and PR #3 goes ready for review.
  - If the journal is read and the logind record is **absent**, that's a real negative finding. Report it precisely, don't merge-prepare, and stop.
- **If the offline journal still can't be read:** make the logind-path check a **documented first-hardware-boot gate** instead of a CI gate.
  - Keep the code and the test, but mark that single assertion as reported, not blocking, with a clear label in the workflow output.
  - Add the exact hardware procedure from the 03c report to `docs/INSTALL.md` §7 (first boot checks).
  - Keep every other assertion blocking, including the observed clean poweroff (QMP guest shutdown and `poweroff.target`) and the second fresh VM pass.
  - This is the only assertion whose status may change, and only in this case.

**Acceptance:** one run, recorded in a "03e" section of `REPORT.md`, with the PR description updated. If the CI is green under the rules above, mark PR #3 ready for review. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
