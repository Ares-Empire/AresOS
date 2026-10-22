# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-22, about 20:35)

- **Brief 06c resumed at 20:34** (PR #10, draft, branch `pkg/06-image-release`, worktree `C:/Users/pab/AresOS-06-image-release`). Codex gpt-6.1-sol xhigh, log `C:/Users/pab/AresOS-06c-resume.log` (`turn.completed` = done), final message `../AresOS-06c-resume.last.md`.
  - Full run `39818554327` was **full run 1 of 2**: the image job passed, and the switch job failed in `os/ci/switch_vm.py` at guest command `tty-password-ready` (exit 1), after stock Bazzite's pre-login reboot. Codex decides whether that's a harness flaw (fix with a regression) or a product failure (stop and report).
  - One full run is left in the 06c budget. About 1,230 of 2,000 CI minutes used in October.
- **When it finishes:** read its REPORT 06c section, then do the confirm review and merge PR #10 per `docs/WORKFLOW.md`.
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
