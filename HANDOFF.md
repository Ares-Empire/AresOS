# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-25)

- **PR #11 merged** (`0c5902a`, squash of briefs 11–11n). 11n's Part B passed in the protected-second VM order. The fresh fix re-review of `d7f0ac4..5d69724` said SAFE (`reviews/11-two-disk-rehearsal/REVIEW.md`, second section). Package 11's CI ledger closed at about 722/900 minutes (5 full runs and 1 Part B run). The org quota resets 1 Nov.
- **Package 13 (keyboard layout) MERGED 2026-10-25 as `775be05`** (PR #12, briefs 13–13g). The first review was CHANGES-NEEDED; the 13g guide fixes made the re-review SAFE. The owner OK'd both JUDGMENT-CALLs and decided the backup keeps the installer's layout. Ledger 389/460. Worktree `C:/Users/pab/AresOS-13-keyboard-layout` is kept (its ignored `.work/` holds local scratch only); the branch isn't deleted. **Next AresOS step:** the safety and followability council on INSTALL.md and OS-BASE §8 / Appendix C (the last gate that doesn't need the laptop).
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
