# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-22, about 23:55)

- **PR #10 merged** as `2fa6641` (briefs 06–06e). The owner gave the merge OK in chat after accepting the judgment calls (recorded in `STATE.md` → Decisions). Branch `pkg/06-image-release` is deleted on GitHub; its worktree `C:/Users/pab/AresOS-06-image-release` is a leftover.
- **Nothing is running.**
- **Next:**
  1. ~~Emergency card~~: done 2026-10-23 (`docs/EMERGENCY.md`, reviews SAFE).
  2. **Remaining install gates** (INSTALL.md "Maintainer release gate"): the two-disk VM rehearsal, GRUB recovery promotion, media pinning and rehearsal, then the safety and followability council. Hardware items wait for the laptop.

## Waiting on the owner

- **Hardware ordered 2026-10-22** (€127.05: SSD, 2 USB sticks, PH0 + PH1 screwdrivers), delivery Mon 2026-10-26. The owner couldn't open the laptop without the right screwdriver, so the slot check now happens when the parts arrive. The SSD return must be requested by about 2026-11-09. Details are in `STATE.md`.

## Watch out

- **Only one Minecraft client-test run at a time** on the laptop (focus stealing). If the owner is playing, keep Gradle and client tests out of packages.
- **Merging:** delete a branch only after `gh pr view N --json state` = MERGED. Never launch Codex into a worktree with unmerged files. Claude Code's auto mode blocks `gh pr merge` without an explicit owner "merge" in chat.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Check its PID and the `turn.completed` line in its log. The owner can start Claude Code with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` to prevent this.
- **Codex assumptions:** before a full CI run, check every new check's assumptions against the image's retained package inventory (06d lost both runs assuming SDDM; Bazzite uses Plasma Login Manager).
- **CI minutes:** about 1,320 of 2,000 used in October.
- **Leftover worktrees** for merged branches 03, 04, 06, 07, 08, 09 and 10. Remove them with `git worktree remove` from the main checkout. The safety check blocks deleting a folder the session is inside.
- **Deferred work:** `briefs/03-followup-activation-audit.md` (activation-graph updater audit).
