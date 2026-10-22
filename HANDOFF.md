# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-23, about 01:40)

- **Package 11** (draft PR #11, branch `pkg/11-two-disk-rehearsal`, worktree `C:/Users/pab/AresOS-11-two-disk-rehearsal`) stopped as briefed after 2 failed automation attempts (59 CI minutes). Media pins (part C) are done, and the protected-disk audit, two-disk fixture and Windows marker work. The protected disk stayed byte-identical in every check that ran. Blocker: the live ISO's installer is **Anaconda Web UI**, and kickstart is unsupported for live installs.
- **11b running since 01:36** (`briefs/11b-webui-install.md`): drive the real Web UI pages from a host-side headless browser through a forwarded port (fallback: Anaconda's D-Bus modules), with a mandatory probe before every full run, then finish parts A and B. Cap 350 minutes and 3 full runs (about 620 minutes were left in October). Codex PID 15420, log `C:/Users/pab/AresOS-11b.log`, final message `../AresOS-11b.last.md`.
- **When it finishes:** read the 11b REPORT section, then the package review (`docs/REVIEW.md`), the fix loop, and an explicit owner "merge". Bring any JUDGMENT-CALL to the owner in plain language.
- **Done 2026-10-23:** PR #10 merged (`2fa6641`); emergency card `docs/EMERGENCY.md` (`d8359f2`).

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
