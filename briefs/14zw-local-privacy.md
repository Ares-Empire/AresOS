# 14zw: The privacy check now runs locally before each push; merge main, then probe and qualification

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zv still apply, with the changes below.

## Integrator decision: privacy proof is the local pre-push hook

The owner's decision on 2026-11-01, made in another session (`fabd476` on `main`) for every Ares-Empire repo:

- **The GitHub privacy workflow is removed.** It runs instead as aresync's local pre-push hook: the repository's `hooks/pre-push` calls `/c/Users/pab/aresync/privacy-check.sh pre-push`. The hook checks gitleaks, noreply emails, and personal terms from `~/.config/aresync/private-terms`, and blocks the push on any finding.
- **The `PRIVATE_TERMS` repo secret is gone.** So this branch's leftover `privacy-check.yml` now skips personal terms.
- **Pull-request privacy runs no longer happen,** because `main` has no such workflow.

So:

1. **Merge `origin/main` into the branch** with a merge commit; never rebase or force-push. This removes `privacy-check.yml` from the branch, so pushes start no workflow and cost no minutes. In `HANDOFF.md` and `STATE.md`, take `main`'s version.
2. **Privacy proof for a head:**
   - The push itself goes through the hook. Never use `--no-verify`. If the hook blocks, STOP and report what it found, without terms or secret values.
   - Before pushing, run the same check yourself on the exact range to be pushed: `privacy-check.sh pre-push` with the hook's standard stdin. Record its exit code, the gitleaks version, and that the "personal terms check skipped" warning was absent.
   - Record no terms, and print no findings beyond what the hook prints.
   - Keep the pinned local gitleaks 8.21.2 scan as before.
3. **Remove the GitHub-privacy gates:**
   - the exact-head privacy run and the pull-request privacy run
   - the push (6) and closing (12) privacy minute reservations: set them to 0, with this brief as the reason
   - historical October/November tests on fixed dates may stay

   Keep the organization reserve at 150, and keep the probe and qualification bounds. Adjust the minute cap only if your 14zv figure needs it.
4. **Local checks for the changed gates,** then one push, then the **probe and qualification on that same head** as in 14zv.
5. Then **STOP and report** as in 14zv.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
