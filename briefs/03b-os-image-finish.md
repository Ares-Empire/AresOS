# 03b: Finish the image checks (TTY prompt and clean poweroff)

Follow-up on branch `pkg/03-os-image` (draft PR #3). Read `reviews/03-os-image/REPORT.md`.

**Goal:** CI goes green on brief 03's full acceptance. The image already boots into labwc. Two things remain:
1. The recovery-TTY check fails on prompt-format synchronization (`root@bazzite:~#` vs. what the test waits for). Fix the test's synchronization properly. Wait on an unambiguous marker you print yourself, not on a prompt string. Keep the assertion that an authenticated recovery login works.
2. Verify the static power defaults end to end: a power-key event causes a clean poweroff, and lid or suspend requests do nothing.

**Also:** export the raw `bootc status` and the runtime updater inventory into the evidence (the report notes both were missed).

**Budget:** at most 3 more full CI runs (owner's Claude approved). Free quotas only, as in brief 03.

**Out of scope:** switching to `bazzite-nvidia-open` and publishing the image (that's brief 06), and everything else.

**Acceptance:** a green workflow run linked in a "03b" section of `REPORT.md`, the PR marked ready for review (not draft), and the PR description updated. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
