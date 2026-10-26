# 15b: Fix the package 15 review findings

Follow-up on branch `pkg/15-owner-path` (PR #14, draft). Read `reviews/15-owner-path/REVIEW.md` (CHANGES-NEEDED). Brief 15 still applies.

Fix all five findings:

1. **Blocking: battery action** (`docs/EMERGENCY.md`).
   - Lead with what to do if the laptop is running or charging: stop using it, and disconnect the external charger only if that is safe without touching a hot or swollen case. Then move it away from anything flammable.
   - Then handle the separate case where the laptop is already open with the battery disconnected.
   - Keep the ban on handling the battery, and keep the requirement for service clearance.
   - Source it from Lenovo's own immediate-action or safety guidance, preferring the LOQ 15IRH8 manual. Use the T490 page only if nothing model-specific exists, and say which one you used.
2. **Blocking: step 7's reboot.**
   - Every place that tells the owner to restart through the tool shows the full canonical command from `os/owner-tools/commands.json` (`sudo /var/lib/ares/at reboot`) and its expected result. Never a bare word that reads like plain `reboot`.
   - Extend the equality test: actionable inline invocations of any owner command, not just fenced Bash blocks, must match `commands.json`. Add a mutation test that a bare inline `reboot` fails it.
3. **Should-fix: boot-order STOPs.**
   - Restore the explicit owner-facing STOP conditions beside the boot-order procedure: Secure Boot changed, a Windows recovery prompt, and a missing internal boot entry while its SSD is attached.
   - Each gets STOP → Help with a named return destination.
4. **Should-fix: returns that keep the calling context.**
   - A record (B/C/D) called from keep-stock returns to keep-stock or step 8, not to step 7.
   - Layout recovery on AresOS returns through proof/finish/completion, then step 8, not step 5.
   - Add tests for these state-dependent returns: link reachability alone can't catch them.
5. **Should-fix: status table release labels.**
   - Label every historical result with the release it tested.
   - Separate the current release's (`9b19b7…`) 13f evidence and limits from the earlier `362af9…` results and from 11n.
   - Keep the drive-order and physical-test limits.

**Also:**
- Remove the 27 dev-client screenshots under `reviews/15-owner-path/screenshots/`. This is a docs-only package and they aren't evidence for it. Keep the report's note that the client suite ran: one timeout, then one pass.
- Restore any tracked screenshots that the client run changed elsewhere, as you already did.

**Tests:** the owner-path and equality tests, plus the full owner suite in WSL. Don't rerun the Minecraft client suite; nothing in this package touches the mod. Pinned local gitleaks over the full history before the **single push** at the end (org at least 150 free minutes). Update the REPORT with a short 15b section. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 15 Codex session).
