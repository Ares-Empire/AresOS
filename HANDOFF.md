# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-22, about 21:45)

- **PR #10** (branch `pkg/06-image-release`, worktree `C:/Users/pab/AresOS-06-image-release`):
  - **06c done:** CI run 2 (39833127717) passed switch, Homebrew policy, tty3 recovery, partitions and rollback.
  - **Package review of `ef07dbc`: CHANGES-NEEDED** (`reviews/06-image-release/REVIEW.md`): 5 should-fix and 1 nit. The key one is `! cmd` checks being exempt from `set -e`, so negative assertions never failed (this includes PR #3's `guest.sh`).
  - **Brief 06d** (all six fixes, no Gradle/Minecraft tests because the owner is playing, max 2 full runs) **running since about 21:45**. Codex log `C:/Users/pab/AresOS-06d.log` (`turn.completed` = done), final message `../AresOS-06d.last.md`.
- **When 06d finishes:** the reviewer re-checks only the fixes (`docs/REVIEW.md`), then merge, once the owner has answered the judgment calls below.
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
