# 03h: Converge PR #3, with a pre-decided split

Follow-up on branch `pkg/03-os-image` (PR #3). Read the 03f and 03g sections of `reviews/03-os-image/REPORT.md`.

**Situation:** the image itself has booted into labwc in every run. Recent failures came only from test machinery for the review's should-fix #2 (activation-aware updater audit): parser bugs, then the 03g release-container preflight failing to start `user@1000.service`. The blocking fix (narrowed contingency) and the pinned toolchain are done and unit-tested.

**Claude's integrator decisions, made in advance:**
1. **The release-container preflight becomes diagnostic only.** Keep it if useful, but it must not block the workflow: a container is not the real boot environment, and it was never an acceptance requirement.
2. **Full run 1** on the current 03f/03g code, with the preflight non-blocking. Green → done.
3. **If run 1 fails in the VM's activation-graph audit** (live managers, dependency following, canary fixtures):
   - Replace that part with the **static strict rule**: every suspicious updater unit must be masked or explicitly on the reviewed allowlist **regardless of unit-file state**, and the live VM must show **no suspicious unit active or running**.
   - Keep the generated-unit coverage if it works in the static form. Otherwise defer it too.
   - Move the activation-graph audit, its canaries and the preflight into a new follow-up brief file `briefs/03-followup-activation-audit.md`, recorded as a residual in the report.
   - **Full run 2** must then be green.
4. Never weaken any other assertion: recovery, power, offline journal/logind, both VM passes, release isolation, the narrowed contingency.

**Budget:** at most 2 full CI runs. Checks-only runs don't count.

**Acceptance:** a green full run with both VM passes, an "03h" section in `REPORT.md`, the PR description updated, and the PR ready for review. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
