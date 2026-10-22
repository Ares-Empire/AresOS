# 03i: Verify the static audit with the Cockpit mask

Follow-up on branch `pkg/03-os-image` (PR #3). Read the 03h section of `reviews/03-os-image/REPORT.md`.

**Situation:** the static strict audit works. In VM 1 it correctly rejected Bazzite's generated `cockpit-container.service` (container auto-update from a mutable `:latest` image), a real inherited updater. 03h added its literal mask (checks-only green). No full run exists for this code.

**Goal:** a green full image workflow with **both VM passes**: canaries rejected, normal policy passing (no unmasked or unreviewed suspicious unit, none active), recovery, power/input, offline journal and logind proof.

**Pre-decided handling:** if a VM run reveals **another genuine inherited updater** (auto-update, rebase, package install or container auto-update), add its literal mask, or removal if it isn't needed (never an allowlist for mutable or privileged update paths), with a regression, and use the next run. Any other kind of failure: stop and report precisely. Never weaken an assertion.

**Budget:** at most 2 full CI runs. Checks-only runs don't count; run one before each full run.

**Acceptance:** a green full run with both VM passes, an "03i" section in `REPORT.md`, and the PR description updated. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
