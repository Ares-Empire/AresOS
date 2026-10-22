# 06b: Qualify the Bazzite → AresOS switch and rollback

Follow-up on branch `pkg/06-image-release` (draft PR #10). Read `reviews/06-image-release/REPORT.md`, especially "Not verified" and the attempt-6 reboot analysis.

**Situation:**
- The private signed image is published, and both fresh VM boots pass on `bazzite-nvidia-open`.
- On the stock stand-in, hardware setup, recovery-admin login and sudo, private verification, pull and staging all pass.
- The reboot after staging timed out. The likely cause is a harness flaw: the serial socket wasn't drained during reboot. It's fixed in `1745f55` with a regression test, but no full run has verified it.

**Goal:** green switch qualification. Reboot into the published AresOS digest → our labwc session → native account creation in that deployment → real tty3 administrator login → partition equality → rollback to stock → stock boots.

**In scope:**
- Use the **switch-only reuse mode** wherever it validly reuses the already-published image and digest, to save CI minutes. Rebuild only if the image source changed.
- Fix only what the runs reveal.

**Pre-decided handling:**
- Another **harness** flaw: fix it with a regression test and use the next run.
- A **product** failure (AresOS doesn't boot after the switch, accounts break, partitions change, rollback fails): stop and report precisely. Don't work around it.

**Budget:** at most 2 full CI runs (checks-only runs don't count). About 1,000 of 2,000 monthly minutes are used, so keep runs lean.

**Acceptance:**
- Green switch and rollback.
- `docs/INSTALL.md` §6 filled in with the tested recipe (no longer "unqualified").
- A "06b" section in `REPORT.md`, and the PR ready for review. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
