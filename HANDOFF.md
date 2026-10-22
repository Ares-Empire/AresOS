# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where I stopped (2026-10-22, about 19:55)

- **Brief 06c is paused** (PR #10, draft, branch `pkg/06-image-release`, worktree `C:\Users\pab\AresOS-06-image-release`).
  - Claude stopped the Codex process so the owner could shut down for the SSD-slot check. Its in-progress evidence was pushed as `cc5fc42` (WIP, `[skip ci]`).
  - **GitHub full run `39818554327` ("OS image") was still running** and continues on GitHub. The image job had built the disk and was in the two VM boots. The switch job comes next: stock → AresOS → policy (including the Homebrew neutralization) → tty3 recovery → partitions → rollback.
- **To resume:**
  1. Check the run: `gh run view 39818554327`.
  2. Relaunch Codex in that worktree (gpt-6.1-sol, xhigh) with: "Read AGENTS.md and briefs/06c-inherited-homebrew.md. You were stopped mid-run. Full run 39818554327 counts as full run 1 of 2. Read its result and evidence, then continue the brief."
  3. Then do the confirm review and merge PR #10.
- **Already proven before 06c:** the private signed image on `bazzite-nvidia-open`. Stock Bazzite switched to AresOS and booted, and the session, accounts and partitions passed. 06b's policy check caught inherited Homebrew, which 06c neutralizes reversibly.

## Waiting on the owner

- **Hardware ordered 2026-10-22** (€127.05: SSD, 2 USB sticks, PH0 + PH1 screwdrivers), delivery Mon 2026-10-26. The owner couldn't open the laptop without the right screwdriver, so the slot check now happens when the parts arrive. The SSD return must be requested by about 2026-11-09. Details are in `STATE.md`.

## Watch out

- **Only one Minecraft client-test run at a time** on the laptop (focus stealing).
- **Merging:** delete a branch only after `gh pr view N --json state` = MERGED. Never launch Codex into a worktree with unmerged files.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Watch the process ID with Monitor instead.
- **CI minutes:** about 1,150 of 2,000 used in October.
- **Leftover worktrees** for merged branches 03, 04, 07, 08, 09 and 10. Remove them with `git worktree remove` from the main checkout. The safety check blocks deleting a folder the session is inside.
- **Deferred work:** `briefs/03-followup-activation-audit.md` (activation-graph updater audit).
