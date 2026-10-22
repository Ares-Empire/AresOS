# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-22, about 22:45)

- **PR #10** (branch `pkg/06-image-release`, worktree `C:/Users/pab/AresOS-06-image-release`):
  - 06c green. The review of `ef07dbc` came back CHANGES-NEEDED (`reviews/06-image-release/REVIEW.md`).
  - **06d** implemented all six fixes and 82 regressions pass, but **no full VM run passed**. Codex's new greeter observer assumed SDDM, while the image uses **Plasma Login Manager**. The saved frame shows the greeter rendered. Both runs were used (one failed, one cancelled).
  - **Brief 06e running since 22:40:** one green full VM run of the 06d sequence (switch-only reuse, max 2 full runs, no Gradle/Minecraft). Codex PID 17128, log `C:/Users/pab/AresOS-06e.log`, final message `../AresOS-06e.last.md`.
- **When 06e is green:** the reviewer re-checks only the 06d/06e fixes (`docs/REVIEW.md`), then merge, once the owner has answered the judgment calls below. 06d adds one more: GRUB recovery uses an identity-checked `ostree admin set-default` (left untested, listed as a release gate).
- **Owner judgment calls asked 2026-10-22, answer pending** (recommended: accept all): (1) installer admin = UID 1000, daily `ares` = 1001; (2) keyless signing with a public Sigstore record (repo/workflow identity + digest; image stays private); (3) a classic read-only `read:packages` GitHub token on the laptop for the private pull.

## Waiting on the owner

- **Hardware ordered 2026-10-22** (€127.05: SSD, 2 USB sticks, PH0 + PH1 screwdrivers), delivery Mon 2026-10-26. The owner couldn't open the laptop without the right screwdriver, so the slot check now happens when the parts arrive. The SSD return must be requested by about 2026-11-09. Details are in `STATE.md`.

## Watch out

- **Only one Minecraft client-test run at a time** on the laptop (focus stealing).
- **Merging:** delete a branch only after `gh pr view N --json state` = MERGED. Never launch Codex into a worktree with unmerged files.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Watch the process ID with Monitor instead.
- **CI minutes:** about 1,150 of 2,000 used in October.
- **Leftover worktrees** for merged branches 03, 04, 07, 08, 09 and 10. Remove them with `git worktree remove` from the main checkout. The safety check blocks deleting a folder the session is inside.
- **Deferred work:** `briefs/03-followup-activation-audit.md` (activation-graph updater audit).
