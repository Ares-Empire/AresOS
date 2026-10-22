# 06c: Neutralize inherited Homebrew after the switch, then finish qualification

Follow-up on branch `pkg/06-image-release` (draft PR #10). Read the 06b section of `reviews/06-image-release/REPORT.md`.

**Finding (06b):** after switching stock Bazzite to AresOS, the published image boots, and the session, account and partition checks pass. The policy check then correctly failed: the daily `ares` user can execute **Homebrew** inherited from the stock install. Persistent `/var/home/linuxbrew` survives a rebase.

**Claude's integrator decision** (consistent with `docs/design/OS-BASE.md` A1: inherited package managers and updaters are not usable by the daily account; only AresOS maintenance changes software):
- In the AresOS image, make inherited Homebrew **unusable by `ares`, reversibly and without deleting anything**. For example, a tmpfiles/ACL or permission rule that denies `ares` traversal and execution of the Homebrew prefix, plus keeping brew off `ares`'s PATH and masking any brew update/setup timers or services.
- Stock Bazzite's owner of the prefix (the first stock user) must keep working after a **rollback**. Verify that in the rollback step.
- Apply the same reasoning to any other inherited user-level package manager or updater the policy check finds in the switched state (for example Distrobox auto-updates or Flatpak user remotes with auto-update). Neutralize reversibly, add a regression, and report each one.
- Regression: switched-state policy shows `ares` can't execute brew, and the stock owner still can.

**Then finish qualification** in the same runs: tty3 recovery-administrator login in the AresOS deployment, partition equality, rollback to stock, and stock boots.

**Pre-decided handling:** further inherited user-level mutation paths are neutralized the same way. A harness flaw gets fixed with a regression. Any other product failure means stop and report.

**Budget:** at most 2 full CI runs, rebuilding and publishing only if the image changed. About 1,100 of 2,000 monthly minutes are used.

**Acceptance:**
- Green switch, policy, recovery and rollback.
- `docs/INSTALL.md` §6 filled in with the tested recipe.
- A "06c" section in `REPORT.md`, and the PR ready for review. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
