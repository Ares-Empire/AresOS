# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-25)

- **PR #11 merged** (`0c5902a`, squash of briefs 11–11n). 11n's Part B passed in the protected-second VM order. The fresh fix re-review of `d7f0ac4..5d69724` said SAFE (`reviews/11-two-disk-rehearsal/REVIEW.md`, second section). Package 11's CI ledger closed at about 722/900 minutes (5 full runs and 1 Part B run). The org quota resets 1 Nov.
- **Package 13 (keyboard layout) MERGED 2026-10-25 as `775be05`** (PR #12, briefs 13–13g). The first review was CHANGES-NEEDED; the 13g guide fixes made the re-review SAFE. The owner OK'd both JUDGMENT-CALLs and decided the backup keeps the installer's layout. Ledger 389/460. Worktree `C:/Users/pab/AresOS-13-keyboard-layout` is kept (its ignored `.work/` holds local scratch only); the branch isn't deleted. **Next AresOS step:** the safety and followability council on INSTALL.md and OS-BASE §8 / Appendix C (the last gate that doesn't need the laptop).
- **Install-gate council DONE 2026-10-25** on `6eb2d0b` (gpt-6-astra, max, read-only): `reviews/councils/2026-10-25-install-gate/` (QUESTION, safety, followability, recovery, VERDICT). **GAPS-FOUND (11): 7 BLOCKING, 4 NON-BLOCKING.** Blocking: (1) the stock-title link skips §5; (2) the owner rollback block lacks CI's target checks; (3) a layout change reboots before proving the password still types; (4) no token revocation on abandonment; (5) first-login preparation order conflicts (EMERGENCY pins first, repair rejects pinned stock; staged update stops repair before cleanup); (6) 547 lines of hand-typed root shell; (7) the tty3 identity check prints ~142 KB of JSON. Next: a fix package (verified helper bundle with short commands, one linear owner checklist, shorter emergency card), owner go pending, then a chair delta check. The worktree was removed. October org Actions use: about 1,406 of 2,000 minutes.
- **Package 14 (owner tools) RUNNING since 2026-10-25** on `pkg/14-owner-tools` (brief `362d077`), worktree `C:/Users/pab/AresOS-14-owner-tools`. Codex session `01a165f9-31fc-79c2-80de-0a8237188116` (gpt-6.1-sol, xhigh), log `../AresOS-14.log`, final message `../AresOS-14.last.md`. It fixes council findings 2, 3, 5, 6 and 7. Owner decisions in the brief: two sticks only (the installer stick becomes the tools stick after the install, via Media Writer's restore), and the laptop stays offline until `prepare` has paused updates. Ledger cap 350 min, 150-min org reserve. **Package 15 comes after 14 merges:** the owner-path rewrite and the emergency card around the new commands (findings 1, 4 and 8–11, plus the council's proportionality list and 14's "for package 15" list). Then the council chair's delta check over both. **Update:** 14's zero-cost gate stopped with a PLAN-GAP: the NVIDIA Flatpak runtime sync retries a Flathub install while offline. Brief 14b (`11728c5`) accepts it as deferred work, since it only touches `/var/lib/flatpak`. 14b then stopped at a second PLAN-GAP: a tools stick present at boot gets a firmware auto entry that the NVRAM audit rejects. Brief 14c (`e96310d`) doesn't widen the audit; instead the stick is hot-plugged after Linux is up and removed before every restart, in both the owner route and CI. 14c is running: log `../AresOS-14c.log`, final message `../AresOS-14c.last.md`, draft PR #13. If the launcher is reaped, codex.exe survives; watch the log for `turn.completed`.
- **Package 12 (the companion in the hub):** brief drafted, not committed, waiting for the owner's go. Draft: `C:/Users/pab/AppData/Local/Temp/claude/C--Users-pab/c9cf9395-8808-409c-be1f-c393ff13e99c/scratchpad/12-hub-companion.md`. On go: commit it as `briefs/12-hub-companion.md`, create worktree `../AresOS-12-hub-companion`, start a **new** Codex session (gpt-6.1-sol xhigh). The Claude crab look is never in this repo. After Codex defines the pack format, Claude writes the private Clawd pack in `C:/Users/pab/aresos-companions/clawd/` (front view 18x5, see the preview) and checks it in the dev client.
- **Companions** live in their own private repo `Ares-Empire/companions` (local `C:/Users/pab/companions`; `python tools/serve.py`, then http://127.0.0.1:8765/preview/). Each companion is a `companions/<id>/design.json`: Clawd plus three app companions (Chromie, Termi, Foldi), outfits, bed sleep, file basketball. The Clawd art stays out of this repo.
- **Later:** new releases from the org publish to `ghcr.io/ares-empire/aresos` with a new Sigstore identity (`publish.sh` and `os-image.yml` still name `carlsenares`). The CI secret `GHCR_READ_TOKEN` expires about 2026-11-22.

## History rewrite (2026-10-23 09:34 UTC)

- An owner-run Claude session rewrote the GitHub history to replace the personal email with the no-reply address. All SHAs changed, so SHAs in older docs name pre-rewrite commits.
- The old local heads are kept as `pre-rewrite/*`. **Never push them, and never force-push.**
- The repo-local git identity is `Patrik Breeck <287037715+carlsenares@users.noreply.github.com>`. The global identity is still personal, so a fresh clone needs the local identity set.

## Waiting on the owner

- **Hardware** (ordered 2026-10-22, €127.05: SSD, 2 USB sticks, PH0 + PH1 screwdrivers), delivery Mon 2026-10-26. The slot check happens when the parts arrive. The SSD return must be requested by about 2026-11-09. Details in `STATE.md`.
- **Go for package 12.**

## Watch out

- **Only one Minecraft client-test run at a time** on the laptop (focus stealing). If the owner is playing, keep Gradle and client tests out of packages.
- **Merging:** delete a branch only after `gh pr view N --json state` = MERGED. Never launch Codex into a worktree with unmerged files.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Check its PID and the `turn.completed` line in its log.
- **Codex assumptions:** check every new check's assumptions against the retained real inventories, not just mocks (11i lost a full run to a mocked `pgrep`).
- **Leftover worktrees** for merged branches 03, 04, 06, 07, 08, 09, 10, 11 and now 13. Remove them with `git worktree remove` from the main checkout once nothing in them is needed (11's ignored `.work/` folders hold local scratch only; the evidence is committed).
- **Deferred work:** `briefs/03-followup-activation-audit.md` (activation-graph updater audit).
